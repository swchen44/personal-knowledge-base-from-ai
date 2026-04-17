---
title: "Claude Code Telemetry 原始碼深度分析：OpenTelemetry 架構、指標設計與 100 人團隊部署策略"
date: 2026-04-13
date_uncertain: true
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#tools/opentelemetry"
  - "#tools/claude-code"
  - "#tools/monitoring"
  - "#ai/agent"
source: "conversation research: Claude Code telemetry source code analysis"
source_type: code
author: "Anthropic (decompiled source)"
status: notes
links:
  - "[[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]]"
  - "[[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]]"
  - "[[2026-04-04-GSTACK-SECURITY-TELEMETRY-CONTROVERSY]]"
  - "[[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]"
  - "[[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]]"
github_stars: N/A
github_language: TypeScript
---

## 摘要（Summary）

從 Claude Code 反編譯原始碼中，完整追蹤遙測（Telemetry）子系統的架構設計、資料流與可匯出指標。本文深入分析 18 個遙測相關檔案（共 5,000+ 行程式碼），揭示三層遙測架構（標準 OTLP、Beta Tracing、Perfetto）、8 個核心計數器指標、完整的 Span 生命週期管理，以及 BigQuery / 1P Event Logger 兩條內部資料管線。針對「100 人公司如何利用這些遙測資料追蹤 Skill 成功率、改善使用者體驗」的需求，本文提出具體的部署策略、自訂指標方案與儀表板設計建議。

## Why — 為什麼存在？

> Claude Code 的遙測子系統要解決什麼根本問題？

- **核心動機**：讓組織能夠量化 AI 程式碼助手的實際價值——誰在用、用多少、花多少錢、效果如何
- **取代/改善什麼**：取代「憑直覺判斷採用率」的盲區。如 [[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]] 中揭示，7 人團隊中 3 人在首月後已停用，但管理者毫不知情
- **目標用戶**：
  - **IT 管理者**：追蹤成本與採用率
  - **工程主管**：識別使用模式差異（如快取效率落差）
  - **平台團隊**：建立組織級可觀測性（Observability）基礎設施

## What — 是什麼？

> 遙測子系統的功能邊界與核心能力

- **主要功能**：
  - 8 個 OTel 計數器指標（Counter Metrics）：成本、令牌、會話、提交、PR、程式碼行數、工具決策、活躍時間
  - 5 種 Span 類型（interaction、llm_request、tool、tool.blocked_on_user、hook）
  - OTel 事件日誌（Event Logging）：工具結果、API 錯誤、Skill 載入、權限決策
  - 多種匯出器：OTLP（gRPC/HTTP）、Prometheus、Console、BigQuery、1P Event Logger
  - 隱私控制：基數限制（Cardinality Control）、內容脫敏（Redaction）、PII 路由
- **不做什麼（Non-goals）**：
  - 不提供開箱即用的儀表板（需自建 Grafana 等）
  - 不追蹤 Skill 執行成功/失敗（僅追蹤 Skill 載入事件）
  - 不做即時告警（需搭配外部告警系統）
- **技術棧（Tech Stack）**：TypeScript、OpenTelemetry SDK v2、Bun runtime、Protobuf、gRPC

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code CLI Session                    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ REPL     │  │ Query    │  │ Tools    │  │ Hooks      │  │
│  │ Screen   │  │ Engine   │  │ System   │  │ System     │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │             │               │         │
│       └──────────────┼─────────────┼───────────────┘         │
│                      ▼                                       │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              Telemetry Layer (5,000+ LoC)             │   │
│  │                                                       │   │
│  │  ┌─────────────┐ ┌──────────────┐ ┌───────────────┐  │   │
│  │  │ Session     │ │ Beta Session │ │ Perfetto      │  │   │
│  │  │ Tracing     │ │ Tracing      │ │ Tracing       │  │   │
│  │  │ (928 LoC)   │ │ (400+ LoC)   │ │ (600+ LoC)    │  │   │
│  │  └──────┬──────┘ └──────┬───────┘ └──────┬────────┘  │   │
│  │         │               │                │            │   │
│  │  ┌──────▼───────────────▼────────────────▼────────┐   │   │
│  │  │        Instrumentation (826 LoC)               │   │   │
│  │  │  MeterProvider │ TracerProvider │ LoggerProvider│   │   │
│  │  └──────┬─────────┴───────┬───────┴───────┬───────┘   │   │
│  │         │                 │               │            │   │
│  └─────────┼─────────────────┼───────────────┼────────────┘   │
│            │                 │               │                │
└────────────┼─────────────────┼───────────────┼────────────────┘
             │                 │               │
     ┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
     │  Metrics     │  │  Traces     │  │  Logs      │
     │  Exporters   │  │  Exporters  │  │  Exporters │
     ├──────────────┤  ├─────────────┤  ├────────────┤
     │ • OTLP       │  │ • OTLP      │  │ • OTLP     │
     │ • Prometheus  │  │ • Console   │  │ • Console  │
     │ • Console    │  │             │  │ • 1P Event │
     │ • BigQuery   │  │             │  │   Logger   │
     └──────┬───────┘  └──────┬──────┘  └─────┬──────┘
            │                 │               │
            ▼                 ▼               ▼
     ┌──────────────────────────────────────────────┐
     │          External Backends                   │
     │  Grafana │ Prometheus │ Datadog │ Honeycomb  │
     │  SigNoz  │ Jaeger     │ BigQuery│ Anthropic  │
     └──────────────────────────────────────────────┘
```

### 執行流程圖（Execution Flowchart）— 遙測初始化

```
 CLI 啟動（cli.tsx）
   │
   ▼
 bootstrapTelemetry()
   │
   ├─ USER_TYPE=ant? ──是──► 複製 ANT_OTEL_* → OTEL_* 環境變數
   │
   ▼
 設定預設 temporality = delta
   │
   ▼
 initializeTelemetry()
   │
   ├─ 建立 Resource（service.name, version, os, arch）
   │
   ├─ 解析 OTEL_METRICS_EXPORTER
   │   ├─ "otlp" ──► 建立 OTLP Metric Exporter
   │   ├─ "prometheus" ──► 建立 Prometheus Exporter
   │   ├─ "console" ──► 建立 Console Exporter
   │   └─ "none" ──► 跳過
   │
   ├─ 是否為 API 客戶？ ──是──► 加入 BigQuery Exporter
   │
   ├─ Enhanced Telemetry Beta？
   │   ├─ 是 ──► 建立 Trace Exporter（OTLP）
   │   └─ 否 ──► 跳過
   │
   ├─ 建立 Logger Provider + Event Logger
   │
   ├─ Perfetto 啟用？ ──是──► 初始化 Perfetto Tracing
   │
   └─ 註冊 shutdown handler（graceful flush）
       │
       ▼
     遙測就緒，開始接收資料
```

### 時序圖（Sequence Diagram）— 一次使用者互動的完整追蹤

```
 User          REPL         QueryEngine      API Client     Tool          OTel
  │              │               │               │            │             │
  │──prompt─────►│               │               │            │             │
  │              │──startInteractionSpan──────────────────────────────────►│
  │              │               │               │            │             │
  │              │──query()─────►│               │            │             │
  │              │               │──startLLMRequestSpan──────────────────►│
  │              │               │──API call────►│            │             │
  │              │               │◄──stream──────│            │             │
  │              │               │──endLLMRequestSpan(tokens, cost)──────►│
  │              │               │               │            │             │
  │              │               │──tool_use────────────────►│             │
  │              │               │               │  startToolSpan─────────►│
  │              │               │               │  startToolBlockedOnUser►│
  │              │◄──permission? │               │            │             │
  │──approve────►│               │               │            │             │
  │              │               │               │  endToolBlockedOnUser──►│
  │              │               │               │  startToolExecution────►│
  │              │               │               │  execute()  │            │
  │              │               │               │  endToolSpan(result)───►│
  │              │               │               │            │             │
  │              │──endInteractionSpan(duration)─────────────────────────►│
  │◄──response───│               │               │            │             │
  │              │               │               │            │      ┌──────┤
  │              │               │               │            │      │export│
  │              │               │               │            │      │batch │
  │              │               │               │            │      └──────┤
  │              │               │               │            │             │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> 遙測子系統採用 **Observer + Strategy** 模式：各模組透過統一介面發射事件，匯出策略在初始化時動態決定。

1. **WeakRef + AsyncLocalStorage Span 管理** — Span 上下文透過 ALS 傳播，同時用 WeakRef 存儲以防止記憶體洩漏。非 ALS 管理的 Span（LLM request、hook）使用 strongSpans Map 持有強引用，確保在 `end*` 函式呼叫前不被 GC 回收
2. **Delta Temporality 預設** — 預設使用 Delta（增量）而非 Cumulative（累積）時間性，因為對短生命週期的 CLI 會話更合理。但 VictoriaMetrics 會靜默丟棄 Delta 指標，需手動設定 `cumulative`
3. **三層遙測分離** — 標準 OTel（客戶可用）、Beta Tracing（詳細追蹤）、Perfetto（內部除錯）各自獨立，避免客戶承擔不必要的效能開銷
4. **基數控制（Cardinality Control）** — `session.id` 預設包含但可關閉，`app.version` 預設排除。100+ 人團隊必須關閉 session.id 以避免指標爆炸
5. **動態匯入匯出器** — OTLP/Prometheus 匯出器在 protocol switch 內動態 import，避免啟動時載入全部 6 個套件（~1.2MB）

### 資料流（Data Flow）

1. 使用者操作觸發 REPL → QueryEngine → API Client/Tool 調用鏈
2. 各環節呼叫 sessionTracing 的 `start*Span()` / `end*Span()` 函式，記錄 Span 屬性
3. Span 屬性包含 `getTelemetryAttributes()` 返回的基礎屬性（user.id、session.id、organization.id）
4. 指標透過 `getCounter()` 建立的計數器累加（如 cost.usage、token.usage）
5. MeterProvider 按 `OTEL_METRIC_EXPORT_INTERVAL`（預設 60 秒）批次匯出
6. TracerProvider 按 `OTEL_TRACES_EXPORT_INTERVAL`（預設 5 秒）批次匯出
7. LoggerProvider 按 `OTEL_LOGS_EXPORT_INTERVAL`（預設 5 秒）批次匯出
8. 會話結束時觸發 shutdown handler，強制 flush 所有剩餘資料（超時 2 秒）

### 關鍵程式碼（Key Code Snippets）

#### 遙測屬性建構（telemetryAttributes.ts）

```typescript
const METRICS_CARDINALITY_DEFAULTS = {
  OTEL_METRICS_INCLUDE_SESSION_ID: true,
  OTEL_METRICS_INCLUDE_VERSION: false,
  OTEL_METRICS_INCLUDE_ACCOUNT_UUID: true,
}

export function getTelemetryAttributes(): Attributes {
  const userId = getOrCreateUserID()
  const sessionId = getSessionId()

  const attributes: Attributes = {
    'user.id': userId,
  }

  if (shouldIncludeAttribute('OTEL_METRICS_INCLUDE_SESSION_ID')) {
    attributes['session.id'] = sessionId
  }
  if (shouldIncludeAttribute('OTEL_METRICS_INCLUDE_VERSION')) {
    attributes['app.version'] = MACRO.VERSION
  }

  const oauthAccount = getOauthAccountInfo()
  if (oauthAccount) {
    const orgId = oauthAccount.organizationUuid
    const email = oauthAccount.emailAddress
    const accountUuid = oauthAccount.accountUuid

    if (orgId) attributes['organization.id'] = orgId
    if (email) attributes['user.email'] = email

    if (
      accountUuid &&
      shouldIncludeAttribute('OTEL_METRICS_INCLUDE_ACCOUNT_UUID')
    ) {
      attributes['user.account_uuid'] = accountUuid
      attributes['user.account_id'] =
        process.env.CLAUDE_CODE_ACCOUNT_TAGGED_ID ||
        toTaggedId('user', accountUuid)
    }
  }

  if (envDynamic.terminal) {
    attributes['terminal.type'] = envDynamic.terminal
  }

  return attributes
}
```

#### OTel 事件記錄（events.ts）

```typescript
export async function logOTelEvent(
  eventName: string,
  metadata: { [key: string]: string | undefined } = {},
): Promise<void> {
  const eventLogger = getEventLogger()
  if (!eventLogger) {
    if (!hasWarnedNoEventLogger) {
      hasWarnedNoEventLogger = true
      logForDebugging(
        `[3P telemetry] Event dropped (no event logger initialized): ${eventName}`,
        { level: 'warn' },
      )
    }
    return
  }

  const attributes: Attributes = {
    ...getTelemetryAttributes(),
    'event.name': eventName,
    'event.timestamp': new Date().toISOString(),
    'event.sequence': eventSequence++,
  }

  const promptId = getPromptId()
  if (promptId) {
    attributes['prompt.id'] = promptId
  }

  for (const [key, value] of Object.entries(metadata)) {
    if (value !== undefined) {
      attributes[key] = value
    }
  }

  eventLogger.emit({
    body: `claude_code.${eventName}`,
    attributes,
  })
}
```

#### Skill 載入事件追蹤（skillLoadedEvent.ts）

```typescript
export async function logSkillsLoaded(
  cwd: string,
  contextWindowTokens: number,
): Promise<void> {
  const skills = await getSkillToolCommands(cwd)
  const skillBudget = getCharBudget(contextWindowTokens)

  for (const skill of skills) {
    if (skill.type !== 'prompt') continue

    logEvent('tengu_skill_loaded', {
      _PROTO_skill_name:
        skill.name as AnalyticsMetadata_I_VERIFIED_THIS_IS_PII_TAGGED,
      skill_source:
        skill.source as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS,
      skill_loaded_from:
        skill.loadedFrom as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS,
      skill_budget: skillBudget,
      ...(skill.kind && {
        skill_kind:
          skill.kind as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS,
      }),
    })
  }
}
```

#### 工具權限決策記錄（permissionLogging.ts）

```typescript
const CODE_EDITING_TOOLS = ['Edit', 'Write', 'NotebookEdit']

async function buildCodeEditToolAttributes(
  tool: ToolType,
  input: unknown,
  decision: 'accept' | 'reject',
  source: string,
): Promise<Record<string, string>> {
  let language: string | undefined
  if (tool.getPath && input) {
    const parseResult = tool.inputSchema.safeParse(input)
    if (parseResult.success) {
      const filePath = tool.getPath(parseResult.data)
      if (filePath) {
        language = await getLanguageName(filePath)
      }
    }
  }

  return {
    decision,
    source,
    tool_name: tool.name,
    ...(language && { language }),
  }
}
```

## 安裝流程（Installation Flow）

> [!info] 追蹤層級
> 遙測功能為 Claude Code 內建，不需額外安裝。僅需設定環境變數即可啟用。

### 啟用觸發方式

```
CLAUDE_CODE_ENABLE_TELEMETRY=1 → instrumentation.ts:initializeTelemetry() → 建立 Provider
OTEL_METRICS_EXPORTER=otlp → 動態 import OTLP exporter → 連線至 OTLP endpoint
OTEL_TRACES_EXPORTER=otlp → 建立 BatchSpanProcessor → 匯出 Span 至 endpoint
```

### 啟用時序圖

```
Admin          settings.json       Claude Code CLI      OTel Collector     Grafana
  │                 │                    │                    │               │
  │──設定 env──────►│                    │                    │               │
  │                 │                    │                    │               │
  │                 │  CLI 啟動          │                    │               │
  │                 │◄───讀取設定────────│                    │               │
  │                 │                    │                    │               │
  │                 │  bootstrapTelemetry │                   │               │
  │                 │───────────────────►│                    │               │
  │                 │                    │──建立 Exporters───►│               │
  │                 │                    │                    │               │
  │                 │     使用者操作      │                    │               │
  │                 │                    │──metrics batch────►│               │
  │                 │                    │──traces batch─────►│               │
  │                 │                    │──logs batch───────►│               │
  │                 │                    │                    │──store────────►│
  │                 │                    │                    │               │
  │                 │     CLI 結束       │                    │               │
  │                 │                    │──flush all────────►│               │
  │                 │                    │                    │               │
```

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| `CLAUDE_CODE_ENABLE_TELEMETRY` | `1` | 啟用主開關（必要） |
| `OTEL_METRICS_EXPORTER` | `otlp,prometheus,console,none` | 選擇指標匯出器 |
| `OTEL_LOGS_EXPORTER` | `otlp,console,none` | 選擇日誌匯出器 |
| `OTEL_TRACES_EXPORTER` | `otlp,console,none` | 選擇追蹤匯出器（需 Beta） |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` / `http/protobuf` / `http/json` | 通訊協定 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP 端點 |
| `OTEL_EXPORTER_OTLP_HEADERS` | `key=value,key2=value2` | 認證標頭 |
| `OTEL_METRIC_EXPORT_INTERVAL` | `60000`（預設） | 指標匯出間隔 ms |
| `OTEL_METRICS_INCLUDE_SESSION_ID` | `true`（預設） | 100 人團隊建議設 `false` |
| `OTEL_LOG_USER_PROMPTS` | `0`（預設） | 記錄使用者提示內容（隱私風險） |
| `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA` | `1` | 啟用分散式追蹤 |

### 團隊集中部署（Managed Settings）

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector.your-company.com:4317",
    "OTEL_METRICS_INCLUDE_SESSION_ID": "false"
  }
}
```

> [!warning] 解除安裝
> 遙測為內建功能，設定 `CLAUDE_CODE_ENABLE_TELEMETRY=0` 或移除環境變數即可關閉。無需清理任何檔案。

---

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 10 分鐘 PoC（Console Exporter） | 設定 `OTEL_METRICS_EXPORTER=console` | `instrumentation.ts` | `ConsoleMetricExporter → stdout` |
| 2 | 生產級 OTLP 匯出 | 設定 `OTEL_METRICS_EXPORTER=otlp` | `instrumentation.ts` | `OTLPMetricExporter → Collector → Grafana` |
| 3 | 追蹤單次互動成本 | 使用者送出提示 | `sessionTracing.ts` | `startInteractionSpan → startLLMRequestSpan → endLLMRequestSpan(tokens)` |
| 4 | 追蹤工具使用決策 | 工具需要權限批准 | `permissionLogging.ts` | `logPermissionDecision → logOTelEvent + counter.add` |
| 5 | 追蹤 Skill 載入 | CLI 啟動 | `skillLoadedEvent.ts` | `logSkillsLoaded → logEvent('tengu_skill_loaded')` |

### 案例詳解

#### 案例 1：10 分鐘 Console PoC

```
管理者：export CLAUDE_CODE_ENABLE_TELEMETRY=1 && export OTEL_METRICS_EXPORTER=console
  │
  ▼
instrumentation.ts:initializeTelemetry()
  │
  ▼
建立 ConsoleMetricExporter ── 寫入 ──► process.stdout
  │
  ▼
每 10 秒（OTEL_METRIC_EXPORT_INTERVAL=10000）印出指標
  │
  ▼
驗證 claude_code.cost.usage、claude_code.token.usage 等指標正常輸出
```

#### 案例 2：100 人團隊 OTLP 部署

```
平台團隊：部署 OTel Collector + Prometheus + Grafana（Docker Compose）
  │
  ▼
managed settings.json ── 設定 ──► 所有開發者的 Claude Code
  │
  ▼
instrumentation.ts:initializeTelemetry()
  │  ├─ 建立 OTLPMetricExporter（grpc://collector:4317）
  │  ├─ 建立 OTLPLogExporter
  │  └─ 建立 BigQueryMetricsExporter（→ api.anthropic.com）
  │
  ▼
每 60 秒批次匯出 ──► OTel Collector ──► Prometheus ──► Grafana Dashboard
  │
  ▼
管理者在 Grafana 看到：每人成本、快取效率、工具接受率、活躍時間
```

> [!note] 閱讀建議
> 若要快速驗證某功能，從「入口檔案」欄直接跳去讀 `src/utils/telemetry/instrumentation.ts` 最有效率。

---

## 8 個核心指標詳解（Metrics Deep Dive）

> [!important] 以下為 Claude Code 內建的 8 個 OTel 計數器指標，全部定義於 `src/bootstrap/state.ts`

| 指標名稱 | 類型 | 單位 | 說明 | 關鍵屬性 |
|---------|------|------|------|---------|
| `claude_code.cost.usage` | Counter | USD | 會話累計成本 | `model` |
| `claude_code.token.usage` | Counter | tokens | 令牌使用量 | `type`（input/output/cache_read/cache_creation） |
| `claude_code.session.count` | Counter | sessions | CLI 會話啟動數 | `user.id` |
| `claude_code.active_time.total` | Counter | seconds | 活躍時間 | `user`（鍵盤）/ `cli`（工具+AI） |
| `claude_code.commit.count` | Counter | commits | Git 提交數 | - |
| `claude_code.pull_request.count` | Counter | PRs | PR 建立數 | - |
| `claude_code.lines_of_code.count` | Counter | lines | 程式碼變更行數 | added/removed |
| `claude_code.code_edit_tool.decision` | Counter | decisions | 程式碼編輯工具接受/拒絕 | `decision`、`source`、`tool_name`、`language` |

### Span 類型與屬性

| Span 類型 | 觸發時機 | 關鍵屬性 |
|-----------|---------|---------|
| `interaction` | 使用者送出提示 | `user_prompt_length`、`interaction.sequence`、`duration_ms` |
| `llm_request` | API 呼叫 | `model`、`input_tokens`、`output_tokens`、`cache_read_tokens`、`ttft_ms`、`success`、`status_code` |
| `tool` | 工具執行 | `tool_name`、`result_tokens` |
| `tool.blocked_on_user` | 等待權限批准 | `decision`、`source` |
| `hook` | Hook 執行 | `hook_event`、`hook_name`、`num_hooks`、`num_success` |

### 事件類型（Events via Logs Exporter）

| 事件名稱 | 觸發時機 | 用途 |
|---------|---------|------|
| `tengu_skill_loaded` | CLI 啟動 | 追蹤 Skill 可用性與來源 |
| `tengu_tool_use_granted_*` | 工具批准 | 追蹤批准來源（config/classifier/prompt/hook） |
| `tengu_tool_use_denied_*` | 工具拒絕 | 追蹤拒絕來源 |
| `api_error` | API 呼叫失敗（重試耗盡） | 追蹤服務可靠性 |
| `tool_result` | 工具執行完成 | `duration_ms`、`success` |

---

## 100 人團隊部署策略（Deployment Strategy）

> [!tip] 可執行建議（Actionable Tip）
> 以下是針對「100 人公司追蹤 Skill 成功率與使用者體驗」的具體方案。

### 第一階段：基礎可觀測性（第 1-2 週）

1. **部署 OTel Collector + Grafana 堆疊**（參考 [[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]] 的 Docker Compose 範例）
2. **透過 managed settings.json 統一設定**，確保所有人的 CLI 自動回報
3. **關閉 session.id**（`OTEL_METRICS_INCLUDE_SESSION_ID=false`）以控制基數
4. **建立基線儀表板**：成本/人、令牌用量/人、快取讀取率

### 第二階段：Skill 追蹤（第 3-4 週）

> [!warning] 注意事項（Watch Out）
> Claude Code 原生**僅追蹤 Skill 載入（`tengu_skill_loaded`），不追蹤 Skill 執行結果**。要追蹤成功/失敗，需要自訂方案。

**方案 A：透過 Hooks 自訂 Skill 追蹤**

利用 Claude Code 的 Hooks 系統（參見 [[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]]），在 Skill 觸發的工具呼叫前後插入追蹤邏輯：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Skill",
        "command": "curl -X POST http://collector:4318/v1/logs -H 'Content-Type: application/json' -d '{\"resourceLogs\":[{\"resource\":{},\"scopeLogs\":[{\"logRecords\":[{\"body\":{\"stringValue\":\"skill_execution\"},\"attributes\":[{\"key\":\"skill_name\",\"value\":{\"stringValue\":\"$TOOL_INPUT_skill\"}},{\"key\":\"success\",\"value\":{\"stringValue\":\"$TOOL_EXIT_CODE\"}}]}]}]}]}'"
      }
    ]
  }
}
```

**方案 B：透過 OTel Logs 事件分析**

啟用 `OTEL_LOGS_EXPORTER=otlp`，收集所有事件日誌，然後在 Grafana 中用 LogQL 或 PromQL 查詢 `tengu_skill_loaded` 事件，統計各 Skill 的載入頻率作為使用率的代理指標（Proxy Metric）。

**方案 C：自訂包裝腳本**

```bash
#!/bin/bash
# /usr/local/bin/claude-tracked
START=$(date +%s%N)
claude "$@"
EXIT_CODE=$?
END=$(date +%s%N)
DURATION=$(( (END - START) / 1000000 ))

# 發送自訂指標到 OTel Collector
curl -s -X POST http://collector:4318/v1/metrics \
  -H "Content-Type: application/json" \
  -d "{\"resourceMetrics\":[{\"resource\":{\"attributes\":[{\"key\":\"user\",\"value\":{\"stringValue\":\"$(whoami)\"}}]},\"scopeMetrics\":[{\"metrics\":[{\"name\":\"claude_code.skill.execution\",\"sum\":{\"dataPoints\":[{\"asInt\":1,\"attributes\":[{\"key\":\"exit_code\",\"value\":{\"intValue\":$EXIT_CODE}},{\"key\":\"duration_ms\",\"value\":{\"intValue\":$DURATION}}]}]}}]}]}]}"
```

### 第三階段：體驗改善指標（第 5-8 週）

| 指標 | PromQL 查詢範例 | 目標 |
|------|----------------|------|
| 快取讀取率 | `rate(claude_code_token_usage{type="cache_read"}[1h]) / rate(claude_code_token_usage{type="input"}[1h])` | > 40% |
| 工具接受率 | `rate(claude_code_code_edit_tool_decision{decision="accept"}[1d]) / rate(claude_code_code_edit_tool_decision[1d])` | > 80% |
| 人均日成本 | `sum by (user_id)(rate(claude_code_cost_usage[1d]))` | 設定預算上限 |
| 活躍使用者數 | `count(count by (user_id)(rate(claude_code_session_count[7d]) > 0))` | 追蹤採用率 |
| TTFT（首 Token 時間） | 需 Beta Tracing：`llm_request` span 的 `ttft_ms` 屬性 | < 2000ms |

---

## 三層遙測架構比較

| 層級 | 名稱 | 啟用方式 | 目標受眾 | 資料粒度 |
|------|------|---------|---------|---------|
| L1 | 標準 OTel | `CLAUDE_CODE_ENABLE_TELEMETRY=1` | 所有客戶 | 指標 + 事件 |
| L2 | Beta Tracing | `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` | Beta 使用者 | + 分散式追蹤 |
| L3 | Perfetto | `CLAUDE_CODE_PERFETTO_TRACE=1` | Anthropic 內部 | + Chrome Trace 格式 |

---

## 架構師觀點（Architect's View）

### 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | 4/5 | 遙測檔案結構清晰，每個關注點獨立檔案（tracing、events、instrumentation、exporter） |
| 可擴展性（Scalability） | 4/5 | 支援多種匯出器組合，基數控制機制完善，動態匯入避免啟動效能損耗 |
| 隱私設計（Privacy by Design） | 5/5 | 預設脫敏、PII 路由到特權欄位、基數控制、opt-in 主開關 |
| 韌性（Resilience） | 4/5 | 1P Event Logger 有磁碟持久化、二次退避重試、認證降級 |
| 文件品質（Documentation） | 3/5 | 原始碼註解品質高，但官方文件對 Span 屬性和事件類型的說明不夠完整 |

> [!tip] 值得學習的設計
> **WeakRef + ALS 的 Span 生命週期管理**是亮點。用 WeakRef 防止記憶體洩漏，用 ALS 自動傳播上下文，用 30 分鐘 TTL + 60 秒清理間隔作為安全網。這個模式適用於任何需要追蹤非同步操作生命週期的場景。

### 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷

- **Skill 執行追蹤缺失** — 僅追蹤 `tengu_skill_loaded`（載入），不追蹤執行結果（成功/失敗/耗時）。對於想用 Skill 成功率改善使用者體驗的場景，這是最大的功能缺口
- **Delta Temporality 陷阱** — VictoriaMetrics 靜默丟棄 Delta 指標，無錯誤訊息。新手容易卡在「有匯出但 Grafana 無資料」的狀態
- **DISABLE_TELEMETRY 混淆** — `DISABLE_TELEMETRY` 控制 Anthropic 內部 Statsig，`CLAUDE_CODE_ENABLE_TELEMETRY` 控制客戶 OTel，兩個完全獨立的系統用相似名稱，造成混淆（見 GitHub Issue #19117）
- **無內建儀表板** — 需要使用者自行建立 Grafana Dashboard，學習曲線較高

### 改進建議（Improvement Suggestions）

1. **新增 `claude_code.skill.execution` 指標** — 追蹤 Skill 名稱、執行時間、成功/失敗、錯誤類型
2. **提供官方 Grafana Dashboard JSON** — 降低部署門檻，類似 Grafana 已有的 Claude Code 整合
3. **Cumulative Temporality 選項更顯眼** — 在文件中更突出 VictoriaMetrics 的相容性問題

## 效能基準（Benchmark）

> [!info] 資料來源
> 基於原始碼分析的效能特性推估，無公開 benchmark 數據。

| 面向 | 數值 | 說明 |
|------|------|------|
| 匯出器動態匯入節省 | ~1.2 MB | 避免啟動時載入全部 6 個 OTLP 套件 |
| 指標匯出間隔 | 60 秒 | 預設值，可調低至 10 秒用於除錯 |
| Span GC 間隔 | 60 秒 | 清理 30 分鐘以上的孤兒 Span |
| Perfetto 記憶體上限 | 100,000 事件 | 超過後淘汰最舊 50% |
| Shutdown flush 超時 | 2 秒 | 確保 CLI 不會因遙測卡住 |
| 1P Event Logger 重試上限 | 30 秒退避 | 二次退避：base * attempts² |

## 快速上手（Quick Start）

```bash
# 1. 10 分鐘 Console 驗證
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=console
export OTEL_LOGS_EXPORTER=console
export OTEL_METRIC_EXPORT_INTERVAL=10000
claude

# 2. 生產級 OTLP 匯出（假設已有 OTel Collector）
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
claude

# 3. 啟用分散式追蹤（Beta）
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_TRACES_EXPORTER=otlp
```

## 我的心得（My Takeaways）

1. **遙測架構的三層設計非常優雅** — L1 給客戶、L2 給 Beta、L3 給內部，各層獨立啟用互不干擾。這個模式可以直接借鏡到任何需要分層可觀測性的產品
2. **Skill 追蹤是最大缺口** — 對於想用資料驅動改善 Skill 品質的團隊來說，目前只能透過 Hooks 自建追蹤，期待官方補上 `skill.execution` 指標
3. **基數控制是團隊部署的關鍵** — 100 人團隊不關 `session.id` 會導致 Prometheus 指標爆炸。這是原始碼裡有但文件不夠強調的重要細節
4. **WeakRef + ALS 的 Span 管理模式** — 非常適合用在任何 CLI 工具的非同步操作追蹤場景
5. **推薦後端選擇**：Grafana Cloud（免費方案可直接接收 OTLP，零基礎設施維護）或 SigNoz（開源替代，有專門的 Claude Code 文件支援）

## 待補充（Open Questions）

- `tengu_skill_loaded` 事件是否透過客戶 OTel 匯出？還是只走 1P Event Logger 管線？需測試確認。建議搜尋：`logEvent vs logOTelEvent routing`
- BigQuery Exporter 的 `checkMetricsEnabled()` 如何判斷組織是否 opt-out？是否有管理控制台設定？建議搜尋：`Anthropic Console metrics opt-out`
- 分散式追蹤的 `TRACEPARENT` 傳播在 sub-agent（`isolation: "worktree"`）情境下是否正常運作？建議搜尋：`Claude Code worktree TRACEPARENT propagation`
- Perfetto Tracing 是否有計畫對外開放？Chrome Trace 格式的視覺化效果遠優於 Jaeger。建議搜尋：`Claude Code Perfetto external access`
- 100 人團隊下，`organization.id` 屬性在 OAuth 認證場景中如何對應到具體人員？需要 Anthropic Console 的組織管理支援。建議搜尋：`Anthropic organization management API`
- `claude_code.active_time.total` 的 `user` 和 `cli` 兩種類型的精確計算邏輯為何？是否包含等待 API 回應的時間？建議搜尋：`active_time tracking implementation`
- 1P Event Logger 的 `tengu_event_sampling_config` 採樣率設定是否也影響客戶 OTel 匯出？還是完全獨立的管線？建議搜尋：`event sampling config scope`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | 三層遙測架構（Standard/Beta/Perfetto）、8 個計數器指標名稱、5 種 Span 類型、`CLAUDE_CODE_ENABLE_TELEMETRY=1` 主開關 |
| **理解（半被動）** | 串聯知識點，掌握核心邏輯 | 遙測資料從 CLI Session → Instrumentation Layer → Exporters → External Backends 的完整流向；Delta vs Cumulative Temporality 的差異對後端相容性的影響；Skill 載入事件與 Skill 執行結果是完全不同的追蹤層級 |
| **分析（主動）** | 批判性思維，看透底層邏輯 | 原生 Skill 追蹤僅到「載入」層級是功能缺口而非設計疏忽——Anthropic 優先解決成本/採用率可見度問題，Skill 執行追蹤可能因 Skill 定義的多樣性（prompt type、fork mode、inline mode）而難以標準化；`DISABLE_TELEMETRY` 與 `CLAUDE_CODE_ENABLE_TELEMETRY` 的命名混淆反映了遙測系統從內部工具演化為客戶功能的歷史包袱 |
| **應用（主動）** | 將理論轉為行動 | (1) 本週內用 Console Exporter 做 10 分鐘 PoC，驗證指標正常流出；(2) 下週部署 OTel Collector + Grafana，用 managed settings.json 統一設定團隊；(3) 第三週用 Hooks 建立自訂 Skill 執行追蹤 |
| **評估（主動）** | 判斷方案優劣，做出決策 | OTel 原生方案 vs Anthropic Analytics API：OTel 提供即時指標但缺少 Skill 追蹤；Analytics API 提供更豐富的歷史資料但延遲較高且依賴 Anthropic 基礎設施。100 人團隊建議兩者並用——OTel 做即時監控告警，Analytics API 做月度報告 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Enhanced Telemetry Beta」與標準 OTel 的界線在哪裡？啟用 Beta 後是否所有 Span 都會匯出，還是僅限特定類型？
- **假設**：本文假設 100 人團隊全部使用 API Key 認證。若部分使用 Claude.ai 訂閱（非 API 計費），成本指標的意義如何改變？
- **證據**：「關閉 session.id 以控制基數」的建議基於 Prometheus 的一般實踐，但具體在 100 人規模下 session.id 會產生多少時間序列？需要實測
- **觀點**：若站在 Anthropic 產品經理立場，不追蹤 Skill 執行結果可能是刻意的——因為追蹤執行結果意味著需要定義「成功」，而 LLM 回應的「成功」本身就難以客觀量化
- **後果**：若 100 人團隊啟用 `OTEL_LOG_USER_PROMPTS=1`，12 個月後可能累積大量含敏感資訊的日誌，需要制定資料保留與清除策略

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 在 100 人規模下，若 OTel Collector 成為單點故障（Single Point of Failure），所有人的遙測資料會同時丟失。應部署 HA（高可用）Collector 或使用 Grafana Cloud 等託管方案
2. **什麼情況下會失敗？** — (a) 使用 VictoriaMetrics 但忘記設定 Cumulative Temporality → 指標靜默消失；(b) 未關閉 session.id 導致 Prometheus OOM；(c) 網路防火牆阻擋 gRPC 4317 埠但無錯誤提示
3. **有沒有更好的替代方案？** — **Anthropic Analytics API**（`/api/claude_code_analytics`）提供伺服器端統計，不需要客戶端部署任何基礎設施。適合只想看月報的團隊。但它無法做到即時監控、自訂告警、或追蹤組織特有的指標（如 Skill 執行率）

---

## 相關連結（Related）
- [[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]] — 實戰案例：7 人團隊部署 OTel 的完整 Docker Compose 堆疊與 8 個指標分析
- [[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]] — 另一個 AI 工具（gstack）的遙測架構設計比較，採用 JSONL + Supabase 而非 OTel
- [[2026-04-04-GSTACK-SECURITY-TELEMETRY-CONTROVERSY]] — 遙測功能的隱私爭議：預設開啟 vs opt-in 的治理問題
- [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — managed settings.json 的設定層級機制，用於團隊集中部署遙測
- [[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]] — Hooks 系統可用於自訂 Skill 追蹤（方案 A）
- [[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]] — Team Memory 功能與組織級管理的另一個面向
- [[2026-04-17-CLAUDE-CODE-FEEDBACK-FRUSTRATION-DETECTION-EVENTMETADATA-ARCHITECTURE]] — 同一遙測系統的反饋/事件層分析：Frustration Detection 演算法、三管道反饋機制、EventMetadata 傳送架構

## References
- [Claude Code Monitoring - Anthropic Docs](https://docs.anthropic.com/en/docs/claude-code/monitoring-usage)
- [Claude Code Analytics API](https://docs.anthropic.com/en/api/claude-code-analytics-api)
- [Agent SDK Observability](https://code.claude.com/docs/en/agent-sdk/observability)
- [Grafana Cloud - Claude Code Integration](https://grafana.com/docs/grafana-cloud/monitor-infrastructure/integrations/integration-reference/integration-claude-code/)
- [SigNoz - Claude Code Monitoring](https://signoz.io/docs/claude-code-monitoring/)
- [Honeycomb - Claude Code Observability](https://www.honeycomb.io/blog/can-claude-code-observe-its-own-code)
- [GitHub Issue #19117 - Telemetry Confusion](https://github.com/anthropics/claude-code/issues/19117)
- [claude-code-otel Docker Compose](https://github.com/ColeMurray/claude-code-otel)
- [Medium - Team Data Revealed (Reza Rezvani)](https://alirezarezvani.medium.com/the-new-claude-code-monitoring-what-our-team-data-revealed-e7f0424d738f)
