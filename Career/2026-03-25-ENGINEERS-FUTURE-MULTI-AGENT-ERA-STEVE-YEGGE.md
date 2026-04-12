---
title: "給現在工程師的未來：軟體工程邁向多代理人（Multi-Agent）時代"
date: 2026-03-25
category: Career
tags:
  - #career/engineering
  - #ai/agents
  - #ai/llm
source: "https://www.youtube.com/watch?v=qvjVQJHrQ-M"
source_type: video
author: "Best Partners TV"
status: notes
channel: "Best Partners TV"
duration: "12:10"
transcript_method: youtube-transcript-api
links:
  - "[[BITTER-LESSON-RICH-SUTTON]]"
  - "[[MULTI-AGENT-SYSTEMS]]"
  - "[[VIBE-CODING]]"
  - "[[ENGINEER-CAREER-IN-AI-ERA]]"
---

## 摘要（Summary）

本文改編自 YouTube 頻道「最佳拍檔（Best Partners TV）」對 Steve Yegge（史蒂夫·耶格）的深度訪談，並依使用者要求撰寫為一篇完整的工程師職涯思考文章。

Yegge 是矽谷四十年的技術老將，曾任職 Google 和 Amazon，以直言不諱的技術評論著稱。他親眼目睹了軟體工程一次又一次的典範轉移（paradigm shift），而這一次——人工智慧（Artificial Intelligence，AI）帶來的衝擊——他認為是史無前例的。本文試圖以他的視角出發，為現在的工程師勾勒出一幅關於未來的清醒地圖。

---

## 一、「球門一直在移動」——這不是第一次了

> [!quote] Steve Yegge 的觀察
> 軟體工程的「球門（goal post）」從來都不是固定的，它一直在往後移動。

Yegge 回憶 1992 年的電腦繪圖（computer graphics）領域：那時候，想在螢幕上畫一條線，你需要：
- 深入理解顯示記憶體（VRAM）機制
- 手寫演算法計算每個像素（pixel）的偏移量
- 處理晦澀的組合語言（assembly language）和位元運算（bit manipulation）

這些技能被視為行業菁英的護城河。

但僅僅兩三年後，隨著高階封裝介面（API）出現，渲染（render）一個多邊形（polygon）變成了一行函式呼叫。那些引以為傲的位元運算技巧，在一夜之間變得毫無用處。

> [!important] 核心規律
> **技術發展的本質，就是不斷地將複雜的事情封裝成簡單的工具，讓人類能夠站在更高的抽象層級（abstraction layer）上，去解決更宏大的問題。**

這個規律，今天再次發生——這一次，輪到「寫程式碼」這件事本身了。

---

## 二、苦澀的教訓（The Bitter Lesson）

著名 AI 學者 Rich Sutton 在他那篇震聾發聵的文章《苦澀的教訓（The Bitter Lesson）》中提出：

> [!quote] Rich Sutton，《The Bitter Lesson》
> 在 AI 幾十年的發展史中，人類總是試圖將自己引以為傲的「領域專業知識（domain knowledge）」硬編碼進系統中——但最終，這些精心設計的規則，都會被「大規模算力（compute）＋通用學習演算法（general learning algorithm）」無情碾壓。

從「深藍（Deep Blue）」擊敗西洋棋世界冠軍卡斯帕羅夫，到「AlphaGo」戰勝圍棋棋王李世乭——歷史一遍又一遍地重複這個苦澀的教訓：

**人類的巧思，在絕對的算力面前不值一提。**

今天，這個教訓終於降臨到了「編寫程式碼（coding）」這件事情本身上。

Yegge 坦承，2022 年底第一代 ChatGPT 崛起時，他讓 AI 寫一段 Emacs Lisp 程式碼，結果一塌糊塗，他當時認為這不過是資本炒作的泡沫。但打臉來得比任何人預期都快——Claude Opus 4.5 已經能在極短時間內生成幾千行完全可運行、邏輯嚴密的程式碼。

---

## 三、工程師如何一步步接納 AI？

Yegge 將工程師對 AI 的接納程度描述為一個連續的光譜（spectrum）：

```
階段 0：完全拒絕
   └─ 認為 AI 生成的程式碼不安全、不可控

階段 1：自動補全（Autocomplete）
   └─ 把 AI 當更聰明的 Tab 鍵（如早期 GitHub Copilot）

階段 2：模組生成（Module Generation）
   └─ 讓 AI 一次生成整個功能模組，測試通過直接合併

階段 3：代理人主導（Agent-Driven）
   └─ 讓 AI Agent 執行偵錯（debug）、執行測試、甚至修復錯誤
   └─ 問題出現：極度無聊感（等待 Agent 思考的空白時間）

階段 4：多代理人編排（Multi-Agent Orchestration）
   └─ 同時啟動數十、數百個 Agent 並行處理不同任務
   └─ 人類轉變為：架構師 / 調度員
```

這不是未來的想像——這是現在正在發生的事。

---

## 四、吸血鬼效應（Vampire Effect）——被 AI 抽乾的不是你的工作，是你的精力

> [!warning] 吸血鬼效應（Vampire Effect）
> 這是最令人意外、也最少被討論到的現象。

在傳統的編程模式中，人類打字速度很慢——但正是這種「慢」，給了大腦充足的思考時間。你在敲鍵盤的同時，大腦在後台默默建構系統的邏輯模型。

然而，當 AI 在一秒鐘內把上千行複雜程式碼「拍」在你面前時：

- 你的工作從「主動的創造（active creation）」，變成了「被動的極速審核（passive high-speed review）」
- 大腦必須像全速運轉的掃描器，在幾秒內驗證數百行程式碼的邏輯正確性
- 這種持續的認知超載（cognitive overload），是一種極其恐怖的精神消耗

Yegge 坦言，在這種模式下工作，他經常在大白天感到精疲力盡，不得不午睡。他身邊許多初創公司高手也遇到相同的狀況。

> [!tip] 實際建議
> 在 AI 協作工作流程中，**主動設計「思考的空隙」**。不要讓自己成為永遠處於審核狀態的機器。每天高強度的 AI 協作工作，三小時可能就是極限——不要強求八小時。質量比數量重要。

---

## 五、多代理人（Multi-Agent）時代：你的新身份

Yegge 目前全力投入的專案「Gas Town」的核心理念是：

> 既然一個 Agent 在工作時人類需要等待，為什麼不同時啟動十個、一百個 Agent 去並行（parallel）處理不同任務？

在這個工作模式下，工程師的角色發生了根本性的逆轉：

```
舊角色：程式碼工匠（Code Craftsman）
   ├─ 逐行敲擊鍵盤
   ├─ 精通十幾種設計模式（design patterns）
   └─ 能手寫各種演算法

新角色：架構師 / 調度員（Architect / Orchestrator）
   ├─ 定義高層架構意圖（architectural intent）
   ├─ 清楚描述業務目標（business objectives）
   ├─ 將任務分發給 Agent 集群
   └─ 審核、調整、整合成果
```

> [!note] 維氏編程（Vibe Coding）
> 這種透過自然語言與 AI 高頻交流、傳達業務邏輯和架構直覺、引導 AI 生成底層實作的方式，被稱為「Vibe Coding」。這不是未來的概念，而是現在最頂尖的工程師已經在做的事。

---

## 六、大公司的創新引擎正在熄火

Yegge 毫不留情地指出，像 Google 和 Amazon 這樣的科技巨頭，內部的創新引擎已經徹底熄火。

原因不只是技術問題，更是根深蒂固的官僚主義（bureaucracy）：

- 任何新想法從提出到立項到落地，需要無數審批流程和跨部門扯皮
- Google 創辦人 Larry Page 曾說「把更多的木柴放在更少的箭後面（Put more wood behind fewer arrows）」——集中資源辦大事
- 但在 AI 時代，這種策略正成為大公司致命的弱點

**現實的對比：**

| | 過去 | AI 時代 |
|---|---|---|
| 建構世界級基礎設施 | 500 名頂尖工程師，耗時 2 年 | 2-20 人精英團隊，幾週完成 |
| 試錯成本 | 極高 | 極低 |
| 迭代速度 | 緩慢 | 極快 |

> [!warning] 冷酷的預測
> Yegge 預測：未來軟體行業將屬於高度敏捷的微型團隊（micro-teams）。那些傳統的、臃腫的軟體工程組織架構，將不可避免地走向崩潰。我們將看到越來越多的大公司進行殘酷的裁員——因為維持龐大研發團隊已不再是競爭力的體現，反而是一種拖累。

---

## 七、傳統 IDE 正在走向死亡

> [!info] IDE 的終結？
> 傳統的整合開發環境（Integrated Development Environment，IDE）本質上是為「人類手工編寫程式碼」這個行為而設計的。

如果我們已經不再需要親自寫程式碼，為什麼還需要一個如此笨重、充滿針對人類手指操作的輔助功能的工具？

Yegge 大膽預測：未來的開發介面將是完全基於對話（conversation-driven）和意圖驅動（intent-driven）的。

我們已經看到這個趨勢：
- **Cursor**：將對話框放在最核心位置
- **Claude Code（Claude Dev）**：以意圖驅動取代手動編輯

程式碼編輯區域正在「退居二線」。

---

## 八、給現在工程師的行動指南

面對這個不可逆轉的洪流，Yegge 的態度是堅定的：

> [!important] 核心訊息
> **抵制是毫無意義的。** 試圖在舊有的技能樹（skill tree）上尋找安全感，就像工業革命時期試圖砸毀紡織機的工人一樣徒勞。

**AI 並不是來取代你做某個具體動作的，它是來「增強（augment）」你的。**

它剝奪了你手寫底層程式碼的「特權」，但同時賦予了你掌控整個軟體系統的上帝視角。

### 你現在應該培養的能力

> [!tip] 給工程師的行動清單

1. **產品直覺（Product Intuition）**
   能夠清楚判斷「什麼值得做」，比「怎麼做」更重要。當 AI 能在幾分鐘內實作任何東西，「做什麼」的判斷力才是護城河。

2. **業務邏輯理解（Business Logic Understanding）**
   能將模糊的業務需求，翻譯成清晰的系統規格和架構決策。這是 AI 最難替代的部分。

3. **AI 協作能力（AI Collaboration Skills）**
   學會如何有效地「提示（prompt）」和「引導（steer）」AI Agent，包括多代理人的編排（orchestration）和任務分解（task decomposition）。

4. **系統思維（Systems Thinking）**
   能夠在高抽象層級思考整體架構，而不只是局部的程式碼實作細節。

5. **快速迭代（Rapid Iteration）**
   在 AI 大幅降低試錯成本的今天，最重要的能力是快速驗證假設（hypothesis）、快速失敗、快速調整。

### 你現在不用再焦慮的事情

- **是否精通某個特定框架（framework）**：框架的壽命越來越短，AI 什麼都會
- **是否能手寫排序演算法**：這和今天能手寫圖形渲染器的組合語言一樣，是在浪費時間
- **是否「真的理解」每一行 AI 生成的程式碼**：在合理的測試覆蓋（test coverage）下，你不需要

---

## 九、最後：選擇的時刻

技術發展的本質，就是不斷地將複雜的事情封裝成簡單的工具，讓人類能夠站在更高的抽象層級上，去解決更宏大的問題。

既然 AI 已經幫我們造好了最鋒利的鏟子，我們又何必非要堅持用雙手刨土？

「拒絕使用 AI」和「完全依賴 AI 失去自己的判斷力」，都是錯誤的兩個極端。

正確的路徑是：

```
你的判斷力 + AI 的執行力 = 超越過去任何時代的個人生產力
```

這是每一個技術人在今天必須做出的選擇。

> [!quote] Steve Yegge
> 放下對舊時代的執念，擁抱那令人恐懼但又無比寬廣的新世界。

---

## 我的心得（My Takeaways）

這支影片讓我印象最深的，是「吸血鬼效應（Vampire Effect）」這個概念——這是我之前從未認真思考過的面向。我們討論 AI 生產力的時候，通常只談「輸出量增加了多少倍」，卻忽略了「認知成本（cognitive cost）的重新分配」。

當 AI 把輸出速度提高 100 倍，但人類的審核能力只提高了 5 倍，這個差距就是新的瓶頸所在。這意味著，在 AI 時代，工程師最重要的基礎設施，是**自己的認知健康與注意力管理**，而不是技能清單的長度。

另一個值得深思的是 Yegge 對大公司的批評。官僚主義並不是新問題，但 AI 讓它第一次有了真正致命的替代方案——小團隊現在真的可以在某些維度上超越大公司，這在過去是幾乎不可能的。

---

## 關鍵洞察（Key Insights）

- **球門效應（Moving Goalposts）**：軟體工程的技能門檻一直在向更高抽象層移動，AI 只是這個趨勢的最新一波，不是終點——參見 [[ABSTRACTION-LAYERS-IN-ENGINEERING]]
- **苦澀的教訓（Bitter Lesson）**：算力＋通用演算法，長期來看必然超越人類專家知識的硬編碼——參見 [[BITTER-LESSON-RICH-SUTTON]]
- **吸血鬼效應（Vampire Effect）**：AI 時代的新瓶頸是人類的認知處理速度，不是程式碼產出量
- **微型團隊崛起（Rise of Micro-Teams）**：AI 讓小團隊在執行力上能比肩大公司，徹底改變產業競爭格局——參見 [[MULTI-AGENT-SYSTEMS]]
- **IDE 典範轉移（IDE Paradigm Shift）**：對話（conversation）正在取代程式碼編輯器成為主要開發介面——參見 [[VIBE-CODING]]

---

## 待補充（Open Questions）

- 吸血鬼效應（Vampire Effect）的認知超載問題，在人體工學或認知科學領域有無對應的研究框架？「三小時是高強度 AI 協作的上限」這個數字有無實驗依據，還是個人經驗？（建議搜尋：`cognitive overload AI-assisted review attention fatigue limit research`）
- Yegge 預測 IDE 走向消亡——但程式碼的靜態結構分析、語法高亮、型別推斷這些工具仍然服務於「人類理解程式碼」的需求。即便不手寫程式碼，工程師仍需閱讀與審查，IDE 的哪些功能在 AI 時代反而更重要？（建議搜尋：`IDE future AI era code review tools static analysis`）
- Gas Town 專案（Yegge 的多代理人系統）的架構細節是什麼？它與 Karpathy 的 AutoResearch、OpenClaw 等同類系統相比，在任務分解和代理人調度上有何不同設計選擇？（建議搜尋：`Steve Yegge Gas Town multi-agent system architecture`）
- 「微型團隊崛起」的論點假設小團隊在 AI 輔助下能達到大公司的執行力——但大公司的護城河還包括品牌信任、合規資質、銷售管道等非技術因素。AI 在哪些特定維度縮短了差距，在哪些維度差距依然存在？（建議搜尋：`micro-team vs big tech competitive advantage AI non-technical moat`）
- Vibe Coding（以自然語言傳達業務邏輯和架構直覺）在對模型傳達隱性知識（tacit knowledge）時有何本質限制？在安全性、合規性等需要精確規格的領域，Vibe Coding 的適用邊界在哪？（建議搜尋：`vibe coding limitations safety compliance precise specification`）
- Yegge 對大公司官僚主義的批評是否低估了規模效應的其他優勢（如資料護城河、算力優勢、人才密度）？歷史上哪些技術典範轉移確實讓小公司顛覆大公司，哪些最終大公司仍佔主導？（建議搜尋：`big tech disruption AI startup vs incumbent data moat compute advantage`）

## 相關連結（Related）

- [[BITTER-LESSON-RICH-SUTTON]] — Rich Sutton 的《苦澀的教訓》是理解 AI 發展規律的必讀文章
- [[MULTI-AGENT-SYSTEMS]] — 多代理人系統的架構設計原則
- [[VIBE-CODING]] — Vibe Coding 的工作方法論與最佳實踐
- [[ENGINEER-CAREER-IN-AI-ERA]] — AI 時代工程師職涯規劃的整體框架
- [[STEVE-YEGGE-EXECUTION-IN-KINGDOM-OF-NOUNS]] — Yegge 的經典文章《名詞王國的執行》
- [[2026-04-09-AI-ONE-PERSON-COMPANY-KARPATHY-OBSIDIAN-KB-OPENCLI]] — 多 AI 角色分工在一人公司中的具體實踐案例
- [[2026-03-28-AI-ERA-ENGINEER-CORE-VALUE-MICHAEL-BOLIN-META-E9]] — 同頻道「最佳拍檔」訪談 Meta E9，從個人層面論證 AI 時代工程師的核心價值
- [[2026-03-30-STANFORD-STUDY-22YO-EMPLOYMENT-DROPS-20PCT-750-CFOS-AI-LAYOFFS-9X]] — 斯坦福數據驗證 Yegge 觀點：初階工程師就業塌方，但資深者反增

## References

- [影片原址](https://www.youtube.com/watch?v=qvjVQJHrQ-M)
- [Rich Sutton - The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)
