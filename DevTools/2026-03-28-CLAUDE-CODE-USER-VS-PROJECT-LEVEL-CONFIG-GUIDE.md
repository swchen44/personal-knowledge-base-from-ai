---
title: "Claude Code 配置層級完全指南：使用者層級與專案層級的管理策略"
date: 2026-03-28
category: DevTools
tags:
  - "#tools/claude-code"
  - "#tools/cli"
  - "#productivity/team-workflow"
  - "#ai/agent"
  - "#devtools/configuration"
source: "conversation"
source_type: article
author: "swchen44 + Claude"
status: notes
links:
  - "[[CLAUDE-CODE-MCP-SETUP]]"
  - "[[CLAUDE-CODE-HOOKS-PATTERNS]]"
  - "[[DEVTOOLS-TEAM-WORKFLOW]]"
---

## 摘要（Summary）

Claude Code CLI 提供了四層配置系統（Managed → Local → Project → User），讓開發者能在個人偏好與團隊共享之間取得平衡。但這套系統並非完全對稱——**Plugin 只能安裝在使用者層級**，而 Skills、Agents、Commands 則可以在兩個層級自由部署。本文系統整理各元件的層級歸屬、開關機制、安裝方式，並提供個人與團隊的實戰建議。

---

## 一、配置層級全景（Configuration Scope Overview）

Claude Code 採用**四層優先級**疊加系統，高層級覆蓋低層級的同一 key，Array 類型則合併（deep merge）：

```
優先級（高→低）

┌─────────────────────────────────────────────────────┐
│  Managed Settings（組織強制，IT 部署）               │  最高優先，不可被覆蓋
│  ~/.claude/managed-settings.json                   │
├─────────────────────────────────────────────────────┤
│  Local Settings（個人本地覆蓋，gitignore）           │  2nd
│  .claude/settings.local.json                       │
├─────────────────────────────────────────────────────┤
│  Project Settings（專案共享，commit 進 repo）        │  3rd
│  .claude/settings.json                             │
├─────────────────────────────────────────────────────┤
│  User Settings（全域個人，對所有專案生效）            │  最低優先
│  ~/.claude/settings.json                           │
└─────────────────────────────────────────────────────┘
```

> [!important] 啟動順序與合併策略
> Claude Code 啟動時依序載入這四個設定檔。衝突的 key 由高優先級覆蓋；Array 欄位（如 `hooks`、`mcpServers`）會**合併**而非替換。檔案異動後由內建 file watcher 自動偵測，無需重啟。

---

## 二、各元件層級對照表

| 元件 | 使用者層級路徑 | 專案層級路徑 | 安裝方式 | Plugin 可捆綁？ |
|------|--------------|------------|---------|--------------|
| **Plugin** | `~/.claude/plugins/cache/{name}/` | ❌ 不支援 | `/plugin install` | — |
| **Skills** | `~/.claude/skills/{name}/SKILL.md` | `.claude/skills/{name}/SKILL.md` | 手動建檔 | ✅ |
| **Agents（Subagents）** | `~/.claude/agents/{name}.md` | `.claude/agents/{name}.md` | 手動 / `/agents` UI | ✅ |
| **Commands** | `~/.claude/commands/{name}.md` | `.claude/commands/{name}.md` | 手動建檔 | ✅ |
| **MCP Server** | `~/.claude/settings.json → mcpServers` | `.claude/settings.json → mcpServers` | 手動編輯 JSON | ✅ |
| **Hooks** | `~/.claude/settings.json → hooks` | `.claude/settings.json → hooks` | 手動編輯 JSON | ✅ |

> [!warning] Plugin 的關鍵限制
> `/plugin install` 安裝的 Plugin **只能存在於使用者層級**（`~/.claude/plugins/`），目前無法安裝到專案層級。一旦安裝，**對該使用者的所有專案無條件生效**，無法在特定專案中單獨停用。

---

## 三、個人使用與團隊使用的場景分析

### 個人開發者場景

個人開發者通常管理多個不同性質的專案，Plugin 的「全域生效」特性在這裡就會顯得笨重：

```
個人開發者的檔案結構

~/.claude/
├── settings.json          ← 全域 MCP（GitHub、Obsidian）、全域 hooks
├── skills/                ← 個人常用技能（article-to-kb、commit 格式化）
├── agents/                ← 個人助理 agents
└── plugins/               ← 安裝的 plugins（無差別影響所有專案）

projectA/.claude/          ← 只在 projectA 生效的設定（前端專案）
├── settings.json          ← 前端專屬 MCP + ESLint hook
├── skills/domain-expert/  ← React 領域知識
└── agents/ux-reviewer.md  ← UX 審查 agent

projectB/.claude/          ← 只在 projectB 生效的設定（後端 API）
├── settings.json          ← 後端專屬 MCP（資料庫、內部 API）
└── agents/api-designer.md ← API 設計 agent
```

**核心策略**：Plugin 只安裝跨所有專案都用到的通用工具；專案特有的領域能力一律放到 `.claude/` 目錄，不透過 Plugin 管理。

### 團隊協作場景

團隊場景下，`.claude/` 目錄成為「Claude 環境的版本控制基礎設施」：

```
團隊 Repo 結構

repo/
├── .claude/
│   ├── settings.json          ← commit 進 repo，全團隊共享
│   │   ├── mcpServers         ← 專案專屬 MCP（內部 API server）
│   │   ├── hooks              ← 共用 hooks（lint on stop、test on write）
│   │   └── permissions        ← 允許執行的指令清單
│   ├── skills/
│   │   ├── domain-expert/     ← 這個 repo 的領域知識
│   │   └── code-review/       ← 標準化 code review skill
│   ├── agents/
│   │   ├── architect.md       ← 架構顧問 agent
│   │   └── qa-engineer.md     ← QA 自動化 agent
│   └── commands/
│       └── release-notes.md   ← 生成 release notes 的 command
├── .gitignore
│   └── # .claude/settings.local.json   ← 個人覆蓋不 commit
└── README.md
    └── # "Claude Code 環境說明：請先執行 /plugin install ..."
```

**核心優勢**：`git clone` 即獲得完整的 Claude 協作環境，新成員零配置上手。

> [!tip] Plugin 的團隊標準化方式
> 由於 Plugin 本身無法 commit 進 repo，改用以下方式標準化：
> 1. 在 `.claude/plugin-marketplaces.json` 中指向公司內部 plugin marketplace
> 2. 在 README 說明「請執行 `/plugin install xxx` 安裝以下 Plugin」
> 3. 將真正重要的能力改寫成 `.claude/skills/` 或 `.claude/agents/`，才能確保團隊一致性

---

## 四、細部開關設定

### (a) 個人模式下的細部開關

#### MCP Server：`disabled` 欄位

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" }
    },
    "obsidian": {
      "command": "node",
      "args": ["/path/to/obsidian-mcp/server.js"],
      "disabled": true    // ← 暫時停用，移除此行則重新啟用
    }
  }
}
```

#### Plugin：CLI 指令操作

```bash
# 安裝
/plugin install plugin-name@marketplace-name

# 停用（保留設定但不啟動）
/plugin disable plugin-name

# 重新啟用
/plugin enable plugin-name

# 完全移除
/plugin uninstall plugin-name
```

> [!warning] Plugin 無法按專案開關
> 以上 `/plugin disable` 是**全域操作**，對所有專案生效。目前沒有任何機制能讓某個 Plugin 只在特定專案停用。

#### Skills：檔案存在即生效

```
開啟：檔案存在於 ~/.claude/skills/{name}/SKILL.md 即自動生效
關閉方法一：刪除目錄（rm -rf ~/.claude/skills/{name}/）
關閉方法二：在 SKILL.md frontmatter 加 disabled: true（部分版本支援）
```

#### Hooks：`disabled` 欄位

```json
// ~/.claude/settings.json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "npm run lint && npm run test:unit",
            "disabled": true    // ← 暫時停用
          }
        ]
      }
    ]
  }
}
```

### (b) 團隊模式下的細部開關

#### 共享設定 + 個人覆蓋模式

這是最重要的模式：team 設定放 `.claude/settings.json`，個人例外放 `settings.local.json`：

```json
// .claude/settings.json（commit 進 repo，全團隊生效）
{
  "mcpServers": {
    "internal-api": {
      "command": "node",
      "args": ["./scripts/mcp-server.js"],
      "env": {
        "API_BASE": "https://api.internal.company.com"
      }
    }
  },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "npm run lint && npm run test:unit"
          }
        ]
      }
    ]
  }
}
```

```json
// .claude/settings.local.json（gitignore，只影響自己）
{
  "mcpServers": {
    "internal-api": {
      "disabled": true        // 個人開發環境沒有內部 API，本地停用
    }
  },
  "hooks": {
    "Stop": []                // 開發迭代期暫時停用 lint hook，加速流程
  }
}
```

#### 安裝專案層級 Hooks（手動）

> [!info] 沒有標準 CLI 安裝指令
> 無論是專案層級還是使用者層級的 Hooks，目前**沒有** CLI 安裝指令。只能透過以下方式設定：
> 1. 直接編輯 `.claude/settings.json`
> 2. 使用 Claude Code 的 `/config` 互動介面（Settings UI）
> 3. 請 Claude 幫你生成 hook 設定並寫入檔案

這是 Claude Code 目前設計哲學「file-based, git-native」的體現——設定是純文字，用 git 管理。

---

## 五、Plugin Scale 問題與替代策略

### 問題根源

```
Plugin 的 Scale 困境

用戶安裝 10 個 Plugin
         │
         ▼
所有專案無差別載入全部 Plugin
         │
         ├── projectA（只需要 2 個）← 仍載入 10 個
         ├── projectB（需要 5 個）  ← 仍載入 10 個
         └── projectC（需要 3 個）  ← 仍載入 10 個

❌ 無法按專案控制哪些 Plugin 生效
❌ Plugin 安裝的 MCP + hooks 寫入 ~/.claude/settings.json，
   解除安裝時需確認已完整清理，否則 Claude Code 啟動會報錯
```

### 替代策略

#### 策略一：Plugin 只裝「跨專案通用工具」

```
✅ 適合用 Plugin 的：
   個人知識庫工具（article-to-kb）
   通用 commit 訊息助手
   個人 coding 風格偏好

❌ 不適合用 Plugin 的：
   只在某個 repo 有意義的 domain knowledge
   需要專案特定環境變數的工具
   團隊共享的流程（改用 .claude/ standalone 設定）
```

#### 策略二：專案用 Standalone 設定替代 Plugin

```
.claude/
├── settings.json      ← 專案 MCP + hooks（commit 進 repo）
├── skills/
│   └── domain-expert/ ← 這個專案的領域知識（取代 Plugin 的 skill）
│       └── SKILL.md
└── agents/
    └── architect.md   ← 這個專案的架構顧問 agent（取代 Plugin 的 agent）
```

每個專案完全隔離，新成員 clone 就有完整環境，不依賴個人的 Plugin 安裝狀態。

#### 策略三：Plugin Marketplace 標準化（團隊）

```json
// .claude/plugin-marketplaces.json（commit 進 repo）
[
  {
    "name": "company-plugins",
    "url": "https://github.com/your-company/claude-plugins"
  }
]
```

搭配 README 說明「請執行以下指令安裝團隊標準 Plugin」，讓每個成員安裝相同版本。

---

## 六、市面上的第三方解決方案

目前針對 Claude Code Plugin 層級管理的第三方工具尚不成熟，但有幾個相關方向：

### direnv（目錄進入自動切換環境變數）

```bash
# 每個專案目錄下的 .envrc
# 搭配 direnv，進入目錄自動 source，離開自動還原
export CLAUDE_DISABLE_PLUGIN_X=true
```
搭配自定義 hook 讀取此環境變數決定行為，可以實現偽「按目錄開關」的效果。

### Mise（多版本工具與環境變數管理）

[Mise](https://mise.jdx.dev/) 支援 per-project 的環境變數設定（`.mise.toml`），可以讓 Claude Code 的 MCP server 在不同專案使用不同版本或設定，間接達成部分隔離效果。

### 自製 Wrapper Script

```bash
#!/bin/bash
# ~/bin/claude-project
# 根據當前目錄動態組合 settings，再傳給 claude

EXTRA_CONFIG=""
if [ -f "./.claude-profile/settings.json" ]; then
  EXTRA_CONFIG="--config ./.claude-profile/settings.json"
fi

claude $EXTRA_CONFIG "$@"
```

> [!note] 期待官方解決
> 最根本的解決方案是等待 Claude Code 官方支援 Plugin 的 per-project 啟用/停用機制。在此之前，**最乾淨的替代方案是完全避開 Plugin，改用 `.claude/` standalone 設定**。如有強烈需求，可透過 `/feedback` 指令向 Anthropic 回報。

---

## 七、決策流程圖（Decision Flowchart）

```
我需要為 Claude Code 加入一個新能力
                  │
                  ▼
      這個能力是「所有專案都需要」嗎？
         │                    │
        YES                   NO
         │                    │
         ▼                    ▼
   考慮用 Plugin         放到專案的 .claude/
   或 ~/.claude/          skills/、agents/
                          settings.json
         │
         ▼
   團隊也需要嗎？
    │         │
   YES        NO
    │         │
    ▼         ▼
  .claude/  ~/.claude/
  （commit  （個人設定）
   進 repo）
         │
         ▼
   能用 standalone 設定（skills/agents）嗎？
         │                          │
        YES                         NO
         │                          │
         ▼                          ▼
   優先用 .claude/             考慮 Plugin，但
   standalone 設定             接受全域生效的限制
   （最高可控性）
```

---

## 八、專業建議總結

> [!tip] 黃金原則：Plugin 是個人工具箱，`.claude/` 是團隊基礎設施

### 個人開發者

1. **Plugin 要精簡**：只安裝真正跨所有專案通用的工具
2. **全域 MCP**：常用服務（GitHub、Obsidian）放 `~/.claude/settings.json`
3. **按專案設定**：專案特有的 MCP、hooks、skills 放 `.claude/`，隔離乾淨
4. **`settings.local.json`**：用來暫時覆蓋不適合目前工作情境的設定

### 團隊

1. **Commit `.claude/settings.json`**：讓整個團隊共享 hooks、MCP、permissions 設定
2. **Gitignore `settings.local.json`**：留給個人覆蓋，不強制統一
3. **Skills 和 Agents 放 repo**：domain knowledge 隨 code 一起版控，新成員立刻獲益
4. **Plugin 清單文件化**：在 README 列出「建議安裝的 Plugin」，但接受每人自行安裝

### 已知設計缺口

> [!warning] 目前的限制
> - Plugin 無法按專案啟用/停用（最常見的痛點）
> - Hooks、MCP Server 沒有 CLI 安裝指令，需手動編輯 JSON
> - Plugin 安裝後的 MCP 和 hooks 寫入 `~/.claude/settings.json`，解除安裝時需確認完整清理

---

## 我的心得（My Takeaways）

Claude Code 的配置系統設計哲學是「**file-based, git-native**」——所有設定都是純文字檔，可以版控、可以 diff、可以 code review。這讓團隊共享設定非常自然，但也帶來了 Plugin 無法專案化的設計限制。

最清晰的心智模型：
- **Plugin** = 個人瑞士刀（裝了就全域用，方便但不靈活）
- **`.claude/` 目錄** = 專案的 Claude 環境（隨 repo 版控，精確可控）

不要試圖用 Plugin 做到專案層級的事，也不要把專案特有的領域邏輯放進個人 Plugin。兩者定位清晰，混用才會帶來管理困境。

## 待補充（Open Questions）

- 四層配置系統中，Array 類型的「deep merge」行為在哪些欄位有效？所有 Array 欄位都合併，還是只有特定欄位（如 `hooks`、`mcpServers`）才合併？（建議搜尋：`Claude Code settings deep merge array policy`）
- Plugin 的「全域生效、不能按專案停用」是否為官方已知的設計缺陷，並已排入 roadmap？有無 issue 或 RFC 可追蹤進度？（建議搜尋：`Claude Code plugin per-project disable roadmap issue`）
- `Managed Settings`（組織強制）的部署方式是什麼？IT 管理員需要透過 MDM、企業登入策略，還是有其他機制部署 `~/.claude/managed-settings.json`？（建議搜尋：`Claude Code managed settings enterprise deployment MDM`）
- `direnv` 與 Claude Code 結合的「偽按目錄開關 Plugin」方式在實作上是否已有人驗證可行？有沒有已知的邊界情況（如 tmux session 繼承環境變數）會導致這個方法失效？（建議搜尋：`direnv Claude Code plugin per-project toggle workaround`）
- Hooks 的 `disabled: true` 欄位在哪個版本的 Claude Code 開始支援？`settings.local.json` 的 `"Stop": []` 覆蓋能確實停用所有繼承自 project settings 的 hooks 嗎？（建議搜尋：`Claude Code hooks disabled field settings.local override`）
- Skills 的 `disabled: true` frontmatter 欄位是否已是正式支援的功能，還是文件中提到的「部分版本支援」？官方文件對此有何說明？（建議搜尋：`Claude Code skill disabled frontmatter official support`）

## 相關連結（Related）

- [[CLAUDE-CODE-MCP-SETUP]] — MCP Server 的安裝與設定方式詳解
- [[CLAUDE-CODE-HOOKS-PATTERNS]] — Hooks 的實際使用模式與範例
- [[DEVTOOLS-TEAM-WORKFLOW]] — 開發團隊工具鏈的整體配置策略
- [[2026-03-02-PSA-CLAUDE-CODE-PLUGINS-LOADING-TWICE-KILLING-CONTEXT]] — settings.json 中 enabledPlugins 設定與外掛重複載入問題的實戰診斷
- [[2026-03-31-CLAUDE-CODE-WORKTREE-X-REPO-MULTI-REPO-PARALLEL-DEVELOPMENT]] — Worktree 模式下的專案層級配置隔離策略

## References

- [Claude Code 官方文件 - Settings](https://docs.anthropic.com/en/claude-code/settings)
- [Claude Code 官方文件 - Plugins](https://docs.anthropic.com/en/claude-code/plugins)
- [Claude Code 官方文件 - MCP](https://docs.anthropic.com/en/claude-code/mcp)
- [Claude Code 官方文件 - Hooks](https://docs.anthropic.com/en/claude-code/hooks)
