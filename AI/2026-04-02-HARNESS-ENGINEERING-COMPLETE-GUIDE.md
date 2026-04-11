---
title: "Harness Engineering 完全解析：從 Prompt 到 Context 再到 Harness 的 AI 工程演進"
date: 2026-04-02
category: AI
tags:
  - "#ai/agent"
  - "#ai/harness-engineering"
  - "#ai/prompt-engineering"
  - "#ai/context-engineering"
  - "#ai/llm"
source: "https://www.youtube.com/watch?v=3DlXq9nsQOE"
source_type: video
author: "歡老師"
channel: "code秘密花園"
duration: "18:30"
transcript_method: manual
status: notes
links:
  - "[[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
  - "[[2026-03-14-OPENCLI-CODE-ANALYSIS]]"
  - "[[AI-AGENT-ARCHITECTURE]]"
---

## 摘要（Summary）

本影片系統性講解了 AI 工程領域的三次重大範式轉移：**提示詞工程（Prompt Engineering）→ 上下文工程（Context Engineering）→ 馬具工程（Harness Engineering）**。這三者是層層包含的關係，分別解決「表達」「信息」「執行」三個層次的問題。影片深入拆解了成熟 Harness 的六層架構，並以 Anthropic 和 OpenAI 的真實工程實踐為案例，說明為何同樣的模型在不同產品中表現差距巨大——關鍵不在模型本身，而在模型外面那套運行系統。

## 關鍵洞察（Key Insights）

- **Agent = Model + Harness**：在一個 Agent 系統中，除了模型本身以外，幾乎所有決定它能不能穩定交付的東西都算 Harness
- **三者是包含關係，非替代關係**：Prompt 是 Context 的一部分，Context 是 Harness 的一部分
- **當 Agent 出問題時，修復方案幾乎從來不是「更努力」，而是確定它缺了什麼結構性能力** — 參見 [[AI-AGENT-ARCHITECTURE]]
- **上下文窗口（Context Window）是稀缺資源**：信息越多注意力越分散，應按需暴露、分層給予

## 詳細內容（Details）

### 一、三次範式轉移

#### 1. 提示詞工程（Prompt Engineering）

> [!note] 核心定義
> 解決「表達」的問題。本質不是命令模型，而是**塑造一個局部的概率空間（probability space）**。

- **目的**：確保模型聽懂你在說什麼
- **做法**：角色設定、風格約束、Few-shot 範例、分步引導、格式規範
- **天花板**：無法憑空彌補缺失的知識、管理動態信息、處理長鏈路狀態

#### 2. 上下文工程（Context Engineering）

> [!note] 核心定義
> 解決「信息」的問題。系統必須在**合適的時機把正確的信息送進去**。

- **Context 的工程意義**：所有影響模型當前決策的信息總合（用戶輸入、歷史對話、檢索結果、工具返回、任務狀態、中間產物、系統規則、安全約束、其他 Agent 傳遞的結果）
- **Prompt 只是 Context 的一部分**
- **Agent Skills 是上下文工程的高級實踐**：不一次性全給，而是按需暴露、分層給予

> [!tip] 關鍵原則：漸進式暴露（Progressive Disclosure）
> 不是一開始就把所有能力全部給模型看，而是只給最少量的原型，等它真正要觸發某些能力時，再把那部分的 SOP、詳細參數、腳本動態加進來。

#### 3. 馬具工程（Harness Engineering）

> [!note] 核心定義
> 解決「執行」的問題。當模型從回答問題走向執行任務，系統不只要負責餵信息，還要能**駕馭整個過程**。

- **核心公式**：`Agent = Model + Harness`，`Harness = Agent - Model`
- **解決的核心挑戰**：當模型開始連續行動時，誰來監督、約束和糾偏它？

### 二、成熟 Harness 的六層架構

```
┌─────────────────────────────────────────────────┐
│  第六層：約束、校驗、失敗與恢復                     │
│  Constraints, Validation, Failure & Recovery     │
├─────────────────────────────────────────────────┤
│  第五層：評估與觀測                                │
│  Evaluation & Observation                        │
├─────────────────────────────────────────────────┤
│  第四層：記憶與狀態                                │
│  Memory & State Management                       │
├─────────────────────────────────────────────────┤
│  第三層：執行編排                                  │
│  Execution Orchestration                         │
├─────────────────────────────────────────────────┤
│  第二層：工具系統                                  │
│  Tool System                                     │
├─────────────────────────────────────────────────┤
│  第一層：信息邊界（上下文管理）                      │
│  Information Boundary (Context Management)        │
└─────────────────────────────────────────────────┘
```

| 層級 | 核心問題 | 關鍵設計 |
|------|---------|---------|
| **第一層：信息邊界** | 模型看到什麼？ | 角色/目標定義、信息裁剪與選擇、結構化組織（規則/任務/狀態/證據分層） |
| **第二層：工具系統** | 給什麼工具、何時調用？ | 工具數量控制、調用時機判斷、結果提煉與篩選 |
| **第三層：執行編排** | 下一步做什麼？ | 理解目標→判斷信息→補充→分析→生成→檢查→修正的完整軌道 |
| **第四層：記憶與狀態** | 做過什麼、還差什麼？ | 區分「當前任務狀態」「會話中間結果」「長期記憶/用戶偏好」 |
| **第五層：評估與觀測** | 做得好不好？ | 輸出校驗、環境驗證、自動測試、日誌與指標、錯誤歸因 |
| **第六層：約束與恢復** | 出錯怎麼辦？ | 行為禁令、輸入/輸出校驗、失敗重試/路徑切換/回滾機制 |

### 三、一線公司的真實實踐

#### Anthropic 的實踐

> [!info] 官方文章
> - [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) — Anthropic 官方工程部落格，描述三代理架構（Planner/Generator/Evaluator）的完整設計
> - [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — 長時間自主任務的 Harness 設計原則

**問題一：上下文焦慮（Context Anxiety）**
- 上下文越來越滿，模型開始丟細節、丟重點，甚至會「著急收尾」
- 一般做法：Context Compaction（壓縮歷史上下文）
- Anthropic 的做法：**Context Reflect** — 不是在原上下文繼續壓，而是啟動一個乾淨的新 Agent，把工作交接給它
- 類比：像工程中遇到記憶體洩漏（Memory Leak），不繼續清理，直接重啟進程再恢復狀態

**問題二：自評偏樂觀（Self-Evaluation Bias）**
- 解決方案：**生產與驗收分離**
  - **Planner**：把模糊需求轉成完整規格
  - **Generator**：逐步實現
  - **Evaluator**：像 QA 一樣真實測試（操作頁面、檢查交互、核實結果）

> [!warning] 關鍵工程原則
> 生產與驗收必須分離。只要評估者足夠獨立，系統就能形成有效循環：生成 → 檢查 → 修復 → 再檢查。

#### OpenAI 的實踐

> [!info] 官方文章
> - [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/) — OpenAI 官方部落格，描述如何用 Agent 從零構建超百萬行程式碼的生產級應用

**工程師角色重新定義**：人類不需要寫一行代碼，只負責設計環境
1. 把產品目標拆解成 Agent 能理解的小任務
2. Agent 失敗時，不是讓它更努力，而是問**環境裡缺了什麼能力**
3. 建立反饋鏈路，讓 Agent 能看到自己的工作結果

**AGENTS.md 的演進**：
- 早期犯的錯：寫了一個巨大的 AGENTS.md，把所有規範塞進去 → 模型更糊塗
- 改進：**AGENTS.md 變成目錄頁**，只保留核心索引，詳細內容拆到子文件（設計文件、執行計劃、質量評分、安全規則）
- Agent 先看目錄，需要時再鑽進去 — 本質與 Agent Skills 的「按需暴露」思路一致

**Agent 自我驗證**：
- 接瀏覽器：能截圖、點頁面、模擬用戶操作
- 接日誌/指標系統：能查 log、查監控
- 每個任務在獨立隔離的環境中跑，互不影響

**系統規則取代 Code Review**：
- 把資深工程師的經驗寫成系統規則
- 規則不只報錯，還會把**怎麼修**一起反饋進下一輪上下文
- 本質上是一套可持續運行的自動治理系統

### 四、客戶拜訪比喻

```
派新人去完成重要客戶拜訪：

Prompt Engineering → 把任務講清楚
  「見面先寒暄 → 介紹方案 → 問需求 → 確認下一步」

Context Engineering → 把資料準備齊全
  「客戶背景、溝通記錄、報價、會議目標」

Harness Engineering → 建立持續監控與糾偏機制
  「帶 Checklist → 關鍵節點即時匯報 → 會後紀要 →
   發現偏差馬上糾正 → 按標準驗收結果」
```

### 五、三者的包含關係

```
┌──────────────────────────────────────────┐
│          Harness Engineering             │
│  ┌────────────────────────────────────┐  │
│  │      Context Engineering           │  │
│  │  ┌──────────────────────────────┐  │  │
│  │  │    Prompt Engineering        │  │  │
│  │  │    解決「表達」問題           │  │  │
│  │  └──────────────────────────────┘  │  │
│  │    解決「信息」問題                 │  │
│  └────────────────────────────────────┘  │
│    解決「執行」問題                       │
└──────────────────────────────────────────┘

簡單單次生成 → Prompt 最重要
依賴外部知識 → Context 很關鍵
長鏈路、低容錯的真實場景 → Harness 不可避免
```

> [!quote] 核心金句
> 真正決定能不能上線的可能是模型，但真正決定能不能落地、能不能穩定交付的，是 Harness。

## 我的心得（My Takeaways）

1. Harness Engineering 不是新概念，而是把過去 Agent 開發中「模型以外的所有東西」給了一個統一的名字
2. 六層架構是一個很好的自查框架：信息邊界→工具系統→執行編排→記憶狀態→評估觀測→約束恢復
3. Anthropic 的 Context Reflect（重啟進程而非壓縮）和 OpenAI 的 AGENTS.md 目錄化思路，都指向同一個核心原則：**上下文是稀缺資源，必須精打細算**

## 相關連結（Related）

- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — Claude Code 的內部架構正是 Harness Engineering 的具體實現
- [[2026-03-14-OPENCLI-CODE-ANALYSIS]] — 另一個 CLI Agent 的架構分析，可對比 Harness 設計差異
- [[AI-AGENT-ARCHITECTURE]] — Agent 架構設計的通用原則
- [[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]] — gstack 的設計哲學程式碼分析，Harness Engineering 的代表性實作
- [[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]] — gstack telemetry 子系統的程式碼分析，Harness 設計中常被忽略的可觀測性面向
- [[2026-03-17-NVIDIA-ANNOUNCED-NEMOCLAW-WHAT-NVIDIA-ACTUALLY-SOLVES-FOR-OPENCLAW-USERS-AND-WHAT-IT-DOES-NOT]] — NemoClaw 的跨進程安全治理層，是 Harness 約束層在企業環境的具體實踐
- [[2026-03-31-AI-WORKFLOW-AGENTS-SKILLS-STANDARDS]] — 從 Prompt 工程升級到流程工程的三層式架構，與 Harness Engineering 的系統化思維相通

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | Harness = Agent - Model；六層架構（信息邊界/工具系統/執行編排/記憶狀態/評估觀測/約束恢復）；Context Reflect；Planner-Generator-Evaluator 三代理架構 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Prompt→Context→Harness 是層層包含關係：Prompt 解決「怎麼說」，Context 解決「給什麼」，Harness 解決「怎麼穩定做」。三者對應任務複雜度的遞增——單次生成只需 Prompt，長鏈路任務必須有 Harness |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維，看透策略底層邏輯 | 影片隱含假設：模型能力已足夠強，瓶頸在工程側。但對於某些領域（如數學推理），模型能力本身可能仍是瓶頸。此外，六層架構的分層界限在實作中可能模糊——例如「評估」和「約束」往往緊密耦合 |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力，將理論轉為行動 | 1. 用六層架構自查現有 Agent 系統，找出最薄弱的一層優先改進；2. 將 AGENTS.md / CLAUDE.md 改為目錄式結構，按需暴露詳細內容；3. 為現有 Agent 加入獨立的 Evaluator 角色做品質閉環 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡，在不確定的情境中做出最佳選擇 | Context Reflect（重啟新 Agent）vs Context Compaction（壓縮舊上下文）：前者更乾淨但成本更高（需要完整的狀態序列化/恢復機制）；對短任務用壓縮即可，對數小時級長任務值得用 Reflect。AGENTS.md 目錄化 vs 全量給入：當工具數 <5 且規範簡短時全量給入更簡單，超過此閾值再拆分 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Harness」這個詞涵蓋範圍極廣，是否存在過度概括的風險？它與傳統軟體工程中的「infrastructure」或「platform」有何本質區別？
- **假設**：影片假設「同模型不同 Harness = 不同表現」，但若基礎模型推理能力不足（如無法遵循複雜指令），再好的 Harness 也難以補救。模型能力的下限在哪？
- **證據**：Anthropic 的 Planner-Generator-Evaluator 架構效果數據（成功率、品質分數）在影片中未具體給出，需查閱原始部落格文章驗證
- **觀點**：反對者可能認為過度工程化 Harness 會增加系統複雜度和維護成本，對小團隊而言「夠用就好」的 Prompt Engineering 可能是更務實的選擇
- **後果**：若所有團隊都投入重度 Harness 建設，可能導致 Agent 系統過度依賴特定工程框架，降低模型升級時的靈活性（Harness 與模型能力的耦合問題）

## References

- [原始影片 — 最近爆火的 Harness Engineering 到底是个啥？一期讲透！](https://www.youtube.com/watch?v=3DlXq9nsQOE)
- [Anthropic — Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [OpenAI — Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)
