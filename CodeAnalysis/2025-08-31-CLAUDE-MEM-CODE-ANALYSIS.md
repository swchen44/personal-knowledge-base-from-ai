---
title: "claude-mem — Claude Code 跨 Session 持久記憶系統深度分析"
date: 2025-08-31
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#ai/claude-code"
  - "#ai/agent"
  - "#tools/cli"
  - "#ai/llm"
source: "https://github.com/thedotmack/claude-mem"
source_type: code
author: "Alex Newman (@thedotmack)"
status: notes
links:
  - "[[AI-AGENT-DESIGN]]"
  - "[[CLAUDE-CODE-SETUP]]"
  - "[[PERSONAL-KNOWLEDGE-BASE]]"
github_stars: 38509
github_language: TypeScript/JavaScript
---

## 摘要（Summary）

`claude-mem` 是一個 Claude Code 插件，透過 6 個生命週期鉤子（lifecycle hooks）自動捕捉每次 coding session 中 Claude 的所有工具使用記錄，用 AI（Claude Agent SDK）壓縮成語意摘要，並在下次 session 開始時將相關記憶注入回上下文視窗（Context Window）。核心問題：LLM 的 context 在 session 結束後全部消失，每次都從零開始。claude-mem 解決了這個問題，讓 Claude 真正「記得」之前做過什麼。

目前 GitHub 有 **38,509 顆 ⭐**、2,787 個 fork，是 Claude Code 插件生態中最受歡迎的記憶工具。

## Why — 為什麼存在？

- **核心動機**：LLM session 無狀態（stateless）——每次 session 結束，上下文完全清空，Claude 不記得上次做了什麼、解決了哪些 bug、專案有哪些特殊設定
- **取代/改善什麼**：取代手動維護 CLAUDE.md 的方式，從被動記錄升級為全自動記憶壓縮
- **目標用戶**：使用 Claude Code 進行長期、複雜專案開發的工程師；需要跨 session 持續作業的 AI Agent 使用者

## What — 是什麼？

- **主要功能**：
  - 自動在 PostToolUse hook 捕捉工具觀察值（observation），存入 SQLite
  - 在 Stop hook 用 Claude AI 壓縮 session 為語意摘要
  - 在 SessionStart hook 從歷史中提取相關記憶，注入為系統上下文（system context）
  - MCP 工具（search、timeline、get_observations）支援自然語言查詢歷史記憶
  - Web Viewer UI（port 37777）即時查看記憶流
  - `<private>` 標籤讓使用者排除敏感內容
  - 30+ 語言版本的 Mode 設定（code、law-study、chill 變體）
- **不做什麼**：不替代完整的向量資料庫知識庫（KB），不做即時搜尋增強（RAG）在每次工具呼叫；主要鎖定 Claude Code session 場景，而非通用 LLM 記憶
- **技術棧（Tech Stack）**：TypeScript、Node.js 18+、Bun（worker service 執行時）、SQLite（FTS5 全文搜尋）、Chroma（向量資料庫，語義搜尋）、Claude Agent SDK、MCP SDK、Express、React（Web Viewer）

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Code (IDE/CLI)                       │
│  ┌────────────┐  ┌───────────────┐  ┌──────────────────────┐   │
│  │  SessionStart│  │ PostToolUse  │  │   Stop / SessionEnd  │   │
│  └─────┬──────┘  └───────┬───────┘  └──────────┬───────────┘   │
│        │  hook scripts   │                      │                │
└────────┼─────────────────┼──────────────────────┼───────────────┘
         │                 │                      │
         ▼                 ▼                      ▼
┌──────────────────────────────────────────────────────────────────┐
│              Worker Service (Bun HTTP API, port 37777)            │
│                                                                    │
│  /api/context/inject   /api/sessions/observations  /api/sessions/  │
│         │                        │                 summarize       │
│         ▼                        ▼                      │         │
│  ┌─────────────┐     ┌──────────────────┐               ▼         │
│  │ContextBuilder│    │ ObservationStore  │   ┌──────────────────┐ │
│  │ (摘要注入)  │    │ (SQLite + FTS5)  │   │  Claude Agent SDK │ │
│  └──────┬──────┘     └────────┬─────────┘   │  (AI 壓縮摘要)   │ │
│         │                     │              └──────────────────┘ │
│         │              ┌──────▼──────────┐                        │
│         │              │  Chroma Vector  │                        │
│         │              │  DB（語義搜尋）│                        │
│         │              └─────────────────┘                        │
│  ┌──────▼──────────────────────────────────────────┐             │
│  │            Web Viewer UI (React, port 37777)     │             │
│  └──────────────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   MCP Server (3 tools)  │
│  search / timeline /    │
│  get_observations       │
└─────────────────────────┘
```

### 執行流程圖（Execution Flowchart）

```
 Claude Code 啟動（SessionStart）
         │
         ▼
   [Setup Hook]
   smart-install.js 檢查依賴（快取）
         │
         ▼
   [Worker Service 啟動]
   bun worker-service.cjs start
         │
         ├─ Worker 已在運行 ──► 跳過
         │
         └─ 首次啟動 ──────► 啟動 HTTP API + Chroma + SQLite
                                     │
                                     ▼
   [context hook]
   GET /api/context/inject
         │
         ├─ 從 SQLite/Chroma 提取相關觀察值
         ├─ ContextBuilder 組裝成緊湊 Markdown
         └─ 注入為 additionalContext（Session 開始前）
                 │
                 ▼
   ┌─────────────────────────────────────────────┐
   │           Claude Code 對話進行中            │
   │                                             │
   │  每次工具呼叫（PostToolUse）:               │
   │  observation handler                        │
   │    → POST /api/sessions/observations        │
   │    → 儲存工具名稱、輸入、回應到 SQLite      │
   └──────────────────┬──────────────────────────┘
                      │
                      ▼
   Claude Code 停止（Stop hook）
   summarize handler
     → 從 transcript 取出最後 assistant 訊息
     → POST /api/sessions/summarize
     → Claude Agent SDK 壓縮成語意摘要
     → 存回 SQLite

   Session 結束（SessionEnd）
   session-complete handler
     → 標記 session 完成
```

### 時序圖（Sequence Diagram）

```
 Claude Code    Hook Script    Worker HTTP     SQLite/Chroma   Claude AI
     │               │              │                │             │
     │──SessionStart─►│              │                │             │
     │               │──context req─►│                │             │
     │               │              │──query history─►│             │
     │               │              │◄────results─────│             │
     │               │              │──build context──┐             │
     │               │◄──additionalContext────────────┘             │
     │◄──ctx inject──│              │                │             │
     │               │              │                │             │
     │──PostToolUse──►│              │                │             │
     │               │──POST obs────►│                │             │
     │               │              │──INSERT─────────►│             │
     │               │◄──200 OK─────│                │             │
     │               │              │                │             │
     │──Stop─────────►│              │                │             │
     │               │──POST summ───►│                │             │
     │               │              │──last message───────────────►│
     │               │              │◄──AI summary────────────────│
     │               │              │──UPDATE session─►│             │
     │               │◄──200 OK─────│                │             │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）：事件驅動（Event-Driven）+ 服務端資料處理
> Hook 腳本只做最輕量的工作（讀取輸入、HTTP 轉發），所有繁重邏輯在 Worker HTTP Service 內非同步處理，避免阻塞 Claude Code 的主要對話流程。

1. **Hook → Worker HTTP 解耦**：Hook 腳本執行時間有限制（timeout），透過 HTTP POST 將工作委派給長期運行的 Worker Service，讓複雜的 AI 壓縮作業在背景非同步完成
2. **漸進式揭露（Progressive Disclosure）**：MCP 搜尋採 3 層架構（search index → timeline → full fetch），避免一次載入大量 Token，~10x 節省 Token 成本
3. **SQLite + FTS5 + Chroma 混合搜尋（Hybrid Search）**：關鍵字搜尋（keyword search）用 SQLite FTS5，語義搜尋（semantic search）用 Chroma 向量資料庫，兩者結果合併排序
4. **Bun 作為 Worker 執行時**：選用 Bun 而非 Node.js 跑 Worker，獲得更快的啟動時間與更佳的效能
5. **Mode 系統**：允許切換不同的觀察值分類模式（code、law-study 等），每個 Mode 有自己的觀察類型（Observation Types）和跨切標籤（concepts），使記憶更結構化

### 資料流（Data Flow）

1. `PostToolUse` hook 收到工具呼叫 JSON → 去除隱私標籤 → 送到 Worker
2. Worker 儲存原始觀察值（raw observation）到 SQLite `observations` 表
3. `Stop` hook 觸發摘要：Worker 呼叫 Claude Agent SDK 將 session 壓縮成摘要
4. `SessionStart` hook 觸發上下文注入：ContextBuilder 從 SQLite + Chroma 查詢最相關的近期觀察值，組裝成壓縮 Markdown，透過 `additionalContext` 注入到 session 開頭

### 關鍵程式碼（Key Code Snippets）

**Hook 入口點（hooks.json）：**

```json
{
  "PostToolUse": [{
    "matcher": "*",
    "hooks": [{
      "type": "command",
      "command": "node \"$_R/scripts/bun-runner.js\" \"$_R/scripts/worker-service.cjs\" hook claude-code observation",
      "timeout": 120
    }]
  }],
  "Stop": [{
    "hooks": [{
      "type": "command",
      "command": "node \"$_R/scripts/bun-runner.js\" \"$_R/scripts/worker-service.cjs\" hook claude-code summarize",
      "timeout": 120
    }]
  }]
}
```

**Observation Handler（src/cli/handlers/observation.ts）核心邏輯：**

```typescript
export const observationHandler: EventHandler = {
  async execute(input: NormalizedHookInput): Promise<HookResult> {
    const workerReady = await ensureWorkerRunning();
    if (!workerReady) {
      return { continue: true, suppressOutput: true, exitCode: HOOK_EXIT_CODES.SUCCESS };
    }

    const { sessionId, cwd, toolName, toolInput, toolResponse } = input;

    // Check if project is excluded from tracking
    const settings = SettingsDefaultsManager.loadFromFile(USER_SETTINGS_PATH);
    if (isProjectExcluded(cwd, settings.CLAUDE_MEM_EXCLUDED_PROJECTS)) {
      return { continue: true, suppressOutput: true };
    }

    // Send to worker - worker handles privacy check and database operations
    const response = await workerHttpRequest('/api/sessions/observations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contentSessionId: sessionId,
        tool_name: toolName,
        tool_input: toolInput,
        tool_response: toolResponse,
        cwd
      })
    });
  }
};
```

**MCP 3 層搜尋工作流示範：**

```typescript
// Step 1: 搜尋索引（~50-100 tokens/result）
search(query="authentication bug", type="bugfix", limit=10)

// Step 2: 取得時序上下文
timeline(observation_id=123)

// Step 3: 僅對篩選後的 ID 取得完整內容（~500-1000 tokens/result）
get_observations(ids=[123, 456])
// 相較全量載入省下約 10x Token
```

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | Handler 職責清晰，Hook 只做 HTTP 轉發，Worker 處理業務邏輯，關注點分離徹底 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐ | Mode 系統支援插拔式觀察類型，已有 30+ 語言 Mode；Worker HTTP API 方便外部接入 |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐ | 有針對 SQLite、agents、search、context 的分類測試，但覆蓋率未公開 |
| 文件品質（Documentation） | ⭐⭐⭐⭐⭐ | 有獨立文件網站（docs.claude-mem.ai）、30+ 語言 README、架構演進歷史文件 |
| 依賴管理（Dependency Management） | ⭐⭐⭐ | 依賴 Bun、uv、Chroma，對非標準環境有安裝負擔；auto-install 機制降低門檻但增加啟動複雜度 |

> [!tip] 值得學習的設計
> **漸進式揭露（Progressive Disclosure）** 搜尋模式：先取 ID 索引（低 Token）→ 時序脈絡（中 Token）→ 按需載入全文（高 Token）。這個 3 層 MCP 工具設計可以直接移植到任何需要大量歷史資料查詢的 AI 應用。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> - **問題一：多重外部依賴**：必須安裝 Bun（JavaScript runtime）+ uv（Python 套件管理）+ Chroma（Python 向量資料庫）。在 Windows、受限 CI 環境中安裝可能複雜，且版本相容性難以維護 — 影響：新用戶上手體驗差，企業環境部署困難
> - **問題二：版本迭代激進**：v10.6.1 相較初版已大幅重構，CHANGELOG 中有多個 bug fix 源自架構調整帶來的破壞性變更（breaking changes） — 影響：升級風險高，需謹慎
> - **問題三：Worker 單點依賴**：所有記憶操作都通過 port 37777 的 Worker HTTP Service，若 Worker 異常崩潰，記憶功能全部降級（graceful degradation 有做，但資料可能遺漏）
> - **問題四：AGPL-3.0 授權**：商業產品若整合此插件，需要開放修改後的原始碼，使用前需確認授權相容性

### 🔮 改進建議（Improvement Suggestions）

1. **提供 Docker 化的 Worker Service**：消除 Bun + uv + Chroma 的本地安裝負擔，一鍵 `docker run` 啟動完整後端
2. **SQLite WAL mode + connection pooling**：高頻 PostToolUse hook 可能造成 SQLite 寫入競爭，考慮 WAL（Write-Ahead Logging）模式

## 效能基準（Benchmark）

> [!info] 資料來源
> 來自官方文件與 README 的定性描述，無正式第三方 benchmark 數據。

| 場景 | claude-mem | 手動 CLAUDE.md |
|------|-----------|----------------|
| Session 上下文注入 | 自動，約 2-5 秒 | 手動維護 |
| MCP 搜尋 Token 成本 | ~10x 節省（3 層搜尋） | 無搜尋能力 |
| 觀察值存儲延遲 | 非同步，不阻塞對話 | N/A |
| 上下文壓縮率 | ~53%（v10.6.1 壓縮優化） | N/A |

## 快速上手（Quick Start）

```bash
# 在 Claude Code 中安裝插件
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem

# 重啟 Claude Code，記憶系統自動啟動

# 查看記憶 Web Viewer
open http://localhost:37777

# MCP 語義搜尋（在 Claude Code 對話中使用）
# Claude 會自動使用 search / timeline / get_observations 工具查詢歷史
```

## 我的心得（My Takeaways）

- **Hook 架構的正確打開方式**：Hook 腳本只負責「接收事件 → 轉發 HTTP」，業務邏輯全在長期運行的 Worker Service 內。這個模式解決了 hook timeout 限制，也讓邏輯可以獨立測試
- **漸進式揭露是解決 Token 稀缺的優雅方案**：在 LLM 應用中，不應一次載入所有歷史資料，而應像這個 3 層搜尋架構一樣，先取 index，再按需深入
- **記憶系統的本質挑戰**：什麼該記、什麼不該記（`<private>` 標籤）、記了如何有效檢索，這些問題 claude-mem 的 Mode 系統給出了一個可實踐的答案：用結構化的觀察類型（Observation Types）來分類記憶
- 此插件即是本知識庫筆記工作流中「長期記憶插件」的提供者，參見 [[CLAUDE-CODE-SETUP]]

## 相關連結（Related）

- [[AI-AGENT-DESIGN]] — Agent 的記憶系統設計原則
- [[CLAUDE-CODE-SETUP]] — Claude Code 安裝設定（含此插件的安裝步驟）
- [[PERSONAL-KNOWLEDGE-BASE]] — 個人知識庫建立，claude-mem 的記憶與知識庫的差異與互補

## References

- [GitHub Repo](https://github.com/thedotmack/claude-mem)
- [官方文件](https://docs.claude-mem.ai/)
- [架構概覽](https://docs.claude-mem.ai/architecture/overview)
- [漸進式揭露哲學](https://docs.claude-mem.ai/progressive-disclosure)
