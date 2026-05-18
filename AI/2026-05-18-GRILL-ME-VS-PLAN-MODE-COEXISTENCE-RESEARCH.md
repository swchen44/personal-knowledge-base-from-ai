---
title: "/grill-me 與 Claude Code Plan Mode 衝突嗎？外部討論盤點 + 三種共存模式"
date: 2026-05-18
category: AI
tags:
  - ai/claude-code
  - ai/skills
  - ai/plan-mode
  - productivity/workflow
  - research/synthesis
source: "conversation research: grill-me + Plan Mode 共存（綜合 WebSearch + 既有 KB 筆記）"
source_type: research
author: "本人綜合研究"
status: notes
links:
  - "[[2026-05-03-CLAUDE-CODE-PLAN-MODE-VS-SUPERPOWERS-CONFLICT-ANALYSIS]]"
  - "[[2026-03-23-GRILL-ME-SKILL-DEEP-DIVE]]"
  - "[[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]]"
  - "[[2026-04-08-SUPERPOWERS-13-SKILLS-PRACTICAL-WALKTHROUGH]]"
  - "[[SUPERPOWERS-OBRA]]"
---

## TL;DR 結論

> [!important] 三句話結論
> 1. **外部完全沒有人專文討論「grill-me + Plan Mode 衝突」**——這是個盲點議題。
> 2. 但 **Superpowers 的 `brainstorming` skill 是 grill-me 的「同層替代品」**，圍繞它已有完整衝突討論（含官方 v4.3.0 攔截 `EnterPlanMode` 的證據鏈），可以推論 grill-me 的處境。
> 3. **grill-me 與 Plan Mode 衝突遠輕於 Superpowers**——因為 grill-me 不寫檔、不自動觸發、不攔截工具呼叫，所以**可以乾淨共存**。本文給出 3 種共存模式（A/B/C）。

---

## 為什麼這個研究有價值

`/grill-me` 是 Matt Pocock 最爆紅的 skill（[[2026-03-23-GRILL-ME-SKILL-DEEP-DIVE|grill-me 深度剖析]]）——強迫深度對齊、走遍 design tree。Plan Mode 是 Claude Code 內建的權限/規劃機制——讀-only 探索完才能寫檔。表面看兩者都在「想清楚再動手」這層，邏輯上應該配合得很好。

但既有 KB 已分析 [[2026-05-03-CLAUDE-CODE-PLAN-MODE-VS-SUPERPOWERS-CONFLICT-ANALYSIS|Plan Mode vs Superpowers]] 的 5 個衝突點（含 Auto Mode 停用 bug、計畫路徑不相容）。這引出一個自然的疑問：**Matt Pocock 的 grill-me 會不會也有類似衝突？**

> [!quote] 用戶提問（本研究的起點）
> 「我最近在研究 grill me，突然看到 PLAN-MODE-VS-SUPERPOWERS 這篇——外面現在有沒有講 grill me 和 Claude Code Plan Mode 有衝突？有沒有討論和經驗分享，或如何共存？」

---

## 外部資源盤點

> 2026-05-18 用 WebSearch 與 WebFetch 對相關討論做了完整盤點。

### 直接命中（grill-me + Plan Mode）

**沒有任何專文**。WebSearch 對以下查詢都查無資料：
- `"grill-me" "plan mode" claude code conflict OR coexist`
- `matt pocock grill-me skill claude code plan mode reddit hackernews`

HN 上的 grill-me 爆紅貼文（[item 47550391](https://news.ycombinator.com/item?id=47550391)）也沒提及 Plan Mode 互動。Matt Pocock 自己的兩篇文章與整個 mattpocock/skills repo 都沒討論這個議題。

### 間接相關（Superpowers brainstorming vs Plan Mode）

| 來源 | 內容 | 對 grill-me 的啟發 |
|------|------|------------------|
| **[obra/superpowers Issue #1260](https://github.com/obra/superpowers/issues/1260)** | 請求 `writing-plans` 與原生 Plan Mode side panel 整合；目前無 maintainer 回應。技術原因：`writing-plans` 把計畫寫到 `docs/superpowers/plans/YYYY-MM-DD-*.md`，**從不呼叫 `ExitPlanMode`**，所以 Plan side panel 永遠空白 | grill-me 不寫檔，**根本沒有這個衝突** |
| **[Superpowers v4.3.0 blog](https://blog.fsck.com/agent-blog/2026/02/12/superpowers-v4-3-0/)** | 官方寫：在 using-superpowers 工作流圖加入 EnterPlanMode 攔截，主動阻止進入原生 Plan Mode，導向 brainstorming skill | grill-me **沒有任何攔截邏輯**，是「邀請式」而非「攔截式」對齊 |
| **[rcanand「Practical Guide」](https://rcanand.bearblog.dev/claude-code-just-got-confusing-plan-mode-vs-superpowers-vs-agent-teams-a-practical-guide/)** | **本研究最有價值的外部資源**。給出 sequential 共存策略：Requirements 用 `/superpowers:brainstorm`、Planning 二選一、Execution 看複雜度。名言：「Using both in sequence is redundant. Pick one.」 | grill-me 也可套用類似策略，但**不需要二選一**——可以 grill-me 先、Plan Mode 後 |
| **[既有 KB PLAN-MODE-VS-SUPERPOWERS 篇](https://github.com/swchen44/personal-knowledge-base-from-ai/blob/main/DevTools/2026-05-03-CLAUDE-CODE-PLAN-MODE-VS-SUPERPOWERS-CONFLICT-ANALYSIS.md)** | 完整源碼分析 5 個衝突點：EnterPlanMode 攔截、Plan side panel 空白、Auto Mode 停用 bug、唯讀限制、Token 重複 | 對照之下，**grill-me 觸發了 0 個**這些衝突 |

---

## 結構差異：grill-me vs Superpowers brainstorming

> [!important] 這是本研究的核心發現
> 兩者解決同個問題（深度對齊），但**機制完全不同**，因此與 Plan Mode 的互動也完全不同。

| 維度 | **`/grill-me`（Matt Pocock）** | **`/superpowers:brainstorming`** |
|------|------------------------------|----------------------------------|
| **檔案大小** | 428 bytes（4 句指令） | 完整 skill 組一部分（含 specs 模板） |
| **觸發方式** | **使用者主動** `/grill-me` | **AI 自動偵測新功能就觸發**（強制） |
| **寫檔行為** | **不寫檔**（純對話流程） | **寫 `docs/superpowers/specs/*.md`** |
| **攔截 EnterPlanMode** | **不攔截**（與 Plan Mode 完全解耦） | **主動攔截**（v4.3.0+ 將 EnterPlanMode 導向自己） |
| **與 Plan Mode 關係** | **正交（Orthogonal）**——可以共存、可以前後串接 | **替代（Replacement）**——刻意取代 Plan Mode |
| **可預測性** | 高（你呼叫才跑） | 中（AI 自動判斷可能誤觸發） |
| **跨 harness** | 任何支援 Claude skill 規範的 harness 都可用 | 多 harness 但 Plan Mode 攔截只對 Claude Code 生效 |

### 衝突類型分類（推論）

```
                 機制衝突 high
                     │
                     │
              Superpowers ★   ←── EnterPlanMode 攔截 + 寫檔位置打架
                     │           Auto Mode 停用 bug、side panel 空白
                     │
                     │
        ─────────────┼─────────────► 衝突高 / 低
                     │
                     │
              grill-me ●   ←── 概念上的「太早出 plan」抱怨
                     │       但機制上零衝突（不攔截、不寫檔、被動觸發）
                     │
                 機制衝突 low
```

**推論結論**：
- grill-me 表面是「概念競爭」（誰先對齊）
- Superpowers brainstorming 是「機制競爭」（攔截 tool call、寫檔位置不同）

---

## 三種共存模式

> [!tip] 本研究最有價值的產出
> 既有外部沒人寫，我們自己根據結構差異推論出三種可用配方。

### 模式 A：grill-me 先、Plan Mode 後（推薦）

```
[使用者輸入模糊需求]
        │
        ▼
   /grill-me <brief>          ← 主動觸發
        │
        ▼ （AI 一題一題追問 16–50 題、走 design tree）
   [達成 shared understanding]
        │
        ▼ Shift+Tab×2 或 /plan
   [Plan Mode 啟動]            ← 原生 Plan Mode 進入
        │
        ▼ AI 寫 plan（已對齊，速度快、品質高）
   ExitPlanMode → 使用者批准
        │
        ▼
   [實作]
```

**為什麼推薦**：
- grill-me 在 Plan Mode 外完成對齊，Plan Mode 進入後 AI 已知足夠 context
- Plan Mode 寫出的 plan **品質遠高於**「冷啟動就進 Plan Mode」的版本
- 完全沒有 EnterPlanMode 攔截衝突
- 適合中等複雜度、需求模糊的功能

**驗證指令**：
```bash
# 在 Claude Code session：
> /grill-me 我想加一個 X 功能
# ...一題一題回答...
> 好，所有 design tree 都走完了

# 按 Shift+Tab×2 進 Plan Mode
> 把剛剛對齊的內容寫成實作 plan
# ...Plan Mode 寫出 plan...
> 批准
```

### 模式 B：Plan Mode 先、grill-me 補洞

```
[使用者進 Plan Mode 直接給需求]
        │
        ▼ AI 探索 codebase、生 plan 草稿
   [Plan 出來但你看了覺得不對齊]
        │
        ▼ Esc 退出 Plan Mode
   /grill-me 剛剛那個 plan 還沒釐清 X、Y、Z
        │
        ▼ （AI grill 你補洞）
   [補完缺口]
        │
        ▼ Shift+Tab×2 重進 Plan Mode
   [Plan Mode 重生 plan]
```

**為什麼適合某些情境**：
- 你不確定要不要 grill（簡單需求）就直接 Plan Mode 試
- Plan 草稿出來才發現對齊不夠，用 grill-me 補洞
- **適合熟手**——能準確判斷「Plan 不夠好」的程度

**風險**：Plan Mode 來回進出可能耗 token；如果反覆來回 2 次以上，不如直接走模式 A。

### 模式 C：完全用 grill-me 取代 Plan Mode（熟手）

```
[使用者輸入需求]
        │
        ▼
   /grill-me <brief>
        │
        ▼
   [深度對齊]
        │
        ▼ 使用者直接說：「不用進 Plan Mode，直接寫 plan.md」
   AI 寫純文字 plan（不進 Plan Mode）
        │
        ▼
   [實作]
```

**為什麼有些人選這個**：
- 完全不用 Plan Mode 的 read-only 限制與批准流程
- grill-me 對齊深度已足夠
- 適合**個人 side project / 寫作類非編碼任務**（Plan Mode 不太適用非編碼）
- 對「Plan Mode 的 EnterPlanMode/ExitPlanMode 干擾」零容忍的人

**缺點**：跳過 Plan Mode 的權限隔離，AI 可能在你不注意時改檔。

---

## 對比：與 [[2026-05-03-CLAUDE-CODE-PLAN-MODE-VS-SUPERPOWERS-CONFLICT-ANALYSIS|既有 KB 的 Superpowers 衝突分析]]差在哪？

| 議題 | Superpowers（既有分析） | grill-me（本研究） |
|------|----------------------|------------------|
| **是否衝突？** | **是**，5 個機制衝突點 | **否**，只有概念競爭、無機制衝突 |
| **是否該同時用？** | 「不應同時啟動」，建議二選一 | **可以共存**，三種配方 |
| **Auto Mode 停用 bug** | 是 SuperPowers 觸發 Plan Mode 循環導致 | grill-me **不會觸發**這個 bug |
| **Plan side panel 空白** | 是 writing-plans 不呼叫 ExitPlanMode | grill-me 不寫 plan，**沒這問題** |
| **CLAUDE.md 規定哪個用** | 必須明確規定（避免衝突） | **不需明確規定**（兩者解耦） |
| **適合使用者** | 「全套工程化」愛好者 | 「需要深度對齊但保留 Plan Mode 自由」的混合派 |

---

## 應用建議：對個人 KB 工作流

針對自己的 KB ingestion + 寫作場景，**推薦模式 A**：

1. **KB ingestion 新文章**：先 `/grill-me 這篇文章要回答什麼問題、要連到哪些既有筆記` → 對齊後寫文（不必進 Plan Mode）
2. **複雜 skill 撰寫**：先 grill-me 釐清 skill 用例 → 再進 Plan Mode 寫 skill 的 SKILL.md
3. **三方框架對比（如本筆記）**：grill-me 已隱式發生（用戶問+我搜尋+確認結構），跳過 Plan Mode 直接寫

---

## 待補充（Open Questions）

1. **如果 Plan Mode 進入時 grill-me 也在進行中**（half-finished），會不會干擾？grill-me 沒有「狀態機」，但 Plan Mode 有讀-only flag——交叉發生的行為未測試。建議搜尋：`claude code plan mode skill state machine interaction`
2. **grill-me 的「relentless」會不會誤觸發 ExitPlanMode**？例如 grill 過程中 AI 突然想交付 plan 退出 Plan Mode？這需要實測。建議搜尋：`grill-me skill auto exitplanmode trigger`
3. **Plan Mode v2.1.0+ 的 `/plan` 指令對 grill-me 的影響**？兩者在「主動 invoke」這層可能彼此遮蔽。建議搜尋：`claude code /plan command v2.1.0 grill-me interaction`
4. **Matt Pocock 本人對 Plan Mode 的立場**？mattpocock/skills repo 沒寫 anti-Plan-Mode 邏輯，但 [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH|workshop]] 中提到「Plan Mode 太早出 plan 是問題」——他到底是要替代 Plan Mode 還是補強它？建議追：`@mattpocockuk` Twitter / mattpocock/skills issues
5. **Superpowers v5.x 之後是否會放棄攔截 EnterPlanMode**？Issue #1260 是個趨勢信號，若 obra 重新擁抱 Plan Mode side panel，那 brainstorming 的衝突就會跟 grill-me 一樣輕。建議追：obra/superpowers releases
6. **多 harness 場景**（Codex CLI / Cursor / Gemini CLI）下 grill-me 與 Plan Mode 衝突有沒有差異？因為 Plan Mode 是 Claude Code 專有，其他 harness 根本沒這個概念。
7. **rcanand 那篇結論「Using both in sequence is redundant. Pick one.」對 grill-me 是否成立**？我推論不成立（可共存），但需要實測驗證。

---

## 相關連結（Related）

- [[2026-05-03-CLAUDE-CODE-PLAN-MODE-VS-SUPERPOWERS-CONFLICT-ANALYSIS]] — **必讀對照**：本研究的姊妹篇，那篇講 Superpowers 機制衝突，本篇講 grill-me 為何沒有
- [[2026-03-23-GRILL-ME-SKILL-DEEP-DIVE]] — grill-me 本身的 4 句指令拆解
- [[2026-04-24-MATT-POCOCK-AI-CODING-WORKFLOW-FULL-WALKTHROUGH]] — grill-me 在 5 skills 工作流中的位置 + 三方對照
- [[2026-04-08-SUPERPOWERS-13-SKILLS-PRACTICAL-WALKTHROUGH]] — Superpowers brainstorming 對照（13 skills 全景）
- [[SUPERPOWERS-OBRA]] — Superpowers 框架概覽
- [[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]] — 三框架比較中對 brainstorming 的概覽
- [[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]] — 第三條路線：GStack 的 CEO Plan 也是替代 Plan Mode 的方式
- [[2026-05-09-STOP-RANDOM-SKILL-4-CORE-GROUPS-FOR-AGENT-PRODUCTIVITY]] — Skill 分類框架，grill-me 屬「工程化開發 / 對齊」組

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 外部無 grill-me + Plan Mode 專文；Superpowers v4.3.0 攔截 EnterPlanMode；Issue #1260；rcanand 文「Pick one」；grill-me 428 bytes；不寫檔不攔截 |
| **理解（半被動）** | 解釋概念的含義及關聯 | grill-me 與 Superpowers brainstorming 解決同問題（深度對齊）但**機制完全不同**：grill-me 是邀請式（使用者主動）、Superpowers 是攔截式（自動觸發 + 攔 EnterPlanMode）。機制差異決定了與 Plan Mode 共存難易 |
| **分析（主動）** | 檢驗論點、拆解假設 | 假設 1：「外部無專文 = 不重要」可能是錯的——也可能因為大家還沒撞上這問題；假設 2：「grill-me 不攔截就無衝突」忽略了「Plan Mode 內呼叫 grill-me」的 read-only 衝突（未測試）；假設 3：三種模式都是邏輯推論，未實測 |
| **應用（主動）** | 將知識套用情境 | 1) KB ingestion 套用模式 A（先 grill-me 後 Plan Mode）；2) 自己寫 skill 時不要學 Superpowers 攔截 EnterPlanMode；3) 寫 CLAUDE.md 規則時，grill-me 列為「對齊優先工具」而非「Plan Mode 替代品」 |
| **評估（主動）** | 比較替代方案 | vs Superpowers brainstorming：grill-me 更輕、更可控、更可共存；vs 純 Plan Mode：grill-me 補強對齊深度。在「不想被 skill 綁架」的場景，grill-me 是更聰明的選擇 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「衝突」一詞在本文有兩層意思——機制衝突（攔截工具呼叫）vs 概念衝突（誰先做對齊）。要嚴格區分。
- **假設**：本文假設「機制不衝突 = 可共存」，但其實還缺一層驗證：使用者習慣（cognitive load）。同時記得 grill-me + Plan Mode 兩個概念對新手是負擔。
- **證據**：三種共存模式都是邏輯推論，**沒有實測證據**。應該找一天實際跑模式 A / B / C 各一次，觀察行為。
- **觀點**：反對者會說「grill-me 本來就是 Plan Mode 該做的事，重複了就刪掉 Plan Mode 用模式 C」——這個批評有道理，但 Plan Mode 的「權限隔離」價值是 grill-me 取代不了的。
- **後果**：若推廣模式 A 給團隊，12 個月後可能：(a) 對齊品質普遍提升、(b) 部分 PM/dev 抱怨「步驟太多」、(c) 出現「跑完 grill-me 就懶得進 Plan Mode 直接寫」的退化（變模式 C 但沒有自覺）。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — **模式 B 的 token 浪費**：Plan Mode → grill-me → Plan Mode 來回，每次都重新探索 codebase。若反覆超過 2 次，token 消耗指數成長且品質不一定提升。最壞情況：你花了 100K token 還沒寫一行 code。
2. **什麼情況下會失敗？**
   - 需求簡單（小 bug fix）：模式 A 跑 grill-me 是 overkill
   - 已有完整 spec：grill-me 重複問已知問題會煩
   - 純 Plan Mode 場景（如 git commit 訊息生成）：grill-me 用不上
   - 多人協作：每人 grill-me 結果不同 → 對齊反而分裂
3. **有沒有更好的替代方案？**
   - **簡單需求**：直接 Plan Mode 或 single-prompt
   - **完全模糊**：先 brainstorming（Superpowers，更發散）再 grill-me（更收斂）
   - **團隊場景**：grill-me 結果寫進 issue tracker 統一參考，不要每人重新跑

---

## References

- 既有 KB 筆記：[`DevTools/2026-05-03-CLAUDE-CODE-PLAN-MODE-VS-SUPERPOWERS-CONFLICT-ANALYSIS.md`](https://github.com/swchen44/personal-knowledge-base-from-ai/blob/main/DevTools/2026-05-03-CLAUDE-CODE-PLAN-MODE-VS-SUPERPOWERS-CONFLICT-ANALYSIS.md)
- 既有 KB 筆記：[`AI/2026-03-23-GRILL-ME-SKILL-DEEP-DIVE.md`](https://github.com/swchen44/personal-knowledge-base-from-ai/blob/main/AI/2026-03-23-GRILL-ME-SKILL-DEEP-DIVE.md)
- [rcanand「Claude Code Just Got Confusing: Plan Mode vs Superpowers vs Agent Teams — A Practical Guide」](https://rcanand.bearblog.dev/claude-code-just-got-confusing-plan-mode-vs-superpowers-vs-agent-teams-a-practical-guide/)
- [GitHub Issue obra/superpowers#1260 — Integrate writing-plans with Claude Code's native Plan Mode / Plan panel](https://github.com/obra/superpowers/issues/1260)
- [Superpowers v4.3.0 blog — Massively Parallel Procrastination](https://blog.fsck.com/agent-blog/2026/02/12/superpowers-v4-3-0/)
- [HN: This is why the grill me skill went viral (item 47550391)](https://news.ycombinator.com/item?id=47550391)
- [mattpocock/skills/productivity/grill-me/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md)
- [jasperfurniss gist — claude-plan-mode-vs-superpowers.md](https://gist.github.com/jasperfurniss/ac657b0e22fc1febe5fd9205855365fc)
