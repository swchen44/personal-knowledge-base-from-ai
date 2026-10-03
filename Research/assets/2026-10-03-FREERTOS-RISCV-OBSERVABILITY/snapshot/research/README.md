# FreeRTOS／RISC-V Observability 研究資料

主要文件：[完整學習與研究報告](FreeRTOS-RISC-V-Observability-研究報告.md)。研究日期為 2026-10-03。

本次要求、研究過程、已完成／未完成事項與遺漏檢查，記錄於[根目錄 README](../README.md)。本檔保留成果與附件索引。

報告包含需求對照、原始碼分析、8 份 PDF 的文字與圖片、YouTube 字幕解析、UART 頻寬、CPU 成本試算、RV32 object 編譯大小、FreeRTOS hooks 與 SDK API、9 組案例索引與操作流程、內部 AI 接續任務及 MECE 檢查。

資料位置：

| 位置 | 內容 |
|---|---|
| `images/` | PDF 重點頁面圖片 |
| [Mermaid 索引](images/mermaid/README.md) | Mermaid 原始碼與 SVG／PNG 備用圖 |
| `pdf-text/` | 8 份 PDF 的原始文字抽取 |
| `pdf-manifest.json` | PDF 頁數與原始／文字 SHA-256 |
| `pdf-visual-review.json` | 逐份圖片檢查與重點頁碼 |
| `youtube-evidence.json` | 字幕來源、發布日期與重點時間點 |
| `source-manifest.json` | 本次原始碼快照的 SHA-256 |
| `measurements/` | RV32 object size 結果與原始 size 輸出 |
| `measure_objects.py` | RV32 編譯探測；不修改原始 SDK |
| `api-link-check.json` | 官方 API 網址檢查 |
| `mermaid-verification.json` | Mermaid 語法檢查結果 |
| `verification.json` | Markdown、附件與數值檢查結果 |
| `requirements-audit.json` | 使用者要求、對應章節與未完成項目的稽核 |
| [內部 AI 接續研究任務](內部AI-接續研究任務.md) | U01～U16 的目的、source／build 工作、依賴、驗收與可貼用指令 |
| [桌面 demo PSF](cases/desktop-demo.psf) | 本次實際產生的模擬 RTOS trace，供學習；GUI 解碼待驗證 |
| `cases/desktop-demo-evidence.json`、`cases/desktop-demo-build.log` | 桌面 demo 編譯／執行條件、結果、warning 與 PSF hash |
| `cases/source-image-review.json` | SWO 範例資料率／event loss 與 host 配置原圖的閱讀紀錄 |

可攜套件保留原相對目錄，因此報告圖片與本地 source／PDF 連結可以一起使用。若只複製 Markdown 單檔，圖片與相對連結也要搬移或改寫。沒有 Mermaid 的平台可使用備用 SVG／PNG。

編譯探測以本次 macOS 的 Homebrew LLVM 路徑為基準：

```sh
python3 research/measure_objects.py
```

其他主機需調整腳本內的 clang／llvm-size 路徑。結果只涵蓋 BareMetal／RingBuffer 的 recorder object，未連結成產品 firmware，沒有板上 CPU 或 UART 實測。產品的真正新增 Flash／RAM 與 CPU loading，仍需在相同 workload 下做 A/B 驗證。

本次沒有上傳內部網路，也沒有修改使用者產品 FreeRTOS source。
