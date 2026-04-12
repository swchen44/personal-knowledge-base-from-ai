---
title: "LLM Wiki — Karpathy 的個人知識庫建構模式"
date: 2026-04-02
category: Productivity
tags:
  - "#productivity/knowledge-base"
  - "#ai/personal-kb"
  - "#ai/agent-architecture"
  - "#productivity/obsidian"
source: "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
source_type: article
author: "Andrej Karpathy"
status: notes
date_uncertain: true
links:
  - "[[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]]"
  - "[[2026-04-01-HARNESSING-CLAUDES-INTELLIGENCE]]"
  - "[[2026-04-03-KARPATHY-AI-INSANITY-AGENTS-AUTORESEARCH-MODEL-SPECIATION]]"
---

## 摘要（Summary）

Andrej Karpathy 發布在 GitHub Gist 的一份**可複製貼上給 LLM Agent** 的想法文件，闡述了「LLM Wiki」模式——一種用 LLM **增量建構並維護**個人知識庫的新典範。核心對比：傳統 RAG 每次查詢都重新檢索原始文件，知識沒有累積；LLM Wiki 則讓 LLM **一次性編譯知識**並**持續更新**——每新增一個來源，LLM 讀完就整合進既有的 wiki，更新實體頁面、修正主題摘要、標記矛盾。結果是一個**會複利成長（Compounding Artifact）** 的結構化知識資產。Karpathy 的實作是 Obsidian + LLM Agent 並排，「Obsidian 是 IDE，LLM 是程式設計師，Wiki 是程式碼庫」。

## 關鍵洞察（Key Insights）

- **這份文件本身就是 prompt**：設計成可直接貼給 OpenAI Codex、Claude Code、OpenCode 等 LLM Agent，讓 agent 和你一起實作細節
- **Wiki 是複利資產（Compounding Artifact）**：不像 RAG 每次從零檢索，Wiki 的交叉參考、矛盾標記、綜合已經預先編譯好
- **人類與 LLM 的新分工**：人類負責「策展來源、引導分析、提問」，LLM 負責「所有無聊的維護工作」——記簿記是 wiki 被荒廢的真正原因
- **三層架構（Three Layers）**：Raw Sources（不可變）→ The Wiki（LLM 完全擁有）→ Schema（CLAUDE.md 或 AGENTS.md）
- **四種操作（Four Operations）**：Ingest（吸收新來源）、Query（查詢並可回存）、Lint（健康檢查）、索引與日誌管理
- **index.md 是內容導向**、**log.md 是時間導向**——兩個特殊檔案讓 LLM 能導航數百頁的 wiki
- **好的查詢答案應該被存回 wiki**：你做的分析、比較、連結不該消失在對話歷史裡
- **Vannevar Bush 的 Memex 終於實現**：1945 年的願景，缺的最後一塊就是「誰來做維護」——LLM 解決了這個問題
- **不需要向量資料庫**：在 ~100 sources / ~幾百頁的規模，一個 index.md 檔案就夠了

## 詳細內容（Details）

### 核心理念：從 RAG 到 Wiki 的典範轉移

> [!important] Karpathy 的核心論點
> 傳統 RAG 的問題：**LLM 在每個問題上都從零重新發現知識**。沒有累積。問一個需要綜合 5 份文件的細微問題，LLM 每次都要重新找碎片、重新拼湊。

傳統 RAG 流程：
```
Query → 檢索 chunk → LLM 現場綜合 → 答案（知識消失）
```

LLM Wiki 流程：
```
Ingest：Source → LLM 讀完 → 更新 wiki 10-15 個頁面
                                    ↓
Query：Wiki（已預編譯）→ LLM 直接讀 → 答案 → 可回存為新頁面
```

> [!quote]
> 「Wiki 是一個持續、複利的資產。交叉參考已經在那裡。矛盾已經被標記。綜合已經反映了你讀過的所有內容。Wiki 隨著每個新來源和每次提問持續變得更豐富。」— Karpathy

### 三層架構（Three-layer Architecture）

```
┌─────────────────────────────────────────────────┐
│         第一層：Raw Sources（原始來源）           │
│   文章、論文、圖片、資料檔案                      │
│   不可變（Immutable）— LLM 只讀不寫               │
│   這是你的真實來源（Source of Truth）              │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         第二層：The Wiki（LLM 產生的 Markdown）   │
│   摘要頁、實體頁、概念頁、比較、總覽、綜合         │
│   LLM 完全擁有此層（Wholly Owned）                │
│   你讀，LLM 寫                                    │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         第三層：Schema（CLAUDE.md / AGENTS.md）   │
│   告訴 LLM：wiki 結構、慣例、工作流程             │
│   讓 LLM 成為紀律性維護者而非通用聊天機器人        │
│   你和 LLM 共同演化此檔案                         │
└─────────────────────────────────────────────────┘
```

### 四種核心操作（Four Operations）

#### 1. Ingest（吸收新來源）

```
你丟一個新來源進 raw 集合 → 告訴 LLM 處理
      ↓
LLM 讀取來源
      ↓
和你討論關鍵要點
      ↓
寫摘要頁面
      ↓
更新 index
      ↓
更新相關的實體頁面和概念頁面
      ↓
附加一筆日誌
      ↓
（一個來源可能觸及 10-15 個頁面）
```

> [!tip] Karpathy 的偏好
> 「我偏好一次吸收一個來源並保持參與——我讀摘要、檢查更新、引導 LLM 強調什麼。但你也可以批次吸收多個來源減少監督。」

#### 2. Query（查詢）

> [!important] 查詢的關鍵洞察
> **好的答案應該被存回 wiki**。你做的比較、分析、連結——這些有價值的東西不應該消失在對話歷史裡。這樣你的探索會像吸收來源一樣在知識庫中複利成長。

答案的輸出形式可以是：
- Markdown 頁面
- 比較表格
- Marp 投影片
- Matplotlib 圖表
- Canvas

#### 3. Lint（健康檢查）

週期性地讓 LLM 檢查 wiki 健康狀態：
- **矛盾**：頁面之間是否互相矛盾？
- **過時聲明**：新來源是否已推翻舊聲明？
- **孤立頁面（Orphan Pages）**：沒有任何入站連結的頁面
- **缺失的概念**：被提到但沒有自己頁面的重要概念
- **缺失的交叉參考**
- **資料缺口**：可以透過網路搜尋補足的空白

#### 4. Indexing & Logging

> [!note] 兩個特殊檔案
> **`index.md`**：**內容導向**。wiki 中所有頁面的目錄，每頁一行摘要、可選 metadata。按類別組織（實體、概念、來源等）。每次 ingest 後更新。查詢時 LLM 先讀 index 找相關頁面，再深入。**在 ~100 sources 規模這就夠了**，不需要 embedding-based RAG。
>
> **`log.md`**：**時間導向**。append-only 的事件記錄——ingest、query、lint pass。
> 實用技巧：每筆以一致前綴開頭（如 `## [2026-04-02] ingest | Article Title`），就可以用 unix 工具解析：
> ```bash
> grep "^## \[" log.md | tail -5
> ```
> 給你最後 5 筆事件。

### 實作環境：Obsidian + LLM Agent

```
 ┌──────────────────┐       ┌──────────────────┐
 │                  │       │                  │
 │    LLM Agent     │       │    Obsidian      │
 │  (Claude Code /  │ ◄───► │   (Graph view,   │
 │   OpenAI Codex)  │       │    wikilinks)    │
 │                  │       │                  │
 └──────────────────┘       └──────────────────┘
       ↓                             ↑
       └───────編輯/瀏覽 wiki─────────┘

 「Obsidian 是 IDE，LLM 是程式設計師，Wiki 是程式碼庫」
```

### 適用場景

| 場景 | 用途 |
|------|------|
| **個人** | 追蹤目標、健康、心理、自我提升——日誌、文章、播客筆記 |
| **研究** | 數週或數月深入某主題——論文、文章、報告，演化的論點 |
| **讀書** | 每章歸檔，建立人物、主題、劇情頁面（如 Tolkien Gateway 風格） |
| **企業/團隊** | 由 LLM 維護的內部 wiki，餵入 Slack、會議記錄、客戶通話 |
| **其他** | 競品分析、盡職調查、旅行規劃、課程筆記、嗜好深挖 |

### 小技巧（Tips & Tricks）

1. **Obsidian Web Clipper**：瀏覽器擴充套件，一鍵把網頁轉成 markdown
2. **下載圖片到本地**：
   - Settings → Files and links → Attachment folder path 設為 `raw/assets/`
   - Settings → Hotkeys 找 "Download attachments for current file" 綁定快捷鍵
   - Clip 完文章後按快捷鍵，所有圖片下載到本地——避免 URL 失效
   - **注意**：LLM 無法在單次閱讀中同時處理含 inline image 的 markdown，需要先讀文字再單獨看圖片
3. **Obsidian Graph View**：看 wiki 的形狀——什麼連到什麼、誰是樞紐、誰是孤兒
4. **Marp**：markdown 投影片格式，Obsidian 有 plugin
5. **Dataview**：對頁面 frontmatter 做查詢，動態生成表格
6. **Git repo**：wiki 就是 markdown 檔案的 git repo——免費獲得版本、分支、協作

### 可選：CLI 工具

當 wiki 變大時可能需要建構輔助工具：
- **qmd**：本地 markdown 搜尋引擎，混合 BM25/vector search 加 LLM re-ranking，有 CLI 和 MCP server
- 也可以讓 LLM 幫你 vibe-code 一個簡單的搜尋腳本

### 為什麼這個模式有效？

> [!quote]
> 「維護知識庫的繁瑣部分不是閱讀或思考——是記簿記（Bookkeeping）。更新交叉參考、保持摘要最新、標記新資料與舊聲明的矛盾、維持數十頁面間的一致性。人類放棄 wiki 是因為維護負擔成長速度快於其價值。**LLM 不會無聊、不會忘記更新交叉參考、一次可以動 15 個檔案**。Wiki 保持維護狀態，因為維護成本趨近於零。」

### 與 Memex 的連結

這個想法在精神上與 Vannevar Bush 1945 年的 Memex 相關——一個個人的、策展的知識儲存，文件之間有關聯軌跡（Associative Trails）。Bush 的願景與後來變成的 Web 不同：**私人、主動策展、文件之間的連結與文件本身一樣有價值**。Bush 無法解決的部分是「誰來做維護」，**LLM 處理了這個問題**。

## 我的心得（My Takeaways）

這份 Gist 直接命中我正在做的事情——**個人知識庫自動化**。幾個特別有啟發的點：

1. **「Wiki 是 compounding artifact」**：這是我對自己知識庫還沒有的覺悟。我一直把它當成「文章歸檔」，但 Karpathy 的模式是「每個新來源都改寫整個 wiki」。這個差異是根本的
2. **「Schema 是讓 LLM 成為紀律性維護者的關鍵」**：對照我自己的 skill（`article-to-personal-kb`），這其實就是我的 schema。應該更積極地演化它，讓它不只是「吸收」還包含「交叉參考、矛盾檢查」
3. **index.md + log.md 雙檔案**：這是我目前缺少的基礎設施。應該馬上在 personal-knowledge-base-from-ai repo 加上這兩個檔案
4. **Lint 操作**：我從來沒對自己的知識庫做過健康檢查。可以寫一個 `/lint` slash command 定期跑
5. **查詢結果回存**：這個最有用——我每次跟 Claude 聊出來的分析結果都消失在對話歷史。應該有個「把這個結論存回知識庫」的機制

對於 Karpathy 的邏輯鏈：RAG 是在每次查詢重做工作；Wiki 是預先編譯知識。這跟 Claude Code 不用 RAG 而用 Grep 的選擇是相同的哲學——**模型能力強到某個程度後，把結構性工作前置（而非在每次查詢時重做）會產生複利**。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | Compounding Artifact、三層架構（Raw Sources / Wiki / Schema）、四種操作（Ingest / Query / Lint / Index）、Memex（Vannevar Bush 1945）、qmd、Obsidian Web Clipper、Marp、Dataview、「LLM 是程式設計師，Wiki 是 codebase」類比 |
| **理解（半被動）** | 解釋概念含義及關聯 | RAG 和 Wiki 的本質差異在於「工作何時做」：RAG 在查詢時做（每次都從零），Wiki 在吸收時做（一次做完持續維護）。這和 Claude Code 用 Grep 不用 RAG 的選擇是相同的哲學——模型能力強後，把結構性工作前置會複利 |
| **分析（主動）** | 檢驗論點、找出假設 | 核心假設：「LLM 不會無聊、不會忘記更新交叉參考」——但實際上 LLM 會**忘記 context window 之外的內容**，導致交叉參考可能不一致。另一個假設：100 sources 規模 index.md 就夠——但沒有提供當 sources > 1000 時的 scaling 策略 |
| **應用（主動）** | 將知識套用情境 | (1) 在 personal-knowledge-base-from-ai repo 建立 `index.md` 和 `log.md` 兩個特殊檔案；(2) 更新 `article-to-personal-kb` skill，讓它在 ingest 新文章時**更新相關的實體頁面和交叉參考**（目前只是存檔，沒有整合）；(3) 寫一個 `/lint-kb` slash command 定期檢查矛盾、孤立頁面 |
| **評估（主動）** | 判斷方案優劣 | Karpathy Wiki vs RAG：前者前期投入大（每次 ingest 要改 10-15 頁），後者即時可用；前者查詢快、答案一致、有複利；後者查詢慢、每次可能答案不同、無累積。**個人知識庫用 Wiki，企業大規模文件用 RAG** 可能是最佳組合。vs NotebookLM：NotebookLM 是純 RAG 模式，不適合長期累積的場景 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「LLM 完全擁有 wiki 層」——當人類發現 LLM 寫錯了某個頁面時怎麼辦？修正應該由人直接編輯，還是告訴 LLM 讓它改？修正的權威性如何定義？
- **假設**：Karpathy 假設「維護成本趨近於零」——但這只在 token 成本趨近於零的前提下成立。若 wiki 成長到需要每次 ingest 都處理 50+ 頁時，token 成本可能非常可觀
- **證據**：「100 sources 規模 index.md 就夠」——這個數字的來源是什麼？是 Karpathy 自己的實驗，還是估算？到了 500 sources 會怎樣？
- **觀點**：若站在 NotebookLM 團隊的立場，他們會如何反駁「RAG 沒有累積」？他們可能會說：使用者對「持久編輯的 wiki」的接受度不如「直接丟 source 得答案」那麼高
- **後果**：若大量使用者採用這個模式，**誰擁有這個 wiki** 變成重要問題。當 LLM 寫的內容佔了 wiki 的 99%，版權、事實正確性、引用誠信都需要重新定義

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** **累積性錯誤（Cumulative Error）**。Wiki 的每次更新都依賴 LLM 對既有內容的理解，如果早期某個頁面有錯誤，後續的更新可能會進一步擴散或強化這個錯誤。不像 RAG 每次從原始文件檢索，Wiki 錯誤會「沉澱」在結構中

2. **什麼情況下會失敗？**
   - **來源矛盾時**：當新來源和舊頁面矛盾時，LLM 需要判斷誰對——這是最難的操作
   - **超大規模**：當 wiki 超過幾千頁，100-sources 的 index.md 策略會失效，需要真正的搜尋引擎
   - **跨模型切換**：不同模型對 wiki 結構的理解可能不同，切換模型會導致 wiki 品質波動
   - **人類不參與**：若使用者完全放手不讀 wiki，LLM 的錯誤會累積到無法發現

3. **有沒有更好的替代方案？**
   - **混合方案**：用 Wiki 存經過驗證的核心知識（複利），用 RAG 處理新 / 低信任度的來源。新來源先在 RAG 層驗證，確認後才整合進 Wiki
   - **人類審查門檻**：對 Wiki 的某些頁面（如 "總覽、核心主張"）設為**人類審核必要**，LLM 只能提建議不能直接改
   - **版本快照**：定期對 Wiki 做快照，讓你能回溯到任何歷史時間點的 wiki 狀態

## 待補充（Open Questions）

- Karpathy 個人的 LLM Wiki 實際有多大規模（頁面數、sources 數）？他有沒有公開過自己的 wiki 結構或部分內容作為參考？（建議搜尋：`Karpathy personal wiki scale sources obsidian`）
- 當 wiki 規模超過 1000 頁時，`index.md` 單一索引檔是否足夠？Karpathy 提到的 `qmd` 工具的實際效能與準確率如何？（建議搜尋：`qmd markdown search engine BM25 vector performance benchmark`）
- LLM Wiki 的 Ingest 操作每次會觸及 10-15 個頁面——這個數字是基於什麼樣的 wiki 規模和 source 類型得出的？對於高度技術性的論文或長篇書籍，這個數字會顯著增加嗎？（建議搜尋：`LLM wiki ingest pages touched per source`）
- 在「LLM 完全擁有 wiki 層」的設計下，若 LLM 在某次 ingest 後錯誤地修改了多個頁面，如何有效率地回溯和修正？git diff 是否足夠，還是需要額外的 audit trail？（建議搜尋：`LLM wiki error correction rollback audit trail git`）
- 不同 LLM（Claude、GPT-4、Gemini）維護同一份 wiki 時，對頁面結構、摘要風格、交叉參考風格的一致性有何影響？切換模型後，wiki 品質是否會出現明顯的「風格斷層」？（建議搜尋：`LLM wiki cross model consistency style transfer obsidian`）
- Karpathy 提到 wiki 適合「企業/團隊」使用案例（如 Slack、會議記錄），但多人協作的 LLM Wiki 如何處理衝突：當兩個人同時 ingest 不同來源並更新同一頁面時，版本衝突如何解決？（建議搜尋：`LLM wiki collaborative editing conflict resolution multi-user`）

## 相關連結（Related）

- [[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]] — Claude Code Agent 的實作層面，與本文的 Schema（CLAUDE.md）概念直接對應
- [[2026-04-01-HARNESSING-CLAUDES-INTELLIGENCE]] — Anthropic 的「讓 Claude 管理自己的 context」哲學，與本文「LLM 擁有 wiki 層」呼應
- [[2026-04-03-KARPATHY-AI-INSANITY-AGENTS-AUTORESEARCH-MODEL-SPECIATION]] — Karpathy 的其他核心觀點（Token 焦慮、自動研究），這份 Gist 是他實踐的一部分
- [[ARTICLE-TO-PERSONAL-KB-SKILL]] — 我自己的 skill 實作，需要根據本文啟示升級為「ingest + 更新交叉參考」
- [[MEMEX-VANNEVAR-BUSH]] — Vannevar Bush 1945 年的 Memex 願景原始論文
- [[OBSIDIAN-AS-IDE]] — Obsidian 作為知識庫 IDE 的使用模式

## References

- [原文 Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — Andrej Karpathy, GitHub Gist
- [Vannevar Bush: As We May Think (1945)](https://www.theatlantic.com/magazine/archive/1945/07/as-we-may-think/303881/) — Memex 的原始論文
- [Tolkien Gateway](https://tolkiengateway.net/wiki/Main_Page) — 文中提到的 fan wiki 範例
- [qmd](https://github.com/tobi/qmd) — Tobi 的本地 markdown 搜尋引擎
- [Obsidian Web Clipper](https://obsidian.md/clipper) — 瀏覽器網頁剪輯工具
- [Marp](https://marp.app/) — Markdown 投影片工具
