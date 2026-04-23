---
title: "newtype OS — 多代理人內容生產編排系統深度分析"
date: 2026-01-09
category: CodeAnalysis
tags:
  - #code-analysis
  - #typescript
  - #ai/multi-agent
  - #ai/content-production
  - #tools/cli
source: "https://github.com/newtype-01/newtype-os"
source_type: code
author: "huangyihe"
status: notes
links:
  - "[[2026-01-09-OH-MY-CLAUDECODE-MULTI-AGENT-ORCHESTRATION]]"
  - "[[2026-03-18-CLAWTEAM-AGENT-SWARM-INTELLIGENCE]]"
  - "[[2026-03-25-ENGINEERS-FUTURE-MULTI-AGENT-ERA-STEVE-YEGGE]]"
  - "[[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]]"
github_stars: 432
github_language: TypeScript
---

## 摘要（Summary）

newtype OS 是一個**8 代理人多層編排系統（8-agent multi-layer orchestration system）**，專為內容生產（Content Production）打造。它基於 [oh-my-opencode](https://github.com/code-yeongyu/oh-my-opencode)（即 [[2026-01-09-OH-MY-CLAUDECODE-MULTI-AGENT-ORCHESTRATION]] 分析過的前身）重新設計，以 OpenCode 為核心引擎，提供兩種部署方式：獨立 CLI（`@newtype-os/cli`）和 OpenCode 外掛（`@newtype-os/plugin`）。

核心概念是「**你的終端裡住著一支內容團隊**」——使用者只跟 Chief（總編輯）對話，Chief 自動拆解需求、派遣 Deputy（副主編）、再由 6 位專業代理人（Researcher、Fact-Checker、Archivist、Extractor、Writer、Editor）各司其職。系統內建 7 套專業技能框架（Skill Framework）、記憶系統（Memory System）、知識庫（Knowledge Base）、以及 WeChat 橋接整合。

版本 v0.0.24 | TypeScript | SUL-1.0 授權 | 432 ⭐ | 68,525 行程式碼

## Why — 為什麼存在？

> 這個專案要解決的根本問題是什麼？現有方案的哪些痛點促使它被創造？

- **核心動機**：傳統 AI 助手是單一代理人（Single Agent）模式，在內容生產流程（調研→分析→撰寫→查證→編輯）中容易出現上下文污染（Context Pollution）、目標漂移（Goal Drift）和品質下降（AI Slop）。newtype OS 將內容生產流程拆解為 8 個專業角色，各自擁有獨立的模型配置（Model Configuration）、工具許可（Tool Allowlist）和提示詞（Prompt），實現「計劃與執行分離（Separation of Planning and Execution）」。
- **取代/改善什麼**：相較於前身 oh-my-opencode，newtype OS 新增了獨立 CLI 部署模式、WeChat 整合、信心路由（Confidence Routing）品質把關機制、以及更成熟的記憶與知識庫系統。相較於 [[2026-03-18-CLAWTEAM-AGENT-SWARM-INTELLIGENCE|ClawTeam]] 的去中心化群智模式，newtype OS 採取中心化的階層式編排（Hierarchical Orchestration）。
- **目標用戶**：內容創作者、自媒體營運者、需要系統化產出高品質文章/研究報告的專業人士。也支援代理人呼叫代理人（Agent-for-Agents）模式，讓其他 AI 開發工具透過 `nt init` 注入技能檔案。

## What — 是什麼？

> 這個專案的功能邊界與核心能力。

- **主要功能**：
  - **8 代理人編排**：Chief → Deputy → 6 位專業代理人的分層派遣
  - **7 套技能框架**：Super Workflow、Super Analyst（12 種分析框架）、Super Writer（6 種寫作方法）、Super Fact-Checker、Super Editor（4 層編輯）、Super Interviewer、Super Obsidian
  - **Prometheus/Sisyphus 計劃-執行分離**：Prometheus 做策略規劃（唯讀）、Sisyphus 做執行派遣
  - **信心路由（Confidence Router）**：根據代理人輸出的信心分數自動決定 pass/polish/rewrite/escalate
  - **記憶系統**：自動生成每日摘要、完整逐字稿保存、7 天自動歸檔長期記憶
  - **知識庫**：`/init` 產生 `AGENTS.md`、`/init-deep` 產生 `KNOWLEDGE.md` 深度代碼索引
  - **WeChat 整合**：透過 WeClaw + ACP 協定橋接 WeChat 訊息到代理人團隊
  - **CLI 命令**：`nt research`、`nt write`、`nt edit`、`nt pipeline` 等支援 `--json` 輸出
- **不做什麼（Non-goals）**：不是通用程式碼生成工具，不直接寫程式碼——聚焦於內容生產領域
- **技術棧（Tech Stack）**：TypeScript、Bun（執行環境與套件管理）、OpenCode SDK（`@opencode-ai/sdk`）、OpenCode Plugin API（`@opencode-ai/plugin`）、Commander（CLI）、Hono（HTTP 框架）、Zod v4（Schema 驗證）、MCP SDK（`@modelcontextprotocol/sdk`）

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                         │
│              TUI (nt) │ CLI Commands │ WeChat               │
└────────────┬──────────┴──────────────┴──────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│                    Chief (總編輯)                            │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │ Thought      │  │ Execution     │  │ Confidence      │  │
│  │ Partner Mode │  │ Coordinator   │  │ Router          │  │
│  └──────────────┘  └───────┬───────┘  └─────────────────┘  │
│   (探索想法)              │           (品質把關)            │
└───────────────────────────┼─────────────────────────────────┘
                            │ chief_task
┌───────────────────────────▼─────────────────────────────────┐
│                   Deputy (副主編)                            │
│  直接執行簡單任務 (edit/write/bash)                         │
│  或派遣專業代理人 ↓                                        │
└──┬──────┬──────┬──────┬──────┬──────┬───────────────────────┘
   │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼
┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐
│Rsrch││F.Chk││Archv││Extr ││Write││Edit │
│研究 ││查證 ││歸檔 ││擷取 ││撰寫 ││編輯 │
└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘
   │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  Exa Search │ Tavily │ Firecrawl │ Context7 │ MCP Servers   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Persistence Layer                         │
│  Memory System          │ Knowledge Base    │ Boulder State  │
│  .newtype/memory/       │ AGENTS.md         │ boulder.json   │
│  MEMORY.md (長期)       │ KNOWLEDGE.md      │ (執行進度)     │
└─────────────────────────────────────────────────────────────┘
```

### 執行流程圖（Execution Flowchart）

```
 User 輸入任務
   │
   ▼
[Chief 接收] ──判斷模式──┐
   │                      │
   │ Mode 1               │ Mode 2
   │ Thought Partner       │ Execution Coordinator
   │ (探索/辯論)           │
   │                      ▼
   │              [Chief 拆解任務]
   │                      │
   │              ┌───────▼───────┐
   │              │ chief_task()  │
   │              │ → Deputy      │
   │              └───────┬───────┘
   │                      │
   │              ┌───────▼───────────────┐
   │              │ Deputy 判斷            │
   │              ├─ 簡單? → 直接執行      │
   │              └─ 複雜? → 派遣專業 Agent│
   │                      │
   │              ┌───────▼───────┐
   │              │ 專業 Agent    │
   │              │ 執行並回報    │
   │              └───────┬───────┘
   │                      │
   │              ┌───────▼───────────┐
   │              │ Confidence Router │
   │              ├─ ≥0.8 → pass     │
   │              ├─ ≥0.5 → polish   │
   │              ├─ <0.5 → rewrite  │
   │              └─ 超過上限 → escalate
   │                      │
   └──────────────────────▼
              [結果回報 User]
```

### 時序圖（Sequence Diagram）

```
 User        Chief       Deputy      Researcher    Writer      Editor
   │           │            │            │            │           │
   │──任務────►│            │            │            │           │
   │           │──拆解──────►│            │            │           │
   │           │            │──調研──────►│            │           │
   │           │            │◄──素材──────│            │           │
   │           │            │──撰寫───────────────────►│           │
   │           │            │◄──初稿──────────────────│           │
   │           │            │──編輯──────────────────────────────►│
   │           │            │◄──定稿─────────────────────────────│
   │           │◄──匯總──────│            │            │           │
   │◄──結果────│            │            │            │           │
```

### Prometheus/Sisyphus 計劃-執行分離時序圖

```
 User       Prometheus    Metis       Sisyphus     Agents
   │           │            │            │            │
   │──/plan───►│            │            │            │
   │           │──訪談──────►│            │            │
   │           │◄──缺口分析──│            │            │
   │           │──生成計劃──►│            │            │
   │           │  (.sisyphus/plans/)     │            │
   │◄──計劃────│            │            │            │
   │                                     │            │
   │──/start-work───────────────────────►│            │
   │                                     │──讀計劃────│
   │                                     │──派遣──────►│
   │                                     │◄──結果──────│
   │◄──完成──────────────────────────────│            │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> 採用**階層式編排（Hierarchical Orchestration）**模式：Chief → Deputy → Specialists，而非扁平式（Flat）或去中心化（Decentralized）群智模式。這讓任務分配更可預測，但也帶來單點瓶頸風險。

1. **計劃-執行分離（Separation of Planning and Execution）**：Prometheus（計劃者）是唯讀的，只能建立 Markdown 計劃檔在 `.sisyphus/` 目錄；Sisyphus（執行者）負責實際操作。這避免了「邊想邊做」導致的上下文污染（Context Pollution）。
2. **信心路由（Confidence Router）**：每個代理人輸出中解析 `**CONFIDENCE: X.XX**` 格式的信心分數，根據閾值（threshold）決定 pass（≥0.8）、polish（≥0.5）、rewrite（<0.5），超過最大重寫次數則 escalate。支援按代理人類型設定不同閾值。
3. **品質維度（Quality Dimensions）**：除了信心分數，另有多維品質評分系統，用於更細粒度的品質把關與改善指引。
4. **OpenCode Plugin 架構**：整個系統作為 OpenCode 的外掛（Plugin）實現，利用 OpenCode 的 session 管理、工具系統和 hook 生命週期。每個 hook 都可獨立啟用/停用。
5. **Chief 的雙模式設計**：Chief 不只是任務分派器，也是**思考夥伴（Thought Partner）**——使用者想探索想法時，Chief 會挑戰邏輯、辯論觀點，而非被動接受指令。

### 資料流（Data Flow）

1. 使用者輸入 → Chief 的 `chat.message` hook 接收
2. Chief 透過 `chief_task` 工具呼叫 Deputy（建立新 session）
3. Deputy 判斷任務性質，直接執行或派遣專業 Agent（同樣透過 `chief_task` + `subagent_type`）
4. 專業 Agent 執行任務，輸出包含信心分數
5. Chief Orchestrator hook 攔截 `tool.execute.after`，解析信心分數，決定路由
6. 結果透過 `output-summarizer` 摘要後回傳 Chief
7. Chief 匯整後回覆使用者
8. Memory System hook 在 session 閒置後自動生成摘要存入 `.newtype/memory/`

### 關鍵程式碼（Key Code Snippets）

**插件入口點 — 完整的 hook 與 tool 組裝（`src/index.ts`）：**

```typescript
const OhMyOpenCodePlugin: Plugin = async (ctx) => {
  startTmuxCheck();
  const pluginConfig = loadPluginConfig(ctx.directory, ctx);
  const disabledHooks = new Set(pluginConfig.disabled_hooks ?? []);
  const isHookEnabled = (hookName: HookName) => !disabledHooks.has(hookName);

  // ... 30+ hooks 逐一初始化 ...

  return {
    tool: {
      ...builtinTools,
      ...backgroundTools,
      look_at: lookAt,
      chief_task: chiefTask,
      skill: skillTool,
      skill_mcp: skillMcpTool,
      slashcommand: slashcommandTool,
      interactive_bash,
    },
    "chat.message": async (input, output) => { /* ... */ },
    "tool.execute.before": async (input, output) => { /* ... */ },
    "tool.execute.after": async (input, output) => { /* ... */ },
    event: async (input) => { /* ... */ },
  };
};
```

**Chief 工具許可清單 — 嚴格限制 Chief 只能透過 `chief_task` 執行（`src/agents/chief.ts`）：**

```typescript
const CHIEF_ALLOWED_TOOLS = [
  "chief_task",       // 唯一的執行路徑
  "todowrite", "todoread",  // 任務管理
  "read", "glob", "grep",   // 只讀理解
  "lsp_hover", "lsp_goto_definition", // LSP 只讀
  "session_list", "session_read",      // Session 回顧
  "skill", "slashcommand",            // Skills/Commands
];
```

**信心路由核心邏輯（`src/hooks/chief-orchestrator/confidence-router.ts`）：**

```typescript
export function getRecommendation(
  confidence: number,
  agentType?: AgentType
): "pass" | "polish" | "rewrite" {
  const thresholds = agentType
    ? getThresholdsForAgent(agentType)
    : { pass: 0.8, polish: 0.5 };

  if (confidence >= thresholds.pass) return "pass";
  else if (confidence >= thresholds.polish) return "polish";
  return "rewrite";
}
```

## 安裝流程（Installation Flow）

> [!info] 追蹤層級
> 本節追蹤到**具體檔案路徑**，而非停在概念層。讀者應能根據本節直接找到安裝後的產物。

### 安裝觸發方式

```
npm install -g @newtype-os/cli  → 全域安裝 CLI
nt                              → 啟動 TUI
nt init                         → 偵測本地 AI 工具，注入技能檔案

bun add @newtype-os/plugin      → 安裝為 OpenCode 外掛
opencode                        → 透過 OpenCode 啟動
```

### 安裝時序圖

```
 User         npm/bun          CLI Binary       Target System
   │              │                │                 │
   │──install ───►│                │                 │
   │              │──下載套件─────►│                 │
   │              │                │──寫入 CLI ──────►│ (global bin: nt)
   │◄─────────────│                │                 │
   │                               │                 │
   │──nt init ────────────────────►│                 │
   │                               │──偵測工具 ──────►│ 掃描 Claude Code,
   │                               │                 │ Cursor, Copilot 等
   │                               │──注入技能檔 ────►│ .claude/skills/,
   │                               │                 │ .cursor/rules/ 等
   │◄──────────────────────────────│                 │
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.config/newtype/newtype-profile.json` | 檔案 | CLI 模式全域設定（代理人模型、啟用/停用功能） |
| `~/.config/opencode/newtype-profile.json` | 檔案 | Plugin 模式全域設定 |
| `.newtype/` | 目錄 | 專案級設定、記憶、計劃（CLI 模式） |
| `.opencode/` | 目錄 | 專案級設定（Plugin 模式） |
| `.newtype/SOUL.md` | 檔案 | Chief 人格自訂檔 |
| `.newtype/memory/` | 目錄 | 每日摘要 `YYYY-MM-DD.md` 與完整逐字稿 |
| `.newtype/MEMORY.md` | 檔案 | 長期記憶歸檔 |
| `.sisyphus/plans/` | 目錄 | Prometheus 產生的執行計劃 |
| `.chief/plans/` | 目錄 | Chief 的任務計劃 |

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| 模型 Provider API Keys | 各 provider 的 API key | 透過 `nt auth login` 或 `/connect` 設定 |

> [!warning] 解除安裝
> CLI 模式：`npm uninstall -g @newtype-os/cli`，需手動清理 `~/.config/newtype/`。
> Plugin 模式：在 `~/.config/opencode/` 中 `bun remove @newtype-os/plugin` 並從 `opencode.json` 移除 `"newtype-profile"`。
> 專案級資料：手動刪除 `.newtype/`、`.sisyphus/`、`.chief/` 目錄。

---

## 使用案例地圖（Use Case Map）

> [!important] 本節針對每個主要使用案例，追蹤從**用戶觸發**到**最終效果**的完整檔案路徑。

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 端到端內容 Pipeline | `nt pipeline "topic"` | `src/cli/index.ts` | CLI → Deputy → Researcher → Writer → Fact-Checker → Editor |
| 2 | 深度研究 | `nt research "topic"` | `src/cli/index.ts` | CLI → Researcher + Fact-Checker |
| 3 | 互動思考夥伴 | TUI 中直接對話 | `src/agents/chief.ts` | Chief (Thought Partner Mode) |
| 4 | 計劃-執行工作流 | `/plan` → `/start-work` | `src/hooks/prometheus-md-only/` | Prometheus → Sisyphus → Agents |
| 5 | WeChat 橋接 | `nt wechat start` | `src/cli/index.ts` | WeClaw → ACP → Chief |
| 6 | 知識庫初始化 | `nt init` / `/init-deep` | `src/tools/knowledge-base/` | 掃描專案結構 → 產生 AGENTS.md / KNOWLEDGE.md |

### 案例詳解

#### 案例 1：端到端內容 Pipeline

```
User：nt pipeline "The future of MCP" --style essay --output-dir ./output/
  │
  ▼
src/cli/index.ts: program.command("pipeline")
  │
  ▼
src/cli/run/runner.ts  ── 建立 session ──► OpenCode SDK
  │
  ▼
Chief (chief.ts)  ── chief_task() ──► Deputy (deputy.ts)
  │
  ├─ Deputy 派遣 Researcher  ──► 外部搜索 (Exa/Tavily/Firecrawl)
  │   └── 回傳素材 + CONFIDENCE score
  │
  ├─ Deputy 派遣 Writer      ──► 根據素材撰寫初稿
  │   └── 回傳草稿 + CONFIDENCE score
  │
  ├─ Deputy 派遣 Fact-Checker ──► 查證事實與來源
  │   └── 回傳驗證報告 + CONFIDENCE score
  │
  └─ Deputy 派遣 Editor       ──► 4 層編輯（結構→段落→句→詞）
      └── 回傳定稿
  │
  ▼
Confidence Router 逐步品質把關
  │
  ▼
輸出：./output/ 目錄下的完成文章
```

#### 案例 4：Prometheus/Sisyphus 計劃-執行工作流

```
User：/plan "重構認證系統到 NextAuth"
  │
  ▼
src/hooks/prometheus-md-only/index.ts  ── 確保 Prometheus 唯讀
  │
  ▼
Prometheus (plannerAgent)  ── 訪談模式
  │
  ├─ 收集需求 → .sisyphus/drafts/
  ├─ 諮詢 Metis → 缺口偵測
  └─ 生成計劃 → .sisyphus/plans/{name}.md
  │
  ▼
User：/start-work
  │
  ▼
src/features/boulder-state/  ── 建立 boulder.json 追蹤狀態
  │
  ▼
Sisyphus  ── 讀取計劃 → 逐一執行 TODO
  │
  ├─ 派遣 Frontend Agent
  ├─ 派遣 Oracle Agent
  └─ 直接執行簡單任務
  │
  ▼
完成（boulder.json 記錄進度，可跨 session 續接）
```

> [!note] 閱讀建議
> 若要快速驗證某功能，從「入口檔案」欄直接跳去讀對應的源碼最有效率。Chief 的核心在 `src/agents/chief.ts`，編排邏輯在 `src/hooks/chief-orchestrator/`。

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐ | 每個 hook 獨立模組化，可個別啟用/停用；但 30+ hooks 的初始化邏輯集中在 `src/index.ts` 略顯臃腫 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐⭐ | 新增代理人只需在 `src/agents/` 建立檔案並加入 `builtinAgents`；新增 hook 同理 |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐⭐ | 大量 `.test.ts` 檔案涵蓋 hooks、tools、shared utilities |
| 文件品質（Documentation） | ⭐⭐⭐⭐ | README 完整、有 orchestration-guide.md 架構文件、CONTRIBUTING.md 清晰 |
| 依賴管理（Dependency Management） | ⭐⭐⭐ | 依賴 OpenCode SDK/Plugin 版本耦合較緊，之前有過 workspace 版本號 bug（v0.0.11 修復） |

> [!tip] 值得學習的設計
> 1. **信心路由（Confidence Router）**是多代理人系統的品質保障典範——不盲目信任代理人輸出，用量化分數決定後續動作。
> 2. **hook 可停用設計**：`disabled_hooks` 讓使用者能精細控制行為，避免「全有或全無」。
> 3. **Chief 的雙模式**：Thought Partner + Execution Coordinator 讓系統既能探索也能執行，使用體驗遠超純粹的任務分派器。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> 架構層面的問題或技術債（Technical Debt）。

- **`src/index.ts` 膨脹**：500+ 行的 plugin 初始化函式，30+ hooks 逐一手動組裝，新增 hook 必須修改此檔案。影響：增加貢獻者的認知負擔。
- **OpenCode 耦合**：深度依賴 `@opencode-ai/plugin` 和 `@opencode-ai/sdk` 的內部 API（session、message、tool 生命週期），若 OpenCode 做破壞性更新則全面受影響。影響：上游版本鎖定風險。
- **SUL-1.0 授權限制**：Sustainable Use License 非 OSI 認證的開源授權，限制商業使用者的部署自由度。影響：企業採用門檻較高。
- **中文提示詞硬編碼**：Deputy、部分 Agent 的 system prompt 以中文撰寫（如 `"副主编，Chief 的执行层"`），非中文使用者的體驗可能受影響。

### 🔮 改進建議（Improvement Suggestions）

1. **Hook 註冊機制**：將 `src/index.ts` 的手動 hook 組裝改為自動掃描或註冊表模式，減少重複樣板程式碼
2. **OpenCode 抽象層**：在 OpenCode SDK 之上建立薄抽象層，降低直接耦合
3. **提示詞國際化（i18n）**：將中文 system prompt 抽出為可替換的語言套件

## 效能基準（Benchmark）

> [!info] 資料來源
> 無公開 benchmark 數據。以下為架構層面的效能特性分析。

| 場景 | 效能特性 | 瓶頸 |
|------|---------|------|
| 單次內容 Pipeline | 依序經過 4-6 個 Agent，每個 Agent 是獨立 LLM 呼叫 | 總延遲 = 各 Agent 延遲之和（非平行） |
| Confidence Router 觸發 rewrite | 最多 2 次重寫（`DEFAULT_MAX_REWRITE_ATTEMPTS`），再失敗則 escalate | 最差情況下延遲 ×3 |
| 記憶歸檔 | 7 天觸發一次，透過 Archivist Agent 做 LLM 摘要 | 大量歷史記憶時摘要耗時 |

## 快速上手（Quick Start）

```bash
# 方式一：獨立 CLI（推薦）
npm install -g @newtype-os/cli
nt                    # 啟動 TUI，使用 /connect 連接模型
nt init               # 初始化專案（偵測本地 AI 工具並注入技能）

# 方式二：OpenCode Plugin
cd ~/.config/opencode
bun add @newtype-os/plugin
# 編輯 opencode.json 加入 "plugin": ["newtype-profile"]
opencode

# 使用 CLI 命令
nt research "AI Agent architecture trends 2026" -o research.md
nt pipeline "The future of MCP" --style essay --output-dir ./output/
```

## 我的心得（My Takeaways）

- **信心路由是多代理人品質控制的實用模式**：比起單純信任每個 Agent 的輸出，用量化的信心分數 + 閾值路由來自動決定「通過/潤色/重寫/升級」，是一個值得在自己的代理人系統中採用的設計。
- **計劃-執行分離的價值**：Prometheus 唯讀、Sisyphus 執行的設計，從架構上杜絕了「邊想邊做」的問題。這對任何需要多步驟執行的代理人系統都是好的實踐。
- **從 oh-my-opencode 到 newtype OS 的演進**：相較於 [[2026-01-09-OH-MY-CLAUDECODE-MULTI-AGENT-ORCHESTRATION|前身 oh-my-opencode]]，newtype OS 在品質控制（Confidence Router）、記憶系統、獨立部署方面都有顯著進步，代表了 OpenCode 生態系外掛的成熟方向。
- **Hook 系統的設計權衡**：30+ hooks 每個都可獨立啟停是很好的，但全部手動組裝在一個大函式裡是典型的 "configuration over convention" 取捨。

## 待補充（Open Questions）

- Prometheus/Sisyphus 在跨 session 續接時，boulder.json 的狀態恢復機制是否可靠？有哪些邊界情況（edge case）可能導致狀態遺失？（建議搜尋：`boulder state recovery multi-session`）
- 信心路由的閾值（0.8/0.5）是如何決定的？有沒有基於實際產出品質的調參（tuning）數據？（建議搜尋：`confidence threshold calibration multi-agent`）
- WeChat 整合透過 WeClaw + ACP 協定運作，WeClaw 的安全模型（Security Model）是什麼？是否有訊息加密或權限控制？（建議搜尋：`weclaw acp protocol security`）
- 多個代理人同時執行時的 token 消耗量如何？一次完整 Pipeline 大約需要多少 token？有沒有成本優化策略？（建議搜尋：`multi-agent llm token cost optimization`）
- `@opencode-ai/plugin` 的版本穩定性如何？OpenCode SDK 是否有向後相容（Backward Compatibility）承諾？（建議搜尋：`opencode sdk versioning policy`）

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 8 代理人角色（Chief/Deputy/Researcher/Fact-Checker/Archivist/Extractor/Writer/Editor）；信心路由閾值（pass≥0.8, polish≥0.5, rewrite<0.5）；Prometheus 唯讀、Sisyphus 執行；7 套技能框架名稱 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | newtype OS 的核心論點是「計劃與執行分離」可以解決單一代理人的上下文污染問題。Chief 不只是路由器而是思考夥伴，Deputy 是判斷層（簡單自己做、複雜才派遣），Confidence Router 是品質閘門。三者形成「對話→決策→執行→品控」的完整迴路 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 關鍵假設：(1) 階層式編排優於扁平式——但當任務高度平行時，層級開銷可能反而拖慢速度；(2) 信心分數是可靠的品質代理指標——但 LLM 自我評估的校準性（calibration）已知存在問題；(3) 中文 prompt 不影響多語系使用——但 Deputy 的中文指令可能在非中文模型上產生不預期行為 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | (1) 在自己的多代理人系統中引入 Confidence Router 機制，對每個 Agent 輸出解析信心分數並自動路由；(2) 將 Prometheus/Sisyphus 的計劃-執行分離模式應用於 ConnSys Jarvis 的任務編排 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | 與 [[2026-03-18-CLAWTEAM-AGENT-SWARM-INTELLIGENCE|ClawTeam]] 比較：newtype OS 的階層式編排在品質控制上更強（有 Confidence Router），但靈活性較差（新增角色需要修改 Deputy 的派遣邏輯）。與前身 oh-my-opencode 比較：品質控制和記憶系統有實質進步，但從 Claude Code 轉向 OpenCode 平台可能失去部分 Claude Code 生態的使用者 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「信心分數」到底由誰計算？是 Agent 自評還是有獨立的評估者？若是自評，「信心」的定義在不同 Agent 間是否一致？
- **假設**：計劃-執行分離成立的前提是「好的計劃可以被忠實執行」。若 Sisyphus 在執行中發現計劃有缺陷，回饋機制是什麼？是否支援計劃修訂？
- **證據**：432 stars 和 72 forks 代表一定的社群認可，但缺乏使用者的品質產出比較數據。「8 代理人比 1 個好」的主張需要實證支持。
- **觀點**：反對者會說：多代理人系統的 token 成本是單一代理人的數倍，而品質提升可能不成比例。何時「直接用好模型單次呼叫」比「用一般模型多次呼叫」更有效率？
- **後果**：若依照 newtype OS 的模式建構內容生產工作流，12 個月後可能面對：(1) OpenCode SDK 破壞性更新導致全面重構；(2) 模型能力提升讓部分角色冗餘（如 Fact-Checker 若模型本身就更準確）

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — OpenCode 平台耦合風險。newtype OS 深度依賴 `@opencode-ai/plugin` 的 session、tool、hook 生命週期 API。若 OpenCode 停止維護或做不相容更新，整個系統需要大幅重寫。這不是假設性風險——v0.0.11 已經出現過 workspace 版本依賴 bug。
2. **什麼情況下會失敗？** — (1) 快速迭代的小型內容需求（一條社群貼文），8 代理人 Pipeline 的延遲和成本過高；(2) 高度技術性的內容（如韌體分析報告），通用的 Writer/Editor Agent 可能不如領域專家的單一 prompt；(3) 網路不穩定時，多次 LLM API 呼叫的失敗率累積。
3. **有沒有更好的替代方案？** — 若需求是「高品質內容生產」，替代方案包括：(a) Claude Code + 自定義 Skills（更輕量，不需要額外平台）；(b) [[2026-03-18-CLAWTEAM-AGENT-SWARM-INTELLIGENCE|ClawTeam]]（去中心化模式，適合可平行拆解的研究任務）；(c) 直接使用頂級模型（如 Claude Opus）的長 prompt + 結構化輸出，在模型足夠強時可能比多代理人更高效。選擇 newtype OS 的理由是：當內容生產需要**標準化流程**且**品質把關不可省略**時。

## 相關連結（Related）

- [[2026-01-09-OH-MY-CLAUDECODE-MULTI-AGENT-ORCHESTRATION]] — newtype OS 的前身，基於 oh-my-opencode（原名 oh-my-claudecode）的多代理人編排系統
- [[2026-03-18-CLAWTEAM-AGENT-SWARM-INTELLIGENCE]] — 另一種多代理人協調模式：去中心化群智 vs newtype OS 的階層式編排
- [[2026-03-25-ENGINEERS-FUTURE-MULTI-AGENT-ERA-STEVE-YEGGE]] — Steve Yegge 對多代理人時代工程師角色的思考，呼應 newtype OS「Agent-for-Agents」的設計方向
- [[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]] — AI Agent 從教學到實戰的痛苦教訓，可對照 newtype OS 的信心路由設計
- [[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]] — 另一個 AI 工具整合框架的設計哲學比較

## References

- [GitHub Repo](https://github.com/newtype-01/newtype-os)
- [npm: @newtype-os/cli](https://www.npmjs.com/package/@newtype-os/cli)
- [npm: @newtype-os/plugin](https://www.npmjs.com/package/@newtype-os/plugin)
- [huangyihe Twitter](https://x.com/huangyihe)
- [newtype.pro (Substack)](https://newtype.pro/)
- [oh-my-opencode (上游)](https://github.com/code-yeongyu/oh-my-opencode)
