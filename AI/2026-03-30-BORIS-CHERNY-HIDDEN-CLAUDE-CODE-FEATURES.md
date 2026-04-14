---
title: "Boris Cherny：13 個你不知道的 Claude Code 隱藏功能"
date: 2026-03-30
category: AI
tags:
  - "#ai/claude-code"
  - "#tools/cli"
  - "#productivity/workflows"
source: "https://x.com/bcherny/status/2038454336355999749"
source_type: article
author: "Boris Cherny"
status: notes
links:
  - "[[CLAUDE-CODE-HOOKS]]"
  - "[[CLAUDE-CODE-GIT-WORKTREES]]"
  - "[[CLAUDE-CODE-SDK]]"
---

## 摘要（Summary）

Claude Code 創始人 Boris Cherny 在 2026-03-30 發佈的推文串（Thread），分享了 13 個 Claude Code 中常被忽略但他個人最常使用的功能，涵蓋行動裝置使用、跨裝置會話（Session）切換、自動化排程、Hooks、桌面應用整合、Git 工作樹（Worktree）等。此串獲得 2.6M 瀏覽、43K 書籤，是了解 Claude Code 進階用法的高密度資源。

## 關鍵洞察（Key Insights）

- Claude Code 有官方 iOS/Android App，可直接在手機上寫程式碼 — 參見 [[CLAUDE-CODE-MOBILE]]
- `/teleport` 與 `--teleport` 可把雲端會話（Cloud Session）無縫轉移到本機終端機繼續
- `/loop` 讓你可以把重複性工作（如程式碼審查（Code Review）、Auto-rebase）排程化，定時執行
- Hooks 讓 Claude Code 的 Agent 生命週期（Agent Lifecycle）可程式化，是強大的自動化（Automation）入口點
- `claude -w` + 工作樹（Worktree）是 Cherny 同時運行數十個 Claude 實例的核心手法
- `/batch` 可把大型變更集（Changeset）分發給幾百甚至幾千個 Agent 並行處理
- `--bare` 最高可提升 SDK 啟動速度（SDK Startup Speed）10 倍，適合 Non-interactive 使用情境

## 詳細內容（Details）

### 1/ Claude Code 有手機 App

> [!info] 官方支援行動裝置
> Claude Code 同時支援 iOS 與 Android。Cherny 表示他「大量」在 iOS App 裡寫程式碼，不需要打開筆電就能做修改。

下載方式：Claude App（iOS/Android）> 左側「Code」標籤。

---

### 2/ 跨裝置切換會話（Session Teleport）

在行動裝置、網頁、桌面 App 和終端機之間自由切換會話：

```bash
# 把雲端會話（Cloud Session）繼續到本機終端機
claude --teleport

# 或在會話中執行
/teleport

# 讓手機/網頁控制本機正在跑的會話
/remote-control
```

> [!tip] Cherny 的設定
> Cherny 本人啟用了「Enable Remote Control」，讓他可以從手機控制桌機上正在運行的 Claude。

---

### 3/ 排程執行提示詞（Run Prompts on a Schedule）

使用 `/loop` 搭配 Cron 排程工具（Cron Scheduling Tools），讓提示詞（Prompt）重複執行：

```bash
# 每 5 分鐘執行一次 /babysit
/loop 5m /babysit

# 常見用途：自動程式碼審查（Code Review）、自動 Rebase
```

> [!tip] 可執行建議
> 設定 `/loop 10m /check-tests` 讓 Claude 每 10 分鐘自動跑測試，有錯誤時自動修復。

---

### 4/ Hooks — Agent 生命週期的程式化控制點

Hooks 讓你可以在 Agent 生命週期（Agent Lifecycle）的特定時刻植入確定性邏輯（Deterministic Logic）：

**範例用法：**
- `SessionStart`：每次啟動 Claude 時動態載入上下文（Context）
- 自動審核（Audit）Agent 執行的操作
- 在特定操作前後觸發自定義腳本

> [!note] 關鍵概念
> Hooks 是把 Claude Code 從「對話工具」升級為「可程式化 Agent 框架」的關鍵入口。參見 [[CLAUDE-CODE-HOOKS]]

---

### 5/ Dispatch — 共享辦公室調度（Share Office Space）

Dispatch 是 Claude Desktop App 的安全遠端控制（Secure Remote Control）工具：

- 可使用你的 MCP、瀏覽器（Browser）等
- Cherny 每天用它在不編寫程式碼時查看 Slack、管理郵件和文件
- 即使人不在電腦前，也能讓 Claude 在電腦上執行工作

---

### 6/ Claude Code 搭配 Chrome（Beta）

```
Claude Code + Chrome DevTools Protocol
→ 測試 Web App
→ 讀取 Console Logs
→ 自動化瀏覽器操作
→ Debug（偵錯）
```

官方文件：[Use Claude Code with Chrome (beta) - Claude Code Docs](https://code.claude.com)

---

### 7/ Desktop App 自動啟動並測試 Web 伺服器

Claude Desktop App 內建讓 Claude 自動：
1. 運行你的 Web 伺服器（Web Server）
2. 在內建瀏覽器中測試它

CLI 也可以設定類似功能，但 Desktop App 開箱即用（Out of the Box）。

---

### 8/ 分支（Fork）會話

兩種 Fork 現有會話的方式：

```bash
# 方法一：在會話中執行
/branch

# 方法二：從 CLI 執行
claude --resume <session-id> --fork-session
```

> [!tip] 使用情境
> 想從某個檢查點（Checkpoint）嘗試多種不同的解決方向時，Fork 會話而不是重新開始。

---

### 9/ /btw — 不打斷 Agent 的插播提問

當 Agent 正在工作時，用 `/btw` 提出旁支問題，不會中斷主要工作流程（Workflow）：

```
/btw how do i spell daushund?
→ dachshund — German for "badger dog" (dachs = badger, hund = dog).
```

> [!note] 設計理念
> 這是 Claude Code 對「對話流程中斷」問題的解法：讓 Agent 繼續跑的同時，人類也可以插播提問。

---

### 10/ Git 工作樹（Git Worktrees）支援

> [!important] Cherny 同時運行數十個 Claude 的秘密
> "I have dozens of Claudes running at all times, and this is how I do it."

```bash
# 在新工作樹（Worktree）中啟動新會話
claude -w

# 或在會話中建立工作樹
/worktree create <branch-name>
```

Git Worktrees 讓多個 Agent 可以在同一個 Repository 的不同分支上**同時**工作，互不干擾。參見 [[CLAUDE-CODE-GIT-WORKTREES]]

---

### 11/ /batch — 大型變更集的並行分發

```
/batch
→ Claude 面試你，了解任務需求
→ 自動分發給 N 個 Worktree Agents（可達數百乃至數千個）
→ 並行完成任務
```

**最佳使用情境：**
- 大型程式碼遷移（Code Migration）
- 跨多個模組的重構（Refactoring）
- 任何可平行化（Parallelizable）的工作

---

### 12/ --bare — 最高提速 SDK 啟動 10 倍

```bash
# 預設模式（會搜尋 CLAUDE.md、設定、MCP）
claude -p "your prompt"

# Bare 模式（跳過搜尋，明確指定要載入的內容）
claude -p "your prompt" --bare
```

> [!tip] 使用時機
> 在非互動式（Non-interactive）的 SDK 使用情境（如 CI/CD、批次腳本）中，`--bare` 可大幅減少啟動延遲（Startup Latency）。參見 [[CLAUDE-CODE-SDK]]

---

### 13/ --add-dir — 跨多個 Repository 工作

```bash
# 在 repo-A 啟動，同時賦予 Claude 存取 repo-B 的權限
claude --add-dir /path/to/repo-B

# 或在會話中動態新增
/add-dir /path/to/repo-B
```

`--add-dir` 不只告訴 Claude 其他 Repo 的存在，還同時給予**操作權限（Permissions）**。

---

## 我的心得（My Takeaways）

這串推文最有價值的點在於：Cherny 本人實際在工作中使用這些功能，不是官方文件的轉錄，而是真實的工作流程（Workflow）揭露。

最值得立刻嘗試的三個功能：
1. **`/btw`** — 立刻可用，改善日常互動體驗
2. **`claude -w` + Worktrees** — 對需要同時跑多個任務的人是倍增器（Force Multiplier）
3. **Hooks + SessionStart** — 把 CLAUDE.md 的靜態指令升級為動態上下文載入

## 待補充（Open Questions）

- `/batch` 能分發給「數百乃至數千個 Agent」——這個規模下的 API 費用估算為何？有沒有官方的成本計算器或用量預警機制防止帳單爆炸？（建議搜尋：`Claude Code batch agents cost estimation token billing`）
- `--teleport` 跨裝置切換 session 時，session 的狀態（包括 context history 和 Tools 狀態）如何同步？若在手機和桌機間快速切換，是否有 race condition 的風險？（建議搜尋：`Claude Code teleport session state sync race condition`）
- Dispatch 的「安全遠端控制」具體採用什麼安全協議？在公共 WiFi 或企業防火牆環境下，遠端控制本機 MCP 和瀏覽器的資料傳輸是否經過端對端加密？（建議搜尋：`Claude Code Dispatch remote control security protocol encryption`）
- `/btw` 的「不打斷主流程」是透過什麼機制實現的？在技術實作上，主任務和 `/btw` 問題是否在同一個 context window 中處理，還是完全隔離的平行處理？（建議搜尋：`Claude Code /btw parallel context implementation`）
- `claude -w` + Git Worktrees 同時跑數十個 Claude 實例時，每個 worktree 是否有獨立的 CLAUDE.md 設定層級？不同 worktree 的 Hook 是否互相干擾？（建議搜尋：`Claude Code worktree CLAUDE.md hooks isolation multiple instances`）
- Claude Code iOS/Android App 目前的功能集和 CLI 有何差異？行動裝置上是否能完整執行 Hooks、Worktrees 和 MCP 等進階功能？（建議搜尋：`Claude Code mobile app feature parity iOS Android CLI`）

## 相關連結（Related）

- [[CLAUDE-CODE-HOOKS]] — Hooks 機制深入探討
- [[CLAUDE-CODE-GIT-WORKTREES]] — Git Worktrees 並行工作實務
- [[CLAUDE-CODE-SDK]] — SDK 非互動式使用與 --bare 旗標
- [[2026-01-08-CLAUDE-CODE-SCHEDULER-CODE-ANALYSIS]] — Boris 提到的排程功能，此為 scheduler 插件的程式碼深度分析
- [[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]] — Boris 提到的團隊記憶功能，此為 Team Memory 的原始碼深度分析
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — `--resume` 會刷新 CLAUDE.md 快取的原始碼驗證，與 Boris 提到的 resume 功能直接相關
- [[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]] — Reza Rezvani 分析本文中提及的 Boris 技巧文章，並實測 Karpathy CLAUDE.md 四原則

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 13 個功能名稱：mobile app、/teleport、/loop、hooks、Dispatch、Chrome、Desktop web server、/branch、/btw、worktrees、/batch、--bare、--add-dir |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | 這 13 個功能可分成三類：跨裝置使用（1-2）、自動化與生命週期控制（3-4、11）、多 Agent 並行架構（10-11）、以及日常效率提升（5-9、12-13） |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維，看透策略底層邏輯 | 隱含假設：使用者已熟悉基本 Claude Code CLI；Cherny 的「數十個 Agent 同時跑」場景要求穩定的機器資源；/batch 的「數千個 Agent」說法需核實是否有資源/成本限制 |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力，將理論轉為行動 | 1) 立刻設定 SessionStart Hook 動態載入專案上下文；2) 把 CI 腳本改用 `--bare` 模式減少啟動時間；3) 在下一個大型重構任務試用 `/batch` |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡，在不確定的情境中做出最佳選擇 | 優點：功能互補，低門檻高收益；缺點：Dispatch 和 /batch 對一般個人用戶的可及性（Accessibility）不明；與 Cursor/Aider 等競品相比，Claude Code 的行動裝置支援是差異化優勢 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：`/batch` 中的「數千個 Agents」是否會有 API 費用爆炸的問題？有沒有成本上限機制？
- **假設**：本文的前提是使用者已在一定程度上熟悉 Claude Code；若完全新手，哪個功能應該最先學？
- **證據**：`--bare` 真的可以提速 10 倍嗎？這個數字在哪些情境下測量的？網路延遲是否是更大的瓶頸？
- **觀點**：若站在競品（Cursor、Aider、Cline）的立場，對這 13 個功能最有力的反擊是什麼？
- **後果**：若大規模使用 Worktrees + /batch，12 個月後 Repository 的分支管理（Branch Management）會不會變成噩夢？

## References

- [原始推文串](https://x.com/bcherny/status/2038454336355999749) — Boris Cherny on X, Mar 30, 2026
- [Claude Code 官方文件](https://code.claude.com)
