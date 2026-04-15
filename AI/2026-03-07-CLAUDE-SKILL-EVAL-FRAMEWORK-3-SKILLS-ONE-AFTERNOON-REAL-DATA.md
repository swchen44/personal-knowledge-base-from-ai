---
title: "Claude Skill 評估框架（Eval Framework）：3 個技能、一個下午、真實數據"
date: 2026-03-07
category: AI
tags:
  - ai/skill-design
  - ai/eval
  - tools/claude-code
source: "https://alirezarezvani.medium.com/claude-skill-eval-framework-3-skills-one-afternoon-real-data-5b43e06182cb"
source_type: article
author: "Reza Rezvani"
status: notes
links:
  - "[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]"
  - "[[SKILL-MD-SPECIFICATION]]"
  - "[[AGENT-SKILL-PATTERNS]]"
---

## 摘要（Summary）

作者 Reza Rezvani 在一個下午用 Anthropic 2026 年 3 月發布的 skill-creator 評估框架（eval framework），對他生產環境中的 3 個 skill 進行系統性測試與迭代。文章記錄了每個 skill 在真實評估資料下的失敗模式、迭代過程與量化改善結果，並說明評估框架如何將 skill 開發從「猜測」轉變為「工程」。

![Skill-Eval-Iterate 循環：三個互相連結的測試/評估節點](assets/2026-03-07-SKILL-EVAL/skill-eval-iterate-cycle.png)

## 關鍵洞察（Key Insights）

- **假陽性（false positive）比漏報（miss）更危險** — 一個把乾淨程式碼標記為問題的 skill，會訓練開發者完全忽略它的輸出。參見 [[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]
- **序列錯誤（sequence error）在輸出審查中是不可見的** — 只有評估的完整執行記錄（eval transcript）才能揭露步驟順序問題
- **Benchmark 模式量化 skill 的投資回報** — 多消耗 40% token，但減少 70% 人工修正，數據驅動決策
- **描述優化（description optimization）將觸發精準度從 ~70% 提升至 ~90%** — 在 skill 穩定後才執行，不要在仍在修改 skill 時就優化
- **在寫 skill 之前先寫測試案例** — 提示工程（Prompt Engineering）的測試驅動開發（Test-Driven Development，TDD），防止把「第一版剛好能做到的事」當成成功的定義

## 詳細內容（Details）

### Skill-Creator 評估框架新增的四項能力

> [!note] 2026-03-03 更新新增功能
> Anthropic 在 2026 年 3 月 3 日的 skill-creator 更新中，將 skill 開發從猜測變成可測量的工程：
> 1. **評估框架（Eval Framework）**：定義測試提示詞（prompt）和成功標準，系統告訴你 skill 是否達標
> 2. **Benchmark 模式（Benchmark Mode）**：有/無 skill 兩種情況對比，取得通過率、token 用量與計時資料
> 3. **多代理人 A/B 比較（Multi-agent A/B Comparison）**：兩個版本的 skill 由獨立代理人盲評，消除確認偏誤（confirmation bias）
> 4. **描述優化（Description Optimization）**：自動化迴圈測試 skill 的觸發描述，改寫以減少假陽性與假陰性

### Skill 分類：能力提升 vs 偏好編碼

> [!note] 兩類 Skill 的重要區別
> - **能力提升 Skill（Capability Uplift）**：幫助 Claude 做基礎模型無法穩定完成的事，如生產等級的 OpenAPI 文件。隨模型改善可能變得不必要。
> - **偏好編碼 Skill（Encoded Preference）**：對 Claude 已知如何執行的任務按團隊特定流程排序，如程式碼審查清單。價值取決於對實際工作流程的保真度。
>
> 這個區別影響評估策略，也影響何時該退役一個 skill。

---

### Skill 1：PR 審查標準（Encoded Preference）

**背景**：團隊有特定程式碼審查要求：只使用具名匯入（named imports，支援 tree-shaking）、feature 模組中不使用 barrel exports、每個 API 端點都要有 Zod 驗證、錯誤回應使用 `AppError` 類別。

**評估結果**：
- 測試案例：5 個真實 PR diff
- 第一次迭代：3/5（漏掉路徑別名（path alias）相關問題；對乾淨 PR 假陽性）
- 第三次迭代：4/5（剩餘漏報記錄為已知限制）

**關鍵發現**：
- 假陽性（把乾淨程式碼標記為問題）比漏報更有破壞性
- 修正假陽性的指令：`"Do not flag style preferences that are not documented in the standards list."`
- Benchmark 比較：無 skill 時 Claude 自然抓到 2/5，加入 skill 後第三次迭代達到 4/5

---

### Skill 2：API 文件生成器（Capability Uplift）

**背景**：將 Express route handler 轉換為包含型別化請求/回應 schema、錯誤碼與說明、rate limit 標注與範例請求的 OpenAPI 3.1 文件。

**Benchmark 量化結果**：

| 情況 | 生產就緒度評分 |
|------|-------------|
| 無 skill | ~40% |
| 有 skill，第 1 次迭代 | ~65% |
| 有 skill，第 3 次迭代 | ~85% |

**Token 用量分析**：
- skill 多消耗約 40% token
- 但輸出需要約少 70% 人工修正
- 對每週生成 API 文件的團隊，這個取捨明確合算

**框架限制**：評估框架擅長二元斷言（輸出是否包含錯誤碼，是/否），但不適合品質判斷（錯誤說明是否有幫助？範例是否真實？）這些需要人工審查。

---

### Skill 3：事件回應 Runbook（Encoded Preference）

**背景**：事件回應工作流程：P0–P3 嚴重度分類、按嚴重度的利害關係人通知模板、結構化的根本原因分析（root cause analysis）提示詞、事後報告（post-mortem）文件生成。

**關鍵發現：序列錯誤（Sequence Error）**

> [!warning] 序列錯誤在輸出審查中不可見
> 第一次測試模擬資料庫連線逾時（30% API 請求受影響）：
> - skill 正確分類為 P2
> - 生成了通知模板和根本原因分析框架
> - **但** 在確認影響範圍之前就通知了工程負責人
> - 我們的流程明確要求在升級通報前先完成影響評估，以避免警報疲勞
>
> 最終文件看起來完全正確，但只有讀取評估完整執行記錄才能發現這個排序問題。

**修正方式**：
- 嘗試一：加入明確的排序指令：`"Step 1 MUST complete and produce its output BEFORE proceeding to Step 2."`
- 更有效的方式：說明為何順序重要，而非只是要求它——解釋驅動比命令驅動更有效。

**測試案例結果（第 2 次迭代後）**：
- 資料庫連線逾時 ✅
- 第三方 API 降級 ✅
- 驗證服務故障 ✅
- 假警報（正確輸出「不需要行動」）✅

---

### 描述優化（Description Optimization）的效果

**原始描述**：
```
Code review skill that checks PRs against team coding standards including import conventions, error handling, and module structure.
```

**優化後描述**：
```
Analyze pull request diffs and code changes against team-specific coding standards. Use when reviewing code, checking PRs, looking at diffs, assessing code quality against project conventions, or when asked about import patterns, error handling approaches, barrel exports, or module boundaries — even if the user does not explicitly say 'code review.'
```

**觸發精準度改善**：
- 原始：should-trigger 查詢中 7/10 正確觸發
- 優化後：9/10 正確觸發
- 假觸發率也下降——優化後的描述正確忽略了「撰寫新程式碼」的查詢（原始版本有時會攔截這類查詢）

> [!tip] 描述優化的時機
> 在 skill 穩定後才執行描述優化。在 skill 本身仍在變動時優化描述，等於在為移動中的目標優化觸發精準度。

---

### 誠實的限制（Honest Limitations）

> [!warning] 框架的現實限制
> 1. **Claude.ai 的上下文限制**：完整的評估工作流程（平行代理人、基準線比較、評分、Benchmark）是為支援子代理人（subagent）的 Claude Code 設計的。Claude.ai 中只能循序執行測試案例，體驗明顯不如嚴謹。
> 2. **評估設計本身是一種技能**：第一批測試案例太簡單，Claude 不用 skill 就能通過。Benchmark 顯示無差異，白費一個迭代週期。好的評估要測試邊界案例，不是 happy path。
> 3. **主觀品質難以斷言**：框架適合二元檢查，不適合品質梯度。
> 4. **描述優化的冷啟動問題**：需要 20 個精心設計的觸發查詢，前幾個 skill 的負面範例（不應觸發但共享關鍵字的查詢）很難寫好。
> 5. **無團隊規模分享機制**：評估在本地執行，沒有內建的跨團隊分享、時間追蹤或 CI 自動觸發機制。

### 建議的入門順序

> [!tip] 從偏好編碼 Skill 開始，而非能力提升 Skill
> 1. **先寫測試案例，再寫 skill**：TDD 應用於提示工程，防止你無意識地把第一版剛好產生的東西定義為成功
> 2. **用 Benchmark 模式做升級決策**：新 Claude 模型上線時，對每個 skill 跑評估。若基礎模型在無 skill 情況下通過能力提升評估，就退役該 skill
> 3. **描述優化在 skill 穩定後才跑**

## 我的心得（My Takeaways）

這篇文章最有價值的部分是「序列錯誤不可見」這個洞察——我在自己的 skill 開發中也有同樣的盲點，只看最終輸出是否看起來正確，卻沒有驗證執行步驟的順序。

「在寫 skill 之前先寫測試案例」是我打算立刻採用的實踐。原因和程式碼的 TDD 一樣：測試先行會強迫你在寫任何指令之前，就先清楚說明「好的輸出長什麼樣子」。

Benchmark 模式的量化角度（40% token vs 70% 修正減少）也很實用——讓 skill 投資的取捨從「感覺好像有幫助」變成可以說明的數字。

## 待補充（Open Questions）

- 文章的 Benchmark 模式中，5 個 PR diff 測試案例是否足以代表真實分布？小樣本數下，通過率從 3/5 到 4/5 的統計意義有多大？（建議搜尋：`AI skill eval statistical significance small sample benchmark`）
- 序列錯誤（sequence error）的偵測仍需人工讀取完整執行記錄（eval transcript），是否有自動化偵測步驟順序問題的方案？（建議搜尋：`LLM agent step order verification automated eval`）
- 描述優化使觸發精準度從 7/10 升至 9/10，但 10 個樣本的評估基礎是否太小？有無更大規模的觸發測試建議？（建議搜尋：`skill trigger description optimization sample size`）
- 「在寫 skill 之前先寫測試案例」的 TDD 方法，如何避免測試案例本身的設計偏見（即寫出的測試案例只覆蓋已知 happy path）？（建議搜尋：`AI skill TDD test case design bias coverage`）
- 評估框架目前無法在 CI/CD 中自動觸發，若要整合到 PR 流程，有哪些已知的可行方案？（建議搜尋：`Claude skill eval CI CD integration automation`）
- 能力提升型 Skill（Capability Uplift）的退役判斷依賴基礎模型評估通過，但評估標準本身是否需要隨時間更新以避免評估過時（evaluation staleness）？（建議搜尋：`AI capability skill retirement evaluation staleness`）

## 相關連結（Related）

- [[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]] — skill-creator 評估框架的詳細說明與四項核心能力
- [[SKILL-MD-SPECIFICATION]] — SKILL.md 格式規格，30+ 工具共同採用的標準
- [[AGENT-SKILL-PATTERNS]] — 5 種代理人技能設計模式（Tool Wrapper、Generator、Reviewer、Inversion、Pipeline）
- [[2026-03-18-5-AGENT-SKILL-DESIGN-PATTERNS-EVERY-ADK-DEVELOPER-SHOULD-KNOW]] — Google Cloud Tech 發布的 ADK 設計模式文章，與本文的 skill 分類框架互補
- [[2026-03-07-CLAUDE-SKILLS-2.0-THE-SELF-IMPROVING-AI-CAPABILITIES-THAT-ACTUALLY-WORK]] — Skills 2.0 的回饋循環機制，將本文的 eval 框架嵌入自動化優化流程
- [[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]] — gstack 的三層測試金字塔程式碼分析，另一套 AI Agent 評估實作
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — Description 工程實驗與 5-8 skills 上限，eval 框架的應用場景擴展

## References

- [原文](https://alirezarezvani.medium.com/claude-skill-eval-framework-3-skills-one-afternoon-real-data-5b43e06182cb)

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 評估框架（Eval Framework）、Benchmark 模式、多代理人 A/B 比較、描述優化（Description Optimization）、能力提升型 Skill（Capability Uplift）、偏好編碼型 Skill（Encoded Preference）、假陽性（false positive）、序列錯誤（sequence error）、觸發精準度（trigger accuracy）從 70% 提升至 90%、Benchmark 量化結果（多消耗 40% token 但減少 70% 人工修正） |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | 評估框架將 skill 開發從「直覺驅動」轉變為「數據驅動工程」：能力提升型 skill 解決基礎模型的能力缺口，其生命週期會隨模型進步而縮短；偏好編碼型 skill 將特定工作流程標準化，具有長期穩定的價值；評估框架的核心邏輯是在 skill 設計完成後，以系統性測試案例驗證行為是否符合預期，而序列錯誤這類「輸出看起來正確但執行順序錯誤」的問題，只有完整的執行記錄（eval transcript）才能揭露。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | （1）文章以 5 個 PR diff 作為 benchmark 樣本，但 5 個案例的統計基礎薄弱，從 3/5 到 4/5 的改善不足以排除隨機因素；（2）描述優化的觸發精準度測試僅基於 10 個樣本（7/10 → 9/10），同樣存在過小樣本問題；（3）文章假設「假陽性比漏報更危險」在所有場景下成立，但在高風險生產環境（如安全漏洞審查），漏報可能更致命，此假設需依情境評估。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | （1）在開發任何新 skill 前，先撰寫至少 5 個涵蓋邊界案例的測試案例，明確定義「好的輸出」的判斷標準；（2）對現有已部署的 skill 執行 Benchmark 模式，量化有無 skill 的通過率差異，用數字說服團隊 skill 的投資回報；（3）對穩定未修改的 skill 執行描述優化，收集 20 個觸發查詢（含不應觸發但關鍵字相似的負例），提升自動載入精準度。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | 能力提升型 vs 偏好編碼型的投資優先順序取決於時間視野：能力提升型 skill 投資有期限（模型進步後須退役），偏好編碼型則隨使用累積複利；從退役成本角度看，最好從偏好編碼型入手，確立評估基礎設施後，再謹慎引入能力提升型。描述優化的時機管理（在 skill 穩定後才執行）是本文最具實踐價值的反直覺建議，貿然在修改期優化描述等於為移動中的目標校準瞄準器，徒增噪音。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：文章提到「評估框架適合二元斷言，不適合品質梯度」——在需要評估輸出品質的 skill（如文件生成、程式碼審查說明）中，有哪些已知的方法可以補充這個盲點？
- **假設**：文章假設序列錯誤只有透過「讀取完整執行記錄」才能偵測，但若 skill 的執行步驟本身設計為產生可驗證的中間輸出，是否可以在不讀取記錄的情況下自動偵測排序問題？
- **證據**：Benchmark 模式宣稱多消耗 40% token 但節省 70% 人工修正，這兩個數字是針對哪個 skill（API 文件生成器）的測量結果？是否適用於其他 skill 類型，還是存在顯著的場景依賴性？
- **觀點**：若從團隊協作角度看，評估測試案例應由 skill 開發者自行設計，還是應由獨立的使用者（潛在的使用方）設計？兩者的盲點各是什麼？
- **後果**：若 skill TDD（先寫測試案例）被廣泛採用，測試案例本身是否會形成一種「需求鎖定」——即 skill 的迭代被測試案例的設計所約束，難以跳脫最初的需求假設？
