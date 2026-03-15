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

## 相關連結 (Related)

- [[CLAUDE-CODE-141-AGENTS-SETUP]] — 互補：141 個代理人的 10 色團隊架構；Superpowers 的子代理人審查模式可整合進去
- [[CLAUDE-MEMORY-ENGINE]] — 互補：記憶系統 (memory system) + 學習循環；Superpowers 專注工作流程紀律，Memory Engine 專注跨會話知識保留
- [[CLAUDE-CODE-HOOKS]] — 底層機制：Superpowers 技能的自動觸發依賴 hooks 系統；了解 hooks 才能深入自訂技能行為
- [[AI-AGENT-MEMORY]] — 更廣泛的代理人記憶架構研究；Superpowers 用技能文件做為「記憶」的外化形式
