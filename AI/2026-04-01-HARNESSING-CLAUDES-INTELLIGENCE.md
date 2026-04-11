---
title: "駕馭 Claude 的智慧 — 建構平衡智能、延遲與成本的應用程式"
date: 2026-04-01
category: AI
tags:
  - "#ai/agent-architecture"
  - "#ai/context-engineering"
  - "#devtools/claude-code"
  - "#ai/agent-harness"
source: "https://claude.com/blog/harnessing-claudes-intelligence"
source_type: article
author: "Lance Martin（Anthropic Claude Platform 技術人員）"
status: notes
date_uncertain: true
links:
  - "[[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]]"
  - "[[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
  - "[[CONTEXT-ENGINEERING]]"
---

## 摘要（Summary）

這是 Anthropic 官方部落格的重要文章，由 Claude Platform 團隊成員 Lance Martin 撰寫。核心論點：**「Agent 框架（Agent Harness）編碼了對 Claude 能力限制的假設，但這些假設會隨著 Claude 變強而失效。」** 文章提出三個建構 Claude 應用的核心模式：(1) 使用 Claude 已熟悉的工具；(2) 持續問「我能停止做什麼？」；(3) 謹慎設定邊界。核心哲學來自 Anthropic 共同創辦人 Chris Olah 的話——「生成式 AI 系統是長出來的，而不是建造出來的」。

## 關鍵洞察（Key Insights）

- **框架是過時假設的墳場**：Agent Harness 裡每一個「保護 Claude」的機制都是在假設 Claude 某方面不行——但隨著能力升級，這些機制會變成阻礙
- **用 Claude 已熟悉的工具**：Claude Code 只靠 bash + 文字編輯器兩個工具就達到 SWE-bench Verified 49% state-of-the-art；Skills、memory tool、programmatic tool calling 都是這兩個工具的組合
- **讓 Claude 編排自己的動作**：給 Claude code execution tool（如 bash），讓它寫程式碼決定哪些工具輸出要進 context、哪些要過濾——Opus 4.6 在 BrowseComp 從 45.3% → 61.6%
- **讓 Claude 管理自己的上下文**：Skills 的 YAML frontmatter 是「漸進式揭露（Progressive Disclosure）」——只有一行描述載入 context，需要時才讀完整內容
- **讓 Claude 保存自己的上下文**：Compaction 和 memory folder 讓 Claude 自己決定要記什麼；Sonnet 4.5 在 BrowseComp 固定 43%，但 Opus 4.6 相同設定達到 84%
- **快取命中（Cache Hit）五原則**：靜態在前動態在後、用訊息更新而非改 prompt、別切換模型、小心管理工具、更新 breakpoints
- **死重（Dead Weight）會瓶頸效能**：Sonnet 4.5 的「context 焦慮」需要重置——但 Opus 4.5 這問題消失了，之前的補償機制反而變成死重

## 詳細內容（Details）

### 核心哲學：生成而非建造

> [!quote]
> 「生成式 AI 系統像 Claude 是長出來的，而不是建造出來的。研究員設定條件引導成長，但精確的結構或能力並非總是可預測。」— Chris Olah（Anthropic 共同創辦人）

這造成建構 Claude 應用的挑戰：**Agent Harness 編碼了「Claude 不能自己做什麼」的假設，但這些假設會隨 Claude 變強而過時**。甚至本文分享的經驗教訓，也需要頻繁重新檢視。

### 模式一：使用 Claude 已熟悉的工具

> [!important] Claude Code 的極簡主義
> 2024 年末 Claude 3.5 Sonnet 在 SWE-bench Verified 達到 49% state-of-the-art，**只用了 bash 和文字編輯器兩個工具**。Bash 從未被設計用來建構 Agent，但它是 Claude 已經熟悉、並且隨時間越用越好的工具。

以下進階功能都是 bash + text editor 的組合：
- **Agent Skills**（漸進式揭露的任務上下文）
- **Programmatic Tool Calling**（程式化工具呼叫）
- **Memory Tool**（記憶工具）

### 模式二：問「我能停止做什麼？」

#### A. 讓 Claude 編排自己的動作（Let Claude Orchestrate）

**過時的假設**：每個工具結果都必須流過 Claude 的上下文視窗來決定下一步動作。

**問題**：讀一個大表格只為了推理單一欄位——整個表格進入 context，Claude 為每一行它不需要的資料付出 token 成本。

**解法**：給 Claude code execution 工具（bash 或語言特定 REPL）。Claude 寫程式碼表達工具呼叫和邏輯，**只有程式碼執行的輸出會進入 context**。

```
以前的流程：
Tool A → [全部結果進 context] → Claude 決定 → Tool B

新流程：
Claude 寫程式碼 → Tool A → 程式碼過濾/管道 → Tool B → [只有最終結果進 context]
```

**實測數據**：在 BrowseComp 評測中，給 Opus 4.6 過濾自己工具輸出的能力，準確率從 **45.3% → 61.6%**。

> [!note] 這個模式的深意
> 編排決策從 harness 轉移到 model。由於程式碼是 Claude 編排動作的通用方式，**強大的程式設計模型同時也是強大的通用 Agent**。

#### B. 讓 Claude 管理自己的上下文（Let Claude Manage Context）

**過時的假設**：System prompt 應該手工編寫、包含所有任務相關指令。

**問題**：預載指令不可擴展——每個 token 都消耗 Claude 的注意力預算（Attention Budget）；預載很少用到的指令是浪費。

**解法三件組**：

| 機制 | 作用 |
|------|------|
| **Skills** | YAML frontmatter 短描述預載入 context，完整內容透過 read file tool 漸進式揭露 |
| **Context Editing** | 選擇性移除過時或不相關的 context（舊工具結果、thinking blocks） |
| **Subagents** | Claude 決定何時 fork 到新的 context window 隔離工作 |

**實測數據**：Opus 4.6 生成 subagent 的能力，在 BrowseComp 比最佳單 Agent 運行高 **2.8%**。

#### C. 讓 Claude 保存自己的上下文（Let Claude Persist）

**過時的假設**：記憶系統應該依賴模型外的檢索基礎設施（向量資料庫等）。

**解法**：給 Claude 簡單的方式**自己選擇要保存什麼內容**。

1. **Compaction**：Claude 摘要過去的 context 以維持長時程任務的連續性
2. **Memory Folder**：Claude 寫 context 到檔案，之後需要時讀取

**實測數據（BrowseComp，agentic search）**：

| 模型 | 相同 compaction 預算的分數 |
|------|--------------------------|
| Sonnet 4.5 | 43%（對任何 budget 都持平） |
| Opus 4.5 | 68% |
| Opus 4.6 | **84%** |

**BrowseComp-Plus**：給 Sonnet 4.5 memory folder，準確率從 **60.4% → 67.2%**。

> [!example] Pokémon 長時程遊戲的對比
> **Sonnet 3.5（14,000 步後）**：把記憶當成逐字稿，31 個檔案（包括兩個關於毛毛蟲 Pokémon 的近乎重複檔），還卡在第二個城鎮：
> ```json
> caterpie_weedle_info:
> - Caterpie and Weedle are both caterpillar Pokémon.
> - Caterpie is a caterpillar Pokémon that does not have poison.
> - Weedle is a caterpillar Pokémon that does have poison.
> ```
>
> **Opus 4.6（相同步數）**：10 個檔案整理成目錄、3 個道館徽章、從自己失敗中蒸餾的 learnings file：
> ```json
> /gameplay/learnings.md:
> - Bellsprout Sleep+Wrap combo: KO FAST with BITE before Sleep
>   Powder lands. Don't let it set up!
> - Gen 1 Bag Limit: 20 items max. Toss unneeded TMs before dungeons.
> - Spin tile mazes: Different entry y-positions lead to DIFFERENT
>   destinations.
> ```

### 模式三：謹慎設定邊界

#### 設計 Context 以最大化快取命中

Messages API 是無狀態的——Agent Harness 需要在每一輪打包新 context 加上所有歷史動作、工具描述和指令。快取 token 的成本只有基礎輸入 token 的 **10%**。

| 原則 | 描述 |
|------|------|
| **靜態在前，動態在後（Static first, dynamic last）** | 穩定內容（system prompt、tools）放最前面 |
| **用訊息更新（Messages for updates）** | 在訊息中 append `<system-reminder>`，不要編輯 prompt |
| **別切換模型（Don't change models）** | 快取是模型特定的，切換會破壞快取。需要便宜模型就用 subagent |
| **小心管理工具（Carefully manage tools）** | 工具在快取前綴中，新增/移除會失效。動態發現用 **tool search**（append 而不破壞快取） |
| **更新 Breakpoints** | 多輪應用（如 Agent）要把 breakpoint 移到最新訊息——用 **auto-caching** 處理 |

#### 用宣告式工具（Declarative Tools）設定 UX、可觀測性、安全邊界

Claude 不知道應用的安全邊界或 UX 介面。Bash 工具給 Claude 廣泛的程式化控制權，但只給 harness 一個命令字串——每個動作形狀都一樣。

**把動作提升為專用工具（Dedicated Tools）的好處**：
- Harness 得到動作特定的 hook，有型別化參數可以攔截、把關、渲染、稽核
- **不可逆動作**（如外部 API 呼叫）可由使用者確認門控
- **寫入工具**（如 `edit`）可包含 staleness check，防止 Claude 覆寫已變更的檔案
- **UX**：渲染為 modal 顯示問題給使用者
- **可觀測性**：typed tool 給 harness 結構化參數可記錄、追蹤、重播

> [!tip] Claude Code 的 Auto-mode 範例
> Auto-mode（當時研究階段）在 bash 工具外提供安全邊界：讓第二個 Claude 讀命令字串並判斷安全性。這個模式可以**減少專用工具的需求**，但只適用於使用者信任大方向的任務。高風險動作仍需專用工具。

### 展望：刪除死重（Pruning Dead Weight）

> [!warning] 死重會瓶頸 Claude 的效能
> Sonnet 4.5 在長時程任務中會因為感覺到 context 限制即將到來而過早結束（「context 焦慮」）。團隊加了重置機制來處理。**Opus 4.5 這個行為消失了，之前加的補償機制反而變成死重。**

> [!important] 核心問句
> 隨著時間推移，應用中的結構或邊界應該根據這個問題被剪枝：**「我能停止做什麼？」**

## 我的心得（My Takeaways）

這篇文章是 Anthropic 官方對「如何建構 AI 應用」最重要的架構指引之一。最有啟發的幾個點：

1. **「框架是過時假設的墳場」**——這個觀點打破了很多人對「完善的 Agent 框架」的迷思。每一個你為了「保護」Claude 加的機制，都可能在下一代模型中變成瓶頸
2. **Bash 作為通用工具的證明**——Claude Code 用最簡單的工具達到 SOTA，證明「能力 > 工具複雜度」。這對選型決策有直接啟示：**優先選 Claude 已熟悉的工具**
3. **Opus 4.6 比 Sonnet 4.5 在長時程任務的 84% vs 43%**——這個差距極大，說明模型能力對結構性任務的影響遠超預期。花錢升級 Opus 做複雜 Agent 任務是合理的
4. **「我能停止做什麼？」應該是每次模型升級後的常駐問題**——這跟我自己的工作流程很吻合：每次 Claude 變強，應該主動測試哪些老技巧可以丟掉

這篇文章跟 [[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]] 形成有趣對比——後者是「用 Markdown 組裝 Agent」的實作層，這篇是「為什麼組裝要這樣做」的哲學層。兩篇互補閱讀收穫更大。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 三大模式（Use what Claude knows / Ask what you can stop doing / Set boundaries carefully）、Agent Harness、Progressive Disclosure（漸進式揭露）、快取 10% 成本、Context Editing、Dead Weight、BrowseComp/SWE-bench 等評測名 |
| **理解（半被動）** | 解釋概念含義及關聯 | 三個模式有內在邏輯：第一個說「用 Claude 懂的」，第二個說「別替 Claude 做它自己能做的」，第三個說「但該設的邊界還是要設」。核心張力是「給 Claude 自由 vs 設定保護」，關鍵在於這條線會隨模型能力不斷移動 |
| **分析（主動）** | 檢驗論點、找出假設 | 文章假設「模型能力會持續提升」——但這忽略了：(1) 某些能力可能退化（安全對齊後模型變保守）；(2) 不同版本間的能力分布可能不均勻（鋸齒狀能力，參見 Karpathy 筆記）；(3) 企業環境的可重現性需求，與「隨模型變化調整架構」的哲學有衝突 |
| **應用（主動）** | 將知識套用情境 | (1) 審視自己專案中所有 Agent Harness 機制，列出每一個的「假設」，標註哪些在 Opus 4.6 可能已失效；(2) 把系統提示詞中的指令改寫成 Skills（`.claude/skills/*.md`），實現漸進式揭露，減少每輪的 token 消耗 |
| **評估（主動）** | 判斷方案優劣 | Code Execution 編排 vs 傳統 Tool Calling：前者讓模型更自由、效能更好（BrowseComp 16.3% 提升），但可觀測性差、安全邊界模糊；後者結構化、易於稽核，但有 token 浪費和過度打包問題。高自主任務選前者，高合規任務選後者 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Dead Weight」的判斷標準是什麼？如何在不 A/B 測試每個機制的情況下快速識別哪些是過時的補償？
- **假設**：「給 Claude 自己選擇要記什麼」假設 Claude 的選擇判斷總是好的——但 Pokémon 例子顯示 Sonnet 3.5 就是選錯了。在模型選擇能力不足時，這個模式會失效
- **證據**：所有數據都來自 Anthropic 自己的評測（BrowseComp、SWE-bench）。這些評測是否有偏向 Claude 的設計？第三方評測會呈現相同結論嗎？
- **觀點**：若站在 OpenAI/Google 的立場，他們會如何反駁「harness 是死重」的觀點？他們可能會主張結構化的 harness 提供了可觀測性和可重現性，這在企業場景是必要的
- **後果**：若所有團隊都採用「讓 Claude 決定一切」的模式，是否會導致生產系統變得無法偵錯和追蹤？當出問題時，如何還原 Claude 的決策過程？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** 「讓 Claude 自己寫程式碼編排動作」意味著**任意程式碼執行**——在沒有嚴格沙盒的環境中，這是嚴重的安全風險。Claude 寫的程式碼可能意外刪除檔案、外洩資料、或產生 infinite loop 燒 token

2. **什麼情況下會失敗？**
   - **模型能力不足**：Sonnet 3.5 在長時程任務選錯記憶內容，證明這個模式對模型能力有下限要求
   - **需要嚴格可重現性**：金融、醫療等領域需要每次執行都可重現，而 Claude 自主編排引入不確定性
   - **快取設計不當**：若沒有遵循 5 原則，token 成本會失控
   - **沒有 sandbox**：允許 Claude 執行任意程式碼但沒有沙盒隔離

3. **有沒有更好的替代方案？**
   - **混合方案**：關鍵路徑用宣告式工具（安全、可稽核），非關鍵路徑用 code execution（效率、靈活）。Claude Code 的 auto-mode 就是這個思路
   - **其他框架**：LangGraph 的 state machine 模式對複雜有狀態的工作流更合適；本文的模式更適合探索性、無固定流程的任務

## 相關連結（Related）

- [[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]] — 實作層的 Markdown Agent 組裝方法，與本文的哲學層形成互補
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — Claude Code 原始碼中的 Agent 循環、記憶系統、工具設計，驗證本文主張的實作
- [[CONTEXT-ENGINEERING]] — Attention Budget、Progressive Disclosure 等概念的系統化方法論
- [[2026-04-03-KARPATHY-AI-INSANITY-AGENTS-AUTORESEARCH-MODEL-SPECIATION]] — Karpathy 的「Agent 用不好是人的問題」與本文「harness 是死重」觀點呼應
- [[AGENT-HARNESS-DESIGN]] — Anthropic 另一篇關於長時程任務 Agent 設計的文章
- [[2025-10-16-DESIGN-YOUR-SOCRATIC-AI-MENTOR-FRAMEWORK]] — 蘇格拉底式提問框架，與本文「減少結構、讓 AI 自主思辨」的哲學形成互補視角
- [[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]] — Claude Code 記憶系統的原始碼分析，驗證本文「Claude 已內建記憶」的主張
- [[2026-03-26-WRITING-YOUR-FIRST-SIMPLE-AI-AGENT]] — 入門級 Agent 的 5 原則設計，與本文「減少結構」的哲學形成「增加結構 vs 減少結構」的辯證
- [[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]] — Agent 開發實戰踩坑錄，以「重述（Restatement）」機制驗證本文「Claude 需要明確指引而非過度結構」的觀點

## References

- [原文](https://claude.com/blog/harnessing-claudes-intelligence) — Anthropic Blog, Lance Martin
- [Agent Harness Design Long-running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps) — 前置參考文章
- [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Attention Budget 的深入討論
- [claude-api skill](https://github.com/anthropics/skills/tree/main/skills/claude-api) — 文章提到的所有工具和模式的 skill 實作
- [The Urgency of Interpretability](https://www.darioamodei.com/post/the-urgency-of-interpretability) — Chris Olah 關於「AI 是長出來的」的原文
