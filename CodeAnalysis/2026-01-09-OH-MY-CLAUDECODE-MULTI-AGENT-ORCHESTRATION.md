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
