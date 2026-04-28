---
title: "Claude Code Token 成本計算完整管線研究 — 從 API 回應到 JSONL 事後分析的精確對齊方案"
date: 2026-04-28
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#tools/claude-code"
  - "#ai/token-optimization"
  - "#ai/cost-tracking"
  - "#tools/analytics"
source: "conversation research: Claude Code token & cost calculation pipeline analysis"
source_type: code
author: "Anthropic (decompiled source)"
status: notes
links:
  - "[[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-17-CLAUDE-CODE-FEEDBACK-FRUSTRATION-DETECTION-EVENTMETADATA-ARCHITECTURE]]"
  - "[[2026-01-22-THE-LONGFORM-GUIDE-TO-EVERYTHING-CLAUDE-CODE]]"
  - "[[2026-01-24-CLAUDE-CODE-HOOKS-CODE-ANALYSIS]]"
github_stars: N/A
github_language: TypeScript
---

## 摘要（Summary）

從 Claude Code 反編譯原始碼中，完整追蹤 **Token 計數與費用計算** 的全管線設計——從 Anthropic API 回傳的 `usage` 物件，經過即時計費、JSONL 持久化，到事後分析的完整資料流。本研究涵蓋 8 個核心檔案、約 2,500+ 行程式碼的分析，揭示了 6 個定價層級、4 種 token 分類、Opus 4.6 雙重定價機制，以及 **JSONL 事後分析的 6 個致命陷阱**（實測顯示天真累加會導致 90% 的費用高估）。最終提供完整的 Python 分析腳本，精確對齊 `/cost` 指令的計算結果。

## Why — 為什麼要研究這個？

> 核心問題：使用者在使用 Claude Code 時，想知道「花了多少錢」——但 JSONL session log 中 **不存費用**，只存原始 token 計數。如何從 JSONL 正確重建費用？

- **核心動機**：Claude Code 的 `/cost` 指令在 session 進行中可即時顯示費用，但 session 結束後這些資料只能從 JSONL 重建。重建過程存在多個非直覺的陷阱。
- **解決什麼**：讓使用者能對歷史 session 做精確的費用分析，對齊 `/cost` 的計算邏輯。
- **目標用戶**：API 付費使用者、團隊管理者（追蹤 Token 消耗）、開發者（建構自訂監控儀表板）。

## What — 涵蓋什麼？

- **Token 計數來源**：API 伺服器回傳，非本地計算
- **即時計費管線**：`claude.ts` → `calculateUSDCost()` → `addToTotalSessionCost()` → `STATE`
- **JSONL 寫入路徑**：`message.usage` 如何嵌入 transcript entry
- **JSONL 讀取與事後分析**：正確提取 token 數據的 JSON path
- **6 個陷阱**：重複 entries、advisor 子用量、fast mode、synthetic、classifier、subagent
- **完整分析腳本**：Python 實作，可直接對齊 `/cost`

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Anthropic Claude API Server                     │
│                                                                      │
│  每次 API 呼叫回傳 usage 物件（token 計數由伺服器產生，非本地計算）      │
│  { input_tokens, output_tokens, cache_creation_input_tokens,         │
│    cache_read_input_tokens, server_tool_use, speed, iterations }      │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ streaming: message_delta event
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                 claude.ts (API Client)                                │
│                 src/services/api/claude.ts:2245-2257                  │
│                                                                      │
│  ① lastMsg.message.usage = usage    ← 掛到 message 物件上           │
│  ② calculateUSDCost(model, usage)   ← 查定價表算美金                 │
│  ③ addToTotalSessionCost(cost, usage, model) ← 累加到全局            │
└─────────────┬─────────────────────────────────┬──────────────────────┘
              │ (即時計費路徑)                    │ (持久化路徑)
              ▼                                  ▼
┌─────────────────────────┐       ┌──────────────────────────────────┐
│ modelCost.ts            │       │ sessionStorage.ts                │
│ ┌─────────────────────┐ │       │                                  │
│ │ getModelCosts()     │ │       │ insertMessageChain(messages)     │
│ │ → 查 MODEL_COSTS 表 │ │       │ → appendEntry(transcriptMsg)    │
│ │ → 判斷 fast mode    │ │       │ → appendEntryToFile()           │
│ └──────────┬──────────┘ │       │ → JSON.stringify(entry) + '\n'  │
│ ┌──────────▼──────────┐ │       │ → fs.appendFileSync()           │
│ │ tokensToUSDCost()   │ │       └──────────────┬───────────────────┘
│ │ → 套用計費公式      │ │                       │
│ └─────────────────────┘ │                       ▼
└─────────────┬───────────┘       ┌──────────────────────────────────┐
              │                   │ .jsonl 檔案 (磁碟)               │
              ▼                   │ ~/.claude/projects/<proj>/       │
┌─────────────────────────┐       │      <sessionId>.jsonl           │
│ cost-tracker.ts         │       │ ┌─ {"type":"user",...}           │
│                         │       │ ├─ {"type":"assistant",          │
│ addToTotalSessionCost() │       │ │    "message":{"usage":{...}}}  │
│ ① per-model 累加        │       │ ├─ {"type":"assistant",...}      │
│ ② STATE.totalCostUSD   │       │ └─ ...                           │
│ ③ OTel counters 上報   │       │                                  │
│ ④ advisor 遞迴處理      │       │ ⚠ 不存 cost，只存 token 計數    │
└──────────┬──────────────┘       └──────────┬───────────────────────┘
           │                                  │
           ▼                                  ▼
┌─────────────────────────┐       ┌──────────────────────────────────┐
│ STATE (全局狀態)         │       │ 事後分析                          │
│ bootstrap/state.ts      │       │                                  │
│                         │       │ stats.ts:processSessionFiles()   │
│ totalCostUSD            │       │ → 讀取 .jsonl 逐行              │
│ modelUsage: {[model]:   │       │ → 篩選 type=assistant + usage    │
│   ModelUsage}           │       │ → 累加 per-model tokens          │
│ totalAPIDuration        │       │ → 自行用定價表算費用             │
│ totalLinesAdded/Removed │       │                                  │
└──────────┬──────────────┘       │ ⚠ 必須去重 + 處理陷阱           │
           │                      └──────────────────────────────────┘
           ▼
┌─────────────────────────┐
│ 顯示層                   │
│ StatusLine.tsx ← 即時    │
│ /cost 指令    ← 手動查   │
│ Stats.tsx     ← 歷史圖表 │
│ saveCurrentSessionCosts()│
│   → project config JSON  │
└─────────────────────────┘
```

### 執行流程圖（Execution Flowchart）

```
使用者發送訊息
   │
   ▼
query.ts 組裝 API 請求
   │
   ▼
claude.ts 呼叫 Anthropic API (streaming)
   │
   ├── message_start event
   │   └─ 初始 usage (input/cache tokens 已確定)
   │
   ├── content_block_stop event (可能多次)
   │   └─ 每個 content block 建立一條 AssistantMessage
   │      └─ 此時 usage 是 partial (output_tokens 還在增長)
   │      └─ message 被 yield 出去 → 寫入 JSONL ⚠
   │
   └── message_delta event (最終，只一次)
       │
       ├─ usage = final (完整的 token 計數)
       │
       ├─ lastMsg.message.usage = usage (只更新最後一條)
       │
       ├─ calculateUSDCost(model, usage)
       │   │
       │   ├─ getModelCosts(model, usage)
       │   │   │
       │   │   ├─ 是 Opus 4.6? ──是──► usage.speed == "fast"?
       │   │   │                           ├─ 是 → $30/$150
       │   │   │                           └─ 否 → $5/$25
       │   │   │
       │   │   └─ 否 → 查 MODEL_COSTS 表
       │   │       └─ 找不到 → fallback $5/$25 + 標記 unknown
       │   │
       │   └─ tokensToUSDCost(costs, usage)
       │       └─ 套用公式 → 回傳 USD 金額
       │
       └─ addToTotalSessionCost(cost, usage, model)
           │
           ├─ STATE.totalCostUSD += cost
           ├─ per-model usage 計數器累加
           ├─ OTel costCounter.add(cost)
           ├─ OTel tokenCounter.add(各類 tokens)
           │
           └─ getAdvisorUsage(usage)
               │
               └─ 遍歷 usage.iterations[]
                   └─ type == "advisor_message"?
                       └─ 是 → 遞迴呼叫 addToTotalSessionCost()
```

### JSONL 寫入時序圖（Sequence Diagram）

```
 API Server       claude.ts          REPL/query        sessionStorage      Disk (.jsonl)
     │                │                   │                  │                  │
     │──stream event─►│                   │                  │                  │
     │  (msg_start)   │                   │                  │                  │
     │                │──set partial usage │                  │                  │
     │                │                   │                  │                  │
     │──stream event─►│                   │                  │                  │
     │ (block_stop)   │──yield msg────────►│                  │                  │
     │                │  (partial usage)  │──insertChain()──►│                  │
     │                │                   │                  │──appendEntry()──►│ ⚠ partial
     │                │                   │                  │                  │
     │──stream event─►│                   │                  │                  │
     │ (block_stop)   │──yield msg────────►│                  │                  │
     │                │  (partial usage)  │──insertChain()──►│                  │
     │                │                   │                  │──appendEntry()──►│ ⚠ partial
     │                │                   │                  │                  │
     │──stream event─►│                   │                  │                  │
     │ (msg_delta)    │                   │                  │                  │
     │  FINAL usage   │──mutate last msg  │                  │                  │
     │                │  .usage = final   │                  │                  │
     │                │──yield msg────────►│                  │                  │
     │                │                   │──insertChain()──►│                  │
     │                │                   │                  │──appendEntry()──►│ ★ final
     │                │                   │                  │                  │
     │                │──addToTotalSession │                  │                  │
     │                │  Cost(final)      │                  │                  │
     │                │                   │                  │                  │
```

> [!warning] JSONL 中的 usage 陷阱
> 由於 streaming 的非同步性，一次 API 呼叫可能產生 2-4 條 assistant 行（共享同一個 `message.id`）。
> 早期行的 usage 是 **partial**（output_tokens 還在增長），只有最後一條是 **final**。
> `claude.ts` 的計費只在 `message_delta` 事件時觸發一次（使用 final usage），但 JSONL 中所有行都帶 usage。

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> Token 計數採用「伺服器權威」模式——所有 token 數量由 API 伺服器計算並回傳，本地不做 tokenization。費用計算則是純本地邏輯（查定價表 + 數學公式）。

1. **Token 不本地計算** — API 伺服器回傳的 `usage` 物件是唯一權威來源。本地只做粗估（`字元數 ÷ 4`）用於補足最後一次 API 回覆後新增的訊息。
2. **費用不存入 JSONL** — JSONL 只存原始 token 計數，費用在 runtime 計算。這允許定價表更新後重新計算歷史費用。
3. **Per-model 分帳** — 每個模型獨立追蹤用量（input/output/cache_read/cache_write/web_search/cost），支援混合模型場景。
4. **直接 mutation 而非物件替換** — `lastMsg.message.usage = usage`（直接修改屬性），因為 transcript write queue 持有 message 物件的引用，物件替換會斷開引用。
5. **Advisor 遞迴計費** — 伺服器端 advisor tool 的子用量嵌套在 `usage.iterations[]` 中，`addToTotalSessionCost()` 遞迴處理。

### 資料流（Data Flow）

1. Anthropic API 伺服器在 streaming 結束時回傳 `message_delta` 事件，攜帶完整的 `usage` 物件
2. `claude.ts` 將 usage 掛到 message 物件上，同時觸發計費
3. `calculateUSDCost()` 根據模型名稱查定價表，套用公式算出美金金額
4. `addToTotalSessionCost()` 累加到全局 `STATE`，同時上報 OpenTelemetry
5. Message（含 usage）被 `sessionStorage` 序列化寫入 `.jsonl` 檔案
6. 事後分析從 `.jsonl` 讀取 assistant message 的 `message.usage`，用定價表重算費用

### 關鍵程式碼（Key Code Snippets）

#### 核心計費公式 — `tokensToUSDCost()`

```typescript
// src/utils/modelCost.ts:131-141
function tokensToUSDCost(modelCosts: ModelCosts, usage: Usage): number {
  return (
    (usage.input_tokens / 1_000_000) * modelCosts.inputTokens +
    (usage.output_tokens / 1_000_000) * modelCosts.outputTokens +
    ((usage.cache_read_input_tokens ?? 0) / 1_000_000) *
      modelCosts.promptCacheReadTokens +
    ((usage.cache_creation_input_tokens ?? 0) / 1_000_000) *
      modelCosts.promptCacheWriteTokens +
    (usage.server_tool_use?.web_search_requests ?? 0) *
      modelCosts.webSearchRequests
  )
}
```

#### Opus 4.6 雙重定價 — `getModelCosts()`

```typescript
// src/utils/modelCost.ts:144-164
export function getModelCosts(model: string, usage: Usage): ModelCosts {
  const shortName = getCanonicalName(model)
  // Opus 4.6 根據 speed 動態選擇定價
  if (shortName === firstPartyNameToCanonical(CLAUDE_OPUS_4_6_CONFIG.firstParty)) {
    const isFastMode = usage.speed === 'fast'
    return getOpus46CostTier(isFastMode)
    // fast → COST_TIER_30_150 ($30/$150)
    // normal → COST_TIER_5_25 ($5/$25)
  }
  const costs = MODEL_COSTS[shortName]
  if (!costs) {
    trackUnknownModelCost(model, shortName)
    return MODEL_COSTS[getCanonicalName(getDefaultMainLoopModelSetting())] ?? DEFAULT_UNKNOWN_MODEL_COST
  }
  return costs
}
```

#### 累加與 Advisor 遞迴 — `addToTotalSessionCost()`

```typescript
// src/cost-tracker.ts:278-323
export function addToTotalSessionCost(cost: number, usage: Usage, model: string): number {
  const modelUsage = addToTotalModelUsage(cost, usage, model)
  addToTotalCostState(cost, modelUsage, model)

  // OTel 上報
  getCostCounter()?.add(cost, attrs)
  getTokenCounter()?.add(usage.input_tokens, { ...attrs, type: 'input' })
  getTokenCounter()?.add(usage.output_tokens, { ...attrs, type: 'output' })
  getTokenCounter()?.add(usage.cache_read_input_tokens ?? 0, { ...attrs, type: 'cacheRead' })
  getTokenCounter()?.add(usage.cache_creation_input_tokens ?? 0, { ...attrs, type: 'cacheCreation' })

  let totalCost = cost
  // 遞迴處理 advisor 子用量
  for (const advisorUsage of getAdvisorUsage(usage)) {
    const advisorCost = calculateUSDCost(advisorUsage.model, advisorUsage)
    totalCost += addToTotalSessionCost(advisorCost, advisorUsage, advisorUsage.model)
  }
  return totalCost
}
```

#### JSONL 寫入 — `appendEntryToFile()`

```typescript
// src/utils/sessionStorage.ts:2573-2584
function appendEntryToFile(fullPath: string, entry: Record<string, unknown>): void {
  const fs = getFsImplementation()
  const line = jsonStringify(entry) + '\n'
  try {
    fs.appendFileSync(fullPath, line, { mode: 0o600 })
  } catch {
    fs.mkdirSync(dirname(fullPath), { mode: 0o700 })
    fs.appendFileSync(fullPath, line, { mode: 0o600 })
  }
}
```

#### Context Window 估算 — `tokenCountWithEstimation()`

```typescript
// src/utils/tokens.ts:230-265
export function tokenCountWithEstimation(messages: readonly Message[]): number {
  // 找最後一個有 usage 的 assistant message
  // 走回同一個 message.id 的第一條（處理平行 tool call 拆分）
  // context size = 上次 API 的 token 總計 + 之後新增訊息的粗估
  return getTokenCountFromUsage(usage) +
    roughTokenCountEstimationForMessages(messages.slice(i + 1))
}
// 粗估方式：字元數 ÷ 4
```

---

## 定價表（Pricing Table）

所有定價數據來自 `src/utils/modelCost.ts`，對應 [Anthropic 官方定價](https://platform.claude.com/docs/en/about-claude/pricing)。

| 模型 | 定價層級 | Input / Mtok | Output / Mtok | Cache Write / Mtok | Cache Read / Mtok | Web Search / 次 |
|------|---------|-------------|--------------|-------------------|------------------|----------------|
| Sonnet 全系列（3.5v2/3.7/4/4.5/4.6） | COST_TIER_3_15 | $3 | $15 | $3.75 | $0.30 | $0.01 |
| Opus 4 / 4.1 | COST_TIER_15_75 | $15 | $75 | $18.75 | $1.50 | $0.01 |
| Opus 4.5 | COST_TIER_5_25 | $5 | $25 | $6.25 | $0.50 | $0.01 |
| **Opus 4.6 (normal)** | COST_TIER_5_25 | $5 | $25 | $6.25 | $0.50 | $0.01 |
| **Opus 4.6 (fast mode)** | COST_TIER_30_150 | **$30** | **$150** | **$37.50** | **$3.00** | $0.01 |
| Haiku 3.5 | COST_HAIKU_35 | $0.80 | $4 | $1.00 | $0.08 | $0.01 |
| Haiku 4.5 | COST_HAIKU_45 | $1 | $5 | $1.25 | $0.10 | $0.01 |

> [!warning] Opus 4.6 雙重定價
> Opus 4.6 的定價取決於 `usage.speed` 欄位。`"fast"` 時用 $30/$150（6 倍正常價）。
> Fast mode 是由使用者開啟 `/fast` 後，API 伺服器自動使用快速推理通道並在 usage 中標記。

---

## JSONL 資料結構

### JSONL 檔案位置

```
~/.claude/projects/<projectId>/<sessionId>.jsonl          ← 主 session
~/.claude/projects/<projectId>/<sessionId>/subagents/
    agent-<agentId>.jsonl                                 ← 子 agent
```

### Assistant 行的完整結構（真實範例）

```json
{
  "type": "assistant",
  "uuid": "a1b2c3d4-...",
  "parentUuid": "e5f6g7h8-...",
  "isSidechain": false,
  "sessionId": "f3e6c061-...",
  "timestamp": "2026-04-28T06:30:00.000Z",
  "cwd": "/Users/swchen.tw/git/claude-code",
  "version": "2.1.108",
  "gitBranch": "main",
  "userType": "ant",
  "requestId": "req_abc123...",

  "message": {
    "id": "msg_01XYZ...",
    "type": "message",
    "role": "assistant",
    "model": "claude-opus-4-6",
    "content": [{ "type": "text", "text": "..." }],
    "stop_reason": "end_turn",

    "usage": {
      "input_tokens": 1,
      "cache_creation_input_tokens": 14236,
      "cache_read_input_tokens": 53925,
      "output_tokens": 3528,
      "server_tool_use": { "web_search_requests": 0 },
      "speed": "standard",
      "service_tier": "standard",
      "cache_creation": {
        "ephemeral_1h_input_tokens": 14236,
        "ephemeral_5m_input_tokens": 0
      },
      "iterations": [],
      "inference_geo": ""
    }
  }
}
```

### 事後分析的 JSON Path 速查

| JSON Path | 用途 |
|-----------|------|
| `.type` | 篩選 `"assistant"` |
| `.message.model` | 查定價表 |
| `.message.id` | 去重（平行 tool call） |
| `.message.usage.input_tokens` | 累加 |
| `.message.usage.output_tokens` | 累加 |
| `.message.usage.cache_creation_input_tokens` | 累加 |
| `.message.usage.cache_read_input_tokens` | 累加 |
| `.message.usage.server_tool_use.web_search_requests` | 累加 |
| `.message.usage.speed` | 判斷 fast mode |
| `.message.usage.iterations[]` | Advisor 子用量 |
| `.timestamp` | 時間序列分析 |

---

## 事後分析的 6 個陷阱

### 陷阱 1：平行 tool call 產生重複 entries（最致命，誤差 90%）

**問題**：當 Claude 一次回覆中使用多個工具時（例如 thinking + 3 個 tool_use），streaming 會為每個 content block 產生一條獨立的 assistant 行。它們共享同一個 `message.id`，但每條都帶 usage。

**原因**：`claude.ts` 在 `content_block_stop` 事件時就建立新的 AssistantMessage 並 yield（`:2210`），此時 usage 是 partial。只有 `message_delta` 事件（最後）才帶有 final usage，但只更新 `newMessages.at(-1)`。

**實測數據（真實 session）**：

```
# 同一個 message.id: msg_01R2qHo34aNCas26eKUKHFG7
Line 6:  content=thinking  output_tokens=21    ← partial
Line 7:  content=tool_use  output_tokens=561   ← final ★

# 同一個 message.id: msg_01KaGM3ksPGfjtaNes6E5Ag6 (4 entries!)
Line 15: content=thinking  output_tokens=20    ← partial
Line 16: content=tool_use  output_tokens=20    ← partial
Line 18: content=tool_use  output_tokens=20    ← partial
Line 20: content=tool_use  output_tokens=239   ← final ★
```

**實測誤差**：

```
天真法（所有行）: cost=$7.6107  input=17,358  output=42,756
正確法（去重後）: cost=$4.0055  input=6,242   output=41,544

差異: cost 多算 $3.6053（誤差率 90%）
差異: input 多算 11,116 tokens
```

> [!important] 正確做法
> 按 `message.id` 分組，**只取每組的最後一條**（它有 final usage）。

### 陷阱 2：Advisor 子用量（隱藏費用）

**問題**：`/cost` 在計算時會從 `usage.iterations[]` 中提取 `type === "advisor_message"` 的條目，這些是伺服器端 advisor tool 的子用量，有獨立的模型和 token 數，會額外累加到總費用中。

```typescript
// advisor.ts:115-128
export function getAdvisorUsage(usage: BetaUsage): Array<BetaUsage & { model: string }> {
  const iterations = usage.iterations
  if (!iterations) return []
  return iterations.filter(it => it.type === 'advisor_message')
}
```

> [!important] 正確做法
> 遍歷 `usage.iterations[]`，對 `type === "advisor_message"` 的條目，用其自帶的 `model` 查定價表，獨立計算費用後加總。

### 陷阱 3：Fast mode 動態定價

**問題**：Opus 4.6 有兩套定價（normal $5/$25 vs fast $30/$150），不能只看模型名稱，還必須看 `usage.speed` 欄位。

> [!important] 正確做法
> `model == "claude-opus-4-6" and usage.speed == "fast"` 時用 6 倍定價。

### 陷阱 4：合成訊息（Synthetic Messages）

**問題**：`message.model === "synthetic"` 的行是內部合成的假訊息（用於 compaction boundary 等），不代表真實的 API 呼叫。

> [!tip] 正確做法
> 篩選時跳過 `model === "synthetic"`。

### 陷阱 5：Classifier 費用不在 /cost 中

**問題**：Auto mode 的權限分類器（yoloClassifier）使用 Haiku 做 side query，程式碼明確註解：`// does NOT call addToTotalSessionCost, so classifier tokens are excluded`。分類器的 usage 也不寫入 JSONL。

> [!warning] 已知差異
> `/cost` 不包含分類器費用，JSONL 也沒有。如果你想追蹤 Anthropic 實際帳單上的費用，分類器費用是一個 gap。

### 陷阱 6：Subagent 的 JSONL 在不同路徑

**問題**：Subagent（Agent tool 產生的子 agent）的 transcript 不在主 session 檔案中，而是在 `<sessionId>/subagents/agent-<agentId>.jsonl`。

> [!important] 正確做法
> 分析時掃描 `subagents/` 子目錄下的所有 `.jsonl` 檔案。

---

## 完整正確的分析腳本（Python）

```python
import json, os
from pathlib import Path
from collections import defaultdict

# ═══════════════════════════════════════════════════════════
# 定價表（USD per million tokens）
# 來源: src/utils/modelCost.ts — MODEL_COSTS
# ═══════════════════════════════════════════════════════════
PRICING = {
    "claude-opus-4-6":   {"in": 5,    "out": 25,  "cw": 6.25,  "cr": 0.5},
    "claude-opus-4-5":   {"in": 5,    "out": 25,  "cw": 6.25,  "cr": 0.5},
    "claude-opus-4-1":   {"in": 15,   "out": 75,  "cw": 18.75, "cr": 1.5},
    "claude-opus-4":     {"in": 15,   "out": 75,  "cw": 18.75, "cr": 1.5},
    "claude-sonnet-4-6": {"in": 3,    "out": 15,  "cw": 3.75,  "cr": 0.3},
    "claude-sonnet-4-5": {"in": 3,    "out": 15,  "cw": 3.75,  "cr": 0.3},
    "claude-sonnet-4":   {"in": 3,    "out": 15,  "cw": 3.75,  "cr": 0.3},
    "claude-3-7-sonnet": {"in": 3,    "out": 15,  "cw": 3.75,  "cr": 0.3},
    "claude-haiku-4-5":  {"in": 1,    "out": 5,   "cw": 1.25,  "cr": 0.1},
    "claude-3-5-haiku":  {"in": 0.8,  "out": 4,   "cw": 1.0,   "cr": 0.08},
}
FAST_PRICING = {"in": 30, "out": 150, "cw": 37.5, "cr": 3.0}
DEFAULT_PRICING = PRICING["claude-opus-4-6"]

def canonicalize(model: str) -> str:
    """模擬 src/utils/model/model.ts 的 firstPartyNameToCanonical()"""
    m = model.lower()
    # 順序重要：先匹配更具體的版本號
    for key in ["claude-opus-4-6", "claude-opus-4-5", "claude-opus-4-1",
                "claude-opus-4",
                "claude-sonnet-4-6", "claude-sonnet-4-5", "claude-sonnet-4",
                "claude-3-7-sonnet", "claude-3-5-sonnet",
                "claude-haiku-4-5", "claude-3-5-haiku"]:
        if key in m:
            return key
    return m

def get_pricing(model: str, usage: dict) -> dict:
    """模擬 src/utils/modelCost.ts 的 getModelCosts()"""
    canonical = canonicalize(model)
    # 陷阱 3: Opus 4.6 fast mode
    if canonical == "claude-opus-4-6" and usage.get("speed") == "fast":
        return FAST_PRICING
    return PRICING.get(canonical, DEFAULT_PRICING)

def calc_cost(model: str, usage: dict) -> float:
    """模擬 src/utils/modelCost.ts 的 tokensToUSDCost()"""
    p = get_pricing(model, usage)
    return (
        (usage.get("input_tokens", 0) / 1_000_000) * p["in"]
      + (usage.get("output_tokens", 0) / 1_000_000) * p["out"]
      + (usage.get("cache_creation_input_tokens", 0) / 1_000_000) * p["cw"]
      + (usage.get("cache_read_input_tokens", 0) / 1_000_000) * p["cr"]
      + usage.get("server_tool_use", {}).get("web_search_requests", 0) * 0.01
    )

def analyze_jsonl(path: str) -> dict:
    """
    正確分析單個 JSONL 檔案。
    回傳格式與 /cost 的 formatModelUsage() 對齊。
    """
    # 陷阱 1: 按 message.id 分組，只取最後一條
    last_by_id = {}  # message_id → (model, usage)

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("type") != "assistant":
                continue
            msg = entry.get("message", {})
            usage = msg.get("usage")
            if not usage:
                continue
            model = msg.get("model", "unknown")
            # 陷阱 4: 跳過合成訊息
            if model == "synthetic":
                continue
            msg_id = msg.get("id", f"noid-{id(entry)}")
            # 後出現的覆蓋前面的 → 最後一條 = final usage
            last_by_id[msg_id] = (model, usage)

    # 累加 per-model 統計
    totals = defaultdict(lambda: {
        "input": 0, "output": 0, "cache_w": 0, "cache_r": 0,
        "web_search": 0, "cost": 0.0
    })

    for msg_id, (model, usage) in last_by_id.items():
        canonical = canonicalize(model)
        cost = calc_cost(model, usage)
        t = totals[canonical]
        t["input"]      += usage.get("input_tokens", 0)
        t["output"]     += usage.get("output_tokens", 0)
        t["cache_w"]    += usage.get("cache_creation_input_tokens", 0)
        t["cache_r"]    += usage.get("cache_read_input_tokens", 0)
        t["web_search"] += usage.get("server_tool_use", {}).get("web_search_requests", 0)
        t["cost"]       += cost

        # 陷阱 2: 處理 advisor 子用量
        for it in usage.get("iterations", []):
            if it.get("type") == "advisor_message":
                adv_model = it.get("model", model)
                adv_cost = calc_cost(adv_model, it)
                adv_canonical = canonicalize(adv_model)
                ta = totals[adv_canonical]
                ta["input"]   += it.get("input_tokens", 0)
                ta["output"]  += it.get("output_tokens", 0)
                ta["cache_w"] += it.get("cache_creation_input_tokens", 0)
                ta["cache_r"] += it.get("cache_read_input_tokens", 0)
                ta["cost"]    += adv_cost

    return dict(totals)

def analyze_session(session_dir: str, session_id: str) -> dict:
    """
    分析完整 session：主檔案 + 所有 subagent 檔案。
    陷阱 6: 別忘了 subagents/
    """
    results = {}

    # 主 session 檔案
    main_jsonl = os.path.join(session_dir, f"{session_id}.jsonl")
    if os.path.exists(main_jsonl):
        results = analyze_jsonl(main_jsonl)

    # Subagent 檔案
    subagent_dir = os.path.join(session_dir, session_id, "subagents")
    if os.path.isdir(subagent_dir):
        for f in os.listdir(subagent_dir):
            if f.endswith(".jsonl"):
                sub = analyze_jsonl(os.path.join(subagent_dir, f))
                for model, usage in sub.items():
                    if model not in results:
                        results[model] = usage
                    else:
                        for k in usage:
                            results[model][k] += usage[k]

    # 輸出格式對齊 /cost 的 formatTotalCost()
    total_cost = sum(m["cost"] for m in results.values())
    print(f"Total cost:  ${total_cost:.4f}")
    print(f"Usage by model:")
    for model, u in sorted(results.items()):
        print(f"  {model:>21}: {u['input']:>8,} input, {u['output']:>8,} output, "
              f"{u['cache_r']:>8,} cache read, {u['cache_w']:>8,} cache write "
              f"(${u['cost']:.4f})")

    return results

# 使用範例
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python analyze_session.py <path-to-jsonl>")
        sys.exit(1)
    results = analyze_jsonl(sys.argv[1])
    total_cost = sum(m["cost"] for m in results.values())
    print(f"\nTotal cost: ${total_cost:.4f}")
    for model, u in sorted(results.items()):
        print(f"  {model:>21}: {u['input']:>8,} in, {u['output']:>8,} out, "
              f"{u['cache_r']:>8,} cr, {u['cache_w']:>8,} cw (${u['cost']:.4f})")
```

---

## 實驗結果

### 實驗環境

- Session JSONL：`~/.claude/projects/-Users-swchen-tw-git-claude-code/f3e6c061-e79c-492b-885c-7294030476f5.jsonl`
- 模型：claude-opus-4-6（standard speed）
- Session 類型：一般開發對話

### 統計數據

| 指標 | 數值 |
|------|------|
| 總 assistant messages（帶 usage） | 80 行 |
| 唯一 API 呼叫（unique message.id） | 37 次 |
| 產生重複 entries 的 API 呼叫 | 21 次（佔 57%） |
| 重複 entries 的總行數 | 64 行 |
| 所有重複 entries 的最後一條 = 最大 output | 21/21（100%） |

### 天真法 vs 正確法 — 精確對比

| 方法 | cost | input tokens | output tokens |
|------|------|-------------|--------------|
| 天真法（逐行累加） | $7.6107 | 17,358 | 42,756 |
| 正確法（message.id 去重） | $4.0055 | 6,242 | 41,544 |
| **誤差** | **+$3.6053 (+90%)** | **+11,116** | **+1,212** |

> [!warning] 關鍵發現
> Input tokens 的誤差遠大於 output tokens，因為每條重複 entry 都帶有相同的 input/cache token 數（API 呼叫的輸入 context 不變），但 output tokens 只有最後一條是 final。

---

## 對齊檢查表

### 必須處理（否則數字不對）

- [ ] 按 `message.id` 去重，只取每組最後一條（誤差可達 90%）
- [ ] Fast mode 定價：`usage.speed === "fast"` 時用 $30/$150（6 倍差異）
- [ ] Advisor iterations：遍歷 `usage.iterations[]` 中 `type=advisor_message` 的條目
- [ ] 跳過 synthetic：`message.model === "synthetic"` 是內部假訊息

### 容易遺漏（影響完整性）

- [ ] Subagent 檔案：`<sessionId>/subagents/agent-*.jsonl`
- [ ] Model 名稱正規化：`canonicalize()` 統一各種變體名
- [ ] Web search 費用：`$0.01/次`

### 已知差異（無法從 JSONL 補齊）

- [ ] Classifier 費用：`/cost` 不含，JSONL 也不含
- [ ] Token estimation：本地粗估，不入 JSONL
- [ ] Compaction API call：有入 JSONL（可正常計算）

---

## 涉及的核心檔案清單

| 檔案路徑 | 用途 | 關鍵函式 |
|---------|------|---------|
| `src/utils/modelCost.ts` | 定價表與計費公式 | `calculateUSDCost()`, `tokensToUSDCost()`, `getModelCosts()` |
| `src/utils/tokens.ts` | Token 提取與估算 | `getTokenUsage()`, `tokenCountWithEstimation()`, `getCurrentUsage()` |
| `src/cost-tracker.ts` | Session 費用追蹤 | `addToTotalSessionCost()`, `formatTotalCost()`, `saveCurrentSessionCosts()` |
| `src/bootstrap/state.ts` | 全局狀態管理 | `getTotalCostUSD()`, `getTotalInputTokens()`, `addToTotalCostState()` |
| `src/services/api/claude.ts` | API client streaming | `message_delta` 處理, `updateUsage()` |
| `src/utils/sessionStorage.ts` | JSONL 讀寫 | `insertMessageChain()`, `appendEntryToFile()`, `loadTranscriptFile()` |
| `src/utils/stats.ts` | 歷史統計分析 | `processSessionFiles()`, `aggregateClaudeCodeStats()` |
| `src/services/tokenEstimation.ts` | Token 估算 | `roughTokenCountEstimation()`, `countMessagesTokensWithAPI()` |
| `src/utils/advisor.ts` | Advisor 子用量 | `getAdvisorUsage()` |
| `src/components/StatusLine.tsx` | 狀態列顯示 | cost, context_window 資料組裝 |

---

## 我的心得（My Takeaways）

1. **Token 計數的「伺服器權威」模式值得學習** — 不在本地做 tokenization，直接信任 API 回傳的數字。這避免了本地 tokenizer 版本不一致的問題。
2. **JSONL 不存計算結果（費用），只存原始數據（token 數）是好的設計** — 允許定價表更新後重新計算。
3. **Streaming 的非同步性是隱藏陷阱** — 一次 API 呼叫產生多條 JSONL 行，且各行的 usage 狀態不同（partial vs final），這在事後分析時極易出錯。
4. **message.id 是去重的關鍵** — 所有從同一次 API 回應拆分出來的 assistant 行共享相同的 `message.id`。
5. **雙重定價機制** — Opus 4.6 的 fast mode 6 倍定價，提醒我在成本估算時不能假設同一模型只有一種價格。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | Token 四分類（input/output/cache_write/cache_read）、6 個定價層級、JSONL 中 usage 的 JSON path（`.message.usage.input_tokens`）、`message.id` 用於去重 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | `/cost` 讀取的是記憶體中的 STATE 累計值；JSONL 不存費用只存 token 數；streaming 的 content_block_stop 先於 message_delta，導致 JSONL 中早期行的 usage 是 partial；Opus 4.6 的定價不只看模型名，還看 `speed` 欄位 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | stats.ts 的事後分析**不處理**去重和 advisor，因此其數字可能與 `/cost` 不同；classifier 費用是「帳單存在但 /cost 不追蹤」的已知 gap；JSONL 的 mutation 寫入依賴 JavaScript 的物件引用語義，在其他語言中可能無法直接重現 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | ① 立即可用：將本文的 Python 腳本存為 `analyze_session.py`，對所有歷史 session 跑一次成本報表；② 將定價表做成獨立 config，定期從 Anthropic 官網同步更新；③ 在團隊 dashboard 中加入 per-session 和 per-model 的費用趨勢圖 |
| **評估（主動）** | 判斷多個方案的優劣 | 「不存費用」的設計在定價更新時有優勢，但增加了事後分析的複雜度；如果 JSONL 同時存 cost，可以減少分析端的陷阱但犧牲歷史重算能力。streaming 的 partial usage 寫入設計是為了即時性（crash recovery），但代價是分析複雜度。權衡後，原設計合理——crash recovery 比分析便利性更重要 |

### 分析型追問（Socratic Follow-up）

- **澄清**：`usage.iterations` 中除了 `advisor_message` 還有哪些 type？它們的 token 是否也應計入費用？
- **假設**：本文假設 Anthropic 的計費與 `usage` 回傳的數字完全一致。如果 API 計費系統有延遲或捨入差異，JSONL 分析的結果會偏離實際帳單多少？
- **證據**：90% 的誤差數字來自單一 session 的實測。在不同使用模式（純對話 vs 重度工具使用）下，誤差率是否一致？
- **觀點**：如果站在「JSONL 應該也存 cost」的立場，最有力的論據是什麼？（降低分析門檻、減少計算錯誤風險）
- **後果**：如果 Anthropic 更新定價但使用者的分析腳本沒有同步，12 個月後累計的費用報表會有多大偏差？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 定價表硬編碼在分析腳本中。如果 Anthropic 調價（歷史上已發生多次），腳本算出的數字就是錯的。建議將定價表獨立為 JSON config，並記錄每個價格的生效日期。
2. **什麼情況下會失敗？** — ① 新模型上線但未加入 canonicalize() 的映射表；② JSONL 格式變更（新增欄位或改變 nesting）；③ 巨大 session（數 GB 的 JSONL）導致 Python 腳本記憶體溢出（需改用串流處理）。
3. **有沒有更好的替代方案？** — 直接讀取 Anthropic API 的 billing dashboard 或 usage API（如果有）是更權威的方式，但目前 Claude Code 的帳單 API 不對外開放。另一個方案是在 Claude Code 的 hook 系統中攔截 API 回應，即時將 cost 寫入獨立的 CSV/SQLite，避免事後從 JSONL 重建。

---

## 待補充（Open Questions）

- `usage.iterations` 中除了 `advisor_message` 是否還有其他 type，如何影響費用計算？建議搜尋 `iterations type` 或追蹤 Anthropic API changelog
- Anthropic 的實際帳單計費粒度與 `usage` 回傳的數字之間是否有捨入差異？建議比對 API 帳單頁面與 JSONL 分析結果
- `cache_creation.ephemeral_1h_input_tokens` 和 `ephemeral_5m_input_tokens` 的分別對費用有何影響？目前的計費只看 `cache_creation_input_tokens` 總數
- `service_tier` 欄位（如 `"standard"`）是否影響定價？目前的分析忽略了此欄位
- `inference_geo` 欄位是否暗示不同地區有不同定價？
- Compaction（context 壓縮）觸發的 API 呼叫是否使用不同模型（如 Haiku），其費用路徑是否與主對話一致？
- 團隊訂閱（Pro/Team/Enterprise）方案是否有不同的 token 計費邏輯？

## 相關連結（Related）

- [[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]] — 本文的計費管線與 OTel 遙測管線共享 `costCounter` 和 `tokenCounter`，是同一個 state 物件的兩個面向
- [[2026-04-17-CLAUDE-CODE-FEEDBACK-FRUSTRATION-DETECTION-EVENTMETADATA-ARCHITECTURE]] — EventMetadata 傳送架構中的 analytics 事件包含 `cost_usd_micros` 欄位，是另一個費用數據來源
- [[2026-01-22-THE-LONGFORM-GUIDE-TO-EVERYTHING-CLAUDE-CODE]] — Token 經濟學章節涵蓋了使用者視角的成本優化策略（cache hit 最大化、context window 管理）
- [[2026-01-24-CLAUDE-CODE-HOOKS-CODE-ANALYSIS]] — Hook 系統可用於即時攔截 API 回應並建構獨立的費用追蹤管線
- [[2026-04-02-CLAUDE-CODE-ISSUE-42796-EXTENDED-THINKING-REGRESSION]] — 品質退化導致 API 成本從 $345 暴增至 $42,121（122 倍），是成本異常的實際案例
- [[2026-04-10-CLAUDE-SESSION-ANALYZER-CODE-ANALYSIS]] — 開源的 Session 分析工具，含 Bedrock Opus 成本估算模組

## References

- [Anthropic 官方定價頁面](https://platform.claude.com/docs/en/about-claude/pricing)
- [Claude Code 反編譯原始碼 — src/utils/modelCost.ts](conversation research)
- [Claude Code 反編譯原始碼 — src/cost-tracker.ts](conversation research)
- [Claude Code 反編譯原始碼 — src/utils/tokens.ts](conversation research)
