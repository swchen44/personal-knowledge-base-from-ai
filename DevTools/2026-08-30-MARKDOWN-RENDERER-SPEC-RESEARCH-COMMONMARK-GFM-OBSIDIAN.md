---
title: "Markdown 渲染器前期研究 — CommonMark / GFM / Obsidian 三層規格全景與擴充語法對照"
date: 2026-08-30
category: DevTools
tags:
  - "#devtools/markdown"
  - "#devtools/parser"
  - "#research/spec"
  - "#project/markdown-renderer"
source: "conversation"
source_type: article
author: "swchen44 + Claude (Fable 5)"
status: notes
links:
  - "[[2026-05-23-RTK-RUST-TOKEN-KILLER-LOG-COMPRESSION-ARCHITECTURE]]"
  - "[[OBSIDIAN-POWER-TIPS]]"
  - "[[2026-04-02-KARPATHY-LLM-WIKI-PATTERN]]"
  - "[[2026-08-18-KB-NAVIGATION-VS-BARE-AGENT-EXPERIMENT-30-NOTES-FILENAME-BEATS-SKILL-TREE]]"
---

## 摘要（Summary）

本篇整理一次關於「Markdown 到底有沒有標準規格」的研究討論，目的是為**未來自製 Markdown 渲染器（Renderer）專案**留下可直接引用的前期研究。討論從 RTK 專案的 README.md 混用 HTML 出發，釐清了三件事：（1）Markdown 與 HTML 混用是規格允許的合法行為；（2）GitHub 的渲染標準是**兩層規格**——CommonMark（基礎）＋ GFM（GitHub Flavored Markdown，官方超集），兩者都有形式化規格書與機器可讀測試集；（3）Obsidian Flavored Markdown **沒有形式化規格**，只有官方說明文件，屬於「實作即規格（implementation-defined）」。文末附上 GitHub 與 Obsidian 兩邊完整的擴充語法（Extension Marks）對照表，作為未來實作的檢查清單。

## 關鍵洞察（Key Insights）

- **Markdown 內嵌 HTML 是規格內行為**：CommonMark 規定解析器遇到原始 HTML（Raw HTML）時原樣輸出。開源專案 README 標頭用 `<p align="center">`、`<img width>`、`<picture>` 排版是標準慣例，因為置中、圖片尺寸、深淺色切換是純 Markdown 做不到的
- **GFM 是 CommonMark 的嚴格超集**，只加 5 個官方擴充：表格（Tables）、任務清單（Task Lists）、刪除線（Strikethrough）、自動連結（Autolinks）、HTML 標籤過濾（Tagfilter）
- **規格書本身就是測試集**：CommonMark/GFM 的 spec.txt 內含 600+ 組「輸入 → 期望 HTML」配對，社群慣例直接拿來當一致性測試（Conformance Test）跑——自製渲染器等於規格附贈完整測試
- **GitHub 網站效果 ≠ GFM spec**：`@提及`、`#123`、emoji、Mermaid、數學公式、alerts 都是平台層後處理，不在規格內
- **Obsidian 是「實作即規格」**：語法只有 help 文件描述，邊界情況以 Obsidian 本體行為為準；社群 parser（obsidian-export、remark-obsidian、Quartz）是逆向出來的事實規格
- **Wikilink 解析不只是語法問題**：`[[Note]]` 要落地成連結需要 vault 層的檔名索引（最短唯一路徑 + aliases），架構上必須與語法 parser 分層 — 參見 [[OBSIDIAN-POWER-TIPS]]

## 詳細內容（Details）

### 一、起點：README.md 混用 HTML 的合法性

討論起點是 [[2026-05-23-RTK-RUST-TOKEN-KILLER-LOG-COMPRESSION-ARCHITECTURE|RTK 專案]] 的 README.md。它在 Markdown 檔案裡大量使用 HTML：

```html
<p align="center">
  <img src="..." alt="RTK" width="500">
</p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="...theme=dark" />
  <source media="(prefers-color-scheme: light)" srcset="..." />
  <img alt="Star History Chart" src="..." />
</picture>
```

三個結論：

1. **合法**：CommonMark 與 GFM 都允許內嵌原始 HTML，解析器原樣輸出交給瀏覽器
2. **GitHub 會做白名單過濾（Sanitize）**：`<script>`、`<style>`、inline `style` 屬性會被剝掉——所以 README 用老式的 `align="center"` 屬性而非 CSS
3. **HTML 區塊內的 Markdown 不解析**：在 `<p>...</p>` 內部 `**粗體**` 會失效，必須改用 `<strong>`

> [!warning] 可移植性代價（Portability Cost）
> 這些 HTML 在 GitHub/GitLab 正常，但在更嚴格的渲染器（如 crates.io 的 README sanitize、終端 Markdown 檢視器）中可能退化成純文字。內容仍可讀，只是失去排版效果。

### 二、GitHub 的標準：兩層規格

> [!note] 關鍵術語（Key Term）
> **CommonMark**：Markdown 的形式化規格，把原始語法所有模糊處（巢狀清單、HTML 區塊邊界、emphasis 解析）定義清楚。**GFM（GitHub Flavored Markdown）**：GitHub 在 CommonMark 上定義的嚴格超集（Strict Superset）。

| 層 | 規格書 | 性質 |
|----|--------|------|
| CommonMark | https://spec.commonmark.org/ | 基礎規格，600+ 機器可讀範例 |
| GFM | https://github.github.com/gfm/ | CommonMark + 5 個官方擴充 |

GFM 的 5 個官方擴充：

1. **Tables** — `| a | b |` 表格語法
2. **Task list items** — `- [ ]` / `- [x]`
3. **Strikethrough** — `~~刪除線~~`
4. **Autolinks 擴充** — 裸網址自動變連結
5. **Disallowed Raw HTML（Tagfilter）** — `<script>`、`<title>`、`<style>` 等標籤轉義

**參考實作（Reference Implementation）**：GitHub 官方維護 [cmark-gfm](https://github.com/github/cmark-gfm)（C 語言，fork 自 CommonMark 參考實作 cmark）。

**GitHub 網站的完整渲染管線**（spec 之外還有平台層）：

```
 Markdown 原文
     │
     ▼
[GFM 解析]  ← cmark-gfm，規格內
     │
     ▼
[HTML Sanitize]  ← 白名單過濾，historically html-pipeline
     │
     ▼
[平台後處理]  ← @提及、#123、emoji、Mermaid、數學、alerts、語法高亮
     │         （皆不在 GFM spec 內）
     ▼
 最終 HTML
```

### 三、Obsidian 的「規格」現狀

Obsidian 官方稱其語法為 **Obsidian Flavored Markdown**（https://help.obsidian.md/obsidian-flavored-markdown ），但性質與 GFM 完全不同：

| | GFM | Obsidian Flavored Markdown |
|---|---|---|
| 形式化規格書 | 有（含 600+ 機器可讀測試範例） | 沒有，只有人類閱讀的說明文件 |
| 參考實作 | 開源（cmark-gfm） | 閉源（Obsidian 本體不開源） |
| 邊界情況定義 | 精確定義 | 未定義，以 Obsidian 實際行為為準 |

Obsidian 基底是 CommonMark + GFM（表格、刪除線、任務清單都支援），再疊上自有擴充（完整清單見文末對照表）。遇到邊界情況（如 wikilink 內同時有 `|` 和 `#`、callout 巢狀嵌 embed）只能拿 Obsidian 本體實測。

### 四、自製渲染器的建議路線圖

> [!tip] 可執行建議（Actionable Tip）
> 分四階段，每階段都有明確的「正確性依據」：
>
> 1. **CommonMark 核心** — 拿 spec.txt 的範例當 conformance test 跑
> 2. **GFM 5 擴充** — 同樣有 spec 測試集可循
> 3. **Obsidian 擴充層** — 以 plugin 形式疊加，參考社群實作 + 自建 fixture 對照真實 Obsidian
> 4. **（選配）平台層功能** — emoji、Mermaid、數學等，只能行為對照，無 spec 可循

**可參考的現成實作**（依語言）：

| 語言 | 實作 | 備註 |
|------|------|------|
| Rust | [comrak](https://github.com/kivikakk/comrak) | GFM 完整支援，crates.io 使用；架構就是「CommonMark 核心 + 擴充分層」 |
| Rust | pulldown-cmark | 更快，但只有部分 GFM 擴充 |
| Rust | [obsidian-export](https://github.com/zoni/obsidian-export) | 處理了 wikilink/embed 解析，Obsidian 擴充的事實規格參考 |
| JavaScript | micromark / remark | CommonMark + GFM plugin；remark-wiki-link、remark-obsidian 處理 Obsidian 層 |
| JavaScript | Quartz、obsidian-html | 「vault 發佈成網站」類專案，最完整的 Obsidian 渲染重現 |
| Go | goldmark | Hugo 使用 |

> [!important] 架構決策：wikilink 解析要分層
> `[[Note]]` 的**語法解析**（切出 target/heading/block-id/alias）屬於 parser；**連結目標解析**（哪個檔案）需要 vault 索引——Obsidian 用「最短唯一路徑」規則找檔案，還要處理 frontmatter 的 `aliases`。這部分邏輯必須放在語法 parser 之外，否則 parser 無法獨立測試。

---

## 附錄：GitHub 與 Obsidian 擴充語法（Extension Marks）完整對照

> [!info] 本節是未來渲染器專案的實作檢查清單（Implementation Checklist）。「規格層級」欄標示該語法的正確性依據來源。

### GitHub 擴充 Marks

| 語法（Mark） | 範例 | 規格層級 |
|--------------|------|----------|
| 表格（Tables） | `\| a \| b \|` + `\|---\|---\|` | GFM spec |
| 任務清單（Task Lists） | `- [ ] todo` / `- [x] done` | GFM spec |
| 刪除線（Strikethrough） | `~~text~~` | GFM spec |
| 自動連結（Autolinks） | `https://example.com`（裸網址） | GFM spec |
| HTML 過濾（Tagfilter） | `<script>` → `&lt;script>` | GFM spec |
| 腳註（Footnotes） | `[^1]` + `[^1]: 內容` | 平台層（spec 外） |
| Alerts | `> [!NOTE]` / `[!TIP]` / `[!IMPORTANT]` / `[!WARNING]` / `[!CAUTION]` | 平台層 |
| 提及（Mentions） | `@username` | 平台層 |
| Issue/PR 參照 | `#123`、`owner/repo#123` | 平台層 |
| Commit 參照 | SHA 自動連結 | 平台層 |
| Emoji 短碼 | `:smile:` | 平台層 |
| 數學公式（Math） | `$inline$`、`$$block$$`、` ```math ` | 平台層 |
| Mermaid 圖表 | ` ```mermaid ` code block | 平台層 |
| GeoJSON / TopoJSON / STL | ` ```geojson ` 等 code block | 平台層 |
| 語法高亮（Syntax Highlighting） | ` ```rust ` 等語言標註 | 平台層（Linguist） |
| 標題錨點（Heading Anchors） | 標題自動產生 `#heading-id` | 平台層 |
| 色碼預覽 | `` `#RRGGBB` `` 顯示色塊 | 平台層 |

### Obsidian 擴充 Marks

| 語法（Mark） | 範例 | 說明 |
|--------------|------|------|
| Wikilink | `[[筆記名]]` | 內部連結，需 vault 索引解析 |
| Wikilink 別名顯示 | `[[筆記名\|顯示文字]]` | `\|` 後為顯示文字 |
| Wikilink 標題連結 | `[[筆記名#標題]]`、`[[#同檔標題]]` | 連到特定 heading |
| Wikilink 區塊連結 | `[[筆記名#^block-id]]` | 連到特定段落 |
| 區塊 ID（Block ID） | `段落文字 ^my-id`（清單/引用另起一行） | 讓段落可被引用 |
| 筆記嵌入（Embed） | `![[筆記名]]`、`![[筆記名#標題]]` | 內嵌其他筆記內容 |
| 圖片嵌入 + 尺寸 | `![[image.png\|300]]` | 指定寬度 |
| PDF 嵌入 | `![[doc.pdf#page=3]]` | 指定頁碼 |
| Callout | `> [!note]`、`> [!warning] 自訂標題` | 類型：note/tip/warning/info/example/quote/bug/danger/success/failure/question/abstract/todo 等 |
| 可摺疊 Callout | `> [!faq]- 預設摺疊`、`> [!faq]+ 預設展開` | `-`/`+` 控制摺疊狀態 |
| 螢光筆（Highlight） | `==重點文字==` | GFM 沒有 |
| 註解（Comments） | `%%隱藏文字%%`、`%%` 區塊 `%%` | 渲染時不顯示 |
| Frontmatter Properties | 檔頭 `---` YAML 區塊（tags/aliases/cssclasses） | 解析為結構化屬性 |
| 行內標籤（Inline Tags) | `#tag`、`#nested/tag` | 支援巢狀階層 |
| 數學公式（Math/LaTeX） | `$e^{i\pi}+1=0$`、`$$...$$` | MathJax |
| Mermaid 圖表 | ` ```mermaid ` code block | 可用 `internal-link` class 連 vault 筆記 |
| 腳註（Footnotes） | `[^1]` + `[^1]: 內容` | 同 GitHub |
| 行內腳註（Inline Footnotes） | `^[直接寫在行內]` | **GFM 沒有**，Obsidian 特有 |
| 任務清單（Task Lists） | `- [ ]` / `- [x]`，另支援 `- [/]`、`- [-]` 等自訂狀態 | 擴充狀態依主題（Theme）而定 |

### 兩邊語法衝突/差異速查

| 語法 | GitHub | Obsidian |
|------|--------|----------|
| `> [!note]` | Alerts（僅 5 種類型，不可自訂標題、不可摺疊） | Callouts（13+ 種類型、可自訂標題、可摺疊） |
| `==text==` | 不支援（原樣輸出） | 螢光筆 |
| `[[link]]` | 不支援（原樣輸出） | Wikilink |
| `%%text%%` | 不支援（原樣輸出） | 註解（隱藏） |
| `^[inline]` | 不支援 | 行內腳註 |
| `#tag` | 原樣文字（或誤判 heading，視位置） | 行內標籤 |
| Frontmatter | 渲染成表格（僅 blob 頁） | 解析為 Properties |

---

## 我的心得（My Takeaways）

1. **規格分層決定架構分層**：CommonMark → GFM → Obsidian → 平台層的規格強度遞減，渲染器的模組邊界應該直接照這個分層切，每層用不同的正確性驗證策略（spec 測試 → 社群實作對照 → 實測 fixture）
2. **spec.txt 即測試集**是這次研究最有價值的發現——自製渲染器不用自己發明測試，先讓 CommonMark 600+ 範例全過再談擴充
3. 這個模式和 RTK 的 snapshot/fixture 測試策略（參見 [[2026-05-23-RTK-RUST-TOKEN-KILLER-LOG-COMPRESSION-ARCHITECTURE]]）一致：**拿真實輸出當 fixture，不用合成資料**
4. 若渲染器最終要服務個人知識庫（如 [[2026-04-02-KARPATHY-LLM-WIKI-PATTERN]] 的 LLM Wiki 模式），Obsidian 擴充層 + vault 索引是必做項，且 vault 索引可以獨立成庫

## 待補充（Open Questions）

- CommonMark spec 有版本演進（0.29 → 0.31.x），GFM spec 停在基於 0.29 的版本——兩者的差異清單是什麼？自製渲染器該以哪個版本為準？（建議搜尋：`commonmark spec changelog`、`gfm spec version 0.29`）
- GitHub 實際上是否已從 cmark-gfm 遷移到其他實作（有傳聞遷移到 Rust 的 comrak）？這影響「參考實作」該看哪個 repo（建議搜尋：`github markdown comrak migration`）
- Obsidian 的「最短唯一路徑」wikilink 解析規則的精確行為（同名檔案在不同資料夾、大小寫敏感度、副檔名省略規則）沒有官方形式化定義——需要實測建 fixture（建議搜尋：`obsidian shortest path when possible link resolution`）
- Obsidian 的 Live Preview 與 Reading View 渲染行為有已知差異（如部分 HTML、巢狀 callout），差異清單在哪？（建議搜尋：`obsidian live preview reading view differences`）
- GFM tagfilter 的完整標籤黑名單與 GitHub 實際 sanitize 白名單（html-pipeline / 現行實作）並不相同——實作「GitHub 模擬模式」時兩者要分開實作嗎？（建議搜尋：`github markup sanitization whitelist`）
- 渲染器的目標輸出是 HTML、終端（ANSI）、還是 AST？若要像 RTK 一樣做終端輸出，CommonMark 測試集的 HTML 比對就不能直接用，驗證策略要重新設計

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | CommonMark spec URL、GFM 的 5 個官方擴充名稱、cmark-gfm 是參考實作、Obsidian Flavored Markdown 無形式化規格、spec.txt 含 600+ 測試範例 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | 「規格強度遞減鏈」：CommonMark（形式化+測試集）→ GFM（形式化超集）→ Obsidian（文件描述）→ 平台層（無文件，行為即規格）。渲染器的驗證策略必須隨層級改變 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 隱含假設：「照 spec 實作 = 與 GitHub 顯示一致」——實際上 GitHub 有 sanitize 與後處理，spec 相容只保證第一段管線；另一個未驗證假設是社群 Obsidian parser 忠實重現了 Obsidian 行為 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | （1）立即可做：clone commonmark spec repo，把 spec.txt 範例抽成測試 harness，跑通一個現成 parser 當 baseline；（2）為 Obsidian 邊界情況建 fixture 庫：在真實 Obsidian vault 放測試筆記，截圖/匯出對照 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | 自寫 parser vs 包裝 comrak + 自寫 Obsidian 擴充層：後者省下 CommonMark 核心的巨量邊界處理（emphasis 解析是出名的難），若目標是「做出可用的 Obsidian 渲染」應選後者；若目標是「學習 parser 設計」才選前者 |

### 分析型追問（Socratic Follow-up)

- **澄清**：「Obsidian 相容」的精確定義是什麼——語法解析一致？渲染視覺一致？還是連結解析行為一致？三者工作量差一個數量級
- **假設**：「spec.txt 全過 = CommonMark 相容」的前提是測試集覆蓋完整；spec 範例沒覆蓋到的行為（如 pathological input 的效能）如何驗證？
- **證據**：「GitHub 遷移到 comrak」目前只是社群傳聞層級，未經查證；實作前應確認官方 cmark-gfm 的維護狀態
- **觀點**：反對者會說：現成 parser 這麼多，自製渲染器是重造輪子——最有力的回應是什麼？（差異化：終端輸出？LLM token 優化？vault 感知？）
- **後果**：若渲染器以 Obsidian 相容為目標，12 個月後 Obsidian 改版新增語法（歷史上 callout、properties 都是後加的），無 spec 可循的追趕成本如何攤提？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — Obsidian 擴充層無規格可循，邊界情況的相容性只能靠實測窮舉；最壞情況是投入大量時間後，渲染結果在真實 vault 上仍與 Obsidian 有肉眼可見差異，使用者不信任
2. **什麼情況下會失敗？** — （a）從零手寫 CommonMark 核心：emphasis/連結解析的邊界情況極多，容易卡死在第一階段；（b）目標渲染 GitHub 網站效果而非 GFM spec：平台層功能無規格，逆向成本無上限；（c）Obsidian 大改版（如語法變更）導致擴充層需重寫
3. **有沒有更好的替代方案？** — 有：基底直接用 comrak（Rust、GFM 完整、可掛自訂擴充），只自寫 Obsidian 擴充層與 vault 索引。除非目的是學習 parser 理論，否則不建議從零寫 CommonMark 核心；JavaScript 生態則可直接組裝 micromark + remark-obsidian 快速驗證產品假設，之後再決定是否 Rust 重寫

## 相關連結（Related）

- [[2026-05-23-RTK-RUST-TOKEN-KILLER-LOG-COMPRESSION-ARCHITECTURE]] — 本次討論的起點專案；其 fixture/snapshot 測試策略可直接沿用到渲染器的 conformance test
- [[OBSIDIAN-POWER-TIPS]] — Obsidian Markdown 語法（wikilink/Bases/Canvas）的使用端整理，與本篇的實作端視角互補
- [[2026-04-02-KARPATHY-LLM-WIKI-PATTERN]] — 渲染器的潛在應用場景：LLM 維護的 Obsidian 知識庫需要 vault 感知的渲染
- [[2026-08-18-KB-NAVIGATION-VS-BARE-AGENT-EXPERIMENT-30-NOTES-FILENAME-BEATS-SKILL-TREE]] — Markdown 知識庫的檢索實證研究，說明 Markdown 作為知識載體的工程價值

## References

- [CommonMark Spec](https://spec.commonmark.org/)
- [GitHub Flavored Markdown Spec](https://github.github.com/gfm/)
- [cmark-gfm（GitHub 官方參考實作）](https://github.com/github/cmark-gfm)
- [Obsidian Flavored Markdown 官方文件](https://help.obsidian.md/obsidian-flavored-markdown)
- [comrak（Rust GFM 實作）](https://github.com/kivikakk/comrak)
- [obsidian-export（Rust vault 轉換器）](https://github.com/zoni/obsidian-export)
- [GitHub Docs — Writing on GitHub](https://docs.github.com/en/get-started/writing-on-github)
