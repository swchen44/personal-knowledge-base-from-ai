---
title: "Claude Skill Eval 框架：3個技能、一個下午、真實數據"
date: 2026-03-07
category: AI
tags:
  - ai/claude-code
  - ai/skills
  - ai/eval
  - tools/claude
  - productivity/skill-building
source: "https://medium.com/@alirezarezvani/claude-skill-eval-framework-3-skills-one-afternoon-real-data-5b43e06182cb"
source_type: article
author: "Reza Rezvani"
status: notes
links:
  - "[[CLAUDE-MEMORY-ENGINE]]"
  - "[[CLAUDE-CODE-141-AGENTS-SETUP]]"
---

## Summary

作者在建立超過 20 個生產用技能（skill）之後，透過 Anthropic 於 2026 年 3 月發布的技能評估（skill eval）框架，第一次用**數據**驗證技能（skill）到底有沒有用。框架帶來的最大改變：技能（skill）開發從「感覺有效」變成「數據驗證有效」。一個下午、三個技能（skill）、三套迭代循環（iteration cycle），揭露了三種過去看不見的失敗模式。

## Key Insights

- **誤報（false positive）比漏報（false negative）更致命** — 把乾淨的程式碼標記為有問題，會讓開發者養成忽略所有審查（review）的習慣，這比漏掉一個真正的問題還糟
- **順序錯誤（sequence error）在輸出中是隱形的** — 最終文件看起來正確，但評估逐步記錄（eval transcript）才能揭露步驟順序問題
- **基準測試（benchmark）量化技能（skill）價值** — 多用 40% 詞元（token），但減少 70% 手動修正，讓投資決策變得清晰
- **描述優化（description optimization）是被低估的功能** — 觸發準確率（trigger accuracy）從 70% 提升到 90%，大幅降低誤觸發（false trigger）
- **先寫測試案例（test case）再寫技能（skill）** — 評估優先（eval-first）開發等同測試驅動開發（TDD, Test-Driven Development），防止你不知不覺用第一個草稿來定義「成功」
- **技能（skill）有使用期限** — 當基礎模型（base model）能力追上技能（skill）時，基準測試（benchmark）數據會告訴你，此時應該退休（retire）它

## Details

### Skill Eval 框架的四大能力（2026 年 3 月更新）

> [!note] 這次更新的意義
> Anthropic 官方部落格說「為技能（skill）開發帶來嚴謹性」，但實際上更接近：把提示詞工程（prompt engineering）從猜測變成工程實踐。

| 能力 | 功能描述 |
|------|---------|
| **評估框架（Eval Framework）** | 定義測試提示詞（test prompts）+ 斷言條件（assertions），系統判斷技能（skill）輸出是否正確 |
| **基準測試模式（Benchmark Mode）** | 有無技能（skill）的對比數據：通過率（pass rate）、詞元用量（token usage）、執行時間 |
| **多代理 A/B 比較（Multi-agent A/B Comparison）** | 兩個版本盲測（blind test），由獨立代理（agent）評判，消除確認偏誤（confirmation bias） |
| **描述優化（Description Optimization）** | 自動測試觸發描述（trigger description），迭代改善誤觸發（false positive）和漏觸發（false negative） |

### 兩種 Skill 類型的區別

> [!important] 類型決定策略
> 這個區別影響測試方式，也決定技能（skill）何時應該被退休（retire）。

**能力提升型（Capability Uplift）**
- Claude 本身做不到或做不穩定的事
- 例：生成符合團隊規範的完整 OpenAPI 3.1 文件
- 注意：隨著模型（model）進步，這類技能（skill）可能被模型本身取代

**編碼偏好型（Encoded Preference）**
- Claude 本來就會做，但要按照你的特定流程（workflow）
- 例：按照團隊的程式碼審查（code review）標準逐項檢查
- 這類技能（skill）的價值取決於與實際工作流程（workflow）的吻合度

---

### Skill 1：PR Review Standards（編碼偏好型）

**問題**：新開發者要花數週才能學會團隊的程式碼審查（code review）期待，每次 Claude Code 對話也從零開始。

**評估測試設計（Eval Design）**：5 個測試提示詞（test prompt），模擬真實 PR 差異（PR diff）（包含桶出口（barrel export）、原始資料實體（raw entity）、乾淨 PR 等案例）

**迭代結果（Iteration Results）**：

| 迭代 | 結果 | 問題 |
|------|------|------|
| 第 1 次 | 3/5 | 漏掉路徑別名（path alias）問題；乾淨 PR 被誤報（false positive） |
| 第 2 次 | 4/5 | 加入明確的路徑規範；消除誤報（false positive） |
| 第 3 次 | 4/5 | 剩餘邊界案例（edge case）記錄為已知限制 |

**關鍵修正**：加入「不要標記未在標準清單中的風格偏好（style preference）」，消除了對乾淨 PR 的誤報（false positive）。

> [!warning] 最重要的洞察
> 誤報（false positive）是比漏報（false negative）更嚴重的失敗。沒有系統性的評估（eval），這個問題根本不可能被發現。

---

### Skill 2：API 文件生成器（能力提升型）

**目標**：從 Express 路由處理器（route handler）生成完整 OpenAPI 3.1 文件，包含型別化綱要（typed schemas）、錯誤代碼（error codes）、速率限制注解（rate limit annotations）和範例請求。

**基準測試對比（Benchmark Comparison）**：

| 指標 | 無 Skill | Skill 迭代 1 | Skill 迭代 3 |
|------|---------|------------|------------|
| 文件品質分數 | ~40% | ~65% | ~85% |
| 詞元用量（Token Usage） | 基準 | +40% | +40% |
| 需要手動修正 | 基準 | -50% | -70% |

**主要問題**：迭代 1 發現驗證端點（auth endpoint）文件寫錯（描述持有者令牌（Bearer token），但實際是帶自訂標頭（custom header）的 JWT 工作階段（session-based JWT））。修正：在技能（skill）參考資料區加入團隊特定的驗證模式（auth pattern）。

> [!tip] 評估（Eval）的盲點
> 評估（eval）框架擅長二元斷言（binary assertions）（輸出是否包含錯誤代碼（error codes）？是/否），但難以評估品質梯度（quality gradients）（錯誤說明（error description）是否有幫助？）這部分仍需人工審閱。

---

### Skill 3：事故響應手冊（Incident Response Runbook）（編碼偏好型）

**目標**：將團隊事故響應（incident response）流程編碼成技能（skill）（P0-P3 嚴重性分類（severity classification）、通知模板（notification template）、根本原因分析（root cause analysis）、事後分析（post-mortem）文件）。

**意外發現：順序錯誤（sequence error）是隱形的**

測試案例：資料庫連線逾時（database connection timeout）影響 30% API 請求。技能（skill）正確分類、正確生成文件，**但**在確認影響範圍（impact scope）之前就通知工程負責人——違反團隊流程（workflow）。最終文件看起來完全正確，只有讀評估逐步記錄（eval transcript）才能發現。

**修正方式**：

```
❌ 強制命令：「步驟 1 完成前不得進行步驟 2」
✅ 解釋原因：說明為什麼順序很重要（避免警告疲勞（alert fatigue））
```

> [!note] 原則勝過規則
> skill-creator 本身的哲學在這裡得到驗證：解釋「為什麼」比強制「怎麼做」更有效。

---

### 描述優化（Description Optimization）：被低估的功能

**原始描述** → 觸發準確率（trigger accuracy）7/10
**優化後描述** → 觸發準確率（trigger accuracy）9/10，誤觸發（false trigger）率顯著降低

優化流程（optimization loop）：生成 20 個評估查詢（eval queries）（10 個應觸發、10 個不應觸發）→ HTML 介面審閱 → 優化器（optimizer）最多跑 5 次迭代（iteration）。

---

### 框架的真實限制

> [!warning] 誠實的評估

| 限制 | 說明 |
|------|------|
| **Claude.ai 體驗降級** | 無法並行子代理（subagent），無法跑基準對比（baseline comparison），只能順序執行 |
| **評估設計（eval design）本身是技能** | 太簡單的測試案例（test case）會讓你誤以為技能（skill）有效 |
| **主觀品質難以量化** | 二元斷言（binary assertions）有效，品質梯度（quality gradients）評估仍需人工 |
| **描述優化（description optimization）冷啟動難** | 需要 20 個精心設計的評估查詢（eval queries），初次很難想到好的負樣本（negative examples） |
| **無團隊規模分享機制** | 評估（eval）結果在本地執行，無法跨團隊追蹤或整合到持續整合（CI）系統 |

---

### 建議的開發流程

```
1. 先從編碼偏好型（encoded preference）技能（skill）開始
   → 預期輸出明確，評估斷言（eval assertions）容易寫

2. 先寫測試案例（test case），再寫技能（skill）（TDD 思維）
   → 防止用第一個草稿來定義「成功」

3. 技能（skill）穩定後再做描述優化（description optimization）
   → 不要對移動中的目標優化觸發精度（trigger accuracy）

4. 用基準測試模式（benchmark mode）做退休（retire）決策
   → 當基礎模型（base model）通過能力提升型（capability uplift）技能（skill）的評估（eval）時，退休它
```

## References

- [原文](https://medium.com/@alirezarezvani/claude-skill-eval-framework-3-skills-one-afternoon-real-data-5b43e06182cb)
- [作者的 Claude Code Skill Factory](https://github.com/alirezarezvani/claude-code-skill-factory)
