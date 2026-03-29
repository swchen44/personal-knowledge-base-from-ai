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

## 相關連結（Related）

- [[CLAUDE-CODE-HOOKS]] — 這套系統的底層機制，hooks 的原理和設定方式
- [[AI-AGENT-MEMORY]] — 更廣義的 AI 記憶架構，對比 vector DB vs markdown 方式
- [[SECOND-BRAIN-WITH-AI-TOOLS]] — Ali Abdaal 談 AI 工具建立第二大腦，理念相通
- [[OBSIDIAN-POWER-TIPS]] — Obsidian 知識圖譜技巧，可整合 Memory Engine 的日記輸出
- [[GITHUB-BACKUP-STRATEGY]] — 跨裝置同步的 GitHub repo 設定策略
- [[AI-CONTEXT-WINDOW]] — Context 壓縮問題是這套工具存在的根本原因

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
