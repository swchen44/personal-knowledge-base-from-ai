---
title: "Karpathy 準則 vs Claude Code 內建 System Prompt：逐條原始碼比對與實用建議"
date: 2026-01-27
category: AI
tags:
  - "#ai/claude-code"
  - "#ai/prompt-engineering"
  - "#devtools/configuration"
  - "#ai/llm"
source: "https://github.com/forrestchang/andrej-karpathy-skills/blob/main/CLAUDE.md"
source_type: article
author: "Andrej Karpathy / forrestchang"
status: notes
github_stars: 34941
links:
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
  - "[[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]]"
  - "[[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]]"
  - "[[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]]"
---

## 摘要（Summary）

Andrej Karpathy 提出的四條 LLM 程式設計行為準則（GitHub 34K stars）被廣泛用於 `.claude/CLAUDE.md` 來改善 Claude Code 的程式設計品質。本文透過**直接比對 Claude Code 反編譯原始碼**（`src/constants/prompts.ts`），逐條驗證這些準則是否已內建於 system prompt，量化覆蓋度，並提出基於原始碼證據的實用建議。核心發現：**準則 2（Simplicity First）和準則 3（Surgical Changes）與內建 prompt 幾乎逐字重疊，額外加入只會浪費 Token；而準則 1（Think Before Coding）和準則 4（Goal-Driven Execution）提供了內建 prompt 欠缺的「提前溝通」和「結構化驗證」，值得加入。**

## 關鍵洞察（Key Insights）

- **準則 2 和 3 已內建**：`prompts.ts:201-203` 的 `codeStyleSubitems` 與 Karpathy 準則的措辭幾乎完全相同，加入等同重複消耗 Token — 參見 [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]
- **準則 1 有增量價值**：Claude Code 內建的是「卡住才問」（`prompts.ts:233`），Karpathy 要求的是「不確定就問」，後者更安全 — 參見 [[CLAUDE-CODE-CONTEXT-ENGINEERING]]
- **準則 4 的「步驟→驗證→迴圈」結構是最大缺口**：Claude Code 只有模糊的「失敗時診斷」指令，沒有要求明確列出驗證計畫
- **34K stars 不代表都需要加**：這份準則的流行度來自「教 LLM 少做蠢事」的共鳴，但 Anthropic 團隊已經把最關鍵的部分寫進 system prompt 了 — 參見 [[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]]

## 詳細內容（Details）

### Karpathy 準則原文（完整保留）

```markdown
# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
```

### 逐條比對：Karpathy vs Claude Code 內建 System Prompt

#### 準則 1：Think Before Coding — ⚠️ 部分覆蓋

| Karpathy 要求 | Claude Code 內建？ | 原始碼位置 |
|---|---|---|
| 明確陳述假設 | ❌ 未提及 | — |
| 多種解讀時列出選項 | ❌ 未提及 | — |
| 有更簡單方案時要說出來 | ⚠️ 間接 | `prompts.ts:233` |
| 不確定時停下來問 | ⚠️ 語氣不同 | `prompts.ts:233` |

> [!important] 關鍵差異：「卡住才問」vs「不確定就問」
> Claude Code 內建：`Escalate to the user with AskUserQuestion only when you're genuinely stuck after investigation, not as a first response to friction.`
> Karpathy 要求：`If uncertain, ask.` / `If something is unclear, stop. Name what's confusing. Ask.`
> 
> Claude Code 鼓勵自主嘗試，Karpathy 鼓勵提前溝通。對於重要的程式碼變更，Karpathy 的版本更安全。

#### 準則 2：Simplicity First — ✅ 高度覆蓋

| Karpathy 要求 | Claude Code 內建原文（`prompts.ts`） |
|---|---|
| No features beyond what was asked | `Don't add features, refactor code, or make "improvements" beyond what was asked.`（:201） |
| No abstractions for single-use code | `Don't create helpers, utilities, or abstractions for one-time operations.`（:203） |
| No "flexibility" that wasn't requested | `Don't design for hypothetical future requirements.`（:203） |
| No error handling for impossible scenarios | `Don't add error handling, fallbacks, or validation for scenarios that can't happen.`（:202） |
| 200 lines → 50 lines, rewrite | `Three similar lines of code is better than a premature abstraction.`（:203） |

> [!note] 幾乎逐字重疊
> Karpathy 的五條 Simplicity 規則全部被 Claude Code 的 `codeStyleSubitems`（`prompts.ts:200-203`）覆蓋。措辭甚至極為接近。**額外加入只會浪費每次 API call 的 Token。**

#### 準則 3：Surgical Changes — ✅ 高度覆蓋

| Karpathy 要求 | Claude Code 內建原文（`prompts.ts`） |
|---|---|
| Don't "improve" adjacent code | `A bug fix doesn't need surrounding code cleaned up.`（:201） |
| Don't add docstrings to unchanged code | `Don't add docstrings, comments, or type annotations to code you didn't change.`（:201） |
| Don't refactor unbroken things | 同上 |
| Remove YOUR orphan imports | `Avoid backwards-compatibility hacks like renaming unused _vars`（:236） |
| Don't remove pre-existing dead code | ⚠️ Claude Code 說 `If you are certain that something is unused, you can delete it completely`（:236）— **更積極** |

> [!warning] 唯一差異：死碼處理
> Karpathy：「看到無關死碼，提一下但不要刪」
> Claude Code：「確定沒用就可以刪」
> Claude Code 更激進。如果你偏好保守（不希望 AI 主動刪除你不熟悉的程式碼），可以加入 Karpathy 的版本。

#### 準則 4：Goal-Driven Execution — ⚠️ 部分覆蓋

| Karpathy 要求 | Claude Code 內建？ | 說明 |
|---|---|---|
| 定義成功標準 | ❌ 未明確要求 | — |
| 列出步驟+驗證點 | ❌ 未明確要求 | — |
| 迴圈直到驗證通過 | ⚠️ 間接 | `diagnose why before switching tactics`（:233） |
| 完成前跑測試 | ⚠️ ant-only | `verify it actually works: run the test`（:211）— 僅限 Anthropic 內部用戶 |

> [!important] 最大缺口
> 「步驟→驗證→迴圈」的結構化執行框架是 Karpathy 準則中**最有原創價值的部分**。Claude Code 內建只有模糊的「失敗時診斷」和 ant-only 的「完成前跑測試」。對外部用戶來說，這條準則提供了內建 prompt 完全沒有的指引。

### 四條準則的覆蓋度總覽

```
┌──────────────────────┬──────────┬───────────────────────────────────┐
│      Karpathy 準則    │ 覆蓋程度  │ 建議                              │
├──────────────────────┼──────────┼───────────────────────────────────┤
│ 1. Think Before Coding│ ⚠️ 部分  │ ✅ 值得加「不確定就問」             │
├──────────────────────┼──────────┼───────────────────────────────────┤
│ 2. Simplicity First  │ ✅ 已覆蓋 │ ❌ 不需要 — 逐字重疊              │
├──────────────────────┼──────────┼───────────────────────────────────┤
│ 3. Surgical Changes  │ ✅ 已覆蓋 │ ❌ 不需要 — 高度重疊              │
├──────────────────────┼──────────┼───────────────────────────────────┤
│ 4. Goal-Driven       │ ⚠️ 部分  │ ✅ 值得加「步驟+驗證點」格式       │
│    Execution         │          │                                   │
└──────────────────────┴──────────┴───────────────────────────────────┘
```

### 建議的最佳劃分策略

> [!tip] 只加有增量價值的部分
> 不要整篇照搬 Karpathy 準則。準則 2 和 3 已內建，加入只浪費 Token（每次 API call 都要載入 CLAUDE.md）。只加準則 1 和 4 中**內建 prompt 欠缺的部分**。

**建議放在 `~/.claude/CLAUDE.md` 或 `~/.claude/rules/think-and-verify.md`**：

```markdown
## 不確定就問
- 在實作前，明確陳述你的假設。如果不確定，先問。
- 如果有多種解讀，列出來讓我選，不要自己默默選一個。
- 如果有更簡單的做法，說出來。推回不合理的要求。

## 目標驅動
對多步驟任務，先列出計畫：
1. [步驟] → 驗證：[檢查方式]
2. [步驟] → 驗證：[檢查方式]

完成前，跑測試或驗證腳本確認結果。
```

**不建議加入的部分**（已內建，會浪費 Token）：
- 「不加未被要求的功能」→ 已在 `prompts.ts:201`
- 「不為假設性需求設計」→ 已在 `prompts.ts:203`
- 「不改善相鄰程式碼」→ 已在 `prompts.ts:201`
- 「不加不可能場景的錯誤處理」→ 已在 `prompts.ts:202`

### 注入層考量

基於本系列研究（參見 [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]），不同注入方式的 Token 成本：

| 放置位置 | Token 消耗 | 適用性 |
|---------|-----------|--------|
| `~/.claude/CLAUDE.md` | 每次 API call 都載入 | 全局行為規範（如「不確定就問」） |
| `~/.claude/rules/verify.md`（無 paths:） | 每次 API call 都載入 | 同上，只是組織方式不同 |
| `~/.claude/rules/verify.md`（有 paths:） | 按需載入 | 只在操作特定檔案時注入 |
| `.claude/skills/verify/SKILL.md` | 呼叫時才注入 | 不適合行為規範（模型不會主動觸發） |

> [!warning] 行為準則不適合放在 Skills 中
> Skills 是按需注入的——只有在模型決定呼叫或用戶輸入 `/skill-name` 時才載入。行為準則需要**每次 API call 都生效**，所以必須放在 CLAUDE.md 或無條件 rules 中。

## 我的心得（My Takeaways）

1. **「整篇照搬」是最常見的錯誤**：34K stars 導致很多人不加思考就把整份 Karpathy CLAUDE.md 貼進自己的 CLAUDE.md。但其中 50% 的內容已經是 Claude Code 內建行為，等於花 Token 重複說一樣的話。
2. **原始碼比對是唯一可靠的判斷方式**：沒有讀 `prompts.ts`，就不可能知道「Simplicity First」是否已內建。靠直覺判斷會導致不必要的 Token 浪費或遺漏真正有價值的補充。
3. **CLAUDE.md 的真正價值在「補差距」而非「強調」**：重複 system prompt 已有的內容頂多起到「強調」作用，但代價是每次 API call 都多消耗 Token。更好的策略是只加 system prompt 沒有的、你個人在意的行為規範。
4. **ant-only 的指令揭示了「外部用戶的缺口」**：`prompts.ts:211` 的「完成前跑測試」只對 Anthropic 內部用戶啟用。這意味著外部用戶如果不自己加入類似指令，模型預設不會主動驗證。

## 待補充（Open Questions）

- Karpathy 準則在不同模型（Claude Opus vs Sonnet vs Haiku）上的效果是否一致？較小的模型是否更需要這類明確指令？建議搜尋：`karpathy guidelines model size effect`
- Claude Code 的 `codeStyleSubitems` 是否會隨版本更新而變化？如果未來版本移除了某些內建規則，之前不需要的 CLAUDE.md 補充可能又變得必要。建議搜尋：`claude code prompts.ts changelog`
- 「不確定就問」的指令是否會導致模型過度頻繁地停下來詢問，反而降低效率？需要找到「自主執行」和「提前溝通」之間的最佳平衡點。建議搜尋：`claude code ask frequency user experience`
- ant-only 的 `codeStyleSubitems`（如不寫註解、完成前驗證）是否值得外部用戶手動加入？這些是否因為外部模型行為不同才被限制？建議搜尋：`claude code ant only prompt differences`
- 除了 Karpathy 準則，還有哪些社群流行的 CLAUDE.md 模板？它們與內建 prompt 的重疊度如何？建議搜尋：`awesome claude code claudemd templates`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，確立基礎知識 | Karpathy 四條準則名稱（Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution）；`prompts.ts` 中 `codeStyleSubitems` 的位置（:200-203）；`AskUserQuestion` 的觸發條件 |
| **理解（半被動）** | 解釋概念的含義及關聯 | 準則 2 和 3 與內建 prompt 是「重疊關係」不是「補充關係」——因為 Anthropic 團隊顯然參考了這類社群準則來設計 system prompt。準則 1 和 4 是「補差距」——填補內建 prompt 中「不確定時的行為」和「結構化驗證」的缺口。 |
| **分析（主動）** | 檢驗論點、找出假設 | 本研究假設「重複的指令不會強化效果」，但實際上 LLM 可能因為看到多次相同指令而更嚴格遵守。這個假設需要 A/B 測試驗證。另一個假設是「Token 節省比行為強化更重要」——在上下文視窗很大的模型上，Token 成本可能不是瓶頸。 |
| **應用（主動）** | 規劃執行方案 | (1) 立即從 CLAUDE.md 中移除與 `prompts.ts:200-203` 重疊的規則，只保留準則 1 和 4 的補充部分；(2) 建立 `~/.claude/rules/think-and-verify.md` 存放精簡版的行為準則 |
| **評估（主動）** | 判斷方案優劣 | 「整篇照搬」方案：簡單但浪費 ~200 tokens/call。「精簡補差距」方案：省 Token 但需要讀原始碼才能判斷。「完全不加」方案：省 Token 但失去準則 1、4 的補充價值。建議選「精簡補差距」——投入一次性的研究成本，換取長期的 Token 效率。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「覆蓋」的定義是什麼？「措辭接近」是否等同「行為效果相同」？LLM 對同義但不同措辭的指令，遵守程度是否有差異？
- **假設**：本文假設 Claude Code 的 system prompt 不會被用戶覆蓋或修改。但如果用戶用 `CLAUDE_CODE_SIMPLE=true` 環境變數啟動（`prompts.ts:450-453`），所有內建 prompt 都會被替換為極簡版——此時 Karpathy 準則就全部變成必要的了。
- **證據**：我們只做了文字比對，沒有做行為測試。「prompts.ts 有寫」不等於「模型在實際執行中嚴格遵守」。需要用 eval 框架量化遵守率。
- **觀點**：反對意見可能是「重複強調有助於模型更嚴格遵守」——這在 prompt engineering 中是已知的技巧（repetition for emphasis）。代價是 Token，收益是更高的遵守率。
- **後果**：若大量用戶依照本文建議移除 CLAUDE.md 中的重疊規則，但 Anthropic 未來版本移除了某些內建規則，這些用戶的模型行為可能會退化而不自知。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 移除重疊規則後，如果內建 prompt 在未來版本中變更，用戶可能失去這些行為保障而不自知。
2. **什麼情況下會失敗？** — (a) 使用 `CLAUDE_CODE_SIMPLE=true` 時內建 prompt 被替換為極簡版；(b) 未來 Claude Code 版本移除 `codeStyleSubitems` 中的某些規則；(c) 使用非 Anthropic 的 API provider（Bedrock/Vertex）時 system prompt 可能有差異。
3. **有沒有更好的替代方案？** — 折衷方案：保留所有四條準則但用 **有條件規則**（`paths:` frontmatter）限定只在操作程式碼檔案時注入，減少非程式碼對話的 Token 消耗。

## 相關連結（Related）

- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — CLAUDE.md 和 Rules 的載入時機、快取機制、Token 注入層完整分析
- [[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]] — Reza Rezvani 對 Karpathy 四原則的實測：Simplicity First 最有效、Goal-Driven 最弱
- [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] — 七位專家的 CLAUDE.md 最佳實踐比較
- [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]] — 漸進式揭露（Progressive Disclosure）策略，避免 CLAUDE.md 膨脹
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — Claude Code 原始碼洩漏解析，涵蓋 system prompt 結構

## References

- [Karpathy Guidelines CLAUDE.md](https://github.com/forrestchang/andrej-karpathy-skills/blob/main/CLAUDE.md)（GitHub 34K stars）
- Claude Code 反編譯原始碼 `src/constants/prompts.ts`（`getSimpleDoingTasksSection()`, `codeStyleSubitems`）
