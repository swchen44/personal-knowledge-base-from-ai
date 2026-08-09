---
title: "RTK Rust Token Killer — Log 壓縮與 AI Agent 輸出治理架構深度分析"
date: 2026-05-23
category: CodeAnalysis
tags:
  - code-analysis
  - rust
  - ai/agent
  - devtools/cli
  - observability/logging
source: "https://github.com/rtk-ai/rtk"
source_type: code
author: "rtk-ai"
status: notes
links:
  - "[[2026-04-28-CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]]"
  - "[[2026-04-18-CLAUDE-CODE-TOKEN-QUOTA-THREE-TRAPS-AND-FIXES]]"
  - "[[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]]"
  - "[[2026-05-20-CODEX-HOOK-AND-SKILLS-PARAMETERS-DEEP-DIVE]]"
github_stars: "43.8k+（GitHub 搜尋快照，2026-05-24）"
github_language: "Rust"
local_source: "/Users/swchen.tw/git/rtk_plan/rtk"
local_commit: "805caf7d069e93370a316682b36aad59d562de2e"
local_version: "0.40.0"
---

## 摘要（Summary）

RTK（Rust Token Killer）是一個 Rust 單一 binary 的 CLI proxy，目標是在命令輸出進入 LLM 上下文視窗（Context Window）前先做語意壓縮。它不是單純把 stdout 截短，而是把「不同命令的輸出」轉成「AI agent 下一步決策需要的訊號」：測試只保留 failure，Git 只保留狀態摘要，log 先做 severity 分桶與重複歸併，長輸出失敗時再用 tee 保留完整原文路徑。

本筆記以本機 checkout `/Users/swchen.tw/git/rtk_plan/rtk` 為主，對應 `rtk-ai/rtk` commit `805caf7`，`Cargo.toml` 版本為 `0.40.0`。公開 GitHub 搜尋快照顯示 repo 約 43.8k stars、最新 release 索引仍停在 v0.39.0，因此版本欄位以本機原始碼為準。

## Why — 為什麼存在？

- **核心動機**：AI coding agent 最大浪費不是「模型不會寫 code」，而是每次工具輸出都把大量低價值 log、progress bar、重複訊息、成功路徑 boilerplate 塞進上下文。
- **取代/改善什麼**：取代「叫模型自己在 raw output 裡找重點」這種高 token、高錯誤率做法；把結構化壓縮前移到工具層。
- **目標用戶**：長時間使用 Claude Code、Codex、Cursor、Gemini CLI、OpenCode 等 agent 的開發者，尤其是經常跑 test/build/lint/git/log 的工程流程。

> [!important] 核心精神（Core Principle）
> RTK 的精神是 **「先分類，再壓縮；先保證可恢復，再節省 token」**。它不追求漂亮摘要，而是追求 agent 能立刻採取下一步行動的最小訊號。

## What — 是什麼？

- **主要功能**：
  - CLI proxy：`rtk git status`、`rtk cargo test`、`rtk pytest`、`rtk log file.log` 等。
  - Hook rewrite：`git status` 可在 agent hook 中被改寫為 `rtk git status`。
  - Declarative TOML filters：用 `.rtk/filters.toml`、`~/.config/rtk/filters.toml`、內建 `src/filters/*.toml` 擴充 line-based 壓縮。
  - Tracking analytics：記錄 raw tokens、filtered tokens、saved tokens、執行時間。
  - Tee recovery：失敗時將完整 raw output 存到本地檔案，只在摘要旁給 `[full output: ...]`。
- **不做什麼（Non-goals）**：
  - 不把所有命令都交給 LLM 摘要。
  - 不保證每個工具都懂語意；未知命令會 passthrough 或用 TOML line filter。
  - 不取代 OpenTelemetry（OTel）或正式 log pipeline；RTK 是 agent context 前的壓縮層。
- **技術棧（Tech Stack）**：Rust 2021、`clap` CLI、`regex`、`serde/toml/json`、`rusqlite` tracking DB、`dirs` platform path、agent hook shell/TypeScript integration。

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌──────────────────────────────────────────────────────────────┐
│                    AI Agent / Human CLI                       │
│  Bash tool / terminal / plugin API / rules file instruction   │
└───────────────────────────┬──────────────────────────────────┘
                            │ raw command
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                 Hook Rewrite / rtk rewrite                    │
│  discover::registry + lexer + permission verdict              │
│  "git status" ───────────────► "rtk git status"               │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                         src/main.rs                           │
│  Clap parse → Commands enum → dedicated Rust module            │
│             ↘ parse fail → TOML filter lookup → passthrough    │
└───────────────────────────┬──────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
┌────────────────┐  ┌────────────────┐  ┌──────────────────────┐
│ Dedicated cmds │  │ TOML pipeline   │  │ Passthrough / Proxy   │
│ git/test/lint  │  │ regex line DSL  │  │ raw execution         │
└───────┬────────┘  └───────┬────────┘  └──────────┬───────────┘
        │                   │                      │
        ▼                   ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│ core::runner / core::stream / core::tee / core::tracking      │
│ capture/stream → filter → print compact → save raw if needed  │
└──────────────────────────────────────────────────────────────┘
```

### 執行流程圖（Execution Flowchart）

```
Start
  │
  ▼
[Agent emits shell command]
  │
  ├─ Hook available? ── no ──► [User must call rtk explicitly / rules guidance]
  │
  yes
  │
  ▼
[rtk rewrite checks rules + permissions]
  │
  ├─ no RTK equivalent ──► [Run original command]
  │
  ├─ deny matched ──────► [Let agent permission system deny]
  │
  └─ rewrite matched
        │
        ▼
   [rtk command runs child process]
        │
        ├─ dedicated command module ─► [semantic formatter]
        ├─ TOML filter matched ──────► [8-stage line pipeline]
        └─ no match ─────────────────► [passthrough]
        │
        ▼
   [Print compact output]
        │
        ├─ failed + large raw? ─► [tee full output + path hint]
        │
        ▼
   [Track token savings in SQLite]
        │
        ▼
      End
```

### 時序圖（Sequence Diagram）

```
Agent        Hook         RTK binary        Child Tool       Tracking/Tee
  │            │              │                 │                │
  │ git status │              │                 │                │
  │───────────►│              │                 │                │
  │            │ rtk rewrite  │                 │                │
  │            │─────────────►│                 │                │
  │            │ rtk git ...  │                 │                │
  │◄───────────│              │                 │                │
  │ execute rewritten command │                 │                │
  │──────────────────────────►│                 │                │
  │            │              │ git status      │                │
  │            │              │────────────────►│                │
  │            │              │ raw stdout      │                │
  │            │              │◄────────────────│                │
  │ compact output            │                 │ track savings  │
  │◄──────────────────────────│────────────────────────────────►│
  │            │              │ failed? tee raw output ─────────►│
```

### 關鍵設計決策（Key Design Decisions）

1. **Dedicated Rust modules 優先**：高價值、高語意工具（Git、test、lint、build）用 Rust 模組處理，因為只靠 regex 無法知道哪些 failure block 最重要。
2. **TOML filter 作為長尾擴充**：對 predictable line-by-line output，用 declarative filter 即可，不必每個工具都寫 Rust。
3. **Fail-safe passthrough**：filter 失敗或命令不支援時，保留原命令行為與 exit code，避免為省 token 破壞 build/test 的真實結果。
4. **Tee recovery**：短輸出直接呈現；長失敗輸出以檔案保留。這避免「壓縮過頭」導致 agent 無法追查。
5. **Tracking 不是主流程依賴**：tracking 寫入 SQLite 是旁路指標，不應影響命令本身成功與否。

### 資料流（Data Flow）

1. Hook 或使用者輸入 command。
2. `main.rs` 以 `clap` parse 到 `Commands` enum；成功則 dispatch 到專用模組。
3. 專用模組呼叫 `core::runner::run_filtered()`、`run_streamed()` 或 `run_passthrough()`。
4. `core::stream::run_streaming()` 捕捉 stdout/stderr，並用 10 MiB `RAW_CAP` 避免無限吃記憶體。
5. Filter 產出 compact output。
6. 若失敗且 raw output 足夠大，`core::tee` 寫到本地 raw log 並輸出 hint。
7. `core::tracking` 估算 token，寫入 platform data dir 的 SQLite。

### 關鍵程式碼（Key Code Snippets）

`src/core/runner.rs` 的核心抽象把「執行子命令、filter、print、track」集中起來，讓每個 command module 不需要重寫同樣的 capture/track 邏輯：

```rust
pub enum RunMode<'a> {
    Filtered(Box<dyn Fn(&str) -> String + 'a>),
    Streamed(Box<dyn StreamFilter + 'a>),
    Passthrough,
}

pub fn run(
    mut cmd: Command,
    tool_name: &str,
    args_display: &str,
    mode: RunMode<'_>,
    opts: RunOptions<'_>,
) -> Result<i32> {
    let timer = tracking::TimedExecution::start();
    let cmd_label = format!("{} {}", tool_name, args_display);
    // mode 分支中執行 child process、套用 filter、列印、tracking
}
```

`src/core/toml_filter.rs` 的 8-stage pipeline 是 RTK 最值得借鏡的「可配置壓縮語言」：

```text
1. strip_ansi
2. replace
3. match_output
4. strip/keep_lines
5. truncate_lines_at
6. head/tail_lines
7. max_lines
8. on_empty
```

`src/cmds/system/log_cmd.rs` 的 log dedupe 精神很清楚：先把 timestamp、UUID、hex、長數字、path 正規化，再依 severity 分桶和計數：

```rust
if line_lower.contains("error")
    || line_lower.contains("fatal")
    || line_lower.contains("panic")
    || line_lower.contains("critical")
    || line_lower.contains("alert")
    || line_lower.contains("emerg")
    || line_lower.contains("severe")
{
    let count = error_counts.entry(normalized.clone()).or_insert(0);
    if *count == 0 {
        unique_errors.push(line.to_string());
    }
    *count += 1;
} else if line_lower.contains("warn") || line_lower.contains("notice") {
    let count = warn_counts.entry(normalized.clone()).or_insert(0);
    if *count == 0 {
        unique_warnings.push(line.to_string());
    }
    *count += 1;
} else if line_lower.contains("info") {
    *info_counts.entry(normalized).or_insert(0) += 1;
}
```

`src/core/truncate.rs` 用全域 cap 表達「不同訊號的保留預算」：

```rust
pub const CAP_ERRORS: usize = 20;
pub const CAP_WARNINGS: usize = 10;
pub const CAP_LIST: usize = 20;
pub const CAP_INVENTORY: usize = 50;
```

> [!tip] 對我們目前 log 爆量問題的直接啟發
> 不要只問「log 要少多少行」，要先定義訊號類別：error、warning、decision、progress、debug、artifact reference。每類有不同 cap、排序、dedupe key 與 raw recovery 策略。

## 安裝流程（Installation Flow）

### 安裝觸發方式

```
brew install rtk
  → Homebrew formula
  → binary placed in Homebrew prefix

curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/master/install.sh | sh
  → install.sh
  → downloads release binary
  → writes to ${RTK_INSTALL_DIR:-$HOME/.local/bin}/rtk

cargo install --git https://github.com/rtk-ai/rtk rtk
  → Cargo build/install
  → writes binary to Cargo bin dir

rtk init -g
  → src/hooks/init.rs
  → installs hook + RTK.md + settings.json patch for supported agents
```

### 安裝時序圖

```
User          Package/Script        RTK init                Agent Config
 │                  │                  │                         │
 │ install binary   │                  │                         │
 │─────────────────►│                  │                         │
 │                  │ write rtk binary │                         │
 │                  │─────────────────►│ ~/.local/bin/rtk        │
 │ rtk init -g      │                  │                         │
 │────────────────────────────────────►│                         │
 │                  │                  │ write hook              │
 │                  │                  │────────────────────────►│ ~/.claude/hooks/rtk-rewrite.sh
 │                  │                  │ write RTK.md            │
 │                  │                  │────────────────────────►│ ~/.claude/RTK.md
 │                  │                  │ patch settings.json     │
 │                  │                  │────────────────────────►│ ~/.claude/settings.json
 │ restart agent    │                  │                         │
 │───────────────────────────────────────────────────────────────►│
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.local/bin/rtk` | binary | `install.sh` 預設安裝位置 |
| `~/.claude/hooks/rtk-rewrite.sh` | shell hook | Claude Code PreToolUse rewrite |
| `~/.claude/RTK.md` | markdown | slim awareness instructions |
| `~/.claude/CLAUDE.md` | markdown | `@RTK.md` reference |
| `~/.claude/settings.json` | JSON | hook registration，安裝前會備份 |
| `~/.config/rtk/config.toml` 或 macOS `~/Library/Application Support/rtk/config.toml` | TOML | tracking、tee、hooks exclude、limits |
| `~/.config/rtk/filters.toml` | TOML | user-global custom filters |
| `{project}/.rtk/filters.toml` | TOML | project-local custom filters，需要 trust |
| `~/.local/share/rtk/tee/` 或 platform data dir | directory | failure raw output recovery |
| `~/.local/share/rtk/tracking.db` 或 platform data dir | SQLite | token savings tracking |
| `$CODEX_HOME/RTK.md` 或 `~/.codex/RTK.md` | markdown | Codex mode awareness document |
| `$CODEX_HOME/AGENTS.md` 或 `~/.codex/AGENTS.md` | markdown | Codex instruction injection |

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| `RTK_INSTALL_DIR` | binary installation directory | `install.sh` |
| `RTK_VERSION` | pinned release version | `install.sh` |
| `RTK_DISABLED=1` | single-command bypass | 執行時 |
| `RTK_NO_TOML=1` | bypass TOML filters | 執行時 |
| `RTK_TOML_DEBUG=1` | debug matching filter and line counts | 執行時 |
| `RTK_TEE=0` | disable raw tee | 執行時 |
| `RTK_TEE_DIR` | custom tee directory | 執行時 |
| `RTK_HOOK_AUDIT=1` | enable hook audit log | hook 執行時 |
| `RTK_AUDIT_DIR` | custom hook audit dir | hook 執行時 |
| `RTK_TELEMETRY_DISABLED=1` | disable telemetry | 執行時 |
| `SKIP_ENV_VALIDATION=1` | forwarded to selected child processes | `--skip-env` |

> [!warning] 解除安裝
> `rtk init -g --uninstall` 會移除 hook、RTK.md、settings.json entry 等 agent integration，但 tracking DB、tee raw output、user config 與 binary 需依安裝方式額外清理。

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 自動改寫 Bash command | `git status` via agent hook | `src/hooks/rewrite_cmd.rs` | `hooks::permissions → discover::registry → hook processor` |
| 2 | 專用 CLI 壓縮 | `rtk git status` / `rtk cargo test` | `src/main.rs` | `Commands enum → cmds::* → core::runner` |
| 3 | 長尾工具 line filter | `rtk gradle build` parse fallback | `src/main.rs:run_fallback` | `toml_filter::find_matching_filter → apply_filter` |
| 4 | Log dedupe | `rtk log app.log` / stdin | `src/cmds/system/log_cmd.rs` | `normalize → severity bucket → count → cap` |
| 5 | Raw output recovery | failed command with large output | `src/core/tee.rs` | `tee_and_hint → write_tee_file → rotation` |
| 6 | Token savings dashboard | `rtk gain` | `src/analytics/gain.rs` | `core::tracking → SQLite aggregate` |

### 案例詳解

#### 案例 1：Hook rewrite

```
用戶 / Agent：git status
  │
  ▼
agent hook invokes rtk rewrite
  │
  ▼
src/hooks/rewrite_cmd.rs
  │
  ├─ check_command() loads deny/ask/allow rules
  │
  └─ registry::rewrite_command()
        │
        ▼
discover::lexer splits chains and redirects safely
        │
        ▼
discover::rules maps command to RTK equivalent
        │
        ▼
stdout: rtk git status
```

#### 案例 2：Dedicated command filter

```
用戶：rtk git status
  │
  ▼
src/main.rs Clap parse
  │
  ▼
Commands::Git { command: GitCommands::Status }
  │
  ▼
src/cmds/git/*
  │
  ▼
core::runner::run_filtered()
  │
  ├─ execute native git
  ├─ compact status output
  ├─ preserve exit code
  └─ tracking::TimedExecution
```

#### 案例 3：Log dedupe

```
用戶：rtk log app.log
  │
  ▼
src/cmds/system/log_cmd.rs::run_file()
  │
  ▼
read full file
  │
  ▼
normalize each line:
timestamp / UUID / hex / long number / path → placeholders
  │
  ▼
bucket by severity:
error-like / warning-like / info
  │
  ▼
sort unique patterns by frequency
  │
  ▼
print summary + capped top errors/warnings
```

#### 案例 4：TOML custom filter for our noisy logs

```
用戶：rtk my-build-command
  │
  ▼
Clap cannot parse as dedicated RTK command
  │
  ▼
main.rs::run_fallback()
  │
  ▼
lookup priority:
1. .rtk/filters.toml
2. ~/.config/rtk/filters.toml
3. built-in filters
  │
  ▼
apply 8-stage pipeline
  │
  ▼
print compact output, record savings
```

## Log 爆量問題：RTK 的處理精神

### 不是摘要，而是訊號預算（Signal Budget）

RTK 沒有把 log 當成一串文字，而是把輸出分成不同價值層級：

| 訊號類型 | RTK 策略 | 我們可借鏡的規則 |
|----------|----------|------------------|
| Error / failure | 顯示最多，保留原始第一筆與 count | cap 20；按頻率與嚴重度排序 |
| Warning / notice | 顯示較少 | cap 5–10；只保留 unique pattern |
| Success / ok | 盡量一行 | `on_empty = "tool: ok"` |
| Progress / download / installing | strip | 不該進上下文，除非卡住 |
| Large raw output | tee to file | 摘要旁只放路徑 |
| Debug / trace | default hidden | 需要 `-v` / `--debug` 才顯示 |
| Inventory list | cap higher | 例如 packages、resources 可保留 50 |

### 對「update RTK / 減少我們手上 log」的建議

如果我們要改寫目前的 update RTK 或自己的 log 管線，我建議不要先改成「少印一點」。應該採用 RTK 這個分層：

1. **新增 log classification**：每行先歸類為 `error`、`warn`、`decision`、`progress`、`debug`、`artifact`。
2. **定義 normalize key**：timestamp、UUID、path、PID、duration、request id 都正規化後再 dedupe。
3. **每類 cap 不同**：error 20、warn 10、progress 0–3、debug 0、artifact references 10。
4. **成功路徑極短**：沒有 error/warn 時輸出 `ok: {summary}`，不要列完整執行過程。
5. **失敗才給 recovery path**：完整 log 寫到 `/tmp`、專案 `.logs/` 或 data dir，摘要中只輸出 `[full output: path]`。
6. **把 filter 規則變成資料**：先用 `.rtk/filters.toml` 或類似 TOML/JSON DSL，不要每個噪音模式都寫死在程式碼。

> [!example] 可作為起點的 project-local filter
> 若我們的 update command 是 line-based build/install log，可以先用 `.rtk/filters.toml` 快速驗證：

```toml
schema_version = 1

[filters.update-rtk]
description = "Compact update RTK logs — keep errors, warnings, decisions, and final summary"
match_command = "^update-rtk\\b"
strip_ansi = true
strip_lines_matching = [
  "^\\s*$",
  "^Downloading\\b",
  "^Installing\\b",
  "^Resolving\\b",
  "^Progress:",
  "^\\[debug\\]",
  "^\\[trace\\]",
]
truncate_lines_at = 160
max_lines = 40
on_empty = "update-rtk: ok"

[[tests.update-rtk]]
name = "drops progress and keeps warning"
input = "Downloading package\nProgress: 30%\n[warn] config already exists\nDone"
expected = "[warn] config already exists\nDone"
```

### 如果要更進一步：做 dedicated Rust/TS filter

TOML 適合 predictable line output；如果我們的 log 有 nested sections、JSON events、test failure blocks，應該改成 dedicated parser：

```
raw events
  │
  ▼
parse into structured records
  │
  ├─ severity
  ├─ phase
  ├─ entity path
  ├─ stable fingerprint
  └─ raw span offset
  │
  ▼
rank:
errors > warnings > decisions > summaries > progress
  │
  ▼
print compact report + full log pointer
```

## 架構師觀點（Architect's View）

### 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | 4/5 | `cmds/` 依 ecosystem 分層，`core::runner` 抽掉共同 execution skeleton。 |
| 可擴展性（Scalability） | 4/5 | TOML filters 解決長尾工具；dedicated modules 解決高價值工具。 |
| 安全性（Safety） | 4/5 | permission verdict 在 rewrite 前檢查；project filters trust-gated；fail-safe passthrough。 |
| 可觀測性（Observability） | 4/5 | tracking DB、gain、hook audit、tee recovery 形成自我量測閉環。 |
| 效能（Performance） | 4/5 | Rust single binary，streaming capture，raw cap 防止超大輸出吃爆。 |
| 測試策略（Test Coverage） | 4/5 | TOML filters 內嵌 tests；核心 normalization/truncate 有 unit tests。 |

> [!tip] 值得學習的設計
> RTK 把「壓縮規則」拆成三層：rewrite 決定是否介入、filter 決定怎麼壓縮、tee 決定怎麼恢復原文。這讓 token 節省不必犧牲除錯能力。

### 缺點與風險（Weaknesses & Risks）

- **語意壓縮可能漏訊號**：line-based TOML filter 對跨行錯誤、JSON nesting、progress 中的異常訊息容易誤刪。
- **hook 覆蓋率依 agent 能力而異**：Claude/Cursor/Gemini 這類 hook integration 較穩；Codex rules-file integration 仍依賴模型遵守。
- **tracking token 估算只是近似**：以字元估 token 可以看趨勢，不應用來做精準計費。
- **project-local filters 有信任與治理成本**：團隊若亂加 strip 規則，可能把重要 warning 藏起來。
- **版本資訊與公開文件可能不同步**：本機 `0.40.0` 與公開 release 索引 v0.39.0 有落差，導入時要以實際 binary `rtk --version` 為準。

### 改進建議（Improvement Suggestions）

1. 為 `rtk log` 增加 structured JSONL mode：輸出 `{severity, count, fingerprint, sample}`，方便 agent 或 dashboard 二次處理。
2. 將 cap 從 compile-time constants 逐步移入 config：讓團隊可依專案類型調整 error/warn/list 預算。
3. 對 TOML filter 增加 `priority` 或 explicit shadowing metadata：避免 project filter 無意蓋掉 built-in filter。
4. 對 failure tee 檔案加入 session id / command id metadata：方便把摘要與完整 raw output 對回同一次 agent turn。
5. 提供 `rtk filter --explain`：顯示每個 stage 刪了幾行，降低「被 filter 吃掉」的不信任感。

## 效能基準（Benchmark）

| 場景 | RTK 官方/README 主張 | 設計原因 |
|------|----------------------|----------|
| `ls` / `tree` | 約 -80% | 目錄樹化、忽略噪音目錄 |
| `cat` / `read` | 約 -70% | code filter level、line cap |
| `grep` / `rg` | 約 -80% | group by file、限制每檔結果 |
| `git status` | 約 -80% | 狀態聚合 |
| `git add/commit/push` | 約 -92% | 成功路徑壓成 ok |
| `cargo test` / `npm test` | 約 -90% | failures only |
| `pytest` / `go test` | 約 -90% | failures only + block parsing |
| `rtk log` | 依重複度而定 | severity 分桶 + normalize + count |

本機未重新跑 benchmark；此表以 README 與原始碼設計推論為主。實際 savings 取決於專案規模、測試失敗型態、log 重複度與 filter 是否命中。

## 快速上手（Quick Start）

```bash
# 驗證是不是 Rust Token Killer，而不是同名 Rust Type Kit
rtk --version
rtk gain

# 用於單次 log 壓縮
rtk log app.log
journalctl -u my-service | rtk log

# 對專案加自訂 filter
mkdir -p .rtk
$EDITOR .rtk/filters.toml
rtk trust
rtk verify --filter update-rtk

# 需要完整輸出時暫停 RTK
RTK_DISABLED=1 git status
```

## 我的心得（My Takeaways）

我之前把「log 太多」直覺想成 UI/輸出格式問題；RTK 顯示更正確的切入點是 **「agent context 前的資訊治理」**。核心不是漂亮摘要，而是把每個工具輸出轉成 decision surface：下一步要修哪裡、是否要重跑、是否需要讀 full output。

對我們自己的 update RTK 或任何高噪音流程，我會採用三步：

1. 先建立 stable fingerprint 與 severity bucket，不急著做自然語言摘要。
2. 成功路徑只輸出 final state；失敗路徑輸出 top-N unique failures + full raw path。
3. 把噪音規則外部化成 `.rtk/filters.toml` 這類資料檔，等模式穩定後再升級成程式碼 parser。

## FAQ — RTK 怎麼先被呼叫？

> [!faq]- RTK 是怎麼做到先呼叫自己的指令？
> RTK 不是在作業系統（Operating System）層攔截所有 shell command。它靠的是 AI coding agent 的「執行工具前」整合點：hook、plugin API，或 prompt-level rules。核心流程是：agent 想執行 `git status` → integration 先拿到 command string → 呼叫 `rtk rewrite "git status"` → RTK 回傳 `rtk git status` → agent 實際執行改寫後的命令。

> [!faq]- 所以真正的核心是 hook 嗎？
> 不是。真正的核心是 `rtk rewrite`，rewrite 規則集中在 Rust binary 裡。Hook、plugin、rules file 都只是 adapter。它們的職責是解析各 agent 的 payload、呼叫 `rtk rewrite`、再用該 agent 支援的格式把 command 改回去。

> [!faq]- OpenCode 沒有 shell hook，那它怎麼攔截？
> OpenCode 用 TypeScript plugin，不是 shell hook。`hooks/opencode/rtk.ts` 註冊 `tool.execute.before` event，只處理 `bash` / `shell` tool，讀取 `args.command`，執行 `rtk rewrite ${command}`。如果回傳 rewritten command，就直接把 `args.command` mutate 成新值。因此 OpenCode 是「plugin 事件前置改寫」，不是 OS hook，也不是 shell alias。

```typescript
return {
  "tool.execute.before": async (input, output) => {
    const tool = String(input?.tool ?? "").toLowerCase()
    if (tool !== "bash" && tool !== "shell") return

    const command = (args as Record<string, unknown>).command
    if (typeof command !== "string" || !command) return

    const result = await $`rtk rewrite ${command}`.quiet().nothrow()
    const rewritten = String(result.stdout).trim()
    if (rewritten && rewritten !== command) {
      ;(args as Record<string, unknown>).command = rewritten
    }
  },
}
```

> [!faq]- Codex CLI 也會被透明攔截嗎？
> 目前不是。RTK 對 Codex CLI 的整合是 `rtk init --codex` 寫入 `AGENTS.md` / `RTK.md`，屬於 prompt-level guidance。也就是提醒模型「請優先用 `rtk <cmd>`」，但沒有 guaranteed interception。模型可能遵守，也可能忘記。

> [!faq]- 哪些 agent 是真正透明改寫？
> Claude Code、Cursor、Gemini 走 full hook；OpenCode、Hermes、Pi、OpenClaw 走 plugin / extension API。這些都能在 command 執行前改寫。Cline、Windsurf、Codex、Kilo Code、Antigravity 則主要是 rules file / instruction，屬於 guidance，不是硬性攔截。

| 類型 | 例子 | 是否真正攔截 | 機制 |
|------|------|--------------|------|
| Full hook | Claude Code、Cursor、Gemini | 是 | Agent hook API 在 tool execution 前改寫 command |
| Plugin / extension | OpenCode、Hermes、Pi、OpenClaw | 是 | Plugin event 中原地 mutate command |
| Rules / instructions | Codex、Cline、Windsurf、Kilo、Antigravity | 否 | 提示模型優先使用 `rtk` |

### RTK Hook / Plugin 實作對照表（Source Map）

| Agent / 目標 | Source code 位置 | 檔名 | 實作語言 | 安裝後位置 / 設定檔 | 實作方法 | 是否透明改寫 |
|--------------|------------------|------|----------|----------------------|----------|--------------|
| Claude Code | `src/hooks/init.rs`、`src/hooks/hook_cmd.rs`、`src/hooks/constants.rs`；legacy artifact 在 `hooks/claude/` | `init.rs`、`hook_cmd.rs`、`constants.rs`、`rtk-rewrite.sh` | Rust；legacy shell 為 Bash + jq | `~/.claude/settings.json` 的 `hooks.PreToolUse`，命令為 `rtk hook claude`；另寫 `~/.claude/RTK.md` 與 `~/.claude/CLAUDE.md` reference | `rtk init -g` patch `settings.json`，在 Bash tool 執行前讀 JSON，改寫 `tool_input.command`，輸出 `hookSpecificOutput.updatedInput` | 是 |
| Cursor | `src/hooks/init.rs`、`src/hooks/hook_cmd.rs`；legacy artifact 在 `hooks/cursor/` | `init.rs`、`hook_cmd.rs`、`rtk-rewrite.sh` | Rust；legacy shell 為 Bash + jq | `~/.cursor/hooks.json` 或 Cursor hook 設定，命令為 `rtk hook cursor` | Cursor `preToolUse` hook 讀 `tool_input.command`，回傳 `updated_input.command`；沒有 rewrite 時回 `{}` | 是 |
| Gemini CLI | `src/hooks/hook_cmd.rs`、`src/hooks/init.rs` | `hook_cmd.rs`、`init.rs` | Rust | `~/.gemini/` hook 設定；常數為 `BeforeTool` / `rtk-hook-gemini.sh` | Gemini `BeforeTool` hook 只處理 `run_shell_command`，輸出 `{"decision":"allow","hookSpecificOutput":{"tool_input":{"command":...}}}` | 是 |
| VS Code Copilot Chat | `src/hooks/hook_cmd.rs` | `hook_cmd.rs` | Rust | 由 `rtk init --global --copilot` 註冊 preToolUse | 自動偵測 snake_case `tool_name` / `tool_input.command` 格式，回傳 Claude-like `updatedInput` | 是 |
| GitHub Copilot CLI | `src/hooks/hook_cmd.rs` | `hook_cmd.rs` | Rust | 由 `rtk init --global --copilot` 註冊 | Copilot CLI 不支援直接 `updatedInput`，RTK 回傳 `permissionDecision: "deny"` 與建議命令，讓 agent retry | 半透明；不是原地改寫 |
| OpenCode | `hooks/opencode/rtk.ts`；installer 在 `src/hooks/init.rs` | `rtk.ts`、`init.rs` | TypeScript plugin | `~/.config/opencode/plugins/rtk.ts` | OpenCode plugin 註冊 `tool.execute.before`，只處理 `bash` / `shell` tool，呼叫 `rtk rewrite` 後 mutate `args.command` | 是 |
| Pi coding agent | `hooks/pi/rtk.ts`；installer 在 `src/hooks/init.rs` | `rtk.ts`、`init.rs` | TypeScript extension | project-local `.pi/extensions/rtk.ts` 或 global `~/.pi/agent/extensions/rtk.ts` | Pi extension 監聽 `tool_call` event，用 `isToolCallEventType("bash", event)` guard，呼叫 `rtk rewrite` 後 mutate `event.input.command` | 是 |
| Hermes | `hooks/hermes/rtk-rewrite/__init__.py`、`hooks/hermes/rtk-rewrite/plugin.yaml`；installer 在 `src/hooks/init.rs` | `__init__.py`、`plugin.yaml`、`init.rs` | Python plugin + YAML manifest | `~/.hermes/plugins/rtk-rewrite/`，並 patch `~/.hermes/config.yaml` 的 `plugins.enabled` | Hermes Python plugin 在 terminal tool 執行前讀 mutable payload，呼叫 `rtk rewrite` 後 mutate `command`；fail open | 是 |
| OpenClaw | `openclaw/index.ts`、`openclaw/openclaw.plugin.json` | `index.ts`、`openclaw.plugin.json` | TypeScript plugin | 透過 `openclaw plugins install ./openclaw` 安裝 | OpenClaw plugin 使用 `before_tool_call` 類型 hook，委派 `rtk rewrite` 後改寫 command | 是 |
| Codex CLI | `hooks/codex/rtk-awareness.md`；installer 在 `src/hooks/init.rs` | `rtk-awareness.md`、`init.rs` | Markdown instructions + Rust installer | `$CODEX_HOME/RTK.md` / `$CODEX_HOME/AGENTS.md`，未設定則 `~/.codex/` | `rtk init --codex` 寫 awareness document 與 `@RTK.md` reference；沒有程式化 hook，只靠模型遵守 instructions | 否；prompt-level guidance |
| Cline / Roo Code | `hooks/cline/rules.md`；installer 在 `src/hooks/init.rs` | `rules.md`、`init.rs` | Markdown rules + Rust installer | project root `.clinerules` | 寫入自訂規則，要求模型偏好 `rtk <cmd>` | 否；prompt-level guidance |
| Windsurf | `hooks/windsurf/rules.md`；installer 在 `src/hooks/init.rs` | `rules.md`、`init.rs` | Markdown rules + Rust installer | project root `.windsurfrules` | 寫入 workspace-scoped rules，要求 Cascade 優先用 `rtk` | 否；prompt-level guidance |
| Kilo Code | `hooks/kilocode/rules.md`；installer 在 `src/hooks/init.rs` | `rules.md`、`init.rs` | Markdown rules + Rust installer | `.kilocode/rules/rtk-rules.md` | 寫入 Kilo Code rules directory，提示 shell commands 要 prefix `rtk` | 否；prompt-level guidance |
| Google Antigravity | `hooks/antigravity/rules.md`；installer 在 `src/hooks/init.rs` | `rules.md`、`init.rs` | Markdown rules + Rust installer | `.agents/rules/antigravity-rtk-rules.md` | 寫入 Antigravity rules directory，提示優先使用 `rtk` | 否；prompt-level guidance |

> [!note] 表格解讀
> `src/hooks/init.rs` 負責「安裝 / 移除 / patch 設定檔」，`src/hooks/hook_cmd.rs` 負責 Rust-native hook processor，`hooks/*` 則是各 agent 的外部 artifact 或 rules。真正的 rewrite 規則仍集中在 `src/discover/registry.rs`，各 integration 不應複製 rewrite logic。

> [!faq]- 所有作業系統通通可以用嗎？
> 要分成「RTK binary 可用」與「透明自動改寫可用」。手動執行 `rtk git status` 這種 binary usage 在 Windows、macOS、Linux 都可以。透明 shell hook 則依 agent 與 OS 而定：RTK 文件明確說 shell hook 需要 Unix shell；native Windows 會 fallback 到 prompt-level instructions。若要 Windows 上有完整 hook 行為，官方建議使用 WSL。

> [!faq]- 如果 hook / plugin 出錯，會不會擋住原命令？
> RTK 的設計目標是 fail open。找不到 `rtk`、payload 格式不符、`rtk rewrite` 出錯，adapter 應讓原始 command 照常執行。這符合 RTK 的 fail-safe 原則：省 token 不能犧牲命令可執行性。

## 待補充（Open Questions）

- RTK `0.40.0` 是否已正式 release？公開 GitHub 搜尋快照仍顯示 v0.39.0 latest，需查 GitHub Releases 或 tag。建議搜尋：`rtk-ai rtk v0.40.0 release`
- `rtk log` 是否有 planned JSON output？目前原始碼顯示是 text summary，若要接入 dashboard 需要結構化輸出。建議搜尋：`rtk log json output issue`
- TOML filter 的 trust model 在多人 repo 中如何治理？誰有權修改 `.rtk/filters.toml`？建議搜尋：`rtk project filters trust security`
- 對 agent hook collision 的處理在不同工具上是否仍有 edge cases？建議搜尋：`rtk hook collision Claude Code Cursor Gemini`
- 若我們把 update RTK 的 full raw output 寫到檔案，保留多久、存哪裡、是否包含敏感資訊？建議搜尋：`AI agent command output tee retention privacy`
- RTK 的 token 估算公式與實際 Claude/Codex tokenizer 的偏差多大？建議搜尋：`RTK token tracking estimation accuracy`

## 相關連結（Related）

- [[2026-04-28-CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]] — 同樣關注 token 成本，但 Claude Code 那篇偏計費對齊，RTK 偏工具輸出前置壓縮。
- [[2026-04-18-CLAUDE-CODE-TOKEN-QUOTA-THREE-TRAPS-AND-FIXES]] — RTK 是處理「環境與工具輸出膨脹」的具體工具層解法。
- [[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]] — gstack 用 append-only log + cursor sync 做觀測；RTK 用 tee + tracking DB 做 agent context 壓縮後的恢復與量測。
- [[2026-05-20-CODEX-HOOK-AND-SKILLS-PARAMETERS-DEEP-DIVE]] — Codex hook/skills 規格可對照 RTK 的 hook rewrite integration 限制。
- [[OUTBOX-PATTERN]] — tee raw output 與 tracking DB 都可視為 command output 的本地 outbox。

---
- [[2026-08-07-OPEN-CODE-REVIEW-ALIBABA-AI-CODE-REVIEW-CLI-CODE-ANALYSIS]] — 同屬「進 context 前先工程化削減」哲學:RTK 壓縮命令輸出,OCR 把探索與定位整段移出 LLM

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 必記概念：CLI proxy、hook rewrite、dedicated command module、TOML filter、tee recovery、tracking DB、severity bucket、stable fingerprint。 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | RTK 在 agent 與 shell 之間加一層 proxy：hook 負責介入，command module 或 TOML filter 負責壓縮，tee/tracking 負責可恢復與可量測。三者合起來才是完整 token 節省系統。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維，看透策略底層邏輯 | 關鍵假設是「命令輸出的決策訊號可以被規則化」。這對 test/build/git 很成立；對含業務語意的 log 或非結構化 crash dump，line filter 可能刪掉稀有但重要的訊號。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力，將理論轉為行動 | 行動 1：為 update RTK 建 `.rtk/filters.toml`，先 strip progress/debug、保留 warn/error/final summary。行動 2：在自己的 log pipeline 加 fingerprint + count。行動 3：失敗時寫 full raw output，摘要只放 path hint。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡，在不確定的情境中做出最佳選擇 | TOML filter 開發快、風險是語意不足；dedicated parser 成本高但可靠；LLM summary 彈性最高但 token 成本和不穩定性最高。對 update log 應先 TOML，穩定後升級 parser。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：我們說「Log 太多」時，真正想減少的是 token、視覺干擾、儲存成本，還是 debug 時間？
- **假設**：如果我們假設 progress/debug 預設無價值，在哪些 failure case 這個假設會失效？
- **證據**：目前 update RTK 的 raw log 中，error/warn/progress/debug 各佔多少比例？沒有樣本分佈前不該直接設定 cap。
- **觀點**：反對者會說壓縮 log 會降低除錯能力；RTK 用 tee recovery 回答這個批評，我們是否也有同等恢復路徑？
- **後果**：若 12 個月後所有 agent command 都被 filter，團隊是否會失去閱讀 raw output 的習慣，導致少數複雜事故更難排？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 最大風險是 filter 把真正的根因刪掉，agent 依 compact output 做錯修復。對策是 failure tee、filter tests、`RTK_DISABLED=1` bypass 與 `--verbose` raw mode。
2. **什麼情況下會失敗？** — 當 log 的重要訊號不是由 severity keyword、固定 pattern 或可解析 block 表達時，line-based filter 會失效；例如業務不變量違反只出現在普通 info line。
3. **有沒有更好的替代方案？** — 若已經有 structured events，應直接用 JSON parser/ranker，而非 regex；若是正式 production observability，應用 OTel / Loki / Datadog。RTK 類方案最適合 agent context 前的本地開發輸出壓縮。

## References

- [GitHub Repo — rtk-ai/rtk](https://github.com/rtk-ai/rtk)
- [Local source — /Users/swchen.tw/git/rtk_plan/rtk](</Users/swchen.tw/git/rtk_plan/rtk>)
- [README.md](https://github.com/rtk-ai/rtk/blob/master/README.md)
- [Architecture docs](https://github.com/rtk-ai/rtk/blob/master/docs/contributing/ARCHITECTURE.md)
- [Built-in filters README](https://github.com/rtk-ai/rtk/blob/master/src/filters/README.md)
