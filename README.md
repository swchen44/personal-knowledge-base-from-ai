# personal-knowledge-base-from-ai
📚 Personal knowledge base — articles, videos, and research notes curated with AI. Obsidian-compatible with tags, links, and knowledge graph support.

## 📌 Recent Notes
- [構建 Claude Code 的經驗：我們如何使用 Skills（技能擴充）](./AI/2026-03-17-LESSONS-FROM-BUILDING-CLAUDE-CODE-HOW-WE-USE-SKILLS.md) — Anthropic 內部 9 大 Skills 分類與最佳實踐，含完整原文翻譯
- [claude-code-hooks — 程式碼深度分析](./CodeAnalysis/2026-01-24-CLAUDE-CODE-HOOKS-CODE-ANALYSIS.md) — 零依賴 Node.js Hook 集合架構分析，含雙模組模式、Regex 安全等級設計與 262 個測試
- [Claude Code 最被低估的功能：Hooks 完整指南](./DevTools/2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS.md) — 13 個 Hook 事件類型完整解說，含危險指令阻擋、機密保護、Slack 通知等實用範例
- [2 分鐘啟用 Claude Code LSP：你可能錯過的最重要升級](./DevTools/2026-02-28-2-MINUTE-CLAUDE-CODE-UPGRADE-LSP.md) — 啟用 LSP 後程式碼導覽從 30-60 秒縮短至 50ms，包含完整安裝步驟與 CLAUDE.md 設定
- [PSA：你的 Claude Code 外掛可能一直重複載入，正在耗盡上下文視窗](./DevTools/2026-03-02-PSA-CLAUDE-CODE-PLUGINS-LOADING-TWICE-KILLING-CONTEXT.md) — 診斷與修復 Plugin/Skill 重複載入問題，可減少 50-60% 前置開銷
- [Claude Memory Engine — Hooks + Markdown 記憶與學習系統](./CodeAnalysis/2026-03-07-CLAUDE-MEMORY-ENGINE.md) — Hook-driven 架構讓 Claude Code 自動儲存 session、偵測踩坑、跨裝置同步，零依賴
- [WezTerm macOS 聽寫版本：完整工作階段技術摘要](./DevTools/2026-03-20-WEZTERM-SESSION-TECHNICAL-SUMMARY.md) — 踩坑紀錄、關鍵決策、錯誤修復速查表
- [ClawTeam — Agent 蜂群智能框架程式碼深度分析](./CodeAnalysis/2026-03-17-CLAWTEAM-AGENT-SWARM-INTELLIGENCE.md) — 零基礎設施 Multi-Agent 框架，CLI 驅動 Agent 蜂群自動協作
- [CrewAI — 多代理人協作編排框架深度分析](./CodeAnalysis/2023-10-27-CREWAI-CODE-ANALYSIS.md) — 46K⭐ Python 多 Agent 框架：Crews（自主協作）+ Flows（事件驅動工作流）雙軌設計，完全獨立於 LangChain
- [claude-code-scheduler — Claude Code 跨平台定時任務排程系統深度分析](./CodeAnalysis/2026-01-08-CLAUDE-CODE-SCHEDULER-CODE-ANALYSIS.md) — 485⭐ OS 原生排程器封裝（launchd/crontab/Task Scheduler），支援自然語言設定、Git Worktree 隔離、自主執行模式
- [claude-mem — Claude Code 跨 Session 持久記憶系統深度分析](./CodeAnalysis/2025-08-31-CLAUDE-MEM-CODE-ANALYSIS.md) — 38K ⭐ Claude Code 長期記憶插件架構深度分析：Hook 事件驅動、SQLite+Chroma 混合搜尋、漸進式揭露 MCP 工具
- [二十分鐘從零搭建極簡版投研 Agent：Claude Code 完整教程](./AI/2026-03-16-BUILD-AGENT-WITH-CLAUDE-CODE-IN-20-MINUTES.md) — Windows 環境下用 Claude Code 二十分鐘建立投研 Agent，含安裝、設定、個性化資料填充全流程
- [從源碼編譯 WezTerm macOS 聽寫分支，並解決中文字型顯示問題](./DevTools/2026-03-20-WEZTERM-MACOS-DICTATION-BUILD-AND-CJK-FIX.md) — 自編譯 WezTerm feat/macos-dictation 分支、解決 CJK 亂碼與字寬異常、打包為 .app bundle

- [西門子歌美颯 HR Head Jeffery 訪談](./Career/2023-07-04-SIEMENS-GAMESA-HR-HEAD-JEFFERY-INTERVIEW.md) — HR 職涯瓶頸、台灣離岸風電產業、政治敏感度與 MBA 留學決策
- [【外商秘密】努力十年還卡在同級別？揭露 Competency 三大模型](./Career/2025-12-12-WHY-STUCK-AT-SAME-LEVEL-COMPETENCY-THREE-MODELS.md) — 外商人資 Jasmin 揭露外商晉升的核心標準：Competency 三大模型（思維、行為、合作能力），以及為何台灣人常在外商受挫
- [【Stakeholder #1】為什麼你做得越多，反而越容易被卡？](./Career/2025-12-23-STAKEHOLDER-1-WHY-MORE-WORK-GETS-YOU-STUCK-HR-REVEALS-TRUTH.md) — HR Jasmin 揭露：努力錯方向比不努力更危險，真正的 Stakeholder 不是你的直屬主管
- [gitagent — Git 原生 AI 代理人框架無關標準深度分析](./CodeAnalysis/2026-02-24-GITAGENT-GIT-NATIVE-AI-AGENT-STANDARD.md) — Git Repository 就是你的 Agent：框架無關、可版本控制、內建 FINRA 合規驗證的 AI 代理人定義標準
- [GNAP — Git 原生代理人協議程式碼深度分析](./CodeAnalysis/2026-03-12-GNAP-GIT-NATIVE-AGENT-PROTOCOL.md) — 零基礎設施的多代理人協調協議：4 種 JSON 實體 + git = 完整 AI 代理人協作平台
- [Claude Skill 評估框架：3 個技能、一個下午、真實數據](./AI/2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA.md) — 用 skill-creator eval framework 系統測試 3 個生產 skill，揭露假陽性、序列錯誤與 Benchmark 量化結果
- [每位 ADK 開發者都應了解的 5 種代理人技能設計模式](./AI/2026-03-18-5-AGENT-SKILL-DESIGN-PATTERNS-EVERY-ADK-DEVELOPER-SHOULD-KNOW.md) — Tool Wrapper、Generator、Reviewer、Inversion、Pipeline 五種模式，涵蓋代理人技能設計的完整工具箱
- [Karpathy 的 AgentHub：建立你第一個 AI 代理人群集的實作指南](./AI/2026-03-17-KARPATHYS-AGENTHUB-A-PRACTICAL-GUIDE-TO-BUILDING-YOUR-FIRST-AI-AGENT-SWARM.md) — 代理人原生（agent-native）基礎設施：用 DAG + 訊息板取代 Git 分支與 PR，讓 AI 代理人無需人類審查即可非同步協作程式碼

- [NemoClaw：NVIDIA 真正為 OpenClaw 用戶解決了什麼——以及沒解決的是什麼](./AI/2026-03-17-NVIDIA-ANNOUNCED-NEMOCLAW-WHAT-NVIDIA-ACTUALLY-SOLVES-FOR-OPENCLAW-USERS-AND-WHAT-IT-DOES-NOT.md) — NVIDIA 發布的 OpenClaw 安全治理層評估：跨進程執行架構正確，但仍是 alpha 軟體
- [Claude Code 官方文件：用 Skill 擴充 Claude 的能力](./AI/2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION.md) — Claude Code 官方 Skills 系統完整說明：Skill Creator、評估（eval）、分叉模式（fork mode）、open standard 架構
- [Claude Skills 2.0：真正有效的自我改善 AI 能力](./AI/2026-03-07-CLAUDE-SKILLS-2.0-THE-SELF-IMPROVING-AI-CAPABILITIES-THAT-ACTUALLY-WORK.md) — Skills 2.0 回饋循環系統：自動建立、測試、A/B 比較、優化
- [Claude Skill Eval 框架：一個下午、三個技能、真實數據](./AI/2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA.md) — 實戰評估 Claude Skills 框架：結構化測試流程與真實效果數據
