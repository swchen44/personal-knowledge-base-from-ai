---
title: "做 AI Agent 最痛苦的事：明明看了很多教程，最後還是做不對"
date: 2026-04-07
category: AI
tags:
  - "#ai/agent"
  - "#ai/context-engineering"
  - "#ai/architecture"
  - "#productivity/lessons-learned"
source: "https://www.youtube.com/watch?v=eWFKPPgHMCw"
source_type: video
author: "数字黑魔法"
status: notes
channel: "数字黑魔法"
duration: "19:49"
transcript_method: yt-dlp
links:
  - "[[CONTEXT-ENGINEERING]]"
  - "[[AI-AGENT-ARCHITECTURE]]"
  - "[[SKILL-DYNAMIC-INJECTION]]"
---

## 摘要（Summary）

這部影片是 AI Agent 開發者歷經三個月反覆踩坑後的真實復盤。作者分享了從「教科書式架構」到「真正有效架構」的演化過程，揭示一個核心洞察：**許多教程給你的是抽象好的結果，但沒有告訴你他們怎麼淌過這趟渾水**。影片以「如何生成講解影片的 AI Agent」為案例，深度拆解三個架構迭代階段，並提出「重述（Restatement）」作為解決長任務不穩定的核心機制。

---

## 關鍵洞察（Key Insights）

- **Plan-and-Execute 是工作方式，不是強制的架構形態** — 不要把它自動翻譯成「必須有一個 Planner Agent + 一個 Executor Agent」的三層架構
- **子 Agent（Sub-Agent）有兩種：冗餘的和必要的** — 第一次刪掉是對的（因為它是架構強迫症），第二次加回來也是對的（因為需要上下文隔離），形式相同但理由完全不同
- **Skill（技能）的本質是動態提示詞注入（Dynamic Prompt Injection）** — 它暴露了原本子 Agent 的冗餘性，因為從頭到尾都是同一個 Agent 在工作，天然繼承上下文 → 參見 [[SKILL-DYNAMIC-INJECTION]]
- **重述（Restatement）是長任務穩定性的核心控制手段** — 不只要告訴模型「下一步是什麼」，還要反覆提醒「下一步要怎麼做」
- **KV Cache 決定 Restatement 的位置** — 靜態規則放 SystemPrompt，動態資訊追加到上下文尾端
- **不要因為熱門專案用了某個框架就跟著用** — 先問自己：我的系統真的需要這個東西嗎？

---

## 詳細內容（Details）

### 三個月的割裂感（Disconnect）

作者描述 AI Agent 開發的矛盾現象：
- 行業每天往前衝，Context Engineering → Skill → Harness，新名詞不斷
- 自己寫的 Agent 卻還是「慢、笨、不穩定、不按設計跑」
- 每次看到新架構都期待能解決所有問題，用上去才發現毫無改變

> [!note] 核心問題所在
> 教程把「已抽象總結好的東西」拿出來展示，但沒有告訴你他們**怎麼反覆迭代、踩坑爬出來**才得到這個架構。

---

### 第一次架構迭代：發現 Plan-and-Execute 的誤解

**初始架構**：主 Agent（Orchestration Layer）+ 設計 Sub-Agent + 編碼 Sub-Agent

**發現的問題**：

1. **小改動成本太高** — 改一行程式碼也要走完整流程（主 Agent → 分發 → Sub-Agent 執行）
2. **主 Agent 越權** — 明明只負責編排，卻忍不住自己動手修改程式碼，無論怎麼在提示詞中強調職責邊界都無效

**根本誤解**：

> [!warning] 架構強迫症（Architecture OCD）
> 一聽到「Plan and Execute」就自動翻譯成「必須有清晰切分的 Planner 和 Executor 組件」。實際上，Plan-and-Execute **是 Agent 的工作方式，不是系統必須遵守的組織架構**。

觀察 OpenCode 的真實架構後發現：主 Agent 既能寫程式碼，又能做編排；Sub-Agent 也能寫程式碼。這種「重複」在教科書裡看起來是問題，實際上是合理的設計。

---

### 第二次架構迭代：用 Skill 取代 Sub-Agent

**實驗**：把 Design Sub-Agent 和 Coding Sub-Agent 的系統提示詞直接變成 Skill，在原來調用 Sub-Agent 的地方改為動態注入 Skill。

**結果**：

- 整體效能沒有下降，複雜任務反而有所提升
- Token 開銷變小
- 原來子 Agent 之間的通信成本（如何讓 Sub-Agent 看到圖片？如何傳遞搜尋結果？）直接消失

> [!tip] Skill 的核心價值
> 不是「Skill 很厲害可以取代 Sub-Agent」，而是「Skill 暴露了原本的 Sub-Agent 本來就是冗餘設計」。從頭到尾都是同一個 Agent 工作，天然繼承整個上下文。

**架構壓平**：多層通信鏈路 → 單一 Agent + 動態 Skill 注入，系統更輕、更順、更便宜。

---

### 重述（Restatement）機制：解決長任務的兩大問題

**問題一：上下文焦虑（Context Anxiety）**

長任務到後期，模型會開始「趕工」——生成速度越來越快、程式碼越來越短、步驟越來越潦草。根本原因：上下文視窗（Context Window）越來越長，模型感受到「快到底了」的壓力。

**問題二：Skill 約束失效**

已寫好的規則和流程在任務後期開始失效，模型忘記了 Skill 裡的具體要求。

**解決方案：Restatement（重述）**

> [!important] Restatement 的核心原則
> 不只告訴模型「下一步是什麼」，還要反覆提醒「下一步要**怎麼**做」。週期性地把 Skill 裡的關鍵規則重新拿出來再說一遍。

**注意力高地的兩個位置**：
1. SystemPrompt（始終可見）
2. 最新生成內容的後面（上下文尾端，離當前輸出最近）

```
注意力分布示意：

[SystemPrompt] ◄──── 注意力高地（靜態規則放這裡）
[...長長的中間上下文...]
[最近生成的內容]
[Restatement 追加] ◄── 注意力高地（動態資訊放這裡）
[模型現在要生成的內容]
```

**KV Cache 工程考量**：

| 資訊類型 | 放置位置 | 原因 |
|---------|---------|------|
| 靜態規則（程式碼風格、輸出格式） | SystemPrompt | 始終可見，不會觸發重新計費 |
| 動態資訊（計劃、ToDoList、Skill 關鍵規則） | 上下文尾端（追加） | 避免修改前段導致整條快取鏈重算 |

> [!warning] ToDoList 不夠用
> 有了 ToDoList 只知道「做到第幾步、下一步是什麼」，但可能**忘記**你特別在意的事情（如「程式碼輸出不能合併、不能偷懶」）。需要同時 Restate 步驟 **和** 關鍵執行規則。

---

### 第三次架構迭代：把 Sub-Agent 以不同理由帶回來

**新問題：程式碼同質化**

因為 Agent 是創意工具，希望每段程式碼都有獨立思考。但實際情況是：第一段用了某個框架，後面的 Agent 就認為「照著寫就行」，越來越失去獨立判斷。

**這次問題的方向相反**：
- 之前（Restatement 解決的）：**該看到的資訊沒被看到**
- 現在：**不該看到的資訊被看到了**

**解決方案**：重新引入 Sub-Agent，但理由完全不同

> [!note] 兩種 Sub-Agent 的本質差異
> | | 第一次的 Sub-Agent | 第三次的 Sub-Agent |
> |--|--|--|
> | **原因** | 架構強迫症（Plan/Execute 分層） | 必要的上下文隔離（Context Isolation） |
> | **移除後** | 系統更輕更順更便宜 ✅ | 系統變得更差 ❌ |
> | **本質** | 冗餘設計 | 必要設計 |

新的 Sub-Agent 搭配 Restatement：只把「需要看到的資訊」注入到 Sub-Agent 的上下文，同時**屏蔽掉不應該看到的東西**（如之前已生成的程式碼）。

---

### 最終架構演化路徑

```
初始：主 Agent (Orchestration) + Sub-Agent × N
  ↓ 發現：職責越權 + 小改動成本高
第一次迭代：Skill 動態注入（壓平架構）
  ↓ 發現：程式碼同質化（Context 污染）
第二次迭代：主 Agent + Sub-Agent（上下文隔離用途）
  + Restatement 機制貫穿全程
```

**表面上回到原點，但背後依據完全不同。**

---

### 對新概念的態度

> [!tip] 避免「熱門框架焦慮」
> - Skill、Harness、Context Engineering 等概念，在某些場景被驗證有效
> - 但對你的專案是否有效，只有你自己最有發言權
> - **先問**：我的系統真的需要這個東西嗎？
> - **不要**：因為熱門專案用了某個框架就跟著用

---

## 我的心得（My Takeaways）

1. **架構設計要回答「為什麼」**，而不是「看起來對不對」。同樣形式的子 Agent 架構，可能是冗餘設計，也可能是必要設計——關鍵是背後的理由。

2. **Restatement 是一個值得深入研究的工程模式**。長任務的穩定性問題，本質上是注意力管理問題，而不只是「記憶系統」的問題。

3. **KV Cache 意識**：在設計提示詞和上下文管理時，要考慮靜態 vs 動態資訊的放置位置，這直接影響成本和效果。

4. **踩坑過程本身就是最有價值的學習**——這個影片做到了教程做不到的事：展示了「怎麼一次次迭代爬出泥潭」。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | Plan-and-Execute、Skill（動態提示詞注入）、Restatement、KV Cache、Context Isolation、Sub-Agent 的兩種本質 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Skill 不是取代 Sub-Agent，而是暴露了 Sub-Agent 的冗餘性；Restatement 解決的是注意力管理問題，不是記憶系統問題；兩次 Sub-Agent 設計形式相同但依據完全不同 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維，看透策略底層邏輯 | 作者的假設：「職責邊界清晰 = 好架構」是架構強迫症；未論及：Restatement 的頻率如何決定？過度 Restatement 會不會帶來新的 Token 浪費？ |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力，將理論轉為行動 | 1. 在長任務結尾前週期性追加 Skill 關鍵規則到上下文尾端；2. 重新審查現有 Sub-Agent：它是為了架構美觀，還是真的解決了上下文隔離問題？ |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡，在不確定的情境中做出最佳選擇 | 優點：基於真實迭代而非理論，有說服力；限制：案例特定於「生成影片的 AI Agent」，創意類任務對獨立性要求更高，不一定適用於所有 Agent 場景 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「Restatement」的定義是什麼？是每個步驟都要重複，還是只在特定觸發條件（如任務進行到 X% 時）才重複？如何精確化重複的時機與內容？
- **假設**：本文論點成立的關鍵前提是「單一 Agent 長任務」。若 Agent 任務很短（< 5 步），Restatement 的必要性如何改變？
- **證據**：作者說「用 Skill 後效能沒下降甚至提升」——這個比較是在相同任務上的 A/B 測試，還是主觀感受？有量化數據嗎？
- **觀點**：從反對者角度，「Sub-Agent 冗餘論」是否過度簡化？Sub-Agent 除了避免重複外，還有隔離故障域、並行執行等優點，這些在作者的案例中是否被忽略了？
- **後果**：若廣泛採用「Restatement + 壓平架構」，12 個月後可能出現什麼副作用？例如：隨著任務越來越複雜，單一 Agent 的上下文視窗會不會成為新瓶頸？

### 方案批判三問（Critical Evaluation）

> [!warning] 針對「壓平架構 + Restatement」方案的批判

1. **最大的風險是什麼？** — 在長任務中過度依賴 Restatement，可能導致上下文大量重複，Token 成本反而超過原本分層架構的通信成本；且若 Restatement 的內容選擇不當，可能反而加劇模型的注意力偏移。

2. **什麼情況下會失敗？**
   - 任務需要多個 Agent **並行**執行（壓平架構本質是串行）
   - 任務涉及的上下文太長，超過單一 Agent 可有效管理的範圍
   - 任務不是「創意生成」類，而是「精確執行多步骤」類，此時上下文繼承反而可能引入干擾

3. **有沒有更好的替代方案？**
   - **Memory System + RAG**：把歷史生成結果做摘要存入向量記憶庫，Sub-Agent 只檢索必要的相關片段，而非注入全量上下文——這樣既保留了上下文隔離，也避免了全量上下文污染
   - 何時選替代方案：當任務規模大到單一 Agent 上下文視窗無法承載時

---

## 待補充（Open Questions）

- Restatement 的最佳觸發時機如何量化決定？是固定步驟數、上下文視窗使用率百分比，還是其他動態指標？業界有無對 Restatement 頻率的實驗數據？（建議搜尋：`LLM agent restatement frequency context window strategy`）
- 當任務需要多個 Agent 並行執行時，「壓平架構」本質上是串行的這個限制如何克服？並行 Agent 的上下文同步問題有哪些現有解法？（建議搜尋：`parallel agent context synchronization coordination`）
- Memory System + RAG 作為替代方案，在創意生成類任務中的實際效果如何？向量記憶庫對「上下文污染」問題的改善程度有量化比較嗎？（建議搜尋：`RAG agent creative generation context pollution benchmark`）
- KV Cache 的具體成本模型是什麼？在不同模型提供商（OpenAI、Anthropic、Google）上，「修改前段導致整條快取鏈重算」的計費影響有多大？（建議搜尋：`KV cache cost model prompt caching pricing`）
- 本文案例特定於「創意影片生成 Agent」——對「精確多步驟執行」類任務（如資料庫遷移、部署流程），壓平架構與分層架構的優劣比較是否有其他研究？（建議搜尋：`agent architecture deterministic tasks vs creative tasks`）

## 相關連結（Related）

- [[CONTEXT-ENGINEERING]] — 本影片核心依賴的上下文管理概念
- [[AI-AGENT-ARCHITECTURE]] — Plan-and-Execute、Orchestration 等架構模式
- [[SKILL-DYNAMIC-INJECTION]] — Skill 動態注入的具體機制與應用
- [[KV-CACHE-OPTIMIZATION]] — KV Cache 對提示詞設計的工程影響
- [[2026-04-12-HARNESS-ENGINEERING-HUNGYI-LEE-NTU-LLM-GUIDANCE]] — 李宏毅用 Gemma 4 E2B 展示小模型的可能性，與 Agent 落地痛點形成對比
- [[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]] — Stanford 論文以 DPI 理論證明 Sub-Agent 冗餘可能只是浪費令牌，為本文踩坑經驗提供理論支撐

## References
- [YouTube 影片](https://www.youtube.com/watch?v=eWFKPPgHMCw)
- 頻道：数字黑魔法
