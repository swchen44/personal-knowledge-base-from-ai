# CodeAnalysis Index

| 筆記 | 摘要 | 日期 |
|------|------|------|
| [[2026-05-20-CODEX-HOOK-AND-SKILLS-PARAMETERS-DEEP-DIVE]] | Codex Hook 系統參數規格 + Skills 搜尋路徑：9 種 hook event 完整 input/output schema、`schemars` 自動產 fixture 流程、6 條 skill root 路徑、`SKILL.md`+`agents/openai.yaml` 結構、scope 優先級、MAX_SCAN_DEPTH=6 等掃描限制 | 2026-05-20 |
| [[2026-05-23-RTK-RUST-TOKEN-KILLER-LOG-COMPRESSION-ARCHITECTURE]] | RTK Rust Token Killer 原始碼分析：hook rewrite、dedicated command modules、TOML filters、tee recovery、tracking DB 與 log dedupe；整理出可套用到 update RTK / 高噪音 log 的訊號預算與壓縮策略 | 2026-05-23 |
| [[2026-05-20-CODEX-CLI-VS-CLAUDE-CODE-DEEP-COMPARISON]] | OpenAI Codex CLI vs Anthropic Claude Code 深度對比：10 個架構維度 + 5 個體驗維度 + 決策矩陣；Codex 的 Starlark execpolicy + OS 原生沙盒 vs Claude Code 的對話式 approval + 5 種擴充面 | 2026-05-20 |
| [[2026-05-20-CODEX-CLI-CODE-ANALYSIS]] | OpenAI Codex CLI 程式碼深度分析：103 個 Rust crate、Node dispatcher + Rust binary、execpolicy（Starlark）、三平台原生沙盒（Seatbelt/Bubblewrap/Windows）、雙向 MCP、ChatGPT OAuth | 2026-05-20 |
| [[2026-05-17-GBRAIN-EVALS-VS-JARVIS-EVAL-METHODOLOGY]] | gbrain 與 gbrain-evals AI agent eval 方法論深度研究：sealed qrels + multi-adapter + LLM-as-judge with structured evidence；含 Jarvis Integration Test 三步走借鏡 backlog | 2026-05-17 |
| [[2026-04-10-CLAUDE-SESSION-ANALYZER-CODE-ANALYSIS]] | Claude Session Analyzer 深度分析 + 真實使用驗證：情感分析 100% 誤判、subagent 美化指標、三層防線改善方案 | 2026-04-10 |
| [[2026-04-28-CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]] | Claude Code Token 成本計算完整管線研究：從 API usage 到 JSONL 事後分析，含 6 個陷阱與 90% 誤差實測 | 2026-04-28 |
| [[2026-04-24-CLAUDE-MEM-V12-PERSISTENT-MEMORY-PLUGIN-DEEP-DIVE]] | Claude-Mem v12 深度分析 — 66K stars 的 Claude Code 持久記憶外掛，Hook 驅動 + Agent SDK 壓縮 + 混合搜尋架構 | 2026-04-24 |
| [[2026-01-09-NEWTYPE-OS-MULTI-AGENT-CONTENT-PRODUCTION-ORCHESTRATION]] | newtype OS — 8 代理人多層編排內容生產系統，含信心路由品質控制與計劃-執行分離架構 | 2026-01-09 |
| [[2026-04-20-CLAUDE-CODE-MARKETPLACE-GERRIT-404-ROOT-CAUSE]] | Claude Code Marketplace 連線 Gerrit Server 回傳 404 根因分析：parseMarketplaceInput URL 分類邏輯缺陷與完整驗證流程 | 2026-04-20 |
| [[2026-04-17-CLAUDE-CODE-FEEDBACK-FRUSTRATION-DETECTION-EVENTMETADATA-ARCHITECTURE]] | Claude Code 使用者反饋系統深度分析：Frustration Detection 演算法、三管道反饋機制、EventMetadata 傳送架構 | 2026-04-17 |
| [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]] | Claude Code Hook API 原始碼深度解析：24 個事件、完整 I/O Schema、Query Loop 狀態機、Stop Hook 防循環與多種 Use Case | 2026-04-29 |
| [[2026-04-29-CLAUDE-CODE-DISABLE-MODEL-INVOCATION-SKILL-VISIBILITY-SOURCE-ANALYSIS]] | disable-model-invocation 雙道防線解析：模型清單過濾 + validateInput 拒絕、跨 Skill/Hook/Command 呼叫限制與繞過方案 | 2026-04-29 |
| [[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]] | Claude Code Telemetry 原始碼深度分析：三層 OTel 架構、8 個指標、Span 生命週期與 100 人團隊部署策略 | 2026-04-13 |
| [[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]] | Claude Code Plugin 完整生命週期 — 安裝/停用/移除/更新五大操作的檔案影響分析與三種 Scope 比較 | 2026-04-12 |
| [[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]] | npx skills 深度分析 — parseSource 解析、discoverSkills 搜尋、安裝更新機制與 Gerrit Server 相容性 | 2026-04-11 |
| [[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]] | Claude Code Team Memory 深度解析 — Server、REST API、分類規則與啟用方式 | 2026-04-08 |
| [[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]] | gstack 程式碼架構分析 — Telemetry 是怎麼做到的 | 2026-04-07 |
| [[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]] | gstack 設計哲學與多 Agent 整合架構 — Plugin、Symlink、Headless 全解 | 2026-04-07 |
| [[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]] | gstack 程式碼分析 — AI Agent / Skill 的 E2E 測試架構與 KPI 設計 | 2026-04-07 |
| [[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]] | Claude Code 記憶系統深度解析 — 六層架構、AutoDream 與動態召回 | 2026-04-07 |
| [[2026-03-18-CLAWTEAM-AGENT-SWARM-INTELLIGENCE]] | ClawTeam — AI 代理群智協調框架深度分析 | 2026-03-18 |
| [[2026-03-17-CLAWTEAM-AGENT-SWARM-INTELLIGENCE]] | ClawTeam — Agent 蜂群智能框架程式碼深度分析 | 2026-03-17 |
| [[2026-03-14-OPENCLI-CODE-ANALYSIS]] | OpenCLI — 程式碼深度分析：把任何網站變成 CLI 的 AI 原生工具 | 2026-03-14 |
| [[2026-03-12-GNAP-GIT-NATIVE-AGENT-PROTOCOL]] | GNAP — Git 原生代理人協議（Git-Native Agent Protocol）程式碼深度分析 | 2026-03-12 |
| [[2026-03-07-CLAUDE-MEMORY-ENGINE]] | Claude Memory Engine — 以 Hooks + Markdown 打造的 Claude Code 記憶與學習系統 | 2026-03-07 |
| [[2026-02-24-GITAGENT-GIT-NATIVE-AI-AGENT-STANDARD]] | gitagent — Git 原生 AI 代理人框架無關標準深度分析 | 2026-02-24 |
| [[2026-01-24-CLAUDE-CODE-HOOKS-CODE-ANALYSIS]] | claude-code-hooks — 程式碼深度分析 | 2026-01-24 |
| [[2026-01-09-OH-MY-CLAUDECODE-MULTI-AGENT-ORCHESTRATION]] | oh-my-claudecode — Claude Code 多代理人編排系統深度分析 | 2026-01-09 |
| [[2026-01-08-CLAUDE-CODE-SCHEDULER-CODE-ANALYSIS]] | claude-code-scheduler — Claude Code 跨平台定時任務排程系統深度分析 | 2026-01-08 |
| [[2025-08-31-CLAUDE-MEM-CODE-ANALYSIS]] | claude-mem — Claude Code 跨 Session 持久記憶系統深度分析 | 2025-08-31 |
| [[2023-10-27-CREWAI-CODE-ANALYSIS]] | CrewAI — 多代理人協作編排框架深度分析 | 2023-10-27 |
| [[2026-05-22-SKILLOPT-SELF-EVOLVING-AGENT-SKILLS-CODE-ANALYSIS]] | 把 Agent 技能當神經網路訓練的文字空間優化器（內部代號 ReflACT）：minibatch 反思 + 驗證閘門 + 學習率裁剪，52/52 best-or-tied | 2026-05-22 |
| [[2025-12-29-SKILLSBENCH-AGENT-SKILL-USE-BENCHMARK-CODE-ANALYSIS]] | 第一個評測「agent 用 skill 用得多好」的基準：94+5 個 Harbor 任務、oracle 100%+outcome 測試、47K skill 生態研究；與 SkillOpt 互補(產生 vs 評測) | 2025-12-29 |
| [[2026-06-24-CODEBASE-MEMORY-MCP-PRO-VS-CODEGRAPH-CODE-KNOWLEDGE-GRAPH-COMPARISON]] | 程式碼知識圖譜兩雄：Pure C 查詢引擎(memory-mcp-pro) vs TS 單一工具代理導向(CodeGraph) 深度比較 | 2026-06-24 |
