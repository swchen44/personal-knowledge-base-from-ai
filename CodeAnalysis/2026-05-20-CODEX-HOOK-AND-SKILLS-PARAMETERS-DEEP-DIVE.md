---
title: "Codex Hook 系統參數與 Skills 搜尋路徑 — 原始碼層級深度規格"
date: 2026-05-20
category: CodeAnalysis
tags:
  - code-analysis
  - codex
  - hooks
  - skills
  - extension-api
source: "https://github.com/openai/codex"
source_type: code
author: "OpenAI"
status: notes
github_stars: 30000+
github_language: Rust
links:
  - "[[2026-05-20-CODEX-CLI-CODE-ANALYSIS]]"
  - "[[2026-05-20-CODEX-CLI-VS-CLAUDE-CODE-DEEP-COMPARISON]]"
  - "[[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]]"
---

## 摘要（Summary）

本筆記是 [[2026-05-20-CODEX-CLI-CODE-ANALYSIS]] 的延伸，回答兩個具體問題：

1. **Codex Hook 系統的輸入/輸出參數有哪些？** — 從 `codex-rs/hooks/` 與 `codex-rs/protocol/src/protocol.rs` 原始碼 + `hooks/schema/generated/` 中由 schemars 自動產出的 18 個 JSON schema fixture（9 種事件 × input/output），整理出 9 個事件的完整 wire schema。
2. **Codex Skills 的搜尋路徑是什麼？** — 從 `codex-rs/core-skills/src/loader.rs::skill_roots_from_layer_stack_inner` 與 `codex-rs/skills/src/lib.rs` 找出 6 個 skill root 來源、4 種 scope 優先級、scan 深度上限與 SKILL.md 格式。

簡言之：Codex 把 hook **雙層化**（內部 Rust in-process hook 只有 `AfterAgent`；外部 command hook 有 9 種事件），Skills **多層化**（6 個 root 來源、4 種 scope），全部用 schemars 自動產出可發布的 JSON schema，是 Codex 工程紀律的最佳範例。

## Why — 為什麼分這兩塊？

> Codex 採用「**核心薄、衛星厚**」策略：核心只暴露 hook 與 skill 兩個擴充面，其餘交由用戶/管理員/插件擴充。

- **Hook 系統** — 給外部腳本攔截 Codex 執行流程的機會（PreToolUse 可改寫 tool 輸入、PermissionRequest 可決定 allow/deny、UserPromptSubmit 可注入 context）。所有事件用 schemars 自動產 JSON schema，外部工具可依 schema 嚴格驗證 payload。
- **Skills 系統** — 給用戶/組織/插件提供「按描述自動觸發的能力包」。透過多層 SkillRoot 路徑 + scope 優先級，讓 admin / user / project / plugin 都能定義 skill，且不互相干擾。

## What — 是什麼？

- **Hook**：在 9 個 lifecycle 事件點，Codex 透過 stdin/stdout JSON 呼叫使用者註冊的外部 command（也支援 Prompt 與 Agent 兩種 handler 類型），允許 hook 改寫輸入、拒絕執行、注入 context、發出 systemMessage。
- **Skills**：以 `SKILL.md`（YAML frontmatter + Markdown）為單位的可重用能力包。Codex 啟動時從 6 個 root 來源掃描（最深 6 層、每 root 上限 2000 個），合併出 effective skill 集合，依 scope 排序，被 LLM 看到後可按 description 自動選用。

## How — 如何運作？

### Hook 系統架構圖

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Codex 主流程                                 │
│                                                                       │
│  user prompt ──► SessionStart hook ──► UserPromptSubmit hook ──►      │
│                                                                       │
│  LLM 決定 tool_call ──► PreToolUse hook ──► PermissionRequest hook    │
│                                              │                        │
│                                              ▼                        │
│                                       sandbox + execpolicy            │
│                                              │                        │
│                                              ▼                        │
│                                         執行 tool                      │
│                                              │                        │
│                                              ▼                        │
│                                       PostToolUse hook                │
│                                                                       │
│  context 超量 ──► PreCompact hook ──► 壓縮 ──► PostCompact hook        │
│                                                                       │
│  subagent 啟動 ──► SubagentStart hook                                  │
│                                                                       │
│  session 結束 ──► Stop hook                                            │
└──────────────────────────────────────────────────────────────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
   Command           Prompt              Agent
   handler           handler             handler
   (spawn shell)    (注入 prompt)        (呼 subagent)
       │                 │                 │
       ▼                 ▼                 ▼
   stdin JSON         注入 LLM         spawn subagent
   stdout JSON        context          完成後 callback
```

### Hook 執行時序圖

```
 Codex Core    HookDispatcher    Hook Process (外部 shell command)
     │               │                       │
     │──事件發生────►│                       │
     │               │                       │
     │               │──schema 驗證 input──►│
     │               │   (依 9 種 schema)    │
     │               │                       │
     │               │──spawn handler──────►│
     │               │   stdin = JSON       │
     │               │                       │ 處理...
     │               │                       │
     │               │◄─────stdout JSON─────│
     │               │   universal + hook_specific
     │               │                       │
     │               │──schema 驗證 output──┐│
     │               │                      ││
     │               │  解析 decision:      ││
     │               │   · approve/block    ││
     │               │   · allow/deny/ask   ││
     │               │   · updatedInput     ││
     │               │   · additionalContext││
     │               │                      ││
     │◄──HookResult──│                      ││
     │   · Success                          ││
     │   · FailedContinue                   ││
     │   · FailedAbort                      ││
     │                                      ││
     ▼                                      ││
 依 decision 繼續 / abort / 改寫           ─┘│
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> 把 hook 完整 schema 用 `schemars` 在編譯時自動產出 JSON schema fixture，並把產出的 JSON 同時 commit 到 `schema/generated/`（透過 `pnpm run write-hooks-schema`）。這讓外部 hook 作者有**官方權威 schema 可下載**，且**rebuild 時自動 diff 出 breaking change**。

1. **雙層 Hook 系統** — 內部 Rust API（`hooks/src/types.rs::HookEvent::AfterAgent`）給 in-process 編譯型 Rust hook 用；外部 command hook（9 種事件）給跨語言、跨進程的 shell command 用。兩者解耦，內部 API 可頻繁演進不影響外部 schema。
2. **3 種 handler type**（從 `HookHandlerType` enum）：`Command`（spawn shell）/ `Prompt`（注入 prompt）/ `Agent`（呼叫 subagent），各 type 有 timeout、async、windows fallback、status_message 設定。
3. **deny_unknown_fields + schemars** — 所有 wire struct 都用 `#[serde(deny_unknown_fields)]`，拒絕未知欄位；用 `schemars::JsonSchema` derive 自動產 schema。當 Cargo 結構改動時，`pnpm run write-hooks-schema` 會更新 `schema/generated/`，CI 會偵測 drift。
4. **PreToolUse 雙層決策** — top-level `decision: approve|block`（粗顆粒）+ `hookSpecificOutput.permissionDecision: allow|deny|ask`（細顆粒）。Hook 可只用粗的，也可用細的覆蓋 sandbox 預設行為。
5. **Reserved fields（fail-closed）** — `PermissionRequest` 的 `updatedInput / updatedPermissions / interrupt` 三個欄位「保留給未來」，**目前 hook 寫了就直接 fail closed**（拒絕該 hook）。是個有紀律的 forward-compat 設計：先把欄位定義出來避免未來改 schema，但執行時嚴格拒絕未實作的能力。

### 資料流

1. 事件發生（如 LLM 要呼叫 shell tool）→ HookDispatcher 收到 internal event
2. 依 `HookEventName` 查找註冊的 hook（多層 source：Plugin / User / Project / Mdm / CloudRequirements / SessionFlags / System / LegacyManagedConfigFile / LegacyManagedConfigMdm / Unknown）
3. 對每個 matched hook：spawn process → 寫入 stdin JSON（依 `*-input.schema.json`）
4. 等待 stdout JSON（依 `*-output.schema.json`）
5. 解析 output → 決定 `HookResult`（Success / FailedContinue / FailedAbort）
6. 累積 `HookRunSummary`（含 entries: Warning/Stop/Feedback/Context/Error）
7. 多個 hook 串行（同 matcher group 內）或並行（不同 group 間）執行

### 關鍵程式碼（Key Code Snippets）

**內部 Rust in-process hook**（取自 `hooks/src/types.rs`）：

```rust
pub type HookFn = Arc<dyn for<'a> Fn(&'a HookPayload) -> BoxFuture<'a, HookResult> + Send + Sync>;

#[derive(Debug)]
pub enum HookResult {
    /// Success: hook completed successfully.
    Success,
    /// FailedContinue: hook failed, but other subsequent hooks should still execute and the
    /// operation should continue.
    FailedContinue(Box<dyn std::error::Error + Send + Sync + 'static>),
    /// FailedAbort: hook failed, other subsequent hooks should not execute, and the operation
    /// should be aborted.
    FailedAbort(Box<dyn std::error::Error + Send + Sync + 'static>),
}

#[derive(Debug, Serialize, Clone)]
#[serde(rename_all = "snake_case")]
pub struct HookPayload {
    pub session_id: ThreadId,
    pub cwd: AbsolutePathBuf,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub client: Option<String>,
    #[serde(serialize_with = "serialize_triggered_at")]
    pub triggered_at: DateTime<Utc>,
    pub hook_event: HookEvent,
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "event_type", rename_all = "snake_case")]
pub enum HookEvent {
    AfterAgent {
        #[serde(flatten)]
        event: HookEventAfterAgent,
    },
}
```

**`HookEventName` 列舉**（取自 `protocol/src/protocol.rs:1332`）：

```rust
#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq, JsonSchema, TS, EnumIter)]
#[serde(rename_all = "snake_case")]
pub enum HookEventName {
    PreToolUse,
    PermissionRequest,
    PostToolUse,
    PreCompact,
    PostCompact,
    SessionStart,
    UserPromptSubmit,
    SubagentStart,
    Stop,
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq, JsonSchema, TS)]
#[serde(rename_all = "snake_case")]
pub enum HookHandlerType { Command, Prompt, Agent }

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq, JsonSchema, TS)]
#[serde(rename_all = "snake_case")]
pub enum HookSource {
    System, User, Project, Mdm,
    SessionFlags, Plugin, CloudRequirements,
    LegacyManagedConfigFile, LegacyManagedConfigMdm,
    Unknown,
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq, JsonSchema, TS)]
#[serde(rename_all = "snake_case")]
pub enum HookOutputEntryKind { Warning, Stop, Feedback, Context, Error }
```

---

## 9 個 Hook 事件的完整參數規格

> [!important] 來源 = `codex-rs/hooks/schema/generated/{event}.command.{input|output}.schema.json`，由 `pnpm run write-hooks-schema` 自動產出。

### 共同 Input 欄位（所有事件）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `session_id` | `string` | 當前 session 的 ThreadId |
| `turn_id` | `string` | **Codex extension**：當前 turn ID（給 turn-scoped hook 用） |
| `transcript_path` | `string \| null` | session rollout JSONL 的路徑（可用來事後讀對話） |
| `cwd` | `string` | 當前工作目錄 |
| `hook_event_name` | const string | 該事件的常數名（如 `"PreToolUse"`） |
| `model` | `string` | 當前 LLM 模型 ID |
| `permission_mode` | enum | `"default"` / `"acceptEdits"` / `"plan"` / `"dontAsk"` / `"bypassPermissions"` |

### 共同 Output 欄位（HookUniversalOutputWire）

| 欄位 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `continue` | `bool` | `true` | 是否繼續執行後續 hook / 主流程 |
| `stopReason` | `string \| null` | `null` | 若 `continue=false`，這裡可說明原因 |
| `suppressOutput` | `bool` | `false` | 是否抑制 hook 的輸出顯示給使用者 |
| `systemMessage` | `string \| null` | `null` | 注入給 LLM 的系統訊息 |

> 注：所有 output 用 `camelCase`，所有 input 用 `snake_case`。這是 Codex 故意維持的 wire 一致性慣例（input 來自 Codex 自己，sticks to Rust snake_case；output 由使用者寫的 handler 回，沿用 Web/JS camelCase）。

### 1. PreToolUse — Tool 執行前

**Input 額外欄位**：

| 欄位 | 型別 |
|------|------|
| `tool_name` | `string` |
| `tool_input` | `any`（tool 參數，schema 標 `true`） |
| `tool_use_id` | `string` |

**Output 額外能力**：

| 欄位 | 值 / 結構 | 用途 |
|------|-----------|------|
| `decision` | `"approve"` / `"block"` | 粗顆粒批准/阻擋 |
| `reason` | `string` | 解釋 decision |
| `hookSpecificOutput.permissionDecision` | `"allow"` / `"deny"` / `"ask"` | 細顆粒，覆蓋 sandbox 預設 |
| `hookSpecificOutput.permissionDecisionReason` | `string` | 解釋 permissionDecision |
| `hookSpecificOutput.updatedInput` | `any` | **改寫 tool 輸入**（最強能力之一） |
| `hookSpecificOutput.additionalContext` | `string` | 注入 LLM context |

### 2. PermissionRequest — 權限請求

**Input 額外欄位**：`tool_name`、`tool_input`（**無 `tool_use_id`**，與 PreToolUse 區別）

**Output 額外能力**：

| 欄位 | 值 |
|------|-----|
| `hookSpecificOutput.decision.behavior` | `"allow"` / `"deny"` |
| `hookSpecificOutput.decision.message` | `string` |
| `hookSpecificOutput.decision.updatedInput` ⚠️ | **保留，現在會 fail closed** |
| `hookSpecificOutput.decision.updatedPermissions` ⚠️ | **保留，現在會 fail closed** |
| `hookSpecificOutput.decision.interrupt` ⚠️ | **保留，true 會 fail closed** |

### 3. PostToolUse — Tool 執行後

**Input 額外欄位**：`tool_name`、`tool_input`、`tool_response`（**多了 tool 的回應**）、`tool_use_id`

**Output 額外能力**：

| 欄位 | 值 |
|------|-----|
| `decision` | `"block"`（**只能 block，不能 approve**） |
| `reason` | `string` |
| `hookSpecificOutput.additionalContext` | `string` |
| `hookSpecificOutput.updatedMCPToolOutput` | `any`（**改寫 MCP tool 輸出**）|

### 4. PreCompact / 5. PostCompact — 對話壓縮前後

**Input 額外欄位**：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `trigger` | enum | 壓縮觸發原因（由 `compaction_trigger_schema` 定義） |

**Output**：只有 universal output（無事件特定欄位）

### 6. SessionStart — Session 啟動

**Input 額外欄位**：

| 欄位 | 值 |
|------|-----|
| `source` | `"startup"` / `"resume"` / `"clear"` |

**Output 額外能力**：

| 欄位 | 值 |
|------|-----|
| `hookSpecificOutput.additionalContext` | `string`（**啟動時注入 context — 最常見的 hook 用途**） |

### 7. UserPromptSubmit — 使用者送出 prompt

**Input 額外欄位**：

| 欄位 | 型別 |
|------|------|
| `prompt` | `string`（使用者輸入的 prompt 內容） |

**Output 額外能力**：

| 欄位 | 值 |
|------|-----|
| `decision` | `"block"`（**只能 block，不能 approve** — 因為 user prompt 本來就是 allowed）|
| `hookSpecificOutput.additionalContext` | `string` |

### 8. SubagentStart — Subagent 啟動

Schema 與 SessionStart output 同構（共用 `SessionStartHookSpecificOutputWire`）。Input 內容應與 SessionStart 類似但語意上對應 subagent 而非主 session。

### 9. Stop — Session / Turn 停止

只有 universal output（從 schema 名稱推斷無事件特定欄位）。

### 額外 wire enum

```rust
// schema.rs::PreToolUseDecisionWire
"approve" | "block"

// schema.rs::PreToolUsePermissionDecisionWire
"allow" | "deny" | "ask"

// schema.rs::PermissionRequestBehaviorWire
"allow" | "deny"

// schema.rs::BlockDecisionWire (用於 PostToolUse / UserPromptSubmit)
"block"   // 注意：只有 block，沒有 approve
```

---

## Skills 搜尋路徑完整地圖

> [!important] 來源 = `codex-rs/core-skills/src/loader.rs::skill_roots_from_layer_stack_inner` + `codex-rs/skills/src/lib.rs`。

### Skill Root 來源（6 條搜尋路徑）

按 `ConfigLayerStackOrdering::HighestPrecedenceFirst` 順序：

| # | 來源 | 路徑 | Scope | 備註 |
|---|------|------|-------|------|
| 1 | **Project**（`ConfigLayerSource::Project`） | `{project_config_folder}/skills/` | `Repo` | 由 project 的 ConfigLayerStack 決定 |
| 2a | **User（deprecated）** | `{CODEX_HOME}/skills/` 即 `~/.codex/skills/` | `User` | 向後相容，建議改用 2b |
| 2b | **User（推薦）** | `$HOME/.agents/skills/` | `User` | 主要使用者 skill 路徑 |
| 3 | **System（embedded）** | `{CODEX_HOME}/skills/.system/` 即 `~/.codex/skills/.system/` | `System` | 從 Codex 二進位內嵌（`include_dir!` 編譯時打包）解壓出來；用 `.codex-system-skills.marker` 檔記錄指紋避免重複展開 |
| 4 | **Admin** | `/etc/codex/skills/`（Unix） | `Admin` | 從 `ConfigLayerSource::System` 推 |
| 5 | **Plugin** | 各 plugin 提供的 `PluginSkillRoot.path` | `User` | 含 `plugin_id` 標記 |
| 6 | **Repo agents 路徑（cwd 向上）** | 從 cwd 走到 project_root，每一層的 `{dir}/.agents/skills/` | `Repo` | 動態探測 |

### Scope 優先級（排序權重）

```rust
fn scope_rank(scope: SkillScope) -> u8 {
    // 數字越小，sort 時越前面
    match scope {
        SkillScope::Repo => 0,
        SkillScope::User => 1,
        SkillScope::System => 2,
        SkillScope::Admin => 3,
    }
}
```

> [!warning] Scope 排序的語意
> `scope_rank` **只決定 sort 顯示順序與 dedupe 時誰先被保留**（前面的會被 `seen.insert()` 鎖定，後面同名同路徑被略過）。它不是「override 鏈」—— 同名 skill 不會自動覆蓋，而是同 `path_to_skills_md` 才會 dedupe。

### Skill 檔案結構

每個 skill 目錄至少要有：

```
{skill-dir}/
├── SKILL.md                    ← 必有；YAML frontmatter + Markdown 本文
└── agents/                      ← 可選；進階 metadata
    └── openai.yaml              ← interface + dependencies + policy
```

**`SKILL.md` frontmatter 結構**（取自 `loader.rs::SkillFrontmatter`）：

```yaml
---
name: my-skill              # 必填
description: ...            # 必填
metadata:
  short-description: ...    # 可選
---

# 這裡開始是 Markdown 本文
```

**`agents/openai.yaml` 結構**（取自 `loader.rs::SkillMetadataFile`）：

```yaml
interface:
  display_name: My Skill
  short_description: ...
  icon_small: icons/small.png
  icon_large: icons/large.png
  brand_color: "#FF6600"
  default_prompt: ...

dependencies:
  tools:
    - type: mcp                  # 工具類型
      value: filesystem
      description: ...
      transport: stdio
      command: npx ...
      url: ...

policy:
  allow_implicit_invocation: true
  products:
    - Codex                       # 限定哪些 product 可用
```

### 掃描限制

| 常數 | 值 | 影響 |
|------|-----|------|
| `MAX_SCAN_DEPTH` | `6` | 從 skill root 向下最多走 6 層 |
| `MAX_SKILLS_DIRS_PER_ROOT` | `2000` | 一個 root 最多被偵測 2000 個 skills |
| `MAX_NAME_LEN` | `64` | `name` 欄位上限 |
| `MAX_DESCRIPTION_LEN` | `1024` | `description` 欄位上限 |
| `MAX_DEFAULT_PROMPT_LEN` | `1024` | `default_prompt` 上限 |
| `MAX_DEPENDENCY_*_LEN` | `64` / `1024` | dependency 欄位上限 |

### Skill 載入流程

```
codex 啟動
  │
  ▼
SkillsManager::new()
  │
  ├─► install_system_skills()  ── 寫入 ~/.codex/skills/.system/
  │   (從 binary include_dir! 內嵌解壓 + marker 檢查)
  │
  ▼
SkillsManager::skills_for_cwd(input)
  │
  ▼
skill_roots(fs, config_layer_stack, cwd, plugin_skill_roots)
  │
  ├─► skill_roots_from_layer_stack_inner  ── 路徑 1-4
  ├─► plugin_skill_roots                   ── 路徑 5
  └─► repo_agents_skill_roots              ── 路徑 6（cwd 向上找）
  │
  ▼
load_skills_from_roots(roots)
  │
  ├─► 對每個 root 呼叫 discover_skills_under_root
  │   ├─ 用 `fs.get_metadata` 確認 root 存在
  │   ├─ BFS 掃描，最多 6 層
  │   ├─ 找到 SKILL.md 就 parse frontmatter
  │   ├─ 找到對應 agents/openai.yaml 就讀進階 metadata
  │   └─ 超過 MAX_SKILLS_DIRS_PER_ROOT 即停止
  │
  ├─► dedupe by path_to_skills_md
  ├─► 依 scope_rank → name → path 排序
  │
  ▼
build_implicit_skill_path_indexes
  │
  ▼
filter_skill_load_outcome_for_product（依 restriction_product 過濾）
  │
  ▼
resolve_disabled_skill_paths（依 config rules 停用）
  │
  ▼
finalize_skill_outcome → SkillLoadOutcome
  │
  ▼
LLM 看到合併後的 skill 清單（含 name + description + scope）
```

## 安裝流程（Installation Flow）

> [!info] 與 [[2026-05-20-CODEX-CLI-CODE-ANALYSIS]] 的安裝產物互補

### 第一次啟動 Codex 時 — Hook / Skill 相關產物

```
codex 第一次啟動
  │
  ├─► SkillsManager::new()
  │   └─► install_system_skills() 把 binary embedded 內建 skills 解壓到：
  │       ~/.codex/skills/.system/
  │       ~/.codex/skills/.system/.codex-system-skills.marker
  │
  └─► 不會自動建立 ~/.codex/skills/、~/.agents/skills/、/etc/codex/skills/
      （這些由使用者/admin 自行建立）
```

### 安裝產物清單（hook + skills）

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.codex/skills/.system/` | 目錄 | Codex 內建 skills（從 binary 內嵌解壓）|
| `~/.codex/skills/.system/.codex-system-skills.marker` | 標記檔 | 指紋；避免重複解壓 |
| `~/.codex/skills/` | 目錄（使用者建） | 使用者 skills（deprecated 路徑） |
| `~/.agents/skills/` | 目錄（使用者建） | **使用者 skills（推薦路徑）** |
| `/etc/codex/skills/` | 目錄（admin 建，Unix） | Admin / 組織層 skills |
| `{project}/.agents/skills/` | 目錄（repo 建） | 專案層 skills，會被 cwd 向上找到 |
| `~/.codex/config.toml` | TOML | 含 `[[hooks]]` 段定義 hook |
| `~/.codex/requirements.toml` | TOML | `allow_managed_hooks_only = true` 可禁用 user/project/session hooks |

### 解除安裝

- Skills：`SkillsManager::new(..., bundled_skills_enabled=false)` 會呼叫 `uninstall_system_skills`（即 `std::fs::remove_dir_all(~/.codex/skills/.system/)`）
- Hooks：使用者刪 `~/.codex/config.toml` 中對應段；或 admin 在 `requirements.toml` 設 `allow_managed_hooks_only = true`

---

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發 | 入口檔 | 核心鏈 |
|---|---------|------|--------|--------|
| 1 | 寫一個 PreToolUse hook 攔截 shell 並改寫 | LLM tool_call | `hooks/src/engine/dispatcher.rs` | `dispatcher → schema_loader → spawn process → 讀 stdin/stdout → 改 tool_input` |
| 2 | 寫一個 SessionStart hook 注入 context | session 啟動 | 同上 | 同上，回 `additionalContext` |
| 3 | 寫一個 SKILL.md 給 codex 自動載入 | codex 啟動掃描 | `core-skills/src/manager.rs` | `SkillsManager::skills_for_cwd → skill_roots → load_skills_from_roots → discover_skills_under_root` |
| 4 | 用 admin 強制限制 hook | `requirements.toml` | `core-skills` 中的 `requirement_layer` 過濾 | `requirements.toml::allow_managed_hooks_only = true` |

### 案例 1：寫一個 PreToolUse hook（改寫 shell 命令）

```
使用者寫 ~/.codex/config.toml：
  [[hooks]]
  event = "pre_tool_use"
  matcher = { tool_name = "Bash" }
  type = "command"
  command = "/usr/local/bin/codex-hook.sh"
  timeout_sec = 5
  │
  ▼
codex 啟動 → 解析 config → 註冊到 HookDispatcher
  │
  ▼
LLM 回 tool_call(Bash, "rm -rf node_modules")
  │
  ▼
dispatcher 認出 event = PreToolUse，matcher 命中
  │
  ▼
spawn /usr/local/bin/codex-hook.sh
  · stdin = {"session_id":...,"turn_id":...,"cwd":...,
             "hook_event_name":"PreToolUse",
             "tool_name":"Bash",
             "tool_input":{"command":"rm -rf node_modules"},
             "tool_use_id":...,
             "model":"gpt-5.3-codex",
             "permission_mode":"default",
             "transcript_path":"~/.codex/sessions/rollout-...jsonl"}
  │
  ▼
hook 處理後 stdout：
  {"hookSpecificOutput":{
     "hookEventName":"PreToolUse",
     "permissionDecision":"allow",
     "updatedInput":{"command":"rm -rfv node_modules"},
     "additionalContext":"已加上 -v 顯示細節"
   },
   "systemMessage":"hook 已調整命令以便除錯"}
  │
  ▼
dispatcher 驗證 schema → HookResult::Success → Codex 用 updatedInput 取代原 tool_input → 進 sandbox 執行
```

### 案例 2：寫一個 SessionStart hook（注入專案規則）

```
~/.codex/config.toml:
  [[hooks]]
  event = "session_start"
  type = "command"
  command = "/usr/local/bin/inject-rules.sh"
  │
  ▼
session 啟動 → dispatcher 呼叫
  · stdin = {..., "hook_event_name":"SessionStart", "source":"startup"}
  │
  ▼
hook stdout：
  {"hookSpecificOutput":{
     "hookEventName":"SessionStart",
     "additionalContext":"專案規則：(1) 不要動 db/migrations；(2) 改 schema 前必須跑 alembic check"
   }}
  │
  ▼
Codex 把 additionalContext 注入 system prompt → LLM 開始 turn 時看得到
```

### 案例 3：寫一個 SKILL.md 給 Codex 自動載入

```
使用者建立：~/.agents/skills/refactor-helper/SKILL.md

---
name: refactor-helper
description: 用 AST 重構大型 TypeScript 專案，能拆檔、改名、抽 hook
metadata:
  short-description: TS 重構
---

# 工作流

1. 找出要重構的檔案...
  │
  ▼
codex 啟動 → SkillsManager::new()
  │
  ▼
skills_for_cwd → skill_roots：
  · ~/.codex/skills/  (deprecated)
  · ~/.agents/skills/  ✅ 命中 refactor-helper/SKILL.md
  · ~/.codex/skills/.system/  (內建)
  · /etc/codex/skills/  (若有)
  · {project}/.agents/skills/  (若 cwd 在 repo 內)
  · plugin paths  (若有 plugin)
  │
  ▼
load_skills_from_roots：
  · BFS 掃描 ~/.agents/skills/，最深 6 層
  · 在 refactor-helper/ 找到 SKILL.md
  · parse YAML frontmatter → SkillMetadata
  · 找不到 agents/openai.yaml → 沒有 interface/policy
  │
  ▼
dedupe + sort by scope (Repo=0, User=1, System=2, Admin=3)
  · refactor-helper.scope = User → rank 1
  │
  ▼
LLM 收到 system prompt 含 skill 描述 → 對話中可自動觸發 refactor-helper
```

### 案例 4：Admin 強制限制 hook 來源

```
/etc/codex/requirements.toml（admin 寫入）：
  allow_managed_hooks_only = true
  │
  ▼
codex 啟動 → 解析 ConfigLayerStack
  │
  ▼
HookSource 過濾：
  · System → ✅ 保留（內建）
  · Mdm / CloudRequirements → ✅ 保留（管理員設）
  · LegacyManagedConfigMdm → ✅ 保留
  · User / Project / SessionFlags / Plugin → ❌ 全部禁用
  · LegacyManagedConfigFile → ❌ 禁用
  │
  ▼
即使使用者 ~/.codex/config.toml 寫了 hook，runtime 也不會執行
```

---

## 架構師觀點（Architect's View）

### ✅ 優點

| 面向 | 評估 | 說明 |
|------|------|------|
| Schema 可發布（Publishable Schema）| ⭐⭐⭐⭐⭐ | 用 schemars 自動產 18 個 JSON schema fixture，外部 hook 作者可下載直接驗證；CI 偵測 schema drift |
| 安全性 | ⭐⭐⭐⭐⭐ | `deny_unknown_fields` 拒絕未知欄位；reserved fields fail-closed；`allow_managed_hooks_only` 給 admin 一鍵禁用使用者 hook |
| 擴充面廣度 | ⭐⭐⭐⭐ | 9 個 lifecycle 事件 × 3 種 handler type（Command/Prompt/Agent）= 27 種組合 |
| Skills 多 scope 設計 | ⭐⭐⭐⭐⭐ | 6 條搜尋路徑 + 4 種 scope，個人、組織、專案、插件各有獨立空間，互不干擾 |
| 內外解耦 | ⭐⭐⭐⭐⭐ | 內部 Rust API（types.rs::HookEvent::AfterAgent）vs 外部 command hook 兩條獨立演進線 |

> [!tip] 值得學習的設計
> 1. **「Schema 自動產出 + CI fixture」流程**：把 wire schema 用 `schemars::JsonSchema` derive 在 Rust 端，產出 JSON schema 並 commit 到 repo，外部 hook 作者下載即用，rebuild 時 diff 即可看出 breaking change
> 2. **「保留欄位 fail-closed」紀律**：把未來要實作的能力先在 schema 留位（`updatedInput`/`updatedPermissions`/`interrupt`），但 runtime 寫了就拒絕。避免 schema 演進時破壞既有 hook
> 3. **「snake_case input / camelCase output」雙慣例**：Codex 自己產的 payload 用 Rust 風格，使用者寫的 handler 回應用 JS/Web 風格 —— 兩邊都不違反語言慣例

### ⚠️ 缺點與風險

- **沒有官方 hook handler boilerplate / SDK** — 9 種事件 × 5+ 共同欄位 × 各自的 hook_specific_output，新手寫第一個 hook 學習成本不小；目前沒看到官方 helper crate 或 npm 包
- **`updatedInput` 改寫 tool 輸入是高權力低監督** — Hook 可悄悄改寫 LLM 的 tool 輸入而使用者不一定知道；audit 路徑不明
- **Skills 沒有 namespace 衝突偵測** — 兩個 root 都有 `refactor-helper/SKILL.md` 但路徑不同，會兩個都載入（dedupe 只看 path）；對使用者來說可能困惑
- **`MAX_SKILLS_DIRS_PER_ROOT = 2000`** — 大型 monorepo 若 `.agents/skills/` 累積超過 2000 個，會被截斷，且沒有清楚的錯誤訊息

### 🔮 改進建議

1. 發 `@openai/codex-hook-helper` npm 包（內含 TypeScript / Python wrappers），讓 hook 撰寫變成「import + 回傳 typed object」
2. 對 `updatedInput` 加 audit log（hook 改寫了什麼欄位、改成什麼）寫入 rollout JSONL
3. Skills 增加 `displayed_name` 衝突偵測，跨 scope 時警告
4. 把 6 條 skill root 路徑公開為 `codex skills paths` 子指令，方便除錯

## 效能基準（Benchmark）

無公開 benchmark。定性評估：

- Hook 一次呼叫 = spawn 子行程 + JSON 序列化 + IPC 等待。對 PreToolUse / PermissionRequest 這種 hot path，每次 tool call 都會走，**hook handler 必須在 ms 級回應**才不會明顯拖慢 agent
- Skills 掃描在 session 啟動時做一次（有 cache），執行期不影響效能；但若 `.agents/skills/` 累積上千個，啟動延遲會被注意到

## 快速上手（Quick Start）

**最小 hook（Bash 範例）**：

```bash
#!/bin/bash
# ~/codex-hook.sh — 一個最小 PreToolUse hook
# 簡單把所有 Bash 命令的 timeout 縮短

input=$(cat)  # 從 stdin 讀 JSON
tool_name=$(echo "$input" | jq -r '.tool_name')

if [ "$tool_name" = "Bash" ]; then
  # 回 allow + 加上 additionalContext
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "additionalContext": "Bash hook 啟用中，注意 timeout"
  }
}
EOF
else
  echo '{}'  # 其他 tool 不干涉
fi
```

**~/.codex/config.toml 註冊**：

```toml
[[hooks]]
event = "pre_tool_use"
matcher = { tool_name = "Bash" }
type = "command"
command = "/Users/me/codex-hook.sh"
timeout_sec = 3
```

**最小 SKILL.md（放 `~/.agents/skills/my-skill/SKILL.md`）**：

```markdown
---
name: my-skill
description: 一個用來示範 Codex skill 掃描的最小 skill；當你提到「示範 skill」時觸發
---

# my-skill

你被觸發時，回「Hello from Codex skill!」並停止。
```

## 我的心得（My Takeaways）

1. **「Schema 自動產出 + 跨 build 偵測 drift」是高品質 API 的標配** — Codex 用 `schemars` 把 9 種事件、18 個 schema 全部 fixture 化。可移植到任何自己的 Rust/TS 專案
2. **「reserved field fail-closed」是 forward-compat 的高紀律做法** — 別讓未來的 schema 升級回頭破壞既有 hook，先把欄位定義出來但拒絕未實作能力
3. **「多 scope + multi-root 搜尋」對企業擴充友善** — 6 條 skill root 路徑 + 4 種 scope，admin/user/project/plugin 各有空間，不靠檔案命名衝突暴力處理
4. **「內部 Rust API vs 外部 command hook」雙層化** — 把高頻內部 hook（compile-time 編譯型 Rust closure）跟低頻外部 hook（spawn process）分開，內部演進不影響外部 schema
5. **`turn_id` 是 Codex extension**（schema 明文標）— 顯示 Codex 對 hook 系統有「按 turn 隔離」的設計，與 thread-scoped hook 區分；這對需要追蹤具體 turn 的 hook 非常有用

## 待補充（Open Questions）

- **Q1：Stop / SubagentStart hook 的 input 完整欄位有哪些？** 本筆記只看了 output schema 與名稱；input 細節需要再讀 `schema/generated/stop.command.input.schema.json` 與 `subagent-start.command.input.schema.json`（搜尋：`codex stop subagent_start hook schema`）
- **Q2：Hook 在多個 matcher group 之間是並行還是順序？** 從 declarations.rs 看到 `into_matcher_groups()` 與 `group.hooks`，需讀 dispatcher.rs 確認執行語意（搜尋：`codex hook matcher group execution order`）
- **Q3：`tool_input` 是 free-form `any`，handler 怎麼知道每個 tool 的 schema？** 是否有對應的 tool schema registry？（搜尋：`codex tool_input schema discovery`）
- **Q4：`updatedMCPToolOutput`（PostToolUse）真的能改寫嗎？** 還是會被忽略？需測試 + 看 dispatcher.rs（搜尋：`codex PostToolUse updatedMCPToolOutput dispatcher`）
- **Q5：Skill 同名衝突怎麼處理？** 兩個 root 都有 `name: foo` 的 SKILL.md（不同路徑），dedupe 只看 path，但 LLM 看到兩個 `foo` 怎麼選？（搜尋：`codex skill name collision`）
- **Q6：`policy.allow_implicit_invocation = false` 的 skill 怎麼觸發？** Skill 設定為「不允許自動觸發」時，使用者要怎麼明確呼叫？（搜尋：`codex skill explicit invocation`）
- **Q7：`MAX_SCAN_DEPTH=6` 是否含 SKILL.md 本身？** 影響 monorepo 中 skill 放在 `apps/x/y/.agents/skills/z/` 這種深層位置時能否被找到（搜尋：`codex skill scan depth limit`）

## 相關連結（Related）
- [[2026-05-22-SKILLOPT-SELF-EVOLVING-AGENT-SKILLS-CODE-ANALYSIS]] — SkillOpt：把 Agent 技能當神經網路訓練的文字空間優化器（驗證閘門/minibatch 反思/學習率裁剪）
- [[2026-05-23-RTK-RUST-TOKEN-KILLER-LOG-COMPRESSION-ARCHITECTURE]] — RTK 展示了 hook rewrite 如何把 shell command 在進入模型上下文前改寫與壓縮，可對照 Codex hook / skill 搜尋路徑限制。

- [[2026-05-20-CODEX-CLI-CODE-ANALYSIS]] — Codex CLI 主筆記；本文是其「Hook + Skills」面向的深度補完
- [[2026-05-20-CODEX-CLI-VS-CLAUDE-CODE-DEEP-COMPARISON]] — 兩家對比文；本文補完了 Codex 端 hook / skill 的具體事實
- [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]] — Claude Code Hook API 對照；兩家事件清單高度相似（PreToolUse / PostToolUse / UserPromptSubmit / SessionStart / Stop / PreCompact / SubagentStop），可逐項對比
- [[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]] — gstack 跨多 host 整合中，Codex 的 skill root 是其支援的目標之一
- [[2026-08-14-CLAUDE-CODE-SKILL-BUDGET-MECHANISM-AND-REDUCTION-FLOW]] — Claude Code 的 skill 清單 1% 預算機制與 Codex 硬上限＋顯式開關的跨工具對照
- [[2026-08-18-KB-NAVIGATION-VS-BARE-AGENT-EXPERIMENT-30-NOTES-FILENAME-BEATS-SKILL-TREE]] — 本篇的 1024 上限等事實作為 KB 檢索實驗的 gold 題目來源，實驗證實檔名可直達

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 必記：(1) Codex 有 9 種 hook event（PreToolUse / PermissionRequest / PostToolUse / PreCompact / PostCompact / SessionStart / SubagentStart / UserPromptSubmit / Stop）；(2) 3 種 handler type（Command / Prompt / Agent）；(3) Skills 有 6 條 root 路徑；(4) 共同 input 7 欄、共同 output 4 欄；(5) 內部 Rust hook 只有 `AfterAgent` |
| **理解（半被動）** | 解釋概念的含義及關聯 | Codex 把 hook 雙層化：內部 Rust API（in-process，類型安全，給 codex-core 自己用）vs 外部 command hook（spawn process + JSON，給使用者跨語言擴充）。Skills 多 scope 化：用 6 條 root 路徑配合 4 種 scope，讓「個人/組織/專案/插件」各有空間又不衝突。schemars 自動產 schema 串起兩層 |
| **分析（主動）** | 找出假設 | 假設：(1) 「使用者 hook 在 ms 級回應」— 不然會明顯拖慢 agent；(2) 「使用者願意 maintain JSON schema 一致」— 但沒提供官方 helper SDK，使用者要自己 parse；(3) 「`updatedInput` 改寫不需 audit」— 高權力低監督；(4) 「6 條 root 路徑能覆蓋所有合理需求」— 但 Windows 沒有 `/etc/codex/`，跨平台是否一致？ |
| **應用（主動）** | 規劃執行方案 | 立即可做：(A) 用 PreToolUse hook 攔截 Bash 並對 `rm -rf` 強制加 confirmation；(B) 用 SessionStart hook 自動注入專案規則（替代 `~/.codex/CLAUDE.md` 等 static 文件）；(C) 在 monorepo 設 `.agents/skills/` 讓專案層 skill 自動隨 cwd 進入而生效；(D) 用 admin `requirements.toml::allow_managed_hooks_only = true` 強制企業政策 |
| **評估（主動）** | 多方案權衡 | Codex hook（9 種事件 + 3 種 handler + Schema 自動產出）vs Claude Code hook（7 種事件 + JSONL stdin/stdout 但無 reserved field fail-closed）：Codex 更工程化（schemars + fail-closed + admin override），但學習曲線陡；Claude Code 更上手（純 JSON + 簡單事件），但企業治理較弱。**選 Codex**：若需要嚴格 schema validation + 企業 admin override；**選 Claude Code**：若以個人/小團隊為主，不需要 reserved field 等紀律 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「9 種 hook event」中 PreCompact / PostCompact 與 PreToolUse / PostToolUse 都是配對，但 SessionStart 沒有 SessionEnd，反而有 Stop — Stop 是 SessionEnd 還是 TurnStop？事件命名是否一致？
- **假設**：本文假設 hook handler 是受信任的（trusted），但若 admin 註冊的 hook 本身有漏洞或惡意，能繞過 sandbox 嗎？hook 是在 sandbox 內還是外執行？
- **證據**：「Skills 載入有 cache」這點來自 `cache_by_cwd` 與 `cache_by_config` 兩個 RwLock；cache invalidation 機制（`clear_cache`）的觸發時機？config 變更時自動失效嗎？
- **觀點**：站在「不應該讓 hook 改寫 LLM 輸入」陣營，最有力的論點是「hidden mutation 破壞可預測性 + 難以 debug」；Codex 設計者如何回應？
- **後果**：若 12 個月後使用者大量寫 hook + skill，runtime overhead 累積會多嚴重？是否需要 lazy load / 並行優化？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — PreToolUse 的 `updatedInput` 能力過大：hook 可悄悄改寫 LLM 的 tool 輸入而使用者看不見 audit。最壞情況：admin 註冊的 hook 把所有 `rm` 命令改成 `rm -rf /`，使用者完全無感覺。雖然 sandbox 會接住，但若 `danger-full-access` 模式下完蛋。次風險：reserved field `updatedPermissions` 一旦未來開放，hook 可動態改 sandbox 規則，需嚴謹 audit
2. **什麼情況下會失敗？** — (a) hook 處理超過 timeout（預設無，但能設）→ Codex 等不到 stdout，hook 視為 fail；(b) hook 輸出不合 schema（多了未知欄位、漏了 required 欄位）→ `deny_unknown_fields` 直接 reject；(c) Skills 累積超過 2000 → 截斷且無錯誤；(d) Windows 環境沒有 `/etc/codex/`，admin scope skill 路徑失效
3. **有沒有更好的替代方案？** — (a) 用 [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE|Claude Code Hook]]：事件更精簡（7 種），無 reserved field，新手友善；(b) 用 MCP server 代替部分 hook 場景：MCP 可主動提供工具給 LLM，類似 Skills + Hook 混合體；(c) 寫 plugin（codex-plugin）：更深度整合但需 Rust 知識。**選 Codex hook 的時機**：你要嚴格 schema、admin override、事件粒度細到 PreCompact 與 SubagentStart

## References

### 原始碼路徑
- `codex-rs/hooks/src/types.rs` — 內部 Rust API (HookEvent / HookResult / HookPayload)
- `codex-rs/hooks/src/schema.rs` — 外部 command hook 完整 wire schema
- `codex-rs/hooks/src/declarations.rs` — Plugin hook 註冊
- `codex-rs/hooks/src/engine/dispatcher.rs` — Hook 派發邏輯（445 行）
- `codex-rs/hooks/src/engine/schema_loader.rs` — Schema 載入（138 行）
- `codex-rs/hooks/schema/generated/*.json` — 18 個自動產出的 JSON schema fixture
- `codex-rs/protocol/src/protocol.rs:1330-1453` — HookEventName / HookHandlerType / HookExecutionMode / HookScope / HookSource / HookTrustStatus / HookRunStatus / HookOutputEntryKind
- `codex-rs/core-skills/src/loader.rs` — Skills 載入流程與 6 條 root 路徑
- `codex-rs/core-skills/src/manager.rs` — SkillsManager 與 cache
- `codex-rs/core-skills/src/system.rs` — System skills install/uninstall
- `codex-rs/skills/src/lib.rs` — Embedded system skills（`include_dir!`）

### 外部文件
- [Codex GitHub Repo](https://github.com/openai/codex)
- [Codex Skills 官方文件](https://developers.openai.com/codex/skills)（stub，連到線上）
- [Codex Hooks 官方文件](https://developers.openai.com/codex/config-advanced)（stub）
