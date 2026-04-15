---
title: "CLAUDE.md 最佳實踐全攻略：七位專家的痛點、方案與 Skills 按需載入實戰比較"
date: 2026-04-15
category: AI
tags:
  - "#ai/claude-code"
  - "#ai/context-engineering"
  - "#ai/prompt-engineering"
  - "#ai/skill-design"
  - "#tools/cli"
  - "#productivity/workflows"
source: "https://www.humanlayer.dev/blog/writing-a-good-claude-md"
source_type: article
author: "Kyle (HumanLayer), Anthropic, Andrej Karpathy, Gábor Mészáros, Ran Isenberg, Alexander Opalic, Tyler Folkman"
status: notes
links:
  - "[[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]]"
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
  - "[[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]]"
  - "[[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]"
  - "[[2026-03-30-BORIS-CHERNY-HIDDEN-CLAUDE-CODE-FEATURES]]"
  - "[[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]]"
---

## 摘要（Summary）

本文綜合七位業界專家與官方文件對 CLAUDE.md 撰寫最佳實踐的研究，涵蓋從「為什麼 Claude 會忽略你的 CLAUDE.md」的根本原因，到「Skills 能否取代 CLAUDE.md 實現按需載入」的前沿實驗數據。核心發現：**CLAUDE.md 不是越詳細越好，LLM 的指令遵循能力在 150-200 條指令後開始均勻衰減**；最佳策略是「CLAUDE.md 放事實、Skills 放流程」的混合架構，但 Skills 的自動觸發有 20-40% 失敗率（Vercel 實驗），關鍵流程仍需手動觸發。本文整理了每位專家的獨特痛點與解決方案，並歸納出經過交叉驗證的最佳實踐清單。

## 關鍵洞察（Key Insights）

- **指令預算有限** — LLM 可靠遵循約 150-200 條指令，Claude Code 系統提示已佔 ~50 條，你只剩 100-150 條額度（Kyle, HumanLayer 2025）
- **指令衰減是均勻的** — 不是選擇性忽略某些規則，而是所有規則的遵循率一起下降（Kyle, HumanLayer 2025）
- **Skills 按需載入可節省 82% tokens** — 但自動觸發不可靠，56% 從未被調用（Alexander Opalic 引用 Vercel 實驗 2026）
- **Karpathy 用不到 70 行約束 LLM 行為**，而非注入知識（Karpathy 2025）
- **官方金句**：「當 CLAUDE.md 裡某段內容從『事實』變成『流程』，就該移到 Skill」（Anthropic 2025-2026）
- **MUST 比 prefer 有效** — 指令式語言（prescriptive）的遵從率顯著高於建議式語言（Gábor Mészáros 2026）

---

## 第一章：研究來源總覽

| # | 文章 | 作者 | 身份 | 發表時間 | 定位 |
|---|------|------|------|---------|------|
| 1 | [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) | Kyle | HumanLayer 創辦人 | 2025-11-25 | 理論派：深入分析 LLM 為何忽略指令 |
| 2 | [Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices) | Anthropic | 官方 | 2025 末首發，持續更新 | 最權威完整的官方指南 |
| 3 | [Karpathy's CLAUDE.md Skills Guide](https://antigravity.codes/blog/karpathy-claude-code-skills-guide) | Andrej Karpathy（Forrest Chang 整理） | 前 OpenAI / Tesla AI 主管 | 2025 中（原始分享） | AI 大神的行為準則派 |
| 4 | [CLAUDE.md From Basic to Adaptive](https://dev.to/cleverhoods/claudemd-best-practices-from-basic-to-adaptive-9lm) | Gábor Mészáros | 開發者 / Reporails CLI 作者 | 2026 初 | 成熟度模型派（L0-L6） |
| 5 | [Lessons From Real Projects](https://ranthebuilder.cloud/blog/claude-code-best-practices-lessons-from-real-projects/) | Ran Isenberg | AWS Serverless Hero / 首席雲架構師 | 2026 初 | 實戰派：三個真實專案教訓 |
| 6 | [Stop Bloating Your CLAUDE.md](https://alexop.dev/posts/stop-bloating-your-claude-md-progressive-disclosure-ai-coding-tools/) | Alexander Opalic | 開發者 | 2026-01-18 | 漸進式揭露實作派 |
| 7 | [Claude Skills Solve the Context Window Problem](https://tylerfolkman.substack.com/p/the-complete-guide-to-claude-skills) | Tyler Folkman | JobNimbus 技術長（CTO） | 2026 | Skills 深度剖析 |

---

## 第二章：各專家痛點與解決方案

### 2.1 Kyle（HumanLayer）— 2025-11-25

> [!warning] 核心痛點
> **Claude 會忽略 CLAUDE.md 的內容。** 根本原因是 Claude Code 的系統提示（system prompt）包含一句話：「this context may or may not be relevant to your tasks. You should not respond unless highly relevant.」——這導致 Claude 主動跳過不普遍適用的指令。

**痛點清單：**
- CLAUDE.md 太長導致指令遵循率全面下降（不是選擇性忽略，是均勻衰減）
- `/init` 自動生成的內容品質差，壞的引導會級聯放大錯誤
- 程式碼片段放進 CLAUDE.md 容易過時（stale）

**解決方案：**

| 方案 | 做法 |
|------|------|
| **精簡至上** | 根檔案 <60 行，只放普遍適用的內容 |
| **三要素框架** | 圍繞 WHAT（技術棧）、WHY（專案目的）、HOW（執行細節）組織 |
| **漸進式揭露** | 用 `agent_docs/` 目錄存放補充文件，讓 Claude 自行判斷是否相關 |
| **用指標取代片段** | 用 `file:line` 指向程式碼，避免片段過時 |
| **不要自動生成** | 手動精心撰寫，不用 `/init` |
| **不做 Linter** | 用 ESLint/Biome 做格式檢查，不浪費 LLM |

```
agent_docs/
  ├── building_the_project.md
  ├── running_tests.md
  ├── code_conventions.md
  └── service_architecture.md
```

### 2.2 Anthropic 官方 — 2025-2026（持續更新）

> [!warning] 核心痛點
> **開發者容易掉入「過度指定的 CLAUDE.md」陷阱**——檔案太長，重要規則被噪音淹沒，Claude 反而忽略真正重要的指令。

**痛點清單：**
- 「廚房水槽式 Session」：一個 session 做太多不相關的事，context 被無關資訊填滿
- 反覆修正但越改越錯：context 被失敗方案污染
- 信任-驗證落差：產出看起來對但實際沒處理邊界情況

**解決方案：**

| 方案 | 做法 |
|------|------|
| **精簡測試法** | 「刪掉這行會導致 Claude 犯錯嗎？不會就砍」 |
| **禁令配方向** | 「不要用 `--legacy-peer-deps`；改用更新套件解決衝突」 |
| **Include/Exclude 表** | 明確列出該放與不該放的內容 |
| **`@import` 語法** | `@docs/git-instructions.md` 引用外部文件 |
| **多層級檔案** | `~/.claude/CLAUDE.md`（全域）→ `./CLAUDE.md`（專案）→ 子目錄（按需） |
| **升級規則** | 同一指令在對話中說超過兩次 → 寫進 CLAUDE.md |
| **強調語法** | 加 `IMPORTANT` 或 `YOU MUST` 提升遵循率 |
| **Skills 分離** | CLAUDE.md 放事實，Skills 放程序性知識 |

**官方 Include/Exclude 表：**

| 該放（Include） | 不該放（Exclude） |
|-----------------|-------------------|
| Claude 猜不到的 Bash 指令 | Claude 從程式碼能推斷的東西 |
| 與預設不同的程式碼風格規則 | Claude 已知的標準語言慣例 |
| 測試指令與偏好的測試框架 | 詳細 API 文件（改用連結） |
| Repo 禮儀（分支命名、PR 規範） | 經常變動的資訊 |
| 專案特有的架構決策 | 冗長教學或教程 |
| 開發環境怪癖（必要的 env vars） | 逐檔描述 codebase |
| 常見陷阱或非直覺行為 | 不言自明的做法（如「寫乾淨的程式碼」） |

### 2.3 Andrej Karpathy — 2025

> [!warning] 核心痛點
> **LLM 有四種頑固的壞習慣**：（1）靜默假設不問問題、（2）過度工程化與推測性抽象、（3）「順便重構」污染 diff、（4）沒有明確的成功標準就亂做。

**痛點清單：**
- LLM 做出隱含的解釋選擇卻不告知使用者
- 200 行能寫成 50 行但 LLM 偏好冗長方案
- 修一個 bug 時順便改格式、重構不相關的程式碼
- 「review and improve the code」這種指令沒有可驗證的目標

**解決方案 — 四大行為準則（不到 70 行）：**

```markdown
## 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them.
- If a simpler approach exists, say so.
- If something is unclear, stop. Name what's confusing.

## 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" that wasn't requested.
- No error handling for impossible scenarios.
- If 200 lines could be 50, rewrite it.

## 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice dead code, mention it — don't delete it.

## 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests, then make them pass"
- "Fix the bug" → "Reproduce it in a test, then fix"
- "Refactor X" → "Ensure tests pass before and after"
```

> [!note] Karpathy 的獨特之處
> 他的 CLAUDE.md **完全不放技術棧資訊**，只做「性格塑造（Behavioral Shaping）」。其他專家都在教你放什麼資訊，Karpathy 教你怎麼約束 LLM 的行為模式。

**反模式對照表：**

| 問題 | 表現 | 解法 |
|------|------|------|
| 隱藏假設（Hidden Assumptions） | 靜默假設範圍不問問題 | 列出假設，請求澄清 |
| 過度工程化（Over-Engineering） | 簡單計算用策略模式（Strategy Pattern） | 保持最小直到複雜度真正需要 |
| 風格漂移（Style Drift） | 修 bug 時順便重排格式 | 只改與問題相關的行 |
| 弱成功標準（Weak Success Criteria） | 「Review and improve the code」 | 「Write test → make pass → verify regressions」 |

### 2.4 Gábor Mészáros — 2026 初

> [!warning] 核心痛點
> **大多數 CLAUDE.md 停留在 L1-L2 水準**：有檔案但組織混亂，建議式語言（「prefer TypeScript」）被 LLM 忽略，單一檔案無法應對 monorepo 中不同成熟度的元件。

**痛點清單：**
- 建議式語言遵從率低
- 單一 CLAUDE.md 無法差異化引導 monorepo 的不同元件
- 缺乏成熟度自評框架，不知道從何改進

**解決方案 — 六級成熟度模型（L0-L6）：**

| 等級 | 名稱 | 特徵 | 適用場景 |
|------|------|------|---------|
| L0 | Absent | 沒有指令檔 | 一次性專案 |
| L1 | Basic | 有檔案、有版控 | 起步階段 |
| L2 | Scoped | 用 RFC 2119 語言（MUST/MUST NOT） | 小專案，明確慣例 |
| L3 | Structured | 多檔案引用，按關注點分離 | 團隊協作 |
| L4 | Abstracted | 路徑作用域載入（編輯 `src/api/` 載入 API 規則） | Monorepo |
| L5 | Maintained | L4 + 定期維護、過期追蹤 | 長期維運 |
| L6 | Adaptive | Skills + MCP 動態載入 | 進階自動化 |

> [!tip] 關鍵洞見
> **「MUST use TypeScript strict mode」比「Prefer TypeScript」有效得多。** 指令式語言（prescriptive）在 agent 遵從率上顯著優於建議式語言（suggestive）。

**自評指標：**

| 指標 | 最低等級 |
|------|---------|
| 指令檔存在 | L1 |
| 明確約束語句 | L2 |
| 多檔案引用 | L3 |
| 路徑特定規則載入 | L4 |
| 主動維護紀律 | L5 |
| Skills 或 MCP 整合 | L6 |

### 2.5 Ran Isenberg（AWS Serverless Hero）— 2026 初

> [!warning] 核心痛點
> **領域專業才是瓶頸，不是工具。** 在三個真實專案中發現：AI 無法主動識別你的盲點（安全、SEO、合規），你必須靠自己的專業來引導它。

**三個真實專案教訓：**

| 專案 | 規模 | 做法 | 痛點 | 教訓 |
|------|------|------|------|------|
| ranthebuilder.cloud | 中 | 基本 CLAUDE.md | 漏掉 SEO、GA、安全硬化 | 需主動搜尋社群 Skills 補盲點 |
| Propel（看板 App） | 大 | BMAD 方法論先規劃 | 無（提前發現 36 個流程 + 安全風險） | 完整規劃值得投資 |
| mac-folder-sync | 小 | 跳過規劃只用 Plan Mode | 漏掉安全問題、邊界情況 | Plan Mode 需要你主動問難問題 |

**解決方案：**

| 方案 | 做法 |
|------|------|
| **六要素 CLAUDE.md** | 專案概述、技術棧、指令、目錄結構、程式碼慣例、重要規則 |
| **控制在 200 行內** | 超過就用 Skills 動態引入 |
| **偏好 Skills 而非 MCP** | 「我能讀 Skill 文本、檢查安全問題、理解它告訴 Claude 什麼」 |
| **大專案用 BMAD** | 寫程式前先做完整的規格規劃 |
| **主動搜尋社群 Skills** | Claude 不會主動建議，你要自己找 |

### 2.6 Alexander Opalic — 2026-01-18

> [!warning] 核心痛點
> **2000+ 行的 CLAUDE.md 在 session 開始前就吃掉一半的 context 預算。** 而且 Claude 每次 session 都犯同樣的錯，因為規則太多反而全部失效。

**痛點清單：**
- 2000+ 行 CLAUDE.md（風格指南 200 行、架構決策 150 行、陷阱 300 行、測試慣例 100 行）
- 工作開始前就消耗大量 token
- Skills 自然觸發不可靠

**解決方案 — 50 行 CLAUDE.md + 漸進式揭露：**

```markdown
# CLAUDE.md（~50 行）
- 專案描述
- 必要指令（dev server、lint、type check）
- 技術棧
- 目錄結構
- 指向 /docs/ 的指標

# IMPORTANT: 開始任務前先識別哪些 docs 相關並讀取
```

```
/docs/
  ├── nuxt-content-gotchas.md     # 15 條血淚教訓
  ├── nuxt-component-gotchas.md   # Vue 陷阱
  ├── testing-strategy.md         # 測試策略
  └── SYSTEM_KNOWLEDGE_MAP.md     # 架構總覽
```

> [!important] Vercel Agent Evals 的反面實驗
> - AGENTS.md 內嵌壓縮索引 → **100% pass rate**
> - Skills 自然觸發 → 最高 **79% pass rate**，**56% 從未被調用**
> - **結論：Skills 的自動觸發不完全可靠**，不能完全取代 CLAUDE.md

**三大原則：**
1. **如果工具能強制執行，就不要寫文字說明** — ESLint、TypeScript、Prettier、husky pre-commit hooks
2. **CLAUDE.md 只放通用 context** — 50 行以內
3. **用 `/docs/` + custom agents 做情境式載入**

### 2.7 Tyler Folkman（JobNimbus CTO）— 2026

> [!warning] 核心痛點
> **傳統做法在 session 開始時就前置載入 5,000+ tokens 的工作流 context**，還沒開始工作就吃掉大量 context window。MCP 更誇張——光是描述 capabilities 就消耗數萬 tokens。

**解決方案 — Skills 的三層 Token 效率模型：**

| 層級 | 內容 | Token 成本 | 載入時機 |
|------|------|-----------|---------|
| Tier 1 | 名稱 + description（metadata） | ~30-50 tokens/skill | 每次 session 開始 |
| Tier 2 | SKILL.md 完整指令 | 按需 | 觸發時才載入 |
| Tier 3 | 附屬資源（模板、腳本、範例） | 按需 | 執行時才載入 |

**實測數據：**
- 傳統 CLAUDE.md：session 開始前載入 **5,000+ tokens**
- Skills 方式：每個 skill 只載 **30-50 tokens** metadata
- ClaudeFast Code Kit（20+ skills）：每 session 節省約 **15,000 tokens**（**82% 改善**）

**早期影響指標（Anecdotal）：**
- 文件格式化：使用品牌指南 skill 節省 60-70% 時間
- 程式碼審查：自訂 review hooks 減少 40% 修訂循環
- 新人 onboarding：團隊 skill 套件加速 2-3x
- 合規：自動化強制執行 ~100% 遵循率 vs 手動文件 ~60%

---

## 第三章：核心共識（七位專家都同意的事）

### 3.1 精簡至上 — 少即是多

| 專家 | 建議行數 | 理由 |
|------|---------|------|
| Kyle (2025) | <60 行（根檔案） | 150-200 指令上限，系統提示已佔 ~50 |
| Anthropic (2025-2026) | 「盡量短」 | 每行都要通過「刪了會出錯嗎？」測試 |
| Karpathy (2025) | <70 行 | 只放行為準則，不放知識 |
| Ran Isenberg (2026) | <200 行 | 超過就動態引入 |
| Alexander Opalic (2026) | ~50 行 | 2000+ 行曾導致全面失效 |

### 3.2 必備三要素：WHAT / WHY / HOW

| 面向 | 內容 | 提到的來源 |
|------|------|-----------|
| **WHAT** | 技術棧、專案結構、目錄地圖 | 全部 7 位 |
| **WHY** | 專案目的、架構決策背景 | Kyle, 官方, Ran |
| **HOW** | build/test/lint 指令、工作流程 | 全部 7 位 |

### 3.3 不要用 LLM 做格式檢查

- **Kyle (2025)**：明確反對，應用確定性工具
- **官方 (2025-2026)**：「Claude 已知的標準慣例不需要寫」
- **Karpathy (2025)**：「Match existing style, even if you'd do it differently」
- **Opalic (2026)**：「If a tool can enforce it, don't write prose about it」

### 3.4 禁令要搭配替代方案

- **官方**：每個禁止配一個方向
- **Karpathy**：困惑時停下來說出困惑點
- **Gábor**：用 MUST NOT 明確禁止，同時用 MUST 指出替代路徑

---

## 第四章：核心分歧

### 4.1 `/init` 自動生成：正反兩派

| 立場 | 代表 | 理由 |
|------|------|------|
| **強烈反對** | Kyle (2025) | CLAUDE.md 是最高槓桿點，壞引導會級聯放大錯誤 |
| **推薦使用** | Anthropic 官方 (2025-2026) | `/init` 分析 codebase 偵測 build 系統和測試框架，提供好的起點再精煉 |
| **中立偏避** | Ran Isenberg (2026) | 用 BMAD 方法論先規劃，再手寫 CLAUDE.md |
| **條件性支持** | Gábor (2026) | 可做為 L1 起點，但必須升級到 L2+ |

### 4.2 行為約束 vs 知識注入

| 路線 | 代表 | 內容 |
|------|------|------|
| **行為準則派** | Karpathy (2025) | 不放技術棧，只約束四種行為模式 |
| **知識注入派** | Kyle, 官方, Ran | 放技術棧、指令、架構決策 |
| **兩者皆要** | Opalic (2026), Gábor (2026) | CLAUDE.md 放通用知識 + Skills 放行為/流程 |

### 4.3 檔案結構策略

| 策略 | 代表 | 做法 |
|------|------|------|
| **單一精簡檔** | Karpathy (2025) | 一個 <70 行的檔案 |
| **引用式** | Kyle (2025), 官方 | CLAUDE.md + `@import` 引用 `agent_docs/` |
| **路徑作用域** | Gábor (2026) | 子目錄放專屬 CLAUDE.md（L4 等級） |
| **docs + agents** | Opalic (2026) | 50 行 CLAUDE.md + `/docs/` + custom agents |
| **Skills 架構** | Tyler (2026) | CLAUDE.md 最小化 + Skills 做一切 |

---

## 第五章：Skills 能否取代 CLAUDE.md？按需載入深度研究

### 5.1 載入機制的根本差異

根據 [Anthropic 官方 Skills 文件](https://code.claude.com/docs/en/skills) 與 [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] 的原始碼分析：

| 特性 | CLAUDE.md | Skills |
|------|-----------|--------|
| **何時載入** | session 啟動時**全量載入**，memoize 快取 | 只載入 description（~30-50 tokens/skill），**內容按需載入** |
| **token 成本** | 全文每次都計入 context | Tier 1: metadata ~30-50 tokens；Tier 2: 觸發時載全文；Tier 3: 附屬資源按需 |
| **觸發方式** | 自動、永遠存在 | Claude 自動判斷 or 使用者 `/skill-name` 手動觸發 |
| **熱載入** | **不支援**（memoize 快取，需 `--resume` 刷新） | **支援**（chokidar 檔案監控，修改即時生效） |
| **compaction 行為** | 隨對話壓縮 | 壓縮後重新附加，保留前 5,000 tokens，合計上限 25,000 tokens |
| **適合放什麼** | 通用事實、永遠適用的規則 | 程序性知識、特定工作流、領域專業 |

### 5.2 官方對分工的精確定義

> [!quote] Anthropic 官方
> 「Create a skill when you keep pasting the same playbook, checklist, or multi-step procedure into chat, or when **a section of CLAUDE.md has grown into a procedure rather than a fact**. Unlike CLAUDE.md content, a skill's body loads only when it's used, so long reference material costs almost nothing until you need it.」

**判斷標準：事實（Fact）vs 流程（Procedure）**

| 放 CLAUDE.md（事實） | 移到 Skills（流程） |
|---------------------|-------------------|
| 技術棧版本（Next.js 15, Drizzle） | 部署流程（build → test → push） |
| build/test/lint 指令 | GitHub issue 修復 SOP |
| 分支命名規範 | Code review checklist |
| 架構決策（為什麼用 X 不用 Y） | 遷移工作流程（React → Vue） |
| 非預設慣例（ES modules, not CommonJS） | 特定領域知識（API 設計規範、安全審查） |

### 5.3 實驗數據：Skills 按需載入的效能與限制

**正面數據（Tyler Folkman 2026）：**
- 傳統 CLAUDE.md：session 開始前載入 **5,000+ tokens**
- Skills 方式：每個 skill 只載 **30-50 tokens** metadata
- ClaudeFast Code Kit（20+ skills）：每 session 節省約 **15,000 tokens**（**82% 改善**）

**反面數據（Alexander Opalic 2026，引用 Vercel Agent Evals）：**

| 方式 | Pass Rate | 備註 |
|------|-----------|------|
| AGENTS.md 內嵌壓縮索引 | **100%** | 全量載入，但精簡 |
| Skills 自然觸發 | **最高 79%** | 且 **56% 從未被調用** |
| Skills 基線（不觸發時） | ~56% | 與不用 Skills 相當 |

> [!warning] 關鍵發現
> Skills 的自動觸發（model-invoked）有 **20-40% 失敗率**。Claude 判斷 skill 是否相關依賴 description 的品質，如果 description 關鍵字不匹配使用者的表述，skill 就不會被載入。

### 5.4 Skill 內容的生命週期（官方細節）

根據 [官方文件](https://code.claude.com/docs/en/skills)：

1. **Session 開始**：只載入所有 skill 的 name + description（budget = context window 的 1%，fallback 8,000 字元）
2. **觸發時**：rendered SKILL.md 以單一訊息進入對話，**整個 session 都存在**
3. **Auto-compaction 時**：重新附加最近調用的 skill（前 5,000 tokens），合計上限 25,000 tokens，從最新的開始填充
4. **`disable-model-invocation: true`**：description 完全不載入 context，不佔任何 token

**控制誰可以觸發：**

| Frontmatter | 使用者可觸發 | Claude 可觸發 | 載入時機 |
|-------------|------------|--------------|---------|
| （預設） | 是 | 是 | description 永遠在 context，觸發時載入全文 |
| `disable-model-invocation: true` | 是 | 否 | description 不在 context，使用者手動觸發時才載入 |
| `user-invocable: false` | 否 | 是 | description 永遠在 context，Claude 判斷後自動載入 |

### 5.5 最佳混合架構

```
CLAUDE.md（~50-100 行）
├── 專案概述（2-3 句）
├── 技術棧 + 版本號
├── 關鍵指令（dev/test/build/lint）
├── 通用規則（MUST/MUST NOT）
├── @docs/architecture.md（引用）
└── "IMPORTANT: 開始任務前先識別相關 docs 並讀取"

.claude/skills/
├── deploy/SKILL.md              ← disable-model-invocation: true（手動）
├── fix-issue/SKILL.md           ← disable-model-invocation: true（手動）
├── api-conventions/SKILL.md     ← Claude 自動載入（按需）
├── code-review/SKILL.md         ← Claude 自動載入（按需）
└── security-review/SKILL.md     ← Claude 自動載入（按需）
```

> [!tip] Skills 自動觸發優化技巧
> 根據官方文件，skill 的 `description` + `when_to_use` 合計上限 1,536 字元，且會被截斷。**將關鍵使用場景放在 description 開頭**（front-load the key use case），確保 Claude 能匹配到。

---

## 第六章：綜合最佳實踐（附來源標註）

### 必做（所有專案適用）

| # | 建議 | 來源 |
|---|------|------|
| 1 | **控制在 100-150 行以內** | Kyle (2025): 150-200 指令上限；Anthropic: 精簡；Karpathy (2025): <70 行 |
| 2 | **只放 Claude 猜不到的東西** | Anthropic (2025-2026):「Anything Claude can figure out by reading code → 排除」 |
| 3 | **用 MUST/MUST NOT 而非 prefer/should** | Gábor (2026): RFC 2119 語言，prescriptive 遵從率顯著更高 |
| 4 | **搭配驗證手段（測試/lint 指令）** | Anthropic (2025-2026):「Give Claude a way to verify its work — 最高槓桿」 |
| 5 | **禁令配替代方案** | Anthropic (2025-2026):「Pair every prohibition with a direction」 |
| 6 | **定期修剪** | Anthropic:「Treat CLAUDE.md like code: prune it regularly」；Kyle (2025): 指令衰減是均勻的 |
| 7 | **升級規則：重複說兩次就寫進去** | Anthropic (2025-2026):「If you have to repeat an instruction more than twice, promote it」 |

### 進階（中大型專案推薦）

| # | 建議 | 來源 |
|---|------|------|
| 8 | **加入 Karpathy 式行為準則** | Karpathy (2025): 四原則（Think → Simplicity → Surgical → Goal-Driven） |
| 9 | **漸進式揭露（`@import` + Skills）** | Kyle (2025): `agent_docs/`；Anthropic: `@path/to/import`；Opalic (2026): `/docs/` |
| 10 | **路徑作用域（子目錄 CLAUDE.md）** | Gábor (2026): L4 Abstracted；Anthropic: child CLAUDE.md on demand |
| 11 | **事實放 CLAUDE.md、流程放 Skills** | Anthropic (2025-2026): 官方分工定義；Tyler (2026): 三層 token 模型 |
| 12 | **關鍵 Skills 用 `disable-model-invocation: true`** | Opalic (2026): Vercel 實驗顯示自動觸發 56% 從未被調用；Anthropic: deploy 等有副作用的 skill |
| 13 | **用工具強制執行而非文字說明** | Opalic (2026):「If a tool can enforce it, don't write prose」；Kyle (2025): 不做 Linter |

### 避免

| # | 避免事項 | 來源 |
|---|---------|------|
| 1 | 不要放 Claude 從程式碼能推斷的東西 | Anthropic (2025-2026) |
| 2 | 不要放經常變動的資訊 | Anthropic (2025-2026) |
| 3 | 不要放冗長教學或 API 文件（用連結代替） | Anthropic (2025-2026), Kyle (2025) |
| 4 | 不要用 CLAUDE.md 做程式碼風格檢查 | Kyle (2025), Opalic (2026) |
| 5 | 不要完全依賴 Skills 自動觸發 | Opalic (2026): Vercel 實驗 56% 未觸發 |
| 6 | 不要用 `/init` 後就不管了 | Kyle (2025): 壞引導會級聯放大；Gábor (2026): 只是 L1 起點 |

---

## 第七章：漸進式揭露完整策略

### 7.1 三種揭露機制比較

| 機制 | Token 成本 | 可靠性 | 適用場景 |
|------|-----------|--------|---------|
| **`@import` 引用** | 啟動時全量載入（比全塞少但仍前置） | 100%（一定被讀到） | 通用但不想塞主檔的內容 |
| **Skills（auto-trigger）** | ~30-50 tokens metadata，觸發時才載全文 | 60-79%（Vercel 實驗） | 程序性知識、可被自動匹配的工作流 |
| **Skills（manual `/name`）** | 0 tokens 直到手動觸發 | 100%（你自己觸發） | 有副作用的操作（deploy, commit） |
| **`/docs/` + 指示句** | 取決於 Claude 是否遵循指示 | 80-90%（需在 CLAUDE.md 加 IMPORTANT） | 領域 gotchas、架構文件 |

### 7.2 從 2000 行瘦身到 50 行的遷移路徑

```
Before:
├── CLAUDE.md（2000+ 行）
│   ├── 風格指南（200 行）         → 移到 ESLint/Prettier
│   ├── 架構決策（150 行）         → 移到 docs/architecture.md + @import
│   ├── 陷阱集（300 行）           → 移到 docs/gotchas.md + @import
│   ├── 測試慣例（100 行）         → 移到 .claude/skills/testing/
│   ├── 部署流程（80 行）          → 移到 .claude/skills/deploy/
│   ├── API 規範（200 行）         → 移到 .claude/skills/api-conventions/
│   └── 其他（970 行）             → 審視是否需要，大部分刪除

After:
├── CLAUDE.md（~50 行）
├── docs/
│   ├── architecture.md
│   └── gotchas.md
└── .claude/skills/
    ├── deploy/SKILL.md
    ├── testing/SKILL.md
    └── api-conventions/SKILL.md
```

---

## 我的心得（My Takeaways）

1. **CLAUDE.md 是你與 AI 之間的契約**——寫太多等於沒寫，因為遵從率均勻下降。50-100 行是甜蜜點。
2. **Karpathy 的「性格塑造」思路值得所有人借鑑**——與其告訴 LLM 知識（它可以自己讀），不如約束它的行為（它自己改不了）。
3. **Skills 是未來但現在還不完美**——82% 的 token 節省很誘人，但 56% 未觸發的問題不容忽視。關鍵流程用手動觸發，非關鍵才用自動。
4. **Gábor 的 L0-L6 模型是最好的自評工具**——大部分人在 L1-L2，目標至少 L3，monorepo 需要 L4+。
5. **「如果工具能強制執行，就不要寫文字」**（Opalic 金句）——這一條能砍掉 CLAUDE.md 30-50% 的內容。

## 待補充（Open Questions）

- **Skills description 的最佳長度是多少？** 官方只說合計 1,536 字元上限，但沒有給出最佳實踐的字數。太短可能匹配不到，太長被截斷。需要實驗。
- **`@import` 引用的檔案在 compaction 時如何處理？** CLAUDE.md 本體會被壓縮，但 `@import` 引用的子檔案是否也被保留？官方文件未明確說明。
- **Vercel 的 agent evals 完整方法論？** Opalic 引用了 Vercel 的數據（100% vs 79%），但原始實驗的完整設計、受測 skill 數量、評估標準等細節未公開。需要找到原始來源。
- **多層級 CLAUDE.md 的合併規則？** 官方說高層覆蓋低層，Array 類型合併——但具體合併是 append 還是 deep merge？衝突時的行為是什麼？可參考 [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]。
- **Skills 在大型團隊（50+ 工程師）的管理經驗？** 目前所有經驗都來自個人或小團隊。大團隊的 skill 命名衝突、版本管理、品質控制如何處理？
- **Karpathy 四原則在非 Claude 系統（Cursor, Copilot）的效果？** 行為準則理論上是模型無關的，但不同模型的指令遵循特性不同，效果可能差異很大。
- **CLAUDE.md 指令衰減的精確曲線？** Kyle 說「150-200 條後衰減」，但衰減是線性、指數、還是階梯式？不同模型版本之間是否有差異？建議搜尋：`LLM instruction following scaling degradation benchmark`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | 150-200 指令上限、系統提示佔 ~50 條、Skills metadata ~30-50 tokens、Vercel 實驗 56% 未觸發、Karpathy 四原則名稱、官方「事實 vs 流程」分工原則 |
| **理解（半被動）** | 解釋概念的含義及關聯 | CLAUDE.md 的指令衰減不是「重要的留、不重要的丟」，而是**所有指令的遵循率一起均勻下降**——這解釋了為什麼「多寫一條好建議」反而會讓既有的好建議也失效。Skills 的三層載入（metadata → 指令 → 資源）是經典的漸進式揭露（Progressive Disclosure）模式，與 UI 設計中的同名概念完全一致。 |
| **分析（主動）** | 檢驗論點、拆解假設 | Kyle 的「150-200 指令上限」缺乏嚴格的實驗方法論——是哪個模型版本？什麼任務類型？衰減曲線是什麼形狀？Vercel 的 agent evals 數據（56% 未觸發）也是二手引用，原始實驗條件不明。Karpathy 的行為準則「biases toward caution over speed」——這在大型重構任務中可能過於保守。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | **立即可做：**（1）審視自己的 CLAUDE.md 行數，砍到 100 行以下（2）將所有 deploy/commit 類 skill 加上 `disable-model-invocation: true`（3）在 CLAUDE.md 頂部加入 Karpathy 四原則的精簡版 |
| **評估（主動）** | 判斷多個方案的優劣 | 純 CLAUDE.md 方案（100% 可靠但佔 context）vs 純 Skills 方案（省 token 但 56% 未觸發）vs 混合方案（最佳但維護複雜度高）——**混合方案勝出，但要接受「維護兩套系統」的成本**。對小專案（<5 檔案）可能 overhead 不值得。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「指令遵循」的定義是什麼？是「完全遵守」還是「部分遵守也算」？不同定義下 150-200 上限會如何變化？
- **假設**：所有建議都假設 CLAUDE.md 在 session 開始時被完整讀取——但如果未來 Anthropic 改用按需載入（像 Skills 一樣），這些建議是否全部失效？
- **證據**：Karpathy 的四原則缺乏 A/B 測試數據。「最有效的是 Simplicity First」這個結論來自 Reza Rezvani 的個人觀察，樣本量 n=1。
- **觀點**：反對者可能說：「精簡 CLAUDE.md 只是症狀治療——真正的解決方案是讓模型支援更大的 context window 或更好的指令優先級機制。」
- **後果**：如果團隊全面採用 Skills 架構但忽略 description 品質，12 個月後可能發現：核心 skills 從未被自動觸發、新成員不知道有哪些 skills 可用、維護成本高於收益。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — Skills 自動觸發的 56% 未觸發率意味著：你認為 Claude 知道但它其實不知道。這比「沒有設定 skill」更危險，因為你會有虛假的安全感。
2. **什麼情況下會失敗？** — 當 skill 數量 >20 且 description budget 被截斷時；當使用者的表述與 description 關鍵字不匹配時；當 auto-compaction 丟棄已觸發但較早的 skill 時。
3. **有沒有更好的替代方案？** — Opalic 的「CLAUDE.md + /docs/ 指示句」方案在 Vercel 測試中達到 100% pass rate，不依賴 Skills 的觸發機制。權衡：佔用更多啟動 context 但可靠性更高。適合在可靠性 > token 效率的場景使用。

## 相關連結（Related）

- [[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]] — Karpathy 四原則的實測深度解析，本文第 2.3 節的延伸
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — CLAUDE.md 與 Skills 的原始碼級載入機制分析，驗證本文的「全量 vs 按需」論點
- [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]] — 官方 Skills 文件的完整筆記，本文第五章的基礎
- [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — 配置層級指南，補充本文未深入的多層級合併規則
- [[2026-03-30-BORIS-CHERNY-HIDDEN-CLAUDE-CODE-FEATURES]] — Boris Cherny（Claude Code 創造者）的隱藏功能解析
- [[2026-04-09-ANTHROPIC-SHIPPED-THREE-OF-FIVE-HARNESS-LAYERS]] — Anthropic Harness 架構的整體觀，Skills 是其中的能力層
- [[2026-03-17-LESSONS-FROM-BUILDING-CLAUDE-CODE-HOW-WE-USE-SKILLS]] — Anthropic 團隊自己如何使用 Skills 的經驗
- [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]] — Alexander Opalic 的 CLAUDE.md 瘦身實戰，Vercel agent evals 的原始數據來源
- [[2026-01-27-VERCEL-AGENTS-MD-OUTPERFORMS-SKILLS-IN-AGENT-EVALS]] — Vercel 實驗原始報告，本文第五章引用的 100% vs 79% vs 56% 數據的一手來源
- [[2026-01-27-KARPATHY-GUIDELINES-VS-CLAUDE-CODE-BUILTIN-SYSTEM-PROMPT]] — 逐行比對 Karpathy 準則與 `prompts.ts`，準則 2/3 已內建、1/4 值得加入
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — 延伸研究：Skills/Commands/Subagents/Plugins 四機制比較與 description 工程最佳實踐

## References

- [Writing a Good CLAUDE.md — Kyle, HumanLayer (2025-11-25)](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [Best Practices for Claude Code — Anthropic 官方 (2025-2026)](https://code.claude.com/docs/en/best-practices)
- [Karpathy's CLAUDE.md Skills File Guide — Forrest Chang 整理 (2025-2026)](https://antigravity.codes/blog/karpathy-claude-code-skills-guide)
- [CLAUDE.md From Basic to Adaptive — Gábor Mészáros (2026)](https://dev.to/cleverhoods/claudemd-best-practices-from-basic-to-adaptive-9lm)
- [Claude Code Best Practices: Lessons From Real Projects — Ran Isenberg (2026)](https://ranthebuilder.cloud/blog/claude-code-best-practices-lessons-from-real-projects/)
- [Stop Bloating Your CLAUDE.md — Alexander Opalic (2026-01-18)](https://alexop.dev/posts/stop-bloating-your-claude-md-progressive-disclosure-ai-coding-tools/)
- [Claude Skills Solve the Context Window Problem — Tyler Folkman (2026)](https://tylerfolkman.substack.com/p/the-complete-guide-to-claude-skills)
- [Extend Claude with Skills — Anthropic 官方文件](https://code.claude.com/docs/en/skills)
- [CLAUDE.md Best Practices — Nick Babich, UX Planet (2026)](https://uxplanet.org/claude-md-best-practices-1ef4f861ce7c)
- [Writing the Best CLAUDE.md — Bex Tuychiev, DataCamp (2026-03-17)](https://www.datacamp.com/tutorial/writing-the-best-claude-md)
