---
title: "寫你的第一個簡單 AI Agent — 五個核心原則"
date: 2026-03-26
category: AI
tags:
  - "#ai/agent-architecture"
  - "#ai/beginner-guide"
  - "#productivity/workflows"
source: "https://blogs.cisco.com/ai/writing-your-first-simple-ai-agent-here-are-some-tips"
source_type: article
author: "Yuri Kramarz（Cisco Blogs）"
status: notes
links:
  - "[[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]]"
  - "[[2026-04-01-HARNESSING-CLAUDES-INTELLIGENCE]]"
  - "[[REACT-AGENT-PATTERN]]"
---

## 摘要（Summary）

Cisco 部落格上的入門文章，作者 Yuri Kramarz 用極簡的方式說明 AI Agent 的本質：**Agent 不過是一組「告訴 AI 該如何思考並執行行動」的指令**。它不只是告訴 AI 要做什麼，更是告訴它**如何面對問題**。文章提出建構第一個 Agent 的五個核心原則（身份、邊界、結構化思考、驗證、誠實承認限制），並附上一個可以直接使用的 Document Summarizer Agent 範例——整個範本不到 200 字，可以立即套用在 Claude Code 或 Codex 上。

## 關鍵洞察（Key Insights）

- **Agent 的本質**：把你「最好的決策流程」捕捉成一個可以規模化、且每次執行結果一致的格式
- **模糊的 Agent 產生模糊的結果**：「幫忙處理回饋」vs「分析客戶回饋以挖掘產品改進機會」的差異，就是結果品質的差異
- **多數人的失敗點**：只寫「該做什麼」，沒寫「該避免什麼」——寫下 Agent 做什麼 **以及** 不做什麼，兩者同等重要
- **Observe → Reflect → Act（觀察、反思、行動）**：最可靠的結構化思考模式，強迫 Agent 按順序思考，避免隨機跳躍
- **驗證檢查點**：在產出前自問「我確定嗎？什麼情況會讓這是錯的？」——生產環境表現最好的 Agent 不是最聰明的，而是**會仔細檢查自己工作**的
- **誠實承認限制**：「我無法分析圖片」「我可能遺漏未見對話的上下文」——這不是弱點，是可靠性
- **最好的 Agent 不是最聰明的，而是最清晰的**（The best agents aren't the cleverest, but the clearest）

## 詳細內容（Details）

### 五大核心原則

#### 1. 賦予身份（Give it an identity）

> [!quote]
> 「一個模糊的 Agent 會產生模糊的結果。一個知道『我分析客戶回饋以挖掘產品改進機會』的 Agent，會勝過只是『幫忙處理回饋』的 Agent。」

每個 Agent 都要有明確的目的宣告，哪怕只是一句話，也能幫它找到立足點。

#### 2. 定義邊界（Define the boundaries）

> [!important] 最常見的失敗點
> 多數人只告訴 Agent 要做什麼，卻沒告訴它要**避免**什麼。

最好的 Agent 有明確的邊界：
```
✓ I will summarize documents.
✗ I will not make any recommendations.
```

這種清晰度能防止範圍蔓延（Scope Creep）和幻覺（Hallucination）。

#### 3. 結構化思考（Structure the thinking）

> [!note] 核心模式：Observe → Reflect → Act
> **Observe（觀察）**：事實是什麼？眼前是什麼？
> **Reflect（反思）**：這些事實合起來代表什麼？什麼是意外的？什麼是缺失的？
> **Act（行動）**：根據綜合判斷，正確的輸出是什麼？

當你強迫 Agent 依序經過這個流程，它就會停止隨機跳躍，開始有方法地思考。

#### 4. 完成前驗證（Validate before concluding）

建立一個檢查點（Checkpoint），讓 Agent 自問：
- 這完整嗎？（Is this complete?）
- 這準確嗎？（Is this accurate?）
- 我有信心嗎？（Am I confident?）

#### 5. 誠實承認限制（Be honest about limitations）

> [!tip] 這不是弱點，是可靠性
> Agent 一定會遇到它處理不了的狀況，不能假裝它沒遇到。把誠實內建進設計裡：
> - 「I cannot analyze images.」
> - 「I may miss context from conversations I haven't seen.」
> - 「Complex legal questions require additional review.」

### 完整範本：Document Summarizer Agent

這是文章給的完整可用範本（不到 200 字指令），可直接套用在 Claude Code 或 Codex：

```markdown
AGENT: Document Summarizer

TOOLS: Read, Grep

PURPOSE:
I read text documents and produce clear, concise summaries.

WHAT I DO:
- Read the full document
- Identify the main points and key details
- Produce a summary in 3-5 bullet points
- Note anything unclear or missing

WHAT I DON'T DO:
- Make recommendations
- Add information not in the source
- Summarize images or tables

MY PROCESS:
1. OBSERVE: Read the document completely. Note the main topic,
   key facts, and structure.
2. REFLECT: What's the core message? What details support it?
   What's most important to someone who won't read the original?
3. ACT: Write the summary. Keep it brief. Lead with what matters most.

BEFORE FINISHING:
- Does my summary capture the main point?
- Did I stick to what's actually in the document?
- Would someone understand the original from reading this?

LIMITATIONS:
- Long documents may lose nuance in short summaries
- Technical jargon is simplified; specialists may want more detail
- I summarize what's there, not what should be there
```

### 五個原則在範本中的對應

```
範本區塊                         對應原則
──────────────────────────────────────────
AGENT 標題 + PURPOSE          → 1. 身份（Identity）
WHAT I DO / WHAT I DON'T DO    → 2. 邊界（Boundaries）
MY PROCESS（OBSERVE/REFLECT/ACT）→ 3. 結構化思考（Structure）
BEFORE FINISHING                → 4. 驗證（Validation）
LIMITATIONS                     → 5. 誠實（Honesty）
```

### 真正的啟示（The Real Insight）

> [!quote]
> 「從一個任務開始，寫下你最厲害的人是怎麼想這件事的。建立結構、測試、迭代、實驗。你的第一個 Agent 不會完美，但你會學到**如何把專業翻譯成能產生一致結果的指令**。最好的 Agent 不是最聰明的，而是最清晰的。」

## 我的心得（My Takeaways）

這篇文章的價值在於它把 Agent 建構去神秘化到極致——**Agent 不是什麼玄學，它就是「你最好決策流程」的結構化寫法**。幾個特別有用的切入點：

1. **「寫下不做什麼」的力量**：我以前寫 prompt 時幾乎都只寫「做什麼」，這篇讓我意識到「不做什麼」的清單才是防止幻覺和範圍蔓延的關鍵
2. **Observe → Reflect → Act 的通用性**：這不只是 AI Agent 的框架，也是**人類思考的框架**。可以直接套用在日常對話的 prompt 中，強迫 Claude 先觀察再推理
3. **入門者的 200 字範本**：對比 [[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]] 的 10 步複雜框架，這個 5 原則範本是「**寫第一個 Agent 該從哪裡開始**」的最佳起點

這篇和前面兩篇文章（Karpathy 影片、Anthropic Harness 哲學、Rezvani 10 步框架）形成完整的學習曲線：**入門（這篇）→ 實作（10 步框架）→ 哲學（Anthropic）→ 前沿（Karpathy）**。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 5 個核心原則（Identity / Boundaries / Structure / Validation / Honesty）、Observe-Reflect-Act 模式、Document Summarizer 範本的 6 個區塊（AGENT/TOOLS/PURPOSE/WHAT I DO/WHAT I DON'T DO/MY PROCESS/BEFORE FINISHING/LIMITATIONS） |
| **理解（半被動）** | 解釋概念含義及關聯 | 5 個原則不是獨立的，而是對應到 Agent 生命週期的不同階段：啟動時需要身份與邊界（what & what not），執行中需要結構化思考（how），產出前需要驗證（check），失敗時需要誠實（limits）。每個原則解決一個具體的失敗模式 |
| **分析（主動）** | 檢驗論點、找出假設 | 文章假設「結構化指令能產生可預測行為」——但這在模型能力不足時不成立（模型可能忽略 Process 區塊）。另外「寫下你最好的決策流程」假設專家能清楚表達自己的隱性知識（Tacit Knowledge），而這通常很難 |
| **應用（主動）** | 將知識套用情境 | (1) 為自己日常用 Claude 做的某個重複任務（如週報摘要）寫一份 200 字的 Agent 範本，套用五原則；(2) 把 Observe-Reflect-Act 加入現有的 CLAUDE.md，作為預設思考流程 |
| **評估（主動）** | 判斷方案優劣 | 這 5 原則 vs Rezvani 的 10 步框架：前者是「原則導向」，適合寫第一個 Agent、快速迭代；後者是「工具導向」，適合建構生產環境的多 Agent 系統。入門用前者，規模化用後者。vs Anthropic 的哲學層：這篇教你「怎麼開始」，Anthropic 教你「什麼時候停止做以前在做的事」 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「結構化思考」和「過度指令化」的界線在哪？什麼時候 `MY PROCESS` 變成束縛而非幫助？
- **假設**：五個原則假設使用者自己對任務有清晰的理解——但如果使用者自己都不確定任務邊界呢？這篇文章對此沒有提供建議
- **證據**：文章說「生產環境表現最好的 Agent 不是最聰明的，而是會仔細檢查的」——這個主張有什麼實證支持？有基準測試嗎？
- **觀點**：Anthropic 的 Harness 文章主張「讓 Claude 自己決定要做什麼」，但這篇主張「明確告訴 Agent 該做與不該做」——這兩種哲學在哪些場景衝突？如何調和？
- **後果**：若大量開發者套用這個 200 字範本開始寫 Agent，會不會產生大量「看起來有結構但實際效能平庸」的 Agent？標準化會不會帶來同質化？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** 「誠實承認限制」的 LIMITATIONS 區塊可能變成 Agent **拒絕嘗試**的藉口——明明能做的事因為 prompt 裡寫了「I cannot」就放棄嘗試。這個風險在過度保守的模型（高 alignment）上特別明顯

2. **什麼情況下會失敗？**
   - **任務本身就需要創造性跳躍**（如 brainstorming、藝術創作），強迫 Observe-Reflect-Act 會扼殺發散思維
   - **快速變化的任務環境**，預先寫死的 WHAT I DO / WHAT I DON'T DO 清單跟不上變化
   - **使用者自己沒搞清楚任務**，這時候結構化的 Agent 只會快速產出錯誤答案

3. **有沒有更好的替代方案？**
   - **漸進式 prompt**：從最簡單的 single-line prompt 開始，每次失敗後才加結構。避免過早優化
   - **範例導向（Few-shot）**：給 Agent 3 個好範例和 3 個反例，讓它自己歸納邊界，有時比明確列出規則更有效
   - **混合方案**：用這篇的 5 原則寫骨架，用 Anthropic 的「漸進式揭露」技術讓 Agent 按需載入詳細指令

## 相關連結（Related）

- [[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]] — 進階版：從 5 原則擴展到 10 步工具導向框架
- [[2026-04-01-HARNESSING-CLAUDES-INTELLIGENCE]] — 哲學層：Anthropic 對「什麼時候該減少結構」的觀點，與本文的「增加結構」形成辯證
- [[REACT-AGENT-PATTERN]] — ReAct（Reasoning + Acting）模式，與本文的 Observe-Reflect-Act 高度相關
- [[PROMPT-ENGINEERING-PRINCIPLES]] — 提示工程基本原則
- [[AGENT-BOUNDARIES-DESIGN]] — Agent 邊界設計專題

## References

- [原文](https://blogs.cisco.com/ai/writing-your-first-simple-ai-agent-here-are-some-tips) — Cisco Blogs, Yuri Kramarz, 2026-03-26
- [Claude Code Sub-agents](https://code.claude.com/docs/en/sub-agents) — 文章提到的 Claude Code 子代理文件
- [Codex agents.md](https://developers.openai.com/codex/guides/agents-md/) — 文章提到的 OpenAI Codex agents.md 指南
