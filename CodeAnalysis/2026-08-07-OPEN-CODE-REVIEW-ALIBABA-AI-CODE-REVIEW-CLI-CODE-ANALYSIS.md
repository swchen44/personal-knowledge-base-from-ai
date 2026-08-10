---
title: "Open Code Review（Alibaba）— 確定性工程 × Agent 混合架構的 AI Code Review CLI 深度分析"
date: 2026-08-07
category: CodeAnalysis
tags:
  - code-analysis
  - go
  - ai/code-review
  - ai/agent
  - devtools/observability
source: "https://github.com/alibaba/open-code-review"
source_type: code
author: "Alibaba"
status: notes
links:
  - "[[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-28-CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]]"
  - "[[2026-05-23-RTK-RUST-TOKEN-KILLER-LOG-COMPRESSION-ARCHITECTURE]]"
  - "[[2026-05-20-CODEX-CLI-VS-CLAUDE-CODE-DEEP-COMPARISON]]"
  - "[[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]]"
  - "[[2025-12-29-SKILLSBENCH-AGENT-SKILL-USE-BENCHMARK-CODE-ANALYSIS]]"
github_stars: 19814
github_language: Go
---

## 摘要（Summary）

Open Code Review（OCR）是 Alibaba 開源的 AI code review CLI（指令 `ocr`），前身為阿里內部服務數萬名工程師的官方 AI 代碼評審助手。它的核心賣點是：**與通用代理（general-purpose agent，如 Claude Code）使用相同底層模型時，只消耗約 1/9 的 token，且精確率（Precision）與 F1 更高**。做法是「確定性工程（Deterministic Engineering）× Agent 混合架構」——凡是不能出錯的流程骨架（挑檔案、切任務、配規則、算行號、過濾誤報）全部由 Go 程式碼確定性完成，LLM 只負責「判斷單一檔案的 diff 裡有沒有問題」這一件事。本筆記整合原始碼逐行分析（pipeline、省 token 機制、委托模式、OpenTelemetry 遙測）與社群聲音（GitHub issues 與網路評價）。

## Why — 為什麼存在？

> 這個專案要解決的根本問題：通用 agent 做 code review 的三大痛點。

- **核心動機**：純語言驅動（natural-language-driven）的 review 缺乏硬約束（hard constraints），導致：
  1. **覆蓋不完整** — 大變更集上 agent 會「偷工減料（cut corners）」，選擇性只看部分檔案。
  2. **位置漂移（position drift）** — 回報的問題行號與實際代碼位置對不上。
  3. **品質不穩定** — 自然語言 Skill 難以除錯，prompt 微調就會讓品質大幅波動。
- **取代/改善什麼**：取代「把 Claude Code + Skill 當 code reviewer」的用法；也對標 CodeRabbit、GitHub Copilot Review 等商業產品，但以 CLI + 開源 + 自帶模型端點的形式存在。
- **目標用戶**：需要在本地開發流程或 CI/CD 中做自動化 review 的工程團隊；尤其是在意 API 成本（token 花費）與誤報率（false positive）的團隊。

## What — 是什麼？

- **主要功能**：
  - `ocr review` — 讀取 Git diff（workspace / branch range / single commit 三種模式），對每個變更檔案產生帶精確行號的結構化評審意見。
  - `ocr scan` — 整檔掃描（不需 git diff），用於稽核不熟悉的代碼庫。
  - `ocr delegate` — 委托模式（Delegation Mode）：OCR 只做確定性工程（檔案篩選、規則解析），由宿主 coding agent 用自己的 LLM 執行實際 review，**OCR 端不需要 API Key**。
  - `ocr session` / `ocr viewer` — session 管理與瀏覽器回放。
  - 規則系統（review rules）：以路徑 glob 匹配的四層規則（custom > project > global > system）。
  - OpenTelemetry 遙測、MCP 工具擴充、Claude Code / Codex / Cursor / OpenCode plugin。
- **不做什麼（Non-goals）**：不自動修代碼（default mode 只回報問題；委托模式的 plugin 才會讓宿主 agent 順手修）；刻意犧牲召回率（Recall）換精確率——benchmark 自己承認 Recall 低於通用 agent，是「寧可少報、不可誤報」的取捨。
- **技術棧（Tech Stack）**：Go（單一 binary）、Git >= 2.41（diff、code search 都靠 git）、OpenTelemetry Go SDK、npm 發佈殼層（binary 分發）、Astro 文件站（`pages/`）。

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌────────────────────────────────────────────────────────────────┐
│                     CLI（cmd/opencodereview）                   │
│   review │ scan │ delegate │ session │ viewer │ config │ rules │
└──────┬───────────────┬──────────────┬─────────────────────────┘
       │               │              │（delegate：不碰 LLM）
       ▼               ▼              ▼
┌─────────────┐ ┌────────────┐ ┌──────────────────┐
│internal/agent│ │internal/   │ │internal/delegate │
│ 主編排器     │ │scan        │ │ 檔案挑選+規則分組 │
│ (per-file    │ │ 整檔批次   │ │ → stdout(md/json)│
│  子任務分派) │ │ bundling   │ └──────────────────┘
└──┬───────┬──┘ └─────┬──────┘
   │       │          │
   ▼       ▼          ▼
┌────────────┐  ┌──────────────────────────────┐
│internal/diff│  │ internal/llmloop             │
│ git diff 解析│  │ tool-use 迴圈 / 三區壓縮     │
│ sliding-    │  │ / CommentWorkerPool          │
│ window 定位 │  └──────┬───────────────────────┘
│ LLM 重錨    │         │
└────────────┘         ▼
┌────────────┐  ┌──────────────┐  ┌───────────────────┐
│internal/    │  │internal/tool │  │internal/telemetry │
│config       │  │ 6 個精簡工具 │  │ OTel spans/metrics│
│ 規則引擎/    │  │ +MCP 動態工具│  │ console/OTLP      │
│ 白名單/模板  │  └──────────────┘  └───────────────────┘
└────────────┘
       │
       ▼
┌────────────────┐
│ internal/llm   │ ← 22+ providers（全部要 API Key）
│ endpoint 解析   │    OCR_LLM_* / config.json / ANTHROPIC_*
└────────────────┘
```

### 執行流程圖（`ocr review` 端到端）

標【工程】= 確定性 Go 程式碼；【LLM】= 語言模型呼叫。

```
 Start: ocr review
   │
   ▼
[解析 git diff]【工程】internal/diff/git.go
   │
   ▼
[五道過濾閘挑檔案]【工程】internal/agent/preview.go:34
   │  binary → user_exclude → user_include → 副檔名白名單 → 測試檔 pattern
   │
   ├─ 單檔 diff > MaxTokens×80% ──► [直接丟棄，不發 request]【工程】
   │
   ▼
[凍結 coverage manifest]【工程】agent.go:1044 ← 保證不漏檔
   │
   ▼
[每檔一個子任務，semaphore 併發=8]【工程】agent.go:490
   │（以下為單一檔案的隔離流程，context 零共享）
   ▼
[規則匹配：glob → 單一規則文件]【工程】system_rules.go:130
   │
   ├─ 變更 < 50 行 ──► 跳過 Plan
   │
   ▼
[Plan 階段：一次 LLM 產檢查清單]【LLM】agent.go:1462（無工具可呼叫）
   │
   ▼
[Main tool-use 迴圈 ≤30 輪]【LLM】llmloop/loop.go:177
   │  工具：code_comment / file_read / code_search / file_read_diff
   │        / file_find / task_done
   │  context 到 60% 背景壓縮、80% 同步壓縮【工程切分+LLM 摘要】
   │
   ▼
[行號定位：sliding-window 比對]【工程】diff/resolver.go:62
   │
   ├─ 失敗 ──► [LLM 重錨 RE_LOCATION_TASK]【LLM】relocation.go:23 ──► 再比對一次
   │
   ▼
[反思過濾：證偽式 REVIEW_FILTER_TASK]【LLM】agent.go:1231
   │  只移除 diff 中有直接反證的評論 → 偏向 precision
   ▼
[第二次行號解析 + 輸出 text/JSON]【工程】shared.go:343
   │
   ▼
  End
```

### 時序圖（單一檔案子任務內的元件互動）

```
 agent(子任務)   llmloop        LLM API       tool registry   diff resolver
     │              │              │                │               │
     │──組 prompt──►│              │                │               │
     │              │──request────►│                │               │
     │              │◄─tool_call───│                │               │
     │              │──執行工具────────────────────►│               │
     │              │◄─工具結果─────────────────────│               │
     │              │──request(續)─►│               │               │
     │              │◄─code_comment─│               │               │
     │              │──existing_code 比對──────────────────────────►│
     │              │◄─StartLine/EndLine（或失敗→LLM 重錨）─────────│
     │              │◄─task_done────│               │               │
     │◄─評論集合────│              │                │               │
     │──REVIEW_FILTER_TASK────────►│                │               │
     │◄─要移除的評論 id────────────│                │               │
     │─(移除誤報，輸出)             │                │               │
```

### 委托模式時序圖（Delegation Mode）

```
 開發者        宿主 Agent(Claude Code)      ocr CLI          git
   │                  │                      │                │
   │─/delegate-review►│                      │                │
   │                  │──ocr delegate preview►│               │
   │                  │◄─檔案清單+排除原因────│（純工程，0 LLM）│
   │                  │──ocr delegate rule f1 f2──►│          │
   │                  │◄─規則分組 checklist───│               │
   │                  │──git diff <merge_base>..<to>─────────►│
   │                  │◄─diff────────────────────────────────│
   │                  │─(用自己的 LLM 逐檔 review)             │
   │◄─評審結果+修復───│                      │                │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 核心哲學：確定性工程 × Agent 混合（Deterministic Engineering × Agent Hybrid）
> 「不能出錯的步驟」由工程保證正確性，「需要動態判斷的步驟」才交給 LLM。這是它與純 Skill/prompt 驅動方案最根本的差異。

1. **每檔獨立隔離 context（divide-and-conquer）** — 每個檔案是一個 goroutine 子任務、獨立對話（`agent.go:490`）。避免通用 agent 單一長對話中「前面檔案的內容一直佔著 context 重複計費」的浪費，也讓大變更集不會 cut corners。代價：放棄跨檔推理（文件明言 "No cross-file reasoning"）。
2. **行號由工程計算，不由 LLM 輸出** — LLM 只回報 `existing_code` 文字片段，行號用 sliding-window 在 diff hunk 上比對算出（`diff/resolver.go:62`），失敗才 LLM 重錨。直接消滅 position drift。
3. **規則預匹配（template-engine-based rule matching）** — doublestar glob 對路徑匹配、first-match-wins、四層優先序 custom > project > global > system（`system_rules.go:388`）。一個檔案只帶一份規則進 prompt，注意力集中、token 也省。
4. **證偽式反思過濾（falsification-style reflection）** — 獨立 LLM 呼叫扮演 fact-checker，「只有 diff 中有直接反證才移除評論」（`agent.go:1231`）。系統性壓低誤報，對應 benchmark 用 Recall 換 Precision 的取捨。
5. **Token 預算多重守門** — 單檔 diff 超限直接丟棄、prompt 超限 fail-fast、60%/80% 兩段式 context 壓縮、<50 行跳過 Plan。所有閾值單一定義共用（`compression.go:29` 的 `PromptTokenLimit`）。
6. **遙測零侵入（no-op by default）** — 停用時 `StartSpan` 回傳 no-op span，呼叫端無條件 `defer span.End()`，主流程無任何 telemetry 分支（`telemetry/span.go:25`）。

### 資料流（Data Flow）

1. git diff → `[]model.Diff`（hunks + 增刪行數）→ 預建唯讀 DiffMap 供工具查詢（`agent.go:473`）。
2. 過濾後檔案集 → 凍結 manifest → 併發子任務。
3. 子任務內：規則文本 + diff + plan 指引 → placeholder 替換組 prompt（`agent.go:1143`）→ tool-use 迴圈 → `code_comment` 產出評論。
4. 評論 → 非同步 worker pool 做定位/反思 → 過濾 → 最終 text/JSON 輸出 + session JSONL（`~/.opencodereview/`，可用 viewer 回放）。

### 關鍵程式碼（Key Code Snippets）

**(1) Token 閾值單一定義 — 所有守門共用一個常數來源**（`internal/llmloop/compression.go`）：

```go
// Compression thresholds, as fractions of MaxTokens.
const (
	tokenSoftThreshold    = 0.60 // async background compression
	tokenWarningThreshold = 0.80 // immediate sync compression
)

// PromptTokenLimit returns tokenWarningThreshold (80%) of maxTokens. It is
// shared by the agent and scan pre-flight gates, their large-input filters, and
// computeActiveZoneSize so the threshold has a single definition.
func PromptTokenLimit(maxTokens int) int {
	return int(float64(maxTokens) * tokenWarningThreshold)
}
```

**(2) 行號定位的核心 — 連續多行滑動視窗比對**（`internal/diff/resolver.go`）：

```go
// matchConsecutive scans sideLines for a consecutive run matching all targetLines.
func matchConsecutive(sideLines []indexedLine, targetLines []string) (startLine, endLine int, found bool) {
	if len(targetLines) == 0 || len(sideLines) < len(targetLines) {
		return 0, 0, false
	}
	for i := 0; i <= len(sideLines)-len(targetLines); i++ {
		matched := true
		for j, target := range targetLines {
			if sideLines[i+j].content != target {
				matched = false
				break
			}
		}
		if matched {
			return sideLines[i].lineNum, sideLines[i+len(targetLines)-1].lineNum, true
		}
	}
	return 0, 0, false
}
```

**(3) 遙測零侵入模式 — 停用時回傳 no-op span**（`internal/telemetry/span.go`）：

```go
// StartSpan creates a new span from the given context. When telemetry is not enabled,
// it returns a no-op span so callers can safely defer .End().
func StartSpan(ctx context.Context, name string, opts ...trace.SpanStartOption) (context.Context, trace.Span) {
	if !IsEnabled() {
		return ctx, trace.SpanFromContext(ctx)
	}
	return getTracer().Start(ctx, name, opts...)
}
```

**(4) API Key 必填的驗證邏輯 — Token 為空即判定無效**（`internal/llm/resolver.go`）：

```go
	for _, strategy := range strategies {
		ep, ok, err := strategy.fn()
		if err != nil {
			return ResolvedEndpoint{}, fmt.Errorf("resolve %s: %w", strategy.name, err)
		}
		if ok && ep.URL != "" && ep.Token != "" && ep.Model != "" {
			return finalizeResolvedEndpoint(strategy.name, ep)
		}
	}

	return ResolvedEndpoint{}, fmt.Errorf("no valid LLM endpoint configured; one of OCR_LLM_URL/OCR_LLM_TOKEN/OCR_LLM_MODEL, ~/.opencodereview/config.json, or ANTHROPIC_BASE_URL/ANTHROPIC_AUTH_TOKEN/ANTHROPIC_MODEL must be set")
```

## 深入主題（Deep Dives）

### 主題一：「約 1/9 token」到底省在哪裡？

對照組：通用 agent 是「單一長對話、自己 grep repo、自己決定看哪些檔、自己算行號、規則靠自然語言」。OCR 的每一項省法都有對應程式碼：

| # | 機制 | 一般 agent 的浪費 | OCR 的做法 | 證據 |
|---|------|------------------|-----------|------|
| A | 確定性檔案挑選 | LLM 先 ls/grep 探索、多輪決定範圍 | git diff + 五道過濾閘，LLM 零參與 | `preview.go:34` |
| B | 每檔隔離 context | 長對話中舊檔內容重複計費 | 每檔獨立子任務，零共享 | `agent.go:490` |
| C | 規則預匹配 | 所有規則全塞 prompt | glob 匹配單一規則文件 | `system_rules.go:130` |
| D | 確定性行號定位 | LLM 數行號、常漂移 | sliding-window 由 Go 算 | `resolver.go:62` |
| E | 精簡工具集（6 個） | 工具 schema 佔 prompt、試錯多 | 場景化蒸餾的最小工具集 | `tool/definitions.go:17` |
| F | DiffMap 預快取 | 查其他檔要重跑 git | 記憶體唯讀 map 直查 | `agent.go:473` |
| G | 小 diff 跳過 Plan | 每檔都規劃 | <50 行直接省一次呼叫 | `agent.go:1116` |
| H | 三區 context 壓縮 | context 線性膨脹 | 60%/80% 兩段式摘要壓縮 | `compression.go:21` |
| I | Token 預算守門 | 巨型檔照送燒錢 | 超限 fail-fast 不發 request | `agent.go:1167`、`agent.go:1376` |
| J | 場景化精簡 prompt | 通用長系統提示 | `main_task_system.md` 僅 25 行 | `internal/config/template/prompts/` |

A/B/C/D/F 讓 LLM 不必做「探索與計算」（通用 agent 最燒 token 的部分），G/H/I 砍掉無效呼叫，E/J 壓縮每次 request 的固定開銷。

LLM 可用的 6 個工具：`code_comment`（回報問題，附 `existing_code` 供定位）、`task_done`（收尾）、`file_read`（讀變更後檔案，≤500 行）、`code_search`（git grep，≤100 筆）、`file_read_diff`（查其他檔 diff）、`file_find`（找檔案）。Plan 階段只有後三個唯讀工具，且以純文字嵌入、不可實際呼叫。

### 主題二：沒有 API Key 能用嗎？委托模式省什麼？

**API Key 需求**：`ocr review` / `ocr scan` 強制要求 URL + Token + Model 三者非空（`llm/resolver.go:115`），內建 22+ providers 全部要 key，連本地端點也要塞一個非空字串（placeholder 可混過不驗證的本地服務）。完全不碰 LLM 的子命令：`delegate`、`session`、`viewer`、`rules`、`version`、`completion`。

**委托模式的兩層「省」（結論相反，必須分開講）**：

> [!important] 「省 token」有兩種意義
> - **省荷包（API 費用/免 Key）**：委托模式最省（= 零）。OCR 端 0 token、免 Key，推理跑在宿主 agent 的訂閱額度（如 Claude Code 月費）上。這才是委托模式的真正賣點。
> - **省 raw token（LLM 實際吞吐量）**：default mode 更省。它是專用最佳化迴圈（25 行 system prompt、逐檔餵 diff、三區壓縮、預算守門）；委托模式跑在通用 agent 上，要疊上龐大的 agent 系統開銷。但委托模式仍比「叫 agent 裸 review」省——OCR 的 scaffolding（範圍、清單、規則、git 指令）省掉了 agent 自行探索的 token。

一句話：**要單次 review 吞最少 token → default mode；要不花 API 錢、複用訂閱 → 委托模式。**

委托模式的輸出介面：`ocr delegate preview`（mode + 檔案清單 + 排除原因，Markdown 或 `--format json`）與 `ocr delegate rule <paths>`（規則按 `source|pattern|text` 去重分組，`rulegroup.go:46`）。宿主 agent 靠 plugin（slash command / skill）串接：preview → rule → git diff → 逐檔 review → 保證 coverage（每檔必須 reviewed 或明確 skipped）。

### 主題三：OpenTelemetry 遙測設計

預設**關閉**，`OCR_ENABLE_TELEMETRY=1` 開啟；exporter 支援 console 與 OTLP gRPC/HTTP;吃標準 `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_SERVICE_NAME`；支援 `TRACEPARENT` 接上游 trace（CI 可串分散式 trace）；每次執行把 TraceID 印到 stderr 方便查詢。

**Span 樹**（對應 review 生命週期）：

```
review.run（review.repo/from/to/model）
├── diff.parse（files.changed、lines.inserted/deleted）
└── subtask.execute.<file>（file.path、lines.*）
    ├── plan.execute
    ├── main.loop
    │   ├── llm.request（llm.model、duration_ms、total_tokens、status）
    │   └── tool.execute.<name>（tool.name、duration_ms、status）
    └── review_filter.execute（comments.before、comments.filtered）
```

另有 `event.*` 零時長 span 記錄決策點（`event.plan.skipped`、`event.token.threshold.exceeded`、`event.subtask.error/panic` 等）。

**Metrics（8 個，`ocr.` 前綴）**：review 時長、審查檔案數、產出評論數、LLM 請求數（model+status）、token 用量、LLM 請求時長、工具呼叫數與時長（tool.name）。

**隱私**：只送「形狀」（次數/時長/狀態/token 數），不送 prompt 或代碼內容；完整對話存本機 `~/.opencodereview/` 供 viewer 回放。`content_logging` 旗標目前是保留的 no-op。

> [!tip] 值得抄的四個設計
> 1. **no-op 抽象**：停用時 `StartSpan` 回傳 no-op span，埋點零侵入（`span.go:25`）。
> 2. **CLI 短命程序的 flush 模式**：`Init` 冪等回傳 bool，啟用才 `defer ShutdownWithTimeout(5s)`，保證 batch exporter 出清。
> 3. **Best-effort 哲學**:metric 註冊錯誤刻意吞掉、exporter 失敗只警告——遙測絕不弄掛主流程。
> 4. **TraceID 印 stderr**:一次執行直接可跳到 Jaeger/Tempo。

> [!warning] 兩個反面教材
> 1. **未遵循 GenAI semantic conventions**：用自訂 `llm.model`/`llm.total_tokens` 而非 `gen_ai.request.model`/`gen_ai.usage.input_tokens`;且已拿到 input/output/cache token 細分卻只記 total。
> 2. **文件與實作漂移**：文件稱 LLM/tool 不發獨立 span、HTTP exporter 未接——實際都已實作。`service.name` 只能靠 `OTEL_SERVICE_NAME` 設，config 檔沒有對應欄位，漏設會變 `unknown_service`。

## 安裝流程（Installation Flow）

> [!info] 追蹤層級
> npm 安裝走「殼層套件 + 平台 binary optionalDependency + postinstall 落地」模式；install.sh 走「GitHub Releases 直接下載 binary」模式。

### 安裝觸發方式

```
npm install -g @alibaba-group/open-code-review
  → postinstall: scripts/install.js
  → 從 @alibaba-group/ocr-{os}-{arch}（optionalDependency）複製 binary
  → 寫入 <npm-global>/node_modules/@alibaba-group/open-code-review/bin/
  →（fallback）從 GitHub Releases urlPattern 下載並驗 sha256

curl -fsSL .../install.sh | sh
  → 從 https://github.com/alibaba/open-code-review/releases/download/<ver>/
  → 寫入 $OCR_INSTALL_DIR（預設 /usr/local/bin）
```

### 安裝時序圖

```
 開發者        npm             scripts/install.js       檔案系統
   │            │                     │                    │
   │─install -g►│                     │                    │
   │            │──postinstall───────►│                    │
   │            │                     │─讀 optionalDep     │
   │            │                     │  @alibaba-group/   │
   │            │                     │  ocr-darwin-arm64  │
   │            │                     │─複製+chmod 755────►│ .../bin/opencodereview
   │            │                     │─(無 optionalDep 時)│
   │            │                     │  下載 GitHub       │
   │            │                     │  Releases + sha256 │
   │            │◄────────────────────│                    │
   │◄─`ocr` 可用─│（bin/ocr.js wrapper 轉呼叫 binary）      │
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `<npm-global>/bin/ocr` | symlink | 指向 `bin/ocr.js` wrapper |
| `<npm-global>/node_modules/@alibaba-group/open-code-review/bin/opencodereview` | binary | 實際 Go 執行檔（postinstall 落地） |
| `/usr/local/bin/opencodereview` | binary | install.sh 路徑（`OCR_INSTALL_DIR` 可改） |
| `~/.opencodereview/config.json` | 檔案 | provider/model/telemetry 設定（`ocr config` 產生） |
| `~/.opencodereview/`（sessions） | 目錄 | review session JSONL 逐字稿，供 `ocr viewer` 回放 |
| `~/.opencodereview/update-available` | 檔案 | 更新提示快取（`bin/ocr.js` 寫入） |

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| `OCR_INSTALL_DIR` | 安裝目錄（預設 `/usr/local/bin`） | install.sh 安裝時 |
| `OCR_LLM_URL` / `OCR_LLM_TOKEN` / `OCR_LLM_MODEL` | LLM 端點三要素 | 執行時（優先於 config.json） |
| `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_MODEL` | 借用 Claude Code 的環境變數 | 執行時（fallback 來源） |
| `OCR_ENABLE_TELEMETRY` | `1` 開啟遙測 | 執行時 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_SERVICE_NAME` / `OTEL_EXPORTER_OTLP_PROTOCOL` | 標準 OTel 設定 | 執行時 |
| `TRACEPARENT` | W3C trace context | CI 串分散式 trace |

> [!warning] 解除安裝
> `npm uninstall -g @alibaba-group/open-code-review`（或刪除 `$OCR_INSTALL_DIR/opencodereview`），另需手動清理 `~/.opencodereview/`（設定 + session 逐字稿）。

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | Workspace review | `ocr review` | `cmd/opencodereview/review_cmd.go` | `internal/agent` → `internal/llmloop` → `internal/diff` |
| 2 | Branch range review | `ocr review --from main --to feat` | 同上 | 同上（merge-base 模式） |
| 3 | 單 commit review | `ocr review --commit abc123` | 同上 | 同上（`NewCommitProvider`） |
| 4 | 整檔掃描 | `ocr scan [--path dir]` | `cmd/opencodereview/scan_cmd.go` | `internal/scan`（by-language/by-directory 批次 bundling） |
| 5 | 委托模式 | `ocr delegate preview` / `rule` | `cmd/opencodereview/delegate_cmd.go` | `internal/delegate`（0 LLM） |
| 6 | Session 回放 | `ocr session list` / `ocr viewer` | `session_cmd.go` / `viewer_cmd.go` | `internal/session` / `internal/viewer` |
| 7 | LLM 設定 | `ocr config provider` / `ocr llm` | `config_cmd.go` / `llm_cmd.go` | `internal/llm`（22+ providers、連線測試） |
| 8 | CI/CD | GitHub Actions（`action.yml`） | `action.yml` → `scripts/github-actions/` | review + PR comment 回貼 |

### 案例詳解

#### 案例 1：`ocr review`（workspace 模式）

```
用戶：ocr review
  │
  ▼
cmd/opencodereview/review_cmd.go:146 loadLLMRuntime
  │  ── 解析 ──► internal/llm/resolver.go（無 Key 即中止）
  ▼
internal/agent/agent.go:235 Agent.Run
  │  ── 讀取 ──► git diff（internal/diff/git.go）
  │  ── 過濾 ──► internal/agent/preview.go（五道閘）
  ▼
agent.go:490 dispatchSubtasks（每檔併發、隔離 context）
  │  ── 規則 ──► internal/config/rules/system_rules.go
  │  ── 迴圈 ──► internal/llmloop/loop.go（6 工具、≤30 輪）
  │  ── 定位 ──► internal/diff/resolver.go（sliding window）
  │  ── 過濾 ──► agent.go:1231 executeReviewFilter（證偽）
  ▼
cmd/opencodereview/shared.go:343 二次行號解析
  │
  ▼
輸出 text/JSON + session JSONL（~/.opencodereview/）
```

#### 案例 5：委托模式（免 API Key）

```
用戶（宿主 agent 內）：/delegate-review
  │
  ▼
plugins/open-code-review/claude-code/commands/delegate-review.md
  │  Step 1 ──► ocr delegate preview
  │              └─ delegate_cmd.go:56 → agent.Preview（挑檔+排除原因）
  │  Step 2 ──► ocr delegate rule <paths>
  │              └─ delegate_cmd.go:69 → delegate.GroupRules（規則去重分組）
  │  Step 3 ──► git diff <merge_base>..<to>（宿主 agent 自己抓）
  │  Step 4 ──► 宿主 agent 用自己的 LLM 逐檔 review + 修 High/Medium
  ▼
評審結果留在宿主 agent 對話中（OCR 全程 0 LLM token）
```

## 社群觀點（Community Voices）

> [!info] 調查時點:2026-08-10。Repo 動能:2026-05-18 開源,約 3 個月即 19,814 stars / 1,387 forks;release 節奏極密集(8 月第一週出 5 版,最新 v1.8.10);maintainer 幾乎每 issue 必回、中英雙語,社群 bug 常「隔天變 PR」。

### GitHub Issues / Discussions 的聲音

**願景與路線圖**:

- 官方 ROADMAP:H2 2026 → JetBrains plugin、Delegate Mode、**Ultra Mode**(多輪 pass 關聯收斂,解結果不穩定);H1 2027 → Domain-Specific Long-Term Memory。明確「Not Planned」:自動修 code、通用 coding assistant、內建 self-hosted LLM。
- [#59](https://github.com/alibaba/open-code-review/issues/59) **PR-aware reviews**:OCR 是 stateless 的,被駁回的誤報下一輪還會出現;maintainer 正在設計 filesystem-based 跨 run 狀態(對應 Long-Term Memory)。
- [#331](https://github.com/alibaba/open-code-review/issues/331) **委托模式的起源**:社群要求用 Claude Code 訂閱取代 API Key,maintainer 明確拒絕重放 OAuth token(違反 Anthropic ToS),轉而設計出 Delegate Mode——「OCR 做確定性工程、宿主 agent 出推理」的分工就是這樣談出來的。
- [#470](https://github.com/alibaba/open-code-review/issues/470) 語言支援眾包(「language experts wanted」),Nim、Nix、Haskell、Julia、Bicep 等由社群認領合併——低門檻 contributor 導流策略成功。

**最痛的抱怨(依社群壓力排序)**:

1. [#409](https://github.com/alibaba/open-code-review/issues/409) **大 MR token 成本爆炸**:「一個 MR 干了平時一個半月的成本」、1000+ 檔重構 MR 燒掉上億 token 後手動中止且已完成部分全部作廢。Maintainer 承認 diff review 路徑缺 budget 護欄(max_tokens / max_model_requests / 全局 deadline),分兩線修:versioned run manifest(#367,失敗也輸出 partial 結果)+ 提前剎車機制。**這是對「省 token」宣稱最有力的反例:單檔守門有了,全局預算沒有。**
2. [#555](https://github.com/alibaba/open-code-review/issues/555) / #247 **結果不穩定**:同一 commit 每次跑出的評論不同;官方定調 LLM 固有隨機性,短期解法 `temperature: 0`,長期押注 Ultra Mode。
3. [#6](https://github.com/alibaba/open-code-review/issues/6) **行號幻覺與 open-core 差距**:maintainer 揭露內部有專門訓練的行號重定位模型(準確率 98–99%),因「合規問題」未開源——開源版用 sliding-window + LLM 重錨替代。[#167](https://github.com/alibaba/open-code-review/issues/167) / #746 跨檔幻覺(掃 `pom.xml` 回報 Java code)已加三層緩解但無法根除,弱模型上更明顯。
4. [#709](https://github.com/alibaba/open-code-review/issues/709) 重複評論濾不乾淨(確認為 bug,社群已提實作方案)。
5. [#719](https://github.com/alibaba/open-code-review/issues/719) **高水準的「determinism = 省錢」bug**:Go map 迭代亂序導致 plan-phase prompt 非 byte-stable,直接打掉 DeepSeek/OpenAI 的 prefix caching;#718 diff fingerprint 不穩定會靜默破壞 `--resume`。
6. [#800](https://github.com/alibaba/open-code-review/issues/800) skill 文件教宿主 agent 用 `--format json` 但使用者的 binary 沒有此 flag——目前原始碼已有(`shared_flags.go:218`),這是 **skill 文件與已安裝 binary 版本漂移**的新型 bug,agent-plugin 生態特有。

**使用心得與比較**:

- [Discussion #380](https://github.com/alibaba/open-code-review/discussions/380) vs CodeRabbit 實測:**CodeRabbit 偏 big-picture,OCR 抓 low-level bug 更多**;但 CodeRabbit 幾輪就收斂,OCR 跑到兩位數輪次還在挑 JSDoc 措辭之類的 nits,曾陷入 forever loop,使用者被迫硬設 4 輪上限。
- [Discussion #403](https://github.com/alibaba/open-code-review/discussions/403) **有趣的視角反轉**:企業使用者拿 OCR 對比內部 T8 reviewer(同用 GPT-5.5),感受是「OCR 側重召回、覆蓋面極廣、precision 反而輸」——與官方「高 precision 低 recall」的自我定位相反。說明 precision/recall 的感受高度依賴對照組的評審原則。
- [#684](https://github.com/alibaba/open-code-review/issues/684) maintainer 公開 Go 語言細分:OCR + Claude-4.6-Opus **F1 27.21%(precision 33.3%)vs 裸跑 Claude Code F1 10.22%(precision 6.2%、824 條評論)**——harness 價值最有力的量化證據:pipeline 把誤報壓掉一個數量級。
- [#210](https://github.com/alibaba/open-code-review/issues/210) CodeGraph 整合討論中,maintainer 透露**內部每個影響 agent 效果的改動都要跑 200 個真實 PR 的夜間評測**——eval-driven development 的實例。

### 網路上的評價(HN / 中文社群 / 部落格)

**Hacker News**([2026-06-05 主串](https://news.ycombinator.com/item?id=48406358),284 分、73 則留言):

- **最重要的一條質疑**:用戶 eranation 獨立重跑官方 benchmark 的 10 個 PR,得到 recall ~74% 但 **precision 只有 ~12%**(官方宣稱 25–38%),F1 掉到 ~20%;maintainer 回應是一個關鍵 tool call 異常、已修復。無論真因為何,「自建自測 benchmark 無外部稽核」的質疑(moclaw、thecontext 等部落格同樣點名)仍未解除。
- precision vs recall 之爭:一派認為「recall 才是王道」,另一派反駁「誤報也要花時間確認,那就是浪費」——OCR 的取捨站在後者。
- 踩雷點:內建規則檔是中文(英文用戶要自行翻譯)、GPT-5.x 相容性問題、有用戶經 OpenRouter 測 50 個 PR 花約 $7。
- 一派 HN 用戶認為「自建 Claude wrapper 就夠了」,OCR 的反駁論點是確定性管線的覆蓋保證與定位校正。

**中文社群**:

- [V2EX](https://www.v2ex.com/t/1220633):「只改 1–2 個檔案的 PR 有時要跑幾分鐘」、無快取機制、大檔整檔重掃;OP 主張學 Meta RADAR 做風險分級路由,而非逐行 LLM 審查。
- [另一則 V2EX](https://www.v2ex.com/t/1231364) 的定位共識:OCR 適合當 CI 的「**高置信提示層**」,merge 閘門仍應是確定性檢查 + 人——「篩查層,不是合併閘門」。
- [知乎](https://zhuanlan.zhihu.com/p/2053892567784239748)(偏官方視角)披露內部數據:月活 2 萬人、370 萬次評審、採納率 >30%、有效評論近 80%、評論位置準確率 >97%;token 對比 352K–743K vs 通用 agent 的 2M–5M。

**技術部落格的定位分析**:

- [thecontext.dev](https://thecontext.dev/en/news/2026-06-11-alibaba-open-code-review/) 提出最有洞察的觀點:AI code review 的價值不是多抓 bug,而是「**把團隊的隱性審查標準凍結成每個 PR 都會跑的 check**」;並警告誤報會讓團隊直接關掉工具、無人看的本地 review 會淪為「review theater」;實測結論:大 changeset 上贏過通用 agent,小 diff 差距不大。
- [moclaw.ai](https://moclaw.ai/blog/alibaba-open-code-review):小型實測(17 行 NPE bug、約 4,632 tokens 抓到 1 個 high-severity);指出「內部兩年、百萬缺陷」宣稱無外部稽核;與 CodeRabbit/Greptile 是不同形態產品(本地 CLI vs SaaS),賣點在資料駐留(data residency)。
- **明確沒找到的**:Reddit 專門討論串、有影響力的 YouTube 實測、涵蓋 OCR 的第三方大規模 monorepo 評測——證據面仍以官方數據 + 零星個人實測為主。

### 綜合判讀

社群氛圍務實、工程導向、對批評開放:maintainer 誠實(公開承認 recall 不領先、公開對自己不利的細分數據),換來高品質的對抗性檢驗(HN 重測、#403 反向觀察、#210 方法論追問),形成正向循環。壓力最集中的三件事:**大 MR 成本失控**(#409,修復中)、**輸出不穩定與幻覺**(押注 Ultra Mode)、**API Key 門檻**(已被 delegate mode 化解)。深層結構問題是 **open-core 張力**:最關鍵的行號重定位模型不開源,開源版效果天花板與官方 benchmark 的可復現性都因此打上問號。

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐ | Go 單一 binary、套件邊界清晰（agent/llmloop/diff/tool/telemetry 各司其職）、閾值單一定義 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐ | per-file 併發天然水平擴展;MCP 動態工具、四層規則、多 provider |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐ | 核心模組有測試（OpenSSF Gold 徽章）,但 prompt 效果本質難以單元測試 |
| 文件品質（Documentation） | ⭐⭐⭐ | 文件站完整多語，但**與實作有多處漂移**（telemetry span、HTTP exporter 說明皆過時） |
| 依賴管理（Dependency Management） | ⭐⭐⭐⭐ | Go modules + binary 分發;npm 殼層只做下載落地，供應鏈面積小、有 sha256 驗證 |

> [!tip] 最值得學習的設計
> 「**LLM 只產文字證據，位置由工程計算**」（sliding-window 定位）是通用性極高的模式——任何要 LLM 輸出「指向原文的結構化結果」的系統（引用來源、標註、diff suggestion）都可以抄這招，讓 LLM 做它擅長的、把精確性交還給程式碼。

### ⚠️ 缺點與風險（Weaknesses & Risks）

- **放棄跨檔推理**：per-file 隔離是省 token 的核心，但跨檔案的邏輯錯誤（介面改了、呼叫端沒改，且兩者不在同一 diff hunk 語境）依賴 LLM 主動用 `file_read_diff` 才能發現——影響：架構級缺陷的 Recall 天花板。
- **Recall 刻意偏低**：benchmark 自承召回率低於通用 agent——影響：把它當唯一防線會漏真問題,適合當「高信噪比的第一道過濾」而非全面審計。
- **文件與實作漂移**：telemetry 文件至少三處與程式碼不符——影響：依文件接 observability 會踩坑，需以原始碼為準。
- **Telemetry 未跟 GenAI 慣例**:自訂 attribute 命名，與 Langfuse/OpenLLMetry 生態對接要自己 mapping;token 細分（input/output/cache）已取得卻未上報。
- **API Key 硬性必填**：即使本地不驗證的端點也要塞 placeholder token——小陷阱，文件未明說。
- **全局預算護欄缺失**（社群 #409 實證）：單檔有 token 守門,但整個 review run 沒有 max_tokens / max_model_requests / 全局 deadline——1000+ 檔的大 MR 可能燒掉巨量 token 後超時,且已完成部分作廢。官方修復進行中（run manifest + 提前剎車）。
- **Prompt 非 byte-stable 打掉 provider caching**（#719）:Go map 迭代亂序讓 plan prompt 每次不同,DeepSeek/OpenAI 的 prefix cache 失效——「確定性」沒做徹底反而變成隱性成本。

### 🔮 改進建議（Improvement Suggestions）

1. Telemetry 改用 `gen_ai.*` semantic conventions,並上報 input/output/cache token 細分。
2. 提供「跨檔關聯 pass」選項:在 per-file 之後跑一輪僅看「介面變更 × 呼叫端」的關聯檢查，補跨檔 Recall。
3. 允許 token 欄位為空字串以支援無認證的本地端點（或文件明示 placeholder 慣例）。
4. 文件與程式碼同步的 CI 檢查（span 清單、exporter 支援表自動生成）。

## 效能基準（Benchmark）

> [!info] 資料來源
> 官方 benchmark（README + 官網）：50 個開源 repo、200 個真實 PR、10 種語言、80+ 資深工程師交叉標註 1,505 個 ground-truth 問題。以下為官方宣稱，社群反應見「社群觀點」一節。

| 指標 | Open Code Review | 通用 agent（Claude Code，同底模） |
|------|------------------|----------------------------------|
| Precision / F1 | 顯著較高（官方圖表） | 較低 |
| Recall | 較低（刻意取捨） | 較高 |
| Avg Token | **約 1/9** | 基準 |
| Avg Time | 較快 | 較慢 |

已公開的具體數字（來源:issue #684 與知乎官方文）:

| 數據點 | OCR | 裸跑 Claude Code |
|--------|-----|------------------|
| Go 語言 F1（Claude-4.6-Opus 同底模） | 27.21% | 10.22% |
| Go 語言 Precision | 33.3% | 6.2%（824 條評論） |
| 全 benchmark Precision 區間 | 25–38% | 7–16% |
| Token 消耗 | 352K–743K | 2M–5M |

定性解讀：省 token 的機制（見深入主題一）在架構上站得住腳,#684 的 Go 細分也顯示 harness 確實把誤報壓掉一個數量級。但三個保留:① benchmark 自建自測,HN 用戶獨立重跑 10 個 PR 得到 precision 僅 ~12%（官方歸因於已修復的 tool call 異常）,可復現性存疑;② 內部行號重定位模型未開源,官方數據與開源版效果可能有差;③ #409 證明「省 token」在大 MR 場景可能失效——單檔守門存在、全局預算護欄缺失。「1/9」應視為「典型場景的量級宣稱」而非普遍保證。

## 快速上手（Quick Start）

```bash
npm install -g @alibaba-group/open-code-review

# 方式一:default mode(需 API Key)
ocr config provider     # 互動式選 provider、填 Key、測連線
ocr config model
cd your-project
ocr review                                # workspace 模式
ocr review --from main --to feature-x     # branch range
ocr scan --path internal/agent            # 整檔掃描

# 方式二:委托模式(免 API Key,在 Claude Code 等宿主 agent 內)
ocr delegate preview
ocr delegate rule src/main.go src/handler.go

# 觀測(選配)
OCR_ENABLE_TELEMETRY=1 \
OTEL_SERVICE_NAME=open-code-review \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
ocr review
```

## 我的心得（My Takeaways）

1. **「確定性骨架 + LLM 填空」是省 token 的第一性原理**:通用 agent 最貴的不是回答、是「探索」。凡是能離線算好的（挑檔、配規則、算行號）就不要讓 LLM 做。這個原則可以直接搬到任何 agent 系統設計。
2. **「省 token」要先問「哪種 token」**:raw token 效率與 API 帳單是兩回事。委托模式 raw token 較多但帳單為零（吃訂閱）,default mode 相反。設計工具時要把這兩個維度講清楚,行銷話術常混為一談。
3. **Precision 與 Recall 是產品定位,不只是指標**:OCR 敢把「Recall 較低」寫進 README,因為它知道 review 工具的死穴是「狼來了」——誤報多了沒人看。證偽式 reflection 就是把這個定位做進架構。
4. **Telemetry 的 no-op 模式與 CLI flush 模式**直接可抄到自己的 Go CLI 專案。

## 待補充（Open Questions）

- 官方 benchmark 的 200 個 PR 與標註資料是否公開可復現？「1/9 token」在不同模型（如 Haiku 級 vs Opus 級）上是否穩定？（建議搜尋:`open-code-review benchmark reproduction`、官方 repo 是否釋出 eval dataset）
- 三區 context 壓縮的摘要品質如何影響後半段 review 的準確度？有沒有壓縮導致漏報的案例分析？（建議搜尋:`memory compression degradation LLM agent`）
- 委托模式下宿主 agent 是否真的遵守 coverage 承諾（每檔 reviewed 或 skipped）？Skill 的自然語言約束沒有工程強制,實務遵從率未知。（建議搜尋:GitHub issues `delegate coverage`）
- 內部版與開源版的能力差已被部分證實（issue #6:內部有專門訓練、準確率 98–99% 的行號重定位模型,因合規未開源,開源版以 sliding-window + LLM 重錨替代）——但還有哪些內部元件未開源？官方 benchmark 數據是用哪一版跑出來的？（建議搜尋:`open-code-review internal model compliance`）
- `file_read` 限 500 行、`code_search` 限 100 筆的截斷,對超大檔案/monorepo 的 Recall 影響有多大？
- MCP 工具擴充後,精簡工具集的「省 token」優勢會不會被沖淡？有沒有工具數量 vs 效果的實測？

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | ① 確定性工程 × Agent 混合架構;② sliding-window 行號定位（`existing_code` → 行號）;③ 委托模式（Delegation Mode,免 API Key）;④ 三區 context 壓縮（60%/80% 閾值）;⑤ 證偽式反思過濾（REVIEW_FILTER_TASK） |
| **理解（半被動）** | 串聯知識點 | 核心邏輯鏈:「探索最燒 token」→「把探索工程化」→「LLM 只判斷單檔」→「per-file 隔離」→「省 token + 抗 cut corners」;而「證偽過濾 + 低 Recall 取捨」共同服務「高信噪比」這個產品定位 |
| **分析（主動）** | 找出假設與漏洞 | 關鍵假設:①「單檔 + 6 工具」足以發現大多數值得報的問題（跨檔缺陷被結構性犧牲）;② benchmark 自建自測,標註者與出題者同源;③ 委托模式假設宿主 agent 會遵守自然語言的 coverage 約束,無工程強制 |
| **應用（主動）** | 轉為行動 | ① 在自己的 agent 系統中,把「可離線計算的步驟」從 prompt 移到程式碼（挑檔、定位、規則匹配）;② 抄 telemetry 的 no-op span + CLI flush 模式到 Go CLI 專案;③ 在 CI 用 `TRACEPARENT` 把 review 串進既有分散式 trace |
| **評估（主動）** | 權衡取捨 | vs CodeRabbit/Copilot Review:OCR 開源、自帶端點、可觀測,但無 PR 平台深度整合的開箱體驗;vs 直接用 Claude Code review:OCR 省 token、高 precision,但跨檔推理與 Recall 較弱。適合「高頻 CI 過濾 + 成本敏感」場景;不適合「一次性的深度架構審計」（該用 scan 或通用 agent） |

### 分析型追問（Socratic Follow-up）

- **澄清**:「約 1/9 token」中的 token 是指單次 review 的總消耗、還是分攤到每個發現的問題？分母定義不同,結論差很多。
- **假設**:「per-file 隔離不損失重要缺陷」這個前提,在微服務單 repo（改 proto 影響十個服務）的場景還成立嗎？
- **證據**:benchmark 的 1,505 個 ground-truth 是否涵蓋「跨檔案缺陷」這個類別？若不涵蓋,低 Recall 的真實代價被低估。
- **觀點**:站在 CodeRabbit 這類商業產品的立場,最有力的批評可能是:「CLI 工具缺少 PR 對話式互動與團隊知識累積,review 是協作流程不是批次任務」。
- **後果**:若團隊依賴 OCR 12 個月,可能的副作用:工程師習慣「零誤報」後對它放行的 code 過度信任,而它的 Recall 缺口(跨檔、架構級問題)正好是最貴的那類 bug。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 把「高 Precision」誤解為「高覆蓋」。OCR 刻意犧牲 Recall,漏掉的往往是跨檔/架構級缺陷——最壞情況是團隊裁撤人工 review 後,這類 bug 直達生產環境。
2. **什麼情況下會失敗？** — ① 跨檔強耦合的變更（介面 + 呼叫端分離）;② 超大單檔(diff 超過 MaxTokens×80% 直接被丟棄,連 review 都不做,只在 telemetry 留 event);③ 規則文件與專案慣例不符時,glob first-match-wins 會拿錯規則;④ 無 API Key 且宿主 agent 不支援 plugin 的環境。
3. **有沒有更好的替代方案？** — 若要 PR 平台深度整合與團隊協作,CodeRabbit / Copilot Review 更順;若要深度架構審計,通用 agent(Claude Code)+ 明確指示的 Recall 更高;若要零成本起步,委托模式本身就是 OCR 內建的替代路徑。OCR 的甜蜜點是「CI 高頻執行 + token 成本敏感 + 誤報零容忍」的組合。

## 相關連結（Related）

- [[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]] — Claude Code 的 OTel 三層架構 vs OCR 的單層 no-op 設計,兩種 CLI 遙測哲學對照
- [[2026-04-28-CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]] — Claude Code 記 4 種 token 細分,OCR 只記 total——token 會計精度的正反例
- [[2026-05-23-RTK-RUST-TOKEN-KILLER-LOG-COMPRESSION-ARCHITECTURE]] — 同屬「進 context 前先工程化壓縮」哲學,RTK 壓 log、OCR 壓 review 流程
- [[2026-05-20-CODEX-CLI-VS-CLAUDE-CODE-DEEP-COMPARISON]] — OCR 對標的「通用 agent」陣營全景,理解它為何選擇專用化路線
- [[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]] — 另一套工具鏈的遙測設計(本地寫入+背景同步),與 OCR 的 OTLP 直送對照
- [[2025-12-29-SKILLSBENCH-AGENT-SKILL-USE-BENCHMARK-CODE-ANALYSIS]] — 自建 benchmark 的方法論參照:OCR 的 1/9 宣稱同樣面臨「自建自測」的可信度問題
- [[2026-07-31-DOTNET-SKILLS-POLYGLOT-UNIT-TEST-AGENT-CODE-ANALYSIS]] — Microsoft 的鏡像案例:同樣「專用 harness 打素的通用 agent」,但買的是可靠性(失敗 -63%、token +3.2%)而非 token 效率——兩條正交的專用化路線

## References

- [GitHub Repo](https://github.com/alibaba/open-code-review)
- [官方文件](https://open-codereview.ai/docs)
- [Delegation Mode 文件](https://open-codereview.ai/docs/delegate)
- [Telemetry 文件](https://open-codereview.ai/docs/telemetry)
- [npm 套件](https://www.npmjs.com/package/@alibaba-group/open-code-review)
