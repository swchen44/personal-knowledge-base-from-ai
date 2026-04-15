---
title: "Claude Code Skill Frontmatter 原始碼深度解析：context:fork、agent、hooks 的運作原理與 FAQ"
date: 2026-04-16
category: DevTools
tags:
  - "#devtools/claude-code"
  - "#ai/agent-architecture"
  - "#devtools/configuration"
  - "#ai/prompt-engineering"
source: "conversation"
source_type: article
author: "swchen44 + Claude"
status: notes
links:
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]]"
  - "[[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]]"
  - "[[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]]"
---

## 摘要（Summary）

深入追蹤 Claude Code 反編譯原始碼，解析 SKILL.md YAML frontmatter 中三個進階欄位的內部運作原理：`context: fork`（隔離執行）、`agent:`（代理人選擇）、`hooks:`（事件鉤子）。核心發現：**fork 模式建立完全隔離的上下文**，agent 欄位控制模型、工具集和 CLAUDE.md 是否載入，而 **skill hooks 在被呼叫後持續生效直到 session 結束**（非一次性），多個 skill 的 hooks 會累積。本文基於 `SkillTool.ts`、`forkedAgent.ts`、`loadSkillsDir.ts`、`registerSkillHooks.ts` 等原始碼的逐行追蹤。

## 關鍵洞察（Key Insights）

- **`context: fork` 建立完全隔離的對話**：獨立的 readFileState（clone）、abort controller、messages，skill 內容變成 user message 傳給子代理人，只回傳文字摘要 — 參見 [[CLAUDE-CODE-SUBAGENT-ARCHITECTURE]]
- **`agent:` 欄位控制五個維度**：模型、工具集（白名單/黑名單）、CLAUDE.md 是否載入、effort、permission mode。Explore agent 用 Haiku + 唯讀工具 + 省略 CLAUDE.md
- **Skill hooks 在呼叫後持續存在直到 session 結束**：不是一次性的，不會在呼叫其他 skill 時消失。多個 skill 的 hooks 會累積。唯一清除時機是 `once: true`（成功後移除）或 session 結束
- **Hooks 有四種類型**：`command`（Shell）、`prompt`（LLM 評估）、`http`（Webhook）、`agent`（代理人驗證器），全部支援 `if` 條件過濾和 `once` 一次性執行

## 詳細內容（Details）

### 一、Skill 被呼叫時的分岔點：Inline vs Fork

```typescript
// SkillTool.ts:623
if (command?.type === 'prompt' && command.context === 'fork') {
    return executeForkedSkill(...)   // ← Fork 模式
}
// 否則走 Inline 模式
const processedCommand = await processPromptSlashCommand(...)
```

**Inline 模式（預設）**

```
用戶/模型 呼叫 /my-skill
  │
  ▼
SkillTool.call()
  │
  └── processPromptSlashCommand()
        │
        ├── getPromptForCommand()  ← 從閉包取出完整 SKILL.md
        └── 回傳 newMessages       ← 注入主對話
              │
              ▼
        主模型繼續處理（使用全部工具，佔用主上下文）
```

**Fork 模式（`context: fork`）**

```
用戶/模型 呼叫 /deep-research
  │
  ▼
SkillTool.call()
  │
  └── command.context === 'fork'  ← 分岔！
        │
        ▼
  executeForkedSkill()
        │
        ├── prepareForkedCommandContext()
        │     ├── getPromptForCommand()          ← 取得完整內容
        │     ├── command.agent → 決定 agent     ← 預設 'general-purpose'
        │     ├── parseToolListFromCLI()         ← 解析 allowed-tools
        │     └── createUserMessage(skillContent) ← 內容變成 user message
        │
        └── runAgent({
              agentDefinition,          ← agent 配置
              promptMessages: [skillContent],
              model: command.model,
            })
              │
              ▼
          獨立的對話循環
              │
              └── 完成 → extractResultText()
                    │
                    ▼
              只回傳文字摘要到主對話
```

> [!important] Fork 的隔離程度
> Fork 建立完全獨立的環境（`forkedAgent.ts:306-310`）：
> - `readFileState`：clone（獨立副本）
> - `nestedMemoryAttachmentTriggers`：全新 Set
> - `abortController`：child（連結到 parent，但獨立）
> - `setAppState`：no-op（隔離，不影響主對話）

#### Inline vs Fork 完整比較

```
┌──────────────────┬───────────────────────┬───────────────────────┐
│      面向         │    Inline（預設）      │   Fork（context:fork）│
├──────────────────┼───────────────────────┼───────────────────────┤
│ 上下文            │ 共享主對話            │ 獨立隔離              │
│ 工具集            │ 主模型的全部工具      │ agent 定義的工具       │
│ 模型              │ 主模型                │ agent 定義的模型       │
│ CLAUDE.md         │ 已載入（主對話有）    │ 視 agent 設定          │
│ 結果回傳          │ 注入對話 continuation │ 只回傳文字摘要         │
│ Token 消耗        │ 佔用主上下文          │ 獨立計算              │
│ 可使用的工具      │ 全部（含 Edit/Write） │ 可限制為唯讀           │
│ readFileState     │ 共享                  │ clone（獨立副本）      │
│ 適用場景          │ 需要修改檔案的任務    │ 純研究/分析任務        │
└──────────────────┴───────────────────────┴───────────────────────┘
```

### 二、`agent:` 欄位的作用

```typescript
// forkedAgent.ts:212-217
const agentTypeName = command.agent ?? 'general-purpose'
const baseAgent =
    agents.find(a => a.agentType === agentTypeName) ??
    agents.find(a => a.agentType === 'general-purpose') ??
    agents[0]
```

`agent:` 決定 fork 執行時使用的 **AgentDefinition**，控制以下維度：

| agent 值 | 模型 | 工具集 | CLAUDE.md | 適用場景 |
|---------|------|--------|-----------|---------|
| `Explore` | Haiku（外部） | 唯讀（禁止 Agent/Edit/Write/NotebookEdit） | ❌ 省略 | 程式碼搜尋 |
| `Plan` | 同 Explore | 同 Explore | ❌ 省略 | 架構設計 |
| `general-purpose`（預設） | inherit | 全部工具 | ✅ 載入 | 完整任務 |
| 自訂（`.claude/agents/*.md`） | 由 frontmatter 定義 | 由 `tools:`/`disallowedTools:` 定義 | 視設定 | 客製化 |

**Explore agent 的具體限制**（`exploreAgent.ts:64-83`）：

```typescript
export const EXPLORE_AGENT: BuiltInAgentDefinition = {
    agentType: 'Explore',
    disallowedTools: [
        'Agent',          // 不能再 spawn sub-agent
        'ExitPlanMode',
        'Edit',           // 不能編輯檔案
        'Write',          // 不能寫入檔案
        'NotebookEdit',
    ],
    model: 'haiku',       // 外部用戶用 Haiku（快速便宜）
    omitClaudeMd: true,   // 省略 CLAUDE.md（省 5-15 Gtok/week）
}
```

> [!tip] 何時選哪個 agent
> - **純搜尋/研究**：`agent: Explore` — Haiku 快速、唯讀安全、不佔主上下文
> - **需要寫檔案**：不設 `agent:` 或 `agent: general-purpose` — 用 inline 更好
> - **背景長任務**：`context: fork` + `agent: general-purpose` + skill frontmatter 設 `background: true`

#### AgentDefinition 的完整控制欄位

```typescript
// loadAgentsDir.ts:106-133
type BaseAgentDefinition = {
    agentType: string           // agent 名稱
    whenToUse: string          // 描述
    tools?: string[]           // 允許的工具（白名單）
    disallowedTools?: string[] // 禁止的工具（黑名單）
    skills?: string[]          // 預載的 skills
    mcpServers?: AgentMcpServerSpec[]  // 專屬 MCP servers
    hooks?: HooksSettings      // 專屬 hooks
    model?: string             // 模型
    effort?: EffortValue       // 思考努力程度
    permissionMode?: PermissionMode    // 權限模式
    maxTurns?: number          // 最大對話輪數
    omitClaudeMd?: boolean     // 是否省略 CLAUDE.md
    memory?: AgentMemoryScope  // 持久記憶範圍
    isolation?: 'worktree' | 'remote'  // 隔離模式
    background?: boolean       // 背景執行
}
```

### 三、`hooks:` 欄位 — Skill 被呼叫後註冊到 Session

#### 註冊流程

```
用戶/模型 呼叫 /my-skill
  │
  ▼
processPromptSlashCommand()    ← processSlashCommand.tsx:877
  │
  └── registerSkillHooks(hooks, skillName, skillRoot)
        │                       ← registerSkillHooks.ts:20
        ├── 遍歷 hooks 的每個事件（PreToolUse, PostToolUse...）
        │
        └── addSessionHook(event, matcher, hook, onHookSuccess, skillRoot)
              │
              ▼
        hooks 存入 AppState.sessionHooks
        → 從此刻起持續生效，直到 session 結束
```

#### 四種 Hook 類型

```yaml
hooks:
  PostToolUse:
    - matcher: "Write"
      hooks:
        # 類型 1：Shell 命令（Command Hook）
        - type: command
          command: "eslint --fix $FILE"
          if: "Write(*.ts)"      # 進一步過濾
          timeout: 30            # 秒
          shell: bash            # 或 powershell
          async: true            # 非阻塞執行
          once: false            # 持續觸發
          statusMessage: "Running ESLint..."

        # 類型 2：LLM Prompt Hook
        - type: prompt
          prompt: "檢查 $ARGUMENTS 是否遵守規範"
          model: "claude-haiku-4-5-20251001"

        # 類型 3：HTTP Webhook
        - type: http
          url: "https://my-server.com/hook"
          headers:
            Authorization: "Bearer $MY_TOKEN"
          allowedEnvVars: ["MY_TOKEN"]

        # 類型 4：Agent 驗證器
        - type: agent
          prompt: "驗證單元測試是否通過"
          model: "claude-sonnet-4-6"
```

#### 可用的 Hook 事件（31 種）

| 事件 | 觸發時機 | 常用場景 |
|------|---------|---------|
| `PreToolUse` | 工具執行**前**（可阻止） | 攔截危險操作 |
| `PostToolUse` | 工具執行**後** | 自動 lint/format |
| `PostToolUseFailure` | 工具執行失敗後 | 錯誤通知 |
| `UserPromptSubmit` | 用戶送出提示前 | 輸入驗證 |
| `SessionStart` | Session 啟動 | 環境初始化 |
| `SessionEnd` | Session 結束 | 清理資源 |
| `SubagentStart` / `SubagentStop` | 子代理人生命週期 | 監控 |
| `PreCompact` / `PostCompact` | 上下文壓縮前後 | 記錄壓縮事件 |
| `FileChanged` | 檔案變更 | 自動重新載入 |
| `ConfigChange` | 設定變更 | 動態反應 |

（完整列表：PreToolUse, PostToolUse, PostToolUseFailure, Notification, UserPromptSubmit, SessionStart, SessionEnd, Stop, StopFailure, SubagentStart, SubagentStop, PreCompact, PostCompact, PermissionRequest, PermissionDenied, Setup, TeammateIdle, TaskCreated, TaskCompleted, Elicitation, ElicitationResult, ConfigChange, WorktreeCreate, WorktreeRemove, InstructionsLoaded, CwdChanged, FileChanged）

#### `matcher` 和 `if` 的雙層過濾

```
事件觸發（如 PostToolUse）
  │
  ▼
第一層：matcher 粗篩
  └── "Write" → 只在 Write 工具觸發時進入
        │
        ▼
第二層：if 細篩（Permission Rule 語法）
  └── "Write(*.tsx)" → 只在寫 .tsx 檔時執行 hook
        │
        ▼
執行 hook（command / prompt / http / agent）
```

### 四、FAQ：Skill Hooks 常見問題

> [!faq]- Q1：Skill 的 hooks 是一次性的嗎？呼叫其他 Skill 後會消失嗎？
> **不是一次性的。** Hooks 在 skill 被呼叫後註冊到 `AppState.sessionHooks`，會**持續存在直到 session 結束**。呼叫其他 skill 不會清除之前 skill 的 hooks。
> 
> ```
> /lint-on-save     ← 註冊 PostToolUse hook
>   ▼
> Edit 某檔案       ← hook 觸發！
>   ▼
> /kb-create URL    ← 呼叫其他 skill（hook 仍存在）
>   ▼
> Write 某檔案      ← hook 仍然觸發！
>   ▼
> /exit             ← Session 結束，hooks 全部清除
> ```
> 
> 原始碼證據：`clearSessionHooks()` 只在 `executeSessionEndHooks()`（session 結束）和 `runAgent()` finally（子代理人結束）中被呼叫，不在 skill 完成時被呼叫。

> [!faq]- Q2：多個 Skill 的 hooks 會互相衝突嗎？
> **不會衝突，但會累積。** 每個 skill 呼叫都會 `addSessionHook()`，不會移除之前的。例如 Skill A 掛了 eslint，Skill B 掛了 prettier，兩個都呼叫後，每次 Write 都會同時跑 eslint 和 prettier。

> [!faq]- Q3：如何讓 hook 只觸發一次？
> 在 hook 中設定 `once: true`。第一次成功執行後自動 `removeSessionHook()`：
> ```typescript
> // registerSkillHooks.ts:36-42
> const onHookSuccess = hook.once
>     ? () => { removeSessionHook(setAppState, sessionId, eventName, hook) }
>     : undefined
> ```

> [!faq]- Q4：Skill hooks 和 settings.json hooks 有什麼差異？
> | 面向 | Skill Hooks | Settings.json Hooks |
> |------|------------|-------------------|
> | 生效時機 | Skill 被呼叫後才註冊 | Session 啟動時自動註冊 |
> | 持久性 | Session 內有效 | 永久 |
> | 管理方式 | 封裝在 SKILL.md | 分散在 settings.json |
> | 可分享性 | 跟 Skill 一起安裝/分享 | 需手動複製設定 |
> | `CLAUDE_PLUGIN_ROOT` | ✅ 可用 | ❌ |

> [!faq]- Q5：`context: fork` + `agent: Explore` 的 skill 可以修改檔案嗎？
> **不行。** Explore agent 的 `disallowedTools` 明確禁止 Edit 和 Write。嘗試寫檔案會失敗。如果需要修改檔案，使用 inline 模式或 `agent: general-purpose`。

> [!faq]- Q6：fork 模式的結果如何回到主對話？
> Fork 完成後，`extractResultText()` 從子代理人的最後一則 assistant message 提取文字，以 `tool_result` 格式回傳：
> ```
> Skill "deep-research" completed (forked execution).
> 
> Result:
> {子代理人的最後回覆文字}
> ```
> 主對話只看到這段摘要，不會看到子代理人的中間過程。

### 五、完整 Frontmatter 欄位總覽

```yaml
---
# === 基本資訊 ===
name: my-skill              # 顯示名稱（Display Name）
description: "做什麼用的"     # 描述（給模型判斷用）
when_to_use: "何時該用"      # 觸發提示（When to Use）
version: "1.0"              # 版本號

# === 執行控制 ===
context: fork               # 執行模式：fork（隔離）| 省略（inline）
agent: Explore              # 搭配 fork 使用的 agent 類型
model: claude-sonnet-4-6    # 覆蓋預設模型
effort: high                # 思考努力程度
shell: bash                 # 預設 shell

# === 工具與安全 ===
allowed-tools:              # 允許的額外工具
  - "Bash(npm *)"
  - "Write"
disable-model-invocation: false  # 禁止模型主動呼叫
user-invocable: true        # 用戶可用 /name 呼叫

# === 條件觸發 ===
paths:                      # 只在操作匹配檔案時出現在 skill_listing
  - "src/components/**"

# === 參數 ===
arguments: ["query", "scope"]    # 命名參數
argument-hint: "<query> [scope]" # 參數提示

# === Hooks — 呼叫後註冊到 session ===
hooks:
  PostToolUse:
    - matcher: "Write"
      hooks:
        - type: command
          command: "eslint --fix ${TOOL_INPUT_file_path}"
          if: "Write(*.ts)"
          timeout: 15
          async: true
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "echo 'About to run bash command'"
          if: "Bash(rm *)"  # 只在刪除指令前觸發
---
```

### 六、Token 與速度的取捨

| 模式 | Token 成本 | 速度 | 結果品質 | 適用場景 |
|------|-----------|------|---------|---------|
| Inline | 高（佔主上下文） | 快 | 高 | 修改檔案、執行任務 |
| Fork + general-purpose | 高（獨立上下文） | 慢 | 高 | 完整背景任務 |
| Fork + Explore | **低**（Haiku + 無 CLAUDE.md） | **最快** | 中 | 搜尋/分析 |
| Fork + Plan | **低** | **最快** | 中 | 架構設計 |

## 我的心得（My Takeaways）

1. **Skill hooks 的累積特性是雙面刃**：好處是可以逐步建立自動化工作流（呼叫一個 skill 註冊 linter，呼叫另一個註冊 formatter）；風險是忘記自己掛了什麼 hooks，導致意外的副作用。建議控制每個 skill 的 hooks 數量，並在 skill description 中說明會註冊哪些 hooks。
2. **`context: fork` + `agent: Explore` 是被低估的組合**：用 Haiku 模型快速搜尋程式碼，結果只佔主上下文的一段摘要。適合在需要大量搜尋的工作流中使用。
3. **`once: true` 適合初始化型任務**：例如「首次呼叫時安裝依賴」或「首次呼叫時建立目錄結構」——只需執行一次，之後自動移除。

## 待補充（Open Questions）

- Fork 模式下的 skill hooks 是註冊在主 session 還是子代理人的 session？如果是子代理人，hooks 是否在 fork 結束時就被清除？建議搜尋：`registerSkillHooks fork agentId sessionId`
- `asyncRewake: true` 的 hook 在 exit code 2 時「喚醒模型」的具體機制是什麼？建議搜尋：`asyncRewake hook exit code 2 rewake`
- 多個 skill 的 hooks 在同一事件上累積時，執行順序是什麼？先註冊先執行還是有其他優先級？建議搜尋：`sessionHooks execution order multiple matchers`
- `agent` hook 類型的驗證邏輯有多深？它是用什麼標準來判斷「通過/失敗」？建議搜尋：`execAgentHook verdict pass fail`
- 是否有辦法在不結束 session 的情況下手動清除特定 skill 的 hooks？建議搜尋：`removeSessionHook manual trigger slash command`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，確立基礎知識 | `context: fork`、`agent: Explore`、`addSessionHook()`、`clearSessionHooks()`、`once: true`、`disallowedTools`、`omitClaudeMd` — 七個核心 API |
| **理解（半被動）** | 解釋概念的含義及關聯 | Fork 建立隔離環境是為了保護主上下文不被搜尋結果淹沒；hooks 累積是因為它們綁在 session 而非 skill；Explore 用 Haiku 是為了速度和成本；`omitClaudeMd` 是因為唯讀 agent 不需要寫程式碼的規範 |
| **分析（主動）** | 檢驗論點、找出假設 | 假設「唯讀 agent 不需要 CLAUDE.md」——但某些 CLAUDE.md 規則（如語言偏好、回答風格）可能對搜尋結果的呈現方式有影響。另外假設「hooks 累積不會導致效能問題」——如果註冊了 30 個 hooks，每次工具呼叫都會遍歷所有 matchers |
| **應用（主動）** | 規劃執行方案 | (1) 為常用的搜尋任務建立 `context: fork` + `agent: Explore` 的 skill；(2) 用 `once: true` hooks 實作「首次初始化」工作流；(3) 在 skill description 中註明會掛哪些 hooks |
| **評估（主動）** | 判斷方案優劣 | Fork + Explore：最省 Token 但只能唯讀。Fork + general-purpose：最靈活但成本高。Inline：最簡單但佔主上下文。建議：搜尋/分析用 Fork+Explore，需要寫檔案的用 Inline，背景任務用 Fork+GP |

### 分析型追問（Socratic Follow-up）

- **澄清**：「隔離」的邊界在哪？Fork 的子代理人能讀取主對話中已讀過的檔案嗎？（readFileState 是 clone，所以能看到已快取的，但主對話之後的操作看不到）
- **假設**：本文假設 hooks 累積不會影響效能——但如果一個 session 中呼叫了 20 個帶 hooks 的 skills，每次工具呼叫都要遍歷所有 hooks 的 matchers，是否會有可感知的延遲？
- **證據**：我們確認了 `clearSessionHooks()` 只在 session 結束時呼叫，但沒有確認 `--resume` 後 hooks 是否會保留。Session hooks 存在 `AppState` 中，resume 時 AppState 是重建的，所以 hooks 應該會消失。
- **觀點**：反對意見可能是「hooks 應該跟 skill 生命週期綁定，skill 結束就清除」——但這會讓「持續性自動化」（如 lint-on-save）無法實現。
- **後果**：若用戶不了解 hooks 累積特性，可能在 session 中累積大量 hooks 導致每次工具呼叫都觸發多個 shell 命令，拖慢工作流。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — Hooks 累積導致**不可預期的副作用**。用戶呼叫了帶 hooks 的 skill 後忘了，後續操作被 hook 攔截或修改，但用戶不知道原因。
2. **什麼情況下會失敗？** — (a) Fork 模式下呼叫了需要 Edit/Write 的 skill，但 agent 是 Explore（工具被禁止）；(b) Hook 中的 shell command 依賴特定環境但未安裝；(c) 多個 hooks 同時修改同一檔案導致競爭條件（Race Condition）。
3. **有沒有更好的替代方案？** — 對於持續性自動化，settings.json hooks 更適合（session 啟動即生效、不需要先呼叫 skill）。Skill hooks 更適合「可選的、情境性的」自動化。

## 相關連結（Related）

- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — Skills 的載入時機、快取機制、Token 注入層完整分析，本文聚焦 frontmatter 進階欄位
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — Skills/Commands/Subagents 完整比較，本文深入 fork/agent 的內部實作
- [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]] — Skills 官方文件整理，本文補充原始碼級的運作原理
- [[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]] — Hooks 基礎指南，本文補充 skill hooks 的累積特性與 FAQ
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — 原始碼洩漏解析，涵蓋 Agent Loop 等核心機制

## References

- Claude Code 反編譯原始碼（基於 v2.1.88 source map 洩漏版本）
- 關鍵檔案：
  - `src/tools/SkillTool/SkillTool.ts` — Skill 呼叫分岔點（inline vs fork）
  - `src/utils/forkedAgent.ts` — `prepareForkedCommandContext()` 隔離環境建立
  - `src/skills/loadSkillsDir.ts` — Frontmatter 解析（`parseHooksFromFrontmatter()`）
  - `src/utils/hooks/registerSkillHooks.ts` — Hooks 註冊到 session
  - `src/utils/hooks/sessionHooks.ts` — `addSessionHook()` / `removeSessionHook()` / `clearSessionHooks()`
  - `src/tools/AgentTool/built-in/exploreAgent.ts` — Explore agent 定義
  - `src/schemas/hooks.ts` — Hook 四種類型的 Zod schema
  - `src/entrypoints/agentSdkTypes.js` — 31 種 hook 事件列表
- [Claude Code Skills 官方文件](https://docs.anthropic.com/en/claude-code/skills)
