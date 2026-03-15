---
name: add-article
description: >
  Standard SOP for adding a new knowledge note to this personal knowledge base.
  Combines Obsidian knowledge-graph techniques (wikilinks, Bases-compatible frontmatter,
  callouts, Canvas hints) with YouTube transcript workflows.
  All notes are written in Traditional Chinese (Taiwan) with English proper nouns
  preserved in brackets — e.g., 知識圖譜 (Knowledge Graph).
license: MIT
allowed-tools: read write
metadata:
  author: swchen44
  version: "2.0.0"
  category: knowledge-management
---

# 加入文章 (Add Article) — 知識圖譜 (Knowledge Graph) 標準流程 (SOP)

## 目的 (Purpose)

每一篇筆記都要做到兩件事：**記錄知識**，以及**連結到其他知識**。
沒有雙向連結的筆記是孤島；有完整雙向連結、前置資料 (frontmatter)、標籤 (tags) 的筆記，
則是能自我成長的知識圖譜 (Knowledge Graph) 節點。

此技能 (skill) 確保每篇筆記皆：
- **可搜尋 (Discoverable)** — 透過標籤 (tags)、屬性 (properties)、Bases 資料庫檢視
- **互相連結 (Connected)** — 透過雙向連結 (wikilinks) 建立圖譜邊 (graph edges)
- **可閱讀 (Readable)** — 透過 callout 區塊與結構化章節
- **可視覺化 (Visualizable)** — 可出現在 Canvas 心智圖 (mind map) 中

---

## 🌐 語言規則 (Language Rule)：台灣繁體中文 + 保留英文專有名詞

> [!important] 所有筆記內容一律以**台灣繁體中文**撰寫，遵守以下規則：

### 規則一：中文翻譯 + 括號保留英文原文
當一個專有名詞被翻譯成中文時，**必須在中文後加上括號 () 標示英文原文**。

| ✅ 正確寫法 | ❌ 錯誤寫法 |
|-----------|-----------|
| 知識圖譜 (Knowledge Graph) | 知識圖譜 |
| 大型語言模型 (Large Language Model) | LLM 模型 |
| 提示工程 (Prompt Engineering) | prompt engineering |
| 自主代理人 (Autonomous Agent) | 自主 agent |
| 前置資料 (Frontmatter) | 前置資料 |
| 雙向連結 (Wikilink) | 雙向連結 |
| 上下文視窗 (Context Window) | 上下文窗口 |

### 規則二：工具名稱、品牌名稱直接使用英文
以下類型**不翻譯**，直接保留英文：

- 工具 / 軟體名稱：Obsidian、Claude、GitHub、yt-dlp、Whisper、NotebookLM
- 程式語言 / 框架：Python、JavaScript、YAML、Markdown
- 指令 / 標籤名稱：`tags`、`source_type`、slash command
- 縮寫廣為人知者：API、CLI、SDK、LLM、AI（可單獨使用，無需展開）

### 規則三：雙向連結 (Wikilink) 檔名維持英文全大寫
`[[CLAUDE-MEMORY-ENGINE]]` — 檔名格式不變，可在正文中以中文描述

### 規則四：引用原文時保留原語言
區塊引用或程式碼中若引用原文英文，不需翻譯。

---

## 步驟一：確定分類 (Category) 與檔名 (Filename)

選擇正確的資料夾：

| 分類 | 使用時機 |
|------|---------|
| `AI/` | 人工智慧 (AI) 框架、大型語言模型 (LLM)、代理人 (Agent)、提示工程 (Prompt Engineering)、機器學習 (ML) |
| `Videos/` | YouTube 影片、演講、教學影片 |
| `WebArticles/` | 部落格文章、新聞、評論文章 |
| `Research/` | 學術論文、技術深入探討 |
| `Books/` | 書籍摘要與重點整理 |
| `Productivity/` | 工作流程 (Workflow)、個人系統 (Personal System)、GTD、工具 |
| `DevTools/` | 開發者工具、CLI、SDK、編輯器 |
| `Finance/` | 投資、經濟學 (Economics)、金融科技 (Fintech) |
| `Design/` | 使用者介面 (UI/UX)、產品設計、視覺思考 (Visual Thinking) |
| `Science/` | 物理、生物、天文、普通科學 |
| `OpenSource/` | 開源專案 (Open Source Project) 與社群 |
| `Security/` | 資訊安全 (Cybersecurity)、隱私 (Privacy)、資安 (InfoSec) |

**檔名規則**：全大寫英文加連字號 (ALL-CAPS with hyphens)，例如：`AI/CLAUDE-AGENTS-OVERVIEW.md`

---

## 步驟二：建立前置資料 (Frontmatter)（Bases 相容格式）

每篇筆記必須以 YAML 前置資料 (frontmatter) 開頭。
這些欄位讓筆記可在 Obsidian Bases 中建立資料庫檢視。

```yaml
---
title: "筆記完整標題（台灣繁體中文）"
date: YYYY-MM-DD
category: AI
tags:
  - tag1
  - tag2
  - tag3
source: "https://original-url.com"
source_type: article   # article | video | paper | tool | book | podcast
author: "原作者姓名"
status: notes          # notes | reviewed | complete
links:
  - "[[RELATED-NOTE-1]]"
  - "[[RELATED-NOTE-2]]"
---
```

**影片筆記額外欄位**（`Videos/` 分類使用）：
```yaml
channel: "頻道名稱 (Channel Name)"
duration: "00:00"
transcript_method: yt-dlp   # yt-dlp | whisper | notebooklm | manual
```

> [!tip] 為何 Frontmatter 很重要
> 每個欄位都可在 .base 檔案中作為篩選條件或公式。
> 若跳過 `status`，就無法建立「顯示所有未審閱筆記」的檢視。
> 一致的前置資料 (frontmatter) = 強大的可查詢資料庫 (queryable database)。

---

## 步驟三：撰寫筆記正文 + 雙向連結 (Wikilinks)

使用以下結構，**一律以台灣繁體中文撰寫**，並遵守語言規則：

```markdown
## 摘要 (Summary)
一段說明：這是什麼、為何重要。

## 關鍵洞察 (Key Insights)
- 洞察一 — 參見 [[RELATED-CONCEPT]]（相關概念）
- 洞察二
- 洞察三

## 詳細內容 (Details)
更深入的筆記、引用、程式碼片段、圖表。

> [!note] 關鍵術語 (Key Term)
> 用 callout 定義重要術語，使其在圖譜檢視中突出顯示。

> [!tip] 可執行建議 (Actionable Tip)
> 用 tip callout 記錄你實際可以做的事。

> [!warning] 注意事項 (Watch Out)
> 用 warning callout 記錄陷阱、限制或風險。

## 我的心得 (My Takeaways)
我學到了什麼，以及如何應用。

## 相關連結 (Related)
- [[RELATED-NOTE-1]] — 連結理由簡述
- [[RELATED-NOTE-2]] — 連結理由簡述
- [[RELATED-NOTE-3]] — 連結理由簡述
```

### 雙向連結 (Wikilink) 策略 — 知識圖譜的核心

雙向連結使筆記形成圖譜，而非一堆散落的檔案。

**原則：**
- 在 `## 相關連結` 區塊至少連結 **3 篇相關筆記**
- 在正文中提及某個已有獨立筆記的概念時，即時連結：`使用[[Transformer 架構 (Architecture)]]`
- 若相關筆記尚不存在，仍可先寫下雙向連結 — 它會顯示為待建立的紅色連結
- 使用 `[[Note Name|顯示文字]]` 當筆記名稱不適合直接出現在句子中

**標籤 (Tag) 策略**：每篇筆記使用 3–5 個標籤，使用巢狀標籤提升精確度：
`#ai/llm`、`#tools/cli`、`#productivity/workflows`

---

## 步驟四：Callout 類型參考

```markdown
> [!note] 標題       — 一般筆記、觀察
> [!tip] 標題        — 可執行建議
> [!warning] 標題    — 注意事項、風險
> [!info] 標題       — 背景資訊
> [!example] 標題    — 具體範例
> [!quote] 標題      — 值得保留的直接引用
> [!abstract] 標題   — 摘要
> [!todo] 標題       — 待辦事項 (Action Items)
> [!important] 標題  — 重要規則或必讀資訊

> [!faq]- 折疊標題   — 加上 - 預設折疊
> 點擊後才展開。
```

---

## 步驟五：嵌入 (Embeds)（選用但強大）

```markdown
![[ARCHITECTURE-DIAGRAM.png|600]]          — 嵌入圖片
![[CONCEPT-NOTE#關鍵章節]]                 — 嵌入另一篇筆記的某個章節
![[MyBase.base#Active Projects]]           — 嵌入 Bases 資料庫檢視
```

---

## 📺 YouTube 知識圖譜工作流程 (YouTube Knowledge Graph Workflow)

專屬 `Videos/` 分類的工作流程，用於擷取、轉錄 (transcribe) 並將 YouTube 內容轉換為結構化知識筆記。

### 方法一 (Method 1)：yt-dlp（推薦）
適用於有官方或自動產生字幕的影片。

```bash
# 安裝
pip install yt-dlp

# 下載自動產生字幕（優先繁體中文，次選簡體中文，再選英文）
yt-dlp --write-auto-sub --sub-lang "zh-Hant,zh-Hans,en" --skip-download "YOUTUBE_URL"

# 轉換為 SRT 格式
yt-dlp --write-sub --write-auto-sub --convert-subs srt --skip-download "YOUTUBE_URL"

# 同時下載影片描述文字
yt-dlp --write-description --write-auto-sub --skip-download "YOUTUBE_URL"
```

### 方法二 (Method 2)：Python youtube-transcript-api
適用於需要批次處理多部影片時。

```python
from youtube_transcript_api import YouTubeTranscriptApi
video_id = "VIDEO_ID"  # 從 URL 中的 ?v=VIDEO_ID 取得

# 優先繁體中文，退而求其次英文
transcript = YouTubeTranscriptApi.get_transcript(
    video_id,
    languages=["zh-Hant", "zh-Hans", "en"]
)

full_text = " ".join([t["text"] for t in transcript])
print(full_text)
```

安裝：`pip install youtube-transcript-api`

### 方法三 (Method 3)：無字幕 — Whisper AI 自動轉錄 (Auto-Transcription)
適用於完全沒有字幕的影片。

```bash
# 步驟一：用 yt-dlp 下載純音訊 (audio)
yt-dlp -f "bestaudio" -o "audio.%(ext)s" "YOUTUBE_URL"

# 步驟二：安裝並執行 OpenAI Whisper
pip install openai-whisper
whisper audio.mp4 --language Chinese --output_format txt

# 更快的替代方案 (alternative)
pip install faster-whisper
```

Python 範例：
```python
import whisper
model = whisper.load_model("base")  # 選項：tiny / base / small / medium / large
result = model.transcribe("audio.mp4", language="zh")
print(result["text"])
```

### 方法四 (Method 4)：Google NotebookLM（無程式碼選項）
適用於需要快速 AI 生成摘要而不寫程式碼時。

1. 前往 https://notebooklm.google.com/
2. 新增來源 (Add Source) → 貼上 YouTube 影片網址
3. NotebookLM 自動擷取字幕並生成知識摘要 (knowledge summary)
4. 使用問答 (Q&A) 面板提取重點
5. 複製輸出內容並貼入本知識庫的筆記正文格式

> 最適合：有字幕的 TED Talk、技術演講、教學影片。

### 方法五 (Method 5)：Claude AI 摘要（最快）
1. 用方法一或二取得逐字稿 (transcript) 文字
2. 貼入 Claude 並加上以下提示 (prompt)：
   > 「請將這段 YouTube 逐字稿轉換成結構化知識筆記，包含：摘要 (Summary)、關鍵洞察 (Key Insights)、關鍵概念 (Key Concepts)、以及行動項目 (Action Items)。請用台灣繁體中文撰寫，專有名詞加上括號標示英文原文。」
3. 將 Claude 的輸出貼入筆記正文並儲存至 `Videos/`

---

### Videos/ 前置資料範本

```yaml
---
title: "影片標題（台灣繁體中文）"
date: YYYY-MM-DD
category: Videos
source_type: video
source: "https://youtube.com/watch?v=VIDEO_ID"
channel: "頻道名稱 (Channel Name)"
duration: "00:00"
transcript_method: yt-dlp
tags:
  - youtube
  - tag2
---
```

`transcript_method` 選項：`yt-dlp` | `whisper` | `notebooklm` | `manual`

---

## 步驟六：更新根目錄 README.md

在根目錄 `README.md` 的 `## 📌 Recent Notes` 下新增一行：

```markdown
- [NOTE-TITLE](./CATEGORY/NOTE-TITLE.md) — 一行繁體中文說明
```

---

## 知識圖譜連結 (Knowledge Graph) 至 Bases 與 Canvas

### 何時建議建立或更新 Bases 檢視：
- 同一分類累積 3 篇以上筆記 → 建議建立 `.base` 檔案進行總覽
- 使用者想查看「所有未審閱筆記」或「本月的筆記」

### 何時建議建立或更新 Canvas 心智圖：
- 已新增多篇筆記，探討同一大主題的不同面向
- 使用者想視覺化看到概念之間的連結

Canvas 筆記節點格式：
```json
{
  "id": "<16碼十六進位>",
  "type": "file",
  "x": 0, "y": 0,
  "width": 400, "height": 300,
  "file": "CATEGORY/NOTE-NAME.md"
}
```

---

## Obsidian 語法快速參考

| 語法 | 功能說明 |
|------|---------|
| `[[筆記名稱]]` | 雙向連結 (Wikilink)（建立圖譜邊） |
| `[[筆記名稱\|顯示文字]]` | 自訂顯示文字的雙向連結 |
| `[[筆記名稱#章節]]` | 連結至特定章節 |
| `![[筆記名稱]]` | 嵌入完整筆記內容 |
| `![[圖片.png\|300]]` | 嵌入圖片並指定寬度 |
| `#tag` 或 `#area/subtopic` | 行內標籤 (Inline Tag)（用 / 建立巢狀） |
| `%%隱藏內容%%` | 在閱讀檢視中隱藏的註解 |
| `==高亮文字==` | 螢光標記文字 |
| `$e^{i\pi}+1=0$` | 行內 LaTeX 數學公式 |

---

## ✅ 完整品質檢查清單 (Quality Checklist)

### 🌐 語言規則 (Language Rule) 確認
- [ ] 正文全程使用**台灣繁體中文**撰寫
- [ ] 所有翻譯成中文的專有名詞，均已加上括號標示英文原文（如：知識圖譜 (Knowledge Graph)）
- [ ] 工具名稱、品牌名稱、程式語言保持英文原文

### 📋 前置資料 (Frontmatter) 確認
- [ ] 包含 `title`（台灣繁體中文標題）
- [ ] 包含 `date`、`tags`（至少 3 個）、`source`、`source_type`、`status`、`links`
- [ ] 影片筆記額外包含 `channel`、`duration`、`transcript_method`

### 🔗 知識圖譜 (Knowledge Graph) 確認
- [ ] 至少 **3 個雙向連結 (wikilinks)**（即使目標筆記尚未存在）
- [ ] 至少 **1 個 callout** 用於關鍵洞察、術語或建議
- [ ] 包含 `## 相關連結` 區塊，附簡短連結理由

### 📁 檔案結構確認
- [ ] 檔名為 ALL-CAPS 加連字號的英文格式
- [ ] 放置於正確的分類資料夾 (CATEGORY/)
- [ ] 根目錄 README.md 的 Recent Notes 區塊已更新

### 📺 YouTube 筆記額外確認
- [ ] 已記錄取得逐字稿 (transcript) 的方法
- [ ] `channel` 欄位已填寫
- [ ] `transcript_method` 已設定
- [ ] 影片 URL 已包含（可點擊連結）
- [ ] 影片描述文字已包含在詳細內容 (Details) 章節（如可取得）
