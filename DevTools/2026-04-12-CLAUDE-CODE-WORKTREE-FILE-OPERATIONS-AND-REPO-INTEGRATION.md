---
title: "Claude Code Worktree 檔案操作全解析：從原始碼追蹤新增/修改/讀取，到 repo Multi-Repo 整合實戰"
date: 2026-04-12
date_uncertain: true
category: DevTools
tags:
  - "#tools/claude-code"
  - "#git/worktree"
  - "#tools/repo"
  - "#devtools/multi-repo"
  - "#devtools/parallel-development"
source: "對話研究：Claude Code 原始碼分析"
source_type: article
author: "swchen"
status: notes
links:
  - "[[2026-03-31-REPO-MULTI-REPO-MANAGEMENT-AND-GIT-WORKTREE-ADVANCED-GUIDE]]"
  - "[[2026-03-31-CLAUDE-CODE-WORKTREE-X-REPO-MULTI-REPO-PARALLEL-DEVELOPMENT]]"
  - "[[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]]"
---

## 摘要（Summary）

本文從**檔案系統操作**的角度，完整追蹤 Claude Code worktree 功能在建立、使用、清理各階段「新增了什麼檔案」「修改了什麼設定」「讀取了什麼資料」。接著探討如何在 Android `repo`（Multi-Repo）環境中整合 worktree，搭配 Gerrit topic 進行跨 repo 並行開發。所有分析均基於 Claude Code 反編譯原始碼 `src/utils/worktree.ts`（1170+ 行）的逐行閱讀。

> [!important] 前置閱讀
> 本文是以下兩篇的**第三篇續集**，建議先閱讀基礎概念：
> - [[2026-03-31-REPO-MULTI-REPO-MANAGEMENT-AND-GIT-WORKTREE-ADVANCED-GUIDE]] — repo 三層儲存架構 + git worktree 原理
> - [[2026-03-31-CLAUDE-CODE-WORKTREE-X-REPO-MULTI-REPO-PARALLEL-DEVELOPMENT]] — Claude Code worktree × repo 並行開發指南

---

## 關鍵洞察（Key Insights）

- **建立一個 worktree 會觸碰 7 種以上的檔案操作**：從 `mkdir` 到 `symlink` 到 `copyFile` 到 `git config`，遠比想像中複雜
- **稀疏檢出（sparse checkout）是大型 monorepo 的關鍵加速器** — 透過 `--no-checkout` + `sparse-checkout set --cone` 避免全量 checkout
- **`.worktreeinclude` 機制**解決了「gitignored 但 worktree 需要」的檔案傳遞問題，使用 `ignore` 函式庫實現 `.gitignore` 語法匹配
- **Symlink 策略**避免 `node_modules` 等大目錄在 worktree 中重複佔磁碟
- **repo 工具沒有內建 worktree 支援**，必須透過 `repo forall -c 'git worktree ...'` 間接操作
- **Hooks 擴展（WorktreeCreate / WorktreeRemove）**讓非 Git VCS 也能使用 worktree 功能

---

## 第一部分：檔案操作完整追蹤

### 1.1 目錄結構總覽

```
<git-root>/
├── .claude/
│   └── worktrees/
│       └── <flattened-slug>/           ← worktree 工作目錄
│           ├── .git                     ← git worktree 指標檔（非目錄）
│           ├── .claude/
│           │   └── settings.local.json  ← 從主 repo 複製
│           ├── node_modules → <git-root>/node_modules  ← symlink
│           ├── .cache → <git-root>/.cache              ← symlink
│           └── (sparse checkout 或完整 checkout 的檔案)
├── .git/
│   ├── config                           ← core.hooksPath 被修改
│   └── worktrees/
│       └── <flattened-slug>/            ← git 內部 worktree 中繼資料
│           ├── HEAD
│           ├── ORIG_HEAD
│           ├── commondir
│           ├── gitdir
│           └── index
├── .worktreeinclude                     ← 使用者自訂，控制哪些 gitignored 檔案要複製
└── .husky/                              ← hooks 來源（若存在）
```

> [!note] Slug 扁平化規則（Slug Flattening）
> `user/feature` → `user+feature`（`/` 替換為 `+`）。原因是避免 git ref D/F 衝突（`worktree-user` 檔 vs `worktree-user/feature` 目錄），以及防止巢狀 worktree 被父 worktree 刪除時連帶清除。
> 原始碼：`src/utils/worktree.ts:208-219`

### 1.2 建立階段 — 檔案操作明細

以下按執行順序列出每一步的檔案操作，標注**新增（C）、修改（M）、讀取（R）**：

#### 步驟 1：驗證與準備

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 讀取 .git 指標檔 | R | `<worktree>/.git` | `worktree.ts:247` `readWorktreeHeadSha()` |
| 建立 worktrees 目錄 | C | `<git-root>/.claude/worktrees/` | `worktree.ts:258` `mkdir(recursive)` |

```typescript
// Fast resume path: 讀取 .git 指標檔判斷 worktree 是否已存在
const existingHead = await readWorktreeHeadSha(worktreePath)
if (existingHead) {
  return { worktreePath, worktreeBranch, headCommit: existingHead, existed: true }
}
```

#### 步驟 2：Fetch 遠端分支

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 讀取 git 設定 | R | `.git/config`, `.git/packed-refs` | `worktree.ts:284-292` |
| 讀取 ref | R | `.git/refs/remotes/origin/<branch>` | `worktree.ts:290` `resolveRef()` |
| 網路 fetch（條件式） | M | `.git/objects/`, `.git/FETCH_HEAD` | `worktree.ts:296-301` |

> [!tip] 效能優化
> 若 `origin/<branch>` 已存在本地，直接用 `resolveRef()` 讀取 SHA，**跳過 fetch**。在大型 repo（21 萬檔案、1600 萬物件）中，這省下了 6-8 秒的 commit-graph 掃描時間。
> 原始碼：`worktree.ts:278-293`

#### 步驟 3：建立 Git Worktree

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 建立 worktree 目錄 | C | `<git-root>/.claude/worktrees/<slug>/` | `worktree.ts:328` |
| 建立 .git 指標檔 | C | `<worktree>/.git`（內容為 `gitdir: ../../.git/worktrees/<slug>`） | git 自動建立 |
| 建立 worktree 中繼資料 | C | `.git/worktrees/<slug>/HEAD`, `commondir`, `gitdir`, `index` | git 自動建立 |
| 建立/重設分支 | M | `.git/refs/heads/worktree-<slug>` | `worktree.ts:328` `-B` flag |

```bash
# 實際執行的 git 指令
git worktree add -B worktree-<slug> <path> origin/<default-branch>
# -B（非 -b）：強制重設孤兒分支，省去先 git branch -D 再建立的開銷
```

#### 步驟 4：稀疏檢出（Sparse Checkout，選用）

僅當 `settings.worktree.sparsePaths` 有設定時觸發：

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 建立 sparse-checkout 設定 | C | `<worktree>/.git/info/sparse-checkout` | `worktree.ts:349-354` |
| 修改 git config | M | `.git/worktrees/<slug>/config` | git 自動 |
| checkout 檔案 | C | `<worktree>/` 下指定路徑的檔案 | `worktree.ts:358-362` |

```bash
git sparse-checkout set --cone -- frameworks/base packages/apps/Settings
git checkout HEAD
```

> [!warning] 失敗回滾
> 若 sparse-checkout 或 checkout 失敗，會立即 `git worktree remove --force` 清除半成品，防止下次 resume 時誤判為有效 worktree。
> 原始碼：`worktree.ts:341-348`

#### 步驟 5：後置設定（Post-Creation Setup）

這是檔案操作最密集的階段：

**5a. 複製 settings.local.json**

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 讀取來源 | R | `<git-root>/.claude/settings.local.json` | `worktree.ts:518` |
| 建立目標目錄 | C | `<worktree>/.claude/` | `worktree.ts:521` |
| 複製檔案 | C | `<worktree>/.claude/settings.local.json` | `worktree.ts:522` `copyFile()` |

**5b. 設定 Git Hooks 路徑**

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 檢查 hooks 目錄 | R | `<git-root>/.husky/`、`<git-root>/.git/hooks/` | `worktree.ts:538-551` |
| 讀取現有 config | R | `.git/config`（`core.hooksPath`） | `worktree.ts:558-559` |
| 修改 git config | M | `.git/config`（`core.hooksPath = <主 repo hooks 路徑>`） | `worktree.ts:562-567` |

```typescript
// 只在值不同時才寫入，省去 ~14ms 的 subprocess 開銷
if (existing !== hooksPath) {
  await execFileNoThrowWithCwd(gitExe(),
    ['config', 'core.hooksPath', hooksPath],
    { cwd: worktreePath })
}
```

> [!warning] Husky 會覆蓋 core.hooksPath
> Husky 的 prepare 腳本（`git config core.hooksPath .husky`）會在每次 `bun install` 時將共用的 `.git/config` 值重設為相對路徑，導致各 worktree 指向自己的 `.husky/`。
> 原始碼：`worktree.ts:590-596`

**5c. 建立 Symlinks**

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 讀取設定 | R | `settings.worktree.symlinkDirectories` | `worktree.ts:581-582` |
| 建立 symlink | C | `<worktree>/node_modules` → `<git-root>/node_modules` | `worktree.ts:121` `symlink()` |
| 路徑安全檢查 | R | 驗證無路徑穿越（path traversal） | `worktree.ts:109` |

```typescript
// 安全：驗證目錄名不包含 .. 等路徑穿越
if (containsPathTraversal(dir)) {
  logForDebugging(`Skipping symlink for "${dir}": path traversal detected`)
  continue
}
await symlink(sourcePath, destPath, 'dir')
```

**5d. 複製 .worktreeinclude 檔案**

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 讀取 .worktreeinclude | R | `<git-root>/.worktreeinclude` | `worktree.ts:397` |
| 列出 gitignored 檔案 | R | `git ls-files --others --ignored --exclude-standard --directory` | `worktree.ts:413-417` |
| 模式匹配 | R | 用 `ignore` 函式庫比對 patterns | `worktree.ts:423-428` |
| 展開折疊目錄（條件式） | R | `git ls-files --others --ignored --exclude-standard -- <dirs>` | `worktree.ts:460-471` |
| 複製匹配檔案 | C | `<worktree>/<matched-file>` | `worktree.ts:482-495` |

```
效能說明：
--directory flag 將完全 gitignored 的目錄折疊為單一項（如 node_modules/）
在大型 repo 中：~500k 項 / ~7s → ~數百項 / ~100ms
```

### 1.3 使用階段 — 檔案操作明細

#### Session 中切換到 Worktree（EnterWorktreeTool）

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 讀取 canonical git root | R | `.git/`（向上搜尋） | `EnterWorktreeTool.ts:84` |
| 儲存 worktree 狀態 | M | project config（session storage） | `EnterWorktreeTool.ts:97` |
| 清除記憶快取 | M | 記憶體中的 CLAUDE.md / memory 快取 | `EnterWorktreeTool.ts:101` |
| 清除 system prompt 快取 | M | 記憶體中的 system prompt sections | `EnterWorktreeTool.ts:99` |

```typescript
// EnterWorktreeTool.ts:77-119 執行流程
const mainRepoRoot = findCanonicalGitRoot(getCwd())
const worktreeSession = await createWorktreeForSession(getSessionId(), slug)
process.chdir(worktreeSession.worktreePath)
setCwd(worktreeSession.worktreePath)
saveWorktreeState(worktreeSession)
clearSystemPromptSections()
clearMemoryFileCaches()
```

#### Sub-agent Worktree（createAgentWorktree）

| 操作 | 類型 | 差異 | 原始碼位置 |
|------|------|------|-----------|
| 不修改全域狀態 | — | 不呼叫 `process.chdir`、不改 `currentWorktreeSession` | `worktree.ts:896-952` |
| 更新 mtime（resume 時） | M | `utimes(worktreePath, now, now)` 防止被清理 | `worktree.ts:946-947` |
| 使用 canonical root | R | `findCanonicalGitRoot`（非 `findGitRoot`）確保在主 repo 下建立 | `worktree.ts:926` |

### 1.4 清理階段 — 檔案操作明細

#### 手動退出（ExitWorktreeTool — remove 模式）

| 操作 | 類型 | 檔案 / 路徑 | 原始碼位置 |
|------|------|------------|-----------|
| 檢查未提交變更 | R | `git status --porcelain` | `ExitWorktreeTool.ts:174-224` |
| 檢查未推送 commit | R | `git rev-list --count <baseline>..HEAD` | `ExitWorktreeTool.ts` |
| 刪除 worktree 目錄 | D | `<git-root>/.claude/worktrees/<slug>/`（整個目錄） | `worktree.ts:843-845` |
| 刪除 worktree 中繼資料 | D | `.git/worktrees/<slug>/` | git 自動清理 |
| 刪除暫時分支 | D | `.git/refs/heads/worktree-<slug>` | `worktree.ts:871-876` |
| 清除 session 狀態 | M | project config | `worktree.ts:861-864` |

```typescript
// cleanupWorktree() 完整流程
process.chdir(originalCwd)
await execFileNoThrowWithCwd(gitExe(),
  ['worktree', 'remove', '--force', worktreePath], { cwd: originalCwd })
currentWorktreeSession = null
saveCurrentProjectConfig(current => ({ ...current, activeWorktreeSession: undefined }))
await sleep(100)  // 等 git 釋放鎖
await execFileNoThrowWithCwd(gitExe(), ['branch', '-D', worktreeBranch], { cwd: originalCwd })
```

#### 自動清理（Stale Worktree Cleanup）

| 操作 | 類型 | 條件 | 原始碼位置 |
|------|------|------|-----------|
| 掃描 worktrees 目錄 | R | 每 30 天自動執行 | `worktree.ts:1058-1136` |
| 匹配 ephemeral patterns | R | 只清理 `agent-a*`、`wf_*`、`bridge-*`、`job-*` | `worktree.ts:1030-1041` |
| 安全檢查：tracked changes | R | `git status --porcelain -uno` 必須為空 | fail-closed |
| 安全檢查：unpushed commits | R | `git rev-list --max-count=1 HEAD --not --remotes` 必須為空 | fail-closed |
| 刪除 worktree | D | `git worktree remove --force` | 通過安全檢查後 |
| 修剪中繼資料 | D | `git worktree prune` | 最後執行一次 |

Ephemeral 模式匹配規則：
```
/^agent-a[0-9a-f]{7}$/          — AgentTool worktrees
/^wf_[0-9a-f]{8}-[0-9a-f]{3}-\d+$/  — WorkflowTool worktrees
/^bridge-[A-Za-z0-9_]+(-[A-Za-z0-9_]+)*$/  — Bridge worktrees
/^job-[a-zA-Z0-9._-]{1,55}-[0-9a-f]{8}$/   — Template job worktrees
```

### 1.5 檔案操作總整理表

| 階段 | 新增（C） | 修改（M） | 讀取（R） | 刪除（D） |
|------|---------|---------|---------|---------|
| **建立** | worktree 目錄、`.git` 指標檔、worktree 中繼資料、分支 ref、`settings.local.json`、symlinks、`.worktreeinclude` 匹配檔案 | `.git/config`（hooksPath）、`.git/refs/heads/`（分支） | `.git` 指標檔、git config、remote refs、`.worktreeinclude`、gitignored 檔案列表 | — |
| **使用** | — | project config（session storage）、記憶體快取 | canonical git root、worktree 狀態 | — |
| **清理** | — | project config | `git status`、`git rev-list`、worktrees 目錄掃描 | worktree 目錄、中繼資料、暫時分支 |

---

## 第二部分：三種 Worktree 模式比較

### 模式比較表

| 面向 | 啟動時（`--worktree`） | 中途進入（EnterWorktree） | Sub-agent（`isolation: "worktree"`） |
|------|----------------------|--------------------------|--------------------------------------|
| **觸發方式** | CLI flag | Tool call | Agent 定義中的 `isolation` 參數 |
| **入口程式碼** | `src/setup.ts:174-285` | `EnterWorktreeTool.ts:77-119` | `worktree.ts:902-952` |
| **改 `projectRoot`** | ✅ 是 | ❌ 否 | ❌ 否 |
| **改 `process.chdir`** | ✅ 是 | ✅ 是 | ❌ 否 |
| **改全域 session** | ✅ 是 | ✅ 是 | ❌ 否 |
| **tmux 支援** | ✅（`--tmux`） | ❌ 否 | ❌ 否 |
| **生命週期** | 整個 session | 到 ExitWorktree 或 session 結束 | agent 執行期間 |
| **自動清理** | session 結束時提示 | ExitWorktree 或 session 結束時 | agent 結束時自動清理 |

### WorktreeSession 資料結構

```typescript
type WorktreeSession = {
  originalCwd: string           // 進入前的工作目錄
  worktreePath: string          // worktree 路徑
  worktreeName: string          // slug 名稱
  worktreeBranch?: string       // 暫時分支名（worktree-<slug>）
  originalBranch?: string       // 進入前的分支
  originalHeadCommit?: string   // 基準 commit（用於計算 commit 數）
  sessionId: string
  tmuxSessionName?: string
  hookBased?: boolean           // 是否用 hooks 建立（非 git）
  creationDurationMs?: number   // 建立耗時（resume 時為 unset）
  usedSparsePaths?: boolean     // 是否使用了 sparse checkout
}
```

---

## 第三部分：設定參考

### settings.json 中的 worktree 設定

```json
{
  "worktree": {
    "symlinkDirectories": ["node_modules", ".cache", ".bin"],
    "sparsePaths": ["frameworks/base", "packages/apps/Settings"]
  }
}
```

| 設定項 | 類型 | 說明 |
|--------|------|------|
| `symlinkDirectories` | `string[]` | 要以 symlink 取代複製的目錄列表，避免磁碟浪費 |
| `sparsePaths` | `string[]` | 稀疏檢出的目錄列表，大型 monorepo 必備 |

### .worktreeinclude 檔案

放在 git root，語法同 `.gitignore`：

```
# 複製 API 金鑰設定到 worktree
config/secrets/api.key

# 複製所有 .env 檔案
**/.env
**/.env.local

# 複製建構快取的特定檔案
.turbo/cache/manifest.json
```

### Hooks 擴展

```json
{
  "hooks": {
    "WorktreeCreate": [{
      "command": "bash scripts/worktree-create.sh"
    }],
    "WorktreeRemove": [{
      "command": "bash scripts/worktree-remove.sh"
    }]
  }
}
```

- **WorktreeCreate**: 輸入 `{ slug }` → 輸出 `{ worktreePath }`
- **WorktreeRemove**: 輸入 `{ worktreePath }` → 回傳 `boolean`

---

## 第四部分：結合 repo (Multi-Repo) 開發

### 4.1 repo 工具的 Worktree 現狀

> [!warning] 關鍵事實
> **repo 沒有內建 worktree 支援。** 必須透過 `repo forall` 間接操作 `git worktree`。

| 面向 | `repo --reference` | `repo forall` + `git worktree` | Claude Code worktree |
|------|--------------------|---------------------------------|---------------------|
| repo 指令可用 | ✅ 完全可用 | ❌ secondary 不可用 | ❌ 單一 git repo |
| 磁碟共享 | object store | `.git` 目錄 | `.git` + symlinks |
| 建立速度 | 慢（需 sync） | 快（秒級） | 快 + sparse checkout |
| 適合場景 | 長期多分支開發 | 臨時 hotfix / review | AI agent 隔離執行 |
| Gerrit 推送 | ✅ `repo upload` | ✅ `git push refs/for/` | ✅ 透過 BashTool |

### 4.2 `repo forall` 環境變數

```bash
repo forall -c '
  echo "REPO_PROJECT=$REPO_PROJECT"   # 專案名（如 platform/frameworks/base）
  echo "REPO_PATH=$REPO_PATH"         # 相對路徑
  echo "REPO_REMOTE=$REPO_REMOTE"     # remote 名稱
  echo "REPO_LREV=$REPO_LREV"         # 本地 revision（commit SHA）
  echo "REPO_RREV=$REPO_RREV"         # 遠端 revision（分支名）
'
```

### 4.3 整合方案架構

```
┌──────────────────────────────────────────────────────────┐
│                    開發者工作站                            │
│                                                          │
│  ┌─────────────────────┐  ┌─────────────────────────┐   │
│  │  主工作區（repo sync）│  │  Worktree 工作區        │   │
│  │  ~/aosp-main/        │  │  /tmp/hotfix/           │   │
│  │                      │  │                          │   │
│  │  frameworks/base/ ───┼──┼─► frameworks/base/      │   │
│  │  packages/apps/   ───┼──┼─► packages/apps/        │   │
│  │  .repo/              │  │  （無 .repo，不受 repo   │   │
│  │                      │  │   管理）                  │   │
│  └─────────────────────┘  └────────────┬────────────┘   │
│                                         │                │
│  ┌──────────────────────────────────────▼──────────────┐ │
│  │  Claude Code Session（--worktree 或 EnterWorktree） │ │
│  │  在 worktree 中獨立工作                               │ │
│  │  可透過 BashTool 執行 git push refs/for/             │ │
│  └──────────────────────────────────────┬──────────────┘ │
│                                         │                │
└─────────────────────────────────────────┼────────────────┘
                                          │
                                          ▼
                                   ┌────────────┐
                                   │   Gerrit    │
                                   │  (topic=X)  │
                                   └────────────┘
```

### 4.4 實戰範例

#### 範例 1：緊急 Hotfix（不中斷主開發）

```bash
# 主工作區正在開發 feature-A，需要同時修 hotfix
cd ~/aosp-main

# 為需要修改的 repo 建立 worktree
repo forall platform/frameworks/base packages/apps/Settings -c '
  git worktree add /tmp/hotfix/$REPO_PATH hotfix-branch
'

# 在 worktree 中修改
cd /tmp/hotfix/frameworks/base
# ... 修改程式碼 ...
git add -A && git commit -m "Fix critical ANR in SystemServer"

# 用 Gerrit 推送 review（在 worktree 中直接推）
git push origin HEAD:refs/for/main%topic=hotfix-anr

# 同樣處理 Settings
cd /tmp/hotfix/packages/apps/Settings
git push origin HEAD:refs/for/main%topic=hotfix-anr

# 修完後清理
cd ~/aosp-main
repo forall platform/frameworks/base packages/apps/Settings -c '
  git worktree remove /tmp/hotfix/$REPO_PATH
'
```

#### 範例 2：用 Gerrit Topic 關聯跨 repo 變更

```bash
TOPIC="feature-new-camera"
BRANCH="dev/camera-v2"

# 批量建立 worktree
repo forall hardware/camera platform/frameworks/av packages/apps/Camera2 -c '
  git worktree add /tmp/camera-dev/$REPO_PATH -b '"$BRANCH"'
'

# 各 repo 獨立開發，最後用同一個 topic 推送
for proj in hardware/camera frameworks/av packages/apps/Camera2; do
  cd /tmp/camera-dev/$proj
  git push origin HEAD:refs/for/main%topic=$TOPIC
done

# Gerrit 上就能用 topic 一起 review / submit
```

#### 範例 3：Claude Code + Repo 自動化腳本

利用 Claude Code 的 `WorktreeCreate` hook，自動為 repo 環境建立 worktree：

```bash
#!/bin/bash
# repo-worktree-create.sh — WorktreeCreate hook
SLUG="$1"
BASE="/tmp/claude-worktrees/$SLUG"
PROJECTS="platform/frameworks/base packages/apps/Settings"

for proj in $PROJECTS; do
  repo forall $proj -c "
    mkdir -p $BASE/\$REPO_PATH
    git worktree add $BASE/\$REPO_PATH -b worktree-$SLUG
  "
done

echo "{\"worktreePath\": \"$BASE\"}"
```

#### 範例 4：對比兩個 Android 版本

```bash
# 同時維持兩個版本的 checkout
repo forall -c 'git worktree add /tmp/android-13/$REPO_PATH android-13.0.0_r1'
repo forall -c 'git worktree add /tmp/android-14/$REPO_PATH android-14.0.0_r1'

# 比較特定模組差異
diff -r /tmp/android-13/frameworks/base/core \
        /tmp/android-14/frameworks/base/core

# 清理
repo forall -c 'git worktree remove /tmp/android-13/$REPO_PATH 2>/dev/null'
repo forall -c 'git worktree remove /tmp/android-14/$REPO_PATH 2>/dev/null'
repo forall -c 'git worktree prune'
```

### 4.5 注意事項

> [!warning] repo forall + worktree 的陷阱
> 1. **Worktree 路徑必須在 repo 工作區外** — 放在裡面會干擾 `repo sync`
> 2. **不要在 worktree 活躍時 `repo sync` 同一分支** — `repo sync` 可能做 force checkout 和 GC
> 3. **`repo abandon` / `repo prune` 不知道 worktree 的存在** — 刪除分支會破壞活躍的 worktree
> 4. **Secondary workspace 無法用 `repo sync` / `repo upload`** — 只能用原生 `git push`
> 5. **建構系統（Soong/Make）期望完整目錄結構** — 手動組裝的 worktree 可能缺少必要檔案

---

## 我的心得（My Takeaways）

1. Claude Code worktree 的檔案操作遠比表面看到的複雜 — 一個 `EnterWorktree` 背後涉及 10+ 次檔案系統操作
2. `.worktreeinclude` 的設計很精巧：用 `--directory` flag 折疊大目錄，只展開真正需要的部分，兼顧正確性和效能
3. 在 repo 環境中，`repo forall + git worktree` 是可行的 workaround，但失去了 `repo sync`/`repo upload` 的便利性
4. 對於 Android 開發，`repo init --reference` 可能是更穩定的多工作區方案
5. Hooks 擴展機制（WorktreeCreate/Remove）為非 Git VCS 留下了擴展空間，這在企業環境中很有價值

---

## 待補充（Open Questions）

- repo 官方是否有計劃加入原生 worktree 支援？搜尋關鍵字：`AOSP repo tool worktree feature request`
- Claude Code 的 sparse-checkout 設定是否支援 per-project 不同的 sparsePaths？搜尋：`claude code settings worktree sparsePaths project-level`
- `git worktree add --orphan` 是否能和 `repo forall` 更好地整合？搜尋：`git worktree orphan branch repo forall`
- 在超大型 repo（100+ project）環境中，`repo forall -c 'git worktree add ...'` 的效能瓶頸在哪？
- WorktreeCreate hook 的輸出格式是否支援額外的中繼資料（如 tmux session name）？
- Claude Code 是否支援在同一 session 中建立多個 worktree？（目前看起來 `EnterWorktree` 不允許嵌套）
- Gerrit 的 topic submit 在跨 worktree 的 commit 間是否有原子性保證？搜尋：`gerrit topic submit atomicity`

---

## 相關連結（Related）

- [[2026-03-31-REPO-MULTI-REPO-MANAGEMENT-AND-GIT-WORKTREE-ADVANCED-GUIDE]] — 本文的基礎：repo 三層儲存架構與 git worktree 原理
- [[2026-03-31-CLAUDE-CODE-WORKTREE-X-REPO-MULTI-REPO-PARALLEL-DEVELOPMENT]] — 前作：Claude Code worktree × repo 並行開發完全指南
- [[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]] — 同樣從檔案操作角度分析 Claude Code 功能的姊妹文
- [[2026-04-07-CLAUDE-CODE-MEMORY-SYSTEM]] — Claude Code 記憶系統也使用檔案系統操作，可對比參考
- [[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]] — Hooks 功能詳解，WorktreeCreate/Remove 是其中的 hook 事件

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，確立基礎知識 | `git worktree add -B`、`.claude/worktrees/`、`settings.worktree.sparsePaths`、`.worktreeinclude`、`repo forall -c` 五個核心指令/路徑 |
| **理解（半被動）** | 解釋概念的含義及關聯 | Worktree 建立是一個七步流程（驗證→fetch→add→sparse→settings→hooks→symlink→include），每步都有對應的檔案操作；repo forall 是 repo 世界中唯一能操作 git worktree 的橋樑 |
| **分析（主動）** | 檢驗論點、找出假設 | 關鍵假設：worktree 目錄結構在 `.claude/worktrees/` 下是安全的（但若磁碟空間不足？）；`--directory` 折疊優化假設大部分 gitignored 目錄不需要展開（但 `.worktreeinclude` 指向深層路徑時效能退化）；repo forall 假設所有 project 都有相同的分支 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. 為 Android 專案建立 `.worktreeinclude` 和 `settings.json` 中的 `sparsePaths` 設定，加速 worktree 建立；2. 撰寫 WorktreeCreate hook 整合 repo forall，讓 Claude Code 在 multi-repo 環境中自動建立跨 project worktree；3. 用 `symlinkDirectories` 設定 `out/` 目錄的 symlink，避免建構輸出佔用雙倍空間 |
| **評估（主動）** | 判斷多個方案的優劣 | `repo --reference` vs `repo forall + worktree`：前者保持完整 repo 功能但建立慢且佔空間，後者快速但失去 repo 管理能力。對於「快速 hotfix + Gerrit review」場景，worktree 方案更優；對於「長期並行開發」場景，`--reference` 更穩定。Claude Code worktree 最適合 AI agent 隔離場景，不適合替代完整的 multi-repo 管理 |

### 分析型追問（Socratic Follow-up）

- **澄清**：`.worktreeinclude` 中的「模式匹配」與 `.gitignore` 的語法完全一致嗎？`!` 否定模式是否有效？
- **假設**：本文假設 `findCanonicalGitRoot` 總能正確找到主 repo root。若在 repo managed 的子 project 中執行，canonical root 是哪一層？
- **證據**：「稀疏檢出省下 6-8 秒」的數據來自原始碼註釋，是否有實際 benchmark 驗證？
- **觀點**：若站在 repo 工具維護者的角度，為什麼不加入原生 worktree 支援？可能的技術債或架構限制是什麼？
- **後果**：若大量使用 agent worktree（例如 10+ 個並行 agent），`.git/worktrees/` 目錄的中繼資料會膨脹到什麼程度？是否影響 git 效能？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 在 repo 環境中使用 worktree 最大的風險是 `repo sync` 與 worktree 的交互：`repo sync` 可能做 force checkout 或 GC，破壞活躍 worktree 的狀態，導致**未提交的工作遺失**。
2. **什麼情況下會失敗？** — 當 repo manifest 中的 project 數量超過數百個時，`repo forall -c 'git worktree add ...'` 會因為串行執行而極其緩慢；若某些 project 沒有目標分支，會出現部分成功部分失敗的不一致狀態。
3. **有沒有更好的替代方案？** — 對於 multi-repo 並行開發，`repo init --reference` + 獨立 sync 是更穩定的方案（完全保持 repo 功能）；代價是建立時間更長（需要完整 sync）和磁碟空間更大（即使用 reference，仍需要完整 working tree）。選擇標準：臨時操作用 worktree，長期並行用 reference。

---

## References

- Claude Code 原始碼：`src/utils/worktree.ts`（1170+ 行）
- Claude Code 原始碼：`src/tools/EnterWorktreeTool/EnterWorktreeTool.ts`（128 行）
- Claude Code 原始碼：`src/tools/ExitWorktreeTool/ExitWorktreeTool.ts`（330 行）
- [Git Worktree 官方文件](https://git-scm.com/docs/git-worktree)
- [Android repo 工具](https://gerrit.googlesource.com/git-repo/)
