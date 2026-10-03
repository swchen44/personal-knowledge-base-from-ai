# Server 統計：原 PDF 表格的可搜尋版本

來源：`Percepio-How-to-Visualize-Response-Times-in-FreeRToS-Whitepaper-final.pdf`，第 3 頁，fig. 1A／1B。表格依原畫面轉寫；原始版面可在同套附件的 PDF 或原始 ZIP 查看。

| 版本／Actor | CPU usage | Execution min | Execution avg | Execution max | Response min | Response avg | Response max |
|---|---:|---:|---:|---:|---:|---:|---:|
| fig. 1A／Server | 6.655% | 51 µs | 1.034 ms | 2.339 ms | 186 µs | 1.842 ms | 5.777 ms |
| fig. 1B／Server | 7.964% | 51 µs | 1.106 ms | 2.554 ms | 185 µs | 2.771 ms | 7.483 ms |

原畫面以短時間格式顯示 `51`、`186`、`185` 與 `1.034` 等值；表中的 µs／ms 依白皮書時間尺度與研究報告換算。這是兩版 Server task 的比較，沒有同一 firmware 的 recorder on/off 對照，不能當成 SDK CPU overhead。

| 指標 | 改變 |
|---|---:|
| CPU usage | +1.309 個百分點，約 +19.7% 相對變化 |
| 平均 execution time | 約 +7.0% |
| 平均 response time | 約 +50.4% |

CPU usage、execution time 與 response time 的分母不同；平均值也不能取代 deadline miss 或最大延遲。
