---
title: "Garry Tan：用 Tokenmaxxing + GStack 達成 400 倍個人生產力"
date: 2026-05-17
category: AI
tags:
  - ai/agents
  - ai/claude-code
  - productivity/workflow
  - business/yc
  - philosophy/human-in-the-loop
source: "https://www.youtube.com/watch?v=fmR91KKSEuc"
source_type: video
author: "Garry Tan（轉述）／最佳拍檔（大飛）"
status: notes
links:
  - "[[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]]"
  - "[[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]]"
  - "[[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]]"
  - "[[2026-04-25-CLAUDE-SKILLS-PLAYBOOK-DESCRIPTION-SUBAGENT-DEBUG-PROMPTS]]"
channel: "最佳拍檔 Best Partners TV"
duration: "14:24"
transcript_method: youtube-transcript-api
original_source: "Lightcone Podcast（YouTube：https://www.youtube.com/watch?v=57lDpTwiW6g）"
---

## 摘要（Summary）

這是中文頻道「最佳拍檔」對 **YC（Y Combinator）總裁 Garry Tan** 在 Lightcone 播客專訪的 14 分鐘濃縮版。Garry Tan 時隔 **13 年**重新回到 Coding，僅靠 YC 全職工作之餘的時間，達到自己 2013 年寫代碼時的 **400 倍生產力**。支撐這套效率的兩個核心：
1. **Tokenmaxxing**（Token 最大化）— 不計成本「煮沸海洋」(Boil the Ocean)，用算力換完整、深度、精準
2. **GStack** 工作流（Plan → Eng → Review 三段式，後迭代為 CEO Plan / Mega Plan）

這場專訪也回答了一個全網爭議題：「代碼行數能不能衡量生產力？」Garry Tan 的答案是 — **物理代碼行數毫無意義，邏輯代碼密度（logical code density）才是**。

> [!important] 為什麼這場專訪值得收錄
> 這是「個人 AI 時代」的標誌性案例：一個人 + AI = 過去整個團隊。它也代表了與 [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH|Matt Pocock 5 skills]] **截然不同的工作流哲學**（Token 觀完全相反），值得對比閱讀。

---

## 關鍵洞察（Key Insights）

### 1. AI 是法拉利，你必須是機械師（不只是駕駛員）

> [!quote] Garry Tan 的核心比喻
> 「使用 OpenClaw 這類 AI 智能體就像駕駛一輛頂級的法拉利跑車——它能帶來極致的速度，但極易出現故障。如果你只是一個只會踩油門的駕駛員，沒有修車的能力，它會在你最需要的時刻直接拋錨在路邊。」

**所以使用 AI 的核心不是「輸入指令、等待輸出」，而是要成為能打開引擎蓋、排查故障的機械師。**——必須深入掌握 prompt 編寫邏輯與模型底層原理。

### 2. Tokenmaxxing（Token 最大化）= Boil the Ocean

> 過去人類做研究、寫代碼，會因為精力與時間有限而被迫簡化流程、減少信源。**AI 智能體沒有這個限制**——可以不計成本地全面覆蓋，把海量調研和交叉比對交給 AI，**大膽消耗 Token、投入算力**，換取成果的極致完整、深度和精準。

**對應實踐**：花 5–10 美元 call Opus API → 相當於人類查閱幾十篇文章 + 通讀整本書 + 逐一批注。

**Garry Tan 的成本心法**：每天花 500 美元在 Token 上，只要換回超高生產力就是最划算的投資（用舊金山房租類比：不住在舊金山的機會成本更高）。

### 3. Human in the Loop 永遠不可替代

> [!quote]
> 「如果有人能造出完全不需要人類參與的軟體開發系統，我會無比震驚。我只想讓 AI 幹枯燥的髒活累活，而人類專注於創造、決策和價值把控。這才是人機協作的正確姿態。」

人類負責：提出需求、賦予主觀能動性、把控核心方向
機器負責：消耗算力、處理海量數據、執行重複性工作

### 4. Thin Wrappers, Fat Skills（薄殼應用、厚技能）

這是 Garry Tan 對「Agent 工程」最關鍵的觀察：

> 現在很多人做 AI 應用失敗，是因為**把本該用自然語言描述的邏輯硬塞進脆弱的代碼裡了**。
>
> 正確方式：
> - 用 **Markdown** 編寫**非確定性**的意圖、指令、執行流程（像婚禮策劃師給助手寫執行清單）
> - 用**傳統代碼**處理**確定性**任務（如 API 呼叫）

> [!important] 「Markdown 本質就是另一種形式的代碼，只是編譯方式不同。」
> 工程師的核心能力已經從「編寫代碼」變成「編寫 Skill」——學會劃分大模型處理範圍與代碼處理範圍。

### 5. 邏輯代碼密度 vs 物理代碼行數

> [!quote] 對「代碼行數能不能衡量生產力」的回應
> 「物理代碼行數毫無意義，**邏輯上的代碼密度**才是衡量生產力的核心。1990–2000 年的軟體工程文獻顯示，專業工程師每天的生產級代碼只有 30–50 行。我 2013 年兼職寫代碼時每天只有 14 行；2026 年借助 AI，邏輯代碼密度達到當年的 400 倍。**AI 不會像人類一樣為了刷行數而刻意注水代碼**。」

---

## Garry's List 案例：Posterous 三次重構

這是貫穿全片的標誌性案例。同一個產品（Posterous）的三次實作：

```
┌─────────────────┬────────────┬─────────┬──────────┬──────────────────┐
│      版本       │   人數     │  時間    │   成本    │      亮點         │
├─────────────────┼────────────┼─────────┼──────────┼──────────────────┤
│ 1. Posterous    │  6–7 人    │ 1.5 年   │ 400 萬 USD │ YC 2008 第一項目 │
│    (2008)       │            │          │           │ 曾為全球前 200   │
│                 │            │          │           │ 網站、Twitter    │
│                 │            │          │           │ 2000 萬 USD 收購 │
├─────────────────┼────────────┼─────────┼──────────┼──────────────────┤
│ 2. Post Haven   │  2 人      │ 3 個月   │ 10 萬 USD │ 第二次重構       │
├─────────────────┼────────────┼─────────┼──────────┼──────────────────┤
│ 3. Garry's List │  1 人      │ 5 天     │ ~200 USD  │ Claude Code      │
│   (2026)        │ (Garry Tan)│         │          │ + RAG + Agent    │
│                 │            │          │           │ 100K+ GitHub ⭐  │
└─────────────────┴────────────┴─────────┴──────────┴──────────────────┘

第 1 → 第 3 版：人力 1/7、時間 1/110、成本 1/20000，且功能更完整
```

第三版的核心升級：**不再只是博客工具**——整合 RAG + Agent，能遞迴爬取整個互聯網（如 Garry 自己所有推文），對任何議題做深度研究、交叉比對所有支持與反對觀點、生成資料來源完備的報告，「相當於包攬了頂尖調查記者的全部工作」。

> 動機其實是政治參與：Garry Tan 在舊金山政治實踐中發現公立學校七八年級學生很難正常學習代數，這正是他當年考入 Stanford 工程學院的基礎。他認為「優質教育不應該是富人的特權」，決定親自寫平台來發聲。

---

## GStack 工作流：從繁瑣指令到 CEO Plan

### 起源：把常用指令整理到 Apple Notes

> 「我原本沒有計劃做這個框架，只是因為開發中反覆輸入相同的指令覺得繁瑣，於是把常用指令整理到 Apple Notes，再導入 Claude Code，慢慢形成了固定流程。」

### 早期關鍵發現：先畫 ASCII 圖再寫代碼

> [!tip] 對 Claude Code 的 prompt 技巧
> 寫代碼**前**，先讓 Claude Code 用 ASCII art 畫出：
> - 完整的資料流
> - 輸入/輸出
> - 用戶動線
> - 報錯資訊
> - 狀態機（state machine）
> - 依賴圖（dependency graph）
> - 處理流水線
> - 決策樹
>
> 這相當於給 AI 預載了完整的上下文，**直接解決了 AI 寫代碼出現 Bug、邏輯不全的問題**。

### 迭代為 Plan-Eng-Review 範式

```
Plan (計畫)
  │
  ▼
Engineering (工程)
  │
  ▼
Review (審查)
  │
  ▼ 回到 Plan 或交付
```

### CEO Plan / Mega Plan：元提示詞（Meta-Prompt）

借鑑 Airbnb 共同創辦人 Brian Chesky 的「**十星級體驗（10-Star Experience）**」理念：
- 普通人評產品只到 5 星
- Brian Chesky 會追問：6 星、7 星、10 星的體驗是什麼？逼出產品的完美形態

Garry Tan 把這個理念融入 AI prompt：

> 讓 AI 在開發時思考「10 倍速的檢驗標準」——**如何用 2 倍的力氣，交付 10 倍的價值**。

這個小小的指令調整，讓 AI 能從模型的**隱空間（Latent Space）**中提取更優質的方案，把項目目標具象化。**這是 G-Stack 最核心的價值之一。**

### Garry Tan 的日常開發流程

```
┌─────────────────────────────────────────────────────────┐
│  起點：永遠是「答疑時間（Office Hour）」+ CEO 審查       │
└────────────────────┬────────────────────────────────────┘
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   設計審查      開發者體驗     工程審查
   (UI)          審查           (Eng Review)
       │             │             │
       └─────────────┼─────────────┘
                     ▼
            ┌──────────────┐
            │ Codex 執行   │ ── Conductor 管理任務隊列
            │ (主力 coding)│   過去 48h：13 個 PR
            └──────┬───────┘
                   ▼
            ┌──────────────────────────┐
            │ Playwright 自動瀏覽器測試 │ (封裝後解決 MCP 慢的問題)
            └──────────────────────────┘
```

**讓 AI 同時承擔多個角色**：CEO、設計師、開發者體驗專員、測試工程師。Garry Tan 自己只負責把控核心方向、驗證最終成果。

### 測試覆蓋率心法

> [!warning] Vibe Coding 新手的痛點
> 手寫代碼時只會做最少的測試，只想寫新功能，導致代碼質量粗糙——80% 情況能勉強運行，一旦有真實用戶就崩潰。

**Garry Tan 的結論**：100% 測試覆蓋率過於冗餘，**80%–90% 才是最佳實踐**。

---

## 工具分工：Claude Code + Codex 互補

| 工具 | 定位 | 適用場景 |
|------|------|---------|
| **Claude Code** | 統籌規劃 | 適配 ADHD 工作模式、整體流程編排，但偶爾出現幻覺 |
| **Codex** | 主力編程 | 「智商 200 的極客 CTO」，硬核複雜問題、Bug 排查 |
| **Playwright** | QA | 自動瀏覽器測試、質量驗證；封裝後解決 Claude Code MCP 速度慢的問題 |

**時間分配**：50–60% 用 Claude Code，剩下用 OpenClaw。

---

## gbrain：解決 Claude Code「暴力檢索」的個人 RAG 系統

Garry Tan 個人正在研發的下一個項目：

**動機**：解決 Claude Code 暴力檢索、浪費上下文視窗（Context Window）的問題

**技術棧**：
- Vector Embedding
- Hybrid RRF（Reciprocal Rank Fusion）
- Chunking
- Postgres + pgvector 插件
- 完整 RAG 系統

**洞察**：
> 隨著代碼庫不斷擴大，**人類會把代碼邏輯加載到大腦中，而 AI 也需要同樣的上下文理解**。

---

## 詳細內容（Details）：個人 AI 黃金時代

### Homebrew Computer Club 時刻

Garry Tan 認為我們正處於 AI 時代的 **Homebrew Computer Club** 階段——就像 1976 年蘋果 I 型電腦誕生時，Jobs 與 Wozniak 用麵包板、木箱拼湊出個人電腦。

**現在的對應**：普通開發者只需 **2–3 小時 + 500–1000 美元 Token 成本**，就能搭建屬於自己的 AI 智能體系統。

### 用 Token 買回時間

> [!quote] 整場專訪最動人的金句
> 「我羨慕擁有大量自由時間的『時間億萬富翁』。而 AI 讓每個人都能調用幾百萬年的機器時間，為自己的目標服務。我作為 YC 總裁，時間極度稀缺，只能在會議間隙開發項目；而 AI 幫我把每一分鐘都放大價值，讓我也成為了時間的億萬富翁。」

### YC 核心格言

> **「Live in the future, build what's missing.」**
> （生活在未來，構建缺失的東西。）
>
> Tokenmaxxing 就是對這句話的最佳實踐。

---

## 我的心得（My Takeaways）

1. **Tokenmaxxing 與 Memento 模式是兩種極端**——[[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH|Matt Pocock]] 主張「100K token 後變笨、要 clear context、節省 system prompt」；Garry Tan 主張「不計成本投入算力、Boil the Ocean、每天 500 美元」。兩者其實**不衝突**：Matt 講的是**單 session 內**的 token 管理，Garry 講的是**整體成本投入**態度。可以同時採用：單 session lean，但整體不省 API call。
2. **「邏輯代碼密度」是更誠實的生產力指標**——值得在自己工作中改用「完成的有意義任務數」而非「打字量」。
3. **Thin Wrappers / Fat Skills 是非常深刻的設計原則**——這就是 [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0|Karpathy 的 Software 3.0]] 在實作上的具體化：自然語言 = 第三類程式語言。
4. **CEO Plan 的「10x 思考」可遷移到我自己的 prompt 庫**——下次寫 KB ingestion prompt 時加一句「if a 10x version exists, what would it look like」。
5. **Playwright 封裝替代 MCP** 是個聰明 hack——MCP 慢就直接繞過，這個務實態度值得學。
6. **「我會用一個 1 人團隊重寫過去 6–7 人團隊做的東西」這個 mindset 太強了**——不是想著用 AI 提升 20%，而是想著「過去什麼是不可能的，現在可不可以」。

---

## 待補充（Open Questions）

1. **GStack 完整公開了嗎**？影片提到 Garry Tan 把「簡單的技能框架發到網上、20 萬人瀏覽」，後來迭代為 CEO Plan / Mega Plan，但沒給出 repo URL。建議搜尋：`garry tan gstack github` / `garry tan ceo plan skill`。
2. **「過去 48 小時提交 13 個 PR」的 Conductor 工具細節**？看起來像是 Claude Code 任務隊列管理工具，但不是內建的。建議搜尋：`claude code conductor task queue PR`。
3. **gbrain 開源了嗎**？Garry Tan 說「AI 開源黃金時代到來」，自己的 gbrain 是否準備開源？建議追：Garry Tan 個人 GitHub。
4. **400 倍如何驗證**？影片提到「用專業工具做了標準化分析」，但工具名與方法都沒給。建議搜尋：`logical code density measurement tool` / `garry tan productivity benchmark methodology`。
5. **Codex 在 2026 年是哪個版本**？OpenAI 的 Codex（2021 退役）、GitHub Copilot 還是新一代？建議追：OpenAI 2026 Codex 相關公告。
6. **與 [[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK|既有 GStack 篇章]] 的差異**？KB 已有 GStack 介紹，本篇是否揭露了新內容？需後續比對。
7. **「Token 買時間」的長期成本曲線**？如果每天 500 美元 Token，年成本 ~18 萬美元；對個人是否真划算？對企業團隊呢？

---

## 相關連結（Related）

- [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]] — **必讀對照**：另一套完全不同的 AI coding 工作流哲學，特別是 Token 觀完全相反
- [[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]] — GStack 在 KB 中已有的介紹，本篇補充 Garry Tan 親自談 GStack 的起源與 CEO Plan 演化
- [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] — Karpathy 的 Software 3.0 與 Garry Tan 的「Markdown 就是代碼」高度同調
- [[2026-04-25-CLAUDE-SKILLS-PLAYBOOK-DESCRIPTION-SUBAGENT-DEBUG-PROMPTS]] — Skill 設計手冊，可印證 Garry Tan 的「Fat Skills」哲學
- [[2026-04-18-CLAUDE-CODE-TOKEN-QUOTA-THREE-TRAPS-AND-FIXES]] — 與 Tokenmaxxing 的反向視角：怎麼樣不浪費 Token
- [[2026-05-09-STOP-RANDOM-SKILL-4-CORE-GROUPS-FOR-AGENT-PRODUCTIVITY]] — 另一個 skill 分類框架，可與 GStack 對照
- [[2026-03-23-GRILL-ME-SKILL-DEEP-DIVE]] — Matt Pocock 的「對齊優先」與 Garry Tan 的「CEO Plan 元提示」可對照

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | Tokenmaxxing / Boil the Ocean、GStack 三段式（Plan-Eng-Review）、CEO Plan / Mega Plan、Thin Wrappers Fat Skills、Garry's List = Posterous 第三次重構（1 人 / 5 天 / 200 美元）、80–90% 測試覆蓋率、邏輯代碼密度 = 400×、Homebrew Computer Club 時刻、Brian Chesky 10 星級體驗 |
| **理解（半被動）** | 解釋概念的含義及關聯 | 三條主線串起：(1) 哲學線 — 法拉利比喻 → 機械師心態 → Human in the Loop；(2) 方法論線 — Tokenmaxxing → GStack → CEO Plan → Thin Wrappers Fat Skills；(3) 證據線 — Posterous 三次重構 + 400× 邏輯代碼密度。三線收斂於「個人 AI 革命」 |
| **分析（主動）** | 檢驗論點、拆解假設 | 假設 1：「每天 500 美元 Token 投入划算」對個人開發者門檻極高；假設 2：「邏輯代碼密度 400×」用什麼工具量？影片沒給；假設 3：「Garry Tan 是時隔 13 年的新手」但他是 YC 總裁，每天接觸最新 AI 工具的密度遠超普通人，這個對照組不公平；假設 4：「Boil the Ocean」與 Matt Pocock 的 Memento 模式衝突，必須區分「單 session lean」vs「整體不省」 |
| **應用（主動）** | 將知識套用情境 | 1) 把「寫代碼前先讓 AI 畫 ASCII 圖（資料流/狀態機/決策樹）」加入自己的 Claude Code 工作流；2) 把「10x 思考」加入個人 prompt 庫（每個 task 都問：如果 10x 版本長怎樣？）；3) 把「Thin Wrappers, Fat Skills」當成判斷新 AI 工具好壞的 lens；4) 用 Playwright 封裝替代慢的 MCP server |
| **評估（主動）** | 比較替代方案 | vs Matt Pocock 5 skills：Garry 更實用主義（80% 覆蓋夠了）、Matt 更教條（vertical TDD 嚴格）；vs Karpathy AgentHub：Garry 是個人實踐者、Karpathy 是基建願景者；vs Superpowers / GSD：GStack 比這兩者更輕量、更個人化、更聚焦 review 環節 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「邏輯代碼密度」具體怎麼測？是 cyclomatic complexity？是 feature points？影片沒給工具與公式，這是核心數字的關鍵漏洞。
- **假設**：「400 倍」是個人最佳記錄還是平均？2013 年「每天 14 行」是兼職基準還是專業基準？比較基線（baseline）的選擇能戲劇性改變結論。
- **證據**：Posterous 三次重構的對照數據（6-7 人/1.5 年/400 萬 vs 1 人/5 天/200 美元）非常震撼，但**功能等價性**沒有第三方驗證——第三版多了 RAG / Agent，前兩版沒這些；如果只比同等功能，比率可能小很多。
- **觀點**：反對者可以說「Tokenmaxxing 是 YC 總裁的特權，普通開發者一年算力預算可能就是 Garry Tan 一天，500 美元/天的範式不可遷移」。
- **後果**：若全行業擁抱 Tokenmaxxing，12 個月後可能出現：(a) 算力消耗成為主要成本，雲服務商獲利暴漲；(b) 一人公司爆炸性增長；(c) 中階開發人才需求大幅萎縮（但 Senior + AI 需求暴增）；(d) 「Thin Wrappers Fat Skills」式 AI 應用淘汰大量「重代碼薄 prompt」的舊產品。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — **成本失控與 prompt 漂移**：每天 500 美元在實驗階段燒著爽，產品上線後變成持續性 OPEX，毛利可能完全被 token 吃掉。最壞情況：你做了一個「示範性」很強的產品但根本沒商業模式。另外 Tokenmaxxing 鼓勵「不計成本」會養成「能不思考就交給 AI」的反思惰性，長期削弱判斷力。
2. **什麼情況下會失敗？**
   - **付費 API 預算受限**（學生 / 獨立開發者 / 早期 startup）
   - **任務本質確定性極高**（CRUD / 報表）：傳統代碼成本更低
   - **資料敏感性高**（醫療 / 金融）：不能無限制送進雲端 LLM
   - **延遲敏感**（即時系統）：deep research 模式秒級回應做不到
   - **個人沒有 senior 工程背景**：Garry Tan 強調「要當機械師」，新手連 prompt 都寫不好，Tokenmaxxing 會放大錯誤
3. **有沒有更好的替代方案？**
   - **預算受限場景**：用 [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH|Matt Pocock 的 Memento 模式]] + small-grain task 比較省
   - **企業團隊**：[[Karpathy AgentHub]] 提供共用基建，避免每人各自 Tokenmaxx
   - **生產級 AI 應用**：用混合架構 — confidence 高的走確定性代碼、confidence 低才走 LLM；不要全量 Tokenmaxx
   - **學習階段**：先掌握傳統 SE 基礎，再加 AI 槓桿；直接跳到 Vibe Coding 會塌方

---

## References

- [影片：AI给我带来400倍生产力 | YC总裁Garry Tan（最佳拍檔 Best Partners TV，14:24）](https://www.youtube.com/watch?v=fmR91KKSEuc)
- [原始來源：Lightcone Podcast — Garry Tan on YC channel](https://www.youtube.com/watch?v=57lDpTwiW6g)
- [Garry Tan 個人 Twitter](https://twitter.com/garrytan)
- [Y Combinator](https://www.ycombinator.com/)
- 相關背景：Frederick P. Brooks Jr., *No Silver Bullet* — 軟體工程沒有銀彈，但 Garry Tan 試圖證明 AI 就是這發銀彈
- Brian Chesky（Airbnb co-founder）的 **10-Star Experience** 設計理念
