---
title: "npx skills 深度分析 — parseSource 解析、discoverSkills 搜尋、安裝更新機制與 Gerrit Server 相容性"
date: 2026-04-11
category: CodeAnalysis
tags:
  - #code-analysis
  - #tools/cli
  - #ai/agent
  - #devtools/skill-system
  - #gerrit
source: "https://github.com/vercel-labs/agent-browser"
source_type: code
author: "Vercel Labs"
status: notes
links:
  - "[[CLAUDE-CODE-SKILL-SYSTEM]]"
  - "[[GERRIT-WORKFLOW]]"
  - "[[NPX-SKILLS-CLI]]"
github_stars: N/A
github_language: Rust
---

## 摘要（Summary）

Agent Browser 是 Vercel Labs 開發的瀏覽器自動化（Browser Automation）CLI 工具，供 AI 代理人（Agent）控制 Chrome 瀏覽器。本文深入分析其 **Skill 系統**的完整運作機制，包含兩套獨立的 skill 載入架構：

1. **CLI 內建載入**（Rust，硬編碼 5 個 skill，嵌入系統提示詞）
2. **`npx skills` 外部管理**（Node.js，支援 GitHub/GitLab/Gerrit/本地路徑，安裝到 AI 代理人目錄）

重點釐清在 **Gerrit Server** 環境下的相容性問題、搜尋規則、安裝產物（Artifacts），以及更新流程的限制。

## Why — 為什麼存在？

> AI 代理人需要「知道怎麼用工具」的知識注入機制。Skill 系統就是這個橋樑。

- **核心動機**：AI 編碼助手（Claude Code、Cursor、Codex 等）需要知道如何操作 agent-browser，但不能每次都從零學起。Skill 把操作知識打包成 `SKILL.md` 文件，注入到 AI 的系統提示詞（System Prompt）中
- **取代/改善什麼**：取代手動在 `CLAUDE.md` 中撰寫工具說明的方式，實現跨代理人（Cross-Agent）、跨專案的知識共享
- **目標用戶**：使用 AI 編碼助手的開發者，特別是需要瀏覽器自動化能力的團隊

## What — 是什麼？

- **主要功能**：
  - CLI 內建 skill 載入：啟動時將 skill 內容嵌入 AI 系統提示詞
  - `npx skills add`：從 GitHub/GitLab/Git/本地路徑安裝 skill 到 AI 代理人目錄
  - `npx skills check/update`：檢查和更新已安裝的 skill（僅限 GitHub 來源）
  - `npx skills list`：列出已安裝的 skill
- **不做什麼（Non-goals）**：不是 plugin 系統，不支援運行時動態載入；不提供 skill marketplace
- **技術棧（Tech Stack）**：
  - CLI 核心：Rust（`cli/src/`）
  - Skill 管理工具：Node.js（`skills` npm 套件 v1.4.9）
  - Skill 格式：Markdown + YAML frontmatter（`SKILL.md`）

## How — 如何運作？

> [!important] Agent Browser 有**兩套完全獨立**的 skill 機制，不要混淆。

### 系統架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Browser 生態系                         │
├─────────────────────────────┬───────────────────────────────────┤
│                             │                                   │
│   機制 A：CLI 內建載入        │   機制 B：npx skills 外部管理      │
│   (Rust, 編譯時決定)          │   (Node.js, 執行時安裝)           │
│                             │                                   │
│   ┌───────────────────┐     │   ┌─────────────────────────┐     │
│   │  SKILL_NAMES[]    │     │   │  npx skills add <src>   │     │
│   │  硬編碼 5 個 skill  │     │   │  支援多種來源格式        │     │
│   └────────┬──────────┘     │   └────────────┬────────────┘     │
│            │                │                │                  │
│   ┌────────▼──────────┐     │   ┌────────────▼────────────┐     │
│   │  find_skills_dir() │     │   │  parseSource()          │     │
│   │  從 binary 向上找   │     │   │  解析來源 URL/路徑       │     │
│   └────────┬──────────┘     │   └────────────┬────────────┘     │
│            │                │                │                  │
│   ┌────────▼──────────┐     │   ┌────────────▼────────────┐     │
│   │  load_skills()     │     │   │  git clone / 直接讀取    │     │
│   │  讀取 SKILL.md     │     │   └────────────┬────────────┘     │
│   └────────┬──────────┘     │                │                  │
│            │                │   ┌────────────▼────────────┐     │
│   ┌────────▼──────────┐     │   │  discoverSkills()       │     │
│   │  get_system_prompt()│     │   │  三階段搜尋 SKILL.md    │     │
│   │  嵌入 AI 提示詞     │     │   └────────────┬────────────┘     │
│   │  <skill> XML 標籤   │     │                │                  │
│   └───────────────────┘     │   ┌────────────▼────────────┐     │
│                             │   │  installSkillForAgent()  │     │
│   用於：agent-browser chat  │   │  複製 + symlink          │     │
│   / dashboard AI 功能       │   └────────────┬────────────┘     │
│                             │                │                  │
│                             │   ┌────────────▼────────────┐     │
│                             │   │  寫入 lock file          │     │
│                             │   │  記錄來源 + hash          │     │
│                             │   └─────────────────────────┘     │
│                             │                                   │
│                             │   用於：Claude Code / Cursor /    │
│                             │   Codex / 所有 AI 編碼助手        │
│                             │                                   │
└─────────────────────────────┴───────────────────────────────────┘
```

### 機制 A：CLI 內建 Skill 載入流程

```
agent-browser chat "打開 google.com"
        │
        ▼
get_system_prompt()  [chat.rs:124, OnceLock 只執行一次]
        │
        ▼
load_skills()  [chat.rs:98]
        │
        ├─► find_skills_dir()  [chat.rs:84]
        │     從 binary 路徑逐層向上找 skills/ 目錄
        │     驗證：skills/agent-browser/SKILL.md 必須存在
        │
        ├─► 遍歷 SKILL_NAMES = ["agent-browser", "slack",
        │     "electron", "dogfood", "agentcore"]
        │
        ├─► 讀取每個 skills/{name}/SKILL.md
        │
        ├─► strip_frontmatter()  [chat.rs:112]
        │     移除 YAML frontmatter
        │
        └─► 組裝系統提示詞：
              <skill name="agent-browser">...</skill>
              <skill name="slack">...</skill>
              ...
```

> [!warning] 限制
> `SKILL_NAMES` 是 `const` 硬編碼陣列，**新增 skill 必須改 Rust 原始碼並重新編譯**。`skills/vercel-sandbox/` 目錄雖然存在但不在陣列中，因此不會被載入。

### 機制 B：`npx skills` 外部管理流程

#### B1：來源解析（`parseSource`）

```
用戶輸入
    │
    ├─ 本地路徑 (/path/to/repo)
    │   └─► type: "local"，直接讀取
    │
    ├─ github: 前綴 (github:owner/repo)
    │   └─► type: "github"，轉換為 GitHub URL
    │
    ├─ gitlab: 前綴 (gitlab:owner/repo)
    │   └─► type: "gitlab"，轉換為 GitLab URL
    │
    ├─ GitHub URL (https://github.com/...)
    │   ├─ /tree/branch/subpath → type: "github" + ref + subpath
    │   ├─ /tree/branch → type: "github" + ref
    │   └─ /owner/repo → type: "github"
    │
    ├─ GitLab URL (https://gitlab.com/...)
    │   └─► type: "gitlab"（支援 /-/tree/ 格式）
    │
    ├─ owner/repo 簡寫
    │   └─► type: "github" ⚠️ 永遠硬解析為 GitHub
    │
    ├─ 非 GitHub/GitLab 的 HTTPS URL
    │   └─► type: "well-known"（透過 HTTP 直接抓取 SKILL.md）
    │
    └─ 其他 Git URL (ssh://..., git@..., https://...*.git)
        └─► type: "git" ✅ Gerrit 走這條路
```

> [!important] Gerrit Server 關鍵發現
> - `owner/repo` 簡寫格式**永遠被解析為 GitHub**（`cli.mjs:187-195`），Gerrit 用戶**不能用簡寫**
> - 完整的 SSH/HTTPS Git URL 會被歸類為 `type: "git"`，使用 `git clone --depth 1` 處理
> - Well-known URL 模式（非 GitHub/GitLab 的 HTTPS URL）也可使用，直接透過 HTTP 抓取

#### B2：Skill 發現（`discoverSkills`）三階段搜尋

```
discoverSkills(searchPath)
        │
   ┌────▼────────────────────────────────────────────────┐
   │ 階段 1：根目錄檢查                                    │
   │ searchPath/SKILL.md 存在？                           │
   │   YES → 回傳 1 個 skill                              │
   │          （除非 --full-depth 才繼續往下）              │
   │   NO  → 進入階段 2                                    │
   └────┬────────────────────────────────────────────────┘
        │
   ┌────▼────────────────────────────────────────────────┐
   │ 階段 2：掃描「優先目錄」的一級子資料夾                  │
   │                                                      │
   │ 共 26+ 個優先路徑，依序掃描：                          │
   │   searchPath/                                        │
   │   searchPath/skills/                                 │
   │   searchPath/skills/.curated/                        │
   │   searchPath/skills/.experimental/                   │
   │   searchPath/skills/.system/                         │
   │   searchPath/.agents/skills/                         │
   │   searchPath/.claude/skills/                         │
   │   searchPath/.cline/skills/                          │
   │   searchPath/.codex/skills/                          │
   │   searchPath/.github/skills/                         │
   │   searchPath/.goose/skills/                          │
   │   searchPath/.windsurf/skills/                       │
   │   ... (共支援 26+ 個 AI agent 目錄)                   │
   │                                                      │
   │ 每個目錄：列出子資料夾 → 檢查子資料夾/SKILL.md        │
   │ 收集所有找到的，用 seenNames Set 去重                  │
   └────┬────────────────────────────────────────────────┘
        │
   ┌────▼────────────────────────────────────────────────┐
   │ 階段 3：遞迴深度搜尋（觸發條件二擇一）                 │
   │   a) 前面找到 0 個 skill                              │
   │   b) 使用了 --full-depth 旗標                         │
   │                                                      │
   │ findSkillDirs(searchPath, depth=0, maxDepth=5)       │
   │   遞迴搜尋所有子目錄，最深 5 層                        │
   │   跳過：node_modules, .git, dist, build, __pycache__ │
   │   每找到一個含 SKILL.md 的目錄就記錄                   │
   └─────────────────────────────────────────────────────┘
```

> [!note] SKILL.md 有效性判定
> 光是有 `SKILL.md` 檔案不夠，frontmatter 中必須同時包含 `name` 和 `description` 兩個字串欄位，否則 `parseSkillMd()` 回傳 `null`，該 skill 會被跳過（`cli.mjs:537-538`）。

#### B3：安裝寫入（`installSkillForAgent`）

```
installSkillForAgent(skill, agentType, options)
        │
        ▼
┌─ mode === "copy" ──────────────────────────────┐
│   cleanAndCreateDirectory(agentDir)             │
│   copyDirectory(skill.path → agentDir)          │
│   回傳 { path: agentDir, mode: "copy" }        │
└─────────────────────────────────────────────────┘

┌─ mode === "symlink"（預設）──────────────────────┐
│                                                  │
│   1. cleanAndCreateDirectory(canonicalDir)       │
│      → ~/.agents/skills/<name>/                  │
│      先 rm -rf 舊目錄，再 mkdir                   │
│                                                  │
│   2. copyDirectory(skill.path → canonicalDir)    │
│      複製 SKILL.md、references/、templates/ 等    │
│      排除：.git、__pycache__、metadata.json、     │
│            所有 .* 開頭檔案                       │
│                                                  │
│   3. createSymlink(canonicalDir → agentDir)      │
│      → ~/.claude/skills/<name>                   │
│        → symlink 到 ../../.agents/skills/<name>  │
│                                                  │
│   4. 若 symlink 失敗 → 退回 copy 模式            │
└─────────────────────────────────────────────────┘
```

### 安裝產物時序圖

```
用戶              npx skills           git              檔案系統
 │                    │                 │                   │
 │──add <source>─────►│                 │                   │
 │                    │                 │                   │
 │                    │──clone──────────►│                   │
 │                    │◄──/tmp/skills-xx│                   │
 │                    │                 │                   │
 │                    │──discoverSkills()                   │
 │                    │  (三階段搜尋)                        │
 │                    │                 │                   │
 │◄──列出找到的 skill──│                 │                   │
 │──確認安裝──────────►│                 │                   │
 │                    │                 │                   │
 │                    │──mkdir───────────────────────────────►│ ~/.agents/skills/<name>/
 │                    │──copy────────────────────────────────►│ ~/.agents/skills/<name>/SKILL.md
 │                    │──symlink─────────────────────────────►│ ~/.claude/skills/<name> → ../../.agents/skills/<name>
 │                    │                 │                   │
 │                    │──寫入 lock file────────────���─────────►│ ~/.agents/.skill-lock.json（全域）
 │                    │──寫入 lock file──────────────────────►│ <cwd>/skills-lock.json（專案）
 │                    │                 │                   │
 │                    │──rm /tmp/skills-xx                  │
 │◄──安裝完成─────────│                 │                   │
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.agents/skills/<name>/` | 目錄（canonical） | 實際檔案存放處，所有 agent 的 symlink 都指向這裡 |
| `~/.agents/skills/<name>/SKILL.md` | 檔案 | Skill 定義文件（Markdown + YAML frontmatter） |
| `~/.agents/skills/<name>/references/` | 目錄 | 詳細參考文件（若 skill 有提供） |
| `~/.agents/skills/<name>/templates/` | 目錄 | 使用範本（若 skill 有提供） |
| `~/.claude/skills/<name>` | symlink | Claude Code 的 skill 入口，指向 `../../.agents/skills/<name>` |
| `~/.codex/skills/<name>` | symlink | Codex 的 skill 入口（若已選擇安裝） |
| `~/.agents/.skill-lock.json` | 檔案 | 全域 lock file，記錄來源、hash、安裝/更新時間 |
| `<cwd>/skills-lock.json` | 檔案 | 專案級 lock file，記錄 source、ref、computedHash |

### Lock File 結構

**全域 Lock（`~/.agents/.skill-lock.json`）— 用於 `check`/`update`**

```json
{
  "version": 3,
  "skills": {
    "agent-browser": {
      "source": "vercel-labs/agent-browser",
      "sourceType": "github",
      "sourceUrl": "https://github.com/vercel-labs/agent-browser.git",
      "skillPath": "skills/agent-browser/SKILL.md",
      "skillFolderHash": "b6f762bf402cdfaf6a06514e9ce4142ce3e4fb4c",
      "installedAt": "2026-03-18T22:45:25.273Z",
      "updatedAt": "2026-04-10T23:27:18.438Z"
    }
  },
  "dismissed": {},
  "lastSelectedAgents": ["claude-code", "cursor", "codex"]
}
```

**專案 Lock（`<cwd>/skills-lock.json`）— 用於 `experimental_install`**

```json
{
  "version": 1,
  "skills": {
    "agent-browser": {
      "source": "https://github.com/vercel-labs/agent-browser.git",
      "ref": null,
      "sourceType": "github",
      "computedHash": "a1b2c3d4e5..."
    }
  }
}
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 雙 Lock 設計（Dual Lock Design）
> 全域 lock 追蹤「skill 從哪裡來」（source + hash），用於自動更新比對。專案 lock 追蹤「這個專案用了哪些 skill」（computedHash），用於團隊同步（`experimental_install`）。兩者獨立運作。

1. **Canonical + Symlink 模式**：所有 agent 共享同一份 skill 檔案（存在 `~/.agents/skills/`），各 agent 目錄只放 symlink。更新一次，所有 agent 同步生效 — 原因：避免多份拷貝導致版本不一致
2. **GitHub 優先的更新機制**：`check`/`update` 只透過 GitHub API（`GET /repos/{owner}/{repo}/git/trees/{ref}`）比對 tree SHA，不支援其他 Git 平台 — 原因：GitHub API 提供高效的 tree hash 比對，而通用 git 沒有等效的輕量 API
3. **Shallow Clone**：`git clone --depth 1`，只抓最新一層 — 原因：skill 不需要 git 歷史，節省時間和空間
4. **`owner/repo` 簡寫硬綁 GitHub**：設計上假設大多數 skill 都在 GitHub 上 — 原因：簡化最常見情境的使用體驗

## 安裝流程（Installation Flow）

### 安裝觸發方式

```
npx skills add <source>  → parseSource() → git clone / 直接讀取 → discoverSkills()
                            → installSkillForAgent() → 寫入 canonical + symlink + lock
```

### 三種來源的安裝比較

| | GitHub | Gerrit (SSH/HTTPS) | 本地路徑 |
|---|---|---|---|
| 指令範例 | `npx skills add vercel-labs/agent-browser` | `npx skills add ssh://gerrit:29418/repo` 或 `npx skills add https://gerrit.company.com/a/repo` | `npx skills add /path/to/repo` |
| `parseSource` type | `"github"` | `"git"` | `"local"` |
| 取得方式 | GitHub Blob API（快）或 git clone | `git clone --depth 1` 到 `/tmp/` | 直接讀取本地目錄 |
| lock 中 `skillFolderHash` | ✅ GitHub tree SHA | ❌ 空字串 | ❌ 空字串 |
| `npx skills check` | ✅ 自動比對 | ❌ 被跳過（skipped） | ❌ 被跳過 |
| `npx skills update` | ✅ 自動更新 | ❌ 需手動重裝 | ❌ 需手動重裝 |
| 安裝產物 | 完全相同 | 完全相同 | 完全相同 |

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| `GITHUB_TOKEN` / `GH_TOKEN` | GitHub Personal Access Token | 執行 `check`/`update` 時讀取（用於 GitHub API 認證） |
| `INSTALL_INTERNAL_SKILLS` | `"1"` 或 `"true"` | 安裝時讀取，允許安裝 `metadata.internal: true` 的 skill |
| `SKILLS_DOWNLOAD_URL` | 自訂 URL（預設 `https://skills.sh`） | 安裝時讀取，Well-known 模式的下載基底 URL |
| `XDG_STATE_HOME` | 自訂路徑 | 決定全域 lock file 的存放位置 |
| `GIT_TERMINAL_PROMPT` | `"0"`（強制設定） | clone 時停用互動式密碼提示 |

> [!warning] 解除安裝
> 使用 `npx skills remove <name>` 或 `npx skills remove --all`。手動清理需刪除：
> - `~/.agents/skills/<name>/`（canonical 目錄）
> - `~/.claude/skills/<name>`（symlink）
> - `~/.agents/.skill-lock.json` 中對應的條目
> - `<project>/skills-lock.json` 中對應的條目（若有）

---

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 安裝 Skill（GitHub） | `npx skills add owner/repo` | `cli.mjs` | `parseSource → tryBlobInstall / cloneRepo → discoverSkills → installSkillForAgent → addSkillToLock` |
| 2 | 安裝 Skill（Gerrit/Git） | `npx skills add ssh://...` | `cli.mjs` | `parseSource → cloneRepo → discoverSkills → installSkillForAgent → addSkillToLock` |
| 3 | 安裝 Skill（本地） | `npx skills add /path` | `cli.mjs` | `parseSource → discoverSkills → installSkillForAgent → addSkillToLocalLock` |
| 4 | 列出已安裝 Skill | `npx skills list` | `cli.mjs` | `readdir(agentBaseDir)` |
| 5 | 檢查更新 | `npx skills check` | `cli.mjs:4370` | `readSkillLock → fetchSkillFolderHash (GitHub API) → 比對 hash` |
| 6 | 自動更新 | `npx skills update` | `cli.mjs:4461` | `readSkillLock → fetchSkillFolderHash → buildUpdateInstallSource → 重新 add` |
| 7 | CLI 內建載入 | `agent-browser chat` | `chat.rs:124` | `find_skills_dir → load_skills → strip_frontmatter → 嵌入 system prompt` |

### 案例詳解

#### 案例 1：從 GitHub 安裝 Skill

```
用戶：npx skills add vercel-labs/agent-browser --skill agent-browser -g
  │
  ▼
cli.mjs:parseSource("vercel-labs/agent-browser")
  │  shorthandMatch → type: "github"
  │  url: "https://github.com/vercel-labs/agent-browser.git"
  │
  ▼
tryBlobInstall()  ── 嘗試 ──► GitHub Blob API（快速，不用 clone）
  │ 失敗時退回 ↓
  ▼
cloneRepo(url)  ── git clone --depth 1 ──► /tmp/skills-abc123/
  │
  ▼
discoverSkills(/tmp/skills-abc123/)
  │  階段2：找到 skills/ 子目錄
  │  掃描 skills/agent-browser/SKILL.md ✓
  │  掃描 skills/slack/SKILL.md ✓
  │  ... 共找到 5 個
  │
  ▼
用戶選擇 --skill agent-browser → 過濾為 1 個
  │
  ▼
installSkillForAgent(skill, "claude-code", {global: true})
  │  1. mkdir ~/.agents/skills/agent-browser/
  │  2. copy SKILL.md + references/ + templates/
  │  3. symlink ~/.claude/skills/agent-browser → ../../.agents/skills/agent-browser
  │
  ▼
addSkillToLock("agent-browser", {
  source: "vercel-labs/agent-browser",
  sourceType: "github",
  sourceUrl: "https://github.com/vercel-labs/agent-browser.git",
  skillPath: "skills/agent-browser/SKILL.md",
  skillFolderHash: "b6f762bf..."  ← GitHub tree SHA
})
  │
  ▼
cleanupTempDir(/tmp/skills-abc123/)
```

#### 案例 2：從 Gerrit 安裝 Skill（SSH）

```
用戶：npx skills add ssh://gerrit.example.com:29418/connsys-jarvis -g -y
  │
  ▼
cli.mjs:parseSource("ssh://gerrit.example.com:29418/connsys-jarvis")
  │  不匹配任何 GitHub/GitLab 模式
  │  → type: "git", url: "ssh://gerrit.example.com:29418/connsys-jarvis"
  │
  ▼
cloneRepo("ssh://gerrit.example.com:29418/connsys-jarvis")
  │  git clone --depth 1 → /tmp/skills-xyz789/
  │  ⚠️ 需要 SSH key 已設定（GIT_TERMINAL_PROMPT=0，不會提示密碼）
  │
  ▼
discoverSkills(/tmp/skills-xyz789/)
  │  根目錄無 SKILL.md → 階段2：無優先目錄命中
  │  → 階段3：遞迴搜尋（maxDepth=5）
  │  找到 18 個 SKILL.md（framework 5 + wifi-bora 9 + sys-bora 4）
  │
  ▼
-y 旗標 → 全部安裝
  │
  ▼
installSkillForAgent() × 18
  │  每個 skill 都：mkdir → copy → symlink
  │
  ▼
addSkillToLock("wifi-bora-build-flow", {
  source: "ssh://gerrit.example.com:29418/connsys-jarvis",
  sourceType: "git",
  sourceUrl: "ssh://gerrit.example.com:29418/connsys-jarvis",
  skillPath: "wifi-bora/wifi-bora-base-expert/skills/wifi-bora-build-flow/SKILL.md",
  skillFolderHash: ""  ← ⚠️ 空字串！無法用 GitHub API 取 hash
})
```

#### 案例 2b：從 Gerrit 安裝 Skill（HTTP）

```
用戶：npx skills add https://gerrit.company.com/a/connsys-jarvis -g -y
  │
  ▼
cli.mjs:parseSource("https://gerrit.company.com/a/connsys-jarvis")
  │  hostname 不是 github.com / gitlab.com
  │  URL 不以 .git 結尾，不匹配 Git URL 模式
  │  → type: "well-known"（嘗試透過 HTTP 直接抓取 SKILL.md）
  │  ⚠️ well-known 模式會嘗試從 URL 直接 fetch，但 Gerrit HTTP 端點
  │     回傳的是 Git 頁面，不是 SKILL.md → 可能失敗
  │
  │  ✅ 解決方案：URL 結尾加 .git 強制走 Git clone 路徑
  │
  ▼
用戶（修正）：npx skills add https://gerrit.company.com/a/connsys-jarvis.git -g -y
  │
  ▼
cli.mjs:parseSource("https://gerrit.company.com/a/connsys-jarvis.git")
  │  匹配 /^https?:\/\/.+\.git(?:$|[/?])/i → looksLikeGitSource() = true
  │  → type: "git", url: "https://gerrit.company.com/a/connsys-jarvis.git"
  │
  ▼
cloneRepo("https://gerrit.company.com/a/connsys-jarvis.git")
  │  git clone --depth 1 → /tmp/skills-abc456/
  │  ⚠️ 若 Gerrit 需要認證，需先設定 git credential 或在 URL 中帶 token：
  │     https://<user>:<http-password>@gerrit.company.com/a/connsys-jarvis.git
  │
  ▼
（後續流程與 SSH 案例相同：discoverSkills → installSkillForAgent → addSkillToLock）
```

> [!important] Gerrit HTTP 注意事項
> - Gerrit 的 HTTP clone URL 通常帶 `/a/` 前綴（authenticated）：`https://gerrit.company.com/a/repo-name.git`
> - **URL 必須以 `.git` 結尾**，否則 `parseSource` 會誤判為 `well-known` 類型而失敗
> - HTTP 認證方式：在 Gerrit 個人設定中產生 HTTP Password，透過 `git credential` 或 URL 內嵌傳入
> - SSH 不需要額外處理（只要 SSH key 已配置），**HTTP 則需注意 `.git` 後綴和認證**

#### 案例 5：檢查更新（`npx skills check`）

```
用戶：npx skills check
  │
  ▼
readSkillLock()  ── 讀取 ──► ~/.agents/.skill-lock.json
  │
  ▼
遍歷所有 skill entries
  │
  ├─ entry.skillFolderHash 存在 且 entry.skillPath 存在？
  │   │
  │   YES → fetchSkillFolderHash(entry.source, entry.skillPath, token, entry.ref)
  │   │     呼叫 GitHub API: GET /repos/{source}/git/trees/{ref}?recursive=1
  │   │     比對回傳的 tree SHA 與 entry.skillFolderHash
  │   │     │
  │   │     ├─ 相同 → "✓ Up to date"
  │   │     └─ 不同 → "↑ Update available"
  │   │
  │   NO → 歸入 skipped[]
  │         原因："no hash available" 或 "no skill path"
  │         顯示："To update: npx skills add <sourceUrl> -g -y"
  │
  ▼
顯示結果：
  ✓ All skills are up to date
  或
  2 update(s) available:
    ↑ agent-browser (source: vercel-labs/agent-browser)
  
  3 skill(s) cannot be checked automatically:
    • wifi-bora-build-flow (no hash available)
      To update: npx skills add ssh://gerrit...:29418/connsys-jarvis -g -y
```

> [!warning] Gerrit / 本地來源的更新限制
> `check` 和 `update` 完全依賴 GitHub API 的 tree hash 比對機制。非 GitHub 來源的 `skillFolderHash` 永遠為空字串，因此**永遠被跳過**。唯一的更新方式是手動重新執行 `npx skills add`。

---

## connsys-jarvis 實戰範例

### Repo 結構

```
connsys-jarvis/                          ← 根目錄（無 SKILL.md）
├── framework/
│   └── framework-base-expert/
│       └── skills/                      ← 5 個 skill
│           ├── framework-expert-create-flow/SKILL.md
│           ├── framework-expert-discovery-knowhow/SKILL.md
│           ├── framework-handoff-flow/SKILL.md
│           ├── framework-memory-tool/SKILL.md
│           └── framework-skill-create-flow/SKILL.md
├── wifi-bora/
│   ├── wifi-bora-base-expert/
│   │   └── skills/                      ← 6 個 skill
│   │       ├── wifi-bora-arch-knowhow/SKILL.md
│   │       ├── wifi-bora-build-flow/SKILL.md
│   │       ├── wifi-bora-linkerscript-knowhow/SKILL.md
│   │       ├── wifi-bora-memory-knowhow/SKILL.md
│   │       ├── wifi-bora-protocol-knowhow/SKILL.md
│   │       └── wifi-bora-symbolmap-knowhow/SKILL.md
│   └── wifi-bora-memory-slim-expert/
│       └── skills/                      ← 3 個 skill
│           ├── wifi-bora-ast-tool/SKILL.md
│           ├── wifi-bora-lsp-tool/SKILL.md
│           └── wifi-bora-memslim-flow/SKILL.md
├── sys-bora/
│   ├── sys-bora-base-expert/
│   │   └── skills/                      ← 2 個 skill
│   │       ├── sys-bora-gerrit-tool/SKILL.md
│   │       └── sys-bora-repo-tool/SKILL.md
│   └── sys-bora-preflight-expert/
│       └── skills/                      ← 2 個 skill
│           ├── sys-bora-gerrit-commit-flow/SKILL.md
│           └── sys-bora-preflight-flow/SKILL.md
└── (bt-bora, lrwpan-bora, wifi-gen4m, wifi-logan — 結構類似)
```

**共 18 個 SKILL.md，分佈在第 4 層深度。**

### 指令範例與結果

#### Gerrit Server 安裝（SSH）

```bash
# 安裝全部 18 個 skill（全域）
npx skills add ssh://gerrit.company.com:29418/connsys-jarvis -g -y

# 只安裝 wifi-bora 相關（用 --skill 過濾名稱）
npx skills add ssh://gerrit.company.com:29418/connsys-jarvis \
  --skill wifi-bora-build-flow --skill wifi-bora-arch-knowhow -g

# 先預覽有哪些 skill（不安裝）
npx skills add ssh://gerrit.company.com:29418/connsys-jarvis --list
```

#### Gerrit Server 安裝（HTTP）

```bash
# ⚠️ URL 必須以 .git 結尾，否則會被誤判為 well-known 類型
# 安裝全部 18 個 skill（全域）
npx skills add https://gerrit.company.com/a/connsys-jarvis.git -g -y

# 只安裝特定 skill
npx skills add https://gerrit.company.com/a/connsys-jarvis.git \
  --skill wifi-bora-build-flow -g

# 若 Gerrit 需要認證（HTTP Password），可在 URL 中帶入
npx skills add https://user:httpPasswd@gerrit.company.com/a/connsys-jarvis.git -g -y

# 先預覽有哪些 skill（不安裝）
npx skills add https://gerrit.company.com/a/connsys-jarvis.git --list
```

#### 本地路徑安裝

```bash
# 先 clone 到本地（SSH 或 HTTP 皆可）
git clone ssh://gerrit.company.com:29418/connsys-jarvis \
  /Users/swchen.tw/git/connsys-jarvis
# 或
git clone https://gerrit.company.com/a/connsys-jarvis.git \
  /Users/swchen.tw/git/connsys-jarvis

# 安裝全部
npx skills add /Users/swchen.tw/git/connsys-jarvis -g -y

# 路徑指到不同層級的差異：

# 根目錄 → 階段3 遞迴 → 找到 18 個
npx skills add /Users/swchen.tw/git/connsys-jarvis

# 領域目錄 → 階段3 遞迴 → 找到 9 個（wifi-bora 下全部）
npx skills add /Users/swchen.tw/git/connsys-jarvis/wifi-bora

# expert 目錄 → 階段2 命中 skills/ → 找到 6 個
npx skills add /Users/swchen.tw/git/connsys-jarvis/wifi-bora/wifi-bora-base-expert

# skills 目錄 → 階段3 遞迴 → 找到 6 個
npx skills add /Users/swchen.tw/git/connsys-jarvis/wifi-bora/wifi-bora-base-expert/skills

# 單一 skill 目錄 → 階段1 直接命中 → 找到 1 個
npx skills add /Users/swchen.tw/git/connsys-jarvis/wifi-bora/wifi-bora-base-expert/skills/wifi-bora-build-flow
```

#### 更新流程

```bash
# GitHub 來源：自動檢查 + 更新
npx skills check          # 檢查哪些有新版
npx skills update         # 一鍵更新全部

# Gerrit 來源：手動重新安裝 = 更新（SSH）
npx skills add ssh://gerrit.company.com:29418/connsys-jarvis -g -y

# Gerrit 來源：手動重新安裝 = 更新（HTTP，URL 必須帶 .git）
npx skills add https://gerrit.company.com/a/connsys-jarvis.git -g -y

# 本地路徑來源：先 pull，再重裝
cd /Users/swchen.tw/git/connsys-jarvis && git pull
npx skills add /Users/swchen.tw/git/connsys-jarvis -g -y

# 只更新單一 skill
npx skills add /Users/swchen.tw/git/connsys-jarvis \
  --skill wifi-bora-build-flow -g -y
```

#### 查詢與管理

```bash
# 列出所有已安裝的 skill
npx skills list
npx skills list -g         # 全域
npx skills list --json     # JSON 格式

# 移除
npx skills remove wifi-bora-build-flow
npx skills remove --all    # 全部移除
```

---

## 架構師觀點（Architect's View）

### 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐ | 清晰的 canonical + symlink 架構，更新一處所有 agent 同步 |
| 可擴展性（Scalability） | ⭐⭐⭐ | 新增 agent 只需在 `agents` 物件中加一筆設定，但 CLI 內建的 skill 列表是硬編碼 |
| 跨平台相容（Cross-Platform） | ⭐⭐⭐⭐ | `parseSource()` 支援 GitHub/GitLab/通用 Git/本地路徑四種模式 |
| 文件品質（Documentation） | ⭐⭐⭐ | README 和 docs 完整但未提及非 GitHub 更新的限制 |
| 安全性（Security） | ⭐⭐⭐⭐ | 路徑安全檢查（path traversal protection）、排除敏感檔案 |

> [!tip] 值得學習的設計
> **Canonical + Symlink** 模式是一個優雅的解決方案：一份實際檔案、多個 symlink 入口。既避免了同步問題，又保持了各 agent 目錄結構的獨立性。

### 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷

- **GitHub 綁定的更新機制**：`check`/`update` 完全依賴 GitHub API tree hash。使用 Gerrit、GitLab 自建站、或本地路徑安裝的 skill 無法自動更新，且 `skillFolderHash` 永遠為空 — 影響：企業用戶（常用 Gerrit/GitLab 自建站）需要自建更新腳本
- **CLI 硬編碼 skill 列表**：`SKILL_NAMES` 是 Rust `const`，新增 skill 需重新編譯 — 影響：第三方 skill 無法被 CLI 的 `chat` 功能使用
- **owner/repo 簡寫硬綁 GitHub**：會誤導 Gerrit/GitLab 用戶 — 影響：初次使用時可能遇到 clone 失敗而不知原因

### 改進建議（Improvement Suggestions）

1. 為非 GitHub 來源支援 `computedHash`（本地計算 SHA256 並存入全域 lock），使 `check`/`update` 能比對本地 vs 遠端的 hash
2. CLI 增加環境變數（如 `AGENT_BROWSER_EXTRA_SKILLS`）來擴充 `SKILL_NAMES`，免除重新編譯需求
3. 讓 `parseSource` 的簡寫格式支援自訂 Git host（如 `SKILLS_DEFAULT_HOST=gerrit.example.com`）

---

## 效能基準（Benchmark）

| 場景 | GitHub Blob API | Git Clone（Gerrit） | 本地路徑 |
|------|----------------|-------------------|---------|
| 首次安裝 1 個 skill | ~2-3 秒 | ~5-15 秒（視網路） | < 1 秒 |
| 首次安裝 18 個 skill | ~3-5 秒 | ~5-15 秒（clone 一次） | < 1 秒 |
| 檢查更新（check） | ~1-3 秒 | ❌ 不支援 | ❌ 不支援 |
| 自動更新（update） | ~3-10 秒 | ❌ 需手動重裝 | ❌ 需手動重裝 |

> GitHub Blob API 模式在首次安裝時最快，因為它不需要 `git clone` 整個 repo，而是直接透過 API 取得 tree 結構和 blob 內容。

## 快速上手（Quick Start）

```bash
# 1. 安裝 agent-browser CLI
npm install -g agent-browser

# 2. 安裝 skill 到 Claude Code（GitHub 來源）
npx skills add vercel-labs/agent-browser --skill agent-browser -g

# 3. 安裝 skill 到 Claude Code（Gerrit SSH）
npx skills add ssh://your-gerrit:29418/your-repo -g -y

# 4. 安裝 skill 到 Claude Code（Gerrit HTTP，URL 須帶 .git）
npx skills add https://gerrit.company.com/a/your-repo.git -g -y

# 5. 安裝 skill 到 Claude Code（本地路徑）
npx skills add /path/to/cloned/repo -g -y

# 6. 驗證安裝
npx skills list -g
ls -la ~/.claude/skills/
```

## 我的心得（My Takeaways）

1. **`npx skills` 比想像中強大**：它不只是 GitHub 專用工具，`parseSource()` 的 fallback 機制讓任何 Git URL 都能用。關鍵是要知道不能用 `owner/repo` 簡寫
2. **Gerrit 用戶的痛點在更新**：安裝完全沒問題，但自動更新機制被 GitHub API 綁死了。建議寫一個 shell script 定期 `npx skills add <gerrit-url> -g -y` 來模擬自動更新
3. **兩套 skill 機制容易混淆**：CLI 內建的 5 個 skill（Rust 硬編碼）和 `npx skills` 管理的 skill 是完全獨立的系統，目標用戶不同（前者給 CLI 自己的 chat 功能，後者給外部 AI 代理人）
4. **Canonical + Symlink 是個好模式**：值得在自己的工具中借鑑，解決「多入口、一份資料」的同步問題
5. **discoverSkills 的三階段搜尋**很聰明：優先目錄機制確保常見結構快速命中，遞迴搜尋作為兜底確保不漏

## 待補充（Open Questions）

- 機制 A 的 `SKILL_NAMES` 是硬編碼在 Rust 原始碼中，新增 skill 需要重新編譯整個 binary。這對於需要客製化 skill 的企業用戶來說是嚴重限制，Vercel Labs 是否有計劃讓 SKILL_NAMES 可由外部設定檔動態指定？（建議搜尋：`agent-browser skill names dynamic config external`）
- `npx skills check/update` 只支援來自 GitHub 的 skill 自動更新，Gerrit/GitLab 來源的 skill 無法自動更新。對於使用內部 Gerrit server 的企業，有什麼替代的 skill 版本管理流程？（建議搜尋：`npx skills update gerrit gitlab self-hosted version management`）
- `discoverSkills` 在階段 3 的遞迴搜尋最深 5 層，且跳過 `node_modules` 等常見忽略目錄，但如果一個 monorepo 的 skill 放在第 6 層，就會被靜默忽略。有沒有辦法提高深度限制或指定額外搜尋路徑？（建議搜尋：`npx skills discoverSkills max depth custom path`）
- skill lock file 記錄了安裝來源和 hash，用來追蹤版本。但 lock file 的格式是否有文件說明？若 lock file 損壞或遺失，`npx skills update` 會怎麼處理？（建議搜尋：`npx skills lock file format corruption recovery`）
- `owner/repo` 簡寫格式永遠被解析為 GitHub，這表示在只有 Gerrit/GitLab 的環境中，所有 skill 安裝都需要完整 URL。這個行為是否有計劃改進（例如加入 `--provider` 旗標）？（建議搜尋：`npx skills add provider flag gitlab gerrit shorthand`）

## 相關連結（Related）

- [[CLAUDE-CODE-SKILL-SYSTEM]] — Claude Code 的 skill 系統如何讀取 `.claude/skills/` 目錄
- [[GERRIT-WORKFLOW]] — Gerrit Server 的 SSH 認證與 git 操作流程
- [[NPX-SKILLS-CLI]] — `skills` npm 套件的完整指令參考
- [[2026-04-12-CLAUDE-CODE-PLUGIN-LIFECYCLE-INSTALL-DISABLE-REMOVE-UPDATE]] — Claude Code Plugin 完整生命週期：安裝/停用/移除/更新的檔案影響分析
- [[2026-04-19-CLAUDE-CODE-PLUGIN-JSON-DEPENDENCIES-SHARED-SKILLS-SOURCE-ANALYSIS]] — Skills 路徑解析機制的另一個面向：plugin.json 中的 skills 路徑如何被 loader 處理

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | 1. `SKILL_NAMES` 硬編碼 5 個名稱（chat.rs:79）2. `discoverSkills` 三階段搜尋 3. 安裝產物：canonical 在 `~/.agents/skills/`，symlink 在 `~/.claude/skills/` 4. `owner/repo` 簡寫永遠解析為 GitHub 5. Lock file 版本號：全域 v3、專案 v1 |
| **理解（半被動）** | 解釋概念的含義及關聯 | `npx skills` 的設計哲學是「GitHub 優先，其他平台能用但體驗降級」。三階段搜尋的邏輯是：精確匹配 → 常見結構 → 暴力搜尋，這跟 DNS 解析或 PATH 查找的策略一致。Canonical + Symlink 的關係類似「資料庫正規化」——消除冗餘，透過參照（reference）存取 |
| **分析（主動）** | 批判性思維，找出假設 | **關鍵假設**：所有 skill 都在 GitHub 上（`owner/repo` 簡寫硬綁 GitHub、`check`/`update` 只用 GitHub API）。**潛在漏洞**：`skillFolderHash` 為空時無法偵測更新，但也不會報錯——用戶可能以為 skill 是最新的，實際上遠端已有重大變更。**未論及的前提**：SSH key 必須已配置且無密碼保護（`GIT_TERMINAL_PROMPT=0`） |
| **應用（主動）** | 將理論轉為行動 | 1. 立即可做：寫一個 cron script `npx skills add ssh://gerrit:29418/connsys-jarvis -g -y` 每日執行，模擬自動更新 2. 在 connsys-jarvis 的根目錄加一個 `SKILL.md`（meta skill），讓階段1 直接命中，作為所有子 skill 的索引入口 3. 使用 `--list` 旗標先預覽再安裝，避免 18 個 skill 全裝造成雜亂 |
| **評估（主動）** | 判斷多方案優劣 | **Gerrit 安裝 vs 本地路徑**：Gerrit 安裝每次都要 clone（5-15 秒），但保證來源一致；本地路徑瞬間完成但需要手動 `git pull` 保持同步。對於 CI/CD 環境推薦 Gerrit 直裝；對於個人開發推薦本地路徑 + pull 腳本。**替代方案**：不用 `npx skills` 而是直接手動 copy SKILL.md 到 `.claude/skills/` —— 更簡單但失去 lock file 追蹤和團隊同步能力 |

### 分析型追問（Socratic Follow-up）

- **澄清**：`well-known` URL 模式的具體行為是什麼？它是否直接抓取 `<url>/.well-known/skills.json`？這對自建 Gerrit 的 HTTP 端點有何啟示？
- **假設**：本文假設 Gerrit Server 支援 `git clone --depth 1`。若 Gerrit 配置了限制（如禁止 shallow clone），安裝會直接失敗。如何處理？
- **證據**：「GitHub Blob API 比 git clone 快」的主張基於什麼？在企業內網環境（Gerrit 伺服器在同一局域網）可能反而更快
- **觀點**：若 Vercel 認為「大多數用戶用 GitHub」的假設正確，那投資在非 GitHub 更新機制上可能不划算。但對於企業用戶，這正是 adoption 的最大障礙
- **後果**：若團隊全面採用 `npx skills` 管理 connsys-jarvis 的 18 個 skill，12 個月後 lock file 會累積大量 `skillFolderHash: ""` 的記錄，`npx skills check` 的輸出會被 skipped 項目淹沒，降低可讀性

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — Gerrit 來源的 skill 無法自動偵測更新。若上游修正了關鍵 bug（如 skill 中的錯誤指令導致資料損毀），下游用戶不會收到通知，可能持續使用有問題的舊版 skill。風險等級：**中高**（取決於 skill 內容的影響範圍）
2. **什麼情況下會失敗？** — (a) Gerrit Server 禁止 shallow clone（`--depth 1`）時 clone 會失敗 (b) SSH key 需要密碼時無法互動輸入 (c) 企業防火牆阻擋 `skills.sh` 域名時 telemetry 呼叫會超時（不影響功能但拖慢速度） (d) SKILL.md 缺少 `name` 或 `description` frontmatter 時被靜默跳過，用戶可能不知道某些 skill 未安裝成功
3. **有沒有更好的替代方案？** — 對於 Gerrit 環境，可以考慮：(a) 直接在 CI/CD pipeline 中用 `cp` 複製 SKILL.md 到 `.claude/skills/`，繞過 `npx skills` 但犧牲 lock file 追蹤 (b) 搭建一個輕量級的 HTTP endpoint 提供 SKILL.md，利用 `well-known` 模式安裝 (c) 在 Gerrit 的 change-merged hook 中觸發 `npx skills add` 實現半自動更新

## References

- [Agent Browser GitHub Repo](https://github.com/vercel-labs/agent-browser)
- [skills npm 套件](https://www.npmjs.com/package/skills)（v1.4.9）
- 原始碼分析：`cli/src/native/stream/chat.rs`（CLI 內建 skill 載入）
- 原始碼分析：`~/.npm/_npx/.../skills/dist/cli.mjs`（`npx skills` 管理工具）
- [connsys-jarvis Repo](https://github.com/swchen44/connsys-jarvis)（範例 repo）
