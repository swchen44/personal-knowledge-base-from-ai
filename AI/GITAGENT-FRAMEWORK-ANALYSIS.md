---
title: "gitagent — A Framework-Agnostic, Git-Native Standard for AI Agents"
date: 2026-03-15
category: AI
tags:
  - "#ai/agent"
  - "#tools/git"
  - "#ai/framework"
source: "https://github.com/open-gitagent/gitagent"
source_type: tool
author: "open-gitagent"
status: complete
links:
  - "[[AI-AGENT-FRAMEWORKS-COMPARISON]]"
  - "[[CLAUDE-CODE-WORKFLOW]]"
  - "[[CONTEXT-WINDOW-OPTIMIZATION]]"
---

                              ## Summary

                              gitagent is an open standard that turns any Git repository into a portable, framework-agnostic AI agent definition. The core idea is: drop a few structured files into any repo, and it becomes an agent that can be exported to Claude Code, OpenAI Agents SDK, CrewAI, LangChain, and more — via adapters. All versioning, branching, and collaboration is handled natively by Git.

                              ## Key Insights

                              - **Your repo IS your agent** — no separate agent platform needed, just files in a git repo
                              - **Two required files only**: `agent.yaml` (manifest) and `SOUL.md` (identity)
                              - **Adapters do the translation** — same definition exports to 8+ frameworks via `gitagent export --format <adapter>`
                              - **Progressive disclosure exists in code but isn't fully used** — `skill-loader.ts` has `loadSkillMetadata()` (lightweight) and `loadSkillFull()` (full), but export adapters currently use full load
                              - **Knowledge uses `always_load` filter** — only docs marked `always_load: true` in `knowledge/index.yaml` get inlined into the output
                              - **DUTIES.md is the most ignored section** — only `system-prompt` and `claude-code` adapters handle it; all others skip it

                              ## File Structure

                              ```
                              my-agent/
                              ├── agent.yaml          # [Required] Manifest: name, version, model, compliance
                              ├── SOUL.md             # [Required] Identity, personality, values
                              ├── RULES.md            # Hard constraints
                              ├── DUTIES.md           # Segregation of duties (SOD)
                              ├── AGENTS.md           # Framework-agnostic fallback instructions
                              ├── skills/             # Capability modules (SKILL.md + scripts)
                              ├── tools/              # MCP-compatible tool definitions (YAML)
                              ├── workflows/          # Multi-step procedures
                              ├── knowledge/          # Reference docs (controlled by index.yaml always_load)
                              ├── memory/runtime/     # Persistent cross-session state
                              ├── hooks/              # bootstrap.md, teardown.md
                              ├── compliance/         # Regulatory artifacts
                              └── agents/             # Sub-agents (recursive structure)
                              ```

                              ## Adapter Comparison

                              | Block | system-prompt | claude-code | openai | crewai | openclaw | nanobot | lyzr | github |
                              |-------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
                              | SOUL.md | ✅ | ✅ | ✅ | ⚠️parse | ✅file | ✅ | ⚠️regex | delegate |
                              | RULES.md | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | delegate |
                              | DUTIES.md | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | delegate |
                              | skills | full | full | full | desc only | passthrough | full | full | delegate |
                              | knowledge | always_load | always_load | ❌ | ❌ | always_load | always_load | ❌ | delegate |
                              | tools/ | ❌ | ❌ | Python stubs | ❌ | TOOLS.md | name only | ❌ | delegate |
                              | compliance | ✅ full+SOD | ✅ full+SOD | ⚠️partial | ❌ | ⚠️partial | ⚠️partial | ⚠️partial | delegate |
                              | memory | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | delegate |

                              ## Skill Loading — Design Gap

                              `skill-loader.ts` already implements progressive disclosure:

                              ```typescript
                              loadSkillMetadata()  // ~100 tokens, frontmatter only
                              loadSkillFull()      // complete frontmatter + Markdown body
                              ```

                              **Where lightweight is used:** `gitagent skills list` (CLI management only)
                              **Where full load is used:** ALL export adapters (claude-code, system-prompt, openai, nanobot, lyzr)

                              This means every invocation inlines ALL skill full text into the context window, even for skills never triggered. The infrastructure for lazy loading exists but is not wired to the export path — a good opportunity for a PR.

                              See GitHub Issue: https://github.com/open-gitagent/gitagent/issues/19

                              ## Quick Start

                              ```bash
                              npm install -g gitagent
                              gitagent init --template standard
                              gitagent validate
                              gitagent export --format claude-code
                              gitagent export --format system-prompt
                              gitagent export --format openai
                              ```

                              ## My Takeaways

                              - The git-native approach is elegant — no new infrastructure, just conventions on top of git
                              - The adapter pattern cleanly separates "what the agent is" from "how it runs"
                              - The compliance features (FINRA, SOD, audit logging) are unusually thorough for an open source tool
                              - The progressive disclosure gap in export adapters is a real issue worth contributing a fix for
                              - OpenClaw's passthrough approach for skills is the most principled — let the runtime parse, don't pre-digest

                              ## 待補充（Open Questions）

                              - 技能懶加載（Lazy Loading）的 PR 機會已被識別（GitHub Issue #19），但現有適配器全部使用全量載入——修改後對不同規模技能庫（10 個 vs 100 個技能）的上下文視窗節省量估計有多大？（建議搜尋：`gitagent lazy loading skill progressive disclosure context window`）
                              - DUTIES.md（職責分離）只有兩個適配器支援，其餘全部跳過——對於需要合規控制的企業場景，缺少 SOD 支援的安全風險具體是什麼？（建議搜尋：`AI agent segregation of duties compliance SOD enterprise`）
                              - 各框架適配器（CrewAI、LangChain、OpenAI）對 `agent.yaml` 解析的差異在實務中會導致哪些行為不一致？是否有跨框架行為一致性的測試套件？（建議搜尋：`gitagent adapter cross-framework behavior consistency testing`）
                              - `SOUL.md` 給 Agent 賦予身份與價值觀的設計在不同框架中有不同程度的支援——當框架對 SOUL.md 只做 regex 解析（如 Lyzr）時，Agent 的身份一致性如何保證？（建議搜尋：`agent identity soul personality cross-framework consistency`）
                              - Git 原生版本控制作為 Agent 定義的管理機制，在 Agent 定義頻繁更新的生產環境中有何實際優勢？與傳統 Agent 平台（如 LangSmith、Langfuse）的版本管理相比有何差異？（建議搜尋：`git-native agent versioning production deployment comparison`）

                              ## Related

                              - [[AI-AGENT-FRAMEWORKS-COMPARISON]]
                              - [[CLAUDE-CODE-WORKFLOW]]
                              - [[CONTEXT-WINDOW-OPTIMIZATION]]
                              - [[OBSIDIAN-KNOWLEDGE-MANAGEMENT]]
                              - [[2026-02-24-GITAGENT-GIT-NATIVE-AI-AGENT-STANDARD]] — gitagent 同一專案的深度程式碼分析（繁中版），含 CLI、adapter、合規功能細節

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | gitagent 開放標準、`agent.yaml` + `SOUL.md` 兩個必要檔案、8 個 adapter（system-prompt、claude-code、openai、crewai、openclaw、nanobot、lyzr、github）、`always_load` 知識過濾、`DUTIES.md` 僅兩個 adapter 支援、GitHub Issue #19（技能懶加載）、`loadSkillMetadata()` vs `loadSkillFull()` 的差異 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | gitagent 的核心概念是「Git 倉庫即 Agent 定義」——將 Agent 的身份、規則、技能、工具全部以 Git 原生檔案表示，再透過 adapter 模式翻譯成各框架的執行格式，達到「一次定義、多處執行」的目標。adapter 層把「agent 是什麼」與「agent 如何跑」解耦，是這個標準的根本價值所在。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 1. **Progressive Disclosure 的設計意圖與現實落差**：`skill-loader.ts` 已有輕量/完整兩種載入路徑，但所有 export adapter 仍使用全量載入，等同假設「所有技能在任何對話中都可能被觸發」，這個假設在技能數量多時明顯不成立。2. **DUTIES.md 的覆蓋率問題**：只有兩個 adapter 支援 SOD，其他 adapter 跳過等同假設「企業合規需求可以被省略」，對目標是合規場景的使用者是個隱患。3. **SOUL.md 解析的一致性假設**：不同 adapter 對 SOUL.md 的支援程度差異極大（從完整到 regex 解析），意味著「agent 身份」的一致性實際上由 adapter 品質決定，而非標準本身保證。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. **貢獻 PR 修復 lazy loading**：按照 GitHub Issue #19 的方向，修改 export adapters 改用 `loadSkillMetadata()` 做初始清單，僅在技能被觸發時再 `loadSkillFull()`，可大幅節省 context window。2. **評估 gitagent 作為 connsys-jarvis 的 Agent 標準格式**：gitagent 的 `agent.yaml` + `SOUL.md` + skills 目錄結構與 connsys-jarvis 的設計高度吻合，可作為 Phase 2 OpenClaw 遷移的上層規範。3. **建立企業內部 adapter 白名單**：對只關心合規的場景，限定使用 `system-prompt` 或 `claude-code` adapter，因為這兩個是唯一支援 DUTIES.md 的選項。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | **優勢**：Git 原生無需額外基礎設施、adapter 模式框架中立、合規功能對 open source 工具而言異常完備。**劣勢**：adapter 之間功能落差過大（DUTIES.md、knowledge 支援度），標準的「可攜性」承諾在實際框架間並不完整；技能全量載入造成 context window 浪費，在技能庫成長後將成瓶頸。**替代方案比較**：與 LangSmith 等平台相比，gitagent 犧牲了 UI 和可觀測性換取框架中立；與自行維護 CLAUDE.md 相比，gitagent 提供了更結構化的 agent 定義，但引入了 toolchain 依賴。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：gitagent 聲稱「framework-agnostic」，但 adapter 之間對 DUTIES.md、knowledge、tools 的支援差異如此懸殊，這個標準的「可攜性」邊界究竟在哪裡？哪些屬性是真正跨框架可攜的，哪些只是 best-effort？
- **假設**：gitagent 的設計假設 Git 版本控制是 Agent 定義管理的最佳機制——但 Agent 定義若需要秘密管理（API keys、私有知識）、動態更新（不適合 git commit 的頻繁變動），Git 的假設是否仍然成立？
- **證據**：`loadSkillFull()` 全量載入造成 context 浪費的問題有多嚴重？是否有實測數據顯示 10 個技能 vs 100 個技能時的 token 差異，以及對實際輸出品質的影響？
- **觀點**：OpenClaw 的「passthrough 原則」（讓 runtime 自行解析，不預消化）被本文認為是「最有原則的做法」——但這是否意味著標準本身的 adapter 應該盡可能 thin，而不是嘗試模擬各框架的語意？這兩種設計哲學各自的邊界在哪？
- **後果**：如果 gitagent 的技能懶加載 PR（Issue #19）被合入，現有所有採用 gitagent 的 Agent 定義是否需要修改 skills 的 manifest 格式？這個升級路徑對已有大型技能庫的使用者有何遷移成本？
