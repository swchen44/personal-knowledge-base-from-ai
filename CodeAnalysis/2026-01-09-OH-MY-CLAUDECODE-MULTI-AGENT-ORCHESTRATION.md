---
title: "oh-my-claudecode — Claude Code 多代理人編排系統深度分析"
date: 2026-01-09
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#typescript"
  - "#ai/agents"
  - "#tools/cli"
  - "#ai/llm"
source: "https://github.com/Yeachan-Heo/oh-my-claudecode"
source_type: code
author: "Yeachan-Heo"
status: notes
links:
  - "[[CLAUDE-CODE-HOOKS]]"
  - "[[MULTI-AGENT-ORCHESTRATION]]"
  - "[[MCP-MODEL-CONTEXT-PROTOCOL]]"
github_stars: 13861
github_language: TypeScript
---

## 摘要（Summary）

oh-my-claudecode（簡稱 OMC）是一個 Claude Code 的多代理人編排（Multi-agent Orchestration）外掛，版本 v4.9.1，標榜「零學習曲線（Zero Learning Curve）」。它透過自然語言魔術關鍵字（Magic Keywords）、技能（Skills）系統、Hooks 生命週期事件（Lifecycle Events）和 19 個專業代理人（Specialized Agents），讓 Claude Code 自動拆解複雜任務、平行執行（Parallel Execution）、持續驗證直到完成。在 GitHub 已獲得 13,861 顆星（Stars）。

---

## Why — 為什麼存在？

> 這個專案要解決的根本問題是什麼？

- **核心動機**：Claude Code 本身缺乏原生的多代理人協調介面，使用者需要手動拆解任務、管理代理人狀態、處理失敗重試，學習曲線陡峭。
- **取代/改善什麼**：取代手動提示工程（Prompt Engineering）和腳本式工作流，讓複雜的架構/實作/測試/審查流程一鍵觸發。
- **目標用戶**：使用 Claude Code 的中高階工程師，想要自動化多步驟開發任務（如完整功能開發、代碼審查、重構、除錯）。

---

## What — 是什麼？

### 主要功能

- **Team 編排**：staged pipeline（`team-plan → team-prd → team-exec → team-verify → team-fix`），N 個代理人共享任務清單
- **魔術關鍵字（Magic Keywords）**：在提示（Prompt）中輸入關鍵字自動觸發對應工作流（如 `ralph`、`autopilot`、`ulw`、`ralplan`）
- **技能系統（Skills）**：可組合的行為注入（Behavior Injection），支援專案級（`.omc/skills/`）和使用者級（`~/.omc/skills/`）技能
- **Hooks 生命週期**：12 個 Hook 事件點介入 Claude Code 工作流（UserPromptSubmit、PreToolUse、Stop 等）
- **19 個專業代理人（Specialized Agents）**：依複雜度分為 Haiku/Sonnet/Opus 三層
- **HUD 狀態列（HUD Statusline）**：即時顯示代理人狀態與 token 用量
- **tmux CLI 工作者**：支援在 tmux 分割視窗中平行啟動 Codex CLI、Gemini CLI 工作者

### 技術棧（Tech Stack）

| 層次 | 技術 |
|------|------|
| 核心語言 | TypeScript 5.7 + Node.js ≥20 |
| 代理人 SDK | `@anthropic-ai/claude-agent-sdk` |
| MCP 伺服器 | `@modelcontextprotocol/sdk` |
| 程式碼智能（Code Intelligence） | `@ast-grep/napi`、`vscode-languageserver-protocol` |
| 資料庫 | `better-sqlite3`（工作階段（Session）持久化） |
| 建置工具 | esbuild、vitest |
| CLI 框架 | commander.js |

---

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌──────────────────────────────────────────────────────────────────┐
│                     OH-MY-CLAUDECODE (OMC)                        │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     用戶介面層                              │  │
│  │  Claude Code CLI → /team、/setup、/omc-setup、/autopilot   │  │
│  │  魔術關鍵字：ralph、ulw、ralplan、autopilot、ccg ...        │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                            │                                       │
│  ┌─────────────────────────▼──────────────────────────────────┐  │
│  │                   Hooks 層（hook.json）                     │  │
│  │  UserPromptSubmit → keyword-detector.mjs + skill-injector   │  │
│  │  SessionStart     → session-start.mjs + project-memory      │  │
│  │  PreToolUse       → pre-tool-enforcer.mjs                   │  │
│  │  PostToolUse      → post-tool-verifier.mjs                  │  │
│  │  Stop             → context-guard-stop.mjs + persistent-mode│  │
│  │  SubagentStart/Stop → subagent-tracker.mjs                  │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                            │                                       │
│  ┌─────────────────────────▼──────────────────────────────────┐  │
│  │                   技能路由層（Skills Router）                │  │
│  │  skills/ralph/SKILL.md    → PRD 驅動持久執行循環           │  │
│  │  skills/team/SKILL.md     → Native Teams 協調 pipeline      │  │
│  │  skills/autopilot/SKILL.md→ 全自動端對端執行               │  │
│  │  skills/ultrawork/SKILL.md→ 最大平行度執行                 │  │
│  │  skills/ralplan/SKILL.md  → 共識規劃（Consensus Planning）  │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                            │                                       │
│  ┌─────────────────────────▼──────────────────────────────────┐  │
│  │              代理人層（Agents，agents/*.md）                 │  │
│  │  analyst  architect  critic   debugger  designer            │  │
│  │  executor explore   planner   qa-tester scientist           │  │
│  │  security-reviewer  test-engineer  tracer  verifier writer  │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                            │                                       │
│  ┌─────────────────────────▼──────────────────────────────────┐  │
│  │              MCP 工具伺服器（bridge/mcp-server.cjs）         │  │
│  │  LSP 工具：lsp_hover、lsp_diagnostics、lsp_find_references  │  │
│  │  AST 工具：ast_grep_search、ast_grep_replace               │  │
│  │  狀態工具：state_read/write、project_memory_read/write      │  │
│  │  記事本工具：notepad_read/write_priority/write_working      │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 指令到檔案的映射（Command → File Mapping）

以下是使用說明書中介紹的主要指令，以及它們實際呼叫的檔案：

```
指令/關鍵字                → 觸發檔案                              → 核心邏輯
─────────────────────────────────────────────────────────────────────────────

/team N:executor "task"
  └─→ skills/team/SKILL.md                   # Team pipeline 主流程定義
  └─→ src/hooks/bridge.ts                    # Hook 橋接層
  └─→ scripts/keyword-detector.mjs           # 關鍵字偵測（UserPromptSubmit）

ralph: "task"
  └─→ skills/ralph/SKILL.md                  # PRD 驅動持久循環邏輯
  └─→ scripts/persistent-mode.cjs            # Stop hook 中的持久模式控制
  └─→ scripts/keyword-detector.mjs           # 偵測 ralph 關鍵字

autopilot: "task"
  └─→ skills/autopilot/SKILL.md              # 全自動執行流程
  └─→ scripts/keyword-detector.mjs           # 偵測 autopilot 關鍵字

ulw "task" (ultrawork)
  └─→ skills/ultrawork/SKILL.md              # 最大平行度執行
  └─→ scripts/keyword-detector.mjs           # 偵測 ulw/ultrawork

ralplan "task"
  └─→ skills/ralplan/SKILL.md                # 共識規劃
  └─→ scripts/keyword-detector.mjs           # 偵測 ralplan

/deep-interview "idea"
  └─→ skills/deep-interview/SKILL.md         # 蘇格拉底式（Socratic）需求訪談
  └─→ scripts/keyword-detector.mjs           # 偵測 deep-interview

ultrathink
  └─→ scripts/keyword-detector.mjs           # 偵測並注入 ULTRATHINK_MESSAGE
  └─→ src/installer/hooks.ts                 # ULTRATHINK_MESSAGE 定義

deepsearch
  └─→ scripts/keyword-detector.mjs           # 偵測並注入 SEARCH_MESSAGE
  └─→ src/installer/hooks.ts                 # SEARCH_MESSAGE 定義

/ccg "task"
  └─→ skills/ccg/SKILL.md                    # 三模型顧問合成
  └─→ scripts/keyword-detector.mjs           # 偵測 ccg

omc team N:codex "task"
  └─→ bridge/cli.cjs                         # CLI 入口點
  └─→ bridge/team-bridge.cjs                 # tmux 工作者管理
  └─→ scripts/run.cjs                        # 腳本執行器

/omc-setup
  └─→ skills/omc-setup/SKILL.md              # 安裝設定流程
  └─→ scripts/setup-init.mjs                 # SessionStart init hook
  └─→ scripts/plugin-setup.mjs               # 外掛安裝腳本

/skill list|add|remove
  └─→ skills/skill/SKILL.md                  # 技能管理介面
  └─→ src/tools/skills-tools.ts              # 技能工具後端

omc wait [--start|--stop]
  └─→ bridge/cli.cjs                         # CLI 解析
  └─→ src/features/rate-limit-wait/          # 速率限制（Rate Limit）等待邏輯
```

### 執行流程圖（Execution Flowchart）

```
用戶輸入提示（Prompt）
         │
         ▼
[UserPromptSubmit Hook 觸發]
         │
         ├─→ keyword-detector.mjs
         │       │
         │       ├─ 偵測到 ralph ──────────────► 注入 RALPH_MESSAGE
         │       ├─ 偵測到 autopilot ──────────► 注入 autopilot skill
         │       ├─ 偵測到 ulw ─────────────────► 注入 ultrawork skill
         │       ├─ 偵測到 ultrathink ──────────► 注入 ULTRATHINK_MESSAGE
         │       ├─ 偵測到 ccg ─────────────────► 注入 ccg skill
         │       └─ 無關鍵字 ──────────────────► 原始提示繼續
         │
         └─→ skill-injector.mjs
                 │
                 ├─ 掃描 .omc/skills/ (專案級)
                 ├─ 掃描 ~/.omc/skills/ (使用者級)
                 └─ 觸發符合條件的技能注入上下文（Context）
         │
         ▼
[Claude Code 處理（含注入的 System Prompt）]
         │
         ├─ /team 指令 ──────────────────────────────────────────────┐
         │   team-plan → team-prd → team-exec → team-verify          │
         │                                    ↗         ↘            │
         │                               team-fix ──── complete       │
         │                                    ↖___（失敗重試）_____┘  │
         │                                                            │
         ├─ ralph 模式 ─────────────────────────────────────────────┐ │
         │   iteration 1 → prd.json 建立                            │ │
         │   iteration N → 逐 story 執行                            │ │
         │   verification → architect agent 審查                    │ │
         │   完成 ← 所有 story passes: true                         │ │
         │                                                          │ │
         └─ 直接執行（單次）                                         │ │
                                                                    │ │
[PreToolUse Hook] → pre-tool-enforcer.mjs（權限驗證、worker 限制）   │ │
[工具執行（Read/Write/Bash/...）]                                    │ │
[PostToolUse Hook] → post-tool-verifier.mjs + project-memory        │ │
[Stop Hook] → context-guard-stop.mjs → persistent-mode.cjs ◄────────┘ │
                    ├─ ralph 尚未完成 → 繼續執行（不停止）             │ │
                    └─ 完成 → session-end.mjs → 發送通知              ◄┘ │
[SessionEnd Hook] → session-end.mjs（儲存摘要、通知 Telegram/Discord）   │
```

### Team Pipeline 時序圖（Team Pipeline Sequence Diagram）

```
用戶          OMC Lead        team-plan       workers(x3)     team-verify
  │               │               │               │               │
  │  /team 3:executor "task"      │               │               │
  │──────────────►│               │               │               │
  │               │  TeamCreate("task-name")       │               │
  │               │──────────────►│               │               │
  │               │  analyse + decompose           │               │
  │               │──────────────►│               │               │
  │               │◄──── subtask list ────────────│               │
  │               │  TaskCreate x3 (subtasks)      │               │
  │               │───────────────────────────────►│               │
  │               │  spawn worker x3 (executor)    │               │
  │               │───────────────────────────────►│               │
  │               │               │  work on task #1              │
  │               │               │──────────────►│               │
  │               │               │  work on task #2              │
  │               │               │──────────────►│               │
  │               │               │  work on task #3              │
  │               │               │──────────────►│               │
  │               │◄── SendMessage (progress) ────│               │
  │               │  all tasks complete?           │               │
  │               │──────────────────────────────────────────────►│
  │               │               │         verification pass/fail │
  │               │               │               │◄──────────────│
  │               │  TeamDelete + cleanup          │               │
  │               │───────────────────────────────►│               │
  │◄──── 完成報告 ─│               │               │               │
```

### Hook 生命週期與對應腳本（Hook Lifecycle）

```
Claude Code 生命週期事件
      │
      ├─[SessionStart]──────────────────────────────────────────────
      │   ├─ scripts/session-start.mjs         ← 初始化工作階段（Session）狀態
      │   ├─ scripts/project-memory-session.mjs← 載入專案記憶（Project Memory）
      │   └─ scripts/setup-init.mjs            ← (matcher: init) 首次設定
      │
      ├─[UserPromptSubmit]──────────────────────────────────────────
      │   ├─ scripts/keyword-detector.mjs      ← 魔術關鍵字偵測、技能觸發
      │   └─ scripts/skill-injector.mjs        ← 技能自動注入
      │
      ├─[PreToolUse]────────────────────────────────────────────────
      │   └─ scripts/pre-tool-enforcer.mjs     ← 工具權限驗證、worker tmux 阻擋
      │
      ├─[PermissionRequest(Bash)]───────────────────────────────────
      │   └─ scripts/permission-handler.mjs    ← Bash 執行權限處理
      │
      ├─[PostToolUse]───────────────────────────────────────────────
      │   ├─ scripts/post-tool-verifier.mjs    ← 工具輸出驗證
      │   └─ scripts/project-memory-posttool.mjs← 更新專案記憶
      │
      ├─[PostToolUseFailure]────────────────────────────────────────
      │   └─ scripts/post-tool-use-failure.mjs ← 工具失敗處理
      │
      ├─[SubagentStart]─────────────────────────────────────────────
      │   └─ scripts/subagent-tracker.mjs start← 子代理人追蹤開始
      │
      ├─[SubagentStop]──────────────────────────────────────────────
      │   ├─ scripts/subagent-tracker.mjs stop ← 子代理人追蹤結束
      │   └─ scripts/verify-deliverables.mjs   ← 驗證可交付成果
      │
      ├─[PreCompact]────────────────────────────────────────────────
      │   ├─ scripts/pre-compact.mjs           ← 壓縮前儲存狀態
      │   └─ scripts/project-memory-precompact.mjs
      │
      ├─[Stop]──────────────────────────────────────────────────────
      │   ├─ scripts/context-guard-stop.mjs    ← 未完成任務警告
      │   ├─ scripts/persistent-mode.cjs       ← Ralph 持久模式控制
      │   └─ scripts/code-simplifier.mjs       ← 自動代碼簡化
      │
      └─[SessionEnd]────────────────────────────────────────────────
          └─ scripts/session-end.mjs           ← 工作階段摘要、通知推送
```

### 技能組合層次（Skill Composition Layers）

```
┌──────────────────────────────────────────────────────────┐
│  保證層（GUARANTEE LAYER）— 可選                          │
│  ralph: 「直到驗證完成才停止」                            │
│  持久執行、PRD 驅動、architect 審查驗收                    │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  增強層（ENHANCEMENT LAYER）— 0 到 N 個技能              │
│  ultrawork（平行）│ git-master（提交）│ frontend-ui-ux    │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  執行層（EXECUTION LAYER）— 主要技能                      │
│  team（協調）│ autopilot（自主）│ ralplan（規劃）          │
└──────────────────────────────────────────────────────────┘

組合公式：[執行技能] + [0-N 增強] + [可選保證]

範例：
  ralph: ultrawork refactor the API
  → [team/autopilot] + [ultrawork] + [ralph]
  → PRD 建立 → 平行執行 → architect 驗收 → 完成
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> **技能即文件（Skills as Documents）**：工作流邏輯寫在 Markdown 中，Claude 直接閱讀後執行，無需硬編碼程式邏輯。

1. **Markdown-first 技能**：Skills 是 Markdown 檔案，讓社群可以貢獻/修改工作流而無需懂 TypeScript
2. **Hook 驅動架構**：透過 Claude Code 的原生 Hook 系統介入，避免 fork 官方 CLI
3. **MCP 工具伺服器**：LSP/AST 等進階工具透過 MCP 協議（Model Context Protocol）提供，保持擴充性
4. **PRD 驅動驗收（ralph 模式）**：用結構化的 Product Requirements Document 確保 AI 不會「假完成」

### 關鍵程式碼片段（Key Code Snippets）

**createOmcSession — 核心工作階段建立（src/index.ts）**

```typescript
export function createOmcSession(options?: OmcOptions): OmcSession {
  const config: PluginConfig = { ...loadConfig(), ...options?.config };

  let systemPrompt = omcSystemPrompt;
  if (config.features?.continuationEnforcement !== false) {
    systemPrompt += continuationSystemPromptAddition;
  }

  const agents = getAgentDefinitions({ config });
  const externalMcpServers = getDefaultMcpServers({ ... });
  const processPrompt = createMagicKeywordProcessor(config.magicKeywords);

  return {
    queryOptions: {
      options: {
        systemPrompt,
        agents,
        mcpServers: { ...toSdkMcpFormat(externalMcpServers), 't': omcToolsServer },
        allowedTools,
        permissionMode: 'acceptEdits'
      }
    },
    processPrompt,
    backgroundTasks: backgroundTaskManager,
  };
}
```

**hooks.json — Hook 事件與腳本映射（精簡版）**

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "*",
      "hooks": [
        { "command": "node \"$CLAUDE_PLUGIN_ROOT\"/scripts/run.cjs .../keyword-detector.mjs", "timeout": 5 },
        { "command": "node \"$CLAUDE_PLUGIN_ROOT\"/scripts/run.cjs .../skill-injector.mjs", "timeout": 3 }
      ]
    }],
    "Stop": [{
      "matcher": "*",
      "hooks": [
        { "command": "node .../context-guard-stop.mjs", "timeout": 5 },
        { "command": "node .../persistent-mode.cjs", "timeout": 10 },
        { "command": "node .../code-simplifier.mjs", "timeout": 5 }
      ]
    }]
  }
}
```

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐ | 技能（Skills）以 Markdown 分離，邏輯清晰；Hook 腳本模組化 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐⭐ | 技能系統讓用戶無需修改核心即可擴充功能 |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐⭐ | 851 個 TypeScript 測試檔案，有 benchmark 評估框架 |
| 文件品質（Documentation） | ⭐⭐⭐⭐⭐ | 11 種語言 README、ARCHITECTURE.md、REFERENCE.md |
| 依賴管理（Dependency Management） | ⭐⭐⭐⭐ | 依賴合理，MCP SDK 為業界標準，esbuild 建置高效 |

> [!tip] 值得學習的設計
> **技能即文件（Skills as Documents）** 的設計理念極為優雅：每個工作流就是一個 Markdown 檔案，Claude 直接「閱讀」後執行。這使技能可被版本控制、共享、修改，完全不需要寫程式碼。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷

- **硬性依賴 tmux**：`omc team`、速率限制等待等核心功能需要 tmux，Windows 需要安裝第三方 psmux。影響：跨平台相容性（Cross-platform Compatibility）下降
- **npm 套件命名混亂**：Repo 名稱是 `oh-my-claudecode`，npm 套件卻是 `oh-my-claude-sisyphus`，造成安裝困惑。影響：新用戶上手體驗差
- **Hook 腳本是 CommonJS + ESM 混合**：`persistent-mode.cjs` 和 `.mjs` 並存，維護負擔較高。影響：技術債（Technical Debt）累積
- **MCP 工具伺服器單點瓶頸**：所有 LSP/AST/記憶工具都經過 `bridge/mcp-server.cjs`，若進程崩潰會影響所有工具。影響：可靠性（Reliability）風險

### 🔮 改進建議（Improvement Suggestions）

1. **統一 npm 套件名稱**：將 `oh-my-claude-sisyphus` 改為 `oh-my-claudecode` 或提供明確別名
2. **減少 tmux 依賴**：提供純進程模式（Process Mode）作為降級替代（Fallback）
3. **MCP 工具伺服器高可用**：加入自動重啟機制或拆分為多個輕量伺服器
4. **技能版本管理（Skill Versioning）**：為技能加入版本號和向後相容性（Backward Compatibility）機制

---

## 效能基準（Benchmark）

> [!info] 資料來源
> 專案有 `benchmarks/` 目錄，包含 code-reviewer、debugger、executor、harsh-critic 的代理人效能評估框架，但官方基準數據尚未填入實際數值（均為佔位符）。

| 官方宣稱 | 數值 |
|---------|------|
| 智慧模型路由（Smart Model Routing）節省 token 成本 | 30-50% |
| 最大平行代理人數（/team） | 20 |
| 支援 Hook 事件類型 | 12 種 |

**主要效能特性：**
- Haiku 處理快速查詢，Sonnet 處理標準實作，Opus 處理架構分析，自動路由是主要成本最佳化手段
- 平行執行（Parallel Execution）透過 `run_in_background: true` 顯著縮短複雜任務完成時間
- ralph 模式確保任務「真正完成」但每個任務需要多次 Claude API 呼叫

---

## 快速上手（Quick Start）

```bash
# 安裝
/plugin marketplace add https://github.com/Yeachan-Heo/oh-my-claudecode
/plugin install oh-my-claudecode

# 設定
/setup
/omc-setup

# 建立 REST API（全自動）
autopilot: build a REST API for managing tasks

# 修復所有 TypeScript 錯誤（3 個代理人平行）
/team 3:executor "fix all TypeScript errors"

# 需求訪談後執行
/deep-interview "I want to build a task management app"

# 持久執行直到完成
ralph: refactor the authentication module

# 三模型顧問（Tri-model Advisor）
/ccg Review this PR — architecture (Codex) and UI (Gemini)

# tmux CLI 工作者
omc team 2:codex "review auth module for security issues"

# 速率限制（Rate Limit）等待
omc wait --start
```

---

## 我的心得（My Takeaways）

1. **「技能即文件」是最值得借鑑的設計**：把工作流指令寫成 Markdown，讓 LLM 直接閱讀後執行，比硬編碼程式邏輯更靈活，也更容易被社群貢獻和修改。

2. **Hook 系統是 Claude Code 強大的擴充點**：UserPromptSubmit、Stop、PreToolUse 這些生命週期事件讓外掛完全介入 Claude 行為，實現關鍵字偵測、技能注入、持久執行等進階功能。

3. **「ralph」模式體現了 AI 工作流設計的核心挑戰**：如何讓 AI 代理人「真正完成」任務而不是半途而廢？OMC 的答案是 PRD 驅動 + 獨立驗證代理人，值得在自己的 AI 工作流工具中應用。

4. **多模型路由（Multi-model Routing）是實用的成本控制手段**：不是所有任務都需要 Opus，合理分配 Haiku/Sonnet/Opus 能顯著降低 API 成本（宣稱節省 30-50%）。

---

---

## OMC CLI 深度解析（`omc` 指令完整分析）

> [!important] 本節深度分析 `omc` CLI 工具的所有指令、設計動機，以及它解決了哪些「技能系統（Skills）無法獨力解決」的根本問題。

### CLI 的核心定位：Claude Code 的「會話外控制器」

OMC 由兩種元件組成，有一條根本的邊界線：

```
┌─────────────────────────────────┐   ┌──────────────────────────────────────┐
│  Claude Code 會話內（In-session）│   │  Claude Code 會話外（Out-of-session）│
│                                 │   │                                      │
│  Skills（/oh-my-claudecode:xxx）│   │  omc CLI（bridge/cli.cjs）           │
│  Hooks（scripts/*.mjs）         │   │                                      │
│  Agents（agents/*.md）          │   │  ← 使用者在 shell 直接呼叫            │
│  MCP Tools（mcp-server.cjs）    │   │  ← Claude Code 啟動前後執行          │
│                                 │   │  ← 速率限制暫停時仍然存活            │
│  受 Claude Code 程序生命週期限制  │   │  ← 可直接操控 tmux/git/外部 CLI     │
└─────────────────────────────────┘   └──────────────────────────────────────┘
```

**CLI 存在的根本原因：有五類操作是 Skills/Hooks 物理上無法完成的。**

---

### 所有 `omc` 指令一覽

```
omc / omc launch [args...]       — 啟動 Claude Code（含 tmux 自動整合）
omc interop                      — tmux 分割視窗：Claude Code (OMC) + Codex (OMX) 並排
omc ask <claude|codex|gemini>    — 呼叫外部 AI 顧問，輸出儲存為 artifact
omc config                       — 顯示/驗證 OMC 設定
omc config-stop-callback <type>  — 設定 Stop hook 通知（Telegram/Discord/Slack/file）
omc config-notify-profile        — 管理多組通知設定檔（Profile）
omc wait [--start|--stop]        — 速率限制（Rate Limit）偵測與自動恢復精靈
  omc wait status                  └ 詳細速率限制狀態
  omc wait daemon <start|stop>     └ 背景自動恢復常駐程序（Daemon）
  omc wait detect                  └ 掃描 tmux 中被鎖住的 Claude Code 工作階段
omc teleport [ref]               — 從 GitHub Issue/PR/功能名稱建立 git worktree
  omc teleport list                └ 列出現有 worktrees
  omc teleport remove <path>       └ 刪除 worktree
omc session search <query>       — 跨歷史工作階段搜尋 transcript
omc doctor                       — 安裝問題診斷
  omc doctor conflicts             └ 外掛衝突檢查
omc hud                          — 渲染 HUD 狀態列（被 settings.json 的 statusLine 呼叫）
omc mission-board                — 顯示當前工作區的任務看板快照
omc team [N:agent "task"]        — 啟動 tmux CLI 工作者（codex/gemini/claude）
  omc team status <name>           └ 檢查執行中的 Team 狀態
  omc team shutdown <name>         └ 關閉 Team
  omc team api <operation>         └ 低階 Team 狀態 API（send-message/list-tasks/...）
omc autoresearch                 — 自主研究迴圈（Autonomous Research Loop）
omc ralphthon                    — 駭客松（Hackathon）自動化生命週期
omc setup                        — 同步所有元件（hooks/agents/skills）
omc update                       — 檢查並安裝更新
omc version / omc info           — 版本與系統資訊
omc test-prompt <prompt>         — 測試提示詞（Prompt）如何被增強
```

---

### 五大獨立存在的理由

#### 理由一：Claude Code 暫停時需要持續運行的背景程序

**問題**：Claude Code 觸碰 Rate Limit 時整個工作階段暫停，Skills/Hooks 全部停止。但使用者希望 Rate Limit 清除後**自動恢復**，不需要手動守候。

**解法**：`omc wait` 是一個完全在 Claude Code 之外運行的獨立程序。

```
Claude Code 被速率限制暫停
         │
         ▼
omc wait --start
  ├─ 啟動背景 Daemon（每 60 秒輪詢 Rate Limit API）
  ├─ 掃描 tmux 中被 "rate limited" 訊息鎖住的視窗
  ├─ 當 Rate Limit 清除時，向 tmux 視窗發送 Enter 鍵恢復
  └─ Daemon 狀態持久化到 ~/.claude/.omc-daemon-state.json

─── 為什麼 Skill 無法取代？ ───────────────────────────────────────
Skills 在 Claude Code 程序內執行。Claude Code 被 Rate Limit 暫停
時，Skills 也無法執行。只有外部程序才能在 Claude Code 暫停期間
繼續監控狀態並在適當時機自動重啟。
────────────────────────────────────────────────────────────────────
```

#### 理由二：需要在 Claude Code **啟動前**注入環境變數

**問題**：OMC 的通知功能（Telegram、Discord、OpenClaw）透過 Hook 在 `SessionStart`/`Stop` 時發出通知，這些 Hook 讀取 `OMC_TELEGRAM`、`OMC_DISCORD`、`OMC_OPENCLAW` 等環境變數。但環境變數必須在 Claude Code 啟動前就設定好。

**解法**：`omc launch` 是 `claude` 指令的包裝器，在啟動 Claude Code 前設定好所有環境變數：

```bash
omc launch --notify false          # 設定 OMC_NOTIFY=0，再執行 claude
omc launch --openclaw true         # 設定 OMC_OPENCLAW=1，再執行 claude
omc --madmax                       # --madmax 等同 --dangerously-skip-permissions
```

```
omc launch 的內部流程：
  1. 解析 --notify / --openclaw / --telegram 等 flag
  2. 設定對應環境變數（process.env.OMC_NOTIFY = "0"）
  3. 偵測是否在 tmux 內
     ├─ 在 tmux 內：直接執行 claude [...args]
     └─ 在 tmux 外：自動建立 tmux session，在其中執行 claude，然後 attach
  4. 執行完畢後 postLaunch（清理）

─── 為什麼 Skill 無法取代？ ───────────────────────────────────────
Claude Code 啟動後，環境變數已固定。必須在啟動前注入。
────────────────────────────────────────────────────────────────────
```

#### 理由三：直接操控 tmux 視窗分割（Claude Code 沙盒限制）

**問題**：`omc team N:codex "task"` 需要在 tmux 中開啟 N 個分割視窗，各自執行 `codex`/`gemini`/`claude` CLI 進程。Claude Code 內的 Bash tool 雖然能執行 shell 指令，但：
- 直接 `tmux split-window` 在 Claude Code 的 Hook 中被主動**封鎖**（`WORKER_BLOCKED_TMUX_PATTERN`）
- 這是安全設計：防止工作者自己生出更多工作者造成無限遞迴

**解法**：`omc team` 是在 tmux 中直接運行的外部進程，不受 Claude Code 的工具沙盒限制：

```
使用者在 tmux 中執行：
omc team 2:codex "review auth module"
         │
         ├─ 解析：N=2, agent-type=codex, task="review auth module"
         ├─ 建立 Team 名稱（team-name = slugify(task)）
         ├─ tmux split-window → 開 2 個新視窗，各執行：
         │     codex --print --agent-prompt executor "review auth module"
         ├─ 監控各視窗的輸出（tail tmux pane buffer）
         ├─ omc team status auth-review → 讀取 .omc/state/team-state.json
         └─ omc team shutdown auth-review → 向各 pane 發送退出指令

─── 為什麼 Skill 無法取代？ ───────────────────────────────────────
pre-tool-enforcer.mjs 明確封鎖了 Hook 腳本中的 tmux split-window。
這是 OMC 自己的安全防護，防止代理人無限生成子代理人。
外部 CLI 是唯一能做真正 tmux 操作的方式。
────────────────────────────────────────────────────────────────────
```

#### 理由四：HUD 狀態列需要 Claude Code 外部的 Node.js 進程

**問題**：Claude Code 的 `settings.json` 支援 `statusLine.command`，即每次渲染狀態列時執行一個外部指令並取得輸出文字。這個指令由 **Claude Code 程序呼叫**，並非在 Claude Code 內部執行。

**解法**：`omc hud` 就是這個外部指令。

```
settings.json：
{
  "statusLine": {
    "type": "command",
    "command": "\"/path/to/node\" \"/home/user/.claude/hud/omc-hud.mjs\""
  }
}

每次 Claude Code 渲染狀態列時：
  → 執行 omc-hud.mjs（在 Claude Code 外部）
  → 讀取 .omc/state/*.json（代理人狀態、token 用量）
  → 輸出一行文字給 Claude Code 顯示

─── 為什麼 Skill 無法取代？ ───────────────────────────────────────
statusLine.command 本身就是設計為「外部命令」。
Skills 是在 Claude Code 對話內執行的，無法輸出到狀態列。
────────────────────────────────────────────────────────────────────
```

#### 理由五：跨會話、跨時間的狀態操作

這類操作的特徵是「在一個 Claude Code 工作階段結束後、另一個開始前」使用：

| 指令 | 使用時機 | 為什麼在 Claude Code 外？ |
|------|---------|--------------------------|
| `omc teleport '#42'` | 開始工作前，為 Issue #42 建立獨立 git worktree | 是啟動新工作階段的**前置準備** |
| `omc session search "auth bug"` | 工作階段結束後，搜尋過去的對話記錄 | 搜尋歷史紀錄，不需要啟動 Claude |
| `omc config-stop-callback telegram --enable` | 一次性設定，之後所有工作階段都生效 | 設定持久化設定檔，無需 Claude Code |
| `omc doctor conflicts` | 安裝出問題時診斷 | Claude Code 可能根本無法正常啟動 |

---

### CLI 指令分組：按使用場景

```
A. Claude Code 啟動前（Pre-session）
   omc launch            → 帶環境變數啟動 + tmux 自動建立
   omc teleport '#42'    → 建立 issue/PR 的隔離 worktree
   omc setup             → 同步安裝元件
   omc update            → 更新到最新版

B. Claude Code 執行中（In-session，從外部觀察）
   omc hud               → 狀態列渲染（被 settings.json 呼叫）
   omc mission-board     → 任務看板快照
   omc team status       → 檢查 tmux CLI 工作者狀態
   omc team shutdown     → 強制關閉工作者

C. Claude Code 暫停時（Rate Limited）
   omc wait              → 檢查速率限制狀態
   omc wait --start      → 啟動自動恢復 Daemon
   omc wait detect       → 掃描 tmux 中被鎖住的視窗

D. Claude Code 結束後（Post-session）
   omc session search    → 搜尋歷史 transcript
   omc doctor            → 診斷問題

E. 完全獨立使用（Standalone）
   omc ask codex "task"  → 呼叫外部 AI 顧問，不需啟動 Claude
   omc interop           → OMC + OMX 並排工作環境
   omc ralphthon "task"  → 外部編排的駭客松自動化
   omc autoresearch      → 自主研究迴圈（在 worktree 中）
   omc config-stop-callback → 永久設定通知
```

---

### `omc teleport` — git worktree 深度整合

`teleport` 解決了一個具體痛點：開始做一個 GitHub Issue 時，需要手動 `git fetch`、`git checkout -b`、切換目錄，很繁瑣。

```bash
omc teleport '#42'
# 做了什麼：
# 1. 用 gh CLI 查詢 Issue #42 的標題："Fix auth token expiry"
# 2. 建立分支名：fix/42-fix-auth-token-expiry
# 3. git worktree add ~/Workspace/omc-worktrees/issue/myrepo-42 fix/42-fix-auth-token-expiry
# 4. 輸出 worktree 路徑，使用者可直接 cd 進去開新的 Claude Code 工作階段

omc teleport 'add-oauth'
# 建立功能分支：feat/add-oauth
# worktree 路徑：~/Workspace/omc-worktrees/feat/myrepo-add-oauth

omc teleport list
# 列出所有 ~/Workspace/omc-worktrees/ 下的 worktrees
```

> [!tip] 最佳實踐
> `omc teleport` + `omc launch` 組合使用：
> ```bash
> omc teleport '#42' && cd ~/Workspace/omc-worktrees/issue/myrepo-42 && omc
> ```
> 一行指令：建立隔離環境 → 切入 → 啟動 Claude Code（自動附帶 tmux）

---

### `omc ralphthon` — 駭客松自動化生命週期

這是 CLI 中最進階的指令，把「ralph 模式（持久執行）」提升為**全自主的駭客松循環**：

```
使用者執行：omc ralphthon "build a REST API for task management"
                  │
                  ▼ （需要在 tmux 中）
┌──────────────────────────────────────────────────────────┐
│  Phase 1: Deep Interview                                  │
│  → 在 Leader tmux pane 執行 /deep-interview              │
│  → 產生 .omc/ralphthon-prd.json                          │
└──────────────────────────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────────────┐
│  Phase 2: Execute Waves（每波 = 一輪 ralph 執行）          │
│  → 外部 Orchestrator（omc 程序）監控 Claude Code 工作階段  │
│  → 每波執行完畢後比對 PRD story 完成度                    │
│  → 連續 3 波都乾淨（clean）才宣告完成                      │
└──────────────────────────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────────────┐
│  Phase 3: Hardening（強化）                               │
│  → 執行安全審查、測試補全、代碼簡化                       │
└──────────────────────────────────────────────────────────┘
```

**與 ralph 模式的差異：**

| | `ralph` (Skill) | `omc ralphthon` (CLI) |
|--|--|--|
| 執行環境 | Claude Code 工作階段內 | 外部 tmux 編排器 |
| 持久性 | 同一個工作階段 | 跨多個 Claude Code 工作階段 |
| 適用場景 | 單次任務確保完成 | 多小時/整天的自動化開發 |
| tmux 需求 | 可選 | 必須 |

---

### `omc autoresearch` — 自主研究迴圈

解決了一個特殊問題：AI 生成的程式碼有隨機性，如何系統性地「搜尋最佳實作方案」？

```
概念：每次嘗試都在隔離的 git worktree 中執行
      → 透過評估器（evaluator）判斷結果好壞（keep/discard/reset）
      → 保留好的結果，丟棄壞的，持續迭代

使用方式：
omc autoresearch --topic "optimize database query" \
                 --eval "pytest tests/perf/" \
                 --slug "db-query-opt"

→ 每次迭代：建立新 worktree → 讓 Claude 嘗試優化 → 執行 pytest
  keep：合併回主分支
  discard：刪除 worktree，重試
  reset：重置到基準狀態
```

---

### 為什麼不能用其他方法取代 CLI？

| CLI 指令 | 嘗試的替代方案 | 為什麼不可行 |
|---------|--------------|------------|
| `omc wait` 自動恢復 | 在 Claude Code 裡寫 Skill | Rate Limited 時 Skills 無法執行，需要外部常駐程序 |
| `omc launch` 環境注入 | 手動設 export 再啟動 | 使用者每次都要記得設定，容易忘記；無法跨平台一致 |
| `omc team N:codex` | `/team N:codex` Skill | Hooks 封鎖了 `tmux split-window`（安全設計防止遞迴） |
| `omc hud` | 把 HUD 邏輯放在 Hook 裡 | `statusLine.command` 本身就需要外部進程，這是 Claude Code 的 API |
| `omc teleport` | 在 Claude Code 裡執行 git | 這是啟動 Claude Code **之前**的準備動作，不需要啟動 Claude |
| `omc session search` | Claude Code 自帶歷史 | 跨工作階段搜尋需要在無 Claude 的情況下快速查詢 |
| `omc doctor` | 在 Claude Code 裡診斷 | Claude Code 可能根本無法正常啟動，診斷必須在外部 |

> [!note] 核心洞察
> OMC CLI 的本質是一個「**Claude Code 的衛星控制中心**」。它不是要取代 Claude Code，而是填補 Claude Code 程序生命週期邊界上的空隙：啟動前的環境準備、執行中的外部觀察、Rate Limit 時的自動恢復、結束後的狀態查詢。

---

## 安裝與設定深度解析（Installation & Setup Deep Dive）

> [!important] 本節深度分析四個安裝指令的完整運作機制與實際寫入的檔案清單。

### 指令一：`/plugin marketplace add https://github.com/Yeachan-Heo/oh-my-claudecode`

這是 Claude Code 原生的 Plugin Marketplace 系統指令。執行後：

```
Claude Code 讀取 .claude-plugin/marketplace.json
         │
         ▼
git clone https://github.com/Yeachan-Heo/oh-my-claudecode
  → 目標路徑：~/.claude/plugins/marketplaces/omc/
         │
         ▼
登記到 ~/.claude/plugins/installed_marketplaces.json
```

**寫入的檔案：**
```
~/.claude/plugins/marketplaces/omc/
├── .claude-plugin/
│   ├── marketplace.json   ← 市集清單（name: "omc"）
│   └── plugin.json        ← 外掛元資料（name: "oh-my-claudecode"）
├── skills/                ← 全部技能（不立即啟用）
├── agents/                ← 代理人定義
├── hooks/hooks.json       ← Hook 事件設定
├── scripts/               ← Hook 執行腳本
├── bridge/                ← CLI & MCP server
└── ... (完整 repo 內容)
```

`marketplace.json` 中宣告的 `"name": "omc"` 就是之後 `/plugin install oh-my-claudecode` 能找到此外掛的依據。

---

### 指令二：`/plugin install oh-my-claudecode`

Claude Code 從已登記的市集中找到 `oh-my-claudecode` 外掛並執行安裝：

```
讀取 ~/.claude/plugins/marketplaces/omc/.claude-plugin/plugin.json
         │
         ▼
複製外掛內容到版本化快取目錄：
~/.claude/plugins/cache/omc/oh-my-claudecode/{version}/
         │
         ▼
執行 Post-Install 腳本：scripts/plugin-setup.mjs
         │
         ├─ 建立 ~/.claude/hud/ 目錄
         ├─ 安裝 ~/.claude/hud/omc-hud.mjs（HUD wrapper）
         ├─ 修改 ~/.claude/settings.json：加入 statusLine
         ├─ 儲存 node binary 路徑到 ~/.claude/.omc-config.json
         ├─ 修補 hooks/hooks.json：將 `node` 替換為絕對路徑（解決 nvm/fnm 問題）
         └─ 若 node_modules 缺失：執行 npm install --omit=dev --ignore-scripts
         │
         ▼
登記到 ~/.claude/plugins/installed_plugins.json
（記錄 installPath 指向 cache 目錄）
```

**Post-Install 後完整檔案清單：**

```
~/.claude/
├── settings.json                          ← 新增 statusLine 設定
│   {
│     "statusLine": {
│       "type": "command",
│       "command": "\"/path/to/node\" \"/home/user/.claude/hud/omc-hud.mjs\""
│     }
│   }
│
├── hud/
│   └── omc-hud.mjs                        ← HUD 狀態列 wrapper 腳本
│
├── .omc-config.json                        ← OMC 設定（nodeBinary 路徑）
│
└── plugins/
    ├── marketplaces/omc/                   ← 步驟一 clone 的 repo（不變）
    ├── cache/omc/oh-my-claudecode/
    │   └── {version}/                      ← 實際啟用的外掛根目錄
    │       ├── dist/                        ← 編譯後的 TypeScript（MCP tools 等）
    │       ├── agents/                      ← 19 個代理人 Markdown
    │       ├── skills/                      ← 30+ 個技能目錄
    │       ├── hooks/hooks.json             ← 已修補絕對路徑的 Hook 設定
    │       ├── scripts/                     ← keyword-detector.mjs 等 Hook 腳本
    │       ├── bridge/                      ← cli.cjs、mcp-server.cjs、team-bridge.cjs
    │       ├── .claude-plugin/              ← plugin.json、marketplace.json
    │       ├── .mcp.json                    ← MCP server 設定（指向 bridge/mcp-server.cjs）
    │       └── node_modules/                ← npm install --omit=dev 安裝的依賴
    │
    └── installed_plugins.json              ← 記錄 installPath
```

**`settings.json` 的 `statusLine` 的意義：**

Claude Code 每次渲染狀態列時，會執行這個 Node.js 腳本，`omc-hud.mjs` 從外掛快取目錄讀取 `dist/hud/index.js` 並輸出 HUD 文字。這樣 HUD 就能即時反映代理人狀態。

---

### 指令三：`/setup`

這是一個**路由器技能（Router Skill）**，讀取 `skills/setup/SKILL.md`：

```
/setup [argument]
    │
    ├─ 無參數 / --local / --global / --force
    │     └─→ 呼叫 /oh-my-claudecode:omc-setup
    │
    ├─ doctor
    │     └─→ 呼叫 /oh-my-claudecode:omc-doctor
    │
    └─ mcp
          └─→ 呼叫 /oh-my-claudecode:mcp-setup
```

本身不做任何事，只負責分派。

---

### 指令四：`/omc-setup`（四階段安裝精靈）

讀取 `skills/omc-setup/SKILL.md`，按序執行四個階段：

#### 安裝精靈時序圖（Setup Wizard Sequence Diagram）

```
用戶              /omc-setup            scripts/           ~/.claude/
  │                   │                    │                   │
  │  /omc-setup       │                    │                   │
  │──────────────────►│                    │                   │
  │                   │                    │                   │
  │                   │ 檢查 .omc-config.json (是否已設定？)   │
  │                   │───────────────────────────────────────►│
  │                   │◄── 未設定，繼續 ──────────────────────│
  │                   │                    │                   │
  │  ▼ Phase 1                             │                   │
  │  詢問：Local 或 Global？               │                   │
  │◄──────────────────│                    │                   │
  │  回答：Global     │                    │                   │
  │──────────────────►│                    │                   │
  │                   │  setup-claude-md.sh global             │
  │                   │───────────────────►│                   │
  │                   │                    │ 備份舊 CLAUDE.md  │
  │                   │                    │ 下載新版本         │
  │                   │                    │───────────────────►│
  │                   │                    │  寫入 ~/.claude/CLAUDE.md
  │                   │                    │  寫入 .git/info/exclude
  │                   │                    │◄──────────────────│
  │                   │◄── 成功 ───────────│                   │
  │                   │                    │                   │
  │  ▼ Phase 2                             │                   │
  │                   │  呼叫 hud skill    │                   │
  │                   │──────────────────────────────────────► ~/.claude/hud/omc-hud.mjs
  │                   │                    │   ~/.claude/settings.json (statusLine)
  │                   │                    │                   │
  │                   │  清除舊版快取      │                   │
  │                   │  檢查 npm 最新版本 │                   │
  │  詢問：預設執行模式？                  │                   │
  │◄──────────────────│                    │                   │
  │  回答：ultrawork  │                    │                   │
  │──────────────────►│                    │                   │
  │                   │ 寫入 .omc-config.json (defaultExecutionMode)
  │                   │───────────────────────────────────────►│
  │  詢問：安裝 omc CLI？                  │                   │
  │◄──────────────────│                    │                   │
  │  回答：Yes        │                    │                   │
  │──────────────────►│  npm install -g oh-my-claude-sisyphus  │
  │                   │───────────────────►│                   │
  │                   │  /usr/local/bin/omc (或 ~/.npm/bin/omc)│
  │                   │                    │                   │
  │  ▼ Phase 3                             │                   │
  │  詢問：設定 MCP servers？              │                   │
  │◄──────────────────│                    │                   │
  │  詢問：啟用 Agent Teams？              │                   │
  │◄──────────────────│                    │                   │
  │  回答：Yes        │                    │                   │
  │──────────────────►│  jq 修改 settings.json                 │
  │                   │───────────────────────────────────────►│
  │                   │  CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1│
  │                   │                    │                   │
  │  ▼ Phase 4                             │                   │
  │  顯示 Welcome 訊息                     │                   │
  │◄──────────────────│                    │                   │
  │                   │  寫入 .omc-config.json (setupCompleted)│
  │                   │───────────────────────────────────────►│
```

#### 安裝後完整檔案清單（完整版）

```
~/.claude/
│
├── CLAUDE.md                              ← OMC 主要指令系統（含 <!-- OMC:START --> marker）
│   (或 ./.claude/CLAUDE.md 若選 local)
│
├── settings.json                          ← 累積修改：
│   {                                         - statusLine（Phase 1 plugin-setup）
│     "statusLine": { ... },                  - CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS（Phase 3）
│     "env": {
│       "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
│     }
│   }
│
├── hud/
│   └── omc-hud.mjs                        ← HUD 狀態列 wrapper（Phase 2）
│
├── .omc-config.json                        ← OMC 設定檔（累積寫入）：
│   {                                         - nodeBinary（plugin-setup）
│     "nodeBinary": "/path/to/node",          - defaultExecutionMode（Phase 2）
│     "defaultExecutionMode": "ultrawork",    - taskTool（Phase 2，若有 beads）
│     "setupCompleted": "2026-...",           - setupCompleted（Phase 4）
│     "setupVersion": "4.9.1"                 - setupVersion（Phase 4）
│   }
│
└── plugins/
    ├── marketplaces/omc/                   ← /plugin marketplace add 的產物
    ├── cache/omc/oh-my-claudecode/
    │   └── 4.9.1/                          ← 外掛根目錄（$CLAUDE_PLUGIN_ROOT）
    │       ├── dist/                        ← 編譯後 JS（含 MCP tools、HUD engine）
    │       ├── agents/*.md                  ← 19 個代理人定義
    │       ├── skills/                      ← 30+ 技能（ralph、team、autopilot 等）
    │       ├── hooks/hooks.json             ← 已修補絕對 node 路徑的 Hook 設定
    │       ├── scripts/*.mjs               ← keyword-detector、skill-injector 等
    │       ├── bridge/cli.cjs              ← `omc` CLI 入口
    │       ├── bridge/mcp-server.cjs       ← MCP 工具伺服器
    │       ├── bridge/team-bridge.cjs      ← tmux 工作者管理
    │       ├── .mcp.json                    ← MCP server 設定
    │       └── node_modules/               ← 依賴（commander、better-sqlite3、zod 等）
    │
    └── installed_plugins.json              ← 外掛登錄表

# 若選擇安裝 omc CLI（Phase 2）
$(npm root -g)/../bin/omc                   ← 全域 CLI 指令（oh-my-claude-sisyphus）
```

#### Phase 2：CLAUDE.md 的特殊處理

`setup-claude-md.sh` 下載 CLAUDE.md 時有智慧合併邏輯：

```bash
# 1. 優先使用 bundled docs/CLAUDE.md（不需網路）
# 2. 若不存在，curl 從 GitHub 下載
# 3. 備份現有 CLAUDE.md → CLAUDE.md.backup.YYYY-MM-DD
# 4. 合併：保留用戶自訂部分（<!-- OMC:START --> 到 <!-- OMC:END --> 以外的內容）
# 5. 在 .git/info/exclude 加入 OMC 忽略規則（local 模式）
```

CLAUDE.md 內的 `<!-- OMC:START -->` 和 `<!-- OMC:END -->` 標記讓 OMC 可以精確更新自己的區段，同時保留用戶的自訂內容。

---

### 安裝流程全景圖（Complete Installation Flow）

```
/plugin marketplace add URL
         │  git clone → ~/.claude/plugins/marketplaces/omc/
         ▼
/plugin install oh-my-claudecode
         │  copy → ~/.claude/plugins/cache/omc/oh-my-claudecode/4.9.1/
         │  run plugin-setup.mjs:
         │    → ~/.claude/hud/omc-hud.mjs
         │    → ~/.claude/settings.json (statusLine)
         │    → ~/.claude/.omc-config.json (nodeBinary)
         │    → hooks.json (patch node path)
         │    → npm install --omit=dev
         ▼
/setup → /omc-setup
    Phase 1:
         │  setup-claude-md.sh global/local
         │    → ~/.claude/CLAUDE.md（或 ./.claude/CLAUDE.md）
         │    → .git/info/exclude（local 模式）
    Phase 2:
         │  hud skill → settings.json (statusLine 確認)
         │  clear old cache versions
         │  npm view latest version
         │  ~/.claude/.omc-config.json (defaultExecutionMode)
         │  npm install -g oh-my-claude-sisyphus → /usr/local/bin/omc
         │  ~/.claude/.omc-config.json (taskTool)
    Phase 3:
         │  /omc-setup → mcp-setup（選用）
         │  settings.json (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)
    Phase 4:
         │  ~/.claude/.omc-config.json (setupCompleted, setupVersion)
         ▼
Claude Code 重啟後生效：
  - HUD 狀態列顯示代理人資訊
  - UserPromptSubmit Hook 開始偵測關鍵字
  - 所有 skills/ 技能可透過 /oh-my-claudecode:xxx 呼叫
  - $CLAUDE_PLUGIN_ROOT 指向 cache/4.9.1/
```

> [!note] 執行時環境變數（Runtime Environment Variable）
> Claude Code 在執行 Hook 腳本時，會自動設定 `CLAUDE_PLUGIN_ROOT` 指向外掛快取目錄（`~/.claude/plugins/cache/omc/oh-my-claudecode/{version}/`）。所有 `hooks.json` 中的 `"$CLAUDE_PLUGIN_ROOT"` 都是用這個環境變數解析路徑。

> [!tip] 為什麼 `plugin-setup.mjs` 要 patch hooks.json 的 `node` 為絕對路徑？
> 因為 Claude Code 執行 Hook 腳本時使用的 shell 環境可能沒有 `nvm`/`fnm` 注入的 PATH，所以 `node` 指令找不到。用 `process.execPath`（安裝時的 Node.js 絕對路徑）確保 Hook 腳本永遠找到正確的 Node.js。

---

---

## src 原始碼深度解析（Source Code Architecture）

> [!important] 本節解析 `src/` 下 31 個模組的功能、編譯方式、執行時間點，以及它們與 CLI 和外掛系統的完整關係。

### src 模組全覽

```
src/                           (851 個 .ts 檔案)
├── agents/                    ← 19 個代理人定義
├── autoresearch/              ← 自主研究合約系統
├── cli/                       ← CLI 命令實作
├── commands/                  ← 指令展開系統（/omc-setup 等）
├── config/                    ← 設定載入與合併
├── constants/                 ← 常數定義
├── features/                  ← 22 個功能模組
├── hooks/                     ← 48 個 Hook 機制
├── hud/                       ← 17 個 HUD 狀態列元件
├── installer/                 ← 安裝器（postinstall 邏輯）
├── interop/                   ← OMC + OMX 互通層
├── lib/                       ← 15 個共用函式庫
├── mcp/                       ← 11 個 MCP 相關模組
├── notifications/             ← 19 個通知系統
├── openclaw/                  ← OpenClaw 閘道整合
├── planning/                  ← 規劃模組
├── platform/                  ← 跨平台相容
├── providers/                 ← 6 個 Git 提供者（GitHub/GitLab/Gitea）
├── ralphthon/                 ← 7 個 Ralphthon 駭客松模組
├── shared/                    ← 共用型別定義
├── skills/                    ← 技能系統（Learner）
├── team/                      ← 56 個 Team 協作模組
├── tools/                     ← 20 個工具定義
├── utils/                     ← 14 個工具函數
├── verification/              ← 驗證系統
└── index.ts                   ← 主要導出入口
```

---

### TypeScript → 執行檔案：完整編譯流程

OMC 使用「雙軌編譯策略」：

```
src/**/*.ts
     │
     ├─── [tsc]（TypeScript 官方編譯器）
     │         → dist/（ES Module，供動態 import 使用）
     │         → 保留 .d.ts 型別宣告、source map
     │
     └─── [esbuild]（Bundler，Scripts: npm run build）
               ├─ build-cli.mjs           → bridge/cli.cjs（2.6 MB）
               ├─ build-mcp-server.mjs    → bridge/mcp-server.cjs（870 KB）
               ├─ build-skill-bridge.mjs  → dist/hooks/skill-bridge.cjs
               ├─ build-team-server.mjs   → bridge/team-mcp.cjs（654 KB）
               ├─ build-runtime-cli.mjs   → bridge/runtime-cli.cjs（213 KB）
               └─ build-bridge-entry.mjs  → bridge/team-bridge.cjs（72 KB）
```

**為什麼要兩種編譯方式？**

| 情境 | 編譯器 | 原因 |
|------|-------|------|
| CLI、MCP server（獨立執行檔） | esbuild | 需要單一自包含 .cjs 檔案，方便分發和執行 |
| Hook 腳本動態載入 | esbuild（→ .cjs）| Hook 腳本用 `require()` 同步載入，需要 CommonJS |
| SDK 函式庫導出 | tsc（→ ESM） | 支援 Tree-shaking，保留型別宣告 |
| 內部模組互相引用 | tsc（→ ESM） | 支援動態 `import()` 和 Source Map 除錯 |

---

### 各模組詳細說明

#### `src/hooks/`（Hook 橋接層）

Hook 系統是 OMC 最核心的執行機制。每個 Claude Code 生命週期事件都對應到一個 TypeScript 模組。

```
src/hooks/
├── bridge.ts                  ← 主橋接層（5,213 行！所有 Hook 事件的路由中心）
├── bridge-normalize.ts        ← Hook 輸入正規化
├── keyword-detector/          ← UserPromptSubmit：魔術關鍵字偵測
├── ralph/                     ← Stop：Ralph 持久循環狀態管理
├── learner/
│   └── bridge.ts              ← 技能學習器（編譯為 dist/hooks/skill-bridge.cjs）
├── permission-handler/        ← PermissionRequest：Bash 權限處理
├── subagent-tracker/          ← SubagentStart/Stop：子代理追蹤與 Session Replay
│   └── session-replay.ts      ← 記錄工具呼叫時間軸
├── todo-continuation/         ← Stop：待辦事項未完成時阻止停止
├── pre-compact/               ← PreCompact：壓縮前儲存狀態
├── setup/                     ← SessionStart init：首次設定
├── session-end/               ← SessionEnd：工作階段結束清理
├── skill-state/               ← 技能啟用狀態管理
├── omc-orchestrator/          ← PreToolUse/PostToolUse：工具執行追蹤
├── mode-registry/             ← 執行模式（ralph/ultrawork）狀態登錄
├── auto-slash-command/        ← 自動斜線指令偵測
├── agent-usage-reminder/      ← 代理人使用提醒
├── beads-context/             ← Beads 任務工具上下文注入
├── background-notification/   ← 背景任務通知
├── codebase-map.ts            ← 代碼庫結構映射
├── comment-checker/           ← 程式碼註解品質檢查
├── directory-readme-injector/ ← 目錄 README 自動注入
├── empty-message-sanitizer/   ← 清理空訊息
└── factcheck/                 ← 事實查核（選用）
```

**執行路徑：**

```
Claude Code 觸發 Hook 事件
         │
         ▼
hooks/hooks.json 中的指令：
  node "$CLAUDE_PLUGIN_ROOT"/scripts/run.cjs "$SCRIPT_PATH"
         │
         ▼
scripts/run.cjs（輕量 resolver）
  ├─ 解析 $CLAUDE_PLUGIN_ROOT
  ├─ 找到最新版本快取目錄
  └─ 動態 require 或 import 目標腳本
         │
         ▼
scripts/keyword-detector.mjs（等各 .mjs）
  ├─ require('dist/hooks/skill-bridge.cjs')  ← 熱路徑（同步載入）
  └─ 執行業務邏輯，輸出 JSON → stdout → Claude Code
```

`bridge.ts` 是所有 Hook 邏輯的路由中心，根據 Hook 類型分派到對應子模組：

```typescript
// bridge.ts 核心路由（簡化）
switch (hookType) {
  case 'UserPromptSubmit': return handleKeywordDetection(input);
  case 'PreToolUse':       return processOrchestratorPreTool(input);
  case 'PostToolUse':      return processOrchestratorPostTool(input);
  case 'SubagentStart':    return trackSubagentStart(input);
  case 'SubagentStop':     return trackSubagentStop(input) + verifyDeliverables(input);
  case 'Stop':             return contextGuardStop(input) + persistentMode(input);
  case 'SessionEnd':       return sessionEnd(input);
  // ...
}
```

---

#### `src/features/`（功能模組）

22 個功能模組，各自解決獨立問題：

```
src/features/
├── magic-keywords.ts          ← 魔術關鍵字處理器（createMagicKeywordProcessor）
├── continuation-enforcement.ts← 強制完成 System Prompt 附加文字
├── auto-update.ts             ← 自動更新檢查與安裝
├── background-tasks.ts        ← 背景任務管理（shouldRunInBackground）
├── delegation-enforcer.ts     ← 代理路由強制執行
├── delegation-routing/        ← 智慧代理路由決策
├── delegation-categories/     ← 代理類別定義
├── model-routing/             ← Haiku/Sonnet/Opus 自動路由
├── boulder-state/             ← Ralph PRD 計劃進度追蹤（.omc/state/boulder.json）
├── context-injector/          ← 上下文自動注入系統（Context Collector）
├── state-manager/             ← 全域狀態管理
├── task-decomposer/           ← 任務自動拆解
├── verification/              ← 任務完成驗證邏輯
├── notepad-wisdom/            ← 記事本智慧（跨 Session 的筆記）
├── builtin-skills/            ← 內建技能（不需外部 .md 檔）
├── background-agent/          ← 背景代理執行
├── rate-limit-wait/           ← 速率限制偵測與等待
├── session-history-search/    ← Session 歷史搜尋（支援 omc session search）
├── auto-update.ts             ← GitHub API 版本檢查
└── index.ts                   ← 統一重新匯出
```

**boulder-state（計劃進度追蹤）** 是 ralph 模式的基礎：

```
.omc/state/boulder.json 儲存：
  - PRD stories 列表
  - 每個 story 的完成狀態
  - 當前迭代次數
  - 計劃名稱和路徑

ralph 執行時每次迭代都讀寫這個檔案，確保跨 Session 持久化
```

**context-injector（上下文注入器）** 實現了「上下文即時注入」：

```typescript
// 任何模組都可以注冊上下文來源
contextCollector.register({
  type: 'project-memory',  // 來源類型
  priority: 'high',        // 注入優先度
  content: memory,         // 上下文內容
});

// Hook 觸發時自動注入到 Claude 的輸入中
injectPendingContext(hookInput);
```

---

#### `src/tools/`（工具定義）

MCP 工具伺服器提供的所有工具，按類別分組：

```
src/tools/
├── lsp/                       ← LSP（語言伺服器協議）工具（12 個）
│   ├── client.ts              ← LSP 客戶端（連接 TypeScript/Python LSP）
│   ├── servers.ts             ← 語言伺服器發現（tsserver、pylsp 等）
│   ├── utils.ts               ← 符號搜尋、診斷格式化
│   └── index.ts               ← 工具定義導出
├── python-repl/               ← Python REPL 工具
│   ├── bridge-manager.ts      ← Python 進程管理
│   ├── socket-client.ts       ← Unix socket 通信
│   ├── session-lock.ts        ← 工作階段鎖定（防衝突）
│   └── tool.ts                ← MCP 工具定義
├── ast-tools.ts               ← AST 語法樹搜尋（ast-grep）
├── state-tools.ts             ← state_read/write/clear/list_active
├── memory-tools.ts            ← project_memory_read/write/add_note
├── notepad-tools.ts           ← notepad_read/write_priority/working
├── skills-tools.ts            ← 技能清單/新增/搜尋
├── shared-memory-tools.ts     ← 跨代理人共享記憶體
├── session-history-tools.ts   ← 工作階段歷史搜尋工具
├── deepinit-manifest.ts       ← deepinit 增量清單工具
├── lsp-tools.ts               ← LSP 工具集整合
└── types.ts                   ← 工具型別定義
```

**LSP 工具（12 個）完整列表：**

| 工具名稱 | 功能 | 用途 |
|---------|------|------|
| `lsp_hover` | 取得符號型別資訊 | 理解程式碼 |
| `lsp_goto_definition` | 跳轉定義 | 追蹤符號來源 |
| `lsp_find_references` | 找出所有引用 | 影響分析 |
| `lsp_diagnostics` | 單一檔案型別錯誤 | 代碼品質 |
| `lsp_diagnostics_directory` | 整個專案型別檢查 | CI 驗證 |
| `lsp_document_symbols` | 檔案符號大綱 | 快速理解結構 |
| `lsp_workspace_symbols` | 跨專案符號搜尋 | 定位程式碼 |
| `lsp_complete` | 自動補全建議 | 程式碼生成 |
| `lsp_rename` | 符號重命名 | 安全重構 |
| `lsp_format` | 格式化程式碼 | 代碼品質 |
| `lsp_code_action` | 快速修復建議 | 自動修復 |
| `lsp_servers` | 列出可用語言伺服器 | 環境診斷 |

**Python REPL 工具** 使用 Unix socket 通信，讓代理人可以執行 Python 代碼並保持工作階段狀態（變數在多次呼叫間持久化）。

---

#### `src/mcp/`（MCP 工具伺服器）

```
src/mcp/
├── omc-tools-server.ts        ← 主 MCP 工具伺服器（→ bridge/mcp-server.cjs）
├── team-server.ts             ← Team 協作 MCP（→ bridge/team-mcp.cjs）
├── standalone-server.ts       ← 獨立 MCP 伺服器（→ dist/mcp/）
├── servers.ts                 ← MCP 伺服器工廠（exa、context7 整合）
└── omc-tools.ts               ← 工具分組定義
```

**工具分組與禁用機制：**

```
環境變數 OMC_DISABLE_TOOLS=lsp,python
                │
                ▼
omc-tools-server.ts 讀取後
  跳過對應工具群組的初始化
  LSP tools   → 不初始化 LSP client（節省記憶體）
  Python tools → 不啟動 Python bridge 進程
```

`omc-tools-server.ts` 編譯後的 `bridge/mcp-server.cjs` 在 Claude Code 啟動時被 `.mcp.json` 自動載入：

```json
// .mcp.json
{
  "mcpServers": {
    "t": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/bridge/mcp-server.cjs"]
    }
  }
}
```

這就是 Claude Code 中 `lsp_hover`、`ast_grep_search` 等工具可用的原因。

---

#### `src/hud/`（HUD 狀態列）

```
src/hud/
├── index.ts                   ← HUD 入口（讀 stdin JSON → 輸出狀態列文字）
├── state.ts                   ← HUD 狀態讀寫（.omc/state/hud.json）
├── render.ts                  ← 狀態列渲染引擎
├── usage-api.ts               ← Anthropic API 使用量統計
├── transcript.ts              ← 對話記錄解析（.claude/projects/xxx/*.jsonl）
├── omc-state.ts               ← 讀取 Ralph/Ultrawork/PRD 狀態
├── mission-board.ts           ← 任務看板（多個 Team 的合併視圖）
├── background-tasks.ts        ← 背景任務追蹤（HUD 層）
├── custom-rate-provider.ts    ← 自訂速率顯示
└── elements/                  ← 25 個 HUD UI 元件
    ├── agent-dashboard.ts     ← 代理人儀表板
    ├── rate-limit-indicator.ts← 速率限制指示器
    ├── token-usage.ts         ← Token 用量顯示
    ├── ralph-progress.ts      ← Ralph 進度條
    └── ...
```

**HUD 的完整資料流：**

```
Claude Code 渲染狀態列（每幾秒一次）
         │
         ▼
執行 settings.json 中的 statusLine.command：
  node ~/.claude/hud/omc-hud.mjs
         │
         ▼
omc-hud.mjs → 載入 dist/hud/index.js
         │
         ├─ 讀取 .omc/state/hud.json（代理人狀態）
         ├─ 讀取 .omc/state/boulder.json（Ralph PRD 進度）
         ├─ 讀取 .claude/projects/xxx/*.jsonl（Token 用量）
         ├─ 可選：呼叫 Anthropic Usage API（速率限制資訊）
         │
         ▼
render.ts → 組合各個 elements/
         │
         ▼
stdout → 一行文字 → Claude Code 狀態列顯示
```

---

#### `src/agents/`（代理人定義）

```
src/agents/
├── definitions.ts             ← 所有代理人的彙總定義
├── analyst.ts                 ← 需求分析代理（Opus）
├── architect.ts               ← 架構設計代理（Opus）
├── critic.ts                  ← 批評評審代理（Opus）
├── debugger.ts                ← 除錯根因分析（Sonnet）
├── designer.ts                ← UI/UX 設計（Sonnet）
├── document-specialist.ts     ← 文件查詢（Sonnet）
├── executor.ts                ← 程式碼實作（Sonnet）
├── explore.ts                 ← 代碼庫探索（Haiku）
├── planner.ts                 ← 任務規劃（Opus）
├── qa-tester.ts               ← QA 測試（Sonnet，含 tmux）
├── scientist.ts               ← 實驗與假設驗證（Sonnet）
├── tracer.ts                  ← 代理人追蹤（Sonnet）
├── writer.ts                  ← 文件撰寫（Haiku）
├── prompt-helpers.ts          ← 提示工程輔助函式
├── prompt-sections/           ← 可重用的提示片段
├── templates/                 ← 代理人提示範本
├── types.ts                   ← 代理人型別定義
├── utils.ts                   ← 代理人工具函式
└── index.ts                   ← 統一導出
```

**代理人的三層模型路由：**

```typescript
// src/agents/types.ts
type AgentCategory = 'LOW' | 'MEDIUM' | 'HIGH';

// LOW  → claude-haiku    (快速查詢、文件撰寫)
// MEDIUM → claude-sonnet (標準實作、除錯)
// HIGH → claude-opus     (架構、深度分析)

// 自動路由邏輯：
// 環境變數 > 代理人預設 > 任務複雜度推斷
```

**代理人定義的產生方式：** `definitions.ts` 從 `agents/*.md` 讀取 Markdown 提示，結合 TypeScript 型別定義，產生 Claude Agent SDK 需要的 `agents` 物件。

---

#### `src/config/`（設定系統）

```
src/config/
├── loader.ts                  ← 設定載入、合併、驗證
├── models.ts                  ← 模型層級（HIGH/MEDIUM/LOW）設定
├── plan-output.ts             ← 計劃輸出路徑解析
└── index.ts                   ← 統一導出
```

**設定優先層次（高到低）：**

```
1. 環境變數（OMC_MODEL_HIGH、OMC_DISABLE_TOOLS 等）
2. .claude/omc.jsonc（專案設定）
3. ~/.config/claude-omc/config.jsonc（使用者全域設定）
4. 內建預設值
```

`loader.ts` 同時處理 CLAUDE.md 的精簡版本提取（`compactOmcStartupGuidance`），讓 Hook 腳本不需要讀取完整的 CLAUDE.md 就能取得關鍵設定。

---

#### `src/team/`（Team 協作系統，56 個模組）

這是最大的模組群，實作了完整的多代理人 Team 協作：

```
src/team/
├── bridge-entry.ts            ← Team tmux bridge（→ bridge/team-bridge.cjs）
├── runtime-cli.ts             ← Team runtime CLI（→ bridge/runtime-cli.cjs）
├── team-state/                ← Team 狀態機（SQLite or JSON）
│   ├── sqlite-store.ts        ← SQLite 後端（高效能）
│   └── json-store.ts         ← JSON 後端（回退）
├── worker/                    ← Worker 代理人啟動邏輯
│   ├── spawn-claude.ts        ← 啟動 Claude CLI worker
│   ├── spawn-codex.ts         ← 啟動 Codex CLI worker
│   └── spawn-gemini.ts        ← 啟動 Gemini CLI worker
├── messaging/                 ← 代理人間通信（SendMessage）
├── task-tracker/              ← 共享任務清單（TaskCreate/TaskList）
├── heartbeat/                 ← Worker 存活偵測
├── monitor/                   ← 整體 Team 監控
└── mission-board/             ← 任務看板整合
```

**Team 的三種後端模式：**

```
omc team 3:claude "task"    → Claude CLI workers（tmux 視窗）
omc team 2:codex "task"     → Codex CLI workers（tmux 視窗）
/team 3:executor "task"     → Claude Code native Teams（CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1）
```

---

#### `src/notifications/`（通知系統）

```
src/notifications/
├── telegram.ts                ← Telegram Bot API
├── discord.ts                 ← Discord Webhook / Bot
├── slack.ts                   ← Slack Incoming Webhook
├── file.ts                    ← 檔案輸出（Markdown/JSON）
├── profile-manager.ts         ← 多設定檔管理
└── tag-parser.ts              ← 標記解析（@alice、@here 等）
```

通知在 `Stop` Hook（`session-end.mjs`）中觸發，讀取 `~/.claude/.omc-config.json` 中的設定後發送。

---

### 完整「原始碼 → 編譯產物 → 執行時間點」映射表

```
src/                          編譯方式    產物                        執行時機
─────────────────────────────────────────────────────────────────────────────
index.ts                      tsc ESM     dist/index.js               CLI啟動/MCP載入
agents/definitions.ts         tsc ESM     dist/agents/definitions.js  createOmcSession()
config/loader.ts              tsc ESM     dist/config/loader.js       所有啟動時
hooks/bridge.ts               tsc ESM     dist/hooks/bridge.js        Hook腳本動態import
hooks/learner/bridge.ts       esbuild CJS dist/hooks/skill-bridge.cjs Hook腳本同步require
hud/index.ts                  tsc ESM     dist/hud/index.js           statusLine指令
tools/lsp-tools.ts            tsc ESM     dist/tools/lsp-tools.js     MCP工具呼叫
tools/python-repl/            tsc ESM     dist/tools/python-repl/     MCP工具呼叫
mcp/omc-tools-server.ts       esbuild CJS bridge/mcp-server.cjs       Claude Code啟動時（.mcp.json）
mcp/team-server.ts            esbuild CJS bridge/team-mcp.cjs         omc team 啟動時
team/bridge-entry.ts          esbuild CJS bridge/team-bridge.cjs      tmux worker 啟動時
team/runtime-cli.ts           esbuild CJS bridge/runtime-cli.cjs      omc team runtime
cli/index.ts                  esbuild CJS bridge/cli.cjs              $ omc 執行
installer/index.ts            tsc ESM     dist/installer/index.js     npm install postinstall
features/magic-keywords.ts    tsc ESM     dist/features/              createOmcSession()
features/boulder-state/       tsc ESM     dist/features/boulder-state/ Hook執行時讀寫
features/context-injector/    tsc ESM     dist/features/context-injector/ Hook執行時注入
autoresearch/runtime.ts       tsc ESM     dist/autoresearch/           omc autoresearch
ralphthon/*.ts                esbuild CJS bridge/cli.cjs內嵌           omc ralphthon
```

---

### 資料流總覽：src 模組如何協同工作

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        執行層級與 src 模組對應                            │
└──────────────────────────────────────────────────────────────────────────┘

Layer 0：Claude Code 宿主
  └─ 讀取 .mcp.json → 啟動 bridge/mcp-server.cjs（src/mcp/omc-tools-server.ts）
  └─ 讀取 hooks/hooks.json → 在事件觸發時執行 scripts/*.mjs

Layer 1：Hook 執行層（scripts/*.mjs）
  └─ require('dist/hooks/skill-bridge.cjs')  ← src/hooks/learner/bridge.ts
     └─ 技能觸發、關鍵字偵測、上下文注入
  └─ import('dist/index.js')                 ← src/index.ts
     └─ 完整功能存取（boulder state、project memory、context injector）

Layer 2：MCP 工具層（bridge/mcp-server.cjs）
  └─ lsp/client.ts      → lsp_hover、lsp_diagnostics 等 12 個工具
  └─ ast-tools.ts       → ast_grep_search、ast_grep_replace
  └─ python-repl/       → python_repl（保持 Session 變數）
  └─ state-tools.ts     → state_read/write（持久化 Team 狀態）
  └─ memory-tools.ts    → project_memory_*（跨 Session 記憶）
  └─ notepad-tools.ts   → notepad_*（計劃筆記）

Layer 3：HUD 渲染層（dist/hud/index.js）
  └─ omc-state.ts       ← 讀取 ralph/ultrawork 狀態
  └─ transcript.ts      ← 解析 .claude/projects/xxx/*.jsonl
  └─ usage-api.ts       ← Anthropic API 用量
  └─ render.ts          ← 組合 25 個 elements/ 輸出一行文字

Layer 4：CLI 控制層（bridge/cli.cjs）
  └─ cli/launch.ts      ← 環境注入 + tmux 啟動
  └─ cli/wait.ts        ← 速率限制 Daemon
  └─ cli/teleport.ts    ← git worktree 建立
  └─ cli/team.ts        ← tmux worker 管理
  └─ autoresearch/      ← keep/discard/reset 研究迴圈
  └─ ralphthon/         ← 多 Session 駭客松編排

Layer 5：狀態持久化
  .omc/state/boulder.json     ← features/boulder-state/（Ralph PRD 進度）
  .omc/state/hud.json         ← hud/state.ts（HUD 顯示狀態）
  .omc/state/team-state.json  ← team/team-state/（Team 任務清單）
  .omc/project-memory.json    ← tools/memory-tools.ts（專案記憶）
  .omc/notepad.md             ← tools/notepad-tools.ts（計劃筆記）
  ~/.claude/.omc-config.json  ← config/loader.ts（使用者偏好）
```

> [!note] 關鍵洞察
> `src/` 的程式碼**從不直接執行**，它們都被編譯成 `dist/` 或 `bridge/` 後才被使用。真正的執行入口只有四個：`bridge/cli.cjs`（CLI）、`bridge/mcp-server.cjs`（MCP）、`scripts/*.mjs`（Hooks）、`dist/hud/index.js`（HUD）。其餘全部是被這四個入口按需動態載入的函式庫模組。

---

## 待補充（Open Questions）

- OMC 宣稱多模型路由（Haiku/Sonnet/Opus 三層）能節省 30-50% API 成本，這個數字有沒有具體的測量方法或對照實驗支撐？在不同任務類型下節省比例差異有多大？（建議搜尋：`multi-model routing cost savings measurement LLM tiered pricing`）
- `omc wait` 的速率限制（Rate Limit）偵測與自動恢復機制是如何判斷 Claude Code 工作階段已進入速率限制狀態的？偵測的可靠性有多高？（建議搜尋：`claude code rate limit detection programmatic recovery`）
- `ralph` 模式的「連續 3 波都乾淨才宣告完成」這個終止條件實際使用中是否常常不收斂？有沒有社群回報的無限迴圈（infinite loop）案例？（建議搜尋：`oh-my-claudecode ralph infinite loop convergence issues`）
- OMC 的 LSP 工具整合（`lsp_hover`、`lsp_diagnostics` 等）需要本地有 Language Server（如 TypeScript LSP）運行，設定複雜度如何？支援哪些程式語言的 LSP？（建議搜尋：`oh-my-claudecode LSP integration setup supported languages`）
- OMC 的 Python REPL 工具使用 Unix Socket 保持工作階段狀態，這在 Claude Code 工作階段結束後是否能自動清理？長期使用是否有記憶體洩漏風險？（建議搜尋：`claude code MCP python repl unix socket cleanup memory leak`）
- `omc autoresearch` 的「keep/discard/reset」決策是由人類決定還是由 AI evaluator 自動決定？若由 AI 決定，評估器（evaluator）的提示詞設計如何影響結果品質？（建議搜尋：`autonomous research loop AI evaluator design prompt engineering`）

## 相關連結（Related）

- [[CLAUDE-CODE-HOOKS]] — OMC 深度依賴 Claude Code Hook 系統
- [[MULTI-AGENT-ORCHESTRATION]] — Team pipeline 是多代理人編排（Multi-agent Orchestration）的具體實現
- [[MCP-MODEL-CONTEXT-PROTOCOL]] — OMC 的工具伺服器基於 MCP 協議
- [[OH-MY-OPENCODE]] — 原始靈感來源，OpenCode 版本的同類工具

## References

- [GitHub Repo](https://github.com/Yeachan-Heo/oh-my-claudecode)
- [官方文件](https://yeachan-heo.github.io/oh-my-claudecode-website)
- [npm 套件（oh-my-claude-sisyphus）](https://www.npmjs.com/package/oh-my-claude-sisyphus)
- [ARCHITECTURE.md](https://github.com/Yeachan-Heo/oh-my-claudecode/blob/main/docs/ARCHITECTURE.md)
