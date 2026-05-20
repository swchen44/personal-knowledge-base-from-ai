---
title: "Codex CLI 程式碼深度分析 — Rust Monorepo、103 個 Crate、三平台原生沙盒"
date: 2026-05-20
category: CodeAnalysis
tags:
  - code-analysis
  - ai/coding-agent
  - rust
  - terminal-tools
  - sandbox
source: "https://github.com/openai/codex"
source_type: code
author: "OpenAI"
status: notes
github_stars: 30000+
github_language: Rust + TypeScript wrapper
links:
  - "[[2026-05-20-CODEX-CLI-VS-CLAUDE-CODE-DEEP-COMPARISON]]"
  - "[[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]]"
  - "[[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]]"
  - "[[2026-02-12-EVALUATING-AGENTS-MD-CONTEXT-FILES-HELPFUL-FOR-CODING-AGENTS]]"
---

## 摘要（Summary）

Codex CLI 是 OpenAI 於 2025 年 4 月發表的開源終端機編碼代理（terminal coding agent），於 2025 年 6 月完成從 Node.js/TypeScript 到 Rust 的整碼重寫（rewrite），並在 2026 年 5 月達到 **103 個 Rust crate** 的高度模組化規模（codex-rs/ workspace）。本筆記基於 `openai/codex@1392a2a`（2026-05-20 HEAD）對其架構進行靜態分析，涵蓋安裝流程、4 個典型使用案例、跨平台沙盒（sandbox）、Starlark 規則引擎（execpolicy）、雙向 MCP、配置系統等核心子系統。Codex 的設計重心可概括為三條主軸：**「Rust 原生效能」、「OS 層級原生沙盒」、「ChatGPT 帳號整合 + 模型可選」**，與 Anthropic 的 Claude Code（TypeScript on Node.js）形成清楚對比。

## Why — 為什麼存在？

> 這個專案要解決的根本問題是什麼？現有方案的哪些痛點促使它被創造？

- **核心動機**：在終端機提供一個能直接讀寫檔案、執行指令、跑測試、提交 Git 的 AI agent，讓使用者不必離開命令列就能完成從理解需求到實作的整套迴圈。OpenAI 希望這個 agent 是：
  1. **本地優先（local-first）**：在使用者機器上跑，不上傳整個 repo
  2. **零依賴（zero-dependency）**：單一二進位（Rust 編譯），不需要 Node runtime
  3. **OS 原生沙盒**：用 macOS Seatbelt、Linux Bubblewrap/Landlock、Windows RestrictedToken 真正鎖住可寫範圍與網路
  4. **與 ChatGPT 訂閱整合**：Plus/Pro/Business/Edu/Enterprise 使用者直接登入即用，免另接 API key
- **取代/改善什麼**：
  - 取代了 2025 年初的 Node.js/TypeScript 版本（理由：Node runtime 啟動慢、依賴 tree 大、跨平台沙盒不易精準控制）
  - 改善了「逐條 shell 命令彈視窗審批」的人工負擔（改用預先聲明的 Starlark 規則 + sandbox 強制）
  - 改善了「只能用一家 LLM」（透過 `model-provider`、`chatgpt`、`ollama`、`lmstudio` 等多個 crate 抽象出 provider）
- **目標用戶**：
  - 已有 ChatGPT 訂閱、想在終端機用同一個帳號跑 agent 的開發者
  - 對沙盒安全性敏感、需要在受控環境跑 AI 的團隊
  - 希望整合 IDE（VS Code、Cursor、Windsurf）、CI、雲端任務的 agent 平台建構者

## What — 是什麼？

> 這個專案的功能邊界與核心能力。

- **主要功能**：
  - 互動式 TUI（基於 ratatui）：對話、即時看見檔案改動與 shell 輸出
  - 非互動式 `codex exec` 模式：一次性執行 prompt，可接 stdin、可加 `--ephemeral` 不留下 session
  - 多平台 sandbox：`read-only`、`workspace-write`、`danger-full-access` 三檔
  - Starlark 規則引擎（execpolicy）：用 `prefix_rule()` 預先宣告允許/詢問/禁止
  - 雙向 MCP：既當 MCP client（連外部工具），也能當 MCP server（讓其他 agent 把 Codex 當工具）
  - 多 LLM provider 支援：OpenAI ChatGPT、API、Ollama、LM Studio、（部分）AWS Bedrock
  - Hooks 機制（codex-hooks crate）：用 TOML 配置事件鉤子，可被 admin 強制限定
  - App Server / Daemon：把 Codex 變成 background 服務供 IDE/Web 串接
  - Cloud Tasks：將任務送到雲端（chatgpt.com/codex Web）執行
- **不做什麼（Non-goals）**：
  - 不內建 IDE 視覺編輯介面（VS Code/Cursor/Windsurf 各有獨立 plugin）
  - 不取代 Git、shell、編輯器，純粹是 agent 層
  - 不主動上傳 repo 到雲端（雲端模式是 opt-in 的 Cloud Tasks）
- **技術棧（Tech Stack）**：
  - 主語言：**Rust**（codex-rs/ workspace，含 103 個 crate）
  - CLI dispatcher：**Node.js**（codex-cli/bin/codex.js，僅做平台偵測 + spawn 二進位）
  - 建構系統：**Cargo** + **Bazel**（雙構建，Bazel 負責 monorepo 統一）
  - TUI：**ratatui**（Rust TUI 函式庫）
  - 規則引擎：**Starlark**（Google 設計的 Python 子集，用於 execpolicy）
  - 沙盒：Seatbelt `.sbpl`（macOS）+ Bubblewrap/Landlock（Linux）+ Windows sandbox crate
  - MCP：`rmcp` + `@modelcontextprotocol/sdk` 1.26.0
  - 套件管理：pnpm 10.33.0+（Node 端）、Cargo workspace（Rust 端）
  - 發布：npm（platform-specific optional dependencies）+ Homebrew Cask + GitHub Releases

## How — 如何運作？

> 本節包含 3 種 ASCII 圖：系統架構圖、執行流程圖、雙向 MCP 時序圖。

### 系統架構圖（System Architecture）

```
┌────────────────────────────────────────────────────────────────────┐
│                  使用者環境（Terminal / IDE / CI）                  │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ 執行 codex
                               ▼
              ┌──────────────────────────────────────┐
              │   codex-cli/bin/codex.js (Node.js)   │
              │     · 偵測 platform + arch           │
              │     · 從 @openai/codex-{platform}    │
              │       optional-dep 取 vendor 二進位  │
              │     · spawn 子行程 + 信號轉發         │
              └──────────────┬───────────────────────┘
                             │ exec
                             ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │   codex (Rust 二進位)  —  codex-rs/cli/src/main.rs              │
   │                                                                 │
   │   subcommand 分派：interactive / exec / mcp / mcp-server /       │
   │                    sandbox / execpolicy / debug / app           │
   └───────┬─────────────────────────────────────────────────────────┘
           │
   ┌───────┴────────────────────────────────────────────────────────┐
   │  核心子系統（103 crates；以下為代表）                          │
   │                                                                 │
   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
   │  │   codex-tui  │  │  codex-exec  │  │ codex-app-server     │  │
   │  │ (ratatui TUI)│  │ (一次性執行)  │  │ (daemon for IDEs)    │  │
   │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
   │         │                 │                     │              │
   │         └─────────┬───────┴─────────────────────┘              │
   │                   ▼                                            │
   │            ┌─────────────────────┐                             │
   │            │  codex-core (orchestration / Session / TurnContext)│
   │            └──┬──────────┬──────────┬──────────┬──────┬───────┘│
   │               │          │          │          │      │        │
   │               ▼          ▼          ▼          ▼      ▼        │
   │      ┌──────────┐  ┌──────────┐ ┌───────┐ ┌────────┐ ┌──────┐  │
   │      │ model-   │  │codex-mcp │ │ tools │ │ hooks  │ │skills│  │
   │      │ provider │  │(雙向 MCP)│ │       │ │        │ │      │  │
   │      └────┬─────┘  └────┬─────┘ └───┬───┘ └────┬───┘ └──┬───┘  │
   │           │             │           │          │        │      │
   │           ▼             ▼           ▼          ▼        ▼      │
   │      ┌────────────┐ ┌────────┐ ┌──────────────────────────────┐│
   │      │ chatgpt /  │ │ rmcp-  │ │  execpolicy (Starlark 規則)  ││
   │      │ ollama /   │ │ client │ │   + sandboxing（OS 沙盒）    ││
   │      │ lmstudio   │ │        │ │   + bwrap / landlock /       ││
   │      └─────┬──────┘ └────┬───┘ │     seatbelt / windows-sbx   ││
   │            │             │     └──────────────────────────────┘│
   └────────────┼─────────────┼──────────────────────────────────────┘
                ▼             ▼
        ┌──────────────┐  ┌──────────────────┐
        │ LLM API      │  │ MCP Servers      │
        │ (OpenAI/Local)│  │ (filesystem,    │
        └──────────────┘  │  github, ...)    │
                          └──────────────────┘

  本地儲存：~/.codex/{config.toml, memories/, sessions/, login.toml}
  Linux sandbox 資源：codex-resources/bwrap（bundled bubblewrap fallback）
```

### 執行流程圖（Execution Flowchart — 互動模式單回合）

```
 使用者輸入 prompt 進入 TUI
   │
   ▼
[codex-tui 蒐集 context]
   │ 注入 AGENTS.md / config.toml / skills / memories
   ▼
[codex-core 構造 turn context]
   │
   ▼
[model-provider 送 request 到 LLM]
   │
   ├─ 回 text only ──► [TUI render 文字]
   │
   └─ 回 tool_call
        │
        ▼
   ┌────────────────────────────────────┐
   │ tools::tool_executor 分派           │
   ├────────────────────────────────────┤
   │ shell tool？──► execpolicy 評估     │
   │                  │                  │
   │       ┌──────────┼──────────┐       │
   │       ▼          ▼          ▼       │
   │    allow      prompt     forbidden  │
   │       │          │          │       │
   │       │          ▼          │       │
   │       │   [向使用者     ]   │       │
   │       │   [請求 approval]   │       │
   │       │          │          │       │
   │       └──────────┴──┐       └──► [拒絕，回傳錯誤給 LLM]
   │                     ▼
   │              [進入 sandbox：              ]
   │              [ macOS seatbelt /           ]
   │              [ Linux bwrap+seccomp /       ]
   │              [ Windows RestrictedToken     ]
   │                     │
   │                     ▼
   │              [執行 shell command]
   │                     │
   │                     ▼
   │              [stdout/stderr → tool output]
   │
   │ MCP tool？──► codex-mcp::connection_manager
   │                  │
   │                  ▼
   │              [送 JSON-RPC 到 MCP server]
   │                  │
   │                  ▼
   │              [收到 result → tool output]
   │
   ▼
[hooks::registry 發火相對事件（pre/post tool, turn end…）]
   │
   ▼
[rollout / thread-store 寫入 session 歷史]
   │
   ▼
[TUI render 結果]
   │
   ▼
 等待下一輪輸入
```

### 雙向 MCP 時序圖（Sequence — Codex as MCP client AND server）

```
 IDE / 其他 Agent      Codex (mcp-server)     Codex Core         MCP Server (filesystem)
        │                     │                     │                      │
        │──tools/list────────►│                     │                      │
        │                     │──discover──────────►│                      │
        │                     │                     │──tools/list─────────►│
        │                     │                     │◄──tools/list─────────│
        │                     │◄────────────────────│                      │
        │◄──tools list────────│                     │                      │
        │                     │                     │                      │
        │──tools/call          │                     │                      │
        │  (codex.exec)──────►│                     │                      │
        │                     │──exec prompt───────►│                      │
        │                     │                     │ ── tool_call:        │
        │                     │                     │    read_file ───────►│
        │                     │                     │◄── content ──────────│
        │                     │                     │ ── LLM response ─►   │
        │                     │◄── final ─-─────────│                      │
        │◄── result ──────────│                     │                      │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> Codex 整體採用「**核心薄、衛星厚**」策略：`codex-core` 只做編排（Session、TurnContext、approval flow），所有專業能力（沙盒、規則引擎、MCP、Provider、TUI…）都拆成獨立 crate。`AGENTS.md` 明文寫著「**resist adding code to codex-core**」。

1. **Node dispatcher + Rust binary 的雙層 CLI** — 同時取得 npm 生態系（容易發布、容易更新）與 Rust 效能（無 runtime overhead）兩邊優勢。代價是要維護 platform-specific optional dependencies (`@openai/codex-{linux-x64, darwin-arm64, win32-arm64, ...}`)。
2. **三平台原生沙盒** — 不用 Docker、不用 VM、直接呼叫 OS 原生沙盒 API。Linux 偏好系統 `bwrap` 但 bundle 一個 fallback；macOS 用 Seatbelt `.sbpl` policy；Windows 用獨立的 sandbox crate。WSL2 走 Linux 路徑，WSL1 因無 user namespace 直接拒絕沙盒命令。
3. **Starlark 規則引擎取代逐條審批** — execpolicy 用 `prefix_rule(pattern=[...], decision="allow|prompt|forbidden", justification=...)` 預先宣告允許清單，支援列表（alternatives）、`host_executable()` 限定 absolute path、內建 `match`/`not_match` unit-test 範例。決定權從「runtime 跳出 modal」前移到「config-time 宣告」。
4. **雙向 MCP（Both Client & Server）** — 不只用 MCP 接外部工具，還能 `codex mcp-server` 把 Codex 自己暴露給其他 agent。形成可組合的 agent 網絡。
5. **多 provider 抽象 + ChatGPT 帳號整合** — `model-provider` crate 提供統一介面，但有 `chatgpt` 專屬 crate 處理 OpenAI 官方訂閱登入（device code OAuth + PKCE），讓非開發者也能直接用。
6. **hooks 系統 + admin 強制限制** — `requirements.toml` 中 `allow_managed_hooks_only = true` 可禁用使用者層 hooks，讓企業 admin 能強制套用管控政策。
7. **Bazel + Cargo 雙構建** — Cargo 處理開發迴圈，Bazel 處理 monorepo 統一構建、JSON schema 自動產生、跨平台發布。

### 資料流（Data Flow — 一個典型 turn）
1. 使用者在 TUI 輸入 → `codex-tui` 蒐集 prompt
2. `codex-core` 注入 context（AGENTS.md、config.toml、skills、memories）
3. `model-provider` 依 config 決定送到 ChatGPT API / Ollama / LM Studio
4. LLM 回傳 tool_call → `tools::tool_executor` 分派
5. 若是 shell command：`execpolicy` 評估 → 若需要 prompt 則暫停 → 通過後進入 OS sandbox 執行
6. 若是 MCP tool：`codex-mcp::connection_manager` JSON-RPC 呼叫
7. `hooks::registry` 在 pre/post 各階段發火，外部 script 可監聽
8. `rollout` + `thread-store` 寫入 session 歷史到 `~/.codex/sessions/`
9. TUI 渲染結果，等待下一輪

### 關鍵程式碼（Key Code Snippets）

**Starlark 規則範例**（取自 execpolicy/README.md）：

```starlark
prefix_rule(
    pattern = ["cmd", ["alt1", "alt2"]],   # 有序 tokens；list 元素表示 alternatives
    decision = "prompt",                    # allow | prompt | forbidden；預設 allow
    justification = "explain why this rule exists",
    match = [["cmd", "alt1"], "cmd alt2"], # 必須匹配的範例（load-time 驗證）
    not_match = [["cmd", "oops"], "cmd alt3"], # 必須不匹配的範例
)

host_executable(
    name = "git",
    paths = [
        "/opt/homebrew/bin/git",
        "/usr/bin/git",
    ],
)
```

**Sandbox mode 切換**：

```shell
# 預設只讀
codex --sandbox read-only

# 工作目錄可寫，仍封網路
codex --sandbox workspace-write

# 危險：完全停用沙盒（只在容器內用）
codex --sandbox danger-full-access
```

**`~/.codex/config.toml` 配置**：

```toml
sandbox_mode = "workspace-write"
# 在 workspace-write 模式下，~/.codex/memories 自動加入 writable roots
```

**Node CLI dispatcher 平台偵測**（取自 codex-cli/bin/codex.js）：

```javascript
const PLATFORM_PACKAGE_BY_TARGET = {
  "x86_64-unknown-linux-musl": "@openai/codex-linux-x64",
  "aarch64-unknown-linux-musl": "@openai/codex-linux-arm64",
  "x86_64-apple-darwin": "@openai/codex-darwin-x64",
  "aarch64-apple-darwin": "@openai/codex-darwin-arm64",
  "x86_64-pc-windows-msvc": "@openai/codex-win32-x64",
  "aarch64-pc-windows-msvc": "@openai/codex-win32-arm64",
};
```

## 安裝流程（Installation Flow）

> [!info] 追蹤層級
> 本節追蹤到**具體檔案路徑**。讀者應能根據本節直接找到 Codex 安裝後的產物。

### 安裝觸發方式

```
npm install -g @openai/codex
   └─► 解析 optional dependencies (@openai/codex-{platform}-{arch})
       └─► 寫入 node_modules/@openai/codex-{platform}/vendor/{target-triple}/codex/codex
       └─► npm 自動建立 ~/.npm-global/bin/codex → codex-cli/bin/codex.js 的 symlink

brew install --cask codex
   └─► 下載 GitHub Release 的 codex-{aarch64|x86_64}-apple-darwin.tar.gz
       └─► 解壓到 /opt/homebrew/Caskroom/codex/ + symlink 到 /opt/homebrew/bin/codex

直接下載 GitHub Release
   └─► tar -xzf codex-{target}.tar.gz；自行 chmod +x；放入 PATH
```

### 安裝時序圖

```
 使用者     npm/brew              Node dispatcher       OS                ~/.codex/
    │           │                       │                │                    │
    │──install──►│                       │                │                    │
    │           │──optional-dep解析────►│                │                    │
    │           │  (依 platform 抓對應 npm 包)             │                    │
    │           │       │              ▼                │                    │
    │           │       │     寫入 node_modules/...     │                    │
    │           │       │     /vendor/{triple}/codex/    │                    │
    │           │       │     codex (Rust binary)        │                    │
    │           │       │                                │                    │
    │           │◄──完成─────────────────                │                    │
    │◄──完成────│                       │                │                    │
    │                                                                          │
    │ 第一次執行：codex                                                         │
    │                       │                                                  │
    │                       │──platform 偵測             │                    │
    │                       │──spawn vendor binary──────►│                    │
    │                       │                            │                    │
    │                       │                            │──首次無 ~/.codex──►建立目錄
    │                       │                            │                    │
    │                       │      [Sign in with ChatGPT]│──寫入 login.toml──►
    │                       │                            │                    │
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.npm-global/bin/codex`（或對應 brew bin） | symlink | CLI 入口 |
| `node_modules/@openai/codex-{platform}-{arch}/vendor/{target}/codex/codex` | 二進位 | Rust 主程式（npm 安裝路徑） |
| `node_modules/@openai/codex-{platform}-{arch}/vendor/{target}/codex/codex-linux-sandbox` | 二進位 | Linux 沙盒 helper（僅 Linux） |
| `node_modules/@openai/codex-{platform}-{arch}/vendor/.../codex-resources/bwrap` | 二進位 | bundled bubblewrap fallback（僅 Linux，當系統無 `bwrap` 時使用） |
| `~/.codex/config.toml` | TOML 檔 | 使用者層設定（首次執行或登入後建立） |
| `~/.codex/login.toml` | TOML 檔 | ChatGPT OAuth 授權 token（device code flow 完成後寫入） |
| `~/.codex/memories/` | 目錄 | 跨 session 記憶；`workspace-write` 模式下自動加入 writable roots |
| `~/.codex/sessions/` | 目錄 | session rollout 持久化（`codex exec --ephemeral` 可關閉） |
| `~/.codex/requirements.toml` | TOML 檔（選用） | admin 強制設定，含 `allow_managed_hooks_only` |

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| `CODEX_SANDBOX` | `seatbelt` | 子行程在 Seatbelt 沙盒內執行時自動設定 |
| `CODEX_SANDBOX_NETWORK_DISABLED` | `1` | 沙盒禁用網路時自動設定 |
| `CODEX_SANDBOX_NETWORK_DISABLED_ENV_VAR` | （建構時保留名稱） | 永遠不可修改的內部 contract |
| `RUST_LOG` | `info` / `debug` 等 | 開啟 Rust tracing 日誌 |
| `WT_SESSION` | （Windows Terminal 設定） | Codex 用此偵測是否在 WT 內，決定通知 fallback 路徑 |
| `npm_config_user_agent` / `npm_execpath` | （npm 設定） | dispatcher 用來判斷是否是 bun 安裝 |

> [!warning] 解除安裝
> `npm uninstall -g @openai/codex` 只會移除 npm 部分，**不會清理 `~/.codex/`**。完整清除需要 `rm -rf ~/.codex/`（注意：會刪除 session 歷史、記憶、登入 token）。

---

## 使用案例地圖（Use Case Map）

> [!important] 本節針對 4 個主要使用案例，追蹤從**用戶觸發**到**最終效果**的完整檔案路徑。

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 執行 shell 指令並通過 sandbox 與規則檢查 | TUI 對話 → LLM 回傳 shell tool_call | `codex-tui` | `tools → execpolicy → sandboxing → bwrap/seatbelt` |
| 2 | 連到外部 MCP server 取得資源 | `~/.codex/config.toml` 中 `mcp_servers.*` | `codex-mcp` | `connection_manager → rmcp-client → MCP server` |
| 3 | 用 ChatGPT 帳號登入（Device Code OAuth + PKCE） | `codex` 首次執行 → Sign in with ChatGPT | `codex-cli` → `login` | `login::device_code_auth → pkce → server (callback) → token_data` |
| 4 | `codex exec` 非互動模式跑一次性 prompt | shell `codex exec "..."` 或 pipe stdin | `codex-cli` | `codex-exec → codex-core → model-provider → tools` |

### 案例詳解

#### 案例 1：執行 shell 指令（最關鍵的安全路徑）

```
使用者：在 TUI 內接受 LLM 的 shell tool_call
  │
  ▼
codex-tui::chatwidget 接收 LLM 回應
  │
  ▼
codex-tools::tool_executor 分派 → 認出是 shell tool
  │
  ▼
codex-execpolicy::evaluate(command)  ── 讀取 ──► ~/.codex/config.toml + 內建 default.rules
  │
  ├─ decision = "forbidden" → 直接拒絕，回 error 給 LLM
  │
  ├─ decision = "prompt" → 暫停 TUI 跳審批 UI
  │
  └─ decision = "allow"
        │
        ▼
codex-sandboxing::manager 依 sandbox_mode 配置：
  · macOS  → seatbelt.rs 載入 .sbpl policy → sandbox-exec spawn
  · Linux  → bwrap.rs 構造 bubblewrap argv（--ro-bind /, --bind <writable_roots>,
             --ro-bind <protected: .git, .codex>，PR_SET_NO_NEW_PRIVS + seccomp）
  · Windows → windows-sandbox-rs (RestrictedToken)
  │
  ▼
[執行 shell command] → 子行程環境變數有 CODEX_SANDBOX=seatbelt 等標記
  │
  ▼
stdout/stderr → codex-core 收集 → 寫入 rollout/thread-store → 回 LLM
  │
  ▼
codex-hooks::registry 發火 post-tool-call 事件
```

#### 案例 2：連到外部 MCP server

```
config.toml 設定：
  [mcp_servers.filesystem]
  command = "npx"
  args = ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
  │
  ▼
codex 啟動 → codex-mcp::connection_manager 讀 config
  │
  ▼
為每個 server spawn 子行程，建立 stdio 雙向 JSON-RPC
  │
  ▼
rmcp-client 發 initialize → tools/list → resources/list
  │
  ▼
回傳的 tool 加入 codex-tools 的 tool registry，與 built-in tools 合併
  │
  ▼
LLM 看到合併後的完整 tool 清單
  │
  ▼
LLM tool_call mcp:filesystem:read_file → connection_manager 路由回對應 server
```

#### 案例 3：ChatGPT 帳號登入（Device Code OAuth + PKCE）

```
使用者：codex（首次執行）
  │
  ▼
codex-cli/src/main.rs 偵測 ~/.codex/login.toml 不存在
  │
  ▼
TUI 顯示「Sign in with ChatGPT」選項
  │
  ▼
codex-login::device_code_auth 啟動：
  · pkce.rs 生成 code_verifier + code_challenge
  · 向 OAuth server 註冊 device，取得 device_code + user_code
  │
  ▼
TUI 顯示 user_code 與 verify URL (https://chatgpt.com/auth/device)
  │
  ▼
codex-login::server.rs 開 localhost callback server（也接受 polling）
  │
  ▼
使用者在瀏覽器完成授權
  │
  ▼
codex-login::token_data 收到 access_token + refresh_token
  │
  ▼
寫入 ~/.codex/login.toml（含 expiry）；後續 model-provider 自動帶 token
```

#### 案例 4：`codex exec` 非互動模式

```
shell：echo "Summarize this" | codex exec --ephemeral "Read the latest commit"
  │
  ▼
codex-cli/src/main.rs → 偵測 subcommand = "exec"
  │
  ▼
codex-exec crate 接管：
  · 解析 args + 讀 stdin（若有 pipe）
  · 將 stdin 內容 append 為 <stdin> block 接在 prompt 後
  · --ephemeral：rollout 寫入 in-memory 不落地
  │
  ▼
codex-core::Session::new() 不寫入 ~/.codex/sessions/
  │
  ▼
進入單次 turn loop：
  model-provider 送 LLM → tool_call → tools 執行 → 結果回 LLM
  直到 LLM 決定結束
  │
  ▼
最終回應直接 print 到 stdout；exit code 反映 LLM 是否完成
```

> [!note] 閱讀建議
> 若要快速驗證某功能，從「入口檔案」欄直接跳去讀對應的源碼最有效率。例如想了解沙盒，去 `codex-rs/sandboxing/src/` 看 `bwrap.rs`、`seatbelt.rs`、`landlock.rs`。

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | 103 個 crate 的細粒度劃分，每個關注一件事；AGENTS.md 明文要求「resist adding to codex-core」；模組大小限制 500 LoC、超過 800 LoC 必須拆分 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐⭐ | 雙向 MCP + hooks + plugin crate + skills crate 形成多層擴充面；新增 LLM provider 只需新 crate 不動 core |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐⭐ | 大量 `*_tests.rs` sibling 檔；`match`/`not_match` 內建為 execpolicy unit-test；schemars 自動產 JSON schema 並有 fixture |
| 文件品質（Documentation） | ⭐⭐⭐ | 各 crate README 與 AGENTS.md 寫得清楚；但 docs/ 多為 stub 連結到 developers.openai.com（線上文件，無法離線讀） |
| 依賴管理（Dependency Management） | ⭐⭐⭐⭐⭐ | Cargo workspace 統一版本；Bazel 額外鎖 MODULE.bazel.lock；npm 端用 resolutions/overrides 鎖死關鍵 transitive deps（如 minimatch、glob） |
| 安全性（Security） | ⭐⭐⭐⭐⭐ | 三平台原生沙盒；execpolicy + sandbox 雙層；`CODEX_SANDBOX_NETWORK_DISABLED` 為不可變 contract；admin 可用 requirements.toml 強制限制 hooks |
| 效能（Performance） | ⭐⭐⭐⭐⭐ | Rust 編譯產物啟動快、無 Node runtime；ratatui 比 React/ink 渲染輕量 |

> [!tip] 值得學習的設計
> 1. **Starlark 規則引擎當作配置語言** — 既可程式化（變數、函式、列表）、又可靜態驗證（match/not_match 在 load-time 跑）；比 JSON/YAML 表達力強，比寫 Rust 簡單。
> 2. **「核心薄、衛星厚」的工程紀律** — 把 `codex-core` 當神聖小堡壘，所有新功能優先放進新 crate；用 AGENTS.md 把這條紀律寫進 contributor guide。
> 3. **Node + Rust 雙層 CLI** — Node 處理 npm 生態系與更新流，Rust 處理執行期效能與系統呼叫；最大化兩個生態系優勢。
> 4. **OS 原生沙盒** — 不用 Docker、不用 VM；直接呼叫 Seatbelt/Bubblewrap/Landlock，penalty 極低但有真正的隔離。
> 5. **雙向 MCP** — 既當 client 又能當 server，agent 之間可以 chain。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> 列出架構層面的問題或技術債（Technical Debt）。

- **103 個 crate 的學習曲線陡** — 新貢獻者要理解整體 graph 很困難；`codex-core` 雖然名為「薄核心」，但本身仍是 workspace 中最大的 crate（AGENTS.md 主動承認「has become bloated」）
- **Node + Rust 雙層複雜度** — 平台 optional dependencies 機制脆弱，常見錯誤「Missing optional dependency `@openai/codex-{platform}`」需要使用者手動 `npm install -g @openai/codex@latest` 修復
- **docs/ 是 stub** — 多數 docs 檔只是一行連結到 developers.openai.com，離線/受限網路環境無法讀到完整文件
- **execpolicy 規則撰寫門檻** — Starlark 比 JSON 強，但學習成本不為零；錯誤的規則可能讓 agent 被卡死或開太多
- **Bazel + Cargo 雙構建系統的開發成本** — 對沒接觸過 Bazel 的開發者是顯著阻礙；`just bazel-lock-update` 流程偶爾出狀況
- **Linux 沙盒在 WSL1 上直接拒絕** — 沒有降級策略，對舊環境不友善
- **session 歷史預設落地** — `~/.codex/sessions/` 累積大量檔案；需要使用者主動用 `--ephemeral` 或自行清理；privacy 風險（含 prompt 與檔案內容）
- **ChatGPT 帳號流程綁定 OpenAI** — 雖然 `model-provider` 抽象支援其他供應者，但 ChatGPT 訂閱使用者的「絲滑體驗」只給 OpenAI 自家
- **Cloud Tasks 路徑黑盒** — 把任務送到 chatgpt.com/codex 雲端執行的部分，原始碼可見但實際雲端後端行為不公開

### 🔮 改進建議（Improvement Suggestions）
1. **拆分 codex-core** — 把 `Session` / `TurnContext` / approval flow 各自獨立 crate；保留 `codex-core` 只做最薄的編排
2. **提供官方離線文件** — 至少把 developers.openai.com/codex 主要章節 mirror 到 repo `docs/` 內
3. **session 預設 ephemeral + 明確 opt-in 持久化** — privacy by default；保留 `--persist` flag
4. **execpolicy 規則撰寫工具** — 提供 `codex execpolicy lint`、`codex execpolicy explain <cmd>` 之類診斷工具
5. **WSL1 降級路徑** — 即使無法用 bubblewrap，至少可降級到「使用者每條命令手動審批」模式

## 效能基準（Benchmark）

> [!info] 資料來源
> 無官方 benchmark；以下為基於程式碼結構與第三方文章（InfoQ、Daniel Vaughan）的定性評估。

| 場景 | Codex（Rust） | Claude Code（Node） |
|------|---------------|---------------------|
| 冷啟動延遲 | 極快（單一二進位，無 runtime warmup） | 中等（Node 啟動 + 載入大量 JS） |
| TUI 渲染流暢度 | 高（ratatui 編譯型，無 GC pause） | 中（React/ink 有 reconciliation 成本） |
| 記憶體佔用 | 低 | 中至高 |
| 沙盒進入成本 | 極低（OS 原生 syscall） | 中（多走一層 Node IPC） |
| Token 使用觀察 | 已知有 [Issue #19996](https://github.com/openai/codex/issues/19996) 報告反覆啟動會吃大量 token | 一般，但長 session 也有壓力 |
| 跨平台一致性 | 高（三平台原生 sandbox 都實作） | 高，但 Windows 沙盒能力較弱 |

## 快速上手（Quick Start）

```bash
# 安裝
npm install -g @openai/codex
# 或
brew install --cask codex

# 互動式（預設 read-only sandbox）
codex

# 工作目錄可寫，仍封網路
codex --sandbox workspace-write

# 一次性執行
codex exec "Read README.md and summarize in 3 bullets"

# 接 stdin
git diff | codex exec "Review these changes"

# 跑 sandbox 測試
codex sandbox macos -- /bin/ls -la

# 把 Codex 變成 MCP server 給其他 agent 用
codex mcp-server

# 用 execpolicy 評估命令
codex execpolicy check --rules ~/.codex/rules.starlark git status

# 管理 MCP server config
codex mcp add filesystem --command npx --args -y --args @modelcontextprotocol/server-filesystem --args /path
codex mcp list
```

## 我的心得（My Takeaways）

1. **「核心薄、衛星厚」是工程紀律，不是自然發生** — Codex 的 AGENTS.md 明文寫「resist adding to codex-core」，並用 module size 限制（500/800 LoC）強制執行。這對任何成長中的 codebase 都是好範本：把核心當作神聖領域，新功能優先進入新模組，不要先改核心再說。
2. **Sandbox 是 contract，不是 feature** — `CODEX_SANDBOX_NETWORK_DISABLED_ENV_VAR` 與 `CODEX_SANDBOX` 被列為「永遠不可變更」的內部約定，連測試碼都遵守（看到這些變數就直接 early-exit）。這展示了如何把安全屬性提升為一階公民。
3. **配置語言可以是程式語言** — execpolicy 用 Starlark 而不是 JSON，把規則撰寫變成「寫程式 + 寫測試」的工作。同類設計值得在自己的專案（routing、access control）思考。
4. **「雙向 MCP」打開 agent 組合性** — 把自己也暴露為 MCP server 後，可以被其他 agent（包含 Claude Code、Cursor、Windsurf）當成工具用。這是 agent 平台未來的重要走向。
5. **Node + Rust 雙層 CLI 是值得學的模式** — npm 處理發布生態，Rust 處理執行期效能，兩端各做自己擅長的事。可以套用在任何「想用 Rust 但需要進 npm 生態」的工具。

## 待補充（Open Questions）

- **Q1：codex-core 實際多大？** 看到 AGENTS.md 提到「has become bloated」，但沒看到具體 LoC 數字。實際拆分計畫有沒有 RFC？（建議搜尋：`codex-rs codex-core refactor RFC`、`openai/codex discussions core split`）
- **Q2：執行 codex-rs 在 WSL1 上的真實行為？** README 說「rejects sandboxed shell commands」，但 `danger-full-access` 模式下是否可用？（建議搜尋：`codex wsl1 sandbox`、issue tracker）
- **Q3：Cloud Tasks（送到 chatgpt.com/codex Web）後端架構？** 原始碼可見 `cloud-tasks` crate，但雲端執行環境的隔離、保留期限、資料政策不在 repo 中。（建議搜尋：`OpenAI Codex Web cloud architecture privacy`）
- **Q4：execpolicy 與 sandbox 的雙層防線是否有 bypass？** 例如 `prefix_rule` 允許 `git`，但攻擊者 prompt LLM 用 `gi\t` 或 `eval $(echo git)` 是否能繞過？（建議搜尋：`codex execpolicy bypass security review`）
- **Q5：Windows sandbox 的能力邊界？** `windows-sandbox-rs` crate 用 RestrictedToken，但能否阻止網路、能否限制 registry？（建議搜尋：`windows RestrictedToken sandbox limitations`）
- **Q6：hooks 系統的 admin override 機制是否有審計記錄？** `allow_managed_hooks_only` 觸發時，使用者層 hooks 被忽略是否有日誌？（建議搜尋：`codex managed hooks audit log`）
- **Q7：~/.codex/memories 的格式與隱私？** 用什麼結構儲存？跨 session 自動 inject 哪些記憶？是否有清理工具？（建議搜尋：`codex memories format ~/.codex/memories`）

## 相關連結（Related）

- [[2026-05-20-CODEX-CLI-VS-CLAUDE-CODE-DEEP-COMPARISON]] — 本筆記是這篇對比文的主要證據基礎，逐維度提供 Codex 端的事實
- [[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]] — gstack 多 host 整合中將 Codex 列為 8 個 agent 之一，可看 plugin 系統如何「同時供給」Codex 與其他 host
- [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]] — Claude Code 的 Hook API 設計，可與本文 hooks crate 對照
- [[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]] — Codex 也有 `otel` crate，兩家 OTel 策略可對照
- [[2026-02-12-EVALUATING-AGENTS-MD-CONTEXT-FILES-HELPFUL-FOR-CODING-AGENTS]] — Codex 也用 `AGENTS.md` 約定，本筆記中亦多次引用

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 必記：(1) Codex 是 OpenAI 開源終端機 agent；(2) 主語言 Rust + Node dispatcher；(3) 三 sandbox mode (read-only / workspace-write / danger-full-access)；(4) execpolicy 用 Starlark；(5) 雙向 MCP（client + server） |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點 | 用自己的話：Codex 把「安全」拆成兩層 — 預先宣告的 execpolicy 規則決定「能不能執行」，OS 原生 sandbox 決定「執行時能碰什麼」。前者 config-time，後者 runtime，兩層獨立但搭配。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設 | 關鍵假設：(1) 「OS 原生沙盒比 Docker 輕」— 但這預設使用者環境裝得了 Bubblewrap/Seatbelt，且 user namespace 可用；(2) 「Starlark 規則比 JSON 表達力強」— 但對非工程師寫 config 時門檻反而高；(3) 「核心薄」— 但 codex-core 自己承認 bloated，紀律會否持續是問號 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 立即可做：(A) 在自己的 CLI 工具用「Node dispatcher + Rust binary」模式取得跨生態優勢；(B) 把「安全約定變成不可變 env var」這個模式套用到敏感子系統；(C) 把 `match`/`not_match` 內建測試的設計用到自己的 config 格式上 |
| **評估（主動）** | 判斷多個方案的優劣，進行權衡 | 比較 Codex 沙盒 vs Claude Code 對話審批：Codex 適合「規則明確、批次自動化、可預先審計」場景；對話審批適合「探索性開發、規則難以預先列舉」場景。兩者非好壞之分，是「pre-declare vs runtime-decide」的選擇 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Codex 的核心薄」這個說法，當 codex-core 自己已 bloated 時還成立嗎？薄與胖的判斷標準是什麼（LoC？依賴數？API 表面？）
- **假設**：execpolicy 假設「使用者願意預先聲明規則」，但若 LLM 每天提出新型 shell command，規則維護成本是否會壓垮使用者？
- **證據**：「Rust 重寫帶來顯著效能提升」的主張，除了 InfoQ 報導與 issue 討論，有沒有 OpenAI 官方的 benchmark 數字？
- **觀點**：站在 Claude Code 設計者立場，會如何批評 Codex 的「pre-declare 安全模型」？反過來，Codex 會如何批評 Claude Code 的「runtime approval」？
- **後果**：若 Codex 持續推進「雙向 MCP」，12 個月後 agent 生態會變得多 chain？這對 debugging 與責任歸屬有什麼挑戰？

### 方案批判三問（Critical Evaluation — 適用於程式碼或做事方法類內容）

1. **最大的風險是什麼？** — Codex 把安全決策前推到 config-time（execpolicy）。若規則寫錯、太鬆，agent 在 sandbox 內仍可造成資料污染（例如修改不該動的 repo 內檔案）；若規則寫太緊，agent 卡住不會推進。最壞情況是「規則看似嚴格，實際被字串變形繞過」（Q4），導致誤以為安全。
2. **什麼情況下會失敗？** — (a) WSL1 環境（無 user namespace，沙盒模式直接拒絕命令）；(b) 非 OpenAI provider 使用者（ChatGPT 帳號整合的絲滑體驗無法享受）；(c) 不熟 Starlark 的個人開發者（規則維護負擔重）；(d) 需要長對話、頻繁工具呼叫的場景（Issue #19996 報告 token 使用過大）
3. **有沒有更好的替代方案？** — (a) 若主要在容器內跑 agent，Claude Code 的對話審批 + Bash allowlist 更輕量；(b) 若需要團隊集中管理規則，Codex 的 `requirements.toml` + admin override 比 Claude Code 完整；(c) 若需要極致簡單 CLI（不要 sandbox、不要規則），輕量工具如 aichat 更合適。**選 Codex 的時機**：你需要 OS 級隔離、能寫規則、且願意投資沙盒測試流程。

## References

- [Codex GitHub Repo (openai/codex)](https://github.com/openai/codex)
- [Codex CLI Splash & Quickstart README](https://github.com/openai/codex/blob/main/README.md)
- [codex-rs/README.md — Rust 實作說明](https://github.com/openai/codex/blob/main/codex-rs/README.md)
- [codex-rs/AGENTS.md — 工程紀律](https://github.com/openai/codex/blob/main/codex-rs/AGENTS.md)
- [execpolicy README — Starlark 規則語言](https://github.com/openai/codex/blob/main/codex-rs/execpolicy/README.md)
- [linux-sandbox README — Bubblewrap 與 Landlock 細節](https://github.com/openai/codex/blob/main/codex-rs/linux-sandbox/README.md)
- [Introducing Codex | OpenAI (2025-04-16)](https://openai.com/index/introducing-codex/)
- [Introducing upgrades to Codex | OpenAI](https://openai.com/index/introducing-upgrades-to-codex/)
- [Codex Changelog](https://developers.openai.com/codex/changelog)
- [The codex-rs Architecture: How OpenAI Rewrote Codex CLI in Rust — Daniel Vaughan (2026-03-28)](https://codex.danielvaughan.com/2026/03/28/codex-rs-rust-rewrite-architecture/)
- [Another Rust Rewrite: OpenAI's Codex CLI Goes Native — InfoQ (2025-06)](https://www.infoq.com/news/2025/06/codex-cli-rust-native-rewrite/)
- [Codex CLI is Going Native · Discussion #1174](https://github.com/openai/codex/discussions/1174)
- [Unlocking the Codex harness: how we built the App Server — OpenAI](https://openai.com/index/unlocking-the-codex-harness/)
- [Codex token usage issue #19996](https://github.com/openai/codex/issues/19996)
