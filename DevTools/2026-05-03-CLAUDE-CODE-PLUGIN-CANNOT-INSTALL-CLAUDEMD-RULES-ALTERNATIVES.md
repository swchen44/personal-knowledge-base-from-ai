---
title: "Claude Code Plugin 無法安裝 CLAUDE.md / Rules — 原始碼驗證與三種替代方案"
date: 2026-05-03
category: DevTools
tags:
  - #devtools/claude-code
  - #devtools/plugin-system
  - #devtools/configuration
  - #code-analysis
source: "conversation research: Plugin CLAUDE.md/Rules installation + official docs"
source_type: article
author: "swchen44 + Claude"
status: notes
links:
  - "[[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]]"
  - "[[2026-04-19-CLAUDE-CODE-PLUGIN-JSON-DEPENDENCIES-SHARED-SKILLS-SOURCE-ANALYSIS]]"
  - "[[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]]"
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
  - "[[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]]"
  - "[[2026-04-17-CLAUDEMD-MYTHS-DEBUNKED-SOURCE-CODE-VERIFICATION]]"
---

## 摘要（Summary）

深入追蹤 Claude Code v2.1.88 反編譯原始碼及[官方 Plugin 文件](https://code.claude.com/docs/en/plugins-reference)，驗證 Plugin 系統能否自動為使用者安裝 CLAUDE.md 或 `.claude/rules/` 規則檔案。核心結論：**Plugin manifest 沒有任何欄位可以建立、修改或注入 CLAUDE.md 與 rules**。安裝流程是純宣告式的，也沒有 `postInstall` / `onEnable` 生命週期鉤子。本文同時分析 rules frontmatter 的 `paths:` 機制（含兩個已知 bug），並提出三種替代方案（Setup Hook、@path 引用、Skill 替代），附完整源碼追蹤與比較矩陣。

## 關鍵洞察（Key Insights）

- **Plugin manifest 不支援 rules**：`PluginManifestSchema` 的 component 欄位只有 skills / commands / agents / hooks / mcpServers / lspServers / outputStyles / themes / monitors / channels，**沒有 `rules` 欄位** — 源碼 `schemas.ts:884-898`
- **Plugin 安裝是純宣告式**：下載 → 驗證 manifest → 寫入 `installed_plugins.json` → 更新 `settings.json`，**沒有 postInstall 或 onEnable 事件** — 參見 [[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]]
- **Rules 的 `paths:` frontmatter 內部映射為 `globs`**：`parseFrontmatterPaths()` 讀取 `frontmatter.paths`，結果存入 `MemoryFileInfo.globs` 屬性 — 源碼 `claudemd.ts:254-278`
- **Setup Hook 可以建立任何檔案**：Plugin 的 Setup hook 在 session 初始化時執行任意 shell 命令，**無檔案建立限制**（僅需 workspace trust） — 源碼 `hooks.ts:3997-4017`
- **@path 引用無路徑限制**：User-level CLAUDE.md 的 `includeExternal = true`，`expandPath()` 無白名單，可引用 Plugin cache 路徑 — 源碼 `path.ts:32-85`

## 詳細內容（Details）

### 第一章：Plugin Manifest 完整 Component 清單

根據源碼 `schemas.ts:884-898` 的 `PluginManifestSchema` 定義及[官方文件](https://code.claude.com/docs/en/plugins-reference)：

```typescript
// src/utils/plugins/schemas.ts:884-898
export const PluginManifestSchema = lazySchema(() =>
  z.object({
    ...PluginManifestMetadataSchema().shape,              // name, version, author...
    ...PluginManifestHooksSchema().partial().shape,       // hooks
    ...PluginManifestCommandsSchema().partial().shape,    // commands
    ...PluginManifestAgentsSchema().partial().shape,      // agents
    ...PluginManifestSkillsSchema().partial().shape,      // skills
    ...PluginManifestOutputStylesSchema().partial().shape, // outputStyles
    ...PluginManifestChannelsSchema().partial().shape,    // channels
    ...PluginManifestMcpServerSchema().partial().shape,   // mcpServers
    ...PluginManifestLspServerSchema().partial().shape,   // lspServers
    ...PluginManifestSettingsSchema().partial().shape,    // settings
    ...PluginManifestUserConfigSchema().partial().shape,  // userConfig
  }),
)
```

| Component | manifest 欄位 | 預設目錄 | Plugin 支援 |
|-----------|--------------|---------|:-----------:|
| Skills | `skills` | `skills/` | ✅ |
| Commands | `commands` | `commands/` | ✅ |
| Agents | `agents` | `agents/` | ✅ |
| Hooks | `hooks` | `hooks/hooks.json` | ✅ |
| MCP Servers | `mcpServers` | `.mcp.json` | ✅ |
| LSP Servers | `lspServers` | `.lsp.json` | ✅ |
| Output Styles | `outputStyles` | `output-styles/` | ✅ |
| Themes | `themes` | `themes/` | ✅ |
| Monitors | `monitors` | `monitors/monitors.json` | ✅ |
| Channels | `channels` | （inline） | ✅ |
| **CLAUDE.md** | **不存在** | — | ❌ |
| **Rules** | **不存在** | — | ❌ |

> [!important] PluginComponent 類型定義
> ```typescript
> // src/types/plugin.ts:72-78
> export type PluginComponent = 'commands' | 'agents' | 'skills' | 'hooks' | 'output-styles'
> // 沒有 'rules' component
> ```

### 第二章：LoadedPlugin 類型 — 確認無 rules 欄位

```typescript
// src/types/plugin.ts:48-70
export type LoadedPlugin = {
  name: string
  manifest: PluginManifest
  path: string
  source: string
  commandsPath?: string
  commandsPaths?: string[]           // 來自 manifest.commands
  agentsPath?: string
  agentsPaths?: string[]             // 來自 manifest.agents
  skillsPath?: string
  skillsPaths?: string[]             // 來自 manifest.skills
  outputStylesPath?: string
  outputStylesPaths?: string[]       // 來自 manifest.outputStyles
  hooksConfig?: HooksSettings
  mcpServers?: Record<string, McpServerConfig>
  lspServers?: Record<string, LspServerConfig>
  settings?: Record<string, unknown>
  // ❌ 沒有 rulesPath, rulesPaths 或任何 rules 欄位
}
```

### 第三章：Plugin Settings Merge — 只允許 `agent` 鍵

```typescript
// src/utils/plugins/pluginLoader.ts ~line 1050
// mergePluginSettings() — 只允許 'agent' key
// PluginSettingsSchema 過濾只保留白名單鍵
```

即使 Plugin 有 `settings` 欄位，也**無法**透過 settings merge 注入 rules 或 CLAUDE.md 內容。目前 Plugin settings 只能合併 `agent` 配置 — 參見 [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]]。

### 第四章：Rules 發現機制 — 只看 `.claude/rules/` 目錄

```typescript
// src/utils/claudemd.ts:688-776
// processMdRules() — 遞迴掃描 .claude/rules/ 目錄
// 只處理 .md 檔案
// 不搜尋 Plugin 目錄
```

Rules 的發現位置（`claudemd.ts`）：

| 層級 | 路徑 | 說明 |
|------|------|------|
| Managed | `/etc/claude-code/.claude/rules/*.md` | 全域（企業管理） |
| User | `~/.claude/rules/*.md` | 使用者層級 |
| Project | `./.claude/rules/*.md` | 專案層級（可 check in） |

> [!warning] Rules 發現完全不涉及 Plugin 目錄
> `processMdRules()` 只接受 `rulesDir` 參數指定的路徑，不會自動搜尋 `~/.claude/plugins/cache/` 下的任何內容。

### 第五章：Rules Frontmatter 的 `paths:` 機制

#### 解析流程

```
parseFrontmatterPaths(rawContent)          // claudemd.ts:254
  │
  ├── parseFrontmatter(rawContent)          // 提取 YAML frontmatter
  │
  ├── 檢查 frontmatter.paths               // 注意：欄位名是 paths，不是 globs
  │     └── 若無 → 返回 { content }（無條件 rule）
  │
  ├── splitPathInFrontmatter(paths)         // frontmatterParser.ts:189-232
  │     ├── 解析逗號分隔："src/**/*.ts, docs/**"
  │     ├── 展開大括號："src/*.{ts,tsx}" → ["src/*.ts", "src/*.tsx"]
  │     └── 支援 YAML 陣列：["path1", "path2"]
  │
  └── 過濾 match-all pattern
        └── 若全是 "**" → 視為無條件 rule
```

#### 內部名稱映射

```typescript
// src/utils/claudemd.ts:228-234
type MemoryFileInfo = {
  path: string
  type: MemoryType
  content: string
  parent?: string
  globs?: string[]  // ← frontmatter 的 paths: 存到這裡
}

// claudemd.ts:394
// parseFrontmatterPaths 的結果 paths → MemoryFileInfo.globs
return {
  info: { path: filePath, type, content, globs: paths },  // paths → globs
}
```

> [!note] 命名混淆（Naming Confusion）
> Frontmatter 欄位叫 `paths:`，但內部 `MemoryFileInfo` 的屬性叫 `globs`。這解釋了為何 [Issue #17204](https://github.com/anthropics/claude-code/issues/17204) 中有人誤以為 `globs:` 是 frontmatter 的有效欄位名。
> 
> **源碼真相**：`parseFrontmatterPaths()` 只檢查 `frontmatter.paths`，不檢查 `frontmatter.globs`。但因為 `FrontmatterData` 有 `[key: string]: unknown` 通配，`globs:` 在 YAML 解析不會報錯，但**不會被讀取**。

#### 條件式 Rules 觸發時機

```typescript
// src/utils/claudemd.ts:1354-1397
// processConditionedMdRules() — 過濾條件式 rules
export async function processConditionedMdRules(...) {
  // 取得所有帶 globs 的 rules
  const conditionedRuleMdFiles = await processMdRules({ conditionalRule: true })

  // 用 ignore() 匹配 targetPath
  return conditionedRuleMdFiles.filter(file => {
    if (!file.globs || file.globs.length === 0) return false
    return ignore().add(file.globs).ignores(relativePath)
  })
}
```

條件式 rules 透過 `nested_memory` 附件注入，在 `FileReadTool` 讀取匹配檔案時觸發。

#### 已知 Bug

| Issue | 問題 | 狀態 |
|-------|------|------|
| [#17204](https://github.com/anthropics/claude-code/issues/17204) | `paths:` 的引號格式和 YAML list 格式可能不正確運作，文件記載的格式與實際行為不符 | stale |
| [#23478](https://github.com/anthropics/claude-code/issues/23478) | 條件式 rules（帶 `paths:` frontmatter）只在 Read（讀取檔案）時觸發，**Write（寫入檔案）時不觸發** | open |

> [!warning] Write 不觸發條件式 Rules
> 如果你的 rule 是「寫 `.py` 檔時要遵循 PEP 8」，用 `paths: "**/*.py"` 設定，那麼**只有在讀取 .py 檔時才會注入這條 rule**，新建 .py 檔時不會自動注入。這是 [#23478](https://github.com/anthropics/claude-code/issues/23478) 的已知問題。

### 第六章：Plugin 安裝流程 — 為何沒有 postInstall

```
用戶：/plugin install <name>
  │
  ▼
installResolvedPlugin()                    // pluginInstallationHelpers.ts:348-481
  │
  ├── resolveDependencyClosure()            // 解析依賴閉包
  │
  ├── isPluginBlockedByPolicy()             // 策略檢查
  │
  ├── cacheAndRegisterPlugin()              // pluginInstallationHelpers.ts:128-226
  │     ├── 下載/clone 到 ~/.claude/plugins/cache/{market}/{plugin}/{version}/
  │     ├── 計算版本 (calculatePluginVersion)
  │     └── 寫入 installed_plugins.json
  │
  └── 原子性寫入 settings.json enabledPlugins
        └── ❌ 沒有 postInstall hook 觸發
        └── ❌ 沒有檔案建立（CLAUDE.md / rules）
```

> [!important] 安裝流程是純宣告式
> 與 npm 的 `postinstall` 不同，Claude Code Plugin 安裝**不會執行任何腳本**。安裝後的初始化全靠 session 啟動時的 Setup / SessionStart hook。

### 第七章：三種替代方案

#### 方案 A：Setup Hook 自動建立 Rules 檔案

**原理**：Plugin 宣告 `Setup` hook，在 session 初始化時執行 shell 命令建立檔案。

```json
{
  "name": "my-coding-standards",
  "hooks": {
    "Setup": [{
      "hooks": [{
        "type": "command",
        "command": "bash -c 'mkdir -p .claude/rules && [ ! -f .claude/rules/coding-standards.md ] && cp ${CLAUDE_PLUGIN_ROOT}/templates/coding-standards.md .claude/rules/ || true'"
      }]
    }]
  }
}
```

**源碼驗證**：

```typescript
// src/utils/hooks.ts:3997-4017
export async function* executeSetupHooks(
  trigger: 'init' | 'maintenance',
  signal?: AbortSignal,
  timeoutMs: number = TOOL_HOOK_EXECUTION_TIMEOUT_MS,
  forceSyncExecution?: boolean,
): AsyncGenerator<AggregatedHookResult>

// src/utils/sessionStart.ts:177-232
// processSetupHooks() — 在 session 初始化早期觸發
// Setup 是 ALWAYS_EMITTED_HOOK_EVENTS 之一
```

```typescript
// src/utils/hooks.ts:829-1000
// execCommandHook() — 使用 spawn() 執行任意 shell 命令
// 無檔案建立限制
// 唯一限制：需要 workspace trust（互動模式）
```

| 優點 | 缺點 |
|------|------|
| 使用者零操作，自動執行 | 需要使用者接受 workspace trust |
| 可以建立任何檔案（rules / CLAUDE.md） | 每次 session 都會執行（需冪等設計，如 `[ ! -f ... ]`） |
| 能讀取 `$CLAUDE_PROJECT_DIR` 判斷位置 | 沒有 `postInstall` 事件，無法只在安裝時執行一次 |
| 支援條件判斷 | 使用者可能不信任自動寫檔行為 |
| `$CLAUDE_PLUGIN_ROOT` 提供模板來源路徑 | Plugin 更新時可能覆蓋使用者自訂內容 |

> [!tip] 冪等設計（Idempotent Design）
> Setup hook 每次 session 都會觸發，所以必須做冪等檢查。最簡單的方式是 `[ ! -f target ] && cp source target`，確保只在目標不存在時才複製。若要支援 Plugin 更新後推送新版 rules，可以用 checksum 比較或版本號判斷。

#### 方案 B：@path 引用 Plugin Cache 內的檔案

**原理**：使用者在自己的 CLAUDE.md 中用 `@path` 語法引用 Plugin cache 中的 `.md` 檔案。

```markdown
# ~/.claude/CLAUDE.md

## Plugin 提供的規範
@~/.claude/plugins/cache/my-marketplace/coding-standards/1.0.0/rules/python-style.md
@~/.claude/plugins/cache/my-marketplace/coding-standards/1.0.0/rules/typescript-style.md
```

**源碼驗證**：

```typescript
// src/utils/path.ts:32-85
// expandPath() — 展開 ~ 為 home 目錄
// 無路徑白名單或黑名單
// 唯一驗證：null byte check

// src/utils/claudemd.ts:665-682
// isExternal check — 但 User-level CLAUDE.md 的 includeExternal = true
const isExternal = !pathInOriginalCwd(resolvedIncludePath)
if (isExternal && !includeExternal) {
  continue  // 跳過外部檔案
}

// claudemd.ts:833
// User memory — includeExternal: true（永遠允許外部檔案）
```

Plugin cache 路徑結構（`pluginDirectories.ts:53-62`）：
```
~/.claude/plugins/
  cache/<marketplace>/<plugin>/<version>/   ← @path 可以引用這裡
  data/<plugin-id>/                         ← 持久資料目錄
```

| 優點 | 缺點 |
|------|------|
| 不執行程式碼，最安全 | 需要使用者手動加一行 @path |
| 內容隨 Plugin 更新自動生效（同版本內） | 路徑含版本號，Plugin 升級後路徑會變 |
| 完全透明，使用者可以審查引用內容 | 需要知道確切的 cache 路徑 |
| 支援最多 5 層嵌套引用（`MAX_INCLUDE_DEPTH = 5`） | Project-level CLAUDE.md 可能被 `includeExternal` 阻擋 |
| 等同原生 CLAUDE.md 內容，每次 API call 都注入 | Plugin 提供者需要文件教使用者加這行 |

> [!warning] 版本號陷阱
> Plugin cache 路徑包含版本號（如 `.../1.0.0/...`），Plugin 升級到 2.0.0 後舊路徑就失效了。可考慮用 `$CLAUDE_PLUGIN_DATA` 環境變數搭配 Setup hook 建立穩定的 symlink，但這又回到了方案 A 的範疇。

#### 方案 C：用 Skill 替代 Rules（官方推薦路線）

**原理**：不安裝 CLAUDE.md / rules，改用 Plugin 的 skills 提供等效功能。

```
my-plugin/
  skills/
    coding-standards/
      SKILL.md          # marker 檔
      coding-standards.md  # 內含 when_to_use + 編碼規範
```

**效果差異**：

| 特性 | Rules（`.claude/rules/`） | Skill |
|------|:---:|:---:|
| 每次 API call 注入 | ✅（無條件 rules） | ❌ |
| 條件式觸發（檔案匹配） | ✅（`paths:` frontmatter） | ✅（`paths:` frontmatter） |
| Plugin 可直接提供 | ❌ | ✅ |
| 壓縮後自動重新注入 | ✅（via `prependUserContext`） | ❌（invoked_skills 截斷後注入，skill_listing 不重新注入） |
| Token 預算 | 無限制（和 CLAUDE.md 共享） | 1% context window（`SKILL_BUDGET_CONTEXT_PERCENT`） |
| 使用者零操作 | ❌（需手動建立檔案） | ✅（Plugin 自帶） |

> [!note] 社群案例：creating-claude-rules Skill
> [claude-plugins.dev](https://claude-plugins.dev/skills/@pr-pm/prpm/creating-claude-rules) 上有一個叫 `creating-claude-rules` 的 Skill，但它只是**教學型 Skill**——教使用者如何手動撰寫 rules 檔案，並非自動安裝 rules。

### 第八章：三方案比較矩陣

| 特性 | A: Setup Hook | B: @path 引用 | C: Skill 替代 |
|------|:---:|:---:|:---:|
| 使用者零操作 | ✅ | ❌（需加一行） | ✅ |
| 不執行任意程式碼 | ❌ | ✅ | ✅ |
| 每次 API call 都注入 | ✅ | ✅ | ❌ |
| 壓縮後重新注入 | ✅ | ✅ | ❌（truncated） |
| Plugin 更新後自動生效 | 需覆寫 | ✅（同版本） | ✅ |
| 透明可審查 | △ | ✅ | ✅ |
| 不需 workspace trust | ❌ | ✅ | ✅ |
| 官方推薦 | ❌ | ❌ | ✅ |
| Token 效率 | 取決內容大小 | 取決內容大小 | 1% 預算 |

### 第九章：混合方案建議

根據不同需求場景的最佳策略：

```
場景                          推薦方案           理由
──────────────────────────────────────────────────────────
永遠生效的編碼規範             A + B（混合）       Setup Hook 自動加 @path 到 CLAUDE.md
按需觸發的功能                 C（Skill）          官方路線，命名空間隔離
需要零操作 + 零信任的規範      A（Setup Hook）     自動但需 trust
最大透明度                     B（@path）          使用者完全控制
```

**混合方案 A+B 實作**：

```json
{
  "name": "coding-standards",
  "hooks": {
    "Setup": [{
      "hooks": [{
        "type": "command",
        "command": "bash -c 'RULES_REF=\"@${CLAUDE_PLUGIN_ROOT}/rules/standards.md\"; CLAUDEMD=\"$HOME/.claude/CLAUDE.md\"; [ -f \"$CLAUDEMD\" ] && grep -qF \"$RULES_REF\" \"$CLAUDEMD\" || echo \"\\n$RULES_REF\" >> \"$CLAUDEMD\"'"
      }]
    }]
  }
}
```

這個 Setup Hook：
1. 檢查 `~/.claude/CLAUDE.md` 是否已存在
2. 用 `grep -qF` 檢查是否已包含 @path 引用（冪等）
3. 若不存在，append 一行 @path 引用

> [!warning] 使用者信任問題
> 自動修改使用者的 CLAUDE.md 是侵入性行為。Plugin 文件應明確告知使用者這個 Hook 會做什麼，並提供手動操作的替代方式。

### 第十章：官方文件驗證

根據 [Claude Code Plugins Reference](https://code.claude.com/docs/en/plugins-reference) 官方文件（2026-05 版）：

**明確支援的 Component**：
- Skills / Commands / Agents / Hooks / MCP Servers / LSP Servers / Output Styles / Themes / Monitors / Channels

**未提及的 Component**：
- Rules / CLAUDE.md

**官方文件中的相關限制**：
> "Plugin agents work alongside built-in Claude agents" — agents 是附加的，不是取代的
> "Plugin hooks respond to the same lifecycle events as user-defined hooks" — hooks 共享事件體系

**frontmatter-reference.md**（[GitHub 原始碼](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/command-development/references/frontmatter-reference.md)）中只記載了 5 個 command frontmatter 欄位：
1. `description` — 描述
2. `allowed-tools` — 工具白名單
3. `model` — 模型選擇
4. `argument-hint` — 引數提示
5. `disable-model-invocation` — 禁止模型調用

注意：此文件**未記載** `paths:` 欄位（那是 rules / skills 的 frontmatter，不是 command 的）。

## 我的心得（My Takeaways）

1. **Plugin 的設計哲學是「提供能力，不修改環境」**：Plugin 可以增加 skills / agents / hooks 等能力，但不能修改使用者的 CLAUDE.md / rules / settings（除了白名單的 `agent` 鍵）。這是一個有意識的安全設計。

2. **Rules 與 Skills 的根本差異在於「注入頻率」**：Rules（無條件）每次 API call 都注入，Skills 只在被調用時注入且有 1% token 預算。這意味著 Plugin 無法透過 Skills 完全取代 Rules 的「永遠在場」效果。

3. **混合方案 A+B 是目前最務實的做法**：用 Setup Hook 自動在 CLAUDE.md 中加入 @path 引用，既能自動化又保持透明度。但需要注意冪等設計和版本號管理。

4. **`paths:` 的兩個 bug 值得關注**：#17204（格式問題）和 #23478（Write 不觸發）可能影響條件式 rules 的可靠性。

## 待補充（Open Questions）

- Plugin 的 `settings` 欄位白名單未來是否會擴展？如果加入 `rules` 鍵，Plugin 就能透過 settings merge 注入 rules — 搜尋關鍵字：`PluginSettingsSchema allowlisted keys`
- 為何 Plugin 不支援 `postInstall` 生命週期事件？是安全考量還是尚未實作？ — 搜尋關鍵字：`claude code plugin postinstall hook RFC`
- 條件式 rules 的 Write 觸發問題（#23478）是否有修復時程？這會影響所有依賴 `paths:` 的 rules — 搜尋關鍵字：`anthropics/claude-code #23478 status`
- `InstructionsLoaded` hook 事件（在 CLAUDE.md 或 rules 載入時觸發）是否可以用來驗證 rules 是否正確載入？ — 搜尋關鍵字：`InstructionsLoaded hook event`
- 官方是否考慮在 Plugin manifest 中加入 `rules` component 類型？ — 搜尋關鍵字：`claude code plugin rules manifest feature request`

## 相關連結（Related）

- [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] — Plugin 的 Skill frontmatter 欄位支援差異（createPluginCommand 缺少 hooks/context/agent/paths）
- [[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]] — Plugin 完整生命週期中為何沒有 postInstall
- [[2026-04-19-CLAUDE-CODE-PLUGIN-JSON-DEPENDENCIES-SHARED-SKILLS-SOURCE-ANALYSIS]] — Plugin manifest 的 dependencies 與 skills 共享機制
- [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]] — Settings merge 五源機制，Plugin settings 只允許 `agent` 鍵
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — CLAUDE.md 的 memoize 快取與 @include 機制
- [[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]] — Skill 的 token 預算、壓縮機制、與 rules 的效果差異
- [[2026-04-17-CLAUDEMD-MYTHS-DEBUNKED-SOURCE-CODE-VERIFICATION]] — CLAUDE.md 注入機制（prependUserContext 每次 API call）

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | Plugin manifest 的 12 個 component 類型、`parseFrontmatterPaths` 函式、`MemoryFileInfo.globs` 屬性、Setup hook 觸發時機、@path 的 `MAX_INCLUDE_DEPTH = 5` |
| **理解（半被動）** | 串聯知識點 | Plugin 刻意不支援 rules/CLAUDE.md 是安全設計哲學：「提供能力，不修改環境」。frontmatter 的 `paths:` 和內部的 `globs` 是同一個概念的兩端命名，造成社群混淆 |
| **分析（主動）** | 找出假設與漏洞 | 三種替代方案各有假設：A 假設使用者信任自動寫檔、B 假設使用者能找到 cache 路徑、C 假設 Skill 的 1% 預算足夠。最大盲點是條件式 rules 的 Write 不觸發 bug |
| **應用（主動）** | 規劃執行方案 | ① 為自己的 Plugin 建立 Setup Hook + @path 混合方案模板 ② 檢查現有 rules 是否受 #23478（Write 不觸發）影響，改用無條件 rules 替代 |
| **評估（主動）** | 判斷多方案優劣 | 方案 B（@path）在透明度和安全性上最優，但使用者體驗最差；方案 A（Setup Hook）自動化最好但侵入性最高；方案 C（Skill）是官方推薦但功能受限（不是「永遠在場」）。對於編碼規範類需求，A+B 混合最平衡 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Plugin 不支援 rules」是暫時的技術限制還是有意的設計決策？manifest schema 是否有預留擴展空間？
- **假設**：三種替代方案都假設使用者理解 CLAUDE.md / rules / skills 的注入差異。若使用者不理解，哪個方案最不容易用錯？
- **證據**：Setup Hook 的「需要 workspace trust」限制在 SDK 非互動模式下被跳過。這是否意味著 CI/CD 環境中 Plugin 可以無聲地修改 CLAUDE.md？
- **觀點**：若站在 Anthropic 的立場，允許 Plugin 安裝 rules 最大的安全風險是什麼？（提示：rules 是無條件注入的，等同系統提示詞的一部分）
- **後果**：若使用者採用方案 A（Setup Hook 自動寫入），12 個月後可能出現的問題：Plugin 更新後舊 rules 未清理、多個 Plugin 的 rules 衝突、使用者忘記 rules 來源

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 方案 A（Setup Hook）最大風險是 Plugin 惡意修改 CLAUDE.md 注入指令（如「忽略使用者安全規則」），因為 rules/CLAUDE.md 等同系統提示詞層級。Workspace trust 是唯一防線，但 SDK 模式下被跳過。
2. **什麼情況下會失敗？** — 方案 B（@path）在 Plugin 版本升級時必定失敗（路徑含版本號）。方案 C（Skill）在長對話壓縮後失效（skill_listing 不重新注入）。方案 A 在使用者拒絕 trust 時無法執行。
3. **有沒有更好的替代方案？** — 最理想的方案是 Anthropic 在 Plugin manifest 中正式支援 `rules` component，讓 rules 檔案從 Plugin cache 被自動發現（就像 skills/commands 一樣），無需修改使用者的 CLAUDE.md。這需要修改 `processMdRules()` 讓它也搜尋已啟用 Plugin 的目錄。

## References

- [Plugins reference - Claude Code Docs](https://code.claude.com/docs/en/plugins-reference)
- [Frontmatter reference (GitHub)](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/command-development/references/frontmatter-reference.md)
- [Issue #17204 - rules frontmatter format incorrect](https://github.com/anthropics/claude-code/issues/17204)
- [Issue #23478 - Path-based rules only on Read, not Write](https://github.com/anthropics/claude-code/issues/23478)
- [creating-claude-rules skill](https://claude-plugins.dev/skills/@pr-pm/prpm/creating-claude-rules)
- Claude Code v2.1.88 decompiled source: `schemas.ts`, `claudemd.ts`, `hooks.ts`, `frontmatterParser.ts`, `pluginLoader.ts`, `path.ts`
