---
title: "Claude Code Plugin.json 依賴系統與共享 Skills 原始碼深度分析"
date: 2026-04-19
category: DevTools
tags:
  - #devtools/claude-code
  - #devtools/plugin-system
  - #code-analysis
  - #ai/agent-architecture
source: "https://github.com/anthropics/claude-code/issues/9444"
source_type: article
author: "源碼分析 + GitHub Issue #9444 & #27113 社群討論 + 本地實驗驗證（2026-04-20）"
status: notes
links:
  - "[[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]]"
  - "[[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]]"
  - "[[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]]"
  - "[[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]]"
  - "[[2026-03-02-PSA-CLAUDE-CODE-PLUGINS-LOADING-TWICE-KILLING-CONTEXT]]"
---

## 摘要（Summary）

本文深入分析 Claude Code 的 `plugin.json` manifest 結構，聚焦於 **dependencies（依賴宣告）** 與 **skills 路徑共享** 兩大機制。透過逐行追蹤原始碼（`schemas.ts`、`validatePlugin.ts`、`pluginLoader.ts`），釐清 schema 驗證、runtime 載入、path traversal 安全檢查的三層行為差異。同時對照 GitHub Issue [anthropics/claude-code#9444](https://github.com/anthropics/claude-code/issues/9444) 的社群討論，整理目前官方尚未實現的功能缺口與社群 workaround。

## 關鍵洞察（Key Insights）

- **Schema 驗證與 Runtime 載入行為不一致** — `PluginManifestSkillsSchema` 只檢查路徑是否以 `./` 開頭，但 `validatePluginManifest`（`claude plugin validate`）會額外檢查 `..` 路徑。Runtime loader 不檢查 `..`，因此 `./../../other-plugin/skills` 在 runtime 可運作
- **dependencies 目前只做軟性檢查** — 宣告 dependency 不會觸發自動安裝，版本號會被 `DependencyRefSchema` 的 transform 直接丟棄，只做「是否啟用」的降級判斷
- **Plugin 間資源共享是社群最大痛點之一** — Issue #9444 有大量 +1，但截至 2026-04-19 仍為 OPEN 狀態，官方尚未提供正式方案
- **三層驗證機制各司其職** — Zod schema（格式）、validatePlugin（安全 lint）、pluginLoader（runtime 存在性）分別在不同階段運作

## 詳細內容（Details）

### 一、plugin.json 完整 Schema 結構

根據 `src/utils/plugins/schemas.ts` 中的 `PluginManifestSchema`，一個 plugin.json 由以下子 schema 組合而成：

```
PluginManifestSchema = {
  ...PluginManifestMetadataSchema,      // name, version, description, author, keywords, dependencies
  ...PluginManifestHooksSchema,         // hooks (optional)
  ...PluginManifestCommandsSchema,      // commands (optional)
  ...PluginManifestAgentsSchema,        // agents (optional)
  ...PluginManifestSkillsSchema,        // skills (optional)
  ...PluginManifestOutputStylesSchema,  // outputStyles (optional)
  ...PluginManifestChannelsSchema,      // channels (optional)
  ...PluginManifestMcpServerSchema,     // mcpServers (optional)
  ...PluginManifestLspServerSchema,     // lspServers (optional)
  ...PluginManifestSettingsSchema,      // settings (optional)
  ...PluginManifestUserConfigSchema,    // userConfig (optional)
}
```

> [!important] 關鍵設計：除了 `PluginManifestMetadataSchema` 是必要的，其餘子 schema 全部是 `.partial()`，代表所有欄位皆為選填。

### 二、Skills 路徑驗證的三層機制

#### 第一層：Zod Schema 驗證（格式檢查）

```typescript
// schemas.ts:162
const RelativePath = lazySchema(() => z.string().startsWith('./'))

// schemas.ts:484-499
const PluginManifestSkillsSchema = lazySchema(() =>
  z.object({
    skills: z.union([
      RelativePath(),           // 單一路徑
      z.array(RelativePath()),  // 路徑陣列
    ]),
  }),
)
```

**結論**：只檢查路徑是否以 `./` 開頭。`./../../other/skills` 以 `./` 開頭，通過此層 ✅

#### 第二層：validate 指令的安全檢查（Lint）

```typescript
// validatePlugin.ts:92-106
function checkPathTraversal(p, field, errors, hint) {
  if (p.includes('..')) {
    errors.push({
      path: field,
      message: hint
        ? `Path contains "..": ${p}. ${hint}`
        : `Path contains ".." which could be a path traversal attempt: ${p}`,
    })
  }
}

// validatePlugin.ts:203-210 — 在 validatePluginManifest 中呼叫
if (obj.skills) {
  const skills = Array.isArray(obj.skills) ? obj.skills : [obj.skills]
  skills.forEach((skill, i) => {
    if (typeof skill === 'string') {
      checkPathTraversal(skill, `skills[${i}]`, errors)
    }
  })
}
```

**結論**：`claude plugin validate` 會將含 `..` 的路徑標記為 **error**。但此函式只在 validate 指令中被呼叫，不影響 runtime ⚠️

#### 第三層：Runtime Loader（實際載入）

```typescript
// pluginLoader.ts:1265-1307
async function validatePluginPaths(relPaths, pluginPath, ...) {
  const checks = await Promise.all(
    relPaths.map(async relPath => {
      const fullPath = join(pluginPath, relPath)  // 關鍵！直接 join，不檢查 ..
      return { relPath, fullPath, exists: await pathExists(fullPath) }
    }),
  )
  // 只檢查路徑是否存在，不檢查是否逃逸
  for (const { relPath, fullPath, exists } of checks) {
    if (exists) {
      validPaths.push(fullPath)
    } else {
      errors.push({ type: 'path-not-found', ... })
    }
  }
  return validPaths
}
```

**結論**：Runtime 只做 `pathExists()` 檢查，完全不管 `..`。只要目標路徑存在，skills 就會被載入 ✅

> [!warning] 安全隱患
> Runtime loader 不限制 `..` 路徑意味著 plugin 可以讀取 plugin 目錄之外的任何檔案系統路徑。這在 marketplace 分發場景下是安全風險。

### 三、路徑解析範例

假設 plugin 結構如下：

```
monorepo/
├── framework/
│   └── framework-base-expert/
│       └── skills/
│           └── base-skill/
│               └── SKILL.md
├── wifi-bora/
│   ├── wifi-bora-base-expert/
│   │   └── skills/
│   └── wifi-bora-memory-slim-expert/    ← pluginPath
│       └── .claude-plugin/
│           └── plugin.json
└── sys-bora/
    └── sys-bora-preflight-expert/
        └── skills/
```

`pluginPath` = `monorepo/wifi-bora/wifi-bora-memory-slim-expert/`

路徑解析（`join(pluginPath, relPath)`）：

| plugin.json 中的 skills 路徑 | 解析後的絕對路徑 | 是否正確？ |
|------|------|------|
| `./../../framework/framework-base-expert/skills` | `monorepo/framework/framework-base-expert/skills` | ✅ |
| `./../wifi-bora-base-expert/skills` | `monorepo/wifi-bora/wifi-bora-base-expert/skills` | ✅ |
| `./../../sys-bora/sys-bora-preflight-expert/skills` | `monorepo/sys-bora/sys-bora-preflight-expert/skills` | ✅ |

### 四、Dependencies 依賴機制分析

#### DependencyRefSchema — 格式定義

```typescript
// schemas.ts:1348-1391
const DEP_REF_REGEX = /^[a-z0-9][-a-z0-9._]*(@[a-z0-9][-a-z0-9._]*)?(@\^[^@]*)?$/i

export const DependencyRefSchema = lazySchema(() =>
  z.union([
    z.string()
      .regex(DEP_REF_REGEX, '...')
      .transform(s => s.replace(/@\^[^@]*$/, '')),  // 版本號直接丟棄！
    z.object({
      name: z.string().min(1).regex(/^[a-z0-9][-a-z0-9._]*$/i),
      marketplace: z.string().min(1).regex(/^[a-z0-9][-a-z0-9._]*$/i).optional(),
    }).loose()
      .transform(o => (o.marketplace ? `${o.name}@${o.marketplace}` : o.name)),
  ]),
)
```

> [!note] 版本號被丟棄的設計意圖
> 原始碼註解說明這是 **forwards-compat**（向前相容）策略：未來的 client 加入版本約束時，舊 client 不會因為 schema 驗證失敗而拒絕整個 plugin。參見 `CC-993` 版本範圍設計（尚未實作）。

#### 支援的依賴格式

| 格式 | 範例 | 結果 |
|------|------|------|
| 裸名 | `"framework-base-expert"` | 解析到同一個 marketplace |
| 跨 marketplace | `"plugin@other-marketplace"` | 指定 marketplace |
| 帶版本（會被丟棄） | `"plugin@mkt@^1.2"` | transform 移除 `@^1.2` |
| 物件格式 | `{name: "x", marketplace: "y"}` | 轉為 `"x@y"` |

#### Runtime 依賴解析 — verifyAndDemote

依賴檢查在 `dependencyResolver.ts` 的 `verifyAndDemote` 中執行：

- 檢查每個 dependency 是否在同一個 marketplace 中**已啟用**
- 如果 dependency 未啟用或找不到，plugin 會被 **demoted**（降級/停用）
- **不會自動安裝** dependency
- **不會檢查版本**

```
Plugin A 宣告 dependencies: ["B", "C"]
  │
  ├─ B 已啟用？ ──是──► 繼續
  │                  否──► Plugin A 被 demoted
  │
  └─ C 已啟用？ ──是──► 繼續
                     否──► Plugin A 被 demoted
```

### 五、Dependencies 實戰寫法與實驗結果（2026-04-20 驗證）

> [!important] 這一節是透過本地實驗驗證的結果，補充上方原始碼分析所得的理論知識。

#### 5.1 正確的依賴宣告位置（關鍵！）

**Dependencies 必須在兩個地方同時宣告，各自負責不同階段：**

| 位置 | 用途 | 時機 | 若缺少 |
|------|------|------|------|
| `marketplace.json` 的 entry | install-time 自動安裝閉包 | `claude plugins install` | 安裝時不會自動拉取依賴（但不報錯） |
| `plugin.json` | load-time demote 驗證 | Claude Code 啟動時 | 啟動後不會檢查依賴是否啟用 |

> [!warning] 常見誤解
> 只在 `plugin.json` 宣告 `dependencies`，安裝時並**不會**自動安裝依賴。`resolveDependencyClosure`（安裝時的 DFS 遍歷）只讀 marketplace entry 的 `dependencies` 欄位，不讀 plugin 目錄下的 `plugin.json`。

#### 5.2 完整寫法範例 — A → B → C 三層依賴鏈

**目錄結構：**

```
marketplace-root/
├── .claude-plugin/
│   └── marketplace.json       ← marketplace manifest
├── plugin-a/                  ← 根節點
│   ├── .claude-plugin/
│   │   └── plugin.json        ← dependencies: ["plugin-b"]
│   ├── commands/
│   │   └── report.md
│   └── skills/
│       └── report.md
├── plugin-b/                  ← 中間節點
│   ├── .claude-plugin/
│   │   └── plugin.json        ← dependencies: ["plugin-c"]
│   ├── commands/
│   │   └── format.md
│   └── skills/
│       └── format.md
└── plugin-c/                  ← 葉節點（無依賴）
    ├── .claude-plugin/
    │   └── plugin.json
    ├── commands/
    │   └── greet.md
    └── skills/
        └── greet.md
```

**marketplace.json（dependencies 必須在此宣告，安裝才會自動解析）：**

```json
{
  "name": "dep-experiment",
  "owner": { "name": "swchen" },
  "plugins": [
    {
      "name": "plugin-c",
      "source": "./plugin-c",
      "description": "葉節點，無依賴"
    },
    {
      "name": "plugin-b",
      "source": "./plugin-b",
      "description": "中間節點，依賴 C",
      "dependencies": ["plugin-c"]
    },
    {
      "name": "plugin-a",
      "source": "./plugin-a",
      "description": "根節點，依賴 B（B 又依賴 C）",
      "dependencies": ["plugin-b"]
    }
  ]
}
```

> [!note] source 路徑格式
> `RelativePath` schema 要求路徑以 `./` 開頭（`"./plugin-a"` ✅，`"plugin-a"` ❌），相對於 marketplace repo root。

**plugin-a/.claude-plugin/plugin.json（load-time 驗證用）：**

```json
{
  "name": "plugin-a",
  "version": "1.0.0",
  "description": "Root plugin — depends on plugin-b",
  "dependencies": ["plugin-b"]
}
```

**plugin-b/.claude-plugin/plugin.json：**

```json
{
  "name": "plugin-b",
  "version": "1.0.0",
  "description": "Middle plugin — depends on plugin-c",
  "dependencies": ["plugin-c"]
}
```

**plugin-c/.claude-plugin/plugin.json（葉節點，無依賴）：**

```json
{
  "name": "plugin-c",
  "version": "1.0.0",
  "description": "Leaf plugin — no dependencies"
}
```

#### 5.3 Marketplace 加入與驗證指令

```bash
# 1. 驗證 marketplace manifest
claude plugins validate /path/to/marketplace-root

# 2. 加入 marketplace（local directory）
claude plugins marketplace add /path/to/marketplace-root

# 3. 安裝根 plugin，B 和 C 自動被拉進來
claude plugins install plugin-a@dep-experiment
# 輸出：✔ Successfully installed plugin: plugin-a@dep-experiment (scope: user) (+ 2 dependencies)

# 4. 若修改了 marketplace.json，更新快取
claude plugins marketplace update dep-experiment
```

#### 5.4 實驗結果 — 三個情境的實際行為

**情境一：安裝根 plugin，自動解析閉包** ✅

```bash
$ claude plugins install plugin-a@dep-experiment
Installing plugin "plugin-a@dep-experiment"...
✔ Successfully installed plugin: plugin-a@dep-experiment (scope: user) (+ 2 dependencies)

$ claude plugins list | grep plugin-[abc]
  ❯ plugin-a@dep-experiment  Version: 1.0.0  Status: ✔ enabled
  ❯ plugin-b@dep-experiment  Version: 1.0.0  Status: ✔ enabled
  ❯ plugin-c@dep-experiment  Version: 1.0.0  Status: ✔ enabled
```

**情境二：停用中間 plugin，根 plugin 被降級** ✅

```bash
$ claude plugins disable plugin-b@dep-experiment
✔ Successfully disabled plugin: plugin-b (scope: user) — warning: required by plugin-a

$ claude plugins list | grep -A4 plugin-a
  ❯ plugin-a@dep-experiment
    Status: ✘ failed to load
    Error: Dependency "plugin-b@dep-experiment" is disabled — enable it or remove the dependency
```

- 停用時會顯示 `warning: required by plugin-a`（不阻擋，但提醒）
- 下次 Claude Code 載入時，plugin-a 的 `verifyAndDemote` 偵測到 B 被停用 → 降級為 `failed to load`
- `fixed-point` 迭代：若 C 也依賴 A，停用 B 會連帶降級 A，進而降級 C

**情境三：製造循環依賴，安裝直接失敗** ✅

在 `marketplace.json` 加入 `plugin-c → plugin-a`（造成 A→B→C→A 循環），然後嘗試全新安裝：

```bash
$ claude plugins install plugin-a@dep-experiment
Installing plugin "plugin-a@dep-experiment"...
✘ Failed to install plugin "plugin-a@dep-experiment":
  Dependency cycle: plugin-a@dep-experiment → plugin-b@dep-experiment
                    → plugin-c@dep-experiment → plugin-a@dep-experiment
```

> [!tip] 循環偵測的前提
> 循環偵測（cycle detection）只在**安裝時** `resolveDependencyClosure` 的 DFS 遍歷中執行。如果相關 plugins 已全部在 `alreadyEnabled` 集合中，DFS 會跳過它們，循環不會被偵測到。要觸發循環偵測，必須在所有 plugins 尚未安裝的狀態下執行安裝。

#### 5.5 已安裝但 plugin.json 與 marketplace.json 不一致的問題

若只有 `plugin.json` 宣告了 dependencies（marketplace.json 沒有），會出現：

1. 安裝時：只安裝根 plugin，B/C 不會被自動安裝（因為 DFS 找不到依賴）
2. 載入時：plugin-a 報 `Dependency "plugin-b@dep-experiment" is not found in any configured marketplace`
3. 現象看起來像「安裝成功但無法載入」

這是一個容易踩坑的地方——`claude plugins validate` 只驗證 manifest 格式，不會警告你兩邊的 dependencies 是否同步。

### 六、GitHub Issue #9444 — 社群痛點與討論

#### 問題核心

提出者 @jawhnycooke 的 marketplace 有 11 個 plugins，需要把 **32 個 agents 複製到 7 個 plugins** 中。例如 `@code-archaeologist` 被 5 個 plugin 使用。目前每個 plugin 必須各自複製一份，導致：

1. 檔案重複（File Duplication）
2. 維護負擔（Maintenance Burden）
3. 不一致風險（Inconsistency Risk）

#### 目前狀態（截至 2026-04-19）

| 功能 | 狀態 | 說明 |
|------|------|------|
| `dependencies` 欄位 | ✅ 已實現 | 但只做軟性啟用檢查 |
| 版本約束（Version Constraints） | ❌ 未實現 | schema 接受但 transform 丟棄 |
| 自動安裝依賴 | ❌ 未實現 | 不會自動拉取 |
| 跨 marketplace 依賴 | ❌ 未實現 | 裸名只解析到同 marketplace |
| 共享資源 / library 類型 | ❌ 未實現 | `"type": "library"` 不存在 |
| `exports` 機制 | ❌ 未實現 | 無法宣告可被引用的資源 |

#### 社群 Workaround 整理

| 方案 | 做法 | 優點 | 缺點 |
|------|------|------|------|
| **`..` 路徑引用** | `skills: ["./../../other/skills"]` | Runtime 可用 | validate 報錯、安全風險、marketplace 分發失效 |
| **Symlinks** | `ln -s` 共享檔案 | 簡單 | Git 處理 symlink 有坑 |
| **Git Submodule** | 在 plugin 內放 submodule | 版本可控 | submodule 複雜度高 |
| **Monolithic Plugin** | 所有功能放單一 plugin | 一定可運作 | 重複、不可組合 |
| **CLAUDE.md 手動宣告** | 在 CLAUDE.md 寫載入順序 | 無需改 plugin 系統 | 不可靠、難維護 |
| **`strict: false` + 提升 source** | marketplace entry 用 `strict: false` | 官方支援的路徑 | 設定繁瑣、`@` 引用失效 |

> [!tip] 可行的 Workaround — `strict: false` 模式
> 在 `marketplace.json` 中將 plugin entry 設為 `strict: false`，並將 `source` 路徑提升到更高的目錄層級。這樣 skills 路徑就不需要 `..`：
> ```json
> {
>   "name": "my-plugin",
>   "source": "./",
>   "strict": false,
>   "skills": ["./shared-skills", "./my-plugin/skills"]
> }
> ```
> 這是目前最接近官方支援的做法，但 `@skill-name` 呼叫方式可能失效，需改用 "use skill X" 指令。

### 六、plugin.json 結構驗證規則完整整理

以下整理從原始碼提取的所有驗證規則：

| 欄位 | 型別 | 必要性 | 驗證規則 |
|------|------|--------|---------|
| `name` | string | **必要** | 不可為空、不可含空格、建議 kebab-case |
| `version` | string | 選填 | 建議 semver 格式 |
| `description` | string | 選填 | 使用者看到的說明 |
| `author` | object | 選填 | `{name: string, email?: string, url?: string}` |
| `keywords` | string[] | 選填 | 標籤陣列 |
| `dependencies` | string[] | 選填 | 裸名或 `name@marketplace` 格式 |
| `skills` | string \| string[] | 選填 | 必須以 `./` 開頭 |
| `commands` | string \| string[] \| object | 選填 | 以 `./` 開頭，或物件映射格式 |
| `agents` | string \| string[] | 選填 | 以 `./` 開頭，需 `.md` 結尾 |
| `hooks` | string \| object \| array | 選填 | JSON 路徑或 inline hooks 定義 |
| `mcpServers` | string \| object \| array | 選填 | JSON 路徑、MCPB、或 inline 定義 |
| `lspServers` | string \| object \| array | 選填 | JSON 路徑或 inline 定義 |
| `channels` | array | 選填 | MCP channel 宣告 |
| `userConfig` | object | 選填 | 使用者可設定值的宣告 |
| `settings` | object | 選填 | 合併進 settings cascade |

### 七、Plugin 目錄結構慣例

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest（必要）
├── skills/                  # 預設 skills 目錄（自動偵測）
│   └── my-skill/
│       └── SKILL.md
├── commands/                # 預設 commands 目錄（自動偵測）
│   └── my-command.md
├── agents/                  # 預設 agents 目錄（自動偵測）
│   └── my-agent.md
├── hooks/                   # 預設 hooks 目錄
│   └── hooks.json
├── output-styles/           # 預設 output styles 目錄
│   └── my-style.md
└── .mcp.json                # MCP server 設定（自動偵測）
```

> [!note] 自動偵測 vs manifest 宣告
> Plugin loader 會同時掃描**預設目錄**（`skills/`、`commands/`、`agents/`）與 **manifest 中宣告的額外路徑**。兩者可以並存——manifest 的路徑是「額外的」（in addition to），不是「取代」。

### 八、跨 Scope 安裝的依賴解析 — Plugin A@project 依賴 B@user 能否成功？

> [!important] 結論：**依賴會成功** ✅。`verifyAndDemote` 在做依賴檢查時，已經把所有 scope 的 settings 合併成一個扁平的 `enabledPlugins` map，完全不區分安裝 scope。

#### 問題場景

Plugin A 安裝在 **project** scope（`$project/.claude/settings.json`），依賴 Plugin B。Plugin B 安裝在 **user** scope（`~/.claude/settings.json`）。這樣子依賴檢查是否通過？

#### 完整執行流程追蹤

**步驟 1：Settings Merge（五源合併）**

`pluginLoader.ts:1896-1901` 中，`getSettings_DEPRECATED()` 會合併所有 scope 的設定：

```typescript
const settings = getSettings_DEPRECATED()
const enabledPlugins = {
  ...getAddDirEnabledPlugins(),
  ...(settings.enabledPlugins || {}),  // 已合併 managed → user → project → local
}
```

合併後的 `enabledPlugins` 結果：
```json
{
  "A@my-marketplace": true,   // ← 來自 projectSettings
  "B@my-marketplace": true    // ← 來自 userSettings
}
```

> [!note] 關鍵：settings merge 發生在 plugin loading 之前
> Settings cascade 的合併順序為 `managed → user → project → local → flag`，後者覆蓋前者。`enabledPlugins` 是所有層級的**聯集**（union），不是覆蓋——因為每個 plugin ID 是獨立的 key。

**步驟 2：Plugin Loading（統一載入）**

`loadAllMarketplacePlugins`（`pluginLoader.ts:1906-1915`）遍歷合併後的 `enabledPlugins`，不管各 plugin 來自哪個 scope，全部載入到同一個 `plugins` 陣列：

```typescript
const marketplacePluginEntries = Object.entries(enabledPlugins).filter(
  ([key, value]) => {
    const isValidFormat = PluginIdSchema().safeParse(key).success
    if (!isValidFormat || value === undefined) return false
    const { marketplace } = parsePluginIdentifier(key)
    return marketplace !== BUILTIN_MARKETPLACE_NAME
  },
)
```

**步驟 3：assemblePluginLoadResult — 合併所有來源**

`pluginLoader.ts:3177-3196` 將 marketplace plugins、session plugins、builtin plugins 全部合併後，才做依賴檢查：

```typescript
const { plugins: allPlugins, errors: mergeErrors } = mergePluginSources({
  session: sessionResult.plugins,
  marketplace: marketplaceResult.plugins,
  builtin: [...builtinResult.enabled, ...builtinResult.disabled],
  managedNames: getManagedPluginNames(),
})

// 依賴檢查在合併之後才執行
const { demoted, errors: depErrors } = verifyAndDemote(allPlugins)
```

**步驟 4：verifyAndDemote — Scope 無關的依賴判斷**

`dependencyResolver.ts:177-234` 中的核心邏輯：

```typescript
export function verifyAndDemote(plugins: readonly LoadedPlugin[]) {
  const known = new Set(plugins.map(p => p.source))
  const enabled = new Set(plugins.filter(p => p.enabled).map(p => p.source))
  // ...
  for (const p of plugins) {
    if (!enabled.has(p.source)) continue
    for (const rawDep of p.manifest.dependencies ?? []) {
      const dep = qualifyDependency(rawDep, p.source)
      const isBare = !parsePluginIdentifier(dep).marketplace
      const satisfied = isBare
        ? (enabledByName.get(dep) ?? 0) > 0   // 裸名：任何 marketplace 的同名 plugin 啟用即可
        : enabled.has(dep)                      // 帶 @marketplace：精確匹配
    }
  }
}
```

判斷過程（以 A 依賴 B 為例）：
1. `enabled` Set = `{"A@my-marketplace", "B@my-marketplace", ...}`
2. A 的 dependency `"B"`（裸名）→ `qualifyDependency("B", "A@my-marketplace")` → `"B@my-marketplace"`
3. `enabled.has("B@my-marketplace")` → **true** ✅
4. A 不會被 demoted

```
Settings Merge（五源合併成扁平 map）
┌─────────────────────────────────────────────┐
│ managed → user → project → local → flag     │
│                                             │
│ enabledPlugins: {                           │
│   "A@mkt": true,  ← from projectSettings   │
│   "B@mkt": true,  ← from userSettings      │
│ }                                           │
└──────────────┬──────────────────────────────┘
               │
               ▼
    loadAllMarketplacePlugins()
    （不管 scope，全部載入）
               │
               ▼
    allPlugins = [A(enabled), B(enabled), ...]
               │
               ▼
    verifyAndDemote(allPlugins)
    ┌──────────────────────────┐
    │ enabled = {"A@mkt", "B@mkt"} │
    │                          │
    │ A depends on "B"         │
    │ → qualify → "B@mkt"      │
    │ → enabled.has("B@mkt")   │
    │ → true ✅ SATISFIED      │
    └──────────────────────────┘
               │
               ▼
    A 和 B 都正常啟用，Doctor 無錯誤
```

#### 裸名 vs 帶 @marketplace 的依賴比對

`verifyAndDemote` 對裸名（bare dependency）有特殊處理——這是為了支援 `--plugin-dir`（`@inline`）plugins：

```typescript
// dependencyResolver.ts:183-194
const knownByName = new Set(plugins.map(p => parsePluginIdentifier(p.source).name))
const enabledByName = new Map<string, number>()
for (const id of enabled) {
  const n = parsePluginIdentifier(id).name
  enabledByName.set(n, (enabledByName.get(n) ?? 0) + 1)  // multiset 計數
}
```

| dependency 寫法 | 比對方式 | 範例 |
|------|------|------|
| `"B"` （裸名） | `enabledByName.get("B") > 0` — 任何 marketplace 的 B 都算 | `B@epic` 或 `B@other` 都滿足 |
| `"B@my-mkt"` （帶 marketplace） | `enabled.has("B@my-mkt")` — 精確匹配 | 只有 `B@my-mkt` 才算 |

> [!warning] enabledByName 是 multiset
> 如果 `B@epic` 和 `B@other` 同時啟用，`enabledByName.get("B")` = 2。當 demote 其中一個時，計數減為 1，裸名依賴仍然滿足。只有計數歸零才會觸發 demote。

#### Doctor 如何顯示 Plugin 依賴錯誤

Doctor（`/doctor`）指令**不會自己重新檢查依賴**，它只是讀取 `AppState.plugins.errors` 並顯示：

```tsx
// Doctor.tsx:457-463
const pluginsErrors = useAppState(s => s.plugins.errors)

pluginsErrors.length > 0 && (
  <Box flexDirection="column">
    <Text bold color="error">Plugin Errors</Text>
    <Text color="error">└ {pluginsErrors.length} plugin error(s) detected:</Text>
    {pluginsErrors.map((error, i) => (
      <Text key={i} dimColor>
        └ {error.source}: {getPluginErrorMessage(error)}
      </Text>
    ))}
  </Box>
)
```

依賴失敗時的錯誤訊息格式（`types/plugin.ts`）：

```typescript
// 錯誤類型：dependency-unsatisfied
{
  type: 'dependency-unsatisfied',
  source: 'A@my-marketplace',
  plugin: 'A',
  dependency: 'B@my-marketplace',
  reason: 'not-enabled' | 'not-found'
}

// 顯示訊息
// not-enabled: Dependency "B@my-marketplace" is disabled — enable it or remove the dependency
// not-found:   Dependency "B@my-marketplace" is not found in any configured marketplace
```

> [!tip] Doctor 的 Plugin Errors 區塊
> Doctor 不做額外的依賴檢查——它只是呈現 `assemblePluginLoadResult` 中已收集的錯誤。如果依賴在載入時就成功了，Doctor 不會顯示任何 plugin error。

#### Fixed-Point 迭代 — 連鎖降級（Cascading Demotion）

`verifyAndDemote` 使用 fixed-point loop（`dependencyResolver.ts:198`）：降級 A 可能導致依賴 A 的 C 也被降級，因此需要反覆迭代直到沒有變化：

```typescript
let changed = true
while (changed) {
  changed = false
  for (const p of plugins) {
    if (!enabled.has(p.source)) continue
    for (const rawDep of p.manifest.dependencies ?? []) {
      // ... 檢查 dependency 是否 satisfied
      if (!satisfied) {
        enabled.delete(p.source)         // 降級此 plugin
        // 更新 enabledByName 計數
        changed = true                    // 觸發下一輪迭代
        break
      }
    }
  }
}
```

降級範例：
```
A depends on B, C depends on A
B 被停用
  → 第 1 輪：A 的 dependency B 不滿足 → A 被 demoted
  → changed = true，進入第 2 輪
  → 第 2 輪：C 的 dependency A 不滿足（A 已被 demoted）→ C 被 demoted
  → changed = true，進入第 3 輪
  → 第 3 輪：沒有新的 demotion → changed = false → 結束
```

## 我的心得（My Takeaways）

1. **三層驗證的分離設計值得學習** — Schema 管格式、Validate 管安全 lint、Loader 管存在性。這讓 runtime 保持韌性（不會因為新欄位或小問題就 crash），同時給開發者提供嚴格的 lint 工具
2. **`..` 路徑 workaround 在本地開發可行，但不可依賴** — 它繞過了安全檢查、在 marketplace 分發場景會失效。正確做法是等官方依賴系統或用 `strict: false` 模式
3. **版本號被靜默丟棄是一個陷阱** — 寫了 `"dependencies": ["core@^1.0"]` 看起來有版本約束，實際上完全被忽略。需注意這個行為
4. **Plugin 系統比想像中複雜** — 支援 npm、pip、git、github、git-subdir 等多種來源，有 marketplace 層級的安全策略、blocklist、auto-update，以及多 scope 安裝（managed/user/project/local）

## 待補充（Open Questions）

- Plugin 的 `strict: false` 模式具體是如何改變 manifest 解析行為的？marketplace entry 中的欄位如何覆蓋或補充 plugin.json？建議搜尋：`strict false pluginLoader`
- ~~`verifyAndDemote` 降級後的 plugin 在 UI 上如何呈現？~~ **已解答**：Doctor 讀取 `AppState.plugins.errors`，顯示 `dependency-unsatisfied` 錯誤，區分 `not-enabled`（已載入但停用）和 `not-found`（完全找不到）兩種原因
- 跨 marketplace 依賴（`allowCrossMarketplaceDependenciesOn`）目前的實際行為是什麼？這個欄位已經存在於 `PluginMarketplaceSchema` 中，是否已有部分實現？建議搜尋：`crossMarketplace dependency resolve`
- 未來 `CC-993` 版本範圍設計會如何改變現有的 dependency 解析邏輯？transform 丟棄版本號的行為是否會在某個版本被移除？
- Plugin 的 `userConfig` 中 `sensitive: true` 的值如何在 macOS keychain 中儲存？多個 plugin 共享一個 keychain entry 的 2KB 限制（INC-3028）在實務上是否已造成問題？

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 1. `RelativePath` schema 只檢查 `./` 開頭 2. `checkPathTraversal` 只在 validate 指令中執行 3. `DependencyRefSchema` 的 transform 會丟棄版本號 4. runtime loader 用 `join(pluginPath, relPath)` 解析路徑 5. dependencies 裸名解析到同一個 marketplace |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Plugin 系統有三層驗證（Schema → Validate → Loader），各層職責分離：Schema 確保格式合法、Validate 提供安全 lint 回饋、Loader 只管目標是否存在。這種分層設計讓 runtime 有最大韌性，同時透過 validate 工具給開發者嚴格回饋。dependencies 的設計同樣採用漸進策略——先保留欄位格式、用 transform 忽略未實現部分，留給未來版本填補 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | **假設一**：`..` 路徑不檢查是因為 runtime 信任 marketplace 的審核機制（但 `strict: false` 模式繞過了 plugin.json 審核）。**假設二**：版本號丟棄是暫時方案，但若長期維持，使用者會誤以為版本約束有效。**邏輯漏洞**：validate 報 path traversal error 但 runtime 不阻擋，等於安全檢查是 advisory-only，對不跑 validate 的開發者無效 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. **本地 monorepo 開發**：可以用 `./../../` 路徑引用共享 skills，但要在 CI 中跳過 `claude plugin validate` 或接受其 path traversal warning 2. **Marketplace 發佈**：改用 `strict: false` + 提升 source 路徑的方案，避免 `..` 路徑問題 3. **建立 plugin 依賴時**：不要依賴版本號約束，確保所有依賴 plugin 都在同一個 marketplace 中 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | `..` 路徑 vs `strict: false`：前者寫法直覺但安全性差、validate 報錯；後者是官方支援路徑但設定繁瑣、`@` 引用失效。對於內部團隊的 monorepo plugin，`..` 路徑的簡單性值得冒安全風險；對於公開 marketplace，必須用 `strict: false` 或等待 Issue #9444 的正式解決方案 |

### 分析型追問（Socratic Follow-up）

- **澄清**：`strict: false` 中的 "strict" 到底在控制什麼？是「必須有 plugin.json」還是「路徑必須在 plugin 目錄內」？
- **假設**：本文假設 runtime loader 不檢查 `..` 是設計決策而非遺漏。若這是 bug，未來版本可能會加入檢查，屆時所有 `..` workaround 都會失效
- **證據**：Issue #9444 中 @burneyhoel 報告 `../dep.md`（不以 `./` 開頭）被 schema 拒絕，但 `./../../xxx` 可通過。這是 schema 設計的意外副作用而非刻意允許
- **觀點**：反對者可能認為加入正式依賴系統會讓 plugin 生態系統變得像 npm 一樣複雜，而目前的簡單模型（每個 plugin 自包含）雖有重複但更穩定
- **後果**：若大量 plugin 開發者採用 `..` 路徑 workaround，未來官方若加入 path traversal 檢查到 runtime loader，會造成大規模 breaking change

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 使用 `..` 路徑的最大風險是**安全性**：惡意 plugin 可透過 `..` 路徑存取使用者檔案系統中的任意檔案。在 marketplace 場景下，使用者安裝一個 plugin 等於授予它讀取 plugin 目錄之外任意路徑的能力
2. **什麼情況下會失敗？** — 當 plugin 透過 marketplace（而非 `--plugin-dir` 本地目錄）安裝時，`pluginPath` 指向 cache 目錄（`~/.claude/plugins/installed/...`），此時 `../` 路徑不會解析到預期的其他 plugin，而是解析到 cache 目錄結構中的其他位置，導致 `path-not-found` 錯誤
3. **有沒有更好的替代方案？** — `strict: false` + 提升 source 路徑是目前最佳替代方案。長期來看，等待 Issue #9444 的正式依賴共享機制是最穩定的選擇。若團隊急需共享資源，可考慮用一個「共享資源 plugin」搭配 `dependencies` 宣告，讓每個 plugin 都依賴它（即使目前 dependencies 不自動安裝，至少可以提醒使用者需要同時啟用）

## 相關連結（Related）

- [[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]] — Plugin 安裝、停用、移除、更新的完整生命週期，與本文的 dependency 解析機制互補
- [[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]] — Skills 的解析與載入機制深度分析，涵蓋 SKILL.md 發現邏輯
- [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]] — Settings 層級（managed/user/project/local）如何影響 plugin 啟用狀態
- [[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]] — Skill 載入、壓縮、撰寫技巧完整指南
- [[2026-03-02-PSA-CLAUDE-CODE-PLUGINS-LOADING-TWICE-KILLING-CONTEXT]] — Plugin 載入兩次佔用 context 的已知問題

---

## 附錄：社群相關 Issues 分析

### 附錄 A — Issue #9444：Plugin Dependencies 與共享資源（OPEN）

**連結：** [anthropics/claude-code#9444](https://github.com/anthropics/claude-code/issues/9444)
**狀態：** 🟡 OPEN（2025-10-12 開，截至 2026-04-20 仍未關閉）
**作者：** @jawhnycooke ｜ **反應：** 43 個 +1 ｜ **留言：** 15 則

#### 碰到什麼問題？

提出者的 marketplace 有 **11 個 plugins**，需要把 **32 個 agents 複製到 7 個 plugins** 中，原因是多個 plugin 需要同樣的 agents：

- `@code-archaeologist` → 被 5 個 plugin 使用（epcc-workflow、documentation、architecture、tdd-workflow、performance）
- `@security-reviewer` → 被 4 個 plugin 使用
- `@test-generator` → 被 4 個 plugin 使用

**核心痛點：**
1. **檔案重複（File Duplication）** — 相同 agent 定義複製多份
2. **維護負擔（Maintenance Burden）** — 更新時要修改所有副本
3. **不一致風險（Inconsistency Risk）** — 各副本可能逐漸脫節
4. **儲存浪費（Storage Waste）** — marketplace 中的重複 agents 佔用空間

#### 建議的解法是什麼？

提出者建議三個機制共同作用：

**1. Plugin manifest 中的 dependencies 宣告**

```json
{
  "name": "epcc-workflow",
  "version": "1.0.0",
  "dependencies": {
    "common-core": "^1.0.0",
    "security-core": "^2.1.0"
  }
}
```

**2. Library 類型 plugin（共享資源庫）**

```json
{
  "name": "common-core",
  "type": "library",
  "exports": {
    "agents": ["code-archaeologist", "system-designer", "business-analyst"]
  }
}
```

**3. 安裝時自動解析依賴**

```bash
/plugin install epcc-workflow@claude-code-plugins
# 自動執行：
✓ Installing common-core@1.0.0
✓ Installing security-core@2.1.0
✓ Installing epcc-workflow@1.0.0
```

#### 他想解決什麼問題？

本質上是想實現 **DRY（Don't Repeat Yourself）原則** 在 Claude Code plugin 生態系中的應用——讓 plugin 能像 npm package 一樣透過 dependency 機制共享資源，避免 N 個 plugin 各自維護 N 份相同的 agent 定義。

> [!note] 與現況的差距
> 截至 2026-04-20，`dependencies` 欄位已存在於 schema 中，但：
> - 版本約束（`^1.0.0`）被 schema transform 靜默丟棄
> - `type: "library"` 欄位不存在
> - `exports` 欄位不存在
> - 跨 plugin 的 agent 引用（`@code-archaeologist` 解析到 dependency）不存在
>
> 也就是說：自動安裝閉包已部分實現（本文第五節驗證），但資源共享/引用機制仍是 OPEN 需求。

---

### 附錄 B — Issue #27113：Project-level 宣告式依賴（CLOSED）

**連結：** [anthropics/claude-code#27113](https://github.com/anthropics/claude-code/issues/27113)
**狀態：** 🔴 CLOSED（2026-02-20 開，2026-04-06 被機器人關閉為 inactive）
**作者：** @willmjackson ｜ **反應：** 7 個 +1 ｜ **留言：** 5 則

#### 碰到什麼問題？

作者是小公司 CEO，內部有多個 Claude Code skills（品牌聲音、部署工具等）透過私有 GitHub marketplace 分發。**不同專案需要不同的 plugin 子集**，目前沒有方法讓「專案」宣告自己需要哪些 plugin：

1. **缺少安裝提示（No install prompting）** — 新成員 clone repo 後不會被提示安裝缺少的 skills/plugins，只有在用到時才發現功能不存在
2. **缺少必要 vs 建議的區分（No required vs. recommended）** — `.claude/settings.json` 的 `enabledPlugins` 若 plugin 未安裝，無任何警告或提示
3. **Workaround 脆弱** — 目前只能在 `CLAUDE.md` 記載需要安裝的 plugins（Claude 能讀但無法程式化執行），或用 git submodule 管理（複雜且 MCP server 場景失效）

#### 建議的解法是什麼？

在 `.claude/settings.json` 加入宣告式依賴區塊：

```json
{
  "dependencies": {
    "required": [
      "brand-voice@company-tools",
      "deployment-tools@company-tools"
    ],
    "recommended": [
      "extension-capture@company-tools"
    ]
  },
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": { "source": "github", "repo": "company/claude-plugins" }
    }
  }
}
```

**預期行為：**
- `required` 缺少 → 開啟專案時提示安裝（類似 trust prompt 流程）
- `recommended` 缺少 → 通知使用者一次，可關閉
- 全部滿足 → 無提示

額外建議：版本釘定、`claude plugins reconcile` CLI 指令、與 org-level provisioning 整合。

#### 他想解決什麼問題？

與 Issue #9444 的角度不同——#9444 關注的是 **plugin 作者的資源共享**（plugin 間的 DRY），而 #27113 關注的是 **專案消費者的 onboarding 體驗**（像 `package.json` 一樣讓 repo 自我宣告依賴，讓新成員 clone 後自動引導安裝）。

> [!note] 為何被關閉？
> Issue 於 2026-04-06 被 GitHub Actions bot 以「inactive for too long」自動關閉，2026-04-14 被鎖定。官方並未回應或表明是否規劃實作。社群評論（@Techadler）指出版本解析（version pinning）的問題更深——目前 `enabledPlugins` 對每個 project × plugin 組合分開追蹤版本，這在多專案共享同一 user scope plugin 時會造成版本衝突。

> [!warning] 與現況的差距
> `.claude/settings.json` 目前沒有 `dependencies` 欄位，也沒有「開啟專案時提示安裝」的機制。`enabledPlugins` 只是靜態 flag，缺少的 plugin 只有在 `claude plugins list` 時才看到 `failed to load` 錯誤，而非在開啟專案時主動提示。

---

## References

- [GitHub Issue #9444 — Support for Plugin Dependencies and Shared Resources](https://github.com/anthropics/claude-code/issues/9444)
- [GitHub Issue #27113 — Feature: Declarative skill/plugin dependencies at the project level](https://github.com/anthropics/claude-code/issues/27113)
- 原始碼：`src/utils/plugins/schemas.ts`（Schema 定義）
- 原始碼：`src/utils/plugins/validatePlugin.ts`（驗證邏輯）
- 原始碼：`src/utils/plugins/pluginLoader.ts`（Runtime 載入）
- 原始碼：`src/types/plugin.ts`（Plugin 型別定義）
