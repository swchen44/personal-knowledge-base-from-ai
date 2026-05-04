---
title: "從 Vibe Coding 到 Agentic Engineering：Karpathy 的 Software 3.0 宣言、鬼魂心智模型與新時代人才分界線"
date: 2026-04-29
category: AI
tags:
  - ai/llm
  - ai/agent
  - ai/software-paradigm
  - career/engineering
  - productivity/workflows
source:
  - "https://www.youtube.com/watch?v=96jN2OCOfLs"
  - "https://www.bnext.com.tw/article/90837/from-vibe-coding-to-agentic-engineering-andrej-karpathy-s-software-3-0-ghosts-and-new-10x-talent"
source_type: video
author: "Andrej Karpathy"
secondary_author: "李先泰（數位時代中文轉譯）"
status: notes
channel: "Sequoia Capital"
duration: "29:49"
transcript_method: youtube-transcript-api
links:
  - "[[2026-04-03-KARPATHY-AI-INSANITY-AGENTS-AUTORESEARCH-MODEL-SPECIATION]]"
  - "[[2026-04-02-KARPATHY-LLM-WIKI-PATTERN]]"
  - "[[2026-04-09-AI-ONE-PERSON-COMPANY-KARPATHY-OBSIDIAN-KB-OPENCLI]]"
  - "[[2026-02-11-HARNESS-ENGINEERING-LEVERAGING-CODEX-IN-AN-AGENT-FIRST-WORLD]]"
  - "[[2026-03-28-AI-ERA-ENGINEER-CORE-VALUE-MICHAEL-BOLIN-META-E9]]"
---

## 摘要（Summary）

Andrej Karpathy 於 2026 年 4 月在 Sequoia Capital 的 AI Ascent 大會發表演講，系統性闡述了從 Vibe Coding 到 Agentic Engineering（代理工程）的演進。本筆記結合了**原始英文演講逐字稿**與**數位時代李先泰的中文轉譯報導**，以主題為軸線交織兩者：中文報導提供精煉框架，原始逐字稿補充完整脈絡、即興比喻與未被中文報導收錄的段落（如 OpenClaw 安裝範例、神經電腦（Neural Computer）願景、Agent-Native 基礎設施、教育觀點等）。

核心論點：LLM 不是動物而是「鬼魂」（Ghosts）——統計性召喚的精靈，具有鋸齒狀（Jagged）能力分布；Vibe Coding 提升了所有人寫程式的「樓地板」（Floor），Agentic Engineering 則守住品質的「天花板」（Ceiling）並加速執行；能駕馭代理工程的人才加速幅度峰值遠超 10 倍，但核心競爭力在於——**「可外包思考，無法外包理解」**。

> [!info] 來源說明
> 本筆記融合兩個來源：(1) Karpathy 在 Sequoia AI Ascent 2026 的原始演講（29:49），(2) 數位時代李先泰的中文轉譯報導（2026-05-04）。原始引述以區塊引用標示，保留英文原文並附中文翻譯。

## 關鍵洞察（Key Insights）

1. **Software 3.0 是新的計算典範，不只是加速** — Prompt 即程式，LLM 是可程式化的解譯器（Programmable Interpreter），連「安裝軟體」都從 shell script 變成「copy paste 給 agent」— 參見 [[2026-04-03-KARPATHY-AI-INSANITY-AGENTS-AUTORESEARCH-MODEL-SPECIATION]]
2. **LLM 是鬼魂，不是動物** — 沒有本能、好奇心或內在動機，對它吼叫毫無意義；能力是被預訓練資料和 RL 環境「塑造」出來的鋸齒狀分布
3. **Vibe Coding ≠ Agentic Engineering** — 前者提升 Floor（人人可寫程式），後者維持 Quality Bar 同時提速；這是兩個不同的工程紀律
4. **品味與判斷力是目前無法外包的人類能力** — 代理在「填空」上強大，在「設計」上笨拙；你仍需負責 Spec、架構和審美 — 參見 [[2026-03-28-AI-ERA-ENGINEER-CORE-VALUE-MICHAEL-BOLIN-META-E9]]
5. **可驗證性（Verifiability）決定了 AI 自動化的順序** — 傳統電腦自動化「可用程式碼規範的事」，LLM 自動化「可驗證的事」；鋸齒狀能力部分源自 RL 環境的設計偏好
6. **「可外包思考，無法外包理解」** — 資訊仍必須進入人腦才能判斷「什麼值得做、為什麼值得做」，這也是 Karpathy 開發 [[2026-04-02-KARPATHY-LLM-WIKI-PATTERN|LLM 知識庫]] 的根本動機

## 詳細內容（Details）

### 一、從「從未如此落後」說起

Karpathy 開場就以一句令人意外的自白引出主題：

> "I've never felt more behind as a programmer... December was this clear point where the chunks just came out fine and then I kept asking for more and it just came out fine and then I can't remember the last time I corrected it."
>
> 「我從未覺得自己身為程式設計師如此落後……十二月是一個明確的轉折點，模型吐出來的程式碼就是對的，我繼續要求更多，它還是對的，我已經想不起上次修改 AI 輸出是什麼時候了。」

這個轉變反映了人機分工信任曲線的根本改變——從「AI 寫、工程師改」進階到「AI 跑、工程師審」。Karpathy 強調，很多人在 2025 年還把 AI 當成「ChatGPT 的衍生物」，但 2025 年 12 月後的代理式工作流已經是**質變**，不是量變。

### 二、Software 3.0：Prompt 即程式

> [!note] 軟體三代演進（Software Evolution）
> - **Software 1.0**：明確規則的程式碼（Explicit Rules）
> - **Software 2.0**：訓練神經網路，程式設計 = 整理資料集（Training Neural Networks）
> - **Software 3.0**：Prompt + Context Window = 對 LLM 這台可程式化解譯器的程式語言

Karpathy 用兩個生動的範例闡述 Software 3.0 的意義：

**範例一：OpenClaw 安裝** — 傳統做法需要一個龐大的 shell script 來支援各種平台，但 Software 3.0 的做法是：把一段文字 copy paste 給你的 agent，由 agent 觀察你的環境、自行安裝、自行除錯。

> "What is the piece of text to copy paste to your agent? That's the programming paradigm."
>
> 「要 copy paste 給 agent 的那段文字是什麼？這就是新的程式設計典範。」

**範例二：Menu Gen 的頓悟** — Karpathy 自己 vibe coding 了一個 app：拍餐廳菜單照片 → OCR 辨識 → 生成每道菜的示意圖。但他看到了 Software 3.0 版本：直接把照片丟給 Gemini + NanoBanana，模型自動在原始菜單圖像的像素上渲染出菜餚圖片。

> "Actually all of my Menu Gen is spurious. It's working in the old paradigm. That app shouldn't exist."
>
> 「我整個 Menu Gen 是多餘的。它還活在舊典範裡。那個 app 根本不該存在。」

這揭示了一個更深層的洞察：**Software 3.0 不只是「寫程式變快」，而是有些事情從前根本做不到**。例如 Karpathy 的 LLM 知識庫專案（[[2026-04-02-KARPATHY-LLM-WIKI-PATTERN]]）——沒有任何程式碼能「根據一堆事實建立知識庫」，但 LLM 可以將文件重新編譯成全新的知識組織形式。

> "It's not just about programming becoming faster. This is more general information processing that is automatable now."
>
> 「這不只是程式設計變快。這是更廣義的資訊處理現在可以自動化了。」

### 三、LLM 是「鬼魂」，不是動物

> [!important] 鬼魂心智模型（Ghost Mental Model）
> LLM 不是有本能的動物，而是統計模擬電路（Statistical Simulation Circuits），被人類資料召喚出的精靈。預訓練是基底（Substrate），RL 在上面增長出突起的觸手（Appendages）。

Karpathy 坦言這個比喻可能沒有「五個顯著的實用結論」，更多是一種思維框架：

> "If you yell at them, they're not going to work better or worse. It doesn't have any impact. It's all just kind of like these statistical simulation circuits."
>
> 「如果你對它們吼叫，它們不會做得更好或更差，吼叫沒有任何影響。這一切不過是統計模擬電路。」

這個框架的價值在於：幫助你校正對 LLM 的期待，不再用人類直覺去推測它的行為邊界，而是去**探索**那個沒有使用手冊的鋸齒狀能力空間。

### 四、鋸齒狀智慧（Jagged Intelligence）與可驗證性

鬼魂的能力呈現「鋸齒狀」——同一個模型可以重構十萬行程式碼、找出零日漏洞（Zero-Day Vulnerability），卻在常識問題上翻車。

> "I want to go to a car wash to wash my car and it's 50 meters away. Should I drive or should I walk? State-of-the-art models today will tell you to walk because it's so close. How is it possible that state-of-the-art Opus 4.7 will simultaneously refactor a 100,000 line codebase or find zero day vulnerabilities and yet tells me to walk to this car wash? This is insane."
>
> 「我要去 50 公尺外的洗車場洗車，該開車還是走路？最先進的模型會告訴你走路，因為很近。Opus 4.7 怎麼可能同時重構十萬行程式碼、找出零日漏洞，卻告訴我走路去洗車場？這太瘋狂了。」

**鋸齒狀的成因**有兩個維度：

1. **RL 環境的設計**：你在 RL 覆蓋的電路上就「飛起來」，在電路外就掙扎
2. **預訓練資料的分布**：GPT-3.5 到 GPT-4 的棋藝飛躍，不是整體智力提升，而是有人決定把大量棋譜納入預訓練資料

> [!warning] 實務意義
> 你必須探索 LLM 在你的應用領域是落在「RL 電路之內」還是「資料分布之外」。如果不在電路內，不要期望 out-of-the-box 就能用——你需要 Fine-tuning。

Karpathy 進一步以「可驗證性」（Verifiability）框架解釋這個現象：
- 傳統電腦自動化 → 可用程式碼**規範**的事
- LLM 自動化 → 可被**驗證**的事（因為 RL 需要驗證獎勵）

他暗示存在某些「非常有價值但尚未被實驗室納入 RL 環境的可驗證領域」，但拒絕在台上透露具體是哪個。

### 五、Vibe Coding vs. Agentic Engineering

> [!tip] 兩者的區別
> - **Vibe Coding**：提高所有人的 Floor（樓地板）——人人都能用 AI 寫軟體
> - **Agentic Engineering**：維持既有的 Quality Bar（品質天花板），同時用代理加速——不允許因 vibe coding 引入安全漏洞

> "Agentic engineering... you have these agents which are these spiky entities. They're a bit fable, a little bit stochastic, but they are extremely powerful. How do you coordinate them to go faster without sacrificing your quality bar?"
>
> 「代理工程……你有這些尖刺狀的實體（Agent）。它們有點脆弱、有點隨機，但極其強大。你要怎麼協調它們加速，同時不犧牲品質標準？」

### 六、品味、判斷力與「填空 vs. 設計」

代理目前像「實習生」（Intern）——工程師仍然必須負責審美（Aesthetics）、判斷（Judgment）、品味（Taste）和監督（Oversight）。

**Menu Gen 的 email 錯誤**是最佳反例：用 Google 帳號登入、用 Stripe 付款，代理用 email 地址交叉比對兩者——但使用者可能用不同的 email，這是一個設計層面的低級錯誤。

> "Why would you use email addresses to try to cross-correlate the funds? They can be arbitrary. This is such a weird thing to do."
>
> 「為什麼會用 email 來交叉比對資金？email 可以是任意的。這是非常奇怪的判斷。」

Karpathy 在技術細節上給出了一個精確的例子：

> "I already forgot about the keepdims versus keep_dim, whether it's dim or axis, reshape or permute or transpose. I don't remember this stuff anymore. But you still have to know that there's an underlying tensor, there's an underlying view, and you can manipulate the view of the same storage or you can have different storage which would be less efficient."
>
> 「我已經忘了 keepdims 和 keep_dim 的差別、到底是 dim 還是 axis、reshape 還是 permute 還是 transpose。我不記得這些了。但你仍然必須知道底層有一個 tensor，有一個 view，你可以操作同一個 storage 的 view 或者用不同的 storage（但效率較低）。」

這完美詮釋了 [[2026-03-28-AI-ERA-ENGINEER-CORE-VALUE-MICHAEL-BOLIN-META-E9|Michael Bolin 的觀點]]：**底層技術理解力**才是護城河，API 細節可以交給 AI。

> [!tip] Karpathy 對 Plan Mode 的看法
> 他不只是喜歡 Plan Mode——他認為需要更通用的東西：與 agent 一起設計一份**非常詳細的 spec / docs**，你負責頂層分類和監督，agent 負責底層實作。

### 七、新型人才的分界線

> "People used to talk about the 10x engineer. I think this is magnified a lot more. 10x is not the speed up you gain. People who are very good at this peak a lot more than 10x."
>
> 「以前人們說十倍工程師。我認為這個倍率被放大了更多。十倍不是你獲得的加速幅度。真正擅長這個的人，峰值遠超十倍。」

**招募流程也必須改變**——從解演算法題（Puzzle Solving）轉為實戰專案考核：

> "Give me a really big project... Let's write a Twitter clone for agents, make it really good, make it really secure, and then I'm going to use 10 Codex instances to try to break your deployment, and they should not be able to break it."
>
> 「給我一個大型專案……寫一個 Twitter clone，做得很好、很安全，然後我用 10 個 Codex 實例來嘗試打爆你的部署，看你撐不撐得住。」

### 八、Agent-Native 基礎設施的願景

這是**中文報導未收錄**的重要段落。Karpathy 對現有基礎設施的不滿溢於言表：

> "Everything is still fundamentally written for humans and has to be moved around. I don't—why are people still telling me what to do? I don't want to do anything. What is the thing I should copy paste to my agent?"
>
> 「所有東西本質上仍然是為人類寫的。我不——為什麼人們還在告訴我該做什麼？我不想做任何事。我該 copy paste 給 agent 的東西是什麼？」

他提出了一個「Agent-Native 成熟度測試」：能不能只給一個 prompt 讓 LLM 建立 Menu Gen，然後什麼都不用碰就部署到網上？如果可以，代表基礎設施已經夠 Agent-Native 了。參見 [[2026-02-11-HARNESS-ENGINEERING-LEVERAGING-CODEX-IN-AN-AGENT-FIRST-WORLD]]。

### 九、神經電腦（Neural Computer）的未來推演

另一段**中文報導未收錄**的精彩推演：

> "You could imagine completely neural computers... In the early days of computing, people were confused as to whether computers would look like calculators or neural nets. We went down the calculator path... but you could imagine that a lot of this will flip and the neural net becomes the host process and the CPUs become the co-processor."
>
> 「你可以想像完全由神經網路驅動的電腦……在計算的早期，人們搞不清楚電腦會像計算器還是像神經網路。我們走了計算器那條路……但你可以想像這一切會翻轉——神經網路成為主行程（Host Process），CPU 變成協處理器（Co-processor）。」

工具呼叫（Tool Use）在這個願景中變成了一個「歷史遺留的附屬物」（Historical Appendage），只用於少數需要確定性的任務。

### 十、「可外包思考，無法外包理解」

> [!quote] 本場演講最核心的一句話
> "You can outsource your thinking, but you can't outsource your understanding."
>
> 「你可以外包你的思考，但你無法外包你的理解。」

Karpathy 坦言自己正在成為系統的瓶頸——資訊仍然必須進入人腦，才能判斷「我們要建什麼、為什麼值得做、如何指揮代理」。

這也是他開發 LLM 知識庫（[[2026-04-02-KARPATHY-LLM-WIKI-PATTERN]]）的動機——每次用不同的 prompt 對同一批資料做合成資料生成（Synthetic Data Generation），每一次新的投影（Projection）都讓他獲得新的洞察。

> "Anytime I see a different projection onto information, I always feel like I gain insight."
>
> 「每次我看到資訊的不同投影，我總覺得自己獲得了新的洞察。」

## 中文報導 vs. 原始演講的差異對照

| 主題 | 中文報導（bnext） | 原始演講新增內容 |
|------|------------------|----------------|
| Software 3.0 | 提到概念 | OpenClaw 安裝範例、Menu Gen + NanoBanana 完整故事 |
| 鋸齒狀能力 | 洗車場範例 | GPT-3.5→4 棋藝突飛猛進的資料分布成因 |
| 鬼魂比喻 | 有描述 | Karpathy 自承「不確定是否有實用價值」的坦誠 |
| 可驗證性 | 未涉及 | 完整的 Verifiability 框架與 RL 環境關係 |
| Agent-Native 基建 | 未涉及 | 對現有基礎設施的不滿、成熟度測試標準 |
| 神經電腦未來 | 未涉及 | 計算器 vs. 神經網路的歷史選擇、未來翻轉 |
| 技術細節 | keepdims 未提及 | keepdims/dim/axis、tensor storage/view 的具體例子 |
| 品味 vs. RL | 簡要提及 | micro GPT 簡化實驗的失敗、「pulling teeth」比喻 |
| 教育 | 未涉及 | LLM 知識庫作為理解增強工具的闡述 |
| Plan Mode | 未涉及 | Karpathy 認為需要比 Plan Mode 更通用的 spec/docs 協作 |
| 招募 | 有提及 | Twitter clone + 10 Codex 打爆的完整場景描述 |

## 我的心得（My Takeaways）

1. **「那個 app 根本不該存在」是最有力的 Software 3.0 論證**——不是「同樣的事更快」，而是「舊典範下的整個應用層可能是多餘的」。這迫使我重新審視自己正在建的每一個工具：它是在 Software 1.0 的思維下，做了 Software 3.0 一個 prompt 就能取代的事嗎？

2. **鋸齒狀能力的「電路內 vs. 電路外」框架非常實用**——在評估 LLM 能否用於某個任務時，不再問「它夠聰明嗎」，而是問「這個任務在它的 RL 電路覆蓋範圍內嗎」。若不在，就準備好 fine-tuning 預算。

3. **Karpathy 和 Bolin 的結論驚人地一致**——「底層理解」是最後的護城河。API 細節、語法糖、框架特性都可以交給 AI，但你必須知道 tensor 的 storage 和 view 的關係、必須知道為什麼不能用 email 做 cross-reference。

4. **LLM 知識庫 = 理解力的放大器**——Karpathy 不把知識庫當成「存檔系統」，而是當成「理解的催化劑」：對同一批資料做不同投影，每次投影都增加洞察。這完全改變了我對個人知識庫的定位。

## 待補充（Open Questions）

1. **Karpathy 暗示的「非常有價值但未被 Lab 納入 RL 的可驗證領域」到底是什麼？** — 他在台上明確拒絕透露。值得追蹤他後續的推文和專案。建議搜尋關鍵字：`Karpathy verifiable domain RL fine-tuning 2026`

2. **「品味無法外包」是永久性限制還是暫時性限制？** — Karpathy 自己也搖擺不定，他說「nothing fundamental preventing it, it's just the labs haven't done it yet almost」。如果 RL 環境開始納入美學和設計獎勵，這個護城河還在嗎？建議搜尋：`LLM aesthetic reward RL design taste`

3. **Agent-Native 基礎設施的標準是什麼？** — Karpathy 提出了 Menu Gen 部署測試作為初步標準，但完整的成熟度模型是什麼？現有的 MCP、A2A Protocol、[[2026-03-17-KARPATHYS-AGENTHUB-A-PRACTICAL-GUIDE-TO-BUILDING-YOUR-FIRST-AI-AGENT-SWARM|AgentHub]] 各覆蓋了多少？建議搜尋：`agent-native infrastructure maturity model MCP`

4. **「鬼魂」比喻對實際系統設計的指導意義到底有多大？** — Karpathy 坦承自己也不確定這個比喻有「real power」。它是否只是一個防止擬人化偏見的警示？還是能推導出具體的設計原則？建議搜尋：`LLM mental model ghost animal design implication`

5. **10x 到底被放大到了多少？** — Karpathy 說「peak a lot more than 10x」但沒給數字。在 [[2026-02-11-HARNESS-ENGINEERING-LEVERAGING-CODEX-IN-AN-AGENT-FIRST-WORLD|Harness Engineering]] 的案例中，是否有更具體的量化數據？建議搜尋：`agentic engineering productivity multiplier quantitative 2026`

6. **神經電腦（Neural Computer）的翻轉時間線是什麼？** — Karpathy 說 "we're going to get there piece by piece" 但沒有時間估計。GPU 架構是否已經在朝這個方向走？建議搜尋：`neural computer host process CPU co-processor architecture trend`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | Software 1.0/2.0/3.0 三代定義；Vibe Coding vs. Agentic Engineering 的區別；鬼魂（Ghost）比喻；鋸齒狀智慧（Jagged Intelligence）；「可外包思考，無法外包理解」 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Karpathy 的論證鏈：LLM = 可程式化解譯器 → Prompt = 程式語言 → 舊典範下的 App 可能不該存在 → 但 LLM 的鋸齒狀能力源自 RL 電路覆蓋 → 因此人類的角色從「寫程式」轉為「設計 + 監督 + 理解」→ 理解無法外包 → 知識庫是理解的放大器 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | **關鍵假設**：(1) RL 電路覆蓋範圍會持續擴大但「品味」短期內不會被覆蓋——這基於 Lab 的優先順序而非技術限制；(2) Menu Gen 範例暗示所有中間層 App 都會被取代——但現實中許多 App 的價值不只是資訊處理，還包括 UX、品牌、信任；(3)「理解無法外包」的前提是 LLM 不具備真正的理解——這在哲學上有爭議 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | (1) 對自己現有專案做「Menu Gen 審計」——哪些功能本質上是 Software 1.0 在做 Software 3.0 一個 prompt 就能做的事？(2) 建立 agent 工作流時先問「這個任務在 RL 電路內嗎？」，若不在就準備 fine-tuning 方案而非調 prompt (3) 仿照 Karpathy 的 LLM 知識庫模式，對自己的知識庫做多角度投影 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | **優點**：Software 3.0 框架簡潔有力、鬼魂比喻有效防止擬人化偏見、鋸齒狀 + 可驗證性提供了評估 LLM 適用性的實用框架。**缺點**：缺乏量化數據（「遠超 10x」到底多少？）、Agent-Native 願景缺乏具體路線圖、「品味無法外包」可能只是暫時的結論。**替代觀點**：Steve Yegge 的[[2026-03-25-ENGINEERS-FUTURE-MULTI-AGENT-ERA-STEVE-YEGGE|多代理人架構師]]觀點提供了更具體的角色定義；Michael Bolin 的[[2026-03-28-AI-ERA-ENGINEER-CORE-VALUE-MICHAEL-BOLIN-META-E9|底層理解力]]觀點更有操作性 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「Software 3.0」的邊界在哪裡？當 prompt + context 不夠用（例如需要精確的數學證明或型別安全保證）時，是否退回 Software 1.0 + 3.0 的混合模式？
- **假設**：Karpathy 的論點建立在「RL 電路決定能力峰值」這個前提上。若未來出現不依賴 RL 的訓練方法（例如純粹的自監督學習突破），鋸齒狀分布是否會消失？
- **證據**：「遠超 10x 的加速」這個主張完全缺乏量化數據。是否有團隊做過對照實驗？OpenAI 的 Harness Engineering 團隊有沒有公開數字？
- **觀點**：若站在一個資深系統工程師的角度，「Agent-Native 基礎設施」是否會帶來新的安全和可靠性風險？當所有部署都由 agent 自動完成，出了問題誰負責除錯？
- **後果**：若依照 Karpathy 的建議全面擁抱 Agentic Engineering，12 個月後可能出現什麼副作用？例如：工程師是否會因過度依賴 agent 而喪失手動除錯能力？

## 相關連結（Related）
- [[2026-04-03-KARPATHY-AI-INSANITY-AGENTS-AUTORESEARCH-MODEL-SPECIATION]] — Karpathy 稍早的「AI 精神錯亂」演講，涵蓋 agent 工作流、鋸齒狀能力等主題的早期版本
- [[2026-04-02-KARPATHY-LLM-WIKI-PATTERN]] — 本演講中直接提到的 LLM 知識庫模式，是「理解無法外包」論點的實踐工具
- [[2026-04-09-AI-ONE-PERSON-COMPANY-KARPATHY-OBSIDIAN-KB-OPENCLI]] — Karpathy 知識庫架構的延伸實踐，多模型角色分工
- [[2026-02-11-HARNESS-ENGINEERING-LEVERAGING-CODEX-IN-AN-AGENT-FIRST-WORLD]] — OpenAI 團隊實踐 agentic engineering 的案例，與本演講的理論框架互為印證
- [[2026-03-28-AI-ERA-ENGINEER-CORE-VALUE-MICHAEL-BOLIN-META-E9]] — Bolin 的「底層理解力是護城河」與 Karpathy 的「理解無法外包」形成完美呼應
- [[2026-03-25-ENGINEERS-FUTURE-MULTI-AGENT-ERA-STEVE-YEGGE]] — Yegge 的「工程師 → 架構師/調度員」觀點，從組織角度回應 Karpathy 的個人角度
- [[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]] — Karpathy 的 CLAUDE.md 原則實測，與本演講的品味/設計論點互補
- [[2026-03-17-KARPATHYS-AGENTHUB-A-PRACTICAL-GUIDE-TO-BUILDING-YOUR-FIRST-AI-AGENT-SWARM]] — Agent-Native 基礎設施的具體實作，回應本演講的願景
- [[2026-05-04-STANFORD-AUGMENTING-LLMS-FIVE-TECHNIQUES-AI-BUILDER-TOOLKIT]] — Stanford AI 課程的五層縱軸框架，與 Karpathy 的鋸齒狀智慧和 Manager 心態互為印證

## References
- [原始演講 — Andrej Karpathy: From Vibe Coding to Agentic Engineering (Sequoia Capital AI Ascent 2026)](https://www.youtube.com/watch?v=96jN2OCOfLs)
- [中文轉譯報導 — 10 倍工程師不夠看了？Karpathy 拋 agentic engineering 概念（數位時代）](https://www.bnext.com.tw/article/90837/from-vibe-coding-to-agentic-engineering-andrej-karpathy-s-software-3-0-ghosts-and-new-10x-talent)
