---
title: "gstack 程式碼分析 — AI Agent / Skill 的 E2E 測試架構與 KPI 設計"
date: 2026-04-07
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#ai-agent"
  - "#evals"
  - "#llm-as-judge"
  - "#testing"
source: "https://github.com/garrytan/gstack"
source_type: code
author: "garrytan"
status: notes
links:
  - "[[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]]"
  - "[[LLM-AS-JUDGE-PATTERNS]]"
  - "[[AI-AGENT-KPI-FRAMEWORK]]"
github_stars: unknown
github_language: TypeScript
date_uncertain: true
---

## 摘要（Summary）

gstack 是一套以 Claude Code skill 為單位的 AI agent 工作流程套件。它有一個值得學習的 **三層測試金字塔**：靜態驗證（free, < 1s）→ LLM-as-judge 文件品質評分（~$0.15/run）→ 完整 E2E 透過 `claude -p` 子程序跑真 agent（~$3.85/run）。本筆記重點研究：**怎麼驗證一個 AI Agent / Skill 是否正常**、**怎麼把 KPI 量化到可在 CI 阻擋 PR 的程度**，以及這套設計可以怎麼搬到自己的 AI Agent 專案。

## Why — 為什麼存在？

- **核心動機**：AI Agent 的輸出是非確定性的（non-deterministic），傳統 unit test 抓不到「agent 走錯流程」、「agent 沒看到 bug」、「agent 文件寫得讓 LLM 看不懂」這類問題。
- **取代/改善什麼**：取代「眼睛看 demo」「user 抱怨才知道」的盲測。
- **目標用戶**：任何在做 AI agent / LLM workflow / prompt-as-code 的開發者。

## What — 是什麼？

- **主要功能**：
  - 三層測試金字塔（靜態 / LLM-judge / E2E）
  - Diff-based 測試選擇（touchfiles 機制）
  - 雙層 tier（gate 阻擋 PR、periodic 週期跑）
  - Planted-bug ground truth 框架（種 bug → agent 找 → judge 算召回率）
  - LLM-as-judge 評三軸：clarity / completeness / actionability
  - Per-test cost / token / latency / turn 追蹤
  - Eval 結果持久化 + 自動跟上次比對
- **不做什麼（Non-goals）**：不替代人工 review；不評 UI 美學（design-shotgun 另解）。
- **技術棧**：Bun + TypeScript（test runner）、Anthropic SDK（judge）、`claude -p` subprocess（E2E）、JSON ground truth fixtures。

## How — 如何運作？

### 系統架構圖

```
┌──────────────────────────────────────────────────────────────┐
│  測試金字塔（Test Pyramid）                                  │
│                                                              │
│   Tier 3  ┌────────────────────────────────────┐            │
│   E2E    │  skill-e2e-*.test.ts               │ ~$3.85/run │
│   慢/貴   │  spawn `claude -p` 跑真 agent       │            │
│           └─────────────┬──────────────────────┘            │
│                         │                                   │
│   Tier 2  ┌─────────────▼──────────────────────┐            │
│   judge  │  skill-llm-eval.test.ts            │ ~$0.15/run │
│   中速   │  Anthropic API 評分 1-5             │            │
│           └─────────────┬──────────────────────┘            │
│                         │                                   │
│   Tier 1  ┌─────────────▼──────────────────────┐            │
│   靜態   │  skill-validation / gen-skill-docs │ free, <1s  │
│   快/免費 │  schema、frontmatter、template       │            │
│           └────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  E2E 執行流程                                                │
│                                                              │
│  test/skill-e2e-*.test.ts                                    │
│        │                                                     │
│        ▼                                                     │
│  session-runner.ts ── runSkillTest({ prompt, maxTurns,      │
│        │                              allowedTools, ... })   │
│        ▼                                                     │
│  Bun.spawn('claude -p --output-format stream-json …')        │
│        │                                                     │
│        ▼                                                     │
│  讀 NDJSON ─► parseNDJSON ─► toolCalls / turns / cost       │
│        │                       │                             │
│        ▼                       ▼                             │
│  scan BROWSE_ERROR_PATTERNS    寫 progress.log + heartbeat   │
│        │                                                     │
│        ▼                                                     │
│  outcomeJudge(groundTruth, output)                           │
│        │                                                     │
│        ▼                                                     │
│  EvalCollector.addTest(metrics) ─► JSON 持久化 ─► 跟上次比對 │
└──────────────────────────────────────────────────────────────┘
```

### Diff-based 選擇 + Tier 流程圖

```
 git push / CI start
   │
   ▼
[detectBaseBranch + getChangedFiles]
   │
   ▼
[selectTests(changed, E2E_TOUCHFILES)]
   │ 對每個 test，看它依賴的 glob 有沒有被改
   │
   ├─ EVALS_ALL=1 ──────► 全跑
   │
   ├─ 有改 SKILL.md ────► 跑所有依賴 SKILL.md 的 test
   │
   └─ 只改 review/** ──► 只跑 review-* tests
                          │
                          ▼
              [filter by EVALS_TIER]
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
            gate                  periodic
        (CI 阻擋 PR)           (週期 cron / 手動)
              │                        │
              ▼                        ▼
        並發跑 test.concurrent    完整跑（含 Opus）
              │
              ▼
         有任何 fail ──► PR 被擋
```

### LLM-as-Judge 時序圖

```
test       judge        Anthropic API    eval-store
  │          │                │              │
  │ readFileSync('SKILL.md')  │              │
  │──slice section            │              │
  │──judge('section', text)──►│              │
  │          │                │              │
  │          │──prompt with rubric──────────►│ Anthropic
  │          │     "rate clarity/completeness│
  │          │      /actionability 1-5"     │
  │          │                ◄──{c:4,co:4,a:5,reasoning}
  │          │◄──parse JSON               │
  │◄─────────│ JudgeScore              │
  │                                          │
  │──assert clarity>=4, completeness>=4 ...  │
  │──collector.addTest({ scores, passed })──►│ 寫 JSON
  │                                          │
  │ (test end)                               │
  │──autoCompareWithPrevious()──────────────►│ diff vs 上次 run
```

### 關鍵設計決策

> [!note] 設計模式
> Test Pyramid + Planted-Bug Ground Truth + LLM-as-Judge + Diff-based Selection。

1. **三層 Tier 而非「all-or-nothing」**：靜態測試 < 1s 跑全部；judge ~$0.02/test 跑修改過的；E2E 只在 push 時跑。理由：完整 E2E ~$4/run，每次 commit 都跑會破產。
2. **Diff-based touchfiles**：每個 test 在 `E2E_TOUCHFILES` 宣告自己依賴哪些檔案 glob。改 `qa/**` 只觸發 qa-* 測試，改 `*/SKILL.md.tmpl` 觸發所有 journey-* routing 測試。理由：在「便宜」與「不漏測」之間做取捨，宣告式設計讓覆蓋關係可審計。
3. **Gate vs Periodic 雙 tier**：guardrail 類（安全、deterministic）放 gate，品質類、Opus、外部 CLI 依賴放 periodic。理由：CI 不能 30 分鐘也不能花太多錢，但週期跑可以。
4. **`claude -p` 而非 Agent SDK**：因為 test 本身可能在 Claude Code session 內跑，不能用 SDK（會 race）。spawn 完全獨立的 subprocess + stream NDJSON。
5. **NDJSON streaming + heartbeat**：即時看到 agent 在 turn N 呼叫了什麼 tool，long-running test 不是黑盒。寫 atomic heartbeat 給外部監控。
6. **Planted Bug + LLM Judge**：手工種已知 bug 在 fixture HTML/SQL/Ruby 裡，給 ground truth JSON（id、category、severity、detection_hint），讓 judge 算 detection_rate / false_positives / evidence_quality。是 agent 召回率（recall）的客觀指標。
7. **Per-test cost + 模型 + latency 全紀錄**：`first_response_ms`、`max_inter_turn_ms`、`total_cost_usd`、`turns_used` 都進 EvalResult。有了這些才能訂 KPI、回歸監控。
8. **Auto-compare with previous run**：每次跑完自動跟上一個 run 比 pass/fail/cost/duration，regression 一眼看到。
9. **「讀檔不要 copy 整個 SKILL.md」**：CLAUDE.md 明文禁止，因為 1900 行 SKILL.md 灌進 agent context 會導致 timeout / turn limit，section extract 後 38s 完成、不 extract 會 5-10x 倍速度。

### 關鍵程式碼

**LLM-as-Judge 文件評分 rubric**（`test/helpers/llm-judge.ts:62-90`）

```typescript
export async function judge(section: string, content: string): Promise<JudgeScore> {
  return callJudge<JudgeScore>(`You are evaluating documentation quality for an AI coding agent's CLI tool reference.

The agent reads this documentation to learn how to use a headless browser CLI. It needs to:
1. Understand what each command does
2. Know what arguments to pass
3. Know valid values for enum-like parameters
4. Construct correct command invocations without guessing

Rate the following ${section} on three dimensions (1-5 scale):

- **clarity** (1-5): Can an agent understand what each command/flag does from the description alone?
- **completeness** (1-5): Are arguments, valid values, and important behaviors documented? Would an agent need to guess anything?
- **actionability** (1-5): Can an agent construct correct command invocations from this reference alone?

Scoring guide:
- 5: Excellent — no ambiguity, all info present
- 4: Good — minor gaps an experienced agent could infer
- 3: Adequate — some guessing required
- 2: Poor — significant info missing
- 1: Unusable — agent would fail without external help

Respond with ONLY valid JSON in this exact format:
{"clarity": N, "completeness": N, "actionability": N, "reasoning": "brief explanation"}

Here is the ${section} to evaluate:

${content}`);
}
```

**Planted-Bug Recall Judge**（`test/helpers/llm-judge.ts:96-129`）

```typescript
export async function outcomeJudge(
  groundTruth: any,
  report: string,
): Promise<OutcomeJudgeResult> {
  return callJudge<OutcomeJudgeResult>(`You are evaluating a QA testing report against known ground truth bugs.

GROUND TRUTH (${groundTruth.total_bugs} planted bugs):
${JSON.stringify(groundTruth.bugs, null, 2)}

QA REPORT (generated by an AI agent):
${report}

For each planted bug, determine if the report identified it. A bug counts as
"detected" if the report describes the same defect, even if the wording differs.
Use the detection_hint keywords as guidance.

Also count false positives: issues in the report that don't correspond to any
planted bug AND aren't legitimate issues with the page.

Respond with ONLY valid JSON:
{
  "detected": ["bug-id-1", "bug-id-2"],
  "missed": ["bug-id-3"],
  "false_positives": 0,
  "detection_rate": 2,
  "evidence_quality": 4,
  "reasoning": "brief explanation"
}`);
}
```

**Ground Truth 範例**（`test/fixtures/qa-eval-ground-truth.json`）

```json
{
  "fixture": "qa-eval.html",
  "bugs": [
    {
      "id": "broken-link",
      "category": "functional",
      "severity": "medium",
      "description": "Navigation link 'Resources' points to /nonexistent-404-page which returns 404",
      "detection_hint": "link|404|broken|dead|nonexistent|Resources"
    },
    {
      "id": "disabled-submit",
      "category": "functional",
      "severity": "high",
      "description": "Contact form submit button has 'disabled' attribute permanently",
      "detection_hint": "disabled|submit|button|form|cannot submit|contact"
    },
    {
      "id": "console-error",
      "category": "console",
      "severity": "high",
      "description": "TypeError on page load: Cannot read properties of undefined",
      "detection_hint": "console|error|TypeError|undefined|map"
    }
  ],
  "total_bugs": 5,
  "minimum_detection": 2,
  "max_false_positives": 5
}
```

**E2E baseline 比對基準**（`test/fixtures/eval-baselines.json`）

```json
{
  "command_reference": { "clarity": 4, "completeness": 3, "actionability": 4 },
  "snapshot_flags":    { "clarity": 4, "completeness": 4, "actionability": 4 },
  "browse_skill":      { "clarity": 4, "completeness": 4, "actionability": 4 },
  "qa_workflow":       { "clarity": 4, "completeness": 4, "actionability": 4 },
  "qa_health_rubric":  { "clarity": 4, "completeness": 3, "actionability": 4 }
}
```

**E2E 阻擋條件**（`test/skill-llm-eval.test.ts:83-92`）

```typescript
passed: scores.clarity >= 4 && scores.completeness >= 3 && scores.actionability >= 4,
// ...
expect(scores.clarity).toBeGreaterThanOrEqual(4);
expect(scores.completeness).toBeGreaterThanOrEqual(3);
expect(scores.actionability).toBeGreaterThanOrEqual(4);
```

> [!important] 注意 completeness 故意只要求 3 — 因為 command reference 表是「快速查表」，細節在子章節。**KPI 不一定每軸都要 5**，要看那塊內容的目的。

## 🎯 AI Agent KPI 設計框架（從 gstack 萃取）

> [!tip] 這是本筆記給你的核心交付物。可直接抄進你的 AI Agent 專案。

### KPI 分四類

| 類別 | KPI | 衡量方式 | gstack 對應 |
|------|-----|---------|------------|
| **正確性（Correctness）** | Detection Rate（召回率） | 種 N 個已知 bug，agent 找到幾個 | `outcomeJudge.detection_rate` |
| | False Positive Rate | 報告中不存在的問題數 | `false_positives` |
| | Evidence Quality（1-5） | 每個發現有沒有截圖、reproducible step、element ref | `evidence_quality` |
| **效能（Performance）** | Latency p50/p95 | 從 spawn 到結束的 wall clock | `duration` |
| | First Token Latency | spawn 到第一個 NDJSON line | `firstResponseMs` |
| | Max Inter-Turn Latency | 兩次 tool call 間最長靜默 | `maxInterTurnMs` |
| | Turns Used | agent 用了幾個對話 turn | `turnsUsed` |
| **成本（Cost）** | $/run | 整個 task 花的 USD | `total_cost_usd` |
| | Token Usage | input / output / cache 分開 | `usage.*_tokens` |
| **品質（Quality, 主觀但可量化）** | Clarity 1-5 | LLM judge 評分 | `judge.clarity` |
| | Completeness 1-5 | 漏掉重要資訊嗎 | `judge.completeness` |
| | Actionability 1-5 | 看完能直接行動嗎 | `judge.actionability` |

### KPI 訂定的四個原則

1. **每軸都要有 baseline**（不是 0），且明確寫在 fixture：`eval-baselines.json` 用「上次正常的分數」當門檻，不會用「滿分」當門檻。
2. **不同 KPI 不同 tier**：「不可妥協的安全 / 功能性」→ gate（CI 擋 PR）。「品質、模糊判斷」→ periodic。
3. **regression 門檻 ≠ 絕對門檻**：應該檢查「比上次差多少」而不只是「夠不夠 4 分」。gstack 的 `autoCompareWithPrevious` 就是這個。
4. **失敗模式可分類**：`exit_reason` 分 `success` / `timeout` / `error_max_turns` / `exit_code_N` / `error_api`，可以聚合看「最近一週 timeout 比例多少」而不是「過/不過」。

### 你應該種的 Ground Truth 類型

- **Functional bugs**：明確壞掉的東西（按鈕無作用、API 500）
- **Visual bugs**：肉眼可見但難用 unit test 抓的（overflow、對齊）
- **Accessibility bugs**：a11y 違規（缺 alt、對比度）
- **Console errors**：runtime exception
- **Edge case bugs**：邊界數字、空字串、超長輸入
- **Negative cases**：故意放「看起來像 bug 但其實不是」的測 false positive

每個 bug 給：`id`、`category`、`severity`、`description`、`detection_hint`（給 judge 比對的關鍵字）。

## 安裝流程（Installation Flow）

### 安裝時序圖

```
 user        bun install     ./setup        package.json scripts
   │             │              │                  │
   │──bun install►              │                  │
   │             │──install deps│                  │
   │──./setup───────────────────►                  │
   │                            │──bun run build──►│ gen:skill-docs
   │                            │                  │ build browse/design
   │                            │──symlink skills──►│
   │                            │                  │
   │ (test 環境額外)             │                  │
   │──export ANTHROPIC_API_KEY   │                  │
   │──bun test ─────────────────────────────────────► 跑 free tier
   │──bun run test:evals ───────────────────────────► 跑 LLM judge + E2E
```

### 安裝產物清單（測試相關）

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.gstack/projects/$SLUG/evals/` | 目錄 | 每次 eval run 的 JSON 結果 |
| `~/.gstack/projects/$SLUG/e2e-runs/$RUNID/` | 目錄 | 每個 test 的 ndjson transcript + progress.log |
| `~/.gstack-dev/e2e-live.json` | 檔案 | 全域 heartbeat（pid、currentTest、turn、lastTool） |
| `test/fixtures/*-ground-truth.json` | 檔案 | planted bug 標準答案 |
| `test/fixtures/eval-baselines.json` | 檔案 | LLM-judge 分數基準 |

### 環境變數

| 變數 | 用途 |
|------|------|
| `ANTHROPIC_API_KEY` | 必須；judge 與 E2E 都呼叫 Anthropic API |
| `EVALS=1` | 啟用 LLM-judge tier |
| `EVALS_ALL=1` | 強制跑全部測試（忽略 diff selection） |
| `EVALS_TIER=gate\|periodic` | 只跑特定 tier |
| `EVALS_BASE=main` | diff 比對基準 branch |
| `EVALS_MODEL=claude-opus-4-6` | 覆寫測試使用的模型 |

---

## 使用案例地圖（Use Case Map）

| # | 使用案例 | 觸發 | 入口檔案 | 核心鏈 |
|---|---------|------|---------|-------|
| 1 | 跑免費快速測試 | `bun test` | `test/skill-validation.test.ts` | parser → schema check → assert |
| 2 | 跑 LLM judge 評文件 | `bun run test:evals` | `test/skill-llm-eval.test.ts` | touchfiles → judge() → eval-store |
| 3 | 跑 E2E 真 agent | `bun run test:e2e` | `test/skill-e2e-*.test.ts` | runSkillTest → claude -p → outcomeJudge |
| 4 | CI 阻擋 PR | GitHub Actions | `.github/workflows/evals.yml` | `EVALS_TIER=gate` 跑必過項 |
| 5 | 比較兩個 run | `bun run eval:compare` | `eval-store.ts` | 讀兩個 JSON → diff 表格 |
| 6 | 預覽 diff 會跑哪些 | `bun run eval:select` | `touchfiles.ts` | git diff → match globs → list |

### 案例詳解

#### 案例 3：E2E 真 agent 跑 QA skill

```
bun run test:e2e
  │
  ▼
test/skill-e2e-qa-workflow.test.ts:test('qa-b6-static')
  │
  ▼
runSkillTest({
  prompt: "/qa http://localhost:9999/qa-eval.html",
  workingDirectory: tmpDir,
  maxTurns: 15,
  allowedTools: ['Bash','Read','Write']
})
  │
  ▼
session-runner.ts: Bun.spawn(['claude','-p',...])
  │
  ├─ stream NDJSON ─► parseNDJSON ─► toolCalls / turns
  │
  ├─ heartbeat 寫 ~/.gstack-dev/e2e-live.json
  │
  ├─ scan BROWSE_ERROR_PATTERNS
  │
  ▼
agent 結束，拿 result.output（QA 報告 markdown）
  │
  ▼
outcomeJudge(qa-eval-ground-truth.json, output)
  │ Anthropic API: "比對 ground truth 種的 5 個 bug，agent 找到幾個"
  ▼
{ detected: ['broken-link','console-error'], missed: [...], detection_rate: 2 }
  │
  ▼
expect(detection_rate).toBeGreaterThanOrEqual(2)  // ground truth.minimum_detection
expect(false_positives).toBeLessThanOrEqual(5)
  │
  ▼
EvalCollector.addTest({ name, cost, duration, detection_rate, ... })
  │
  ▼
寫 ~/.gstack/projects/$SLUG/evals/v0.15.15.0-main-e2e-{ts}.json
  │
  ▼
autoCompareWithPrevious() → 印比對表格
```

#### 案例 4：CI gate 阻擋 PR

```
PR push
  │
  ▼
GitHub Actions: .github/workflows/evals.yml
  │
  ├─ Job 1: bun test (free, < 30s)
  │   └─ skill validation, gen-skill-docs, browse integration
  │
  └─ Job 2: EVALS_TIER=gate bun run test:evals
       │
       ▼
   touchfiles.ts: getChangedFiles(main) → ['qa/SKILL.md.tmpl','qa/templates/...']
       │
       ▼
   selectTests(changed, E2E_TOUCHFILES) → ['qa-quick','qa-only-no-fix','qa-bootstrap']
       │
       ▼
   filter by E2E_TIERS → 全是 gate → 全跑
       │
       ▼
   spawn claude -p × 3（並發）
       │
       ├─ 任一 fail ─► PR red ─► 不能 merge
       │
       └─ 全 pass ─► PR green ─► 可 merge
```

---

## 架構師觀點（Architect's View）

### ✅ 優點

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性 | ⭐⭐⭐⭐⭐ | touchfiles 是宣告式單一檔案，加 test 改一處 |
| 成本控制 | ⭐⭐⭐⭐⭐ | diff-based + tier 雙重剪枝，~$4 上限是真的 |
| 觀測性 | ⭐⭐⭐⭐⭐ | NDJSON streaming + heartbeat + per-test transcript |
| 可重現性 | ⭐⭐⭐⭐ | ground truth JSON 把 agent 評估從「主觀」變「半客觀」 |
| 失敗診斷 | ⭐⭐⭐⭐⭐ | exit_reason 細分 + 失敗 transcript 永久保存 |
| 跨 agent 通用 | ⭐⭐⭐⭐ | 同一 framework 同時測 Claude / Codex / Gemini |

> [!tip] 最值得偷的設計
> **「Planted Bug + Detection Hint」** 模式 — 人類在 fixture 種已知 bug、寫 detection_hint 關鍵字，judge 用模糊比對算召回。讓「agent 抓 bug 能力」變成可量化、可回歸監控的數字，這是我看過最簡單又最實用的 agent eval 框架。

### ⚠️ 缺點與風險

> [!warning] 已知缺陷

- **LLM judge 自身有 variance**：claude-sonnet-4-6 評分本身會跳動 ±1 分，所以 baseline 設 4 而非 5 是務實但削弱了精度。沒看到多次重試取平均。
- **judge 用同家族模型**：用 sonnet 評 sonnet 寫的 SKILL.md 有同質性偏誤（self-preference bias）。理想上應該用不同 family 或多 judge ensemble。
- **detection_hint 是字串 OR**：對英文以外語言或概念性 bug 不友善。
- **沒有 statistical significance test**：detection_rate 從 3 變 2 有可能只是 LLM 隨機性。
- **`max_inter_turn_ms` 只看單次峰值**：應改成 p95 才有統計意義。
- **E2E 完全跑時 30-45 分鐘**：CI 預算是上限，無法縮短只能 selection 變聰明。
- **`callJudge` 只 retry 一次（429）**：對 API rate limit 不夠 robust。
- **沒有 prompt 變化的 A/B test 框架**：想驗「換 prompt 是否改善 KPI」需要手動跑兩次。

### 🔮 改進建議

1. judge 跑 N=3 取中位數，降 variance
2. 加 cross-judge（用 GPT-4 評 Claude，反之亦然）做 sanity check
3. detection_hint 改成 embedding similarity，不依賴關鍵字
4. eval-store 加 statistical test（two-proportion z-test）判斷 regression 是否顯著
5. 加 prompt A/B fixture：同一 ground truth、跑兩個 prompt 版本、比 KPI

## 效能基準（Benchmark）

> [!info] 來源：CLAUDE.md 自述

| 場景 | 成本 | 時間 |
|------|------|------|
| `bun test`（Tier 1 全部） | $0 | < 2s |
| `bun run test:evals`（diff-based） | ~$4 上限 | varies |
| 完整 E2E suite（all） | unknown | 30–45 分鐘 |
| 單個 LLM-judge test | ~$0.02 | ~3s |
| 單個 E2E test（QA skill） | ~$0.50 | 30s–3min |

預期瓶頸：API rate limit（並發跑時），以及 `claude -p` 啟動冷啟動時間。

## 快速上手（Quick Start）

```bash
# 1) Clone gstack 看完整範例
git clone https://github.com/garrytan/gstack
cd gstack && bun install

# 2) 跑免費測試（理解 Tier 1）
bun test

# 3) 跑 LLM judge 範例（要 API key）
export ANTHROPIC_API_KEY=sk-ant-...
bun run test:evals

# 4) 看上次 eval 結果與比對
bun run eval:list
bun run eval:compare
bun run eval:summary

# 5) 預覽 diff 會選哪些 test
bun run eval:select
```

## 我的心得（My Takeaways）

把 gstack 的方法搬到我自己的 AI Agent 專案，最重要的是：

1. **Day 1 就建三層 tier**：靜態 free，judge 中等，E2E 貴。不要等到後期才補測試，因為 agent 行為會 drift。
2. **Ground truth 是 agent eval 的核心資產**：種 bug 比寫 prompt 更難但更值錢。每個 fixture 寫好 `id`、`description`、`detection_hint`。
3. **KPI 要分軸 + baseline 不一定 5 分**：把 clarity / completeness / actionability 拆開看，每軸獨立 baseline。「actionability 必須 4」「completeness 可以 3」是可以的，看內容用途。
4. **規定每個 test 必須宣告 touchfiles**：強制思考「這個 test 在保護什麼程式」。沒宣告的 test = 黑盒。
5. **observability 不是 nice-to-have**：streaming NDJSON + heartbeat + per-test transcript，是 long-running agent test 唯一保命符。
6. **cost 必須是 first-class metric**：把 `total_cost_usd`、`turns_used` 放在 EvalResult 的 schema 第一級欄位，每次都看，不然會破產。
7. **Self-preference 是真的**：別只用 Claude 評 Claude，至少加一個 cross-family judge 做 sanity。
8. **KPI 訂在「比上次差」而非「夠不夠 N 分」**：絕對門檻給 floor（不能掉到 3 以下），相對 regression 給 ceiling（不能比上次差超過 X%）。

## 待補充（Open Questions）

- gstack 的 Planted-Bug 框架需要手工維護 ground truth JSON（已知 bug 清單）。當 codebase 持續演進，這些 fixture 如何保持與真實代碼同步？有沒有自動化更新 ground truth 的方法？（建議搜尋：`planted bug ground truth maintenance fixture sync`）
- LLM-as-Judge 評分的一致性（consistency）如何保證？同一份 SKILL.md 在不同時間送給 judge 可能得到不同分數。gstack 是否有對 judge 本身做校準（calibration）或多次取樣取平均？（建議搜尋：`LLM judge consistency calibration inter-rater reliability`）
- E2E 測試以 `claude -p` 子程序跑真實 Agent，每次約 $3.85。若 Claude API 的定價改變或模型更新，歷史 cost benchmark 就會失去可比性。gstack 是否有 normalize cost 的機制（例如按 token 數而非美元計算）？（建議搜尋：`AI agent eval cost normalization benchmark reproducibility`）
- `outcomeJudge` 判斷 Agent 是否找到 planted bug 時，是否有考慮 Agent 找到 bug 但用不同描述方式的情況？judge prompt 的相似度判斷邊界是如何定義的？（建議搜尋：`LLM judge semantic equivalence bug detection paraphrase`）
- Diff-based touchfiles 是開發者手動宣告「這個測試依賴哪些檔案」，若宣告不完整（漏填 glob），可能導致相關測試在 CI 中被跳過。有沒有自動偵測依賴關係的計劃？（建議搜尋：`test dependency detection automatic touchfiles CI coverage`）

## 相關連結（Related）

- [[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]] — 同 repo 的 telemetry 設計，KPI 落地的另一面
- [[LLM-AS-JUDGE-PATTERNS]] — LLM 評 LLM 的常見 pattern 與陷阱
- [[AI-AGENT-KPI-FRAMEWORK]] — 從本文萃取的 KPI 表格（待寫）
- [[EVAL-DRIVEN-DEVELOPMENT]] — 把 eval 當 TDD 的工作流
- [[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]] — Garry Tan 80–90% 測試覆蓋率心法的源頭專訪

---
- [[2026-05-17-GBRAIN-EVALS-VS-JARVIS-EVAL-METHODOLOGY]] — gbrain-evals 是另一套成熟的 agent eval 方法論，含 12 節 spec-first 報告模板與多 adapter 對照組設計
- [[2026-08-18-KB-NAVIGATION-VS-BARE-AGENT-EXPERIMENT-30-NOTES-FILENAME-BEATS-SKILL-TREE]] — eval 方法論的實際應用案例：三組對照＋紅隊迭代＋transcript 稽核的 KB 檢索實驗

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 三層 tier（validation / llm-judge / e2e）；KPI 三軸（clarity / completeness / actionability，1-5）；planted bug ground truth 五欄位（id / category / severity / description / detection_hint）；E2E 透過 `claude -p --output-format stream-json` 而非 SDK；diff-based selection 透過 E2E_TOUCHFILES |
| **理解（半被動）** | 串聯知識點 | 為何要三層：成本 vs 覆蓋的權衡。為何 `claude -p`：test 自身在 Claude session 跑會 race。為何 touchfiles：在 cost cap $4 內維持高覆蓋率。為何 ground truth：把 agent recall 從主觀變半客觀。Tier + Selection + Cost-tracking + Heartbeat 一起構成「能上 CI 的 agent eval」這個整體。 |
| **分析（主動）** | 找出假設 | 假設 1：LLM-judge 評分穩定 → 實際 ±1 variance。假設 2：detection_hint 字串比對能涵蓋所有「同義表述」→ 對非英語 / 概念性 bug 失效。假設 3：完整 E2E suite 30-45 分鐘 CI 可接受 → 對快速迭代不友善。假設 4：用 sonnet 評 sonnet 中立 → self-preference bias 未控制。 |
| **應用（主動）** | 規劃執行 | (1) **本週**：在我的 AI Agent 專案建 `test/fixtures/ground-truth/` 目錄，種 5–10 個已知 case，包含 detection_hint。(2) **下週**：寫 `judge.ts` 三軸評分模板（clarity/completeness/actionability + reasoning，要求 JSON output），用兩家 LLM (Claude + GPT-4) 跑 cross-judge sanity。(3) **下個 sprint**：建 EvalCollector 紀錄 cost/duration/turns，用 JSON 持久化，加 auto-compare-with-previous。 |
| **評估（主動）** | 多方案權衡 | **替代方案 A：純 unit test 不做 LLM eval** → 完全 deterministic 但測不到「agent 是否做對事」，只測「程式碼是否沒爆」。適用 deterministic skill；不適用 prompt-driven agent。**替代方案 B：用 LangSmith / Weights & Biases / Helicone 第三方平台** → 開箱即用、有 UI、貴、vendor lock-in。適用團隊，不適用個人 OSS。**替代方案 C：人工 review demo 影片** → 抓得到 UX 問題但不可 scale、無 regression。**gstack 方案最適合「個人 / 小團隊、prompt-as-code、要 CI 阻擋」的場景**。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Detection rate」的定義是「找到的 bug 數」還是「找到的 bug 數 / 總 bug 數」？gstack 用前者（整數），會不會混淆？
- **假設**：LLM judge 評分的 inter-rater reliability 沒測，怎麼證明這個 KPI 有效？
- **證據**：CLAUDE.md 寫「節省 5-10x 時間」是一次測試還是統計平均？
- **觀點**：站在「不該用 LLM 評 LLM」陣營的角度，最有力的批評是「它系統性偏好同 prompt style 的輸出」，gstack 怎麼防？目前看起來沒防。
- **後果**：12 個月後 agent 變更頻繁，touchfiles 沒同步維護的話，會出現 test 沒跑到的「沉默漏洞」。誰負責 audit touchfile 的完整性？

### 方案批判三問

1. **最大的風險是什麼？** — KPI 失靈而沒被發現。如果 LLM judge 自己 drift 了（API 模型升級），baseline 4 變成「太鬆」或「太嚴」，整個 CI gate 給的安全感是假的。沒有 judge 自己的 calibration test。
2. **什麼情況下會失敗？** — (a) 種的 ground truth bug 太集中於某類（例如全是 functional），會錯失 visual / a11y / performance。(b) 並發跑 E2E 撞 API rate limit，failures 會被當成「test broken」而非「rate limit」。(c) 用同一個 fixture 反覆跑會 overfit prompt。
3. **有沒有更好的替代方案？** — 對「需要稽核 / 監管 / 高 stakes」的 agent，應該配 OpenAI Evals / DeepEval / Promptfoo 這類專業 framework + human-in-the-loop spot check。對「個人 / 內部工具 / 高速迭代」，gstack 方案是甜蜜點。當你需要 token-level attribution、trace context、A/B prompt comparison 三者皆有時，就該換 LangSmith 或自建。

## References

- [GitHub Repo](https://github.com/garrytan/gstack)
- `test/helpers/session-runner.ts` — `claude -p` subprocess + NDJSON
- `test/helpers/llm-judge.ts` — `judge()` 與 `outcomeJudge()`
- `test/helpers/touchfiles.ts` — diff-based selection + tier 分類
- `test/helpers/eval-store.ts` — EvalCollector 持久化 + 比對
- `test/skill-llm-eval.test.ts` — LLM judge 範例
- `test/fixtures/qa-eval-ground-truth.json` — planted bug 範例
- `test/fixtures/eval-baselines.json` — KPI baseline
- `CLAUDE.md` — 測試命令、tier 說明、E2E fixture 抽取規範
