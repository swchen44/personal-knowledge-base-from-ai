---
title: "Agent Harness 十二大模組完全解析 — Harness 工程、模型效能影響與七大架構抉擇"
date: 2026-04-24
category: AI
tags:
  - "#ai/harness-engineering"
  - "#ai/agent-architecture"
  - "#ai/multi-agent"
  - "#ai/context-engineering"
  - "#ai/llm"
source: "https://www.youtube.com/watch?v=S36ri23-l60"
source_type: video
author: "大飛"
status: notes
channel: "Best Partners TV"
duration: "23:06"
transcript_method: youtube-transcript-api
links:
  - "[[2026-02-11-HARNESS-ENGINEERING-LEVERAGING-CODEX-IN-AN-AGENT-FIRST-WORLD]]"
  - "[[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]]"
  - "[[2026-04-01-HARNESSING-CLAUDES-INTELLIGENCE]]"
  - "[[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]]"
  - "[[2023-10-27-CREWAI-CODE-ANALYSIS]]"
  - "[[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]]"
---

## 摘要（Summary）

本影片系統性拆解 Agent Harness 的十二大核心模組與七大架構抉擇。Agent Harness 是包裹大型語言模型（LLM）的操作系統級軟體基礎設施，能將無狀態、只會輸出文字的裸模型，變成有目標、會用工具、能糾錯、可持久運行的生產級智能體（Agent）。影片引用 LangChain 實驗證明——完全不改動模型，僅優化 Harness 架構就能讓智能體從排名 30 名外飆升至第 5 名，充分說明 Harness 工程（Harness Engineering）的重要性。影片也比較了 Anthropic、OpenAI、LangGraph、CrewAI、AutoGen 五大框架的設計哲學差異，最後歸納出搭建 Agent Harness 必須面對的七大架構抉擇。

## 關鍵洞察（Key Insights）

- **「如果你不是模型，你就是 Harness」** — LangChain 的 Vivek Trivedi 一語道破：搭建智能體的本質不是創造會思考的 AI，而是搭建一套 Harness 再對接給模型。參見 [[2026-02-11-HARNESS-ENGINEERING-LEVERAGING-CODEX-IN-AN-AGENT-FIRST-WORLD]]
- **Harness 設計差異 > 模型差異** — 相同模型搭配不同 Harness，效能可能天差地別。LangChain 僅優化 Harness 就讓 TerminalBench 2.0 排名從 30 名外升至第 5 名
- **上下文腐爛（Context Rot）是隱形殺手** — 史丹佛研究顯示，關鍵資訊落在上下文視窗（Context Window）中段時，模型效能暴跌 30% 以上。參見 [[2026-04-01-HARNESSING-CLAUDES-INTELLIGENCE]]
- **脚手架隱喻（Scaffolding Metaphor）** — Harness 如同建築脚手架，模型能力越強，Harness 複雜度越應降低。Manus 專案半年重構五次，每次做減法，效能反而提升
- **錯誤的數學殘酷性** — 10 步流程每步 99% 成功率，端到端僅 90.4%，錯誤會雪球式放大

## 詳細內容（Details）

### 為何需要 Agent Harness？

> [!important] 核心問題
> 許多智能體演示時流暢無比，但放到生產環境（Production Environment）立刻翻車。開發者的直覺反應是「模型不行」，但真正的問題出在模型周圍的基礎設施——即 Agent Harness。

LangChain 的實驗打醒了整個行業：完全不改模型權重（Model Weights）和底層演算法，只優化 Harness 架構，就讓智能體在 TerminalBench 2.0 評測中從 30 名外直接飆升至第 5 名。另有研究團隊讓 LLM 自主優化 Harness 架構，任務通過率衝到 76.4%，吊打所有人工設計的系統。

### 三個容易混淆的工程層級

| 層級 | 聚焦 | 範疇 |
|------|------|------|
| 提示工程（Prompt Engineering） | 打磨模型接收的指令 | 單次交互品質 |
| 上下文工程（Context Engineering） | 管理模型在不同階段看到哪些資訊 | 資訊流管理 |
| Harness 工程（Harness Engineering） | 涵蓋前兩者 + 工具編排、狀態持久化、錯誤恢復、驗證迴圈、安全管控、生命週期管理 | 完整應用基礎設施 |

> [!warning] 常見誤解
> Harness 不是「給提示詞套個殼」，而是一套讓自主智能體實現自主思考、自主行動、自主修復的完整系統，是玩具級 Demo 與生產級智能體的本質區別。

### 計算機架構類比

> [!note] 精準類比
> 裸 LLM 就像只有 CPU 的電腦——有核心計算能力但無法獨立完成任務。上下文視窗 = 臨時記憶體（快但有限）；向量資料庫 = 硬碟（大但慢）；工具整合 = 設備驅動程式；Agent Harness = 作業系統。Beren Millidge（2023）指出：「我們透過 Agent Harness 重新發明了馮·諾依曼架構（Von Neumann Architecture）。」

### 十二大核心模組

#### 模組 1：編排迴圈（Orchestration Loop）

智能體的心跳與所有行為的核心引擎。ReAct 迴圈和 TAO（Think-Act-Observe）迴圈都是其具體實現。

**運行邏輯：**
1. 組裝完整提示詞（系統指令 + 工具資訊 + 記憶 + 對話歷史）
2. 發送給模型，等待輸出
3. 解析輸出，判斷是否需要工具調用
4. 執行工具調用，結果回傳模型
5. 重複直到任務完成或觸發終止條件

> [!tip] Anthropic 的「笨迴圈（Dumb Loop）」設計
> 所有智能決策由模型完成，Harness 運行時只負責流程調度，不參與核心推理。模型專注智能輸出，Harness 專注穩定執行，分工明確。

#### 模組 2：工具（Tools）

智能體的「手」，與現實世界交互的唯一途徑。工具以標準化 Schema 形式定義，包含名稱、描述、參數類型、回傳格式。

**工具層職責鏈：** 工具註冊 → Schema 校驗 → 參數提取 → 沙箱執行 → 結果捕獲 → 格式化回傳

| 框架 | 工具體系 |
|------|---------|
| Anthropic Claude Code | 六大類：檔案操作、搜尋、命令執行、網頁存取、程式碼智能、子智能體孵化 |
| OpenAI Agents SDK | 三類：函式呼叫工具、官方託管工具（搜尋/程式碼解釋器/檔案檢索）、MCP 伺服器工具 |

#### 模組 3：記憶（Memory）

跨越時間尺度、保持任務連續性的關鍵。分為短期記憶（單次會話內對話歷史）和長期記憶（跨會話持久化）。參見 [[2026-04-01-HARNESSING-CLAUDES-INTELLIGENCE]]

| 框架 | 長期記憶方案 |
|------|------------|
| Anthropic Claude Code | `claude.md` 專案檔 + 自動生成的 `MEMORY.md` |
| LangGraph | 按命名空間組織的 JSON 儲存 |
| OpenAI | SQLite 或 Redis 會話儲存 |

> [!note] Claude Code 三級記憶層級（業界標杆）
> - **第一層**：輕量級索引（約 150 字元），常駐記憶體，快速響應
> - **第二層**：詳細主題檔案，按需載入
> - **第三層**：原始交互記錄，僅透過搜尋存取
>
> 核心設計原則：智能體不完全依賴記憶，行動前與實際狀態核對驗證。

#### 模組 4：上下文管理（Context Management）

> [!warning] 生產級智能體最容易默默翻車的重災區

**核心痛點：上下文腐爛（Context Rot）** — 史丹佛「Lost in the Middle」研究與 Chroma 團隊實驗印證：關鍵資訊在上下文視窗中段時，效能暴跌 30%+。

**四種應對策略：**

| 策略 | 做法 | 效果 |
|------|------|------|
| 壓縮（Compaction） | 對話歷史做摘要，保留核心決策，丟棄冗餘工具輸出 | 延長有效上下文 |
| 觀察屏蔽（Observation Masking） | 隱藏舊工具輸出細節，保留調用記錄 | 減少 Token，不丟邏輯 |
| 即時檢索（Just-in-time Retrieval） | 維護輕量索引，動態載入所需資料 | 精準高效 |
| 子智能體委派（Sub-agent Delegation） | 複雜任務拆分，只返回精簡摘要 | 大幅降低主智能體壓力 |

> [!quote] Anthropic 上下文工程指南
> 「找到最小的高信噪比 Token 集合，用最少的關鍵資訊最大化實現預期任務效果。」

#### 模組 5：提示詞組裝（Prompt Assembly）

定義模型在每一輪推理中看到的世界，是分層堆疊的結構化過程。

**標準組裝順序：**
1. 系統提示詞 → 身份與核心規則
2. 工具定義 → 可用能力
3. 記憶檔案 → 歷史經驗
4. 對話歷史 → 當前進度
5. 用戶訊息 → 最新需求

OpenAI Codex 採用嚴格優先級棧：伺服器系統訊息 > 工具定義 > 開發者指令 > 用戶指令 > 對話歷史。

#### 模組 6：工具呼叫與結構化輸出（Tool Calling & Structured Output）

模型與 Harness 之間的通用語言。模型直接回傳標準化 `tool_calls` 結構化物件，Harness 解析後判斷：有工具呼叫就執行並繼續迴圈，無工具呼叫就輸出最終答案。

#### 模組 7：狀態與檢查點（State & Checkpointing）

實現斷點續跑、可回溯、可除錯的核心。

| 框架 | 狀態方案 |
|------|---------|
| LangGraph | 類型化字典 + 歸約器合併 + 超級步驟邊界檢查點 |
| OpenAI | 四種互斥策略：應用記憶體 / SDK 會話 / 對話 API / `previous_response_id` 鏈式呼叫 |
| Claude Code | **Git 提交作為檢查點**，進度檔案作為結構化草稿本 |

#### 模組 8：錯誤處理（Error Handling）

> [!warning] 殘酷的數學事實
> 10 步流程，每步 99% 成功率 → 端到端僅 90.4%。錯誤會滾雪球式放大。

**LangGraph 四類錯誤分類（業界典範）：**

| 類型 | 範例 | 處理方式 |
|------|------|---------|
| 瞬時錯誤 | 網路波動、API 限流 | 帶退避策略的重試 |
| 模型可恢復錯誤 | 參數錯誤、邏輯失誤 | 錯誤包裝成工具訊息回傳模型自主調整 |
| 用戶可修復錯誤 | 權限不足、設定錯誤 | 中斷流程等待人工輸入 |
| 意外錯誤 | 系統崩潰 | 直接拋出便於除錯 |

Stripe 的生產級 Harness 將重試次數嚴格限制在兩次以內，避免無限重試耗盡資源。

#### 模組 9：護欄（Guardrails）

智能體的安全紅線，防止越權、有害、違規操作。

**OpenAI SDK 三層防護：**
1. **輸入護欄** — 過濾惡意和違規輸入
2. **輸出護欄** — 確保輸出內容合規安全
3. **工具護欄** — 管控工具呼叫權限

> [!tip] Anthropic 的權限設計
> 在架構上將權限執行與模型推理完全解耦：模型只負責思考「想做什麼」，工具系統負責判斷「能做什麼」。Claude Code 獨立管控約 40 種離散工具能力，三階段把關：專案載入時建立信任 → 每次調用前檢查權限 → 高風險操作需用戶明確確認。

#### 模組 10：驗證與回饋（Verification & Feedback）

玩具級與生產級智能體的分水嶺。

**三種驗證方式：**
1. **規則式回饋** — 測試用例、Linter、型別檢查器等確定性工具
2. **視覺回饋** — Playwright 等工具截圖檢查 UI 效果
3. **模型當裁判** — 獨立子智能體評估主智能體輸出

> [!quote] Boris Cherny（Claude Code 創始人）
> 「給智能體加入驗證自身工作的機制，能讓輸出品質提升 2–3 倍。」

#### 模組 11：子 Agent 編排（Subagent Orchestration）

讓單一智能體升級為智能體集群。參見 [[2023-10-27-CREWAI-CODE-ANALYSIS]]

| 框架 | 子 Agent 模式 |
|------|-------------|
| Claude Code | Fork（父上下文副本）、Teammate（獨立終端通信）、Worktree（獨立 Git 工作樹） |
| OpenAI SDK | Agents-as-tools（專家處理細分任務）、Handoffs（任務全面交接） |
| LangGraph | 嵌套狀態圖（Nested State Graph） |

#### 模組 12：初始化與環境搭建（Initialization & Environment Setup）

所有模組協同工作的起點，定義智能體從啟動到運行的完整生命週期。

**標準執行週期：**

```
提示詞組裝 → 模型推理 → 輸出分類 → 工具執行 → 結果打包 → 上下文更新 → 回到第一步
```

**終止條件（多層級）：** 模型輸出無工具呼叫 / 達最大輪次 / Token 預算耗盡 / 護欄觸發 / 用戶中斷 / 安全拒絕

### 五大框架比較

| 框架 | 設計哲學 | Harness 實現 | 適用場景 |
|------|---------|------------|---------|
| **Anthropic Claude Agent SDK** | 薄 Harness，信任模型 | `query()` + 笨迴圈 + Gather-Act-Verify | 與模型深度耦合，輕量高效 |
| **OpenAI Agents SDK** | 程式碼優先 | `Runner` 類 + 原生 Python 工作流 | 快速開發生產級應用 |
| **LangGraph** | 圖結構設計 | 顯式狀態圖 + `llm_call`/`tool_node` 節點 | 複雜多分支長流程 |
| **CrewAI** | 角色導向多智能體 | Agent-Task-Crew 解耦 + Flows 路由 | 多角色協作任務 |
| **AutoGen** | 對話驅動編排 | 五種編排模式（順序/並發/群組/交接/magentic） | 開放式多智能體互動 |

### 脚手架隱喻與共同進化

Harness 如同建築脚手架——臨時基礎設施，大樓建成後拆除。**模型能力越強，Harness 複雜度應越低。**

- Manus 專案半年重構五次，每次做減法，效能反而提升
- 現代大模型在後訓練（Post-training）階段會將特定 Harness 納入訓練迴圈，模型與框架深度耦合
- **面向未來測試**：模型升級後，智能體效能自然提升，無需增加 Harness 複雜度

### 七大架構抉擇

| # | 抉擇 | 建議 |
|---|------|------|
| 1 | 單智能體 vs 多智能體 | 先榨乾單智能體效能；工具重疊超 10 個或任務域明顯分離才拆分。參見 [[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]] |
| 2 | ReAct 迴圈 vs 計劃-執行迴圈 | ReAct 靈活但每步成本高；Plan-Execute 分離規劃與執行，LLMCompiler 比順序 ReAct 快 3.6 倍 |
| 3 | 上下文管理策略 | 五種方法：時間清理 / 對話摘要 / 觀察遮罩 / 結構化筆記 / 子智能體委派。核心：保留推理痕跡，減少 Token 消耗 |
| 4 | 驗證迴圈設計 | 計算式驗證（測試/Linter）提供確定性 + 推理驗證（模型裁判）解決語義問題，兩者結合最優 |
| 5 | 權限與安全 | 寬鬆模式高效但有風險，嚴格模式安全但低效，依部署場景平衡 |
| 6 | 工具範圍 | 工具越多效能越差。Vercel 砍掉 80% 工具後效能提升。只暴露當前步驟所需的最小工具集 |
| 7 | Harness 厚度 | 薄 Harness 信任模型，厚 Harness 程式碼控制邏輯。模型越強，越該偏向薄 Harness |

## 我的心得（My Takeaways）

這支影片將 Agent Harness 的概念做了系統性整理，十二大模組的分類方式很有參考價值。特別是「笨迴圈」設計哲學——讓 Harness 只做調度、不做推理——值得在自己的 Agent 專案中貫徹。七大架構抉擇中，「工具越多效能越差」和「先榨乾單智能體」這兩點最具實戰指導意義。

## 待補充（Open Questions）

- LangChain 的 TerminalBench 2.0 實驗具體優化了 Harness 的哪些模組？原始論文或部落格連結為何？建議搜尋：`LangChain TerminalBench 2.0 harness optimization`
- 影片提到「LLM 自主優化 Harness 架構，任務通過率 76.4%」，該研究的具體方法論是什麼？是用強化學習（RL）還是程式碼生成？建議搜尋：`LLM self-optimize agent harness architecture 76.4%`
- Manus 專案五次重構的具體減法細節？每次移除了什麼、保留了什麼？建議搜尋：`Manus AI agent harness refactoring simplification`
- Stripe 的生產級 Harness 除了重試限制為兩次外，還有哪些特殊的錯誤處理策略？建議搜尋：`Stripe agent harness production error handling`
- 影片提到模型在後訓練階段會將特定 Harness 納入訓練迴圈，這在實踐中是如何操作的？是在 RLHF 中加入 Harness 互動作為環境嗎？建議搜尋：`post-training harness-aware LLM fine-tuning`

## 相關連結（Related）

- [[2026-06-17-WHAT-IS-LOOP-ENGINEERING-HOW-DIFFERENT-HARNESS-ENGINEERING]] — 對照 Agent Harness 十二模組與 Loop 的 automations / state / sub-agent 控制面分工
- [[2026-02-11-HARNESS-ENGINEERING-LEVERAGING-CODEX-IN-AN-AGENT-FIRST-WORLD]] — OpenAI 官方的 Harness 工程文章，本影片多次引用其概念
- [[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]] — Anthropic 五層 Harness 架構分析，與本影片十二模組分類可交叉對照
- [[2026-04-01-HARNESSING-CLAUDES-INTELLIGENCE]] — Anthropic 官方的上下文工程與智能平衡指南，對應本影片的模組 4、5
- [[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]] — 從零建立 Agent 的實戰框架，可視為本影片理論的實踐版
- [[2023-10-27-CREWAI-CODE-ANALYSIS]] — CrewAI 程式碼深度分析，對應本影片提到的角色導向多智能體架構
- [[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]] — 單智能體 vs 多智能體的實證研究，佐證本影片第一大架構抉擇
- [[2026-05-04-STANFORD-AUGMENTING-LLMS-FIVE-TECHNIQUES-AI-BUILDER-TOOLKIT]] — Stanford 五層分類與 Harness 十二模組互為不同粒度的 agentic system 設計框架

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 十二大模組名稱（編排迴圈、工具、記憶、上下文管理、提示詞組裝、工具呼叫、狀態檢查點、錯誤處理、護欄、驗證回饋、子 Agent 編排、初始化）；「如果你不是模型，你就是 Harness」；上下文腐爛（Context Rot）導致效能暴跌 30% |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Harness 本質是讓裸 LLM 變成生產級智能體的「作業系統」。三層工程層級（提示工程 ⊂ 上下文工程 ⊂ Harness 工程）是包含關係而非並列。脚手架隱喻說明 Harness 與模型的共同進化：模型能力提升 → Harness 應做減法 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 影片預設「模型能力持續快速提升」，因此主張薄 Harness；但若模型進展停滯，厚 Harness 的價值反而會增加。LangChain 實驗僅引用排名變化，未說明具體優化了哪些模組，論證力度不夠完整。五大框架比較偏向概念層，缺乏實際 benchmark 數據支撐 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. 在自己的 Agent 專案中導入「笨迴圈 + 驗證迴圈」設計，確保 Harness 不參與推理、但強制驗證輸出 2. 審計現有工具數量，遵循「最小工具集」原則，移除非必要工具 3. 為長流程任務加入 Git 檢查點機制，實現斷點續跑 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | 薄 Harness vs 厚 Harness 不應僅以「模型強度」為唯一判斷標準，還需考量：可稽核性（Auditability）需求高的企業場景更適合厚 Harness；快速迭代的個人專案更適合薄 Harness。ReAct vs Plan-Execute 的選擇也取決於任務可預測性——高度可預測的流程用 Plan-Execute 省 Token，不可預測的開放式探索用 ReAct 更穩健 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：影片中「Harness」與「Framework」的邊界在哪？LangGraph 既是框架也是 Harness 嗎？還是框架提供建構 Harness 的工具？
- **假設**：影片假設「模型越強 Harness 越薄」，但如果模型的推理能力提升速度遠超其工具使用能力呢？Harness 的哪些模組會最後被模型內化？
- **證據**：「Vercel 砍掉 80% 工具後效能提升」——效能指標是什麼？是任務成功率、延遲還是成本？不同指標下結論可能不同
- **觀點**：若站在「厚 Harness」支持者（如企業合規團隊）的立場，會如何反駁「笨迴圈」設計？在金融、醫療等高風險領域，讓模型做所有決策是否可接受？
- **後果**：若整個行業都朝薄 Harness 方向發展，12 個月後可能出現：(1) 過度依賴特定模型供應商的鎖定風險 (2) 缺乏中間層導致除錯困難 (3) 安全事件增加

## References

- [原文](https://www.youtube.com/watch?v=S36ri23-l60)
