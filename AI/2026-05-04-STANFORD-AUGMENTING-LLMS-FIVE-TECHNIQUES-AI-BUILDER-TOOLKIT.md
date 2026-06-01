---
title: "Stanford 兩小時 AI 課精華版：Augmenting LLMs 的五種技巧 + AI Builder 工具包"
date: 2026-05-04
category: AI
tags:
  - ai/llm
  - ai/agent
  - ai/prompt-engineering
  - ai/rag
  - ai/eval
source: "https://www.patreon.com/posts/157335306"
source_type: article
author: "Gary Chen"
status: notes
links:
  - "[[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]]"
  - "[[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]]"
  - "[[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]]"
  - "[[2026-03-28-AI-ERA-ENGINEER-CORE-VALUE-MICHAEL-BOLIN-META-E9]]"
  - "[[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]]"
---

## 摘要（Summary）

Gary Chen 整理 Stanford 教授 Kian Katanforoosh 的 Beyond LLM 課程精華，提出 AI Builder 的核心框架：強化 LLM 有兩條軸——**橫軸**是換更強的 base model（這是 Lab 的事），**縱軸**是在現有 LLM 上疊工程技術（這是你的事）。縱軸有五層：Prompt Engineering → Fine-tune → RAG → Agentic Workflow → Multi-Agent。每層解決不同問題、耐久性（Durability）不同、適用場景不同。文章的核心論點是：真正的 AI Builder 不是「會用 ChatGPT」，而是具備 **Manager 心態 + Fuzzy Engineering 思維**——會做任務分解（Task Decomposition）、會分辨 Fuzzy 與 Deterministic、會設護欄（Guardrail）、會跑 Eval、會挑對的工具層。

## 關鍵洞察（Key Insights）

1. **橫軸是別人的事，縱軸才是你的事** — 橫軸（換 base model）每年 100 億美金級的資本支出，你拿不了方向盤；縱軸五層才是低成本、高槓桿、跟你一輩子的技能
2. **Prompt Engineering 是 Portable Asset，Fine-tune 是 Brittle Commitment** — Prompt 換 model 直接受惠；Fine-tune 綁死舊 model，下一代 base model 直接打贏你（附 Ross Lazerovitz Slack overfit 案例）
3. **RAG 的獨立價值不只準確度，還有檢索效率與即時更新** — 即使 context window 拉到 100 萬 token，latency 和預索引的效率優勢讓 RAG 短期內不可替代
4. **Traditional vs. Agentic Software 是七面之差** — 資料、邏輯、開發路徑、維護、使用者互動、測試、系統設計全部不同；核心轉變是從「管邏輯」到「管邊界」— 參見 [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]]
5. **Deterministic-first 護欄三層篩選** — (1) Task 分類 → (2) 護欄類型 → (3) Trigger 條件；沒有第三層，護欄就是門面
6. **Eval 三維度交叉** — End-to-End vs Component / Objective vs Subjective / Quantitative vs Qualitative = 六格矩陣，空格就是你的盲點
7. **Multi-Agent 不是進階，是工具** — 只在有真實 Parallelism 或跨團隊 Reusability 時才上；「能 Simple 就 Simple」永遠優先 — 參見 [[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]]

## 詳細內容（Details）

### 一、縱軸 vs. 橫軸：你能施力的只有一條軸

> [!important] 核心框架
> - **橫軸**：換 base model（GPT-4 → GPT-5, Claude 3.5 → 4.7）— Lab 的事，100 億美金級
> - **縱軸**：五層工程技術 — 你的事，低成本高槓桿

Stanford 教授整理的 base LLM 四個限制：
1. **Domain knowledge 缺失**：不知道你公司內部文件、產品規格、客戶歷史
2. **資訊落後**：新詞、新事件、新公司聽不懂
3. **控制難**：機率輸出，同一 prompt 跑兩次兩個答案
4. **Long context 會 Lost in the Middle**：小事實藏在大量文件裡，模型有時候找不出來

這四個限制 OpenAI 和 Anthropic 自己都在解。你能做的是用縱軸五層來繞過或緩解它們。

### 二、Prompt Engineering：Portable 的長期投資

> [!note] Portable Asset
> Prompt 換 base model 大多直接受惠。投入時間是 portable asset，不是 sunk cost。

**BCG × Harvard × Wharton × UPenn 的顧問實驗**（2023 年 9 月）— 三組 BCG 顧問，三個發現：

1. **Jagged Frontier（鋸齒狀邊界）**：AI 不是所有任務都加分，有些反而扯後腿。會用 AI 的人知道邊界在哪裡 — 這與 [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0|Karpathy 的鋸齒狀智慧]] 概念完全呼應
2. **Falling Asleep at the Wheel（方向盤前睡著）**：太信任 AI 在它不擅長的任務上的產出，結果比沒用 AI 更慘
3. **Centaurs vs. Cyborgs**：分工委派型（一個大 prompt）vs. 高頻來回型（一句一句協作），看任務性質切換

> [!tip] Prompt Chaining 才是核心技巧
> 不是 Chain of Thought（叫模型 step by step 想），而是把複雜 prompt **拆成多個獨立 prompt**，前一個 output 餵進下一個。每步可獨立測試、獨立 debug，給你 Observability。

Kian Katanforoosh 自己公司 Workera 的實務觀察：**對話超過 8 turn，模型開始 lose itself**。解法是把對話切 chapter，第一段做完總結成 summary 再帶進下一段。

### 三、Fine-tune：能不簽的承諾就別簽

> [!warning] Fine-tune 是 Brittle 的
> 花兩個月 fine-tune 完，下個月新 base model 出來直接打贏。投入不是 portable asset，是對舊 model 的承諾。

**Ross Lazerovitz 的 Slack Fine-tune 案例**（2023 年 9 月）：把公司 Slack 訊息餵進模型，希望模型「講話像我們」。Demo 當天叫模型寫 blog post，模型回：「I shall work on that in the morning.」追問現在就要，模型說：「I'm writing right now. It's 6:30 a.m. here.」— 這是 overfit，模型學會了 Slack 的拖延文化，沒學會寫作。

**教授結論**：能不 fine-tune 就不 fine-tune。除非法律、科學那種重複高精度領域，否則別碰。

### 四、RAG：檢索哲學，不是讓模型記住

> [!note] RAG 的哲學選擇
> 與其讓模型「記住」一切，不如讓它「查得到」一切。

**進階技巧**：
- **Chunking + 多層次儲存**：同時保留整篇、每章、每段的向量，retrieval 時先找章節再鑽到段落
- **HyDE（Hypothetical Document Embeddings）**：先用 query 讓 LLM 生成假回答，把假回答 embed 後去找真文件，語意空間更接近、命中率拉高

**Long Context vs. RAG 辯論**：
- 反方：Context window 拉到 100 萬 token，直接讀整個資料庫就好
- Stanford 教授回應：理論上對，實務上錯。**Latency** — 每次問問題都要重讀整個 Google Drive，沒人等得了。搜尋引擎也不是每次 query 重爬整個網路

> [!warning] Gary Chen 的補充
> 這個判斷有時間性。三年後算力翻幾倍、attention 機制大改進，RAG 工程師的工作可能從「設計 retrieval pipeline」變成「設計 hybrid retrieval + long context routing」。

### 五、七面之差：Traditional vs. Agentic Software

| 面向 | Traditional Software | Agentic Software |
|------|---------------------|-----------------|
| **資料** | 結構化（JSON、DB、表單） | 自由文本、圖片、音訊 |
| **邏輯** | Deterministic，同 input 同 output | Fuzzy，同 input 可能不同 output |
| **開發路徑** | 定義 function 寫死 workflow | 組合 prompt + 工具 + 外部資料 |
| **維護** | 一個 bug 影響相關 feature | 一個 prompt 改動波及多個 unrelated workflows |
| **使用者互動** | 靜態 menu / form / 固定流程 | 動態 conversational，無預設路徑 |
| **測試** | 跑一百次結果一樣 | Iterative exploratory，無法窮舉 |
| **系統設計** | 精確控制每一步執行路徑 | **Manager 心態**：給目標與邊界，讓 AI 自己決定 |

> [!important] 核心心態轉變
> 寫程式時你管邏輯，做 Agent 時你管邊界。— 這與 [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE|Harness Engineering]] 的「harness 決定 agent 能不能交付」框架一脈相承。

### 六、Deterministic-first 護欄三層篩選

```
Task 進來
  │
  ▼
[第一層：Task 分類]
  │ 問：有標準答案？風險容忍度？需要重複高精度？
  ├─ 有標準答案 ──► Deterministic 處理（完成）
  └─ 無標準答案 ──► Fuzzy 處理
                      │
                      ▼
              [第二層：護欄類型]
                │ Human-in-the-loop / Appeal / Fallback / Rule-based filter
                ▼
              [第三層：Trigger 條件]
                │ 什麼狀況 escalate 給人類？
                │ 人類 review signal 怎麼變成下一輪 eval data？
                ▼
              有第三層 → 護欄真正運作
              沒第三層 → 護欄只是門面
```

Workera 的實例：語音題用 Appeal 機制 — 受測者覺得 LLM 判分不對可以申訴，真人介入糾正。不是讓 AI 零錯誤，是 AI 出錯時有人接得住。

### 七、Agentic Workflow：McKinsey 信用 Memo 案例

**四個核心要素**（Anthropic 拆法）：
- **Prompts**：角色定義
- **Context Management**：Working Memory + Archival Memory
- **Tools**：做動作的（flight search、payment）
- **Resources**：拿資料的（CRM lookup、知識庫）

**自主性三層**：
1. Hardcoded Steps — 每步寫死
2. **Hardcoded Tools + Agent 自己決定步驟** — 現在 production 最常見、教授推薦起點
3. Fully Autonomous — 風險最高，agent 可能自動訂 100 張機票

**McKinsey 信用 Memo 改造**：

```
Before（1-4 週）                    After（省 20-80%）
─────────────────                  ─────────────────
RM 收 15+ 來源資料                  RM prompt AI Agent
    │                                  │
    ▼                                  ▼
Credit Analyst 寫 20h+ 分析       Agent 拆給 Specialist Agents
    │                                  │
    ▼                                  ▼
RM review → feedback              Specialists 各自 gather + analyze
    │                                  │
    ▼                                  ▼
Analyst 改稿（1-4 輪）            生成 Memo 草稿
    │                                  │
    ▼                                  ▼
最終 Memo                         RM + Analyst review → Agent 整合
                                       │
                                       ▼
                                   最終 Memo
```

> [!quote] Stanford 教授的 Caveat
> "Change is so hard。從 demo 到 10 萬人的企業真的這樣跑，要 10 到 20 年。"
> 技術不是 bottleneck，人是。

### 八、Eval 三維度交叉

| | Objective | Subjective |
|---|-----------|-----------|
| **End-to-End** | 整體成功率 | 使用者滿意度 |
| **Component** | 每步準度（Python script 驗證） | 語氣/同理心（LLM-as-Judge） |

**Quantitative** vs. **Qualitative** 是第三個維度。三維度交叉形成六格矩陣，**沒有對應 eval question 的格子就是你的盲點**。

**LLM-as-Judge 四種玩法**：
1. Pairwise Comparison — 兩個答案問哪個好
2. Single-answer Grading — 一到五分
3. Reference-guided Pairwise — 多給標準答案
4. Rubric-based — 你定評分標準

### 九、Multi-Agent：能 Simple 就 Simple

兩個獨立理由上 Multi-Agent：
1. **Parallelism**：訂機票時找航班/飯店/天氣可同時跑
2. **Reusability**：Design agent 給行銷和產品團隊共用，優化一次多方受惠

> [!warning] 條件
> 沒有真實 Parallelism、沒有跨團隊復用 → 硬上 Multi-Agent 只增加複雜度。這與 [[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS|Stanford 研究：單一 Agent 在等 token 預算下勝過 Multi-Agent]] 的結論一致。

**關鍵觀念翻轉**：Agent 之間互相溝通，本質上就是 MCP Protocol。每個 Agent 對外暴露一組 tool-like 介面，其他 Agent 像呼叫工具一樣呼叫。**Tool 跟 Agent 是同一種介面思維的不同顆粒度**。

互動模式：
- **Hierarchical**（推薦）：使用者只跟 Orchestrator 講話，Orchestrator 派工
- **Flat**：Agent 之間直接互通，適合緊密耦合的子系統（如 Climate Control ↔ Energy Management）

### 十、縱軸是工程心態的位移

> [!tip] 五層一句話總結
> 1. **Prompt Engineering** — LLM 有性格，要 chain 不要黑盒
> 2. **Fine-tune** — 個承諾，能不簽就不簽
> 3. **RAG** — 讓模型查得到，不是讓模型記住
> 4. **Agentic Workflow** — Manager 心態，給目標與邊界，不寫每一行 code
> 5. **Multi-Agent** — Single-agent 加一層介面紀律，不是新架構

## 我的心得（My Takeaways）

1. **「Portable vs. Brittle」是我見過最清晰的 Prompt vs. Fine-tune 決策框架** — 不是問「哪個效果好」，而是問「投入的時間是跟著你走還是綁在舊 model 上」。這改變了我對技術投資的思考方式。

2. **七面之差表格值得貼在團隊的看板上** — 我見過太多團隊用 traditional software 的測試方法去測 agentic system，然後困惑為什麼跑一百次結果都不一樣。這張表可以快速校正預期。

3. **三層護欄篩選補上了 [[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY|AI Agent 痛苦教訓]] 中缺少的結構化方法** — 那篇文章講了很多「會出什麼事」，但沒有系統化的「怎麼防」。三層篩選提供了可操作的框架。

4. **「Tool 跟 Agent 是同一種介面思維的不同顆粒度」** — 這句話讓 Multi-Agent 設計突然變得清晰。不用額外學一套新思維，就是 MCP 協議的延伸。

## 待補充（Open Questions）

1. **Prompt Chaining 和 Plan Mode 的關係是什麼？** — 文章說 chaining 是把複雜 prompt 拆成多個獨立 prompt，這和 Claude Code 的 Plan Mode、Karpathy 說的 spec/docs 設計是同一件事嗎？還是有層次差異？建議搜尋：`prompt chaining vs plan mode agentic workflow 2026`

2. **HyDE 在哪些場景下會適得其反？** — 用 LLM 生成假文件再用來 retrieve 真文件，如果 LLM 對該領域理解本身就錯，假文件會不會把 retrieval 帶偏？建議搜尋：`HyDE failure cases hallucination RAG retrieval`

3. **「對話超過 8 turn 模型 lose itself」這個觀察有沒有更系統性的研究？** — Workera 的解法是切 chapter + summary，但這個 8 turn 門檻是 model-specific 還是通用現象？新一代模型（Claude 4.7、GPT-5.4）有改善嗎？建議搜尋：`LLM conversation degradation turn count context window 2026`

4. **McKinsey 的「省 20-80% 時間」數字跨度很大，決定因素是什麼？** — 是任務複雜度？是組織成熟度？還是 agent 設計品質？這個 range 對規劃 ROI 幾乎沒有參考價值。建議搜尋：`McKinsey generative AI productivity variance enterprise deployment`

5. **RAG 的 hybrid retrieval + long context routing 未來，有沒有人已經在做？** — Gary Chen 自己也預測 RAG 工程師的角色會轉變。有沒有已經在實驗 hybrid 模式的團隊或論文？建議搜尋：`hybrid RAG long context routing attention optimization 2026`

6. **「10-20 年落地」這個判斷的依據是什麼？** — Stanford 教授的 epistemic humility 令人敬佩，但 10-20 年的時間跨度是基於歷史類比（如 ERP 導入）還是有更具體的分析？建議搜尋：`enterprise AI adoption timeline McKinsey Stanford prediction`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，確立基礎知識 | 縱軸五層（Prompt Engineering / Fine-tune / RAG / Agentic Workflow / Multi-Agent）；Portable vs. Brittle；七面之差；護欄三層篩選；Eval 三維度交叉六格 |
| **理解（半被動）** | 解釋概念的含義及關聯 | 文章的論證鏈：橫軸是 Lab 的事 → 縱軸才是你的事 → 五層各解不同問題 → Traditional vs. Agentic 是七面之差 → Fuzzy 需要 Deterministic-first + 護欄 → Eval 是三維度交叉 → Multi-Agent 只在有 Parallelism/Reusability 時上 → 核心是從「管邏輯」到「管邊界」的心態位移 |
| **分析（主動）** | 檢驗論點、找出假設 | (1) 「Prompt 是 Portable」假設 base model 的 API 介面和行為模式不會劇變——但如果未來 model 完全改變了 prompt 格式？(2) 「能不 Fine-tune 就不 Fine-tune」忽略了 Fine-tune 在 latency 和 cost 優化上的價值（小模型 + fine-tune 可能比大模型 + prompt engineering 便宜得多）(3) 七面之差隱含 binary 分類，但現實中很多系統是 hybrid |
| **應用（主動）** | 將知識套用情境 | (1) 用三層護欄篩選審計自己現有的 agent workflow — 第三層 trigger 條件是否真的設了？(2) 建立 Eval 三維度六格矩陣，找出自己專案的盲點格 (3) 對現有的 fine-tune 投資重新評估 — 是 portable asset 還是 brittle commitment？ |
| **評估（主動）** | 判斷多個方案的優劣 | **優點**：五層框架清晰實用、護欄三層可直接操作、七面之差表格有教育價值。**缺點**：缺乏量化數據支撐（McKinsey 20-80% 跨度太大）、「10-20 年落地」缺乏方法論、Fine-tune 的否定過於絕對。**替代觀點**：[[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE|Harness Engineering]] 把焦點放在 Harness 而非五層分類，可能更適合已經在做 agent 的團隊；[[2026-04-15-AI-DEVELOPER-EVOLUTION-PRACTITIONER-GUIDE-PERE-VILLEGA|Pere Villega 的開發者演化]] 提供了更漸進的轉型路線圖 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Manager 心態」具體要做到什麼程度的抽象？是只定 spec 還是要 review 每個 agent 的 output？「管邊界」的邊界在哪裡？
- **假設**：文章假設縱軸五層是線性堆疊的。但實務上很多團隊跳過 Fine-tune 直接上 RAG + Agentic Workflow，五層是否更像是可選的工具箱而非階梯？
- **證據**：BCG 顧問實驗的 Jagged Frontier 發現，能否推廣到軟體工程場景？顧問工作和寫 code 的 AI 輔助模式可能根本不同。
- **觀點**：若站在 Fine-tune 支持者的角度，對於低延遲場景（edge device、real-time API），small model + fine-tune 仍然是唯一可行方案，教授的「能不 fine-tune 就不 fine-tune」是否過於學術派？
- **後果**：若所有團隊都遵循「能 simple 就 simple」只用 single agent，是否會錯過 multi-agent 架構在可維護性上的優勢（單一 agent 的 prompt 越來越肥大 vs. 多個精簡 agent 各司其職）？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 把五層當階梯而非工具箱，導致團隊按順序嘗試而非根據問題選擇。例如先花三個月做 Prompt Engineering，發現不夠再花三個月做 RAG，其實一開始就該直接上 RAG。風險是浪費時間。
2. **什麼情況下會失敗？** — 當 base model 的能力邊界（Jagged Frontier）恰好落在你的核心任務上時，五層工程技術可能都救不了。此時唯一的出路是等橫軸進步或 fine-tune — 但文章說別 fine-tune。
3. **有沒有更好的替代方案？** — [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE|Harness Engineering]] 不按五層分類，而是從「編排迴圈、記憶管理、工具整合、安全邊界」等模組化角度設計 agent。對已經在做 agentic system 的團隊，Harness 框架可能比五層分類更有操作性。

## 相關連結（Related）
- [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] — Karpathy 的鋸齒狀智慧概念與本文的 Jagged Frontier 完全呼應；Manager 心態 vs. 管邊界的論點互為印證
- [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]] — 從 Harness 架構角度切入 agentic engineering，與本文的五層縱軸提供互補的分類視角
- [[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]] — Stanford 研究用實驗數據支持「能 simple 就 simple」，與本文 Multi-Agent 章節結論一致
- [[2026-03-28-AI-ERA-ENGINEER-CORE-VALUE-MICHAEL-BOLIN-META-E9]] — Bolin 的「底層理解力是護城河」呼應本文的「Manager 心態 = 理解邊界而非寫每行 code」
- [[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]] — 實戰經驗驗證了七面之差中的「維護」和「測試」面向的痛苦
- [[2026-04-15-AI-DEVELOPER-EVOLUTION-PRACTITIONER-GUIDE-PERE-VILLEGA]] — Pere Villega 的開發者演化路線圖，從不同角度描述同一個 Traditional → Agentic 轉型
- [[2026-02-11-HARNESS-ENGINEERING-LEVERAGING-CODEX-IN-AN-AGENT-FIRST-WORLD]] — OpenAI 團隊零手寫程式碼的實踐，是本文 Agentic Workflow 章節的極端案例
- [[2026-04-24-AGENT-HARNESS-12-MODULES-COMPLETE-GUIDE]] — Harness 十二模組提供了比五層更細粒度的 agentic system 設計框架
- [[2026-05-25-HUMAN-SOP-TO-AGENTIC-WORKFLOW-PROMPT-TOOLKIT]] — 把任務拆成獨立節點正是本文 decomposition 技巧在個人 SOP 上的落地

## References
- [原文 — Stanford 兩小時 AI 課精華版（Gary Chen, Patreon）](https://www.patreon.com/posts/157335306)
