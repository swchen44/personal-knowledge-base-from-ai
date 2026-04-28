---
title: "141 Claude Code Agents: The Setup That Actually Works"
date: 2026-03-16
category: AI
tags:
  - ai/claude-code
  - ai/agents
  - productivity/workflows
  - tools/claude
  - devtools/automation
source: "https://alirezarezvani.medium.com/141-claude-code-agents-the-setup-that-actually-works-a-complete-guide-98c2c79bf867"
source_type: article
author: "Alireza Rezvani (Reza)"
status: notes
links:
  - "[[CLAUDE-MEMORY-ENGINE]]"
  - "[[CLAUDE-CODE-HOOKS]]"
  - "[[AI-AGENT-MEMORY]]"
---

## Summary

After 6 months building 141 Claude Code agents in production, Alireza Rezvani (CTO) shares the 10-team color-coded structure, 8 autonomous skills, and 19 slash commands that turned agent chaos into a manageable system. The key insight: organize agents by **domain ownership**, not by task — and keep teams small with isolated contexts.

## Key Insights

- **Domain teams beat task agents** — organizing by codebase area (not by task type) prevents context bleed and work duplication, see [[CLAUDE-CODE-HOOKS]]
- **3 agents max per team** — teams with 4+ agents averaged 12-min handoffs; teams with ≤3 averaged 4 minutes
- **shared_memory: false is critical** — shared context caused agents to apply solutions from unrelated problems incorrectly
- **Skills unlock autonomy** — without skills you babysit every task; with the right skills agents handle 70–80% of work unsupervised
- **Start small, validate first** — build 3–5 agents before scaling; infrastructure complexity before validation is the #1 failure mode, see [[AI-AGENT-MEMORY]]

## Details

### The 10-Team Color System

> [!note] Why Colors?
> Colors are faster to type (/blue-review vs /engineering-core-review) and force team scope to stay small. If you can't associate a team's purpose with a color, it's probably doing too much.

**Engineering Teams (4):**
- Blue — Core application code
- Cyan — Infrastructure and DevOps
- Orange — External integrations and APIs
- Yellow — Database and data processing

**Support Teams (3):**
- Green — Quality assurance and testing
- Red — Security auditing
- Purple — Architecture and planning

**Operational Teams (3):**
- Gray — Documentation and knowledge management
- White — Performance monitoring and optimization
- Black — Incident response and debugging

### Team Config Pattern

Each team lives in .claude/teams/<color>-team.yaml with:
- context_isolation: strict
- max_concurrent_agents: 3
- shared_memory: false
- Explicit handoff_rules preserving decisions, constraints, rationale

### 8 Autonomous Skills

| Skill | Time Savings |
|-------|-------------|
| code-review | 15 min → 3 min per PR; 62% more issues caught |
| doc-sync | Doc accuracy 65% → 94%; 5 hrs/wk → 45 min |
| test-generation | Generates unit + edge case tests (propose mode) |
| dependency-audit | Weekly security/license scan |
| refactoring-scout | Detects code smells and duplication patterns |
| performance-monitor | Flags regressions in new code paths |
| migration-assistant | DB migrations with rollback planning |
| incident-analyzer | Correlates error logs with recent changes |

> [!warning] Skill Autonomy Levels
> Never start at Full Auto for code-modifying skills. Use Supervised → earn autonomy over time. The author lost an afternoon reverting "optimizations" on a hand-tuned critical path.

### 19 Slash Commands

**Core 8 (daily):** /blue-review, /green-test, /gray-doc, /red-audit, /purple-plan, /cyan-deploy, /orange-integrate, /yellow-query

**Context 5:** /handoff [team], /context-dump, /context-load, /isolate, /resume [id]

**Utility 6:** /status, /costs, /metrics, /rollback [n], /explain [agent], /pause

### Honest Limitations

> [!warning] Known Failure Points
> 1. **Context window cap**: accuracy drops from 89% → 60% when juggling 15+ file modifications; max 10 concurrent agents
> 2. **15% handoff info loss**: even with explicit preservation rules; fix = write critical decisions to shared .claude/decisions.md
> 3. **Cost**: avg $12/day, peaks at $40 on heavy days; use /costs + daily limits
> 4. **Skill drift**: Code Review flagged 62% fewer issues in month 6 vs month 1; fix = monthly skill audits
> 5. **Human oversight gap**: full autonomy on business-critical paths leads to logic violations

## My Takeaways

- The **color-team domain model** is the key structural insight — I can apply this immediately to any multi-agent setup
- **shared_memory: false** is counterintuitive but correct; explicit handoffs > implicit shared state
- The **Supervised autonomy tier** principle maps directly to how [[CLAUDE-MEMORY-ENGINE]] handles the Correction Cycle — earn trust through demonstrated reliability
- **ROI math**: 45-hour setup cost, 12–15 hours/week savings → break-even in ~3 weeks for CTOs managing 7+ person teams; overkill for solo devs on small projects
- The repo **claude-code-tresor** (288 stars) is worth cloning as a starting template

## 待補充（Open Questions）

- 「3 agents max per team」的 4-minute vs 12-minute handoff 數據是如何量測的？計時起點和終點如何定義，且這個數字對不同任務類型（code review vs. 資料庫遷移）是否有差異？（建議搜尋：`multi-agent handoff latency measurement benchmark`）
- 15% handoff information loss 的具體原因是什麼？除了寫入 .claude/decisions.md，是否有其他減少資訊遺失的機制（如結構化 handoff schema、向量記憶庫）？（建議搜尋：`agent handoff information loss reduction strategies`）
- Skill drift（第 6 個月 Code Review 少偵測 62% 問題）的根本原因是什麼？是 prompt 腐化、模型更新，還是程式碼庫本身的語意漂移？如何設計月度 skill audit 流程？（建議搜尋：`agent skill drift prompt decay monthly audit`）
- 「context_isolation: strict」模式下，不同 team 之間如何共享確實需要共享的資訊（如架構決策、全域常數）？shared .claude/decisions.md 是否足夠，或需要更精細的選擇性共享機制？（建議搜尋：`agent context isolation selective sharing cross-team`）
- 顏色命名系統（color-coded teams）在超過 10 個 team 時如何擴展？顏色數量有限，是否有其他命名空間策略可供參考？（建議搜尋：`multi-agent team naming strategy namespace scaling`）

## Related

- [[CLAUDE-MEMORY-ENGINE]] — complementary system: memory + learning across sessions; hooks architecture maps to this team system
- [[CLAUDE-CODE-HOOKS]] — the underlying hook mechanism that powers all agent triggers and handoffs
- [[AI-AGENT-MEMORY]] — broader research on AI memory architectures; vector DB vs markdown tradeoffs
- [[OBSIDIAN-POWER-TIPS]] — knowledge management systems that parallel the .claude/decisions.md shared context pattern
- [[2026-03-17-NVIDIA-ANNOUNCED-NEMOCLAW-WHAT-NVIDIA-ACTUALLY-SOLVES-FOR-OPENCLAW-USERS-AND-WHAT-IT-DOES-NOT]] — NemoClaw 的跨進程安全治理層，為多代理人系統提供進程外的安全約束機制
- [[2026-03-29-CONNSYS-JARVIS-AGENTHUB-INTEGRATION-DESIGN]] — Jarvis 多代理協調架構，將本文的 domain team 概念實作為 Expert 角色分工
- [[2026-04-02-CLAUDE-CODE-ISSUE-42796-EXTENDED-THINKING-REGRESSION]] — 50+ 並行 agent session 的品質退化量化分析，影響多代理工作流的穩定性

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 10 色彩命名團隊系統（Blue/Cyan/Orange/Yellow/Green/Red/Purple/Gray/White/Black）、`shared_memory: false`、`context_isolation: strict`、`max_concurrent_agents: 3`、8 個自主 Skills（code-review/doc-sync/test-generation/dependency-audit/refactoring-scout/performance-monitor/migration-assistant/incident-analyzer）、19 個 Slash Commands（核心 8/上下文 5/工具 6）、`/handoff`、`.claude/decisions.md`、Supervised 自主層級、skill drift、日均 $12 運作成本 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | 本文的核心架構思路是「以領域所有權組織代理人，而非以任務類型」。10 色彩團隊系統並非裝飾性命名，而是強制每個團隊保持窄焦範圍（否則無法與單一顏色關聯）。`shared_memory: false` 的反直覺設計源於一個觀察：共享上下文讓代理人跨領域套用解法，反而造成錯誤；明確的 handoff 規則雖有 15% 資訊遺失，但比隱式共享狀態更可預測、更易除錯。Supervised→Full Auto 的漸進授權模式讓信任隨可靠性累積，而非預先假設。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 1. 「3 agents max per team」的 4 分鐘 vs 12 分鐘 handoff 數據是核心論據，但文章沒有說明量測方法、樣本數量或任務類型，這個數字的通用性存疑；2. Skill drift（第 6 個月 Code Review 少偵測 62% 問題）的根本原因未被分析——是 prompt 腐化、模型更新還是程式碼庫語意漂移——月度 skill audit 的有效性取決於能診斷出正確原因；3. 文章建議的 ROI 試算（45 小時設定成本、每週 12-15 小時節省、3 週回本）對不同規模的團隊差異極大，但只給出了「CTO 管理 7+ 人團隊」的單一情境。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. 複製 10 色彩系統作為起點，從最痛的 3 個領域（如 Blue 核心程式碼、Green 品質測試、Gray 文件）建立第一批代理人，驗證後再擴展；2. 立即在現有代理人設定中加入 `shared_memory: false` 並建立 `.claude/decisions.md` 共享關鍵架構決策，取代隱式共享狀態；3. 對所有 code-modifying skills 強制從 Supervised 模式開始，設計 30 天觀察期後再評估是否提升自主層級。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | 10 色彩團隊系統的優勢是強制範圍約束和快速溝通（`/blue-review` 比 `/engineering-core-review` 快），缺點是在超過 10 個領域時顏色空間耗盡、且顏色-領域映射對新成員不直觀。日均 $12（峰值 $40）的成本對個人開發者不划算，但對 CTO 管理多人團隊的情境可能僅是一個初階工程師月薪的極小比例。與集中式協調方案（如 Claude Code multi-agent）相比，本文的分散式域團隊方案在 context 隔離和並發吞吐上更好，但管理開銷（19 個 slash commands、8 個 skills 的維護）也更高。適合已有清晰領域邊界的成熟產品，不適合仍在探索架構的早期創業。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「domain ownership」作為組織代理人的原則聽起來合理，但在實際產品中，許多任務天然跨越多個域（如一個功能同時涉及 API 設計、資料庫遷移、前端組件）。這種跨域任務在 10 色彩系統中如何處理？由哪個顏色負責協調？
- **假設**：「shared_memory: false 是關鍵」這個主張假設代理人的錯誤主要來自「跨域上下文污染」，但另一種解釋是代理人缺乏足夠的全局上下文導致重複工作。這兩個假設哪個更符合你的實際場景？
- **證據**：「Skill drift」（Code Review 在第 6 個月少偵測 62% 問題）是一個驚人的退化幅度。若原因是 prompt 腐化，那 prompt 為何在沒有人修改的情況下會「腐化」？這個現象是否可能有其他解釋（如程式碼庫風格改變導致審查標準不再適用）？
- **觀點**：從工程文化的角度，將所有決策集中在 `.claude/decisions.md` 一個共享檔案，是否反而製造了新的單點故障（SPOF）？若這個檔案過時或不完整，代理人基於錯誤的「共享知識」做出決策的後果比 `shared_memory: false` 更難診斷嗎？
- **後果**：若這套 141 代理人架構被廣泛採用，工程師的職責是否會從「寫程式碼」轉變為「設計和維護代理人系統」？這個轉變對工程師的職涯發展意味著什麼？需要培養哪些新的核心能力？
