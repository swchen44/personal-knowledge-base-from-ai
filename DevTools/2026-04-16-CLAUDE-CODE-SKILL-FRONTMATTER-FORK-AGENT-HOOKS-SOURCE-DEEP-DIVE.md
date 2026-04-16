---
title: "Claude Code Skill Frontmatter 深度解析：context:fork、agent、hooks 的原始碼原理、最佳實踐與已知問題"
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
  - "[[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]]"
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

### 七、案例學習：Plugin Skill Frontmatter 欄位遺失問題

> [!warning] Plugin Hooks Bug（社群回報）
> 當 skill 從 plugin 載入時（無論是 `--plugin-dir` 還是 marketplace 安裝），frontmatter 中的 `hooks`、`context: fork`、`agent:`、`paths:` **全部被忽略**。

#### 原始碼驗證：確認問題存在

透過比對兩條載入路徑的程式碼，確認問題確實存在：

**本地 skill 載入路徑**（`loadSkillsDir.ts`）：
```typescript
// loadSkillsDir.ts:447-468
const { frontmatter, content: markdownContent } = parseFrontmatter(content)
const parsed = parseSkillFrontmatterFields(frontmatter, markdownContent, skillName)
//                  ↑ 解析 hooks, context, agent, effort, paths 等所有欄位

return createSkillCommand({
    ...parsed,           // ← 包含 hooks, context, agent, paths
    markdownContent,
    source,
    baseDir: skillDirPath,
    loadedFrom: 'skills',
    paths,
})
```

**Plugin skill 載入路徑**（`loadPluginCommands.ts`）：
```typescript
// loadPluginCommands.ts:218-325
function createPluginCommand(commandName, file, ...) {
    const { frontmatter, content } = file
    // 手動解析每個欄位...
    const allowedTools = parseSlashCommandToolsFromFrontmatter(...)
    const model = frontmatter.model ? parseUserSpecifiedModel(...) : undefined
    const effort = frontmatter['effort'] ? parseEffortValue(...) : undefined
    // ...

    return {
        type: 'prompt',
        name: commandName,
        allowedTools, model, effort,  // ← 這些有
        // ❌ 沒有 hooks
        // ❌ 沒有 context（fork）
        // ❌ 沒有 agent
        // ❌ 沒有 paths
        // ❌ 沒有 skillRoot
    }
}
```

#### 遺失欄位完整對照

| Frontmatter 欄位 | 本地 skill | Plugin skill | 影響 |
|-----------------|-----------|-------------|------|
| `hooks:` | ✅ `parseHooksFromFrontmatter()` | ❌ **完全沒解析** | hooks 不會註冊 |
| `context: fork` | ✅ 解析為 `executionContext` | ❌ **沒有** | 永遠走 inline 模式 |
| `agent:` | ✅ 解析 | ❌ **沒有** | 無法指定 Explore/Plan |
| `paths:` | ✅ `parseSkillPaths()` | ❌ **沒有** | 無法做條件觸發 |
| `skillRoot` | ✅ `baseDir` | ❌ **沒有** | `${CLAUDE_SKILL_DIR}` 無效 |
| `name` | ✅ | ✅ | 正常 |
| `description` | ✅ | ✅ | 正常 |
| `allowed-tools` | ✅ | ✅ | 正常 |
| `model` | ✅ | ✅ | 正常 |
| `effort` | ✅ | ✅ | 正常 |

#### 根因分析

```
┌─────────────────────────────────────────────────────────┐
│              經典軟體工程問題：                            │
│        「兩條獨立的程式碼路徑沒有同步更新」                 │
│                                                         │
│  loadSkillsDir.ts                loadPluginCommands.ts   │
│  ──────────────────              ────────────────────── │
│  parseSkillFrontmatterFields()   createPluginCommand()   │
│    ↓                               ↓                    │
│  createSkillCommand()            手動逐一解析欄位         │
│    ↓                               ↓                    │
│  全部欄位都有                    hooks/context/agent/     │
│                                  paths 沒有加入          │
│                                                         │
│  ※ 當新欄位被加入 createSkillCommand 時，                │
│    createPluginCommand 沒有同步更新                      │
└─────────────────────────────────────────────────────────┘
```

> [!note] 可能是刻意的安全限制
> `processSlashCommand.tsx:874` 有一個安全檢查：
> ```typescript
> const hooksAllowedForThisSkill = 
>     !isRestrictedToPluginOnly('hooks') || isSourceAdminTrusted(command.source);
> ```
> 這暗示 Anthropic **可能有意限制** plugin hooks（plugin 來源不受信任）。但 `context: fork` 和 `agent:` 不涉及安全性，更像是單純的遺漏。

#### Workaround

```bash
# 將 plugin 的 skill 複製到專案的 .claude/skills/ 目錄
cp -r ~/.claude/plugins/cache/{marketplace}/{plugin}/{version}/skills/my-skill \
      .claude/skills/my-skill

# 本地 skill 路徑會使用 createSkillCommand()，所有欄位都會生效
```

#### 案例學習價值

| 教訓 | 說明 |
|------|------|
| **共用解析函式** | 如果兩條路徑要處理同一種格式（SKILL.md frontmatter），應該共用同一個解析函式（如 `parseSkillFrontmatterFields`），而非各自手動解析 |
| **新增欄位時的 checklist** | 每次在 `createSkillCommand` 加入新欄位，都應檢查 `createPluginCommand` 是否也需要同步 |
| **測試覆蓋的盲點** | 如果測試只驗證本地 skill 的 frontmatter 解析，plugin skill 的遺漏就無法被發現 |

### 八、企業 Marketplace 部署：命名冒名防護（Impersonation Protection）

> [!warning] 實測：clone Anthropic plugin 後改名會被擋
> 當使用者把官方 plugin clone 到自己的 repo、微調 marketplace 或 plugin 名稱後，會看到錯誤訊息：
> ```
> Marketplace name impersonates an official Anthropic/Claude marketplace
> ```
> 這是 `src/utils/plugins/schemas.ts` 中**刻意設計**的冒名防護機制，用以防止第三方偽裝成 Anthropic 官方 marketplace。

#### 五層防禦機制

```
 新增 marketplace / 載入 plugin
   │
   ▼
 第一層：基本路徑安全檢查（schemas.ts:225-232）
   └── 禁止 "/"、"\"、".."、單獨 "."
         │
         ▼
 第二層：冒名 regex 偵測（schemas.ts:70-71）
   └── BLOCKED_OFFICIAL_NAME_PATTERN
         │
         ▼
 第三層：非 ASCII 字元（同形異義攻擊防護）
   └── /[^\u0020-\u007E]/  禁止西里爾字母等冒名
         │
         ▼
 第四層：保留名稱（schemas.ts:239-244）
   └── "inline"、"builtin" 不能用
         │
         ▼
 第五層：保留名稱的來源驗證
   └── validateOfficialNameSource()
         必須來自 github.com/anthropics/*
```

#### 8 個保留名稱（僅 Anthropic 官方可用）

```typescript
// schemas.ts:18-27
export const ALLOWED_OFFICIAL_MARKETPLACE_NAMES = new Set([
    'claude-code-marketplace',
    'claude-code-plugins',
    'claude-plugins-official',
    'anthropic-marketplace',
    'anthropic-plugins',
    'agent-skills',
    'life-sciences',
    'knowledge-work-plugins',
])
```

這些名稱即使你用了，也必須來自 `github.com/anthropics/*`，否則報錯：
```
The name 'claude-code-plugins' is reserved for official Anthropic marketplaces.
Only repositories from 'github.com/anthropics/' can use this name.
```

#### 冒名 Regex 詳解

```typescript
// schemas.ts:70-71
const BLOCKED_OFFICIAL_NAME_PATTERN =
    /(?:official[^a-z0-9]*(anthropic|claude)|(?:anthropic|claude)[^a-z0-9]*official|^(?:anthropic|claude)[^a-z0-9]*(marketplace|plugins|official))/i
```

三個分支邏輯：

1. `official` + 分隔符 + `anthropic|claude`
2. `anthropic|claude` + 分隔符 + `official`
3. **以** `anthropic|claude` 開頭 + `marketplace|plugins|official`

> [!note] `[^a-z0-9]*` 允許任意分隔符
> 這段代表「0 或多個非字母數字字元」，所以 `anthropic-official`、`anthropic_official`、`anthropic.official`、`anthropic  official`（底線、點、空格、dash）**全部都會被擋**。

#### 命名安全性對照表

| ✅ 會通過 | ❌ 會被擋 | 原因 |
|---------|----------|------|
| `yourcompany-plugins` | `claude-plugins-v2` | 以 `claude` 開頭 + `plugins` |
| `internal-tools` | `anthropic-marketplace-new` | 以 `anthropic` 開頭 + `marketplace` |
| `acme-ai-tools` | `official-claude-plugins` | `official` + `claude` |
| `my-claude-tools` | `claude-official` | `claude` + `official` |
| `team-formatter-suite` | `claude_official_tools` | 底線也算分隔符 |
| `formatter-claude-utils` | `clаude-plugins`（西里爾 а） | 非 ASCII |
| `anthropic-wrapper` | `anthropic-official-wrapper` | `anthropic` + `official` |
| **(注意)** `my-anthropic-plugins` ✅ | `anthropic-plugins-fork` ❌ | 前者沒以 `anthropic` 開頭 |

> [!tip] 關鍵規則
> 只要**不以 `claude` 或 `anthropic` 開頭**，通常就不會觸發第二分支。所以 `my-anthropic-tools` 可以，`anthropic-tools` 不行。

#### 給企業部署的命名建議

```
✅ 推薦命名模式：
  {公司名}-{功能}        → "acme-formatter-plugins"
  {品牌}-{tools/ai}      → "acme-ai-tools"
  internal-{something}   → "internal-dev-tools"
  {team}-{purpose}       → "platform-team-formatter"

❌ 避免的模式：
  anthropic-*            → 觸發第三分支
  claude-*               → 觸發第三分支
  official-{anthropic}*  → 觸發第一分支
  {anthropic}*-official* → 觸發第二分支
  {非 ASCII 字元}         → 觸發第三層

🔒 絕對禁止（系統保留）：
  inline                 → --plugin-dir 會話保留
  builtin                → 內建 plugin 保留
```

#### 案例：假設你要 fork Anthropic 的 plugin

```bash
# ❌ 錯誤做法 — 會被擋
原 marketplace: anthropic-marketplace（Anthropic 官方）
你 fork 後改名為: anthropic-marketplace-mycompany
# 錯誤：以 anthropic 開頭 + marketplace → regex 匹配

# ❌ 錯誤做法 — 會被擋
你 fork 後改名為: claude-plugins-internal
# 錯誤：以 claude 開頭 + plugins → regex 匹配

# ✅ 正確做法
你 fork 後改名為: mycompany-plugins
# 通過：不以 claude/anthropic 開頭

# ✅ 或者改名為
你 fork 後改名為: internal-mirror-anthropic
# 通過：anthropic 不在開頭

# ✅ 或者
你 fork 後改名為: devtools-mirror
# 通過：完全中性
```

#### 設計意圖

```
第一層防禦（代碼層）：regex + 非 ASCII 擋直接冒名
       ↓
第二層防禦（註冊層）：保留名稱必須來自 github.com/anthropics/*
       ↓
第三層防禦（政策層）：企業用 strictKnownMarketplaces 做白名單

防禦目的：
  • 防止供應鏈攻擊（惡意 plugin 偽裝 Anthropic 官方）
  • 防止 homograph attack（西里爾字母冒充拉丁字母）
  • 保留官方品牌名稱（類似商標保護）
  • 不擋間接變體（my-claude-tools 可以），避免 false positive
```

### 九、補遺：其他安全檢查與企業部署機制

#### 9.1 MarketplaceNameSchema 的完整檢查鏈

```typescript
// schemas.ts:216-246
const MarketplaceNameSchema = z.string()
    .min(1, 'Marketplace must have a name')
    .refine(name => !name.includes(' '), {
        message: 'Marketplace name cannot contain spaces...'
    })
    .refine(name => !name.includes('/') && !name.includes('\\') 
                  && !name.includes('..') && name !== '.', {
        message: 'Marketplace name cannot contain path separators...'
    })
    .refine(name => !isBlockedOfficialName(name), {
        message: 'Marketplace name impersonates an official Anthropic/Claude marketplace'
    })
    .refine(name => name.toLowerCase() !== 'inline', {
        message: 'Marketplace name "inline" is reserved for --plugin-dir session plugins'
    })
    .refine(name => name.toLowerCase() !== 'builtin', {
        message: 'Marketplace name "builtin" is reserved for built-in plugins'
    })
```

#### 9.2 Plugin Name Schema（相對寬鬆）

```typescript
// schemas.ts:274-285 — 只擋空格，不擋冒名
name: z.string()
    .min(1, 'Plugin name cannot be empty')
    .refine(name => !name.includes(' '), {...})
    // ❗ 沒有 isBlockedOfficialName 檢查
    // ❗ 沒有保留名稱檢查
```

> [!note] Plugin name vs Marketplace name
> **Plugin name 的限制比 marketplace name 寬鬆很多**。冒名防護只作用在 marketplace name 層級。這是合理的——攻擊者的威脅向量是「註冊一個假冒官方的 marketplace 來分發惡意 plugin」，而非 plugin 自己的名字。

#### 9.3 Plugin ID 格式驗證

```typescript
// schemas.ts:1339-1346
export const PluginIdSchema = z.string()
    .regex(
        /^[a-z0-9][-a-z0-9._]*@[a-z0-9][-a-z0-9._]*$/i,
        'Plugin ID must be in format: plugin@marketplace'
    )
```

Plugin ID 的格式：`{plugin-name}@{marketplace-name}`，例如 `formatter@company-tools`。兩邊都只允許字母、數字、`-`、`_`、`.`。

#### 9.4 Path Traversal 保護（`lspPluginIntegration.ts`）

```typescript
// lspPluginIntegration.ts:30-45 — 解析 LSP 設定時的 sandbox 檢查
const resolvedFilePath = resolve(pluginPath, relativePath)
const rel = relative(resolvedPluginPath, resolvedFilePath)

// 如果解析後的路徑逃出 plugin 目錄（以 .. 開頭或是絕對路徑）
if (rel.startsWith('..') || resolve(rel) === rel) {
    return null  // 拒絕
}
```

Plugin 內部的相對路徑必須真正落在 plugin 目錄內，即使 zod schema 沒擋住 `..`，執行時也會被攔截。

#### 9.5 企業部署關鍵機制：`CLAUDE_CODE_PLUGIN_SEED_DIR`

> [!important] 這是企業 marketplace 部署的**最強武器**
> `pluginDirectories.ts:85-90` 中的 `getPluginSeedDirs()` 讀取此環境變數，允許企業在容器映像中**預先內建 marketplace 和 plugin 快取**，CC 以**唯讀 fallback layer** 的方式使用，**不需重新 clone**。

**Seed 目錄結構**（與 primary plugins 目錄對應）：

```
$CLAUDE_CODE_PLUGIN_SEED_DIR/
  ├── known_marketplaces.json        ← 預註冊的 marketplace 清單
  ├── marketplaces/
  │     └── {company-tools}/         ← 預 clone 的 marketplace 內容
  │           └── .claude-plugin/marketplace.json
  └── cache/
        └── {marketplace}/
              └── {plugin}/
                    └── {version}/...  ← 預安裝的 plugin 快取
```

**支援多路徑（PATH-like precedence）**：

```bash
# Unix：用 ":" 分隔
export CLAUDE_CODE_PLUGIN_SEED_DIR="/opt/cc-seed-corp:/opt/cc-seed-team"

# Windows：用 ";" 分隔
# 第一個 seed 命中 marketplace 就贏
```

#### 9.6 Seed-managed 條目不可被覆蓋

```typescript
// marketplaceManager.ts:1864-1872
const oldEntry = config[marketplace.name]
if (oldEntry) {
    const seedDir = seedDirFor(oldEntry.installLocation)
    if (seedDir) {
        throw new Error(
            `Marketplace '${marketplace.name}' is seed-managed (${seedDir}). ` +
            `To use a different source, ask your admin to update the seed, ` +
            `or use a different marketplace name.`
        )
    }
}
```

> [!warning] 企業 seed 設定可鎖定名稱
> 一旦 admin 透過 seed 註冊了 `company-tools` marketplace，使用者**無法**用同名的不同來源覆蓋它（會拋錯）。這是強制的「admin 鎖定」機制。

#### 9.7 Marketplace 自動更新規則

```typescript
// schemas.ts:47-57
export function isMarketplaceAutoUpdate(marketplaceName, entry): boolean {
    return entry.autoUpdate ?? (
        ALLOWED_OFFICIAL_MARKETPLACE_NAMES.has(normalizedName) &&
        !NO_AUTO_UPDATE_OFFICIAL_MARKETPLACES.has(normalizedName)
    )
}

// knowledge-work-plugins 是唯一預設不自動更新的官方 marketplace
const NO_AUTO_UPDATE_OFFICIAL_MARKETPLACES = new Set(['knowledge-work-plugins'])
```

**預設行為**：
- 官方 marketplace：**預設自動更新**（knowledge-work-plugins 除外）
- 第三方 marketplace：**預設不自動更新**（需使用者手動或 `autoUpdate: true`）

#### 9.8 Plugin Block by Policy

```typescript
// pluginPolicy.ts:17-20
export function isPluginBlockedByPolicy(pluginId: string): boolean {
    const policyEnabled = getSettingsForSource('policySettings')?.enabledPlugins
    return policyEnabled?.[pluginId] === false
}
```

管理員可透過 `policySettings.enabledPlugins` 的 `false` 值**強制禁用特定 plugin**，使用者在任何 scope 都無法安裝或啟用。

```json
// /etc/claude-code/managed-settings.json
{
  "enabledPlugins": {
    "malicious-plugin@some-marketplace": false,  // ← 強制禁用
    "formatter@company-tools": true               // ← 強制啟用
  }
}
```

#### 9.9 官方 Marketplace 自動安裝

```typescript
// officialMarketplaceStartupCheck.ts:47-51
export function isOfficialMarketplaceAutoInstallDisabled(): boolean {
    return isEnvTruthy(
        process.env.CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL
    )
}
```

預設情況 Claude Code 會嘗試自動安裝 `claude-plugins-official`。企業部署可設 `CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL=1` 停用，只讓員工用公司 marketplace。

#### 9.10 完整的企業部署「黃金設定」

```bash
# 環境變數
export CLAUDE_CODE_PLUGIN_SEED_DIR="/opt/cc-company-seed"
export CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL=1

# Managed settings（/etc/claude-code/managed-settings.json）
{
  # 白名單：只允許公司 marketplace
  "strictKnownMarketplaces": [
    { "source": "hostPattern", "hostPattern": "*.yourcompany.com" }
  ],
  
  # 預註冊：員工不用手動 add
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": { "source": "github", "repo": "your-company/plugins" }
    }
  },
  
  # 預啟用特定 plugin
  "enabledPlugins": {
    "formatter@company-tools": true,
    "security-checker@company-tools": true,
    "legacy-plugin@third-party": false  # 明確禁用
  },
  
  # 封鎖非 plugin 的自訂內容
  "strictPluginOnlyCustomization": ["skills", "hooks", "mcp"],
  
  # 自訂信任訊息
  "pluginTrustMessage": "Only install plugins from YourCompany-approved sources."
}
```

#### 9.11 Plugin 安全檢查完整清單

| # | 檢查項目 | 位置 | 觸發時機 | 行為 |
|---|---------|------|---------|------|
| 1 | JSON syntax 有效性 | validatePlugin.ts | 讀取時 | ❌ Error |
| 2 | Path traversal（`..`） | validatePlugin.ts | 解析時 | ❌ Error |
| 3 | Plugin name 重複（同 marketplace） | validatePlugin.ts:430 | 驗證時 | ❌ Error |
| 4 | Plugin name 空格檢查 | schemas.ts:279 | 解析時 | ❌ Error |
| 5 | **Marketplace name 冒名**（regex） | schemas.ts:235 | 註冊時 | ❌ Error |
| 6 | **Marketplace name 非 ASCII** | schemas.ts:94 | 註冊時 | ❌ Error |
| 7 | **Marketplace name 保留字**（inline/builtin） | schemas.ts:239-244 | 註冊時 | ❌ Error |
| 8 | **保留名稱來源驗證**（github.com/anthropics/*） | marketplaceManager.ts:1851 | 載入後 | ❌ Error |
| 9 | Plugin ID 格式（`name@mkt`） | schemas.ts:1343 | 解析時 | ❌ Error |
| 10 | Path sandbox（LSP 設定） | lspPluginIntegration.ts:40 | 載入時 | 回傳 null |
| 11 | **strictKnownMarketplaces** | marketplaceHelpers.ts:480 | 下載前 | ❌ 擋下載 |
| 12 | **blockedMarketplaces** | marketplaceHelpers.ts:482 | 下載前 | ❌ 擋下載 |
| 13 | **strictPluginOnlyCustomization** | pluginOnlyPolicy.ts:19 | 載入時 | ⚠️ 封鎖用戶層 |
| 14 | **isPluginBlockedByPolicy** | pluginPolicy.ts:17 | 安裝/啟用時 | ❌ 阻斷 |
| 15 | **Seed-managed 鎖定** | marketplaceManager.ts:1867 | 覆蓋時 | ❌ Error |
| 16 | Plugin hooks 安全閘 | processSlashCommand.tsx:874 | 註冊 hooks 時 | ⚠️ 非 trusted 跳過 |
| 17 | Plugin name kebab-case | validatePlugin.ts:260 | 驗證時 | ⚠️ Warning |

（加粗表示**企業管理員可控制**的機制）

## Skill Hooks 最佳實踐（2026-04-16 追加研究）

> [!info] 來源
> 本節基於 [Anthropic 官方 hooks 文件](https://code.claude.com/docs/en/hooks)、[Everett Quebral 的 Skills/Hooks/Plugins 實戰文章](https://www.everettquebral.com/blog/artificial-intelligence/skills-hooks-and-plugins-in-claude-code)、[GitHub Issue #17688](https://github.com/anthropics/claude-code/issues/17688) 以及對話研究整理。

### Skill Hooks vs Settings Hooks 的選擇決策

| 場景 | 用 Skill Hooks | 用 Settings Hooks |
|------|---------------|-------------------|
| **永遠都要執行的檢查**（如 lint 所有寫入） | | **Settings** — 不依賴 skill 是否被觸發 |
| **只在特定工作流中才需要的檢查** | **Skill** — 隨 skill 生命週期自動管理 | |
| **一次性初始化**（環境設定） | **Skill + `once: true`** | |
| **需要分發給團隊** | **Skill**（隨 plugin 打包）— 但注意 #17688 bug | |
| **安全策略（永不允許某操作）** | | **Settings** — 不可繞過 |

> [!quote] Everett Quebral
> 「Hooks are not a softer version of skills. They are automation points.」
> Skills 是建議性的（Claude 可能不觸發），Hooks 是確定性的（一定會執行）。

### 完整 Frontmatter 欄位驗證表

根據官方文件逐一驗證所有 SKILL.md frontmatter 欄位：

| 欄位 | 狀態 | 說明 |
|------|------|------|
| `name` | **官方支援** | 顯示名稱，也是 `/slash-command` |
| `description` | **官方支援** | Claude 自動觸發的匹配依據 |
| `when_to_use` | **官方支援** | 追加到 description，合計上限 1,536 字元 |
| `context: fork` | **官方支援** | 在獨立 subagent 中執行 |
| `agent` | **官方支援** | 搭配 fork 指定 agent 類型 |
| `model` | **官方支援** | 覆蓋預設模型 |
| `effort` | **官方支援** | low/medium/high/max（max 限 Opus 4.6） |
| `allowed-tools` | **官方支援** | 允許的工具白名單 |
| `disable-model-invocation` | **官方支援** | 禁止 Claude 自動呼叫 |
| `user-invocable` | **官方支援** | 從 `/` 選單隱藏 |
| `paths` | **官方支援** | glob pattern 路徑觸發 |
| `argument-hint` | **官方支援** | 自動補全時的參數提示 |
| `hooks` | **官方支援** | skill 專屬的生命週期 hooks |
| `shell` | **官方支援** | bash 或 powershell |
| ~~`arguments`~~ | **不存在** | 用 `$ARGUMENTS`、`$0`、`$1` 取代 |

### Skill Hooks 支援的所有事件

根據官方文件，所有事件都在 skill hooks 中可用：

- `PreToolUse`、`PostToolUse`、`PostToolUseFailure`
- `PermissionRequest`、`PermissionDenied`
- `SessionStart`、`UserPromptSubmit`、`Stop`
- `SubagentStart`、`SubagentStop`
- `TaskCreated`、`TaskCompleted`

### Skill Hooks vs Settings Hooks 生命週期差異

| 面向 | Settings Hooks | Skill/Agent Hooks |
|------|---------------|-------------------|
| **作用範圍** | 全域或專案級 | **僅限元件活躍期間** |
| **持久性** | 存在設定檔中 | **僅在記憶體中** |
| **清理** | 需手動移除 | **元件結束時自動清理** |
| **可分享** | 取決於檔案位置 | 隨元件一起打包分發 |
| **`once` 欄位** | 不適用 | **Skills 專屬**——執行一次後自動移除 |

### 實戰組合模式

**模式 1：Skill 定義工作流 + Hooks 強制品質**

```yaml
---
name: api-development
description: REST API development workflow. Auto-invoke when creating endpoints or route handlers. Do NOT load for frontend or CSS work.
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          if: "Write(src/api/**)|Edit(src/api/**)"
          command: "npx eslint --fix $CLAUDE_FILE_PATHS"
          statusMessage: "Running linter..."
---
```

**模式 2：`once: true` 做環境初始化**

```yaml
---
name: project-setup
description: Initialize development environment
disable-model-invocation: true
hooks:
  SessionStart:
    - hooks:
      - type: command
        command: "./scripts/check-dependencies.sh"
        once: true
---
```

**模式 3：安全操作 = `disable-model-invocation` + `allowed-tools` + hooks 三重保護**

```yaml
---
name: deploy
description: Deploy to production
disable-model-invocation: true
allowed-tools: Bash(npm run build) Bash(npm run deploy)
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/deployment-safety-check.sh"
          timeout: 30
---
```

### 已知問題與 Plugin Hooks Bug

> [!warning] Issue #17688：Plugin 內 Skill Hooks 不觸發（OPEN）
> 當 skill 從 plugin 載入時（無論 `--plugin-dir` 或 marketplace 安裝），frontmatter 中的 hooks **被完全忽略**。
> 
> | 來源 | Frontmatter Hooks |
> |------|------------------|
> | 專案 skill（`.claude/skills/`） | **正常運作** |
> | 專案 agent（`.claude/agents/`） | **正常運作** |
> | Plugin skill（任何安裝方式） | **不運作** |
> | Plugin agent（任何安裝方式） | **不運作** |
> 
> **根因**：與本文原始碼分析中發現的「兩條獨立程式碼路徑」問題一致——`createSkillCommand()` 會解析 hooks，但 `createPluginCommand()` 不會。
> 
> **Workaround**：將有 hooks 的 skill 複製到 `.claude/skills/` 目錄。
> 
> 參考：[GitHub Issue #17688](https://github.com/anthropics/claude-code/issues/17688)

### 修正版完整 Frontmatter 範本

```yaml
---
# 基本資訊
name: my-skill
description: "做什麼用的。Auto-invoke when X. Do NOT load for Y."
when_to_use: "額外的觸發提示（與 description 合計 ≤1536 字元）"

# 執行控制
context: fork               # fork | (省略=inline)
agent: Explore              # 搭配 fork 使用
model: claude-sonnet-4-6    # 覆蓋預設模型
effort: high                # low | medium | high | max

# 工具與安全
allowed-tools:
  - "Bash(npm *)"
  - "Write"
disable-model-invocation: false
user-invocable: true

# 條件觸發
paths:
  - "src/components/**"

# 參數（沒有 arguments 欄位，用 $ARGUMENTS/$0/$1）
argument-hint: "<query> [scope]"

# Hooks — 呼叫後註冊到 session，結束後自動清理
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "eslint --fix $CLAUDE_FILE_PATHS"
          statusMessage: "Running linter..."
  SessionStart:
    - hooks:
      - type: command
        command: "./setup.sh"
        once: true

# Shell 設定
shell: bash
---
```

## 我的心得（My Takeaways）

1. **Skill hooks 的累積特性是雙面刃**：好處是可以逐步建立自動化工作流（呼叫一個 skill 註冊 linter，呼叫另一個註冊 formatter）；風險是忘記自己掛了什麼 hooks，導致意外的副作用。建議控制每個 skill 的 hooks 數量，並在 skill description 中說明會註冊哪些 hooks。
2. **`context: fork` + `agent: Explore` 是被低估的組合**：用 Haiku 模型快速搜尋程式碼，結果只佔主上下文的一段摘要。適合在需要大量搜尋的工作流中使用。
3. **`once: true` 適合初始化型任務**：例如「首次呼叫時安裝依賴」或「首次呼叫時建立目錄結構」——只需執行一次，之後自動移除。
4. **Plugin skill 的進階 frontmatter 欄位不會生效**：從原始碼確認 `hooks`、`context: fork`、`agent:`、`paths:` 在 plugin 載入路徑中全部被忽略。如果需要這些功能，必須將 skill 放在 `.claude/skills/` 而非透過 plugin 安裝。這是「兩條獨立程式碼路徑沒有同步更新」的經典軟體工程問題。

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
- [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] — CLAUDE.md 七位專家最佳實踐，Skills hooks 在整體 harness 中的定位

## References

- Claude Code 反編譯原始碼（基於 v2.1.88 source map 洩漏版本）
- 關鍵檔案：
  - `src/tools/SkillTool/SkillTool.ts` — Skill 呼叫分岔點（inline vs fork）
  - `src/utils/forkedAgent.ts` — `prepareForkedCommandContext()` 隔離環境建立
  - `src/skills/loadSkillsDir.ts` — Frontmatter 解析（`parseHooksFromFrontmatter()`）
  - `src/utils/hooks/registerSkillHooks.ts` — Hooks 註冊到 session
- [Hooks Reference — Anthropic 官方文件](https://code.claude.com/docs/en/hooks)
- [Skills, Hooks, and Plugins in Claude Code — Everett Quebral](https://www.everettquebral.com/blog/artificial-intelligence/skills-hooks-and-plugins-in-claude-code)
- [Issue #17688: Skill-scoped hooks not triggered in plugins](https://github.com/anthropics/claude-code/issues/17688)
  - `src/utils/hooks/sessionHooks.ts` — `addSessionHook()` / `removeSessionHook()` / `clearSessionHooks()`
  - `src/tools/AgentTool/built-in/exploreAgent.ts` — Explore agent 定義
  - `src/schemas/hooks.ts` — Hook 四種類型的 Zod schema
  - `src/entrypoints/agentSdkTypes.js` — 31 種 hook 事件列表
- [Claude Code Skills 官方文件](https://docs.anthropic.com/en/claude-code/skills)
