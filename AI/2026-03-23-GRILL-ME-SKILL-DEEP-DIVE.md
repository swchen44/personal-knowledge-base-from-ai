---
title: "/grill-me：三句話、86K stars，Matt Pocock 最爆紅的 Claude Code Skill"
date: 2026-03-23
category: AI
tags:
  - ai/skills
  - ai/claude-code
  - productivity/design-thinking
  - technique/rubber-ducking
source: "https://www.aihero.dev/my-grill-me-skill-has-gone-viral"
source_type: article
author: "Matt Pocock"
status: notes
links:
  - "[[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]]"
  - "[[2026-05-09-STOP-RANDOM-SKILL-4-CORE-GROUPS-FOR-AGENT-PRODUCTIVITY]]"
  - "[[2026-04-08-7-RULES-FOR-CREATING-EFFECTIVE-CLAUDE-CODE-SKILL]]"
  - "[[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]]"
---

## 摘要（Summary）

`/grill-me` 是 Matt Pocock 寫過最短、影響力最大的 Claude Code skill——**整支 skill 不到 100 字**，但讓他的 [mattpocock/skills](https://github.com/mattpocock/skills) repo 在三個月內衝到 86K stars。本筆記深入剖析這三句話的設計：為什麼短卻有效、它如何取代傳統的 rubber ducking、以及它在 Matt 整套工作流中的位置。

> [!important] 為什麼這個 skill 值得單獨成篇
> Matt 自己說「這是我寫過最有用的 skill，連非編程場景也用」。它揭示一個反直覺的真理：**skill 不在長，而在挑對時機、用對詞**。學會這個寫法可以幫助自己寫更精準的 skill。

---

## SKILL.md 原文（完整保留）

來源：[github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md)

```markdown
---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.
```

**檔案大小**：428 bytes（含 frontmatter）。本體指令只有 4 句。

---

## 三句指令的設計拆解

> [!note] 每一句都拆得開、缺一不可

### 第 1 句：「Interview me relentlessly until we reach a shared understanding」

**關鍵詞**：`relentlessly`（不留情地）+ `shared understanding`（共同理解）

**設計動機**：
- 一般 AI agent 太禮貌，問兩三題就停止追問。`relentlessly` 強制它**問到對齊為止**
- `shared understanding` 是 Frederick Brooks《The Design of Design》的核心概念——設計失敗多半源自雙方對問題的理解不同
- 對應的反例：Plan Mode 預設行為（AI 太早出 plan，雙方還沒對齊就生 document）

> [!quote] Matt 在影片中的觀察（[完整 walkthrough](https://www.youtube.com/watch?v=-QFHIoCo-Ko) 第 12–30 分）
> 「Claude Code 在 Plan Mode 下，往往在我們真正彼此理解前就吐出一份 plan。grill-me skill 強迫進行那場該有的對話。」

### 第 2 句：「Walk down each branch of the design tree, resolving dependencies between decisions one-by-one」

**關鍵詞**：`design tree`（設計樹）+ `dependencies`（決策間依賴）

**概念來源**：Brooks 提出設計是一棵樹——你需要一路走遍每個分支才算完整。例如設計搜尋頁：

```
搜尋介面
├── 進階搜尋 UI ─┬── 過濾條件有哪些？
│               ├── 排序方式？
│               └── 結果如何顯示？
└── 簡單文字框 ─── 模糊搜尋演算法？
```

如果只決定「用進階搜尋」就跳走，後面三個問題會在實作時才浮現，**而那時改設計成本最高**。

### 第 3 句：「For each question, provide your recommended answer」

**這是 Matt 後來才加的關鍵句**。

**問題**：原本只問問題、不給答案的版本，逼用戶每題都動腦回答，對話節奏太慢。

**解法**：AI 問問題時**同時推薦答案**。如果是顯而易見的好答案，用戶只要回「yes」就過關。

> [!tip] 對話加速效應
> Matt 估算這句話讓 grilling session 從「打字累死」變成「按 yes/no 為主」，**整體對話時間至少縮短 40%**，且不犧牲對齊品質。

### 第 4 句：「If a question can be answered by exploring the codebase, explore the codebase instead」

**設計意圖**：避免問用戶「現在這個函數叫什麼」「table schema 長怎樣」這類**可自答**的問題。AI 應該主動讀 code 而不是浪費用戶頻寬。

**進階機制**（影片中 demo）：grill-me 會建立 **sub-agent** 做 codebase 探索，在 Opus 上可以燒掉 93.7K token——但**主 agent 的 context 不會爆炸**，因為子任務在獨立 context 跑完只回報摘要。這是控制 100K token 臨界點的關鍵技巧。

---

## 為什麼短卻有效？

### 與傳統 Rubber Ducking 的差異

> [!info] Rubber Ducking（橡皮鴨除錯法）
> 1990 年代 *The Pragmatic Programmer* 提出：對著橡皮鴨「逐行解釋自己的程式碼」，常常講到一半就自己發現 bug。
> 核心機制：**強迫把模糊想法明確語言化**。

| 維度 | Rubber Duck | `/grill-me` |
|------|-----------|------------|
| 推力來源 | 你自己對著鴨子講 | AI 主動追問 |
| 對話節奏 | 你決定講多少 | AI 不放過任何分支 |
| 提供答案 | 鴨子不會說話 | AI 給推薦答案，你只要 yes/no |
| 領域覆蓋 | 只到你想得到的 | AI 走完整個 design tree |
| 適用場景 | 已有 code、debug 用 | 從 vague brief 開始、設計階段 |

**核心升級**：rubber duck 是被動鏡像，grill-me 是**主動的設計樹遍歷器**。

### Plan Mode 太早出 Plan 的問題

Claude Code 預設 Plan Mode 流程：用戶說需求 → AI 探索 codebase → AI 生 plan → 用戶批准。問題：

- AI 對需求的理解可能跟用戶差很遠，但 plan 出來後用戶傾向「直接批准」（沉沒成本）
- 沒有強制的「對齊」階段
- Plan 通常包含過多實作細節（檔案路徑、code snippet），這些細節在實作時容易過時

**`/grill-me` 補位**：在生 plan 之前，**強迫一場深度對話**。產出的不是 plan，而是 **grilling session 紀錄**——一份對話文本，包含所有決策的「為什麼」。後續再用 `/to-prd` 把對話合成 PRD。

---

## 實戰數據

> 來自 Matt 在 [5 Agent Skills I Use Every Day](https://www.aihero.dev/5-agent-skills-i-use-every-day) 與 96 分鐘 [Full Walkthrough](https://www.youtube.com/watch?v=-QFHIoCo-Ko)：

- **單次 session 問題數**：16–50 題（取決於功能複雜度）
- **平均 session 時長**：約 45 分鐘
- **Token 消耗**（含 sub-agent 探索）：主 agent ~20–30K，sub-agent 額外 93.7K（Opus 案例）
- **Repo stars**：grill-me 發佈後 3 個月，整個 mattpocock/skills 從 0 衝到 86K stars，**單 skill 帶動整 repo**

---

## 應用場景

### 編碼場景（Coding）

> Matt 自己的主場景，串接其他 skill：

```
vague brief / client.md
        │
        ▼
   /grill-me  ────► grilling-session.md
        │
        ▼
   /to-prd  ──────► PRD.md
        │
        ▼
   /to-issues ───► issues/*.md (vertical slices + DAG)
        │
        ▼
   /tdd + AFK loop ─► commits
```

→ 完整工作流請見 [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]]

### 非編碼場景（Non-Coding）

Matt 用 grill-me 規劃下一門課程內容、與 AI 進行深度討論。他建議改寫成**非編碼版**：

```
Interview me relentlessly about every aspect of this until
we reach a shared understanding. Walk down each branch of the design
tree resolving dependencies between decisions one by one.

For each question, provide your recommended answer.
```

（差異：拿掉「explore the codebase」那一句。）

> [!tip] 個人應用構想
> - 規劃下一篇文章的論點結構
> - 釐清職涯決策（換工作、轉領域）
> - 規劃旅行行程的優先順序
> - 跟 AI 一起設計新的個人系統（GTD、KB schema）

---

## 在整體工作流中的位置

`/grill-me` 是 Matt 五個核心 skill 中的 **Step 1**：

| 順序 | Skill | 角色 |
|------|------|------|
| **1** | **`/grill-me`** | 對齊（vague → shared understanding） |
| 2 | `/to-prd` | 規劃（對話 → PRD） |
| 3 | `/to-issues` | 拆解（PRD → vertical slices） |
| 4 | `/tdd` | 實作（red-green-refactor） |
| 5 | `/improve-codebase-architecture` | 維護（找 deepening opportunity） |

它是**整套流程能跑起來的前提**——沒有對齊，後面 PRD / issues / 實作都是在錯方向上加速。

→ 完整 pipeline 詳見 [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]]

---

## 影片中的 Demo（12:00–30:00）

> 影片時間軸對應段：[Full Walkthrough](https://www.youtube.com/watch?v=-QFHIoCo-Ko) 12:00–30:00。

**Demo 內容**：PM Sarah Chen 寄來 `client-brief.md`，內容大致是「Cadence（CMS + 影片編輯器）學生留存率低，想加入 gamification」。Matt 在現場執行：

```
/grill-me @client-brief.md
```

Claude 開始一題一題問：
1. 「點數經濟（point economy）：哪些行為賺點？建議從『完成單元』+ `每日連續登入』開始」
2. 「點數有沒有衰減？建議：30 天不活躍開始衰減」
3. 「儀表板呈現：建議用進度環 + 連續登入火焰圖示，避免 leaderboard 引起社交焦慮」
4. ...一直到第 16 題

> [!warning] Matt 在影片中提到的注意事項
> - **Grilling 可能無止盡**：複雜功能可達 50 題，可在 skill 加「20 題後自動停下檢查」的停止點
> - **不要優化 grilling 本身**：目標是達成對齊，不是寫出完美對話紀錄
> - **Session 結束後立刻 `clear context` 跑 `/to-prd`**：避免 grilling 過程的探索性內容污染 PRD 合成

---

## 我的心得（My Takeaways）

1. **「短 skill 的設計」是可學習的技藝**——選對 4 個關鍵詞（relentlessly / shared understanding / design tree / recommended answer）就足夠承載一個完整方法論。我自己寫 skill 常常掉進「寫越多越完整」的陷阱。
2. **「provide your recommended answer」這個小改動非常聰明**——它把對話從「考試」變成「快速確認」，用戶體驗大幅改善。值得套用到自己其他需要使用者回答的 skill（例如 KB 攝入時的分類確認）。
3. **Sub-agent 委派是控制 context 的關鍵技巧**——讓主 agent 保持 lean，把探索性消耗轉到子 agent。這對我的 KB 攝入流程啟發很大：與其讓主 agent 又抓網頁又寫 markdown，不如 explore agent 抓網頁回傳大綱，主 agent 才寫。
4. **「強制對齊再生 plan」這個次序值得移植到 KB 寫作**：先 grill 自己「這篇 KB 要回答什麼問題」，再決定結構。本筆記其實就是這樣寫的——先 plan mode 對齊，再動筆。
5. **非編碼場景值得試**——下次規劃個人專案前先跑一次 grill-me 非編碼版。

---

## 待補充（Open Questions）

1. **`relentlessly` 的具體執行邊界是什麼**？Claude / Sonnet / Opus 在這個詞的詮釋上是否一致？是否曾觀察到模型「賴皮」只問 3 題就收？建議搜尋：`prompt engineering relentlessly stop condition`
2. **`design tree` 概念是否被某些模型誤解為實作層樹結構**（如資料結構）而非設計決策樹？是否需要更明確的詞？
3. **「provide recommended answer」會不會偏向 anchoring bias**——用戶為了省事都選推薦答案，導致設計被 AI 主導？Matt 沒提到這個風險。建議搜尋：`LLM recommendation anchoring effect design decision`
4. **與 [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] 的「specification first」哲學**怎麼搭？Karpathy 主張 spec → code，Matt 主張對話 → PRD → code，差異在哪？
5. **Grilling session 紀錄該不該存進 repo**？Matt 在影片中說 PRD 完成後應該刪除（避免 doc rot），那 grilling session 也該刪嗎？
6. **能不能反向使用：讓 AI 把人類 grill 自己的決策**（自我審視）變成 reflection 工具？

---

## 相關連結（Related）

- [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]] — 本篇的姊妹文，完整工作流走查與 5 skills 串接
- [[2026-05-09-STOP-RANDOM-SKILL-4-CORE-GROUPS-FOR-AGENT-PRODUCTIVITY]] — 另一個視角的 skill 分類方法
- [[2026-04-08-7-RULES-FOR-CREATING-EFFECTIVE-CLAUDE-CODE-SKILL]] — skill 設計原則，可印證「短而精」風格
- [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]] — Claude Code skills 官方規範
- [[2026-03-17-LESSONS-FROM-BUILDING-CLAUDE-CODE-HOW-WE-USE-SKILLS]] — Anthropic 對 skill 的設計觀點
- [[2026-03-18-5-AGENT-SKILL-DESIGN-PATTERNS-EVERY-ADK-DEVELOPER-SHOULD-KNOW]] — 通用 skill 設計模式

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | grill-me 由 4 句指令組成、檔案 428 bytes、單次 session 16–50 題約 45 分鐘、概念來自 Frederick Brooks《The Design of Design》、`provide recommended answer` 是後加的關鍵句 |
| **理解（半被動）** | 解釋概念的含義及關聯 | 4 句指令對應 4 個機制：強迫性 + 結構性（樹遍歷）+ 加速性（推薦答案）+ 委派性（codebase 自查）。它與 rubber duck 的差異是「被動鏡像 vs 主動遍歷」 |
| **分析（主動）** | 檢驗論點、拆解假設 | 假設 1：「AI 給推薦答案不會造成 anchoring」未經驗證；假設 2：「Design tree 對 AI 是清晰概念」可能因模型而異；假設 3：「relentlessly 能讓 AI 真的問到底」需要看不同模型的執行差異 |
| **應用（主動）** | 將知識套用情境 | 1) 把「短 skill 設計法」套用到自己寫的 KB ingestion skill：少即是多；2) 把「provide recommended answer」套用到所有問用戶問題的場景（包括 AskUserQuestion）；3) 跑非編碼版 grill 規劃個人 side project |
| **評估（主動）** | 比較替代方案 | vs Plan Mode：grill-me 更慢但對齊更深，需求清楚的小修改不該用；vs Superpowers brainstorming：grill-me 更短更通用，brainstorming 更結構化但偏 brain-storming 而非 decision-tree；vs 自己 rubber duck：grill-me 主動性遠超，但失去「自己想透徹」的鍛鍊 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「relentlessly」對不同模型（Opus / Sonnet / Haiku / GPT-5）的執行強度是否一致？這個詞在 system prompt 中的 weight 是否可調？
- **假設**：「設計樹是真實存在的結構」這個前提對所有設計問題都成立嗎？很多設計決策更像權衡網絡而非樹（決策 A 同時影響 B 和 C，B 也影響 C）。
- **證據**：「86K stars」是這個 skill 成功的證據嗎？還是 Matt 個人品牌與其他 skills 的集合效應？單獨拆出來看 grill-me 的引用量？
- **觀點**：反對者會說「45 分鐘的 grilling 比直接動手寫 spec 還慢，產出又只是對話紀錄，效率低」——這個批評在什麼情境下成立？
- **後果**：若每個 feature 都用 grill-me，12 個月後團隊可能：(a) 養成深度對齊的好習慣；(b) 也可能養成「沒 grill 就不敢動」的依賴，喪失快速決策能力。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — **Anchoring bias 與時間黑洞**：AI 給推薦答案會讓人懶得想替代方案，最後決策都靠 AI 帶；同時 grilling 容易越拉越長，45 分鐘變 2 小時，把實作時間吃光。最壞情況：你完美對齊了一個錯方向的需求。
2. **什麼情況下會失敗？**
   - **需求清楚的小修改**（改個 bug、加個欄位）→ overkill 到誇張
   - **AI 對該 domain 無知識** → 推薦答案會誤導
   - **沒有強自律** → grilling 變成拖延實作的合理化藉口
   - **用戶不熟悉「對齊比實作重要」這個價值觀** → 中途會放棄，覺得「我問你要 plan 你卻一直問我問題」
3. **有沒有更好的替代方案？**
   - **小修改**：直接 Plan Mode 或 single-prompt，不需要 grill
   - **完全模糊的需求**：先用 [[Superpowers brainstorming]] skill（更發散式），對齊到一個雛形後再進 grill-me
   - **個人 KB / 寫作**：用 grill-me 非編碼版直接取代傳統 outline 流程
   - **團隊場景**：grill-me 用於需求對齊，配合 Linear / Notion 而非 GitHub issues

---

## References

- [My 'Grill Me' Skill Went Viral（原文）](https://www.aihero.dev/my-grill-me-skill-has-gone-viral)
- [grill-me SKILL.md 原始檔](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md)
- [mattpocock/skills GitHub Repo](https://github.com/mattpocock/skills)
- [5 Agent Skills I Use Every Day](https://www.aihero.dev/5-agent-skills-i-use-every-day) — 完整 5 skills 系列文
- [Full Walkthrough: Workflow for AI Coding（YouTube, 96 min）](https://www.youtube.com/watch?v=-QFHIoCo-Ko) — 12:00–30:00 段是 grill-me demo
- Frederick P. Brooks Jr., *The Design of Design: Essays from a Computer Scientist* (2010)
- Hunt & Thomas, *The Pragmatic Programmer* — Rubber Duck Debugging 起源
