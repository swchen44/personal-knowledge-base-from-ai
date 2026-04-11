---
title: "六萬星就等於安全嗎？gstack 遙測爭議與治理滯後的省思"
date: 2026-04-04
category: Security
tags:
  - "#security/supply-chain"
  - "#security/telemetry"
  - "#ai/tools"
  - "#opensource/governance"
source: "https://tznthou.com/posts/gstack--mnjvllm4"
source_type: article
author: "tznthou"
status: notes
links:
  - "[[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]]"
  - "[[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]]"
  - "[[2026-03-16-THE-SHORTHAND-GUIDE-TO-EVERYTHING-AGENTIC-SECURITY]]"
---

## 摘要（Summary）

gstack 是 Y Combinator 總裁 Garry Tan 開源的 Claude Code Skill 工具包，上線不到一個月就累積六萬顆星。但作者花了半小時用 Perplexity 交叉查證後發現：gstack 在安裝時**默默收集工作階段資料**（讀取 `~/.claude/projects/` 下的 session 檔案），而且初次安裝引導會推使用者選擇 `community` 遙測層級。更嚴重的是，負責接收遙測資料的後端函式使用了不該使用的「管理員金鑰（Admin Key）」來連接 Supabase 資料庫，可完全繞過存取權限規則（RLS）。獨立審計**未發現惡意行為**，但揭露了一個核心議題：**不是惡意，是治理跟不上成長**。

## 關鍵洞察（Key Insights）

- **星數衡量的是關注度，不是安全性** — 六萬星不代表有很多人真的翻過程式碼
- **不是「蒐集了什麼」的問題，而是「你沒問過我」的問題** — 核心爭議是預設值與知情同意（Informed Consent）
- **AI 開發工具的信任門檻比一般套件更高** — 它們跑在開發環境裡，能讀你的工作階段、專案、工作模式 — 參見 [[2026-03-16-THE-SHORTHAND-GUIDE-TO-EVERYTHING-AGENTIC-SECURITY]]
- **產業尚未建立成熟的遙測治理標準（Telemetry Governance）**：什麼該蒐集、怎麼告知、`off` 到底該多 `off`，都還沒共識

## 詳細內容（Details）

![Perplexity 交叉查證 GitHub](assets/2026-04-04-GSTACK-SECURITY/perplexity-github.webp)

### 社群在意的四個方向

截至 2026-04-04，GitHub 上跟 Telemetry（遙測）相關的問題回報與修復提案已累積數十則，歸納為四類：

#### 1. 它會讀你的 Claude Code 工作階段檔案

社群成員 **rumi-ali** 對 gstack v0.11.17.0 做了獨立安全審計（Issue #467）：

- `gstack-global-discover` 會讀 `~/.claude/projects/` 下的工作階段檔案
- 取前 8KB 抓取工作目錄路徑
- 同時掃描 Codex 和 Gemini 的暫存資料夾
- **不讀對話內容**，但知道你在哪些專案工作、何時活躍
- **安裝時完全沒告知這件事**

#### 2. 設 `off` 之後到底還會不會上傳？

> [!tip] 重點：修復後（#467）確實已不上傳
> 設成 `off` 之後，確實不會再上傳資料到 Supabase（gstack 用來存遙測資料的雲端資料庫）。本地 session 檔當然會寫（記錄專案名稱和分支名），但這是每個 AI 工具都在做的。

真正爭議在於**預設值**：初次安裝時，引導語會推你選 `community` 遙測層級，措辭不中立。沒特別注意的話，預設就是有在傳的。

#### 3. 每次執行指令都會發網路請求

- 每次執行 gstack 指令都會送訊息
- 遙測不設 `off` 的話，還會同時向 Supabase 傳送資料
- 這些網路請求是**靜默的**，不會給任何提示

#### 4. 安裝引導「帶風向」

初次安裝時建議選 `community`，措辭有推銷味，不是中立地讓使用者自己決定。

### 硬核的安全漏洞：萬能鑰匙

![Issue #750 修復提案](assets/2026-04-04-GSTACK-SECURITY/issue-750.webp)

> [!warning] Issue #675：Supabase Admin Key 誤用
> 負責接收遙測資料的後端函式使用了不該使用的**管理員金鑰（Admin Key / Service Role Key）**來連接資料庫。

**白話說明**：
- Supabase 有一套 **Row Level Security（RLS）** 存取權限規則
- 但 Admin Key 是萬能鑰匙，可以完全跳過這些規則
- 原本的操作用一般金鑰（Anon Key）就夠，根本不需要萬能鑰匙
- 如果有人找到方法直接呼叫這個入口，存取限制不會擋它

截至查證日，這個問題仍未解決，修復提案 #750 正在處理中。

### 不是惡意，是治理滯後

![問題到底出在哪？](assets/2026-04-04-GSTACK-SECURITY/problem-source.webp)

> [!important] rumi-ali 獨立安全審計結論：**未發現惡意行為**
> 不讀對話內容、不偷 API Key、不改系統設定。

#### 版本紀錄拉出的時間軸

| 日期 | 版本 | 發生了什麼 |
|------|------|-----------|
| 3/12 | v0.0.1 | 專案首次公開，無遙測相關目錄，說明文件也沒出現 "Telemetry" 或 "Privacy" 字樣 |
| 3/20 | v0.8.6 | **一次性加入完整遙測機制**：本地紀錄腳本 + Supabase 資料表結構 + 後端接收函式 + 隱私章節文件同時上線 |
| 3/25 | v0.11.16.0 | Supabase 安全加固（社群審查後才做） |
| 4/4 | v0.15.4.0 | 目前版本，仍有未解決問題 |

> [!quote] 作者的診斷
> gstack 從個人工具包變成六萬星專案，速度太快了。3/12 公開、3/20 加遙測、3/25 就被抓出安全問題，整個過程不到兩週。一個人（或小團隊）的個人專案突然有六萬雙眼睛盯著看，治理架構當然來不及建。

### 水電師傅的類比

作者用了一個精準的類比：

> 這就像你找了一個水電師傅來家裡修水管，結果後來發現他順便記錄了你家哪幾間房間有在使用。他沒偷東西、沒翻你抽屜、沒拍照，就是記了一下「主臥有人住、書房常開燈」。你能說他是壞人嗎？好像不能。但你會覺得不舒服嗎？會。因為你沒有同意這件事。

### 不只 gstack — 整個 AI 開發工具的信任問題

現在的 AI 開發者工具（Cursor、Windsurf、Claude Code 本身，甚至現在最紅的龍蝦）都跑在你的開發環境裡：
- 能讀到你的工作階段
- 能讀到你的專案結構
- 能看到你的工作模式

這些工具的**信任門檻**本來就比一般套件高很多。但目前整個產業都還沒建立成熟的遙測治理標準。

### 那到底還能不能用？

> [!tip] 作者建議：可以用，但要知道自己在信任什麼
> **已修復**：獨立審計沒發現惡意行為；`off` 不寫本地紀錄的問題已修復；維護者回應態度正面
>
> **未解決**：Admin Key 繞過 RLS 的漏洞還在修；初次安裝引導措辭還沒改
>
> **實務建議**：
> - 個人專案無敏感資料 → 可以用
> - 公司環境或有機密內容 → 至少把遙測設成 `off`，定期關注 issue 進展

## 我的心得（My Takeaways）

1. **評估開源工具安全性不能只看星數**：星數是關注度的指標，不是審查品質的指標。真正翻過程式碼的人可能遠少於想像
2. **預設值就是民主選擇**：「有揭露、能關掉」不夠好，「預設關閉、主動開啟」才是真正尊重使用者
3. **個人專案爆紅後需要立即補治理**：當一個 side project 突然有數萬使用者，原本的「個人決定」就變成「產業標準問題」
4. **AI 工具的威脅模型（Threat Model）不同於一般 CLI**：它們有權讀 session、project、edit history，信任審查應該更嚴格

## 相關連結（Related）

- [[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]] — gstack 作為三大 AI 編程框架之一，本文揭露了其治理層面的問題
- [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]] — gstack 是 Harness Engineering 的代表作之一，但安全性是 Harness 設計常被忽略的一環
- [[2026-03-16-THE-SHORTHAND-GUIDE-TO-EVERYTHING-AGENTIC-SECURITY]] — 代理人工具安全的通用防禦框架
- [[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]] — gstack telemetry 子系統的程式碼分析，本文爭議的技術細節在此
- [[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]] — gstack 測試架構的程式碼分析，另一面向的設計品質

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，確立基礎知識 | gstack = Garry Tan 開源的 Claude Code Skill 工具包；6 萬星不到一個月；Issue #467（讀 session 檔）、#675（Admin Key 誤用）、#750（修復中）；`gstack-global-discover` 會掃描 `~/.claude/projects/` |
| **理解（半被動）** | 解釋概念的含義及關聯 | 文章論證結構：先陳述爭議 → 拉出版本紀錄證明不是惡意 → 用水電師傅類比點出知情同意問題 → 從 gstack 延伸到整個 AI 開發工具的信任議題。核心論點：「不是蒐集了什麼的問題，而是你沒問過我的問題」 |
| **分析（主動）** | 檢驗論點、找出假設 | 作者的關鍵假設：「獨立審計沒找到惡意 = 可以放心用」。但審計只是時間點快照，無法保證未來版本不會引入惡意邏輯。此外，作者把問題歸因於「治理滯後」，但也可能是作者刻意低調處理敏感功能（如果是 YC 總裁的專案，這個歸因更值得懷疑） |
| **應用（主動）** | 將知識套用情境 | 1. 建立個人的 AI 工具安全檢查清單：安裝前看 package.json postinstall、grep 程式碼中的 telemetry/analytics 關鍵字、檢查是否有 network call；2. 為公司環境建立政策：AI 工具遙測必須 opt-in，預設 off，並加入 allowlist；3. 在 CI pipeline 中加入 supply chain 監控工具（如 Socket、Snyk）自動掃描新 dependency 的網路行為 |
| **評估（主動）** | 判斷多個方案的優劣 | 「停用 vs 繼續用」的權衡：停用損失工具帶來的生產力，繼續用承擔資料外洩風險。決策關鍵在於資料敏感度 —— 個人專案選「用 + off」成本最低；客戶機密專案應選「等 #750 修復 + 完整審計報告發布後再用」。另一個替代方案是自己 fork 並移除遙測程式碼，適合高安全要求但需要工具功能的團隊 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「治理滯後」和「刻意隱瞞」的界線在哪？如何從版本紀錄客觀判斷哪一種？
- **假設**：作者假設 rumi-ali 的獨立審計可信。但審計者的資歷、方法論、是否有利益衝突都沒揭露。審計本身的可信度如何驗證？
- **證據**：6 萬星的數字來源是什麼時間點的快照？這些星有多少是機器人（Bot）或短期炒作造成的？
- **觀點**：Garry Tan 作為 YC 總裁有強烈誘因蒐集開發者行為資料（這對 YC 評估新創趨勢極有價值）。這個背景是否改變了「治理滯後」的解讀？
- **後果**：若產業因此建立「遙測必須 opt-in」的共識，現有大量已經 opt-out-by-default 的工具（包括 VS Code、IntelliJ）會面臨怎樣的反彈？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — Admin Key 繞過 RLS 的漏洞若被攻擊者利用，可能外洩全部使用者的工作目錄路徑、專案名稱、分支名、活躍時間。對商業機密和併購資訊洩漏的風險極高
2. **什麼情況下會失敗？** — 當使用者在機密專案、受管制行業（金融/醫療/軍工）、或使用含 NDA 內容的 repo 時，即使 `off` 也不建議使用，因為網路請求仍會發出（只是內容減少），可被用作 side channel 追蹤
3. **有沒有更好的替代方案？** — 替代方案一：Fork gstack 並移除所有 telemetry 程式碼，維護純淨版本（高成本高安全）；替代方案二：使用 Superpowers + GSD 組合避開 gstack（功能略少但無爭議）；替代方案三：只使用 Claude Code 原生 subagents 自行配置（最乾淨但要花時間建設定）

## References

- [原文 — 六萬星就等於安全嗎？gstack 遙測爭議](https://tznthou.com/posts/gstack--mnjvllm4)
- [gstack GitHub Repo](https://github.com/garrytan/gstack)
- Issue #467（session 檔案讀取審計）、#675（Admin Key 誤用）、#750（修復中）
