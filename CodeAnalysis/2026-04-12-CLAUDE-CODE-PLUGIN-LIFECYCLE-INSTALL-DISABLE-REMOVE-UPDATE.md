---
title: "Claude Code Plugin 完整生命週期 — 安裝、停用、移除、更新的檔案影響全解析"
date: 2026-04-12
category: CodeAnalysis
tags:
  - #code-analysis
  - #claude-code
  - #plugin-system
  - #typescript
  - #ai/tools
source: "claude-code decompiled source analysis"
source_type: code
author: "Anthropic (decompiled)"
status: notes
links:
  - "[[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]]"
  - "[[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]]"
  - "[[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]]"
github_stars: N/A
github_language: TypeScript
---

## 摘要（Summary）

深度分析 Claude Code Plugin 系統的完整生命週期：安裝（Install）、使用（Runtime）、停用（Disable）、移除（Uninstall）、更新（Update）五大操作，逐一追蹤每個操作會觸碰哪些檔案、修改什麼內容。特別聚焦於 Plugin 內含的 Skills、Commands、Hooks 三類元件在各階段的行為差異。核心發現：Plugin 實體永遠快取在 `~/.claude/plugins/cache/`，三種安裝 Scope（user / project / local）只影響 `enabledPlugins` 寫入哪個 settings 檔；移除後快取不會立即刪除，而是標記 `.orphaned_at` 等待 7 天後背景清理。

## Why — 為什麼要研究這個？

> Claude Code 的 Plugin 系統是其擴充能力的核心，但官方文件只說明「怎麼裝」，沒有解釋安裝後檔案系統層面到底發生了什麼。

- **核心動機**：理解 Plugin 安裝、停用、移除、更新各階段的檔案層級影響，避免殘留檔案或意外覆蓋
- **常見誤解**：很多人以為 Plugin 的 Skills 會裝到 `~/.claude/skills/`，Commands 會裝到 `~/.claude/commands/`——實際上完全不會
- **目標用戶**：需要管理多個 Plugin、跨專案協作、或自行開發 Plugin 的進階使用者

## What — 是什麼？

### Plugin 系統的五種元件

Plugin 是一個容器，可包含以下五種元件：

| 元件 | 目錄 | 檔案格式 | 用途 |
|------|------|---------|------|
| Commands | `commands/` | `*.md` | 使用者可透過 `/command` 觸發的指令 |
| Skills | `skills/` | `SKILL.md` | 系統 prompt 匹配後自動觸發的能力 |
| Agents | `agents/` | `*.md` | Agent tool 可載入的代理人定義 |
| Hooks | `hooks/` | `hooks.json` | 事件驅動的回呼函式（PreToolUse、PostToolUse 等） |
| Output Styles | `output-styles/` | 樣式檔 | 自訂輸出渲染方式 |

### 三種安裝 Scope

| Scope | Settings 檔位置 | 共享範圍 | Git 追蹤 |
|-------|----------------|---------|---------|
| **user** | `~/.claude/settings.json` | 你所有專案都生效 | 否 |
| **project** | `$PROJECT/.claude/settings.json` | 團隊所有人（同 repo） | **是** |
| **local** | `$PROJECT/.claude/settings.local.json` | 只有你、只有這個 repo | 否（自動 gitignore） |

### 技術棧（Tech Stack）

- 語言：TypeScript（ESM + TSX）
- 執行環境（Runtime）：Bun
- 框架：Commander.js（CLI）、React/Ink（TUI）
- 儲存：JSON 檔案（settings、installed_plugins）、Keychain（secrets）

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌──────────────────────────────────────────────────────────────┐
│                    使用者操作層                                │
│  /plugin install  │  /plugin disable  │  /plugin uninstall   │
└────────┬──────────┴────────┬──────────┴────────┬─────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────┐
│              pluginOperations.ts — 操作路由                    │
│  installPluginOp()  setPluginEnabledOp()  uninstallPluginOp()│
└────────┬──────────┬────────┬──────────┬────────┬─────────────┘
         │          │        │          │        │
         ▼          │        ▼          │        ▼
┌────────────────┐  │  ┌──────────┐    │  ┌───────────────────┐
│ installResolved│  │  │ settings │    │  │ removeInstallation│
│ Plugin()       │  │  │ .json    │    │  │ + markOrphaned()  │
│                │  │  │ 更新     │    │  │                   │
└───────┬────────┘  │  └──────────┘    │  └────────┬──────────┘
        │           │                  │           │
        ▼           ▼                  ▼           ▼
┌──────────────────────────────────────────────────────────────┐
│                    檔案系統層                                  │
│                                                              │
│  ~/.claude/settings.json ←──────── enabledPlugins 啟用紀錄    │
│  $PROJ/.claude/settings.json ←──── project scope             │
│  $PROJ/.claude/settings.local.json ← local scope            │
│                                                              │
│  ~/.claude/plugins/                                          │
│  ├── installed_plugins.json ←────── 安裝 metadata（V2）      │
│  ├── cache/{mkt}/{name}/{ver}/ ←─── Plugin 實體快取          │
│  │   ├── .claude-plugin/plugin.json  Manifest                │
│  │   ├── commands/**/*.md            指令                     │
│  │   ├── skills/**/SKILL.md          Skill                   │
│  │   ├── agents/**/*.md              Agent                   │
│  │   ├── hooks/hooks.json            Hook 設定               │
│  │   └── .orphaned_at               孤兒標記                  │
│  └── data/{plugin-id}/              持久資料                   │
└──────────────────────────────────────────────────────────────┘
```

### 檔案地圖標記說明

```
HOME (~/.claude/)
├── settings.json                          ← [A] User scope 啟用紀錄
├── plugins/
│   ├── installed_plugins.json             ← [B] 安裝 metadata (V2)
│   ├── cache/{marketplace}/{plugin}/{ver}/ ← [C] Plugin 實體快取
│   │   ├── .claude-plugin/plugin.json     ←     Manifest
│   │   ├── commands/**/*.md               ←     指令定義
│   │   ├── skills/**/SKILL.md             ←     Skill 定義
│   │   ├── agents/**/*.md                 ←     Agent 定義
│   │   ├── hooks/hooks.json               ←     Hook 定義
│   │   ├── output-styles/                 ←     輸出樣式
│   │   └── .orphaned_at                   ← [D] 孤兒標記（移除/更新後出現）
│   └── data/{plugin-id}/                  ← [E] Plugin 持久資料目錄
│
├── skills/                                ← ✗ Plugin 安裝不會碰
└── commands/                              ← ✗ Plugin 安裝不會碰

PROJECT ($PROJECT/)
├── .claude/
│   ├── settings.json                      ← [F] Project scope 啟用紀錄
│   └── settings.local.json                ← [G] Local scope 啟用紀錄
└── .gitignore                             ← [H] Local scope 安裝時追加

系統 Keychain                               ← [I] Plugin secrets
記憶體 STATE.registeredHooks                 ← [J] 執行期 Hook 註冊表
記憶體 Memoize Cache                         ← [K] commands/skills/agents/hooks 快取
```

> [!important] 關鍵澄清
> `~/.claude/skills/` 和 `~/.claude/commands/` 是給使用者**手寫**自訂 skill / command 的目錄，跟 Plugin 安裝是**完全獨立**的兩套系統。Plugin 的所有元件（skills、commands、hooks、agents）統一存放在 `~/.claude/plugins/cache/` 下。

---

## 安裝流程（Installation Flow）

### 安裝時序圖

```
使用者        pluginOperations      pluginInstallationHelpers       檔案系統
  │                │                         │                        │
  │──install───────►│                         │                        │
  │                │──installResolvedPlugin()─►│                        │
  │                │                         │                        │
  │                │    1. Policy 檢查        │                        │
  │                │    2. 解析依賴閉包        │                        │
  │                │                         │                        │
  │                │                         │──enabledPlugins=true───►│ settings.json
  │                │                         │                        │   [A/F/G]
  │                │                         │                        │
  │                │                         │──cacheAndRegisterPlugin─►│
  │                │                         │  ├─下載/複製 plugin     │ cache/ [C]
  │                │                         │  ├─calculateVersion     │
  │                │                         │  └─addInstalledPlugin   │ installed_plugins.json [B]
  │                │                         │                        │
  │                │                         │──createPluginFromPath───►│ 自動發現元件：
  │                │                         │  ├─commands/*.md        │
  │                │                         │  ├─skills/SKILL.md      │
  │                │                         │  ├─agents/*.md          │
  │                │                         │  └─hooks/hooks.json     │
  │                │                         │                        │
  │                │                         │──clearAllCaches()       │ [K] 記憶體清除
  │                │                         │                        │
  │                │     (local scope 額外)   │                        │
  │                │                         │──addToGitignore()──────►│ .gitignore [H]
  │                │                         │                        │
  │◄──安裝完成─────│                         │                        │
```

### 安裝產物清單

| 路徑 | 類型 | 用途 | 觸發條件 |
|------|------|------|---------|
| `~/.claude/settings.json` | 檔案 | 寫入 `enabledPlugins[id]=true` | user scope |
| `$PROJECT/.claude/settings.json` | 檔案 | 寫入 `enabledPlugins[id]=true` | project scope |
| `$PROJECT/.claude/settings.local.json` | 檔案 | 寫入 `enabledPlugins[id]=true` | local scope |
| `$PROJECT/.gitignore` | 檔案 | 追加 `.claude/settings.local.json` | local scope |
| `~/.claude/plugins/cache/{mkt}/{name}/{ver}/` | 目錄 | Plugin 完整程式碼 | 全部 |
| `~/.claude/plugins/installed_plugins.json` | 檔案 | 安裝 metadata | 全部 |

### 元件自動發現（Component Discovery）

安裝完成後，`createPluginFromPath()` 會用 `Promise.all` 並行偵測五個目錄是否存在：

```typescript
// pluginLoader.ts:1373-1391
const [commandsDirExists, agentsDirExists, skillsDirExists, outputStylesDirExists] =
  await Promise.all([
    !manifest.commands ? pathExists(join(pluginPath, 'commands')) : false,
    !manifest.agents ? pathExists(join(pluginPath, 'agents')) : false,
    !manifest.skills ? pathExists(join(pluginPath, 'skills')) : false,
    !manifest.outputStyles ? pathExists(join(pluginPath, 'output-styles')) : false,
  ])
```

若目錄存在，自動設定對應的 `plugin.commandsPath`、`plugin.skillsPath` 等。若 `plugin.json` manifest 已宣告路徑，則以 manifest 為準。

---

## 使用流程（Runtime Loading）

### 啟動載入時序圖

```
Session 啟動     main.tsx          pluginLoader       loadPluginCommands    STATE
    │               │                  │                     │                │
    │──啟動─────────►│                  │                     │                │
    │               │──initVersioned──►│                     │                │
    │               │──cleanupOrphan──►│ (背景)              │                │
    │               │                  │                     │                │
    │               │──loadAllPlugins──►│                     │                │
    │               │                  │──讀 settings ───────────────────────►│
    │               │                  │  合併 [A]+[F]+[G]+managed           │
    │               │                  │──讀 installed_plugins.json [B]      │
    │               │                  │                     │                │
    │               │                  │──createPluginFromPath()             │
    │               │                  │  (對每個 enabled plugin)             │
    │               │                  │                     │                │
    │               │                  │──getPluginCommands()─►│              │
    │               │                  │──getPluginSkills()───►│              │
    │               │                  │──loadPluginAgents()──►│              │
    │               │                  │──loadPluginHooks()───►│──register──►│ [J]
    │               │                  │                     │                │
    │               │                  │──memoize 快取────────────────────────►│ [K]
    │               │                  │                     │                │
    │◄──就緒─────────│                  │                     │                │
```

### 元件載入函式對照

| 元件 | 載入函式 | 檔案 | 行號 | 發現方式 |
|------|---------|------|------|---------|
| Commands | `getPluginCommands()` | `loadPluginCommands.ts` | 414-677 | `commands/**/*.md` 遞迴掃描 |
| Skills | `getPluginSkills()` | `loadPluginCommands.ts` | 840-942 | `skills/**/SKILL.md` |
| Agents | `loadPluginAgents()` | `loadPluginAgents.ts` | 231+ | `agents/**/*.md` 遞迴掃描 |
| Hooks | `loadPluginHooks()` | `loadPluginHooks.ts` | 91-157 | `hooks/hooks.json` |
| Output Styles | 內建載入 | `pluginLoader.ts` | 1585-1611 | `output-styles/` 目錄偵測 |

> [!note] 所有載入函式都有 Memoize
> 每個 `get*()` / `load*()` 函式都被 memoize 包裝，第一次呼叫後快取在記憶體中。只有 `clearAllCaches()` 才能清除，強制重新載入。

---

## 停用流程（Disable）

### 停用時序圖

```
使用者         pluginOperations         settings.json         STATE
  │                │                        │                   │
  │──disable───────►│                        │                   │
  │                │──findPluginInSettings()  │                   │
  │                │                        │                   │
  │                │──updateSettingsForSource()                  │
  │                │  enabledPlugins[id] = false                 │
  │                │────────────────────────►│ [A/F/G]          │
  │                │                        │                   │
  │                │──clearAllCaches()───────────────────────────►│ [K] 清除
  │                │──pruneRemovedPluginHooks()──────────────────►│ [J] 清除
  │                │                        │                   │
  │◄──停用完成──────│                        │                   │
  │                │                        │                   │
  │  ⚠️ 不刪除任何檔案                       │                   │
  │  快取 [C] 保留、installed_plugins [B] 不變│                   │
```

> [!warning] 停用 vs 移除的差異
> 停用只改 **1 個 settings 檔**（`true` → `false`），快取和安裝紀錄完全保留，隨時可重新啟用。移除則會刪除 settings key、安裝紀錄、並標記快取為孤兒。

---

## 移除流程（Uninstall）

### 移除時序圖

```
使用者        pluginOperations      installedPluginsManager    cacheUtils       檔案系統
  │                │                         │                    │                │
  │──uninstall─────►│                         │                    │                │
  │                │                         │                    │                │
  │                │──updateSettingsForSource()                                    │
  │                │  enabledPlugins[id] = undefined (刪除 key)                    │
  │                │─────────────────────────────────────────────────────────────►│ [A/F/G]
  │                │                         │                    │                │
  │                │──clearAllCaches()────────────────────────────────────────────►│ [K]
  │                │                         │                    │                │
  │                │──removePluginInstallation()                                  │
  │                │────────────────────────►│                    │                │
  │                │                         │──移除 scope entry──────────────────►│ [B]
  │                │                         │                    │                │
  │                │──(是最後一個 scope？)     │                    │                │
  │                │                         │                    │                │
  │                │──markPluginVersionOrphaned()──────────────────►│               │
  │                │                         │                    │──.orphaned_at──►│ [D]
  │                │                         │                    │                │
  │                │──deletePluginOptions()───────────────────────────────────────►│ pluginConfigs
  │                │──(清除 Keychain)──────────────────────────────────────────────►│ [I]
  │                │                         │                    │                │
  │                │──(deleteDataDir?)────────────────────────────────────────────►│ [E] 可選刪除
  │                │                         │                    │                │
  │◄──移除完成──────│                         │                    │                │
  │                │                         │                    │                │
  │   ···7 天後···  │                         │                    │                │
  │                │                         │                    │                │
  │                │  cleanupOrphanedPluginVersionsInBackground() │                │
  │                │─────────────────────────────────────────────►│                │
  │                │                         │                    │──刪除快取──────►│ [C]
```

### 移除的檔案影響清單

| 時間點 | 檔案 | 動作 | 程式碼出處 |
|--------|------|------|-----------|
| 立即 | Settings [A]/[F]/[G] | 刪除 `enabledPlugins[id]` key | `pluginOperations.ts:509-514` |
| 立即 | `installed_plugins.json` [B] | 移除該 scope 的 entry | `pluginOperations.ts:520` |
| 最後 scope | `.orphaned_at` [D] | 建立孤兒標記 | `cacheUtils.ts:56-63` |
| 最後 scope | Keychain [I] | 清除 plugin secrets | `pluginOperations.ts:538` |
| 最後 scope | `settings.pluginConfigs` | 清除 plugin 選項 | `pluginOperations.ts:538` |
| 可選 | `plugins/data/{id}/` [E] | 刪除持久資料 | `pluginOperations.ts:539-541` |
| **7 天後** | `plugins/cache/{mkt}/{name}/{ver}/` [C] | 背景刪除整個快取 | `cacheUtils.ts:74-116` |

> [!important] 7 天延遲清理設計
> 移除後快取**不會立即刪除**。`cacheUtils.ts:24` 定義 `CLEANUP_AGE_MS = 7 * 24 * 60 * 60 * 1000`（7 天）。每次 session 啟動時 `cleanupOrphanedPluginVersionsInBackground()` 會檢查所有 `.orphaned_at` 標記，超過 7 天才刪除。這設計是為了防止誤刪後無法復原。

---

## 更新流程（Update）

### 更新時序圖

```
使用者        pluginOperations       pluginLoader       cacheUtils        檔案系統
  │                │                     │                  │                │
  │──update────────►│                     │                  │                │
  │                │──讀取舊版本───────────────────────────────────────────────►│ [B]
  │                │                     │                  │                │
  │                │──cachePlugin()──────►│                  │                │
  │                │  (下載/複製新版本)    │                  │                │
  │                │                     │                  │                │
  │                │──calculateVersion()──►│                  │                │
  │                │                     │                  │                │
  │                │  版本相同？ ──是──► 已是最新版             │                │
  │                │      │否                                │                │
  │                │      ▼                                  │                │
  │                │──copyToVersionedCache()─────────────────────────────────►│ [C] 新版
  │                │                     │                  │                │
  │                │──updateInstallationPathOnDisk()─────────────────────────►│ [B] 更新
  │                │  (installPath → 新路徑, version → 新版本)                │
  │                │                     │                  │                │
  │                │──markPluginVersionOrphaned(舊路徑)──────►│               │
  │                │                     │                  │──.orphaned_at─►│ [D] 舊版
  │                │                     │                  │                │
  │◄──更新完成──────│                     │                  │                │
  │  ⚠️ 需重啟 Session 才生效              │                  │                │
  │                │                     │                  │                │
  │  ···7 天後···   │                     │                  │                │
  │                │  cleanupBackground()─────────────────►│                │
  │                │                     │                  │──刪除舊快取────►│ [C] 舊版
```

> [!note] 更新不改 Settings
> 更新操作**不會**修改任何 settings 檔（[A]/[F]/[G]），因為 `enabledPlugins` 的值不變。只有 `installed_plugins.json` 會更新 `installPath`、`version`、`lastUpdated` 欄位。

---

## 完整檔案影響矩陣

| 檔案 | 安裝 | 使用 | 停用 | 啟用 | 移除 | 更新 |
|------|:----:|:----:|:----:|:----:|:----:|:----:|
| **[A]** `~/.claude/settings.json` | ✏️ `=true` | 👁️ 讀 | ✏️ `=false` | ✏️ `=true` | 🗑️ 刪 key | — |
| **[F]** `$PROJ/.claude/settings.json` | ✏️ `=true` | 👁️ 讀 | ✏️ `=false` | ✏️ `=true` | 🗑️ 刪 key | — |
| **[G]** `$PROJ/.claude/settings.local.json` | ✏️ `=true` | 👁️ 讀 | ✏️ `=false` | ✏️ `=true` | 🗑️ 刪 key | — |
| **[H]** `$PROJ/.gitignore` | ✏️ 追加 | — | — | — | — | — |
| **[B]** `installed_plugins.json` | ✏️ 新增 | 👁️ 讀 | — | — | 🗑️ 移除 | ✏️ 更新 |
| **[C]** Plugin 快取目錄 | 🆕 建立 | 👁️ 讀 | — | — | ⏰ 7天後刪 | 🆕 新版 + ⏰ 舊版 |
| **[D]** `.orphaned_at` 標記 | — | — | — | — | 🆕 建立 | 🆕 建立(舊版) |
| **[E]** Plugin data 目錄 | — | 讀寫 | — | — | 🗑️ 可選刪 | — |
| **[I]** Keychain secrets | — | 👁️ 讀 | — | — | 🗑️ 清除 | — |
| **[J]** 記憶體 Hook 註冊 | 🆕 註冊 | 🔄 觸發 | 🗑️ 清除 | 🆕 註冊 | 🗑️ 清除 | ⏰ 重啟後 |
| **[K]** 記憶體 Memoize | 🗑️ 清除 | 🆕 建立 | 🗑️ 清除 | 🗑️ 清除 | 🗑️ 清除 | — |

圖例：✏️ 修改 | 🆕 建立 | 🗑️ 刪除 | 👁️ 讀取 | 🔄 使用 | ⏰ 延遲 | — 不動

---

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組鏈 |
|---|---------|---------|---------|-----------|
| 1 | 安裝 Plugin (user) | `/plugin install --scope user` | `pluginOperations.ts:321` | `installPluginOp → installResolvedPlugin → cacheAndRegisterPlugin → addInstalledPlugin` |
| 2 | 安裝 Plugin (project) | `/plugin install --scope project` | `pluginOperations.ts:321` | 同上，settings 寫入位置不同 |
| 3 | 安裝 Plugin (local) | `/plugin install --scope local` | `pluginOperations.ts:321` | 同上 + `addFileGlobRuleToGitignore` |
| 4 | 停用 Plugin | `/plugin disable` | `pluginOperations.ts:771` | `setPluginEnabledOp → updateSettingsForSource → clearAllCaches` |
| 5 | 移除 Plugin | `/plugin uninstall` | `pluginOperations.ts:428` | `uninstallPluginOp → removePluginInstallation → markOrphaned → deletePluginOptions` |
| 6 | 更新 Plugin | `/plugin update` | `pluginOperations.ts:830` | `performPluginUpdate → cachePlugin → copyToVersionedCache → updateInstallationPathOnDisk` |
| 7 | 使用 Plugin Command | `/plugin-name:command` | `loadPluginCommands.ts:414` | `getPluginCommands → loadAllPluginsCacheOnly → createPluginFromPath → loadCommandsFromDirectory` |
| 8 | Plugin Skill 觸發 | 系統 prompt 匹配 | `loadPluginCommands.ts:840` | `getPluginSkills → loadSkillsFromDirectory → SKILL.md 解析` |
| 9 | Plugin Hook 執行 | 事件觸發（如 PreToolUse） | `loadPluginHooks.ts:91` | `loadPluginHooks → convertPluginHooksToMatchers → registerHookCallbacks` |

### 案例詳解

#### 案例 1：安裝 Plugin（User Scope）

```
使用者：/plugin install my-plugin --scope user
  │
  ▼
pluginOperations.ts:installPluginOp()
  │── 驗證 scope
  │── 查找 marketplace entry
  │
  ▼
pluginInstallationHelpers.ts:installResolvedPlugin()
  │── scopeToSettingSource('user') → 'userSettings'
  │── isPluginBlockedByPolicy() 檢查
  │── resolveDependencyClosure() 解析依賴
  │
  ├── updateSettingsForSource('userSettings', {enabledPlugins: {id: true}})
  │   └── 寫入 ──► ~/.claude/settings.json
  │
  ├── cacheAndRegisterPlugin()
  │   ├── cachePlugin() ──► 下載到 ~/.claude/plugins/cache/{mkt}/{name}/{ver}/
  │   ├── createPluginFromPath() ──► 自動發現 commands/skills/agents/hooks
  │   └── addInstalledPlugin() ──► 寫入 installed_plugins.json
  │
  └── clearAllCaches() ──► 清除記憶體 memoize
```

#### 案例 5：移除 Plugin

```
使用者：/plugin uninstall my-plugin --scope user
  │
  ▼
pluginOperations.ts:uninstallPluginOp()
  │── resolveDelistedPluginId() 解析 pluginId
  │── loadInstalledPluginsV2() 確認已安裝
  │
  ├── updateSettingsForSource() ──► settings.json: 刪除 enabledPlugins[id]
  ├── clearAllCaches() ──► 記憶體清除
  ├── removePluginInstallation() ──► installed_plugins.json: 移除 entry
  │
  ├── (是最後 scope？)
  │   ├── markPluginVersionOrphaned() ──► 寫入 .orphaned_at
  │   ├── deletePluginOptions() ──► 清除 pluginConfigs + Keychain
  │   └── deletePluginDataDir() ──► (可選) 刪除 data 目錄
  │
  └── findReverseDependents() ──► 警告反向依賴
```

---

## 三種 Scope 安裝差異完整比較

```
┌────────────────────────────────────────────────────────────────┐
│                     User Scope                                 │
│  Settings: ~/.claude/settings.json                             │
│  作用範圍：你所有的專案                                          │
│  Git 追蹤：否                                                  │
│  額外動作：無                                                   │
├────────────────────────────────────────────────────────────────┤
│                     Project Scope                              │
│  Settings: $PROJECT/.claude/settings.json                      │
│  作用範圍：本專案所有協作者                                      │
│  Git 追蹤：是（會 commit、push、讓團隊自動取得）                  │
│  額外動作：無                                                   │
├────────────────────────────────────────────────────────────────┤
│                     Local Scope                                │
│  Settings: $PROJECT/.claude/settings.local.json                │
│  作用範圍：只有你、只有這個 repo、只有這台電腦                    │
│  Git 追蹤：否（自動加入 .gitignore）                             │
│  額外動作：addFileGlobRuleToGitignore() (settings.ts:508-512)  │
├────────────────────────────────────────────────────────────────┤
│                 三者共用（不分 Scope）                           │
│  Plugin 快取：~/.claude/plugins/cache/{mkt}/{name}/{ver}/       │
│  安裝紀錄：~/.claude/plugins/installed_plugins.json             │
│  記憶體：clearAllCaches() 清除 memoize                          │
└────────────────────────────────────────────────────────────────┘
```

---

## 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> Plugin 系統採用「設定與實體分離」模式：Settings 檔控制啟用狀態，快取目錄存放程式碼實體，兩者透過 `installed_plugins.json` 連結。

1. **Plugin 實體統一快取** — 不管 scope，程式碼都快取在 `~/.claude/plugins/cache/`。避免 project scope 把大型 plugin 程式碼放進 git repo。
2. **延遲清理（7 天）** — 移除後不立即刪除快取，而是寫 `.orphaned_at` 標記。防止誤操作無法復原，也避免重新安裝時需要重新下載。
3. **停用保留全部狀態** — 停用只改 settings 的 boolean 值，不動快取和紀錄。讓「暫時停用試試」的使用者體驗最順暢。
4. **Scope 優先級合併** — `managed > local > project > user`，企業 policy 可覆蓋所有層級。
5. **元件自動發現** — 安裝時用目錄探測（`pathExists`）自動發現 commands/skills/agents/hooks，降低 plugin 作者的設定負擔。`plugin.json` manifest 可覆蓋自動發現結果。
6. **Memoize + 原子清除** — 所有元件載入函式都有 memoize，只在 install/disable/uninstall 時統一清除，避免每次 API 呼叫都重新掃描磁碟。

---

## 關鍵程式碼（Key Code Snippets）

### 安裝核心：寫入 Settings + 快取

```typescript
// pluginInstallationHelpers.ts:429-473

// ── ACTION: write entire closure to settings in one call ──
const closureEnabled: Record<string, true> = {}
for (const id of resolution.closure) closureEnabled[id] = true
const { error } = updateSettingsForSource(settingSource, {
  enabledPlugins: {
    ...getSettingsForSource(settingSource)?.enabledPlugins,
    ...closureEnabled,
  },
})

// ── Materialize: cache each closure member ──
const projectPath = scope !== 'user' ? getCwd() : undefined
for (const id of resolution.closure) {
  let info = depInfo.get(id)
  if (!info) continue
  await cacheAndRegisterPlugin(id, info.entry, scope, projectPath, localSourcePath)
}
```

### 移除核心：刪 key + 標記孤兒

```typescript
// pluginOperations.ts:507-528

// Remove the plugin from the appropriate settings file (delete key entirely)
const newEnabledPlugins: Record<string, boolean | string[] | undefined> = {
  ...settings?.enabledPlugins,
}
newEnabledPlugins[pluginId] = undefined  // undefined = 刪除 key
updateSettingsForSource(settingSource, { enabledPlugins: newEnabledPlugins })

clearAllCaches()
removePluginInstallation(pluginId, scope, projectPath)

const isLastScope = !remainingInstallations || remainingInstallations.length === 0
if (isLastScope && installPath) {
  await markPluginVersionOrphaned(installPath)
}
if (isLastScope) {
  deletePluginOptions(pluginId)
  if (deleteDataDir) {
    await deletePluginDataDir(pluginId)
  }
}
```

### 快取路徑計算

```typescript
// pluginDirectories.ts:53-62
export function getPluginsDirectory(): string {
  const envOverride = process.env.CLAUDE_CODE_PLUGIN_CACHE_DIR
  if (envOverride) {
    return expandTilde(envOverride)
  }
  return join(getClaudeConfigHomeDir(), getPluginsDirectoryName())
}

// pluginLoader.ts:172-176
export function getVersionedCachePath(pluginId: string, version: string): string {
  return getVersionedCachePathIn(getPluginsDirectory(), pluginId, version)
}
```

### Settings 路徑決定

```typescript
// settings.ts:239-307
export function getSettingsRootPathForSource(source: SettingSource): string {
  switch (source) {
    case 'userSettings':
      return resolve(getClaudeConfigHomeDir())        // ~/.claude/
    case 'projectSettings':
    case 'localSettings':
      return resolve(getOriginalCwd())                // $PROJECT/
  }
}

export function getRelativeSettingsFilePathForSource(source): string {
  switch (source) {
    case 'projectSettings':
      return join('.claude', 'settings.json')         // .claude/settings.json
    case 'localSettings':
      return join('.claude', 'settings.local.json')   // .claude/settings.local.json
  }
}
```

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐ | 設定與實體分離、各操作有獨立函式、錯誤路徑清晰 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐⭐ | 新元件類型只需加一個目錄探測 + 載入函式，不動現有邏輯 |
| 安全性（Safety） | ⭐⭐⭐⭐⭐ | Policy 封鎖、7 天延遲清理、scope 隔離，多層防護 |
| 可逆性（Reversibility） | ⭐⭐⭐⭐⭐ | 停用/移除都保留快取，7 天內可復原 |
| 多租戶支援（Multi-tenancy） | ⭐⭐⭐⭐ | user/project/local 三層 scope + managed policy 覆蓋 |

> [!tip] 值得學習的設計
> 「設定與實體分離」+ 「延遲清理」的組合非常優雅。Settings 只存 boolean flag，實體統一快取。移除時先標記、7 天後才刪，兼顧了磁碟空間管理和操作安全。這個模式可以應用到任何需要「安裝/移除」語意的系統。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> 以下是架構層面的潛在問題。

- **快取膨脹**：每次更新都保留舊版 7 天，高頻更新的 plugin 可能累積大量快取。沒有全域大小限制。
- **V1/V2 雙寫**：`addInstalledPlugin()` 同時寫 V1 和 V2 格式，增加了不一致風險和維護成本。
- **更新需重啟**：更新後的元件（特別是 hooks）要等下次 session 才會載入新版，沒有熱重載機制。
- **跨 scope 依賴不明確**：Plugin A 在 user scope、Plugin B 在 project scope 且依賴 A，移除 A 只會「警告」不會「阻止」。

### 🔮 改進建議（Improvement Suggestions）
1. 加入快取大小上限或 LRU 策略，自動清理最舊的孤兒版本
2. 新增 `--hot-reload` 選項，允許更新後立即載入新版元件
3. 統一 V1/V2 格式，去除雙寫邏輯

---

## 效能基準（Benchmark）

| 場景 | 特性 |
|------|------|
| 安裝（有依賴） | 依賴解析 + 下載為串列，多個 plugin 逐一快取 |
| 啟動載入 | `loadAllPluginsCacheOnly()` 使用快取，不觸發網路 I/O |
| 元件發現 | 5 個目錄偵測用 `Promise.all` 並行 |
| 停用/啟用 | 只改 1 個 JSON key + 清快取，毫秒級 |
| 孤兒清理 | 背景非同步，不阻塞主流程 |

---

## 快速上手（Quick Start）

```bash
# 安裝到 user scope（所有專案生效）
claude /plugin install my-plugin@marketplace --scope user

# 安裝到 project scope（團隊共享）
claude /plugin install my-plugin@marketplace --scope project

# 安裝到 local scope（只有你、只有這個 repo）
claude /plugin install my-plugin@marketplace --scope local

# 停用
claude /plugin disable my-plugin

# 重新啟用
claude /plugin enable my-plugin

# 更新
claude /plugin update my-plugin

# 移除
claude /plugin uninstall my-plugin --scope user
```

---

## 程式碼出處索引

| 功能 | 檔案 | 行號 | 函式 |
|------|------|------|------|
| 安裝核心 | `pluginInstallationHelpers.ts` | 348-481 | `installResolvedPlugin()` |
| 快取寫入 | `pluginInstallationHelpers.ts` | 128-226 | `cacheAndRegisterPlugin()` |
| 元件發現 | `pluginLoader.ts` | 1348-2006 | `createPluginFromPath()` |
| 載入 Commands | `loadPluginCommands.ts` | 414-677 | `getPluginCommands()` |
| 載入 Skills | `loadPluginCommands.ts` | 840-942 | `getPluginSkills()` |
| 載入 Agents | `loadPluginAgents.ts` | 231+ | `loadPluginAgents()` |
| 載入 Hooks | `loadPluginHooks.ts` | 91-157 | `loadPluginHooks()` |
| 停用/啟用 | `pluginOperations.ts` | 574-748 | `setPluginEnabledOp()` |
| 移除 | `pluginOperations.ts` | 428-559 | `uninstallPluginOp()` |
| 更新 | `pluginOperations.ts` | 897-1089 | `performPluginUpdate()` |
| 孤兒清理 | `cacheUtils.ts` | 56-116 | `cleanupOrphanedPluginVersionsInBackground()` |
| Settings 路徑 | `settings.ts` | 239-307 | `getSettingsRootPathForSource()` |
| Plugin 目錄 | `pluginDirectories.ts` | 53-62 | `getPluginsDirectory()` |
| 安裝紀錄寫入 | `installedPluginsManager.ts` | 874-912 | `addInstalledPlugin()` |

---

## 我的心得（My Takeaways）

1. **設定與實體分離**是 Plugin 系統最核心的設計。Settings 只存「這個 plugin 是否啟用」的 boolean，不存路徑、不存版本。路徑和版本由 `installed_plugins.json` 管理，實體由快取目錄管理。三者各司其職。

2. **延遲清理**模式值得借鏡。不立即刪除、而是標記後等待期滿再清理，是一種「軟刪除」思路。適用於所有使用者可能後悔的破壞性操作。

3. **Scope 系統**設計得很巧妙。User/Project/Local 三層加上 Managed policy 覆蓋，既支援個人偏好、團隊共享、又不失企業管控。特別是 local scope 自動加 `.gitignore` 的小細節，避免了使用者忘記排除。

4. **`~/.claude/skills/` 不會被 Plugin 碰到**——這個事實消除了我的一個重大誤解。手寫的 skill 和 plugin 安裝的 skill 是完全獨立的命名空間。

---

## 待補充（Open Questions）

- Plugin 之間的依賴衝突（dependency conflict）如何解決？`resolveDependencyClosure()` 是否有版本約束語法（如 semver range）？建議搜尋：`resolveDependencyClosure version conflict`
- 同一個 plugin 在不同 scope 安裝不同版本時，哪個版本的元件會被載入？Settings 優先級（managed > local > project > user）是否同時決定了元件載入優先級？建議搜尋：`mergePluginSources scope priority`
- `installed_plugins.json` 的 V1 → V2 遷移邏輯是否完全穩定？是否有邊界情況（如遷移中途 crash）導致資料不一致？建議搜尋：`migrateV1ToV2 error handling`
- ZIP 快取模式（`isPluginZipCacheEnabled()`）在什麼環境下會啟用？對啟動速度有多大影響？建議搜尋：`CLAUDE_CODE_PLUGIN_ZIP_CACHE`
- Plugin 的 hooks 是否能 override 使用者在 `settings.json` 中手寫的 hooks？如果衝突，誰的優先級更高？建議搜尋：`mergeHooks plugin user priority`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | 1. Plugin 快取在 `~/.claude/plugins/cache/` 2. 三種 scope：user/project/local 3. 移除後 7 天延遲清理 4. `installed_plugins.json` 是 V2 格式 5. `~/.claude/skills/` 不受 plugin 影響 |
| **理解（半被動）** | 解釋概念的含義及關聯 | Plugin 系統採「設定與實體分離」模式：Settings 控制「是否啟用」，快取存放「程式碼」，`installed_plugins.json` 連結兩者。三種 scope 的差異只在於 settings 寫入位置，快取位置完全相同。停用、移除、更新是三種不同程度的「關閉」操作：停用只改 boolean、移除刪 key + 標記孤兒、更新則是新建 + 標記舊版孤兒。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設 | 關鍵假設：使用者不會在 7 天內需要復原已刪除的 plugin（否則 .orphaned_at 機制無用）。設計隱含的取捨：快取統一在 home 目錄意味著多專案共享 plugin 程式碼（節省磁碟），但也意味著 project scope 的「團隊共享」只共享 settings flag，不共享程式碼——每個團隊成員的機器上都要各自快取一份。 |
| **應用（主動）** | 將知識套用情境 | 1. 開發自訂 plugin 時，只需在根目錄放 `commands/`、`skills/`、`hooks/hooks.json` 等目錄，無需手寫 manifest（自動發現） 2. 團隊共享 plugin 時，用 project scope 安裝，settings.json 會進 git，其他成員 clone 後自動取得相同的 plugin 設定 3. 除錯時可直接檢查 `~/.claude/plugins/installed_plugins.json` 確認安裝狀態 |
| **評估（主動）** | 判斷多個方案的優劣 | 「設定與實體分離」vs「all-in-one 安裝」：分離模式的優點是 settings 檔小（只有 boolean）、git diff 乾淨、團隊不需傳輸大型 plugin 程式碼；缺點是每台機器要各自下載快取、離線環境無法自動安裝。與 VS Code extension 的「同步設定即同步擴充」模式相比，Claude Code 更偏向「聲明式」——只聲明意圖，不保證全自動部署。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「enabledPlugins」欄位中的 `false` 和「key 不存在」語意相同嗎？（答案是不同：`false` = 顯式停用，key 不存在 = 從更低優先級繼承）
- **假設**：如果使用者的磁碟空間不足，7 天延遲清理是否反而成為問題？有沒有強制立即清理的選項？
- **證據**：`installed_plugins.json` 的 V1/V2 雙寫被稱為「技術債」，但是否有數據顯示這導致過實際問題？
- **觀點**：如果站在 Plugin 開發者的角度，「自動發現」是否降低了可預測性？manifest 聲明 vs 目錄自動發現，哪個更安全？
- **後果**：若大量 plugin 採用 project scope 安裝，每個 `.claude/settings.json` 都有長長的 enabledPlugins 清單，是否會造成 settings 合併衝突（merge conflict）？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 快取膨脹。每次更新保留舊版 7 天，高頻更新的 plugin（如 nightly build）可能累積數十個版本。沒有全域磁碟用量上限或版本數上限。極端情況下可耗盡磁碟空間。
2. **什麼情況下會失敗？** — 離線安裝場景。Project scope 的 settings.json 宣告了 `enabledPlugins[id]=true`，但新團隊成員的機器上沒有快取，`loadAllPluginsCacheOnly()` 會 emit `plugin-cache-miss`，元件不會載入。需要手動 `plugin install` 觸發下載。
3. **有沒有更好的替代方案？** — VS Code 的 Extension Marketplace 模式：settings sync 時同步擴充本身，而非只同步 flag。優點是「一鍵同步全部」，缺點是 settings 檔案大、同步慢。Claude Code 的「只同步 flag」模式更輕量，但犧牲了全自動化。

---

## 相關連結（Related）

- [[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]] — npx skills 的另一種安裝路徑，與 plugin install 互補
- [[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]] — 記憶系統同樣採用分層架構，與 plugin 的 scope 設計理念一致
- [[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]] — Team Memory 的同步機制可與 project scope plugin 對照理解
- [[2026-01-24-CLAUDE-CODE-HOOKS-CODE-ANALYSIS]] — Hooks 系統的深度分析，plugin hooks 是其擴充形式
- [[2026-04-12-CLAUDE-CODE-WORKTREE-FILE-OPERATIONS-AND-REPO-INTEGRATION]] — 同樣以檔案操作角度分析 Claude Code 功能的姊妹文

## References

- Claude Code decompiled source: `src/utils/plugins/`, `src/services/plugins/`
- 核心檔案：`pluginInstallationHelpers.ts`, `pluginOperations.ts`, `pluginLoader.ts`, `installedPluginsManager.ts`, `cacheUtils.ts`, `settings.ts`
