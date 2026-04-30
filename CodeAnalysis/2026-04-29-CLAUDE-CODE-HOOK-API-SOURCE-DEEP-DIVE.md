---
title: "Claude Code Hook API 原始碼深度解析：24 個事件、完整 I/O Schema、Query Loop 狀態機與實戰 Use Case"
date: 2026-04-29
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#devtools/claude-code"
  - "#ai/agent-architecture"
  - "#devtools/hooks"
  - "#typescript"
source: "conversation"
source_type: code
author: "swchen44 + Claude"
status: notes
links:
  - "[[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]]"
  - "[[2026-01-24-CLAUDE-CODE-HOOKS-CODE-ANALYSIS]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
  - "[[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]"
  - "[[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]]"
github_stars: N/A
github_language: TypeScript
---

## 摘要（Summary）

基於 Claude Code 反編譯原始碼的逐行追蹤，完整解析 Hook API 的內部機制。相較於既有筆記（[[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]] 涵蓋 13 個事件），本篇追蹤到 **24 個 Hook 事件**、**6 種 Hook 類型**（command / prompt / agent / http / callback / function）、**完整的 JSON Input/Output Schema**（逐欄位對照原始碼），以及最關鍵的——**Hook 如何透過 `query.ts` 的狀態機（State Machine）改變 Claude 的執行行為**。涵蓋 Stop Hook 自我檢查、PreToolUse 攔截修改、PermissionRequest 自動決策等多種 Use Case，並分析防無限循環、信任檢查、效能瓶頸等 Boundary / Limitation。

## Why — 為什麼需要這篇？

> 現有知識庫中已有 Hook 相關筆記，但都停在「怎麼設定」與「有哪些事件」的層次。

- **核心動機**：要自己寫 Hook API，必須理解 Hook 的 Input 長什麼樣、Output 能控制什麼行為、以及行為改變在 query loop 狀態機中如何傳播
- **與既有筆記的差異**：本篇從**反編譯原始碼**出發，追蹤到 `src/types/hooks.ts`、`src/schemas/hooks.ts`、`src/query.ts`、`src/query/stopHooks.ts`、`src/services/tools/toolExecution.ts` 的具體行數
- **目標讀者**：想自己寫 Hook 腳本或 Hook HTTP 服務的開發者

## What — 是什麼？

- **主要內容**：
  - 24 個 Hook 事件完整清單（含新增的 `Elicitation`、`ConfigChange`、`WorktreeCreate` 等）
  - 6 種 Hook 類型的 Zod Schema 定義
  - 每個事件的 Input JSON 欄位
  - `hookSpecificOutput` 的完整 discriminated union（按 `hookEventName` 分支）
  - query loop 狀態機中 Stop Hook 的 blocking → continue → re-query 完整流程
  - 多種實戰 Use Case
  - Boundary / Limitation 分析

- **不涵蓋**：Hook 的 UI 渲染層（Ink 元件）、analytics 打點細節

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌────────────────────────────────────────────────────────────┐
│                    settings.json                           │
│  (policySettings > userSettings > projectSettings > local) │
│                                                            │
│  hooks:                                                    │
│    PreToolUse:                                             │
│      - matcher: "Bash"                                     │
│        hooks:                                              │
│          - type: command                                   │
│            command: "./check.sh"                           │
└────────────────────────┬───────────────────────────────────┘
                         │ 載入
                         ▼
┌────────────────────────────────────────────────────────────┐
│              Hook Config Snapshot                          │
│  src/utils/hooks/hooksConfigSnapshot.ts                    │
│  (合併 policy + user + project + local + plugin + session) │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│              getMatchingHooks()                            │
│  src/utils/hooks.ts                                       │
│  按 event name + matcher 過濾                              │
│  + if 條件用 permission rule syntax 評估                   │
│  + trust check (shouldSkipHookDueToTrust)                 │
└────────────────────────┬───────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┬──────────────┐
          ▼              ▼              ▼              ▼
   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐
   │  command   │  │  prompt   │  │   http    │  │  agent   │
   │ (shell    │  │ (LLM     │  │ (POST to  │  │ (multi-  │
   │  spawn)   │  │  eval)   │  │  URL)     │  │  turn)   │
   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬─────┘
         │              │              │              │
         └──────────────┼──────────────┴──────────────┘
                        ▼
┌────────────────────────────────────────────────────────────┐
│              HookResult → AggregatedHookResult             │
│  src/types/hooks.ts:259-289                                │
│                                                            │
│  blockingError? │ preventContinuation? │ updatedInput?     │
│  permissionBehavior? │ additionalContext? │ retry?         │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│              Consumer（呼叫端）                              │
│                                                            │
│  toolExecution.ts  → PreToolUse / PostToolUse              │
│  query.ts          → Stop hook → 狀態機 continue           │
│  handlePromptSubmit → UserPromptSubmit                     │
│  session init      → SessionStart / Setup                  │
└────────────────────────────────────────────────────────────┘
```

### 執行流程圖（Stop Hook 為例）

```
模型回覆完畢 (end_turn / stop_reason = "end_turn")
    │
    ▼
query.ts:1270  handleStopHooks()
    │
    ▼
stopHooks.ts:180  executeStopHooks()
    │
    ├── 傳入 stop_hook_active 旗標
    ├── 提取 last_assistant_message 文字
    │
    ▼
hooks.ts:3730  executeStopHooks()
    │
    ├── createBaseHookInput() 建立 base JSON
    ├── 加入 stop_hook_active + last_assistant_message
    │
    ▼
hooks.ts  executeHooks()  (所有 Hook 並行執行)
    │
    ├── Hook A: exit 0 → success
    ├── Hook B: exit 2 → blockingError ← ★ 這裡阻止停止
    │
    ▼
stopHooks.ts:257-266  收集 blockingErrors
    │
    ▼
query.ts:1285  blockingErrors.length > 0 ?
    │
    ├── YES → 建立新 State:
    │         messages = [...原有, ...blockingErrors]
    │         stopHookActive = true     ← ★ 防循環旗標
    │         transition.reason = 'stop_hook_blocking'
    │         continue  ← ★ 回到 query loop 頂部
    │                     模型再次被呼叫 API
    │
    └── NO  → return { reason: 'completed' }
              session 正常結束
```

### 時序圖（PreToolUse Hook 攔截工具呼叫）

```
 模型(API)     toolExecution.ts      hooks.ts          Hook Script
    │                │                   │                   │
    │──tool_use────►│                   │                   │
    │  (Bash, rm)   │                   │                   │
    │               │──runPreToolUse───►│                   │
    │               │                   │──spawn/POST──────►│
    │               │                   │                   │── 讀 stdin JSON
    │               │                   │                   │── 檢查 tool_input
    │               │                   │◄──exit 2 + JSON──│
    │               │◄──blockingError──│                   │
    │               │                   │                   │
    │               │  (不執行工具)      │                   │
    │◄──tool_result─│                   │                   │
    │  "Error: ..." │                   │                   │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）：Event-Driven Hook + State Machine
> Hook 系統採用事件驅動 + stdin/stdout JSON 管道（Pipe）架構，與 query loop 的有限狀態機（FSM）整合。

1. **並行執行、聚合結果**：同一事件的多個 Hook 以 `Promise.all` 並行執行（`src/utils/hooks.ts`），結果聚合到 `AggregatedHookResult`，第一個 `blockingError` 優先。這是效能考量——避免 N 個 Hook 序列執行造成延遲放大
2. **exit code 語意化**：exit 0 = 成功，exit 2 = blocking（阻止操作），其他 = non-blocking warning。選擇 exit 2 而非 1 是因為 1 在 Unix 中太通用（常被意外觸發）
3. **`hookSpecificOutput` discriminated union**：不同事件的回傳能力完全不同（PreToolUse 能改 input，PostToolUse 能改 output），用 `hookEventName` 做鑑別器（discriminator）確保型別安全
4. **信任檢查（Trust Check）集中化**：所有 Hook 執行前必須通過 `shouldSkipHookDueToTrust()`，未接受信任對話框的 workspace 完全跳過 Hook

---

## 完整 Hook 事件清單（24 個事件）

來源：`src/entrypoints/sdk/coreTypes.generated.ts` + `src/utils/hooks.ts`

| # | 事件名稱 | 觸發時機 | 可改變的行為 |
|---|---------|---------|-------------|
| 1 | `PreToolUse` | 工具執行**前** | 阻止/修改 input/自動批准權限/注入上下文 |
| 2 | `PostToolUse` | 工具執行**後**（成功） | 替換 MCP 輸出/注入上下文 |
| 3 | `PostToolUseFailure` | 工具執行**後**（失敗） | 注入上下文 |
| 4 | `UserPromptSubmit` | 使用者提交提示 | 阻止提交/注入上下文 |
| 5 | `Stop` | 模型主動停止（end_turn） | **阻止停止 → 模型繼續工作** |
| 6 | `StopFailure` | Stop Hook 自身失敗 | 通知/記錄 |
| 7 | `SubagentStop` | 子代理人停止 | 阻止子代理人結束 |
| 8 | `SessionStart` | Session 開始/恢復/清除 | 注入初始訊息/監聽檔案/注入上下文 |
| 9 | `SessionEnd` | Session 結束 | 清理（timeout 僅 1.5 秒） |
| 10 | `Setup` | 初始化階段（init/maintenance） | 注入上下文 |
| 11 | `SubagentStart` | 子代理人啟動 | 注入上下文 |
| 12 | `Notification` | 通知事件 | 注入上下文 |
| 13 | `PermissionRequest` | 權限檢查 | 自動 allow/deny + 修改 input |
| 14 | `PermissionDenied` | 權限被拒絕 | 重試（`retry: true`） |
| 15 | `PreCompact` | Context 壓縮前 | 注入自定壓縮指令 |
| 16 | `PostCompact` | Context 壓縮後 | 注入上下文 |
| 17 | `TeammateIdle` | 團隊成員閒置 | 阻止閒置（繼續工作） |
| 18 | `TaskCreated` | Task 建立 | 通知/記錄 |
| 19 | `TaskCompleted` | Task 完成 | 阻止完成 |
| 20 | `Elicitation` | MCP elicitation 請求 | 代替使用者回答 |
| 21 | `ElicitationResult` | Elicitation 結果 | 修改結果 |
| 22 | `ConfigChange` | 設定變更 | 通知/記錄 |
| 23 | `CwdChanged` | 工作目錄變更 | 註冊新的 watchPaths |
| 24 | `FileChanged` | 監聽的檔案變更 | 註冊新的 watchPaths |

> [!note] 額外事件
> 原始碼中還定義了 `WorktreeCreate`、`WorktreeRemove`、`InstructionsLoaded` 等事件，出現在 `hookSpecificOutput` 的 union type 中，但尚未有獨立的 `execute*Hooks()` 函式，可能仍在開發中。

---

## 完整 Input Schema（傳入 Hook 的 JSON）

### Base 欄位（所有事件共用）

來源：`src/utils/hooks.ts:301-328` `createBaseHookInput()`

```json
{
  "session_id": "uuid-string",
  "transcript_path": "/Users/xxx/.claude/sessions/session-id.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "default",
  "agent_id": "subagent-uuid 或 undefined",
  "agent_type": "general-purpose",
  "hook_event_name": "PreToolUse"
}
```

### 各事件專屬欄位

來源：`src/entrypoints/sdk/coreTypes.generated.ts:69-98`

**PreToolUse / PostToolUse / PostToolUseFailure**：
```json
{
  "tool_name": "Bash",
  "tool_input": { "command": "rm -rf /tmp/test" },
  "tool_use_id": "toolu_xxx"
}
```
PostToolUse 額外有 `"tool_response": { ... }`

**Stop / SubagentStop**（`src/utils/hooks.ts:3765-3780`）：
```json
{
  "hook_event_name": "Stop",
  "stop_hook_active": false,
  "last_assistant_message": "模型最後一次回覆的完整文字"
}
```
SubagentStop 額外有 `"agent_id"`, `"agent_transcript_path"`, `"agent_type"`

**UserPromptSubmit**：
```json
{
  "hook_event_name": "UserPromptSubmit",
  "prompt": "使用者輸入的完整文字"
}
```

**SessionStart**（`src/utils/hooks.ts:3971-3977`）：
```json
{
  "hook_event_name": "SessionStart",
  "source": "startup | resume | clear | compact",
  "agent_type": "general-purpose",
  "model": "claude-opus-4-6"
}
```

**SessionEnd**：
```json
{
  "hook_event_name": "SessionEnd",
  "exit_reason": "user_exit | timeout | error"
}
```

**CwdChanged**：
```json
{
  "hook_event_name": "CwdChanged",
  "cwd": "/new/working/directory"
}
```

**FileChanged**：
```json
{
  "hook_event_name": "FileChanged",
  "path": "/path/to/changed/file"
}
```

**Notification**：
```json
{
  "hook_event_name": "Notification",
  "message": "通知訊息內容"
}
```

---

## 完整 Output Schema（Hook 回傳的 JSON）

來源：`src/types/hooks.ts:50-176` `syncHookResponseSchema`

### 通用控制欄位

```json
{
  "continue": true,
  "suppressOutput": false,
  "stopReason": "原因說明（continue=false 時顯示）",
  "decision": "approve | block",
  "reason": "決策理由",
  "systemMessage": "警告訊息（顯示給使用者）"
}
```

### `hookSpecificOutput` Discriminated Union

以 `hookEventName` 做鑑別器（discriminator），不同事件能回傳不同的特殊欄位：

**PreToolUse**（最強大的控制點）：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow | deny | ask | passthrough",
    "permissionDecisionReason": "自動批准理由",
    "updatedInput": { "command": "安全化後的指令" },
    "additionalContext": "注入給模型的額外上下文"
  }
}
```

**PostToolUse**：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "...",
    "updatedMCPToolOutput": { "替換 MCP 工具的回傳值": true }
  }
}
```

> [!warning] `updatedMCPToolOutput` 僅適用於 MCP 工具
> 來源 `src/types/hooks.ts:103-105`，明確標注 `Updates the output for MCP tools`。內建工具（Bash、Read 等）的輸出不可被替換。

**SessionStart**：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "...",
    "initialUserMessage": "自動注入的第一條使用者訊息",
    "watchPaths": ["/path/to/watch/for/FileChanged"]
  }
}
```

**PermissionRequest**：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow",
      "updatedInput": { "可選的修改後 input": true },
      "updatedPermissions": [{ "path": "...", "permission": "..." }]
    }
  }
}
```

或拒絕：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "deny",
      "message": "拒絕理由",
      "interrupt": true
    }
  }
}
```

**PermissionDenied**：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionDenied",
    "retry": true
  }
}
```

**Elicitation**：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "Elicitation",
    "action": "accept | decline | cancel",
    "content": { "key": "value" }
  }
}
```

**CwdChanged / FileChanged**：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "CwdChanged",
    "watchPaths": ["/new/paths/to/watch"]
  }
}
```

### 非同步模式（Async Protocol）

Command Hook 的 stdout **第一行**輸出此 JSON 即轉為背景執行：

```json
{ "async": true, "asyncTimeout": 15000 }
```

由 `AsyncHookRegistry`（`src/utils/hooks/AsyncHookRegistry.ts`）管理，透過 `checkForAsyncHookResponses()` 定期輪詢。`asyncRewake: true` 的 Hook 在 exit code 2 時會喚醒模型。

---

## 6 種 Hook 類型

來源：`src/schemas/hooks.ts:31-189`

| 類型 | 設定方式 | 執行機制 | 適用場景 |
|------|---------|---------|---------|
| `command` | `"type": "command", "command": "..."` | Shell spawn（bash/zsh/powershell） | 最通用，任何語言的腳本 |
| `prompt` | `"type": "prompt", "prompt": "..."` | 呼叫小模型（Haiku）評估條件 | 不想寫腳本，用自然語言判斷 |
| `agent` | `"type": "agent", "prompt": "..."` | 啟動多輪 agent session | 需要讀檔案、跑工具來驗證 |
| `http` | `"type": "http", "url": "..."` | POST hookInput JSON 到 URL | 遠端服務整合、webhook |
| `callback` | 程式化註冊 | TypeScript 函式直接呼叫 | SDK / Plugin 內部使用 |
| `function` | Session 層級註冊 | async function | SDK Stop hook 等 |

### command Hook 完整 Schema

```json
{
  "type": "command",
  "command": "./my-hook.sh",
  "shell": "bash",
  "if": "Bash(rm *)",
  "timeout": 10,
  "statusMessage": "正在檢查安全性...",
  "once": false,
  "async": false,
  "asyncRewake": false
}
```

### prompt Hook — `$ARGUMENTS` 佔位符

```json
{
  "type": "prompt",
  "prompt": "以下是工具呼叫的 JSON：$ARGUMENTS\n\n判斷是否安全。若不安全回傳 {\"decision\": \"block\"}",
  "model": "claude-haiku-4-5-20251001",
  "timeout": 30
}
```

`$ARGUMENTS` 會被替換為完整的 hookInput JSON 字串。

### http Hook — Header 環境變數插值

```json
{
  "type": "http",
  "url": "https://my-hook-server.com/webhook",
  "headers": {
    "Authorization": "Bearer $MY_TOKEN",
    "X-Session": "$SESSION_ID"
  },
  "allowedEnvVars": ["MY_TOKEN", "SESSION_ID"],
  "timeout": 30
}
```

> [!warning] `allowedEnvVars` 白名單
> 只有在 `allowedEnvVars` 中明確列出的環境變數才會被插值（interpolation），其他 `$VAR` 引用會被替換為空字串。這是安全設計。

---

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | Hook 事件 | 觸發方式 | 核心檔案 |
|---|---------|----------|---------|---------|
| 1 | 模型停下來時要求自我檢查 | `Stop` | 模型 end_turn | `query.ts:1270` → `stopHooks.ts:65` → `hooks.ts:3730` |
| 2 | 攔截危險 Bash 指令 | `PreToolUse` | Bash 工具呼叫 | `toolExecution.ts:800` → `hooks.ts` |
| 3 | 自動批准安全操作 | `PreToolUse` | 任何工具呼叫 | `toolExecution.ts:831-837` |
| 4 | 修改工具輸入 | `PreToolUse` | 任何工具呼叫 | `toolExecution.ts:834-837` |
| 5 | 替換 MCP 工具輸出 | `PostToolUse` | MCP 工具完成 | `hooks.ts` |
| 6 | 代替使用者做權限決策 | `PermissionRequest` | 工具需要權限 | `hooks.ts:4252` |
| 7 | Session 啟動注入上下文 | `SessionStart` | claude 啟動 | `hooks.ts:3962` |
| 8 | 檔案監聽觸發自動操作 | `FileChanged` | 監聽的檔案被修改 | `hooks.ts:4373` |

### 案例 1：模型停下來時要求自我檢查（Stop Hook）

> [!important] 這是最實用的 Use Case 之一——讓模型在「以為自己完成了」的時候被 Hook 攔住，強制檢查 checklist。

```
模型輸出 end_turn
  │
  ▼
query.ts:1270  handleStopHooks()
  │
  ▼
stopHooks.ts:180  executeStopHooks(
                    permissionMode,
                    signal,
                    undefined,
                    stopHookActive ?? false,   ← ★ 防循環旗標
                    agentId,
                    toolUseContext,
                    [...messages, ...assistantMessages],
                    agentType
                  )
  │
  ▼
hooks.ts:3753-3763  提取 last_assistant_message
                    （從最後一條 assistant message 中取純文字）
  │
  ▼
你的 Hook 收到 stdin JSON:
{
  "session_id": "...",
  "cwd": "...",
  "hook_event_name": "Stop",
  "stop_hook_active": false,      ← 第一次是 false
  "last_assistant_message": "好的，我已經完成了所有修改..."
}
  │
  ├── 你的腳本判斷：沒看到 checklist 確認 → exit 2 + stderr 訊息
  │
  ▼
stopHooks.ts:257-266  blockingError 被收集
  │
  ▼
query.ts:1285-1308  建立新 State:
  messages = [...原有, ...blockingErrors]
  stopHookActive = true           ← ★ 下次 Hook 看到這個
  continue                        ← ★ 回到 query loop
  │
  ▼
模型再次被呼叫 API（看到 blocking error 訊息）
  → 模型按照 error 訊息檢查 checklist
  → 模型再次 end_turn
  │
  ▼
Hook 再次執行，但 stop_hook_active = true
  → 你的腳本看到 active = true → exit 0（放行）
```

**設定範例（settings.json）**：
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash /path/to/stop-checker.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**stop-checker.sh 範例**：
```bash
#!/bin/bash
INPUT=$(cat)

STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  exit 0  # 放行，避免無限循環
fi

LAST_MSG=$(echo "$INPUT" | jq -r '.last_assistant_message // ""')

# 檢查是否提到 checklist 相關關鍵字
if ! echo "$LAST_MSG" | grep -qi "checklist\|已完成\|verified\|all done\|確認完畢"; then
  echo "請先完成以下 checklist 再停止：
1. 所有修改的檔案都已儲存
2. 測試已通過（若有相關測試）
3. 沒有遺留的 TODO
4. git status 確認無未預期的變更
請逐一確認後再繼續。" >&2
  exit 2  # blocking error → 模型繼續
fi

exit 0  # 放行
```

**prompt hook 版本（無需寫腳本）**：
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "以下是 AI 助手的最後回覆：\n\n$ARGUMENTS\n\n請判斷助手是否真的完成了全部工作。檢查項目：1) 是否有明確的完成確認 2) 是否有遺漏的步驟 3) 是否需要執行測試。若判斷尚未完成，回傳 {\"decision\": \"block\", \"reason\": \"請完成所有步驟並確認 checklist\"}。若已完成，回傳 {\"decision\": \"approve\"}"
          }
        ]
      }
    ]
  }
}
```

### 案例 2：攔截危險 Bash 指令（PreToolUse）

```
模型呼叫 Bash(rm -rf /)
  │
  ▼
toolExecution.ts:800  runPreToolUseHooks()
  │
  ▼
Hook 收到:
{
  "tool_name": "Bash",
  "tool_input": { "command": "rm -rf /" }
}
  │
  ├── 你的腳本：匹配危險模式 → exit 2
  │
  ▼
toolExecution.ts:853-860  建立 Error tool_result
  → 模型收到錯誤訊息（不會執行 rm -rf /）
```

### 案例 3：修改工具輸入（PreToolUse updatedInput）

> [!tip] updatedInput 的強大用途
> 你可以透過 PreToolUse 的 `updatedInput` 在不阻擋的情況下**改寫工具的輸入**。例如自動加上 `--dry-run`、修改檔案路徑、或注入額外參數。

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "passthrough",
    "updatedInput": {
      "command": "rm -rf /tmp/test --dry-run"
    }
  }
}
```

處理邏輯在 `toolExecution.ts:834-837`：
```
case 'hookUpdatedInput':
  processedInput = result.updatedInput
  break
```

### 案例 4：代替使用者做權限決策（PermissionRequest）

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'INPUT=$(cat); CMD=$(echo $INPUT | jq -r \".tool_input.command\"); if echo \"$CMD\" | grep -q \"^git \"; then echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"PermissionRequest\\\",\\\"decision\\\":{\\\"behavior\\\":\\\"allow\\\"}}}\" ; else echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"PermissionRequest\\\",\\\"decision\\\":{\\\"behavior\\\":\\\"deny\\\",\\\"message\\\":\\\"Only git commands auto-approved\\\"}}}\" ; fi'"
          }
        ]
      }
    ]
  }
}
```

### 案例 5：Session 啟動注入環境上下文

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"當前 Git 分支: '$(git branch --show-current)'\",\"initialUserMessage\":\"請先檢查最近的 git log，了解上次工作的進度。\"}}'"
          }
        ]
      }
    ]
  }
}
```

---

## Boundary / Limitation 分析

### 1. Stop Hook 的防無限循環機制

**來源**：`query.ts:1303` 和 `hooks.ts:3769`

```
第一次 Stop → stopHookActive = undefined → Hook 可阻擋
Hook 阻擋 → 設定 stopHookActive = true
模型繼續工作 → end_turn 再次觸發 Stop
第二次 Stop → stopHookActive = true → Hook 可讀取此旗標決定放行
```

> [!warning] `stop_hook_active` 不是硬性防護
> 系統**不會**自動跳過第二次的 Stop Hook 執行。它只是在 hookInput 中傳入 `stop_hook_active: true` 旗標，**由你的 Hook 腳本自行決定是否放行**。如果你的腳本忽略這個旗標且始終 exit 2，**就會進入無限循環**，直到 token 預算耗盡或使用者中斷。

**更危險的情況**：如果模型在第二輪完成工作後又自己停了（`query.ts:1110` 會把 `stopHookActive` 重設為 `undefined`），你的 Hook 會再次被觸發且看到 `active = false`。所以穩健的寫法應該：

```bash
# 方法一：信任 stop_hook_active 旗標（最簡單）
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then exit 0; fi

# 方法二：用檔案記錄計數（更穩健）
COUNT_FILE="/tmp/stop-hook-count-$SESSION_ID"
COUNT=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
if [ "$COUNT" -ge 2 ]; then
  rm -f "$COUNT_FILE"
  exit 0  # 最多阻擋 2 次
fi
echo $((COUNT + 1)) > "$COUNT_FILE"
```

### 2. SessionEnd Hook 的超時限制

**來源**：`src/utils/hooks.ts` 中的 `SESSION_END_HOOK_TIMEOUT_MS_DEFAULT = 1500`

SessionEnd Hook 只有 **1.5 秒**的執行時間。這是因為使用者正在離開，不應該等待太久。不適合做：
- 大檔案上傳
- 複雜的 API 呼叫
- 資料庫操作

適合做：
- 輕量 Webhook 通知
- 寫一行到本地 log 檔

### 3. 信任對話框（Trust Dialog）是硬性前提

**來源**：`src/utils/hooks.ts` — `shouldSkipHookDueToTrust()`

如果 workspace 未接受信任對話框，**所有 Hook 完全不執行**（靜默跳過，不報錯）。在 CI/CD 或 headless 環境中需要特別注意。

### 4. Hook 的效能影響

- Hook 是**同步阻塞**的（除非標記 `async: true`）
- `PreToolUse` 在**每次工具呼叫**時觸發，如果 Hook 腳本慢（>100ms），會明顯拖慢互動
- 來源 `toolExecution.ts:864-866`：超過 `SLOW_PHASE_LOG_THRESHOLD_MS` 的 Hook 會被記錄慢日誌
- 建議：高頻 Hook 用 Bash（10-20ms 啟動）或 Node.js（50-100ms），避免用 Python（200-400ms）

### 5. `updatedMCPToolOutput` 只能替換 MCP 工具輸出

來源 `src/types/hooks.ts:103-105`：

```typescript
updatedMCPToolOutput: z
  .unknown()
  .describe('Updates the output for MCP tools')
  .optional()
```

內建工具（Bash、Read、Write、Grep 等）的輸出**不可透過 Hook 替換**。這限制了 PostToolUse Hook 在內建工具上的能力——你只能注入 `additionalContext`，不能改寫結果。

### 6. `if` 條件使用 Permission Rule Syntax

`if` 欄位不是普通的正則表達式（regex），而是 Claude Code 內部的 Permission Rule Syntax：

```json
{
  "if": "Bash(git *)"     // ✅ 匹配 git 開頭的 Bash 指令
  "if": "Bash(rm *)"      // ✅ 匹配 rm 開頭的 Bash 指令
  "if": "Read(*.ts)"      // ✅ 匹配讀取 .ts 檔案
  "if": "Write(src/*)"    // ✅ 匹配寫入 src/ 下的檔案
}
```

不支援完整 regex，只支援 glob-like 匹配��

### 7. 設定檔優先順序

Hook 的載入有嚴格的優先順序：

```
policySettings（管理員強制）
  > userSettings（~/.claude/settings.json）
    > projectSettings（.claude/settings.json）
      > localSettings（.claude/settings.local.json）
        > pluginHook（Plugin 註冊）
          > sessionHook（SDK runtime 註冊）
```

`shouldAllowManagedHooksOnly()` 為 true 時，只有 policySettings 的 Hook 會執行。

### 8. 並行執行的副作用

同一事件的多個 Hook 是**並行**執行的。如果兩個 PreToolUse Hook 都回傳不同的 `updatedInput`，只有其中一個生效（取決於 Promise.all 的聚合邏輯）。同理，如果一個 Hook 回傳 `"allow"` 而另一個回傳 `"deny"`，`deny` 優先。

### 9. Prompt / Agent Hook 的模型成本

`prompt` 和 `agent` 類型的 Hook 會**呼叫 LLM API**，產生額外的 token 費用。預設使用 Haiku（最便宜），但仍需注意：
- 高頻事件（PreToolUse）搭配 prompt hook → 每次工具呼叫都多一次 API call
- agent hook 是多輪對話，成本更高
- 建議搭配 `if` 條件過濾，只在匹配時觸發

### 10. command Hook 的環境隔離

Command Hook 的 shell 環境來自 `subprocessEnv`（`src/utils/subprocessEnv.ts`），繼承了使用者的 shell profile。但：
- `PATH` 可能與使用者的互動式 shell 不同
- 不保證 nvm/pyenv/conda 等版本管理器已初始化
- 建議在 Hook 腳本中使用絕對路徑（如 `/usr/bin/jq`）

---

## HookResult 與 AggregatedHookResult 的聚合邏輯

來源：`src/types/hooks.ts:259-289`

```typescript
// 單個 Hook 的結果
export type HookResult = {
  message?: Message                         // UI 顯示的訊息
  systemMessage?: Message                   // 系統訊息
  blockingError?: HookBlockingError         // 阻塞錯誤
  outcome: 'success' | 'blocking' | 'non_blocking_error' | 'cancelled'
  preventContinuation?: boolean             // 阻止繼續
  stopReason?: string                       // 停止原因
  permissionBehavior?: 'ask' | 'deny' | 'allow' | 'passthrough'
  hookPermissionDecisionReason?: string     // 權限決策理由
  additionalContext?: string                // 注入的上下文
  initialUserMessage?: string               // 注入的初始訊息
  updatedInput?: Record<string, unknown>    // 修改後的工具輸入
  updatedMCPToolOutput?: unknown            // 修改後的 MCP 輸出
  permissionRequestResult?: PermissionRequestResult
  retry?: boolean                           // 是否重試
}

// 聚合後的結果（多個 Hook 合併）
export type AggregatedHookResult = {
  message?: Message
  blockingErrors?: HookBlockingError[]      // 所有 blocking errors
  preventContinuation?: boolean
  stopReason?: string
  hookPermissionDecisionReason?: string
  permissionBehavior?: PermissionResult['behavior']
  additionalContexts?: string[]             // ★ 複數！所有上下文合併
  initialUserMessage?: string
  updatedInput?: Record<string, unknown>
  updatedMCPToolOutput?: unknown
  permissionRequestResult?: PermissionRequestResult
  retry?: boolean
}
```

> [!note] `additionalContexts` 是陣列
> 多個 Hook 注入的 `additionalContext` 會被合併成 `additionalContexts[]` 陣列，全部注入給模型。這允許多個 Hook 各自注入不同的上下文而不互相覆蓋。

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可擴展性（Extensibility） | ⭐⭐⭐⭐⭐ | 24 個事件覆蓋完整生命週期，6 種 Hook 類型適應不同場景 |
| 安全設計（Security） | ⭐⭐⭐⭐ | Trust check、SSRF guard、env var 白名單、if 條件過濾 |
| 效能考量（Performance） | ⭐⭐⭐⭐ | 並行執行、async 模式、慢 hook 日誌 |
| 協議設計（Protocol） | ⭐⭐⭐⭐ | stdin/stdout JSON、exit code 語意化、discriminated union |
| 向後相容（Backward Compat） | ⭐⭐⭐ | 舊版 13 事件的 Hook 腳本仍可運作，新欄位都是 optional |

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷

- **Stop Hook 無限循環風險**：`stop_hook_active` 不是硬性防護，依賴使用者腳本自律。缺少系統層級的 max retry 限制
- **SessionEnd timeout 太短**：1.5 秒幾乎只夠做本地 I/O，任何網路操作都有失敗風險
- **Hook 間無通訊機制**：並行執行的多個 Hook 無法互相感知結果，可能產生衝突的決策（如一個 allow、一個 deny）
- **prompt/agent Hook 的隱性成本**：每次觸發都是一次 API call，在高頻事件上容易失控

---

## 我的心得（My Takeaways）

1. **Stop Hook 是最實用的功能**：它讓你能夠在模型「以為自己完成了」的時候攔住它，這對 autonomous agent 的品質控制至關重要
2. **hookSpecificOutput 的 discriminated union 設計值得學習**：不同事件有不同的回傳能力，用型別系統保證不會亂用
3. **exit code 2 的選擇很聰明**：避免 exit 1 的歧義，且在 shell 腳本中很容易使用
4. **async protocol 的設計很巧妙**：第一行 JSON 決定同步/非同步，簡單但有效
5. **寫 Hook 時最重要的三件事**：(a) 檢查 `stop_hook_active` 防循環，(b) 用 `if` 條件縮小觸發範圍，(c) 效能——高頻事件用 Bash 不用 Python

## 待補充（Open Questions）

- Hook 的 `if` 條件（Permission Rule Syntax）的完整語法文件在哪裡？目前只能從原始碼推斷 glob-like 匹配規則
- `asyncRewake: true` 的 Hook 在背景完成後，模型會收到什麼格式的喚醒訊息？目前只知道 exit code 2 會觸發，但具體的 message injection 流程未追蹤
- 多個 Hook 同時回傳 `updatedInput` 時的衝突解決策略是什麼？最後一個覆蓋？還是合併？需要追蹤 `AggregatedHookResult` 的聚合函式
- `WorktreeCreate` / `WorktreeRemove` / `InstructionsLoaded` 這些事件是否已有對應的 `execute*Hooks()` 實作？在目前的反編譯版本中只看到型別定義
- HTTP Hook 的 SSRF Guard（`src/utils/hooks/ssrfGuard.ts`）具體限制了哪些 URL 模式？是否阻擋 localhost / 內網 IP？
- `callback` 和 `function` 類型的 Hook 是否有公開的 SDK API 讓開發者註冊？目前看起來只供內部使用
- 搜尋關鍵字：`permission rule syntax claude code`、`asyncRewake hook protocol`、`SSRF guard claude code hooks`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | ① Hook 有 24 個事件 ② 6 種類型（command/prompt/agent/http/callback/function）③ exit code 2 = blocking ④ `hookSpecificOutput` 用 `hookEventName` 做 discriminator ⑤ Stop hook 有 `stop_hook_active` 防循環旗標 |
| **理解（半被動）** | 解釋概念的含義及關聯 | Hook 系統是 query loop 狀態機的外掛擴展點——hookInput 透過 stdin 傳入事件上下文，Hook 的 stdout JSON 透過 `AggregatedHookResult` 回饋到狀態機，改變 `state.messages`、`state.stopHookActive` 等欄位，驅動 query loop 的 `continue` 或 `return`。本質是 Event → Side-Effect → State Transition 的模式 |
| **分析（主動）** | 批判性思維，看透底層邏輯 | ① `stop_hook_active` 是軟旗標而非硬限制——系統信任 Hook 開發者的自律，這在團隊協作中是風險點 ② `updatedMCPToolOutput` 只限 MCP 工具是刻意的安全邊界——內建工具的輸出可信度更高，不應被外部 Hook 篡改 ③ 並行執行 + 無衝突解決 = 潛在的 race condition |
| **應用（主動）** | 將理論轉為行動 | ① **立即可做**：在 `~/.claude/settings.json` 加入 Stop Hook，用 `stop_hook_active` 做一次 checklist 驗證 ② **中期可做**：用 HTTP Hook 接入團隊的 CI/CD webhook，在 PreToolUse 時自動檢查 lint 規則 ③ **長期可做**：建立 Hook 腳本庫，按專案類型（前端/後端/基礎建設）組合不同的 Hook 集 |
| **評估（主動）** | 判斷多個方案的優劣 | command hook vs prompt hook：command 快（10-20ms Bash）但需維護腳本，prompt 慢（需 API call）但用自然語言描述條件。高頻事件（PreToolUse）選 command，低頻高判斷力場景（Stop）可考慮 prompt。agent hook 最貴（多輪對話）但最強大，僅適用於關鍵驗證 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「blocking error」在 Hook 系統中的精確定義是什麼？是 exit code 2 就夠、還是 stderr 也需要有內容？空 stderr 的 exit 2 會怎樣？
- **假設**：Stop Hook 的防循環設計假設 Hook 開發者會檢查 `stop_hook_active`。若此假設不成立（如團隊新人寫了不檢查的 Hook），最壞情況是無限循環消耗 token budget。是否應有系統層級的 max_stop_hook_retries？
- **證據**：文中稱「同一事件的 Hook 並行執行」，但如果兩個 Hook 都回傳 `updatedInput`，聚合邏輯如何處理？需要實際追蹤 `aggregateHookResults()` 函式
- **觀點**：若站在安全團隊的角度，`http` hook 允許 POST 到任意 URL 是否是供應鏈攻擊（Supply Chain Attack）的向量？惡意的 `.claude/settings.json` 可以把所有工具呼叫的上下文外洩
- **後果**：若大規模使用 prompt/agent hook，12 個月後可能出現的副作用：API 成本失控、Hook 延遲累積影響使用者體驗、Hook 腳本的維護債務

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — Stop Hook 無限循環會持續消耗 API token 直到預算耗盡或使用者手動中斷。在 headless/CI 環境中沒有人能中斷，可能造成巨額帳單。HTTP Hook 若配置不當（如指向惡意 URL），會外洩 session 上下文中的敏感資訊
2. **什麼情況下會失敗？** — (a) workspace 未接受 trust dialog → 所有 Hook 靜默失敗 (b) Hook 腳本依賴的工具不在 PATH 中（如 jq 未安裝）→ 非預期的 exit code (c) prompt/agent Hook 在 API rate limit 下會 timeout (d) SessionEnd Hook 在 1.5 秒內完不成網路請求
3. **有沒有更好的替代方案？** — 對於 Stop Hook 的 checklist 驗證場景，替代方案是把 checklist 寫進 CLAUDE.md 的 system prompt，讓模型自己遵守。優點：無延遲、不消耗額外 API；缺點：模型可能忽略 prompt 中的指令，Hook 是硬性的強制機制。建議兩者並用：CLAUDE.md 做軟提醒，Stop Hook 做硬驗證

---

## 相關連結（Related）

- [[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]] — 入門級 Hook 指南，涵蓋 13 個事件和基本設定
- [[2026-01-24-CLAUDE-CODE-HOOKS-CODE-ANALYSIS]] — 第三方 Hook 腳本集合（karanb192/claude-code-hooks）的程式碼分析
- [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] — Skill YAML frontmatter 中 hooks 欄位的內部運作
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — Claude Code 反編譯原始碼的整體概覽
- [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — settings.json 的層級與優先順序
- [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]] — 設定檔完整指南
- [[2026-04-29-CLAUDE-CODE-DISABLE-MODEL-INVOCATION-SKILL-VISIBILITY-SOURCE-ANALYSIS]] — Hook 無法直接呼叫 Skill 的原因分析，與本文 Hook 系統形成互補

## References

- 反編譯原始碼：`src/utils/hooks.ts`（主 Hook 引擎，~4600 行）
- Hook Schema 定義：`src/schemas/hooks.ts`
- Hook 型別定義：`src/types/hooks.ts`
- Hook 事件清單：`src/entrypoints/sdk/coreTypes.generated.ts`
- Query Loop 狀態機：`src/query.ts`
- Stop Hook 處理：`src/query/stopHooks.ts`
- 工具執行中的 Hook 呼叫：`src/services/tools/toolExecution.ts`
