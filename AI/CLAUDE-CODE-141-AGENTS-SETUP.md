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

## Related

- [[CLAUDE-MEMORY-ENGINE]] — complementary system: memory + learning across sessions; hooks architecture maps to this team system
- [[CLAUDE-CODE-HOOKS]] — the underlying hook mechanism that powers all agent triggers and handoffs
- [[AI-AGENT-MEMORY]] — broader research on AI memory architectures; vector DB vs markdown tradeoffs
- [[OBSIDIAN-POWER-TIPS]] — knowledge management systems that parallel the .claude/decisions.md shared context pattern
