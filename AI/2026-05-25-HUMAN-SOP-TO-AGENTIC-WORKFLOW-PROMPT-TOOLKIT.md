---
title: "把最無聊的重複流程交給 AI：從 Human SOP 變成 Agentic Workflow 的 Prompt 工具包"
date: 2026-05-25
category: AI
tags:
  - ai/agentic-workflow
  - ai/prompt-engineering
  - ai/mcp
  - productivity/workflows
  - ai/skills
source: "https://www.patreon.com/posts/ba-zui-wu-liao-159637740"
source_type: article
author: "Gary Chen"
status: notes
links:
  - "[[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]]"
  - "[[2026-03-31-AI-WORKFLOW-AGENTS-SKILLS-STANDARDS]]"
  - "[[2026-05-04-STANFORD-AUGMENTING-LLMS-FIVE-TECHNIQUES-AI-BUILDER-TOOLKIT]]"
  - "[[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]]"
  - "[[2026-04-09-AI-ONE-PERSON-COMPANY-KARPATHY-OBSIDIAN-KB-OPENCLI]]"
  - "[[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]]"
---

## 摘要（Summary）

本篇由 Gary Chen 撰寫，主張**前沿模型的能力早已不是瓶頸**——真正的瓶頸在於「你有沒有把工作講清楚到 agent 能接手」。作者反對把整包任務丟給一個超強 mega agent（黑箱、不可 debug），主張用**分而治之（divide and conquer）**把一份「寫給人看的流程（Human SOP）」拆成一條由小節點組成的 agentic workflow。

文章提出**四步拆解法**（格式標準化 → 任務拆解與鏈結 → 雙向開發 → 整合與執行環境），並點出一個結構性死結：**越資深的人，因為判斷被壓縮成默會知識（tacit knowledge），第一版 SOP 越容易翻車**。最後校準期待——先求「一致性」再談「全自動」——並指出這套能力會把你的角色從搬 context 的「搬運工」升級成設計流程的「流程擁有者（process owner）」，是未來兩三年最值錢的護城河。

本筆記包含三部分：**①原文（原封不動轉錄）→ ②我的分析 → ③配套的五步 Prompt 工具包（原封不動轉錄）**。

> [!info] 來源與日期說明
> 本篇為兩份配套內容的合併筆記：Patreon 文章（原文）＋ garytalksstuff.com 提供的五步 Prompt 工具包。Prompt 工具包頁面 URL 標示日期為 `20260525`（2026-05-25），故採用此日期；Patreon 文章發布欄顯示「昨日」。

## 關鍵洞察（Key Insights）

- **瓶頸換位了**：問題不是「模型會不會做」，而是「你有沒有把事情講到它能接手」。模糊任務餵給強模型，只會得到「更快、更有自信的錯誤答案」。
- **Mega agent 是最多人翻車的起點**：整包進、整包出的黑箱無法 review、無法 debug，永遠不可能 production-ready。
- **拆成節點才能對症下藥**：每個節點有明確 input／output／成功標準，節點間靠 artifact（通常是 JSON）傳遞，「哪裡壞改哪裡」。
- **第一版 SOP 必翻車，且越資深越慘**：默會知識（tacit knowledge）把判斷壓縮成直覺，資深者能寫成規則的比例反而最低 — 參見 [[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]]。
- **先求一致，再談全自動**：拆解的第一個紅利不是全自動，而是**可重複的一致性**。
- **角色升級**：從 manual orchestration 的「搬運工／調度員」升級成 process owner — 呼應 [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] 的人才分界線。

> [!note] 關鍵術語（Key Term）：默會知識（Tacit Knowledge）
> 已長在你肌肉記憶裡、卻說不出口的「直覺」。寫 SOP 就是逼你把這些直覺翻譯成白紙黑字。挖掘方法只有一招：**不要從「你以為你怎麼做」開始，要從「你實際做出來的成品」往回推**。

---

## 原文（Original Article）

> [!quote] 以下為作者原文，原封不動轉錄（繁體中文原文）。

把最無聊的重複流程交給 AI：從 Human SOP 變成 Agentic Workflow 的 Prompt 工具包

作者：Gary Chen

前沿模型的能力早就不是什麼瓶頸了。

如果你有在關注最近的 coding agent，會發現它們在 Terminal-Bench 這種要連續操作多步工具、跨檔案改 code 的硬核測試上，分數已經一路從六七成狂飆到八成以上。現在要它 review 一整包 pull request，或是照著 Figma 乖乖切版，甚至跨 Slack 跟 GitHub 去把漏掉的 context 給撈回來... 這些一年前聽起來像科幻小說的場景，現在根本是每天的日常。

既然模型這麼強，為什麼當你真的把一個真實任務「整包」丟給它的時候，出來的東西常常還是很不靠譜？

其實，坑根本不在模型身上。模型已經強到一個地步，真正的瓶頸已經悄悄換了位子：現在的問題不是「模型會不會做」，而是「你到底有沒有把這件事講到它能聽懂、能接手」。

這就是最要命的地方。如果你拿一個很模糊的任務，去餵給一個超強的模型，結果會怎樣？它不會通靈給你滿分考卷，它只會給你一個「更快、更有自信的錯誤答案」。它會洋洋灑灑幫你生出一大堆東西，每一步看起來好像都挺有道理，但整包湊起來就是歪的，而且你還很難一眼抓出到底是哪邊出包了。

### 本期文章包含以下內容

為什麼不能整包丟給一個超強 agent：mega agent 看起來最省事，卻是最多人翻車的起點。先講清楚拆解到底解決了什麼它做不到的事。

到底要怎麼拆？四步講給你聽：從格式標準化到接上真實工具，一步步把一份只有你看得懂的白話 SOP，改造成 agent 能無腦照跑的生產線。

為什麼你的第一版 SOP 絕對會翻車：拆解「為什麼你總是寫不出完整流程」背後的真實機制。先爆個雷：越資深的人，越難把工作交出去。

先別管全自動了，先求「一致」吧：聊聊大家對「把流程交給 AI」最常踩的坑，還有這個不切實際的期待，是怎麼讓你的專案還沒上線就先宣告陣亡的。

從「搬運工」升級成「流程的擁有者」：當你真的靜下心來拆解任務，你的角色會跟著升級。為什麼這會是未來兩三年最值錢的競爭力？

五步 Prompt 工具包：直接拿你手上最煩、最重複的那份流程來試。貼進去跑一圈，出來就會是一條真正能上線運作的 agentic workflow。

先給你打一劑預防針，聽起來有點反直覺：你那份自己覺得寫得天衣無縫的流程，第一次跑，百分之百會垮掉。而且資歷越深的人，通常垮得越慘。這真不是因為你不夠認真，這是一個結構性的死結。

### 🔧 本期工具

這是我整理的一組五步 Prompt 工具包。它的功能很單純：幫你把一份「寫給活人看的流程（Human SOP）」，一步步打造成 agent 能無腦照做的 agentic workflow。你可以把它想像成是在蓋一條工廠生產線，每個小站點都有自己的輸入跟輸出。

怎麼用：挑一份你最常重複、最不想做的流程，從第一個 prompt（SOP Triage）開始，它先幫你判斷這份值不值得拆、該從哪下手。接著 Format Standardizer、Pipeline Decomposer、Tacit Knowledge Extractor、Integration & Checkpoint Planner 這四個，會帶你把它跑完下面要講的那四步。每個 prompt 的 output 就是下一個的 input，跑完你手上拿到的是一條能上線的 workflow，不是一份還要再翻譯一次的文件。

### 等等，為什麼不乾脆丟給一個超強的 agent 就好？

你可能會想：模型都這麼神了，我幹嘛還要搞這些拆解？整包丟給它，讓它從頭跑到尾不就得了？這種「一個 agent 包山包海」的玩法，業界叫它 mega agent。聽起來很爽，但它正是大多數人翻車的起點。

問題出在哪？舉個生活化的例子。你出門前請了個幫手，只丟一句「把家裡打掃乾淨」就走人，回家大概率會吐血。為什麼？因為你跟他對「乾淨」的定義根本不一樣。你以為的乾淨是地板不黏腳、水槽沒堆碗，他以為的乾淨是東西有歸位、看得順眼就好。問題從來不是他笨，是你沒講清楚，而他又不會通靈。

mega agent 就是這個幫手。你跟它說「幫我優化整個開發流程」，它一定會生出點什麼，可能改一堆 config、refactor 一個你根本不該動的模組。但它是個徹底的黑箱：你看不到哪段推理是對的、哪個工具調錯了、哪一段是它自己腦補的。整包進、整包出，中間發生什麼你完全沒法 review，更別說 debug。

反過來，如果你把任務拆成一串小節點，每個都有明確的 input、output 跟成功標準，情況就完全不一樣。出錯了，你回去翻 log，發現是「分類」那段把客訴誤判成諮詢，你就只修那一份 SOP，查資料的、寫回覆的、做 QC 的，動都不用動。哪裡壞改哪裡，對症下藥。

這也是為什麼那些企業級的 agentic workflow 框架，做的就是「把複雜流程拆成一串小 agent」這件事。因為他們要上 production，要的是穩定性、可觀測性、可修復性。一個你看不到內部的黑箱，永遠不可能 production-ready，因為你根本不敢讓它上線。所以 divide and conquer、分而治之這個老到掉牙的觀念，在 agent 時代反而更值錢：你不是在訓練一個超人，而是在設計一條生產線。它乍看很無聊，但可預測、有邊界、出錯能修，而這些才是真正重要的事。

### 好，那到底要怎麼拆？四步走一遍

講了半天「拆」，到底實際怎麼操作？別想得太玄。我拿「寫週報」這種人人都嫌煩的鳥事當例子，把這四步走一遍給你看。

**第一步，格式標準化。** 先把你那份白話 SOP，翻成 agent 讀得懂的版本，重點三個。一是參數化，別把規則寫死成「一定要條列式」，改成 format 這種參數，讓同一份 SOP 能 cover 不同場合。二是用 MUST / SHOULD / MAY 標清楚每條規則的強度，這是 RFC 2119 的寫法，逼你想清楚哪條不能妥協、哪條看狀況，比方「MUST 附上本週數字」「SHOULD 點名功臣」「MAY 放張慶祝的 GIF」。三是用 Markdown 把 Parameters、Steps、Error Handling 切乾淨。最容易翻車的地方：很多人每條都寫成 MUST，結果現實稍微一變，整個流程就卡死。

**第二步，任務拆解與鏈結。** 把這份 SOP 切成幾個獨立節點，每個只做一件明確的事。週報拆開大概是：撈這週數據、篩出重點、寫成草稿、潤稿四段。每段有自己的 input、output 跟成功標準，能單獨跑、單獨 debug，獨立到一個程度，甚至能各自包成一個小 skill，也就是一個資料夾，裝著它的 SOP、參考資料跟能直接跑的腳本，之後別條流程要用就直接拿。為什麼一直跳針強調「獨立」？因為撈數據那段出包，你只要修那一段，後面潤稿的邏輯動都不用動。那節點之間靠什麼接？靠 artifact，通常就是一份 JSON。篩重點那段吐出一份 JSON，列清楚這週每個重點、對應數字、功臣是誰，寫草稿那段直接吃這份 JSON，不是靠 agent 之間通靈。

**第三步，雙向開發。** 這步最多人跳過，卻是整套裡最關鍵的。你的第一版 SOP 一定有洞（為什麼，下一節會講），所以正確玩法不是關在房間憋一份完美版，而是跑一次、撞牆一次、補一條規則，再跑再補。比方它第一次把數字四捨五入到你想翻桌，你就補一條「金額一律不准四捨五入」。幾輪下來，SOP 就穩到 cover 八九成情境，剩下的極端狀況丟給人就好。速度的關鍵從來不是你寫得多完美，是你迭代得多快。

**第四步，整合與執行環境。** 再漂亮的 SOP，沒接上真實工具，也只是一份躺著的文件。週報的工具就是你的數據源、Slack、Google Doc 這些。這時你會撞到一個現實：每家公司系統都長得不一樣，你為 A 公司寫的接法，搬到 B 公司可能整個動不了。這就是 MCP（Model Context Protocol）想解決的事，你可以把它想成 AI 世界的 USB-C，一套標準接口，讓 agent 用同一種方式串不同工具。最後別忘了在高風險的環節插一個 human-in-the-loop checkpoint，比方「數字對外公布前，停下來等你按 OK」。這樣整條線就不是一台脫韁的機器，而是你掌舵、agent 出力。

四步走完，一份原本只能你自己跑的週報，就變成一條每天能自動跑、出錯還能第一時間知道去哪修的 workflow 了。而上面那組工具，做的就是抓著你，把你自己挑的那份 SOP，實際跑完這四步。

### 為什麼你的第一版 SOP 絕對會翻車

說真的，我可以給你一個保證：不管你在業界打滾多久、多會畫流程圖，你寫出來的第一版 agent SOP，拿去跑絕對會翻車。這不是在看衰你，而是背後有個結構性的死穴。

這個死穴叫 默會知識（tacit knowledge）。聽起來很學術？說白了，就是那些已經長在你肌肉記憶裡、但你根本不知從何說起的「直覺」。寫 SOP，其實就是逼你把這些直覺，硬生生翻譯成白紙黑字的規則。但這玩意最搞人的地方在於：你平常根本感覺不到它的存在，直到 AI 幫你搞砸了，你才會驚覺：「啊，慘了，忘記跟它說這個條件！」

為什麼會這樣？因為「變專業」的過程，本來就是一個把判斷偷偷藏起來的過程。

如果你是工程師，你可以把這當成是寫程式的「編譯」。剛入行的時候，你做的每個決定都像 source code（原始碼），一行一行清清楚楚攤在腦子裡，你會刻意去想「等一下要先檢查這個，再檢查那個」。但做久了，這些判斷就會被大腦自動編譯成 machine code（機器碼），壓縮成一種你連想都不用想的直覺。就像新手學開車，每次變換車道，心裡都要默念一遍：看後照鏡、打方向燈、轉頭看死角、轉方向盤。十年老司機呢？一邊跟旁邊的人瞎聊，一邊方向盤一打就切過去了。你之所以變快、變強，靠的就是這種「壓縮」。但代價是什麼？代價是你現在大腦裡只剩下機器碼，當年的原始碼早不知道丟哪去了。

這就帶出一個超反直覺的結論：越資深的人，越難把工作交給 agent。

你越強，判斷被壓縮得越狠，能直接寫成規則的比例就越低。反而是那些剛入行的新手，工作還停留在「原始碼」階段，每一步都能講得頭頭是道，他們的 SOP 反而更好讓 agent 接手。結果就是：最需要 AI 幫忙減輕負擔的高手，偏偏是最難把工作交出去的那群人。這才是真正卡死一堆人的痛點。

所以，千萬不要把自己關在房間裡，妄想能憑空寫出一份「完美 SOP」。我之前看過一個開發者，花了快四十個小時在那邊精雕細琢他的委派規則，結果跑起來還是一路撞牆，最後他崩潰地說，管這個 agent 比帶一個實習生還累。我也遇過一個客戶，花了兩個月憋出一份他們自認無懈可擊的 SOP，結果上線第一天就垮了。為什麼？因為他們寫的全是「想像中」的情境，真實世界根本不按牌理出牌。

要把這該死的默會知識挖出來，只有一招：別從你「以為你怎麼做」開始，要從你「實際做出來的成品」往回推。

把過去你覺得做得最棒的幾份產出攤在桌上，然後像個偵探一樣，逐一逼問自己：「當初為什麼這樣選？」那些你平常沒明講、卻默默在用的判斷標準，才會像擠牙膏一樣一點一滴被擠出來。這就是工具包裡 Tacit Knowledge Extractor 在幹的活。它才不管你平常「自稱」怎麼做，它會要你直接交出成品，然後像拿著放大鏡一樣，幫你把藏在裡面的方法論給逆向工程出來。

### 先求「一致」，再談「全自動」

很多人一聽到「把流程交給 AI」，眼睛就發光了，腦袋裡浮現的都是「太爽了，以後這件事我都不用管了」的全自動畫面。聽我一句勸，這個期待會害死你。它會讓你不自覺地把第一個專案搞得又大又肥，結果成效不如預期時，你就兩手一攤說：「唉，現在的 agent 還是太笨了。」

其實，拆解任務帶來的第一個紅利，從來就不是什麼全自動，而是「一致性」。

這兩個東西差很多喔。全自動是「你不用管了」，但一致性是「每次那一刀切下去，標準都一模一樣」。你今天辛苦弄好一條客訴分類的 workflow，它真正幫你解決的痛點是：明天它還是會用同一套邏輯去分類；下禮拜換你同事來跑，結果也不會走鐘；輸出的格式更是穩穩當當，不會今天長這樣、明天長那樣。這種「可重複性」聽起來很無聊，遠沒有「全自動」那麼性感，但在真實的職場裡，這種穩定的輸出品質，才是真正能讓你晚上睡好覺的護城河。

想通這一點，你對 agent 的期待就會整個校準回來。

你不需要一開始就逼它接管全場。你先讓它每次都能穩定吐出一個「你信得過」的版本就好，哪怕最後一步還是得靠你親自去按那個確認鍵，這筆交易怎麼看都划算。一個能穩定幫你生出及格初稿的系統，就算你還得稍微收個尾，也絕對比你每次在那邊面對空白文件從零開始要強上一百倍。至於全自動？那是以後的事。要不要放手讓它全自動，取決於這件事出包的代價有多大，還有你的檢查機制夠不夠硬，那完全是另一個等級的問題了。記住，第一步永遠是：先讓它穩定、可重複。

這也是為什麼，我強烈建議你，千萬不要一口氣把公司所有的流程都往 agent 身上砸。

挑一個你平常覺得最智障、最常重複的流程，先弄出一個能幫你省下三成時間的版本就好。讓它穩穩地幫你省，之後再慢慢往上疊加。在工具包的最後一個 prompt 裡，我附了一份跑完一週後的「體檢 checklist」，裡面只問三個問題：

1. 它真的有幫你省到時間嗎？
2. 你花在幫它擦屁股、檢查錯誤的時間，有比你自己動手做少嗎？
3. 如果明天我把這個 workflow 關掉，你會不會覺得痛苦？

你看，這三題在意的全是「到底能不能用」和「表現穩不穩定」，完全沒有半個字在問它有沒有達到全自動。

### 從苦命「搬運工」，升級成「流程的擁有者」

當你開始認真把任務拆解，走到最後你會發現，真正改變的其實不是你的產出，而是你的「角色」。

回想一下，在你還沒做拆解之前，你是怎麼跟 agent 互動的？說穿了，那是一份超級心累的苦差事：你不停地下指令說「先做這個」、「去參考那份資料」、「看一下這個檔案」、「啊，不對，重來」、「不要用這種官腔語氣」... 這在行話裡叫 manual orchestration。你其實是在替系統做那些「它本來就該自己記住」的苦力活。你既是那個到處複製貼上搬 context 的搬運工，又是那個指揮交通的調度員。最崩潰的是，只要你下次還要做同樣的事，這整套動作就得原封不動再來一遍。

但是，一旦你把流程拆解好，寫成了一條 agent 能讀懂的 workflow，那些煩人的搬運和調度，就會直接沉澱到底層系統裡。這時候，你的工作就默默往上升了一級。

你不再是個苦命的 clipboard，不再是個沒有靈魂的 router。你升級成了一個 process owner。你的工作重心，會從「親自下去跑這條流程」，變成「站在高處設計：我們需要哪些流程？哪些環節要靠人來把關？萬一出錯了，備案是什麼？」。那些機械化、重複性高的爛缺都交出去了，你留給自己的，是最純粹的「判斷」與「設計」。

那代表什麼？那代表這層升級，就是你未來兩三年在職場上最值錢的護城河。

而且這不是工程師圈內的小眾預言。MCP 這個協定現在 ChatGPT、Claude、Cursor 全都支援，Anthropic 還在 2025 年初把它捐給了 Linux Foundation 底下的 Agentic AI Foundation，等於正式昭告它會是個有人長期維護的開放標準。再往上看，ServiceNow、IBM、AWS 這些大公司，內部處理 IT ticket、HR 請求、各種服務流程，早就改用 agentic workflow 在跑，而不是傳統的規則引擎。換句話說，「把流程拆給 agent 跑」正在變成基礎建設，而能設計這些流程的人，自然就站在浪頭上。

老實說，未來會用 AI、會寫 prompt 的門檻，只會越來越低。真正稀缺的人才，是那些能一眼看出「我手邊這堆爛事，哪一塊可以被打包成可重複使用的基礎建設」的人。而且，這件事還有一個你可能沒想過的隱藏紅利：當你成功把你的判斷邏輯寫進 workflow 裡，這些寶貴的經驗，就不會只鎖在你一個人的腦袋裡了。以前，一個資深大神離職，他那套「只可意會不可言傳」的神奇直覺，就直接跟著他走出公司大門了。現在？它被留在了 workflow 裡，變成公司實實在在能帶得走的資產。

說到底，我們今天聊這一切，並不是在教你怎麼「玩 AI」。你真正在學的，是怎麼把你腦袋裡那些難以言喻的專業，精準地翻譯成一套「不管是人還是機器，都能無痛接手」的系統。

模型每一天都在變強，如果你每次都還得從頭跟它解釋一遍你要什麼... 那真正的瓶頸從來就不是模型，是你。

---

## 我的分析（My Analysis）

> [!note] 以下為筆記者（Claude）對原文的延伸分析，非作者原文。

### 這篇文章的論證骨架

作者其實是用一條清楚的因果鏈在說服讀者：

```
模型已夠強  ──►  瓶頸換成「人講不清楚」
                     │
                     ▼
        整包丟 mega agent  ──►  黑箱、不可 debug、不敢上 production
                     │
                     ▼
          divide and conquer（拆成節點 + JSON artifact）
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   四步拆解法              第一版必翻車（默會知識）
   1 格式標準化            └─► 解法：從「成品」反推判斷
   2 拆解與鏈結
   3 雙向開發（迭代）
   4 整合與執行（MCP + HITL）
                     │
                     ▼
       先求「一致性」，再談「全自動」
                     │
                     ▼
        角色升級：搬運工 ──► process owner（護城河）
```

### 與既有知識的連結

- **「拆成小節點」呼應 Stanford 的 decomposition 技巧** — 參見 [[2026-05-04-STANFORD-AUGMENTING-LLMS-FIVE-TECHNIQUES-AI-BUILDER-TOOLKIT]]，把大任務拆成可驗證的小步驟是 augmenting LLM 的核心手法之一。
- **「打包成 skill」呼應 Skills 三層架構** — 作者說每個節點可包成一個資料夾裝 SOP＋腳本，這正是 [[2026-03-31-AI-WORKFLOW-AGENTS-SKILLS-STANDARDS]] 與 [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]] 講的 skill 結構。
- **「第一版必翻車」呼應 AI Agent 的痛苦教訓** — 參見 [[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]]，看完教程仍做不對，本質上就是默會知識沒被外化。
- **「process owner」呼應 Karpathy 的人才分界線** — [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] 同樣主張未來價值在「設計與治理系統」而非親手執行。

### 我認為文章最強與最弱的地方

> [!tip] 最強：把「為什麼你寫不出好 SOP」講成結構性問題
> 「source code 編譯成 machine code」這個比喻精準命中痛點 — 它解釋了為何**越資深越難交付**，並給出可操作的解法（從成品反推），而不是空喊「請寫清楚一點」。這比多數同類文章只停在「prompt 要寫好」深一層。

> [!warning] 最弱：對「拆解成本」與「何時不該拆」幾乎沒著墨
> 文章強力推銷拆解，但拆成多節點本身有維護成本（多個 SOP、JSON schema、節點接縫）。對於一次性、低頻、或本來就模糊到不值得形式化的流程，硬拆反而是過度工程。作者只在 Prompt 1（SOP Triage）裡用「該不該拆」帶過，正文沒有平衡論述。

> [!warning] 待查證：MCP 捐給 Linux Foundation 的細節
> 原文稱「Anthropic 在 2025 年初把 MCP 捐給 Linux Foundation 底下的 Agentic AI Foundation」。此說法的確切時間點與機構名稱我無法在本次作業中查證，引用前建議自行核實（見 Open Questions）。

### 一句話總結

> 別把 AI 當超人來訓練，把它當生產線來設計 — 你的價值不在跑得多快，而在你能把多少「只可意會」的判斷，翻譯成「可重複交付」的規則。

---

## 配套五步 Prompt 工具包（Prompt Set — 原封不動轉錄）

> [!important] 以下為 garytalksstuff.com 提供的配套提示詞集合，原封不動轉錄。來源：`https://garytalksstuff.com/20260525_sopflow_promptset_1`
> 五個 prompt 可一路串接跑完，也可單獨使用。全部與 Claude、ChatGPT、Gemini 任何對話介面相容。

### 工具包總說明

**Human SOP → Agentic Workflow 拆解工具包**

五個串接的 prompt，帶你把一份寫給人看的流程，一步步變成 agent 能穩定執行的 agentic workflow：SOP Triage 挑對象、Format Standardizer 標準化、Pipeline Decomposer 拆節點、Tacit Knowledge Extractor 補判斷、Integration & Checkpoint Planner 接工具。配套那篇講把 Human SOP 變 agentic workflow 的 Patreon 文章使用。

這組工具配套那篇講「把 Human SOP 變成 agentic workflow」的文章。文章的結論是：前沿模型已經夠強，你的 agent 跑不好，問題通常不在模型，而在你還沒把工作講清楚到它能接手。而把一份流程拆好、交給 agent 穩定執行，第一個回報不是全自動，是一致性，到最後它還會把你的角色從搬 context 的人，升級成設計與治理流程的 process owner。

這五個 prompt 把文章講的方法，變成你能對自己一份真實流程一路跑完的工具。你挑一份手上最無聊、最常重複的流程，從 SOP Triage 開始判斷該不該拆、從哪拆，接著 Format Standardizer 幫你結構化、Pipeline Decomposer 幫你拆成獨立節點、Tacit Knowledge Extractor 幫你把說不出口的判斷補回去，最後 Integration & Checkpoint Planner 幫你接上真實工具跟人工確認點。每個 prompt 的 output 就是下一個的 input，跑完你手上拿到的是一條可以上線的 workflow，不是一份還要再翻譯一次的文件。

**提示**：五個 prompt 可以一路串接跑完，也可以單獨用。如果你已經有 SOP、只是 agent 跑不穩，可以直接從 Format Standardizer 或 Tacit Knowledge Extractor 進。全部跟 Claude、ChatGPT、Gemini 任何對話介面相容。

### 怎麼用這組 prompts

**路徑 A（從零改造一份流程）**：SOP Triage → Format Standardizer → Pipeline Decomposer → Tacit Knowledge Extractor → Integration & Checkpoint Planner 依序跑，每一個的 output 貼進下一個。

**路徑 B（你已經知道要拆哪份、手上也有白話 SOP）**：跳過 SOP Triage，直接從 Format Standardizer 開始。

**路徑 C（你的 workflow 跑得起來，但產出總差一點）**：直接跑 Tacit Knowledge Extractor，把你漏掉、說不出口的判斷挖出來補回去。

### 包含內容

- **Prompt 1：SOP Triage** — 從你一堆重複流程裡挑出最該先拆的那一份，並判斷它夠不夠清楚到能拆
- **Prompt 2：Format Standardizer** — 把白話流程改寫成參數化、標好 MUST／SHOULD／MAY 的結構化 SOP
- **Prompt 3：Pipeline Decomposer** — 把 SOP 拆成獨立節點，定義每個節點的 input／output 跟節點間的 JSON artifact
- **Prompt 4：Tacit Knowledge Extractor** — 從你的實際成品反推你說不出口的判斷，補回 SOP，附雙向開發迭代 checklist
- **Prompt 5：Integration & Checkpoint Planner** — 規劃工具接點、human-in-the-loop checkpoint，跟一份跑一週後的評估 rubric

**工具建議**：五個都建議在 Claude（Opus 或 Sonnet）或 ChatGPT 的對話介面跑，因為它們需要來回追問、逼出你的具體流程跟判斷。產出的結構化 SOP、pipeline schema、checkpoint 計畫都是純文字，可以直接貼進你的 skill 檔、agent 工具或團隊文件。

---

#### Prompt 1：SOP Triage

**功能**：

你手上一定不只一份重複流程。這個 prompt 用對話幫你從裡面挑出最值得第一個拆成 workflow 的那一份，並判斷它現在夠不夠清楚到能拆，避免你一頭栽進一個註定失敗的對象。

**什麼時候用**：

你想開始把日常流程交給 agent，但不確定該從哪一份下手；或你懷疑某個流程其實還太模糊、現在不適合自動化。

**你會拿到**：

一份 triage 報告：每份候選流程在 recurrence、判斷依賴度、可檢查性三個維度的 1-5 分評分，一個排序後的推薦順序，第一順位那份的卡點與下一步，以及任何「現在還不該拆」的明確標記。

**可以接到哪**：

Prompt 2: Format Standardizer（拿排序第一的流程進去標準化）

**AI 會問你**：

1. 你最近常重複做、又覺得煩的流程有哪些？先列出來，一份一句話就好
2. 每一份大概多久做一次？一天好幾次、每週、還是每個案子一次
3. 哪幾份做起來很吃你的個人判斷，哪幾份比較像照表操課
4. 哪幾份你一眼就能看出做得好不好，哪幾份很難檢查
5. 這些流程裡，有沒有哪一份做錯的代價特別高，例如碰錢、改權限、對外發送

---

#### Prompt 2：Format Standardizer

**功能**：

把你選定的白話流程，改寫成 agent 讀得懂的結構化 SOP。它會把寫死的步驟參數化、用 MUST／SHOULD／MAY 標清楚每條規則的強度，再切成 Parameters、Steps、Error Handling 幾個區塊，讓同一份 SOP 能 cover 多種情境，而不是只 cover 一種。

**什麼時候用**：

你已經挑好要拆哪份流程，手上是一段白話描述，想把它變成 agent 能穩定執行的規格。

**你會拿到**：

一份結構化 SOP：包含 Parameters（可帶入的變數與選項）、Steps（每條標上 MUST／SHOULD／MAY）、Error Handling，乾淨到可以直接塞進 skill 檔或 MCP 接口。

**可以接到哪**：

Prompt 3: Pipeline Decomposer（把這份結構化 SOP 拆成 pipeline 節點）

**AI 會問你**：

1. 請用你平常的講法，把這份流程從頭到尾講一遍，包含你會偷懶跳過、或一定會做的地方
2. 這份流程在不同情境下會變嗎？例如數量、緊急程度、對象不同時，做法會不會不一樣
3. 哪些步驟絕對不能跳，哪些有理由可以省，哪些做不做都行
4. 做這件事最容易出錯、或最容易被忘記的地方是哪裡

---

#### Prompt 3：Pipeline Decomposer

**功能**：

把一份結構化 SOP 拆成一條 pipeline，每個步驟變成一個獨立節點，各自有明確的 input、output 跟成功標準。它還會幫你定義節點之間傳遞的 artifact 格式（通常是 JSON），讓「哪裡壞改哪裡」變成可能，而不是整包重寫。

**什麼時候用**：

你已經有一份結構化 SOP（最好是 Format Standardizer 的產出），想把它變成一條可以獨立 debug、獨立替換每一段的生產線。

**你會拿到**：

一份 pipeline 設計：節點清單（每個一件明確的事）、每個節點的 input／output／成功標準、節點之間的 JSON artifact schema，以及標出哪些節點未來可以獨立抽換。

**可以接到哪**：

Prompt 4: Tacit Knowledge Extractor（把你說不出口的判斷補進這些節點）

**AI 會問你**：

1. 請貼上你的結構化 SOP，或把這份流程的步驟講一遍
2. 這條流程從頭到尾，你覺得可以切成哪幾個獨立的階段
3. 每個階段做完，會產出什麼東西交給下一段
4. 哪個階段最常出錯、或最可能之後想換掉做法

---

#### Prompt 4：Tacit Knowledge Extractor

**功能**：

你寫的第一版 SOP 一定漏掉一堆你自己都沒意識到的判斷，因為那些判斷早就被你壓縮成直覺。這個 prompt 不問你『你都怎麼做』，它要你交出過去最滿意的幾份成品，然後從成品反推出你說不出口的標準，幫你一條一條補回 SOP。

**什麼時候用**：

你的 SOP 或 workflow 第一版跑出來，產出總覺得差一點、不是你要的，但你講不清楚到底哪裡不對。

**你會拿到**：

一份補丁清單：從你實際成品反推出的判斷規則（每條都對應到一個具體的成品證據），可以直接加進 SOP 的對應步驟，外加一份雙向開發迭代 checklist，引導你每跑一輪補一條。

**可以接到哪**：

Prompt 5: Integration & Checkpoint Planner（把補強後的流程接上真實工具）

**AI 會問你**：

1. 這份流程的成品，你過去最滿意的三到五份能不能貼上來，或描述到我能重建的程度
2. 這幾份裡，有沒有哪個地方是你特別堅持、別人可能不會這樣做的
3. 你最近一次拒絕或大改某個版本，是因為哪裡不對
4. 有沒有哪種狀況你會直接破例、不照原本流程走

---

#### Prompt 5：Integration & Checkpoint Planner

**功能**：

再漂亮的 SOP，不接上真實工具就只是一份文件。這個 prompt 幫你規劃這條 workflow 怎麼接到你公司實際在用的系統，哪些有現成的 MCP／connector、哪些要自己接，再幫你在高風險的決策點設好 human-in-the-loop checkpoint，最後給你一份跑一週後的評估 rubric。

**什麼時候用**：

你的 pipeline 設計好了（最好有 Pipeline Decomposer 的產出），準備讓它真的在你的工具環境裡跑起來，而不是停在紙上。

**你會拿到**：

一份整合計畫：每個節點要接的工具清單（標出哪些有現成 MCP／connector、哪些要自建或人工橋接）、觸發方式與排程建議、高風險決策點的 human-in-the-loop checkpoint 設計，以及一份跑一週後問三個問題的評估 rubric。

**可以接到哪**：

獨立使用（這是整條流程的最後一步）

**AI 會問你**：

1. 你這條 workflow 會用到哪些系統？例如 ticket 系統、資料庫、Slack、Google Sheet、版本控制
2. 這些系統裡，哪些有官方 API 或現成 MCP，哪些你只能手動操作
3. 整條流程裡，哪幾個決策一旦做錯代價很高？例如碰錢、改權限、對外發送
4. 這條流程你希望多久跑一次、由什麼觸發

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 必記核心術語：①Mega agent ②默會知識（Tacit Knowledge）③Artifact（節點間傳遞的 JSON）④MCP（Model Context Protocol）⑤Human-in-the-loop checkpoint ⑥Process owner |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | 核心論點：模型已不是瓶頸，瓶頸是「人講不清楚」。解法是把 Human SOP 用四步（標準化→拆節點→迭代→接工具）拆成 agentic workflow。各概念關係：默會知識→第一版必翻車→所以要雙向開發迭代；拆節點→可 debug→才敢上 production |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維，看透策略底層邏輯 | 關鍵假設：①拆解的維護成本永遠低於整包重寫（未必，低頻流程可能反之）②讀者有「過去最滿意的成品」可供反推（新手或新流程沒有）③MCP 已成熟到能串多數企業系統（實務上覆蓋率仍有限）。未論及的前提：何時「不該拆」正文幾乎略過 |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力，將理論轉為行動 | 立即可執行：①挑一份手上最煩、最高頻的流程（如週報、客訴分類），跑 Prompt 1 SOP Triage 評分 ②把該流程的 3-5 份「最滿意成品」找出來，跑 Prompt 4 反推默會判斷規則 ③在最高風險節點（碰錢／改權限／對外發送）設一個 HITL checkpoint |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡，在不確定的情境中做出最佳選擇 | 本文「拆成 pipeline」vs「mega agent 整包」vs「傳統 RPA／規則引擎」三者取捨：pipeline 在可觀測性與可修復性勝出，但前期設計成本高；mega agent 適合一次性探索；RPA 適合零判斷、完全固定的流程。何時選 pipeline：高頻＋中等判斷依賴＋輸出需一致 |

### 分析型追問（Socratic Follow-up）

- **澄清**：本文的「獨立節點」要獨立到什麼程度才算夠？節點切太細會不會反而讓接縫（JSON artifact）的維護成本超過拆解的好處？
- **假設**：「從成品反推默會知識」假設你手上有夠好、夠多的成品 — 若這是一條全新流程、根本沒有歷史成品，這個方法還成立嗎？
- **證據**：作者用「四十小時調委派規則仍撞牆」「客戶兩個月 SOP 上線即垮」當證據，但這些是軼事（anecdote）。有沒有量化數據支持「拆解後一致性顯著提升」？
- **觀點**：若站在反對者立場 — 隨著模型 context window 與推理能力持續變強，「整包丟 mega agent」會不會在兩三年後反而變成對的做法，讓今天精心拆解的 pipeline 變成過度工程？
- **後果**：若全公司都把流程拆成 workflow，12 個月後是否會出現「workflow 債」 — 大量過時、無人維護的 SOP 與 JSON schema，反而比當初的混亂更難治理？

### 方案批判三問（Critical Evaluation）

> [!warning] 本內容屬「做事方法／流程設計」類，加入方案批判三問。

1. **最大的風險是什麼？** — 在高風險節點（碰錢、改權限、對外發送）若沒設好 human-in-the-loop checkpoint，一條「穩定一致」的 workflow 反而會**穩定地、一致地、自動地**把同一個錯誤放大執行 N 次。一致性是雙面刃：對的事一致地對，錯的事也一致地錯。
2. **什麼情況下會失敗？** — ①低頻或一次性流程：拆解的形式化成本 > 收益 ②全新流程沒有歷史成品：Tacit Knowledge Extractor 的「反推」無素材可用 ③判斷依賴度極高且情境高度發散的流程（如創意、談判）：再多 MUST/SHOULD/MAY 也 cover 不完，硬拆只是把模糊偽裝成結構 ④組織不接受「先求一致、暫不全自動」的期待落差時，專案會在心理上被判定失敗。
3. **有沒有更好的替代方案？** — 對**零判斷、完全固定**的流程，傳統 RPA／規則引擎更穩更便宜，不需要 LLM；對**一次性探索任務**，直接用 mega agent 反而省事（反正不重複跑、不需可維護性）。本文方法的最佳適用區間是**「高頻 × 中等判斷依賴 × 輸出需一致」**這個交集 — 落在交集外時應選替代方案。

---

## 我的心得（My Takeaways）

- **最值得內化的一句**：「先求一致，再談全自動。」這把多數人對 AI 自動化的過高期待校準回務實的起點 — 一個穩定的及格初稿，價值遠大於追求一步到位的全自動而最終放棄。
- **可直接套到個人知識庫流程**：這篇講的「Human SOP → 拆節點 → JSON artifact → 迭代」其實正是我自己 `kb-create` skill 的設計哲學 — 把「讀文章→分類→寫筆記→交叉連結→更新索引」拆成獨立步驟，每步可單獨除錯。本文給了我一個檢視框架：哪些步驟其實藏著我說不出口的判斷（例如「分類」與「挑哪些舊筆記回填」），值得用 Tacit Knowledge Extractor 反推外化。
- **對 connsys-jarvis 多 agent 設計的啟發**：「節點間靠 JSON artifact 而非 agent 通靈」這條原則，正好對應我在設計裡用 Gerrit Bus + Shared Ref Repo 做為節點間傳遞媒介的思路 — 共享狀態要顯式、可檢查，不能靠 agent 之間隱式傳遞。
- **保留的懷疑**：作者對「何時不該拆」著墨太少。我會把「先判斷該不該拆」（Prompt 1 的精神）當成比四步法本身更前置、更重要的一關。

## 待補充（Open Questions）

- 作者稱「Anthropic 在 2025 年初把 MCP 捐給 Linux Foundation 底下的 Agentic AI Foundation」 — 這個機構名稱與捐贈時間我無法在本次作業中查證，是否屬實？（建議搜尋：`MCP Linux Foundation Agentic AI Foundation Anthropic donation`）
- 文中引用的 Terminal-Bench 分數「從六七成飆到八成以上」具體是哪個榜單、哪些模型、哪個時間點？（建議搜尋：`Terminal-Bench leaderboard coding agent score`）
- 「節點間用 JSON artifact 傳遞」在實務上如何做 schema 版本管理？當上游節點輸出格式改變時，下游節點如何不靜默崩潰？（建議搜尋：`agent pipeline JSON schema versioning contract`）
- ServiceNow／IBM／AWS 「內部早已用 agentic workflow 取代規則引擎」 — 有沒有公開的 case study 或白皮書佐證這個強斷言？（建議搜尋：`ServiceNow agentic workflow enterprise case study 2025`）
- 五步 Prompt 工具包是否有公開的範例輸出（example run），可以對照看「跑完長什麼樣」？（建議搜尋：`garytalksstuff SOP pipeline prompt example output`）
- 對「判斷依賴度極高」的創意／談判類流程，本文方法的適用邊界在哪？是否存在反例顯示硬拆會降低品質？

## 相關連結（Related）

- [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] — 同樣主張人才價值轉向「設計與治理系統」，呼應本文 process owner 的角色升級論
- [[2026-03-31-AI-WORKFLOW-AGENTS-SKILLS-STANDARDS]] — 把「每個節點包成 skill」的具體三層式架構（Agents／Skills／Standards）
- [[2026-05-04-STANFORD-AUGMENTING-LLMS-FIVE-TECHNIQUES-AI-BUILDER-TOOLKIT]] — decomposition 是 augmenting LLM 的核心技巧，與本文「拆成節點」同源
- [[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]] — 「看了教程仍做不對」本質就是默會知識未外化，與本文死結互為印證
- [[2026-04-09-AI-ONE-PERSON-COMPANY-KARPATHY-OBSIDIAN-KB-OPENCLI]] — 一人公司如何把判斷沉澱進系統，呼應本文「經驗留在 workflow 而非腦袋」
- [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]] — 以 5 個 Agent Skills 落地的完整工作流走查，是本文方法論的實作對照
- [[2026-07-02-CONTEXT-CONVERTER-17-VOICE-PROMPTS-TURN-TALK-INTO-WORK-OUTPUT]] — 同作者 Gary Chen 的另一組配套 prompt 工具包，可對照兩者的 prompt 設計手法

## References

- [Patreon 原文：把最無聊的重複流程交給 AI](https://www.patreon.com/posts/ba-zui-wu-liao-159637740)
- [配套五步 Prompt 工具包（garytalksstuff.com）](https://garytalksstuff.com/20260525_sopflow_promptset_1)
