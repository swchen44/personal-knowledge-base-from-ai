---
title: "Superpowers：適用於程式碼代理人 (Coding Agent) 的可組合技能框架 (Composable Skills Framework)"
date: 2026-03-16
category: OpenSource
tags:
  - ai/agents
  - ai/claude-code
  - tools/skills-framework
  - devtools/workflow
  - productivity/tdd
source: "https://github.com/obra/superpowers"
source_type: tool
author: "Jesse (obra)"
status: notes
links:
  - "[[CLAUDE-CODE-141-AGENTS-SETUP]]"
  - "[[CLAUDE-MEMORY-ENGINE]]"
  - "[[CLAUDE-CODE-HOOKS]]"
  - "[[AI-AGENT-MEMORY]]"
---

## 摘要 (Summary)

Superpowers 是一個建立在可組合「技能 (skills)」之上的完整軟體開發工作流程 (software development workflow) 框架，設計給程式碼代理人 (coding agent) 使用。技能會自動觸發 (auto-trigger)，代理人不需要特別指令即可執行正確流程。支援 Claude Code、Cursor、Codex、OpenCode、Gemini CLI，並已上架官方插件市場 (plugin marketplace)。

核心思想：**代理人有了技能 (skills)，就有了超能力 (Superpowers)。**

---

## 關鍵洞察 (Key Insights)

- **技能即自動工作流程 (Automated Workflow)**：技能在符合情境時自動觸發，不是建議，是強制流程 — 參見 [[CLAUDE-CODE-HOOKS]]
- **撰寫技能 = TDD 應用於流程文件**：先寫失敗的測試情境 (failing test scenario)，再寫技能，用 RED-GREEN-REFACTOR 迭代 — 參見 [[AI-AGENT-MEMORY]]
- **描述 (description) = 觸發條件，非內容摘要**：若 description 摘要了工作流程，代理人會走捷徑跳過閱讀完整技能文件（Claude Search Optimization，CSO 陷阱）
- **代理人驅動開發 (Subagent-Driven Development)**：每個工程任務派出全新子代理人 (subagent)，搭配兩階段審查（規格合規 (Spec Compliance) → 程式碼品質 (Code Quality)），比共用上下文更穩定 — 參見 [[CLAUDE-CODE-141-AGENTS-SETUP]]
- **最少 3 個組合壓力 (combined pressures) 才能測試紀律型技能**：時間壓力、沉沒成本 (sunk cost)、權威語氣同時施加，才能找出代理人的合理化藉口 (rationalization)

---

## 詳細內容 (Details)

### 基礎工作流程 (Basic Workflow) — 7 個自動觸發技能

| 順序 | 技能名稱 | 觸發時機 | 功能 |
|------|---------|---------|------|
| 1 | brainstorming | 開始寫程式之前 | 透過提問精煉想法、驗證設計 |
| 2 | using-git-worktrees | 設計確認後 | 在新分支建立隔離工作空間 (isolated workspace) |
| 3 | writing-plans | 設計批准後 | 拆解任務為 2–5 分鐘、含驗證步驟的小任務 |
| 4 | subagent-driven-development | 計劃啟動後 | 每個任務派出新子代理人，兩階段審查 |
| 5 | test-driven-development | 實作期間 | 強制 RED-GREEN-REFACTOR 循環 |
| 6 | requesting-code-review | 任務之間 | 檢查規格合規性，嚴重問題阻止進度 |
| 7 | finishing-a-development-branch | 任務完成後 | 驗證測試、提供合併/PR/保留/捨棄選項 |

### 完整技能庫 (Skills Library)

**測試 (Testing)：**
- `test-driven-development` — 包含測試反模式 (anti-patterns) 參考
- `systematic-debugging` — 4 階段根本原因分析 (root cause analysis) 流程
- `verification-before-completion` — 確認真的修好了，不只是「感覺修好了」

**協作 (Collaboration)：**
- `brainstorming`、`writing-plans`、`executing-plans`
- `dispatching-parallel-agents` — 並發子代理人 (concurrent subagents) 工作流程
- `requesting-code-review`、`receiving-code-review`

**元技能 (Meta Skills)：**
- `writing-skills` — 用 TDD 方法創建新技能的完整指南

### 撰寫技能的關鍵規則

> [!warning] CSO（Claude 搜索優化，Claude Search Optimization）陷阱
> **description 絕對不能摘要工作流程**。
> 測試發現：description 說「代碼審查在任務之間」時，代理人只做了一次審查；
> 改成「在執行包含獨立任務的實作計劃時使用」後，代理人正確執行了兩階段審查。
> description = 觸發條件 (triggering conditions)，不是工作流程摘要。

> [!tip] YAML Frontmatter 規則
> - 只有 `name` 和 `description` 兩個欄位，合計最多 1024 字元
> - `name`：只用字母、數字、連字號，不能用括號或特殊字元
> - `description`：第三人稱，以 "Use when..." 開頭，只寫觸發條件

**鐵律 (Iron Law)：**
> 沒有先跑失敗測試 (failing test)，就不能寫技能。包含新增技能和修改現有技能，沒有例外。

### 技能文件結構 (Skill File Structure)

```bash
# 每個技能是一個資料夾，只有 SKILL.md 是必要的
skills/
  skill-name/
    SKILL.md          # 主要參考文件（必要）
    supporting-file   # 只有需要時才加（重型參考文件或可重用工具）
```

### 哲學 (Philosophy)

- **測試驅動開發 (Test-Driven Development, TDD)**：永遠先寫測試
- **系統化優於臨時性 (Systematic over ad-hoc)**：流程勝過靈感
- **降低複雜度 (Complexity Reduction)**：簡單是第一目標
- **證據優於聲明 (Evidence over Claims)**：宣告成功前先驗證

### 安裝方式

```bash
# Claude Code 官方市場 (Official Marketplace)
/plugin install superpowers@claude-plugins-official

# Cursor
/add-plugin superpowers

# Gemini CLI
gemini extensions install https://github.com/obra/superpowers
```

---

## 我的心得 (My Takeaways)

- **description = 觸發條件** 這個 CSO 洞察直接可套用到我自己的技能設計上；之前建立的 obsidian-knowledge-graph skill 的 description 需要用此標準重新審視
- **撰寫技能即 TDD** 的框架讓技能有客觀的成功標準：代理人在有 skill 和沒有 skill 時行為差異，量化了技能的實際價值
- **子代理人兩階段審查**（規格合規 → 程式碼品質）是比 [[CLAUDE-CODE-141-AGENTS-SETUP]] 顏色團隊更細粒度的審查模式，兩者可整合使用
- **YAGNI (You Aren't Gonna Need It)** + **DRY (Don't Repeat Yourself)** + TDD 三原則在多代理人環境中比單代理人更重要：15% 的交接資訊損失 (handoff info loss) 會放大每一個設計偏差
- **「一個好範例勝過多個平庸範例」** — 技能文件設計哲學與知識庫筆記設計哲學一致：深度優於廣度

---

## 待補充（Open Questions）

- Superpowers 的「自動觸發」機制具體依賴什麼底層機制實現？是透過 Claude Code 的 Hooks 系統、CLAUDE.md 的 skills 載入，還是其他機制？不同工具（Cursor、Codex、Gemini CLI）的觸發方式是否一致？（建議搜尋：`Superpowers obra skill auto-trigger mechanism hooks`）
- `writing-skills` 元技能要求「先寫失敗的測試情境，再寫技能」，但針對行為性技能（而非程式碼），測試情境的「失敗」如何客觀判定？有沒有具體的評估指標或測試框架？（建議搜尋：`Superpowers skill TDD testing failing scenario evaluation`）
- `subagent-driven-development` 的「兩階段審查」中，第一階段「規格合規」的評審是由另一個 AI subagent 執行還是人工？AI 審查的 false negative 率有多高？（建議搜尋：`Superpowers subagent code review spec compliance accuracy`）
- 技能的 `description` 欄位有 1024 字元限制，如果觸發條件需要更複雜的描述（如多種不同情境），有沒有官方建議的設計模式（如拆分多個技能還是使用包含語法）？（建議搜尋：`Superpowers skill description character limit complex trigger`）
- Superpowers 上架官方 Plugin Marketplace 後，版本更新機制是什麼？若 obra 更新了核心技能邏輯，用戶是自動獲取最新版還是需要手動重新安裝？（建議搜尋：`Claude Code plugin marketplace version update auto update`）
- 「最少 3 個組合壓力才能測試紀律型技能」這個結論是基於什麼實驗或觀察得出的？有沒有其他可以有效壓測 AI 技能紀律的方法？（建議搜尋：`AI agent skill discipline testing pressure combined stimuli`）

## 相關連結 (Related)

- [[CLAUDE-CODE-141-AGENTS-SETUP]] — 互補：141 個代理人的 10 色團隊架構；Superpowers 的子代理人審查模式可整合進去
- [[CLAUDE-MEMORY-ENGINE]] — 互補：記憶系統 (memory system) + 學習循環；Superpowers 專注工作流程紀律，Memory Engine 專注跨會話知識保留
- [[CLAUDE-CODE-HOOKS]] — 底層機制：Superpowers 技能的自動觸發依賴 hooks 系統；了解 hooks 才能深入自訂技能行為
- [[AI-AGENT-MEMORY]] — 更廣泛的代理人記憶架構研究；Superpowers 用技能文件做為「記憶」的外化形式
- [[2026-05-03-CLAUDE-CODE-PLAN-MODE-VS-SUPERPOWERS-CONFLICT-ANALYSIS]] — Plan Mode vs SuperPowers 衝突深度分析：EnterPlanMode 攔截機制、Auto Mode 停用、計畫檔案路徑不相容
- [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]] — 另一個 TDD-first 的 AI coding 工作流，與 Matt Pocock 的 /tdd skill 對照
- [[2026-04-08-SUPERPOWERS-13-SKILLS-PRACTICAL-WALKTHROUGH]] — Superpowers 13 個 skill 的實戰詳解版（自動 vs 手動觸發、6 核心流程、三方對照），補充本筆記的概念性介紹
- [[2026-05-18-GRILL-ME-VS-PLAN-MODE-COEXISTENCE-RESEARCH]] — grill-me 結構性對照：為何 brainstorming 與 Plan Mode 機制衝突，grill-me 卻沒有
- [[2026-06-30-AI-DLC-CLAUDE-CODE-END-OF-VIBE-CODING-VS-OPENSPEC-SUPERPOWERS]] — AWS AI-DLC 方法論的三方比較（AI-DLC vs OpenSpec vs Superpowers），Superpowers 被定位為輕量 process skills 路線的代表。

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | Superpowers 框架、七個自動觸發技能（brainstorming → finishing-a-development-branch）、CSO（Claude Search Optimization）陷阱、description 欄位 1024 字元限制、子代理人兩階段審查（規格合規 → 程式碼品質）、TDD 三原則（YAGNI、DRY、RED-GREEN-REFACTOR） |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Superpowers 的核心邏輯是「把技能設計成自動觸發的強制工作流程，而非可選的建議」。description 欄位寫觸發條件而非工作流程摘要，是因為代理人會把 description 當做是否閱讀完整文件的依據——一旦 description 已經揭示了流程，代理人就會走捷徑跳過完整技能文件（CSO 陷阱）。子代理人驅動開發則透過隔離上下文來減少交接資訊損失，比共用上下文的共享會話更穩定可靠。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | （1）框架假設「代理人在符合觸發條件時會忠實閱讀完整 SKILL.md」，但若代理人跳過閱讀，整個自動觸發機制就會失效——CSO 陷阱本身即說明此假設並不穩健；（2）「最少 3 個組合壓力才能測試紀律型技能」的結論缺乏量化方法論，尚未有公開的測試框架支撐；（3）15% 交接資訊損失的數字被提及但未附出處，其適用範圍（模型、任務類型）未明。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | （1）用 CSO 標準審查既有技能的 description 欄位，把「說明流程」的 description 改為「Use when... 觸發條件」格式；（2）建立 `writing-skills` 元技能作為所有新技能的閘道，強制先寫失敗的測試情境再建技能；（3）整合子代理人兩階段審查到現有 CI 流程，以規格合規審查阻止低品質任務交接。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | Superpowers 相比手動提示設計的優勢在於流程一致性與可測試性，但代價是需要為每個技能維護失敗測試情境，維護成本隨技能數量線性增長；與 CLAUDE.md 全域指令相比，技能文件顆粒度更細但觸發依賴描述匹配，存在 CSO 陷阱的系統性風險；子代理人兩階段審查比單一代理人自我審查更可靠，但 AI 審查的 false negative 率仍是未知的關鍵弱點。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「自動觸發」究竟是透過 Claude Code 的 Hooks 系統、CLAUDE.md 的 skills 欄位、還是其他底層機制實現的？不同工具（Cursor、Gemini CLI）的觸發方式是否一致，還是各自有不同的實作？
- **假設**：框架假設代理人在觸發條件符合時會「主動且完整地」閱讀 SKILL.md，但如果代理人在高壓情境下仍然走捷徑，CSO 陷阱以外還有哪些系統性的失效模式？
- **證據**：「15% 交接資訊損失」這個數字的出處是什麼實驗或研究？這個損失率在不同任務類型（程式碼生成 vs. 需求分析）之間是否有顯著差異？
- **觀點**：Superpowers 將紀律型行為外化為「強制工作流程文件」，而非依賴模型本身的指令遵循能力。這個設計哲學是務實的工程選擇，還是在迴避應該解決的模型對齊（alignment）問題？
- **後果**：若 Superpowers 技能的 description 欄位普遍被優化為「觸發條件」格式，未來模型訓練資料中這種格式會不會成為主流，進而改變模型對 description 欄位的解讀方式？
