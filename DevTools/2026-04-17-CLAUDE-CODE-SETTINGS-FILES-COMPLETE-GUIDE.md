---
title: "Claude Code 設定檔完全指南：~/.claude.json、settings.json、Plugin 關聯與常見錯誤"
date: 2026-04-17
category: DevTools
tags:
  - "#devtools/claude-code"
  - "#devtools/configuration"
  - "#ai/agent-architecture"
  - "#tools/cli"
source: "conversation"
source_type: article
author: "swchen44 + Claude"
status: notes
links:
  - "[[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]"
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]]"
---

## 摘要（Summary）

深入追蹤 Claude Code 反編譯原始碼（`config.ts`、`settings.ts`、`types.ts`、`constants.ts`），完整解析四個設定檔（`~/.claude.json`、`~/.claude/settings.json`、`.claude/settings.json`、`.claude/settings.local.json`）的功能、Schema、合併優先級、Plugin 關聯，以及常見錯誤與排查方式。核心發現：**`~/.claude.json` 是程式狀態檔（GlobalConfig），與 `settings.json`（SettingsSchema）完全不同用途**；settings 五源 merge（Plugin → User → Project → Local → Flag → Policy）中 **policySettings 永遠啟用不可停用**；Plugin 的啟停透過 `enabledPlugins` 控制，可在四個層級設定。

## 關鍵洞察（Key Insights）

- **`~/.claude.json` 不是設定檔**：它是 Claude Code 程式自動讀寫的狀態檔（OAuth、theme、onboarding），不參與 settings merge — 參見 [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]
- **Settings 五源合併**：Plugin(base) → userSettings → projectSettings → localSettings → flagSettings → policySettings，後者覆蓋前者，Array 欄位合併去重
- **policySettings 和 flagSettings 永遠啟用**：`--setting-sources=""` 可停用 user/project/local，但 policy 和 flag **永遠在**
- **Plugin 啟停有四層控制**：`enabledPlugins`（四層 settings）、`isPluginBlockedByPolicy`（policy 強制禁用）、`strictKnownMarketplaces`（marketplace 白名單）、`strictPluginOnlyCustomization`（封鎖非 plugin 來源）

## 詳細內容（Details）

### 一、檔案總覽

```
┌──────────────────────────────────────────────────────────────────┐
│                    Claude Code 設定檔架構                          │
│                                                                  │
│  ~/.claude.json              ← GlobalConfig（程式狀態/偏好）      │
│  ~/.claude/settings.json     ← User Settings（全域行為設定）      │
│  .claude/settings.json       ← Project Settings（專案共享，git）  │
│  .claude/settings.local.json ← Local Settings（個人，gitignored） │
│                                                                  │
│  /etc/claude-code/managed-settings.json    ← Policy（企業管控）   │
│  /etc/claude-code/managed-settings.d/*.json← Policy Drop-in      │
└──────────────────────────────────────────────────────────────────┘
```

### 二、`~/.claude.json` — 程式狀態檔（GlobalConfig）

**路徑**：`$CLAUDE_CONFIG_DIR/.claude.json` 或 `~/.claude.json`

> [!important] 這是程式狀態檔，不是行為設定檔
> 儲存 OAuth token、UI 偏好、onboarding 狀態等。**不參與 settings merge**。由 Claude Code 自動讀寫。

**主要欄位**：

| 類別 | 欄位 | 用途 |
|------|------|------|
| 認證 | `primaryApiKey`、`oauthAccount` | OAuth |
| UI | `theme`、`verbose`、`editorMode`、`diffTool`、`showTurnDuration` | 偏好 |
| 行為 | `autoCompactEnabled` | 自動壓縮開關 |
| MCP | `mcpServers` | MCP server 設定 |
| 狀態 | `numStartups`、`hasCompletedOnboarding`、`tipsHistory` | 追蹤 |

**快取機制**：啟動時讀取一次，背景 mtime watcher 監控變化（`startGlobalConfigFreshnessWatcher()`）

**寫入保護**（`config.ts:1219`）：`saveConfigWithLock` 會再讀一次確認 auth 沒被覆蓋

### 三、Settings 檔案（SettingsSchema）

三個 settings 檔案共用**同一個 Zod Schema**（`SettingsSchema`），支援完全相同的欄位集：

| 欄位 | 用途 | 範例 |
|------|------|------|
| `permissions` | 工具權限（allow/deny/ask） | `{ "allow": ["Read", "Bash(npm *)"] }` |
| `hooks` | 事件鉤子 | `{ "PostToolUse": [...] }` |
| `model` | 預設模型 | `"claude-sonnet-4-6"` |
| `env` | 環境變數 | `{ "DEBUG": "1" }` |
| `language` | 回覆語言 | `"chinese"` |
| `attribution` | commit/PR 署名 | `{ "commit": "...", "pr": "..." }` |
| `enabledPlugins` | 啟用的 plugin | `{ "fmt@tools": true }` |
| `extraKnownMarketplaces` | 額外 marketplace | `{ "company-tools": {...} }` |
| `enableAllProjectMcpServers` | 自動批准 MCP | `true` |
| `worktree` | Worktree 設定 | `{ "symlinkDirectories": [...] }` |
| `disableAllHooks` | 停用所有 hooks | `true` |
| `statusLine` | 自訂狀態列 | `{ "type": "command", "command": "..." }` |
| `outputStyle` | 輸出風格 | `"concise"` |
| `cleanupPeriodDays` | transcript 保留天數 | `30` |
| `apiKeyHelper` | API key 腳本路徑 | `"/path/to/script"` |
| `claudeMdExcludes` | 排除特定 CLAUDE.md | `["/path/to/CLAUDE.md"]` |
| `respectGitignore` | 檔案選擇器遵守 gitignore | `true` |
| `sandbox` | Sandbox 設定 | `{ ... }` |

**Policy-only 欄位**（只在 managed-settings.json 中有意義）：

| 欄位 | 用途 |
|------|------|
| `allowManagedPermissionRulesOnly` | 只用 managed 的權限規則 |
| `allowManagedHooksOnly` | 只跑 managed 的 hooks |
| `allowManagedMcpServersOnly` | MCP allowlist 只看 managed |
| `strictPluginOnlyCustomization` | 封鎖非 plugin 的 skills/agents/hooks/mcp |
| `strictKnownMarketplaces` | Marketplace 白名單 |
| `blockedMarketplaces` | Marketplace 黑名單 |
| `availableModels` | 模型白名單 |
| `pluginTrustMessage` | 自訂 plugin 信任訊息 |
| `forceLoginMethod` | 強制登入方式 |

### 四、合併順序（Priority）

```
 最低優先                                                最高優先
 ──────────────────────────────────────────────────────────►

 Plugin     User         Project       Local        Flag      Policy
 Settings   Settings     Settings      Settings     Settings  Settings
 (base)     (~/.claude/  (.claude/     (.claude/    (--flag)  (managed-
             settings.    settings.     settings.             settings.
             json)        json)         local.json)           json)
```

**原始碼**（`settings.ts:674`）：逐源 `mergeWith()` + `settingsMergeCustomizer`
- **Array**：合併去重（不覆蓋）
- **Object**：深度 merge（後者 key 覆蓋）
- **Scalar**：後者覆蓋前者

> [!warning] policySettings 和 flagSettings **永遠啟用**
> ```typescript
> // constants.ts:159-166
> export function getEnabledSettingSources(): SettingSource[] {
>     const result = new Set(getAllowedSettingSources())
>     result.add('policySettings')  // ← 永遠加入
>     result.add('flagSettings')    // ← 永遠加入
>     return Array.from(result)
> }
> ```

### 五、Settings 與 Plugin 的關聯

> [!important] 核心概念
> Settings 檔案中有**多個欄位**專門用來控制 Plugin 的行為。這些欄位可以在不同層級設定，實現從個人偏好到企業管控的完整控制鏈。

#### 5.1 `enabledPlugins` — Plugin 啟停開關

```json
// 格式：{ "plugin-name@marketplace-name": true | false | ["scope1", "scope2"] }
{
  "enabledPlugins": {
    "formatter@company-tools": true,          // 啟用
    "deprecated-tool@old-market": false,      // 停用
    "linter@tools": ["user", "project"]       // 限定 scope
  }
}
```

**四層控制**：

| 層級 | 位置 | 優先級 | 典型用途 |
|------|------|--------|---------|
| User | `~/.claude/settings.json` | 低 | 個人偏好啟停 |
| Project | `.claude/settings.json` | 中 | 團隊統一啟用 |
| Local | `.claude/settings.local.json` | 高 | 個人覆蓋團隊設定 |
| Policy | `managed-settings.json` | **最高** | 企業強制啟用/禁用 |

**範例：團隊強制 + 個人覆蓋**

```json
// .claude/settings.json（團隊共享，git 追蹤）
{
  "enabledPlugins": {
    "formatter@company-tools": true,
    "security-checker@company-tools": true,
    "fun-plugin@third-party": true
  }
}

// .claude/settings.local.json（個人，gitignored）
{
  "enabledPlugins": {
    "fun-plugin@third-party": false   // ← 個人停用，覆蓋團隊
  }
}

// managed-settings.json（企業 IT 部署）
{
  "enabledPlugins": {
    "security-checker@company-tools": true,      // ← 強制啟用，不可停用
    "malicious-plugin@unknown": false             // ← 強制禁用
  }
}
```

合併結果：
- `formatter@company-tools` → **啟用**（project 設 true，無覆蓋）
- `security-checker@company-tools` → **啟用**（policy 強制 true）
- `fun-plugin@third-party` → **停用**（local 覆蓋 project）
- `malicious-plugin@unknown` → **禁用**（policy 強制 false，`isPluginBlockedByPolicy()` 擋住）

#### 5.2 `extraKnownMarketplaces` — 預註冊 Marketplace

```json
// .claude/settings.json — 團隊預註冊公司 marketplace
{
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": {
        "source": "github",
        "repo": "your-company/internal-plugins"
      }
    }
  }
}
```

員工 clone 專案後，marketplace 自動出現，不用手動 `claude plugin marketplace add`。

#### 5.3 Plugin 安全閘門（Policy-only 欄位）

```json
// managed-settings.json — 企業 IT 部署
{
  // 閘門 1：Marketplace 白名單
  "strictKnownMarketplaces": [
    { "source": "github", "repo": "your-company/plugins" },
    { "source": "hostPattern", "hostPattern": "*.yourcompany.com" }
  ],

  // 閘門 2：Marketplace 黑名單（優先於白名單）
  "blockedMarketplaces": [
    { "source": "github", "repo": "malicious/repo" }
  ],

  // 閘門 3：封鎖非 plugin 的 skills/hooks/agents/mcp
  "strictPluginOnlyCustomization": ["skills", "hooks", "agents", "mcp"],
  // 效果：~/.claude/skills/ 和 .claude/skills/ 被忽略
  //       只有 plugin 提供的 skills/hooks/agents 生效

  // 閘門 4：只用 managed 的權限規則
  "allowManagedPermissionRulesOnly": true,
  // 效果：user/project/local 的 permissions 全部忽略

  // 閘門 5：只跑 managed 的 hooks
  "allowManagedHooksOnly": true,

  // 閘門 6：自訂信任訊息
  "pluginTrustMessage": "Only install plugins from YourCompany-approved sources.",

  // 閘門 7：強制啟用/禁用特定 plugin
  "enabledPlugins": {
    "security-checker@company-tools": true,
    "malicious@unknown": false
  }
}
```

#### 5.4 Settings → Plugin 影響流程圖

```
 Plugin 安裝時：
 ──────────────
 strictKnownMarketplaces ──► 白名單檢查（下載前擋住）
 blockedMarketplaces     ──► 黑名單檢查（下載前擋住）
 enabledPlugins[id]=false──► isPluginBlockedByPolicy()

 Plugin 載入時：
 ──────────────
 enabledPlugins ──► 決定啟用/停用（四層 merge）
 strictPluginOnlyCustomization ──► 封鎖非 plugin 的 skills/hooks

 Plugin Skill 執行時：
 ──────────────────────
 allowManagedHooksOnly ──► 只跑 managed hooks
 allowManagedPermissionRulesOnly ──► 只用 managed 權限
 permissions.allow/deny ──► 控制 plugin skill 可用的工具
```

#### 5.5 完整範例：企業環境 + 團隊 + 個人三層設定

```json
// === /etc/claude-code/managed-settings.json（IT 部門部署）===
{
  "strictKnownMarketplaces": [
    { "source": "github", "repo": "acme-corp/claude-plugins" }
  ],
  "enabledPlugins": {
    "security-scanner@acme-corp": true
  },
  "permissions": {
    "deny": ["Bash(curl *)", "Bash(wget *)"]
  },
  "pluginTrustMessage": "Only plugins from acme-corp marketplace are allowed."
}

// === .claude/settings.json（團隊共享，git 追蹤）===
{
  "enabledPlugins": {
    "formatter@acme-corp": true,
    "test-runner@acme-corp": true
  },
  "extraKnownMarketplaces": {
    "acme-corp": {
      "source": { "source": "github", "repo": "acme-corp/claude-plugins" }
    }
  },
  "permissions": {
    "allow": ["Bash(npm test)", "Bash(npm run lint)"]
  },
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write",
      "hooks": [{
        "type": "command",
        "command": "prettier --write ${TOOL_INPUT_file_path}",
        "if": "Write(*.ts)"
      }]
    }]
  }
}

// === .claude/settings.local.json（個人，gitignored）===
{
  "env": {
    "GITHUB_TOKEN": "ghp_xxx"
  },
  "permissions": {
    "allow": ["Bash(gh pr *)"]
  },
  "enabledPlugins": {
    "test-runner@acme-corp": false   // 個人停用（太慢）
  }
}
```

**最終合併結果**：

| 設定項 | 生效值 | 來源 |
|--------|--------|------|
| security-scanner@acme-corp | **啟用** | Policy（強制） |
| formatter@acme-corp | **啟用** | Project |
| test-runner@acme-corp | **停用** | Local 覆蓋 Project |
| permissions.deny | `["Bash(curl *)", "Bash(wget *)"]` | Policy |
| permissions.allow | `["Bash(npm test)", "Bash(npm run lint)", "Bash(gh pr *)"]` | Project + Local（Array 合併） |
| hooks.PostToolUse | prettier hook | Project |
| env.GITHUB_TOKEN | `ghp_xxx` | Local |

### 六、`~/.claude.json` vs `settings.json` 差異

| 面向 | `~/.claude.json` | `settings.json` |
|------|-------------------|-----------------|
| 性質 | 程式狀態檔 | 行為設定檔 |
| Schema | `GlobalConfig` type | `SettingsSchema`（Zod 驗證） |
| 寫入者 | Claude Code 程式自動 | 使用者/管理員手動 |
| 參與 merge | ❌ | ✅ 五源合併 |
| Plugin 相關 | `mcpServers`（舊，建議移到 settings） | `enabledPlugins`、`strictKnownMarketplaces` 等 |
| 快取 | 背景 mtime watcher | Session 快取 |
| 錯誤處理 | `ConfigParseError` + 備份搜尋 | Zod `safeParse` + 靜默丟棄未知 key |

### 七、常見錯誤與排查

> [!faq]- 1. JSON 語法錯誤
> **症狀**：設定沒生效，debug log 有 `Invalid JSON syntax`
> **排查**：`python3 -m json.tool .claude/settings.json`

> [!faq]- 2. 拼錯欄位名（Zod 靜默丟棄）
> **症狀**：設定有內容但不生效
> **原因**：`permission` 而非 `permissions`、`hook` 而非 `hooks`
> **排查**：`claude plugin validate` 或查 debug log

> [!faq]- 3. 權限規則不生效
> **原因**：`allowManagedPermissionRulesOnly: true` 在 managed 中，或 `--setting-sources` 排除了 project
> **排查**：看 effective settings

> [!faq]- 4. Hooks 不觸發
> **原因**：`disableAllHooks: true`、`allowManagedHooksOnly: true`、或 `strictPluginOnlyCustomization: ["hooks"]`

> [!faq]- 5. `~/.claude.json` 損壞
> **原因**：並行 instance 寫入競爭
> **排查**：有備份機制（`findMostRecentBackup`），按提示 `cp` 還原

> [!faq]- 6. Plugin 無法安裝
> **原因**：`strictKnownMarketplaces` 白名單不包含來源，或 `blockedMarketplaces` 擋住
> **排查**：檢查 managed-settings.json

> [!faq]- 7. Plugin 啟用但不生效
> **原因**：`isPluginBlockedByPolicy()` — policy 中 `enabledPlugins[id] === false` 強制禁用，覆蓋所有層
> **排查**：`getSettingsForSource('policySettings')?.enabledPlugins`

### 八、`--setting-sources` 控制載入

```bash
# 只用 user + project
claude --setting-sources user,project

# 全部停用（只剩 policy + flag）
claude --setting-sources ""
```

有效值：`user`、`project`、`local`

> [!warning] policy 和 flag 不能停用
> `getEnabledSettingSources()` 永遠包含 `policySettings` 和 `flagSettings`

## 我的心得（My Takeaways）

1. **`~/.claude.json` 和 `settings.json` 是完全不同的東西**：前者是「程式記住你的偏好」，後者是「你告訴程式該怎麼做」。混淆兩者是最常見的新手錯誤。
2. **企業部署的關鍵是 managed-settings.json**：所有 policy-only 欄位（`strictKnownMarketplaces`、`allowManagedHooksOnly` 等）只在這個檔案中有意義。搭配 `CLAUDE_CODE_PLUGIN_SEED_DIR` 可以做到「開箱即用、鎖死來源」。
3. **Array 合併去重是優點也是陷阱**：`permissions.allow` 在 project 設了 `["Bash(npm *)"]`，local 設了 `["Bash(gh *)"]`，最終是兩者**合併**而非覆蓋。這讓你可以在不同層「追加」權限，但也可能導致意外的寬鬆。
4. **Zod 靜默丟棄未知 key 是雙面刃**：Runtime 不會因為拼錯 key 而崩潰，但也不會告訴你「`permission` 沒生效」。用 `claude plugin validate` 或 debug log 排查。

## 待補充（Open Questions）

- `enabledPlugins` 在 merge 時，boolean `true`/`false` 與 array `["user"]` 的合併行為是什麼？後者覆蓋前者還是也做 array merge？建議搜尋：`settingsMergeCustomizer enabledPlugins boolean array`
- `mcpServers` 同時出現在 `~/.claude.json`（GlobalConfig）和 `settings.json`（SettingsSchema）時，哪個優先？是否有 migration 邏輯？建議搜尋：`mcpServers migration globalConfig settings`
- `cleanupPeriodDays: 0` 是否真的會刪除所有既有 transcript？還是只停止寫入新的？建議搜尋：`cleanupPeriodDays 0 delete transcript`
- 背景 mtime watcher 的輪詢頻率是多少？在 NFS/Docker volume 上是否可靠？建議搜尋：`globalConfigFreshnessWatcher interval polling`
- `--setting-sources ""` 停用所有 user/project/local 後，`enabledPlugins` 完全由 policy 決定嗎？還是 plugin 安裝狀態有另外的持久化？建議搜尋：`installed_plugins.json setting-sources empty`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確立基礎知識 | 四個檔案路徑、`GlobalConfig` vs `SettingsSchema`、五源合併順序、`policySettings` 永遠啟用 |
| **理解（半被動）** | 串聯知識點 | `~/.claude.json` 是「程式的記憶」（OAuth/theme），`settings.json` 是「你給程式的指令」（permissions/hooks）。Plugin 控制分散在 `enabledPlugins`（啟停）和 7 個 policy-only 欄位（安全閘門）。 |
| **分析（主動）** | 找出假設 | 假設「Array merge 去重」不會導致安全問題——但 `permissions.allow` 的合併意味著 local 可以**追加**團隊沒批准的權限。若 managed 沒設 `allowManagedPermissionRulesOnly`，這是一個潛在風險。 |
| **應用（主動）** | 規劃執行方案 | (1) 將團隊共用權限放 `.claude/settings.json` 並 commit；(2) 將 API key 放 `.claude/settings.local.json` 並確認 gitignore；(3) 企業部署用 managed-settings.json 鎖定 marketplace + 強制啟用安全 plugin |
| **評估（主動）** | 判斷方案優劣 | 「全放 user settings」方案：簡單但無法團隊共享。「全放 project settings」方案：可共享但 API key 會洩漏。「三層分離」方案：最安全但學習成本高。建議新團隊用三層分離搭配 extraKnownMarketplaces 預註冊。 |

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — `permissions.allow` 的 Array merge 讓使用者可以在 local 中**追加**團隊沒批准的工具權限。若沒有 `allowManagedPermissionRulesOnly`，這是設計上的安全缺口。
2. **什麼情況下會失敗？** — (a) Zod 靜默丟棄拼錯的 key，使用者以為設了但實際沒生效；(b) 多人同時編輯 `~/.claude.json` 造成損壞；(c) Symlink 斷裂導致 settings 靜默跳過。
3. **有沒有更好的替代方案？** — 對企業來說，`managed-settings.json` + `CLAUDE_CODE_PLUGIN_SEED_DIR` 的組合比讓員工各自設定更安全可控。

## 相關連結（Related）

- [[2026-03-28-CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — 配置層級系統的完整指南，本文補充原始碼級的 merge 邏輯
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — CLAUDE.md 和 Settings 的載入時機比較
- [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] — Plugin 安全機制（命名防護、17 項檢查、企業部署），與本文的 settings 控制互補
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — 原始碼洩漏解析，涵蓋 settings 載入的整體架構
- [[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]] — 團隊統一 settings.json 配置遙測環境變數的實際範例
- [[2026-04-19-CLAUDE-CODE-PLUGIN-JSON-DEPENDENCIES-SHARED-SKILLS-SOURCE-ANALYSIS]] — Settings 層級如何控制 plugin 啟用狀態與 dependency 解析
- [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]] — Settings hooks 設定的底層消費端：24 個事件的 I/O Schema 與 query loop 狀態機如何處理 Hook 回傳值

## References

- Claude Code 反編譯原始碼（基於 v2.1.88 source map 洩漏版本）
- 關鍵檔案：
  - `src/utils/config.ts` — `GlobalConfig` type、`getGlobalConfig()`、`saveGlobalConfig()`
  - `src/utils/settings/settings.ts` — `loadSettingsFromDisk()`、`parseSettingsFile()`、`settingsMergeCustomizer()`
  - `src/utils/settings/types.ts` — `SettingsSchema`（Zod）、所有設定欄位定義
  - `src/utils/settings/constants.ts` — `SETTING_SOURCES`、`getEnabledSettingSources()`
  - `src/utils/env.ts` — `getGlobalClaudeFile()` 路徑解析
  - `src/utils/plugins/pluginPolicy.ts` — `isPluginBlockedByPolicy()`
  - `src/utils/settings/pluginOnlyPolicy.ts` — `isRestrictedToPluginOnly()`、`isSourceAdminTrusted()`
