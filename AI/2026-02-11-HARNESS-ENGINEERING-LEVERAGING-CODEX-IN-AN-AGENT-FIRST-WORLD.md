---
title: "Harness Engineering：在代理人優先（Agent-First）的世界中善用 Codex"
date: 2026-02-11
category: AI
tags:
  - "#ai/agent"
  - "#ai/harness-engineering"
  - "#ai/codex"
  - "#ai/software-engineering"
  - "#productivity/workflows"
source: "https://openai.com/index/harness-engineering/"
source_type: article
author: "Ryan Lopopolo"
status: notes
links:
  - "[[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]]"
  - "[[AI-AGENT-ARCHITECTURE]]"
  - "[[CLAUDE-CODE-SKILLS-DOCUMENTATION]]"
---

## 摘要（Summary）

OpenAI 工程團隊進行了一項為期五個月的實驗：以零行手寫程式碼的方式，完全由 Codex 代理人（Agent）生成約一百萬行產品級程式碼，涵蓋應用邏輯（Application Logic）、測試、CI 設定、文件、可觀測性（Observability）及內部工具。三名工程師的小團隊平均每人每天合併 3.5 個 PR，隨團隊擴展至七人後產出持續增長。這篇文章揭示了「Harness Engineering」的核心理念——工程師的角色從寫程式碼轉變為設計系統、鷹架（Scaffolding）與槓桿（Leverage），讓代理人能有效執行工作。

## 關鍵洞察（Key Insights）

- **人類導航，代理人執行（Humans steer, Agents execute）**——工程師不再直接寫程式碼，而是透過提示（Prompt）引導 Codex，專注於設計開發環境、指定意圖、提供結構化回饋 — 參見 [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]]
- **給代理人地圖，而非千頁說明書**——上下文（Context）是稀缺資源，巨大的指令檔會擠掉任務、程式碼和相關文件，導致代理人遺漏關鍵限制或優化錯誤目標
- **代理人可讀性（Agent Legibility）優先於人類偏好**——程式碼庫（Codebase）中任何不在倉庫上下文中可存取的東西，對代理人而言等於不存在；團隊將所有資訊推入版本控制的產物（Artifact）中
- **架構不變量（Architectural Invariants）取代微管理**——透過機械式規則（Mechanical Rules）與自訂 Linter 確保架構合規，而非逐一審查每個實作

## 詳細內容（Details）

### 核心哲學：零手寫程式碼

團隊運行的核心原則是「No manually-written code」。每一行程式碼——應用邏輯、測試、CI 設定、文件、可觀測性設定與內部工具——全部由 Codex 撰寫。這迫使團隊重新思考工程工作的本質。

> [!note] 關鍵轉變（Key Shift）
> 缺少手動寫碼引入了一種全新的工程工作模式，聚焦在系統（Systems）、鷹架（Scaffolding）與槓桿（Leverage）上。工程團隊的首要工作變成了：讓代理人能做有用的事。

### 倉庫作為知識系統（Repository as Knowledge System）

團隊放棄了龐大的指令文件，採用結構化的文件方式：

- **AGENTS.md**：約 100 行的目錄（Table of Contents），指向更深層資源
- **docs/ 目錄**：包含地圖（Maps）、執行計畫（Execution Plans）、設計規格（Design Specs）、架構決策（Architectural Decisions）
- 這些文件成為代理人操作的單一事實來源（Single Source of Truth）

> [!tip] 可執行建議（Actionable Tip）
> 將知識編碼到版本控制的產物中（程式碼、Markdown、Schema），而非依賴口頭傳遞或外部文件。讓倉庫本身成為完整的知識庫。

### 架構約束與分層模型

OpenAI 強制執行嚴格的依賴流向，使用機械式規則：

**依賴順序**：`Types → Config → Repo → Service → Runtime → UI`

執行機制：
- 結構測試（Structural Tests）驗證架構合規性
- 防止跨層違規（Cross-layer Violations）
- 代理人被限制在已定義的層內操作
- 自訂 Linter 確保每個業務領域遵循嚴格的分層模型

### 黃金原則（Golden Principles）

團隊實施了「黃金原則」——防止模式複製（Pattern Replication）與程式碼漂移（Code Drift）的機械式規則。定期的清理流程如同垃圾回收（Garbage Collection），透過針對性的重構 PR 解決技術債（Technical Debt）。

### 合併哲學的轉變

傳統的阻斷式合併閘門（Blocking Merge Gates）變得適得其反。團隊改採：
- 最小化審查要求
- 短命的拉取請求（Short-lived Pull Requests）
- 透過後續執行而非無限期阻斷來處理測試不穩定（Test Flakes）

### 代理人自主等級

Codex 最終達成了端到端的功能開發能力：

1. 驗證程式碼庫狀態
2. 從遙測資料（Telemetry Data）重現 Bug
3. 實施修復
4. 執行驗證
5. 開啟拉取請求（Pull Request）
6. 回應回饋
7. 合併變更
8. 僅在需要判斷時才升級（Escalate）給人類

### 可讀性工具（Legibility Tools）

工程師讓應用程式和可觀測性堆疊（Observability Stack）對代理人直接可讀：

- **Per-worktree Bootability**：每個工作樹（Worktree）可獨立啟動
- **Chrome DevTools Protocol 整合**：代理人可直接操作瀏覽器
- **本地可觀測性堆疊**：透過 LogQL 和 PromQL 暴露日誌（Logs）與指標（Metrics）
- 單次 Codex 執行有時運作長達六小時處理複雜任務

> [!warning] 注意事項（Watch Out）
> 團隊承認了幾個未知數：完全代理人生成的系統的長期架構一致性（Architectural Coherence）如何維持？隨著模型改進，有效性如何演變？紀律更多展現在鷹架（Scaffolding）而非程式碼本身。

### 開發指標

| 指標 | 數值 |
|------|------|
| 開發時間 | 5 個月 |
| 程式碼行數 | ~1,000,000 行 |
| 合併 PR 數量 | ~1,500 個 |
| 初始工程師數量 | 3 人 |
| 最終工程師數量 | 7 人 |
| 初始每人每日 PR 數 | 3.5 個 |
| 手寫程式碼行數 | 0 行 |

## 我的心得（My Takeaways）

1. **Harness Engineering 的核心不是「讓 AI 寫程式」，而是「設計讓 AI 能穩定交付的系統」**。這與 [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]] 中提到的「Agent = Model + Harness」概念一致——模型之外的運行系統才是決勝關鍵。

2. **文件即基礎設施（Documentation as Infrastructure）**的做法值得借鏡：100 行的 AGENTS.md 作為目錄、docs/ 作為深層知識——這個結構化方式讓上下文窗口（Context Window）的利用效率最大化。

3. **架構約束的機械式執行**（Linter + 分層模型）是防止代理人「創造性破壞」的關鍵防線。沒有這些約束，大量代理人產出的程式碼很快就會架構腐敗（Architecture Decay）。

4. **合併哲學的轉變**特別有啟發性——在代理人大量產出 PR 的世界中，傳統的重度 Code Review 流程成為瓶頸。需要找到品質與速度的新平衡點。

## 相關連結（Related）

- [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]] — 同一概念的中文影片深度解析，涵蓋 Harness 六層架構
- [[CLAUDE-CODE-SKILLS-DOCUMENTATION]] — Claude Code 的 Skill 機制，類似 Harness 中的結構化代理人能力
- [[AI-AGENT-ARCHITECTURE]] — 代理人架構設計的通用框架

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | Harness Engineering、Agent Legibility、Architectural Invariants、Golden Principles、分層模型（Types → Config → Repo → Service → Runtime → UI） |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Harness Engineering 的核心邏輯是：工程師不寫程式碼，而是建構讓代理人能穩定產出的系統。這包含三個支柱——結構化知識（倉庫即知識系統）、機械式約束（Linter + 分層）、可觀測性回饋（代理人可讀的日誌與指標）。三者缺一不可：沒有知識結構，代理人缺乏上下文；沒有約束，架構腐敗；沒有可觀測性，問題無法自主修復。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | **關鍵假設**：(1) Codex 模型能力足以處理所有開發任務——但文章未詳述失敗案例或代理人無法處理的場景比例；(2) 團隊成員都是高水準工程師，能準確設計鷹架——這在一般團隊中未必成立；(3) 五個月的實驗週期可能不足以暴露長期架構退化問題。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | (1) 在自己的專案中建立 AGENTS.md 目錄結構，將口頭知識轉為版本控制的文件；(2) 為 AI 代理人設計分層架構約束與自訂 Linter，防止架構腐敗；(3) 嘗試「短命 PR + 後續修復」的合併策略，取代傳統重度審查流程。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | **優點**：極致的產出效率（3.5 PR/人/天）、迫使知識顯性化、架構約束可累積。**缺點**：零手寫程式碼的極端立場可能犧牲靈活性——某些一次性修復手動更快；高度依賴模型能力，模型退化或 API 不穩定時無備援方案；對工程師的「提示設計」能力要求極高，學習曲線陡峭。**替代方案**：混合模式（80% 代理人 + 20% 手寫）可能是更務實的選擇，保留人類介入的彈性。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「Agent Legibility（代理人可讀性）」與傳統的程式碼可讀性（Code Readability）具體差異在哪？是否需要犧牲人類可讀性來換取代理人可讀性？
- **假設**：本文假設嚴格的分層模型能涵蓋所有業務場景。若遇到需要跨層存取的複雜功能，這個框架如何應對？
- **證據**：文章聲稱約十分之一的傳統開發時間即可完成，但未提供對照組數據。這個倍速估算的可信度如何？
- **觀點**：若站在資深工程師的立場，完全放棄手寫程式碼是否意味著放棄了深入理解系統的能力？長期來看，團隊是否會失去 Debug 複雜問題的直覺？
- **後果**：若 12 個月後團隊全面採用此方法，最可能出現的副作用是：工程師變成「提示工程師」，技術深度下降，對模型的依賴成為單點故障（Single Point of Failure）。

### 方案批判三問（Critical Evaluation）

> [!warning] 適用於技術方案類內容

1. **最大的風險是什麼？** — 完全依賴 AI 代理人產生的程式碼庫可能累積大量「看似正確但邏輯脆弱」的程式碼。當模型無法理解深層業務邏輯時，產出的程式碼可能在邊緣案例（Edge Cases）中失敗，且人類團隊因長期未直接寫碼而缺乏快速定位問題的能力。
2. **什麼情況下會失敗？** — (1) 模型能力退化或 API 服務中斷時，團隊缺乏手動接續的能力；(2) 專案規模超過代理人上下文窗口的有效範圍時，架構決策品質下降；(3) 跨團隊協作時，不同團隊的 Harness 設計不相容導致整合困難。
3. **有沒有更好的替代方案？** — 混合模式（Hybrid Approach）：核心架構決策與關鍵路徑由人類手寫，重複性工作、測試、文件、CI 設定由代理人處理。這保留了人類對系統核心的深度理解，同時獲取代理人的效率優勢。適合的選擇時機：當團隊對代理人能力尚未建立足夠信任時，或業務邏輯極度複雜時。

## References

- [Harness engineering: leveraging Codex in an agent-first world | OpenAI](https://openai.com/index/harness-engineering/)
- [OpenAI Introduces Harness Engineering - InfoQ](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex/)
- [Unlocking the Codex harness: how we built the App Server | OpenAI](https://openai.com/index/unlocking-the-codex-harness/)
- [Unrolling the Codex agent loop | OpenAI](https://openai.com/index/unrolling-the-codex-agent-loop/)
