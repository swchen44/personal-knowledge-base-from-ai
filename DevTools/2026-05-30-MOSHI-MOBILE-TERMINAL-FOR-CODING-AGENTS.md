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
> 以下整理自官方 /docs 主頁的 Voice 段落（`getmoshi.app/docs/voice` 專頁因連線問題本次未能抓取，更細的設定步驟見 Open Questions）。

Moshi 讓你用「講」的方式驅動終端機，支援三種辨識引擎（dictation engine）：

| 辨識引擎 | 處理位置 | 特性 |
|---------|---------|------|
| **Apple SpeechAnalyzer** | 裝置端（on-device） | iOS 內建、隱私佳、免網路 |
| **本地 Whisper（local Whisper）** | 裝置端（on-device） | 開源模型、離線可用 |
| **雲端引擎（hosted cloud engine）** | 雲端 | 可能辨識更準，但語音會送出 |

### 兩種語音模式

```text
┌─────────────────────────────────────────────┐
│  Chat mode（聊天模式）                         │
│  語音 → 先組成 prompt（可檢視/修改）→ 再送出     │
│  適合：給 agent 下完整指令，避免講錯直接執行      │
├─────────────────────────────────────────────┤
│  Command mode（命令模式）                      │
│  語音 → 直接打進 shell（即時輸入）              │
│  適合：快速打指令、檔名、短字串                  │
└─────────────────────────────────────────────┘
```

> [!tip] 可執行建議
> 重視隱私就選 **Apple SpeechAnalyzer** 或 **本地 Whisper**（語音不出裝置）；要對 agent 下長 prompt 時用 **Chat mode** 先檢視再送，避免語音辨識錯字直接被執行。

## 貼圖到 Prompt（Image Paste）

> [!info] 資料來源
> 整理自官方 /docs 主頁的 Image paste 段落（`getmoshi.app/docs/image-paste` 專頁本次未能抓取，圖片實際存放位置／保留時間見 Open Questions）。

**運作方式**：在 prompt 中直接貼上**截圖、照片、或剪貼簿圖片**，Moshi 會把圖片轉成一個 **可抓取的 URL（fetchable URL）** 交給 agent —— agent 就能讀取該圖。

```text
 手機端                         host 上的 agent
   │                                │
   │ 貼上截圖/照片/剪貼簿圖片         │
   │──── Moshi 產生 fetchable URL ──►│
   │                                │── 透過 URL 抓取圖片 ──►（讀圖）
   │                                │
   ✗ 不需 scp　✗ host 不留暫存檔
```

> [!tip] 為什麼方便
> 傳統做法要把圖 `scp` 到 host、再在 prompt 裡指路徑、用完還要清暫存檔。Moshi 直接給 agent 一個 URL，**省去 scp 與暫存檔清理**。相關開關位於 Settings 的「檔案分享（file sharing）」。

> [!warning] 資安考量
> 「可抓取的 URL」代表圖片被放到某處供 agent 抓取。**該 URL 的存放位置、保留時間、存取權限官方主頁未交代**（見 Open Questions）—— 貼含機敏資訊的截圖前請留意。

## 安裝與設定細節（Installation & Setup）

### 完整建議設定流程

```text
 在 host（你的 Mac / Linux / VPS / homelab）上：
   1. 安裝 mosh 與 tmux
        └─ mosh：網路切換/斷線時連線仍存活
        └─ tmux：App 退背景時 agent 仍繼續跑（long-lived workspace）
   2. （選用）安裝 moshi-hook —— 有用 coding agent 才需要
        └─ 把 agent 事件（approval / session / tool / turn）送進 App Inbox

 在手機 App（iOS / Android）上：
   3. 新增一個連線（connection），用 SSH key 驗證
   4. 把 tmux 設為長期工作區
   5. 開啟推播通知（push notifications）
```

### 連線（Connection）儲存的設定欄位

Home 的每個 saved connection 會記住：

| 欄位 | 說明 |
|------|------|
| host / port | 目標主機位址與埠 |
| username | 登入帳號 |
| auth mode | 驗證方式（建議 SSH key） |
| transport preference | 傳輸偏好（SSH vs mosh） |
| mosh / SSH routing | mosh 或 SSH 的路由設定 |

> [!important] 三件事缺一不可的理由
> - **mosh** → 讓終端在網路切換時不斷線；
> - **tmux** → 讓 agent 在 App 切到背景時繼續執行；
> - **moshi-hook** → 讓 Moshi 知道何時該通知你（approval 等）。
> 三者組合起來，才有「手機 babysit 長任務」的完整體驗。

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
