---
title: "Claude Code 原始碼洩漏！11 個隱藏秘密完整解析"
date: 2026-04-02
category: DevTools
tags:
  - "#devtools/claude-code"
  - "#ai/agent-architecture"
  - "#ai/context-engineering"
source: "https://www.youtube.com/watch?v=Xm84gXIG7hE"
source_type: video
author: "Programmer Fish Skin（程序員魚皮）"
status: notes
channel: "Programmer Fish Skin"
duration: "20:08"
transcript_method: youtube-transcript-api
links:
  - "[[CLAUDE-CODE-ARCHITECTURE]]"
  - "[[REACT-AGENT-PATTERN]]"
  - "[[CONTEXT-ENGINEERING]]"
---

## 摘要（Summary）

2026年4月，Claude Code 2.1.88 版本的 npm 發布包意外包含了 Source Map 檔案，導致 51 萬行 TypeScript 原始碼完整洩漏。這支影片透過 AI 輔助深入解析原始碼，揭露了 Claude Code 的 11 個核心設計秘密——從 Agent 循環（Agent Loop）、三層記憶架構（Three-tier Memory Architecture）、五級上下文壓縮（Five-level Context Compression），到反蒸餾（Anti-distillation）與臥底模式（Undercover Mode）。對於任何在做 AI 應用開發的人，這份原始碼堪稱目前最好的 AI 應用架構教材。

## 關鍵洞察（Key Insights）

- **洩漏原因**：打包工具 Bun 預設生成 Source Map 檔（59.8MB JSON），工程師發布時忘了排除 `.map` 檔——這是 Claude Code 發布以來**第二次**犯同樣錯誤
- **架構本質**：Claude Code 的核心 Agent 循環就是一個 `while(true)` 無限迴圈，使用經典 ReAct（推理加執行）機制，沒有什麼神秘的黑科技
- **不用 RAG**：內容檢索完全用 Grep 文字搜尋，不用向量資料庫（Vector Database）——模型越強，讓 AI 自己決定搜什麼反而效果更好
- **預設安全（Fail-closed）**：工具設計預設 `isConcurrencySafe=false`、`isReadOnly=false`，不宣告就當危險操作處理
- **YOLO 模式有影子 AI**：`dangerously-skip-permissions` 模式背後偷跑一個 AI 分類器（`yoloClassifier.ts`）持續把關，加上共 5 個安全關卡
- **反蒸餾策略**：往 API 請求中注入假工具定義，讓競爭對手蒸餾訓練的模型越訓越差（反間計）
- **記憶不存程式碼**：三層記憶系統只記人的偏好與判斷，不記程式碼行號——因為程式碼會變，但記憶不會自動更新，防止產生誤導性快取

## 詳細內容（Details）

### 洩漏機制解析

Source Map 是開發環境用於 debug 的翻譯對照表（一個 JSON 檔），包含：
- `sources`：所有源檔案的路徑陣列
- `sourcesContent`：每個檔案的完整原始碼陣列

只要寫個腳本解析這個 JSON，就能完整還原所有原始碼。某安全研究員在 X 上發現，數小時內 GitHub 出現多個鏡像，其中一個不到一天就將近 10 萬 Star。

> [!warning] 重複犯錯
> 這是 Claude Code 發布以來第二次出現相同事故（第一次是 2025 年 2 月），令人懷疑是 Vibe Coding 過度依賴 AI 導致忽略基本發布流程。

### 六層架構總覽

```
┌─────────────────────────────────────────────────┐
│          CLI / 介面層（React Ink 框架）            │
│         終端機互動 UI，用 React 寫命令列介面         │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│            Agent 循環引擎（query.ts）              │
│         while(true) ReAct 決策核心                │
└──────┬──────────────┬──────────────┬────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼────────────┐
│  工具系統    │ │  記憶系統   │ │  上下文壓縮系統   │
│ 40+ 內建工具 │ │  三層架構   │ │  五級壓縮策略     │
│ + MCP 擴展  │ │            │ │                  │
└─────────────┘ └────────────┘ └─────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│               權限與安全系統                       │
│    YOLO 模式影子 AI + 5 個安全關卡 + 20+ 規則      │
└─────────────────────────────────────────────────┘
```

### 秘密一：Agent 循環是 `while(true)`

`query.ts` 核心邏輯：

```
while(true):
  1. 上下文壓縮（若需要）
  2. 呼叫大模型（claude.ts → queryModel）
  3. 若回應包含 tool_use → 執行工具 → 追加結果 → 繼續循環
  4. 若無 tool_use → 任務完成 → 退出循環
```

> [!note] ReAct 機制（Reasoning + Acting）
> 讓 AI 形成「思考→行動→觀察→再思考」的閉環，這是當前 AI Agent 的主流設計模式。

原始碼中還有一段工程師留下的「**巫師守則（Wizard Rules）**」注釋——三條關於 thinking block 處理的約束規則，違反者「將受到整整一天 debug 和薅頭發的懲罰」。

### 秘密二：工具設計的 Fail-closed 原則

`Tool.ts` 的 `buildTool` 工廠函數設計：

```typescript
// 預設值設計
isConcurrencySafe: false  // 預設不允許並發
isReadOnly: false          // 預設視為危險操作
```

**如果開發者忘了宣告「我只是讀檔」，系統自動當成危險操作處理。**

> [!tip] Fail-closed 設計哲學
> 就像公司門禁：沒刷卡預設進不去。對 AI 應用而言，「預設禁止」比「預設允許」安全太多——Claude Code 直接操作整個程式碼庫，一旦出錯可能半個月的程式碼都白寫。

### 秘密三：讀寫分離的工具並發

```
並發上限：預設 10 個工具同時執行（可透過環境變數調整）

執行邏輯：
─────────────────────────────────────────
 [讀取A] [讀取B] [讀取C] → 可同時並發執行
      ↓
 [寫入D] → 必須等前面所有操作完成才執行
─────────────────────────────────────────

批次完成後，上下文修改排隊依序應用
（不立即生效，等整批完成再合併）

異常處理：判斷方法本身拋出異常 → 也當作不安全處理
```

### 秘密四：系統提示詞的快取分裂（Prompt Cache Splitting）

```
系統提示詞結構：

┌────────────────────────────────────┐
│         靜態部分（全球共享）          │
│  所有用戶共用同一份 Prompt Cache     │
├──── 動態邊界標記（dynamic boundary）┤
│         動態部分（每人獨立）          │
│  - 當前時間                         │
│  - Git 倉庫狀態                     │
│  - CLAUDE.md 規則                  │
└────────────────────────────────────┘
```

> [!warning] 快取失效陷阱
> 如果把動態內容混入靜態部分，每個用戶的提示詞都不一樣，全球共享的快取就全廢了。這個優化技巧對高流量 AI 應用可以大幅節省成本。

### 秘密五：不用 RAG，用 Grep

業界主流做法：RAG（Retrieval-Augmented Generation，檢索增強生成）
→ Embedding → 向量資料庫 → 語義搜尋 → 傳給模型

Claude Code 的做法：**直接用 Grep 文字搜尋**

> [!quote]
> 「我們試過 RAG，但發現讓 AI 自己決定搜什麼、怎麼搜，效果遠遠好於 RAG。」— Boris Cherny（Claude Code 創始人）

類比：
- RAG = 你幫實習生整理好相關資料打包給他看
- Grep = 直接給他公司文件庫的權限讓他自己找

**模型能力越強，後者優勢越大。** 而且 Grep 沒有索引過期問題、不用維護向量資料庫，工程複雜度降一個量級。

### 秘密六：三層記憶架構（Three-tier Memory Architecture）

```
層次      儲存內容                限制                  載入方式
─────────────────────────────────────────────────────────────────
第一層    MEMORY.md（索引目錄）    最多200行 / 25KB      每次對話全部載入
          只存指針不存內容         每行≤150字符

第二層    話題檔案（Topic Files）  最多5個相關檔案        Sonnet 小模型選擇
          偏好/架構約定/踩過的坑

第三層    歷史對話（History）      無固定上限             Grep 關鍵字搜尋
          特定格式儲存
```

**MEMORY.md 截斷機制**：超出限制時在最後換行符處切割（不切斷行的中間），並追加 WARNING 告知 AI 索引未完整載入。

> [!important] 記憶不存程式碼的設計哲學
> 記憶只存人的偏好與判斷，程式碼事實永遠去原始碼實時讀取。這從根源上消滅了「快取與資料庫不一致」這個最常見的 Bug。

記憶挑選規則中有個 punchline：**「如果某個工具正在被使用，不要載入它的使用文件——因為你都在用了說明你會用；但一定要載入它的已知問題和坑點。」**

### 秘密七：五級上下文壓縮（Five-level Context Compression）

```
上下文佔用增加
      │
      ▼
[第一級：剪裁（Trim）]
  舊的工具呼叫結果只保留結構，丟棄內容
      │
      ▼（若仍不足）
[第二級：微壓縮（Micro-compression）]
  體積大的工具執行結果卸載到快取（不是丟掉）
      │
      ▼（若仍不足）
[第三級：上下文折疊（Context Folding）]
  對中間對話進行摘要，只保留關鍵資訊
      │
      ▼（佔用超過閾值）
[第四級：自動壓縮（Auto-compression）]
  觸發全量摘要壓縮
      │
      ▼（API 返回 413 錯誤）
[第五級：應急壓縮（Emergency Compression）]
  緊急觸發

        ⚡ 斷路器（Circuit Breaker）
  連續失敗 3 次 → 自動停止重試
  （2026-03-10 發現：1000+ 個 session 連續壓縮失敗 50+ 次，
   最誇張的一個 session 失敗了 3000+ 次還在重試）
```

### 秘密八：YOLO 模式的影子 AI

`dangerously-skip-permissions`（YOLO）模式並非完全不設防：

```
一次工具呼叫的 5 個安全關卡：

1. Feature Flag 檢查
2. 工具本身的安全屬性（isConcurrencySafe / isReadOnly）
3. 影子 AI 分類器（yoloClassifier.ts）→ 每次主 AI 要執行操作都過一遍
4. Bash 命令安全檢查（20+ 條規則，定義於專門檔案）
5. 最終權限確認
```

### 秘密九：Feature Flag 洩露的產品路線圖

| 功能名稱 | 描述 |
|---------|------|
| KAIROS 長期助手模式 | AI 可 24 小時持續運行不結束 |
| AutoDream 自動做夢 | AI 白天工作記筆記，晚上自動整理記憶 |
| 多 Agent 協作模式 | 一個 AI 指揮多個 AI 協同工作 |
| 語音模式（Voice Mode） | 語音操作 Claude Code |
| 瀏覽器操作工具 | 控制瀏覽器進行自動化操作 |

### 秘密十：反蒸餾（Anti-distillation）策略

有些競爭對手透過錄製 API 流量來「蒸餾」Claude Code 的能力——把大模型的輸入輸出錄下來，訓練自己的小模型。

Anthropic 的應對：**在 API 請求中注入假的工具定義**，讓競爭對手拿去訓練的模型越訓越差。本質是反間計（Counter-intelligence）。

### 秘密十一：臥底模式（Undercover Mode）

Anthropic 內部員工用 Claude Code 向開源專案提交程式碼時，會自動啟用臥底模式：
- 預設開啟，無法強制關閉
- 只有倉庫被確認為**內部倉庫**時才關閉
- 目的：防止內部模型代號、隱私資訊透過開源貢獻洩漏

### 彩蛋：數字寵物系統

`buddy/` 目錄下藏著一套尚未發布的數字寵物系統（鴨子、鵝、貓、龍...），原本計畫後續上線，結果因為原始碼洩漏提前被大家發現。

> [!note] 工程師的浪漫
> Anthropic 工程師準備讓 AI 寫程式累了之後還能去撸 AI 寵物。

還有一個小細節：因為 Claude 老是浪費一輪對話去執行「檢查目錄是否存在」的命令，工程師直接在檔案中硬編碼一行提示：「這個目錄已經存在了，直接用 Write 工具往裡寫就行。」

## 我的心得（My Takeaways）

這份原始碼最驚人的地方是：Claude Code 的核心技術全都是業界已知的基礎設計——`while(true)` 循環、讀寫分離、分層快取、斷路器、功能開關——沒有任何神秘的黑科技。但 Claude Code 把這些東西組合到了 AI 場景裡，打磨到極致細節（MEMORY.md 截斷邏輯、記憶挑選規則的 punchline、壓縮斷路器的加入）。

幾個最有啟發性的設計決策：
1. **不用 RAG 的決定**：反直覺但有道理。模型越強，讓 AI 自主決策越好。「哪些能力交給工程系統、哪些留給 AI 模型」這個邊界值得持續重新評估
2. **Fail-closed 預設值**：工具預設安全屬性為危險，需要主動宣告安全。這個設計在不確定性高的 AI 場景特別重要
3. **記憶不存程式碼**：從根源消滅快取不一致問題，而不是試圖解決它

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，建立基礎知識 | ReAct 機制、三層記憶架構（MEMORY.md/話題檔案/歷史對話）、五級壓縮策略、Fail-closed 原則、`yoloClassifier.ts`、Source Map 洩漏原因、Feature Flags（KAIROS/AutoDream） |
| **理解（半被動）** | 解釋概念含義及關聯 | `while(true)` + ReAct = AI 能連續自主工作的本質；提示詞快取分裂 = 靜態部分共享降成本、動態部分個人化；記憶不存程式碼 = 從設計上消除快取不一致；Grep 取代 RAG = 模型能力越強，自主搜尋優於預處理索引 |
| **分析（主動）** | 檢驗論點、找出假設 | 關鍵假設：「模型越強，Grep 效果越好於 RAG」——這在模型能力仍有限時可能不成立；五級壓縮的第3000次重試問題說明自動化系統需要明確的失敗上限（斷路器）；Feature Flag 洩露路線圖，說明安全審計不只是程式碼，也包括功能設計資訊 |
| **應用（主動）** | 將知識套用情境 | (1) 在自己的 AI 應用中實作提示詞快取分裂（靜態/動態邊界），減少 token 成本；(2) 工具設計採用 Fail-closed 預設值，強制開發者主動宣告安全屬性 |
| **評估（主動）** | 判斷方案優劣 | RAG vs Grep：RAG 在語意搜尋上有優勢（近義詞匹配），但維護成本高、有索引過期問題；Grep 簡單可靠但依賴精確關鍵字；最佳選擇取決於模型能力和工程資源。三層記憶與純 RAG 相比，三層記憶更可控但需要更多設計，RAG 更通用但準確度可能不如 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「記憶只存偏好與判斷，不存程式碼」——這個邊界在實際操作中如何維護？如果用戶或 AI 不小心把程式碼細節寫進記憶怎麼辦？
- **假設**：影片假設反蒸餾策略（注入假工具定義）有效——但競爭對手是否能透過比對多次 API 呼叫的一致性來識別並過濾假數據？
- **證據**：「讓 AI 自己決定搜什麼效果遠好於 RAG」這個結論是基於什麼基準測試？是否有公開數據或只是主觀評估？
- **觀點**：從競爭對手角度看，Source Map 洩漏到底值多少錢？核心技術（`while(true)` + ReAct）並非祕密，真正難以複製的是哪些部分？
- **後果**：若 KAIROS（24小時持續運行）正式上線，對 token 成本和用戶數據安全有什麼影響？用戶是否能接受 AI 在沒有交互的情況下持續訪問其程式碼庫？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** 三層記憶系統的最大風險是「記憶腐爛（Memory Rot）」——偏好記憶在初期很準確，但隨著時間推移和項目演進，舊的記憶可能變成誤導；目前沒有看到自動記憶過期或驗證機制

2. **什麼情況下會失敗？** 五級壓縮在「每一級都無法有效壓縮」的情況下失敗（如上下文裡全是無法摘要的二進位數據）；Grep 搜尋在記憶檔案本身索引失效或用戶不按規律組織記憶時效果會大幅下降

3. **有沒有更好的替代方案？** 記憶系統可以考慮加入**時間衰減（Time Decay）**機制，讓舊記憶的權重隨時間降低；上下文壓縮可以探索**結構化壓縮**（保留工具呼叫的 schema 但壓縮內容）vs 當前的純摘要方式

## 待補充（Open Questions）

- 五級上下文壓縮中，第三級「上下文折疊（Context Folding）」的摘要是由主模型執行還是獨立的較小模型？折疊後的摘要是否有品質驗證機制，以防止關鍵資訊遺失？（建議搜尋：`Claude Code context folding compression model quality`）
- 反蒸餾（Anti-distillation）策略中注入的「假工具定義」是否在每次 API 請求都注入，還是只在特定條件下啟用？Anthropic 是否有公開說明過這個機制的存在？（建議搜尋：`Claude Code anti-distillation fake tool definitions API`）
- KAIROS（24小時持續運行模式）與 AutoDream（自動整理記憶）的功能旗標是否在洩漏後仍存在於最新版本？有沒有預計的公開上線時間？（建議搜尋：`Claude Code KAIROS AutoDream feature flag release timeline`）
- 三層記憶系統中，「第二層話題檔案的選擇」是由 Sonnet 模型負責——這個選擇過程有沒有一致性保證？若不同版本的 Sonnet 選擇不同的相關檔案，會導致什麼問題？（建議搜尋：`Claude Code memory topic file selection consistency`）
- `yoloClassifier.ts` 的影子 AI 分類器使用什麼模型？是輕量化的分類模型還是完整的語言模型？其判斷結果是否可被用戶查看或覆蓋？（建議搜尋：`Claude Code yoloClassifier model safety shadow AI`）
- 提示詞快取分裂（Prompt Cache Splitting）的「動態邊界」是如何定義的？是固定的分隔符還是由 Claude Code 動態計算，並且這個機制是否在 Claude API 文件中有公開說明？（建議搜尋：`Claude API prompt cache splitting dynamic boundary`）

## 相關連結（Related）

- [[CLAUDE-CODE-ARCHITECTURE]] — Claude Code 架構設計整體概覽
- [[REACT-AGENT-PATTERN]] — ReAct（推理+執行）機制的設計模式詳解
- [[CONTEXT-ENGINEERING]] — 上下文工程（Context Engineering）最佳實踐
- [[PROMPT-CACHE-OPTIMIZATION]] — 提示詞快取（Prompt Cache）優化技巧
- [[FAIL-CLOSED-DESIGN]] — Fail-closed 設計哲學在系統架構中的應用
- [[2026-03-02-PSA-CLAUDE-CODE-PLUGINS-LOADING-TWICE-KILLING-CONTEXT]] — 外掛重複載入導致上下文浪費，與原始碼中的技能注入機制直接相關
- [[2026-02-28-2-MINUTE-CLAUDE-CODE-UPGRADE-LSP]] — LSP 工具是原始碼中隱藏的實驗性功能之一
- [[2026-03-25-AI-BUG-FINDING-VULNPOCALYPSE]] — 使用 Claude Code `--dangerously-skip-permissions` 模式進行漏洞研究的實戰案例
- [[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]] — 基於同份洩漏原始碼，深入拆解記憶系統的十大設計細節
- [[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]] — 基於同份洩漏原始碼，深入分析 Team Memory Server 與 REST API
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — 基於同份原始碼，深入追蹤 CLAUDE.md 與 Skills 的快取與熱載入機制
- [[2026-04-17-CLAUDE-CODE-FEEDBACK-FRUSTRATION-DETECTION-EVENTMETADATA-ARCHITECTURE]] — 基於同份原始碼，深入分析反饋系統、挫折偵測演算法與 EventMetadata 傳送架構

## References

- [YouTube 影片](https://www.youtube.com/watch?v=Xm84gXIG7hE) — Programmer Fish Skin, 2026-04-02
- [Claude Code npm 包](https://www.npmjs.com/package/@anthropic-ai/claude-code) — 原始碼洩漏來源
