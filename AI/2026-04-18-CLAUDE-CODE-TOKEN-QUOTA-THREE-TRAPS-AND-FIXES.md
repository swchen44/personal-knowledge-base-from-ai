---
title: "Claude 額度瞬間爆掉？你可能踩了這三個雷——快取失效、尖峰時段與環境膨脹的完整解法"
date: 2026-04-18
category: AI
tags:
  - "#ai/claude-code"
  - "#ai/token-management"
  - "#productivity/workflows"
source: "https://www.youtube.com/watch?v=rQmTWRu8fJ8"
source_type: video
author: "Dustin"
status: notes
channel: "AgentCrew Academy"
duration: "5:20"
transcript_method: youtube-transcript-api
links:
  - "[[2026-04-15-AI-DEVELOPER-EVOLUTION-PRACTITIONER-GUIDE-PERE-VILLEGA]]"
  - "[[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]]"
  - "[[2026-04-17-CLAUDEMD-MYTHS-DEBUNKED-SOURCE-CODE-VERIFICATION]]"
  - "[[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]]"
---

## 摘要（Summary）

AgentCrew Academy 的 Dustin 整理了 Claude（含 Claude Code）額度快速耗盡的三大原因及對應解法。影片雖短（5 分鐘），但涵蓋了多數使用者會踩到的坑：使用過高階模型、撞到尖峰時段視窗縮減、以及最常被忽略的**快取（Prompt Cache）失效**問題。解法包含快取保持策略、`/compact` 與 `/clear` 使用時機、以及精簡 CLAUDE.md / rules / MCP 降低每次對話起始成本。

## 關鍵洞察（Key Insights）

- **快取失效是額度爆掉的最大隱形原因** — Max 方案快取保留 1 小時、Pro 方案只有 5 分鐘；閒置超時後整包對話重新計費，參見 [[2026-04-15-AI-DEVELOPER-EVOLUTION-PRACTITIONER-GUIDE-PERE-VILLEGA|Pere Villega 系列第 9 章]]
- **三個破壞快取的行為**：閒置超時、中途切換模型/思考強度、對話中貼圖片
- **環境膨脹（Environment Bloat）是隱形成本** — CLAUDE.md、rules、MCP 工具定義都會被注入上下文，預設每次都載入，參見 [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]]

## 詳細內容（Details）

### 三大原因

#### 原因 1：使用最耗額度的模型

Claude 有不同模型：Opus（最強最貴）、Sonnet（均衡）、Haiku（最快最省）。很多人不知道自己一直在用最貴的預設模型。

> [!tip] 解法
> 日常任務用 Sonnet 就夠了。把 Opus 留到真正需要深度推理（Deep Reasoning）、解複雜 bug 的時候再用。

#### 原因 2：尖峰時段視窗縮減

Anthropic 在**美東時間的尖峰時段**（台灣時間晚上八點到凌晨兩點）會縮減五小時可用額度視窗（Rate Limit Window）。

> [!warning] 注意
> 如果你剛好撞到這個時間，同樣的五小時視窗內你的額度實際上比其他時段少。盡量把工作移到晚上八點之前完成。

#### 原因 3：快取（Prompt Cache）失效

> [!important] 快取機制關鍵數字
> - **Max 方案**：快取保留 **1 小時**
> - **Pro 方案**：快取只保留 **5 分鐘**
>
> 超時後整包對話都會被重新計費。如果對話很長或包含大量檔案，重新開啟對話時吃掉的額度非常可觀。

Claude 在處理對話時，會把說過的東西、讀過的檔案暫存在記憶體（Prompt Cache）裡。下一次繼續對話時不需要重新讀一遍，就不會耗費大量額度。

### 解法：避免快取失效的三個關鍵行為

| 行為 | 說明 |
|------|------|
| **不要讓對話閒置** | Pro 不超過 5 分鐘、Max 不超過 1 小時。預期離開時先 `/compact` 壓縮上下文 |
| **不要中途切換模型或思考強度** | 這些動作也會讓快取失效 |
| **不要在對話中間貼圖片** | 貼圖片也會破壞快取暫存 |

### 解法：善用 `/compact` 與 `/clear`

> [!note] 上下文監控指令
> - `/context` — 隨時檢查上下文視窗佔用情況
> - `/statusline` — 設定狀態列（Status Line），隨時顯示佔用情況

**`/compact`（壓縮）**：
- 時機：上下文到 **60%** 時主動壓縮（不用等自動壓縮）；或一個小任務階段完成時
- 效果：把整個對話整理成摘要，繼承重要脈絡但佔用空間大幅縮小
- 技巧：可在後面加空格說明壓縮重點，例如 `/compact 保留 API 設計決策`

**`/clear`（清空）**：
- 時機：要換一個完全不相關的新任務時
- 效果：清掉所有前一任務的對話歷史，額度耗費最低

> [!tip] 經驗法則
> 小任務完成 → `/compact`；大任務完成或換主題 → `/clear`

### 解法：精簡環境文件降低起始成本

CLAUDE.md、rules、MCP 工具設定都會被 Claude Code 主動注入上下文（Context）。如果設定很長、掛了很多工具、規則大量文字，**這些都默默佔用額度**。

| 項目 | 精簡方式 |
|------|---------|
| **CLAUDE.md** | 只放全域性（Global）適用的規則 |
| **Rules** | 特定檔案才用到的規則，放在 rules 指定路徑載入（按需載入） |
| **Skills** | 特定工具或工作流的規則，放在 Skill 裡——只有呼叫時才載入，不常駐上下文，參見 [[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]] |
| **MCP** | 用不到的 MCP 工具打 `/mcp` 進去 disable 或移除 |

> [!important] 核心邏輯
> 每次對話的**起始成本**越低，同樣的額度就能做越多事情。精簡環境是一次投資、持續回報的優化。

### 完整解法總整理

```
額度快速耗盡的三個原因          對應解法
───────────────────          ─────────
1. 用了太高階的模型           → 日常改 Sonnet，Opus 留複雜任務
2. 尖峰時間撞到視窗           → 台灣時間晚上八點前完成工作
3. 快取容易失效               → 不閒置、不換模型、不貼圖
                              → 小任務完 /compact
                              → 大任務完 /clear
                              → 精簡 CLAUDE.md / rules / MCP
```

## 我的心得（My Takeaways）

這支影片最有價值的資訊是**快取保留時間的具體數字**（Max 1 小時 vs Pro 5 分鐘）和**三個破壞快取的行為**——這些在 Anthropic 官方文件中不容易找到，但對日常使用影響極大。

與 [[2026-04-15-AI-DEVELOPER-EVOLUTION-PRACTITIONER-GUIDE-PERE-VILLEGA|Pere Villega 系列]] 第 9 章的「上下文視窗求生術」相呼應——Pere Villega 是從技術面分析 autocompact 危險與 context 經濟學，Dustin 則是從**使用者體驗面**整理出實際踩坑與解法，兩者互補。

「精簡環境文件」的建議也與 [[2026-04-17-CLAUDEMD-MYTHS-DEBUNKED-SOURCE-CODE-VERIFICATION|CLAUDE.md 迷思破解]] 的結論一致：CLAUDE.md 應該只放 Claude 自己無法從 codebase 發現的資訊。

## 待補充（Open Questions）

- 快取保留時間（Max 1 小時、Pro 5 分鐘）的來源是什麼？Anthropic 官方文件有明確記載嗎？還是社群實測推斷？（建議搜尋：`Anthropic prompt cache TTL Max Pro plan documentation`）
- 「中途切換模型會讓快取失效」——這是所有模型切換都會嗎？還是只有跨家族（例如 Opus → Sonnet）才會？同家族不同版本呢？（建議搜尋：`Claude prompt cache invalidation model switch behavior`）
- 「貼圖片破壞快取」的技術原因是什麼？是因為多模態（Multimodal）輸入改變了整個 prompt 結構？還是圖片 token 太大導致快取 key 改變？（建議搜尋：`Claude multimodal prompt cache invalidation image`）
- API 使用者（非 Max/Pro 訂閱）的快取保留時間是多少？是否也適用同樣的失效規則？（建議搜尋：`Anthropic API prompt caching TTL billing`）
- 影片提到尖峰時段縮減額度視窗——這個「縮減」的比例是多少？是固定比例還是動態調整？（建議搜尋：`Anthropic rate limit peak hours window reduction 2026`）

## 相關連結（Related）

- [[2026-04-15-AI-DEVELOPER-EVOLUTION-PRACTITIONER-GUIDE-PERE-VILLEGA]] — 第 9 章「上下文視窗的實戰求生術」，從技術面分析 autocompact 與 context 經濟學
- [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] — CLAUDE.md 最佳實踐，支持本影片「精簡 CLAUDE.md」的建議
- [[2026-04-17-CLAUDEMD-MYTHS-DEBUNKED-SOURCE-CODE-VERIFICATION]] — CLAUDE.md 迷思破解，驗證「CLAUDE.md 該放什麼不該放什麼」
- [[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]] — Skill 載入、壓縮、撰寫技巧完整指南，本影片建議「把規則放 Skill」的實作參考
- [[2026-04-19-WRITING-A-GOOD-CLAUDE-MD]] — HumanLayer 的 CLAUDE.md 撰寫指南：指令預算理論支持本影片「精簡環境」的建議

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 基礎知識 | Max 快取 1 小時 / Pro 快取 5 分鐘；三個破壞快取行為（閒置、換模型、貼圖）；`/compact` 壓縮 vs `/clear` 清空 |
| **理解（半被動）** | 串聯邏輯 | 額度問題的因果鏈：環境膨脹 → 高起始成本 → 快取失效 → 整包重新計費 → 額度爆掉。快取是中介變數——即使模型選對、時段對，快取失效也會導致額度暴漲 |
| **分析（主動）** | 找出假設 | **假設 1**：快取保留時間數字來自社群實測而非官方文件，可能隨版本更新改變。**假設 2**：「精簡 CLAUDE.md」建議暗示所有內容都有同等 token 成本，但實際上 CLAUDE.md 可能有 prompt caching 優化。**未論及**：API 使用者的費率結構完全不同，影片混淆了訂閱制與 API 計費 |
| **應用（主動）** | 立即行動 | (1) 跑 `/context` 審計目前環境——特別是 MCP 數量與 CLAUDE.md 行數；(2) 在 shell profile 加 alias `cl` 為 `/statusline` 預設開啟版本 |
| **評估（主動）** | 權衡方案 | 影片建議「不貼圖」但若任務必須用圖（UI 截圖 debug），則需權衡快取失效成本 vs 描述 UI 不用圖的溝通成本。替代方案：用 agent-browser 自動截圖直接嵌入 prompt，可能不走同一個快取路徑 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「快取」在本影片中同時指 Anthropic 伺服器端的 Prompt Cache 和 Claude Code 的 conversation history——這兩者是同一回事嗎？
- **假設**：影片假設使用者都是訂閱制（Max/Pro）——但 API 計費模式完全不同，快取保留時間也可能不同，這個前提對 API 使用者是否成立？
- **證據**：「尖峰時段縮減額度視窗」的說法有 Anthropic 官方來源嗎？還是社群觀察推斷？
- **觀點**：若站在「我寧願多付錢也不要管這些」的使用者立場，這些優化技巧的投入產出比如何？
- **後果**：若所有使用者都避開尖峰時段，是否會導致新的尖峰出現在其他時段？

## References

- [原文](https://www.youtube.com/watch?v=rQmTWRu8fJ8)
