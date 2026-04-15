---
title: "從零建立 Claude Code Agent 的 10 步框架 — 不用 LangChain、只靠 Markdown 檔案的生產環境實戰"
date: 2026-03-31
category: AI
tags:
  - "#ai/agent-architecture"
  - "#devtools/claude-code"
  - "#ai/context-engineering"
  - "#productivity/workflows"
source: "https://alirezarezvani.medium.com/how-to-build-claude-code-agents-from-scratch-the-10-step-framework-i-actually-use-in-production-6f6a358f4f8c"
source_type: article
author: "Alireza Rezvani (Reza)"
status: notes
links:
  - "[[CLAUDE-CODE-ARCHITECTURE]]"
  - "[[CONTEXT-ENGINEERING]]"
  - "[[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
---

## 摘要（Summary）

作者 Alireza Rezvani 是一位 CTO，他分享了從 LangChain + 自建 ReAct 迴圈的複雜架構，轉向純 Markdown 檔案 + Claude Code 原生功能的 10 步框架。核心主張：Claude Code 已經內建了 Agent 系統、記憶系統、工具權限、多 Agent 協作、MCP 整合等所有你需要的功能——不需要 LangChain、CrewAI 或 OpenAI Swarm，只需要 `.md` 檔案和 YAML 前置資料（Frontmatter）。完整 10 步：（1）Agent 定義（2）Skills I/O（3）CLAUDE.md 行為調校（4）工具權限（5）多 Agent 協作（6）三層記憶（7）MCP 外部能力（8）輸出交付（9）UI 整合（10）Hooks 監控。作者的生產安全策略：所有 agent 運行在 Tailscale 之後，零公開端口（Zero Public Ports）。

## 關鍵洞察（Key Insights）

- **Agent 定義 = 一個 Markdown 檔案**：放在 `.claude/agents/` 目錄，用 YAML frontmatter 定義 name、description、model、tools、color。`description` 就是路由邏輯（Routing Logic），要寫成觸發條件而非職位描述
- **行為調校 = CLAUDE.md 層級架構**：組織策略 → 專案 CLAUDE.md → 用戶 CLAUDE.md → `.claude/rules/*.md`（按檔案路徑作用域）→ MEMORY.md，**越具體越優先**
- **工具欄位 = 權限邊界**：`tools: Read, Grep, Glob` 的 Agent 不能修改檔案；加上 PreToolUse Hook 可以對 Bash 命令做驗證——**最小權限（Least Privilege）不是選項，是必要條件**
- **三層記憶（Three-tier Memory）**：Auto-memory（MEMORY.md，冷啟動消除器）→ Agent 層級記憶（`memory: project`）→ CLAUDE.md 作為制度化記憶（Institutional Memory）
- **Subagent vs Agent Teams**：Subagent 成熟可用（不能巢狀生成）；Agent Teams 實驗性質（需 Opus 4.6，15-20 分鐘後可能協調崩潰）
- **MCP 的實際限制**：作者試了 7 個 MCP server，砍掉 4 個——每個 MCP 連線都增加延遲和 Token 開銷，生產環境只跑 3 個
- **Meta-judge 模式**：Stop Hook 觸發另一個 Agent 來評估第一個 Agent 的產出——Agent 評估 Agent，但成本倍數是真實的
- **輸出層 = Skills + Slash Commands**：Skill 定義輸出格式，Slash Command 提供觸發器。作者的 CEO 晨間簡報：slash command → skill → memory → Telegram，完全自動化
- **UI = 使用者已在用的介面**：不建 Gradio/Streamlit，透過 OpenClaw 橋接 Telegram/Slack。「無需學習新工具，採用是即時的」
- **安全策略**：所有 agent 運行在 Tailscale 後面，零公開端口。作者自認這個框架「要么是最優雅的，要么是最可怕的——取決於你對純文字檔存取生產系統的信任程度」

## 詳細內容（Details）

### 10 步框架總覽

| 步驟 | 傳統框架做法 | Claude Code 原生做法 |
|------|------------|-------------------|
| 1. 定義角色 | Python class + system prompt | `.claude/agents/*.md` + YAML frontmatter |
| 2. 設計 I/O | Pydantic AI / LangChain Output Parser | `SKILL.md` + arguments + 輸出格式規範 |
| 3. 調校行為 | Prompt Tuning / Prefix Tuning | CLAUDE.md 層級架構 + `.claude/rules/*.md` |
| 4. 推理與工具 | LangChain tools / OpenAI function calling | `tools` 欄位 + PreToolUse Hook |
| 5. 多 Agent | CrewAI / LangGraph / OpenAI Swarm | Subagent（穩定）/ Agent Teams（實驗） |
| 6. 記憶 | Zep / ChromaDB / FAISS | Auto-memory + Agent-level memory + CLAUDE.md |
| 7. 外部能力 | 自建整合 | MCP servers |
| 8. 輸出 | Markdown / PDF / JSON formatter | Skills + Slash Commands（`.claude/commands/`） |
| 9. UI | Gradio / Streamlit / FastAPI | Remote Control + OpenClaw（Telegram/Slack） |
| 10. 監控 | 日誌 + 基準測試 | Hooks（4 種：PreToolUse/PostToolUse/Stop/Notification） |

### 步驟 1：Agent 定義

> [!important] `description` 是路由邏輯
> 不要寫「helps with security」這種模糊描述。要寫成**觸發條件**：「Reviews code changes for security vulnerabilities, auth issues, and data exposure. Use after any PR touches auth, payments, or user data.」

```yaml
---
name: security-reviewer
description: Reviews code changes for security vulnerabilities, auth issues, and data exposure. Use after any PR touches auth, payments, or user data.
model: sonnet
tools: Read, Grep, Glob, Bash
color: red
---

You are a security specialist reviewing code for vulnerabilities.
Focus on: injection flaws, auth bypass, data exposure,
insecure configurations. Report findings with file paths,
line numbers, and severity ratings.
```

### 步驟 2：Skills 作為 Schema 層

```yaml
---
name: pr-review
description: Structured pull request review
arguments:
  - name: branch
    description: Branch name to review
    required: true
  - name: focus
    description: Review focus area (security, performance, style)
    required: false
---

Review the PR on branch {{branch}}.
Output format:
1. Summary (2 sentences)
2. Critical issues (blocking)
3. Suggestions (non-blocking)
4. Verdict: APPROVE / REQUEST_CHANGES
```

> [!tip] 輸出格式越明確越好
> 作者維護 48 個 skills，效果最好的是輸出格式規範最明確的——Claude 在你給它結構時會尊重結構。

### 步驟 3：CLAUDE.md 層級架構

```
組織策略（Organization policy）         ← 最廣泛
  ↓
專案 CLAUDE.md（committed to Git）      ← 團隊慣例
  ↓
用戶 ~/.claude/CLAUDE.md               ← 個人預設
  ↓
.claude/rules/*.md                     ← 按檔案路徑作用域
  ↓
MEMORY.md（自動生成）                    ← 學習到的上下文
```

> [!tip] 模組化規則（Modular Rules）
> 不要寫一份 200 行的 CLAUDE.md，改用按路徑作用域的規則檔：

```yaml
# .claude/rules/api-standards.md
---
paths:
  - "src/api/**/*.ts"
---
All endpoints must include Zod input validation.
Use the standard AppError format for error responses.
Rate limiting configuration goes in src/api/middleware/.
```

前端工程師不會看到後端規則，API 開發者不會看到 React 元件慣例——**更少雜訊，更好產出**。

### 步驟 4：工具權限 = 最小權限原則（Least Privilege）

```yaml
---
name: db-reader
description: Execute read-only database queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
---
```

> [!warning] 給每個 Agent 完整工具存取是走向混亂的最快路徑
> 作者的 OpenClaw 多 Agent 系統嚴格分離工具：監控 Agent 只讀、事件回應 Agent 有 Bash 但有 guardrail、規劃 Agent 完全沒有執行工具。

### 步驟 5：Subagent vs Agent Teams

| 特性 | Subagent | Agent Teams |
|------|----------|-------------|
| 穩定度 | 生產就緒（Production-ready） | 實驗性質（Experimental） |
| 通信 | 只回報給 parent，彼此不通信 | 透過共享任務板（Task Board）+ 訊息直接通信 |
| 用途 | 聚焦委派（Code review、探索、文件生成） | 真正並行工作（前後端同時開發） |
| 限制 | **不能巢狀生成（flat delegation only）** | 需 Opus 4.6，15-20 分鐘後可能協調崩潰 |
| Token 消耗 | 4-7x（vs 單 Agent） | ~15x |

### 步驟 6：三層記憶

| 層次 | 機制 | 用途 |
|------|------|------|
| Auto-memory | `~/.claude/MEMORY.md`，Claude 自動寫入 | 冷啟動消除器（Cold-start Eliminator）——3 週累積 23 行專案知識 |
| Agent-level memory | frontmatter 加 `memory: project` | 跨對話持久化，Agent 累積模式和慣例 |
| CLAUDE.md | 版控共享 | 制度化記憶——個人發現 → 提升為團隊共享 |

### 步驟 7：外部能力 — MCP 作為整合層（Integration Layer）

```bash
claude mcp add playwright npx @playwright/mcp@latest
claude mcp add github gh copilot mcp
```

連線後，agent 可以瀏覽頁面、與 GitHub 互動、查詢資料庫——無需自訂整合程式碼。

作者的 OpenClaw 設定透過 MCP 路由到 Google Workspace、Jira 和 GitHub，使協調 agent 能透過單一協定（Protocol）存取電子郵件、日曆、專案看板和程式碼儲存庫。

> [!warning] MCP 的實際限制
> 每個 MCP 連線都增加延遲（Latency）和 Token 開銷。作者嘗試了 7 個 MCP server，最終砍掉 4 個，生產環境只跑 3 個——「增加的上下文消耗不值得額外的能力」。

### 步驟 8：輸出交付 — Skills + Slash Commands 作為輸出層

Skill 定義輸出格式，`.claude/commands/` 的斜線指令（Slash Command）提供觸發器：

```markdown
# /commands/weekly-digest.md
Run the weekly-digest skill. Pull from memory/daily/ for the past
7 days. Output as a structured briefing with: highlights, blockers,
decisions made, and open questions.
```

> [!example] CEO 晨間簡報實戰案例
> 斜線指令觸發 skill → skill 從記憶體提取資訊 → 格式化輸出 → 透過 OpenClaw 經由 Telegram 發送。CEO 無需輸入任何內容，簡報在每天早上 7:00 自動送達。

### 步驟 9：使用者介面 — Remote Control + 訊息整合

不用 Gradio、Streamlit 或 FastAPI。對 Claude Code agent 來說，「UI」是使用者**已經在用的介面**：

- **Claude Code Remote Control** — 在終端機啟動任務，從手機監控
- **OpenClaw** — 將 Claude Code 橋接到 Telegram、Slack、Discord 或 WhatsApp

> [!tip] 作者的實戰選擇
> 團隊使用 Telegram 作為 UI。所有 agent 互動都透過 CEO 早已在用的即時通訊介面。「無需安裝新 App、無需登錄、無需學習——由於無需學習任何新內容，採用是即時的。」

### 步驟 10：Hooks 監控 + Meta-judge 模式

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write",
      "hooks": [{"type": "command", "command": "npm run lint"}]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{"type": "command", "command": "./scripts/notify-slack.sh"}]
    }]
  }
}
```

> [!note] Meta-judge 模式
> Stop Hook 觸發另一個 Agent 評估第一個 Agent 的產出。分數低於閾值 → 觸發重試。作者在安全審查等關鍵工作流使用，但「Agent 評估 Agent」的成本倍數是真實的。

### 框架的侷限

> [!warning] 誠實的侷限評估

1. **上下文視窗退化（Context Window Degradation）**：多 Agent 工作流消耗 4-7x tokens，Agent Teams 接近 15x
2. **Subagent 不能巢狀**：如果工作流需要三層委派，需要 Agent Teams 或外部協調器（如 OpenClaw）
3. **Agent Teams 實驗性質**：協調失敗、超時、團隊領導失去隊友進度追蹤
4. **沒有內建可觀測性（Observability）**：無儀表板、無追蹤檢視器、無稽核日誌——Hooks 只給事件級別控制，聚合成監控系統是你自己的工作

## 我的心得（My Takeaways）

這篇文章最有價值的不是「10 步框架」本身，而是幾個來自生產環境的經驗教訓：

1. **`description` 是路由邏輯**——這個觀點改變了我對 Agent 定義的理解。與其寫「是什麼」，不如寫「什麼時候觸發」
2. **模組化 rules 按路徑作用域**——前端工程師不需要看後端規則。這個設計直接減少上下文雜訊，提升產出品質
3. **MCP 的 3 server 實際上限**——作者試了 7 個砍到 3 個，Token 開銷是真實的限制
4. **「本地發現 → 共享編纂」的記憶流程**——個人 auto-memory 發現專案知識後，提升為團隊共享的 CLAUDE.md

這些都是可以立即應用到自己 Claude Code 工作流的具體改進。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | CLAUDE.md 5 層覆蓋順序、`.claude/agents/` 目錄、4 種 Hook 類型（PreToolUse/PostToolUse/Stop/Notification）、Subagent 不能巢狀、Agent Teams 需 Opus 4.6、MCP 延遲成本 |
| **理解（半被動）** | 解釋概念含義及關聯 | 整個框架的核心是「把框架代碼替換為設定檔」——Agent 定義是 .md、行為調校是 CLAUDE.md 層級、I/O 是 SKILL.md、監控是 hooks.json。不需要程式碼 → 不需要部署 → 行為變更 = 編輯檔案 |
| **分析（主動）** | 檢驗論點、找出假設 | 作者假設 Claude Code 的原生功能足以替代所有外部框架——但這依賴 Claude 模型的能力持續領先。若切換到其他 LLM，整套框架（.claude/agents/、CLAUDE.md 層級等）完全不可攜帶；另外「48 個 skills」的維護成本未被討論 |
| **應用（主動）** | 將知識套用情境 | (1) 為自己的專案建立 `.claude/rules/` 模組化規則，按檔案路徑作用域；(2) 把現有 CLAUDE.md 拆分為聚焦的規則檔，減少上下文雜訊 |
| **評估（主動）** | 判斷方案優劣 | Markdown-only 框架 vs LangChain/CrewAI：前者零部署、行為變更即時、但完全綁定 Claude 生態且缺乏可觀測性和測試框架；後者有學習曲線和維護成本，但可攜帶性高、有完整的除錯工具鏈。對於 Claude Code 深度用戶前者更優，但對需要多模型切換的團隊後者更安全 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Agent-level memory」的 `memory: project` 具體儲存在哪裡？是 `.claude/` 目錄下的什麼結構？持久化格式是什麼？
- **假設**：框架假設所有需求都能用 Claude Code 原生功能滿足——若需要自訂 embedding 搜尋（如大型知識庫 RAG）怎麼辦？
- **證據**：「48 個 skills」和「23 行 auto-memory」——這些數字在多大規模的團隊/多少個 repo 上驗證過？
- **觀點**：若站在 LangChain 維護者的立場，他們會如何反駁「不需要框架」的主張？
- **後果**：若整個團隊深度依賴此框架 12 個月後，Anthropic 大幅改變 Claude Code 的設定檔格式或記憶系統，遷移成本有多大？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** 完全鎖定（Vendor Lock-in）在 Anthropic 生態——所有 Agent 定義、記憶、行為規則都用 Claude Code 專有格式。若需要切換到 OpenAI Codex 或 Google 的 Agent 系統，遷移成本極高

2. **什麼情況下會失敗？** (a) 團隊需要多模型混用（部分任務用 GPT、部分用 Claude）；(b) 需要複雜的 Agent 間通信模式（超過 flat delegation）；(c) 需要企業級可觀測性（審計日誌、追蹤、成本分析儀表板）

3. **有沒有更好的替代方案？** 混合方案：用 Claude Code 原生功能處理 80% 的日常工作，用 LangGraph 處理需要複雜狀態機（State Machine）的工作流。這樣保留了 Markdown-only 的簡潔性，但在框架真正有價值的場景不會受限

## 待補充（Open Questions）

- `memory: project` 欄位的具體儲存機制為何？儲存在 `.claude/` 目錄的哪個位置？跨多個工程師協作時，不同人的 Agent-level memory 是否會衝突或覆蓋？（建議搜尋：`Claude Code agent memory project frontmatter storage location`）
- 作者維護 48 個 skills 的經驗是否有公開的 skills 倉庫可參考？維護 48 個 skill 的認知負擔有多重？有無自動測試框架確保 skill 描述和實際行為對齊？（建議搜尋：`Alireza Rezvani claude-skills repository 48 skills maintenance`）
- `.claude/rules/*.md` 的「按檔案路徑作用域（path-scoped rules）」機制，當 Claude 同時在兩個不同路徑的檔案工作時，兩組規則是否會合併？若有衝突，以哪個優先？（建議搜尋：`Claude Code rules path scope conflict resolution`）
- Meta-judge 模式（Stop Hook 觸發另一個 Agent 評估輸出）的「重試觸發」機制如何避免無限迴圈？若評估 Agent 和生成 Agent 互相否定對方，是否有最大重試次數的熔斷器（Circuit Breaker）？（建議搜尋：`Claude Code meta-judge retry loop circuit breaker`）
- 「Subagent 不能巢狀生成（flat delegation only）」這個限制的技術原因是什麼？是設計決策（安全考量）還是實作限制？未來版本是否有計劃支援多層委派？（建議搜尋：`Claude Code subagent nesting limitation flat delegation design decision`）
- 此框架完全依賴 Claude Code 的專有格式，作者提到 Vendor Lock-in 是最大風險——有沒有開放標準（如 gitagent、GNAP）可以作為跨平台的 Agent 定義格式，讓同一套 Agent 能在不同 AI 工具上運行？（建議搜尋：`AI agent definition open standard portable format cross-platform`）

## 相關連結（Related）

- [[CLAUDE-CODE-ARCHITECTURE]] — Claude Code 的內部架構，驗證本文框架的技術可行性
- [[CONTEXT-ENGINEERING]] — 上下文工程（Context Engineering）的系統性方法
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — Claude Code 原始碼洩漏中的 Agent 循環、記憶系統設計，與本文框架高度互補
- [[2026-01-09-OH-MY-CLAUDECODE-MULTI-AGENT-ORCHESTRATION]] — oh-my-claudecode 的程式碼分析，展示另一種多代理人編排實作
- [[2026-03-14-OPENCLI-CODE-ANALYSIS]] — OpenCLI 的程式碼分析，可作為 Agent 工具整合的參考架構
- [[2026-03-16-SELF-EVOLVING-AGENT-CORE-MECHANISMS]] — 自我進化代理人的評估函數與記憶系統設計，為本文框架提供自動化迭代的進階方向
- [[2026-03-26-WRITING-YOUR-FIRST-SIMPLE-AI-AGENT]] — 入門版的 5 原則 Agent 建構指南，與本文 10 步框架形成由淺入深的學習路徑
- [[2026-04-07-AI-AGENT-PAINFUL-LESSONS-TUTORIALS-TO-REALITY]] — Agent 開發三個月踩坑復盤，揭示教科書式架構到有效架構的真實演化過程
- [[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]] — 同作者 Reza 對 Karpathy CLAUDE.md 的實測，展示 CLAUDE.md 合併順序與令牌預算管理
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — Skills + context:fork 如何部分取代 Subagents 的實戰比較與決策流程圖

## References

- [原文](https://alirezarezvani.medium.com/how-to-build-claude-code-agents-from-scratch-the-10-step-framework-i-actually-use-in-production-6f6a358f4f8c) — Alireza Rezvani, Medium, 2026-03-31
- [claude-code-tresor](https://github.com/alirezarezvani) — 作者的 Agent 設定檔範例倉庫
- [claude-skills](https://github.com/alirezarezvani) — 作者維護的 48 個 skills 倉庫
