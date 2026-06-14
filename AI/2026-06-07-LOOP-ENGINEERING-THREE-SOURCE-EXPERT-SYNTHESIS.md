---
title: "Loop Engineering（迴圈工程）綜合分析：上游源頭 Rahul 原文 × 三個下游觀點（學理／產品原語／實作紀律）"
date: 2026-06-07
category: AI
tags:
  - ai/agents
  - ai/loop-engineering
  - ai/agentic-workflow
  - tools/claude-code
  - meta/comparative-analysis
source: "https://addyosmani.com/blog/loop-engineering/"
source_type: article
author: "Sai Rahul（源頭）/ Addy Osmani / MindStudio / lunkerchen（綜合四來源）"
status: notes
links:
  - "[[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]]"
  - "[[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]]"
  - "[[2026-03-30-BORIS-CHERNY-HIDDEN-CLAUDE-CODE-FEATURES]]"
  - "[[2026-03-17-KARPATHYS-AGENTHUB-A-PRACTICAL-GUIDE-TO-BUILDING-YOUR-FIRST-AI-AGENT-SWARM]]"
  - "[[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]]"
  - "[[CLAUDE-MEMORY-ENGINE]]"
multi_source: true
sources_compared:
  - "https://x.com/sairahul1/article/2064277888216555684"  # 上游源頭
  - "https://addyosmani.com/blog/loop-engineering/"
  - "https://www.mindstudio.ai/blog/what-is-loop-engineering-ai-coding-agents"
  - "https://github.com/lunkerchen/loop-engineering-skill"
---

## 摘要（Summary）

「迴圈工程（Loop Engineering）」是 2026 年中浮現的一個概念轉向：**你不再親自提示（prompt）代理人的每一步，而是設計一套會自己提示代理人的系統。** 本筆記交叉比較四個來源：**上游源頭** Sai Rahul 的 X 長文《Loops: What Every AI Engineer Needs to Know in 2026》（普及與綜合者），以及三個**下游觀點**——Addy Osmani 的部落格（實踐者兼懷疑論者）、MindStudio 的教學文（學理 + 廠商）、lunkerchen 的 `loop-engineering-skill` GitHub repo（可執行的實作紀律）。四者恰好構成一個從**源頭框架 →（學理 / 產品原語 / 實作紀律）三向擴散**的傳承樹。

> [!important] 補記（本次更新）：找到了共同上游源頭
> 原筆記留有一條 Open Question：「三來源共同引用的 Rahul《Loops 2026》原文在哪？」——**已找到並納入**（見下方〈源頭考據〉一節）。關鍵證據：repo 的 `SKILL.md` 明確標註 inspired by Rahul，且其分層路由點名的 DeepSeek / Kimi / MiniMax **直接繼承自 Rahul 的成本論述**；Addy 文與 Rahul 文更有**近乎逐字的重疊段落**。Rahul 是這波概念的「中央散播節點」。

核心結論：四者在「迴圈是什麼、需要哪些零件」上高度互補（六原語 + 五階段幾乎是共識）；但在**「驗證的最終責任歸誰」與「成本是該抽象掉還是該正面管理」**兩點上存在真實張力。Addy 的警句最值得記住：「**Build the loop. Stay the engineer.**（設計迴圈，但仍要當那個工程師。）」——而這句話其實源自 Rahul 的「build it like someone who intends to stay the engineer」。

> [!important] 一句話定位四來源
> - **Sai Rahul（源頭）** 把 Steinberger / Cherny 的兩則推文「翻譯成完整心智模型」，並補上**成本經濟學**——其餘三者都是它的下游分流
> - **MindStudio** 回答「迴圈是什麼」（WHAT / WHY，往上接到學術界的 ReAct）
> - **Addy Osmani** 回答「迴圈由哪些已上市的產品原語組成」（生態系層，工具中立）
> - **lunkerchen repo** 回答「怎麼把迴圈做出來、為什麼會壞」（實作 + 失敗模式 + 程式碼）

---

## 三來源定位速覽

| 維度 | Addy Osmani 部落格 | MindStudio 教學文 | lunkerchen `loop-engineering-skill` |
|------|------------------|------------------|-------------------------------------|
| 體裁 | 實踐者隨筆（帶懷疑） | 教學文 + 產品行銷 | 開源 Skill（Hermes Agent 格式）|
| 抽象層 | 生態系 / 產品原語 | 概念 / CS 教科書 | 實作 / 工程紀律 |
| 思想源頭 | Peter Steinberger、Boris Cherny（業界 2025–2026） | ReAct 論文（Princeton + Google，學術） | Rahul《Loops 2026》+ Steinberger + Cherny（橋接兩者）|
| 核心框架 | 5 原語 + 記憶（共 6 件） | 迴圈解剖 5 要件 + 4 種迴圈模式 | 5 階段 + 6 元件 + 5 大殺手 |
| 工具立場 | 工具中立（Codex ↔ Claude Code 對照） | 導流到 MindStudio 平台 | Hermes / Nous Research（但開源 MIT）|
| 成本態度 | 警告「token 成本要小心」 | 淡化（交給平台處理） | 正面管理（明列 token 預算 + 分層路由）|
| 對人的角色 | 強調「人仍是天花板與最終驗證者」 | 幾乎不談（強調可自動化、無程式碼）| 強調 maker≠checker，但偏向自動化驗證 |
| License / 形態 | 文章 | 文章（含 FAQ）| MIT，含 3 支 bash script |

> [!note] 上表是「三個下游觀點」的橫向比較；它們共同的**上游源頭**是下一節分析的 Rahul 原文。

---

## 源頭考據：Sai Rahul 的原始框架與傳承樹

> [!important] 這一節是本筆記的更新重點。前一版把 Rahul 列為待查；現已取得原文（[X 長文](https://x.com/sairahul1/article/2064277888216555684)），並確認它是整波「Loop Engineering」論述的**中央散播節點**。

### 傳承樹（Lineage）

```
        Peter Steinberger（OpenClaw→OpenAI）："Stop prompting. Design loops."
        Boris Cherny（Claude Code）："My job is to write loops."
                          │  （兩則推文，原始火花）
                          ▼
        ┌─────────────────────────────────────────────┐
        │  Sai Rahul《Loops 2026》X 長文（源頭/普及者）   │
        │  把兩則推文「翻譯成完整心智模型」               │
        │  6 building blocks · 5 stages · open/closed    │
        │  + 成本經濟學（中國 LLM 是解方）                │
        └───────┬───────────────┬───────────────┬───────┘
                │               │               │
        近乎逐字重疊        概念對齊         明確標註 inspired by
                ▼               ▼               ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
        │ Addy Osmani  │ │ MindStudio   │ │ lunkerchen repo  │
        │ 生態系/產品   │ │ 學理(ReAct)  │ │ 實作/Hermes/碼   │
        └──────────────┘ └──────────────┘ └──────────────────┘
                                │
                          往上接學術源頭
                                ▼
                ReAct（Reason+Act, Princeton+Google）
```

### 三項傳承證據（為何斷定 Rahul 是源頭）

1. **repo 明確標註。** `loop-engineering-skill` 的 `README.md` 開宗明義：「Inspired by Rahul's "Loops: What Every AI Engineer Needs to Know in 2026"」。其 SKILL.md 的 token 成本數字（50K–200K / 500K–2M）、分層路由點名的 **DeepSeek V4 Flash / Kimi / MiniMax**，全都直接搬自 Rahul——這解答了原 Open Question「repo 的 token 數字與模型名稱從哪來」。
2. **Addy 與 Rahul 近乎逐字重疊。** 兩篇都用同樣的 Steinberger/Cherny 引言、同樣的「每天早上 triage 迴圈」例子，結尾更幾乎一字不差：Rahul「build it like someone who intends to stay the engineer」↔ Addy「Build the loop. Stay the engineer.」；「兩個人造一模一樣的迴圈會得到完全相反的結果」這段在兩文都出現。傳承關係明確（共同推文源 + 高度互文）。
3. **六原語清單同源。** Rahul 的「6 building blocks」與 Addy / repo 的清單**完全相同且同序**（Automations → Worktrees → Skills → Plugins → Subagents → Memory），且每條都附「它在 5 階段裡觸發哪一步」的對應——這個「原語 ↔ 階段」對應正是 Rahul 的原創編排。

### Rahul 獨有、其他三者較弱的三項貢獻

> [!info] 為什麼仍值得單獨讀 Rahul：他補上了下游各自省略的「為什麼負擔得起」與「先做哪種」。

**(A) 成本經濟學 + 中國 LLM 是解方（最鮮明的原創角度）**

Rahul 把「成本」當成全文的**第一個**段落，而非附註。他直言這是「沒人先告訴你的隱藏障礙」：

> 「Loops are not hard to design. They are hard to afford.（迴圈不難設計，難在負擔得起。）」

他的數字與解方（repo 的成本章節即源自此）：

| 規模 | Token 消耗 |
|------|-----------|
| 單代理人中型編碼任務 | 50,000–200,000 tokens |
| 艦隊迴圈（orchestrator + 3 專家）| 500,000–2,000,000 tokens |
| 每日排程迴圈 | 每週數百萬 tokens |

解方是**中國前沿模型**——DeepSeek V4、Kimi、MiniMax 讓迴圈「在經濟上可行」。他特別點名 DeepSeek V4：**1M 上下文視窗、384K 最大輸出、Flash + Pro、極低 token 定價、高併發（Flash 達 2500 requests）**，並下了金句：「**1.7 billion tokens for \$20**，你終於負擔得起造一個迴圈。」

> [!warning] 偏誤提醒
> 此段帶有明顯的「中國模型推廣」傾向（數字與定價皆為自述、未引第三方評測）。可信的部分是**論點結構**（成本是真實障礙、便宜前沿模型改變方程式）；不可盡信的是**具體數字與模型優劣排名**。

**(B) Open Loop vs Closed Loop——「2026 最重要的實務區分」**

| 類型 | 特性 | 預算 | Rahul 的建議 |
|------|------|------|-------------|
| **Open Loop（開環）** | 探索性、自由漫遊、能做出你沒完整 spec 的東西 | 燒錢兇（「眼睛流淚」）| 對標準鬆散的專案會變「slop machine」；90% 沒有無限預算的人「還不實用」|
| **Closed Loop（閉環）** | 有界、人先設計好端到端路徑 + 每步 eval gate | 一般預算可負擔 | **先從閉環開始**，建好品質閘門後再開放 |

repo 的「Open/Closed 兩種迴圈類型」即直接繼承這組區分，但 Rahul 把它和**預算**綁在一起講，更務實。

**(C) Prompt Engineer vs Loop Engineer——明確的技能斷層表**

| | Prompt Engineer | Loop Engineer |
|---|----------------|---------------|
| 核心 | 寫更好的指令（語言技巧）| 設計更好的回饋循環（軟體工程技巧）|
| 產出 | 更好的單次輸出 | 可靠、已驗證的結果 |
| 誰是回饋循環 | **你**（每次手動 review）| **系統**（自我檢查、自我修正）|
| 一句話 | "Write me a function" | "Write → test → fix until green" |
| 付費對象 | 單次輸出 | 已驗證的結果 |

> [!quote] Rahul 的定錨句
> 「Prompt engineers ask AI for output. Loop engineers design systems that produce verified outcomes.（提示工程師向 AI 要產出；迴圈工程師設計能產出『已驗證結果』的系統。）」「One reliable loop is worth a thousand perfect prompts.（一個可靠的迴圈，勝過一千個完美的提示。）」

### Rahul 的四個實戰迴圈範本（程式碼完整保留）

Rahul 給了四個可直接套用的迴圈骨架，這是其他三者都沒有的「即用範本」：

```plaintext
The Coding Loop
Read VISION.md + ARCHITECTURE.md
↓
Plan the next change
↓
Edit the code
↓
Run tests automatically
↓
If tests fail → read error → fix → retest
↓
If tests pass → summarize changes
↓
Stop
```

```plaintext
The Research Loop
Define research question
↓
Search for sources
↓
Summarize findings
↓
Verify claims against sources
↓
Compare conflicting information
↓
Synthesize final answer
↓
Stop when confidence threshold met
```

```plaintext
The Content Loop
Topic + audience + goal defined
↓
Draft created
↓
Critique agent reviews draft
↓
Rewrite based on critique
↓
Score against success criteria
↓
If score passes → publish
↓
If score fails → rewrite again
```

```plaintext
The Sales Outreach Loop
ICP (Ideal Customer Profile) defined
↓
Find leads matching profile
↓
Enrich with company data
↓
Qualify against criteria
↓
Personalize message
↓
Quality review
↓
Send or escalate to human
```

> [!tip] 共同骨架
> Rahul 點破四者其實是同一副骨架：**Goal → Action → Check → Fix → Repeat until done。** 換掉「Action」與「Check」的內容，就是不同領域的迴圈。

---

## 關鍵洞察（Key Insights）

- **槓桿點移動，不是工作變簡單。** 三者一致：價值從「寫好一個 prompt」移到「設計好一個迴圈」。Addy 點破——Cherny 的意思不是工作變輕鬆，而是「leverage point moved（槓桿支點移位了）」。參見 [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] 的 Software 3.0 脈絡。
- **「迴圈」的反面是「鏈（chain）」。** MindStudio 給了最清楚的定義學界界線：chain 是線性 A→B→C 且可預測；loop 是動態的，可重試、可改策略、可回退。迴圈工程的本質就是「閉合回饋落差（close the feedback gap）」。
- **六大原語在三者間幾乎逐一對齊。** Automations、Worktrees、Skills、Plugins/Connectors、Subagents、Memory——Addy 與 repo 用的是**同一份清單**，差別只在 Addy 對照 Codex/Claude Code 產品，repo 對照 Hermes 實作。這代表此清單已接近業界共識。
- **maker ≠ checker 是迴圈能無人值守的唯一理由。** repo 把它寫成硬規則：Worker（context A）與 Verifier（context B）必須是**獨立 API 呼叫、無共享歷史**——「繼承了 worker 上下文的 verifier，也繼承了它的盲點」。這正是 Claude Code `/goal` 底層在做的事。參見 [[2026-03-30-BORIS-CHERNY-HIDDEN-CLAUDE-CODE-FEATURES]]。
- **「迴圈是 harness 的上一層樓。」** Addy 明言 loop engineering 坐落在 agent harness engineering 之上——harness 是單一代理人運行的環境，loop 是讓它「按時觸發、生小幫手、自我餵食」的那一層。參見 [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]]、[[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]]。
- **記憶必須在磁碟上，不在上下文裡。** 三者都強調：模型每次 run 之間會遺忘，所以「做完什麼、下一步什麼」要存成 Markdown / Linear 板 / 狀態檔。repo 更進一步——**存的是「規則」不是「日誌」**。參見 [[CLAUDE-MEMORY-ENGINE]]。
- **真正的障礙不是智力，是 token 成本。** 這是源頭 Rahul 最被低估、卻被下游淡化的洞察：「迴圈不難設計，難在負擔得起。」開環（open loop）燒錢兇到「90% 沒有無限預算的人還不實用」——所以務實路線是**先做閉環（closed loop）**，用便宜前沿模型，建好品質閘門再開放。參見 [[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]]。

---

## 詳細內容（Details）

### 一、共同核心：六大原語與五階段

三來源最大的交集，是把「一個會自走的迴圈」拆成可辨識的零件。Addy 與 repo 的清單幾乎一字不差：

| 原語（Primitive） | 在迴圈裡的職責 | Codex App（Addy） | Claude Code（Addy） | Hermes 實作（repo） |
|------------------|--------------|-------------------|---------------------|---------------------|
| **Automations** | 排程觸發發現與分流（心跳） | Automations 分頁 + Triage 收件匣 + `/goal` | 排程任務、cron、`/loop`、`/goal`、hooks、GitHub Actions | `cronjob` 排程 |
| **Worktrees** | 平行代理人不互相踩檔 | 每 thread 內建 worktree | `git worktree`、`--worktree`、`isolation: worktree` | `git worktree add` → `.worktrees/<branch>/` |
| **Skills** | 把專案知識寫下來、每 run 複利 | Agent Skills（`SKILL.md`） | Agent Skills（`SKILL.md`） | `project-context/*` + VISION/ARCH/RULES 文件 |
| **Plugins / Connectors** | 讓迴圈能動到真實工具（DB、Slack、Linear） | Connectors（MCP）+ plugins | MCP servers + plugins | MCP 工具、`delegate_task` |
| **Subagents** | 出主意的人 ≠ 檢查的人 | `.codex/agents/`（TOML） | `.claude/agents/` + agent teams | `delegate_task role=leaf/orchestrator` |
| **Memory / State** | 跨 run 不遺忘 | Markdown 或 Linear（connector）| Markdown（`AGENTS.md`、進度檔）或 Linear（MCP）| `.dev-loop-state.md`、`skill-compounder.sh` |

repo 則把「執行流程」濃縮成**五階段（5 Stages）**，這是 MindStudio 的 ReAct「reason→act→observe→repeat」之工程化版本：

```
DISCOVER ─► PLAN ─► EXECUTE ─► VERIFY ─► ITERATE（或 DONE）
   探索        規劃      只做必要      獨立      過 = 出貨
   狀態        分解      的事 + 抓     脈絡      不過 = 診斷
            選模型層級    輸出/metadata  驗證      → 換策略再迴圈
```

> [!note] 關鍵術語（Key Term）：ReAct 模式（Reason + Act）
> 由 Princeton 與 Google 提出，做法是**把推理步驟與行動步驟交錯**：模型先想（reason）、再做（act）、觀察結果（observe）、再想、再做。MindStudio 指出，現代所有代理人迴圈幾乎都可追溯到這個模式——它是迴圈工程的學理起點。

### 二、三方比較矩陣：互補與互斥

#### 🟢 互補之處（三者拼起來才完整）

1. **抽象層互補（這是最大的價值）。** 三者剛好疊成一個堆疊：MindStudio 的「迴圈解剖」（Goal / Tools / Context / Termination / Error handling）解釋了 repo「五大殺手」每一條在防什麼；Addy 的「六原語」則告訴你這些零件**今天用哪個產品按鈕就能拿到**。

   ```
   ┌──────────────────────────────────────────────┐
   │  MindStudio：WHY / WHAT                        │
   │  ReAct 學理、迴圈 vs 鏈、解剖 5 要件、4 種模式    │
   └───────────────────┬──────────────────────────┘
                       │ 「概念落地成產品」
   ┌───────────────────▼──────────────────────────┐
   │  Addy Osmani：生態系原語                        │
   │  6 原語 × Codex/Claude Code 對照、工具中立        │
   └───────────────────┬──────────────────────────┘
                       │ 「產品落地成程式碼」
   ┌───────────────────▼──────────────────────────┐
   │  lunkerchen repo：實作紀律                      │
   │  5 階段、5 殺手、Worker/Verifier 碼、bash script │
   └──────────────────────────────────────────────┘
   ```

2. **失敗模式 ↔ 解剖要件，恰好對應。** MindStudio 的「一個好迴圈需要的 5 要件」與 repo 的「5 大殺手」是同一枚硬幣的兩面：

   | MindStudio 解剖要件（正面） | repo 5 大殺手（反面） |
   |--------------------------|---------------------|
   | 明確目標 + 可測終止條件 | （目標模糊 → 無限迴圈）|
   | 上下文管理 | **Context Collapse**（第 12 步忘了第 1 步要什麼）|
   | 錯誤處理（真正適應，非重試）| **No Self-Correction**（同錯重試、昂貴空轉）|
   | 終止邏輯（成功/失敗/升級）| —（對應 repo 的 VERIFY gate）|
   | 工具集 | —；repo 補上 **No Verifier / No Guardrails / No Memory** |

3. **迴圈模式詞彙互補。** MindStudio 提供了 Addy 與 repo 都沒明列的「模式分類學」：Retry Loop、Plan-Execute-Verify Loop、Explore-Narrow Loop、Human-in-the-Loop——這是挑選迴圈架構時的實用詞彙表。

#### 🔴 互斥 / 張力之處（三者真正分歧）

> [!warning] 張力一：驗證的「最終責任」歸誰？——這是最深的分歧
> - **repo**：驗證可以、也應該交給一個**獨立 context 的自動 verifier**（Worker/Verifier 分離）。傾向「把人移出迴圈」。
> - **Addy**：「**Verification is still on you.**」一個無人值守的迴圈，也是一個無人值守地在犯錯的迴圈。自動 verifier 只是讓「它說完成了」這句話更有份量，但「done 是一個主張、不是一個證明」。
> - **判讀**：兩者不矛盾於技術（都要 maker≠checker），但矛盾於**態度**。repo 解決「機器如何自查」，Addy 提醒「人不能因此交出判斷力」——他稱失去判斷的姿態為 **cognitive surrender（認知投降）**。

> [!warning] 張力二：成本——抽象掉，還是正面管理？（四來源在此分歧最大）
> - **Rahul（源頭）**：成本是**全文第一章**、是「沒人先說的隱藏障礙」。解方＝中國前沿模型（DeepSeek V4 / Kimi / MiniMax），「1.7B tokens for \$20」。最積極面對成本，但帶中國模型推廣偏誤。
> - **repo**：把成本當一級設計議題——明列「單代理人中型任務 50K–200K tokens、艦隊迴圈 + 3 專家 500K–2M、每日排程迴圈每週數百萬」，並用**分層模型路由（Tiered Routing）**正面管理。**此數字與模型清單即承自 Rahul。**
> - **Addy**：居中但偏警戒——「你絕對**必須**小心 token 成本，用量模式落差極大」。參見 [[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]]、[[2026-04-18-CLAUDE-CODE-TOKEN-QUOTA-THREE-TRAPS-AND-FIXES]]。
> - **MindStudio**：基礎設施（重試、限流、狀態管理）「跟實際邏輯無關」，應交給平台（賣點：`@mindstudio-ai/agent` SDK）。**淡化成本**——與 Rahul 恰成兩極。

> [!warning] 張力三：廠商視角的偏誤（Vendor Bias）
> - **MindStudio**：目的是賣平台，因此論述傾向「迴圈很難、基礎設施很煩、交給我們」。
> - **Addy**：刻意工具中立——「一旦你發現形狀都一樣，就不再爭論用哪個工具」。
> - **repo**：綁 Hermes / Nous Research 術語（Fable 5、`delegate_task`、`max_spawn_depth`），但 MIT 開源、可移植。

### 三、實作紀律的精華：repo 的可執行模式

repo 的獨到貢獻，是把抽象原則變成**可貼上就用的程式碼**。以下完整保留三段最關鍵的實作（依語言規則，程式碼不翻譯、不省略）：

**(1) Worker / Verifier 必須是獨立 context**

```python
# worker builds in context A
worker = client.messages.create(model="...", messages=[{"role": "user", "content": prompt}])

# verifier grades in context B — completely independent
verifier = client.messages.create(
    model="...",
    messages=[{"role": "user", "content": f"Grade this output against this rubric:\n\nOUTPUT: {worker.text}\n\nRUBRIC: {rubric}"}]
)
# No shared history. No bias. Clean judgment.
```

**(2) 分層模型路由（Tiered Model Routing）——別用最貴的模型做每件事**

```python
def route_task(task_type, complexity):
    if task_type in ("architecture_decision", "hard_bug_diagnosis",
                     "multi_file_reasoning", "final_verification",
                     "ambiguity_resolution") or complexity == "high":
        return "best-model"        # Fable 5, Opus
    elif task_type in ("data_extraction", "reformatting",
                       "boilerplate_generation", "simple_edit",
                       "routine_retry") and complexity == "low":
        return "cheap-model"       # Haiku, MiniMax
    else:
        return "mid-model"         # Sonnet, DeepSeek V4 Flash
```

> [!tip] 可執行建議（Actionable Tip）
> 規則：「**只在判斷力重要時才升級到貴模型。大多數迴圈迭代很便宜——驗證才是該花錢的地方。**」這與 [[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]] 的 token 經濟學一致。

**(3) 記憶存「規則」不存「日誌」（Memory as Rules, Not Logs）**

```python
def extract_rule(client, failed_attempt, error_output):
    response = client.messages.create(
        model="best-model",
        messages=[{"role": "user", "content": f"""
A task just failed. Extract ONE general rule to remember for next time.

WHAT FAILED:
{failed_attempt}

ERROR:
{error_output}

Write a single clear rule that would prevent this failure in the future.
Format: "RULE: [concise general principle]"
Do not write a note about this specific case.
Write a rule that applies broadly.
"""}]
    )
    return response.text
```

**(4) 閉環腳本 `dev-loop.sh` 的核心迴圈（write → test → fix → verify）**

```bash
while [ "$ITER" -lt "$MAX_ITER" ] && [ "$PASS" = false ]; do
  ITER=$((ITER + 1))
  echo "--- Iteration $ITER/$MAX_ITER ---"

  # Phase: TEST
  TEST_OUTPUT=$(eval "$TEST_CMD" 2>&1) || true
  TEST_EXIT=$?

  if [ "$TEST_EXIT" -eq 0 ]; then
    echo "✓ All tests passed!"
    PASS=true
    break
  fi

  echo "✗ Tests failed (exit $TEST_EXIT)"
  echo "$TEST_OUTPUT" | tail -40

  if [ "$ITER" -ge "$MAX_ITER" ]; then
    echo "⚠ Max iterations ($MAX_ITER) reached. Loop stopping."
    echo "$TEST_OUTPUT" > ".dev-loop-last-error.log"
    break
  fi
  # 代理人讀上面的錯誤 → 改碼 → 重跑
done
```

### 四、迴圈架構全圖（repo 的 Worker + Verifier 控制流）

```
                    ┌─────────────────────────────────┐
                    │           LOOP CONTROLLER        │
                    │  (orchestrator / cron trigger)   │
                    └──────────┬───────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    GOAL + CONTEXT    │
                    │  (what done means)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  1. DISCOVER + PLAN  │
                    │  (decompose, route)  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  2. WORKER (ctx A)   │
                    │  execute -> produce  │
                    └──────────┬──────────┘
                               │  output
                    ┌──────────▼──────────┐
                    │  3. VERIFIER (ctx B) │
                    │  independent check   │
                    │  no shared history   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  4. GATE  pass/fail? │
                    └──────┬──────┬────────┘
                        PASS      FAIL
                           │      │
                    ┌──────▼┐  ┌──▼──────────────┐
                    │ DONE  │  │ 5. DIAGNOSE      │
                    └───────┘  │ root cause       │
                               │ extract rule     │
                               │ new approach     │
                               └──┬───────────────┘
                                  │  back to EXECUTE
                                  └─────────────────►
```

> [!example] Addy 描述的「一個迴圈長什麼樣」（生態系語言版的同一件事）
> 每天早上一個 automation 在 repo 上跑 → 呼叫 triage skill 讀昨天的 CI 失敗、open issues、近期 commits → 寫進 Markdown / Linear → 每個值得做的發現開一個隔離 worktree → 派 sub-agent 起草修正 → 第二個 sub-agent 對照 project skills 與既有測試審查 → connector 開 PR、更新 ticket → 處理不了的丟進 triage 收件匣給人。「**你只設計了一次，沒有提示其中任何一步。**」

---

## 我的心得（My Takeaways）

1. **這三篇該一起讀，而不是擇一。** 單看 MindStudio 會以為是 CS 概念複習；單看 repo 會陷進 Hermes 術語；單看 Addy 又少了可貼上的程式碼。三者疊起來，正好是「概念→產品→程式碼」的完整下樓梯。
2. **六原語清單可直接當我自己的 Loop 自評表。** 我可以拿 Automations / Worktrees / Skills / Plugins / Subagents / Memory 六格，逐格檢查自己現有的 Claude Code 工作流缺哪一塊——這比抽象口號實用得多。對照 [[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]] 的「五層只出三層」盤點法。
3. **「Memory as Rules, not Logs」是最被低估的一招。** 我目前的知識庫多半在存「發生了什麼」，而 repo 提醒我該存「下次該遵守什麼規則」。這正好可以回饋到我自己的 auto-memory 機制。
4. **Addy 的警句是定錨。** 「兩個人造一模一樣的迴圈會得到完全相反的結果。一個用它在自己深刻理解的工作上跑更快，另一個用它來逃避理解工作本身。迴圈分不出差別，你分得出。」——這句話該貼在每個 cron 旁邊。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇綜合內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，確立基礎知識 | 必記術語：①迴圈工程（Loop Engineering）②ReAct（Reason+Act）③六原語（Automations/Worktrees/Skills/Plugins/Subagents/Memory）④五階段（DISCOVER→PLAN→EXECUTE→VERIFY→ITERATE）⑤5 大殺手（Context Collapse / No Self-Correction / No Verifier / No Guardrails / No Memory）|
| **理解（半被動）** | 解釋概念含義與關聯 | 迴圈工程＝把槓桿點從「寫 prompt」移到「設計會自走的回饋系統」。它座落於 harness 之上；學理源於 ReAct；落地靠六原語；可靠性靠 maker≠checker 的獨立驗證。三來源是同一概念的三個抽象切面。|
| **分析（主動）** | 檢驗論點、找出假設 | 關鍵假設：①「獨立 context 的 AI verifier 可信到能無人值守」——Addy 質疑此假設（done 是主張非證明）。②MindStudio 假設「成本可被平台抽象掉」——repo 用實際 token 數字反駁。③六原語清單假設 Codex 與 Claude Code 會持續趨同，若產品分化此對照即失效。|
| **應用（主動）** | 將知識轉為行動 | ①用六原語表盤點自己的 Claude Code 工作流缺口。②把 `route_task` 的分層路由套到自己的多代理腳本，驗證步驟才上 Opus。③在知識庫導入「Memory as Rules」——失敗後抽一條通用規則而非存日誌。|
| **評估（主動）** | 判斷方案優劣與取捨 | 何時該建迴圈 vs 直接 prompt？評估：迴圈在「你深刻理解、且有可測終止條件（測試/lint）」的重複性工作上收益最大；在探索性、需求未定、或你不熟的領域，直接 prompt 反而更安全（避免 comprehension debt 與 cognitive surrender）。MindStudio 的無程式碼平台適合非工程師起步，但會犧牲對成本與終止邏輯的掌控。|

### 分析型追問（Socratic Follow-up）

- **澄清**：「迴圈（loop）」與「代理（agentic）」「harness」三詞最容易混用——本文界定：harness 是單一代理的環境，loop 是讓它按時自走的上一層，agentic 是更廣的傘狀詞。哪個邊界最模糊？
- **假設**：整套迴圈工程成立的最關鍵前提是「自動 verifier 真的能抓到 worker 的錯」。若 verifier 與 worker 用同一個基礎模型、只是不同 context，它們是否共享同一類盲點？
- **證據**：repo 的 token 成本數字（50K–2M）來源未標註、Fable 5 等模型名稱無法查證；MindStudio 的 SDK 能力（120+ 方法）也是自述。哪些主張需要獨立佐證？
- **觀點**：若站在「prompt engineering 還沒過時」的反方，最有力的反駁是——對一次性、創造性、需求模糊的任務，設計迴圈的固定成本遠高於直接對話。
- **後果**：若一個團隊把所有開發都交給排程迴圈，12 個月後最可能出現的非預期副作用是什麼？（候選：comprehension debt 累積、對程式碼失去 mental model、token 帳單失控、對單一代理框架鎖定。）

### 方案批判三問（Critical Evaluation）

> 本文含 repo 的可執行方案（bash script + Python 模式），故加入此區塊。

1. **最大的風險是什麼？** 無人值守迴圈在最壞情況下會「無人值守地持續犯錯並出貨」——若 guardrails（RULES.md、預算上限、唯讀模式）沒設好，可能刪檔、花錢、對外呼叫 API 而無人察覺。更隱性的損失是**工程師對自己程式碼失去理解（comprehension debt）**，最終品質下滑、陷入 Addy 說的「越挖越深的下行螺旋」。
2. **什麼情況下會失敗？** ①目標無法寫成可測終止條件（沒有測試/lint 當 gate）→ 迴圈不知何時停。②worker 與 verifier 共享盲點 → 自動驗證形同虛設。③上下文未分解的長任務 → Context Collapse。④token 預算未設 → 艦隊迴圈每週燒數百萬 token。⑤產品/框架快速演化 → 綁定 Hermes 或 MindStudio 的實作過時。
3. **有沒有更好的替代方案？** 對「你深刻理解 + 重複性 + 可驗證」的工作，迴圈優於直接 prompt；但對**探索性、一次性、需求未定**的工作，**直接 prompt（保留 human-in-the-loop）反而更省成本、風險更低**。務實做法是混合：用迴圈處理 triage / 測試修復 / 例行維護，用直接對話處理架構決策與不確定問題——Addy 本人即主張「找到正確的平衡」。

---

## 待補充（Open Questions）

- ~~repo 引用的「Rahul《Loops 2026》」原文在哪？~~ ✅ **已解決（本次更新）**：原文為 [Sai Rahul 的 X 長文](https://x.com/sairahul1/article/2064277888216555684)，已納入〈源頭考據〉一節；它是三個下游來源的共同上游。
- ~~repo 的 token 數字與「DeepSeek V4 Flash / MiniMax」模型清單從哪來？~~ ✅ **部分解決**：直接承自 Rahul 原文的成本章節。但**仍未解**：Rahul 的數字本身是量測還是估計？「Fable 5」對應 2026 年哪個實際模型？建議搜尋：`DeepSeek V4 1M context pricing benchmark`、`Hermes agent Fable 5 model`。
- 自動 verifier 與 worker 用**同一基礎模型不同 context**時，能否真正避免「共享盲點」？有沒有實證評測顯示獨立 context 比 self-critique 抓錯率高多少？建議搜尋：`verifier shared context blind spot eval`、`self-critique vs independent verifier LLM`。
- **新增**：Rahul 與 Addy 的高度互文，究竟是誰引用誰、還是兩人同時取材自 Steinberger 的推文串？兩篇的發布先後與引用方向值得考據。建議搜尋：`steipete loops tweet`、`addyosmani loop engineering sairahul`。
- **新增**：Rahul 強推中國 LLM（DeepSeek/Kimi/MiniMax）作為迴圈成本解方，這個成本優勢在 2026 下半年是否仍成立？西方前沿模型降價後，此論點會不會失效？
- Codex App 與 Claude Code 的六原語對照，在本文發布後是否仍成立？兩產品會持續趨同還是分化？建議追蹤兩者 changelog。
- MindStudio 的 `@mindstudio-ai/agent` SDK「120+ typed capabilities」在真實多代理迴圈中的可靠性與鎖定風險如何？是否有第三方評測？
- 「迴圈工程會不會只是 agent harness engineering 的行銷重新包裝？」Addy 自己把它定位為 harness 的上一層，但兩者邊界在實作上是否真的可分？

---

## 相關連結（Related）

- [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]] — Addy 明言「迴圈是 harness 的上一層樓」，本筆記是其直接延伸
- [[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]] — 用「分層盤點」法看哪些原語已上市，與本文六原語對照表同源
- [[2026-03-30-BORIS-CHERNY-HIDDEN-CLAUDE-CODE-FEATURES]] — 三來源共同引用的 Cherny「我的工作是寫迴圈」；`/loop`、`/goal` 等隱藏功能即迴圈原語
- [[2026-03-17-KARPATHYS-AGENTHUB-A-PRACTICAL-GUIDE-TO-BUILDING-YOUR-FIRST-AI-AGENT-SWARM]] — 對應 repo 的 Fleet Loop（orchestrator→specialists→subagents）
- [[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]] — 呼應三來源在 token 成本上的分歧，提供成本側對照
- [[CLAUDE-MEMORY-ENGINE]] — 對應第六原語 Memory；可延伸到 repo 的「Memory as Rules, not Logs」
- [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] — 「槓桿點移動」的更大時代脈絡

## References

- 【上游源頭】[Loops: What Every AI Engineer Needs to Know in 2026 — Sai Rahul (@sairahul1)](https://x.com/sairahul1/article/2064277888216555684)（X 長文，本波論述的中央散播節點）
- [Loop Engineering — Addy Osmani](https://addyosmani.com/blog/loop-engineering/)（2026-06-07）
- [What Is Loop Engineering? The New Meta for AI Coding Agents — MindStudio](https://www.mindstudio.ai/blog/what-is-loop-engineering-ai-coding-agents)
- [loop-engineering-skill — lunkerchen (GitHub, MIT)](https://github.com/lunkerchen/loop-engineering-skill)（repo 建立 2026-06-10，SKILL v1.1.0）
