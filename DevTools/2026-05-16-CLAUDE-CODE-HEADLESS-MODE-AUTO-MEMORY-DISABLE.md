---
title: "Claude Code Headless 模式與 Auto Memory：完整行為分析與禁用方法"
date: 2026-05-16
category: DevTools
tags:
  - "#devtools/claude-code"
  - "#devtools/configuration"
  - "#ai/memory"
  - "#tools/cli"
source: "conversation"
source_type: article
author: "swchen44 + Claude"
status: notes
links:
  - "[[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]]"
  - "[[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
---

## 摘要（Summary）

深入分析 Claude Code 反編譯原始碼，解析 headless 模式（`-p`/`--print`）是否載入 auto memory（MEMORY.md），以及 `CLAUDE_CODE_DISABLE_AUTO_MEMORY` 環境變數的實際控制範圍。核心發現：**headless 模式與互動式模式走完全相同的 context 建構路徑，且 headless 更積極——它在啟動時主動預取（prefetch）memory**；`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 能完整阻斷讀取與背景寫入，但模型本身若被觸發仍可直接寫入 MEMORY.md。

## 關鍵洞察（Key Insights）

- **Headless 模式一樣讀 memory**：`src/main.tsx:1977-1983` 在進入 `runHeadless()` 前主動呼叫 `getSystemContext()` 和 `getUserContext()`，比互動模式更積極 — 參見 [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]
- **`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 阻斷讀取但只擋部分寫入**：它停用了背景 extraction agent 和 autoDream 整理，但不阻止模型本身主動寫入
- **Memory 路徑由 git root 決定**：slug 是 `sanitizePath(canonical git root)`，同一 repo 所有 worktree 共用同一個 MEMORY.md — 參見 [[2026-04-12-CLAUDE-CODE-WORKTREE-FILE-OPERATIONS-AND-REPO-INTEGRATION]]
- **settings.json 可永久停用**：在 `~/.claude/settings.json` 設 `autoMemoryEnabled: false` 效果等同環境變數，不用每次帶參數 — 參見 [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]]
- **`--bare` 連 CLAUDE.md 也不讀**：`--bare` 設定 `CLAUDE_CODE_SIMPLE=1`，是更激進的隔離，但代價是整個 context 系統都停掉

## 詳細內容（Details）

### Headless 模式的 Context 載入路徑

兩種模式的 context 建構路徑完全相同：

```
getSystemPrompt()               src/constants/prompts.ts:444
  └─ systemPromptSection('memory', ...)
       └─ loadMemoryPrompt()    src/memdir/memdir.ts:419
            └─ AutoMem → ~/.claude/projects/<slug>/memory/MEMORY.md

getUserContext()                src/context.ts:155
  └─ getMemoryFiles()           src/utils/claudemd.ts:790
       └─ 走目錄樹往上找 CLAUDE.md、memory 檔
```

差別只在**時機**：

| | 互動模式 | Headless (`-p`) |
|---|---|---|
| 載入方式 | 懶載入（React hook 觸發） | **主動預取**（啟動時觸發） |
| 相關程式碼 | 由 REPL 元件驅動 | `src/main.tsx:1977-1983` |

Headless 的預取程式碼：
```typescript
// src/main.tsx:1977-1983
void getSystemContext();   // 預取 system context
void getUserContext();     // 預取 user context（含 memory）
// ...
runHeadless(...)           // line 2829 才真正執行
```

### CLAUDE_CODE_DISABLE_AUTO_MEMORY 實際控制範圍

`isAutoMemoryEnabled()` 定義於 `src/memdir/paths.ts:30`：

```typescript
export function isAutoMemoryEnabled(): boolean {
  const envVal = process.env.CLAUDE_CODE_DISABLE_AUTO_MEMORY
  if (isEnvTruthy(envVal)) {
    return false  // 設 1/true/yes → 停用
  }
  // ...其他 fallback...
  return true
}
```

| 功能 | 是否被 `DISABLE_AUTO_MEMORY=1` 擋住 |
|------|-------------------------------------|
| MEMORY.md 注入 system prompt（讀取） | ❌ 完全停用（`memdir.ts:420`） |
| 背景 memory extraction agent | ❌ 停用（`extractMemories.ts:545`） |
| autoDream 夜間整理 | ❌ 停用（`autoDream.ts:99`） |
| /remember skill | ❌ 停用（`remember.ts:71`） |
| Agent memory snapshots | ❌ 停用（`loadAgentsDir.ts:348`） |
| 模型本身主動寫入 MEMORY.md | **⚠️ 沒有被擋**（system prompt 指令仍在） |

> [!warning] 寫入不是完全被擋
> `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 擋住的是背景 extraction agent 的自動寫入，但模型在 system prompt 裡還是收到「可以儲存記憶」的指令。若 prompt 觸發模型去寫，它仍可透過 Bash/Write tool 直接寫入 MEMORY.md。

### Memory 檔案路徑公式

```
~/.claude/projects/{slug}/memory/MEMORY.md

slug = sanitizePath(canonical_git_root)
     = 將 git root 路徑的非字母數字換成 "-"
     = 若超過 200 字元 → 取前 200 + "-" + base36 hash
```

> [!info] Worktree 共用同一 memory
> `canonical git root` 確保同一 repo 的所有 worktree 都指向同一個 MEMORY.md，不會因切換 worktree 產生多份記憶。

### 禁用 Auto Memory 的完整方法

#### 方法一：環境變數（最直接，適合一次性執行）

```bash
# Headless 模式
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude -p "你的問題"

# 互動模式同樣有效
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude
```

#### 方法二：`--bare` flag（最乾淨，但更激進）

```bash
claude --bare -p "你的問題"
```

`--bare` 在 `src/main.tsx:1015` 設定 `CLAUDE_CODE_SIMPLE=1`，同時停掉：
- auto-memory
- CLAUDE.md 自動探索
- hooks、plugin sync、background prefetch

> [!warning] `--bare` 代價較高
> 連 CLAUDE.md 都不讀，適合「完全乾淨的測試環境」，不適合日常使用。

#### 方法三：settings.json 永久設定（適合長期停用）

```json
// ~/.claude/settings.json
{
  "autoMemoryEnabled": false
}
```

由 `src/memdir/paths.ts:50-53` 控制，不用每次帶環境變數，互動與 headless 模式都生效。

#### 方法四：隔離 project root（保證不污染原有 memory）

```bash
mkdir /tmp/clean-run && cd /tmp/clean-run
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude -p "你的問題"
```

即使模型嘗試寫入，也寫到 `/tmp/clean-run` 對應的新 slug，不影響原有 memory。

> [!tip] 最推薦組合
> 一次性隔離執行用：`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude -p "..."` （讀取保證被擋，headless 下模型通常也不會主動寫）。
> 長期不用 memory 用：`settings.json` 的 `autoMemoryEnabled: false`。

## 我的心得（My Takeaways）

- **Headless 不代表「無狀態」**：`-p` 模式仍完整載入 memory 和 CLAUDE.md，行為與互動模式幾乎相同，只是沒有 REPL UI。
- **環境變數旗標命名有點反直覺**：`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 意思是「停用 auto memory」，設為 1 是停用。與 feature flag 的慣例相反（通常 `=1` 是啟用）。
- **`isAutoMemoryEnabled()` 的呼叫圖很廣**：不只是 system prompt，UI 偵測、agent snapshot、/remember skill 都在這個函數控制下，是整個 memory 子系統的單一開關。

## 待補充（Open Questions）

- `CLAUDE_CODE_DISABLE_AUTO_MEMORY` 設定後，`tengu_moth_copse` feature gate（用 attachments 取代 MEMORY.md 注入）的行為是否受影響？這兩個機制是並行還是互斥？搜尋關鍵字：`tengu_moth_copse filterInjectedMemoryFiles`
- `settings.autoMemoryEnabled: false` 在 projectSettings 層級無效（security boundary），那 localSettings 可以設嗎？policy 和 flag settings 呢？搜尋關鍵字：`getInitialSettings autoMemoryEnabled projectSettings`
- 若模型在 headless 模式下確實寫入了 MEMORY.md，下一次 headless 呼叫（有 `DISABLE_AUTO_MEMORY`）是否完全不受影響，還是有其他注入路徑？搜尋關鍵字：`loadMemoryPrompt filterInjectedMemoryFiles`
- `autoMemoryDirectory` 在 settings.json 可自訂路徑，這是否可以用來做「多套 memory profile 切換」的機制？搜尋關鍵字：`autoMemoryDirectory getAutoMemPath`

## 相關連結（Related）

- [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]] — settings.json 合併優先級，`autoMemoryEnabled` 在哪層有效
- [[2026-07-05-TERMINAL-MEMORY-MANAGEMENT-AND-CROSS-PLATFORM-PERSISTENCE]] — 延伸到 `DISABLE_AUTOUPDATER`、scrollback 與 tmux 隔離等終端機層級資源控制策略
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — Claude Code 原始碼架構概覽，context 建構機制
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — CLAUDE.md 發現與載入機制，與 memory 共用 getMemoryFiles
- [[2026-04-12-CLAUDE-CODE-WORKTREE-FILE-OPERATIONS-AND-REPO-INTEGRATION]] — Worktree 與 git root 的關係，解釋為何共用同一 memory slug
- [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — 各層設定的優先級與信任邊界
- [[2026-09-06-CODEX-CLI-VS-CLAUDE-CODE-AUTOMATION-CHEAT-SHEET]] — 將 `claude -p` 放入 Codex／Claude 的非互動自動化、JSON event 與 Supervisor 架構對照

## References

- 來源：與 Claude Code 的對話分析（2026-05-16）
- 原始碼路徑：`src/memdir/paths.ts`、`src/memdir/memdir.ts`、`src/context.ts`、`src/main.tsx`、`src/constants/prompts.ts`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | `CLAUDE_CODE_DISABLE_AUTO_MEMORY`、`--bare`、`autoMemoryEnabled`、`isAutoMemoryEnabled()`、`loadMemoryPrompt()`、slug 路徑公式 |
| **理解（半被動）** | 解釋概念的含義及關聯 | Headless 模式不是無狀態，它與互動模式共用同一 context pipeline，差別只在預取時機；DISABLE_AUTO_MEMORY 是切斷「注入」而非切斷「記憶體子系統」本身 |
| **分析（主動）** | 拆解流程、找出假設 | 關鍵假設：headless 模式下模型不會主動寫 memory——但這只是行為上的常態，不是程式層面的保證；背景 agent 被擋並不等於寫入路徑被封閉 |
| **應用（主動）** | 將知識套用情境 | 1. 跑批次評估腳本時加 `DISABLE_AUTO_MEMORY=1` 避免記憶污染；2. 在 CI 環境加進環境變數確保每次執行環境純淨 |
| **評估（主動）** | 判斷多個方案的優劣 | `DISABLE_AUTO_MEMORY=1` vs `--bare`：前者只停 memory，CLAUDE.md 仍讀；後者連 context 全停。若需要 CLAUDE.md 的行為指引但不要記憶累積，選前者。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「auto memory 的寫入」和「模型主動寫入」是同一件事嗎？如何區分「背景 extraction agent 寫入」與「模型在 turn 內用 Write tool 寫入」？
- **假設**：本文假設 headless 下模型通常不會主動觸發記憶寫入——這個假設在長 prompt、多輪對話、或含有「記住這件事」指令的情境下是否成立？
- **證據**：`extractMemories.ts:545` 被 `isAutoMemoryEnabled()` gate 住，但 system prompt 裡的「儲存記憶指令」具體是什麼文字？這段文字是否也被 gate？
- **觀點**：若站在「需要在 headless 腳本中累積記憶」的使用者立場，`DISABLE_AUTO_MEMORY` 的設計是過度限制還是合理邊界？
- **後果**：若長期使用 `autoMemoryEnabled: false`，下次改回 true 時，中斷期間的對話內容是否完全不可追回？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 誤以為 `DISABLE_AUTO_MEMORY=1` 保證「零記憶寫入」，但模型本身若被 prompt 觸發仍可寫入。在自動化腳本中若未額外隔離目錄，可能悄悄污染生產環境的 MEMORY.md。
2. **什麼情況下會失敗？** — 當 prompt 包含類似「請記住以下資訊」或「儲存到 memory」等指令時，模型仍可呼叫 Bash/Write tool 寫入 MEMORY.md，`DISABLE_AUTO_MEMORY` 並不攔截這條路徑。
3. **有沒有更好的替代方案？** — 更保險的做法是同時使用 `DISABLE_AUTO_MEMORY=1` + 指定空目錄作為 project root（`mkdir /tmp/isolated && cd /tmp/isolated`），這樣即使模型寫入，也寫到隔離的 slug，不影響真實專案的 memory。
