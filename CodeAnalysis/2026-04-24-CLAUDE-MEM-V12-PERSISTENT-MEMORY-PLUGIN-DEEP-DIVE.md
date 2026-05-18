---
title: "Claude-Mem v12 — Claude Code 持久記憶外掛深度分析"
date: 2026-04-24
category: CodeAnalysis
tags:
  - #code-analysis
  - #typescript
  - #ai/agent
  - #tools/cli
  - #claude-code
source: "https://github.com/thedotmack/claude-mem"
source_type: code
author: "Alex Newman (thedotmack)"
status: notes
links:
  - "[[2025-08-31-CLAUDE-MEM-CODE-ANALYSIS]]"
  - "[[2026-03-07-CLAUDE-MEMORY-ENGINE]]"
  - "[[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]]"
  - "[[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]]"
  - "[[2026-01-24-CLAUDE-CODE-HOOKS-CODE-ANALYSIS]]"
github_stars: 66751
github_language: TypeScript
---

## 摘要（Summary）

Claude-Mem 是一個 Claude Code 外掛（plugin），自動捕捉每次 coding session 中的工具使用觀察（observation），透過 Claude Agent SDK 進行 AI 壓縮摘要，並在未來的 session 中注入相關上下文（context）。目前版本 v12.3.9，擁有超過 66,000 GitHub stars，是 Claude Code 生態系中最受歡迎的記憶持久化方案。專案架構已從早期的單體式演進為模組化的事件驅動系統，支援 Claude Code、Gemini CLI、Cursor、Windsurf、OpenCode 等多種 IDE。

## Why — 為什麼存在？

> 這個專案要解決的根本問題是什麼？現有方案的哪些痛點促使它被創造？

- **核心動機**：Claude Code 的每次 session 互相獨立，session 結束後所有上下文（context）消失。開發者在多次 session 之間需要反覆重新解釋專案背景、之前的決策、已發現的 bug 等資訊。
- **取代/改善什麼**：取代手動維護 CLAUDE.md 或手動複製過往對話的低效工作流。Claude-Mem 自動化整個「捕捉 → 壓縮 → 注入」流程。
- **目標用戶**：所有 Claude Code 使用者，特別是維護大型專案、需要跨 session 連續性的開發者。

## What — 是什麼？

> 這個專案的功能邊界與核心能力。

- **主要功能**：
  - 自動捕捉每次工具使用（PostToolUse hook）的觀察
  - 透過 Claude Agent SDK 以獨立的「observer agent」壓縮觀察為結構化記憶
  - 在新 session 開始時注入相關的歷史上下文
  - 混合搜尋（Hybrid Search）：SQLite FTS5 全文搜尋 + ChromaDB 向量語意搜尋
  - MCP 工具整合：`search`、`timeline`、`get_observations` 三層漸進式披露（Progressive Disclosure）
  - Web Viewer UI（http://localhost:37777）即時觀察記憶流
  - 隱私控制：`<private>` 標籤排除敏感內容
  - 多 IDE 支援：Claude Code、Gemini CLI、Cursor、Windsurf、OpenCode
- **不做什麼（Non-goals）**：不是通用知識庫（knowledge base），不做跨用戶記憶共享，不替代版本控制
- **技術棧（Tech Stack）**：TypeScript、Bun（runtime）、Express（HTTP API）、SQLite（bun:sqlite）、ChromaDB（via MCP）、Claude Agent SDK、esbuild（build）

## How — 如何運作？

> [!important] 本節包含 3 種 ASCII 圖表，用 code block 呈現系統全貌。

### 系統架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Claude Code / Gemini CLI / Cursor                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ SessionStart│  │UserPromptSub │  │ PostToolUse │  │Stop/End  │ │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └────┬─────┘ │
└─────────┼────────────────┼─────────────────┼───────────────┼───────┘
          │                │                 │               │
          ▼                ▼                 ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   CLI Layer (Node → Bun bridge)                     │
│  ┌────────────┐  ┌───────────────────────────────────────────────┐  │
│  │bun-runner  │→│ hook-command.ts → handlers/ (8 event types)   │  │
│  │   .js      │  │  context | session-init | observation |       │  │
│  └────────────┘  │  summarize | session-complete | file-context  │  │
│                  └──────────────────────┬────────────────────────┘  │
└─────────────────────────────────────────┼──────────────────────────┘
                                          │ HTTP POST
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Worker Daemon (Express, port 37777)                    │
│                                                                     │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────┐                 │
│  │SessionManager│  │  SDKAgent   │  │SearchManager│                 │
│  │ (lifecycle)  │  │(Agent SDK)  │  │(hybrid srch)│                 │
│  └──────┬───────┘  └──────┬─────┘  └──────┬──────┘                 │
│         │                 │               │                         │
│  ┌──────▼───────┐  ┌──────▼─────┐  ┌──────▼──────┐                 │
│  │PendingMessage│  │ProcessReg- │  │SSEBroadcast-│                 │
│  │   Store      │  │  istry     │  │     er      │                 │
│  └──────────────┘  └────────────┘  └─────────────┘                 │
│         │                                                           │
│  ┌──────▼────────────────────────────────────────────┐              │
│  │           HTTP Routes (REST API)                  │              │
│  │  SessionRoutes | DataRoutes | SearchRoutes        │              │
│  │  SettingsRoutes | LogsRoutes | ViewerRoutes       │              │
│  └───────────────────────────────────────────────────┘              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Storage Layer                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐                 │
│  │  SQLite (bun:sqlite) │  │  ChromaDB (via MCP)  │                 │
│  │  ~/.claude-mem/      │  │  ~/.claude-mem/      │                 │
│  │  claude-mem.db       │  │  chroma/             │                 │
│  │                      │  │                      │                 │
│  │  Tables:             │  │  Collections:        │                 │
│  │  - sessions          │  │  - observations      │                 │
│  │  - memories          │  │  - summaries         │                 │
│  │  - overviews         │  │                      │                 │
│  │  - pending_messages  │  │  Vector embeddings   │                 │
│  │  - user_prompts      │  │  for semantic search │                 │
│  └──────────────────────┘  └──────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 執行流程圖（Execution Flowchart）

```
 新 Session 開始
       │
       ▼
[SessionStart Hook]
       │
       ├── smart-install.js ──► 檢查 Bun/uv 是否已安裝
       │                              │
       │                     ┌────────┴────────┐
       │                     │ 已安裝          │ 未安裝
       │                     │ (跳過)          │ (自動安裝)
       │                     └────────┬────────┘
       │                              │
       ├── worker 啟動 ──► bun worker-service.cjs start
       │                         │
       │                   curl /health 等待就緒
       │                         │
       └── context 注入 ──► ContextBuilder
                                 │
                          ┌──────┴──────┐
                          │ 有歷史資料  │ 無歷史資料
                          │             │
                          ▼             ▼
                    [注入 timeline   [空狀態提示]
                     + summaries]
                          │
                          ▼
[UserPromptSubmit Hook]
       │
       ▼
[session-init Handler] ──► POST /api/sessions/init
       │
       ▼
[SessionManager] ──► 建立 ActiveSession
       │                    │
       ▼                    ▼
[SDKAgent.startSession] ──► spawn Claude subprocess
       │                    │  (Agent SDK query loop)
       │                    │  disallowedTools: 全部禁用
       │                    │  (純觀察者，無工具)
       ▼                    │
[PostToolUse Hook]          │
       │                    │
       ▼                    │
[observation Handler]       │
       │                    │
       ▼                    │
POST /api/sessions/         │
  observations              │
       │                    │
       ▼                    │
[PendingMessageStore]  ◄────┘
  enqueue()                 │
       │                    │
       ▼                    ▼
[SDKAgent 處理]  ──► ResponseProcessor
       │                    │
       ├── storeObservations() ──► SQLite
       ├── chromaSync.sync() ──► ChromaDB
       └── broadcastObservation() ──► SSE/Viewer UI
       │
       ▼
[Stop Hook] ──► summarize ──► /api/sessions/summarize
       │
       ▼
[SessionEnd Hook] ──► session-complete ──► drain pending messages
       │
       ▼
     End
```

### 時序圖（Sequence Diagram）

```
 Claude Code     CLI/Hook       Worker (37777)    SDKAgent       SQLite     ChromaDB
     │              │                │               │              │           │
     │──SessionStart────►│               │               │              │           │
     │              │──smart-install──►│               │              │           │
     │              │──start worker────►│               │              │           │
     │              │              ◄──/health OK──│               │              │           │
     │              │──context req─────►│               │              │           │
     │              │              │──query obs────────────────────►│           │
     │              │              │◄─────────────────obs data──────│           │
     │              │◄──context JSON───│               │              │           │
     │◄──system     │               │               │              │           │
     │  reminder    │               │               │              │           │
     │              │                │               │              │           │
     │──UserPrompt──────►│               │               │              │           │
     │              │──POST /init──────►│               │              │           │
     │              │              │──startSession────►│              │           │
     │              │              │               │──spawn claude──►│           │
     │              │              │               │  (Agent SDK)   │           │
     │              │◄──ack────────────│               │              │           │
     │              │                │               │              │           │
     │──ToolUse─────────►│               │               │              │           │
     │              │──POST /obs───────►│               │              │           │
     │              │              │──enqueue──────────►│              │           │
     │              │              │               │◄─claim msg─────│           │
     │              │              │               │──process───────►│           │
     │              │              │               │              │──sync──────►│
     │              │              │               │              │           │
     │──Stop────────────►│               │               │              │           │
     │              │──POST /summarize──►│               │              │           │
     │              │              │──summary req───►│              │           │
     │              │              │◄──summary──────│──store────────►│           │
     │              │              │               │              │──sync──────►│
     │──SessionEnd──────►│               │               │              │           │
     │              │──POST /complete───►│               │              │           │
     │              │              │──drain──────────►│              │           │
     │              │              │               │              │           │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> 1. **Observer Agent 模式**：SDKAgent 作為純觀察者，禁用所有工具，避免無限迴圈。
> 2. **CLAIM-CONFIRM 佇列模式**：PendingMessageStore 使用原子性狀態轉移確保訊息不遺失。
> 3. **Circuit Breaker**：Generator 連續崩潰超過 3 次後自動中斷，防止無限重試。

1. **Bun 作為 runtime**：選擇 Bun 而非 Node.js 是因為 `bun:sqlite` 提供原生 SQLite 綁定，無需額外的 native module 編譯。Worker daemon 由 Bun 管理進程生命週期。
2. **Hook → HTTP → Queue 三層解耦**：Hook 只負責發送 HTTP 請求到 Worker，Worker 透過 PendingMessageStore 非同步排隊處理。這確保 hook 永不阻塞 Claude Code 主流程。
3. **混合搜尋策略（Hybrid Search）**：同時使用 SQLite FTS5（關鍵字精確匹配）和 ChromaDB（語意向量搜尋），SearchOrchestrator 根據查詢類型自動選擇最佳策略。
4. **漸進式披露（Progressive Disclosure）**：MCP 搜尋工具分三層——`search`（index ~50 tokens/result）→ `timeline`（時序上下文）→ `get_observations`（完整 ~500 tokens/result），節省約 10 倍 token 消耗。
5. **優雅降級（Graceful Degradation）**：Worker 不可用時，hook 以 exit code 0 靜默跳過，絕不阻塞用戶的 Claude Code session。

### 資料流（Data Flow）

1. 用戶在 Claude Code 中使用工具（Read、Edit、Bash 等）
2. PostToolUse hook 捕捉工具輸入/輸出，發送到 Worker HTTP API
3. Worker 將觀察排入 PendingMessageStore（SQLite）
4. SDKAgent 的 message generator 消費佇列中的訊息
5. Agent SDK 呼叫 Claude subprocess 壓縮觀察為結構化 XML（observation 或 summary）
6. ResponseProcessor 解析 XML，存入 SQLite 和 ChromaDB
7. SSEBroadcaster 推送到 Web Viewer UI
8. 下次 session 開始時，ContextBuilder 從 SQLite 查詢最新觀察和摘要，注入為 system reminder

### 關鍵程式碼（Key Code Snippets）

**Hook 事件分發器**（`src/cli/handlers/index.ts`）：

```typescript
export type EventType =
  | 'context'           // SessionStart - inject context
  | 'session-init'      // UserPromptSubmit - initialize session
  | 'observation'       // PostToolUse - save observation
  | 'summarize'         // Stop - generate summary (phase 1)
  | 'session-complete'  // Stop - complete session (phase 2)
  | 'user-message'      // SessionStart (parallel) - display to user
  | 'file-edit'         // Cursor afterFileEdit
  | 'file-context';     // PreToolUse - inject file observation history

const handlers: Record<EventType, EventHandler> = {
  'context': contextHandler,
  'session-init': sessionInitHandler,
  'observation': observationHandler,
  'summarize': summarizeHandler,
  'session-complete': sessionCompleteHandler,
  'user-message': userMessageHandler,
  'file-edit': fileEditHandler,
  'file-context': fileContextHandler
};
```

**SDKAgent 觀察者限制**（`src/services/worker/SDKAgent.ts`）：

```typescript
// Memory agent is OBSERVER ONLY - no tools allowed
const disallowedTools = [
  'Bash', 'Read', 'Write', 'Edit', 'Grep', 'Glob',
  'WebFetch', 'WebSearch', 'Task', 'NotebookEdit',
  'AskUserQuestion', 'TodoWrite'
];
```

**CLAIM-CONFIRM 佇列模式**（概念自 `src/services/sqlite/PendingMessageStore.ts`）：

```
enqueue()           -> INSERT status='pending'
claimNextMessage()  -> UPDATE status='processing' (atomic)
confirmProcessed()  -> DELETE (success)
markFailed()        -> UPDATE status='failed' (retry < 3)

Self-healing: messages in 'processing' for >60s reset to 'pending'
```

**優雅降級錯誤分類**（`src/cli/hook-command.ts`）：

```typescript
// Transport failures — worker unreachable → exit 0 (never block)
const transportPatterns = [
  'econnrefused', 'econnreset', 'epipe', 'etimedout',
  'fetch failed', 'socket hang up',
];

// HTTP 4xx client errors — our bug → exit 2 (blocking, needs fix)
// HTTP 5xx server errors — worker has internal problems → exit 0
```

## 安裝流程（Installation Flow）

> [!info] 追蹤層級
> 本節追蹤到**具體檔案路徑**，而非停在概念層。

### 安裝觸發方式

```
npx claude-mem install → src/npx-cli/commands/install.ts → 複製 plugin/ 到 ~/.claude/plugins/cache/
/plugin marketplace add thedotmack/claude-mem → Claude Code 自動下載 → ~/.claude/plugins/cache/
```

### 安裝時序圖

```
 用戶              npx CLI             Claude Code Settings      目標系統
   │                  │                       │                      │
   │──npx claude-mem──►│                       │                      │
   │   install        │                       │                      │
   │                  │──registerMarketplace───►│                      │
   │                  │   known-marketplaces.json                     │
   │                  │──registerPlugin────────►│                      │
   │                  │   installed-plugins.json                      │
   │                  │──enablePlugin──────────►│                      │
   │                  │   settings.json (enabledPlugins)              │
   │                  │──cpSync plugin/────────────────────────────────►│
   │                  │                        │  ~/.claude/plugins/  │
   │                  │                        │  cache/thedotmack/   │
   │                  │                        │  claude-mem/{ver}/   │
   │                  │                                               │
   │                  │── [SessionStart hook 首次觸發]                  │
   │                  │                                               │
   │                  │──smart-install.js──────────────────────────────►│
   │                  │   檢查 Bun ─── 未安裝 → curl install          │
   │                  │   檢查 uv ──── 未安裝 → curl install          │
   │                  │   bun install（安裝 node_modules）             │
   │                  │──start worker──────────────────────────────────►│
   │                  │   bun worker-service.cjs start                │
   │                  │                        │  PID file            │
   │                  │                        │  ~/.claude-mem/      │
   │◄─────────────────│                        │  worker.pid          │
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.claude/plugins/cache/thedotmack/claude-mem/{version}/` | 目錄 | 外掛主目錄（hooks、scripts、skills、modes） |
| `~/.claude/plugins/known-marketplaces.json` | 檔案 | Marketplace 登記 |
| `~/.claude/plugins/installed-plugins.json` | 檔案 | 已安裝外掛清單 |
| `~/.claude/settings.json` | 檔案 | `enabledPlugins["claude-mem@thedotmack"]: true` |
| `~/.claude-mem/` | 目錄 | 資料目錄 |
| `~/.claude-mem/settings.json` | 檔案 | Claude-Mem 設定（port、model、mode 等） |
| `~/.claude-mem/claude-mem.db` | 檔案 | SQLite 資料庫 |
| `~/.claude-mem/chroma/` | 目錄 | ChromaDB 向量資料庫 |
| `~/.claude-mem/logs/worker-{date}.log` | 檔案 | Worker 日誌 |
| `~/.claude-mem/worker.pid` | 檔案 | Worker 進程 PID |

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| `CLAUDE_PLUGIN_ROOT` | 外掛安裝路徑 | Claude Code 自動設定 |
| `CLAUDE_MEM_DATA_DIR` | 自訂資料目錄（預設 `~/.claude-mem`） | 使用者可選設定 |
| `CLAUDE_MEM_WORKER_PORT` | Worker HTTP port（預設 37777） | 使用者可選設定 |
| `CLAUDE_MEM_WORKER_HOST` | Worker 綁定位址（預設 127.0.0.1） | 使用者可選設定 |
| `CLAUDE_MEM_MODE` | 工作流模式（如 `code`、`code--zh`） | 使用者可選設定 |
| `CLAUDE_MEM_MAX_CONCURRENT_AGENTS` | 最大並行 Agent 數（預設 2） | 使用者可選設定 |

> [!warning] 解除安裝
> 需手動清理：`~/.claude/plugins/cache/thedotmack/`、`~/.claude-mem/`（資料庫）、修改 `~/.claude/settings.json` 移除 enabledPlugins 項目。或執行 `npx claude-mem uninstall`。

---

## 使用案例地圖（Use Case Map）

> [!important] 本節追蹤從**用戶觸發**到**最終效果**的完整檔案路徑。

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 自動記憶捕捉 | PostToolUse hook | `src/cli/handlers/observation.ts` | `observation → Worker → SDKAgent → SQLite/Chroma` |
| 2 | 上下文注入 | SessionStart hook | `src/cli/handlers/context.ts` | `context → ContextBuilder → ObservationCompiler → SQLite` |
| 3 | 記憶搜尋 | MCP tool `search` | `src/servers/mcp-server.ts` | `mcp-server → SearchManager → SearchOrchestrator → Chroma/SQLite` |
| 4 | Session 摘要 | Stop hook | `src/cli/handlers/summarize.ts` | `summarize → Worker → SDKAgent → summary prompt → SQLite` |
| 5 | Web Viewer | 瀏覽器開啟 :37777 | `src/services/worker/http/routes/ViewerRoutes.ts` | `ViewerRoutes → SSEBroadcaster → viewer.html (React)` |
| 6 | 安裝外掛 | `npx claude-mem install` | `src/npx-cli/commands/install.ts` | `install → cpSync → registerPlugin → enablePlugin` |

### 案例詳解

#### 案例 1：自動記憶捕捉

```
用戶：在 Claude Code 中使用任何工具（Read、Edit、Bash...）
  │
  ▼
plugin/hooks/hooks.json: PostToolUse matcher="*"
  │
  ▼
plugin/scripts/bun-runner.js → worker-service.cjs hook claude-code observation
  │
  ▼
src/cli/hook-command.ts:executeHookPipeline()
  │  讀取 stdin JSON（tool_name, tool_input, tool_response）
  │
  ▼
src/cli/handlers/observation.ts:observationHandler.execute()
  │  ── 檢查 ──► project 是否被排除？（EXCLUDED_PROJECTS）
  │  ── POST ──► http://127.0.0.1:37777/api/sessions/observations
  │
  ▼
src/services/worker/http/routes/SessionRoutes.ts
  │
  ▼
src/services/worker/SessionManager.ts:queueObservation()
  │  ── enqueue ──► PendingMessageStore（SQLite pending_messages table）
  │
  ▼
src/services/worker/SDKAgent.ts:createMessageGenerator()
  │  ── claim ──► PendingMessageStore.claimNextMessage()
  │  ── yield ──► buildObservationPrompt() → Agent SDK query loop
  │
  ▼
Claude subprocess（Agent SDK）──► 產生結構化 XML observation
  │
  ▼
src/services/worker/agents/ResponseProcessor.ts
  │  ── parse XML ──► ParsedObservation
  │  ── store ──► SQLite observations table
  │  ── sync ──► ChromaDB（向量嵌入）
  │  ── broadcast ──► SSEBroadcaster → Web Viewer UI
```

#### 案例 2：上下文注入

```
用戶：開啟新的 Claude Code session
  │
  ▼
plugin/hooks/hooks.json: SessionStart
  │
  ▼
src/cli/handlers/context.ts:contextHandler.execute()
  │
  ▼
src/services/context/ContextBuilder.ts:buildContext()
  │  ── 讀取 ──► SessionStore（SQLite）
  │  ── 查詢 ──► ObservationCompiler.queryObservations()
  │  ── 查詢 ──► ObservationCompiler.querySummaries()
  │
  ▼
TokenCalculator.calculateTokenEconomics()
  │  根據 token 預算決定注入多少觀察
  │
  ▼
TimelineRenderer.renderTimeline()
  │  將觀察和摘要按時間排列
  │
  ▼
輸出 JSON → Claude Code 的 system-reminder 注入
```

> [!note] 閱讀建議
> 若要快速驗證某功能，從「入口檔案」欄直接跳去讀對應的源碼最有效率。

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | 從 2000 行單體重構為模組化架構，每個模組職責清晰（SessionManager、SDKAgent、SearchManager 等） |
| 可擴展性（Scalability） | ⭐⭐⭐⭐ | 支援多 IDE 透過 adapter pattern（Claude Code、Gemini、Cursor、Windsurf），搜尋透過 strategy pattern 可插拔 |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐⭐ | 有完整的測試目錄（sqlite、agents、search、context、infrastructure、server） |
| 文件品質（Documentation） | ⭐⭐⭐⭐⭐ | 有 Mintlify 驅動的公開文件站（docs.claude-mem.ai），架構文件詳盡，30+ 語言 README 翻譯 |
| 依賴管理（Dependency Management） | ⭐⭐⭐⭐ | 核心依賴精簡（Agent SDK、Express、SQLite），ChromaDB 透過 MCP 解耦避免 native module 問題 |

> [!tip] 值得學習的設計
> 1. **CLAIM-CONFIRM 佇列模式**：簡潔的原子性狀態轉移處理非同步訊息，含自修復（self-healing）機制。
> 2. **漸進式披露搜尋**：三層 MCP 工具設計節省 10 倍 token，是 AI 工具設計的典範。
> 3. **優雅降級策略**：exit code 分類確保外掛故障絕不阻塞用戶主流程。
> 4. **Observer Agent 禁用所有工具**：防止記憶 agent 意外觸發工具造成無限迴圈。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷

- **Bun 依賴風險**：整個 worker 建立在 Bun runtime 上（`bun:sqlite`），如果 Bun 有 breaking change 或 bug，影響面大
- **單機 localhost 限制**：Worker 綁定 127.0.0.1，不支援遠端或團隊共享記憶（Pro feature 可能解決）
- **資料庫遷移跨版本問題**：已有 `repairMalformedSchema` 修復機制，顯示不同版本間 SQLite schema 衝突是實際痛點
- **Agent SDK 計費**：observer agent 使用 Claude API 進行壓縮，每次 session 都會產生額外 API 費用，對高頻使用者可能顯著
- **最大並行 Agent 數限制**：預設 2 個並行，高負載時可能造成佇列堆積（有 idle session eviction 機制緩解）

### 🔮 改進建議（Improvement Suggestions）

1. 考慮支援 Node.js 原生 SQLite（Node 22+）作為 Bun 的備選，降低 runtime 耦合
2. 提供本地 embedding model 選項（如 ONNX Runtime），減少對 ChromaDB MCP 的依賴
3. 增加觀察壓縮的 cost tracking，讓用戶能監控記憶系統的 API 消耗

## 效能基準（Benchmark）

> [!info] 資料來源
> 以下為架構分析推估的效能特性，非實測數據。

| 場景 | 效能特性 | 說明 |
|------|---------|------|
| Hook 延遲 | < 100ms | Hook 只發 HTTP POST，不等待 AI 處理 |
| 觀察壓縮 | 數秒 | SDKAgent 呼叫 Claude API，取決於 API 回應速度 |
| 上下文注入 | < 1s | SQLite 查詢 + token 計算 |
| 搜尋（FTS5） | < 50ms | SQLite 全文搜尋，本地操作 |
| 搜尋（Chroma） | ~200ms | 向量搜尋透過 MCP stdio 通訊 |
| Worker 啟動 | 5-20s | 等待 /health endpoint 就緒 |

**預期瓶頸**：
- ChromaDB MCP 啟動時的 Python 環境初始化
- 高頻工具使用時的 PendingMessageStore 佇列累積
- SQLite WAL 模式下的寫入競爭（多 session 同時寫入）

## 快速上手（Quick Start）

```bash
# 安裝
npx claude-mem install

# 重啟 Claude Code，記憶系統自動啟動

# 檢查 worker 狀態
curl http://127.0.0.1:37777/health

# 開啟 Web Viewer
open http://127.0.0.1:37777

# 在 Claude Code 中搜尋記憶
# 使用 mem-search skill 或 MCP tools
```

## 我的心得（My Takeaways）

1. **Hook 系統設計精妙**：Claude Code 的 5 個 lifecycle hook 提供了完整的 session 生命週期切入點，claude-mem 巧妙利用每個 hook 完成不同任務。
2. **CLAIM-CONFIRM 模式值得借鑑**：這種簡潔的佇列模式比 Redis 等外部佇列輕量得多，適合單機場景。
3. **漸進式披露是 AI 工具設計的最佳實踐**：不一次傾倒所有資料，而是讓 AI agent 逐步深入，大幅降低 token 浪費。
4. **Observer Agent 的「無工具」設計**：透過 `disallowedTools` 確保記憶 agent 不會觸發副作用，是防止 AI agent 失控的聰明策略。
5. **優雅降級的 exit code 策略**：exit 0 vs exit 2 的分類邏輯值得在所有 hook-based 外掛中複用。

## 待補充（Open Questions）

- 觀察壓縮的平均 token 消耗是多少？長期使用一年後的累積 API 費用估算？（建議搜尋：「claude-mem cost estimation API usage」）
- ChromaDB MCP Server 的嵌入模型是什麼？是否使用 OpenAI embeddings 還是本地模型？（建議搜尋：「chroma-mcp embedding model configuration」）
- Pro Features 的 Memory Stream UI 具體提供哪些額外功能？是否有計劃開源？（建議搜尋：「claude-mem pro features roadmap」）
- 多 worktree 支援（WorktreeAdoption）的合併策略是什麼？如何處理來自不同 worktree 的衝突觀察？（建議搜尋：「claude-mem worktree adoption merge strategy」）
- Endless Mode（beta）的 biomimetic memory architecture 具體機制是什麼？與標準模式的記憶保留率差異？（建議搜尋：「claude-mem endless mode biomimetic memory」）

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 5 個 lifecycle hooks（SessionStart、UserPromptSubmit、PostToolUse、Stop、SessionEnd）；Worker port 37777；CLAIM-CONFIRM 佇列模式；SDKAgent 禁用所有工具；exit code 0/1/2 策略 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | claude-mem 的核心循環是「捕捉 → 壓縮 → 存儲 → 注入」：hook 捕捉原始工具使用 → SDKAgent 用 Agent SDK 壓縮為結構化 XML → 存入 SQLite + ChromaDB → 下次 session 從 ContextBuilder 注入。三層搜尋（search → timeline → get_observations）的漸進式披露是 token 效率的關鍵。優雅降級確保記憶系統的故障不會影響用戶主要的 coding 體驗。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | **關鍵假設**：(1) 用戶願意承擔 observer agent 的額外 API 費用；(2) Bun runtime 穩定性足夠生產環境；(3) 本地 SQLite + ChromaDB 足以應付單用戶的記憶規模。**潛在問題**：observer agent 的壓縮品質完全依賴 Claude 模型的輸出，若模型幻覺（hallucination）則記憶品質受損且無法自行修正。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | (1) 在自己的 Claude Code 外掛開發中採用 CLAIM-CONFIRM 佇列模式處理非同步任務；(2) 在設計 AI 工具的 API 時套用漸進式披露模式，提供 index → detail 的分層查詢；(3) 採用 exit code 0/2 分類策略作為所有 hook-based 外掛的標準錯誤處理模式 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | claude-mem vs CLAUDE.md 手動維護：自動化程度高但有 API 成本和複雜度代價。claude-mem vs Claude Code 內建記憶（若未來推出）：外掛方案靈活但依賴第三方維護。對於個人開發者，claude-mem 的 ROI 取決於 session 頻率——每天多次切換 session 的用戶收益最大，偶爾使用的用戶可能不值得。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「觀察」（observation）和「記憶」（memory）在 claude-mem 中的精確邊界是什麼？觀察是原始工具輸出，記憶是 AI 壓縮後的結構化資料？
- **假設**：若 Claude API 大幅漲價或限流，claude-mem 的 observer agent 架構是否仍可行？是否有 fallback 到本地 LLM 的機制？
- **證據**：66,751 stars 代表用戶量，但實際 daily active 用戶有多少？star 數是否主要來自 README 的品牌效應而非實際使用？
- **觀點**：若站在 Anthropic 官方的立場，claude-mem 這樣的第三方記憶外掛是否會被內建功能取代？官方是否有動機支持或抑制這類外掛？
- **後果**：若 claude-mem 積累一年的記憶資料，SQLite 資料庫大小、ChromaDB 索引大小可能達到多少？是否會出現效能退化？

### 方案批判三問（Critical Evaluation）

> [!warning] 程式碼實作方案批判

1. **最大的風險是什麼？** — Observer agent 使用 Claude API 處理每次工具使用，若 API key 洩漏或帳號被封，所有記憶功能停擺且歷史記憶無法增量更新。此外，SQLite 資料庫若損壞（如進程異常終止），可能丟失所有記憶歷史。
2. **什麼情況下會失敗？** — (1) Bun runtime 版本不相容（已發生過 native module rebuild 問題）；(2) 磁碟空間不足導致 SQLite WAL 無法寫入；(3) 多個 Claude Code session 同時啟動超過 MAX_CONCURRENT_AGENTS 限制時的佇列堆積；(4) ChromaDB MCP server Python 環境損壞。
3. **有沒有更好的替代方案？** — 對於輕量需求，手動維護的 CLAUDE.md + `.claude/commands/` 自訂指令可能更簡單且零成本。對於團隊場景，基於 Git 的共享 context（如 AGENTS.md）更適合。claude-mem 最適合的場景是：個人開發者、高頻 session 切換、需要自動化記憶的長期專案。

## 相關連結（Related）
- [[2025-08-31-CLAUDE-MEM-CODE-ANALYSIS]] — 同一 repo 的早期版本分析，可對比架構演進
- [[2026-03-07-CLAUDE-MEMORY-ENGINE]] — Claude Code 記憶引擎概念分析
- [[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]] — Claude Code 記憶系統整體架構
- [[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]] — 團隊記憶深度分析
- [[2026-01-24-CLAUDE-CODE-HOOKS-CODE-ANALYSIS]] — Claude Code hooks 系統分析，claude-mem 的基礎設施
- [[2026-05-17-GBRAIN-EVALS-VS-JARVIS-EVAL-METHODOLOGY]] — gbrain 是另一套 persistent memory 系統，採 MCP server + hybrid search + auto knowledge graph 路線；與 claude-mem 的 hook-driven 路線是兩種不同哲學

## References
- [GitHub Repo](https://github.com/thedotmack/claude-mem)
- [官方文件](https://docs.claude-mem.ai/)
- [架構概覽](https://docs.claude-mem.ai/architecture/overview)
- [漸進式披露哲學](https://docs.claude-mem.ai/progressive-disclosure)
