---
title: "gitagent — A Framework-Agnostic, Git-Native Standard for AI Agents"
date: 2026-03-15
category: AI
tags:
  - ai-agents
    - gitagent
      - open-standard
        - git-native
          - claude-code
            - framework-agnostic
              - adapter-pattern
                - skills
                  - knowledge-base
                    - obsidian
                      - progressive-disclosure
                        - context-window
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

                              ## Related

                              - [[AI-AGENT-FRAMEWORKS-COMPARISON]]
                              - [[CLAUDE-CODE-WORKFLOW]]
                              - [[CONTEXT-WINDOW-OPTIMIZATION]]
                              - [[OBSIDIAN-KNOWLEDGE-MANAGEMENT]]
