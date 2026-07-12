---
title: "Field Guide to Fable：Anthropic 工程師 Thariq 的「找出你的未知」六招提示詞（中英對照）"
date: 2026-07-01
category: AI
tags:
  - ai/prompt-engineering
  - ai/agentic-coding
  - tools/claude-code
  - ai/unknowns
  - productivity/workflows
source: "https://www.youtube.com/watch?v=9fubhllmsBU"
source_type: video
author: "Thariq Shihipar (Anthropic)"
channel: "AI Engineer"
duration: "19:28"
transcript_method: youtube-transcript-api
status: notes
links:
  - "[[2026-06-17-WHAT-IS-LOOP-ENGINEERING-HOW-DIFFERENT-HARNESS-ENGINEERING]]"
  - "[[2026-06-07-LOOP-ENGINEERING-THREE-SOURCE-EXPERT-SYNTHESIS]]"
  - "[[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]]"
  - "[[2026-07-02-CONTEXT-CONVERTER-17-VOICE-PROMPTS-TURN-TALK-INTO-WORK-OUTPUT]]"
  - "[[2026-03-23-GRILL-ME-SKILL-DEEP-DIVE]]"
  - "[[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]]"
---

## 摘要（Summary）

Anthropic Claude Code 團隊工程師 Thariq Shihipar（X 帳號 @trq212）於 2026 年 7 月 1 日在 AI Engineer World's Fair 發表〈Field Guide to Fable〉演講（當天正值 Claude Fable 5 恢復全球上線），並於 7 月 3 日發布配套長文與 11 個 HTML 範例。核心論點一句話：**「模型品質的瓶頸，是我把地圖對準實地、找出未知的能力」（Fable's bottleneck [is] my ability to match the map and the territory — to find my unknowns）**。

你腦中的計畫、提示詞（Prompt）與規格是「地圖（map）」；真實的程式庫、現實限制才是「實地（territory）」。當模型在實地撞上地圖沒畫的東西，那就是一個「未知（unknown）」——一個你沒指定的決策點。Fable 5 這種等級的模型一次跑的範圍極大，會撞上非常多未知，所以「在便宜的階段找出未知」成了新瓶頸。他給出六個可直接複製的提示詞技巧（盲點巡查、先發散再收斂、反向訪談、給參考不給規格、記錄偏差、合併前小考），貫穿的經濟學邏輯是：**每一次腦力激盪、訪談和參考，都是在問題變貴之前，用便宜方式找出你原本不知道的事。**

本筆記依演講逐字稿與兩篇中文評論交叉驗證，整理出：①一個綜合六招的「最佳啟動提示詞範本」（中英對照）、②六個技巧的原文提示詞與繁中版本、③這些提示詞為什麼要這樣設計的來源背景。

## ⭐ 綜合版最佳提示詞範本（Master Kickoff Prompt，中英對照）

> [!important] 這是本筆記的核心產出
> 把 Thariq 的六招合併成**一個可直接複製的任務啟動提示詞**。設計邏輯：實作前四招（盲點巡查 → 訪談 → 發散選項 → 給參考）在同一個對話裡串成鏈，最後請模型把共識組裝成正式實作提示詞，並把實作中、實作後兩招（偏差記錄、合併前小考）作為常設規則寫進去。方括號 `[...]` 是你要替換的內容。

**English version:**

```
I'm about to [TASK — e.g. add a new auth provider to this codebase].
Context about me: [your familiarity level — e.g. I know our TypeScript stack well,
but I know nothing about the auth modules here].

Before writing any code:

1. Do a blindspot pass over [the relevant modules / this git diff / these docs]
   and report my unknown unknowns — the risks, edge cases and house conventions
   I haven't thought to ask about, ordered by severity, with a one-line reason each.

2. Then interview me one question at a time about anything still ambiguous.
   Prioritize questions where my answer would change the architecture.

3. Where a decision is a matter of taste, don't ask me in words — show me:
   make an HTML page with 3-4 wildly different options so I can react to them.

4. Here is a reference that represents what I want:
   [link / path / code snippet — it can be in another system or language].
   Read it, understand its semantics, and use it as the map for your work.

5. Finally, assemble everything we've settled on into one implementation prompt
   I can review before you start, and include these standing rules in it:
   - Keep an implementation-notes.md. If an edge case forces you off the plan,
     pick the conservative option, log it under "Deviations", and keep going.
   - When done, give me an HTML report on the change with context,
     and a quiz at the bottom I must pass before merging.
```

**繁體中文版：**

```
我準備要 [任務 — 例如：在這個程式庫加一個新的身份驗證提供者（auth provider）]。
關於我的背景：[你的熟悉程度 — 例如：我對我們的 TypeScript 技術棧很熟，
但對這裡的 auth 模組一無所知]。

在寫任何程式碼之前：

1. 請對 [相關模組 / 這段 git diff / 這些文件] 做一次盲點巡查（blindspot pass），
   回報我的 unknown unknowns — 那些我根本沒想到要問的風險、邊界情況與團隊慣例，
   依嚴重程度排序，每項附一句理由。

2. 接著針對仍然模糊的地方，一次一個問題地訪談我。
   優先問那些「我的答案會改變整體架構」的問題。

3. 遇到屬於品味的決定，不要用文字問我 — 直接做給我看：
   做一個 HTML 頁面，放上 3-4 個截然不同的選項，讓我能對它們做出反應。

4. 這是一份代表我想要什麼的參考範例：
   [連結 / 路徑 / 程式碼片段 — 可以來自別的系統或別的語言]。
   請閱讀並理解它的語義，把它當作你工作的地圖。

5. 最後，把我們確認過的所有共識組裝成一份實作提示詞讓我審閱，
   並把以下常設規則寫進去：
   - 維護一份 implementation-notes.md。如果某個邊界情況迫使你偏離計畫，
     選保守的做法，記錄在「Deviations」底下，然後繼續執行。
   - 完成後，給我一份關於這次變更的 HTML 報告（含背景脈絡），
     頁面底部附上一個我必須通過的小考，通過才能合併。
```

> [!tip] 使用要點
> - **背景自述那一行是關鍵**：Thariq 在演講中特別強調「給它一點關於你、你的工作、你所在階段的脈絡，效果極好」。模型知道你哪裡弱，盲點巡查與訪談才會打在對的地方。
> - 簡單任務不必六招全上——單獨抽用任何一招都成立（見下方逐招拆解）。
> - 這個範本每一句都能追溯到演講中的原話設計，不是憑空組合（見「來源背景」一節）。

## 來源背景：這些提示詞為什麼要這樣設計？

### 1. 地圖不等於實地（The map is not the territory）

演講的理論地基。你寫的提示詞與規格是**地圖**，真實程式庫與現實限制是**實地**。模型在實地撞上地圖上沒有的東西時，必須自己做決定——那個決策點就是「未知」。Fable 5 是第一批讓 Thariq 覺得「必須事先想清楚未知」的模型，因為它單次執行覆蓋的範圍太大，會一路撞上大量未指定的決策點。**所以六招全部都在做同一件事：在不同時機、用不同手段，把地圖和實地的落差補起來。**

### 2. Rumsfeld 四象限：不同的未知要用不同的招

Thariq 借用 Donald Rumsfeld 的知識分類，把提示詞裡的資訊落差拆成四象限，而六招各自攻擊不同象限——這正是「為什麼需要六招而不是一招」的答案：

| 象限 | 定義 | 對應技巧 |
|------|------|---------|
| Known Knowns（已知的已知） | 你寫進提示詞的明確需求 | （這是你已經會寫的部分） |
| Known Unknowns（已知的未知） | 你知道自己還沒決定的缺口 | **反向訪談**（招 3）逐題補洞 |
| Unknown Knowns（未知的已知） | 你其實懂、但沒寫下來的直覺標準——「看到就認得」的品味、審美、團隊常規 | **先發散再收斂**（招 2）與**給參考**（招 4）——用「反應」代替「描述」 |
| Unknown Unknowns（未知的未知） | 你連想都沒想過會影響結果的因素 | **盲點巡查**（招 1）主動掃描；**偏差記錄**（招 5）事後捕捉 |

> [!note] 關鍵術語：Unhobbling（解開束縛）
> Thariq 說模型是「養成（grown）」出來的、不是「設計（designed）」出來的，能力像鋸齒一樣高低不平，而且存在「潛藏能力落差（capability overhang）」——能力早就在那裡，只差環境把它接出來（例：一般聊天模型答不出名字以 "aw" 結尾的寶可夢，Claude Code 卻能自己跑程式列全表篩出 Croconaw 與 Drednaw）。**束縛模型的往往是我們**：harness 與提示詞反映的是「我們對模型了解多少」。六招提示詞本身就是 unhobbling 的實踐——其中好幾招（訪談、HTML 報告）在 Opus 4 時代「勉強叫得動」，到 Fable 5 才真正可靠，所以這套提示詞是**跟著模型能力演進校準過的**，不是通用時代產物。

### 3. 經濟學邏輯：越早找到未知越便宜

11 個示範被刻意排成三階段——實作前 8 個、實作中 1 個、實作後 2 個——因為「**寫任何程式碼之前，是找出未知最便宜的地方**」。原文收尾一句話總結：「每一次解說、腦力激盪、訪談和原型，都是找出你原本不知道的事的便宜方法（Every explainer, brainstorm, interview, and prototype is a cheap way to find out what you didn't know）。」

### 4. 留在迴圈裡（Staying in the loop）

實作後的兩招（小考、pitch 文件）不是在測模型，而是在**測你**——答不出小考，代表你已經脫離狀況、對合併的東西「半句話都說不上來」。Thariq 認為這是與這一代模型合作最重要的一環，也呼應他的結語:「東西變好做了，但做出價值還是難（building is easier, but generating value is still hard）」。

## 六招逐一拆解（原文提示詞 + 繁中版本）

> [!quote] 提示詞原文
> 以下英文提示詞為演講與流傳摘要中的原句（完整保留），繁體中文版為本筆記依台灣用語重新翻譯（網路流傳版多為簡體語感，此處已在地化）。

### 招 1：盲點巡查（Blind Spot Pass）〔攻擊 Unknown Unknowns〕

**時機**：進入不熟悉的領域之前。**設計原理**：模型對幾乎所有領域知道的都比你多，問題只在於把知識引出來；直接命名「blindspot pass」這個動作，並把目標定為「幫我把提示詞寫得更好」，讓產出直接回饋到下一輪提示詞品質。演講中他補充：可以指定掃描範圍（模組、git diff、Slack），也能用在學新領域——他剪 Fable launch video 時就用這招學調光（color grading）。

```
I'm adding a new auth provider but know nothing about the auth modules here.
Do a blindspot pass to find my unknown unknowns and help me prompt better.
```

```
我要加一個新的身份驗證提供者（auth provider），但對這裡的 auth 模組一無所知。
請做一次盲點巡查（blindspot pass），找出我的 unknown unknowns，
並幫我把提示詞寫得更好。
```

### 招 2：先發散再收斂（Brainstorm Before Building）〔攻擊 Unknown Knowns〕

**時機**：需求屬於「我看到才知道（I'll know it when I see it）」的類型，尤其是設計。**設計原理**：品味無法用文字描述，但可以用「反應」表達；坦承「我沒有視覺品味」是刻意的——告訴模型不要期待你給標準，改由它給出**刻意拉開差距**的選項（wildly different），讓你用挑選代替描述。

```
I want a dashboard for this data but have no visual taste.
Make an HTML page with 4 wildly different design directions so I can react to them.
```

```
我想幫這些資料做一個儀表板（dashboard），但我沒有視覺品味。
請做一個 HTML 頁面，放上 4 個截然不同的設計方向，讓我能對它們做出反應。
```

### 招 3：讓它反向訪談你（Let It Interview You）〔攻擊 Known Unknowns〕

**時機**：方向已定，但規格裡還有沒想清楚的地方。**設計原理**：「一次一個問題」勝過一次丟一牆問題——降低回答負擔、讓每題都能追問；「優先問會改變架構的問題」是排序函數，把訪談預算花在血本無歸的決策點上（bnext 報導中他在台上實測的版本是「針對這份規格問我 40 個問題」）。這個能力本身就是模型演進的證據：Opus 4 勉強能用 → Opus 4.5 能一口氣訪談 → Fable 5 能生成內嵌問題的 HTML 報告。

```
Interview me one question at a time about anything ambiguous.
Prioritize questions where my answer would change the architecture.
```

```
針對任何模糊不清的地方，一次一個問題地訪談我。
優先問那些「我的答案會改變整體架構」的問題。
```

### 招 4：給參考、不給規格（Give a Reference, Not a Spec）〔攻擊 Unknown Knowns〕

**時機**：文字寫不出你要什麼，但世界上已有做對的例子。**設計原理**：「給模型一張地圖的最好方式，是給它另一張地圖」——源碼是最精確的規格，**即使是另一種語言也成立**，因為要移植的是語義（semantics）而非語法；做 React 元件時丟一個 HTML mock-up 也是同一招。

```
This Rust crate implements the exact backoff I want.
Read it and reimplement the same semantics in our TypeScript client.
```

```
這個 Rust crate 實作了我想要的精確退避（backoff）機制。
請閱讀它，並在我們的 TypeScript client 裡重新實作相同的語義（semantics）。
```

### 招 5：執行中記錄偏差（Log Deviations Mid-Run）〔捕捉實地上的新未知〕

**時機**：長時間自主執行的任務。**設計原理**：再多規劃也擋不住實地的未知，所以改為**讓偏差可見**。三個組件各有作用——「選保守選項」給了預設決策規則（不用停下來等你）、「記錄在 Deviations 底下」讓事後可稽核、「繼續執行」保住自主性。事後這份記錄直接變成第二次嘗試的輸入（「下次開工更聰明」）。

```
Keep an implementation-notes.md. If an edge case forces you off the plan,
pick the conservative option, log it under Deviations, and keep going.
```

```
請維護一份 implementation-notes.md。如果某個邊界情況迫使你偏離計畫，
選保守的做法，記錄在「Deviations」底下，然後繼續執行。
```

### 招 6：合併前考自己（Quiz Yourself Before Merging）〔驗證你還在迴圈裡〕

**時機**：準備開 PR 或合併之前。**設計原理**：出貨代表**別人要繼承你的未知**；小考的受測者是你不是模型——答錯就代表你脫離了狀況。原文示範版本更嚴格：六題小考，答錯會把你導回你略讀跳過的那一段。

```
Give me an HTML report on this change with context
and a quiz at the bottom I must pass.
```

```
請給我一份關於這次變更的 HTML 報告，包含背景脈絡，
頁面底部附上一個我必須通過的小考。
```

## 原文的 11 個 HTML 示範對照表

Thariq 的配套頁面（thariqs.github.io）為六招提供了 11 個實際產出的 HTML artifact，每頁最上方就是可複製的提示詞：

| 階段 | # | 示範 | 對應招式 |
|------|---|------|---------|
| 實作前 | 01 | Blindspot pass（掃描 auth 模組產出七張盲點卡） | 招 1 |
| 實作前 | 02 | Teach me my unknowns（調光互動教學頁） | 招 1 變體 |
| 實作前 | 03 | Four design directions(同一佇列四種呈現) | 招 2 |
| 實作前 | 04 | Mock before you wire（可點擊的拋棄式 mock） | 招 2 變體 |
| 實作前 | 05 | Brainstorm the intervention（十個介入方案光譜） | 招 2 變體 |
| 實作前 | 06 | The interview（一次一題+決策表+可貼提示詞） | 招 3 |
| 實作前 | 07 | Point at a reference（Rust→TypeScript 語義對照） | 招 4 |
| 實作前 | 08 | The tweakable plan（按「可能被改動程度」排序的計畫） | 招 3/4 延伸 |
| 實作中 | 09 | Implementation notes（3 小時執行的偏差日誌） | 招 5 |
| 實作後 | 10 | The buy-in doc（預答審查者異議的 pitch 文件） | 招 6 變體 |
| 實作後 | 11 | Quiz me before I merge（14 檔 diff + 六題必過小考） | 招 6 |

## 我的心得（My Takeaways）

這套六招和我知識庫裡既有的幾條線索合流得很整齊：招 1（盲點巡查）本質上就是 [[2026-07-02-CONTEXT-CONVERTER-17-VOICE-PROMPTS-TURN-TALK-INTO-WORK-OUTPUT]] 裡「意圖補洞（Intent Gap Finder）」的程式庫版——一個掃需求文字、一個掃真實 territory；招 3（反向訪談）正是 [[2026-03-23-GRILL-ME-SKILL-DEEP-DIVE]] /grill-me 走紅的原因,而 Thariq 補上了關鍵的排序函數「優先問會改變架構的問題」。這種跨來源收斂讓我更相信這些不是流行話術，而是同一個底層問題（人講不清楚需求）的不同切面。

最值得內化的其實是四象限的**對招邏輯**:大多數人只會寫 Known Knowns（正面描述需求），偶爾補 Known Unknowns（提問）。但真正炸掉專案的是後兩象限,而後兩象限**無法靠「更努力寫需求」解決**——Unknown Knowns 要靠「反應代替描述」（選項、參考），Unknown Unknowns 要靠「委託模型主動掃描」（盲點巡查）。這是方法論層的差異,不是提示詞措辭的差異。

另外,abmedia 指出這套心法與 Loop Engineering 互補的觀察很準:Loop Engineering（見 [[2026-06-17-WHAT-IS-LOOP-ENGINEERING-HOW-DIFFERENT-HARNESS-ENGINEERING]]）管的是外圈工作流結構,Thariq 的 unknowns 管的是內圈單次提示詞品質——外圈自動化跑得再順,內圈提示詞裡藏著未知,只會把錯誤更快地規模化。

## 待補充（Open Questions）

- **盲點巡查的召回率有多少？** 模型掃出的 unknown unknowns 是否真的涵蓋事後實際爆掉的問題,還是只是「聽起來像風險」的清單？沒有任何量化驗證。可追蹤：`blindspot pass recall evaluation agentic coding unknown unknowns`
- **「選保守選項」的預設決策規則何時會反噬？** 招 5 假設保守選項總是可接受的暫時解,但某些領域(效能、安全)保守與正確可能相反。可追蹤：`conservative default deviation policy agent autonomy failure`
- **六招的成本加總是否會超過收益？** 對小任務,盲點巡查+訪談+四選項原型的 Token 與時間成本可能超過直接做錯再改。缺一個「任務多大才值得啟動全套」的判準。可追蹤：`pre-implementation prompt overhead break-even task size`
- **四象限中的 Unknown Knowns 是否真能被「四個選項」覆蓋？** 品味空間是連續的,四個離散選項可能全部落在你要的區域之外;何時該增加選項數或改用迭代式收斂,原文未談。可追蹤：`design direction sampling diversity preference elicitation`
- **演講提到 Claude Code 系統提示砍掉約八成、原則改為「少下禁令、多給脈絡」,這對用戶自訂的 CLAUDE.md 寫法有什麼具體含義？** 可追蹤：`Claude Code system prompt reduction 80 percent context over constraints CLAUDE.md`

## 相關連結（Related）

- [[2026-06-17-WHAT-IS-LOOP-ENGINEERING-HOW-DIFFERENT-HARNESS-ENGINEERING]] — abmedia 明確指出兩者互補：Loop Engineering 建構外圈工作流，unknowns 心法優化內圈提示詞品質。
- [[2026-06-07-LOOP-ENGINEERING-THREE-SOURCE-EXPERT-SYNTHESIS]] — Loop Engineering 多來源綜合，本文是同一波 Fable 5 心法演化的第三個關鍵節點。
- [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]] — Thariq 的 unhobbling 論點（束縛模型的是 harness 與提示詞）正是 Harness Engineering 的核心命題。
- [[2026-07-02-CONTEXT-CONVERTER-17-VOICE-PROMPTS-TURN-TALK-INTO-WORK-OUTPUT]] — 其中「意圖補洞（Intent Gap Finder）」與招 1 盲點巡查是同一思路的需求文字版。
- [[2026-03-23-GRILL-ME-SKILL-DEEP-DIVE]] — /grill-me 就是招 3「反向訪談」的 skill 化實作，可對照 Thariq 補充的架構優先排序。
- [[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]] — 五層 Harness 堆疊中的驗證層，與招 5、招 6 的偏差記錄／小考機制互相印證。
- [[2026-05-01-GOOGLE-WHITEPAPER-NEW-SDLC-VIBE-CODING-TO-AGENTIC-ENGINEERING]] — Google 白皮書指出「規格品質是新瓶頸」——Thariq 的找未知六招正是攻這個瓶頸的提示詞工法。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | 必記概念：the map is not the territory、unknowns、Rumsfeld 四象限（known knowns / known unknowns / unknown knowns / unknown unknowns）、unhobbling、capability overhang、blindspot pass、staying in the loop、「building is easier, but generating value is still hard」 |
| **理解（半被動）** | 解釋概念的含義及關聯 | 六招是四象限的對招表：訪談補「已知的未知」，選項與參考逼出「未知的已知」，盲點巡查與偏差記錄捕捉「未知的未知」，小考驗證人還在迴圈裡；三階段排列（前 8／中 1／後 2）反映「越早找到未知越便宜」的成本曲線 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設 | 隱含假設：①模型做盲點巡查時自己沒有盲點（用模型找模型的未知有自我參照風險）；②使用者會誠實做完小考而不是跳過；③「保守選項」永遠存在且可辨識。原文對三者皆未提供失效案例 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. 把本筆記的綜合範本存成 Claude Code 的自訂 skill 或片語，接手陌生模組時強制先跑招 1+3；2. 在長任務的提示詞尾端固定附加招 5 的 implementation-notes 條款；3. 團隊 PR 流程加入招 6：PR 描述附模型生成的小考，reviewer 可要求作者先貼出答題結果 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | 對比「寫更完整的 spec」路線：spec 完整化只能覆蓋前兩象限，且邊際成本遞增；Thariq 路線用互動（訪談、選項、參考）攤平後兩象限，但增加前期 Token 與人工介入時間。小任務直接做更划算；跨模組、不熟領域、高返工成本的任務才值得六招全上 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「未知（unknown）」的操作型定義是「模型在實地撞上地圖沒有的決策點」——但怎麼區分「值得升級為訪談問題的未知」和「模型自行決定即可的琐碎未知」？分界線在哪？
- **假設**：盲點巡查假設模型對該領域的知識覆蓋比你廣。若是全新內部系統（模型訓練資料裡不存在），這招會退化成什麼？還剩多少價值？
- **證據**：「Fable 5 對招 4（跨語言語義移植）表現驚人」是講者自述，缺乏對照實驗——同樣的參考移植任務在其他模型上的失敗率是多少？
- **觀點**：站在反對者立場：這六招會不會只是把「寫規格的功夫」換成「回答訪談的功夫」，總工作量沒變、只是換了介面？什麼情境下這個批評成立？
- **後果**：若團隊全面採用「合併前小考」，12 個月後可能出現什麼副作用——小考疲乏、應付式作答、或 reviewer 把責任外包給小考分數？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 對「模型生成的盲點清單」產生虛假安全感：跑過盲點巡查 ≠ 沒有盲點，模型列出的往往是通用風險而非你的專案特有地雷。最壞情況是省略了人工 review,把「已巡查」當「已安全」。
2. **什麼情況下會失敗？** — ①任務太小，六招的前置成本超過返工成本；②領域是模型訓練資料外的封閉知識（內部系統、未公開協定），盲點巡查與參考移植雙雙失效；③使用者不配合互動環節（跳過訪談、不做小考），整套流程退化為形式主義。
3. **有沒有更好的替代方案？** — 若團隊已有成熟的 RFC／design doc 文化，先寫設計文件再餵給模型可能比即時訪談更可稽核；若任務高度重複，把六招固化成 skill（如 /grill-me 之於招 3）比每次手打提示詞更穩定。兩者皆可與本方案混用：文件打底、六招補洞。

## References

- [Thariq Shihipar〈Know your unknowns〉examples 頁（11 個 HTML 示範與提示詞）](https://thariqs.github.io/html-effectiveness/unknowns/)
- [演講影片：Field Guide to Fable — Thariq Shihipar, Anthropic（AI Engineer World's Fair，2026-07-01，19:28）](https://www.youtube.com/watch?v=9fubhllmsBU)
- [鏈新聞：Anthropic 工程師 Fable 5 實戰心法：Finding Unknowns](https://abmedia.io/thariq-shihipar-anthropic-fable-5-field-guide-finding-unknowns-agentic-coding)
- [數位時代：Anthropic 工程師揭 Claude 潛能解鎖術](https://www.bnext.com.tw/article/91455/anthropic-engineer-claude-harness)
