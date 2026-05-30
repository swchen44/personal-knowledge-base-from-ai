---
title: "Vercel 實驗報告：AGENTS.md 在 Agent 評估中完勝 Skills——100% vs 53% 的原始數據"
date: 2026-01-27
category: AI
tags:
  - "#ai/claude-code"
  - "#ai/context-engineering"
  - "#ai/agent-evaluation"
  - "#tools/nextjs"
  - "#ai/prompt-engineering"
source: "https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals"
source_type: article
author: "Jude Gao"
status: notes
links:
  - "[[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]]"
  - "[[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]]"
  - "[[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]]"
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
---

## 摘要（Summary）

Vercel 的 Jude Gao 發表的原始實驗報告，系統性地比較了「AGENTS.md 嵌入壓縮文件索引」與「Skills 按需調用」兩種方式在教導 AI 程式設計 agent 框架專屬知識（Framework-Specific Knowledge）上的效果。**這是被 Alexander Opalic 等多位專家廣泛引用的「100% vs 79% vs 56%」數據的原始出處。** 核心發現：在針對 Next.js 16 新 API 的硬化評估（Hardened Eval）中，AGENTS.md 達到 **100% pass rate**，而 Skills 預設行為 **0% 改善**（與基線持平的 53%），即使加上明確指示也只達 79%。關鍵機制：被動上下文（Passive Context）消除了「是否調用」的決策點（Decision Point），而 Skills 有 **56% 的案例從未被調用**。

## 關鍵洞察（Key Insights）

- **Skills 預設行為 = 沒有改善** — 在 56% 的測試案例中，skill 完全未被調用，pass rate 與基線（53%）持平，甚至在測試項目上反而退步（58% vs 63%）
- **指令措辭（Wording）戲劇性地影響結果** — 「You MUST invoke the skill」讓 agent 過度錨定文件而忽略專案 context；「Explore project first, then invoke skill」效果更好
- **40KB 文件壓縮至 8KB（80% 壓縮率）仍保持 100% pass rate** — 用 pipe-delimited 索引格式，讓 agent 「locate and read specific files」而非前置載入所有內容
- **被動上下文勝過按需檢索** — AGENTS.md 的三個成功機制：無決策點、每一輪都在系統提示中、無排序問題
- **Skills 與 AGENTS.md 是互補而非競爭** — Skills 適合垂直的、使用者明確觸發的工作流（版本升級、路由遷移）；AGENTS.md 適合水平的、所有任務都受益的框架知識
- **核心目標：從預訓練導向推理（Pre-Training-Led Reasoning）轉向檢索導向推理（Retrieval-Led Reasoning）**

## 詳細內容（Details）

### 問題背景：訓練資料的過時性

AI 程式設計 agent 的訓練資料有截止日期（Knowledge Cutoff）。Next.js 16 引入的新 API（如 `'use cache'`、`connection()`、`forbidden()`）不在模型訓練資料集中，導致 agent 產生錯誤程式碼或回退到已棄用的模式。

> [!note] 硬化評估（Hardened Eval）
> 針對訓練資料中不存在的 API 設計測試，確保評估的是「agent 學習新知識的能力」而非「回憶訓練資料的能力」。

**受測 API 清單：**
- `connection()` — 動態渲染（Dynamic Rendering）
- `'use cache'` 指令
- `cacheLife()` 與 `cacheTag()`
- `forbidden()` 與 `unauthorized()`
- `proxy.ts` — API 代理
- 非同步（Async）`cookies()` 與 `headers()`
- `after()`、`updateTag()`、`refresh()`

### 實驗方法論

比較兩種方式：

| 方式 | 機制 | 決策點 |
|------|------|--------|
| **Skills** | 開放標準，打包提示、工具和文件，agent 按需調用 | 有——agent 必須決定是否/何時調用 |
| **AGENTS.md** | 持久的 markdown 文件，提供連續上下文 | 無——資訊永遠存在 |

### 實驗結果

> [!important] 完整數據表
> 
> **整體 Pass Rate：**
> 
> | 配置 | Pass Rate | vs 基線 |
> |------|-----------|---------|
> | 基線（無文件） | 53% | — |
> | Skill（預設） | 53% | +0pp |
> | Skill + 明確指示 | 79% | +26pp |
> | **AGENTS.md 文件索引** | **100%** | **+47pp** |
> 
> **分項 Pass Rate（Build / Lint / Test）：**
> 
> | 配置 | Build | Lint | Test |
> |------|-------|------|------|
> | 基線 | 84% | 95% | 63% |
> | Skill（預設） | 84% | 89% | 58% |
> | Skill + 明確指示 | 95% | 100% | 84% |
> | **AGENTS.md** | **100%** | **100%** | **100%** |

> [!warning] Skills 的負面效果
> 在預設模式下，Skills 不僅沒有改善，測試項目的 pass rate 甚至**從 63% 下降到 58%**——加了文件反而更差。原因是 skill 在 56% 的案例中從未被調用，但其存在可能干擾了 agent 的注意力分配。

### 指令措辭的戲劇性影響

不同的指令措辭（Wording）產生截然不同的結果：

- **「You MUST invoke the skill」** — agent 過度錨定（Anchor）在文件模式上，忽略專案 context。例如在 `'use cache'` 測試中，「先調用」方式正確產生了 `page.tsx`，但遺漏了必要的 `next.config.ts` 修改。
- **「Explore project first, then invoke skill」** — 先建立專案 context 再查閱文件，效果更好。

> [!tip] 可執行建議
> 如果你在自己的 Skills 中使用明確指示，用「先探索、再查閱」的順序比「必須調用」更有效。但無論怎麼優化措辭，都不如直接將資訊嵌入 AGENTS.md。

### AGENTS.md 成功的三個機制

1. **無決策點（No Decision Point）** — 資訊永遠存在，agent 不需要決定「是否」和「何時」調用
2. **一致性可用（Consistent Availability）** — 內容在每一輪的系統提示（System Prompt）中都在
3. **無排序問題（No Ordering Issues）** — 被動上下文消除了「先探索還是先查文件」的排序決策

### 壓縮策略：40KB → 8KB

初始文件約 40KB。壓縮至 8KB（**80% 壓縮率**）後仍維持 100% pass rate。

壓縮格式使用 pipe-delimited 結構：

```markdown
[Next.js Docs Index]|root: ./.next-docs
|IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning
|01-app/01-getting-started:{01-installation.mdx,02-project-structure.mdx,...}
|01-app/02-building-your-application/01-routing:{01-defining-routes.mdx,...}
```

> [!note] 設計理念
> 這個結構提供**索引資訊（Indexing Information）**，讓 agent 能「定位並讀取特定檔案（locate and read specific files）」，而非需要把所有內容前置載入。嵌入的不是文件本身，而是文件的地圖。

### 自動化工具

```bash
npx @next/codemod@canary agents-md
```

此工具執行三個功能：
1. 偵測專案的 Next.js 版本
2. 下載對應版本的文件到 `.next-docs/`
3. 將壓縮索引注入 `AGENTS.md`

注入的內容包含明確指示：

> [!quote] 
> 「Prefer retrieval-led reasoning over pre-training-led reasoning for any Next.js tasks.」

### Skills 與 AGENTS.md 的定位分工

> [!important] 互補而非競爭
> Skills 與 AGENTS.md 不是二選一的關係：
> - **Skills** — 適合**垂直的、動作導向的工作流**，由使用者明確觸發（版本升級、路由遷移、最佳實踐套用）
> - **AGENTS.md** — 適合**水平的改善**，所有框架相關任務都受益
> 
> 對於通用框架知識，「被動上下文目前優於按需檢索（passive context currently outperforms on-demand retrieval）」。

### 給框架作者的建議

1. **不要等 skill 改善了才行動** — 現在就用 AGENTS.md，結果立竿見影
2. **大幅壓縮文件** — 索引（indexing）優於嵌入完整內容（embedding complete content）
3. **建立針對訓練資料缺口的 evals** — 測試 agent 在新 API 上的表現
4. **為檔案式檢索（File-Based Retrieval）組織文件** — 而非要求前置載入所有 context

## 我的心得（My Takeaways）

1. **這是被廣泛二手引用的原始數據來源** — 現在終於看到完整的實驗方法論。之前在 [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]] 和 [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] 中引用的「100% vs 79% vs 56%」數據全部來自這篇。
2. **「壓縮索引 + 檔案式檢索」是一個可泛化的架構** — 不只適用於 Next.js。任何有大量文件的框架（React、Vue、Nuxt、Rails）都可以用同樣的 pipe-delimited 索引格式。
3. **56% 未調用的根本原因是「決策點」本身** — 不是 skill description 寫得不好，而是要求 agent 做「是否調用」的決策本身就是不可靠的。這改變了我對 Skills 的認知——問題不在實作，在機制。
4. **指令措辭的實驗結果非常實用** — 「先探索再查閱」比「必須調用」好，這個洞察可以直接應用到我自己的 skill 設計中。
5. **80% 壓縮率仍 100% pass rate** — 證明 agent 不需要完整文件，只需要一張「地圖」就能自己找到需要的東西。這驗證了漸進式揭露的核心理念。

## 待補充（Open Questions）

- **壓縮索引在 auto-compaction 時如何表現？** AGENTS.md 嵌入的 8KB 壓縮索引在 Claude Code 的 auto-compaction 機制下是否被保留？如果被壓縮或截斷，100% pass rate 是否會下降？建議搜尋：`Claude Code auto-compaction AGENTS.md preservation system prompt`
- **此實驗是否只在 Claude 上測試？** 文章未明確指出使用的模型。如果是在 Claude Sonnet 上的結果，在 GPT-4o 或 Gemini 上是否也能重現？模型的指令遵循特性差異可能影響結果。建議搜尋：`Vercel agent evals model comparison GPT Claude Gemini`
- **多框架共存時的 AGENTS.md 大小問題？** 如果一個 monorepo 同時用了 Next.js、Prisma、TailwindCSS，每個都注入壓縮索引，AGENTS.md 會膨脹到多大？是否仍能維持 100%？建議搜尋：`AGENTS.md multiple framework index monorepo context budget`
- **pipe-delimited 壓縮格式是否有正式規格？** 文章展示的 `|01-app/01-getting-started:{01-installation.mdx,...}` 格式看起來是 Vercel 自訂的。其他框架要採用時，有沒有標準化的壓縮格式規範？建議搜尋：`AGENTS.md compressed index format specification standard`
- **Skills + AGENTS.md 組合的實驗數據？** 文章建議兩者互補，但沒有公布「AGENTS.md + Skills 同時使用」的 pass rate。組合使用是否有 >100% 的效果（例如更少的 token 或更快的完成速度）？建議搜尋：`agent skills combined AGENTS.md eval results`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | AGENTS.md 100% pass rate、Skill 預設 53%（= 基線）、Skill + 明確指示 79%、56% 案例 skill 未被調用、40KB → 8KB 壓縮（80%）、pipe-delimited 索引格式、`npx @next/codemod@canary agents-md` 指令 |
| **理解（半被動）** | 解釋概念的含義及關聯 | 被動上下文（Passive Context）之所以勝出，核心原因不是「資訊更多」，而是「消除了決策點」。Skills 要求 agent 做兩個決策：（1）是否需要額外資訊？（2）何時查閱？這兩個決策各自都可能失敗。AGENTS.md 把這兩個決策的答案硬編碼為「永遠是、永遠在」。這是一個「減少 agent 自由度以提高可靠性」的設計哲學。 |
| **分析（主動）** | 檢驗論點、拆解假設 | **關鍵假設**：實驗只測試了訓練資料中不存在的 API。如果測試的是 agent 已知的成熟 API（如 React hooks），Skills 和 AGENTS.md 的差距可能縮小或反轉——因為 agent 不需要外部知識就能正確回答。**實驗偏誤**：Vercel 是 Next.js 的開發者，他們有動機證明自己的 `npx agents-md` 工具有效。不過數據本身看起來客觀（skills 的 0% 改善不太可能是捏造的）。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | **立即可做：**（1）對自己專案中使用的非主流框架（訓練資料覆蓋率低的），建立壓縮索引嵌入 CLAUDE.md（2）把 skill description 中的「必須調用」改為「先探索專案再查閱」（3）在 CLAUDE.md 中加入「Prefer retrieval-led reasoning over pre-training-led reasoning」指示 |
| **評估（主動）** | 判斷多個方案的優劣 | **AGENTS.md 方案**：100% 可靠、0 決策點，但每次 session 都佔 8KB context。**Skills 方案**：token 節省，但 56% 未觸發。**壓縮索引 + 檔案檢索方案**（本文提出的混合策略）：嵌入地圖而非全文，agent 按需讀取檔案——同時獲得被動上下文的可靠性和檔案檢索的 token 效率。**這是三者中最優的架構**，但需要額外的 `.next-docs/` 目錄維護。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「56% 的案例 skill 未被調用」——這是指 56% 的測試任務中 skill 完全未被觸發，還是 56% 的 API 調用嘗試中 skill 未被查閱？兩者含義不同。
- **假設**：本文假設 agent 的「是否調用 skill」決策是不可靠的。但如果 skill 的 description 品質更好（更精確地匹配測試任務的關鍵字），是否能顯著降低未觸發率？換言之，56% 是機制問題還是實作問題？
- **證據**：實驗只用了 Next.js 16 的新 API，樣本空間有限。100% pass rate 在 10 個 API、100 個 API 和 1000 個 API 的情況下是否都能維持？壓縮索引的規模效應（Scaling Effect）缺乏數據。
- **觀點**：Skills 的支持者可能反駁：「AGENTS.md 每次 session 都佔 8KB，100 個 session 就是 800KB 的浪費。Skills 只在需要時載入，長期看 token 成本更低。」——這是短期效果 vs 長期成本的取捨。
- **後果**：如果所有框架都效仿 Vercel 在 AGENTS.md 中嵌入壓縮索引，一個使用 5 個框架的專案可能有 40KB+ 的 AGENTS.md。此時 context window 的壓力會不會反過來導致效能下降？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — AGENTS.md 膨脹。如果多個框架都注入壓縮索引，加上專案自身的規則，AGENTS.md 可能超過 context window 的最佳容量。此時會觸發 auto-compaction，壓縮索引被截斷，100% pass rate 不復存在。
2. **什麼情況下會失敗？** — （1）框架版本更新但 `.next-docs/` 未同步（2）壓縮索引的格式被 auto-compaction 破壞（3）多框架索引互相干擾 agent 的注意力（4）非 Next.js 框架沒有類似的自動化工具，手動建立壓縮索引成本高。
3. **有沒有更好的替代方案？** — Skills 的 `paths` frontmatter 可以做到路徑觸發（editing `src/app/` 時自動載入 Next.js skill），理論上比全量嵌入更 token-efficient。但 Vercel 的實驗證明這不如被動上下文可靠。最佳折衷可能是：**AGENTS.md 嵌入壓縮索引 + Skills 做垂直工作流**（與本文結論一致）。

## 相關連結（Related）

- [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]] — Alexander Opalic 引用本文數據的漸進式揭露方案，本文是其「100% vs 79%」數據的原始來源
- [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] — 七位專家的 CLAUDE.md 最佳實踐比較，本文的 Vercel 實驗數據是核心論據之一
- [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]] — Skills 的官方文件，本文的 56% 未觸發數據挑戰了 skills 自動觸發機制的可靠性
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — CLAUDE.md 的 memoize 快取與 Skills 的 chokidar 熱載入機制分析，從原始碼角度解釋本文的「被動 vs 按需」差異
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — 將本文的 Skills 56% 未觸發數據放入 Skills/Commands/Subagents 的完整定位分析
- [[2026-02-12-EVALUATING-AGENTS-MD-CONTEXT-FILES-HELPFUL-FOR-CODING-AGENTS]] — ETH Zurich 反面實證：AGENTS.md 在已有文件的 repo 中反而降低 3% 成功率，與本文的 100% 結論形成關鍵對照

## References

- [AGENTS.md Outperforms Skills in Our Agent Evals — Jude Gao, Vercel (2026-01-27)](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)

- [[2026-05-30-MOSHI-MOBILE-TERMINAL-FOR-CODING-AGENTS]] — 行動端遠端操控 AI 編碼代理人的工具（Moshi）
