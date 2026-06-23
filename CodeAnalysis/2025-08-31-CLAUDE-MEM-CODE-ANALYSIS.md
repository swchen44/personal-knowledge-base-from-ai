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

## 待補充（Open Questions）

- claude-mem 使用 Chroma 作為向量資料庫進行語義搜尋，但 Chroma 需要本地安裝 Python 環境。在沒有 Python 的純 Node.js 開發環境中，是否有替代的向量搜尋方案（如 sqlite-vec 或 pgvector）？（建議搜尋：`sqlite-vec nodejs vector search alternative chromadb`）
- ContextBuilder 從 SQLite 與 Chroma 組裝出的「壓縮 Markdown」注入到 session 開頭，這個壓縮格式的品質如何評估？是否有方法測量注入後 Claude 的記憶準確率（recall accuracy）？（建議搜尋：`LLM context injection quality evaluation memory recall`）
- claude-mem 的 AGPL-3.0 授權對企業內部工具的使用限制具體是什麼？若公司內部自用（不對外發布）是否仍需要開源修改部分？（建議搜尋：`AGPL-3.0 license internal use commercial implications`）
- Worker Service 以單一 HTTP Port（37777）為中心，若多個 Claude Code 工作視窗同時執行（multi-session）會發生什麼？是否有 session 隔離機制？（建議搜尋：`claude-mem multi-session support worker service port conflict`）
- 記憶壓縮率宣稱 ~53%（v10.6.1），這個壓縮是由哪個 Claude 模型執行的？壓縮過程本身的 API 費用是否顯著？（建議搜尋：`claude-mem summarization cost API tokens compression model`）

## 相關連結（Related）
- [[2026-06-24-CODEBASE-MEMORY-MCP-PRO-VS-CODEGRAPH-CODE-KNOWLEDGE-GRAPH-COMPARISON]] — 同為代理記憶／檢索類工具，可對照向量記憶 vs 程式碼圖譜路線

- [[AI-AGENT-DESIGN]] — Agent 的記憶系統設計原則
- [[CLAUDE-CODE-SETUP]] — Claude Code 安裝設定（含此插件的安裝步驟）
- [[PERSONAL-KNOWLEDGE-BASE]] — 個人知識庫建立，claude-mem 的記憶與知識庫的差異與互補
- [[2026-04-24-CLAUDE-MEM-V12-PERSISTENT-MEMORY-PLUGIN-DEEP-DIVE]] — 同一 repo v12.3.9 版本的最新深度分析，含完整架構圖與安裝流程追蹤
- [[2026-05-17-GBRAIN-EVALS-VS-JARVIS-EVAL-METHODOLOGY]] — gbrain 與 claude-mem 同為 persistent memory 但設計取向不同：gbrain 走 PGLite + 知識圖層 + multi-adapter eval，claude-mem 走 6 hooks + Agent SDK 壓縮

## References

- [GitHub Repo](https://github.com/thedotmack/claude-mem)
- [官方文件](https://docs.claude-mem.ai/)
- [架構概覽](https://docs.claude-mem.ai/architecture/overview)
- [漸進式揭露哲學](https://docs.claude-mem.ai/progressive-disclosure)

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 6 個生命週期鉤子（PostToolUse、Stop、SessionStart 等）；SQLite FTS5 + Chroma 混合搜尋；Bun 作為 Worker 執行時；MCP 3 層搜尋工具（search / timeline / get_observations）；port 37777 的 Worker HTTP API；`<private>` 隱私標籤；38,509 顆 GitHub Stars；AGPL-3.0 授權 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | claude-mem 的核心洞察是「Hook 腳本只做 HTTP 轉發，所有複雜邏輯交由長期運行的 Worker Service 非同步處理」，這解決了 Hook timeout 限制問題。3 層搜尋架構（index → timeline → full fetch）實現漸進式揭露，以約 10x 的 Token 節省為代價換取可擴展的記憶查詢能力。SQLite FTS5 + Chroma 的混合搜尋策略同時覆蓋關鍵字精確比對與語意相似度查詢兩種需求。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | ①「Worker Service 作為唯一入口」隱含單點失敗風險，若 port 37777 崩潰，所有記憶功能降級；②「AI 壓縮摘要品質等同原始 context」是核心假設，但 Claude Agent SDK 的壓縮模型本身可能引入資訊失真，且壓縮品質未有量化評估方法；③Chroma 依賴 Python 環境打破了「純 TypeScript 工具」的簡潔假設，在 CI/CD 環境安裝複雜度顯著增加 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | ①在自己的 Claude Code 設定中安裝此插件，解決跨 session 的專案上下文遺失問題；②借鑑 3 層 MCP 工具設計模式，在任何需要大量歷史資料查詢的 AI 應用中實作漸進式揭露；③用 `<private>` 標籤保護 API key、密碼等敏感資訊不被記入記憶系統 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | claude-mem 的 3 層搜尋架構在 Token 效率上優於直接載入全部 context；但 Bun + uv + Chroma 三個額外依賴使安裝複雜度顯著高於 Claude Memory Engine（零依賴方案）。AGPL-3.0 授權在企業環境是阻礙，個人使用不受影響。相較於 claude-memory-engine 的純 Markdown 方案，claude-mem 提供更強大的語意搜尋但代價是更高的安裝門檻與更低的透明度。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：claude-mem 的 Worker Service 在 MacBook 上以常駐程式形式運行，若電腦睡眠後喚醒，Worker 是否能自動恢復連線？重啟後 port 37777 的佔用狀態如何處理？
- **假設**：系統假設 Claude Agent SDK 的壓縮摘要能保留 session 中最重要的技術決策細節，但 LLM 壓縮天然傾向保留語意而非細節。若一個 session 包含關鍵的 edge case 處理邏輯，壓縮後是否可能丟失？
- **證據**：文件宣稱「上下文壓縮率 ~53%（v10.6.1）」，但這個指標僅反映字元數壓縮，而非資訊保留率。是否有方法測量「Claude 在注入記憶後對 2 周前問題的回答準確率」？
- **觀點**：從系統管理員角度，AGPL-3.0 授權意味著若企業內部修改並部署此插件，需要開放修改後的原始碼。這與企業通常的「內部工具不外洩」政策相衝突，應如何評估採用風險？
- **後果**：若 claude-mem 的版本迭代引入 breaking changes（已有多次），且 Worker Service 的資料格式改變，舊有的記憶資料是否會自動遷移？若不，累積幾個月的記憶可能一次性全部失效。

### 方案批判三問（Critical Evaluation）

> [!warning] 適用於技術方案類內容

1. **最大的風險是什麼？** — Worker Service 的單點依賴是最大風險：所有記憶操作（觀察值儲存、摘要生成、上下文注入）都必須通過 port 37777 的 HTTP Service。若 Bun 執行時崩潰、port 被佔用、或 Chroma 資料庫損毀，整個記憶系統靜默失效，使用者可能在毫不知情的情況下損失數週的 session 記憶。
2. **什麼情況下會失敗？** — ①多個 Claude Code 工作視窗同時執行時，session 隔離機制是否完備，同一個 Worker Service 能否正確區分來自不同視窗的觀察值；②Python 環境（uv）或 Chroma 版本升級後與舊資料格式不相容，語意搜尋功能靜默降級為僅關鍵字搜尋；③在記憶量大時（1000+ sessions），SQLite 查詢效能下降，Session 開始時的 2-5 秒注入時間拉長至分鐘級
3. **有沒有更好的替代方案？** — ①若注重簡單與透明：Claude Memory Engine（零依賴、純 Markdown、Hook-driven）更易審計和自定義，代價是無語意搜尋；②若注重企業級部署：將 Worker Service Docker 化，用 PostgreSQL + pgvector 取代 SQLite + Chroma，消除本地安裝問題；③若只需要基礎跨 session 記憶：直接用 CLAUDE.md 手動記錄關鍵決策，零依賴，完全透明
