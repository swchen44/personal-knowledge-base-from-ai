---
title: "Moshi — 從手機遠端操控 AI 編碼代理人的行動終端機"
date: 2026-05-30
date_uncertain: true
category: DevTools
tags:
  - tools/cli
  - ai/agent
  - mobile/terminal
  - productivity/workflows
  - ssh
source: "https://getmoshi.app/docs"
source_type: tool
author: "Moshi (getmoshi.app)"
status: notes
links:
  - "[[CLAUDE-CODE-WORKFLOW-TIPS]]"
  - "[[AI-CODING-AGENT-WORKFLOW]]"
  - "[[TMUX-REMOTE-DEV-SETUP]]"
---

## 摘要（Summary）

**Moshi** 是一款 iOS／Android 的**行動終端機（mobile terminal）**App，讓你用手機或平板，連回自己原本就在用的開發機器（Mac、Linux、VPS、homelab），即時觀看、回應並操控長時間執行的 AI 編碼代理人（coding agent）、shell 與 tmux session。

官方比喻最傳神：

> [!quote]
> 「嬰兒監視器（baby monitor）之於熟睡的孩子，就是 Moshi 之於你的 AI 代理人。」
> （What a baby monitor is to a sleeping kid, Moshi is to your AI agents.）

關鍵定位：Moshi **不在自己的雲端跑你的程式碼，也不取代你的 agent CLI**。它只是「行動控制面（mobile control surface）」——運算、工具、git 憑證、agent 程序全部留在你連回去的那台主機（host）上。

## 關鍵洞察（Key Insights）

- **解決的痛點**：AI 編碼代理人常常要跑很久，而且中途會跳出「approval / 確認」請求等你回答。過去你必須開著筆電守在旁邊；Moshi 把這個「守候」搬到手機上 — 參見 [[CLAUDE-CODE-WORKFLOW-TIPS]]。
- **不是螢幕截圖，是真終端機**：它給你一個真正可互動的終端機（real terminal），不是遠端桌面截圖。
- **通知即工作流**：代理人的 approval、prompt、「are you sure」會落到 inbox、鎖定畫面（lock screen）與 Live Activity，一鍵 allow／deny／read first。
- **自己掌控資料主權**：所有敏感資產（repo、SSH config、agent 訂閱）都不離開你的主機。

> [!note] 關鍵術語（Key Term）：moshi-hook
> 安裝在 host 上的掛勾程式，負責把 agent 事件（approvals、session 開始、tool 活動、turn 完成）送進 App 的 Inbox，並驅動 Live Activities 與推播通知（push notification）。

## 詳細內容（Details）

### 你問的四個問題，先給結論

| 你的問題 | 答案 |
|---------|------|
| **可以用在什麼 use case？** | 用手機遠端操控、監看、回應在自己機器上跑的 AI 編碼代理人與 shell（詳見下方「使用案例」） |
| **Codex 可以用嗎？** | ✅ 可以，官方明列支援 |
| **Claude 可以用嗎？** | ✅ 可以（**Claude Code**），官方明列支援 |
| **Windows / Mac / Linux 可以用嗎？** | **Host 端**：Mac、Linux、VPS、homelab ✅；**Windows 文件未明確列出** ⚠️。**手機端**：iOS 與 Android ✅ |
| **要錢嗎？** | **有免費版（Free），核心功能免費可用**；**Pro（付費）** 才解鎖每日重度使用的進階功能（見下表）。確切金額官網未公開標價（見 Open Questions） |

### 免費版 vs Pro（Free vs Pro）

| 功能 | Free | Pro |
|------|:----:|:---:|
| 基本 SSH 終端機、操控 agent | ✅ | ✅ |
| 推播通知 / Inbox 事件 | ✅ | ✅ |
| **mosh**（網路切換時連線存活） | — | ✅ |
| **tmux pairing**（tmux 配對整合） | — | ✅ |
| **image paste**（貼圖進 prompt） | — | ✅ |
| 自訂主題／字型（custom themes/fonts） | — | ✅ |
| 無限儲存主機（unlimited saved hosts） | — | ✅ |
| Apple Watch 動作 | — | ✅ |

> [!info] 資料來源
> Free/Pro 功能差異整理自官網與第三方介紹（getmoshi.app、App Store、評測文章）。**官網未公開具體訂閱金額**，實際價格請以 App Store／Google Play 內顯示為準。

### 支援的 AI 編碼代理人（Supported Agents）

Moshi 可遠端驅動以下 agent（也支援一般 shell）：

- **Claude Code**
- **Codex**
- **OpenCode**
- **Gemini**
- **Cursor**
- **Kimi**
- **Qwen**
- 一般 shell 終端機

### 平台支援（Platform Support）

| 角色 | 支援平台 |
|------|---------|
| **手機端（Client）** | iOS、Android |
| **主機端（Host）** | Mac、Linux box、VPS、homelab |
| **Windows 主機** | ⚠️ 官方文件未明確提及 |

### 主要使用案例（Use Cases）

> [!example] 從手機能做什麼
> - **遠端操作代理人**：在 Mac／Linux／VPS／homelab 上跑 Claude Code、Codex、Gemini、Cursor、Kimi、Qwen，從手機真終端機操控。
> - **回應代理人請求**：approval / prompt / 「are you sure」進 inbox、鎖定畫面、Live Activity，一鍵處理。
> - **掌握進度**：Live Activity 顯示目前 turn；inbox 顯示 tool 執行與 turn 完成；Settings 看 quota 與 token 用量。
> - **隨手開工**：開會空檔、計程車上、散步時，啟動一次 refactor、問個問題、修個 typo —— session 一直活著直到你回來。
> - **語音輸入**：支援 Apple 裝置端 SpeechAnalyzer、本地 Whisper、或雲端引擎。Chat mode 先組 prompt 再送、command mode 直接打進 shell。
> - **直接傳圖**：貼上截圖／照片／剪貼簿圖片進 prompt，agent 拿到可抓取的 URL，免 scp、免在 host 留暫存檔。
> - **為手機優化的輸入**：終端機工具列、自訂快捷鍵、D-pad、完整硬體鍵盤支援。

### App 主要組成

| 區塊 | 功能 |
|------|------|
| **Home** | 已存連線與 active session。連線設定含 host、port、username、auth 模式、傳輸偏好、mosh/SSH 路由設定 |
| **Terminal** | 即時 session：scrollback、重連行為、貼上控制、鍵盤工具列、語音、貼圖、session 切換 |
| **Inbox** | 來自 `moshi-hook` 的 agent 事件：approvals、session 開始、tool 活動、turn 完成 |
| **Settings** | 終端外觀、輸入行為、通知、agent hooks、檔案分享、生物辨識、iCloud 同步、語言、Pro 限定個人化 |

### 建議安裝設定（Recommended Setup）

```text
1. 在 host 安裝 mosh 與 tmux
2. 用 SSH key 驗證新增一個 Moshi 連線
3. 用 tmux 當長期工作區（long-lived workspace）
4. 開啟推播通知（push notifications）
5. 若用編碼代理人，在 host 安裝 moshi-hook
```

> [!tip] 為什麼這樣設定
> - `mosh` 讓終端在網路切換時仍存活；
> - `tmux` 讓 agent 在 App 退到背景時繼續跑；
> - `moshi-hook` 讓 Moshi 有足夠 context，在需要你注意時才通知。

> [!important] 心智模型（Mental Model）
> 把 Moshi 想成「行動控制面」。運算、工具、git 憑證、agent 程序，全部留在你連回去的那台 host。Moshi 不託管你的程式碼。

## 語音輸入（Voice & Dictation）

> [!info] 資料來源
> 整理自官方專頁 `getmoshi.app/docs/voice`（page 12/32）。設定入口：**Settings → Speech**。

Moshi 能把語音轉成終端機輸入，最適合用在：對 agent 下自然語言 prompt、打短 shell 指令、以及不想跟手機鍵盤搏鬥時編輯文字。

### 三種辨識引擎（Speech Engines）

| 引擎 | 處理位置 | 重點 | 計費 |
|------|---------|------|------|
| **Apple（SpeechAnalyzer）** | 裝置端（on-device），iOS 26+ | 不出手機、免下載模型、支援裝置上最快；舊版 iOS 不顯示此選項 | 免費 |
| **Whisper（whisper.cpp）** | 裝置端，需下載模型 | 全 iOS 版本可用、可完全離線；模型從「小型純英文」到「大型多語言」，越大越準但越佔空間／越慢；模型存裝置可移除 | 免費 |
| **Cloud（雲端託管）** | Moshi 雲端 | 通常**辨識最準**、免下載；但需註冊 push token，且**有額度限制（metered）** | **Free 每日小額度、Pro 較大額度**（設定畫面顯示剩餘/總額度） |

> [!warning] 隱私
> 只有 **Cloud** 會把語音送出裝置；**Apple** 與 **Whisper** 完全在裝置端處理。處理機敏內容時優先選後兩者。

### 語言（Language）
可設「自動偵測」或「固定某語言」。常切換語言用自動；引擎一直認錯時改固定。Apple 與 Cloud 一律有語言選單；**Whisper 只有在選多語言模型時**才有（純英文模型只轉英文）。

### 兩種模式：Chat mode 開/關

```text
┌────────────────────────────────────────────────────────┐
│ Chat mode = OFF（命令模式）                              │
│  語音 → 直接以「鍵盤輸入」串進終端機                       │
│  搭配 Auto-send → 轉完自動按 Enter                       │
│  適合：shell 指令、REPL、tmux 操作、短字串                │
├────────────────────────────────────────────────────────┤
│ Chat mode = ON（聊天/組稿模式）                          │
│  語音 + 打字 + 圖片附件 → 在終端機上方的 composer 一起組稿 │
│  點送出才整包送給 agent；送出前可改錯字、補句、貼圖        │
│  適合：對 Claude Code / Codex / Gemini 等下完整 prompt    │
└────────────────────────────────────────────────────────┘
```

> [!tip] 怎麼選
> 工作多是 shell/tmux → 關 Chat mode；多在跟 agent 對話 → 開 Chat mode（送出前可檢視，避免語音錯字直接被執行）。

### 其他
- **Auto-send**：聽寫結束後自動送出；想先檢視就關掉。
- **Transcription history（逐字稿歷史）**：保留近期聽寫，方便「長 prompt 小修改」或「把類似指令送到另一個 session」。
- **實務技巧**：短 prompt 用 push-to-talk；打程式碼類文字時「把標點唸出來」；破壞性指令送出前先看過；離開快網路前先下載好要用的 Whisper 模型。

## 貼圖／貼檔到 Prompt（Image & File Paste）

> [!info] 資料來源
> 整理自官方專頁 `getmoshi.app/docs/image-paste`。觸發捷徑為 **Ctrl+V**（被當成跨平台的通用貼上鍵）。

### 附件來源（Add attachment 面板）
從終端機工具列的「附加」鍵叫出，提供：

| 來源 | 說明 |
|------|------|
| **Camera** | 即時拍照 |
| **Photo** | 從 iOS 相簿選（含截圖） |
| **Files** | iOS 文件選擇器：PDF、壓縮檔、log、設定檔等 |
| **Clipboard** | **只有在 iOS 偵測到可用剪貼簿內容時才出現**（空的或不支援的格式會自動隱藏） |

### 檔案怎麼傳、存哪裡（重要修正）

> [!important] 實際行為：會寫入 host
> 終端機的貼圖/貼檔流程，是把內容**透過 SCP 複製到 host 的 `~/.moshi/uploads/`**，然後把該檔的**本機路徑（local file path，不是 URL）**交給 agent。
> - **Chat mode 開**：路徑附到 composer 訊息。
> - **Chat mode 關**：路徑直接貼進終端機游標處。

```text
 手機端                          host（你的開發機）
   │                                 │
   │ 附加 截圖/照片/檔案              │
   │──── SCP 複製 ──────────────────►│  ~/.moshi/uploads/xxxx.png
   │                                 │
   │   把「本機路徑」給 agent ───────►│  agent 用一般檔案存取讀取
```

> [!warning] 兩個注意點
> 1. **檔案會累積在 `~/.moshi/uploads/`**：可從 Moshi 的 **Files 畫面**（有縮圖）管理，或用 SSH 自行刪除——機敏截圖記得清。
> 2. **Remote clipboard**：若開啟此選項，圖片的絕對路徑也會被送到 host 的剪貼簿，方便在桌面端貼上。
> 3. 部分 agent 需要你在訊息裡**明確指示**配合該檔案路徑，才會正確讀圖。

> [!note] 與「語音 Chat mode 附圖」的差異
> 在語音 Chat mode 內附圖時，官方描述是「送一段 **short URL** 讓 agent 抓取、**不寫入 host**」；而上面終端機的 image paste 則是 **SCP 進 `~/.moshi/uploads/`、給本機路徑**。兩條路徑的落地方式不同，使用時留意。

## 安裝與設定細節（Installation & Setup）

> [!info] 文件結構
> 官方 docs 的 Start 區有「**Install and prepare a host**」與「**Run your first session**」兩頁；Connections 區另有「Connections and authentication」「Tailscale」；Multiplexer 區涵蓋 tmux / Zellij / Herdr。以下為建議起手式。

### 建議設定流程

```text
 在 host（Mac / Linux / VPS / homelab）：
   1. 安裝 mosh 與 tmux
        └─ mosh：網路切換/斷線時連線仍存活
        └─ tmux：App 退背景時 agent 繼續跑（long-lived workspace）
   2. （用 coding agent 才需要）安裝 moshi-hook
        └─ 把 agent 事件（approval / session / tool / turn）送進 App Inbox

 在手機 App（iOS / Android）：
   3. 新增連線（connection），用 SSH key 驗證
   4. 把 tmux 設為長期工作區
   5. 開啟推播通知（push notifications）
```

### 連線（Connection）儲存的設定欄位

| 欄位 | 說明 |
|------|------|
| host / port | 目標主機位址與埠 |
| username | 登入帳號 |
| auth mode | 驗證方式（建議 SSH key） |
| transport preference | 傳輸偏好（SSH vs mosh） |
| mosh / SSH routing | mosh 或 SSH 的路由設定 |

> [!tip] 連線進階
> 文件另列出 **Tailscale** 作為連線方式之一——若 host 在 NAT/防火牆後、沒有公開 IP，用 Tailscale 這類 mesh VPN 會比開埠轉發更省事。多工器除了 tmux 也支援 **Zellij** 與 **Herdr**。

> [!important] 三件套缺一不可的理由
> - **mosh** → 終端在網路切換時不斷線；
> - **tmux** → agent 在 App 切背景時繼續執行；
> - **moshi-hook** → Moshi 知道何時該通知你（approval 等）。
> 三者組合，才有「手機 babysit 長任務」的完整體驗。

## 我的心得（My Takeaways）

- 這正好補上 [[CLAUDE-CODE-WORKFLOW-TIPS]] 裡「長時間 agent 任務需要 babysit」的缺口 —— 用手機 babysit，而不是綁在筆電前。
- 架構上「只做控制面、不碰運算與憑證」的選擇很聰明：降低資安疑慮，也避免和現有 CLI 訂閱衝突。
- 對我自己的 connsys-jarvis multi-agent 設計有啟發：agent 的 approval/事件流（event stream）如果能標準化成 hook → inbox，就能接任何通知前端。
- 若我的 host 是 Windows（WSL 例外），要先確認支援度再投入。

## 待補充（Open Questions）

- **Pro 版確切價格是多少？** 已知 Pro 解鎖 mosh／tmux pairing／image paste／自訂主題／無限主機／Apple Watch；但**確切金額（月費？年費？買斷？）官網未標價**，需到 App Store／Play 確認。（建議搜尋：`getmoshi.app pricing`、`Moshi app Pro subscription price`）
- **Windows host 到底支不支援？** 透過 WSL2 + SSH 是否可行？（建議搜尋：`getmoshi Moshi Windows WSL host`）
- **連線安全模型細節**：除了 SSH key，是否支援憑證輪替、2FA、或零信任（zero-trust）連線？
- **moshi-hook 對各家 agent 的整合深度**：Claude Code 的 hook 與 Codex 的整合是否一致，還是各 agent 支援程度不同？
- **離線／弱網表現**：mosh 之外，App 對長時間斷線的 session 恢復上限為何？
- **資料留存**：貼圖產生的「可抓取 URL」存在哪、保留多久、誰能存取？（資安考量）
- **與 tmux 以外方案的相容性**：不裝 tmux 時功能會少哪些？

## 相關連結（Related）

- [[CLAUDE-CODE-WORKFLOW-TIPS]] — 同樣處理「長時間 AI 編碼代理人任務」的工作流，Moshi 是其行動端補充
- [[2026-07-05-TERMINAL-MEMORY-MANAGEMENT-AND-CROSS-PLATFORM-PERSISTENCE]] — 補充為何長時間 AI CLI 任務應放進 tmux / psmux 類持久化層，而不是綁死在 GUI 終端機視窗
- [[AI-CODING-AGENT-WORKFLOW]] — Codex／Claude Code／Gemini 等代理人的使用方法，Moshi 是它們的遠端控制面
- [[TMUX-REMOTE-DEV-SETUP]] — Moshi 建議用 tmux + mosh + SSH，與遠端開發環境設定高度相關

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 必記核心：Moshi=行動終端機 App（iOS/Android）；支援 Claude Code／Codex／Gemini／Cursor／Kimi／Qwen；host 需裝 mosh+tmux+moshi-hook；有 Free 與 Pro；不託管程式碼 |
| **理解（半被動）** | 解釋概念與關聯 | Moshi 把「守在筆電前等 agent 確認」這件事搬到手機：host 上的 `moshi-hook` 把事件推到手機 inbox → 你一鍵回應 → 指令透過 SSH/mosh 回到仍存活的 tmux session |
| **分析（主動）** | 檢驗論點與假設 | 關鍵假設：你已有一台「常開、可被 SSH 連入」的開發主機。對沒有固定 host（純筆電）或在 Windows 上的人，前提就不成立；安全性完全押在 host 的 SSH 設定上 |
| **應用（主動）** | 轉為行動 | ①在自己的 Linux/Mac dev box 上裝 mosh+tmux+moshi-hook，把 Claude Code 跑在 tmux，手機裝 Moshi 試 babysit 一次長任務；②評估 connsys-jarvis 的 agent 事件流是否能輸出成 moshi-hook 相容格式 |
| **評估（主動）** | 權衡優劣 | vs. 純 SSH App（如 Termius）：Moshi 多了 agent 事件感知與一鍵 approval，但綁定「自有 host」模式；vs. 雲端 agent 平台（如 agent 在雲端跑）：Moshi 保有資料主權但要自己維運 host。重視隱私＋已有 homelab 者划算；想零維運者不適合 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「行動控制面（mobile control surface）」與一般 SSH client 的本質差異到底在哪？是不是只差在 agent 事件感知？
- **假設**：本文最關鍵前提是「使用者已有一台可遠端連入的常開主機」。若此前提不成立（只有筆電、會休眠），Moshi 的價值還剩多少？
- **證據**：「真終端機而非截圖」的體驗優勢，有沒有實測延遲／可用性數據支撐，還是僅為行銷說法？
- **觀點**：站在反對者立場——「不過是包了好看 UI 的 SSH + 通知」，這個批評站得住腳嗎？
- **後果**：若團隊全面採用手機 approval，12 個月後會不會出現「在不專心狀態下隨手批准危險操作」的副作用？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 資安：手機一鍵 approve 等於把高權限操作的把關放到行動情境，分心時誤批可能造成破壞性指令執行、誤刪、或洩漏；且整個信任鏈押在 host 的 SSH 設定上，金鑰外洩即全失守。
2. **什麼情況下會失敗？** — ①沒有常開可遠端連入的 host（純筆電、會休眠／換網路且未用 mosh）；②host 為 Windows 而文件未明確支援；③公司網路封鎖 SSH/mosh 對外連線；④不裝 tmux 時 session 無法在背景存活。
3. **有沒有更好的替代方案？** — 若只要遠端 shell：Termius／Blink 等成熟 SSH App 更通用；若要零維運、不想自管 host：選雲端代理人平台（agent 直接跑在供應商雲端）。**何時選 Moshi**：你已有 homelab/dev box、重視資料主權、且主要痛點是「agent approval 需要隨時隨地回應」時。

## References

- [Moshi 官方文件]( https://getmoshi.app/docs )
- [Voice and dictation](https://getmoshi.app/docs/voice)
- [Image paste](https://getmoshi.app/docs/image-paste)
