# DevTools Index

| 筆記 | 摘要 | 日期 |
|------|------|------|
| [[2026-09-06-CODEX-CLI-VS-CLAUDE-CODE-AUTOMATION-CHEAT-SHEET]] | Codex CLI 與 Claude Code 的互動快捷鍵、非互動自動化、結構化事件、安全邊界與長時間 Agent Supervisor 速查表，含一張可離線閱讀的圖表 | 2026-09-06 |
| [[2026-07-05-TERMINAL-MEMORY-MANAGEMENT-AND-CROSS-PLATFORM-PERSISTENCE]] | Ghostty / Claude Code 記憶體暴增診斷、環境變數止血、tmux / psmux 工作階段持久化與跨平台終端選型 | 2026-07-05 |
| [[2026-05-16-CLAUDE-CODE-HEADLESS-MODE-AUTO-MEMORY-DISABLE]] | Headless 模式（-p）完整讀取 auto memory；`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 阻斷讀取與背景寫入但不阻止模型直接寫入；四種禁用方法比較 | 2026-05-16 |
| [[2026-05-03-CLAUDE-CODE-PLAN-MODE-VS-SUPERPOWERS-CONFLICT-ANALYSIS]] | Plan Mode vs SuperPowers 衝突深度分析：原始碼追蹤 EnterPlanMode 攔截、Auto Mode 停用、計畫路徑不相容、社群 Issues 與最佳實踐建議 | 2026-05-03 |
| [[2026-05-03-CLAUDE-CODE-PLUGIN-CANNOT-INSTALL-CLAUDEMD-RULES-ALTERNATIVES]] | Plugin 無法安裝 CLAUDE.md/Rules 原始碼驗證：manifest 12 component 無 rules、paths: → globs 命名混淆、#17204/#23478 已知 bug、三種替代方案（Setup Hook / @path / Skill）比較矩陣 | 2026-05-03 |
| [[2026-04-19-CLAUDE-CODE-PLUGIN-JSON-DEPENDENCIES-SHARED-SKILLS-SOURCE-ANALYSIS]] | Plugin.json 依賴系統與共享 Skills 原始碼分析：三層驗證機制、實戰寫法（marketplace.json + plugin.json 雙宣告）、實驗結果（A→B→C 鏈）、Issue #9444 / #27113 社群附錄 | 2026-04-19 |
| [[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]] | Skill 完全指南：閉包載入、Token 按需注入、壓縮 5K/25K 保留、三種附件定義（skill_listing / skill_discovery / invoked_skills）、SkillTool Schema vs skill_listing 釐清、7 撰寫技巧 | 2026-04-17 |
| [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]] | 四個設定檔完全指南：GlobalConfig vs SettingsSchema、五源 merge、Plugin 啟停四層控制、7 個 policy-only 閘門 | 2026-04-17 |
| [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] | Skill/Plugin 安全機制全解析：frontmatter 進階欄位 + 冒名防護 + 17 項安全檢查 + 企業 Marketplace 部署 | 2026-04-16 |
| [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] | CLAUDE.md 與 Skills 的熱載入機制：Symlink 修改是否即時生效的原始碼驗證 | 2026-04-14 |
| [[2026-04-12-CLAUDE-CODE-WORKTREE-FILE-OPERATIONS-AND-REPO-INTEGRATION]] | Claude Code Worktree 檔案操作全解析：從原始碼追蹤新增/修改/讀取，到 repo Multi-Repo 整合實戰 | 2026-04-12 |
| [[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]] | Claude Code 監控實戰：OpenTelemetry 設定、生產堆疊與團隊數據揭示的 8 個關鍵指標 | 2026-04-11 |
| [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] | Claude Code 原始碼洩漏！11 個隱藏秘密完整解析 | 2026-04-02 |
| [[2026-03-31-REPO-MULTI-REPO-MANAGEMENT-AND-GIT-WORKTREE-ADVANCED-GUIDE]] | Multi-Repo 管理利器：repo 工具原理剖析 + Git Worktree 進階實戰（含原生 --worktree 模式） | 2026-03-31 |
| [[2026-03-31-CLAUDE-CODE-WORKTREE-X-REPO-MULTI-REPO-PARALLEL-DEVELOPMENT]] | Claude Code Worktree × repo Multi-Repo 並行開發完全指南 | 2026-03-31 |
| [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] | Claude Code 配置層級完全指南：使用者層級與專案層級的管理策略 | 2026-03-28 |
| [[2026-03-20-WEZTERM-SESSION-TECHNICAL-SUMMARY]] | WezTerm macOS 聽寫版本：完整工作階段技術摘要 | 2026-03-20 |
| [[2026-03-20-WEZTERM-MACOS-DICTATION-BUILD-AND-CJK-FIX]] | 從源碼編譯 WezTerm macOS 聽寫分支，並解決中文字型顯示問題 | 2026-03-20 |
| [[2026-03-02-PSA-CLAUDE-CODE-PLUGINS-LOADING-TWICE-KILLING-CONTEXT]] | PSA：你的 Claude Code 外掛（Plugin）可能一直重複載入，正在耗盡你的上下文視窗（Context Window） | 2026-03-02 |
| [[2026-02-28-2-MINUTE-CLAUDE-CODE-UPGRADE-LSP]] | 2 分鐘啟用 Claude Code LSP：你可能錯過的最重要升級 | 2026-02-28 |
| [[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]] | Claude Code 最被低估的功能：Hooks 完整指南 | 2026-01-25 |
| [[2026-05-24-WHY-AI-WEBSITE-CRASHES-AFTER-LAUNCH-BACKEND-SCALING]] | Debug Tuboshu 用手搖店成長比喻，拆解 AI 生成 SaaS 從能動到能撐住流量所需的後端擴展路徑 | 2026-05-24 |
| [[2026-05-30-MOSHI-MOBILE-TERMINAL-FOR-CODING-AGENTS]] | 用手機遠端操控 Claude Code/Codex 等 AI 編碼代理人的 iOS/Android 終端機 App | 2026-05-30 |
| [[2026-08-30-MARKDOWN-RENDERER-SPEC-RESEARCH-COMMONMARK-GFM-OBSIDIAN]] | Markdown 渲染器前期研究：CommonMark/GFM 兩層規格、Obsidian 實作即規格、擴充語法完整對照與實作路線圖 | 2026-08-30 |
