---
title: "Claude Memory Engine — Claude Code 的記憶學習系統"
date: 2026-03-16
category: AI
tags:
  - ai/claude-code
  - ai/memory
  - tools/hooks
  - productivity/learning-system
  - tools/claude
source: "https://github.com/HelloRuru/claude-memory-engine"
source_type: tool
author: "HelloRuru"
status: notes
links:
  - "[[CLAUDE-CODE-HOOKS]]"
  - "[[AI-AGENT-MEMORY]]"
  - "[[SECOND-BRAIN-WITH-AI-TOOLS]]"
  - "[[OBSIDIAN-POWER-TIPS]]"
---

## 摘要（Summary）

Claude Memory Engine 是一套用 hooks + markdown 打造的 Claude Code 記憶學習系統，完全不需要資料庫或外部 API。它解決了 Claude Code 最根本的問題：每次新對話都從零開始，之前花時間修的 bug、設定的偏好、踩過的坑全部消失。更特別的是，這個系統不只讓 Claude「記得」，而是讓它像學生一樣從錯誤中學習成長。

## 關鍵洞察（Key Insights）

- 記憶不等於學習 — 大多數記憶工具只是讓 AI 記住資訊，但這套系統透過「學生循環（Student Loop）」讓 Claude 分析自己的錯誤、找出規律、不再犯同樣的錯，見 [[STUDENT-LOOP-LEARNING]]
- 三重保存點 — 不依賴單一時機：每 20 則訊息自動存、context 壓縮前存（最可靠）、對話結束後存，確保重要資訊不遺失
- Smart Context 自動切換 — 根據工作目錄（CWD）自動載入對應的 project 記憶，切換專案不需手動設定，見 [[AI-CONTEXT-WINDOW]]
- 全透明設計 — 所有邏輯都是 `.js` 和 `.md` 檔案，沒有黑盒，想改什麼直接改
- 跨裝置同步 — 透過私人 GitHub repo 備份，換電腦跑 `/recover` 就還原所有記憶，見 [[GITHUB-BACKUP-STRATEGY]]
- 雙語指令 — 所有 36 個指令都有英文和繁體中文版本（完全對等，用哪個都行）

## 詳細內容（Details）

### 核心架構：Student Loop（學生循環）

> [!note] 什麼是 Student Loop
> 把 Claude 當成期末考前猛 K 書的學生：每堂課做筆記（自動）、整理筆記找規律（手動 /reflect）、建立錯題本（/analyze）、考前複習（自動掃描錯題）。每個循環都比上一個聰明一點點。

**自動執行（每次對話）：**

- `session-start` hook → 載入上次摘要 + 當前 project 記憶 + 待接手任務
- 每 20 則訊息 → `mid-session-checkpoint` 存一個 checkpoint
- Context 壓縮前 → `pre-compact` 存快照 + 踩坑偵測（Pitfall Detection）+ 備份
- 對話結束 → `session-end` 存最終摘要（盡力觸發，非保證）

**手動執行（按需要）：**

| 指令 | 中文 | 功能 |
|------|------|------|
| `/reflect` | `/反思` | 回顧 7 天筆記，找出重複錯誤，升級成永久規則 |
| `/analyze` | `/分析` | 你改了 AI 的輸出後立刻跑，比對兩版差異，建立錯題本 |
| `/correct` | `/訂正` | 隨時查看並複習錯題本，任務前自動掃描 |
| `/save` | `/存記憶` | 手動儲存重要資訊到長期記憶 |
| `/handoff` | `/交接` | 多視窗協作時，把當前進度傳給另一個 Claude 視窗 |
| `/backup` | `/備份` | 推送記憶到 GitHub |
| `/recover` | `/想起來` | 從 GitHub 拉回所有記憶（換電腦或災難恢復） |

### 以檔案為主角的視角（File-Centric View）

> [!note] 換個角度看系統
> 前面以 hook 為主角說明「誰做了什麼」。這個視角反過來，以**檔案**為主角，回答三個問題：誰寫它、什麼時候寫、誰讀它。

> [!note] 標記說明
> 表格中 JS 檔案欄位會以 `← 【Hook 名稱】` 標記「誰 call 這個 JS」。Hook 由 Claude Code 平台根據 `settings.json` 設定自動觸發；slash command 則是 Claude 在對話中直接執行（非 hook）。

| 檔案 | 內容與用途 | 誰寫它（+ 觸發來源） | 什麼時候寫 | 誰讀它（+ 觸發來源） | 什麼時候讀 |
|------|----------|--------|-----------|--------|-----------|
| `sessions/*-session.md` | 對話結束後的摘要快照：主要請求、使用工具、修改檔案。用途：讓下次對話知道上次做了什麼 | `session-end.js` ← **【SessionEnd hook】** | 對話正常結束時 | `session-start.js` ← **【SessionStart hook】** | 下次開新對話時（自動） |
| `sessions/*-compact.md` | Context 壓縮前保存的完整快照，比 session 摘要更詳盡。用途：確保壓縮後仍能還原重要上下文 | `pre-compact.js` ← **【PreCompact hook】** | Context 壓縮前 | `session-start.js` ← **【SessionStart hook】** | 下次開新對話時（自動） |
| `sessions/*-checkpoint.md` | 長對話中途自動保存的進度快照，每 20 則觸發。用途：防止長對話脈絡因壓縮而遺失 | `mid-session-checkpoint.js` ← **【UserPromptSubmit hook】** | 每 20 則訊息 | `session-start.js` ← **【SessionStart hook】** | 下次開新對話時（自動） |
| `sessions/project-index.md` | 各專案所有 session 的列表索引（日期、標題）。用途：讓 `/reflect` 快速了解跨 session 的活動歷史 | `session-end.js` ← **【SessionEnd】**、`pre-compact.js` ← **【PreCompact】** | 每次存摘要時更新 | `/reflect` 指令（slash command，Claude 在對話中執行） | 手動執行 `/reflect` 時 |
| `sessions/reflect-*.md` | 手動 `/reflect` 後生成的學習反思筆記。用途：讓 session-start 計算距上次反思的天數，適時提醒 | `/reflect` 指令（slash command） | 手動執行 `/reflect` 後 | `session-start.js` ← **【SessionStart hook】** | 每次開新對話時（用於計算幾天沒跑） |
| `sessions/debug.log` | 每個 hook 執行時的 debug 輸出（時間戳、動作、錯誤）。用途：除錯時追查 hook 是否正確執行 | `shared-utils.js`（`debugLog`）← **【被所有 hook 腳本 `require()` 呼叫，非直接 hook 觸發】** | 每個 hook 執行時 | 人工查閱 | 除錯時手動查看 |
| `sessions/.checkpoint-state.json` | 目前訊息計數器狀態（已發送幾則訊息）。用途：讓 mid-session-checkpoint 判斷是否達到存檔門檻 | `mid-session-checkpoint.js` ← **【UserPromptSubmit hook】** | 每則訊息發送時 | `mid-session-checkpoint.js` ← **【UserPromptSubmit hook】** | 每則訊息發送時（讀計數器） |
| `sessions/.handoff-read.json` | 已讀交接檔案的 ID 清單。用途：避免同一交接在多次對話中重複彈出提示 | `session-start.js` ← **【SessionStart hook】** | 偵測到新交接時 | `session-start.js` ← **【SessionStart hook】** | 每次開新對話時（避免重複顯示同一交接） |
| `skills/learned/auto-pitfall-{date}.md` | 本次對話中偵測到的踩坑模式（如工具重試 ≥5 次、使用者糾正）。用途：session-start 自動載入警示，避免下次重蹈覆轍 | `pre-compact.js` ← **【PreCompact hook】** | 偵測到踩坑時（條件觸發） | `session-start.js` ← **【SessionStart hook】** | 每次開新對話時（3 天內的自動載入） |
| `skills/learned/writing-review-list.md` | 使用者親自改正過的錯誤合集（翻錯題本）。用途：任務開始前複習，避免再犯同類錯誤 | `/analyze` 指令（slash command） | 手動執行 `/analyze` 後 | `/correct` 指令（slash command） | 手動執行 `/correct` 時，或任務開始前複習 |
| `memory/MEMORY.md` | 所有記憶 topic files 的索引目錄（hub），每行一條指標。用途：被 memory-sync 每則訊息 hash 比對，決定是否重注入 | `/save` 指令（slash command） | 手動 `/save` 後 | `memory-sync.js` ← **【UserPromptSubmit hook】**、`/reload`（slash command） | 每則訊息（hash 比較）、手動 `/reload` 時 |
| `memory/*.md`（topic files） | 主題式記憶內容：用戶偏好、專案細節、回饋、參考資源等（spokes）。用途：Smart Context 依相關性自動選擇注入 | `/save` 指令（slash command） | 手動 `/save` 後 | `session-start.js` ← **【SessionStart hook】**、`/reload`（slash command）、`memory-sync.js` ← **【UserPromptSubmit hook】** | 開新對話（Smart Context）、手動 `/reload`、每則訊息（mtime 偵測） |
| `memory/todo-status.md` | 跨 session 的待辦事項清單（未完成 / 已完成）。用途：對話開頭自動顯示未完成項目，不讓任務遺忘 | `/todo` 指令（slash command） | 手動 `/todo` 更新後 | `session-start.js` ← **【SessionStart hook】**、`/reload`（slash command） | 開新對話時（統計未完成項目）、手動 `/reload` 時 |
| `memory/handoff-{date}.md` | 明確要交棒給下個 session 的任務說明與背景。用途：下次對話自動偵測並顯示，確保任務連續性 | `/handoff` 指令（slash command） | 手動 `/handoff` 後 | `session-start.js` ← **【SessionStart hook】**、`memory-sync.js` ← **【UserPromptSubmit hook】** | 下次開新對話時 & 每則訊息（新交接偵測） |
| `scripts/hooks/.memory-sync-state.json` | 上次同步時各記憶檔的 hash 與 mtime 快照。用途：每則訊息快速比對，只在有變更時才重注入記憶 | `memory-sync.js` ← **【UserPromptSubmit hook】** | 每則訊息發送時 | `memory-sync.js` ← **【UserPromptSubmit hook】** | 每則訊息發送時（比對上次 hash/mtime） |

> [!tip] 最重要的三個檔案
> - `sessions/*-compact.md`：最可靠的快照，pre-compact 寫、session-start 讀，是整個閉迴路的核心
> - `memory/MEMORY.md`：記憶的索引中樞，被 memory-sync 即時監控
> - `skills/learned/auto-pitfall-*.md`：自動學習的成果，session-start 每次都會掃描

---

### Hooks 資料流完整分析

> [!important] 這是理解整套系統的關鍵圖表。每個 hook 的資料流（Input → 讀什麼 → 寫什麼 → Output）。

#### `session-start.js` — SessionStart

**觸發：** 每次開新對話
**Input：** CWD（當前目錄）+ 環境變數

```
讀取：
  ~/.claude/sessions/*-session/compact/checkpoint.md  → 載入上次摘要
  ~/.claude/projects/{project}/memory/*.md             → Smart Context
  ~/.claude/projects/{project}/memory/todo-status.md  → 待辦摘要
  ~/.claude/projects/{project}/memory/handoff-*.md    → 交接偵測
  ~/.claude/sessions/.handoff-read.json               → 已讀狀態
  ~/.claude/skills/learned/auto-pitfall-*.md          → 踩坑警示
  ~/.claude/sessions/reflect-*.md                     → /reflect 提醒

寫入：
  ~/.claude/sessions/.handoff-read.json               → 標記交接已讀

Output → stdout：注入 Claude context（對話開頭你看到的提示）
```

#### `session-end.js` — SessionEnd

**觸發：** 對話結束時（盡力觸發）
**Input：** stdin JSON（`transcript_path`, `cwd`）

```
讀取：
  {transcript_path}.jsonl → 解析整段對話（user messages, tools, files）

寫入：
  ~/.claude/sessions/{date}-{id}-session.md  → 對話摘要（最多保留 30 份）
  ~/.claude/sessions/project-index.md        → 專案 session 索引
  ~/.claude/sessions/debug.log               → debug 紀錄

Output → stdout：無（不注入 context）
```

#### `pre-compact.js` — PreCompact

**觸發：** Context 壓縮前（比 SessionEnd 更可靠）
**Input：** stdin JSON（`transcript_path`, `trigger`, `session_id`, `cwd`）

```
讀取：
  {transcript_path}.jsonl → 解析對話內容

寫入：
  ~/.claude/sessions/{date}-{id}-compact.md           → 壓縮前快照
  ~/.claude/sessions/project-index.md                 → 專案索引
  ~/.claude/skills/learned/auto-pitfall-{date}.md     → 踩坑紀錄（條件觸發）

Output → stdout：無
```

**踩坑偵測邏輯（Pitfall Detection Logic）：**

```
Input: toolCalls（每個工具呼叫 + 是否有 error）
         userMessages（是否包含「不對」「wrong」等字）

偵測三種訊號：
  1. 同工具 + 同目標 ≥ 5 次 → retry pitfall
  2. 工具失敗後又成功     → error-then-fix pitfall
  3. 使用者說「不對/wrong」 → user-correction pitfall

Output: ~/.claude/skills/learned/auto-pitfall-{date}.md
```

#### `mid-session-checkpoint.js` — UserPromptSubmit

**觸發：** 每則使用者訊息發送時
**Input：** stdin JSON（`session_id`, `prompt`）

```
讀取：
  ~/.claude/sessions/.checkpoint-state.json → 訊息計數器

寫入：
  ~/.claude/sessions/.checkpoint-state.json           → 更新計數器
  ~/.claude/sessions/{date}-{id}-checkpoint.md        → 每 20 則存一次

Output → stdout：無
```

#### `memory-sync.js` — UserPromptSubmit

**觸發：** 每則使用者訊息發送時（與 checkpoint 同時觸發）
**Input：** stdin JSON（`session_id`, `prompt`, `cwd`）

```
讀取：
  ~/.claude/projects/{project}/memory/MEMORY.md       → 比較 hash 偵測變更
  ~/.claude/projects/{project}/memory/*.md            → 偵測 mtime 變更
  ~/.claude/projects/{project}/memory/handoff-*.md    → 偵測新交接
  ~/.claude/scripts/hooks/.memory-sync-state.json     → 上次的 hash/mtime 狀態

寫入：
  ~/.claude/scripts/hooks/.memory-sync-state.json     → 更新狀態

Output → stdout：若偵測到其他 session 改了記憶，注入變更摘要
```

#### `pre-push-check.js` — PreToolUse[Bash]

**觸發：** Claude 執行任何 Bash 指令前（`settings.json` 設定 `matcher: "Bash"`）
**Input：** stdin JSON（`tool_name: "Bash"`, `tool_input.command`：即將執行的指令字串）

```
讀取：
  stdin → 解析 tool_input.command
  git diff --cached --name-only（execSync，僅在偵測到 git push 時才執行）

寫入：
  無（不修改任何檔案）

Output → stdout：
  若 command 含 git push       → 輸出 push 前提醒 + staged 敏感檔案警告
  若 command 含 --force / -f  → 輸出 force push 警告
  否則                         → 無輸出（透明放行）

Exit：永遠 process.exit(0)，不阻擋操作
```

#### `write-guard.js` — PreToolUse[Write]

**觸發：** Claude 使用 Write 工具寫入任何檔案前（`settings.json` 設定 `matcher: "Write"`）
**Input：** stdin JSON（`tool_name: "Write"`, `tool_input.file_path`：即將寫入的絕對路徑）

```
讀取：
  stdin → 解析 tool_input.file_path

寫入：
  無（不修改任何檔案）

Output → stdout：
  若路徑匹配 PROTECTED_PATTERNS（.env, credentials, .secret, password）
    且不在 ALLOWED_PATHS 白名單 → 輸出敏感檔案提醒 + 原因說明
  若路徑匹配 WARN_PATTERNS（README.md, CHANGELOG.md, TODO.md）
    → 輸出「Is this needed?」提醒
  否則 → 無輸出（透明放行）

Exit：永遠 process.exit(0)，不阻擋操作
```

### Hooks 系統架構圖（Architecture Diagram）

```
┌──────────────────────────────────────────────────────────────┐
│                     Claude Code Process                       │
│                                                              │
│  ┌──────────┐   ┌────────────┐   ┌──────────────────────┐   │
│  │  Session  │   │   User     │   │     Tool Use         │   │
│  │  Events   │   │  Prompt    │   │  (Bash / Write)      │   │
│  └─────┬─────┘   └─────┬──────┘   └──────────┬───────────┘   │
│        │               │                     │               │
│  ┌─────▼─────┐   ┌─────▼──────┐   ┌──────────▼───────────┐   │
│  │session-   │   │memory-sync │   │ pre-push-check.js    │   │
│  │start.js   │   │.js         │   │ write-guard.js       │   │
│  │session-   │   │mid-session-│   └──────────────────────┘   │
│  │end.js     │   │checkpoint  │                              │
│  │pre-compact│   │.js         │                              │
│  │.js        │   └────────────┘                              │
│  └─────┬─────┘                                               │
└────────┼────────────────────────────────────────────────────-┘
         │ Node.js child process (hooks run outside Claude)
         ▼
┌──────────────────────────────────────────────────────────────┐
│                     File System (~/.claude/)                  │
│                                                              │
│  sessions/         skills/learned/     projects/{proj}/      │
│  ├─ *-session.md   ├─ auto-pitfall-*   ├─ MEMORY.md         │
│  ├─ *-compact.md   └─ writing-review-  ├─ memory/           │
│  ├─ *-checkpoint      list.md          │  ├─ *.md            │
│  ├─ project-index                      │  ├─ todo-status.md  │
│  ├─ reflect-*.md   scripts/hooks/      │  └─ handoff-*.md    │
│  ├─ .checkpoint-   └─ .memory-sync-                         │
│  │  state.json        state.json                            │
│  └─ .handoff-                                               │
│     read.json                                               │
└──────────────────────────────────────────────────────────────┘
         │
         ▼ (session-start stdout → injected into Claude context)
┌──────────────────────────────────────────────────────────────┐
│                   Claude Context Window                       │
│  [上次摘要] [踩坑警示] [待辦] [Smart Context] [交接內容]        │
└──────────────────────────────────────────────────────────────┘
```

### API 層級時序圖（API-Level Sequence Diagrams）

#### 開新對話完整時序

```
 用戶           Claude Code      session-start.js    File System
  │                  │                  │                 │
  │──開啟新對話──────►│                  │                 │
  │                  │──SessionStart───►│                 │
  │                  │                  │──讀 sessions/*──►│
  │                  │                  │◄────────────────│
  │                  │                  │──讀 memory/*.md──►│
  │                  │                  │◄────────────────│
  │                  │                  │──讀 auto-pitfall►│
  │                  │                  │◄────────────────│
  │                  │                  │──寫 .handoff-───►│
  │                  │                  │   read.json     │
  │                  │◄──stdout（摘要）──│                 │
  │◄──context注入────│                  │                 │
  │  （上次摘要+踩坑） │                  │                 │
```

#### 訊息發送時序（每則訊息）

```
 用戶      Claude Code   memory-sync.js  mid-session-cp.js   File System
  │             │               │               │                │
  │──送出訊息──►│               │               │                │
  │             │─UserPrompt───►│               │                │
  │             │               │──讀 MEMORY.md─►│               │
  │             │               │◄──────────────│               │
  │             │               │──比較 hash────►│               │
  │             │               │  （有變化才輸出）│               │
  │             │               │──寫 .sync-────►│               │
  │             │               │   state.json  │               │
  │             │─UserPrompt───►│               │               │
  │             │               │               │──讀 .checkpoint►│
  │             │               │               │◄──────────────│
  │             │               │               │──計數 +1───────►│
  │             │               │               │（第 20 則才寫檔）│
  │◄──Claude回應│               │               │                │
```

#### Context 壓縮時序

```
 Claude Code    pre-compact.js    shared-utils.js    File System
     │                │                 │                │
     │─PreCompact────►│                 │                │
     │  （transcript） │                 │                │
     │                │──parseTranscript►│               │
     │                │                 │──讀 .jsonl────►│
     │                │                 │◄──────────────│
     │                │◄────────────────│               │
     │                │──detectPitfalls─►│               │
     │                │◄────────────────│               │
     │                │──savePitfalls───►│               │
     │                │                 │──寫 auto-──────►│
     │                │                 │   pitfall-*.md │
     │                │──寫 *-compact.md►│               │
     │                │──updateIndex────►│               │
     │                │                 │──寫 project────►│
     │                │                 │   -index.md   │
     │◄───────────────│                 │               │
  （壓縮繼續執行）       │                 │               │
```

### 各 Hook 主要函式流程圖（Function Flowcharts）

#### `session-start.js` 函式流程

```
main()
  │
  ├─► findPendingHandoffs()
  │       │── 讀 memory/handoff-*.md
  │       │── 讀 .handoff-read.json
  │       └── 寫 .handoff-read.json（標記已讀）
  │
  ├─► findLatestSession()
  │       └── 掃描 sessions/*.md，取 7 天內最新
  │
  ├─► loadSmartContext()
  │       └── 比對 CWD 與 PROJECT_CONTEXT，載入對應記憶
  │
  ├─► loadTodoSummary()
  │       └── 讀 memory/todo-status.md，統計未完成項目
  │
  ├─► findRecentMemoryChanges()
  │       └── 掃描 memory/*.md，篩選 24h 內修改的
  │
  ├─► findRecentPitfalls()
  │       └── 掃描 skills/learned/auto-pitfall-*.md，取 3 天內最新
  │
  ├─► checkRecurringPitfalls()
  │       └── 統計各 pitfall type 跨天出現次數，≥3 次就警告
  │
  ├─► checkReflectReminder()
  │       └── 掃描 sessions/reflect-*.md，>7 天沒跑就提醒
  │
  └─► stdout.write（拼接所有輸出，注入 Claude context）
```

#### `pre-compact.js` 函式流程

```
main(inputData)
  │
  ├─► JSON.parse(inputData)
  │       └── 取得 trigger, transcript_path, session_id, cwd
  │
  ├─► parseTranscript(transcriptPath)  ← shared-utils
  │       │── 讀 .jsonl
  │       │── 解析 userMessages（過濾系統注入）
  │       │── 解析 toolsUsed
  │       │── 解析 filesModified
  │       └── 解析 toolCalls（含 hasError flag）
  │
  ├─► detectProjectTag(userMessages, cwd, filesModified)
  │       └── 從 projectPatterns / CWD / 訊息 推斷專案名
  │
  ├─► 寫 sessions/{date}-{id}-compact.md
  │
  ├─► updateProjectIndex(...)  ← shared-utils
  │       └── 讀寫 sessions/project-index.md
  │
  ├─► detectPitfalls(parsed)  ← shared-utils
  │       │── retry 訊號（同工具同目標 ≥5 次）
  │       │── error-then-fix 訊號
  │       └── user-correction 訊號（訊息含「不對/wrong」等）
  │
  ├─► savePitfalls(pitfalls)  ← shared-utils（若 pitfalls > 0）
  │       └── 寫 skills/learned/auto-pitfall-{date}.md
  │
  └─► autoBackup()  ← shared-utils
          └── 執行 memory-backup.sh（若存在）
```

#### `memory-sync.js` 函式流程

```
main()
  │
  ├─► getProjectMemoryDir()
  │       └── 從 CWD 計算 project slug → 找 memory/ 目錄
  │
  ├─► 讀 memory/MEMORY.md
  │       └── 計算 hash（base64 前 32 字元）
  │
  ├─► loadState() → 讀 .memory-sync-state.json
  │
  ├─► 比較 hash
  │       │── 相同 → 跳過
  │       └── 不同 →
  │               ├─ getChangedLines（找新增行）
  │               ├─ 掃描 memory/*.md mtime
  │               ├─ saveState() → 寫 .memory-sync-state.json
  │               └─ stdout.write（注入變更摘要）
  │
  └─► checkHandoffs(memDir, state)
          │── 掃描 memory/handoff-*.md
          │── 比對 known_handoffs
          └── 若有新交接 → stdout.write（注入交接內容）
```

#### `mid-session-checkpoint.js` 函式流程

```
main(inputData)
  │
  ├─► JSON.parse → 取得 session_id, prompt
  │
  ├─► loadState() → 讀 .checkpoint-state.json
  │
  ├─► 累積 messages[]
  │
  ├─► 計算 messagesSinceCheckpoint
  │       │── < 20 → 只更新計數，saveState()
  │       └── ≥ 20 → saveCheckpoint()
  │                     │── miniAnalyze(messages)
  │                     │       │── ACTION_MAP 統計動作詞
  │                     │       └── PROJECT_KEYWORDS 統計專案名
  │                     └── 寫 sessions/{date}-{id}-checkpoint.md
  │
  └─► 清理 >3 天的舊 session 計數記錄
```

#### `pre-push-check.js` 函式流程

```
時序圖：

 Claude Code      pre-push-check.js      git（execSync）
      │                   │                    │
      │─PreToolUse(Bash)──►│                    │
      │ command="git push" │                    │
      │                   │ [/git\s+push/ 匹配？]
      │                   │──git diff --cached──►│
      │                   │◄──（staged 檔名列表）─│
      │                   │ [掃描敏感模式]        │
      │◄── stdout（提醒） ─│                    │
      │                   │ process.exit(0)      │
      │ [繼續執行 git push]│                    │

若 command 為其他 Bash 指令：
      │─PreToolUse(Bash)──►│
      │                   │ [不匹配 git push]
      │                   │ process.exit(0)  ← 無輸出，透明放行
      │ [繼續執行]         │
```

```
流程圖：

main(stdin)
  │
  ├─► JSON.parse(stdin) → 取得 command
  │
  ├─► /git\s+push/ 匹配？
  │     │
  │     ├─ YES ─►
  │     │   stdout.write("About to push! 請確認：...")
  │     │   execSync('git diff --cached --name-only')
  │     │   │
  │     │   └─► 掃描 sensitivePatterns（.env, credentials, .secret, password, .pem, .key）
  │     │           │
  │     │           ├─ 發現敏感檔案 ──► stdout.write("[WARNING] Sensitive files: ...")
  │     │           └─ 無敏感檔案 ──► 繼續
  │     │
  │     └─ NO ──► skip
  │
  ├─► /git push.*--force|git push -f/ 匹配？
  │     ├─ YES ──► stdout.write("[WARNING] Force push detected!")
  │     └─ NO ───► skip
  │
  └─► process.exit(0)  ← 永遠允許，不阻擋操作
```

#### `write-guard.js` 函式流程

```
時序圖：

 Claude Code       write-guard.js
      │                  │
      │─PreToolUse(Write)─►│
      │ file_path="/path/to/.env"
      │                  │ basename() → ".env"
      │                  │ 比對 ALLOWED_PATHS（白名單）→ 不在白名單
      │                  │ 掃描 PROTECTED_PATTERNS → ".env" 匹配
      │◄── stdout（敏感檔案提醒）──│
      │                  │ 繼續掃描 WARN_PATTERNS → 不匹配
      │                  │ process.exit(0)
      │ [繼續執行 Write]  │

若寫入路徑為 README.md：
      │─PreToolUse(Write)─►│
      │                  │ 掃描 PROTECTED_PATTERNS → 不匹配
      │                  │ 掃描 WARN_PATTERNS → README.md 匹配
      │◄── stdout（"Is this needed?"）──│
      │                  │ process.exit(0)
      │ [繼續執行 Write]  │

若寫入路徑無特殊標記（一般 .md 或 .js）：
      │─PreToolUse(Write)─►│
      │                  │ 所有 pattern 都不匹配
      │                  │ process.exit(0)  ← 無輸出，透明放行
      │ [繼續執行 Write]  │
```

```
流程圖：

main(stdin)
  │
  ├─► JSON.parse(stdin) → 取得 file_path
  │
  ├─► basename(file_path) → filename
  │   normalize path（統一 / 分隔符）
  │
  ├─► 比對 ALLOWED_PATHS 白名單（~/.cloudflare/ 等）
  │     └─ 在白名單 ──► 跳過所有檢查，直接 exit(0)
  │
  ├─► 掃描 PROTECTED_PATTERNS（4 個）：
  │   .env$ / credentials / .secret / password
  │     │
  │     ├─ 匹配 AND 不在白名單
  │     │   └─► stdout.write("Writing {file} — {reason}")
  │     └─ 不匹配 ──► skip
  │
  ├─► 掃描 WARN_PATTERNS（3 個）：
  │   README.md / CHANGELOG.md / TODO.md
  │     │
  │     ├─ 匹配 ──► stdout.write("Creating {file} -- Is this needed?")
  │     └─ 不匹配 ──► skip
  │
  └─► process.exit(0)  ← 永遠允許，不阻擋操作

[重要設計原則]
  兩個 hook 都是純 advisory（告知性）：
  - 輸出訊息讓 Claude 知道風險
  - 但從不 process.exit(1) 阻擋操作
  - 決定要不要繼續，由 Claude 判斷
```

---

### 指令讀寫對照（Commands Read/Write Map）

| 指令 | 讀 | 寫 |
|------|----|----|
| `/save` | `memory/*.md`（查重複） | `memory/{topic}.md`、`MEMORY.md` |
| `/reload` | `MEMORY.md`、`memory/*.md`、`todo-status.md` | 無 |
| `/backup` | `memory/*.md`（本機） | GitHub（`gh api PUT`） |
| `/sync` | `memory/*.md` + GitHub | `memory/*.md`（本機）+ GitHub |
| `/analyze` | transcript（使用者的修改） | `skills/learned/writing-review-list.md` |
| `/correct` | `skills/learned/writing-review-list.md` | 無 |
| `/reflect` | `sessions/project-index.md`、`memory/*.md` | `memory/*.md`（精簡）、`sessions/reflect-*.md` |
| `/handoff` | `memory/*.md` | `memory/handoff-{date}.md` |
| `/todo` | `memory/todo-status.md` | `memory/todo-status.md` |
| `/recover` | GitHub（`gh api GET`） | `memory/*.md`、`MEMORY.md`（本機） |

---

### 手動指令讀寫詳解（Slash Commands — Read/Write Detail）

> [!note] Slash Command vs Hook 的差異
> Slash commands（`/save`、`/reflect` 等）是 Claude 在**對話內**直接執行的邏輯，不會觸發 hooks，也不走 `settings.json`。Hook 才是由 Claude Code 平台根據事件自動呼叫 Node.js 腳本。

#### `/save` — 存記憶

**讀：** `memory/*.md`（查重複）、`memory/MEMORY.md`（確認索引）
**寫：** `memory/{topic}.md`（新增 or 更新）、`memory/MEMORY.md`（更新索引）

```
時序圖：

 用戶              Claude（對話中）          File System
  │                      │                       │
  │── /save "內容" ──────►│                       │
  │                      │──讀 memory/*.md ──────►│
  │                      │◄──（所有 topic 檔）────│
  │                      │──讀 MEMORY.md ─────────►│
  │                      │◄──（索引）─────────────│
  │                      │                       │
  │                      │ [查重複，決定寫哪個 topic]
  │                      │                       │
  │                      │──寫 memory/{topic}.md ─►│
  │                      │──寫 MEMORY.md ──────────►│
  │◄── "已儲存到 {file}" ─│                       │
```

```
流程圖：

用戶輸入 /save "要記的內容"
  │
  ▼
掃描 memory/*.md
  │
  ├─ 找到相關 topic 檔 ──► 更新該檔案的對應段落
  │                              │
  └─ 找不到匹配主題 ──────► 建立新的 memory/{topic}.md
                                  │
                                  ▼
                         更新 memory/MEMORY.md 索引
                                  │
                                  ▼
                    回報：已存到 {filename}, section {section}
```

---

#### `/reflect` — 反思

**讀：** `sessions/project-index.md`、`sessions/*-session.md`、`sessions/*-compact.md`、`memory/*.md`、`skills/learned/writing-review-list.md`
**寫：** `memory/*.md`（精簡過時條目）、`sessions/reflect-{date}.md`

```
時序圖：

 用戶              Claude（對話中）          File System
  │                      │                       │
  │── /reflect ──────────►│                       │
  │                      │──讀 sessions/project-index.md ──►│
  │                      │◄──（7 天內的 session 列表）───────│
  │                      │──讀 sessions/*-session.md ───────►│
  │                      │◄──（對話摘要）────────────────────│
  │                      │──讀 sessions/*-compact.md ───────►│
  │                      │◄──（壓縮前快照）──────────────────│
  │                      │──讀 memory/*.md ──────────────────►│
  │                      │◄──（現有記憶）────────────────────│
  │                      │──讀 writing-review-list.md ───────►│
  │                      │◄──（錯題本）──────────────────────│
  │                      │                       │
  │                      │ [分析：找重複錯誤、過時記憶]
  │                      │                       │
  │                      │──寫 memory/*.md（精簡）──────────►│
  │                      │──寫 sessions/reflect-{date}.md ──►│
  │◄── 反思報告 ─────────│                       │
```

```
流程圖：

用戶輸入 /reflect
  │
  ▼
讀 sessions/project-index.md → 取最近 7 天的 session 列表
  │
  ▼
逐一讀入 *-session.md、*-compact.md
  │
  ▼
讀 memory/*.md（找過時 or 重複的條目）
  │
  ▼
讀 writing-review-list.md（找跨天重複的錯誤）
  │
  ▼
分析三件事：
  ├─ 錯誤重複 ≥3 次 ──► 升級為 CLAUDE.md or memory 永久規則
  ├─ 記憶條目已過時 ──► 更新 or 刪除 memory/*.md 對應段落
  └─ 新洞察值得保存 ──► 新增到 memory/*.md
  │
  ▼
寫 sessions/reflect-{date}.md（反思結論存檔）
  │
  ▼
輸出：反思摘要 + 已升級的規則清單
```

---

#### `/analyze` — 分析

**讀：** 當前對話的 context（Claude 直接看到的內容，不需讀檔）
**寫：** `skills/learned/writing-review-list.md`

```
時序圖：

 用戶（修改完 AI 輸出後）  Claude（對話中）          File System
  │                            │                       │
  │── /analyze ────────────────►│                       │
  │                            │ [從 context 中找「用戶修改了哪些 AI 輸出」]
  │                            │ [比對：AI 原始版 vs 用戶修改版]
  │                            │ [提取錯誤模式]
  │                            │                       │
  │                            │──寫 writing-review-list.md ─────────►│
  │◄── "已加入錯題本：{錯誤類型}" │                       │
```

```
流程圖：

用戶輸入 /analyze（剛改完 AI 輸出）
  │
  ▼
掃描當前對話 context：
  ├─ 找出 AI 生成的內容片段
  └─ 找出用戶修改後的版本
  │
  ▼
比對差異，提取錯誤模式（格式？用詞？邏輯？）
  │
  ▼
讀 writing-review-list.md
  │
  ├─ 已有同類錯誤 ──► 更新計數或補充細節
  └─ 新的錯誤 ──────► 新增條目
  │
  ▼
寫 skills/learned/writing-review-list.md
  │
  ▼
輸出：「已加入錯題本：{錯誤類型} — {說明}」
```

---

#### `/correct` — 訂正

**讀：** `skills/learned/writing-review-list.md`
**寫：** 無（純讀取複習，不修改檔案）

```
時序圖：

 用戶              Claude（對話中）          File System
  │                      │                       │
  │── /correct ──────────►│                       │
  │                      │──讀 writing-review-list.md ─────►│
  │                      │◄──（所有錯誤條目）─────────────────│
  │                      │                       │
  │                      │ [閱讀並記入短期記憶，本次對話全程避免]
  │                      │                       │
  │◄── 錯題本摘要（本次要注意的 N 個重點）──────│               │
```

```
流程圖：

用戶輸入 /correct（任務開始前）
  │
  ▼
讀 skills/learned/writing-review-list.md
  │
  ▼
篩選最近 or 高頻錯誤（依優先順序排列）
  │
  ▼
輸出：「本次任務前複習 — 要避免的 {N} 個錯誤」
  │
  ▼
Claude 在本次對話全程記住這些規則（無寫入動作）
```

---

#### `/handoff` — 交接

**讀：** `memory/*.md`（整理當前工作背景）
**寫：** `memory/handoff-{date}.md`

```
時序圖：

 用戶（要切換視窗）  Claude（對話中）          File System
  │                      │                       │
  │── /handoff ──────────►│                       │
  │                      │──讀 memory/*.md ────────►│
  │                      │◄──（當前 project 記憶）──│
  │                      │                       │
  │                      │ [整合：任務 + 背景 + 下一步]
  │                      │                       │
  │                      │──寫 memory/handoff-{date}.md ──►│
  │◄── "交接檔已建立" ────│                       │

（下次開新對話）
  session-start.js ← 【SessionStart hook 自動觸發】
  讀 memory/handoff-{date}.md → 注入交接內容到 context
```

```
流程圖：

用戶輸入 /handoff
  │
  ▼
讀 memory/*.md（當前工作背景與規則）
  │
  ▼
組合交接文件：
  ├─ 當前任務狀態（做到哪、卡在哪）
  ├─ 關鍵背景資訊
  ├─ 下一步建議
  └─ 接手者需注意事項
  │
  ▼
寫 memory/handoff-{date}.md
  │
  ▼
[下次對話] session-start.js（SessionStart hook）偵測到新交接
  └─► 自動注入交接內容到 Claude context
```

---

#### `/backup` — 備份

**讀：** `memory/*.md`（本機）
**寫：** GitHub `projects/{local-path}/memory/*.md`（遠端）

```
時序圖：

 用戶  Claude（對話中）   File System（本機）    GitHub API
  │         │                   │                   │
  │─/backup►│                   │                   │
  │         │──掃描 memory/*.md─►│                   │
  │         │◄──（檔案列表）──────│                   │
  │         │                   │                   │
  │         │ [對每個檔案]        │                   │
  │         │──GET: 取得遠端 SHA ─────────────────────►│
  │         │◄──（SHA + 遠端內容）──────────────────────│
  │         │                   │                   │
  │         │ [比較：有變更才推]  │                   │
  │         │──PUT: 推送 content + SHA ───────────────►│
  │         │◄──（commit SHA）────────────────────────│
  │◄─ 備份報告（N 個更新）─│                   │
```

```
流程圖：

用戶輸入 /backup
  │
  ▼
掃描本機 memory/*.md 列表
  │
  ▼
對每個檔案（序列執行）：
  │
  ├─ GET gh api → 取 GitHub SHA
  │
  ├─ 內容相同 ──────────► 跳過
  │
  └─ 內容有差異 ──────────►
       PUT gh api（content + SHA）
       │
       ├─ 成功 ──► 記錄「已更新」
       └─ 失敗 ──► 報錯，最多重試 3 次
  │
  ▼
輸出：備份完成，{N} 個已更新 / {M} 個無變更

[路徑規範]
  本機：~/.claude/projects/-Users-{name}-{proj}/memory/foo.md
  遠端：projects/-Users-{name}-{proj}/memory/foo.md
```

---

#### `/recover` — 想起來

**讀：** GitHub `projects/{local-path}/memory/*.md`（遠端）
**寫：** `memory/*.md`、`memory/MEMORY.md`（本機）

```
時序圖：

 用戶（換電腦 / 記憶損毀）  Claude（對話中）    GitHub API      本機 File System
  │                           │                   │                  │
  │── /recover ───────────────►│                   │                  │
  │                           │──GET: 列出遠端所有 .md ─────────────►│
  │                           │◄──（檔案清單）──────────────────────│
  │                           │                   │                  │
  │                           │ [對每個檔案]        │                  │
  │                           │──GET: 下載 Base64 content ──────────►│
  │                           │◄──（內容）──────────────────────────│
  │                           │                   │                  │
  │                           │──寫 memory/{topic}.md ──────────────────────►│
  │                           │──寫 memory/MEMORY.md ───────────────────────►│
  │◄── "已還原 N 個記憶檔案" ──│                   │                  │
```

```
流程圖：

用戶輸入 /recover（換電腦 or 本機記憶損毀）
  │
  ▼
GET gh api → 列出 GitHub 上 projects/{path}/memory/ 的所有 .md 檔
  │
  ▼
對每個遠端檔案：
  GET gh api → 下載 Base64 content → decode
  │
  ├─ 本機已存在且相同 ──► 跳過
  └─ 不存在 or 有差異 ──► 寫入本機 memory/{filename}.md
  │
  ▼
重建 memory/MEMORY.md 索引
  │
  ▼
輸出：「已還原 {N} 個記憶檔案：{列表}」
  │
  ▼
建議：執行 /reload 把記憶載入本次對話
```

---

### 系統架構圖（System Architecture）

```
對話中的 JSONL transcript
    │
    ├──► session-end ──────────► sessions/*-session.md
    │                                    │
    └──► pre-compact ──────────► sessions/*-compact.md
              │                          │
              └──────────────► skills/learned/auto-pitfall-*.md
                                         │
                                         ▼
                               session-start（下次對話）
                               注入 context → Claude 知道昨天發生什麼

你手動打 /save
    ↓
memory/*.md + MEMORY.md
    │
    ├──► memory-sync（每則訊息偵測）→ 注入 context（若有跨 session 變更）
    │
    └──► /backup ──────────────► GitHub: projects/{local-path}/memory/*.md
                                          ↑
                                 /recover ─┘（換電腦時拉回）
```

### GitHub 備份路徑規範

> [!important] 備份路徑格式
> 本機路徑 `~/.claude/projects/{project-folder}/` 對應 GitHub 路徑 `projects/{project-folder}/`。
> 永遠使用 `projects/` 前綴，不可直接用專案名稱作為根目錄。

```
本機：~/.claude/projects/-Users-swchen-tw-git-my-project/memory/foo.md
GitHub：projects/-Users-swchen-tw-git-my-project/memory/foo.md
```

資料夾命名規則：把路徑的 `/` 換成 `-`（由 Claude Code 自動決定）。

### 記憶系統目錄結構（Memory File Structure）

Hub-and-Spoke 模型：

```
~/.claude/projects/{project-id}/
  MEMORY.md               ← hub（索引，最多 200 行）
  memory/
    user_profile.md       ← spoke（使用者資訊）
    feedback_*.md         ← spoke（行為規則）
    project_*.md          ← spoke（專案資訊）
    reference_*.md        ← spoke（外部資源位置）
    todo-status.md        ← spoke（跨對話待辦）
    handoff-{date}.md     ← spoke（交接給另一個 session）

~/.claude/sessions/
  {date}-{id}-session.md      ← 對話結束後的摘要
  {date}-{id}-compact.md      ← context 壓縮前的快照
  {date}-{id}-checkpoint.md   ← 每 20 則的中繼摘要
  project-index.md            ← 專案 session 索引
  reflect-{date}.md           ← /reflect 產出的結論
  .checkpoint-state.json      ← 訊息計數狀態
  .handoff-read.json          ← 已讀交接狀態
  debug.log                   ← hook 執行日誌

~/.claude/skills/learned/
  auto-pitfall-{date}.md      ← 踩坑紀錄（pre-compact 自動寫入）
  writing-review-list.md      ← 錯題本（/analyze 手動觸發寫入）
  memory-engine/              ← skill 定義本體
```

### Token 成本

> [!warning] Token 注意事項
> 每次對話開始會多消耗 200–500 tokens（載入上次摘要 + project 記憶 + 踩坑警示）。其他 hooks 幾乎不消耗額外 tokens（處理在背景 Node.js 進程，不進 context）。

### Correction Cycle（錯誤修正循環）

```
你發現 AI 輸出有問題
    ↓ 手動修正
/analyze（立刻跑）
    ↓ 比對改前改後
writing-review-list.md（錯題本）
    ↓ 下次任務開始前 /correct 自動掃描
Claude 知道昨天犯過什麼錯
    ↓ 同樣的錯犯 3 次以上
升級成 CLAUDE.md 或 memory 中的永久規則
```

### 安裝方式（5 步）

```bash
# 1. 建立 GitHub 備份 repo
gh repo create claude-memory --private
git clone https://github.com/YOUR_USERNAME/claude-memory.git ~/.claude/claude-memory

# 2. 複製 hooks、commands、skill
cp hooks/*.js ~/.claude/scripts/hooks/
cp commands/*.md ~/.claude/commands/
cp -r skill/ ~/.claude/skills/learned/memory-engine/

# 3. 建立必要目錄
mkdir -p ~/.claude/sessions/diary ~/.claude/scripts/hooks

# 4. 設定 settings.json — 加入 hooks 設定（見下方 JSON）

# 5. 重啟 Claude Code — hooks 開始生效
```

`settings.json` hooks 設定範例：

```json
"hooks": {
  "SessionStart": [{ "matcher": "*", "hooks": [
    { "type": "command", "command": "node ~/.claude/scripts/hooks/session-start.js" }
  ]}],
  "SessionEnd": [{ "matcher": "*", "hooks": [
    { "type": "command", "command": "node ~/.claude/scripts/hooks/session-end.js" }
  ]}],
  "UserPromptSubmit": [{ "matcher": "*", "hooks": [
    { "type": "command", "command": "node ~/.claude/scripts/hooks/memory-sync.js" },
    { "type": "command", "command": "node ~/.claude/scripts/hooks/mid-session-checkpoint.js" }
  ]}],
  "PreCompact": [{ "matcher": "*", "hooks": [
    { "type": "command", "command": "node ~/.claude/scripts/hooks/pre-compact.js" }
  ]}],
  "PreToolUse": [
    { "matcher": "Bash", "hooks": [{ "type": "command", "command": "node ~/.claude/scripts/hooks/pre-push-check.js" }]},
    { "matcher": "Write", "hooks": [{ "type": "command", "command": "node ~/.claude/scripts/hooks/write-guard.js" }]}
  ]
}
```

**需求：** Claude Code（有 hooks 支援）、Node.js 18+、Zero dependencies

## 我的心得（My Takeaways）

- **立刻要裝：** 這解決了每次開新對話都要重新解釋 context 的問題，完全透明可控
- **`/analyze` 的習慣很重要：** 修完 AI 的輸出後立刻跑，才能讓錯題本真的有用
- **`pre-compact` 才是真正的安全網：** 不要依賴 `session-end`（視窗關掉不一定觸發）
- **GitHub 備份路徑有規範：** 必須用 `projects/{本機路徑}/` 格式，不可直接放根目錄
- **指令全部有中英文版：** `/save` = `/存記憶`，`/backup` = `/備份`，用哪個都行
- **每週一次 `/reflect`：** 不做的話錯題本只是累積，不會升級成永久知識

## 待補充（Open Questions）

- `session-end` hook 無法保證觸發（需視窗正常關閉）——在強制關閉或系統崩潰的情境下，`pre-compact` 作為安全網的觸發率實際有多高？有無量測數據或已知失效場景？（建議搜尋：`Claude Code hooks session-end reliability pre-compact fallback`）
- 踩坑偵測的三個訊號（retry ≥5 次、error-then-fix、user-correction）是否有誤報（False Positive）問題？例如合理的重試（網路不穩定）是否會被誤判為踩坑？（建議搜尋：`agent pitfall detection false positive retry signal`）
- `memory-sync.js` 每則訊息都做 hash 比對，在記憶檔案很多（100+ topic files）時，這個即時掃描的效能影響有多大？是否有批次處理或差分更新的優化空間？（建議搜尋：`Claude Code memory sync performance optimization hash comparison`）
- Student Loop（學生循環）與向量資料庫（Vector DB）記憶方案的適用邊界在哪？對於需要語意檢索（semantic search）而非精確比對的記憶場景，markdown 方案的局限性是什麼？（建議搜尋：`AI agent memory markdown vs vector database semantic retrieval`）
- 多人協作場景中，這套以個人為單位的記憶系統如何與團隊共享知識整合？多個工程師用同一個 repo 時會有哪些衝突或競態問題？（建議搜尋：`Claude Code memory multi-user team shared knowledge conflict`）

## 相關連結（Related）

- [[CLAUDE-CODE-HOOKS]] — 這套系統的底層機制，hooks 的原理和設定方式
- [[AI-AGENT-MEMORY]] — 更廣義的 AI 記憶架構，對比 vector DB vs markdown 方式
- [[SECOND-BRAIN-WITH-AI-TOOLS]] — Ali Abdaal 談 AI 工具建立第二大腦，理念相通
- [[OBSIDIAN-POWER-TIPS]] — Obsidian 知識圖譜技巧，可整合 Memory Engine 的日記輸出
- [[GITHUB-BACKUP-STRATEGY]] — 跨裝置同步的 GitHub repo 設定策略
- [[AI-CONTEXT-WINDOW]] — Context 壓縮問題是這套工具存在的根本原因
- [[2025-08-31-CLAUDE-MEM-CODE-ANALYSIS]] — claude-mem 的程式碼深度分析，同為 Claude Code 記憶插件但以不同方式解決相同問題
- [[2026-03-07-CLAUDE-MEMORY-ENGINE]] — 同一專案 Claude Memory Engine 的另一份程式碼分析，從 hooks + markdown 架構切入

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 7 個 hooks 名稱與觸發時機；36 個指令（18 EN + 18 ZH）；三種踩坑偵測訊號（retry / error-then-fix / user-correction） |
| **理解（半被動）** | 解釋概念的含義及關聯 | hooks 是閉迴路：JSONL → session-end/pre-compact → sessions/*.md → session-start 注入 → Claude 知道昨天發生什麼。MEMORY.md 是 hub，topic files 是 spokes |
| **分析（主動）** | 檢驗論點、拆解流程 | `session-end` 不保證觸發（需視窗正常關閉），因此 `pre-compact` 才是真正的安全網。踩坑偵測依賴「5 次 retry」門檻，若工具在不同 session 重試則偵測不到 |
| **應用（主動）** | 將知識套用情境 | 1. 每次修改 AI 輸出後立刻打 `/analyze`，建立錯題本；2. 每週打一次 `/reflect` 整理踩坑，升級永久規則 |
| **評估（主動）** | 判斷多個方案的優劣 | 相較 claude.ai 內建 Memory：此工具勝在透明可控、分專案、可備份、有學習機制；劣在需自行安裝維護、只支援 Claude Code（不支援 claude.ai 網頁版） |

### 分析型追問（Socratic Follow-up）

- **澄清：** `pre-compact` 和 `session-end` 都在存摘要，若兩個都觸發了，哪一份會被 `session-start` 優先讀取？
- **假設：** 這套系統假設「記憶文件都是人類可讀的 markdown」，若 MEMORY.md 超過 200 行，系統會如何降級？
- **證據：** `/analyze` 能真的讓下次對話更好嗎？還是錯題本只是增加了 token 消耗卻沒有實際改善行為？
- **觀點：** 若 Anthropic 官方推出原生的 Claude Code 記憶功能，這套工具的哪些部分仍然有價值？
- **後果：** 如果每個專案都積累大量 memory 檔案但從不做 `/reflect` 整理，12 個月後 session-start 的 token 消耗和 context 品質會如何演變？

### 方案批判三問（Critical Evaluation）

> [!warning] 方案批判

1. **最大的風險是什麼？**
   記憶內容過時卻仍被注入 context，導致 Claude 依據錯誤假設作業。例如：project 已改架構，但舊的 `project_setup.md` 仍說使用舊版設計。需定期 `/reflect` 清除過時記憶。

2. **什麼情況下會失敗？**
   - Node.js 未安裝或版本過舊（需 18+）
   - `settings.json` hooks 設定格式錯誤（JSON 語法錯誤導致整個 hooks 不生效）
   - `session-end` 在視窗強制關閉時不觸發（依賴 `pre-compact` 作為備援）
   - GitHub token 過期時 `/backup` 和 `/recover` 失效

3. **有沒有更好的替代方案？**
   - **claude.ai 內建 Memory**：設定簡單、零維護，但只能存個人偏好、不分專案、不可備份、無學習機制
   - **CLAUDE.md**：每個專案放一個，永久載入，適合不變的規則；但不適合動態的工作進度或跨 session 摘要
   - **MCP Memory Server（如 mem0）**：支援語意搜尋（Semantic Search），更強的記憶能力，但需要外部服務、有隱私考量

## References

- [GitHub Repo](https://github.com/HelloRuru/claude-memory-engine)
- [原始 README](https://github.com/HelloRuru/claude-memory-engine/blob/main/README.zh-TW.md)
