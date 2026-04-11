---
title: "MacBook Air M5 本地 AI 編程實測：Local LLM 的真實極限在哪裡？"
date: 2026-03-18
category: AI
tags:
  - "#ai/local-llm"
  - "#tools/vibe-coding"
  - "#ai/coding-tools"
  - "#devtools/macos"
  - "#ai/llm"
source: "https://www.youtube.com/watch?v=9oJHV6J-f8Q"
source_type: video
author: "Samuel Gregory"
channel: "Samuel Gregory"
duration: "14:34"
transcript_method: youtube-transcript-api
status: notes
links:
  - "[[2026-01-22-THE-LONGFORM-GUIDE-TO-EVERYTHING-CLAUDE-CODE]]"
  - "[[2026-03-16-BUILD-AGENT-WITH-CLAUDE-CODE-IN-20-MINUTES]]"
  - "[[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]"
---

## 摘要（Summary）

Samuel Gregory 以「MacBook Air M5 全配（32GB RAM）」實測本地 AI 編程（Local AI Coding / Vibe Coding）的可行性。搭配 LM Studio 運行本地 LLM（Qwen 2.5 Coder、DeepSeek），並以 Kilo Code（VS Code 擴充）作為 AI 編程介面。核心結論：**本地模型在 MacBook Air M5 上已有顯著進步，但仍無法應付真正的商業級編程工作**；閉源雲端模型（Anthropic Claude、Codex）仍是嚴肅工作的唯一選擇；開源遠端模型（Miniax、GLM5）是性價比最高的中間地帶。

---

## 關鍵洞察（Key Insights）

- **32GB 是本地 LLM 的實用門檻**：能同時運行多個模型且不超出 VRAM，但 Context Length 仍受限（Qwen 最大 32,768 tokens）— 參見 [[LOCAL-LLM-HARDWARE-REQUIREMENTS]]
- **Context Length > Model Capability**：處理真實 Codebase 時，Context Length 是比模型能力更關鍵的瓶頸
- **速度影響心理狀態**：本地模型的「慢」意外地帶來更深思熟慮的編程節奏，而非只是障礙
- **三層模型選擇策略**：本地免費（Qwen/DeepSeek）→ 開源遠端（Miniax/GLM5）→ 閉源前沿（Claude/Codex），成本與能力遞增
- **Kilo Code 的 Profile 系統**：可為 Architect、Code 等不同模式指定不同模型，實現混合策略

---

## 詳細內容（Details）

### 一、硬體與環境設定

**測試機器**：MacBook Air M5
- 32GB RAM（VRAM 共用）
- 10 Core GPU
- 無風扇設計（散熱全靠機身導熱）

**軟體工具鏈**：

```
LM Studio（模型管理 + 本地 API 伺服器）
    ↓
localhost:1234（OpenAI 相容 API）
    ↓
Kilo Code（VS Code 擴充，AI 編程介面）
    ↓ Profile: Local LM → Provider: LM Studio
實際編程工作
```

> [!note] LM Studio vs Ollama
> - **LM Studio**：更多控制選項，有 Dev Mode，GUI 介面直覺
> - **Ollama**：同時支援本地模型 + 雲端模型，指令行友好，但靈活性略低
> 兩者都可輸出 OpenAI 相容的本地 API，Kilo Code 原生支援 LM Studio 作為 Provider

### 二、測試的三個模型

| 模型 | 大小 | Context Length | 特性 |
|------|------|----------------|------|
| Qwen 2.5 Coder | ~18GB | 32,768 tokens | 程式碼能力強，Context 較短 |
| DeepSeek | — | 163,000 tokens | Context 長，適合大型 Codebase |
| Miniax | — | — | 開源遠端模型，速度快，Style 整合好 |

> [!important] Context Length 是真正的關鍵
> Qwen 在嘗試處理真實 Codebase 時遭遇「number of tokens greater than context length」錯誤。這不是模型能力問題，而是**Context Window（上下文視窗）限制**。DeepSeek 的 163K tokens 解決了這個問題，但犧牲了部分模型能力。

### 三、實測結果

**任務一：詢問 Codebase 概況（`What does this codebase do?`）**
- Qwen 25% Prompt 處理需約 3–5 分鐘（M1 Max 相同任務需 15 分鐘）
- 機身溫熱但不燙手
- 結論：**有顯著改善，但仍慢**

**任務二：修復 Bug（投入真實錯誤訊息）**
- 遭遇 Context Length 錯誤，切換至 DeepSeek
- 工作過程感受：「像在 Flow State 中，只是節奏慢了下來」
- 偶發滑鼠卡頓，但整體運行穩定
- 結論：**能工作，但效率不足以應付商業進度**

**任務三：生成單一 HTML 檔案（Terms & Conditions 頁面）**
- 全新 Context，不需讀取整個 Codebase
- 幾秒內開始回應，快速生成
- 後用 Miniax 補充 CSS 樣式
- 結論：**簡單獨立任務表現良好**

> [!warning] 「測試偏差」陷阱
> 影片特別指出：很多非開發者測試本地 LLM 時，只是「請它生成一頁 HTML 模擬器」，這完全無法反映真實開發工作的需求（需要 Context、需要理解 Codebase、需要連續多輪互動）。

### 四、Kilo Code Profile 系統的混合策略

```
Kilo Code Profiles（多模型混合配置）
├── Architect Mode → 用 Claude Opus（雲端，高推理能力）
├── Code Mode → 用 Local LM（本地，快速執行）
└── Ask Mode → 用 DeepSeek（本地，長 Context）
```

> [!tip] 實用混合策略
> 用本地模型處理**執行層**任務（寫程式碼、格式化、重構），用雲端模型處理**架構層**任務（設計決策、複雜 Debug）。這樣既能降低成本，又能在關鍵時刻保持高品質。

### 五、最終評估

**本地 LLM 在 MacBook Air M5 的適用場景**：

✅ **適合**：
- 簡單的獨立任務（生成單頁 HTML、寫測試、格式化）
- 不急迫的側線任務（想法探索、文件撰寫）
- 完全私密的需求（不能送到雲端的程式碼）
- 學習和實驗

❌ **不適合**：
- 處理大型真實 Codebase
- 商業進度壓力下的開發工作
- 需要高度複雜推理的架構決策

**三層模型選擇建議**：

```
本地模型（Qwen/DeepSeek）
    ↑ 速度慢，但完全免費且私密
    
開源遠端模型（Miniax, GLM5）
    ↑ 速度快，免費或低成本，好的中間地帶
    
閉源前沿模型（Claude Opus, Codex）
    ↑ 最貴，但嚴肅工作的唯一可靠選擇
```

---

## 我的心得（My Takeaways）

1. **Context Length 比 Model Size 更重要**：在實際工作中，能不能讀懂整個 Codebase 遠比模型有多「聰明」更關鍵。這應該成為評估本地模型的第一指標。

2. **速度的心理效應**：影片最有洞察力的觀察是「慢速模型讓人慢下來思考」。這讓我重新思考：AI 回應越快，是否反而讓人進入「勉強接受輸出」的慣性？刻意的慢可能反而促進更深思熟慮的協作。

3. **Kilo Code 的 Profile 混合策略值得採用**：架構用 Claude，執行用本地，這個混合策略非常務實。可以立即在我的工作流程中實施。

4. **Miniax/GLM5 是被低估的選項**：如果不需要完全本地化，開源遠端模型提供了一個很好的中間地帶，值得更深入了解。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本影片的具體應用 |
|---------|---------|----------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | MacBook Air M5（32GB）、LM Studio、Kilo Code、Qwen 2.5 Coder（32K Context）、DeepSeek（163K Context）、Miniax；Context Length 是關鍵限制 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | 本地 LLM 受限於 VRAM 決定可運行的模型大小，Context Length 決定能否處理真實 Codebase，速度則決定工作效率。三者共同決定「本地 AI 編程」的可行性邊界。MacBook Air M5 在 VRAM 上達到可用門檻，但 Context Length 和速度仍有落差。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維，看透策略底層邏輯 | 影片隱含假設：「好的 AI 編程 = 快速回應 + 大 Context」。但這忽略了：1) 本地模型的隱私優勢在商業情境中的具體價值；2) 「慢速帶來的更深思考」可能並非偶發，而是設計性的工作節奏；3) 測試任務（修 Bug、生成獨立頁面）並不代表全部開發工作類型 |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力，將理論轉為行動 | **行動一**：在 Kilo Code 建立 Profile 混合策略——Code Mode 用本地 Qwen（快速執行、免費），Architect Mode 用 Claude（複雜決策）；**行動二**：評估 Miniax/GLM5 作為「開源遠端模型」的中間選項，測試能否替代部分 Claude 用量；**行動三**：下次任務開始前先評估是否需要完整 Codebase Context，若否則切換至本地模型 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡，在不確定的情境中做出最佳選擇 | **優點**：影片誠實呈現限制，不過度吹噓；三層模型策略框架有實用性。**缺點**：測試時間只有一小時，缺乏系統性 Benchmark 數據；未測試 Context Length 上限後的降級策略。**vs 替代方案**：相比「全用雲端」更私密但更慢；相比「等更強硬體」更即時但能力受限。最佳策略應是根據任務性質動態切換，而非固定使用單一模型 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：影片提到「Context Length 是最關鍵因素」，但 Context Length 和模型推理能力之間的取捨如何量化？在什麼條件下，較短的 Context 但更強的推理能力反而更好？
- **假設**：影片假設「閉源模型 = 最佳編程能力」。但如果開源遠端模型（如 DeepSeek R2）的推理能力已與 Claude 相當，這個假設是否還成立？
- **證據**：影片的評估基於一小時的主觀體驗，缺乏客觀 Benchmark。有哪些現有的本地 LLM 編程 Benchmark（如 HumanEval、SWE-Bench）可以補充這個評估？
- **觀點**：若站在「強隱私需求的企業用戶」立場，本地模型的「慢」是否根本不是問題，而是可接受的成本？這種情境下，評估標準應該如何改變？
- **後果**：若未來 MacBook Air M6 將 RAM 擴展至 64GB，本地 AI 編程的可行性門檻會如何改變？哪些現在「不可能」的任務會變得「可能」？

---

## 相關連結（Related）

- [[2026-01-22-THE-LONGFORM-GUIDE-TO-EVERYTHING-CLAUDE-CODE]] — 對比閉源模型（Claude）的進階使用策略，理解為何閉源模型仍是嚴肅工作的選擇
- [[2026-03-16-BUILD-AGENT-WITH-CLAUDE-CODE-IN-20-MINUTES]] — 從提示工程到實際 Agent 部署，理解完整 AI 編程工作流
- [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — Kilo Code Profile 混合策略的延伸：如何在不同工具中管理多模型配置

## References

- [Local AI Coding on MacBook Air M5 — YouTube](https://www.youtube.com/watch?v=9oJHV6J-f8Q)
- [Kilo Code 官網](https://kilocode.ai/)
- [LM Studio 官網](https://lmstudio.ai/)
- [Ollama 官網](https://ollama.ai/)
