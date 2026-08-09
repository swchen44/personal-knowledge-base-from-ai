---
title: "Codex CLI vs Claude Code 深度對比 — 兩大終端機 AI Coding Agent 的架構與體驗"
date: 2026-05-20
category: CodeAnalysis
tags:
  - ai/coding-agent
  - comparison
  - codex
  - claude-code
  - terminal-tools
source: "https://github.com/openai/codex"
source_type: notes
author: "Personal Analysis"
status: notes
links:
  - "[[2026-05-20-CODEX-CLI-CODE-ANALYSIS]]"
  - "[[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]]"
  - "[[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-28-CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]]"
---

## 摘要（Summary）

本筆記以 2026-05-20 為快照，對兩大終端機 AI 編碼代理（terminal AI coding agent）— **OpenAI Codex CLI**（`openai/codex@1392a2a`）與 **Anthropic Claude Code**（最新穩定版）— 進行 10 個架構維度 + 5 個體驗維度的對比。事實基礎為 Codex 原始碼靜態分析（參見 [[2026-05-20-CODEX-CLI-CODE-ANALYSIS]]）與既有 KB 中關於 Claude Code 的多篇深度筆記。一句話結論：**Codex 是「Rust 編譯型 + 預先聲明安全 + 多 provider」路線，Claude Code 是「Node 動態型 + 對話式審批 + 深度擴充 (skill/subagent/plugin)」路線**。沒有絕對優劣，差異反映兩家對「agent 應該如何被使用」的設計哲學分歧。

## 架構分歧總覽圖（Architecture Divergence at a Glance）

> 兩家在「Agent 的 5 個關鍵子系統」上做出的選擇對照。

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       使用者 在終端機輸入 prompt                          │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                ┌────────────┴─────────────┐
                ▼                          ▼
   ┌──────────────────────┐    ┌──────────────────────┐
   │   OpenAI Codex CLI   │    │   Anthropic Claude   │
   │  (Rust + Node disp.) │    │   Code (TypeScript)  │
   └──────────┬───────────┘    └──────────┬───────────┘
              │                           │
   ┌──────────┴──────────┐    ┌───────────┴──────────┐
   │ 1. TUI: ratatui     │    │ 1. TUI: ink + React  │
   │ 2. Provider: 多家   │    │ 2. Provider: 主推    │
   │    抽象 (chatgpt /  │    │    Anthropic（Opus / │
   │    ollama / lmstudio│    │    Sonnet / Haiku）  │
   │    /aws-auth)       │    │                      │
   │ 3. Auth: Device     │    │ 3. Auth: API key /   │
   │    Code OAuth + PKCE│    │    Claude Pro/Max    │
   │ 4. Sandbox: ★★      │    │ 4. Sandbox: ★         │
   │    Starlark rules + │    │    settings allow/   │
   │    OS native (Seat- │    │    deny + 對話審批   │
   │    belt/bwrap/Win)  │    │                      │
   │ 5. 擴充: hooks      │    │ 5. 擴充: 5 種        │
   │    crate (admin     │    │    (hook/skill/      │
   │    enforced)        │    │    subagent/plugin/  │
   │                     │    │    output-style)     │
   └──────────┬──────────┘    └──────────┬───────────┘
              │                          │
              ▼                          ▼
   ┌──────────────────────┐    ┌──────────────────────┐
   │  pre-declare 安全：  │    │  runtime-decide 安全：│
   │  config-time 規則    │    │  對話即時審批        │
   │  + OS kernel 強制    │    │  + Bash allowlist    │
   │                      │    │                      │
   │  ➜ 適合批次/audit    │    │  ➜ 適合探索/互動     │
   └──────────────────────┘    └──────────────────────┘

  哲學分歧（單句總結）：
  ┌────────────────────────────────────────────────────────────────┐
  │  Codex：     「先聲明能做什麼，再讓 OS 強制執行」               │
  │  Claude Code：「邊做邊問，把 agency 留在對話裡」                │
  └────────────────────────────────────────────────────────────────┘
```

## TL;DR 對比矩陣（10 維度速覽）

| # | 維度 | OpenAI Codex CLI | Anthropic Claude Code |
|---|------|------------------|------------------------|
| 1 | **語言棧與發布** | Rust monorepo（103 crate）+ Node.js dispatcher；Cargo + Bazel 雙建構 | TypeScript on Node.js；npm 發布為 `@anthropic-ai/claude-code` |
| 2 | **TUI 渲染** | ratatui（Rust，編譯型，零 GC） | ink + React（Node.js，runtime 渲染） |
| 3 | **LLM Provider 抽象** | `model-provider` crate 統一介面；支援 ChatGPT API、Ollama、LM Studio、AWS Bedrock | Anthropic 自家為主；近期才補上 OpenAI 等第三方支援（Claude Agent SDK / 環境變數切換） |
| 4 | **Auth 機制** | Device Code OAuth + PKCE → `~/.codex/login.toml`；或 API key | API key（ANTHROPIC_API_KEY）/ OAuth 登入 Claude Pro/Max 帳號 |
| 5 | **Session 儲存** | `~/.codex/sessions/rollout-{ISO8601}-{UUID}.jsonl` + `history.jsonl`（全域）+ `session_index.jsonl` + SQLite sidecar；**主檔為 JSONL**；`--ephemeral` 可關閉 | `~/.claude/projects/{cwd-hash}/{session-id}.jsonl`，**也是 JSONL**，預設持久化 |
| 6 | **Tool / Function call 系統** | `tools` crate（4k LoC）+ `core-skills` + 內建 shell/file/web 工具 + dynamic_tool + mcp_tool | 內建 Bash/Read/Write/Edit/Glob/Grep/Task/WebFetch/WebSearch + Skill + Subagent + MCP tool |
| 7 | **Sandbox / 權限模型** | ★★ Starlark 規則引擎 `execpolicy` + **OS 原生沙盒**（macOS Seatbelt / Linux Bubblewrap+Landlock / Windows RestrictedToken）；3 mode：`read-only` / `workspace-write` / `danger-full-access` | ★ settings.json 中 allow/deny 規則 + 對話式 approval 提示；無 OS 級沙盒；採用 IPC 進程隔離 |
| 8 | **MCP 整合** | 原生 client + **可當 server**（`codex mcp-server`）；雙向 | client 為主，近期 Plugin marketplace 整合 MCP；可透過 MCP server 暴露但較不顯眼 |
| 9 | **Hook / 擴充機制** | `codex-hooks` crate（schemars JSON schema 自動產生）+ admin `allow_managed_hooks_only` 強制限定 | 多層擴充：**Hook / Skill / Subagent / Plugin / Output Style**；hook 事件清單豐富（PreToolUse/PostToolUse/UserPromptSubmit/Stop/SubagentStop/PreCompact/SessionStart…）|
| 10 | **配置檔** | `~/.codex/config.toml` (TOML) + `requirements.toml`（admin layer） | `~/.claude/settings.json` + `~/.claude/CLAUDE.md` + project `.claude/settings.json` + `CLAUDE.md` / `AGENTS.md`（多層 merge） |

---

## 逐維度深度對比

### 1️⃣ 語言棧與發布方式

**Codex** — 主體是 Rust monorepo（`codex-rs/`），含 103 個獨立 crate（execpolicy、hooks、tui、login、model-provider、sandboxing…）；外層用 Node.js dispatcher（`codex-cli/bin/codex.js`）做平台偵測 + spawn vendor 二進位。建構系統雙軌：Cargo（開發）+ Bazel（CI、發布、跨平台一致性）。發布管道：npm（透過 platform-specific optional dependencies `@openai/codex-{platform}-{arch}`）+ Homebrew Cask + GitHub Releases。

**Claude Code** — 主體是 TypeScript on Node.js，發布為單一 npm 包 `@anthropic-ai/claude-code`，安裝後直接執行（無需平台 wrapper）。

**影響**：
- Codex 啟動更快（單一靜態二進位，無 Node runtime warmup）；記憶體與 disk footprint 更小
- Codex 跨平台沙盒實作真正各自做（不靠 Node 模擬）；Claude Code 主要靠 Node 的 child_process 與 permission 對話框
- Claude Code 改一行代碼推一個 patch 比較容易（純 TS 熱迴圈）；Codex 涉及 Bazel lockfile 同步較重
- Claude Code 的 plugin 作者寫 TypeScript / Markdown 即可貢獻；Codex 的擴充門檻偏 Rust（hooks 與 skills 雖然可用設定檔，但深度擴充仍需 Rust）

> [!tip] 設計取向
> 「**Rust + Bazel monorepo**」對應「準備長期維護、跨平台一致性最重要」；「**npm 上單一 TS 包**」對應「快速迭代、社群貢獻友善」。

### 2️⃣ TUI 渲染

**Codex** — `codex-rs/tui/` 使用 `ratatui`（Rust）。AGENTS.md 強制 Stylize trait 慣例（`.bold()`, `.dim()`, `.red()`），模組 size limit 500 LoC。
**Claude Code** — 使用 `ink`（React for CLI），元件化結構，React-style state management。

**影響**：
- Codex TUI 編譯成原生機器碼，零 reconciliation cost、零 GC pause；對極長 session、頻繁更新場景有效能優勢
- Claude Code TUI 由 React 思維驅動，貢獻者基數大（任何熟 React 的人都能擴元件）；但對 100Hz 級高頻更新有 overhead
- 兩者都支援 mouse、color、unicode；但 Codex 的 Stylize chain 寫法在程式碼可讀性上更緊湊

### 3️⃣ LLM Provider 抽象

**Codex** — `model-provider` + `model-provider-info` + `models-manager` 三個 crate 處理 LLM 抽象。專屬 crate 有 `chatgpt`、`ollama`、`lmstudio`、`aws-auth`（為 Bedrock 鋪路）。預設透過 `~/.codex/config.toml` 切換 provider 與 model。

**Claude Code** — 主要綁定 Anthropic API（Sonnet / Opus / Haiku）。透過環境變數（`ANTHROPIC_BASE_URL`、`ANTHROPIC_MODEL`）可重定向到 LiteLLM、自架 proxy、其他 provider，但設計重心仍是 Anthropic 自家模型。

**影響**：
- Codex 對「多 model 共存、按任務切換」更原生；可在同一 config 內混用 GPT-5.5、o3、Codex-1
- Claude Code 對「在 Anthropic 內換版本」（Opus ↔ Sonnet ↔ Haiku）非常順暢，但要跨家換 provider 需要靠社群橋接（LiteLLM、claude-code-router 等）
- Codex 的 Ollama / LM Studio 一級支援，本地模型實驗門檻低

### 4️⃣ Auth 機制

**Codex** — `codex-login` crate 完整實作 OAuth Device Code Flow + PKCE：
1. CLI 生成 `code_verifier` + `code_challenge`
2. 向 OAuth server 註冊取得 `device_code` + `user_code`
3. CLI 開 localhost callback server，顯示 `user_code` 與 verify URL
4. 使用者在瀏覽器登入 chatgpt.com
5. callback 收到 token，寫入 `~/.codex/login.toml`

也支援 API key（透過 `OPENAI_API_KEY` 或 `~/.codex/config.toml`）。

**Claude Code** — 主要兩條：
1. `ANTHROPIC_API_KEY` 環境變數（API 直連）
2. `claude login` OAuth 流程（綁定 Claude Pro / Max 訂閱）

兩家都支援企業 SSO（OIDC）但路徑不同。

**影響**：
- Codex 的 ChatGPT 登入流程更「消費者友善」（已有 Plus 帳號就免設 API key）
- Claude Code 對 API key 場景設計更純（適合自動化、CI）
- Codex device code flow 完整，可在沒有瀏覽器的環境（SSH server）登入（用手機掃 URL 完成授權）

### 5️⃣ Session / 對話歷史儲存

> [!important] **兩家都用 JSONL** — 這是先前版本筆記中遺漏的事實。差別在「平鋪 vs 嵌套目錄」與「主檔之外的 sidecar」。

**Codex** — 四層儲存體系（由 `codex-rs/rollout/`、`message-history/`、`thread-store/`、`state-db` 多個 crate 協作）：

| # | 路徑 | 格式 | 用途 |
|---|------|------|------|
| 1 | `~/.codex/sessions/rollout-{ISO8601}-{UUID}.jsonl` | **JSONL** | 主 session log；每行一個 `RolloutItem`（SessionMeta / TurnContext / ResponseItem / EventMsg / Compacted）|
| 2 | `~/.codex/history.jsonl` | JSONL `{session_id, ts, text}` | 全域訊息歷史，跨 session 累積 |
| 3 | `~/.codex/session_index.jsonl` | JSONL `{id, thread_name, updated_at}` | Session 索引（append-only） |
| 4 | SQLite state DB | SQLite | metadata 與 metrics 的 sidecar（**不存對話內容**） |

來源證據：`rollout/src/recorder.rs` 直接寫明「Rollouts are recorded as JSONL and can be inspected with `jq` / `fx`」。
持久化模式有 `Limited`（預設）/ `Extended`（後者會把 `ExecCommandEnd.aggregated_output` 截到 10K bytes，並清空 stdout/stderr 避免爆炸）。
`codex exec --ephemeral` 可關閉持久化。封存路徑：`~/.codex/sessions/archived_sessions/`。

**Claude Code** — `~/.claude/projects/{cwd-hash-encoded}/{session-id}.jsonl` 儲存每次對話。一個 JSONL 檔對應一個 session，包含完整訊息、tool 呼叫、權限決定、token 用量。`/resume` 可恢復；`/clear` 可清空當前 session。

**對比小表**：

| 維度 | Codex | Claude Code |
|------|-------|-------------|
| 主檔格式 | JSONL | JSONL |
| 目錄結構 | 平鋪（檔名含 ISO8601 + UUID） | 嵌套（`{cwd-hash}/{session-id}.jsonl`） |
| 一檔範圍 | 一個 session 一檔 | 一個 session 一檔 |
| 全域歷史 | `~/.codex/history.jsonl` 跨 session 累積 | 無對應檔案（每個 session 獨立） |
| 索引 | `session_index.jsonl` + SQLite sidecar | 靠目錄 + 檔名（cwd-hash 自動分組） |
| Ephemeral | `codex exec --ephemeral` 一鍵關閉 | 無 ephemeral flag；需手動刪檔或 `/clear` |
| Resume | `RolloutRecorderParams::Resume { path }` | `/resume` slash command |
| 持久化篩選 | `EventPersistenceMode::{Limited, Extended}` | 預設全寫；by-event truncation 較少 |

**影響**：
- 兩者主檔皆為 JSONL，**外部分析工具對兩家都友善**（可 stream parse）；參見 [[2026-04-10-CLAUDE-SESSION-ANALYZER-CODE-ANALYSIS]]
- Codex 多了「跨 session 全域 history.jsonl + SQLite 索引 sidecar」，適合長期累積 + 快速 thread 列表查詢
- Claude Code 用目錄結構（cwd-hash）天然分組，但跨 session 累積分析需要自己拼接
- 用 `--ephemeral` 是 Codex 的 privacy advantage（一鍵不落地）；Claude Code 沒有對應 flag

### 6️⃣ Tool / Function call 系統

**Codex** — `codex-rs/tools/` (4k LoC) 是專屬 crate，含：
- `tool_executor` / `tool_call` / `tool_output` — 統一執行框架
- `dynamic_tool` — runtime 動態定義工具
- `mcp_tool` — MCP 工具的 host 端 adapter
- `responses_api` — 對應 OpenAI Responses API 的 tool spec 轉換
- `code_mode` — 特殊 code editing mode
- `json_schema` / `tool_spec` — schema sanitization

外加 `core-skills/` (8 個檔案) 處理 skill 注入與 prompt 渲染。

**Claude Code** — 內建工具：Bash, Read, Write, Edit, Glob, Grep, Task, WebFetch, WebSearch, TodoWrite, NotebookEdit。透過 Skill / Subagent / Plugin 擴充：
- **Skill**：Markdown 描述 + 可選 scripts；模型按 description 自動選用
- **Subagent**：用 `Agent` tool 派發特定能力的子 agent（程式碼審查、研究、debug）
- **MCP tool**：透過 MCP server 接入任意工具

**影響**：
- Codex 的「工具就是 crate 的一級公民」設計適合複雜的 host adapter（schema 轉換、code mode）
- Claude Code 的 Skill 系統低門檻（寫 Markdown 即可）、Subagent 系統強（可避免污染主對話、可平行多工）
- 兩者 MCP 都支援，差別是 Codex 把 MCP 當「主要整合面」，Claude Code 把 MCP 當「擴充面之一」

### 7️⃣ Sandbox / 權限模型（最大架構差異 ★）

**Codex** — **雙層 + OS 原生沙盒**：

第一層：**execpolicy**（Starlark 規則引擎）
```starlark
prefix_rule(
    pattern = ["git", "status"],
    decision = "allow",
    justification = "git status is read-only",
    match = ["git status"],
)
prefix_rule(
    pattern = ["rm", "-rf", "/"],
    decision = "forbidden",
    justification = "Use targeted rm instead",
)
```

第二層：**OS 原生沙盒**
- macOS：`sandboxing/src/seatbelt.rs` + `.sbpl` policy → sandbox-exec
- Linux：`sandboxing/src/bwrap.rs`（系統 bubblewrap 優先，bundled 為 fallback）+ `landlock.rs`（legacy） + `PR_SET_NO_NEW_PRIVS` + seccomp 網路濾過
- Windows：`windows-sandbox-rs` crate（RestrictedToken）

3 mode：`read-only`（預設）、`workspace-write`（cwd + `~/.codex/memories` 可寫，仍封網路）、`danger-full-access`。

**Claude Code** — **單層、對話式 approval**：
- `~/.claude/settings.json` 中可預設 `permissions.allow / deny / ask` 三種規則（針對 Bash 命令 pattern、Tool 名稱）
- 沒有 OS 級沙盒；依靠 Node child_process 隔離
- 對未列入 allow 的工具呼叫，每次彈權限對話框
- 有 `--dangerously-skip-permissions` flag 一次性繞過

**影響（最大架構差異）**：

| 面向 | Codex | Claude Code |
|------|-------|-------------|
| 安全強度 | OS 級隔離（kernel 強制） | 進程級隔離（runtime 強制） |
| 規則維護成本 | 高（需學 Starlark） | 中（settings.json glob） |
| 即時調整彈性 | 低（改 config 重啟） | 高（執行中可在對話內授權） |
| 適合場景 | 批次自動化、長時間無人值守 | 探索式開發、互動 debugging |
| 失敗模式 | 規則過鬆→沙盒兜底；規則過嚴→agent 卡死 | 對話審批疲勞、誤按 yes |

> [!warning] 哲學差異
> Codex 把「能做什麼」決策**前推到 config-time**；Claude Code 把同一決策**留在 runtime**。前者偏 declarative + audit，後者偏 interactive + flexible。

### 8️⃣ MCP 整合

**Codex** — `codex-mcp` crate 內含：
- `connection_manager`：管理多個 MCP server 連線
- `rmcp_client`：Rust MCP client 實作
- `server`：把 Codex 自己暴露為 MCP server（`codex mcp-server`）
- `codex_apps` / `elicitation`：高階 app 整合

`codex mcp` 子命令可 add/list/get/remove MCP server config。

**Claude Code** — MCP client 支援透過 `~/.claude/mcp-config.json` 或 `claude mcp add` 設定；Plugin marketplace 整合 MCP servers；理論上可透過 wrapper 把 Claude Code 暴露為 MCP server，但官方非預設能力。

**影響**：
- Codex 的「雙向 MCP」讓 agent 可以串接（IDE 或其他 agent 把 Codex 當 tool 用）
- Claude Code 的 MCP client 體驗豐富（marketplace、auto-discovery），但暴露為 server 較少官方文檔

### 9️⃣ Hook / 擴充機制

**Codex** — `codex-hooks` crate：
- 902 行的 `schema.rs` 用 `schemars` 自動產生 JSON schema（供外部 hooks 引用）
- 配置驅動：在 `~/.codex/config.toml` 中宣告事件 hook
- 多層配置：user / project / session / requirements / managed
- `requirements.toml` 中 `allow_managed_hooks_only = true` 可禁用使用者層 hooks
- 依賴 `codex-plugin` crate（plugin 系統獨立存在）

**Claude Code** — 擴充面非常豐富，是其最大差異化：
- **Hook**：7+ 個事件點（PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, PreCompact, SessionStart, Notification…）；可阻擋、可注入 context；參見 [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]]
- **Skill**：Markdown + frontmatter 描述能力；自動 trigger 機制
- **Subagent**：可派發專屬 agent（不污染主對話）
- **Plugin**：marketplace 機制（個人/組織安裝）
- **Output Style**：用 Markdown 切換輸出風格
- **Slash Command**：自訂 `/command`

**影響**：
- Codex hook 系統「乾淨且企業友善」（admin 強制覆蓋；自動產 schema）；但擴充層次淺
- Claude Code 擴充層次深（5 種擴充面）、社群活躍（plugin marketplace 已有數千 plugin）；但配置複雜度高
- Codex 更適合「企業集中管理 hook 政策」；Claude Code 更適合「個人深度客製」

### 🔟 配置檔

**Codex** — 純 TOML：
```toml
# ~/.codex/config.toml
sandbox_mode = "workspace-write"
model = "gpt-5.5-codex"
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
```
+ `~/.codex/requirements.toml`（admin 強制設定，含 `allow_managed_hooks_only`）

**Claude Code** — JSON + Markdown 混合：
- `~/.claude/settings.json`（全局設定、permissions、env、hooks）
- `~/.claude/CLAUDE.md`（全局指令、記憶）
- 專案 `.claude/settings.json`（專案層 override）
- 專案 `CLAUDE.md` / `AGENTS.md`（專案層指令）
- `~/.claude/mcp-config.json`（MCP servers）

**影響**：
- Codex TOML 機器可讀性好（structured），但 Markdown-style「人類指令」需另寫成 `AGENTS.md`
- Claude Code 把「設定」與「指令」分為 JSON 與 Markdown 兩種檔案，分工清楚；但檔案數量多、merge 規則複雜
- Codex 用 `requirements.toml` 提供「不可被使用者覆蓋」的 admin layer；Claude Code 透過 enterprise managed settings 也有類似機制

---

## 使用體驗對比（40% 篇幅）

### 訂閱與計費

| 項目 | Codex | Claude Code |
|------|-------|-------------|
| 訂閱整合 | ChatGPT Plus / Pro / Business / Edu / Enterprise 直接登入即用 | Claude Pro / Max（直登）或 Anthropic API key |
| API 計費 | OpenAI API token-based | Anthropic API token-based |
| 訂閱定額包含 token | ChatGPT 各方案有不同上限（每月配額） | Claude Pro / Max 有不同上限 |
| 第三方 model | 開源 model 可走 Ollama / LM Studio 免費；商業 model 需自備 API key | 透過環境變數重定向到 LiteLLM / 其他 proxy |

### 模型選擇彈性

- **Codex**：原生支援 GPT-5.x 家族（GPT-5.5、GPT-5.4、GPT-5.3-Codex 等多版本）、o3 系列、Codex-1 等專為 coding 微調的模型。可在 config 內定義多 profile 對應不同任務（如 plan 用 o3、code 用 codex-1）
- **Claude Code**：原生 Opus 4.7、Sonnet 4.6、Haiku 4.5；可用 `/model` 切換；plan mode 預設用較強模型，coding 用較快模型

### Token 使用

- **Codex** 已知 issue [#19996](https://github.com/openai/codex/issues/19996)：反覆啟動會觸發大量 token 預載；session restart 成本高
- **Claude Code**：擁有完整 token cost calculation pipeline，提供 `/cost` 指令查詢；參見 [[2026-04-28-CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]]。但長 context（>200K token）也會吃緩衝

### 互動順暢度

- **Codex**：Rust 編譯啟動極快；ratatui 渲染流暢無 jitter
- **Claude Code**：Node 啟動稍慢（首次載入 200-500ms）；React/ink 在高頻更新時偶有閃爍；但 UI 元件豐富

### 工作流支援

| 工作流 | Codex | Claude Code |
|--------|-------|-------------|
| Plan mode | `codex` 內建 plan 概念，配合 sandbox 預設 read-only 可規劃不誤改 | 顯式 `Plan mode` + `ExitPlanMode` tool，整段流程結構化 |
| Worktree 隔離 | 透過 `git worktree` 手動 | 內建 worktree 支援（plan mode 提示 + isolation 建議） |
| Subagent | 無原生概念（透過 MCP server chain） | Subagent tool 內建（research / debug / code-review 等） |
| 非互動 | `codex exec` (含 `--ephemeral`) | `claude -p` (one-shot) |
| 自動化 / CI | App Server / Daemon 可 long-running 接 IDE 與 CI | Hook + session JSON 解析 + GitHub Action 整合 |
| 雲端執行 | Cloud Tasks 送 chatgpt.com/codex 雲端跑（opt-in） | 無雲端版本（皆 local） |

---

## 何時選哪個？（Decision Matrix）

| 你的情境 | 推薦 | 為什麼 |
|---------|------|--------|
| 已有 ChatGPT Plus/Pro 訂閱，想試 AI agent | **Codex** | Sign in with ChatGPT 免設 API key，配額已含 |
| 已有 Claude Pro / Max 訂閱 | **Claude Code** | 同理 |
| 企業環境，需要 OS 級隔離 + admin 強制規則 | **Codex** | execpolicy + 三平台原生 sandbox + `requirements.toml` admin layer |
| 個人深度客製，喜歡寫 skill / hook / plugin | **Claude Code** | 5 種擴充面（hook/skill/subagent/plugin/output-style），plugin marketplace |
| 跨多家 LLM provider（本地 + 商業 + 微調） | **Codex** | `model-provider` 抽象一級公民；Ollama/LM Studio 原生 |
| 探索式開發，要邊改邊看 | **Claude Code** | 對話式 approval 比預先聲明規則更輕量 |
| 批次自動化、CI 跑 agent | **Codex** | execpolicy 可預先 audit；exec mode + ephemeral；sandbox 強 |
| 想串接 IDE（VS Code / Cursor / Windsurf） | **皆可** | Codex 有 IDE extension；Claude Code 有 VS Code extension 與 JetBrains |
| 對 React 熟、想貢獻 patches | **Claude Code** | TypeScript codebase 上手快 |
| 對 Rust 熟、想貢獻深度功能 | **Codex** | 103 crate 提供清楚的擴充點 |
| Token 預算極緊，重視成本透明 | **Claude Code** | `/cost` 指令 + token pipeline 文件豐富 |
| Agent chain（讓多個 agent 互相呼叫） | **Codex** | 雙向 MCP（可當 server） |

---

## 我的心得（My Takeaways）

1. **兩家的「安全模型」對應不同的工作型態** — Codex 的 pre-declare 規則 + OS 沙盒適合「批次、無人值守、企業審計」；Claude Code 的 runtime approval 適合「探索、互動、個人開發」。同時用兩家可以取長補短。
2. **擴充哲學是 ROI 而非優劣** — Codex 一個 hook crate vs Claude Code 五種擴充面。前者「乾淨少表面」、後者「豐富多入口」。需要長期維護的工程組織可能偏好前者，需要快速嘗試新工作流的個人偏好後者。
3. **語言棧選擇深刻影響 contributor 群** — Rust monorepo 吸引系統工程師，TypeScript 吸引 web/全端工程師。兩個社群的 plugin / skill 文化會因此差異很大。
4. **Sandbox 是被低估的差異化** — 多數對比文只談 token、UX、價格，但對企業使用者來說，OS 級隔離是 deal-breaker 級的差異。Claude Code 未來若要正式進企業，這塊需要補上。
5. **雙向 MCP 是 agent 平台未來的方向** — Codex 的 `mcp-server` 讓自己被別的 agent 呼叫，這打開了 agent chain 的可能。Claude Code 若不跟進，未來在「agent 之間 chain」上會吃虧。

## 待補充（Open Questions）

- **Q1：實際 benchmark 數據在哪？** 啟動時間、TUI 渲染 fps、相同任務的 token 消耗對比，目前沒有第三方公開 benchmark。（搜尋：`codex vs claude-code benchmark 2026`）
- **Q2：兩家對 long context（>200K token）的處理差異？** Claude Code 有 PreCompact hook 與 auto-compaction；Codex 如何處理？（搜尋：`codex context compaction strategy`）
- **Q3：在 enterprise 環境中，兩家的 audit / compliance 故事完整度？** SOC 2、HIPAA、FedRAMP、Data residency 各家狀態？（搜尋：`codex claude-code enterprise compliance SOC2`）
- **Q4：兩家對 multi-modal（image input、screenshot）的支援差異？** Claude Code 可 paste 圖片；Codex 透過 GPT-5.x 視覺模型支援程度為何？
- **Q5：兩家對「同時跑多個 agent session」的支援差異？** Codex App Server / Daemon 模型 vs Claude Code 多 terminal 平行；資源衝突如何處理？
- **Q6：兩家如何處理「執行了 30 分鐘的長任務」？** Codex Cloud Tasks 可丟到雲端跑；Claude Code 純 local，是否會 time out？

## 相關連結（Related）
- [[2026-05-22-SKILLOPT-SELF-EVOLVING-AGENT-SKILLS-CODE-ANALYSIS]] — SkillOpt：把 Agent 技能當神經網路訓練的文字空間優化器（驗證閘門/minibatch 反思/學習率裁剪）

- [[2026-05-20-CODEX-CLI-CODE-ANALYSIS]] — 本筆記中 Codex 端的所有事實依據，含原始碼路徑與設計細節
- [[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]] — gstack 將 Codex 與 Claude Code 列為 8 個 agent 之一進行整合，可看跨工具 plugin 設計
- [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]] — Claude Code Hook API 原始碼分析，可對照本文「Hook / 擴充機制」維度
- [[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]] — Claude Code OTel 設計；Codex 也有 `otel` crate，可互補閱讀
- [[2026-04-28-CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]] — Claude Code token cost 計算，對照本文「Token 使用」段
- [[2026-04-17-CLAUDE-CODE-FEEDBACK-FRUSTRATION-DETECTION-EVENTMETADATA-ARCHITECTURE]] — Claude Code 的 feedback 架構；Codex 也有 `feedback` crate
- [[2026-04-10-CLAUDE-SESSION-ANALYZER-CODE-ANALYSIS]] — Claude Code session JSONL 解析；對照本文「Session 儲存」維度
- [[2026-03-25-ENGINEERS-FUTURE-MULTI-AGENT-ERA-STEVE-YEGGE]] — 多 agent 時代的工程師角色；本文「雙向 MCP」呼應此趨勢
- [[2026-05-20-CODEX-HOOK-AND-SKILLS-PARAMETERS-DEEP-DIVE]] — Codex Hook 系統與 Skills 搜尋路徑的原始碼層級規格；對應本文「Hook / 擴充機制」與「Skills」維度的完整事實細節
- [[2026-08-07-OPEN-CODE-REVIEW-ALIBABA-AI-CODE-REVIEW-CLI-CODE-ANALYSIS]] — OCR 是「專用化 harness 打通用 agent」的實例:同底模下 F1 27% vs 10%,補完通用 agent 陣營之外的第三條路線

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 必記：(1) Codex = Rust + Node dispatcher；(2) Claude Code = TypeScript on Node；(3) 最大差異是 sandbox（Codex 用 OS 原生 + Starlark 規則，Claude Code 用對話審批 + Bash allowlist）；(4) Codex 支援雙向 MCP；(5) Claude Code 擴充面有 5 種（hook/skill/subagent/plugin/output-style） |
| **理解（半被動）** | 解釋概念的含義及關聯 | 用自己的話：兩家的差異不是「誰先進」，是「對 agent 該如何被使用」假設不同。Codex 假設「需要可預測、可審計、批次跑」；Claude Code 假設「需要靈活、可探索、互動式」。架構選擇從這個假設衍生 |
| **分析（主動）** | 檢驗論點、找出假設 | 關鍵假設：(1) 「Rust 必然更快」— 但對 LLM 等候時間佔主要延遲的場景，啟動 200ms 差異感受不大；(2) 「OS 沙盒一定更安全」— 但需要使用者環境配合（WSL1 無法用）；(3) 「Claude Code 擴充更豐富」— 但對企業集中管理是負擔而非優勢 |
| **應用（主動）** | 套用情境 | 立即可做：(A) 評估自己的工作型態（探索/批次）決定選哪個或同時用；(B) 把 Codex 的 execpolicy 規則撰寫法應用到自己的 CLI 工具 access control；(C) 把 Claude Code 的多層擴充面分類學運用到自己的工具設計上 |
| **評估（主動）** | 判斷優劣、權衡 | 評估：兩家在企業場景的差距正在縮小（Claude Code 推 enterprise managed settings + plugin marketplace 集中管理）；在個人場景的差距也在縮小（Codex 推 IDE extension + skill）。預測 12 個月內兩家會更像，但「安全模型」分歧難消（pre-declare vs runtime 是哲學選擇） |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Claude Code 擴充面有 5 種」這個分類是否準確？Output Style 真的算獨立面向，還是 Hook 的子類？
- **假設**：兩家都假設「使用者願意維護一個 config 檔」。對完全不寫 config 的使用者，誰的預設體驗較好？
- **證據**：「Codex 啟動極快」目前只有主觀印象與 InfoQ 報導；有沒有人做過嚴謹 cold start 比較？
- **觀點**：Claude Code 設計者若看到 Codex 的 execpolicy 設計，會如何回應？「對話審批」會被視為過時還是被視為更尊重 user agency？
- **後果**：若 5 年後兩家完全收斂，使用者選擇基準會變什麼？品牌、模型品質、生態系大小、價格？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 比較兩個快速演化的工具有「時效性風險」。本文以 2026-05-20 為快照，但 Codex CHANGELOG 顯示每日節奏發版，Claude Code 也類似。6 個月後本文中的 50% 細節可能過時。最壞情況：讀者依本文選錯工具，半年後發現選的工具早已補上「不足之處」。
2. **什麼情況下會失敗？** — (a) 在「兩家都不適合」的場景（例如：你需要的是 Cursor / Windsurf 的 IDE 整合，不是 CLI）；(b) 預算極緊只能選一家但需求橫跨兩家強項；(c) 你的工作流長期需求未定，無法判斷自己更接近 「批次型」還是「探索型」
3. **有沒有更好的替代方案？** — (a) **同時用兩家**：Codex 跑批次 / 自動化，Claude Code 互動 debug；用 gstack 之類的 host integration 統一配置（見 [[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]]）。(b) **等 6 個月再決定**：兩家正在快速收斂。(c) **看具體模型品質**：對某類任務（複雜重構、debug long traces）某家明顯較強，模型品質可能比工具差異更重要。

## References

### 官方來源
- [openai/codex GitHub README](https://github.com/openai/codex)
- [Introducing Codex | OpenAI (2025-04-16)](https://openai.com/index/introducing-codex/)
- [Introducing upgrades to Codex | OpenAI](https://openai.com/index/introducing-upgrades-to-codex/)
- [Codex Changelog](https://developers.openai.com/codex/changelog)
- [Claude Code 官方產品頁](https://www.anthropic.com/product/claude-code)
- [Claude Code Documentation](https://code.claude.com/docs/en/overview)
- [How Anthropic teams use Claude Code (PDF)](https://www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf)

### 第三方對比
- [Claude Code vs OpenAI Codex CLI Comparison — Zen van Riel](https://zenvanriel.com/ai-engineer-blog/claude-code-vs-openai-codex-cli-comparison/)
- [Codex vs Claude Code — DataCamp](https://www.datacamp.com/blog/codex-vs-claude-code)
- [Claude Code vs OpenAI Codex 2026 — Northflank](https://northflank.com/blog/claude-code-vs-openai-codex)
- [Claude Code vs OpenAI Codex: Same App in Both — Composio (2026-05)](https://composio.dev/content/claude-code-vs-openai-codex)
- [Claude Code vs Codex CLI 2026 — NxCode](https://www.nxcode.io/resources/news/claude-code-vs-codex-cli-terminal-coding-comparison-2026)

### 架構深析
- [The codex-rs Architecture — Daniel Vaughan (2026-03-28)](https://codex.danielvaughan.com/2026/03/28/codex-rs-rust-rewrite-architecture/)
- [Another Rust Rewrite: Codex CLI Goes Native — InfoQ (2025-06)](https://www.infoq.com/news/2025/06/codex-cli-rust-native-rewrite/)
- [Codex CLI is Going Native · Discussion #1174](https://github.com/openai/codex/discussions/1174)
- [Unlocking the Codex harness: how we built the App Server — OpenAI](https://openai.com/index/unlocking-the-codex-harness/)

### 使用體驗
- [How to Use GPT-5.5 in Codex for Agentic Tasks — MindStudio (2026)](https://www.mindstudio.ai/blog/how-to-use-gpt-5-5-codex-agentic-tasks)
- [How to Choose Between GPT-5.5 / 5.4 / 5.3-Codex — knightli (2026-05)](https://www.knightli.com/en/2026/05/10/gpt-5-5-vs-gpt-5-4-vs-gpt-5-3-codex/)
- [Codex token usage issue #19996](https://github.com/openai/codex/issues/19996)
