---
title: "Claude Code 記憶系統深度解析 — 六層架構、AutoDream 與動態召回"
date: 2026-04-07
category: CodeAnalysis
tags:
  - code-analysis
  - ai/agent
  - memory-system
  - context-engineering
  - llm-application-architecture
source: "https://github.com/anthropics/claude-code (decompiled local copy)"
source_type: code
author: "Anthropic (decompiled / reverse-engineered)"
status: notes
links:
  - "[[CLAUDE-MEMORY-ENGINE]]"
  - "[[CONTEXT-ENGINEERING-PATTERNS]]"
  - "[[FORKED-SUBAGENT-PATTERN]]"
github_stars: N/A (decompiled)
github_language: TypeScript
---

## 摘要（Summary）

本筆記針對本地反編譯版（decompiled）的 Claude Code，逐一拆解其**記憶系統（Memory System）**的十大核心設計：從 CLAUDE.md 四層優先級指令體系、`@include` 遞迴載入、雙軌注入（指令通道 vs 行為通道），到 memdir 四種長期記憶類型、Sonnet 動態相關性召回（dynamic recall）、自動記憶提取（auto-memory extraction）、AutoDream 四階段睡眠重塑（sleep consolidation）、Session Memory 長對話失憶緩解、團隊同步記憶（Team Memory Sync）的安全設計，以及三層快取體系與 Feature Flag 遠程調控。

每一項都對應到具體的檔案路徑與行號，可直接跳轉源碼閱讀。

## Why — 為什麼存在？

> LLM 的上下文視窗（Context Window）有限，且無跨 session 記憶。Claude Code 作為長時間運作的 AI Coding Assistant，必須解決三個根本問題：

- **跨 session 記憶遺失**：每次重啟都從零開始 → 需要可持久化的記憶層
- **上下文預算耗竭**：長對話會塞爆 context window → 需要 Session Memory 壓縮（compaction）
- **使用者重複糾正**：相同的偏好要講十次 → 需要 feedback 通道自動學習

## What — 是什麼？

- **主要功能**：
  - CLAUDE.md 多層指令載入（四層優先級）
  - memdir 長期記憶（四種類型，YAML frontmatter 索引）
  - 動態相關性召回（Sonnet-driven recall）
  - 自動記憶提取（auto-memory extraction，背景子代理）
  - AutoDream 睡眠重塑（四階段 consolidation）
  - Session Memory（會話內筆記 + 自動壓縮）
  - Team Memory Sync（團隊同步，含祕密掃描）
- **技術棧（Tech Stack）**：TypeScript、Bun runtime、forked sub-agent pattern、GrowthBook feature flags

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌──────────────────────────────────────────────────────────────┐
│                       使用者對話 (Query)                       │
└──────────────────────────────┬───────────────────────────────┘
                               │
        ┌──────────────────────▼──────────────────────┐
        │           Context 組裝 (context.ts)          │
        │  ┌────────────────┐  ┌────────────────────┐ │
        │  │  指令通道       │  │   行為通道          │ │
        │  │  CLAUDE.md     │  │   MEMORY.md +      │ │
        │  │  (4 層優先級)   │  │   memdir/*.md      │ │
        │  └────────┬───────┘  └─────────┬──────────┘ │
        └───────────┼───────────────────┼─────────────┘
                    │                   │
       ┌────────────▼─────┐     ┌───────▼────────────┐
       │ claudemd.ts      │     │ memdir/            │
       │ + @include 遞迴   │     │ - findRelevant     │
       │ + 4 層載入順序    │     │   Memories.ts      │
       │                  │     │ - sonnet 召回      │
       └──────────────────┘     └──────────┬─────────┘
                                           │
                ┌──────────────────────────▼──────────────────┐
                │         背景子代理 (Forked sub-agent)        │
                │  ┌──────────────┐  ┌─────────────────────┐ │
                │  │ extract-     │  │   AutoDream         │ │
                │  │ Memories     │  │   (4 phase sleep)   │ │
                │  └──────────────┘  └─────────────────────┘ │
                │  ┌──────────────┐  ┌─────────────────────┐ │
                │  │ SessionMem   │  │   TeamMemorySync    │ │
                │  └──────────────┘  └─────────────────────┘ │
                └─────────────────────────────────────────────┘
                                           │
                                ┌──────────▼──────────┐
                                │   檔案系統           │
                                │ ~/.claude/projects/  │
                                │   <slug>/memory/     │
                                └─────────────────────┘
```

### CLAUDE.md 四層載入流程圖（Loading Flowchart）

```
 Start: getMemoryFiles()
   │
   ▼
[Layer 1: Managed]  /etc/claude-code/CLAUDE.md  (Enterprise)
   │
   ▼
[Layer 2: User]     ~/.claude/CLAUDE.md
   │
   ▼
[Layer 3: Project]  CWD → root 向上掃描，每層 CLAUDE.md
   │                ├─ feature('tengu_paper_halyard')? ──► 跳過
   │                └─ 否則: 遞迴 @include (max depth 5)
   ▼
[Layer 4: Local]    CLAUDE.local.md  (私密，gitignore)
   │
   ▼
[組裝為 system prompt]
   │
   ├─ 前綴: MEMORY_INSTRUCTION_PROMPT
   │       "These instructions OVERRIDE any default behavior
   │        and you MUST follow them exactly as written."
   │
   ▼
   End → 注入 system prompt（後載入者優先級最高）
```

### Sonnet 動態召回時序圖（Sequence Diagram）

```
 User Query   QueryEngine    findRelevantMemories     Sonnet API     memdir/
     │             │                  │                   │            │
     │──query─────►│                  │                   │            │
     │             │──recall(query)──►│                   │            │
     │             │                  │──scanMemoryFiles──┼───────────►│
     │             │                  │◄─manifest─────────┼────────────│
     │             │                  │                   │            │
     │             │                  │──sideQuery───────►│            │
     │             │                  │  (Sonnet)         │            │
     │             │                  │  + recentTools    │            │
     │             │                  │  + manifest       │            │
     │             │                  │◄─selected (≤5)────│            │
     │             │                  │                   │            │
     │             │◄─RelevantMemory[]│                   │            │
     │             │   注入 context   │                   │            │
     │◄────────────│                  │                   │            │
```

### AutoDream 四階段流程圖（Sleep Consolidation）

```
 Trigger gates:
   ├─ time gate    (≥ 24h since last)
   ├─ session gate (≥ 5 sessions touched)
   └─ lock gate    (consolidationLock 鎖檔)
        │
        ▼
   ┌────────────────────────────────────────┐
   │  Fork sub-agent → AutoDream prompt     │
   └────────────────┬───────────────────────┘
                    │
       ┌────────────▼────────────┐
       │ Phase 1: Orient         │  讀 MEMORY.md 索引、skim 現有檔
       └────────────┬────────────┘
                    ▼
       ┌─────────────────────────┐
       │ Phase 2: Gather signal  │  日誌 → 偏移記憶 → grep transcripts
       └────────────┬────────────┘
                    ▼
       ┌─────────────────────────┐
       │ Phase 3: Consolidate    │  合併、轉絕對日期、刪矛盾
       └────────────┬────────────┘
                    ▼
       ┌─────────────────────────┐
       │ Phase 4: Prune & Index  │  維持 200 行 / 25KB 上限
       └────────────┬────────────┘
                    ▼
                   End
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> Claude Code 的記憶系統基於 **「指令 / 行為通道分離」** 與 **「Forked Sub-agent 共享 prompt cache」** 兩大模式。

1. **雙通道注入（Dual-channel injection）**：
   - **指令通道**：`CLAUDE.md` → system prompt 帶 `MUST follow exactly as written`，硬性規則
   - **行為通道**：`MEMORY.md` + memdir → user context 帶啟發式說明，柔性學習
   - 原因：硬性規則需要最高優先級且不可被推翻；行為偏好則需要 LLM 自行判斷適用情境

2. **Sonnet 動態召回 vs 預計算 embedding**：
   - 每次查詢都呼叫 Sonnet 重新評估相關性（不用 embedding 索引）
   - 原因：記憶數量小（≤200 個），Sonnet 能理解語意脈絡 + 工具感知去重，比 embedding 更準確
   - 代價：每次召回多一次 API 呼叫，但用 prompt cache 攤平成本

3. **Forked Sub-agent 共享 prompt cache**：
   - extractMemories / AutoDream / SessionMemory 都用 `runForkedAgent`
   - Fork 出的子代理繼承父代理的 prompt cache → 省 token 成本
   - `skipTranscript: true` → 子代理執行不污染主對話

4. **遞迴載入有 depth + cycle 雙重防護**：
   - `MAX_INCLUDE_DEPTH = 5`（深度上限）
   - `processedPaths: Set<string>`（symlink 與相對路徑都正規化）
   - 原因：避免 `A→B→A` 或 `A→B→C→A` 死循環

5. **Feature Flag 遠程調控所有閾值**：
   - `tengu_paper_halyard` → 跳過 Project/Local 層
   - `tengu_onyx_plover` → AutoDream 的 `minHours/minSessions`
   - `tengu_sm_config` → SessionMemory 閾值
   - 原因：可在不發版的情況下調整記憶系統行為

### 資料流（Data Flow）

1. **載入階段**：`getMemoryFiles()` 依四層順序讀檔，遞迴展開 `@include`
2. **召回階段**：每次 query 觸發 `findRelevantMemories()`，Sonnet 從 manifest 選 ≤5 篇
3. **提取階段**：query loop 結束時，`stopHooks` 觸發 `extractMemories` fork 寫新記憶
4. **重塑階段**：累計 24h + 5 sessions → AutoDream 四階段整理
5. **同步階段**：TeamMemorySync watcher 偵測檔案變更 → 上傳至 server（祕密掃描後）

### 關鍵程式碼（Key Code Snippets）

**1. 四層優先級載入**（`src/utils/claudemd.ts:790+`）

```typescript
// 順序 1: Managed - /etc/claude-code/CLAUDE.md
result.push(...(await processMemoryFile(getMemoryPath('Managed'), 'Managed', ...)))

// 順序 2: User - ~/.claude/CLAUDE.md
result.push(...(await processMemoryFile(getMemoryPath('User'), 'User', ...)))

// 順序 3: Project - CWD 向上遍歷
for (const dir of dirs.reverse()) {
  result.push(...(await processMemoryFile(join(dir, 'CLAUDE.md'), 'Project', ...)))
}

// 順序 4: Local - CLAUDE.local.md
result.push(...(await processMemoryFile(join(dir, 'CLAUDE.local.md'), 'Local', ...)))
```

**2. @include 遞迴 + 循環防護**（`src/utils/claudemd.ts:615-685`）

```typescript
const MAX_INCLUDE_DEPTH = 5

export async function processMemoryFile(
  filePath: string,
  type: MemoryType,
  processedPaths: Set<string>,
  includeExternal: boolean,
  depth: number = 0,
) {
  const normalizedPath = normalizePathForComparison(filePath)
  if (processedPaths.has(normalizedPath) || depth >= MAX_INCLUDE_DEPTH) return []

  const { resolvedPath, isSymlink } = safeResolvePath(getFsImplementation(), filePath)
  processedPaths.add(normalizedPath)
  if (isSymlink) processedPaths.add(normalizePathForComparison(resolvedPath))

  for (const resolvedIncludePath of resolvedIncludePaths) {
    const includedFiles = await processMemoryFile(
      resolvedIncludePath, type, processedPaths, includeExternal, depth + 1, filePath,
    )
    result.push(...includedFiles)
  }
}
```

**3. Sonnet 動態相關性召回**（`src/memdir/findRelevantMemories.ts:77-141`）

```typescript
const SELECT_MEMORIES_SYSTEM_PROMPT = `You are selecting memories that will be useful to Claude Code...
Return a list of filenames for the memories that will clearly be useful (up to 5).
- If unsure, do NOT include.
- If recently-used tools are provided, do NOT select their reference docs (avoid noise).
- Still select warnings, gotchas, known issues about those tools.`

async function selectRelevantMemories(query, memories, signal, recentTools) {
  const manifest = formatMemoryManifest(memories)
  const result = await sideQuery({
    model: getDefaultSonnetModel(),
    system: SELECT_MEMORIES_SYSTEM_PROMPT,
    messages: [{ role: 'user', content: `Query: ${query}\n\nAvailable memories:\n${manifest}` }],
    max_tokens: 256,
    output_format: { type: 'json_schema', schema: {
      type: 'object',
      properties: { selected_memories: { type: 'array', items: { type: 'string' } } },
    }},
  })
  return parsed.selected_memories.filter(f => validFilenames.has(f))
}
```

**4. AutoDream 四階段提示**（`src/services/autoDream/consolidationPrompt.ts`）

```typescript
// Phase 1 — Orient: scan memory dir, read MEMORY.md index
// Phase 2 — Gather recent signal: logs > drifted memories > transcript grep
// Phase 3 — Consolidate: merge new signals, convert relative dates, delete contradicted
// Phase 4 — Prune and index: maintain 200 lines / 25KB cap
```

**5. Forked sub-agent 提取**（`src/services/extractMemories/extractMemories.ts`）

```typescript
const result = await runForkedAgent({
  promptMessages: [createUserMessage({ content: extractPrompt })],
  cacheSafeParams: createCacheSafeParams(context),  // 共享父代理 prompt cache
  canUseTool: createAutoMemCanUseTool(memoryDir),   // 沙箱：只能寫 memory dir
  querySource: 'memory_extraction',
  forkLabel: 'memory_extraction',
  skipTranscript: true,                              // 不污染主 transcript
  onMessage: makeExtractionProgressWatcher(...),
})
```

## 安裝流程（Installation Flow）

> [!info] 此節聚焦記憶系統的「安裝產物」—— 第一次執行時記憶系統會在哪些位置建立檔案。

### 安裝觸發方式

```
bun run dev (首次)
  → init.ts 初始化
  → 第一次 getMemoryFiles() 呼叫
  → 若 ~/.claude/projects/<slug>/memory/ 不存在 → 自動建立
```

### 安裝時序圖

```
 User              cli.tsx            init.ts           memdir/paths.ts        檔案系統
   │                  │                  │                    │                  │
   │──bun run dev────►│                  │                    │                  │
   │                  │──initEntrypoint─►│                    │                  │
   │                  │                  │──getMemoryDir()───►│                  │
   │                  │                  │                    │──mkdir -p───────►│ ~/.claude/projects/<slug>/memory/
   │                  │                  │                    │──touch──────────►│ MEMORY.md (空索引)
   │                  │                  │◄───────────────────│                  │
   │                  │◄─────────────────│                    │                  │
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.claude/CLAUDE.md` | 檔案 | User 層全域指令 |
| `~/.claude/projects/<project-slug>/memory/` | 目錄 | 該專案的長期記憶根目錄 |
| `~/.claude/projects/<project-slug>/memory/MEMORY.md` | 檔案 | 記憶索引（≤200 行 / ~25KB） |
| `~/.claude/projects/<project-slug>/memory/<topic>.md` | 檔案 | 個別記憶（user/feedback/project/reference 四型） |
| `~/.claude/projects/<project-slug>/memory/logs/YYYY/MM/DD.md` | 檔案 | KAIROS 模式 append-only 日誌 |
| `~/.claude/projects/<project-slug>/memory/sessions/` | 目錄 | 過往 session 摘要（compaction 產物） |
| `<repo>/CLAUDE.md` | 檔案 | Project 層指令（檢入 git） |
| `<repo>/CLAUDE.local.md` | 檔案 | Local 層指令（gitignore） |
| `/etc/claude-code/CLAUDE.md` | 檔案 | Managed/Enterprise 層指令 |

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | `1` 關閉自動記憶 | 執行時 |
| `CLAUDE_CODE_SIMPLE` | `1` 簡化模式（關閉記憶） | 執行時 |

> [!warning] 解除安裝
> 移除 Claude Code 後，`~/.claude/projects/<slug>/memory/` 與各層 `CLAUDE.md` 不會被自動清理，需手動 `rm -rf`。

---

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 載入 CLAUDE.md 指令 | session 啟動 / context 組裝 | `src/utils/claudemd.ts` | `getMemoryFiles → processMemoryFile → @include 遞迴` |
| 2 | 動態召回相關記憶 | 每次 user query | `src/memdir/findRelevantMemories.ts` | `scanMemoryFiles → selectRelevantMemories (Sonnet) → 注入 context` |
| 3 | 自動提取新記憶 | query loop 結束時 | `src/query/stopHooks.ts` | `handleStopHooks → executeExtractMemories → runForkedAgent` |
| 4 | AutoDream 重塑 | ≥24h + ≥5 sessions | `src/services/autoDream/autoDream.ts` | `isGateOpen → tryAcquireConsolidationLock → runForkedAgent (4 phases)` |
| 5 | Session Memory 更新 | tokens / tool calls 閾值 | `src/services/SessionMemory/sessionMemory.ts` | `hasMetUpdateThreshold → fork agent → write session note` |
| 6 | Team Memory 同步 | watcher 偵測檔案變更 | `src/services/teamMemorySync/index.ts` | `secretScanner → PUT /api/claude_code/team_memory` |

### 案例詳解

#### 案例 1：載入 CLAUDE.md 指令

```
使用者啟動 session
  │
  ▼
context.ts:getUserContext()
  │
  ▼
claudemd.ts:getMemoryFiles()
  │
  ├─ Layer 1 Managed → /etc/claude-code/CLAUDE.md
  ├─ Layer 2 User    → ~/.claude/CLAUDE.md
  ├─ Layer 3 Project → CWD 向上每層 CLAUDE.md（@include 遞迴）
  └─ Layer 4 Local   → CLAUDE.local.md
  │
  ▼
getClaudeMds() → 注入 system prompt（前綴 MEMORY_INSTRUCTION_PROMPT）
```

#### 案例 2：動態召回相關記憶

```
User 輸入 query
  │
  ▼
QueryEngine.ts → findRelevantMemories(query, memoryDir, signal, recentTools)
  │
  ▼
memoryScan.ts:scanMemoryFiles()
  │   讀取 ~/.claude/projects/<slug>/memory/*.md 的 frontmatter
  │   按 mtime 排序，最多 200 個
  ▼
findRelevantMemories.ts:selectRelevantMemories()
  │   sideQuery → Sonnet API
  │   傳入：query + manifest + recentTools
  │   返回：selected_memories[] (≤5)
  ▼
注入 user context（與 MEMORY.md 一起作為行為通道）
```

#### 案例 3：自動提取新記憶

```
模型產出 final response (無 tool calls)
  │
  ▼
src/query/stopHooks.ts:handleStopHooks()
  │   feature('EXTRACT_MEMORIES') && isExtractModeActive()?
  ▼
extractMemories.ts:executeExtractMemories()
  │   檢查 hasMemoryWritesSince() → 若主代理已寫過 → skip
  ▼
runForkedAgent({
  cacheSafeParams,        // 共享主代理 prompt cache
  canUseTool: createAutoMemCanUseTool(memoryDir),  // 沙箱限制
  skipTranscript: true,
})
  │
  ▼
寫入 ~/.claude/projects/<slug>/memory/<topic>.md + 更新 MEMORY.md
  │
  ▼
appendSystemMessage("Saved 3 memories")  // 通知主對話
```

> [!note] 閱讀建議
> 想理解動態召回，從 `findRelevantMemories.ts` 入；想理解整個記憶生命週期，從 `claudemd.ts:getMemoryFiles` 與 `stopHooks.ts:handleStopHooks` 兩端對讀。

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | 模組邊界清晰：claudemd / memdir / autoDream / sessionMemory 各司其職 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐ | Feature flag 控制所有閾值，可遠程調整不需發版 |
| 安全性（Security） | ⭐⭐⭐⭐ | TeamMemorySync 有 secretScanner、深度限制、symlink 正規化 |
| 文件品質（Documentation） | ⭐⭐⭐⭐ | 內聯 JSDoc 完整解釋設計動機 |
| 創新性（Novelty） | ⭐⭐⭐⭐⭐ | Sonnet-driven recall + AutoDream 在當前 AI Agent 設計中相當前沿 |

> [!tip] 值得學習的設計
> **「指令通道 vs 行為通道分離」** 與 **「Forked sub-agent 共享 prompt cache」** 是兩個能直接套用到自家 AI Agent 的高 ROI 設計。前者解決「硬規則 vs 軟偏好」優先級衝突；後者讓背景任務幾乎不佔額外 token 成本。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> 列出架構層面的潛在問題

- **Sonnet 召回的延遲與成本**：每次 query 都多一次 API 呼叫，雖有 prompt cache，但仍會放大冷啟動延遲
- **AutoDream 鎖機制脆弱**：基於檔案 mtime 的鎖（`tryAcquireConsolidationLock`）在 NFS 等網路檔案系統可能失效
- **記憶上限硬編碼**：200 個檔案 / 25KB 索引上限對長期使用的重度使用者可能不夠
- **沒有跨專案記憶**：每個 project slug 一個 memory dir，跨專案經驗無法復用
- **Sonnet 召回的可解釋性差**：無法解釋為何選了某個記憶（debug 困難）

### 🔮 改進建議（Improvement Suggestions）

1. **混合召回**：先用 embedding 預篩，再用 Sonnet 精選 → 降低 Sonnet 呼叫頻率
2. **記憶分層存儲**：熱記憶（最近 30 天）+ 冷記憶（歸檔），分別用不同策略召回
3. **跨專案記憶共享**：將 user / feedback 類型升級為跨專案，project / reference 維持單專案
4. **AutoDream 時序追蹤**：記錄每次 dream 修改了哪些檔案 + 為什麼，提升可審計性

## 效能基準（Benchmark）

> [!info] 資料來源
> 無公開 benchmark；以下為閱讀程式碼推導的定性特性。

| 場景 | 預期表現 | 瓶頸 |
|------|---------|------|
| 載入 CLAUDE.md（無 @include） | < 50ms | 檔案 IO |
| 載入 CLAUDE.md（深 5 層 @include） | < 200ms | 序列遞迴 |
| Sonnet 召回（200 個記憶） | 1-3s | Sonnet API 延遲 |
| 自動提取（背景） | 不阻塞主對話 | Forked agent 自帶 cache |
| AutoDream 完整四階段 | 30s-2min | grep transcripts + Phase 3 寫入 |

## 快速上手（Quick Start）

```bash
# 1. 啟動 dev 模式
cd /Users/swchen.tw/git/claude-code
bun install
bun run dev

# 2. 觀察記憶系統初始化
ls ~/.claude/projects/

# 3. 手動測試 @include 遞迴
echo "@./shared.md" > CLAUDE.md
echo "Hello from shared" > shared.md
bun run dev  # 應載入兩個檔案

# 4. 檢查 memdir
find ~/.claude/projects -name "MEMORY.md"
```

## 我的心得（My Takeaways）

從這份程式碼最大的收穫是**「記憶系統不是一個黑盒，而是多個可獨立關閉、可獨立調控的子系統」**。以前覺得 AI Agent 的記憶就是「embedding + 向量資料庫」，看完才理解：

- 記憶不只用來召回，也用來**約束行為**（指令通道）
- 記憶提取可以**完全異步**（forked sub-agent 共享 cache）
- 記憶整理可以像人類睡眠一樣**分階段**（AutoDream 四階段）
- 所有閾值都應該**遠程可調**（feature flag），避免硬編碼

接下來想試著把 **「指令通道 / 行為通道分離」** 套用到自己的 Agent 專案。

## 待補充（Open Questions）

- Sonnet 動態召回每次查詢都發一次額外 API 呼叫來評估相關性，這筆費用計入使用者帳單嗎？還是 Anthropic 內部吸收？長時間密集使用下召回呼叫的累計成本有多高？（建議搜尋：`claude code memory recall sonnet cost billing`）
- AutoDream 的「time gate ≥ 24h + session gate ≥ 5」觸發條件是否可由使用者設定？對於每天使用量很低的使用者，AutoDream 可能長期不觸發，導致記憶累積大量未整理的條目。（建議搜尋：`claude AutoDream trigger condition configure threshold`）
- memdir 的四種記憶類型（user/feedback/project/reference）由 extraction sub-agent 自動分類，這個分類的誤判率有多高？有沒有辦法手動審視或修正自動寫入的記憶？（建議搜尋：`claude memdir memory type classification accuracy review`）
- `@include` 遞迴載入最多 5 層深度，若企業的 `CLAUDE.md` 組織結構很深，有沒有已知的遞迴截斷問題或警告訊息通知使用者？（建議搜尋：`claude CLAUDE.md @include recursive depth limit warning`）
- Session Memory 的壓縮（compaction）在壓縮前由 `PreCompact` hook 備份。但壓縮演算法本身的邏輯是什麼？它是否會丟失某些難以重建的細節？（建議搜尋：`claude code session memory compaction algorithm what is lost`）
- Feature Flag `tengu_paper_halyard` 可以讓 Enterprise 跳過 Project/Local 層，這表示企業管理員可以強制所有使用者無法使用本地的 `CLAUDE.local.md`。這個行為有沒有官方文件說明，使用者如何得知自己的本地指令被略過？（建議搜尋：`claude enterprise managed policy CLAUDE.md override feature flag`）

## 相關連結（Related）

- [[CLAUDE-MEMORY-ENGINE]] — 我自己的記憶引擎設計筆記
- [[CONTEXT-ENGINEERING-PATTERNS]] — Context engineering 通用模式整理
- [[FORKED-SUBAGENT-PATTERN]] — Sub-agent fork + prompt cache 共享技術
- [[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]] — Claude Code Plugin 完整生命週期：安裝/停用/移除/更新的檔案影響分析
- [[2026-04-12-CLAUDE-CODE-WORKTREE-FILE-OPERATIONS-AND-REPO-INTEGRATION]] — Worktree 的檔案操作追蹤，與記憶系統的檔案操作可對照參考
- [[2026-04-15-AI-DEVELOPER-EVOLUTION-PRACTITIONER-GUIDE-PERE-VILLEGA]] — 第 6 章從實踐者角度介紹 Teresa Torres 三層記憶系統與 Patrick Zandl 的 JSONL 情節記憶，可與本文工具面分析互補
- [[2026-04-17-CLAUDE-CODE-FEEDBACK-FRUSTRATION-DETECTION-EVENTMETADATA-ARCHITECTURE]] — memory_survey 作為 transcript 分享觸發器的機制，連接記憶壓縮與反饋收集

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 四層優先級（Managed/User/Project/Local）、四種記憶類型（user/feedback/project/reference）、AutoDream 四階段（Orient/Gather/Consolidate/Prune）、`MAX_INCLUDE_DEPTH = 5`、Session Memory 閾值（10K init / 5K update） |
| **理解（半被動）** | 解釋概念與關聯 | 指令通道（CLAUDE.md，硬規則）與行為通道（MEMORY.md，柔性偏好）的差異在於「優先級語氣」與「注入位置」；Sonnet 動態召回取代 embedding 是因為記憶數量小而語意脈絡重要 |
| **分析（主動）** | 檢驗論點與假設 | 假設 1：記憶數量始終 < 200（重度使用者會撞上限）。假設 2：Sonnet 召回比 embedding 準確（無 A/B 數據佐證）。假設 3：AutoDream 鎖檔在所有 FS 都可靠（NFS/分散式 FS 失效） |
| **應用（主動）** | 規劃可執行行動 | 行動 1：在自己的 Agent 加入 `@include` 遞迴 + depth/cycle 防護。行動 2：用 forked sub-agent + prompt cache 重構自家背景任務（自動摘要 / log 整理） |
| **評估（主動）** | 比較替代方案 | vs LangChain Memory：Claude Code 用「Sonnet 召回」而非 `ConversationBufferMemory + embedding`，準確度高但延遲與成本較高；vs Cursor Rules：Cursor 只有單層 .cursorrules，缺乏 4 層優先級與動態召回 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「行為通道」與「指令通道」的邊界在哪？哪些東西該放 CLAUDE.md vs MEMORY.md？
- **假設**：若使用者一天累積 500 個記憶檔案，200 上限的設計會如何降級？
- **證據**：Sonnet 召回真的比 embedding 準嗎？有無 A/B test 數據？
- **觀點**：反對者會說「每次 query 都呼叫 Sonnet 太貴」，如何反駁？
- **後果**：若 AutoDream 把錯誤的「矛盾事實」刪掉了，使用者要如何救回？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？**
   - **AutoDream 誤刪重要記憶**：Phase 3 會刪除「被矛盾的事實」，但「矛盾」由 LLM 判斷，可能誤殺。最壞情況是長期累積的重要 feedback 被一夜清空，且因 `skipTranscript: true` 難以追溯。

2. **什麼情況下會失敗？**
   - **記憶數量爆量**（> 200 檔案）：超出 `scanMemoryFiles` 上限，新記憶會被 mtime 排序擠掉
   - **NFS / 分散式 FS**：`tryAcquireConsolidationLock` 基於 mtime，多機共用 home 目錄時會多次觸發
   - **Sonnet API 故障**：召回完全失效，但因為是「行為通道」非硬性依賴，主對話可繼續
   - **CLAUDE.md 循環引用超過 5 層**：被 `MAX_INCLUDE_DEPTH` 截斷，深層 include 永遠載不到

3. **有沒有更好的替代方案？**
   - **替代 1：Embedding + Sonnet 兩階段召回** —— Embedding 預篩 top-50，Sonnet 精選 top-5，降低 Sonnet 呼叫成本
   - **替代 2：Git-backed memdir** —— 用 git 管理 memdir，AutoDream 的修改自動有版本可追溯，誤刪可 revert
   - **何時選替代**：使用者規模大、誤刪成本高時，git-backed 是必選；個人輕量使用維持現狀即可

## References

- [GitHub — Claude Code（官方）](https://github.com/anthropics/claude-code)
- 本地反編譯版：`/Users/swchen.tw/git/claude-code/src/`
- 關鍵檔案：
  - `src/utils/claudemd.ts`
  - `src/memdir/findRelevantMemories.ts`
  - `src/memdir/memoryTypes.ts`
  - `src/services/extractMemories/extractMemories.ts`
  - `src/services/autoDream/autoDream.ts`
  - `src/services/autoDream/consolidationPrompt.ts`
  - `src/services/SessionMemory/sessionMemory.ts`
  - `src/services/teamMemorySync/index.ts`
