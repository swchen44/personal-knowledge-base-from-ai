---
title: "Claude Code 原始碼分析：CLAUDE.md 與 Skills 的熱載入機制——Symlink、@include 指令與快取全解析"
date: 2026-04-14
category: DevTools
tags:
  - "#devtools/claude-code"
  - "#ai/agent-architecture"
  - "#devtools/configuration"
  - "#tools/cli"
source: "conversation"
source_type: article
author: "swchen44 + Claude"
status: notes
links:
  - "[[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
  - "[[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]"
  - "[[2026-03-30-BORIS-CHERNY-HIDDEN-CLAUDE-CODE-FEATURES]]"
---

## 摘要（Summary）

深入研究 Claude Code 反編譯原始碼，追蹤 CLAUDE.md 與 `.claude/skills/` 在對話過程中的載入時機與快取機制。核心發現：**CLAUDE.md 在 session 啟動時讀取一次後即快取（memoize），對話中修改不會生效**；而 **Skills 透過 chokidar 檔案監控實現熱載入（Hot Reload），對話中修改會即時生效**。進一步追蹤 CLAUDE.md 的 `@include` 指令機制：**只有 `@path` 一種語法有效**（不存在 `@include` 關鍵字或 `read` 語法），所有被引用的檔案在啟動時**遞迴 eager loading**，最深 5 層，同樣被 memoize 快取。對於使用 symlink 管理設定的用戶，這意味著 CLAUDE.md 及其 `@` 引用的所有檔案都需要 `--resume` 才能刷新。

## 關鍵洞察（Key Insights）

- **CLAUDE.md 被 `memoize()` 包裝**，整個 session 只讀取一次磁碟，之後所有 API call 使用快取內容 — 參見 [[CLAUDE-CODE-CONTEXT-ENGINEERING]]
- **Skills 的熱載入是「chokidar 清除快取 + 整體重新載入」**，非逐次延遲載入（~~Lazy Loading~~）。Skill 內容在載入時被閉包（Closure）捕獲，chokidar 偵測變更後清除 memoize 快取，下次存取時從磁碟重新讀取所有 SKILL.md — 參見 [[CLAUDE-CODE-SKILLS-DOCUMENTATION]]
- **Symlink 完整支援**：程式碼用 `realpath()` 解析 canonical path 做去重，chokidar 也能透過 symlink 偵測變更
- **`--resume` 會清除所有快取**：啟動新程序時明確呼叫 `clearSessionCaches()` → `resetGetMemoryFilesCache()`，因此 CLAUDE.md 會重新讀取
- **System prompt 每次 API call 都重新組裝**，但底層資料（CLAUDE.md 內容、git status）來自快取
- **`@path` 是唯一有效的 include 語法**：不存在 `@include` 關鍵字或 `read` 指令，regex 為 `/(?:^|\s)@((?:[^\s\\]|\\ )+)/g`
- **@include 是 eager loading**：所有被引用的檔案在 `getMemoryFiles()` 時就遞迴讀取完畢，不是按需載入
- **最深 5 層遞迴**（`MAX_INCLUDE_DEPTH = 5`），有循環引用保護（`processedPaths: Set<string>`）
- **Skill 的按需是 Token 層而非 I/O 層**：所有 SKILL.md 啟動時就讀進記憶體，但 system prompt 只注入 name+description 索引（佔上下文 1%），完整內容只在呼叫時才注入對話，節省 ~97% Token
- **Plugin 不能注入 CLAUDE.md 或 Rules**：Plugin Manifest 沒有 `rules` 或 `claudeMd` 欄位，`getMemoryFiles()` 不掃描 plugin 目錄。Plugin 只能透過 skills/commands/hooks 間接影響行為，無法達到 system prompt 級的全局指令效果
- **有條件規則（Conditional Rules）是唯一真正按需的 CLAUDE.md 級指令**：在 `paths:` frontmatter 中指定 glob 模式，只在 FileReadTool 讀取匹配路徑時才從磁碟讀取並注入（`nested_memory` attachment），是被低估的 Token 最佳化手段

## 詳細內容（Details）

### CLAUDE.md 的載入機制

CLAUDE.md 的載入鏈涉及三個關鍵函式，全部被 lodash 的 `memoize()` 包裝：

```typescript
// src/utils/claudemd.ts:790
export const getMemoryFiles = memoize(
  async (forceIncludeExternal: boolean = false): Promise<MemoryFileInfo[]> => {
    // 從磁碟讀取所有 CLAUDE.md 檔案
    // 處理 @include 指令載入巢狀檔案
    // 回傳 MemoryFileInfo[] 包含完整檔案內容
  },
);

// src/context.ts:155
export const getUserContext = memoize(async (): Promise<...> => {
  // 呼叫 getMemoryFiles() 取得 CLAUDE.md 內容
  // 組裝 user context 字串
});

// src/context.ts:116
export const getSystemContext = memoize(async (): Promise<...> => {
  // 擷取 git status 快照（也只讀一次）
});
```

> [!important] 三層 memoize 的影響
> `getMemoryFiles()` → `getUserContext()` → `getSystemContext()` 全部被快取。即使 system prompt 每次 API call 都重新組裝（在 `QueryEngine.ts:291-303` 的 `fetchSystemPromptParts()`），底層資料不會刷新。

### CLAUDE.md 的發現範圍

`getMemoryFiles()` 會搜尋以下路徑的 CLAUDE.md：

| 層級 | 路徑 | 說明 |
|------|------|------|
| Managed | `/etc/claude-code/CLAUDE.md` | 系統管理層（System Managed） |
| User | `~/.claude/CLAUDE.md` | 使用者層（User-level） |
| Project | `./CLAUDE.md`、`.claude/CLAUDE.md`、`.claude/rules/*.md` | 專案層（Project-level） |
| Local | `./CLAUDE.local.md` | 本地層（Local-only） |
| Auto-memory | 自動記憶檔案 | 啟用時載入 |

### Skills 的熱載入機制

> [!warning] 勘誤（Erratum）
> 初版描述 skill 內容為「每次呼叫時從磁碟重新讀取（lazy loading）」，經進一步追蹤原始碼確認為**不正確**。實際機制是**閉包捕獲（closure capture）+ chokidar 觸發整體重新載入**，詳見下方。

Skills 的行為與 CLAUDE.md 不同，差異在於有 chokidar 監控觸發快取清除：

**1. Skill 載入流程——閉包捕獲**

```
 啟動 / chokidar 清除快取後的首次呼叫
   │
   ▼
 getSkillDirCommands(cwd)  ← memoize 包裝
   │
   ▼
 loadSkillsFromSkillsDir(basePath)
   │
   ├── fs.readdir(basePath)        ← 列出 .claude/skills/ 下所有子目錄
   │
   └── 對每個子目錄：
         │
         ├── fs.readFile(SKILL.md)  ← 讀取完整內容到記憶體
         │
         ├── parseFrontmatter()     ← 分離 frontmatter 和 markdownContent
         │
         └── createSkillCommand({
               markdownContent,     ← 內容被封裝進閉包
               ...
             })
               │
               └── getPromptForCommand(args) {
                     // markdownContent 來自閉包，不再讀磁碟
                     let finalContent = markdownContent
                     finalContent = substituteArguments(...)
                     finalContent = await executeShellCommandsInPrompt(...)
                     return [{ type: 'text', text: finalContent }]
                   }
```

> [!important] 內容在載入時就已讀完
> `markdownContent` 在 `loadSkillsFromSkillsDir()` 中被 `fs.readFile()` 讀取，然後傳入 `createSkillCommand()` 作為閉包變數。`getPromptForCommand()` 每次呼叫時**不會重新讀磁碟**，而是使用閉包中已快取的內容。

**2. chokidar 檔案監控觸發重新載入**

```
 檔案變更（修改 SKILL.md / symlink 指向的檔案）
   │
   ▼
 chokidar.watch(skillDirectories, { atomic: true })
   │
   ▼
 scheduleReload(changedPath)
   │
   ▼
 setTimeout(300ms debounce)     ← 批次處理，防止重複清除
   │
   ▼
 clearSkillCaches()             ← getSkillDirCommands.cache.clear()
 clearCommandsCache()           ← loadAllCommands.cache.clear()
                                   getSkillToolCommands.cache.clear()
                                   clearSkillIndexCache()
 skillsChanged.emit()           ← 通知 UI 更新
   │
   ▼
 下次需要 skills 時（如 API call 組裝 system prompt）
   │
   ▼
 getSkillDirCommands(cwd)       ← 快取已清除，觸發完整重新載入
   │
   └── 從磁碟重新讀取所有 SKILL.md → 建立新閉包 → 新 markdownContent
```

> [!tip] Symlink 感知
> chokidar 設定了 `atomic: true`，能正確偵測透過 symlink 的檔案變更。同時 `getFileIdentity()` 用 `realpath()` 解析 canonical path，確保同一檔案不會因不同路徑被重複載入。

**3. 完整快取清除鏈時序圖**

```
 chokidar       scheduleReload      clearSkillCaches     getSkillDirCommands
    │                │                     │                      │
    │──file change──►│                     │                      │
    │                │──setTimeout(300ms)──►│                      │
    │                │                     │                      │
    │                │  (debounce 期間      │                      │
    │──file change──►│   更多變更被合併)     │                      │
    │                │                     │                      │
    │                │     300ms 到期       │                      │
    │                │────────────────────►│                      │
    │                │                     │──cache.clear()───────►│
    │                │                     │  (memoize 快取清除)    │
    │                │                     │                      │
    │                │                     │──emit(skillsChanged) │
    │                │                     │                      │
    │                │        下一次 API call 需要 skills           │
    │                │                     │     getCommands()────►│
    │                │                     │                      │
    │                │                     │              重新讀磁碟│
    │                │                     │              建立新閉包│
    │                │                     │◄──新 Command[]────────│
```

> [!note] 與 CLAUDE.md 的關鍵差異
> CLAUDE.md 也是啟動時全部讀完並 memoize，但**沒有 chokidar 監控**來清除快取。Skills 有 chokidar 監控，所以檔案變更後快取會被清除，下次存取時重新讀取。這就是 skills 能在對話中「即時生效」而 CLAUDE.md 不能的根本原因。

**4. 多層 memoize 快取架構**

```
┌─────────────────────────────────────────────────────────┐
│                    API call 層                           │
│  queryModel() → fetchSystemPromptParts()                │
│       │                                                 │
│       ▼                                                 │
│  getCommands(cwd)  ← 每次呼叫，但底層 memoized          │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────┐            │
│  │ loadAllCommands(cwd)  ← memoize 層 1   │            │
│  │     │                                   │            │
│  │     ▼                                   │            │
│  │ getSkillDirCommands(cwd) ← memoize 層 2 │            │
│  │     │                                   │            │
│  │     ▼                                   │            │
│  │ loadSkillsFromSkillsDir()               │            │
│  │   → fs.readFile(SKILL.md)               │            │
│  │   → createSkillCommand()                │            │
│  │   → markdownContent 進入閉包            │            │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  chokidar 觸發時清除：                                   │
│    clearSkillCaches()     → 層 2 清除                    │
│    clearCommandsCache()  → 層 1 + 層 2 + 索引全清除      │
└─────────────────────────────────────────────────────────┘
```

### Skill 的 Token 層按需注入機制

> [!important] 按需（On-demand）的層次
> Skill 的「按需載入」不是指**磁碟 I/O 層**（所有 SKILL.md 啟動時就全部讀進記憶體），而是指 **Token 注入層**：system prompt 只放名稱+描述的索引，完整內容只在 skill 被呼叫時才注入對話。

**兩階段注入架構圖**

```
┌──────────────────────────────────────────────────────────────┐
│                  階段 1：索引注入（每次 API call）              │
│                                                              │
│  getSkillListingAttachments()                                │
│    │                                                         │
│    ├── 取出所有 skill 的 name + description + whenToUse       │
│    │                                                         │
│    ├── formatCommandsWithinBudget()                          │
│    │     │                                                   │
│    │     ├── 預算：上下文視窗的 1%（200K → 8,000 字元）        │
│    │     ├── 每條描述上限 250 字元                             │
│    │     └── 超出預算 → 截斷描述 → 極端時只放名稱             │
│    │                                                         │
│    └── 注入為 system-reminder：                               │
│          "- kb-create: 讀取網頁文章..."                       │
│          "- commit: Create a git commit"                     │
│                                                              │
│  Token 消耗：~1,000 tokens（50 個 skills）                    │
└──────────────────────────────────────────────────────────────┘
                           │
              模型看到索引，決定呼叫某個 skill
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│             階段 2：完整內容注入（呼叫時）                      │
│                                                              │
│  SkillTool.call()                                            │
│    │                                                         │
│    └── getPromptForCommand(args)                             │
│          │                                                   │
│          ├── 從閉包取出 markdownContent（完整 SKILL.md 正文）  │
│          ├── substituteArguments()    ← 替換 $ARGUMENTS       │
│          ├── executeShellCommandsInPrompt() ← 執行 !` ` 指令  │
│          └── 回傳完整 prompt → 注入對話                       │
│                                                              │
│  Token 消耗：~750 tokens（單個 3,000 字的 skill）              │
└──────────────────────────────────────────────────────────────┘
```

**Token 節省效果**

```
 假設：50 個 skills，每個 SKILL.md 平均 3,000 字

 全部注入方案（假設性）：
   50 × 3,000 = 150,000 字 ≈ 37,500 tokens  ❌ 每次 API call

 按需注入方案（Claude Code 實際做法）：
   skill_listing:  50 × ~80 字 = ~4,000 字 ≈ 1,000 tokens  ✅
   呼叫時注入:      1 × 3,000 字 ≈ 750 tokens（僅在需要時）

 節省率：~97%（每次 API call 省 ~36,000 tokens）
```

**關鍵程式碼**

```typescript
// src/tools/SkillTool/prompt.ts:20-28
// 索引預算：上下文視窗的 1%
export const SKILL_BUDGET_CONTEXT_PERCENT = 0.01
export const DEFAULT_CHAR_BUDGET = 8_000

// 每條描述上限 — 索引只是為了讓模型找到 skill，不需要完整內容
// "the Skill tool loads full content on invoke"
export const MAX_LISTING_DESC_CHARS = 250
```

```typescript
// src/skills/loadSkillsDir.ts:96-105
// Token 估算只算 frontmatter，不算正文
export function estimateSkillFrontmatterTokens(skill: Command): number {
  const frontmatterText = [skill.name, skill.description, skill.whenToUse]
    .filter(Boolean)
    .join(' ')
  return roughTokenCountEstimation(frontmatterText)
}
```

**超出預算時的三級降級策略**

```
 50 個 skills，預算 8,000 字元
   │
   ▼
 策略 1：完整描述（name + description + whenToUse，≤250 字/條）
   │ 超出預算
   ▼
 策略 2：截斷描述（bundled skills 保留完整，其他按比例縮短）
   │ maxDescLen < 20 字
   ▼
 策略 3：只放名稱（bundled 例外保留描述）
   例："- kb-create"（無描述）
```

> [!note] parseFrontmatter 的角色
> 磁碟層面沒有「只讀前半段」的機制。`fs.readFile()` 讀完整檔案，然後 `parseFrontmatter()` 將內容分離成 YAML frontmatter 和 markdown 正文兩部分。frontmatter 用於建立索引（`skill_listing`），正文存入閉包等待被呼叫時注入。

### `--resume` 的快取清除流程

```typescript
// src/main.tsx:3358-3362
const { clearSessionCaches } = await import('./commands/clear/caches.js');
clearSessionCaches();
// 內部呼叫 resetGetMemoryFilesCache('session_start')
// → getMemoryFiles.cache.clear()
```

> [!important] 新程序 = 全新快取
> `claude --resume` 啟動的是全新的 Bun 程序。即使沒有明確清除快取，in-memory 的 `memoize` 快取本來就不會跨程序存活。程式碼中額外呼叫 `clearSessionCaches()` 是雙重保險。

### 行為對照表

```
┌────────────────────────┬──────────────────┬──────────────────┐
│          項目           │   對話中修改      │  --resume 後     │
├────────────────────────┼──────────────────┼──────────────────┤
│ CLAUDE.md               │ ❌ 不生效         │ ✅ 重新讀取      │
│ CLAUDE.md 中 @path 檔案 │ ❌ 不生效         │ ✅ 重新讀取      │
│ .claude/rules/（無條件） │ ❌ 不生效         │ ✅ 重新讀取      │
│ .claude/rules/（有條件） │ ✅ 按需讀取+注入  │ ✅ 重新讀取      │
│ .claude/skills/         │ ✅ 即時生效       │ ✅ 重新讀取      │
│ .claude/commands/       │ ✅ 即時生效       │ ✅ 重新讀取      │
│ Plugin skills/commands  │ ✅ 即時生效       │ ✅ 重新讀取      │
│ Git status 快照         │ ❌ 不更新         │ ✅ 重新擷取      │
│ System prompt 組裝      │ ✅ 每次重組       │ ✅ 每次重組      │
│ 對話訊息                │ — 持續累積       │ ✅ 從 transcript  │
│                        │                  │    恢復           │
└────────────────────────┴──────────────────┴──────────────────┘
```

### CLAUDE.md 的 `@` Include 指令機制

> [!important] 語法釐清
> 文件中稱為「`@include` directive」，但這是功能命名，**實際語法只有 `@path`**。不存在 `@include filename` 或 `read filename` 這類語法。

#### 語法格式與 Regex

核心解析 regex（`claudemd.ts:459`）：

```typescript
const includeRegex = /(?:^|\s)@((?:[^\s\\]|\\ )+)/g
```

支援的路徑格式：

| 語法 | 解析結果 | 說明 |
|------|---------|------|
| `@config.md` | `./config.md` | 相對路徑（Relative Path） |
| `@./rules/style.md` | `./rules/style.md` | 明確相對路徑 |
| `@~/global-rules.md` | `$HOME/global-rules.md` | 家目錄路徑 |
| `@/etc/rules.md` | `/etc/rules.md` | 絕對路徑（Absolute Path） |
| `@path\ with\ spaces` | `path with spaces` | 反斜線轉義空格 |
| `@file.md#section` | `file.md`（去掉 `#` 後面） | 片段識別符（Fragment）被去除 |

**常見誤用**：

| 你寫的 | 實際行為 | 問題 |
|-------|---------|------|
| `@include config.md` | 嘗試讀取 `./include` | `include` 被當成路徑名 |
| `read config.md` | 純文字，無效 | 不是合法指令 |
| `` `@config.md` `` | 不觸發 | 在 code span 中被跳過 |
| `<!-- @secret.md -->` | 不觸發 | 在 HTML comment 中被跳過 |

#### 不會觸發的位置（`claudemd.ts:496-513`）

```typescript
// 跳過 code block 和 code span
if (element.type === 'code' || element.type === 'codespan') {
    continue
}
// 跳過 HTML comment
if (element.type === 'html') {
    // 只處理 comment 被 strip 後的殘餘文字
    continue
}
```

#### 載入時機：Eager Loading（非按需）

```
Session 啟動
  │
  ▼
getMemoryFiles()  ← memoize，整個 session 只呼叫一次
  │
  ▼
processMemoryFile(CLAUDE.md, depth=0)
  │
  ├── safelyReadMemoryFileAsync()    ← 讀取檔案內容
  │     │
  │     ▼
  │   parseMemoryFileContent()
  │     │
  │     ├── Lexer.lex()              ← marked 解析 markdown tokens
  │     │
  │     └── extractIncludePathsFromTokens()
  │           │
  │           └── includeRegex.exec()  ← 提取所有 @path
  │                 │
  │                 └── expandPath()   ← 解析為絕對路徑
  │
  ├── result.push(主檔案)             ← 父檔案先加入
  │
  └── for (每個 @path)
        │
        └── processMemoryFile(path, depth+1)  ← 遞迴！
              │
              └── （重複上面的流程）
```

> [!warning] 全部是啟動時一次讀完
> 所有 `@path` 引用的檔案在 `getMemoryFiles()` 被呼叫時就**遞迴展開並讀取完畢**，結果被 `memoize()` 快取。不存在「對話中遇到才去讀」的按需（On-demand）機制。

#### 遞迴深度限制：最多 5 層

```typescript
// claudemd.ts:537
const MAX_INCLUDE_DEPTH = 5

// claudemd.ts:630
if (processedPaths.has(normalizedPath) || depth >= MAX_INCLUDE_DEPTH) {
    return []  // 靜默忽略，不報錯
}
```

遞迴展開示意圖：

```
CLAUDE.md (depth=0)
  ├── @./rules/naming.md (depth=1)
  │     └── @./shared/base-rules.md (depth=2)
  │           └── @./shared/constants.md (depth=3)
  │                 └── @./shared/types.md (depth=4)
  │                       └── @./deep/file.md (depth=5) ← ❌ 忽略
  │
  ├── @~/global-rules.md (depth=1)
  │     └── @~/snippets/react.md (depth=2)  ← ✅ 正常載入
  │
  └── @./rules/naming.md               ← ❌ 已在 processedPaths，跳過（去重）
```

#### 循環引用保護

```typescript
// claudemd.ts:629-648
const normalizedPath = normalizePathForComparison(filePath)
if (processedPaths.has(normalizedPath)) {
    return []  // 已處理過，跳過
}
processedPaths.add(normalizedPath)

// Symlink 也加入去重 set
const { resolvedPath, isSymlink } = safeResolvePath(fs, filePath)
if (isSymlink) {
    processedPaths.add(normalizePathForComparison(resolvedPath))
}
```

時序圖 — `@include` 的完整載入流程：

```
 Session啟動     getMemoryFiles    processMemoryFile   safelyReadMemoryFileAsync
     │                │                   │                       │
     │──呼叫─────────►│                   │                       │
     │                │──CLAUDE.md────────►│                       │
     │                │                   │──讀取 CLAUDE.md───────►│
     │                │                   │◄──內容 + @paths────────│
     │                │                   │                       │
     │                │                   │──遞迴 @rules.md───────►│
     │                │                   │  (depth=1)            │
     │                │                   │◄──內容 + @paths────────│
     │                │                   │                       │
     │                │                   │──遞迴 @base.md────────►│
     │                │                   │  (depth=2)            │
     │                │                   │◄──內容────────────────│
     │                │                   │                       │
     │                │◄──MemoryFileInfo[]─│                       │
     │                │                   │                       │
     │                │── memoize 快取 ────│                       │
     │◄──快取結果──────│                   │                       │
     │                │                   │                       │
  後續 API call       │                   │                       │
     │──再次呼叫──────►│                   │                       │
     │◄──直接回傳快取──│  (不讀磁碟)       │                       │
```

#### 允許的檔案副檔名

`@path` 只載入文字檔案，二進位檔案被靜默跳過（`claudemd.ts:94-227`）：

```typescript
const TEXT_FILE_EXTENSIONS = new Set([
    '.md', '.txt', '.json', '.yaml', '.yml', '.toml',
    '.js', '.ts', '.tsx', '.jsx', '.py', '.go', '.rs',
    '.java', '.sh', '.bash', '.sql', '.html', '.css',
    // ... 共 80+ 種副檔名
])
```

> [!note] 無副檔名的檔案
> 若檔案沒有副檔名（`ext === ''`），則 `!TEXT_FILE_EXTENSIONS.has(ext)` 為 `true`，會被**跳過**。所以 `@Makefile` 或 `@Dockerfile` 這類無副檔名檔案**不會被載入**。

#### 外部路徑限制

```typescript
// claudemd.ts:667-669
const isExternal = !pathInOriginalCwd(resolvedIncludePath)
if (isExternal && !includeExternal) {
    continue  // 跳過專案目錄外的檔案
}
```

預設情況下，`@` 引用的檔案必須在專案工作目錄（CWD）內。`@~/` 或 `@/absolute/` 路徑指向專案外的檔案時，需要 `includeExternal` 參數為 `true` 才會載入。

### Plugin 系統與 CLAUDE.md / Rules 的關係

> [!important] Plugin 不能注入 CLAUDE.md 或 Rules
> Plugin Manifest schema（`PluginManifestSchema`）中**沒有** `rules`、`claudeMd`、`instructions` 等欄位。`getMemoryFiles()` 也**不會掃描** plugin 目錄。Plugin 只能透過 skills 間接提供指令。

**Plugin 能提供的元件**

| 元件 | 說明 | 能替代 CLAUDE.md？ |
|------|------|-------------------|
| `commands/` | 指令（slash commands） | ❌ 呼叫時才注入 |
| `skills/` | 技能（SKILL.md） | ❌ 呼叫時才注入 |
| `hooks` | 事件鉤子（PreToolUse 等） | ⚠️ 可間接影響行為 |
| `agents/` | 代理人定義 | ❌ |
| `mcpServers` | MCP server 設定 | ❌ |
| `output-styles/` | 輸出樣式 | ❌ |
| `settings/user-config` | 使用者設定 | ❌ |
| ~~`rules/`~~ | ❌ **不存在** | — |
| ~~`CLAUDE.md`~~ | ❌ **不存在** | — |

**注入層對比**

```
┌─── System Prompt（每次 API call 自動注入）────┐
│                                               │
│  CLAUDE.md          → ✅ 直接注入              │
│  .claude/rules/*.md → ✅ 直接注入              │
│  Plugin rules       → ❌ 不存在這個概念        │
│                                               │
└───────────────────────────────────────────────┘

┌─── 對話層（按需注入）────────────────────────┐
│                                               │
│  skill_listing     → 索引（name + desc）       │
│  Plugin skills     → ✅ 呼叫時注入完整內容     │
│  Plugin commands   → ✅ 呼叫時注入完整內容     │
│                                               │
└───────────────────────────────────────────────┘

┌─── 事件層（Event Hook）─────────────────────┐
│                                               │
│  Plugin hooks      → ✅ 事件觸發時執行腳本     │
│  （PreToolUse, PostToolUse, etc.）             │
│                                               │
└───────────────────────────────────────────────┘
```

**CLAUDE.md vs Plugin Skills 的關鍵差異**

| 面向 | CLAUDE.md | Plugin Skill |
|------|-----------|-------------|
| 注入位置 | system prompt（每次 API call） | 對話中（呼叫時） |
| 持久性 | 整個 session 生效 | 只在該 turn 生效 |
| 能否設定全局行為 | ✅ | ❌ 只在被呼叫時影響 |
| 跨專案分享 | 手動 symlink | ✅ Plugin 安裝即可 |
| 熱載入 | ❌（需 resume） | ✅（chokidar 監控） |
| 支援 @include | ✅ | ❌ |

> [!note] 變通方案
> Plugin 無法注入 system prompt 級指令，但可以用 **hooks**（如 `PostToolUse`）在事件觸發時執行檢查腳本，間接約束行為。兩者是互補關係，不是替代關係。

**Plugin Skill 的命名規則**

Plugin 提供的 skills 會加上 plugin 名稱作為 namespace，用冒號分隔：

```
plugin-name:skill-name

例：obsidian:obsidian-markdown
    obsidian:json-canvas
    skill-creator:skill-creator
```

**Plugin Skill 載入路徑**

```
~/.claude/plugins/cache/{marketplace}/{plugin}/{version}/
  ├── manifest.json
  ├── skills/
  │     └── my-skill/
  │           └── SKILL.md       ← 啟動時讀取，閉包捕獲
  └── commands/
        └── my-command.md        ← 啟動時讀取，閉包捕獲

getPluginSkills() ← memoize
  └── loadAllPluginsCacheOnly()  ← 只從已安裝快取載入
        └── loadSkillsFromDirectory()
              └── fs.readFile(SKILL.md) → parseFrontmatter()
                    → createPluginCommand({ markdownContent })
```

### `.claude/rules/*.md` 的讀取與注入機制

Rules 分為兩種：**無條件規則（Unconditional）** 和 **有條件規則（Conditional）**。兩者的讀取時機和注入方式完全不同。

```
.claude/rules/
  ├── always-use-chinese.md      ← 無條件規則（無 paths: frontmatter）
  ├── code-style.md              ← 無條件規則
  └── react-patterns.md          ← 有條件規則（有 paths: frontmatter）
        ---
        paths:
          - "src/components/**"
        ---
        React 元件必須使用 functional component...
```

#### 無條件規則：與 CLAUDE.md 完全相同

**讀取時機**：Session 啟動時，與 CLAUDE.md 一起在 `getMemoryFiles()` 中讀取並 memoize。
**注入時機**：每次 API call 都注入 system prompt。

```typescript
// claudemd.ts:909-919 — 在 getMemoryFiles() 中
const rulesDir = join(dir, '.claude', 'rules')
result.push(
    ...(await processMdRules({
        rulesDir,
        type: 'Project',
        processedPaths,
        includeExternal,
        conditionalRule: false,  // ← 只取無條件規則
    })),
)
```

篩選邏輯（`claudemd.ts:773`）：

```typescript
// conditionalRule: false → 只保留沒有 globs（paths:）的檔案
result.push(
    ...files.filter(f => (conditionalRule ? f.globs : !f.globs)),
)
```

#### 有條件規則：真正的按需注入（On-demand Injection）

> [!important] 有條件規則是整個 Claude Code 中**唯一真正按需讀取的 CLAUDE.md 級指令**
> 啟動時**不讀取**，只在 Read tool 觸發且路徑匹配時才從磁碟讀取並注入對話。

**觸發鏈**：

```
 模型呼叫 Read tool 讀取 src/components/Button.tsx
   │
   ▼
 FileReadTool.call()
   │
   └── context.nestedMemoryAttachmentTriggers.add(filePath)
         │
         ▼
 下一次 API call 的 attachment 組裝
   │
   ▼
 getNestedMemoryAttachments()
   │
   └── getNestedMemoryAttachmentsForFile(filePath)
         │
         ├── Phase 1：Managed + User 有條件規則
         │     └── getManagedAndUserConditionalRules(filePath)
         │           └── processConditionedMdRules()
         │                 ├── processMdRules({ conditionalRule: true })
         │                 └── glob 匹配 filePath → 只保留匹配的
         │
         ├── Phase 2：計算目錄範圍
         │     ├── nestedDirs（CWD → 目標檔案 之間的目錄）
         │     └── cwdLevelDirs（根 → CWD 的目錄）
         │
         ├── Phase 3：CWD 以下的巢狀目錄
         │     └── getMemoryFilesForNestedDirectory(dir, filePath)
         │           ├── 該目錄的 CLAUDE.md
         │           ├── 該目錄的無條件規則
         │           └── 該目錄的有條件規則（匹配 filePath 的）
         │
         └── Phase 4：根 → CWD 的目錄
               └── getConditionalRulesForCwdLevelDirectory()
                     → 只取有條件規則（無條件的已在啟動時載入）
```

**Glob 匹配邏輯**（`claudemd.ts:1370-1396`）：

```typescript
return conditionedRuleMdFiles.filter(file => {
    // Project 規則：相對於 .claude 的父目錄
    // Managed/User 規則：相對於 CWD
    const baseDir = type === 'Project'
        ? dirname(dirname(rulesDir))
        : getOriginalCwd()
    const relativePath = relative(baseDir, targetPath)
    // 用 ignore 庫（gitignore 風格）進行匹配
    return ignore().add(file.globs).ignores(relativePath)
})
```

#### Rules 掃描範圍

```
getMemoryFiles() 從根往 CWD 遞迴掃描：

 /etc/claude-code/.claude/rules/   ← Managed（最低優先級）
 ~/.claude/rules/                  ← User
 /Users/.claude/rules/             ← 逐層往上
 ...
 {project-root}/.claude/rules/     ← Project（最高優先級）

每個 rules/ 目錄會遞迴子目錄：
  .claude/rules/
    ├── general.md
    ├── frontend/
    │     ├── react.md
    │     └── css.md
    └── backend/
          └── api.md
```

#### 完整的讀取與注入時機對照表

```
┌─────────────────────┬──────────────────┬──────────────────────────┐
│       規則類型        │    讀取時機       │      注入時機             │
├─────────────────────┼──────────────────┼──────────────────────────┤
│ CLAUDE.md            │ 啟動（eager）    │ 每次 API call            │
│                     │ memoize 快取     │ system prompt             │
├─────────────────────┼──────────────────┼──────────────────────────┤
│ 無條件 rules         │ 啟動（eager）    │ 每次 API call            │
│ （無 paths:）        │ 與 CLAUDE.md     │ system prompt             │
│                     │ 一起 memoize     │                          │
├─────────────────────┼──────────────────┼──────────────────────────┤
│ 有條件 rules         │ 按需（on-demand）│ Read tool 讀取匹配路徑時  │
│ （有 paths:）        │ FileReadTool     │ nested_memory attachment  │
│                     │ 觸發時才讀取     │ （非 system prompt）      │
├─────────────────────┼──────────────────┼──────────────────────────┤
│ Skills               │ 啟動（eager）    │ 索引每次注入（~1%）       │
│                     │ memoize + 閉包   │ 完整內容呼叫時注入        │
└─────────────────────┴──────────────────┴──────────────────────────┘
```

> [!tip] Token 節省策略
> 把只跟特定檔案類型相關的規則加上 `paths:` frontmatter 變成有條件規則。例如 React 規範只在碰到 `src/components/**` 時才注入，避免每次 API call 都消耗這些 Token。這是一個被低估的 Token 最佳化手段。

### 快取清除的內部 API

```typescript
// src/utils/claudemd.ts — 匯出的快取清除函式
export function resetGetMemoryFilesCache(reason: string): void {
  getMemoryFiles.cache.clear?.();
}

// src/context.ts — system prompt injection 變更時清除
export function setSystemPromptInjection(value: string | null): void {
  systemPromptInjection = value;
  getUserContext.cache.clear?.();
  getSystemContext.cache.clear?.();
}
```

> [!warning] 無內建 UI 可手動觸發
> 雖然 `resetGetMemoryFilesCache()` 有匯出，但目前沒有任何 slash command 或 UI 讓用戶在對話中手動觸發。如果需要 CLAUDE.md 變更即時生效，唯一的官方途徑是 exit + resume。

## 實用工作流建議

### 場景一：頻繁修改 Skills

由於 skills 支援熱載入，可以放心地在對話中修改 `.claude/skills/` 下的檔案（包含 symlink 指向的檔案）。變更會在下次 model 呼叫該 skill 時自動反映。

### 場景二：需要更新 CLAUDE.md

```bash
# 修改 CLAUDE.md 或其 symlink 指向的檔案
vim ~/.claude/CLAUDE.md

# 退出當前 session
# 在 Claude Code 中輸入 /exit 或 Ctrl+C

# 用 resume 恢復對話，CLAUDE.md 會重新載入
claude --resume
```

### 場景三：用 Symlink 管理跨專案設定

```bash
# 建立共享 skills 目錄
mkdir -p ~/shared-claude-skills/

# 在各專案中用 symlink 連結
ln -s ~/shared-claude-skills/ .claude/skills

# Skills：修改 ~/shared-claude-skills/ 中的檔案 → 各專案即時生效
# CLAUDE.md：需要 resume 才能生效
```

## 我的心得（My Takeaways）

1. **設計哲學差異明確但機制相似**：CLAUDE.md 和 Skills 都是啟動時讀完並 memoize，差異僅在於 Skills 加了 chokidar 監控來清除快取。「熱載入」不是靠每次重新讀磁碟，而是靠檔案監控觸發快取失效（Cache Invalidation）。
2. **Symlink 是一等公民**：程式碼中明確用 `realpath()` 處理 symlink 去重，chokidar 也能穿透 symlink 監控。這說明 Claude Code 團隊預期用戶會用 symlink 管理設定。
3. **`--resume` 是被低估的功能**：不只是恢復對話，更是刷新所有設定快取的官方途徑。

## 待補充（Open Questions）

- ~~`@include` 指令在 CLAUDE.md 中引用的外部檔案，是否也被 memoize 包含？~~ **已解答**：是的，`@path` 引用的檔案在 `getMemoryFiles()` 時就遞迴讀取，全部被 memoize 快取。修改後需要 resume 才能生效。
- chokidar 監控是否涵蓋 `.claude/rules/*.md`？如果 rules 也有熱載入，那 CLAUDE.md 就是唯一不支援的設定檔。建議搜尋：`skillChangeDetector chokidar watch path`
- 是否有計畫加入 `/reload` 之類的 slash command 來手動刷新 CLAUDE.md 快取？目前社群是否有相關 feature request？建議搜尋：`github claude-code reload claudemd issue`
- `clearSessionCaches()` 除了清除 CLAUDE.md 快取外，還清除了哪些其他快取？完整的清除清單是什麼？建議搜尋：`clearSessionCaches function body`
- 若在對話中用 tool 直接呼叫 `resetGetMemoryFilesCache()`（例如透過 Bash tool 執行 JS），是否能達到不中斷對話就刷新的效果？建議搜尋：`bun eval resetGetMemoryFilesCache`
- `@path` 引用專案外檔案（如 `@~/global-rules.md`）時，`includeExternal` 在哪些情況下為 `true`？預設值是什麼？建議搜尋：`includeExternal getMemoryFiles forceIncludeExternal`
- 無副檔名的檔案（如 `@Makefile`）被跳過是否為刻意設計？有無 issue 討論過允許特定無副檔名檔案？建議搜尋：`TEXT_FILE_EXTENSIONS no extension claudemd`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | `memoize()`、`chokidar`、`realpath()`、`clearSessionCaches()`、`getMemoryFiles()`、`MAX_INCLUDE_DEPTH=5`、`extractIncludePathsFromTokens()` — 七個核心 API |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | CLAUDE.md 和 Skills 都在載入時一次讀完並 memoize，差異僅在於 Skills 有 chokidar 監控來清除快取。`@path` 在同一次 memoize 中遞迴展開。三者形成：CLAUDE.md（全快取、無監控）→ @include（隨父檔案快取）→ Skills（全快取、有 chokidar 監控清除）的梯度。核心差異不是「讀的時機」而是「有沒有人來清除快取」。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 核心假設是「用戶不會在對話中修改 CLAUDE.md」——但使用 symlink 管理跨專案設定的進階用戶恰恰會這麼做。chokidar 的 300ms debounce 在大量檔案同時變更時可能漏掉事件。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | (1) 將頻繁變更的指令放在 skills 而非 CLAUDE.md 中，利用熱載入；(2) 建立 `exit → 修改 → resume` 的肌肉記憶來更新 CLAUDE.md；(3) 用 symlink 共享 skills 目錄給多個專案 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | 熱載入 CLAUDE.md 的替代方案：(a) 加 chokidar 監控 CLAUDE.md — 優：即時生效，劣：system prompt 可能在 API call 途中變更造成不一致；(b) 加 `/reload` command — 優：用戶控制時機，劣：需新增 UI；(c) 維持現狀 + resume — 優：最安全，劣：中斷工作流。目前的設計在安全性和一致性上是最佳選擇。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「memoize」在此處的快取 key 是什麼？`getMemoryFiles` 接受 `forceIncludeExternal` 參數，不同參數值是否會導致多次快取？
- **假設**：本文假設 chokidar 能可靠偵測 symlink 變更——若 symlink 指向的是 NFS 或 FUSE 掛載的遠端目錄，chokidar 的行為是否改變？
- **證據**：程式碼中 `clearSessionCaches()` 在 resume 時被呼叫是確定的，但我們沒有驗證 chokidar 監控是否在所有 OS 上都能穿透 symlink。macOS 的 FSEvents 和 Linux 的 inotify 對 symlink 的處理不同。
- **觀點**：反對意見可能是「CLAUDE.md 也應該熱載入」——但 system prompt 的一致性比即時性更重要，mid-turn 切換 system prompt 可能導致 AI 行為不連貫。
- **後果**：若大量用戶開始依賴 skills 熱載入來繞過 CLAUDE.md 的限制（把原本該放 CLAUDE.md 的內容移到 skills），可能導致 skills 目錄膨脹、系統提示（System Prompt）結構混亂。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 依賴 chokidar 熱載入的最大風險是**靜默失敗**：若 chokidar 因 OS 限制（如 macOS 的 FSEvents 上限）停止偵測變更，用戶不會收到任何通知，只會發現 skill 內容沒有更新。
2. **什麼情況下會失敗？** — (a) 監控的目錄數超過 OS 上限（macOS 預設約 256 個 watch）；(b) symlink 指向的目標跨越檔案系統邊界（如 Docker volume）；(c) 極快速連續修改（<300ms debounce 內多次變更只觸發一次清除）。
3. **有沒有更好的替代方案？** — 替代方案是在每次 skill 呼叫前檢查檔案 mtime，若有變更才重新讀取（polling + mtime check）。優點：不依賴 OS 層的檔案事件；缺點：增加每次 API call 的 I/O 開銷。在大多數場景下，chokidar 是更好的選擇。

## 相關連結（Related）

- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — 同樣基於反編譯原始碼的分析，涵蓋 Agent Loop、記憶架構等核心機制
- [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — 配置層級系統的完整指南，本文聚焦其中載入時機的細節
- [[2026-03-30-BORIS-CHERNY-HIDDEN-CLAUDE-CODE-FEATURES]] — Boris Cherny 提到的 `--resume`、worktree 等進階功能，與本文的 resume 刷新機制相關
- [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]] — Skills 系統的官方文件整理，本文補充了其內部載入機制
- [[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]] — Hooks 的載入機制與 skills 類似，可對照理解
- [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] — CLAUDE.md vs Skills 的最佳實踐比較，引用本文的 memoize 與熱載入發現作為技術佐證
- [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]] — Opalic 的 /docs/ + IMPORTANT 指示句方案，用 Vercel 實驗證明明確引用比 skills 自動觸發更可靠
- [[2026-01-27-VERCEL-AGENTS-MD-OUTPERFORMS-SKILLS-IN-AGENT-EVALS]] — 被動上下文（AGENTS.md）vs 按需檢索（Skills）的原始實驗，從機制層面解釋 memoize 全量載入的優勢
- [[2026-05-03-CLAUDE-CODE-PLUGIN-CANNOT-INSTALL-CLAUDEMD-RULES-ALTERNATIVES]] — @path 引用 Plugin cache 路徑的可行性驗證（expandPath 無限制 + includeExternal = true）
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — Skills 的 frontmatter 控制（fork/paths/allowed-tools）與 Subagents 的選擇決策框架
- [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] — Skill frontmatter 進階欄位（context:fork、agent、hooks）的原始碼深度解析與 FAQ
- [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]] — Settings 五源 merge 與 CLAUDE.md memoize 的關係、Plugin 啟停如何透過 settings 控制
- [[2026-04-17-CLAUDEMD-MYTHS-DEBUNKED-SOURCE-CODE-VERIFICATION]] — 社群 CLAUDE.md 迷思核實：壓縮後 prependUserContext 重新注入、無條件 rules 與 CLAUDE.md 注入位置相同

## References

- Claude Code 反編譯原始碼（基於 v2.1.88 source map 洩漏版本）
- 關鍵檔案：
  - `src/utils/claudemd.ts` — CLAUDE.md 發現、解析、`@include` 遞迴展開、memoize 快取（核心）
  - `src/context.ts` — `getUserContext()` / `getSystemContext()` memoize 包裝
  - `src/skills/loadSkillsDir.ts` — Skills 載入、memoize、chokidar 快取清除
  - `src/utils/skills/skillChangeDetector.ts` — chokidar 檔案監控設定
  - `src/main.tsx` — `--resume` 時的 `clearSessionCaches()` 呼叫
