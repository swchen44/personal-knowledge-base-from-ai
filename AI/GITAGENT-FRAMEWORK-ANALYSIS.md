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
