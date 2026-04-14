---
title: "Claude Code 原始碼分析：CLAUDE.md 與 Skills 的熱載入機制——Symlink 修改是否即時生效？"
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

深入研究 Claude Code 反編譯原始碼，追蹤 CLAUDE.md 與 `.claude/skills/` 在對話過程中的載入時機與快取機制。核心發現：**CLAUDE.md 在 session 啟動時讀取一次後即快取（memoize），對話中修改不會生效**；而 **Skills 透過 chokidar 檔案監控實現熱載入（Hot Reload），對話中修改會即時生效**。對於使用 symlink 管理設定的用戶，這意味著兩者的行為完全不同。此外，`claude --resume` 會重新讀取 CLAUDE.md，提供了一個不中斷對話歷史的折衷方案。

## 關鍵洞察（Key Insights）

- **CLAUDE.md 被 `memoize()` 包裝**，整個 session 只讀取一次磁碟，之後所有 API call 使用快取內容 — 參見 [[CLAUDE-CODE-CONTEXT-ENGINEERING]]
- **Skills 有雙層熱載入機制**：chokidar 監控檔案變更清除 metadata 快取，而 skill 完整內容每次呼叫時才從磁碟讀取（延遲載入（Lazy Loading）） — 參見 [[CLAUDE-CODE-SKILLS-DOCUMENTATION]]
- **Symlink 完整支援**：程式碼用 `realpath()` 解析 canonical path 做去重，chokidar 也能透過 symlink 偵測變更
- **`--resume` 會清除所有快取**：啟動新程序時明確呼叫 `clearSessionCaches()` → `resetGetMemoryFilesCache()`，因此 CLAUDE.md 會重新讀取
- **System prompt 每次 API call 都重新組裝**，但底層資料（CLAUDE.md 內容、git status）來自快取

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

Skills 的行為與 CLAUDE.md 完全不同，有兩個關鍵差異：

**1. chokidar 檔案監控（File Watcher）**

```
// src/utils/skills/skillChangeDetector.ts:110-131
chokidar.watch(skillDirectories, { atomic: true })
  → 偵測檔案變更（包含 symlink）
  → 300ms debounce
  → clearSkillCaches()  // 清除 metadata 快取
  → clearCommandsCache()  // 清除 command 快取
```

> [!tip] Symlink 感知
> chokidar 設定了 `atomic: true`，能正確偵測透過 symlink 的檔案變更。同時 `getFileIdentity()` 用 `realpath()` 解析 canonical path，確保同一檔案不會因不同路徑被重複載入。

**2. 延遲載入（Lazy Loading）完整內容**

```
啟動時：
  getSkillDirCommands()  ←  memoize，快取 metadata（名稱、描述、whenToUse）

每次呼叫時：
  SkillTool.call()
    → getPromptForCommand()  ←  每次從磁碟讀取完整 markdown 內容
```

> [!note] 兩層快取策略
> Metadata（frontmatter）被 memoize 快取，但 chokidar 會在檔案變更時清除。完整 markdown 內容則完全不快取，每次呼叫都重新讀取。這使得 skills 天然支援熱載入。

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
┌───────────────────┬──────────────────┬──────────────────┐
│       項目         │   對話中修改      │  --resume 後     │
├───────────────────┼──────────────────┼──────────────────┤
│ CLAUDE.md          │ ❌ 不生效         │ ✅ 重新讀取      │
│ .claude/rules/*.md │ ❌ 不生效         │ ✅ 重新讀取      │
│ .claude/skills/    │ ✅ 即時生效       │ ✅ 重新讀取      │
│ .claude/commands/  │ ✅ 即時生效       │ ✅ 重新讀取      │
│ Git status 快照    │ ❌ 不更新         │ ✅ 重新擷取      │
│ System prompt 組裝 │ ✅ 每次重組       │ ✅ 每次重組      │
│ 對話訊息           │ — 持續累積       │ ✅ 從 transcript  │
│                   │                  │    恢復           │
└───────────────────┴──────────────────┴──────────────────┘
```

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

1. **設計哲學差異明確**：CLAUDE.md 是「session 級設定」，像啟動參數；Skills 是「工具級資源」，像動態函式庫。兩者的快取策略反映了不同的使用模式假設。
2. **Symlink 是一等公民**：程式碼中明確用 `realpath()` 處理 symlink 去重，chokidar 也能穿透 symlink 監控。這說明 Claude Code 團隊預期用戶會用 symlink 管理設定。
3. **`--resume` 是被低估的功能**：不只是恢復對話，更是刷新所有設定快取的官方途徑。

## 待補充（Open Questions）

- `@include` 指令在 CLAUDE.md 中引用的外部檔案，是否也被 memoize 包含？如果 include 的目標檔案變更，resume 後是否能正確反映？建議搜尋：`claudemd.ts @include resolve`
- chokidar 監控是否涵蓋 `.claude/rules/*.md`？如果 rules 也有熱載入，那 CLAUDE.md 就是唯一不支援的設定檔。建議搜尋：`skillChangeDetector chokidar watch path`
- 是否有計畫加入 `/reload` 之類的 slash command 來手動刷新 CLAUDE.md 快取？目前社群是否有相關 feature request？建議搜尋：`github claude-code reload claudemd issue`
- `clearSessionCaches()` 除了清除 CLAUDE.md 快取外，還清除了哪些其他快取？完整的清除清單是什麼？建議搜尋：`clearSessionCaches function body`
- 若在對話中用 tool 直接呼叫 `resetGetMemoryFilesCache()`（例如透過 Bash tool 執行 JS），是否能達到不中斷對話就刷新的效果？建議搜尋：`bun eval resetGetMemoryFilesCache`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | `memoize()`、`chokidar`、`realpath()`、`clearSessionCaches()`、`getMemoryFiles()` — 五個核心 API/工具名稱 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | CLAUDE.md 用 session 級 memoize 因為它是啟動設定，不需頻繁變更；Skills 用 chokidar + lazy load 因為它是工具資源，需要即時反映開發者的迭代。兩者快取策略的差異源自使用頻率假設的不同。 |
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

## References

- Claude Code 反編譯原始碼（基於 v2.1.88 source map 洩漏版本）
- 關鍵檔案：`src/context.ts`、`src/utils/claudemd.ts`、`src/skills/loadSkillsDir.ts`、`src/utils/skills/skillChangeDetector.ts`、`src/main.tsx`
