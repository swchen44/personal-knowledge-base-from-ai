---
title: "Superpowers 實戰指南：13 個 Skill 怎麼觸發、怎麼用、能解決什麼問題"
date: 2026-04-08
category: AI
tags:
  - ai/agents
  - ai/claude-code
  - ai/skills
  - productivity/workflow
  - engineering/tdd
source: "https://juejin.cn/post/7625943321220005903"
source_type: article
author: "卡卡（掘金）"
status: notes
links:
  - "[[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]]"
  - "[[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]]"
  - "[[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]]"
  - "[[SUPERPOWERS-OBRA]]"
  - "[[2026-05-09-STOP-RANDOM-SKILL-4-CORE-GROUPS-FOR-AGENT-PRODUCTIVITY]]"
github_stars: 194412
github_language: Shell
github_repo: "https://github.com/obra/superpowers"
github_license: "MIT"
---

## 摘要（Summary）

[Superpowers](https://github.com/obra/superpowers)（作者 Jesse Vincent / obra）是 2026 年 Claude Code 社群最火的 skills 框架——**194K stars / 17K forks**，已上架 Anthropic 官方 plugin marketplace，並支援 Claude Code、Codex CLI/App、Cursor、Gemini CLI、OpenCode、Factory Droid、GitHub Copilot CLI 七大 harness。本筆記以掘金作者**卡卡**的 2026-04-08 實戰文章為主體，配合 repo README 與官方資訊，完整拆解 **13 個內建 skill** 的觸發方式（自動 vs 手動）、執行畫面、能解決的問題。

Superpowers 的核心理念可以用一行話總結：

> [!important] 核心哲學
> **把「我說需求 → AI 寫代碼」變成「我說需求 → 先理解 → 再計畫 → 再執行 → 再驗證 → 再收尾」**——每個 skill 就是一個關卡（gate），AI 走到這就停下來等你確認，**不會讓 AI 一路跑到底再回頭看**。

四階段哲學：**設計（Design）→ 計畫（Plan）→ 測試（Test）→ 品質（Quality）**。**強制執行，不是可選的。**

---

## 為什麼存在？— 解決「AI 寫代碼快、返工更頻繁」的根本病

卡卡在文章開頭把痛點講得很直白：

> [!quote] 文章核心觀察
> 「最新的模型確實聰明……但是不可否認的是，大多數人用 AI 編程的方式，其實跟幾年前沒啥區別——就是『提需求，等結果』。
>
> 比如我們說一句『幫我加個登入功能』，AI 給我們一段代碼。我們看看覺得還行，複製貼上進去。跑一下，報錯了……來回折騰好幾輪，最後發現 AI 根本沒理解我們真正想要什麼。
>
> 其實問題不在 AI 不夠強，而是我們跟 AI 的合作方式從一開始就有問題。」

**問題本質**：流程缺失（process gap）。需求要理清楚、方案要設計、測試要先寫、寫完還要驗證——這些環節人類自己做時還算自覺，現在指望 AI 但 AI 不會主動走完。

> [!tip] Superpowers 的價值定位
> 「Skills 和 MCP 的價值，本質上不是讓 AI 變聰明，而是讓 AI **變靠譜**。聰明是模型的事，靠譜是流程的事。」

---

## Repo 基本資料

| 項目 | 內容 |
|------|------|
| **作者** | Jesse Vincent (`obra`) |
| **GitHub** | https://github.com/obra/superpowers |
| **Stars** | 194,412（2026-05-17 截）|
| **Forks** | 17,286 |
| **License** | MIT |
| **建立日** | 2025-10-09 |
| **語言** | Shell |
| **官方安裝** | `/plugin install superpowers@claude-plugins-official` （Anthropic 官方 plugin marketplace）|

> [!info] 七大 harness 全支援
> Claude Code / Codex CLI / Codex App / Factory Droid / Gemini CLI / OpenCode / Cursor / GitHub Copilot CLI — **每個 harness 都要分開安裝**，因為 plugin 機制不同。

---

## 13 個 Skill 全景：自動觸發 vs 手動觸發

> [!important] 二分法
> Superpowers 把 13 個 skill 明確分成兩類：
> - **自動觸發（Auto）**：AI 偵測到特定情境就自己 invoke，**人類不用打指令**
> - **手動觸發（Manual）**：需明確輸入 `/superpowers:xxx` 指令

### 自動觸發（4 個）

| Skill | 觸發時機 |
|------|---------|
| **brainstorming** | 偵測到要做新功能開發 → 停下來問清楚需求 |
| **systematic-debugging** | 偵測到 bug 或測試失敗 → 進入系統化除錯 |
| **test-driven-development** | 開始實作功能時 → 強制要求先寫測試 |
| **verification-before-completion** | AI 想說「完成了」時 → 強制跑驗證、要證據 |

### 手動觸發（9 個）

| Skill | 觸發指令 | 用途 |
|------|---------|------|
| **writing-plans** | `/superpowers:writing-plans` | 把任務拆成清晰的執行步驟 |
| **subagent-driven-development** | `/superpowers:subagent-driven-development` | 用子代理並行執行計畫（**推薦**） |
| **executing-plans** | `/superpowers:executing-plans` | 在獨立 session 順序執行計畫 |
| **using-git-worktrees** | `/superpowers:using-git-worktrees` | 建立隔離開發環境 |
| **dispatching-parallel-agents** | `/superpowers:dispatching-parallel-agents` | 2+ 個獨立任務並行 |
| **requesting-code-review** | `/superpowers:requesting-code-review` | 請求 code review |
| **receiving-code-review** | （收到 review 時）| 處理 review 反饋 |
| **finishing-a-development-branch** | （工作完成時自動 / 手動）| 4 選 1 決定如何收尾 |
| **writing-skills** | `/superpowers:writing-skills` | 自己寫新 skill |

---

## 核心 6 流程：日常開發主線

> [!tip] 卡卡的建議
> 13 個 skill 不用全記，**核心流程記住這 6 個就夠日常使用了**：
> ```
> brainstorming → writing-plans → subagent-driven-development（或 executing-plans）
>                                 → verification-before-completion → finishing-a-development-branch
> ```

### 完整流程 ASCII 圖

```
                              ┌─────────────────────────┐
[使用者說：「想做 X 功能」] ──►│  brainstorming（自動） │ 一問一答，搜索專案脈絡
                              │  → 產出設計方案         │ 存到 docs/superpowers/specs/
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │  writing-plans          │ 拆任務→拆步驟
                              │  → 產出實施計畫文件     │ 存到 docs/superpowers/plans/
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │ 選擇執行方式：           │
                              │  ① subagent-driven-     │ 推薦：當前 session 並行
                              │    development          │   多個 sub-agent 並行任務
                              │  ② executing-plans      │ 備選：獨立 session 順序
                              └────────────┬────────────┘
                                           │ 實作過程中
                                           ▼
                              ┌─────────────────────────┐
                              │  test-driven-           │ 強制先寫測試再實作
                              │  development（自動）    │
                              └────────────┬────────────┘
                                           │ AI 想說「完成」時
                                           ▼
                              ┌─────────────────────────┐
                              │  verification-before-   │ 強制跑 test/lint/build
                              │  completion（自動）     │ → 拿出證據才能說完成
                              └────────────┬────────────┘
                                           │ 全綠後
                                           ▼
                              ┌─────────────────────────┐
                              │  finishing-a-           │ 4 選 1：
                              │  development-branch     │  - 直接合併 main
                              │                         │  - 開 PR
                              │                         │  - 保留分支（手動處理）
                              │                         │  - 其他
                              └─────────────────────────┘
                              [整個流程任一步出 bug]
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │  systematic-debugging   │ 系統化定位
                              │  （自動觸發）           │ 不准 AI 亂改
                              └─────────────────────────┘
```

---

## 6 個核心 Skill 詳解（卡卡實戰記錄）

### 1. brainstorming — 先搞清楚要做什麼

**觸發**：自動。AI 偵測到「想做新功能」就停下，提示：

```
Skill(superpowers:brainstorming) Successfully loaded skill
```

**特色**：
- AI 先搜索專案相關邏輯了解 context，再開始提問
- **一步一步問**，不是一次甩一堆問題
- 問完後說「我已收集足夠信息，現在讓我提出設計方案」
- 給出設計方案（架構思路、關鍵模組、資料流程）
- 確認後寫入 `docs/superpowers/specs/`

> [!warning] 重要產出：specs 文件
> 設計方案不只是「現在用」，是給 **以後的自己 + 接手的人** 看的，記錄「當初為什麼這麼設計」。

### 2. writing-plans — 把任務拆成清晰的步驟

**觸發**：brainstorming 後自動銜接，或手動 `/superpowers:writing-plans`

**標準目錄結構**（Superpowers 強制）：

```
docs/superpowers/
├── specs/       ← brainstorming 產出（設計文件）
└── plans/       ← writing-plans 產出（執行計畫）
    └── YYYY-MM-DD-xxx.md
```

**產出後的選擇提示**：

```
計畫已保存到 docs/superpowers/plans/YYYY-MM-DD-xxx.md

推薦執行方式：
1. 使用 superpowers:subagent-driven-development（在當前會話中執行，推薦）
2. 使用 superpowers:executing-plans（在獨立會話中執行）
```

| 執行方式 | 適用 |
|---------|------|
| `subagent-driven-development` | 小專案 / 想即時監控 |
| `executing-plans` | 大專案 / 需隔離環境 / 手動控制每一步 |

### 3. subagent-driven-development — 並行執行計畫（推薦）

選定後 AI 自動建立**多個子代理（sub-agents）**，**每個負責一部分任務、並行工作**，不必等上一個做完才下一個。

> [!tip] 為什麼推薦這個而不是傳統 executing-plans
> - **並行 = 速度快**
> - **每一步都會回報**，發現問題立刻修正，不用等到最後

### 4. verification-before-completion — 「說完成不代表真完成」

> [!important] 整個 Superpowers 最具突破性的設計
> 不是「使用者請求驗證」時觸發，是 **AI 想要說『完成』時自動介入**——AI 沒法繞過去。

**核心原則：證據優先於聲明（Evidence over Assertion）**

| 聲稱 | ❌ 不能說 | ✅ 必須做 |
|------|----------|----------|
| 測試通過 | 「測試應該通過」 | 跑測試看到 0 failures |
| Lint 通過 | 「lint 應該沒問題」 | 跑 lint 看到 0 errors |
| Bug 修復了 | 「應該修好了」 | 跑原來失敗的測試確認通過 |
| 構建成功 | 「應該能 build」 | 實際跑 build/compile |

**全面驗證對照表**（卡卡整理）：

| 聲稱的內容 | 前端驗證指令 | 後端驗證指令 |
|----------|-----------|-----------|
| 測試通過 | `npm test` | `pytest` / `go test ./...` / `cargo test` |
| Lint 通過 | `npm lint` | `flake8` / `golangci-lint` / `cargo clippy` |
| 構建成功 | `npm build` | `cargo build` / `go build` / `mvn compile` |

### 5. systematic-debugging — Bug 別瞎改

**觸發**：自動。偵測到報錯、測試失敗、構建失敗就介入。

**核心邏輯**：強制先定位（root cause）再修復，**不准 AI 看到報錯就猜原因亂改**。

### 6. finishing-a-development-branch — 工作做完了怎麼收尾

**觸發**：subagent-driven-development / executing-plans 完成後自動，或手動。

**AI 給 4 個選項**：
1. 直接合併到 main
2. 開 PR
3. 保留分支，我自己處理（跳過自動收尾）
4. 其他

---

## 其他 7 個輔助 Skill

| Skill | 用途 | 何時用 |
|------|------|------|
| **test-driven-development** | 實作中強制先寫測試 | 開始實作功能或修 bug |
| **using-git-worktrees** | 隔離開發環境 | 同時開發多個功能不想互相干擾 |
| **dispatching-parallel-agents** | 多個獨立任務並行 | 有 2+ 任務可同時做 |
| **requesting-code-review** | 完成後請 review | 想讓 AI 或別人審查 |
| **receiving-code-review** | 處理 review 反饋 | 收到反饋別直接改，先理解 |
| **writing-skills** | 寫新 skill | 自己想做新 skill |
| **executing-plans** | 順序執行計畫 | 大專案或需隔離 |

---

## 沒有 vs 有 Superpowers 對照表（卡卡原文）

| 維度 | 沒有 Superpowers | 有 Superpowers |
|------|-----------------|---------------|
| **需求處理** | 直接寫代碼，理解偏差高 | 先 `brainstorming` 問清楚 |
| **實施方式** | 想到哪寫到哪 | 按 `writing-plans` 步驟走 |
| **測試策略** | 寫完補測試，覆蓋率低 | TDD 先寫測試再實作 |
| **Bug 處理** | 看到報錯就改，改了再說 | `systematic-debugging` 先定位再修 |
| **完成驗證** | AI 說完成就算完成 | `verification-before-completion` 強制驗證 |
| **代碼審查** | 憑自己判斷 | `requesting-code-review` 有審查流程 |
| **工作隔離** | 同一分支混著改 | `using-git-worktrees` 隔離環境 |
| **多任務** | 一個一個串行 | `dispatching-parallel-agents` 並行 |

---

## 三方對照：Superpowers vs Matt Pocock skills vs GStack

> [!important] 這是本筆記最有價值的章節
> 同樣是 AI coding 工作流框架，三套主流方案的設計哲學差異巨大。看下方表格更容易選對工具。

| 維度 | **Superpowers（Jesse Vincent / obra）** | **Matt Pocock skills** | **GStack（Garry Tan）** |
|------|----------------------------------------|----------------------|------------------------|
| **作者背景** | 開源開發者、長期 dev tools 領域 | 全職 AI 教師、TypeScript 佈道者 | YC 總裁、13 年沒寫 code 的回鍋極客 |
| **Repo Stars** | **194K** ⭐（最高） | 86K ⭐ | 不公開（個人累積） |
| **核心隱喻** | **Skills 就是 Superpowers**（給 agent 超能力） | **日班 / 夜班分工**（人退 AI 進） | **時間億萬富翁**（Tokenmaxxing 買時間） |
| **觸發機制** | **自動 + 手動雙軌**（4 自動 / 9 手動），最強制 | 主要手動 `/skill-name`，自動性弱 | 手動 `/office hours` `/CEO review` 等斜槓指令 |
| **核心 skill 數** | 13 個（6 個核心 + 7 個輔助） | 28 個（含已停用，每天用 5 個） | 23 個專家角色 |
| **強制力** | **最強**（verification-before-completion 阻止 AI 自我聲稱完成） | 中（依賴使用者主動 invoke） | 弱（依賴使用者按斜槓指令） |
| **測試哲學** | **強制 TDD**（自動觸發）+ verification 強制證據 | **嚴格 vertical TDD**（一 test 對一 impl，禁 horizontal） | **80–90% 覆蓋夠**（100% 太冗餘） |
| **目錄結構** | **強制** `docs/superpowers/specs/` + `docs/superpowers/plans/` | 鬆散，依 skill 而定 | 鬆散，個人風格 |
| **計畫產物** | **強制檔案化**（specs.md + plans.md） | PRD 用 issue tracker；issue 完就刪（避免 doc rot） | CEO Plan（meta-prompt）+ Office Hour 對話 |
| **Token 觀** | 未明確表態（中性） | **Memento 模式**（節省、clear context） | **Tokenmaxxing**（不計成本、Boil the Ocean） |
| **多 harness 支援** | **7 個**（Claude Code/Codex/Cursor/Gemini/OpenCode/Factory Droid/Copilot） | 主要 Claude Code | 主要 Claude Code + Codex |
| **典型 demo** | 「廣告回傳功能」（卡卡實戰） | Cadence 課程平台遊戲化 | Garry's List（Posterous 第三次重構） |
| **金句** | 「Skills 不是讓 AI 變聰明，是讓 AI **變靠譜**」 | 「不要優化 PRD，**QA 才是決勝點**」 | 「物理代碼行數毫無意義，**邏輯代碼密度**才是」 |

### 設計取向比較（圖示）

```
                  強制 / 紀律 high
                        │
                        │
                  Superpowers ★   ←── verification 不准 AI 自我聲稱完成
                        │           4 個自動 skill 把關全流程
                        │
                        │
                        │
        Matt Pocock ●   │   ● GStack
                        │
                        │
                  鬆散 / 自由 high
        ←─────────────────────────►
       人類驅動                 AI 驅動
       （/grill-me              （AI AFK，CEO Plan
        每步等對齊）             一次 review 多步）
```

### 該選哪一個？

| 情境 | 推薦 |
|------|------|
| **新手、單人、想最少思考就上手** | Superpowers（4 自動 skill 把關，AI 沒法偷懶） |
| **重視深度對齊、大專案** | Matt Pocock（grill-me 深度問答） |
| **個人 hacker、追速度、有預算** | GStack（Tokenmaxxing 不計成本） |
| **企業團隊 / 多 harness 混用** | Superpowers（7 harness 全支援 + 強制流程） |
| **教學 / 訓練新人 AI workflow** | Superpowers（流程最清晰、文件最齊全） |
| **嚴謹品質要求（醫療 / 金融）** | Matt Pocock TDD + Superpowers verification 雙保險 |
| **創業 demo / hackathon** | GStack（80% 覆蓋夠用） |
| **想自己拼湊 / 客製化** | Matt Pocock（短而精的 skill 風格易改） |

### 三套可以同時用嗎？

**可以，但要分情境**：
- **新功能開發**：Superpowers brainstorming → writing-plans → subagent-driven-development（最強制）
- **複雜架構決策**：套 Matt Pocock 的 `/grill-me` 在 brainstorming 階段做更深訪談
- **個人 side project / hackathon**：直接 GStack 跑 CEO Plan 10×思考
- **整個流程的「最後一關」**：永遠用 Superpowers 的 `verification-before-completion`（這個機制最強）

→ 更詳細的 Matt vs Garry 對照見 [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]] 的「對比視角」章節。

---

## 安裝流程（多 harness）

```bash
# Claude Code — Anthropic 官方 plugin marketplace
/plugin install superpowers@claude-plugins-official

# Claude Code — Superpowers 自家 marketplace
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace

# Codex CLI
/plugins        # 在搜尋介面打 superpowers
# 然後選 Install Plugin

# Cursor
/add-plugin superpowers

# Gemini CLI
gemini extensions install https://github.com/obra/superpowers
gemini extensions update superpowers

# Factory Droid
droid plugin marketplace add https://github.com/obra/superpowers
droid plugin install superpowers@superpowers

# OpenCode
# 對 OpenCode 說：
# "Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md"

# GitHub Copilot CLI
copilot plugin marketplace add obra/superpowers-marketplace
copilot plugin install superpowers
```

> [!warning] 多 harness 必須分別安裝
> Plugin 機制不通用，每個 harness 都要重複安裝一次。

---

## 我的心得（My Takeaways）

1. **「自動觸發」是 Superpowers 比 Matt Pocock skills 強的關鍵**——前者 4 個 skill 自動 invoke、不依賴人類記得打指令；後者要使用者每次主動 `/grill-me`。對「想要懶人 workflow」的人 Superpowers 顯然更友善。
2. **`verification-before-completion` 機制應該移植到所有自己寫的 skill**——這是治「AI 自我聲稱完成」的特效藥。我下次寫 KB ingestion skill 可以加類似機制：每次說「我完成了」前自動跑檢查（檔案存在、commit 成功、cross-link 已回填）。
3. **`docs/superpowers/specs/` + `docs/superpowers/plans/` 強制目錄結構是個好設計**——Matt Pocock 不強制目錄，結果使用者各做各的；Garry Tan 直接不做目錄。強制目錄結構讓「後來人能找到」這件事可預期。
4. **三方對照後我會建議**：新手從 Superpowers 起手（最強制 + 多 harness）；資深 dev 看品味選 Matt（精緻）或 Garry（速度）；對於我自己的 KB 場景，**verification-before-completion 機制最值得 steal**。
5. **194K stars vs 86K stars 的差距告訴我們**：「強制流程 + 多 harness 支援」的網絡效應比「個人風格優雅」更能征服群眾。
6. **卡卡這篇文章的價值不在介紹 Superpowers 本身**（README 也能看到），而在於**畫面感**——每個 skill 觸發後 AI 會說什麼、用戶會看到什麼提示，這種「使用感」比官方文件的概念敘述有用得多。
7. **「specs 文件不是給當下看的」這個觀點呼應 Matt Pocock 的「doc rot」憂慮**——但兩人結論相反：Matt 主張完成後刪除 PRD（避免誤導），Jesse 主張保留 specs（給接手人）。**Superpowers 設計上更同情接手人，Matt 設計上更同情未來 AI**。值得自己思考立場。

---

## 待補充（Open Questions）

1. **Superpowers 的 4 個自動 skill 在 Codex / Cursor / Gemini CLI 上是否同樣可靠**？各 harness 對「detect new feature development」「detect bug」「detect AI claiming completion」的能力可能差很多。建議搜尋：`superpowers cross-harness consistency`
2. **verification-before-completion 怎麼**「**強制**」**AI 不能繞過去**？是用 hook、stop 機制、還是 prompt 工程？源碼追蹤值得做。建議搜尋：`obra superpowers verification implementation`、查 repo `skills/verification-before-completion/SKILL.md`
3. **`subagent-driven-development` 與 [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH|Matt Pocock 的 Sandcastle]] 並行框架有何架構差異**？是否能互相 cherry-pick？
4. **194K stars 中真實使用者比例**？這麼高的 star 數有多少是「收藏沒用」？是否有實際使用率 telemetry？建議搜尋：`superpowers active users telemetry`
5. **為什麼 Anthropic 官方推 Superpowers 進 plugin marketplace**？Anthropic 跟 Jesse Vincent 有合作關係嗎？這對 Claude Skills 官方規範會有什麼影響？建議搜尋：`anthropic superpowers official endorsement`
6. **與 KB 既有 [[SUPERPOWERS-OBRA]] 筆記**（2026-03-16）相比，194K stars 是 2 個月內漲的，這成長率怎麼解釋？「skill 框架熱潮」還是有 viral event？
7. **卡卡的「core 6 skill」推薦與 Anthropic 官方推薦的 6 個 skill 是同一組嗎**？官方有沒有不一樣的入門教學？

---

## 相關連結（Related）

- [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]] — **三方對照之一**：Matt Pocock 5 skills + 日班/夜班；該篇有與本篇的對比章節
- [[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]] — **三方對照之二**：GStack Tokenmaxxing 400× 生產力
- [[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]] — KB 中既有的 Superpowers/GSD/GStack 三框架比較，本篇深化 Superpowers 部分
- [[SUPERPOWERS-OBRA]] — KB 中 2026-03-16 的 Superpowers 概覽筆記，本篇是「13 skills 實戰版」深化補充
- [[2026-05-09-STOP-RANDOM-SKILL-4-CORE-GROUPS-FOR-AGENT-PRODUCTIVITY]] — 4 group 平台無關 skill 分類框架，Superpowers 屬「工程化開發」組
- [[2026-04-08-7-RULES-FOR-CREATING-EFFECTIVE-CLAUDE-CODE-SKILL]] — Superpowers 13 skill 都遵循這些規則，可印證「短而精」原則
- [[2026-03-23-GRILL-ME-SKILL-DEEP-DIVE]] — `brainstorming` 與 grill-me 解決同個問題（深度對齊）但實作風格不同
- [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] — Software 3.0 願景的具體實踐之一

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 13 個 skill 名稱、4 階段哲學（Design→Plan→Test→Quality）、4 自動 / 9 手動觸發二分、194K stars、`docs/superpowers/specs/` + `plans/` 強制目錄、verification 6 種聲稱對照 |
| **理解（半被動）** | 解釋概念的含義及關聯 | 4 個自動 skill 解決「人類忘記 invoke」問題；6 核心流程從 brainstorming 到 finishing 對應軟體開發完整生命週期；自動 vs 手動是「強制 vs 可選」的設計選擇 |
| **分析（主動）** | 檢驗論點、拆解假設 | 假設 1：「AI 變靠譜不是變聰明」隱含「聰明已夠用」，但 GPT-5/Claude 4.7 對複雜需求仍會誤判，模型強化仍重要；假設 2：「強制流程比自由 prompt 好」對熟手反而拖累速度；假設 3：「verification 強制不能繞過」實際上 prompt 工程可繞，需驗證源碼實作 |
| **應用（主動）** | 將知識套用情境 | 1) 在自己的 KB ingestion skill 加入「completion verification」（強制檢查檔案存在 + commit 成功 + cross-link 回填）；2) 套用 `docs/specs/` + `docs/plans/` 雙目錄結構到個人 side project；3) 把 6 核心流程映射到非編碼場景（如寫作：brainstorming → outline → draft → verify → publish） |
| **評估（主動）** | 比較替代方案 | vs Matt Pocock：Superpowers 強制度更高、多 harness 更廣、文件更齊全；Matt 更精緻、客製化空間更大。vs GStack：Superpowers 流程更嚴、目錄結構強制；GStack 更速度導向、依賴使用者自律。**Superpowers 是 baseline，Matt / GStack 是個人風格 fork** |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Skills」一詞在 Superpowers / Matt Pocock / GStack 三套框架中是同一個 Claude Code skill 概念，還是各自有調整？特別是 Superpowers 的 sub-skill（`/superpowers:xxx` 命名）與 Claude 官方 skill 規範的關係。
- **假設**：「自動觸發比手動更好」這個假設成立的前提是「AI 能準確判斷觸發時機」。若 AI 誤判（例如把 refactor 當成 new feature 觸發 brainstorming），會比手動更糟。
- **證據**：「194K stars」「最火 skills 框架」是真實使用度的證據嗎？還是流量明星效應 + Anthropic 官方推廣的結果？需要看 active install rate / 實際 invocation 統計。
- **觀點**：反對者會說「強制流程把 AI 編程變成填表，喪失 vibe coding 的速度」——這個批評對熟手有效，對新手無效。
- **後果**：若全公司強制裝 Superpowers，12 個月後：(a) 程式碼平均品質上升、(b) 開發速度可能短期下降長期回升、(c) 沒寫 specs/plans 的 PR 被擋下、(d) 但也可能養成「沒 Superpowers 就不敢寫」的依賴。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — **過度信任「自動 verify」**：verification-before-completion 是 prompt 層強制，若 AI 找到 workaround（如把測試改弱、把 lint rule 改鬆）讓驗證通過，反而出現「假合格」更難察覺。最壞情況：所有人都信任 Superpowers 把關，但實際把關被靜默繞過。
2. **什麼情況下會失敗？**
   - **舊 codebase 無 lint/test 設置** → verification 無從跑起，skill 退化成裝飾
   - **多語言 monorepo** → 預設驗證命令對不上每個子專案
   - **資深開發者 + 小修改** → 跑完整 brainstorming + writing-plans + TDD 比直接寫還慢 10 倍
   - **AI 模型偏小（Haiku、Gemini Flash）** → 自動觸發判斷不夠精準，誤觸發率高
   - **跨 harness 切換** → 每換一個 harness 都要重裝 + 適應觸發行為差異
3. **有沒有更好的替代方案？**
   - **熟手 / 小修改**：直接 Plan Mode + 自寫 prompt，不需 Superpowers
   - **GStack 風格使用者**：跑 CEO Plan + Office Hour（更輕量、更個人化）
   - **教練式深度對齊**：Matt Pocock 的 `/grill-me`（單一 skill、深度問答）
   - **混合策略**：Superpowers 當「baseline + 把關」，Matt Pocock skill 當「客製對齊」，GStack 當「速度模式」

---

## References

- [Claude Code 進階：用 Superpowers 打造靠譜的 AI 開發工作流（掘金 / 卡卡，2026-04-08）](https://juejin.cn/post/7625943321220005903)
- [obra/superpowers GitHub Repo（194K stars）](https://github.com/obra/superpowers)
- [Anthropic 官方 Claude plugin marketplace — Superpowers](https://claude.com/plugins/superpowers)
- [obra/superpowers-marketplace（Superpowers + 相關 plugins）](https://github.com/obra/superpowers-marketplace)
- 作者 Jesse Vincent（obra）的 [GitHub Sponsors 頁面](https://github.com/sponsors/obra)
