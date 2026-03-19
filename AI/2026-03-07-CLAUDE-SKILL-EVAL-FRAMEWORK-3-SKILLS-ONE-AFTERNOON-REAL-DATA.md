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

作者在建立超過 20 個生產用 skill 之後，透過 Anthropic 於 2026 年 3 月發布的 skill eval 框架，第一次用**數據**驗證 skill 到底有沒有用。框架帶來的最大改變：skill 開發從「感覺有效」變成「數據驗證有效」。一個下午、三個 skill、三套迭代循環，揭露了三種過去看不見的失敗模式。

## Key Insights

- **誤報比漏報更致命** — 把乾淨的程式碼標記為有問題，會讓開發者養成忽略所有 review 的習慣，這比漏掉一個真正的問題還糟
- **順序錯誤在輸出中是隱形的** — 最終文件看起來正確，但 eval 逐步記錄才能揭露步驟順序問題
- **Benchmark 量化 skill 價值** — 多用 40% tokens，但減少 70% 手動修正，讓投資決策變得清晰
- **Description 優化是被低估的功能** — 觸發準確率從 70% 提升到 90%，大幅降低 false positive
- **先寫測試案例再寫 skill** — Eval-first 開發等同 TDD，防止你不知不覺用第一個草稿來定義「成功」
- **Skill 有使用期限** — 當基礎模型能力追上 skill 時，benchmark 數據會告訴你，此時應該退休它

## Details

### Skill Eval 框架的四大能力（2026 年 3 月更新）

> [!note] 這次更新的意義
> Anthropic 官方部落格說「為 skill 開發帶來嚴謹性」，但實際上更接近：把 prompt 工程從猜測變成工程。

| 能力 | 功能描述 |
|------|---------|
| **Eval 框架** | 定義測試 prompts + 斷言條件，系統判斷 skill 輸出是否正確 |
| **Benchmark 模式** | 有無 skill 的對比數據：通過率、token 用量、執行時間 |
| **多代理 A/B 比較** | 兩個版本盲測，由獨立 agent 評判，消除確認偏誤 |
| **Description 優化** | 自動測試觸發描述，迭代改善 false positive 和 false negative |

### 兩種 Skill 類型的區別

> [!important] 類型決定策略
> 這個區別影響測試方式，也決定 skill 何時應該被退休。

**能力提升型（Capability Uplift）**
- Claude 本身做不到或做不穩定的事
- 例：生成符合團隊規範的完整 OpenAPI 3.1 文件
- 注意：隨著模型進步，這類 skill 可能被模型本身取代

**編碼偏好型（Encoded Preference）**
- Claude 本來就會做，但要按照你的特定流程
- 例：按照團隊的 code review 標準逐項檢查
- 這類 skill 的價值取決於與實際工作流程的吻合度

---

### Skill 1：PR Review Standards（編碼偏好型）

**問題**：新開發者要花數週才能學會團隊的 code review 期待，每次 Claude Code 對話也從零開始。

**Eval 測試設計**：5 個測試 prompt，模擬真實 PR diff（包含 barrel export、raw entity、乾淨 PR 等案例）

**迭代結果**：

| 迭代 | 結果 | 問題 |
|------|------|------|
| 第 1 次 | 3/5 | 漏掉 path alias 問題；乾淨 PR 被誤報 |
| 第 2 次 | 4/5 | 加入明確的路徑規範；消除誤報 |
| 第 3 次 | 4/5 | 剩餘邊界案例記錄為已知限制 |

**關鍵修正**：加入「不要標記未在標準清單中的風格偏好」，消除了對乾淨 PR 的誤報。

> [!warning] 最重要的洞察
> 誤報是比漏報更嚴重的失敗。沒有系統性的 eval，這個問題根本不可能被發現。

---

### Skill 2：API 文件生成器（能力提升型）

**目標**：從 Express route handler 生成完整 OpenAPI 3.1 文件，包含 typed schemas、error codes、rate limit annotations 和範例請求。

**Benchmark 對比**：

| 指標 | 無 Skill | Skill 迭代 1 | Skill 迭代 3 |
|------|---------|------------|------------|
| 文件品質分數 | ~40% | ~65% | ~85% |
| Token 用量 | 基準 | +40% | +40% |
| 需要手動修正 | 基準 | -50% | -70% |

**主要問題**：迭代 1 發現 auth endpoint 文件寫錯（描述 Bearer token，但實際是 session-based JWT with custom header）。修正：在 skill 參考資料區加入團隊特定的 auth 模式。

> [!tip] Eval 的盲點
> Eval 框架擅長二元斷言（輸出是否包含 error codes？是/否），但難以評估品質梯度（error 說明是否有幫助？）這部分仍需人工審閱。

---

### Skill 3：事故響應 Runbook（編碼偏好型）

**目標**：將團隊事故響應流程編碼成 skill（P0-P3 分類、通知模板、根本原因分析、事後分析文件）。

**意外發現：順序錯誤是隱形的**

測試案例：資料庫連線逾時影響 30% API 請求。Skill 正確分類、正確生成文件，**但**在確認影響範圍之前就通知工程負責人——違反團隊流程。最終文件看起來完全正確，只有讀 eval 逐步記錄才能發現。

**修正方式**：

```
❌ 強制命令：「步驟 1 完成前不得進行步驟 2」
✅ 解釋原因：說明為什麼順序很重要（避免 alert fatigue）
```

> [!note] 原則勝過規則
> skill-creator 本身的哲學在這裡得到驗證：解釋「為什麼」比強制「怎麼做」更有效。

---

### Description 優化：被低估的功能

**原始描述** → 觸發準確率 7/10
**優化後描述** → 觸發準確率 9/10，false trigger 率顯著降低

優化流程：生成 20 個 eval queries（10 應觸發、10 不應觸發）→ HTML 介面審閱 → 優化器最多跑 5 次迭代。

---

### 框架的真實限制

> [!warning] 誠實的評估

| 限制 | 說明 |
|------|------|
| **Claude.ai 體驗降級** | 無法並行子代理，無法跑 baseline 對比，只能順序執行 |
| **Eval 設計本身是技能** | 太簡單的測試案例會讓你誤以為 skill 有效 |
| **主觀品質難以量化** | 二元斷言有效，品質梯度評估仍需人工 |
| **Description 優化冷啟動難** | 需要 20 個精心設計的 queries，初次很難想到好的負樣本 |
| **無團隊規模分享機制** | Eval 結果在本地執行，無法跨團隊追蹤或 CI 整合 |

---

### 建議的開發流程

```
1. 先從編碼偏好型 skill 開始（不要從能力提升型開始）
   → 預期輸出明確，eval 斷言容易寫

2. 先寫測試案例，再寫 skill（TDD 思維）
   → 防止用第一個草稿來定義「成功」

3. Skill 穩定後再做 description 優化
   → 不要對移動中的目標優化觸發精度

4. 用 benchmark 模式做退休決策
   → 當基礎模型通過能力提升 skill 的 eval 時，退休它
```

## References

- [原文](https://medium.com/@alirezarezvani/claude-skill-eval-framework-3-skills-one-afternoon-real-data-5b43e06182cb)
- [作者的 Claude Code Skill Factory](https://github.com/alirezarezvani/claude-code-skill-factory)
