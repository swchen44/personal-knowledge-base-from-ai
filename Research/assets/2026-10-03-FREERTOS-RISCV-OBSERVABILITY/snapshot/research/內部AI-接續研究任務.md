# 交給內部 AI 的 FreeRTOS／RISC-V Observability 接續研究任務

更新日期：2026-10-03。主報告：[完整研究報告](FreeRTOS-RISC-V-Observability-研究報告.md)；要求與工作紀錄：[根 README](../README.md)。

**目的：用內部已有的產品原始碼，把外部文件的可行性研究轉成可比對的接入方案、真正 firmware 的大小、板上成本與可重現的診斷案例。** 本檔可以與整個 ZIP 一起交給內部 AI。下面列的是接續研究任務，尚未在使用者產品上完成。

## 1. 先讀這些內容，保留哪些基準？

| 內容 | 用途 |
|---|---|
| [主報告第 12 節](FreeRTOS-RISC-V-Observability-研究報告.md#section-12) | SDK 接合、FreeRTOS trace 巨集、API 與 kernel 重編 |
| [第 8～11 節](FreeRTOS-RISC-V-Observability-研究報告.md#section-8) | CPU／RAM／Flash 的量測方法與 RISC-V boundary |
| [第 22 節](FreeRTOS-RISC-V-Observability-研究報告.md#section-22) | 案例：收集後如何判讀、修正與重測 |
| [第 23 節](FreeRTOS-RISC-V-Observability-研究報告.md#section-23) | MECE 分類、任務主要歸屬與採用證據 |
| [Source manifest](source-manifest.json) | 外部研究來源與 SHA-256；產品版本另行記錄 |
| [RV32 object 探測](measurements/rv32-object-size.json) | 12,633 bytes text／13,880 bytes BSS 的編譯邊界；不能當成產品增量 |
| [桌面 demo 證據](cases/desktop-demo-evidence.json) | 事件產生／FILE port 已跑通；GUI decode 尚未驗收 |

本地主 recorder 檔頭 v4.12.0，DFM v2.1.0。桌面 demo 使用另一份 recorder，檔頭 v989.878.767。線上 API Reference 與舊 demos 不一定同版；接入時以選定 source 與實際 headers 確認。

必須保留的已知限制：主 RV32 counter 預設 16 MHz 要校正；Arm CrashCatcher／STM32 flash 不能直接套 RISC-V；通用 UART port 需自行接入；DFM Serial 有 hex 擴張；payload 底層失敗處理與 checksum 存在待驗證缺口。

## 2. 內部 AI 拿到 source 後，能先做哪些事？

| 能力／可用條件 | 可以先完成 | 尚不能由此判定 |
|---|---|---|
| 只有產品 source | 找出整合位置、缺少的 hooks、timer／IRQ／allocator／driver 路徑；提出精確 diff 與量測點 | 真正 CPU loading、UART error rate、電量與 reset 保存可靠度 |
| Source＋正確 toolchain／build 環境 | 建置 baseline 與 recorder 版本，比較 ELF／map／stack；預處理確認 hook 展開 | 板上每事件 cycles、driver 吞吐與 deadline |
| 再有 Tracealyzer／decoder | 驗證 PSF、XML、symbols、已知事件序列、分析步驟 | 真實平台的時間換算，仍需 counter／校時證據 |
| 再有可操作板子／量測設備或可信既有資料 | 跑 A/B workload、UART 壓測、IRQ／reset／sleep 測試並保存原始結果 | 未測過的 workload 或所有競態不存在 |
| 再有後端／供應商報價 | 驗證交付、retention、存取與實際費用 | 未選定部署及實際用量之前的總費用 |

缺少條件時，保留已完成的 source／build 結果及阻塞項，產出能執行的量測程式或步驟；不要用公式或 simulator 補填板上結果。

## 3. 一開始先建立產品事實表

從 source、build 與板級文件填入；找不到的欄位寫「未知」，附查找結果。

| 欄位 | 要記錄的事實／證據 |
|---|---|
| 版本 | 產品 commit／build ID、kernel commit／版本與 fork diff、BSP 版本 |
| 硬體 | RISC-V core／ISA／XLEN、core 數、執行 privilege、RAM／Flash／memory regions、cache／DMA 能存取的區域 |
| 時間 | CPU clock、實際 timestamp counter／clock source、wrap、sleep／DVFS／tickless 行為；CPU clock 與 counter 分開 |
| 建置 | Compiler 版本、ABI、optimization、LTO／GC、linker script、靜態／動態配置、kernel 是否預編譯 |
| FreeRTOS | Preemption／SMP、task／priority、TLS slots、runtime stats、malloc／free、ISR／yield 與現有 trace 巨集 |
| I/O | UART 可用實例、最高實際 baud、DMA／IRQ、console 是否共用、bridge 型號、flow control、collector 的啟動方式 |
| 應用問題 | 已知症狀、request／完成邊界、workload、原 deadline 或預期行為、error／timeout 路徑 |
| 部署 | 開發／CI／正式裝置哪些階段需要收集；現有網路、storage、reset reason 與內部服務 |
| 資源預算 | 有證據的 Flash／RAM／CPU／延遲／電量上限；沒有既定值先報量測，等待產品決策 |

同時建立 `研究結論 → 產品檔案:行號 → 相同／不同 → 影響 → 要怎麼驗證` 對照表。不要把主 SDK 的預設值或 Arm 案例當成產品事實。

## 4. 未完成任務、目的與完成條件

U01～U12 延續根 README，U13～U16 為本次補出的缺口。各任務主要分類見主報告第 23 節；引用依賴不重複計為另一項完成。

| 任務 | 目的 | Source／build 可以先做 | 驗收與輸出 | 額外條件 |
|---|---|---|---|---|
| U01 最小 SDK 接入 | 證明 hooks 接上實際 FreeRTOS，保留已知 RTOS／應用事件 | 檢查 config/include/build/init、預處理 task／queue 路徑；做研究分支的 RAM-only 接入 | 精確修改清單與 diff、可建置 firmware、已知 task／queue 序列的 trace；寫明 kernel 是否重編 | 最終事件驗收需板子或合適的功能驗證環境與 decoder |
| U02 最終 Flash／RAM | 算出真正產品新增成本 | 相同條件建置 baseline／RAM-only／transport；分類 linker map 與 stack／TCB／buffer | ELF／map／size CSV、依分類的增量與 compiler／flags；記錄 linker 移除與 LTO 影響 | 正確產品 toolchain、可重現 build |
| U03 CPU／每事件成本 | 分清 task 使用量、recorder、monitor 與 transport 成本 | 加對照 workload、counter／GPIO 測點；實作第 8 節 A～F 測量框架 | 每事件 cycles 分布、平均／峰值 events/s、總 CPU 增加的百分點與單次行為相對增加；附原始 counter | 板子、可信時鐘與固定 workload |
| U04 最差即時性 | 避免平均 overhead 低仍破壞 IRQ／deadline | 追 critical section／IRQ masking、優先權、buffer 滿時路徑 | IRQ delay、critical section 最大值、response 分布、deadline miss；正常與尖峰條件比較 | 板子／timer／GPIO 或可等價驗證的設備 |
| U05 UART／collector | 證明資料產生率與實際傳輸服務率可匹配 | 選定非阻塞 UART port、ownership、DMA completion、partial write／reconnect；選 console 分流方式 | Source diff、平均與窗口峰值、有效 bytes/s、buffer high-water、errors／loss、host 停頓結果 | 板子、UART／bridge、collector |
| U06 捕捉完整性 | 知道哪些 trace 可相信、snapshot 前史是否足夠 | 定義 loss 計數、有效窗口、freeze／copy／restart／多 trigger 政策 | 已知 marker 對照、捕捉前後窗口與空窗、滿 buffer／斷線／copy 競爭測試；標示無效區間 | 最終驗證需平台或可完整重現的執行環境 |
| U07 RISC-V crash 保存 | Crash／reset 後仍能取回必要證據 | 盤點 trap、寄存器、stack、startup／linker／retained memory／storage；做平台設計 | Trap context＋前史，reset／斷電恢復結果，保存完整性與 wear／刪除時機 | 若產品需要此功能，需板子、reset／斷電與 storage 測試 |
| U08 Timestamp／SMP | 保證時間與共享 recorder 資料的正確性 | 查 counter 權限／頻率、wrap、IRQ restore；有 SMP 再查 core ID、locks、memory ordering | 已知時間校正、單核 IRQ nesting；條件式 sleep／DVFS／wrap／跨核測試 | 依實際 core／timer／privilege／省電設計 |
| U09 裁剪／trigger 策略 | 降低資料量，同時留下問題需要的證據 | 列出內建／客製能力、最小事件集、狀態機、threshold、去重／限流 | 縮減前後 bytes/s 與 CPU，已知異常的偵測／誤報／漏報與前史；標出失去的分析功能 | 具體問題案例與量測條件 |
| U10 可靠後端 | 完整 alert／payload 確實到達且可取回 | 查現有 storage／network，選本地／gateway／cloud；補確認、retry、去重與持久化設計 | 各端故障注入、完整性檢查、對帳／重送、retention、存取權與 payload 下載驗收 | 選定的實際服務與測試環境 |
| U11 費用／是否便宜 | 用相同能力比較成本，產出採用決策 | 盤點需要的 recorder／viewer／server／cloud／probe／bridge 與整合工時 | 正式報價、裝置／使用者／保存量／期間的 TCO 表；假設與不含項目 | 採購需求與供應商報價、實際用量 |
| U12 產品案例與 regression | 證明 SDK 能幫我們定位並確認改善 | 選真實問題或明確控制的測試情境，加 request／state 事件，建 workload | 完整的問題→trace→source 原因→修正 diff→相同條件重測，納入 CI；無原始問題時標成控制實驗 | 產品 workload、分析端與執行環境 |
| U13 Decode／分析流程 | 確認 PSF／XML／symbols 可用，工程師真的能看懂 | 先用桌面 PSF 檢查 viewer，再查產品 schema／decoder 相容性 | 桌面及產品已知序列正確解讀；unknown events／loss、ID／物件／時鐘／priority 證據，操作截圖 | 合適 Tracealyzer／decoder、授權與執行環境 |
| U14 證據格式與版本 | 每份 trace 都能回到正確 source 和收集配置 | 制定 build／device／session／symbols／config／loss metadata 與保存目錄 | 可用模板、hash／schema 版本、trace＋ELF 對照；故意錯版本時可辨識／拒用 | 內部 artifact 保存位置；不必先連外 |
| U15 收集生命週期與控制 | 啟動／停止／設定變更後仍有一致且有界的行為 | 查 boot init、start／stop／rearm、遠端控制、config 持久化與可觀測性自身事件 | 控制狀態表、開關／重啟／反覆 trigger 測試；buffer 與配置版本、錯誤及權限行為 | 遠端控制僅在產品真的需要時驗證 |
| U16 條件式電量驗證 | 判斷 trace 是否妨礙產品省電目標 | 查 poll／debug link／UART wakeup、timer sleep、DMA 與省電配置 | Trace off／RAM-only／transport 的電流／能耗、sleep residency／喚醒次數，同時確認時間戳 | 產品有省電目標時才做；板子與電流量測 |

## 5. 每類任務的實作重點

### 5.1 先完成 U01／U08／U13，才能相信後續數字

用最小的已知 task／queue／ISR 序列驗證：create→ready→switch→send／receive→應用完成事件。附原始 trace 與預期事件清單，核對遺失、ID、物件名稱、priority、timestamp 與 ISR nesting。

標準 FreeRTOS 通常已有 `traceTASK_SWITCHED_IN` 等呼叫點。先查產品 kernel，不直接改 `tasks.c`／`queue.c`；include／config 的改動必須套用到 kernel 編譯單元。預編譯 kernel 要重建，產品 fork 缺失的呼叫點要列出精確 diff。

Timestamp 正確之前，cycles→µs 與 response 指標都保留待校正狀態。SMP、sleep、DVFS 以產品實際配置確認適用性。

### 5.2 U02～U04：成本要用可比對的 A/B

至少保存 baseline、RAM-only、加入 transport 三種 build／run。若需 monitor／DFM，再另加配置；不能把 network／TLS 既有成本全部算到 recorder，也不能漏掉新建 task／TCB／stack／DMA buffer。

固定 workload、compiler／flags、clock、core／scheduler 與觀察窗口。總 CPU、task CPU、每事件時間、單次行為相對增加、UART 占用率分開報告。平均、分布、最大值附對應 workload；用 wall-clock 不同分母的數字不能直接相減。

### 5.3 U05／U06／U09：先驗證資料需求，再提高線速

先量事件產生率及峰值，測 host 暫停、線路錯誤、斷線、buffer 滿與連續 trigger。區分「driver 接受 bytes」與「線上確實完成 bytes」，以及「collector 收到檔案」與「decoder 能完整分析」。

依實際 streamport 契約確認 partial write／busy／fail；DMA 記憶體在完成前不能釋放或覆寫，有 cache 的平台加必要 maintenance／barrier。避免追蹤 UART 自己的 ISR／RTOS 操作形成事件放大或遞迴。

裁剪前先寫 `問題 → 不可刪事件 → 可降低頻率的資料 → 將失去的分析能力`。Host preview 不會降低此前的裝置記錄或線路成本。

### 5.4 U07／U10：異常交付用完整性驗收

明確列出 fault→snapshot→persist→send→ack→delete 的各階段，以及各階段 reset、斷電、busy、partial write、重複 alert 的結果。檢查本地 DFM 未傳遞的底層失敗與 checksum；不要把 `DFM_SUCCESS` 或 MQTT QoS0 當成後端完整保存證據。

依需求保留 trace 前史、RISC-V trap context、reset reason 與版本 metadata。未具備原始碼／平台支持的 crash register 或完整 call stack，不補寫成現有能力。

### 5.5 U11：用同樣能力比較「便宜」

列出比較期間、裝置／工程師數、alert 頻率、payload／摘要大小、保存天數、分析／下載次數、probe／bridge、授權、backend／storage、工程整合與維運工時。只需 task CPU 摘要與需完整排程 trace 的方案，分開比較其能回答的問題。

報價未知時保持空缺，對有來源的價格與用量做敏感度試算。沒有完整服務與用量條件時，總費用保持待評估。

### 5.6 U12～U15：把「能收集」變成「能持續使用」

每個案例留下異常窗口與分析操作，讓另一位工程師能拿相同 trace／symbols 重做分析。Viewer menu 名稱、XML／schema 與授權依內部安裝版本確認。桌面 demo 的 `.psf` 只是第一個學習素材；產品 trace 需另驗。

初始化→收集→trigger→freeze／copy→傳送→rearm 與 start／stop、reset、config 更新，要有可重現的狀態表。可遠端控制時，確認誰能啟動收集、收哪些資料、何時停止及留下什麼稽核。沒有遠端控制需求時，可先保持本地開關。

## 6. 輸出格式與驗收狀態

建議新增產品內部研究目錄，沿用穩定的 U 編號，例如：

```text
internal-research/
├── product-facts.md
├── source-comparison.md
├── task-status.md
├── integration/          最小接入 diff、預處理證據、build 指令
├── builds/               baseline／RAM／transport 的 ELF、map、config
├── measurements/         原始 counter、CSV、workload、校時與環境
├── cases/                trace、metadata、標註圖、原因、修正前後
└── costs/                報價、用量與 TCO／假設
```

每項任務使用以下欄位，未知值不補成 0：

| 欄位 | 內容 |
|---|---|
| 任務／目的 | U 編號與要確認的決策 |
| 適用性 | 必要／依產品條件／已確認不適用，附理由 |
| 證據階段 | 文件研究／source 已確認／建置／host 模擬／板上量測／產品驗收 |
| 狀態 | 待開始／進行中／缺條件／未通過／已通過／不適用 |
| 條件 | Commit／build、compiler／flags、clock／counter、config、workload、日期與工具 |
| 結果 | 原始檔、計算方式、平均／分布／最大值與有效窗口 |
| 驗收 | 產品門檻來源、結果、尚未滿足的原因與依賴 |

Task status 同步回根 README。Source 結論與數字附可追溯的檔案／行號或原始測量；新增結論不覆寫外部研究的原始假設。

## 7. 可直接貼給內部 AI 的指令

```text
請繼續 FreeRTOS／RISC-V observability 研究。

你可存取我們內部產品原始碼。先讀研究套件的 README.md、
research/FreeRTOS-RISC-V-Observability-研究報告.md、
research/內部AI-接續研究任務.md 及 source-manifest.json。

目的：確認本產品 SDK 接入位置，量出真正資源與即時性成本，
並建立「問題→事件→trace→source→修正→重測」的可重現案例。

1. 先盤點產品事實與 source 差異，產出 product-facts.md、
   source-comparison.md；未知規格保持未知，不套用 Arm 案例數字。
2. 依 U01～U16 建立 task-status.md，列適用性、目的、依賴、
   目前可執行事項與驗收。先完成 U01／U08／U13／基本 U14，
   再依需求做 U02～U06／U12；其他任務依實際產品條件安排。
3. 可執行的 source 分析、研究分支最小接入、build、artifact 比較
   持續完成。做真正相同條件的 baseline／RAM／transport 對照。
4. 設備或服務可用時執行量測與故障測試；不可用時完成量測框架，
   寫明缺少條件。公式、object size、桌面 demo 不填成板上實測。
5. 用第 22 節的案例流程分析一個真實問題或明確控制的情境。
   Trace 配上 build／device／session／counter／loss／config／symbols。
   保存原始結果、異常窗口、source 原因與相同條件的修正前後證據。
6. 按第 23 節 MECE 分類檢查 R01～R27 與 U01～U16 的覆蓋，
   每項只有一個主要分類，跨領域依賴用引用表示。
7. 更新研究報告與 README：區分文件研究、source、build、host 模擬、
   板上量測與產品驗收。保留未完成項及原因，不以推測宣稱通過。

交付：產品事實／差異表、整合 diff、build 與 map、量測原始資料、
案例 trace／圖／修正比較、成本與任務狀態。敘述用台灣繁體中文，
保留 API、code、command、path。內部上傳或正式部署依既有授權範圍。
```

本次只準備交接資料，未存取內部產品 source、未上傳內網，也未執行上述產品整合或部署。
