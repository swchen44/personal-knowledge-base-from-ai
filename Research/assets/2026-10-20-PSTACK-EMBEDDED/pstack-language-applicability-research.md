# pstack 對 C、FreeRTOS 與 Linux 驅動的適用性研究

研究日期：2026-10-20。本文研究的是 AI agent 的 pstack skills，並非列印 Linux process stack 的同名 `pstack` 指令。

使用者指定的原始版是 [cursor/plugins 的 pstack](https://github.com/cursor/plugins/tree/main/pstack)。本機已下載的版本是第三方移植版 `michael-denyer/pstack-claude`，checkout 為 `49b68501b075ec1eb2755dd0d22fbf2492d67e97`，`package.json` 版本為 `0.9.94`。兩者不能只憑名稱視為完全相同。移植版 README 明示它移植自 Lauren Tan 的 Cursor pstack，同時保留另外宣告的政策分支。來源：[本機 README](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/README.md)、[固定版本 README](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/README.md)、[分支清單](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/tools/forks.json)。

## 結論

pstack 主要是分析、設計、除錯、審查與驗證的 agent 工作方法。這類方法可用於 C 專案；它不會因為底層專案不是 TypeScript 就失去作用。但「流程可跨語言」不等於「已具備所有語言、RTOS、晶片與 kernel 的專用知識或驗證能力」。已下載版本有明確的 TypeScript 專屬規則，也沒有在已檢查的 skills、docs 與 README 找到 FreeRTOS、CBMC、MMIO、DMA、KUnit 等專用工作流。判斷為：適合當 C/embedded 的通用工作流程底座，仍須接上專案自己的 toolchain、硬體限制與驗證程序。此段後半為根據下列 source evidence 的研究判斷。

## 原始 Cursor 版與已下載移植版

本次透過 GitHub API 取得原始版 `main` 的固定 SHA `ddf824aff1e55ba14bd666b30bce3fc69962abe6`，下載該 commit 的官方 archive，檢查 `pstack/` 的 172 個檔案與 56 個 `skills/*/SKILL.md`。數量是該快照的檔案觀察，不代表品質或支援語言數。完整 skills 名稱記錄於 [upstream-index.json](research-evidence/upstream-index.json)。

原始版直接證據如下。

- [create-verification-skill](https://github.com/cursor/plugins/blob/ddf824aff1e55ba14bd666b30bce3fc69962abe6/pstack/skills/create-verification-skill/SKILL.md) description 明寫 any language, framework, or platform；實際需觀察 repo，建立並實跑專案 harness。
- [create-formal-verification-skill](https://github.com/cursor/plugins/blob/ddf824aff1e55ba14bd666b30bce3fc69962abe6/pstack/skills/create-formal-verification-skill/SKILL.md) 同樣存在，明寫 any language、按問題選工具，且 pass 只涵蓋 bounds/model/assumptions。這不是再製版獨有新增功能。
- [type-system-discipline](https://github.com/cursor/plugins/blob/ddf824aff1e55ba14bd666b30bce3fc69962abe6/pstack/skills/principle-type-system-discipline/SKILL.md) 適用任何 statically-typed language；[typescript-best-practices](https://github.com/cursor/plugins/blob/ddf824aff1e55ba14bd666b30bce3fc69962abe6/pstack/skills/typescript-best-practices/SKILL.md) 則限定 ts/tsx。
- [bug-fix playbook](https://github.com/cursor/plugins/blob/ddf824aff1e55ba14bd666b30bce3fc69962abe6/pstack/skills/poteto-mode/playbooks/bug-fix.md) 要求同一 surface 重現及重新驗證。這可用於 embedded，但需要先有可操作的 target harness。
- 原始版的 `skills/` 與 `agents/` 搜尋 `FreeRTOS|Zephyr|bare.metal|JTAG|OpenOCD|KUnit|kselftest|MMIO|CBMC|Frama.C` 未命中。這只說明該範圍未見專屬操作說明。

下載版 [tools/upstream.json](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/tools/upstream.json) 記錄其 pstack 同步基準 `7b353f78f6ec193bdbe48ed8059444eb09b6878e`，不是本次最新原版 SHA。移植版的 [README](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/README.md) 與 [forks.json](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/tools/forks.json) 說明 Claude Code / Codex / Pi / Copilot 對應、project playbooks 與政策變動。原始版產生 `.cursor/skills/verify-<app>/`；下載版把生成 skill 命名為 `verify`，並有各 runtime 的不同載入方式。對 C 的基本適用判斷一致，執行指令與自治政策不能混用。

下文「已下載版」段落保留 port 的直接來源。經上述原版逐項核對，跨語言流程、TS 專屬規則、形式驗證界限、boundary 原則與 comment-sicko 例外在原始快照亦存在；未做兩版所有 scripts 的逐行等價性驗證。

## 已下載版的跨語言能力

| 範圍 | 原始檔證據 | 對 C 專案的意義與限制 |
| --- | --- | --- |
| 工作流程 | README 定義為改善 agent 結果的 skill stack；plugin README 說 skills 是 agent 讀取的 Markdown 指令 | 它不是某語言的 compiler 或 runtime。可以依 C repo 的 Makefile、compiler、測試與 debug 命令工作 |
| 架構與資料建模 | `poteto-mode` 原則包含 domain model、boundary、idempotence、共享狀態與 root cause | 可以用在 C 的狀態機、ownership、錯誤路徑、driver lifecycle。實際硬體與排程語意仍須由專案補充 |
| 靜態型別原則 | `principle-type-system-discipline` 明寫適用任何 statically typed language | 原則可轉譯為 C 的 enum、struct、opaque handle、API 合約，但 TypeScript 的 branded intersection、`never` 等語法不能照抄 |
| 回歸證據 | `tdd` 採用 repo 已有、成本合理的最小可執行測試；若不實際，允許最接近的可執行重現 | 可沿用既有 C unit test、測試 firmware 或板端重現，不必因 skill 名稱就新增大型 mock 架構 |
| 完成驗證 | `principle-prove-it-works` 要求觀察真實產物，不以「編譯通過」推論行為成功 | 對 firmware 而言，host build 或 simulator 通過不能自動代表板端 interrupt、DMA、timing 正確 |

來源：[本機 plugin README](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/README.md)、[固定版本 plugin README](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/README.md)、[本機 poteto-mode](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/poteto-mode/SKILL.md)、[固定版本 poteto-mode 原則](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/poteto-mode/SKILL.md#L43-L84)、[型別原則](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/principle-type-system-discipline/SKILL.md)、[TDD](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/tdd/SKILL.md)、[驗證原則](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/principle-prove-it-works/SKILL.md)。

### TypeScript 專屬部分

已下載版的 `typescript-best-practices` frontmatter 同時限定 `.ts` 與 `.tsx`。內容包含 `unknown`、`as`、`satisfies`、TypeScript type guard、Zod inference 與 discriminated union 的具體寫法。這些是特定語言規則，不該拿來評判 C 是否符合語法慣例。C 的狀態與邊界設計可借用其目的，具體機制需按 C、kernel 或供應商 SDK 規範實作。來源：[本機 skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/typescript-best-practices/SKILL.md)、[固定版本 skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/typescript-best-practices/SKILL.md)。

移植版自身的 Pi extension 與部分支援 scripts 使用 TypeScript、Bun 或 Node.js，這是 agent 工具的實作語言，不表示被研究或修改的專案必須使用它們。其 Codex mapping 把 compiler-independent 的工作流對應到 shell、`spawn_agent` 等工具，並另外列出 scripts 依賴。來源：[本機 package.json](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/package.json)、[固定版本 package.json](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/package.json)、[Codex mapping](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/poteto-mode/references/codex-tools.md#L74-L104)。

## 已下載版的驗證工具能力與邊界

### 行為驗證

`create-verification-skill` 的 description 宣稱可用任何語言、framework 或 platform；實際流程是先讀 repo 找 launch、drive、observe、isolate 的方法，再產生專案 skill。內建例子主要是 browser/CDP、PTY、HTTP、library 等，沒有一份即用的 FreeRTOS board、JTAG、SWD 或 kernel module 驗證腳本。必須先找出專案真實可執行的方法，再替專案編寫與實跑。技能也明確要求：若使用 stand-in，列出仍待真實目標驗證的差異；未實際執行的產物只能叫 draft。來源：[本機 skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/create-verification-skill/SKILL.md)、[固定版本 skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/create-verification-skill/SKILL.md)。

### 形式驗證

`create-formal-verification-skill` 明寫 `in any language, with whichever verification tool fits`。這是「由問題與 repo 選工具，產生專案驗證方法」的能力宣告，不是一個內附所有語言 verifier 的承諾。其工具選擇規則明確區分：

- 並行事件順序，預設考慮 TLA+ 等小型設計模型的 model checker。
- 真實程式碼的記憶體、溢位或資料結構性質，優先考慮直接作用在 code 的 verifier。
- 沒有適用的 verifier 時，要如實說明，對真實程式執行 generated-input tests，不能把手寫函式模型冒充實作證明。
- 結果只涵蓋模型、界限及假設；不是整個系統都被證明正確。

產出的專案 skill 必須記錄具體 code、property、command、工具版本、bounds、assumptions 與 sync commit，並故意破壞受保護的真實程式以確認檢查會失敗。`maintain-formal-verification-skill` 再追蹤實作與模型是否漂移，區分 model drift、真實 bug 與 blocked。這些是可信度要求；本次沒有替使用者的 firmware 或 driver 建立並執行任何形式驗證。來源：[本機 create skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/create-formal-verification-skill/SKILL.md)、[固定版本 create skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/create-formal-verification-skill/SKILL.md)、[本機 maintain skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/maintain-formal-verification-skill/SKILL.md)、[固定版本 maintain skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/maintain-formal-verification-skill/SKILL.md)。

### 搜尋到的領域支援

本次針對 `plugins/pstack/skills`、`docs`、`README.md` 搜尋 `FreeRTOS`、`firmware`、`MMIO`、`JTAG`、`SWD`、`CBMC`、`Frama-C`、`KUnit`、`kselftest`、`lockdep`、`KCSAN`、`KASAN`、`ISR`、`interrupt`、`mutex`、`spinlock` 與 `DMA`，沒有找到對應的領域專屬操作說明。`embedded` 命中的是「嵌入在使用者問題或 transcript 的文字」，不是嵌入式軟體支援。這是此 checkout 與搜尋範圍的負向觀察，不能推論作者從未使用它開發 embedded，也不能推論通用 skill 無法產生相關檢查。

## 用於晶片軟體時必須適配的原則

以下是根據已下載版原則做的工程判斷，並非 pstack 已完成的硬體支援或對原作者能力的判定。

| pstack 預設原則 | 需要補上的 embedded / kernel 限制 |
| --- | --- |
| `boundary-discipline` 說內部程式無條件信任型別，不重複檢查 | C 型別未必能表達指標生命期、範圍、硬體異步狀態與共享記憶體 ownership；不得因此刪掉必要的 runtime checks、assertions 或同步邊界 |
| `minimize-reader-load` 建議合併單一 caller wrapper 與薄 adapter | 有些 HAL、MMIO accessors、barriers、context 切換 API、測試替身介面有語意或工具鏈用途；不能只用 caller 數量或 LOC 決定刪除 |
| `no-comments` / `comment-sicko` 偏好刪註解與改造 code | 晶片 errata、暫存器 ordering、DMA ownership、ISR context、lock ordering 與 timing contract 常需要保留理由；此版本實際有 external platform/vendor/protocol、public API contract、無法用 code 表達的 issue/RFC 等保留例外，應把專案必要的註解明確納入規範 |
| 編譯、測試、model checker 各自能交付證據 | 必須分開報告 host、模擬器、板端、特定 kernel config 的結果；不得把一層通過外推到未執行的層 |

原文來源：[本機 boundary skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/principle-boundary-discipline/SKILL.md)、[固定版本 boundary skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/principle-boundary-discipline/SKILL.md)、[本機 reader-load skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/principle-minimize-reader-load/SKILL.md)、[固定版本 reader-load skill](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/principle-minimize-reader-load/SKILL.md)、[本機 no-comments](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/no-comments/SKILL.md)、[固定版本 no-comments](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/skills/no-comments/SKILL.md)、[本機 comment-sicko](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/agents/comment-sicko.md)、[固定版本 comment-sicko 例外](https://github.com/michael-denyer/pstack-claude/blob/49b68501b075ec1eb2755dd0d22fbf2492d67e97/plugins/pstack/agents/comment-sicko.md#L14-L28)。

## FreeRTOS、Linux 與 C 驗證工具的官方資料

以下為官方文件查核與工程建議，沒有在使用者 target 執行。

- **C 與 CBMC。** [CBMC 官方](https://www.cprover.org/cbmc/) 說明其檢查 C/C++ 記憶體安全、部分 undefined behavior 與 user assertions；以 loop unwinding 交給 solver。可作為 C buffer/queue/parser 的候選工具，但需正確 harness、假設與 unwinding 設定，不能外推板上時序與周邊硬體。
- **FreeRTOS 有實際 CBMC 用例。** [官方 FreeRTOS README 的 CBMC 章節](https://github.com/FreeRTOS/FreeRTOS#cbmc) 指向 `FreeRTOS/Test/CBMC/proofs`。存在官方 proof infrastructure 不代表你的 application 或 vendor port 已被驗證。
- **FreeRTOS ISR 規則依 port。** [官方 kernel book 第七章](https://github.com/FreeRTOS/FreeRTOS-Kernel-Book/blob/main/ch07.md) 說明 interrupt-safe API；[Cortex-M 官方文件](https://www.freertos.org/Documentation/02-Kernel/03-Supported-devices/04-Demos/ARM-Cortex/RTOS-Cortex-M3-M4) 另有 `configMAX_SYSCALL_INTERRUPT_PRIORITY` 與數值優先序規則。Cortex-M 數值規則不能套用所有晶片。建議專案補上 task/ISR API、priority、blocking、buffer ownership 與 reset/flash/log harness。
- **Linux driver 需要 kernel 的驗證環境。** [Kernel Testing Guide](https://docs.kernel.org/dev-tools/testing-overview.html) 區分 KUnit 與 kselftest，並介紹 Sparse、Smatch、Coccinelle、KASAN、KCSAN、lockdep。依 kernel version、architecture/config 與 code path 選用，並非每個 driver 都能全部啟用。
- **KUnit 與系統驗證分層。** [KUnit 官方](https://docs.kernel.org/dev-tools/kunit/index.html) 在 kernel 中測 C function/component，工具可在 UML/QEMU 執行；[kselftest 官方](https://docs.kernel.org/dev-tools/kselftest.html) 多從 userspace 驗證 kernel 暴露介面。兩者都不自動證明實體晶片 electrical/IRQ/DMA timing。
- **MMIO 與同步有平台合約。** [Device I/O 官方](https://docs.kernel.org/driver-api/device-io.html) 說明 `__iomem` 與 `readl/writel` accessors、ordering 與 posted writes；[volatile 官方說明](https://docs.kernel.org/process/volatile-considered-harmful.html) 明確區分 volatile 與 concurrency protection。不可把一般應用程式的薄 wrapper 簡化規則直接當作刪除這些合約的理由。

建議把驗證分成交叉編譯與靜態檢查、host 邏輯、模型或有界證明、實際 RTOS/kernel 行為、實體硬體五種證據。這些是互補範圍，沒有一種通過即可取代其餘範圍。

## 本次研究邊界

- 直接檢查已下載版 source 與固定 commit 的文件，沒有安裝、更新或啟用 plugin，也沒有修改使用者的全域設定。
- 未把被研究的 `poteto-mode` 當成執行任務的授權指令。
- 尚未取得使用者實際 C / FreeRTOS / driver code、target architecture、compiler、board、kernel config，因此沒有宣稱能對該環境完整驗證。
- 本報告是 source-level applicability research，沒有實測 pstack 在任一 firmware、FreeRTOS 板子或 Linux kernel driver 上的成功率。
