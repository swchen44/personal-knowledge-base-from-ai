---
title: "Claude Code 使用者反饋系統深度分析 — Frustration Detection 演算法、EventMetadata 傳送架構與三管道反饋機制"
date: 2026-04-17
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#tools/claude-code"
  - "#ai/agent"
  - "#tools/analytics"
  - "#security/privacy"
source: "conversation research: Claude Code feedback & telemetry source code analysis"
source_type: code
author: "Anthropic (decompiled source)"
status: notes
links:
  - "[[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
  - "[[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]]"
  - "[[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]]"
  - "[[2026-04-04-GSTACK-SECURITY-TELEMETRY-CONTROVERSY]]"
  - "[[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]"
github_stars: N/A
github_language: TypeScript
---

## 摘要（Summary）

從 Claude Code 反編譯原始碼中，完整追蹤**使用者體驗反饋系統**的設計——Anthropic 如何收集好的與壞的使用者體驗，並將其回傳用於產品改善。本文深入分析三大反饋管道（顯式 /feedback、概率性調查問卷、挫折偵測）、EventMetadata 從產生到傳送至 Datadog 與 Anthropic 1P 的完整資料流架構、負面情緒關鍵字比對演算法、GrowthBook A/B 測試基礎設施，以及多層隱私保護機制（型別系統級防護、敏感資訊脫敏、MCP 工具名稱匿名化、使用者 ID Bucket 化）。涵蓋約 15 個核心檔案、3,000+ 行程式碼的分析。

## Why — 為什麼存在？

> Claude Code 的反饋系統要解決什麼根本問題？

- **核心動機**：CLI 工具不像網頁有滑鼠追蹤或熱圖（Heatmap），Anthropic 需要一套機制來理解使用者在終端機中的真實體驗——是順暢還是挫折？什麼操作最常失敗？
- **取代/改善什麼**：取代「僅靠 GitHub Issue 被動等待回報」的模式。主動收集結構化反饋（structured feedback），搭配 A/B 測試驗證改進效果
- **目標用戶**：
  - **產品團隊**：透過 BigQuery 分析使用者滿意度趨勢
  - **On-call 工程師**：透過 Datadog 即時監控 API 錯誤率和工具失敗率
  - **ML 團隊**：收集帶標籤的 transcript（好/壞/挫折）用於模型改善

## What — 是什麼？

> 反饋系統的功能邊界與核心能力

- **主要功能**：
  - 三管道反饋收集：顯式（/feedback）、概率性調查問卷（Feedback Survey）、挫折偵測（Frustration Detection）
  - 結構化事件追蹤：64 種白名單事件經 Datadog + 1P 雙路徑傳送
  - 完整 transcript 分享（使用者同意後）
  - 動態配置：所有觸發條件透過 GrowthBook 遠端可調
  - 多層隱私保護：型別系統防護 + 脫敏 + 匿名化
- **不做什麼（Non-goals）**：不收集程式碼內容、不追蹤個人使用者身分（Bucket 化）、不在未經同意下上傳對話記錄
- **技術棧（Tech Stack）**：TypeScript、React/Ink、OpenTelemetry SDK、Axios、GrowthBook SDK

## How — 如何運作？

### 系統架構圖（System Architecture）— 三管道反饋收集

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          REPL 主迴圈 (src/screens/REPL.tsx)              │
│                                                                         │
│  ┌──────────────────┐  ┌─────────────────────┐  ┌────────────────────┐  │
│  │  /feedback 指令   │  │  Feedback Survey     │  │ Frustration        │  │
│  │  (使用者主動)     │  │  (概率性觸發)        │  │ Detection          │  │
│  │                  │  │  0.5% 機率           │  │ (ant-only 內部)    │  │
│  │  Feedback.tsx    │  │  useFeedbackSurvey   │  │ useFrustration     │  │
│  │  :157            │  │  .tsx:43             │  │ Detection.ts       │  │
│  └────────┬─────────┘  └──────────┬──────────┘  └──────────┬─────────┘  │
│           │                       │                        │            │
│           ▼                       ▼                        ▼            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              submitTranscriptShare.ts / submitFeedback()         │   │
│  │              (統一的提交邏輯)                                     │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
                    ┌─────────────┼──────────────┐
                    ▼             ▼              ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
           │ /api/claude_  │ │ /api/claude_ │ │ logEvent()       │
           │ cli_feedback  │ │ code_shared_ │ │ (結構化事件)      │
           │              │ │ session_     │ │                  │
           │ (bug report) │ │ transcripts  │ │ → Datadog + 1P   │
           └──────────────┘ └──────────────┘ └──────────────────┘
```

### EventMetadata 傳送架構圖（資料流全景）

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                     應用層：事件產生                                │
 │                                                                  │
 │  tengu_api_success    tengu_tool_use_*    tengu_feedback_survey  │
 │  tengu_api_error      tengu_cancel        tengu_bug_report_*    │
 │  tengu_init           tengu_exit          tengu_compact_failed   │
 └──────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │              logEvent(eventName, metadata)                       │
 │              src/services/analytics/index.ts:133                 │
 │                                                                  │
 │  metadata 只接受 { [key: string]: boolean | number | undefined } │
 │  字串必須標記為 AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE    │
 │                                                                  │
 │  ┌─ sink 未初始化? ──→ eventQueue[] (記憶體佇列，啟動後排出) ─┐    │
 │  └─ sink 已初始化? ──→ 直接分發 ──────────────────────────────┘   │
 └──────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │                    sink.ts — 路由層                               │
 │                    src/services/analytics/sink.ts:48             │
 │                                                                  │
 │  ① shouldSampleEvent(eventName)                                 │
 │     └── GrowthBook config: tengu_event_sampling_config          │
 │     └── 回傳 sample_rate 或 0(丟棄) 或 null(100%記錄)           │
 │                                                                  │
 │  ② 分發到兩個 sink：                                              │
 └──────┬──────────────────────────────────┬───────────────────────┘
        │                                  │
        ▼                                  ▼
 ┌──────────────────┐           ┌──────────────────────────────────┐
 │  Datadog 路徑     │           │  1P (First-Party) 路徑           │
 │                  │           │                                  │
 │ stripProtoFields │           │  保留 _PROTO_* 欄位              │
 │ (移除 PII 欄位)   │           │  (PII 送到特權 BQ column)        │
 └────────┬─────────┘           └──────────────┬───────────────────┘
          │                                    │
          ▼                                    ▼
 ┌──────────────────────────┐   ┌──────────────────────────────────┐
 │ trackDatadogEvent()      │   │ logEventTo1P()                   │
 │ datadog.ts:160           │   │ firstPartyEventLogger.ts:216     │
 │                          │   │                                  │
 │ Guard checks:            │   │ Guard checks:                    │
 │ • NODE_ENV=production    │   │ • isAnalyticsDisabled()?         │
 │ • provider=firstParty    │   │ • isSinkKilled('firstParty')?    │
 │ • DATADOG_ALLOWED_EVENTS │   │                                  │
 │   (64 個白名單事件)       │   │ ① getEventMetadata() 豐富化     │
 │                          │   │    • model, sessionId            │
 │ 資料處理:                 │   │    • envContext (平台/版本/CI)    │
 │ • getEventMetadata()     │   │    • processMetrics (CPU/RAM)    │
 │ • MCP 名稱→ "mcp"       │   │    • subscriptionType            │
 │ • model 正規化           │   │    • agentIdentification         │
 │ • version 截短           │   │    • repo remote hash            │
 │ • userBucket (hash→30桶) │   │                                  │
 │ • ddtags 格式化          │   │ ② getCoreUserData()              │
 │                          │   │    • accountUuid                 │
 │ 批次處理:                 │   │    • organizationUuid            │
 │ • logBatch[] (100 上限)   │   │    • githubActionsMetadata       │
 │ • 15 秒 flush 或滿時送出  │   │                                  │
 └────────┬─────────────────┘   │ ③ OTel LogRecord emit            │
          │                     └──────────────┬───────────────────┘
          ▼                                    │
 ┌──────────────────────────┐                  ▼
 │  HTTP POST               │   ┌──────────────────────────────────┐
 │                          │   │ BatchLogRecordProcessor          │
 │  https://http-intake     │   │ (OpenTelemetry SDK)              │
 │  .logs.us5.datadoghq     │   │                                  │
 │  .com/api/v2/logs        │   │ • 10 秒間隔 或 200 筆觸發        │
 │                          │   │ • maxQueueSize: 8192             │
 │  Headers:                │   │                                  │
 │  • DD-API-KEY: pub...bf  │   │ 觸發 export():                   │
 │  • Content-Type: json    │   └──────────────┬───────────────────┘
 │                          │                  │
 │  Timeout: 5s             │                  ▼
 │  失敗: 靜默丟棄           │   ┌──────────────────────────────────┐
 └──────────────────────────┘   │ FirstPartyEventLoggingExporter   │
                                │ firstPartyEventLoggingExporter   │
                                │ .ts:72                           │
                                │                                  │
                                │ transformLogsToEvents():          │
                                │ ┌─ GrowthbookExperimentEvent     │
                                │ │  • experiment_id               │
                                │ │  • variation_id                │
                                │ │  • device_id, account_uuid     │
                                │ └────────────────────────────────│
                                │ ┌─ ClaudeCodeInternalEvent       │
                                │ │  • event_id, event_name        │
                                │ │  • client_timestamp            │
                                │ │  • device_id, email            │
                                │ │  • auth: {account_uuid,        │
                                │ │          organization_uuid}    │
                                │ │  • env: EnvironmentMetadata    │
                                │ │  • process: base64(metrics)    │
                                │ │  • additional_metadata:        │
                                │ │    base64(JSON blob)           │
                                │ │  • skill_name (from _PROTO_)   │
                                │ └────────────────────────────────│
                                │                                  │
                                │ sendBatchWithRetry():            │
                                └──────────────┬───────────────────┘
                                               │
                           ┌───────────────────┼───────────────────┐
                           │                   │                   │
                           ▼                   ▼                   ▼
                    ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
                    │  成功        │   │  401 錯誤     │   │  其他失敗     │
                    │             │   │              │   │              │
                    │ 清除磁碟佇列│   │ 移除 Auth    │   │ 寫入磁碟     │
                    │ 立即重試    │   │ headers      │   │              │
                    │ 之前失敗的  │   │ 重試一次     │   │ ~/.claude/   │
                    │ 事件        │   │              │   │ telemetry/   │
                    └─────────────┘   └──────────────┘   │ 1p_failed_  │
                                                         │ events.*.json│
                                                         │              │
                                                         │ 二次方退避:   │
                                                         │ 500ms × n²  │
                                                         │ cap: 30s    │
                                                         │ max: 8 次   │
                                                         └──────────────┘

                    ┌──────────────────────────────────────────────────┐
                    │              HTTP POST                            │
                    │                                                   │
                    │  https://api.anthropic.com/api/event_logging/batch│
                    │                                                   │
                    │  Headers:                                         │
                    │  • Content-Type: application/json                 │
                    │  • User-Agent: claude-code/VERSION                │
                    │  • x-service-name: claude-code                    │
                    │  • Authorization: Bearer <OAuth token>            │
                    │                                                   │
                    │  Payload:                                         │
                    │  { events: [                                      │
                    │    { event_type: "ClaudeCodeInternalEvent",       │
                    │      event_data: <proto toJSON()> },              │
                    │    ...                                            │
                    │  ]}                                               │
                    │                                                   │
                    │  Timeout: 10s                                     │
                    └──────────────────────────────────────────────────┘
```

### Frustration Detection 演算法流程圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    REPL 主迴圈 (每次 render)                              │
│                                                                         │
│  useFrustrationDetection(messages, isLoading,                           │
│                           hasActivePrompt, otherSurveyOpen)             │
│  src/screens/REPL.tsx:1724-1725                                         │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │   Guard Checks (前置檢查)   │
              │                            │
              │ • isLoading? → skip        │
              │ • hasActivePrompt? → skip  │
              │ • otherSurveyOpen? → skip  │
              │ • GrowthBook gate? → skip  │
              │ • ("external") === 'ant'?  │
              │   → 外部版本完全不載入      │
              └───────────┬────────────────┘
                          │ pass
                          ▼
         ┌─────────────────────────────────────┐
         │   useMemo #1: 關鍵字偵測 O(n)        │
         │   (掃描每一條 user message)           │
         │                                      │
         │   matchesNegativeKeyword()            │
         │   src/utils/userPromptKeywords.ts:4   │
         │                                      │
         │   正規表達式比對三大類:                │
         │                                      │
         │   ┌─ 髒話類 ────────────────────┐    │
         │   │ wtf, wth, ffs, omfg,        │    │
         │   │ shit(ty|tiest), dumbass,     │    │
         │   │ fuck you, screw this/you     │    │
         │   └─────────────────────────────┘    │
         │   ┌─ 情緒類 ────────────────────┐    │
         │   │ horrible, awful,             │    │
         │   │ pissed/pissing off,          │    │
         │   │ so frustrating,              │    │
         │   │ this sucks, damn it          │    │
         │   └─────────────────────────────┘    │
         │   ┌─ 組合類 ────────────────────┐    │
         │   │ piece of shit/crap/junk,     │    │
         │   │ what the fuck/hell,          │    │
         │   │ fucking broken/useless/      │    │
         │   │ terrible/awful/horrible      │    │
         │   └─────────────────────────────┘    │
         └────────────────┬────────────────────┘
                          │ 偵測到負面情緒
                          ▼
         ┌─────────────────────────────────────┐
         │   useMemo #2: 上下文分析 O(n)        │
         │   (推斷，原始碼被 stub)              │
         │                                      │
         │   可能的額外檢查：                    │
         │   • 連續負面訊息的數量                │
         │   • 近期 tool_use_rejected 事件      │
         │   • 使用者是否多次重試同樣操作        │
         │   • 訊息頻率（快速連續=焦躁）         │
         │   • sideQuery() → Claude classifier  │
         │     分析語境（非單純關鍵字比對）       │
         └────────────────┬────────────────────┘
                          │ 確認挫折
                          ▼
              ┌────────────────────────────┐
              │  state: 'open'             │
              │                            │
              │  顯示 Transcript 分享提示   │
              │  （跳過評分步驟）           │
              └───────────┬────────────────┘
                          │ 使用者選擇
                          ▼
         ┌──────────────────────────────────────┐
         │  handleTranscriptSelect()             │
         │                                       │
         │  'yes' → submitTranscriptShare()      │
         │          trigger: 'frustration'       │
         │          → POST api.anthropic.com     │
         │            /api/claude_code_shared_    │
         │            session_transcripts         │
         │                                       │
         │  'no'  → close survey                 │
         │  'dont_ask_again' → persist to        │
         │          ~/.claude.json               │
         └──────────────────────────────────────┘
```

### Feedback Survey 概率觸發時序圖

```
 使用者        REPL.tsx         useFeedbackSurvey    GrowthBook       Anthropic API
   │             │                    │                  │                 │
   │──輸入訊息──►│                    │                  │                 │
   │             │──render──────────►│                   │                 │
   │             │                   │                   │                 │
   │             │                   │  shouldOpen?      │                 │
   │             │                   │  ├─ isLoading?    │                 │
   │             │                   │  ├─ 已過 10 分鐘? │                 │
   │             │                   │  ├─ ≥5 次輸入?    │                 │
   │             │                   │  ├─ 跨 session    │                 │
   │             │                   │  │  間隔 >27hr?   │                 │
   │             │                   │  └─ Math.random() │                 │
   │             │                   │     ≤ 0.5%?       │                 │
   │             │                   │     (只 roll 一次) │                 │
   │             │                   │                   │                 │
   │             │                   │  [通過所有條件]    │                 │
   │             │                   │                   │                 │
   │◄──────────「您的使用體驗如何？」─│                   │                 │
   │                                 │                   │                 │
   │──選擇 'bad'────────────────────►│                   │                 │
   │                                 │──logEvent────────►│                 │
   │                                 │  (survey_event)   │                 │
   │                                 │                   │                 │
   │                                 │──shouldShow       │                 │
   │                                 │  TranscriptPrompt?│                 │
   │                                 │  probability gate─►│                │
   │                                 │◄─ config.prob ────│                 │
   │                                 │                   │                 │
   │◄────「是否願意分享對話記錄？」──│                    │                 │
   │                                 │                   │                 │
   │──選擇 'yes'────────────────────►│                   │                 │
   │                                 │──submitTranscript────────────────►│
   │                                 │  Share()          │                 │
   │                                 │  trigger:         │                 │
   │                                 │  'bad_feedback_   │                 │
   │                                 │   survey'         │                 │
   │                                 │                   │  POST /api/    │
   │                                 │                   │  claude_code_  │
   │                                 │                   │  shared_       │
   │                                 │                   │  session_      │
   │                                 │                   │  transcripts   │
   │                                 │◄─────────────────────transcript_id│
   │◄──────────「感謝回饋！」────────│                    │                │
   │             │                   │                   │                 │
```

### 生命週期時序圖：啟動到關閉

```
  ┌─ 啟動 (src/entrypoints/init.ts) ───────────────────────────────────┐
  │                                                                     │
  │  init()                                                             │
  │    ├── 同步: 配置載入, graceful shutdown handler 註冊                │
  │    └── 異步: initialize1PEventLogging()                             │
  │             └── GrowthBook refresh → reinitialize1PEventLogging     │
  │                 IfConfigChanged() (長 session 配置熱更新)            │
  │                                                                     │
  │  initSinks() → attachAnalyticsSink()                                │
  │    └── 排出 eventQueue[] 中的早期事件 (queueMicrotask)              │
  │                                                                     │
  │  initializeTelemetryAfterTrust()                                    │
  │    └── Trust dialog 接受後才啟動 OTLP                               │
  └─────────────────────────────────────────────────────────────────────┘
                               │
                    正常運作（事件持續產生）
                               │
  ┌─ 關閉 (src/utils/gracefulShutdown.ts:391-523) ─────────────────────┐
  │                                                                     │
  │  gracefulShutdown()                                                 │
  │    ├── 退出 alt screen, 列印 resume hint                            │
  │    ├── 執行 cleanup functions                                       │
  │    ├── 執行 SessionEnd hooks                                        │
  │    ├── ★ Flush analytics (500ms 上限):                              │
  │    │   Promise.race([                                               │
  │    │     Promise.all([                                              │
  │    │       shutdown1PEventLogging(),  // provider.shutdown()         │
  │    │       shutdownDatadog()          // flush logBatch[]            │
  │    │     ]),                                                        │
  │    │     sleep(500)  // 超時則放棄                                   │
  │    │   ])                                                           │
  │    └── process.exit()                                               │
  └─────────────────────────────────────────────────────────────────────┘
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）— Sink 解耦模式
> `logEvent()` 在 analytics sink 初始化前就可以呼叫（事件排入 queue），等 sink attach 後透過 `queueMicrotask` 異步排出。這確保啟動階段的事件不遺失，同時不阻塞啟動流程。

1. **概率只 roll 一次**（`useFeedbackSurvey.tsx:265-268`）— 防止每次 useMemo 重新計算時重新擲骰，避免多次 render 後調查問卷幾乎 100% 出現
2. **Datadog 與 1P 分離**— Datadog 做低延遲即時監控（15 秒 flush），1P 做高精度 BigQuery 分析（10 秒 batch + 磁碟備份重試）
3. **二次方退避而非指數退避**（`500ms × n²`，cap 30s）— 比指數退避更溫和，適合「端點暫時不可用但會很快恢復」的場景
4. **型別系統級 PII 防護**（`AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS`）— `never` 類型強制開發者明確標記字串不含敏感資訊
5. **使用者 ID Bucket 化**（30 桶）— 用 SHA256 hash 後 mod 30，估算影響使用者數而非追蹤個人

### 資料流（Data Flow）— 事件從產生到落地

1. 應用層呼叫 `logEvent('tengu_api_success', { model, status })` — 只接受 `boolean | number | undefined`
2. `sink.ts` 路由層做取樣（`shouldSampleEvent`）+ PII 分流（strip `_PROTO_*` keys for Datadog）
3. **Datadog 路徑**：`trackDatadogEvent()` → 豐富化 metadata → batch 到 `logBatch[]` → 15 秒或 100 筆時 flush → POST `https://http-intake.logs.us5.datadoghq.com/api/v2/logs`
4. **1P 路徑**：`logEventTo1P()` → `getEventMetadata()` 豐富化 → OTel `LogRecord.emit()` → `BatchLogRecordProcessor` 10 秒或 200 筆觸發 → `FirstPartyEventLoggingExporter.export()` → `transformLogsToEvents()` 轉為 Proto → POST `https://api.anthropic.com/api/event_logging/batch`
5. 1P 失敗時：寫入 `~/.claude/telemetry/1p_failed_events.{sessionId}.{batchUUID}.json` → 二次方退避重試（最多 8 次）

### 關鍵程式碼（Key Code Snippets）

#### 負面情緒關鍵字比對（`src/utils/userPromptKeywords.ts`）

```typescript
/**
 * Checks if input matches negative keyword patterns
 */
export function matchesNegativeKeyword(input: string): boolean {
  const lowerInput = input.toLowerCase()

  const negativePattern =
    /\b(wtf|wth|ffs|omfg|shit(ty|tiest)?|dumbass|horrible|awful|piss(ed|ing)? off|piece of (shit|crap|junk)|what the (fuck|hell)|fucking? (broken|useless|terrible|awful|horrible)|fuck you|screw (this|you)|so frustrating|this sucks|damn it)\b/

  return negativePattern.test(lowerInput)
}
```

#### Feedback Survey 概率控制（`src/components/FeedbackSurvey/useFeedbackSurvey.tsx:30-39`）

```typescript
const DEFAULT_FEEDBACK_SURVEY_CONFIG: FeedbackSurveyConfig = {
  minTimeBeforeFeedbackMs: 600000,          // 10 分鐘
  minTimeBetweenFeedbackMs: 3600000,        // 1 小時
  minTimeBetweenGlobalFeedbackMs: 100000000, // ~27 小時（跨 session）
  minUserTurnsBeforeFeedback: 5,
  minUserTurnsBetweenFeedback: 10,
  hideThanksAfterMs: 3000,
  onForModels: ['*'],
  probability: 0.005                         // 0.5%
};
```

#### 概率只 roll 一次的防護（`useFeedbackSurvey.tsx:263-271`）

```typescript
// Probability check: roll once per eligibility window to avoid re-rolling
// on every useMemo re-evaluation (which would make triggering near-certain).
if (lastEligibleSubmitCountRef.current !== submitCount) {
  lastEligibleSubmitCountRef.current = submitCount;
  probabilityPassedRef.current = Math.random() <= (settingsRate ?? config.probability);
}
if (!probabilityPassedRef.current) {
  return false;
}
```

#### Transcript 提交邏輯（`src/components/FeedbackSurvey/submitTranscriptShare.ts:29-112`）

```typescript
export type TranscriptShareTrigger =
  | 'bad_feedback_survey'
  | 'good_feedback_survey'
  | 'frustration'
  | 'memory_survey'

export async function submitTranscriptShare(
  messages: Message[],
  trigger: TranscriptShareTrigger,
  appearanceId: string,
): Promise<TranscriptShareResult> {
  const transcript = normalizeMessagesForAPI(messages)
  const agentIds = extractAgentIdsFromMessages(messages)
  const subagentTranscripts = await loadSubagentTranscripts(agentIds)

  let rawTranscriptJsonl: string | undefined
  try {
    const transcriptPath = getTranscriptPath()
    const { size } = await stat(transcriptPath)
    if (size <= MAX_TRANSCRIPT_READ_BYTES) {
      rawTranscriptJsonl = await readFile(transcriptPath, 'utf-8')
    }
  } catch { /* File may not exist */ }

  const data = {
    trigger, version: MACRO.VERSION, platform: process.platform,
    transcript, subagentTranscripts:
      Object.keys(subagentTranscripts).length > 0 ? subagentTranscripts : undefined,
    rawTranscriptJsonl,
  }

  const content = redactSensitiveInfo(jsonStringify(data))
  const response = await axios.post(
    'https://api.anthropic.com/api/claude_code_shared_session_transcripts',
    { content, appearance_id: appearanceId },
    { headers, timeout: 30000 },
  )
  return { success: true, transcriptId: response.data?.transcript_id }
}
```

#### 敏感資訊脫敏（`src/components/Feedback.tsx:74-116`）

```typescript
export function redactSensitiveInfo(text: string): string {
  let redacted = text;

  // Anthropic API keys (sk-ant...)
  redacted = redacted.replace(/"(sk-ant[^\s"']{24,})"/g, '"[REDACTED_API_KEY]"');
  redacted = redacted.replace(
    /(?<![A-Za-z0-9"'])(sk-ant-?[A-Za-z0-9_-]{10,})(?![A-Za-z0-9"'])/g,
    '[REDACTED_API_KEY]');

  // AWS keys - AKIAXXX keys
  redacted = redacted.replace(/(AKIA[A-Z0-9]{16})/g, '[REDACTED_AWS_KEY]');

  // Google Cloud keys
  redacted = redacted.replace(
    /(?<![A-Za-z0-9])(AIza[A-Za-z0-9_-]{35})(?![A-Za-z0-9])/g,
    '[REDACTED_GCP_KEY]');

  // Generic API keys in headers
  redacted = redacted.replace(
    /(["']?x-api-key["']?\s*[:=]\s*["']?)[^"',\s)}\]]+/gi,
    '$1[REDACTED_API_KEY]');

  // Authorization headers and Bearer tokens
  redacted = redacted.replace(
    /(["']?authorization["']?\s*[:=]\s*["']?(bearer\s+)?)[^"',\s)}\]]+/gi,
    '$1[REDACTED_TOKEN]');

  // Environment variables with keys
  redacted = redacted.replace(
    /((API[-_]?KEY|TOKEN|SECRET|PASSWORD)\s*[=:]\s*)["']?[^"',\s)}\]]+["']?/gi,
    '$1[REDACTED]');
  return redacted;
}
```

#### logEvent 型別防護（`src/services/analytics/index.ts:19`）

```typescript
// 型別是 never，代表不可能有值——強制開發者每次傳字串都要顯式轉型
// 這是一種「文化型安全措施」：每次寫 as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS
// 都是在提醒自己「我確認這不是程式碼或檔案路徑」
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = never
```

#### EventMetadata 結構（`src/services/analytics/metadata.ts:472-496`）

```typescript
export type EventMetadata = {
  model: string
  sessionId: string
  userType: string
  betas?: string
  envContext: EnvContext
  entrypoint?: string
  isInteractive: string
  clientType: string
  processMetrics?: ProcessMetrics
  sweBenchRunId: string
  sweBenchInstanceId: string
  sweBenchTaskId: string
  agentId?: string
  parentSessionId?: string
  agentType?: 'teammate' | 'subagent' | 'standalone'
  teamName?: string
  subscriptionType?: string
  rh?: string  // Hashed repo remote URL (first 16 chars of SHA256)
  kairosActive?: true
  skillMode?: 'discovery' | 'coach' | 'discovery_and_coach'
  observerMode?: 'backseat' | 'skillcoach' | 'both'
}
```

#### Datadog 白名單事件（`src/services/analytics/datadog.ts:19-64`）

```typescript
const DATADOG_ALLOWED_EVENTS = new Set([
  'chrome_bridge_connection_succeeded',
  'chrome_bridge_connection_failed',
  'chrome_bridge_disconnected',
  'chrome_bridge_tool_call_completed',
  'chrome_bridge_tool_call_error',
  'chrome_bridge_tool_call_started',
  'chrome_bridge_tool_call_timeout',
  'tengu_api_error',
  'tengu_api_success',
  'tengu_brief_mode_enabled',
  'tengu_cancel',
  'tengu_compact_failed',
  'tengu_exit',
  'tengu_init',
  'tengu_model_fallback_triggered',
  'tengu_oauth_error',
  'tengu_oauth_success',
  'tengu_query_error',
  'tengu_started',
  'tengu_tool_use_error',
  'tengu_tool_use_granted_in_prompt_permanent',
  'tengu_tool_use_granted_in_prompt_temporary',
  'tengu_tool_use_rejected_in_prompt',
  'tengu_tool_use_success',
  'tengu_uncaught_exception',
  'tengu_unhandled_rejection',
  'tengu_voice_recording_started',
  'tengu_voice_toggled',
  'tengu_team_mem_sync_pull',
  'tengu_team_mem_sync_push',
  // ... 共 64 個
]);
```

#### 滿意度分類 prompt（`src/commands/insights.ts:430-456`）

```typescript
const FACET_EXTRACTION_PROMPT = `Analyze this Claude Code session and extract structured facets.

CRITICAL GUIDELINES:

2. **user_satisfaction_counts**: Base ONLY on explicit user signals.
   - "Yay!", "great!", "perfect!" → happy
   - "thanks", "looks good", "that works" → satisfied
   - "ok, now let's..." (continuing without complaint) → likely_satisfied
   - "that's not right", "try again" → dissatisfied
   - "this is broken", "I give up" → frustrated
`
```

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 使用者主動回報 bug | `/feedback` 指令 | `src/commands/feedback/feedback.tsx` | `Feedback.tsx → submitFeedback() → POST /api/claude_cli_feedback` |
| 2 | 概率性滿意度調查 | 自動觸發（0.5%） | `src/components/FeedbackSurvey/useFeedbackSurvey.tsx` | `useSurveyState → submitTranscriptShare → POST /api/.../transcripts` |
| 3 | 挫折偵測 | 負面情緒關鍵字 | `src/components/FeedbackSurvey/useFrustrationDetection.ts` | `matchesNegativeKeyword → submitTranscriptShare (trigger: 'frustration')` |
| 4 | 隱式行為追蹤 | 每次工具呼叫/API 請求 | `src/services/analytics/index.ts` | `sink.ts → Datadog + 1P Event Logger → POST endpoints` |
| 5 | 事後 session 分析 | `/insights` 指令 | `src/commands/insights.ts` | `FACET_EXTRACTION_PROMPT → Claude API → structured facets` |

### 案例詳解

#### 案例 1：使用者主動回報 bug（/feedback）

```
使用者：/feedback
  │
  ▼
src/commands/feedback/feedback.tsx
  │
  ▼
src/components/Feedback.tsx:157 — Feedback component
  │ ① 使用者填寫描述
  │ ② 顯示將提交的資料清單
  │ ③ 使用者確認
  ▼
submitFeedback() (Feedback.tsx:522)
  │ 收集：transcript + errors + lastApiRequest + subagentTranscripts
  │ 脫敏：redactSensitiveInfo()
  ▼
POST https://api.anthropic.com/api/claude_cli_feedback
  │ 回傳 feedback_id
  ▼
generateTitle() → queryHaiku() → 自動產生 GitHub Issue 標題
  │
  ▼
使用者按 Enter → 開啟瀏覽器 → GitHub Issue 預填頁面
```

#### 案例 2：概率性滿意度調查

```
REPL render 循環
  │
  ▼
useFeedbackSurvey() (useFeedbackSurvey.tsx:43)
  │ 每次 render 計算 shouldOpen
  │
  │  ┌─ 檢查 6 個條件 ──────────────────────────────────┐
  │  │ 1. state === 'closed'                             │
  │  │ 2. !isLoading                                     │
  │  │ 3. !hasActivePrompt                               │
  │  │ 4. isModelAllowed (GrowthBook: onForModels)       │
  │  │ 5. 時間/次數閾值通過                               │
  │  │ 6. Math.random() ≤ 0.5% (只 roll 一次)            │
  │  └───────────────────────────────────────────────────┘
  │  全部通過
  ▼
彈出調查問卷 → 使用者選擇 good/bad/neutral
  │
  ├─ good/bad → shouldShowTranscriptPrompt()
  │              └─ 概率閘門 (GrowthBook config)
  │              └─ 檢查 transcriptShareDismissed
  │              └─ 檢查 allow_product_feedback policy
  │
  ▼
submitTranscriptShare() → POST /api/claude_code_shared_session_transcripts
```

## 資料最終去向總覽

| 目的地 | 端點 | 用途 | 資料內容 |
|--------|------|------|----------|
| **Anthropic 1P** | `api.anthropic.com/api/event_logging/batch` | BigQuery 內部分析 | 完整 EventMetadata + Proto 結構化事件 |
| **Datadog** | `http-intake.logs.us5.datadoghq.com/api/v2/logs` | 即時監控 + 告警 | 64 種白名單事件 + ddtags |
| **Anthropic Feedback** | `api.anthropic.com/api/claude_cli_feedback` | Bug report | 完整 transcript + 環境資訊 |
| **Anthropic Transcript** | `api.anthropic.com/api/claude_code_shared_session_transcripts` | 使用者同意分享的對話 | 完整 transcript + 子代理記錄 |
| **磁碟備份** | `~/.claude/telemetry/1p_failed_events.*.json` | 失敗重試 | 1P 事件的 JSONL 備份 |

## 隱私保護機制詳解

### 多層防護架構

| 層級 | 機制 | 檔案位置 | 說明 |
|------|------|----------|------|
| **型別系統** | `AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` | `analytics/index.ts:19` | `never` 類型強制轉型，提醒開發者 |
| **資料脫敏** | `redactSensitiveInfo()` | `Feedback.tsx:74-116` | API keys、AWS keys、GCP keys、tokens |
| **工具名稱匿名** | `sanitizeToolNameForAnalytics()` | `metadata.ts:70-77` | 自訂 MCP server → `'mcp_tool'` |
| **使用者 ID 桶化** | `getUserBucket()` | `datadog.ts:295-299` | SHA256 hash → mod 30 |
| **組織策略** | `isPolicyAllowed('allow_product_feedback')` | `useFeedbackSurvey.tsx:237` | ZDR 企業可完全關閉 |
| **環境變數停用** | `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY` | `useFeedbackSurvey.tsx:229` | 使用者可手動停用 |
| **Sink Killswitch** | `isSinkKilled('datadog'/'firstParty')` | `sinkKillswitch.ts` | GrowthBook 遠端關閉 |
| **Essential Traffic** | `isEssentialTrafficOnly()` | `Feedback.tsx:527` | 最小流量模式 |

### _PROTO_* PII 路由機制

```
事件 payload 中的 _PROTO_* 欄位（如 _PROTO_skill_name）
  │
  ├─→ Datadog: stripProtoFields() 移除 → 永遠不會到 Datadog
  │
  └─→ 1P Exporter: 提升到 proto 頂層欄位 → 送到 BigQuery 特權 column
      └── 剩餘的 _PROTO_* 也被 defensive strip → 未知欄位不會洩漏
```

## GrowthBook 動態配置一覽

| 配置名稱 | 用途 | 預設值 |
|----------|------|--------|
| `tengu_feedback_survey_config` | 調查問卷觸發機率、時間間隔、模型白名單 | probability: 0.005 |
| `tengu_bad_survey_transcript_ask_config` | 差評後詢問 transcript 的機率 | probability: 0 |
| `tengu_good_survey_transcript_ask_config` | 好評後詢問 transcript 的機率 | probability: 0 |
| `tengu_event_sampling_config` | 各事件的取樣率 | {} (100% 記錄) |
| `tengu_log_datadog_events` | Datadog 開關 | feature gate |
| `tengu_1p_event_batch_config` | 批次處理配置（間隔、大小、端點） | 10s / 200 / 8192 |
| `tengu_frond_boric` | Sink killswitch（混淆命名） | {} |

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 隱私設計（Privacy by Design） | ⭐⭐⭐⭐⭐ | 型別系統級防護 + 多層脫敏 + PII 路由分流，業界領先 |
| 容錯能力（Fault Tolerance） | ⭐⭐⭐⭐⭐ | 磁碟備份 + 二次方退避 + killswitch，事件幾乎不會遺失 |
| 動態可調（Dynamic Configuration） | ⭐⭐⭐⭐⭐ | 所有參數透過 GrowthBook 遠端調控，不需發布新版本 |
| 使用者尊重（User Respect） | ⭐⭐⭐⭐ | 0.5% 觸發率 + 多重閾值 + transcript 分享 opt-in |
| 解耦程度（Decoupling） | ⭐⭐⭐⭐ | Sink 模式讓事件產生與傳送完全解耦，啟動前事件不遺失 |

> [!tip] 值得學習的設計
> **概率只 roll 一次**的技巧（`lastEligibleSubmitCountRef`）值得所有做概率性 UI 的開發者學習。若每次 re-render 都重新 `Math.random()`，N 次 render 後觸發機率趨近 `1 - (1 - p)^N`，幾乎 100% 出現。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷

- **Frustration Detection 侵入性**：分析使用者文字情緒可能讓人不舒服，且關鍵字比對容易誤判（非英語使用者完全不覆蓋）
- **透明度不足**：普通使用者不知道有 64 種隱式事件被追蹤，/feedback 只是冰山一角；雖然隱私政策可能有提及，但大多數使用者不會閱讀
- **repo remote hash 可洩漏**：雖然是 SHA256 但只取前 16 字元，理論上可與 server side 資料關聯推測使用者在開發什麼專案
- **Process metrics 必要性存疑**：每個事件都附帶 CPU/記憶體使用率，對「改善使用者體驗」的關聯不直觀，更像是效能監控混入了反饋系統
- **GrowthBook 單點依賴**：所有 A/B 測試和配置都依賴 GrowthBook；長時間不可用時只能用上次快取值
- **Transcript 分享風險**：即使有脫敏，完整對話記錄仍可能包含業務邏輯、內部架構等企業敏感資訊

### 🔮 改進建議（Improvement Suggestions）

1. **多語言挫折偵測**：目前 `matchesNegativeKeyword()` 只支援英文，應加入中文（「崩潰」「搞什麼」）、日文等常見語言
2. **透明度儀表板**：在 `/settings` 中顯示「過去 24 小時傳送了 N 個事件到 Anthropic」，讓使用者了解被追蹤的程度
3. **Transcript 局部分享**：允許使用者只分享最後 N 輪對話，而非整個 session，降低敏感資訊暴露風險
4. **本地 frustration 分析**：用輕量級本地模型做情緒分類，避免依賴 sideQuery 的額外 API 呼叫

## 效能基準（Benchmark）

| 面向 | 數值 | 說明 |
|------|------|------|
| Datadog flush 間隔 | 15 秒 | 或 100 筆滿時立即送出 |
| 1P batch 間隔 | 10 秒 | 或 200 筆觸發 export |
| 1P 佇列上限 | 8,192 筆 | 超出即丟棄 |
| 1P HTTP timeout | 10 秒 | |
| Datadog HTTP timeout | 5 秒 | |
| 退避延遲上限 | 30 秒 | 二次方退避 500ms × n² |
| 最大重試次數 | 8 次 | 之後放棄 |
| Shutdown flush 上限 | 500ms | Promise.race 強制退出 |
| 調查問卷最低觸發間隔 | 10 分鐘 | session 內首次 |
| 調查問卷跨 session 間隔 | ~27 小時 | minTimeBetweenGlobalFeedbackMs |
| 調查問卷觸發機率 | 0.5% | 每次符合條件時 |

## 核心檔案參考索引

| 元件 | 檔案路徑 | 關鍵行號 |
|------|----------|----------|
| Feedback 指令 | `src/commands/feedback/feedback.tsx` | All |
| Feedback 元件 | `src/components/Feedback.tsx` | 54-596 |
| Feedback Survey | `src/components/FeedbackSurvey/useFeedbackSurvey.tsx` | 43-295 |
| Transcript 提交 | `src/components/FeedbackSurvey/submitTranscriptShare.ts` | 29-112 |
| Frustration Detection (stub) | `src/components/FeedbackSurvey/useFrustrationDetection.ts` | All |
| 負面情緒關鍵字 | `src/utils/userPromptKeywords.ts` | 4-11 |
| Analytics 公共 API | `src/services/analytics/index.ts` | 133-164 |
| 路由/Sink | `src/services/analytics/sink.ts` | 48-114 |
| Datadog 事件 | `src/services/analytics/datadog.ts` | 12-308 |
| 1P Event Logger | `src/services/analytics/firstPartyEventLogger.ts` | 156-449 |
| 1P Exporter | `src/services/analytics/firstPartyEventLoggingExporter.ts` | 73-779 |
| Metadata 豐富化 | `src/services/analytics/metadata.ts` | 472-743 |
| Killswitch | `src/services/analytics/sinkKillswitch.ts` | All |
| REPL 整合 | `src/screens/REPL.tsx` | 104-110, 1724-1725, 4895 |
| Insights 分析 | `src/commands/insights.ts` | 384-456 |
| Graceful Shutdown | `src/utils/gracefulShutdown.ts` | 391-523 |

## 我的心得（My Takeaways）

1. **「概率只 roll 一次」是通用技巧**：任何在 React render 循環中做概率性決策的場景都應該用 ref 鎖定結果，否則多次 render 會讓機率失真
2. **型別系統可以當文化工具**：`AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` 這個超長的型別名不是技術限制，而是文化提醒——每次轉型都在問自己「這真的不含敏感資訊嗎？」
3. **二次方退避 vs 指數退避**：二次方退避（`n²`）增長比指數（`2^n`）慢很多，適合「暫時性故障」；指數退避適合「可能長時間不可用」的情境
4. **隱式追蹤的道德邊界**：64 種事件的隱式追蹤雖然都匿名化了，但對使用者來說缺乏透明度。做產品時應思考「使用者如果知道，會不會不舒服？」
5. **Sink 解耦模式值得在自己的專案中採用**：先 queue 再 drain 的模式解決了「初始化順序」這個常見的 analytics 工程問題

## 待補充（Open Questions）

- Frustration Detection 的完整原始碼被 stub 掉了，原始版本是否使用 `sideQuery()` 呼叫 Claude 做語境分類？還是純粹靠關鍵字？（建議搜尋：`useFrustrationDetection ant-only implementation`）
- `tengu_frond_boric` 這個 killswitch 的混淆命名有什麼考量？是為了防止 GrowthBook 配置被外部猜測而故意用無意義名稱嗎？（建議搜尋：`GrowthBook feature flag naming convention security`）
- Transcript 分享後，Anthropic 如何使用這些資料？是用於 RLHF/DPO 微調，還是純粹用於 bug 分析？隱私政策中是否有明確說明？（建議搜尋：`Anthropic Claude Code data usage policy transcript`）
- `observerMode: 'backseat' | 'skillcoach' | 'both'` 對應的 observer classifiers 具體做什麼？與 frustration detection 是否有關聯？（建議搜尋：`tengu_backseat observer classifier Claude Code`）
- 為什麼 Datadog 的 `DD-API-KEY` 使用公開的 client token（`pubbbf48...`）而不是 server-side key？這是否意味著外部使用者也可以直接查詢 Datadog logs？（建議搜尋：`Datadog client token vs API key security model`）
- `insights.ts` 的 FACET_EXTRACTION_PROMPT 是事後分析，但是否存在即時版本（real-time session classification）在 ant-only 版本中運行？（建議搜尋：`Claude Code real-time session classification`）

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 三大反饋管道（/feedback、Survey、Frustration Detection）；四個 HTTP 端點；`AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` 型別；0.5% 觸發機率；30 個使用者 bucket |
| **理解（半被動）** | 串聯知識點 | 反饋系統是一個「漏斗」：64 種隱式事件 → 概率性主動詢問 → 使用者同意分享 transcript。每一層都比上一層獲得更豐富但更少量的資料。Datadog 做即時告警（On-call），1P 做深度分析（產品決策） |
| **分析（主動）** | 找出假設 | 關鍵假設：(1) 使用者用英文表達挫折（非英語使用者被忽略）；(2) 0.5% 的觸發率足以獲得統計顯著的反饋樣本；(3) 使用者同意分享 transcript = 代表性樣本（可能存在 self-selection bias——願意分享的人與不願意的人有系統性差異） |
| **應用（主動）** | 轉為行動 | (1) 在自己的 CLI 工具中採用 Sink 解耦模式解決 analytics 初始化時序問題；(2) 使用「概率只 roll 一次」技巧實作 A/B 測試或功能提示；(3) 參考 `redactSensitiveInfo()` 的正則表達式建立自己專案的脫敏函數 |
| **評估（主動）** | 優劣比較 | 與 VS Code 的遙測系統比較：VS Code 使用 Application Insights（Azure）而非 Datadog，且有明確的 telemetry opt-out 設定頁面。Claude Code 的隱私保護更精細（型別系統級），但透明度不如 VS Code（沒有「傳送了哪些事件」的可視化介面） |

### 分析型追問（Socratic Follow-up）

- **澄清**：「挫折偵測」中的「挫折」定義為何？是單純的負面情緒（anger），還是「使用者嘗試多次但無法完成目標」的行為模式？兩者的偵測邏輯截然不同。
- **假設**：本系統假設 transcript 分享是 opt-in 就足夠保護隱私，但如果使用者在挫折狀態下（認知負荷高、判斷力降低）更容易點「yes」，這是否構成暗模式（Dark Pattern）？
- **證據**：0.5% 的觸發率是否經過 A/B 測試驗證為最佳值？文中未提及驗證過程，但 GrowthBook 動態配置暗示 Anthropic 確實在調整此參數。
- **觀點**：隱私倡導者可能認為「64 種隱式事件追蹤」即使匿名化也構成過度收集。Anthropic 能否在不犧牲產品洞察的前提下，將事件種類減半？
- **後果**：如果 Anthropic 開始用收集到的 frustrated 標籤 transcript 做 RLHF 微調，模型可能學會「在使用者生氣時更順從」——這是否會產生安全對齊（Alignment）問題？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — Transcript 分享包含完整對話記錄，即使脫敏也可能殘留業務邏輯。若 Anthropic 內部存取控制（Access Control）失敗，敏感企業資訊可能外洩。最壞情況：企業客戶的 IP（Intellectual Property）透過 transcript 外流。
2. **什麼情況下會失敗？** — (1) 非英語使用者的挫折完全偵測不到；(2) GrowthBook 長時間不可用導致配置凍結在舊版本；(3) 企業設定了 ZDR 但忘記設定 `allow_product_feedback: false`，transcript 仍可能被上傳。
3. **有沒有更好的替代方案？** — **本地優先（Local-first）分析**：在使用者本機跑輕量級分類模型做 session 分析，只上傳結構化的分析結果（如 `{satisfaction: 'frustrated', friction: 'wrong_approach'}`），而非完整 transcript。這大幅降低隱私風險，代價是 Anthropic 失去 debug 的細節。適用於：對隱私要求極高的企業客戶。

## 相關連結（Related）
- [[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]] — 同一遙測系統的 OTel 指標層分析，本文聚焦反饋/事件層
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — 原始碼洩漏事件全景，提及反蒸餾和安全機制
- [[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]] — 記憶系統，與 memory_survey transcript trigger 相關
- [[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]] — 團隊層級的 OTel 監控部署
- [[2026-04-04-GSTACK-SECURITY-TELEMETRY-CONTROVERSY]] — 遙測系統的安全與隱私爭議
- [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — 設定檔層級，影響 analytics 停用方式
- [[2026-04-28-CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]] — 計費管線中 cost_usd_micros 的來源分析，與 EventMetadata 中的費用數據互補

## References
- Claude Code 反編譯原始碼（本地副本）：`/Users/swchen.tw/git/claude-code/`
- 核心檔案群：`src/services/analytics/`（8 檔案）、`src/components/FeedbackSurvey/`（7 檔案）
- GrowthBook SDK：[@growthbook/growthbook ^1.6.5](https://github.com/growthbook/growthbook)
- OpenTelemetry SDK for JS：[@opentelemetry/sdk-logs](https://github.com/open-telemetry/opentelemetry-js)
