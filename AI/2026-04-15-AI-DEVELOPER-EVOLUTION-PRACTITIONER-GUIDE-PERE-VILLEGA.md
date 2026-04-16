---
title: "AI 開發者演化：實踐者指南全系列（Pere Villega 11 章合輯）"
date: 2026-04-15
category: AI
tags:
  - "#ai/claude-code"
  - "#ai/agentic-development"
  - "#productivity/workflows"
  - "#devtools/lsp"
  - "#ai/context-engineering"
source: "https://perevillega.com/series/ai-developer-evolution/"
source_type: article
author: "Pere Villega"
status: notes
series_chapters: 11
series_date_range: "2026-03-15 ~ 2026-04-15"
links:
  - "[[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]]"
  - "[[2026-02-12-EVALUATING-AGENTS-MD-CONTEXT-FILES-HELPFUL-FOR-CODING-AGENTS]]"
  - "[[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]]"
  - "[[2026-03-16-THE-SHORTHAND-GUIDE-TO-EVERYTHING-AGENTIC-SECURITY]]"
  - "[[2026-03-25-ENGINEERS-FUTURE-MULTI-AGENT-ERA-STEVE-YEGGE]]"
---

## 摘要（Summary）

本筆記整合 Pere Villega 的《AI Developer Evolution》系列 11 篇文章（2026-03-15 至 2026-04-15），是一本從**懷疑到多代理人協作**的完整實踐指南。作者從個人演化的 11 個階段切入，剖析三大關鍵轉折點（控制權放手、一對多管理、超越人類極限），並深入實務細節：CLAUDE.md 寫法、記憶系統、上下文工程（Context Engineering）、工作流程、遠端部署（Hetzner + Tailscale + Cloudflare Tunnel），以及他開源的 `claude-templates` 起始範本。

系列核心主張可以用兩句話概括：
1. **程式碼變廉價了，系統定義才是資產**——停止為程式碼產量調校，改為系統規格調校。
2. **AI 是外骨骼（Exoskeleton），不是同事（Coworker）**——它放大你既有能力，不是取代你。

> [!important] 閱讀建議
> 11 章按順序閱讀效果最好，但若時間有限，最具實作價值的是第 5、7、9、10、11 章。第 1、2、3 章是思維框架，讀完能省下大量時間重新發明輪子。

---

## 系列章節總覽

| 章 | 標題 | 日期 | 核心 |
|----|------|------|------|
| 1 | AI 輔助開發的實踐者指南（導論） | 2026-03-15 | 11 階段演化與 3 大轉折點 |
| 2 | 程式碼變廉價了，這改變了一切 | 2026-03-16 | 90% 技能歸零，10% 技能 × 1000 |
| 3 | AI 是外骨骼，不是同事 | 2026-03-17 | 生產力悖論與多倍放大器 |
| 4 | Claude Code 第一天 | 2026-03-18 | 環境設定、沙盒、LSP |
| 5 | 決定 AI 工作流成敗的那一份檔案 | 2026-03-23 | CLAUDE.md 最佳實踐 |
| 6 | 打造跨 Session 存活的代理人記憶 | 2026-03-24 | 三層記憶系統 |
| 7 | 上下文工程：取代提示工程的新技能 | 2026-04-08 | 0.0002% vs 99.99% |
| 8 | 唯一有效的工作流 | 2026-04-13 | Spec → Plan → Implement |
| 9 | 上下文視窗的實戰求生術 | 2026-04-15 | 1M 不等於可用 1M |
| 10 | 在 Hetzner 上跑 AI 代理人 | 2026-04-02 | 遠端部署完整方案 |
| 11 | Claude Code 使用者的主觀起點 | 2026-04-12 | claude-templates 範本庫 |

---

# 第 1 章：AI 輔助開發的實踐者指南（導論）

**發布日期**：2026-03-15 | 5 分鐘閱讀

作者觀察到開發者對 AI 的論述分成兩個極端：一派認為代理人（Agent）即將取代開發者；另一派則全盤否定這項技術。作者以中間路線出發，分享從懷疑到每日使用代理人工具的實務經驗。

關鍵洞察是：「**從『這只是自動補全（Autocomplete）』到『我正在用多個代理人並行出貨』的旅程**」並非平滑漸進，而是充滿尷尬的過渡。

## 演化的 11 個階段

1. **否認（Dismissal）**——初次嘗試失敗後，把 AI 視為泡沫炒作
2. **恐懼（Fear）**——看到同事用它快速出貨，觸發職涯安全感
3. **試探性實驗（Tentative Experimentation）**——用 Copilot 做 Tab 補全與偶爾聊天查詢
4. **帶輔助輪的代理人（Agent with Training Wheels）**——啟用 IDE 代理人但每個動作都要批准
5. **YOLO 模式**——解除批准限制，改為審查 diff 而非手寫程式
6. **跳出 IDE**——用 CLI 代理人；IDE 本身變成瓶頸
7. **多代理人（Multi-agent）**——管理 3 到 5 個並行實例
8. **自主循環（Autonomous Loops）**——代理人在夜間針對成功標準自行迭代
9. **群集管理（Swarm Management）**——手動協調 10 個以上代理人
10. **編排器建造者（Orchestrator Builder）**——打造工具來管理代理人群集
11. **「駭客任務」時刻（"The Matrix" Moment）**——透過委派更快打造任何東西

## 三大關鍵轉折點（Fulcrums）

### 轉折點 1：放手控制權（第 4 → 5 階段）

這是信任的門檻，多數開發者卡在這裡。心理上從「AI 協助我」轉為「我監督 AI」，直接衝擊開發者身為程式碼作者的身份認同。「**這感覺像放棄，即使它實際上是進步**」。

### 轉折點 2：一對多（第 6 → 7 階段）

這是營運面的挑戰：瓶頸從代理人變成了開發者本人。成功關鍵是設計約束——測試、linter、CI 管線、成功標準。作者引用 Geoffrey Huntley 的「**反壓（backpressure）**」一詞來描述：驗證工作但不逐行審查。

### 轉折點 3：人類極限（第 9 → 10 階段）

手動管理 10 個以上代理人不可持續。開發者必須從軟體工程過渡到營運與上下文工程（Context Engineering），整個技能組需要根本性地重塑。

## 共通模式

每一個轉折都是「接受人類參與度降低」：先放棄寫程式、再放棄程式碼審查、最後放棄協調責任。

---

# 第 2 章：程式碼變廉價了，這改變了一切

**發布日期**：2026-03-16 | 9 分鐘閱讀

Kent Beck（極限程式設計 XP 與 TDD 之父）於 2023 年 4 月發推文：

> 「**我 90% 的技能剛歸零。10% 的技能價值漲了 1000 倍。**」

2025 年 11 月的 Podcast 中他補充，這 10% 具體是：「擁有願景、設定達成願景的里程碑、追蹤設計以維持或控制複雜度等級——這些能力現在的槓桿比『知道 Rust 的 & 和 * 和括號該放哪』高太多了。」

## 350K 美元的週末專案

Paul Ford（Postlight 前執行長）在 Anthropic 送 Pro 訂戶 $1000 Claude Code 額度時，決定每天燒 $100 在擱置十年的個人專案上。Ford 當過多年軟體成本估算師，所以能給出真實數字：

- 將 1999 年自創的「極度晦澀難懂的資料格式」舊部落格移植到新 CMS
- 建立帶 TypeScript 前後端的時間軸視覺化專案
- 寫出 OwnCast 的功能複刻版
- **總花費：約 $150**

> 「在 Claude Code 寫程式，就像在玩塔麻可（Tamagotchi），只是這隻塔麻可是 40 人的工程與產品團隊，而且它不會產出小小的數位便便，而是會部署後端有資料庫、有型別安全 API 介面、有 React 前端的 Web 應用。」——Paul Ford

以 2021 年的零售費率，光是資料集轉換一項就需要 350,000 美元——一個產品經理、一個設計師、兩個工程師（含資深）、4 到 6 個月的設計、寫程式、測試，加上維護。Ford 一個人週末晚上搞定，只用到剩下的促銷額度。

## 塑造一切的那個限制

程式碼過去一直都貴。幾百行乾淨且有測試覆蓋的程式碼，對多數開發者來說要花一整天。這不是小事，它是塑造我們產業所有習慣與制度的核心限制。

為什麼要估故事點？因為開發者時間貴。為什麼要排 Backlog 優先級？因為無法全做，必須選值得的。所有的——**計畫、估算、功能優先級、程式碼審查、架構審查、衝刺規劃——都是「寫程式是昂貴部分」這個前提的下游產物。**

代理人把這個成本徹底打穿地板了。

Kent Beck 在 2025 年 9 月的〈Programming Deflation〉一文中主張：**便宜的程式碼解鎖潛在需求**。有數百萬個問題因為軟體解方成本超過價值而沒人去解；當成本暴跌，這些問題變得值得解。世界上的軟體總量會上升，不是下降。

## 「好程式碼」仍然有代價

免得有人以為作者在說品質不重要：它比以往更重要。

Simon Willison 對「好程式碼」的定義：**能動、我們知道它能動、解決對的問題、優雅處理錯誤、簡單最小、有測試保護、文件適當、允許未來變更**，以及相關的 `-ilities`：可存取性、可測試性、可靠性、安全性、可維護性、可觀察性、可擴展性、可用性。

代理人可以協助完成上述大部分，但開發者仍需負責確保產出實際上是好的。LLM 的**隨機性（Stochastic nature）**意味著不能盲信輸出：測試通過不代表是好測試，程式碼編譯不代表正確。

弔詭的是，這正是 LLM 在程式碼領域比其他領域強大的原因——我們有編譯器（要嘛編譯過，要嘛過不了）、有測試套件、有型別系統、linter、靜態分析。軟體有多數其他領域沒有的驗證工具。

但驗證要先知道「正確長什麼樣」——而這正是那 10% 技能（× 1000 倍）所在之處。

## DORA 報告的矛盾數據

Google 2024 年的 DORA 報告揭露反向的弔詭：
- 75% 的開發者認為自己更有生產力
- 但 AI 採用率每增加 25%，交付速度下降 1.5%，系統穩定性下降 7.2%
- 39% 的受訪者表示對 AI 生成的程式碼「幾乎沒有信任或完全沒信任」

**工具讓我們感覺更快，數據顯示我們並沒有**——除非我們改變工作方式。

## 釘槍類比（Nail Gun Analogy）

> AI 是釘槍。在不熟練者手上很危險，在專業者手上能大幅加速。而最後，大家只在乎那個位置有一根釘子就好。

使用者不在乎你的 SonarQube 分數、你用函式式還是物件導向、六角形架構還是分層架構、Rust 還是 TypeScript。他們在乎 App 做了該做的、夠快、不遺失資料、需要時能用。

## 系統才是資產（The System Is the Asset）

以 C2C 二手交易市場為例。系統是什麼？不是語言、微服務、部署拓撲。系統是：
- **SLA**：延遲、可用性
- **資料**：稽核軌跡、帳戶、交易紀錄
- **合約**：什麼進去、什麼出來
- **不變量（Invariants）**：每個商品每個用戶只能出一個價、每個用戶最多上架 N 件

**如果這些定義都完備，你可以重造這個系統無數次——不同工具、架構、團隊、代理人——用戶都不會察覺。**

## 思維轉變

使用 AI 代理人所需的技能組，結合了**產品經理**與**開發團隊經理**。你需要知道要建什麼、為什麼重要、「完成」長什麼樣、如何驗證結果。要指定**結果（outcomes）而非實作（implementations）**——宣告式開發（declarative development）勝過指令式微管理（imperative micromanagement）。

試圖微管理代理人輸出的開發者會受苦；學會指定、驗證、迭代的開發者會茁壯。那 10% × 1000 倍是**判斷力、規格化、驗證**。那 90% 歸零的是**打字**。

> 「停止為程式碼產量優化，開始為系統定義優化。」

截至 2026 年初，**GitHub 約 4% 的 commits 由 Claude Code 單獨提交**，而且只會增加。

---

# 第 3 章：AI 是外骨骼，不是同事

**發布日期**：2026-03-17

## 生產力悖論（Productivity Paradox）

2025 年一項研究發現，使用 AI 工具的開發者比沒用的慢 **19%**，但自認為快了 **24%**——感知與現實之間有 43 個百分點的落差。

METR 研究（16 位資深開發者、246 個真實任務的隨機對照試驗）揭示：這個減速**不是 AI 本身造成**，而是未被改造的工作流造成。研究顯示「用 AI 寫程式認知負擔較低，讓人更容易恍神或滑 Slack。」開發者感覺每單位活躍工作更快，但總時鐘時間反而增加。

## J 曲線與適應

19% 的減速代表典型的 **J 曲線生產力低谷**——任何重大工具採用都會經歷。早期數位相機對老手攝影師不如底片、早期汽車輸給馬匹。為不同工作流優化的工具，初期一定會產生抵消速度增益的摩擦。

METR 2025 年後續研究估算**加速 18%**——戲劇性的反轉。但值得注意：開發者拒絕參與無 AI 對照組，顯示選擇偏誤。一位受試者說：「我真的很愛用 AI！」另一位承認「徒手做就像一整個城市要走路，因為已經習慣搭 Uber。」

## 倍增器論（Multiplier Thesis）

AI 作為**倍增器（multiplier）**而非自主代理人發揮作用。

> **深度領域知識 + 強判斷力 + 清晰思考**，被 AI 放大後產生變革性輸出。
> **模糊指令 + 無法評估回傳**，產生聽起來很自信的垃圾——而且規模放大。

真正的差異化來自專業。一位有 15 年經驗的採購主管 30 秒內發現兩家「供應商」其實是同一母公司的子公司——這知識存在他對 2019 年併購案的記憶中，AI 無法存取。

## 為什麼「外骨骼」這個比喻貼切

Ben Gregory 的**外骨骼（Exoskeleton）框架**更好地解釋為何開發者無法回頭到 AI 前的工作流：

- Ford 的 **EksoVest** 在製造業實現 **83% 傷害下降**，工人仍每天做 4,600 次過肩舉
- **Sarcos Guardian XO** 提供 **20:1 力量放大**：「100 磅感覺像 5 磅」

外骨骼不取代人類，它**放大既有能力**，讓人能以更少疲勞做更多持續產出。AI 同理：當開發者不用把心力花在樣板程式、commit 訊息、格式化上時，創造性判斷工作（真正的瓶頸）就有了容量。

## 認知負債（Cognitive Debt）

Margaret-Anne Storey 在 2026 年 2 月提出**認知負債**：儘管程式碼乾淨，**共享理解（shared understanding）卻在流失**。一個學生團隊用 prompt 生了數週的功能，到第 7-8 週卻無法做簡單改動，因為「沒人能解釋為什麼做了那些設計決策。」

Simon Willison 類似經驗：接受大型 AI 生成改動卻沒完整理解，讓他「在一座自己曾熟悉的城市裡改用 GPS 導航。」

Martin Fowler 的觀察：「**開發者體驗（Developer Experience）與代理人體驗（Agent Experience）的范氏圖是一個圓**。」改善人類理解的做法（模組化、命名、文件）同時也優化代理人效能。**程式碼品質投資不與 AI 輔助對立，它是前提。**

## Mitchell Hashimoto 的三要素

有意義的工具採用必然經歷：不效率 → 適當 → 發現工作流。他的突破來自兩次手動重製 commits，然後找出三個要點：

1. 把 Session 切分為獨立、清晰、可執行的任務
2. 把模糊需求分為**規劃**與**執行**兩階段
3. 給代理人驗證方法——它們通常能自行修復錯誤

關鍵補充：「**知道什麼時候不該伸手找代理人**，同等重要。學會這個分辨是一半的戰鬥。」

## 起點：最難的問題

從最難的問題開始，不是最簡單的。簡單任務什麼也教不會；困難問題強迫你明確表達上下文——這才是真技能。

> 「在真實工作上每天花 15 分鐘處理一個真實問題，建立起的直覺比任何課程、教學、Twitter 串要快。」

---

# 第 4 章：Claude Code 第一天

**發布日期**：2026-03-18

多數人第一次用 AI 代理人的體驗很糟，不是代理人不好，而是**設定不對**。作者看過太多人裝了 Claude Code、在家目錄開 Terminal、然後納悶為什麼代理人讀了 `.env` 還輸出平庸結果。本章提供設定檢查清單。

## 帳號選擇

三條路：
- **Claude Pro**：訂閱有使用上限。便宜方案限制極重，容易把 token 燒光；升級高階方案成本 5-10 倍
- **API（按 token 計費）**：重度使用或並行 Session 時適合。Requesty 值得評估（跨供應商的 token 成本優化器）
- **免費方案警告**：「不要從免費方案開始然後依此判斷技術好壞。寧願編列預算用 API。」

## 隔離第一（Isolation First）

這節是為了嚴重安全理由放在前面。**每一個代理人 Session 都應跑在容器或隔離 VM 中，沒有 host 檔案系統掛載、環境變數中沒有正式環境 token。**

### 安全疑慮

一個能存取 `.ssh` 金鑰、`.aws` 憑證、`.kube` 設定、shell 設定的代理人，風險極大。Trail of Bits 已記錄過：代理人讀取**被構造過的 log 檔**可產生外洩憑證到外部伺服器的腳本。

### 兩層防線

Trail of Bits 建議：
- **第一層**：`settings.json` 的 deny 規則，阻擋讀取敏感路徑（SSH 金鑰、雲端憑證、套件登錄 token、git 憑證、shell 設定、macOS keychain、加密錢包）
- **第二層**：`/sandbox` 指令在 OS 層級強制規則——macOS 的 Seatbelt 或 Linux 的 bubblewrap

> [!warning] 關鍵：沒有 `/sandbox`，deny 規則只擋 Claude 的 Read 工具。像 `cat ~/.ssh/id_rsa` 這樣的 Bash 指令仍然可執行。

### 容器選擇

- **DevContainers**：不掛載 host，設 `enableNonRootDocker: true`。Anthropic 官方推出 `ghcr.io/anthropics/devcontainer-features/claude-code:1.0`
- **devc**（Trail of Bits CLI）：`devc .` 安裝範本，`devc shell` 進入容器
- **dropkit**（Trail of Bits）：自動化在 DigitalOcean 開拋棄式 droplet，附 Tailscale VPN
- **Codespaces**：隔離好、筆電不用一直開機。但不支援 `~/.claude/CLAUDE.md`，首次啟動慢
- **VPS 選項**：£10/月的便宜 VPS 配 tmux 持久 Session，任何裝置 SSH 進去都能工作
- **Lima/Colima 警告**：Lima 預設範本以唯讀方式掛載 host 路徑，配上 `--dangerously-skip-permissions` 就是安全風險

## 原生沙盒（Native Sandbox）

2025 年中以來，Claude Code 內建沙盒——Seatbelt（macOS）或 bubblewrap（Linux）。輸入 `/sandbox` 啟用。

**關鍵指標**：內部使用中，沙盒讓權限詢問減少 **84%**。

邊界：
- **檔案系統隔離**：寫入限於工作目錄；讀取不限（除明確 deny 的路徑）
- **網路隔離**：僅連線到核可的 domain

所有子行程繼承這些限制。啟用沙盒時，auto-allow 模式執行沙盒內的 Bash 指令不再詢問，而邊界違規會觸發通知。

沙盒不取代高風險情境的容器隔離，但提供「**80% 的安全效益、5% 的設定成本**」。

## Terminal 設定

- **Ghostty**：原生 Metal GPU 渲染，不卡頓；內建分割面板（Cmd+D）
- **Session 管理**：tmux 或 zellij 做持久 Session
- **通知**：開系統通知讓 Claude 要輸入或任務完成時知道。ntfy.sh 可推播到手機
- **語音**：「**說話大概比打字快三倍，而且口述的 prompt 明顯更詳細**」——wisprflow.ai，Claude 也內建 `/voice` 指令

## 2 分鐘的 LSP 升級（最高槓桿）

這是單一最高槓桿的設定變更。

**沒有 LSP**：Claude 用文字搜尋（Grep、Glob、Read）導航 codebase。找常見符號如 `User` 可能回傳 847 個匹配橫跨 203 個檔案，耗時 30-60 秒與大量 token。

**有 LSP**：同樣查詢在約 **50ms 內回傳精確檔案與行號**，**100% 準確**。

**Context 視窗節省巨大**：與其讀幾十個檔案找定義，Claude 只需讀一個檔。

**自我修正編輯**是殺手級功能。每次編輯後，語言伺服器推送診斷（型別錯誤、缺少 import、未定義變數），Claude 同一個回合立刻修復。

### LSP 設定

**步驟 1**：在 `~/.claude/settings.json` 加：

```json
{
  "env": {
    "ENABLE_LSP_TOOL": "1"
  }
}
```

也在 shell profile 加 `export ENABLE_LSP_TOOL=1` 作為備援。

**步驟 2**：安裝對應語言伺服器：
- Python：`npm i -g pyright`
- TypeScript：`npm i -g typescript-language-server typescript`
- Go：`go install golang.org/x/tools/gopls@latest`
- Rust：`rustup component add rust-analyzer`

**步驟 3**：安裝並啟用 plugin：
```
claude plugin marketplace update claude-plugins-official
claude plugin install pyright-lsp
claude plugin list  # 驗證啟用
```

**步驟 4**：重啟 Claude Code。

在 CLAUDE.md 加上以下推一把：

```
### Code Intelligence
Prefer LSP over Grep/Glob/Read for code navigation:
- goToDefinition / goToImplementation to jump to source
- findReferences to see all usages across the codebase
- hover for type info without reading the file
After writing or editing code, check LSP diagnostics before moving on.
```

## Token 監控

Token 是你的貨幣。對話長度驅動成本——每次新請求都送整段先前對話，**不是線性成長**。

用 **ccstatusline** 追蹤 token 消耗與 Session 重置。定期跑 `/context` 評估剩餘空間。工具、MCP、CLAUDE.md 都算在內。**MCP 是動態載入不是啟動時載入**，這個陷阱可能讓 Session 看似寬裕、某個 MCP 載入後瞬間吃掉一半剩餘 context。

## 新專案檢查清單

寫任何 prompt 前先確認：
- **MCP 評估**：哪些 MCP 會幫忙（Postgres、SQLite、Slack、Honeycomb 等）。每個 MCP 光存在就吃 context token
- **CLI 工具可用性**：非通用的工具在 `CLAUDE.md` 列出讓代理人知道
- **DevContainer / 隔離設定**：確保機密只作用在開發環境
- **CLAUDE.md 存在**：最近測試建議聚焦在重要且非顯而易見的資料
- **測試框架可用**：「代理人無法驗證自己的工作，品質會急遽下降。給它檢查機制可提升品質 2-3 倍」

## 不要安裝什麼

Claude Code 生態活躍到不行。抗拒安裝所有看起來很讚的東西。

**每個 skill、MCP、設定檔都在吃 context 視窗。** 裝新東西後跑 `/context` 評估衝擊。SuperClaude 這類工具裝完可能剩不到 60k token——「**等於沒開始工作就已經少了 75% 的桌面，上面堆滿沒打開的參考書。**」

## 從最少開始

「**最好的設定是你了解每一塊為什麼在那裡**。」

---

# 第 5 章：決定 AI 工作流成敗的那一份檔案

**發布日期**：2026-03-23

CLAUDE.md 是 Claude Code 在每個 Session 開始時讀取的專案特定指令與上下文的 markdown 簡報文件。作者形容：「**你交給新團隊成員第一天看的簡報，但這個新人失憶，每天早上都要重看一次。**」

## 反對自動生成的理由

引用 ETH Zurich 研究與 Addy Osmani 分析：`/init` 自動生成的 AGENTS.md 反而**損害代理人效能並增加約 20% 成本**。

關鍵發現：
- LLM 生成的上下文檔案**降低任務成功率 2-3%**、成本上漲 20% 以上
- 開發者親寫的檔案**提升成功率約 4%**、成本最多上漲 19%
- 人類撰寫的 AGENTS.md 讓中位時鐘時間下降近 **29%**
- 只有當 repo 完全沒文件時，LLM 生成才提升 2.7%

關鍵洞察：「**自動生成的內容不是沒用，是冗餘。代理人讀 repo 就能發現全部。**」

## 最小主義原則

CLAUDE.md 每一行都要通過這個測試：**代理人讀 code 能自己發現嗎？能的話，刪掉。**

**應該放什麼**：
- 非標準工具偏好（「用 `uv` 不用 `pip`」）
- 任務完成程序（「一律用 `--no-cache` 跑測試」）
- 重構警告（「不要把 auth 模組重構成標準 Express middleware」）
- 棄用告示（「`legacy/` 目錄已棄用但被正式模組引用」）

**不應該放什麼**：
- 專案結構描述（「這是 monorepo，套件在 /packages」）
- 標準指令（「以下指令跑測試與 lint」）

給代理人 500 行規格，它會當成「**合規檢查清單，而不是概念框架**」。研究建議實務閾值 200-300 行，超過效能急跌。

## 三層 CLAUDE.md 階層

- **全域**（`~/.claude/CLAUDE.md`）：每個 Session 都載入。極簡——個人偏好、工作風格、參考檔索引。產品經理 Teresa Torres 的只有幾行
- **專案**（repo 根目錄）：專案特定架構決策、已知陷阱、無法從 codebase 發現的 bash 指令
- **子目錄**：僅當 Claude 存取那些目錄時載入。容易重複通用資訊

Claude Code 從工作目錄向上遞迴載入所有 CLAUDE.md。這層疊代表**污染會跨檔案相乘**，簡潔更關鍵。

## 該放什麼

1. **非標準指令**：`cargo clippy`、`pnpm lint`、`ruff check`——只在偏離慣例時寫。數據顯示提到 `uv` 會讓代理人每任務平均用 1.6 次；不提就不到 0.01 次
2. **完成步驟**：一個綜合腳本 `runAll.sh` 比列出各步驟更有效
3. **避免讀取的檔案**：大文件資料夾、產生的檔案、vendor 目錄
4. **Log 存取指令**：如何取最後 20 行 log，或建 `tail-logs` 指令
5. **非顯而易見的慣例**
6. **工作流圖**：用 Graphviz/dot 標記——Claude 對此處理特別好，「**比散文更不歧義**」

## 團隊實踐（Boris Cherny 分享）

Boris Cherny（Claude Code 作者、Anthropic Staff Engineer）表示團隊在 git 維護一份共享 CLAUDE.md，成員每週貢獻多次：

> 「**每次看到 Claude 做錯什麼，我們就加進 CLAUDE.md，這樣下次它就不會再犯。**」

複合式改善：每個修正預防未來 Session 重蹈覆轍。例：「絕不用 enum，永遠用 literal unions」系統性解決問題。

## CLAUDE.md 作為強制函數

這份檔也是 codebase 健康的診斷工具：
- **複雜指令** → 簡化工具，不是擴大文件。建合併步驟的腳本
- **代理人找不到資訊** → codebase 結構可能不好。重組而非加指令
- **工具使用有問題** → 那個工具可能不適合，找替代品

> Martin Fowler 的觀察適用：「開發者體驗與代理人體驗的范氏圖是一個圓。」

**理想的 CLAUDE.md 幾乎空白**——不是懶得投入，而是底層問題已修在 codebase 本身。

## 起點建議

從近乎空白的 CLAUDE.md 開始，只放一條指令：「在這個專案裡遇到任何讓你意外或困惑的，請用 comment 標記出來。」跑幾個 Session，記下 Claude 標的，能修的修在 codebase，剩下的才加進 CLAUDE.md。

> **多數代理人建議的新增內容，是 codebase 不清楚的指標。把它當診斷工具，不是指令手冊。**

---

# 第 6 章：打造跨 Session 存活的代理人記憶

**發布日期**：2026-03-24

Claude Code 每個 Session 都從零開始。對管理多個專案的人，這不可持續。

## Teresa Torres 的三層上下文系統

### 第一層：全域 CLAUDE.md
`~/.claude/CLAUDE.md`，每個 Session 都載入。極短，只包含：
- 個人工作偏好
- 規劃方式
- 回饋偏好
- 參考上下文檔的索引

原則：保持最小。不必要的資訊會在不相干任務上爭注意力。

### 第二層：專案 CLAUDE.md
每個專案資料夾有自己的 CLAUDE.md。這分離避免 Torres 稱的「**上下文污染（Context Contamination）**」——不相干資訊干擾任務完成。

### 第三層：參考上下文檔
小而聚焦的 markdown 檔（業務檔案、受眾分眾、產品細節），**按需載入**，由全域檔的索引引導。

## 停下來捕捉規則（Stop-and-Capture Rule）

Torres 最可執行的原則：**每次你要對 Claude 重複解釋之前解釋過的內容時，暫停並存檔。** 不要另外排時間寫文件，讓上下文在工作中有機生成。

## Session 結束儀式

Torres 在 Session 結束時問 Claude：
> 「你學到了哪些關於和我合作的事？什麼該加進上下文檔？」

這維持資訊品質，並避免商業細節塞爆 CLAUDE.md。

## claudecode-kb 實作（Patrick Zandl）

以檔案為主、git 版控的結構：

```
my-knowledgebase/
├── preferences/
├── patterns/
├── snippets/
├── troubleshooting/
├── projects/
├── memory/
└── scripts/
```

**關鍵洞察**：Zandl 發現原本 170 行的 CLAUDE.md 中段效能惡化。研究《**Lost in the Middle**》（Liu et al., TACL 2024）揭露 LLM 呈現 **U 型注意力**。解方：CLAUDE.md 減到 40 行，當成**路由器**指向詳細指令檔。

### JSONL Session Log
專案含機讀格式 Session log（append-only）。避免 markdown 實作中意外改寫破壞先前資料。

### 情節記憶（Episodic Memory）
`memory/decisions.jsonl` 捕捉重大決策——日期、理由、考慮過的選項、結果——保留未來類似決策的上下文。

## 無壓力起步

1. **漸進式建立**——不要一次蓋大系統，持續維護
2. **最小可行結構**——先分工作與個人資料夾
3. **像委派者思考**——如果你不願把任務交給沒解釋過的新員工，Claude 也一樣需要上下文

## 每週維護

Zandl 建議每週花 15 分鐘檢視知識庫，刪除陳舊、補齊缺漏。**過時上下文造成的問題比缺少上下文還多。**

## 核心洞察

**記憶是設計問題（Memory is a design problem）。** Claude Code 每個 Session 預設白紙。問題不是「要不要建持久記憶」，而是「多刻意地建」。

---

# 第 7 章：上下文工程：取代提示工程的新技能

**發布日期**：2026-04-08

核心洞察：**你的 prompt 只占模型 context 視窗的 0.0002%，剩下 99.99%（CLAUDE.md、工具定義、對話歷史）才決定實際效能。**

## 四層框架

1. **提示工藝（Prompt Craft）**：清楚指令（必要但槓桿最小）
2. **上下文工程（Context Engineering）**：策劃 prompt 以外的一切（80% 的獲益）
3. **意圖工程（Intent Engineering）**：為自主代理人編碼目標與邊界
4. **規格工程（Specification Engineering）**：讓組織知識機器可執行

## 有效上下文包含什麼

「**上下文應聚焦 HOW**：標準作業程序、runbook、怎麼測試」——而非 WHAT。

具體要放：
- 開發流程與測試協定
- 架構決策紀錄（Architectural Decision Records, ADR）
- 領域知識與使命宣言
- API 綱要與設計模式

## 關鍵洞察：看不見的上下文

Michael Mueller 的研究揭露：「**從代理人角度，它拿不到的上下文等於不存在。**」Slack thread 裡的架構決策、團隊成員腦中的領域模型、沒寫下的慣例——對代理人全部不可見。

解方：**把所有關鍵知識版控在 repo 裡成為機器可讀文件。**

## 減少上下文需求

三種結構性方法最小化 context 視窗浪費：

1. **任務切小**——「加一個重試機制到 payment service」比「改進 payment 系統」需要的上下文少得多
2. **寫鬆耦合程式碼**——模組化架構讓代理人只讀相關檔案
3. **統一技術棧選擇**——一致的模式免去解釋變體的 token

## 規則 vs. 閘門（Rules vs. Gates）

關鍵區分：
- **規則（Rules）**是建議，代理人可以合理化地跳過
- **閘門（Gates）**是客觀條件，阻擋繼續

與其寫「記得讀 style guide」，改寫「**寫程式前 → 讀 style guide → 在 context 中確認 → 才能繼續**」。結合 Hooks（根據任務類型自動載入上下文）與 Gates（阻擋條件）創造可靠的上下文傳遞。

## XML 標籤很重要

「**XML 標籤與分隔符不是風格偏好**」，而是幫模型區分內容類型的**結構訊號**。把指令包在 `<instructions>`、範例包在 `<example>`，改善模型可靠性並減少混淆。

## 組織意涵

> 「**最會建上下文基礎設施的團隊，會從 AI 代理人獲得最好結果。**」

這代表從個人 prompt 優化轉為**組織知識管理**——把上下文當作程式碼處理：要版控、要文件、要維護。

---

# 第 8 章：唯一有效的工作流

**發布日期**：2026-04-13

## 開場故事

作者經驗：AI 代理人技術上完美實作了功能（編譯過、測試過），卻**做了完全錯的目標**。這事件說明根本原則：

> 「**如果你從水管喝水，限制不是水管能流出多少水。**」

## 核心論點

工程實踐在代理人時代**比以往更重要**。經典軟體工程紀律**以機器速度放大**好壞流程。與其發明新的 AI 專用工作流，最有效的路是**運用既有最佳實踐**。

## 推薦工作流

### 階段 1：規格建立（Specification Creation）
透過迭代問答與 AI 腦力激盪詳細需求，整理成 `spec.md`。**範圍管理關鍵**——餵系統可控、獨立的任務，而不是整個系統需求。

### 階段 2：任務切分（Task Breakdown）
把計畫切成小的邏輯增量。每個要剛好在 context 視窗內，且可獨立審查。

### 階段 3：帶驗證的實作（Implementation with Verification）
循序執行任務，把結果 commit。小 commit 易於審查與記錄。CI/CD、linter、型別檢查、測試套件建立**回饋迴路（Feedback Loop）**。

### 階段 4：上下文工程
提供完整上下文：高階目標、不變量、範例解方、低效做法的警告、相關文件。

## Boris Tane 的標註計畫法

1. **研究階段（Research Phase）**：深度檢視 codebase，產出 `research.md`
2. **規劃階段（Planning Phase）**：製作詳細 `plan.md`，含做法、程式碼片段、檔案路徑、權衡
3. **標註循環（Annotation Cycle）**：人類審查並**在計畫上行內註記**（1-6 輪）——**明確指令是「還不要寫程式」**
4. **實作階段（Implementation Phase）**：按詳細計畫機械式執行

## Jamon Holmgren 的夜班法（Night Shift Method）

白天寫規格（不用 AI），晚上代理人實作。這把標註原則推到邏輯極致——要求**能預期澄清需求的嚴格規格寫作**。

## 關鍵原則

- **階段分離**：研究、規劃、實作**在不同 Session**。研究吃大量 context；實作前清 Session 才有滿滿的 context
- **動手前先審**：總是挑戰產生的輸出。程式碼現在是**可拋棄的**，**規格與測試才是有價值的產物**
- **隨機性管理**：LLM 輸出非確定性，**重新生成的成本**遠低於出貨壞實作

## 關鍵洞察

> 「**紀律不在工具，而在抗拒直接跳到實作的衝動。**」

這個模式比 AI 更早存在，但在代理人輔助開發中變得越來越關鍵。

---

# 第 9 章：上下文視窗的實戰求生術

**發布日期**：2026-04-15

## 上下文的經濟學

理論上 **100 萬 token**，實務上差很多。載 MCP、skill、文件階層、保持對話歷史後，可用 context 快速縮水。研究顯示「**模型在 context 視窗超過某些閾值後會退化**」，變得不可靠。

每次互動成本比預期高。10 個 token 的查詢不是獨立的——它包含**整段先前對話加上回應**。後續查詢必須重傳所有過往交換，這是**二次方（quadratic）成長，不是線性**。

工具使用加重負擔。Web 搜尋結果、檔案讀取、MCP 輸出在 Session 中**永久累積**。

## 為什麼 Autocompact 很危險

Claude Code 的自動壓縮在約 95% context 用量時觸發，用語言模型摘要做**有損壓縮**。**關鍵失敗模式**：系統可能丟掉被判定為「與當前任務無關」的 CLAUDE.md 指令與架構限制。

> [!warning] 建議：**關掉 autocompact，手動用 `/clear`**。雖然繁瑣，但可避免關鍵系統指令在 Session 中途被靜默刪除。

## Context 長度等於效能

Anthropic 自家研究揭露效能會隨 context 成長惡化：

- Opus 4.6：256K tokens 時 91.9% → 1M 時 78.3%
- Sonnet：256K 時 90.6% → 1M 時 65.1%（25.5% 降幅）

**即使空間看似充足，可靠性也顯著下降。Sonnet 填到一半，資訊檢索就有約 20% 失敗機率。**

## Research → Plan → Implement 切分

最有效的 context 管理技巧是**存檔再清空**：

1. 徹底完成研究
2. 把發現與計畫存到硬碟
3. 執行 `/clear`
4. 重新載入計畫
5. 在完整 context 可用下實作

這避免重複傳遞研究 token，並在代理人失常時能復原。

## 子代理人（Subagents）：新鮮 context 是資源

子代理人拿**獨立的 context 視窗**，隔離吃 context 的操作（web 研究、文件閱讀、測試執行）。主編排器保持乾淨，只收到結果而非中間工具輸出。

限制：**子代理人不能呼叫子代理人**——只能一層深。

## LSP 作為 context 省錢王

LSP 整合大幅減少導航開銷——毫秒級回傳精確檔案位置與行號，不用在幾百個匹配中 grep。

額外好處：
- 編輯自我修正帶自動診斷
- 語意化參考尋找取代文字比對
- 消除重構時漏掉的使用處

**「LSP 設定是 Claude Code 工作流最高 ROI 的改進之一。」**

## Context Mode MCP

MCP 傳統上一次載入所有工具——光 GitHub MCP 每回合就送約 5,000 token。新工具如 Context Mode、Cloudflare 的 Code Mode **壓縮工具輸出**，並用簡化的「搜尋/執行」模式取代龐大的工具目錄。

## 每日實務紀律

- **關 autocompact**：存計畫到檔案後手動 `/clear`
- **選擇性載入 MCP**：只載當前任務需要的；優先用 CLI 替代
- **積極殺 context**：一個任務一個 Session；**Esc 按兩次**可 rollback
- **審計安裝**：裝任何 skill 或 MCP 後跑 `/context`，避免工作開始前就吃掉 50% 以上
- **復原選項**：Esc-Esc rollback 或 `/rewind` 優先於 `/compact`

## 大局觀

Context 是你「**最珍貴的資源**」——即使在 1M token 下，這根本上是**注意力問題**，不純粹是 token 問題。獲得最好結果的開發者**把 context 當有限預算**，**積極清理、強制存檔**。

這個紀律會轉移到規格寫作、repo 結構、人際溝通——**為思考者刻意策劃資訊，是普遍有用的技能**。

---

# 第 10 章：在 Hetzner 上跑 AI 代理人

**發布日期**：2026-04-02

## 為什麼要遠端

大家都建議代理人要沙盒化，但傳統 Docker + 掛載卷的設定常暴露 host 系統。解方直接了當：**用遠端機器開發**。Claude 的 `remote` 與 `dispatch` 擴充讓代理人可線上存取，讓這更實用。

作者整套設定涵蓋：**Hetzner VPS 開機 → 安全強化 → Tailscale + Cloudflare Tunnel 保護 → 挑對應的機型跑 Claude Code 多子代理人並行**。

## 為什麼是 Hetzner

Hetzner 是 VPS 市場性價比最好的，同規格下通常比 DigitalOcean、Linode 便宜 **30-50%**。即使 2026 年 4 月漲價 30-37%，仍是價值領先者。

### 機型選擇

- **CX 系列**（共享 Intel/AMD，僅歐盟）：CX23（2 vCPU, 4 GB, 約 €5/月）～ CX53（16 vCPU, 32 GB, €22.99/月）
- **CAX 系列**（ARM Ampere Altra）：**目前不建議**，比 Intel 等價版貴且 Docker image 支援有限
- **CPX 系列**（AMD EPYC，全球）：€5.99～€71.49/月；效能更好但貴
- **CCX 系列**（專用 AMD EPYC vCPU）：**消除噪鄰問題**；CCX33 €62.99/月（8 vCPU, 32 GB），CCX43 €125.49/月（16 vCPU, 64 GB）
- **專用伺服器（Dedicated）**：AX42（AMD Ryzen 7 PRO 8700GE, 64 GB DDR5 ECC, 2×512 GB NVMe）約 €54/月——**持續效能比雲端實例更好、更便宜**。Server Auction 拍賣甚至從 €30-50/月起

提醒：主要 IPv4 位址多收 €0.50/月；IPv6 免費但某些服務相容性差。

## 強化伺服器

**防禦縱深**：SSH 金鑰驗證、非 root 使用者、UFW 防火牆、fail2ban 防爆破、unattended-upgrades 自動更新。

作者提供生產就緒的 cloud-init YAML：
- 建立非 root sudo 使用者、SSH 金鑰驗證
- 安裝安全套件（fail2ban、ufw、unattended-upgrades）
- 強化 sysctl（禁 source routing、禁 ICMP redirects、開 TCP syncookies）
- fail2ban 設 3 次失敗就 ban 24 小時
- **建立 8 GB swap**（代理人 RAM 會爆——這是必需）
- 啟用 UFW，僅開 SSH
- 禁 root 登入、keyboard-interactive auth
- MaxAuthTries 設 2
- 禁 TCP forwarding、X11 forwarding、agent forwarding

> [!warning] Swap 是必需：「**代理人會暴衝 RAM**」，設 `vm.swappiness=10`——優先 RAM，允許溢出到磁碟。

同時使用 Hetzner Cloud Firewall（邊緣層）與 UFW（host 層）作為**冗餘防禦**。用 HetrixTools 監控需允許 ICMP。

## Tailscale

Tailscale 在你裝置間建立 **WireGuard 加密 mesh 網路**。Hetzner VPS 加入後，可用穩定 Tailscale IP 做 SSH，然後**把 port 22 對公網完全關閉**。

### 安裝

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
```

`--ssh` 啟用 Tailscale SSH，認證走身份提供者（不再依賴 SSH 金鑰檔）。MagicDNS 讓你用 `ssh deploy@machine-name` 連。

雲端初始化自動化：
```bash
runcmd:
  - ['sh', '-c', 'curl -fsSL https://tailscale.com/install.sh | sh']
  - ['tailscale', 'up', '--auth-key=tskey-auth-xxxxx', '--ssh']
```

### 防火牆設定

確認 Tailscale 能用後，鎖緊 UFW 只允許 Tailscale SSH：
```bash
sudo ufw delete allow 22/tcp
sudo ufw allow in on tailscale0 to any port 22 comment 'SSH via Tailscale only'
```

Hetzner Cloud Firewall 僅開 UDP 41641（WireGuard 直連）與 ICMP。

### ACL 設定

限制存取到打上 agents 標籤的機器：
```json
{
  "tagOwners": { "tag:agents": ["autogroup:admin"] },
  "acls": [
    { "action": "accept", "src": ["autogroup:admin"], "dst": ["tag:agents:*"] }
  ],
  "ssh": [
    {
      "action": "accept",
      "src": ["autogroup:admin"],
      "dst": ["tag:agents"],
      "users": ["<username>", "root"]
    }
  ]
}
```

另外還可用 **subnet routing**（多伺服器）與 **exit nodes**（流量走 VPS 出口）。

## Cloudflare Tunnel

Cloudflare Tunnel 在**應用層**作為反向代理，與 Tailscale（網路層）互補。處理公開服務：自訂 domain、DDoS 防護、HTTP/3。

### 設定

在 Cloudflare Zero Trust 儀表板建 tunnel、裝 cloudflared：
```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | \
  sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared noble main' | \
  sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install cloudflared
sudo cloudflared service install eyJhIjoiNGRl...
```

Wildcard domain：建 public hostname `*.yourdomain.com` 指向 `http://localhost:80`，加 CNAME 紀錄（Name = `*`, Target = `<TUNNEL_ID>.cfargotunnel.com`）。

### Cloudflare Access

保護管理介面用。**一次性 PIN（OTP）** 寄 10 分鐘有效碼到核准 email——零外部設定。

## Claude Code 資源需求

### 單一實例
官方最低 4 GB RAM。低於這，Linux OOM killer 會砍 Claude Code。實務上輕量工作編列 **8 GB + swap**。

### 並行子代理人
理論上每個實例約 2 GB，10-20 個同時跑需 48-64 GB。實務上代理人會觸發編譯與測試，**32 GB 機器也會 OOM**。

**建議**：
1. 一律加 swap（多代理人至少 8 GB）
2. 積極監控，RAM 超過 90% 警示
3. 殺孤兒程序：`pkill -f "claude.*--resume"` 定期執行
4. 編列**理論需求的兩倍**——每代理人 4 GB 而非 2 GB

### 機型指南

| 機型 | 規格 | 用途 |
|------|------|------|
| CX23（2 vCPU, 4 GB） | €5/月 | 單一 Session，探索性工作 |
| CPX32/CX33（4 vCPU, 8 GB） | €7-14/月 | **甜蜜點**：單 Session 含編譯與測試 |
| CCX33（8 專用 vCPU, 32 GB） | €62.99/月 | 多並行代理人 Session |
| AX42 專用（8C/16T, 64 GB） | 約 €57/月 | 若每天跑代理人，比 CCX33 更划算 |

## 跑 Claude Code

標準工作流：SSH + tmux + API key：
```bash
echo 'export ANTHROPIC_API_KEY=sk-ant-api03-your-key' >> ~/.bashrc
source ~/.bashrc
tmux new-session -d -s claude
tmux send-keys -t claude 'claude' C-m
```

後續 `tmux attach -t claude`。Claude.ai 訂閱者可在初次啟動時走瀏覽器驗證。

隔離環境讓使用 `--dangerously-skip-permissions` 相對安全，但仍建議**用範圍縮小的 API key**——只給本地與開發環境存取權。

## 自動化腳本

### hcloud 開機腳本
用 hcloud CLI 建防火牆（開 port 22 SSH、UDP 41641 Tailscale、ICMP）、開伺服器、輸出 IP 與下一步。

### 後置設定腳本
SSH 進去 cloud-init 完成後跑：
- 用 auth key 裝 Tailscale
- 可選裝 Cloudflare Tunnel
- 裝 Claude Code
- 設 cron（每 30 分清孤兒程序、每 5 分記錄 RAM）

## 結論

**多數開發者的推薦設定**：CCX33 或專用 AX42，用提供的 cloud-init 強化，Tailscale 存取。「這些腳本與設定刻意最小化」，讓開發者可用 Claude 的基礎設施專業能力來改寫，而非死記文件。

---

# 第 11 章：Claude Code 使用者的主觀起點

**發布日期**：2026-04-12

作者推出 **claude-templates**——一個預設好的 repo，把 plugin、skill、CLI 工具、沙盒設定打包在單一安裝腳本裡。

## 解決的問題

> 「每個我聊過的 Claude Code 使用者都有同樣的軌跡：裝起來、vanilla 跑一週、然後下個月花時間累積**散落在多個 repo 的 plugin、skill、MCP 伺服器、shell alias、沙盒設定**。」

claude-templates 提供：
- 用 `install.sh` 統一安裝
- YOLO 模式的預設安全護欄
- 跨多機器的可重現設定
- 更新與解除安裝腳本

## 安裝

需求：`curl`、`npm`、Homebrew（Docker 選配，用於安全掃描）

```bash
git clone https://github.com/pvillega/claude-templates.git
cd claude-templates
./install.sh
cl  # 新 alias 啟動 Claude Code
```

## 核心元件

**Plugin**：Superpowers（工作流自動化）、Engram（SQLite 持久記憶）、程式碼審查、安全指引、自訂 `ct` plugin（13 個 skill）

**CLI 工具**：fd、ripgrep、rtk（token 優化輸出）、gh、jscpd、semgrep、gitleaks、agent-browser、axe-core、pa11y、Nuclei、ZAP

**全域 Skill**：Web 研究（Tavily、Context7）、瀏覽器自動化、資料庫操作、Obsidian 整合、UI 元件、安全審查

**安全設定**：
- 擋敏感系統路徑
- 拒絕破壞性指令（rm -rf）
- 防止 force-push

## 工作流自動化

**Session Hook**：自動 Engram 記憶管理、後壓縮協定重注入、子代理人輸出捕捉

**品質強制**：編輯後 Semgrep 掃描、任務完成合理化偵測、語言特定 linter

**Skill 啟用**：任務執行前三步評估所有可用 skill

## 實務開發者工作流

- **功能規劃**：腦力激盪 → 實作計畫 → TDD 工作流
- **寫程式**：測試優先、自動文件取用
- **審查與修復**：並行代碼審查代理人、迭代錯誤修復、邊界情況偵測
- **Git 操作**：自動化 commit 訊息、PR 建立、分支清理
- **記憶管理**：透過 Engram 的跨 Session 上下文（帶衰退模型）

## 客製化哲學

> 「最好的 Claude Code 設定是**為你的特定工作流量身打造**的那個。」

鼓勵使用者 fork repo 並根據以下調整：
- 語言特定偏好
- 不同記憶系統
- 專案特定 hook
- 技術棧變體

## 安全考量

支援 YOLO 模式（`--dangerously-skip-permissions`）的同時，實作多層保護：擋系統路徑、指令拒絕規則、編輯後 Semgrep 驗證、commit 前 gitleaks 掃描。引用 Simon Willison 的「**致命三連（lethal trifecta）**」警告，針對不受限代理人存取。

## 關鍵要義

claude-templates 是「**主觀的起點**」——不是處方——為了加速設定、同時保持合理的安全預設。**真正價值在 fork 並客製化到自己開發實踐後才浮現。**

---

## 我的心得（My Takeaways）

讀完這 11 章，最有感的三個觀念：

1. **系統才是資產，程式碼是可拋棄的**——停止把「產出多少行程式碼」當成輸出指標，把「系統規格、合約、不變量」當成真正該投資的東西。這是對 [[2026-02-12-EVALUATING-AGENTS-MD-CONTEXT-FILES-HELPFUL-FOR-CODING-AGENTS|ETH Zurich AGENTS.md 研究]] 的精神升級版。
2. **外骨骼（Exoskeleton）不是同事（Coworker）**——這個比喻解釋了為什麼「AI 取代開發者」與「AI 是團隊新成員」兩個說法都不對。它是**放大器**，深度專業 + 強判斷力才有放大效果；否則只是放大垃圾。
3. **LSP + `/clear` + 小 Session = 最大 ROI**——比起一堆花俏 plugin，把 LSP 裝好、autocompact 關掉、學會積極 clear，投入 30 分鐘的回報遠超過堆疊 SuperClaude 這類工具。

對 [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS|「別塞爆 CLAUDE.md」]] 的印證：第 5、6 章是實戰版，包含 Boris Cherny、Teresa Torres、Patrick Zandl 三位實踐者的具體做法。Torres 的「**停下來捕捉（Stop-and-Capture）規則**」值得收進自己的 Claude 工作流。

第 10 章的 Hetzner 設定相當硬核但完整——如果要自建代理人遠端環境，是目前看過最詳盡的實戰文件之一。

## 待補充（Open Questions）

1. Simon Willison 主張「反正便宜就試一下（fire off a prompt anyway）」——這個建議在什麼規模的組織下**開始變危險**？個人 side project 當然沒事，但放到 50 人工程團隊會造成什麼失控？（建議搜尋：`AI coding agent governance medium team risk`）
2. DORA 報告中「AI 採用率每 +25%，交付速度 -1.5%、穩定性 -7.2%」——這些數字是**採用過程中的陣痛**還是**長期穩態**？有沒有 2026 年後期的追蹤研究？（建議搜尋：`DORA 2026 AI adoption steady state`）
3. Anthropic 自家數據顯示 Sonnet 在 1M 長度下檢索準確率掉到 65.1%——這數字**在特定任務類型下是多少**？Code 類任務是否比一般 QA 更慘？（建議搜尋：`Claude Sonnet long context benchmark coding tasks`）
4. 作者推崇 Boris Tane 的「標註計畫法」需要 1-6 輪人類審查——這種高互動模式如何擴展到**多開發者並行的團隊**？會不會反而變成 PM 的瓶頸？（建議搜尋：`AI agent annotated plan workflow team scaling`）
5. 第 11 章的 claude-templates 把幾十個 plugin 打包——這是否違反了第 4 章自己主張的「從最少開始，了解每一塊為什麼在那裡」？（建議搜尋：`claude-templates opinionated defaults minimalism tension`）
6. 「AI 是釘槍」這個類比在資安領域適用嗎？釘槍錯釘一根是局部傷害，但代理人錯釘一次可能是 credential 外洩。類比邊界在哪裡？（建議搜尋：`AI coding agent analogy limits security risk amplification`）

## 相關連結（Related）

- [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]] — 精簡 CLAUDE.md 的漸進式揭露策略，與第 5 章核心主張一致
- [[2026-02-12-EVALUATING-AGENTS-MD-CONTEXT-FILES-HELPFUL-FOR-CODING-AGENTS]] — ETH Zurich 138 個實例實證研究，第 5 章直接引用此研究
- [[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]] — Claude Code 記憶系統實作分析，補充第 6 章的工具面細節
- [[2026-03-16-THE-SHORTHAND-GUIDE-TO-EVERYTHING-AGENTIC-SECURITY]] — 代理人安全完整指南，呼應第 4、10 章的隔離與沙盒主張
- [[2026-03-25-ENGINEERS-FUTURE-MULTI-AGENT-ERA-STEVE-YEGGE]] — Steve Yegge 談工程師邁入多代理人時代，與第 1-3 章的演化論相互呼應

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本系列進行結構化分析。

| 認知層次 | 核心目的 | 對本系列的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 基礎知識 | (1) 11 階段演化（Dismissal→The Matrix）；(2) Kent Beck 金句「90% 歸零，10% × 1000」；(3) 三個轉折點（Fulcrum：控制權放手、一對多、人類極限）；(4) 0.0002% vs 99.99%（prompt 與 context 比例）；(5) METR 研究數字（19% 慢 vs 自認 24% 快）；(6) Anthropic 長 context 數據（Sonnet 1M 僅 65.1%） |
| **理解（半被動）** | 串聯邏輯 | 核心論證鏈：程式碼變廉價（第 2 章）→ 故系統規格成為新資產 → 人類角色從寫 code 轉為規格設計與驗證（第 3 章外骨骼）→ 最關鍵的實作是 CLAUDE.md + 記憶 + Context（第 5-7 章）→ 用對工作流（第 8 章）→ 保護 context 視窗（第 9 章）→ 隔離環境（第 4、10 章）→ 可重現起點（第 11 章）。這個鏈是「**從為何到如何的垂直整合**」。 |
| **分析（主動）** | 找出假設 | **關鍵假設 1**：Beck 的「10% × 1000」建立在「程式碼產量等於價值」是錯誤前提上——但若你的工作主要是**調試生產環境事故**，判斷力早就是 100%，AI 的放大效果可能有限。**假設 2**：外骨骼類比暗示「既有能力」是標準化的，但資深工程師的能力分布極不均。**假設 3**：「系統才是資產」論述隱含「你已經有能力定義正確系統」——但寫不出好規格的開發者用 AI 會怎樣？**偏見**：作者樣本多為有經驗的獨立開發者/小團隊，大型企業情境較少。 |
| **應用（主動）** | 立即行動 | (1) **本週**：裝 LSP（第 4 章），跑 `/context` 審計現有設定，關掉 autocompact；(2) **本月**：採用 Teresa Torres 的三層記憶系統——全域 CLAUDE.md、專案 CLAUDE.md、按需參考檔；(3) **本季**：導入 Boris Tane 的 research.md → plan.md → 標註 → 實作四階段工作流到至少一個專案；(4) **年度**：評估 Hetzner + Tailscale 自建代理人環境，特別是若要跑 YOLO 模式；(5) **文化**：在團隊推「**每次看到 Claude 做錯就加進 CLAUDE.md**」（Boris Cherny 做法）。 |
| **評估（主動）** | 權衡方案 | **優點**：系列是目前見過最完整的「從思維到實作」框架，11 章邏輯清晰，引用大量一手研究（METR、DORA、ETH Zurich、Anthropic 自家數據）。**缺點**：(a) claude-templates（第 11 章）違反第 4 章的簡樸主張，作者自身路線有內在張力；(b) 對**團隊**與**多專案協作**的情境著墨較少，多數建議預設個人開發者；(c) Hetzner 方案對非技術主管或資安敏感產業不可行。**替代方案對比**：若走 Cursor/Copilot 路線，第 4、10、11 章大部分都不適用；若走 Codespaces 全雲端，第 10 章可跳過；若公司強制使用單一 IDE（如金融業），第 6 章的檔案系統記憶得改用企業 KB 系統。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「外骨骼」與「同事」的精確差別是什麼？在什麼條件下外骨骼會變成同事？（例：能自己排隊、能自己定義成功標準時）
- **假設**：「程式碼變廉價」這個主張假設 API 成本持續下降——若 OpenAI/Anthropic 在 2027 年漲價 10 倍會怎樣？作者是否有考慮成本彈性？
- **證據**：第 3 章的 METR 研究只有 16 位開發者、246 個任務——這樣的樣本數量如何推論到「產業普遍現象」？
- **觀點**：若站在「我只是想安靜寫 code」的資深開發者立場，本系列最討厭的論點是什麼？最難反駁的是什麼？
- **後果**：若所有開發者都按第 8 章採用「Spec → Plan → Implement」四階段工作流，整個軟體產業的 time-to-market 會加速還是減速？PM 角色如何變動？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？**
   盲目套用「系統才是資產」心法卻沒有**先學會定義系統**——初級工程師跳過學習傳統編碼基本功、直接用 AI，導致**認知負債（Cognitive Debt）**累積：整個系統能動，卻沒人懂為什麼動、哪裡會壞、如何重建。後續 12-18 個月，生產事故處理能力斷層，年輕世代開發者失去 debug 的肌肉記憶。

2. **什麼情況下會失敗？**
   - **團隊不成熟**：還沒建立清楚的工程實踐（CI、測試、code review）就導入代理人，會放大既有混亂
   - **領域知識高度隱性**：如金融法規、醫療合規——知識在資深人員腦中，代理人無法取用
   - **組織沒決策紀錄文化**：沒有 ADR、沒有 runbook、關鍵資訊散落 Slack——第 7 章的「上下文工程」直接失敗
   - **嚴格資安/合規環境**：無法用 API、無法 YOLO 模式、無法跑遠端 VPS——整個第 4、10、11 章失效

3. **有沒有更好的替代方案？**
   - **對大型企業**：先投資「**機器可讀文件基礎設施**」（ADR、runbook、API spec as code），再讓代理人進場——順序顛倒成本極高
   - **對初級開發者**：**禁用 YOLO 模式**，強制用帶輔助輪的階段（第 4 階段）2-3 個月，建立驗證直覺後再進 YOLO
   - **對重視資安的團隊**：Codespaces + 企業 SSO + 稽核 log 比作者推薦的 Hetzner 自建更合理
   - **對個人開發者但 token 預算有限**：local LLM（如 Qwen Coder、DeepSeek）+ 嚴格 context 管理，比追高階模型更永續

## References

- [原系列首頁](https://perevillega.com/series/ai-developer-evolution/)
- [Chapter 1 — A Practitioner's Guide](https://perevillega.com/posts/2026-03-15-fulcrums-of-ai-developer-evolution)
- [Chapter 2 — Code Is Cheap Now](https://perevillega.com/posts/2026-03-16-code-is-cheap-now)
- [Chapter 3 — AI Is an Exoskeleton](https://perevillega.com/posts/2026-03-17-ai-is-an-exoskeleton-not-a-coworker)
- [Chapter 4 — Your First Day With Claude Code](https://perevillega.com/posts/2026-03-18-your-first-day-with-claude-code)
- [Chapter 5 — The One File That Makes or Breaks Your AI Workflow](https://perevillega.com/posts/2026-03-23-the-one-file-that-makes-or-breaks-your-ai-workflow)
- [Chapter 6 — Building Agent Memory](https://perevillega.com/posts/2026-03-24-building-agent-memory-that-survives-between-sessions)
- [Chapter 7 — Context Engineering](https://perevillega.com/posts/2026-04-08-context-engineering-the-skill-that-replaced-prompt-engineering)
- [Chapter 8 — The Only Workflow That Works](https://perevillega.com/posts/2026-04-13-the-only-workflow-that-works)
- [Chapter 9 — Surviving the Context Window](https://perevillega.com/posts/2026-04-15-surviving-the-context-window-in-practice)
- [Chapter 10 — Running AI Coding Agents on Hetzner](https://perevillega.com/posts/2026-04-02-running-ai-coding-agents-on-hetzner)
- [Chapter 11 — An Opinionated Starting Point](https://perevillega.com/posts/2026-04-12-an-opinionated-starting-point-for-claude-code-users)
