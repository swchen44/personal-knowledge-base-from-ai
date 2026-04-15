---
title: "別再把 CLAUDE.md 塞爆了：AI 程式設計工具的漸進式揭露策略"
date: 2026-01-18
category: AI
tags:
  - "#ai/claude-code"
  - "#ai/context-engineering"
  - "#ai/prompt-engineering"
  - "#tools/cli"
  - "#productivity/workflows"
source: "https://alexop.dev/posts/stop-bloating-your-claude-md-progressive-disclosure-ai-coding-tools/"
source_type: article
author: "Alexander Opalic"
status: notes
links:
  - "[[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]]"
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
  - "[[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]]"
  - "[[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]"
  - "[[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]]"
---

## 摘要（Summary）

Alexander Opalic 提出一套實戰驗證的 CLAUDE.md 瘦身策略：將 2000+ 行的臃腫指令檔精簡為 ~50 行，透過「漸進式揭露（Progressive Disclosure）」機制——`/docs/` 目錄存放情境式知識、custom agents 處理特定領域、`/learn` skill 自動捕捉血淚教訓——來維持 context window 的效率。文章引用 Vercel 的 agent evals 實驗數據，證明「直接在指令檔內嵌壓縮索引」比「依賴 Skills 自動觸發」更可靠（100% vs 最高 79% pass rate，56% 的 skills 從未被調用）。核心哲學：**不要對抗無狀態（stateless），要設計與它協作的系統。**

## 關鍵洞察（Key Insights）

- **CLAUDE.md 應控制在 ~50 行** — 只放每個 session 都需要的通用 context：專案描述、技術棧、關鍵指令、目錄結構、文件指標 — 參見 [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]]
- **「如果工具能強制執行，就不要寫文字說明」** — 用 ESLint/TypeScript/Prettier 取代 200 行格式指南，改成一行：`Run pnpm lint:fix && pnpm typecheck after code changes`
- **Skills 自動觸發不可靠** — Vercel agent evals 顯示：AGENTS.md 內嵌索引 100% pass rate，skills 自然觸發最高 79%，56% 從未被調用
- **明確指示比隱式觸發更可靠** — 在 CLAUDE.md 加 `IMPORTANT: Read relevant docs below before starting any task` 的效果優於依賴 skills 的模糊觸發條件
- **`/learn` skill 建立自增長的知識庫** — 每次對話結束時，自動分析非顯而易見的洞察並寫入 `/docs/`，形成回饋循環（Feedback Loop）
- **Symlink 實現跨工具共享** — `ln -s CLAUDE.md agents.md` 讓 Claude Code、Copilot、Cursor 共用同一份設定

## 詳細內容（Details）

### 核心問題：臃腫的 CLAUDE.md

AI 程式設計工具是無狀態的（stateless）——每個 session 從零開始，沒有前一次對話的記憶。開發者的典型反應是「把所有東西都塞進 CLAUDE.md」，結果產生 2000+ 行的臃腫檔案：

- 風格指南（200 行）
- 架構決策（150 行）
- 陷阱集（300 行）
- 測試慣例（100 行）
- 其餘雜項

> [!warning] 後果
> 還沒開始工作，一半的 context 預算就被消耗了。而且 Claude 每次 session 還是犯同樣的錯——因為規則太多，全部都失效了。

### 解決方案：三層漸進式揭露架構

#### 第一層：精簡 CLAUDE.md（~50 行）

作者的實際 CLAUDE.md：

```markdown
# CLAUDE.md

Second Brain is a personal knowledge base using Zettelkasten-style wiki-links.

## Commands
pnpm dev          # Start dev server
pnpm lint:fix     # Auto-fix linting issues
pnpm typecheck    # Verify type safety

Run `pnpm lint:fix && pnpm typecheck` after code changes.

## Stack
- Nuxt 4, @nuxt/content v3, @nuxt/ui v3

## Structure
- `app/` - Vue application
- `content/` - Markdown files
- `content.config.ts` - Collection schemas

## Further Reading

**IMPORTANT:** Read relevant docs below before starting any task.

- `docs/nuxt-content-gotchas.md`
- `docs/testing-strategy.md`
- `docs/SYSTEM_KNOWLEDGE_MAP.md`
```

> [!important] 關鍵設計
> 末尾的 `IMPORTANT: Read relevant docs below before starting any task` 是整個系統運作的核心——沒有這句，Claude 不會主動查閱 `/docs/`。

#### 第二層：`/docs/` 情境式知識

```
docs/
├── nuxt-content-gotchas.md     # 15 條血淚教訓
├── nuxt-component-gotchas.md   # Vue 特定陷阱
├── testing-strategy.md         # 測試策略
└── SYSTEM_KNOWLEDGE_MAP.md     # 架構總覽
```

每個 gotcha 條目的格式範例：

```markdown
## Page Collection Queries: Use `stem` Not `slug`

The `slug` field doesn't exist in page-type collections.
Use `stem` (file path without extension) instead:

// ❌ Fails: "no such column: slug"
queryCollection('content').select('slug', 'title').all()

// ✅ Works
queryCollection('content').select('stem', 'title').all()
```

> [!tip] 可執行建議
> 對於訓練資料覆蓋率低的領域（如 Nuxt Content），需要在 CLAUDE.md 中加入明確的方向性指引：「If you encounter Nuxt Content API issues, read `docs/nuxt-content-gotchas.md` first.」

#### 第三層：Custom Agents

在 `.claude/agents/` 建立專業化的代理人：

- `nuxt-content-specialist.md` — 內容查詢、MDC、搜尋
- `nuxt-ui-specialist.md` — 元件樣式、主題設定
- `vue-specialist.md` — 響應式系統（Reactivity）、組合式函式（Composables）
- `nuxt-specialist.md` — 路由、設定、部署

每個 agent 只在相關情境載入，並記錄了透過 `llms.txt` 存取官方文件的方式。

### `/learn` Skill：自增長的知識庫

作者建立了一個 `/learn` skill，功能是：

1. 分析當次對話中可複用的、非顯而易見的洞察
2. 識別 `/docs/` 中適合儲存的位置
3. 請求使用者批准後才寫入
4. 隨時間累積專案專屬的 gotchas 知識庫

> [!note] 回饋循環（Feedback Loop）
> 隨時間推移，`/docs/` 變成一個精選的知識庫，記錄了 AI 工具在你的 codebase 中容易犯錯的地方。這形成一個自增強的系統：學習不斷累積 → Claude 在開始任務前一致性地閱讀相關文件 → context window 保持高效。

### Vercel Agent Evals：關鍵實驗數據

> [!important] 實驗結果
> Vercel 的 agent evals 發現：
> - **AGENTS.md 內嵌壓縮 docs 索引 → 100% pass rate**
> - **Skills 自然觸發 → 最高 79% pass rate**
> - **Skills 基線（從未觸發）→ 56%**
> 
> 結論：明確的 docs 引用比 skills 的模糊觸發條件更可靠。

### 跨工具相容性

用 symlink 讓同一份設定在多個 AI 工具間共享：

```bash
ln -s CLAUDE.md agents.md
```

這樣 Claude Code、VS Code Copilot、Cursor 都能讀取同一份 `CLAUDE.md`——「one source of truth, no drift between tools」。

### 實作注意事項

1. **背壓（Backpressure）很重要** — 來自 linter、type checker、build 工具的自動化回饋讓 agent 能自我修正，無需人工介入。這對 Ralph 等自主技術（AI 透過任務佇列工作，沒有持續指導）尤其關鍵。
2. **Skills 仍不可預測** — 觸發條件模糊，明確的 docs 引用方式更可靠。
3. **對稀疏領域要明確** — 訓練資料覆蓋率低的主題（如特定框架的新版 API），需要額外的方向性指引。

## 我的心得（My Takeaways）

1. **「如果工具能強制執行，就不要寫文字」**——這一條原則能砍掉 CLAUDE.md 30-50% 的內容。ESLint 規則比 CLAUDE.md 裡的風格指南可靠一百倍。
2. **`IMPORTANT: Read relevant docs below before starting any task` 這句話是魔法咒語**——沒有它，Claude 不會主動查閱文件。有了它，整個漸進式揭露系統才能運作。
3. **`/learn` skill 的設計理念值得借鑑**——不只是手動維護 gotchas，而是讓 AI 自己發現並提議記錄，形成可持續的知識積累循環。
4. **Vercel 實驗打臉了「Skills 萬能」的假設**——56% 從未被調用的數據太驚人。在我自己的專案中，關鍵知識應該用明確引用而非依賴 skills 自動觸發。
5. **Symlink 做跨工具共享是個聰明的做法**——一份設定維護，多個工具受益。

## 待補充（Open Questions）

- **Vercel agent evals 的完整實驗設計是什麼？** 文章引用了 100% vs 79% 的數據，但沒有公開原始實驗的 skill 數量、評估標準、受測任務類型。需要找到 Vercel 的原始出處。建議搜尋：`Vercel agent evals AGENTS.md skills pass rate 2025 2026`
- **`IMPORTANT` 指示句的遵從率在長 session 中如何衰減？** 文章說加了這句就會讀 docs，但在 auto-compaction 後，這句話是否還在 context 中？它被壓縮掉的風險有多高？建議搜尋：`Claude Code auto-compaction CLAUDE.md instruction preservation`
- **`/learn` skill 的誤報率（False Positive Rate）是多少？** 自動提議儲存的洞察中，有多少是真正有用的、多少是噪音？長期使用後 `/docs/` 會不會也變得臃腫？建議搜尋：`Claude Code learn skill accuracy gotcha documentation automation`
- **Custom agents 與 Skills 在 token 效率上的差異？** 文章推薦 custom agents 而非 skills，但沒有比較兩者的 token 消耗。agents 的系統提示是否也會佔用 main context？建議搜尋：`Claude Code custom agents vs skills token consumption context isolation`
- **在 monorepo 場景中，/docs/ 目錄該如何分層？** 作者的範例是單一專案（Nuxt），但如果有 5+ packages 各自有不同的 gotchas，/docs/ 該放在根目錄還是各 package 下？建議搜尋：`Claude Code monorepo CLAUDE.md docs progressive disclosure directory structure`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | CLAUDE.md 建議 ~50 行、Vercel 實驗 100% vs 79% vs 56%、三層架構（CLAUDE.md / /docs/ / agents）、`/learn` skill 自動捕捉洞察、symlink 跨工具共享 |
| **理解（半被動）** | 解釋概念的含義及關聯 | 漸進式揭露（Progressive Disclosure）在 AI 程式設計中的應用：不是「少給資訊」，而是「在正確的時機給正確的資訊」。CLAUDE.md 是永遠在場的通用 context，/docs/ 是按需載入的領域知識，custom agents 是隔離 context 的專家。三者形成「context 漏斗」：寬泛 → 情境 → 專精。 |
| **分析（主動）** | 檢驗論點、拆解假設 | **關鍵假設**：Claude 會遵守 `IMPORTANT: Read relevant docs` 指示。但這依賴 Claude 的指令遵循——正是 CLAUDE.md 太長時會衰減的能力。如果 CLAUDE.md 精簡到 50 行，這句話的遵從率應該很高；但如果 compaction 壓縮了它，系統就失效。**Vercel 數據的局限**：二手引用，原始實驗條件不明，56% 未觸發可能與 skill description 品質有關而非 skills 機制本身的問題。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | **立即可做：**（1）審視自己的 CLAUDE.md，將所有「可由 linter/formatter 強制執行」的規則移除（2）建立 `/docs/` 目錄，將現有 CLAUDE.md 中的 gotchas 移入（3）在 CLAUDE.md 末尾加上 `IMPORTANT: Read relevant docs below before starting any task` 指示句 |
| **評估（主動）** | 判斷多個方案的優劣 | **Opalic 方案（docs 引用）vs Skills 方案 vs Karpathy 方案（行為準則）**——Opalic 的 100% pass rate 最可靠但需要手動維護 docs；Skills 省力但 56% 未觸發；Karpathy 的行為準則不處理領域知識。最佳策略是三者混合：Karpathy 行為準則放 CLAUDE.md 頂部，通用 context 放 CLAUDE.md 主體，領域 gotchas 用 Opalic 的 /docs/ 引用，程序性工作流用 Skills（手動觸發）。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「漸進式揭露（Progressive Disclosure）」在本文中指的是 Claude 按需讀取 /docs/ 檔案——但這真的是「漸進式」嗎？更準確地說，是「明確指示式載入」，因為 Claude 不是逐步揭露越來越深的細節，而是一次性讀取被引用的整個檔案。
- **假設**：本文假設 Claude 會在「每次任務開始前」都遵守 IMPORTANT 指示句去讀相關 docs。但如果使用者在同一 session 中連續處理多個不相關任務（不 /clear），Claude 是否還會在第二個任務前重新查閱 docs？
- **證據**：Vercel 的 100% vs 79% 數據是本文的核心論據，但這是二手引用。原始實驗的受測 skill 數量、任務複雜度、模型版本等關鍵變數均未公開，無法判斷實驗的外部效度（External Validity）。
- **觀點**：反對者可能說：「/docs/ 方案本質上是把 CLAUDE.md 的內容搬到另一個地方，Claude 每次還是要讀全部相關的 docs 檔案，token 消耗並沒有真正減少——只是從『啟動時消耗』變成『任務開始時消耗』。」
- **後果**：如果團隊採用 `/learn` skill 自動累積 gotchas，12 個月後 /docs/ 可能累積數百條 gotcha——此時 Claude 讀取所有 docs 的 token 成本可能超過一個精簡的 CLAUDE.md。需要定期修剪（pruning）機制。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — `/docs/` 無人維護導致過時資訊污染 Claude 的判斷。如果某個 gotcha（如「用 stem 不要用 slug」）在框架升級後不再適用，但沒人移除，Claude 會根據過時資訊給出錯誤建議。風險等級：中——不會造成系統崩潰，但會累積技術債。
2. **什麼情況下會失敗？** — （1）CLAUDE.md 的 IMPORTANT 指示句在 auto-compaction 後被移除（2）/docs/ 檔案太多，Claude 讀完所有相關 docs 後 context 反而更擁擠（3）使用者不 /clear 就切換任務，前一個任務載入的 docs 佔用 context 但不相關。
3. **有沒有更好的替代方案？** — Skills 的 `paths` frontmatter 可以做到路徑作用域的自動載入（editing `src/api/` 時自動載入 API conventions skill），理論上比「在 CLAUDE.md 寫 IMPORTANT 指示 Claude 自己判斷哪些 docs 相關」更精準。缺點是 skills 自動觸發的 56% 未觸發問題。最佳方案可能是：高優先 gotchas 用 CLAUDE.md 直接 `@import`，低優先的用 `/docs/` + IMPORTANT 指示句。

## 相關連結（Related）

- [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] — 七位專家的 CLAUDE.md 最佳實踐交叉比較，本文是其中 Alexander Opalic 的完整觀點
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — CLAUDE.md 的 memoize 快取機制，解釋了為什麼 CLAUDE.md 是全量載入且不能在 session 中刷新
- [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]] — Skills 的官方文件完整筆記，補充本文對 Skills 觸發機制的批評
- [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — 配置層級指南，symlink 跨工具共享的技術基礎
- [[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]] — Karpathy 用行為準則（而非知識注入）的互補方案，可與本文的 /docs/ 方案結合
- [[2026-01-27-VERCEL-AGENTS-MD-OUTPERFORMS-SKILLS-IN-AGENT-EVALS]] — 本文引用的 Vercel 實驗原始報告：AGENTS.md 100% vs Skills 53%，完整方法論與數據
- [[2026-01-27-KARPATHY-GUIDELINES-VS-CLAUDE-CODE-BUILTIN-SYSTEM-PROMPT]] — 原始碼級驗證 Karpathy 準則與內建 prompt 的重疊度，支持本文「不要重複內建指令」的論點

## References

- [Stop Bloating Your CLAUDE.md: Progressive Disclosure for AI Coding Tools — Alexander Opalic (2026-01-18)](https://alexop.dev/posts/stop-bloating-your-claude-md-progressive-disclosure-ai-coding-tools/)
