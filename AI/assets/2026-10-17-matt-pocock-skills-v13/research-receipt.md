# 來源與重算紀錄

日期：2026-10-18。這是主筆記的查核附件，不是另一篇主題筆記。

## 固定來源

- 上游：[mattpocock/skills](https://github.com/mattpocock/skills)
- Commit：`49dd158d1076134a641b33efb035946536778336`
- Manifest：v1.3.1、27 skills；16 組 explicit-only 的 Claude／Codex 設定一致。
- 影片：[Gary Chen 的 v1.3 更新介紹](https://www.youtube.com/watch?v=QqhyqMvdx5Q)
- 影片資訊：Gary Chen，2026-10-17，10:43。
- 字幕：youtube-transcript-api 回傳人工 `zh-TW`；yt-dlp 保存 JSON3 備份。
- 本機來源 `handoff.md` SHA-256：`c50e50735cf7d6ae72cb0dcf5e890d2197956627dc2c07d55124de740b6b74ad`。
- 本機字幕 JSON3 SHA-256：`a4b15887f71965043b350b67f1537e38711c254633c23e273a69a0bb86a2458c`。
- 兩張圖片為影片 06:18、10:03 截圖，已逐張檢視；不代表畫面示例已實際驗收。

原始 handoff、完整字幕與影片留在本機 source-materials，不發布含本機環境路徑的原研究文件，也不公開整份字幕。文章保留可公開的研究結論及來源連結。

## 靜態重算

工具：Python 3、PyYAML 6.0.3、Git；程式見同資料夾的 `check-description-cost.py`。

執行方式：`python3 check-description-cost.py /path/to/full-upstream-clone`。

| Ref | Skills | Visible | All parsed chars | Visible parsed chars |
| --- | ---: | ---: | ---: | ---: |
| 221ffca^ | 15 | 12 | 3527 | 2837 |
| 221ffca | 18 | 5 | 3421 | 1782 |
| 6a62d72^ | 15 | 12 | 3527 | 2837 |
| 6a62d72 | 17 | 5 | 2338 | 941 |
| 47bde84 | 17 | 5 | 2338 | 941 |
| 49dd158 | 27 | 11 | 3870 | 2150 |

字元為 UTF-16 code units，已解析 YAML、正規化空白。未計名字、路徑、正文、宿主包裝或工具訊息。

`49dd158` 直接計算 YAML description 原字串時為 3888／2156，吻合 handoff。相對解析值多出 18／6：

| Skill | YAML 表示額外字元 | 模型可見 |
| --- | ---: | --- |
| setup-matt-pocock-skills | 2 | 否 |
| to-spec | 2 | 否 |
| implement | 2 | 否 |
| implement-spec | 2 | 否 |
| code-review | 4 | 是 |
| pr | 2 | 是 |
| retro | 2 | 否 |
| wait-what | 2 | 否 |

差異來自引用符號與跳脫引號。原始研究未附可執行計數程式，故本次確認的是「原字串口徑可重現數字」，不宣稱已追查原程式實作。

## 驗證邊界

執行了靜態檔案檢查與重算，沒有安裝、啟動或改寫被研究的 skills，沒有跨宿主 benchmark 或完整 runtime prompt。#975、#1123 本次重新讀取；其餘部分 issue／PR 回饋沿用 handoff，非即時全面重查。圖表與 Markdown 驗證只證明本次 KB 產物，不證明上游工作流有效。

## KB 產物驗證

- 主文三個 Mermaid blocks：`validate-mermaid.sh` 全數通過；Mermaid CLI 產生三張 PNG，逐張檢視並修正第二張初版的標籤重疊。
- 主文與本附件：markdownlint 通過；沿用此 KB 的長行與表格格式，停用 MD013、MD060。
- Frontmatter 必要欄位、兩張圖片、兩個研究附件及四組雙向連結存在且一致。
- 六條 Open Questions、七段六頂帽子回饋與三個 Mermaid blocks 計數通過。
- INDEX、README、LOG 都包含新筆記；LOG 前綴與原版本完全一致，確保只追加。
- 四張舊筆記只新增 frontmatter／Related 回鏈；移除新增行後與原版本逐字一致。
