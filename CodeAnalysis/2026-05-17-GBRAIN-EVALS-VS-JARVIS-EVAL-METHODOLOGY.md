---
title: "gbrain 與 gbrain-evals — AI Agent Eval 方法論深度研究與 Jarvis Integration Test 對照"
date: 2026-05-17
category: CodeAnalysis
tags:
  - ai/agent-eval
  - ai/llm-as-judge
  - methodology/benchmark
  - tools/eval-framework
  - reference/jarvis-integration-test
source: "https://github.com/anthropic/gbrain + gbrain-evals（本地分析 /Users/swchen.tw/git/gbrain_set/）"
source_type: code
author: "Anthropic / gbrain team"
status: notes
links:
  - "[[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]]"
  - "[[2026-04-10-CLAUDE-SESSION-ANALYZER-CODE-ANALYSIS]]"
  - "[[2026-04-24-CLAUDE-MEM-V12-PERSISTENT-MEMORY-PLUGIN-DEEP-DIVE]]"
  - "[[2026-03-07-CLAUDE-MEMORY-ENGINE]]"
  - "[[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]]"
  - "[[2026-03-29-CONNSYS-JARVIS-OPENCLAW-NATIVE-PLUGIN-DESIGN]]"
  - "[[2025-08-31-CLAUDE-MEM-CODE-ANALYSIS]]"
  - "[[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]]"
github_stars: "private"
github_language: TypeScript
---

## 摘要（Summary）

`gbrain` 是 Anthropic 為 AI agent 設計的**個人知識大腦系統**（Personal Knowledge Brain），底層用 PGLite（Postgres + pgvector 嵌入式版）+ 混合檢索（Hybrid Search：keyword + vector + RRF）+ 自動知識圖譜（Knowledge Graph），對外提供 CLI / MCP server / Admin SPA 三介面，給 OpenClaw、Hermes 等 agent 平台當長期記憶（Long-term Memory）層。

更重要的是 `gbrain-evals` — 一個**獨立的公開評估倉庫**，跑 BrainBench（內部 12 Category 評估）與 LongMemEval（公開基準）。它代表了當前 AI agent eval 方法論演進的一個成熟範例：**Sealed qrels**（封閉真值集）、**Multi-adapter baseline**（多實作對照）、**LLM-as-judge with structured evidence**（結構化證據評審）、**NDJSON streaming + worker sharding**（流式輸出與分片並行）、**Content-addressed embedding cache**（內容定址快取）、**Spec-first 12-section report templates**（先寫骨架後跑數字）。

本研究是針對使用者自家「Connsys Jarvis Integration Test」做對照學習用，最後一節提供具體的可借鏡 backlog（三步走實施計畫）。

## Why — 為什麼存在？

> AI agent 的評估方法論還在演進，社群沒有公認標準。gbrain-evals 是少數同時跨「retrieval 確定性指標 + LLM-as-judge 主觀評分 + 對抗測試 + 跨系統公開比較」四個維度的成熟範例。

### gbrain 本體存在的理由

- **核心動機**：AI agent 很聰明但容易遺忘。需要一個能跨會議 / 郵件 / Twitter / 語音的整合性長期記憶層，且自動連結、自動濃縮、自動知識圖譜，不要每次都靠 LLM 重做。
- **取代/改善什麼**：純向量 RAG 在「跨時間、跨來源的個人知識」場景效果差。gbrain 加上知識圖層（Knowledge Graph）+ source-aware 排名 + 自動 link 抽取（零 LLM call），把 P@5 拉到 49.1%，R@5 到 97.9%。
- **目標用戶**：OpenClaw、Hermes 等 agent 平台開發者；想自架個人知識系統的開發者；做 Memory-augmented LLM 研究者。

### gbrain-evals 分倉的理由（依 README 第 28-38 行）

> 基準語料（~4MB）不該被倒入每個 gbrain 使用者的安裝裡。`gbrain-evals` 是「想跑 BrainBench 時才克隆」的東西，不是「想用 gbrain 當大腦時」克隆的。

三項工程收益：

1. **單向依賴（One-way Dependency）**：`gbrain-evals/package.json` 透過 GitHub URL 拉 `gbrain` 當 library（或本機 `bun link`）。eval → product 是單向、清晰的。
2. **獨立演進速度（Independent Velocity）**：gbrain 核心保持輕量（`docs/ethos/THIN_HARNESS_FAT_SKILLS.md` 的設計哲學）。Adapter、語料、新基準在 eval 倉快速迭代，不會膨脹主產品。
3. **強制清晰 API 邊界（Forced API Boundary）**：eval 倉只能用 gbrain 的公開 subpath exports（`pglite-engine`、`operations`、`link-extraction`、`embedding`、`search/vector-grep-rrf-fusion` …），結構上禁止 eval 程式碼蔓入私有實作細節。

## What — 是什麼？

### 主要功能

#### gbrain 本體

- **CLI**：`gbrain sync / import / search / dream / doctor` 等
- **MCP server**（Model Context Protocol，stdio + HTTP+OAuth 2.1）
- **React 19 Admin SPA**（嵌入二進位 65KB gzip）
- **29 個 Fat-Markdown Skills**（定義 WHEN+HOW+WHAT 工作流）
- **18 個整合食譜（Recipes）**：email-to-brain、x-to-brain、meeting-ingestion 等
- **Minions Job Queue**：Postgres-native 背景工作佇列

#### gbrain-evals

- **BrainBench**：12 個 Category 內部基準（retrieval / ingestion / provenance / skill compliance / workflows / multimodal 等）
- **LongMemEval `_s` split**：500 題公開基準，與 MemPalace、Hindsight、Stella、Contriever 等對標
- **4 個 reference adapter**：grep-only / vector / vector-grep-rrf-fusion / gbrain（多實作對照）
- **6 個 JSON Schema 契約**：corpus-manifest / public-probe / evidence-contract / scorecard / tool-schema / transcript

### 不做什麼（Non-goals）

- **gbrain 不是雲端 SaaS**：本地優先（local-first），無雲端鎖定（no cloud lock-in）
- **gbrain-evals 不評估 QA accuracy**：只評 retrieval recall。QA 對錯交給其他系統發布的 QA judge
- **gbrain-evals 不做 prompt engineering 自動最佳化**：人工編寫 prompt，evals 只測效果

### 技術棧（Tech Stack）

| 層 | 技術 |
|---|---|
| 嵌入式 DB | `@electric-sql/pglite 0.4.3`（Postgres 17.5 via WASM） |
| Scale-out DB | Postgres + `pgvector 0.2.0`（Supabase 相容） |
| LLM SDK | `anthropic 0.30.0`、`ai 6.0.168` |
| MCP | `@modelcontextprotocol/sdk 1.29.0` |
| HTTP | Express 5.1.0 |
| 程式碼分塊 | `tree-sitter-wasm 0.22.6` |
| Admin UI | React 19 |
| Runtime | Bun |

## How — 如何運作？

### 系統架構圖（System Architecture）— gbrain

```
┌─────────────────────────────────────────────────────────────┐
│  Agent Platform (OpenClaw / Hermes / Claude Code)           │
│  ├─ 讀 skills/RESOLVER.md 路由表決策                          │
│  └─ 透過 MCP / CLI 呼叫 gbrain                                │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │       gbrain (TypeScript + Bun) │
        │  ┌──────────────────────────┐   │
        │  │  CLI commands            │   │
        │  │  (sync/import/doctor/    │   │
        │  │   dream/eval-*)          │   │
        │  └──────────────────────────┘   │
        │  ┌──────────────────────────┐   │
        │  │  MCP server              │   │
        │  │  (stdio + HTTP+OAuth)    │   │
        │  └──────────────────────────┘   │
        │  ┌──────────────────────────┐   │
        │  │  Core (operations.ts:    │   │
        │  │   47 shared ops)         │   │
        │  │  ┌──────┐ ┌──────────┐   │   │
        │  │  │Search│ │ Minions  │   │   │
        │  │  │Hybrid│ │ Job Queue│   │   │
        │  │  └──────┘ └──────────┘   │   │
        │  │  ┌──────────────────┐    │   │
        │  │  │ Cycle (9-stage   │    │   │
        │  │  │  maintenance)    │    │   │
        │  │  └──────────────────┘    │   │
        │  └──────────────────────────┘   │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │   Storage Layer (BrainEngine)   │
        │  ┌──────────┐    ┌────────────┐ │
        │  │ PGLite   │ or │ Postgres + │ │
        │  │ (WASM)   │    │  pgvector  │ │
        │  │ default  │    │  (scale)   │ │
        │  └──────────┘    └────────────┘ │
        └─────────────────────────────────┘
```

### 系統架構圖（System Architecture）— gbrain-evals

```
┌─────────────────────────────────────────────────────────────┐
│  gbrain-evals (獨立倉庫，via GitHub URL pin)                  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  CLI: bun run eval:run / eval:brainbench               │ │
│  └─────────────────────┬──────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼──────────────────────────────────┐ │
│  │  Runner Layer                                          │ │
│  │  ┌──────────────────┐  ┌──────────────────┐            │ │
│  │  │ multi-adapter.ts │  │ longmemeval.ts   │            │ │
│  │  │ (BrainBench)     │  │ (公開基準, 1800L)  │            │ │
│  │  └─────────┬────────┘  └────────┬─────────┘            │ │
│  │            │                    │                       │ │
│  │  ┌─────────▼────────────────────▼─────────┐            │ │
│  │  │  4 Reference Adapters (對照組)          │            │ │
│  │  │  grep-only / vector / RRF / gbrain     │            │ │
│  │  └────────────────────────────────────────┘            │ │
│  │  ┌────────────────────────────────────────┐            │ │
│  │  │  judge.ts (LLM-as-Judge, Haiku 4.5)    │            │ │
│  │  │  + tool-use 強制 JSON                    │            │ │
│  │  └────────────────────────────────────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Data Layer                                            │ │
│  │  ├─ world-v1/      240 頁合成傳記                       │ │
│  │  ├─ amara-life-v1/ inbox/slack/cal/notes               │ │
│  │  ├─ gold/          sealed qrels + poison.json          │ │
│  │  └─ longmemeval/embed-cache/  SHA-256 內容定址快取      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Output                                                │ │
│  │  ├─ NDJSON streaming (per-question append, resume)    │ │
│  │  ├─ JSON scorecard                                     │ │
│  │  ├─ Markdown report (CLAUDE.md 強制 12 節模板)          │ │
│  │  └─ SVG charts (純手寫，內聯 GitHub 渲染)               │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│            ▲                                                 │
│            │ depends-on (via GitHub URL)                     │
│            │                                                 │
└────────────┼─────────────────────────────────────────────────┘
             │
       ┌─────┴──────┐
       │   gbrain   │
       │  (library) │
       └────────────┘
```

### 執行流程圖（Execution Flowchart）— READ-ENRICH-WRITE 迴圈

```
 Signal (會議轉錄 / 郵件 / Twitter / 語音)
   │
   ▼
[Signal Detector] ── 平行擷取「想法」+「實體」（非阻塞）
   │
   ▼
[Brain-ops: 查大腦] ── gbrain search / get
   │
   ▼
[用完整上下文回應]
   │
   ▼
[Write: 更新頁面 + 引用來源]
   │
   ▼
[Auto-link] ── 零 LLM 呼叫，自動抽類型化關係
   │
   ▼
[Sync: 索引化變更，供下次查詢]
   │
   ▼
 End
```

### 時序圖（Sequence Diagram）— gbrain-evals 單一 case 生命週期

```
 Runner          Adapter         Engine            Cache         Judge (Haiku)
   │                │              │                 │                │
   │─loadCorpus()──►│              │                 │                │
   │  RichPage[]    │              │                 │                │
   │  with _facts   │              │                 │                │
   │                │              │                 │                │
   │─sanitizePage()─►              │                 │                │
   │  PublicPage[]  │              │                 │                │
   │   (gold 移除)  │              │                 │                │
   │                │              │                 │                │
   │─init(pages)───►│─create()────►│                 │                │
   │                │  PGLite      │                 │                │
   │                │              │                 │                │
   │                │─embed()──────────────────────►│                │
   │                │              │                 │ hash(text)     │
   │                │              │                 │ → SHA-256      │
   │                │              │              ┌──┴──┐             │
   │                │              │              │ hit?│             │
   │                │              │              └──┬──┘             │
   │                │              │   ◄──cached────│                │
   │                │              │                 │                │
   │                │              │   或 OpenAI API──►│ cost          │
   │                │              │   ◄──vector────│ +$0.001        │
   │                │              │              put(text,vec)       │
   │                │              │                 │                │
   │─query(q)──────►│─hybridSearch►│                 │                │
   │                │              │ ┌──RRF fusion─┐ │                │
   │                │              │ │ keyword ∪    │ │                │
   │                │              │ │ vector ∪     │ │                │
   │                │              │ │ source-boost │ │                │
   │                │              │ └─────────────┘ │                │
   │                │  RankedDoc[] │                 │                │
   │ ◄──RankedDoc[]─│              │                 │                │
   │                │              │                 │                │
   │─precisionAtK() │              │                 │                │
   │─recallAtK()    │              │                 │                │
   │                │              │                 │                │
   │ (若 Cat 9)     │              │                 │                │
   │─buildEvidence()│              │                 │                │
   │  (XML evidence)│              │                 │                │
   │──────────────────────────────────────────────────►│ tool: score_  │
   │                │              │                 │  answer()      │
   │ ◄──JudgeResult────────────────────────────────────│                │
   │  verdict/scores│              │                 │                │
   │                │              │                 │                │
   │─NDJSON append──►(file)        │                 │                │
   │  resume-safe   │              │                 │                │
   │                │              │                 │                │
   │─teardown()────►│─close()─────►│                 │                │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 七個結構性設計，每個都解決一個常見的 eval 反模式（anti-pattern）

1. **倉庫分離（Repo Separation）** — eval 倉透過 GitHub URL 依賴主產品。**反模式**：eval 程式碼蔓入主倉造成依賴反轉、語料污染使用者安裝。
2. **Sealed qrels（封閉真值集）** — Adapter 結構上拿不到 `_facts` / `gold`。**反模式**：Adapter 偷看 gold 取得分數，迴歸測試不可信。
3. **Multi-adapter 對照組（Reference Baselines）** — 同題 4 個實作並排跑。**反模式**：只看絕對數字而看不出「是新功能進步還是評測本身漂移」。
4. **LLM-as-Judge with Structured Evidence** — Judge 看 XML evidence（不看原始 tool output）。**反模式**：Judge 被 prompt-injection 污染、被 noise 干擾。
5. **不是所有事都丟 LLM** — Cat 5 用 classify、Cat 8 純指標、Cat 9 才用 rubric judge。**反模式**：「能用 LLM 解決的都丟 LLM」造成成本爆炸且不可重現。
6. **NDJSON streaming + Worker sharding** — Per-question append、`i % N === workerId`。**反模式**：長跑 crash 重來、無法分散式執行。
7. **Spec-first Report Templates** — 先寫 12 節 placeholder 才開始跑數字。**反模式**：跑完數字才開始想「這個 benchmark 到底要回答什麼」。

### 資料流（Data Flow）— 一題完整經過

```
1. loadQuestions() 從 HuggingFace JSON 讀 500 題
2. EmbeddingCache.get(text)：SHA-256 內容定址檢查
3. adapter.init(sanitizePage(pages))：建內部索引（PGLite + HNSW），看不到 _facts
4. adapter.query(sanitizeQuery(q))：看不到 q.gold，回傳 RankedDoc[]
5. recallAtK(results, gold.answer_session_ids, k=5)：runner 用 gold 評分（adapter 拿不到）
6. NDJSON append：per-question 一行，可中斷 resume
7. longmemeval-aggregate.ts：聚合 + markdown report + SVG chart
```

### 關鍵程式碼（Key Code Snippets）

**Adapter 介面（`gbrain-evals/eval/runner/types.ts:209-248`）**

```ts
interface Adapter {
  readonly name: string
  init(rawPages: Page[], config: AdapterConfig): Promise<BrainState>
  query(q: Query, state: BrainState): Promise<RankedDoc[]>
  teardown?(state: BrainState): Promise<void>
  snapshot?(state: BrainState): Promise<string>
  getPoisonDisposition?(state: BrainState): Record<string, PoisonDisposition>
}
```

**Sealed qrels 型別系統強制（`types.ts:44-64`, `117-145`）**

```ts
type PublicPage = Pick<Page, 'slug' | 'type' | 'title' | 'compiled_truth' | 'timeline'>
type PublicQuery = Omit<Query, 'gold'>

// multi-adapter.ts:338, 345
const sealed = pages.map(sanitizePage)   // 結構上去掉 _facts
await adapter.init(sealed, config)

const cleanQuery = sanitizeQuery(q)       // 結構上去掉 gold
const results = await adapter.query(cleanQuery, state)
```

**評分函式（`types.ts:258-273`）— 注意 P 跟 R 的分母不同**

```ts
function precisionAtK(docs: RankedDoc[], relevant: Set<string>, k: number): number {
  const topDocs = topK(docs, k)
  if (topDocs.length === 0) return 0
  let hits = 0
  for (const d of topDocs) if (relevant.has(d.page_id)) hits++
  return hits / topDocs.length         // 分母 = topDocs 長度（已截斷）
}

function recallAtK(docs: RankedDoc[], relevant: Set<string>, k: number): number {
  if (relevant.size === 0) return 0
  const topDocs = topK(docs, k)
  let hits = 0
  for (const d of topDocs) if (relevant.has(d.page_id)) hits++
  return hits / relevant.size          // 分母 = 相關集合大小，不是 K
}
```

**LLM-as-Judge system prompt（`judge.ts:115-125`）**

```
You grade an agent's answer against a rubric for BrainBench. Use ONLY the
ground_truth_pages as the world-of-facts. Anything in final_answer_text not
grounded in ground_truth_pages is a hallucination and must lose points.

Score each rubric criterion 0-5 where:
  5 = fully satisfied
  3-4 = mostly satisfied with minor gaps
  1-2 = partially satisfied, significant gaps or hedging
  0 = absent, contradicted by ground truth, or hallucinated

Be terse in each rationale. One sentence per criterion.
Return your scores via the score_answer tool. Do not reply with plain text.
```

**Tool-use 強制結構化輸出（`judge.ts:137-161`）**

```ts
{
  name: 'score_answer',
  input_schema: {
    type: 'object',
    properties: {
      scores: {
        type: 'array',
        items: {
          criterion_id: { type: 'string' },
          score: { type: 'number', minimum: 0, maximum: 5 },
          rationale: { type: 'string' }
        }
      },
      verdict: { enum: ['pass', 'partial', 'fail'] },
      overall_rationale: { type: 'string' }
    }
  }
}
```

**JudgeEvidence 結構（`cat9-workflows.ts:137-171`，**最重要**）**

```ts
{
  schema_version: 1,
  probe: { id, query, category: 9 },
  final_answer_text: runResult.final_answer,
  evidence_refs: runResult.evidence_refs,
  tool_call_summary: {
    count_by_tool: { read_page: 5, list_entities: 2 },
    saw_poison_items: [...],                              // bridge 計算，非 agent 自報
    brain_first_ordering: 'brain_before_answer' | 'answer_before_brain',
    made_dry_run_writes: [{ slug, has_back_links, has_citation_format }]
  },
  ground_truth_pages,                                     // judge 的「事實世界」
  rubric: scenario.rubric                                 // [{id, weight}, ...]
}
```

> [!important] **關鍵安全邊界**
> Judge **從不**讀原始 tool output、**從不**讀 poison 文本內容。`saw_poison_items: ["poison-001"]` 足以判定 agent 是否中招，但 prompt-injection 的注入文字永遠不會進到 judge 的 context window。

**Verdict 規則（`judge.ts:238-258`）**

```ts
const PASS_THRESHOLD    = 3.5
const PARTIAL_THRESHOLD = 2.5

verdict = overall ≥ 3.5 ? 'pass'
        : overall ≥ 2.5 ? 'partial'
        : 'fail'
```

**Embedding cache schema（`longmemeval-cache.ts:45-54`）**

```sql
CREATE TABLE embeddings (
  model TEXT NOT NULL,         -- e.g. "text-embedding-3-large@1536"
  text_hash TEXT NOT NULL,     -- SHA-256(text) hex
  vector BLOB NOT NULL,        -- Float32 little-endian
  dims INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (model, text_hash)
)
```

**NDJSON resume 模式（`longmemeval.ts:485-486`）**

```ts
const row = {
  question_id, question_type,
  retrieved: string[],
  ground_truth: string[],
  hit_at_k: boolean,
  num_haystack, latency_ms
}
appendFileSync(ndjsonPath, JSON.stringify({ adapter, ...row }) + '\n')

// resume：
const seen = new Set<string>()
for (const line of existing.split('\n')) {
  const o = JSON.parse(line)
  seen.add(`${o.adapter}::${o.question_id}`)
}
// 跳過 seen 裡的 case
```

## 評估方法論演進史（Methodology Evolution）

從 `gbrain-evals/docs/benchmarks/` 13 份報告（2026-04-18 → 2026-05-07），看得到四個演進階段：

### 階段 1（2026-04-18 ~ 04-19）：內部基準起點

- `2026-04-18-brainbench-v1.md` — 240 頁 world-v1 語料，BrainBench 第一版
- `2026-04-19-brainbench-multi-adapter.md` — **關鍵轉折：引入 multi-adapter 對照**
- `2026-04-19-brainbench-v0_11-vs-v0_12.md` — A/B 比版本，證實知識圖層 vs 純 RAG 增益

> 第一版主要回答：「我們的知識圖層真的有幫助嗎？」結論：P@5 +31pt，是的。

### 階段 2（2026-04-23 ~ 04-25）：分類細化

- `2026-04-23-brainbench-cat13-conceptual.md`
- `2026-04-23-brainbench-v0.20.0.md` — 12 Cat 完整套件
- `2026-04-25-brainbench-cat13b-source-swamp.md` — source boost 專項

> 從單一全域數字 → 12 個 Category 分層。每層測不同程式碼路徑。

### 階段 3（2026-05-07）：跨出公開比較

- `2026-05-07-longmemeval-s.md` — **首度對標公開基準**

LongMemEval `_s` split 500 題，gbrain-hybrid R@5 = **97.60%**，比 MemPalace 96.6% 高 1pt，且**檢索迴圈中無 LLM**。重要的是這份報告**誠實揭露兩個負面結果**：

- **Query expansion 是零結果**：97.60% 開或關都一樣 → 預設關掉
- **時間推理輸 1.5pp**：根因是嵌入模型不攜帶排序信號 → 申報為 v0.29 後續工作但未啟動

> 這種「故意限制文件（documented limitations）」是方法論成熟的標誌。不是「我們很棒」，是「以下是我們知道的、不知道的、計劃學的」。

### 階段 4（同時推進）：多模型協作觀察

- `2026-04-18-minions-vs-openclaw-production.md` 與 `subagents.md` — minions job queue vs openclaw subagent 對比
- `2026-04-19-knowledge-runtime-v0.13.md` — runtime 整合
- `2026-04-18-tweet-ingestion.md` — 攝取管線專項

## 設計哲學：THIN HARNESS, FAT SKILLS

`docs/ethos/THIN_HARNESS_FAT_SKILLS.md` 對 eval 設計有三個直接影響：

1. **Skill 是參數化程序（不是 prompt）** — 相同 skill 不同參數產生不同行為。對應到 eval：**相同 runner 用不同 adapter 跑就產生不同見解**。每個 adapter 是一個 skill call。
2. **潛在 vs 確定性步驟分離（Latent vs Deterministic）** — SQL / RRF / HNSW 是確定性的，model judgment / synthesis 是潛在的。對應到 eval：**檢索層用確定性 P@K/R@K，agent/judge 層才用 LLM**。Query expansion 被測試後發現沒加值 → 預設關掉。
3. **Diarization（read 50, write 1）** — 對應 eval：不發佈單一全域數字，發佈**按 question_type 分解的 breakdown**，從模式看故事。

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可重現性（Reproducibility） | ⭐⭐⭐⭐⭐ | Seeded PRNG、N runs、stddev 報告；receipt header 含 prompt_hash + harness_sha |
| 可審計性（Auditability） | ⭐⭐⭐⭐⭐ | 三年後仍能驗證「某天 Opus 為什麼拿 98.3%」 |
| 安全邊界（Security Boundary） | ⭐⭐⭐⭐⭐ | Sealed qrels 結構強制 + judge 不讀 poison 文本（prompt-injection 防線） |
| 成本控制（Cost Control） | ⭐⭐⭐⭐ | Embedding cache 首跑 $2 之後 $0；judge 並發 token bucket |
| 開放性（Openness） | ⭐⭐⭐⭐⭐ | 誠實揭露零結果與已知弱點；對標 MemPalace/Hindsight/Stella 真實數字 |
| 可擴展性（Extensibility） | ⭐⭐⭐⭐ | Adapter interface 乾淨；新基準新增一個 runner 檔即可 |
| 文件品質（Documentation） | ⭐⭐⭐⭐ | CLAUDE.md 強制 12 節報告模板；docs/ethos/ 哲學論文 |

> [!tip] 值得學習的設計
> 「**Spec-first benchmark report**」是這個專案最容易被忽略但最重要的文化：先寫 `docs/benchmarks/<date>-<slug>.md` 12 節骨架全 `[pending]`，再開始跑數字。這強迫先想清楚「這個 benchmark 到底要回答什麼問題」，避免「跑完數字才發現方向錯了」。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷與技術債

- **Sealed qrels 是軟實施**：型別系統強制，但 adapter 內部仍可從 `compiled_truth` 文本推測。README 註明 v2 計畫上 WASM sandbox 做硬實施。
- **無 CI 流程**：solo repo 直接 commit main，無 PR review、無自動化 regression bot。Scale up 後是隱憂。
- **LongMemEval 只測 retrieval**：QA accuracy 沒測（讓 user model 寫答案的能力）。報告誠實標註但未補上。
- **時間推理 1.5pp 落後 MemPalace**：已知問題，根因是嵌入模型不攜帶排序信號，但「申報為 v0.29 後續工作」目前未啟動。
- **Cost 透明但仍高**：BrainBench 全量 ~$100，smoke ~$22。對個人開發者門檻不低。

### 🔮 改進建議（Improvement Suggestions）

1. **加 CI / GitHub Actions** — 自動跑 smoke（`BRAINBENCH_N=1`），PR 比較數字
2. **WASM sandbox sealed qrels** — 從軟實施升級到硬實施
3. **補 QA judge** — 對 LongMemEval 跑 published QA evaluator，補上「retrieval recall ≠ QA accuracy」這層
4. **時間線 → 排名器整合** — 解決 v0.29 申報的時間推理弱點

## 效能基準（Benchmark）

### LongMemEval `_s` split 跨系統比較（2026-05-07）

| System | R@5 | k | n | LLM in retrieval loop | Source |
|---|---|---|---|---|---|
| **gbrain-hybrid+expansion** | **97.60%** | 5 | 500 | Yes (Haiku) | gbrain-evals 2026-05-07 |
| **gbrain-hybrid** | **97.60%** | 5 | 500 | **No** | gbrain-evals 2026-05-07 |
| **gbrain-vector** | 97.40% | 5 | 500 | No | gbrain-evals 2026-05-07 |
| MemPalace v3 | 96.6% | 5 | 500 | Yes | MemPalace paper |
| Hindsight | ~94% | 5 | 500 | Yes | Hindsight paper |
| BM25 baseline | ~70% | 5 | 500 | No | published baselines |

**關鍵發現**：
- gbrain-hybrid 不靠 LLM 就達到 97.60%，**檢索成本顯著低於同等級對手**
- Query expansion 開關**無差別** → gbrain-evals 預設關掉
- temporal-reasoning question type 落後 MemPalace 1.5pp（已知弱點）

### BrainBench v0.20.0 內部基準（2026-04-23）

| Adapter | P@5 | R@5 |
|---|---|---|
| **gbrain** | **49.1%** | **97.9%** |
| vector-grep-rrf-fusion | 17.7% | 90.0% |
| vector-only | 12.3% | 85.1% |
| grep-only | 5.2% | 65.3% |

> **+31pt P@5 over RRF baseline**：證實知識圖層（auto-link extraction + source boost）是負載軸承的，不是 marginal optimization。

### Cost & Latency

| 場景 | 成本 | 時間 |
|---|---|---|
| LongMemEval 首跑（cold embedding cache） | ~$2 | ~30 分鐘 |
| LongMemEval 後續跑（warm cache） | **~$0** | ~5 分鐘 |
| BrainBench 12 Cat 全量 | ~$100 | ~3 小時 |
| BrainBench smoke（N=1） | ~$22 | ~30 分鐘 |
| Judge per-call（Haiku 4.5） | $1-2 (per million tokens) | ~3 秒 |

## 快速上手（Quick Start）

```bash
# 1. Clone 兩個 repo
git clone https://github.com/anthropic/gbrain ~/git/gbrain
git clone https://github.com/anthropic/gbrain-evals ~/git/gbrain-evals

# 2. Link 本機開發
cd ~/git/gbrain && bun link
cd ~/git/gbrain-evals && bun link gbrain && bun install

# 3. Smoke test（BrainBench N=1）
bun run eval:run:dev                       # 約 3 分鐘
# 或 LongMemEval --stratify 10 快速測
bun eval/runner/longmemeval.ts --stratify 10

# 4. 全量 LongMemEval（3 worker 並行）
bash eval/runner/longmemeval-batch.sh

# 5. 看結果
ls docs/benchmarks/
cat eval/reports/<slug>/scorecard.json
```

需要的環境變數：

```bash
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...                  # for embedding
export BRAINBENCH_N=1                      # smoke=1, iterate=5, publish=10
export BRAINBENCH_LLM_CONCURRENCY=4        # 並發 judge 槽位
```

---

## 📋 Backlog — Jarvis Integration Test 借鏡實施計畫

> [!important] 本節是這份研究的核心產出。針對使用者自家的 `Connsys Jarvis Integration Test`（路徑：`~/git/workspace_jarvis/connsys-jarvis/tests/`），對照 gbrain-evals 設計給出三步走 backlog。
>
> **核心判斷**：Jarvis 不是 gbrain 的子集，是**正交但互補**的系統。Jarvis 強「多 skill 共存的端到端品質與行為診斷」，gbrain 強「retrieval / agent 任務的多 adapter 對照與可重現基準」。借鏡是補弱（結構化 evidence、可重現性、I/O 容錯），不是換骨。

### Jarvis 已經比 gbrain 強的地方（不要 throw away）

1. **L7 KPI 層**：用 `framework-session-analyzer-tool` 把 session 分析成 K1-5（user-perceived）+ S1-6（system）三檔評級（Good/Warning/Degraded）— gbrain 完全沒這層
2. **行為分類（BehaviorClassifier）**：thinking 內容 + tool pattern → understanding / designing / exploring / implementing / debugging / verifying 六 phase — gbrain 沒這層
3. **Skill 觸發率追蹤**：解 `expert.json` 依賴樹遞迴擴展期望 skill 集合 — gbrain 沒
4. **Expert 故意共存模式**：`--experts A,B` 模擬真實環境 — gbrain 場景不同
5. **完整 Dashboard pipeline**：collector → generator → static site 7 tabs — gbrain 沒
6. **7 層遞進檢查**（L1 規則 → L7 KPI）：比 gbrain 3 層更細

### 三步走實施計畫

#### Step 1（這週，<5 天）— 低成本高收益

| # | 任務 | 工作量 | 借鏡來源 |
|---|---|---|---|
| 1 | `test_cases.json` 加 JSON Schema 驗證 | 0.5 天 | `gbrain-evals/eval/schemas/*.json` 6 個契約 |
| 2 | **L6 judge 改成結構化 evidence**（最值得抄的單一改動） | 1-2 天 | `judge.ts:165-230` 的 `renderEvidenceForJudge` |
| 3 | Receipt header 加入 `.results/{ts}/receipt.json`（prompt_hash / harness_sha / cmd_args） | 0.5 天 | `gbrain/evals/functional-area-resolver/` baseline-runs |

**為什麼這三個優先**：
- 全部都是 **structural** 改動，不動 test case 內容
- JSON Schema 防誤寫（CI 卡 schema fail）
- 結構化 evidence 同時解決 prompt-injection 防線 + judge 穩定性兩個問題
- Receipt header 讓三年後仍能審計「為什麼這個 case 當時 fail」

#### Step 2（下個 sprint，2-4 週）— 三件套基礎設施

| # | 任務 | 工作量 | 借鏡來源 |
|---|---|---|---|
| 4 | NDJSON streaming：所有 case 結果 append 到 `.results/{ts}/all_cases.ndjson`（並存 per-case 結構） | 2-3 天 | `longmemeval.ts:485-486` |
| 5 | Worker-id sharding：CLI `--worker-id N --total-workers M`，結果路徑含 worker ID | 2-3 天 | `longmemeval.ts:76-78, 414-418` |
| 6 | 零成本 rescore：`rescore.py` 用本地邏輯重算 NL / judge score 不重跑 API | 1-2 天 | `gbrain/evals/functional-area-resolver/rescore.mjs` |

**互相依賴的順序**：任務 4 是基礎（原始 LLM output 進 NDJSON），任務 6 依賴任務 4（要有 predicted 才能 rescore）。三個一起做最划算。完成後：分散式執行、prompt 快速迭代、CI 容錯全解決。

#### Step 3（看需要，1+ 月）— 評估後再做

| # | 任務 | 適用條件 |
|---|---|---|
| 7 | Stratified N（多 seed 重複） | 觀察哪些 case 變異大才做，全量重複成本高 |
| 8 | Multi-adapter baseline | 要做模型遷移驗證或新引擎評估時才需要 |
| 9 | Report-as-spec 12 節模板 | 要對外發佈 benchmark 才需要（已有 dashboard 視覺化的話需求弱） |
| 10 | Content-addressed cache | 重複呼叫 LLM 的 case 多時才值得 |

### 反向觀察：gbrain 可從 Jarvis 借鏡的（雙向學習）

1. **L7 KPI 那層分離設計**：「另一個 AI 分析 session 產生 KPI、再餵回 assertion」這個 pipeline 比 gbrain 直接 hardcode 行為指標（Cat 8 brain_first_ordering 等）更靈活
2. **Rubric markdown 化**：Jarvis 的 `rubrics/<ID>_rubric.md` 比 gbrain 的 JSON rubric 更易寫、易 review、易 git diff

### Backlog 完整對照表

| 維度 | Jarvis | gbrain-evals | 借鏡優先序 |
|---|---|---|---|
| 倉庫分離 | ❌ tests/ 在主倉內 | ✅ 獨立倉 | 中（看主倉膨脹程度） |
| Sealed qrels | ⚠️ golden/ 給 judge 看不給 agent 看 | ✅ 型別強制 | 低（風險低） |
| Multi-adapter baseline | ❌ | ✅ 4 個 reference adapter | 低（看需求） |
| NDJSON resume | ❌ | ✅ | **高**（Step 2） |
| Worker sharding | ⚠️ 共用 pool 但無 worker-id 分片 | ✅ | **高**（Step 2） |
| Stratified N（多 seed） | ❌ | ✅ N∈{1,5,10} | 中 |
| Structured judge evidence | ⚠️ judge 看原始 output | ✅ XML evidence | **最高**（Step 1） |
| 多種評分並存 | ✅ L1-L7（比 gbrain 還細） | ✅ classify/指標/judge | 已對齊 |
| Report-as-spec | ⚠️ 結構鬆散 | ✅ 12 節強制 | 低（有 dashboard） |
| Schema-driven 契約 | ❌ test_cases.json 無 schema | ✅ 6 個 JSON Schema | **高**（Step 1） |
| Content-addr cache | ❌ | ✅ SHA-256 | 低 |
| **零成本 rescore** | ❌ | ✅ rescore.mjs | **高**（Step 2） |
| Receipt header | ⚠️ 有 ts/expert 但無 hash | ✅ 4 hash + cmd_args | **高**（Step 1） |
| KPI 層（L7） | ✅ K1-5 + S1-6 | ❌ gbrain 無 | **Jarvis 獨有** |
| 行為分類（phase） | ✅ 6 phase | ❌ | **Jarvis 獨有** |
| Skill 觸發率追蹤 | ✅ expert.json 依賴樹 | ⚠️ 不同問題 | **Jarvis 獨有** |

---

## 我的心得（My Takeaways）

1. **AI agent eval 沒有銀彈，分層才有道理**：retrieval 層用確定性指標（P@K/R@K）、行為層用結構化評分（Cat 8 純數字）、開放任務用 LLM-as-judge（Cat 9）。把所有事都丟 LLM judge 是反模式。
2. **方法論成熟的標誌是「故意限制文件」**：誠實揭露零結果（query expansion 沒效）與已知弱點（temporal -1.5pp）。「我們不知道什麼」比「我們很棒」更有信任價值。
3. **倉庫分離是強制 API 邊界**：把 eval 拆出去後，主產品被迫整理公開 subpath exports。這個結構效果比技術效果更重要。
4. **Spec-first 報告模板是個文化裝置**：強迫先想清楚「這個 benchmark 要回答什麼」。我以前都是跑完才開始寫報告，常常發現方向錯了。
5. **零成本 rescore 是被低估的設計**：把模型原始 output 存進 baseline 就能事後重新評分。對 prompt 迭代是革命性的（秒級 vs 每次 $$）。

## 待補充（Open Questions）

1. **gbrain 的 sealed qrels v2（WASM sandbox 硬實施）目前進度如何？** — 沒在 CHANGELOG 找到，可能還沒啟動。值得追蹤。建議搜尋：`gbrain-evals WASM sandbox sealed qrels`
2. **temporal-reasoning -1.5pp 弱點的解法是什麼？** — gbrain 申報為 v0.29 後續工作，「時間線抽取輸出連到搜尋排名器」具體怎麼做？是另一個 ranking signal layer 還是 hybrid 排序機制？建議搜尋：`gbrain temporal ranking signal v0.29`
3. **gbrain 的 LongMemEval QA judge 為什麼沒做？** — 報告只測 retrieval recall，沒對 published QA evaluator 跑。是成本問題還是設計選擇？建議搜尋：`LongMemEval QA accuracy judge cost`
4. **MemPalace v3 之後（如有 v4）的數字有更新嗎？** — gbrain 對標的是 96.6% baseline，若 MemPalace 更新數字，gbrain 的 head-to-head 表會落後。
5. **Jarvis L7 KPI 的 `framework-session-analyzer-tool` 怎麼設計的？** — 這是 Jarvis 比 gbrain 強的核心元件，但本研究未深入。建議獨立做一份 deep dive。可連結到 [[2026-04-10-CLAUDE-SESSION-ANALYZER-CODE-ANALYSIS]] 是否為同一工具。
6. **Multi-adapter baseline 對 Jarvis 場景的真實價值**：Jarvis 測的是 multi-skill 共存，沒有「同題不同實作」的需求。但若未來要做模型遷移（如 Sonnet 4.6 → Sonnet 5），這個 pattern 仍適用。值得評估。
7. **gbrain skills 跟 Claude Code Skills 系統的關係**：兩邊都用 fat-markdown skill 概念，但路由、執行、組合方式有何差異？跟 [[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]] 做對照可能有收穫。

## 相關連結（Related）

- [[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]] — gstack 同家族專案的 E2E 測試架構與 KPI 設計；可與 gbrain-evals 的 multi-adapter 對照組做兩種方法論比較
- [[2026-04-10-CLAUDE-SESSION-ANALYZER-CODE-ANALYSIS]] — Claude Session Analyzer 深度分析；可能與 Jarvis L7 KPI 用的 `framework-session-analyzer-tool` 為同一系統，是 Backlog 反向觀察的核心連結
- [[2026-04-24-CLAUDE-MEM-V12-PERSISTENT-MEMORY-PLUGIN-DEEP-DIVE]] — claude-mem v12 同為 persistent memory 系統，與 gbrain 做 architecture 對照
- [[2026-03-07-CLAUDE-MEMORY-ENGINE]] — Claude Code 原生記憶系統；與 gbrain 的 brain-ops 迴圈做設計哲學對照
- [[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]] — gstack 設計哲學；含 THIN_HARNESS_FAT_SKILLS 同源觀念
- [[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]] — gbrain 是 Garry Tan 的個人 RAG 系統，本篇是他解釋為何要做 gbrain（解決 Claude Code 暴力檢索的問題）
- [[2026-03-29-CONNSYS-JARVIS-OPENCLAW-NATIVE-PLUGIN-DESIGN]] — Connsys Jarvis 與 OpenClaw 原生整合設計；本筆記 backlog 的對象專案，提供 Jarvis 設計脈絡
- [[2025-08-31-CLAUDE-MEM-CODE-ANALYSIS]] — claude-mem 早期分析（38K stars）；與 gbrain 同為 persistent memory 系統，可對照 hook-driven vs MCP-driven 兩種記憶整合風格
- [[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]] — Stanford 論文：單一 agent 在同 token budget 下勝過 multi-agent；agent eval 方法論的另一個重要參考

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 必記術語：**Sealed qrels**（封閉真值集）、**RRF**（Reciprocal Rank Fusion）、**P@K / R@K**（Precision/Recall at K）、**LLM-as-Judge**、**NDJSON streaming**、**Multi-adapter baseline**、**JudgeEvidence contract**。關鍵數字：gbrain LongMemEval R@5 = 97.60%、BrainBench P@5 = 49.1%、Judge pass 閾值 3.5 / partial 2.5。關鍵路徑：`gbrain-evals/eval/runner/types.ts`、`judge.ts`、`multi-adapter.ts`、`longmemeval.ts` |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | gbrain-evals 用「型別系統的 PublicPage / PublicQuery 強制 sealed qrels」+「judge 看 XML evidence 不看原始 tool output」兩條結構性防線解決 eval 反模式。Multi-adapter 用 4 個 reference 實作（grep-only / vector / RRF / gbrain）並排跑，使絕對數字之外能看出「是新功能進步還是評測本身漂移」。整套設計的核心邏輯是：**結構先於數字、誠實先於漂亮、可重現先於高效**。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 關鍵假設：(1) 「sealed qrels 軟實施已足夠」— adapter 仍能從 `compiled_truth` 文本推測，型別系統無法阻擋；(2) 「LongMemEval R@5 = QA accuracy 的合理代理」— 報告自己標註「retrieval recall ≠ QA accuracy」但未補上 QA judge；(3) 「Multi-adapter 對照都跑同一語料能公平比較」— 但 4 個 adapter 對「同一 query」可能有不同前處理偏誤。潛在漏洞：solo repo 直 commit main 無 PR review，scale up 後是隱憂。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力 | **可立即執行的 5 個行動**：(1) 把 Jarvis `test_cases.json` 加 JSON Schema 驗證（抄 gbrain-evals 6 個 schema 的格式）；(2) Jarvis L6 judge 改成 `JudgeEvidence` 結構化輸入（抄 `renderEvidenceForJudge` 設計）；(3) Jarvis 加 receipt header（prompt_hash + harness_sha）；(4) Jarvis 加 NDJSON streaming + worker-id sharding（為 resume / 分散式打地基）；(5) 寫 `rescore.py` 對歷史 baseline 重評分，加速 prompt 迭代。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | **gbrain-evals vs Jarvis 取捨**：gbrain-evals 強在「retrieval 可重現基準 + sealed qrels + 多 adapter 對照」，適合產品有公開競爭壓力（要跟 MemPalace / Hindsight 比數字）的場景；Jarvis 強在「多 skill 共存的端到端行為診斷 + L7 KPI 分析 + dashboard」，適合內部品質保證、長期演進追蹤的場景。**結論**：兩者正交互補，不是取代關係。Jarvis 應該補 gbrain 的「I/O 容錯 + 結構化 evidence + 可審計性」這三項基礎建設，但保留自家的 L7 KPI + 行為分類 + dashboard 特色。直接整套抄 gbrain-evals 反而會變成兩套不相容世界觀。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「Sealed qrels」的精確邊界在哪？「adapter 看不到 gold」是否等於「adapter 不可能利用 gold」？型別系統強制 vs 程式碼審查強制 vs WASM sandbox 強制，三者差距在哪？
- **假設**：gbrain-evals 的「multi-adapter 對照組」假設「4 個 adapter 處理同一 query 是公平的」。但若 grep-only adapter 對某些 query 有 trivial-fail 偏誤（如標點不敏感），這對比較有何影響？
- **證據**：「LongMemEval R@5 = 97.60% 擊敗 MemPalace 96.6%」這個對比的 baseline 是 MemPalace 何時的版本？若 MemPalace 已發布 v4 達 98%，gbrain 的 head-to-head 還站得住嗎？
- **觀點**：站在「LLM-as-judge 懷疑論者」角度，最有力的批評是什麼？是 judge 自己有偏誤？rubric 編寫者偏誤？還是「結構化 evidence 把可審計性建在沙上」？
- **後果**：若 Jarvis 全套採納 gbrain 的設計，12 個月後可能出現什麼預期外的副作用？（例：團隊文化轉向「報告先於跑數字」可能延緩迭代速度）

### 方案批判三問（Critical Evaluation — 程式碼/方法論類內容）

1. **最大的風險是什麼？** — 全套搬 gbrain-evals 到 Jarvis 的最大風險是**過度工程化（over-engineering）**：Jarvis 場景是 internal QA（多 skill 共存品質），不是 public benchmark（要跟其他系統比數字）。Sealed qrels / Multi-adapter / Spec-first report 對 Jarvis 意義較弱，但實施成本不低（程式重構 + 團隊習慣改變）。最壞情況：花 2 個 sprint 重構後 Jarvis 變得更複雜但沒解決真正痛點。

2. **什麼情況下會失敗？** — (a) Jarvis 的核心痛點是 throughput（跑得慢）而非 reproducibility，那導入 NDJSON streaming + worker sharding 反而是繞遠路；(b) Jarvis 的 judge 主要痛點是 rubric 寫不好而非 evidence 不結構化，那 L6 judge 改造收益不大；(c) Jarvis 團隊現有的 dashboard pipeline 比 markdown report 更被內部消費者重視，那 spec-first 12 節模板毫無價值。**先驗證痛點再決定借鏡項目**。

3. **有沒有更好的替代方案？** — 替代方案 A：**只抄一個改動（structured judge evidence），其他全不動**，1 週驗證效果。若 judge 穩定性與 prompt-injection 防線有顯著改善，再考慮 Step 2。替代方案 B：**反向操作，把 Jarvis 的 L7 KPI 機制反向開源給 gbrain**，這對社群的價值可能比 Jarvis 抄 gbrain 更大。何時選替代方案：若 Jarvis 團隊資源緊張，A 較合理；若希望提升 Jarvis 在社群可見度，B 更值得做。

## References

- [gbrain repo](https://github.com/anthropic/gbrain) — 主產品（本地路徑 `/Users/swchen.tw/git/gbrain_set/gbrain/`）
- [gbrain-evals repo](https://github.com/anthropic/gbrain-evals) — 評估倉庫（本地路徑 `/Users/swchen.tw/git/gbrain_set/gbrain-evals/`）
- [LongMemEval](https://huggingface.co/datasets/xiaowu0162/longmemeval) — 公開長期記憶基準（500 題 `_s` split）
- [MemPalace paper](https://arxiv.org/abs/2406.13340) — 主要對標系統之一
- 本研究 plan 檔案：`/Users/swchen.tw/.claude/plans/gbrain-1-soft-rossum.md`（完整 8 大節 + Verification + 後續方向）
- 對照對象：Connsys Jarvis Integration Test（本地路徑 `~/git/workspace_jarvis/connsys-jarvis/tests/`）
