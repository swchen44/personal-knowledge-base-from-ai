---
title: "Multi-Repo 管理利器：repo 工具原理剖析 + Git Worktree 進階實戰"
date: 2026-03-31
category: DevTools
tags:
  - "#tools/git"
  - "#tools/repo"
  - "#devtools/multi-repo"
  - "#git/worktree"
source: "本地實驗紀錄"
source_type: article
author: "swchen"
status: notes
links:
  - "[[GIT-INTERNALS]]"
  - "[[MONOREPO-VS-MULTI-REPO]]"
  - "[[ANDROID-BUILD-SYSTEM]]"
---

## 摘要（Summary）

在大型專案（如 Android AOSP、ChromiumOS）中，程式碼分散在數十甚至數百個 Git repo 裡。Google 的 `repo` 工具解決了跨 repo 同步與管理的問題，但它如何在底層管理 Git 物件？當你想同時在多個分支工作時，`git worktree` 又如何與 `repo` 協同？

本文透過**從零建立本地實驗環境**的方式，帶你看清楚 `repo` 的三層儲存架構，以及如何在 repo-managed 的專案上疊加 `git worktree`，實現「一個 repo、多個工作目錄同時並行」的高效開發模式。

---

## 第一部分：`repo` 工具的管理原理

### 為什麼需要 `repo`？

當一個產品由多個獨立的 Git repo 組成（Multi-repo 架構），開發者每天面對的問題是：

- 如何確保所有 repo 在同一個「快照（snapshot）」狀態？
- 如何跨多個 repo 同時建立 feature branch？
- 如何在 CI 環境中一鍵同步全部 repo？

`repo` 是 Google 為 Android AOSP 開發的 Multi-repo 管理工具，核心概念是：用一個 **manifest XML 檔案**描述所有 repo 的清單與版本，搭配 `repo sync` 一次完成所有 clone/pull 動作。

---

### 實驗環境架構

本文建立了一個完全本地的實驗環境，不需要任何 Git server：

```
~/lab/
├── server/               ← 模擬遠端 server（bare repos）
│   ├── manifest.git      ← manifest repo
│   ├── project-a.git     ← project-a 的遠端
│   └── project-b.git     ← project-b 的遠端
└── workspace/            ← repo sync 後的工作目錄
```

**關鍵技巧**：用 `file://` 協定指向本地 bare repo，`repo` 會把它當作遠端 server 使用，不需要架設 HTTP/SSH server。

---

### 步驟一：建立本地 bare repos（模擬 server）

```bash
# 建立 project-a 的 bare repo
git init --bare ~/lab/server/project-a.git

# 用 temp repo 放入初始 commit 並 push
cd /tmp && mkdir tmp-a && cd tmp-a
git init && git checkout -b main
echo "# Project A" > README.md
echo 'print("Hello from project-a")' > main.py
git add . && git commit -m "Initial commit of project-a"
git remote add origin ~/lab/server/project-a.git
git push origin main

# 同樣方式建立 project-b（含 feature branch）
git init --bare ~/lab/server/project-b.git
cd /tmp && mkdir tmp-b && cd tmp-b
git init && git checkout -b main
echo "# Project B" > README.md
echo 'def helper(): return "I am lib"' > lib.py
git add . && git commit -m "Initial commit of project-b"
git checkout -b feature/awesome
echo "# Awesome feature" > feature.md
git add . && git commit -m "Add awesome feature"
git checkout main
git remote add origin ~/lab/server/project-b.git
git push origin main feature/awesome
```

---

### 步驟二：建立 manifest repo

`repo` 的核心是 `default.xml`，它描述了「這個產品由哪些 repo 組成、各自對應到哪個路徑」：

```bash
git init --bare ~/lab/server/manifest.git

cd /tmp && mkdir tmp-manifest && cd tmp-manifest
git init && git checkout -b main

cat > default.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <!-- 指向本地 server 目錄 -->
  <remote name="origin"
          fetch="file:///Users/yourname/lab/server" />

  <!-- 預設追蹤 main branch -->
  <default remote="origin" revision="main" sync-j="4" />

  <!-- 兩個 project：name=bare repo 名稱，path=workspace 中的路徑 -->
  <project name="project-a" path="apps/project-a" />
  <project name="project-b" path="libs/project-b" />
</manifest>
EOF

git add default.xml && git commit -m "Initial manifest"
git remote add origin ~/lab/server/manifest.git
git push origin main
```

`default.xml` 的關鍵欄位說明：

| 欄位 | 說明 |
|------|------|
| `<remote fetch="...">` | bare repo 的根路徑（可以是 URL 或 `file://` 路徑） |
| `<default revision="main">` | 沒有指定 revision 的 project 預設追蹤此 branch |
| `<project name="..." path="...">` | `name` 對應 `{fetch}/{name}.git`，`path` 是 checkout 位置 |

---

### 步驟三：`repo init` + `repo sync`

```bash
cd ~/lab/workspace

# 初始化：下載 manifest
repo init -u file:///Users/yourname/lab/server/manifest.git -b main --no-clone-bundle

# 同步：clone 所有 project
repo sync --no-clone-bundle
```

`repo sync` 完成後，workspace 結構如下：

```
workspace/
├── .repo/                         ← repo 的「大腦」
│   ├── manifest.xml               ← 當前生效的 manifest（symlink）
│   ├── manifests/                 ← manifest repo 的 checkout
│   ├── manifests.git/             ← manifest repo 的 git dir
│   ├── project-objects/           ← 【第一層】共享 Object Store
│   │   ├── project-a.git/objects  ← 所有 fetch 的 git 物件存這裡
│   │   └── project-b.git/objects
│   └── projects/                  ← 【第二層】per-checkout Git Dir
│       ├── apps/project-a.git/    ← HEAD、refs、index 各自獨立
│       └── libs/project-b.git/
├── apps/project-a/                ← 【第三層】工作目錄
│   └── .git → symlink → .repo/projects/apps/project-a.git
└── libs/project-b/                ← 另一個工作目錄
    └── .git → symlink → .repo/projects/libs/project-b.git
```

---

### `repo` 的三層儲存架構（重點）

這是理解 `repo` 的最核心概念。`repo` 把 Git 儲存拆成三層：

```
┌──────────────────────────────────────────────────────────────┐
│  第三層：工作目錄（Working Directory）                         │
│  apps/project-a/   libs/project-b/                           │
│  .git → symlink ↓  .git → symlink ↓                         │
└──────────────────────────────────────────────────────────────┘
               │                    │
               ▼                    ▼
┌──────────────────────────────────────────────────────────────┐
│  第二層：per-checkout Git Dir（.repo/projects/）              │
│  apps/project-a.git/          libs/project-b.git/            │
│  ├── HEAD        (當前 branch) ├── HEAD                      │
│  ├── refs/       (branch 指標) ├── refs/                     │
│  ├── index       (暫存區)      ├── index                     │
│  └── objects → symlink ↓      └── objects → symlink ↓       │
└──────────────────────────────────────────────────────────────┘
               │                    │
               ▼                    ▼
┌──────────────────────────────────────────────────────────────┐
│  第一層：共享 Object Store（.repo/project-objects/）           │
│  project-a.git/objects    project-b.git/objects              │
│  （所有 commits、trees、blobs 的實體儲存位置）                  │
└──────────────────────────────────────────────────────────────┘
```

**為什麼這樣設計？**

- **第一層共享 objects**：若同一個 repo 需要多個 checkout（不同的 manifest 設定），objects 只存一份，節省空間
- **第二層獨立 HEAD/refs**：每個 checkout 有自己的 branch 狀態，互不干擾
- **第三層 symlink**：讓工作目錄的 `.git` 看起來像普通的 git repo，`git` 指令可以正常執行

用 `ls -la` 驗證 symlink 關係：

```bash
# 工作目錄的 .git 是 symlink
$ ls -la ~/lab/workspace/apps/project-a/.git
lrwxr-xr-x  1 user  staff  39 Mar 31 06:13 .git -> ../../.repo/projects/apps/project-a.git

# .repo/projects 底下的 objects 也是 symlink
$ ls -la ~/lab/workspace/.repo/projects/apps/project-a.git/objects
lrwxr-xr-x  1 user  staff  46 Mar 31 06:13 objects -> ../../../project-objects/project-a.git/objects
```

---

### `repo` 的常用指令速查

```bash
# 初始化 workspace
repo init -u <manifest-url> -b <branch>

# 同步所有 project（拉取最新）
repo sync

# 在指定 project 建立新 branch（類似 git checkout -b）
repo start <branch-name> <project-name>
# 例：repo start feature/login project-a

# 查看所有 project 的狀態（類似 git status）
repo status

# 對所有 project 執行同一個 git 指令
repo forall -c 'echo "[$REPO_PROJECT] $(git branch --show-current)"'

# 查看目前 manifest 設定
repo manifest
```

> [!note] `$REPO_PROJECT`
> 在 `repo forall -c` 的指令裡，`$REPO_PROJECT` 是 manifest 中的 `name` 屬性值，可以用來識別當前執行到哪個 project。

> [!warning] `repo forall` 只跑主工作目錄
> `repo forall` 不會遍歷透過 `git worktree add` 建立的額外工作目錄，這是第二部分要解決的問題。

---

## 第二部分：Git Worktree 進階使用

### 什麼是 Git Worktree？

一般的 Git 用法是「一個 repo、一個工作目錄、同一時間只能 checkout 一個 branch」。但在實際開發中，常常需要：

- 主線繼續開發，同時緊急修復一個 hotfix
- 比較兩個 feature branch 的差異
- 在 feature branch 開發時，需要臨時切到主線查閱某個功能

傳統做法是 `git stash` + `git checkout`，但這會破壞當前工作狀態。`git worktree` 的解法是：**讓同一個 repo 同時 checkout 多個 branch 到不同目錄，共享 git objects 但有各自獨立的工作狀態**。

---

### `git worktree` 的底層原理

```
主工作目錄/
└── .git/                          ← 主 git dir（含 HEAD、refs、index）
    ├── objects/                   ← 【共享】所有 commit/tree/blob
    └── worktrees/
        └── my-feature/            ← 額外 worktree 的 metadata
            ├── HEAD               ← 這個 worktree 的 branch 指標
            ├── index              ← 這個 worktree 的暫存區
            ├── gitdir             ← 回指額外工作目錄的 .git 檔案
            └── commondir          ← 指向主 git dir（共用 objects）

額外工作目錄/
└── .git                           ← 只是一個「gitdir 指標檔」（不是目錄！）
    內容：gitdir: /path/to/主.git/worktrees/my-feature
```

**時序圖：`git worktree add` 的建立流程**

```
用戶                git                  filesystem
 │                   │                       │
 │ git worktree add  │                       │
 │   ../feature-wt   │                       │
 │   feature/new-ui  │                       │
 │──────────────────►│                       │
 │                   │── 建立新目錄 ─────────►│ ../feature-wt/
 │                   │── 寫 .git 指標檔 ─────►│ ../feature-wt/.git
 │                   │   (gitdir: ...)        │   = 純文字檔
 │                   │── 建立 worktrees/ ─────►│ .git/worktrees/feature-wt/
 │                   │   metadata             │   HEAD, index, gitdir, commondir
 │                   │── checkout branch ─────►│ ../feature-wt/ 的檔案內容
 │◄──────────────────│                       │
 │  完成              │                       │
```

---

### 在 `repo`-managed 專案上使用 `git worktree`

> [!important] 關鍵事實
> `repo`-managed 專案的 `.git` 是 **symlink**，不是真實目錄。但 `git worktree add` 完全可以在上面正常運作——git 指令會沿著 symlink 找到真正的 git dir（即 `.repo/projects/{path}.git/`），然後在那裡建立 `worktrees/` 子目錄。

```bash
# 進入 repo-managed 的工作目錄
cd ~/lab/workspace/apps/project-a

# 建立 feature branch
git checkout -b feature/new-ui
echo "new UI code" > ui.py
git add ui.py && git commit -m "Add new UI"
git checkout main

# 建立 worktree（在 workspace 的 worktrees/ 子目錄下）
git worktree add ../../worktrees/project-a-feature feature/new-ui
```

執行後的完整鏈結關係：

```
workspace/worktrees/project-a-feature/
└── .git                            ← 純文字指標檔
    內容：gitdir: /lab/workspace/.repo/projects/apps/project-a.git/worktrees/project-a-feature

.repo/projects/apps/project-a.git/
├── HEAD                            ← 主工作目錄的 branch
├── refs/
├── objects → symlink → .repo/project-objects/project-a.git/objects
└── worktrees/
    └── project-a-feature/
        ├── HEAD                    ← 此 worktree 的 branch（feature/new-ui）
        ├── index                   ← 此 worktree 的暫存區
        ├── commondir               ← "../.." 指回 .repo/projects/apps/project-a.git/
        └── gitdir                  ← 指回 workspace/worktrees/project-a-feature/.git
```

用 `git worktree list` 驗證：

```bash
$ git worktree list
/lab/workspace/.repo/projects/apps/project-a.git  376b8e3 [main]
/lab/workspace/worktrees/project-a-feature         fa6663a [feature/new-ui]
```

> [!note] 為什麼主工作目錄顯示 `.repo/projects/...` 的路徑？
> 因為那才是真正的 git dir（bare-like），`apps/project-a/` 只是透過 symlink 指向它的工作目錄。git 自己知道「主 git dir」在哪裡。

---

### 實際使用場景

#### 場景一：hotfix 與 feature 並行開發

```bash
cd ~/lab/workspace/apps/project-a

# 在 main 的基礎上開 hotfix worktree
git checkout main
git branch hotfix/critical-bug
git worktree add ../worktrees/project-a-hotfix hotfix/critical-bug

# 現在可以同時：
# - apps/project-a/ 繼續在 feature/via-repo 開發
# - worktrees/project-a-hotfix/ 處理緊急 bug，不互相干擾

# 在 hotfix worktree 修好 bug
cd ../worktrees/project-a-hotfix
echo "fix content" > bugfix.py
git add bugfix.py && git commit -m "Fix critical bug"

# 完成後清除 worktree
git worktree remove ../worktrees/project-a-hotfix
git branch -d hotfix/critical-bug
```

#### 場景二：同時對照多個版本

```bash
# 開三個 worktree：v1、v2、main
git worktree add ../compare/v1 tags/v1.0
git worktree add ../compare/v2 tags/v2.0
# 主目錄就是 main

# 三個目錄同時開著，用 diff 工具直接比較
diff ../compare/v1/lib.py ../compare/v2/lib.py
diff ../compare/v2/lib.py ./lib.py
```

#### 場景三：CI/CD 並行測試

```bash
# 不同 branch 的測試可以同時跑，不需要等
git worktree add /tmp/test-branch-a feature/auth
git worktree add /tmp/test-branch-b feature/payment

# 在兩個目錄同時跑測試（background）
(cd /tmp/test-branch-a && pytest) &
(cd /tmp/test-branch-b && pytest) &
wait
```

---

### `git worktree` 常用指令速查

```bash
# 建立新 worktree（branch 必須已存在）
git worktree add <路徑> <branch>

# 建立 worktree 並同時新建 branch
git worktree add -b <新branch名> <路徑> <起點>

# 查看所有 worktree
git worktree list

# 移除 worktree（先確保沒有未 commit 的變更）
git worktree remove <路徑>

# 清理已刪除工作目錄的 worktree 記錄
git worktree prune
```

> [!warning] 同一個 branch 不能被兩個 worktree 同時 checkout
> 嘗試 `git worktree add` 一個已被 checkout 的 branch 會報錯：`fatal: 'feature/x' is already checked out at '...'`。需要先在原 worktree 切換到別的 branch。

---

### `repo sync` 對 `git worktree` 的影響

這是實際使用中最重要的問題：

| 操作 | 對 worktree 的影響 |
|------|-------------------|
| `repo sync` | **完全不影響**。worktree 的 HEAD/index 存在 `.repo/projects/{path}.git/worktrees/` 底下，`repo sync` 只更新主工作目錄的 branch，不觸碰 worktrees/ |
| `repo start` | 只對主工作目錄建立 branch，不影響其他 worktree |
| `repo forall -c` | 只跑主工作目錄，不遍歷 worktrees |
| `repo status` | 只顯示主工作目錄的狀態 |

**結論**：worktree 是純 git 層面的功能，`repo` 不感知也不管理它們。這是設計上的隔離，開發者需要自己追蹤手動建立的 worktrees。

> [!tip] 最佳實踐
> 在 workspace 內建立一個統一的 `worktrees/` 目錄，將所有 worktree 放在裡面。這樣既有清楚的目錄結構，又不會被 `repo sync` 干擾：
> ```
> workspace/
> ├── apps/           ← repo sync 管理的主工作目錄
> ├── libs/
> ├── .repo/
> └── worktrees/      ← 自行管理的 worktree 目錄（不被 repo 管轄）
>     ├── project-a-feature/
>     └── project-a-hotfix/
> ```

---

### 完整架構總覽

```
lab/server/（bare repos — 模擬遠端）
├── manifest.git
├── project-a.git
└── project-b.git

lab/workspace/（repo sync 管理的工作區）
├── .repo/
│   ├── project-objects/           ← git objects 實體（共享）
│   │   ├── project-a.git/objects
│   │   └── project-b.git/objects
│   └── projects/                  ← git dir（HEAD、refs、index）
│       ├── apps/project-a.git/
│       │   ├── HEAD               ← 主工作目錄的 branch
│       │   ├── objects ──symlink──► project-objects/project-a.git/objects
│       │   └── worktrees/
│       │       └── project-a-feature/   ← worktree metadata
│       │           ├── HEAD        ← 此 worktree 的 branch
│       │           ├── index
│       │           └── commondir   ← 回指 .repo/projects/apps/project-a.git/
│       └── libs/project-b.git/
│
├── apps/project-a/                ← 主工作目錄（.git 是 symlink）
│   └── .git ──symlink──► .repo/projects/apps/project-a.git/
│
├── libs/project-b/
│   └── .git ──symlink──► .repo/projects/libs/project-b.git/
│
└── worktrees/                     ← 自行管理的 worktree 目錄
    └── project-a-feature/         ← git worktree add 建立
        └── .git                   ← 純文字 gitdir 指標檔
            → .repo/projects/apps/project-a.git/worktrees/project-a-feature/
```

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | `repo init`、`repo sync`、`repo start`、`repo forall`；`git worktree add/list/remove/prune`；`.repo/project-objects/`、`.repo/projects/`、三層儲存架構 |
| **理解（半被動）** | 解釋概念含義及關聯 | `repo` 把 git 儲存拆為三層：objects 共享（節省空間）、git dir 獨立（各自狀態）、工作目錄透過 symlink 連結。`git worktree` 在此架構上額外新增 `worktrees/` metadata，兩者互不干擾 |
| **分析（主動）** | 檢驗論點、找出假設 | 核心假設：使用者自己追蹤 worktrees；`repo forall` 不感知 worktrees 是設計限制，在需要對所有工作樹批次操作時必須自行撰寫 shell script 遍歷；symlink 架構在跨 filesystem 場景可能失效 |
| **應用（主動）** | 將知識套用情境 | 1. CI/CD 並行測試：用 `git worktree add` 對同一 repo 的不同 branch 同時跑測試；2. hotfix 工作流：不需要 `git stash`，直接開新 worktree 修 bug；3. 多版本對照：同時 checkout v1/v2/main 比較差異 |
| **評估（主動）** | 判斷方案優劣，進行取捨 | `repo` 的 symlink 架構比 `git submodule` 更透明，比 monorepo 更靈活；但 `git worktree` 需要手動管理生命週期，若 worktree 目錄意外刪除需要 `git worktree prune` 清理，有維護成本 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思：

- **澄清**：「`.git` 是 symlink」和「`.git` 是 gitdir 指標檔」這兩種機制有何不同？在什麼情況下 git 用前者、什麼情況用後者？
- **假設**：本文的三層架構論點成立的前提是「所有 checkout 都在同一個 filesystem 上」。如果跨 NFS 或 Docker volume，symlink 行為會改變嗎？
- **證據**：`repo sync` 不影響 worktrees 這個結論是在 repo 2.62 版本實測的，更早期的版本（如 2.x 之前）是否有不同行為？
- **觀點**：若站在「monorepo 支持者」的立場，他們會如何批評 `repo` + `worktree` 的方案？管理複雜度是否真的比 monorepo 低？
- **後果**：若一個大型團隊（50人+）廣泛採用 `git worktree`，12 個月後在 CI/CD 系統、code review 流程、磁碟管理上可能出現什麼新的複雜度？

### 方案批判三問

> [!warning] 這個方案在以下情況需要特別注意

1. **最大的風險是什麼？**
   - 工作目錄的 `.git` 是 symlink，若 `.repo/` 目錄結構被意外破壞（如誤刪），**所有 worktrees 的 git 狀態都會失效**，因為它們共享同一個 git dir
   - `repo sync` 在某些版本可能會 rebase 主工作目錄，若 worktree 的 branch 基於相同 commit，可能需要手動 rebase worktree

2. **什麼情況下會失敗？**
   - **跨 filesystem**：`git worktree add` 的路徑跨 filesystem（如另一個硬碟），symlink 仍可運作，但 `commondir` 的相對路徑會失效
   - **Windows**：symlink 在 Windows 需要管理員權限，`repo` 的三層 symlink 架構在 Windows 開發環境上支援有限
   - **IDE 整合**：部分 IDE（如舊版 IntelliJ）無法正確識別 symlink `.git`，可能導致 git 功能失效

3. **有沒有更好的替代方案？**
   - **git submodule**：內建於 git，不需額外工具，但版本鎖定是手動的，更新繁瑣
   - **monorepo（如 Bazel + single repo）**：完全消除跨 repo 同步問題，但 repo 規模增長後 clone 時間極長
   - **`git worktree` vs `git clone --local`**：`--local` clone 也會共享 objects，但建立 overhead 更高且不共享 refs 更新

---

## 我的心得（My Takeaways）

1. **`repo` 的設計比想象中更聰明**：三層架構（objects / git-dir / working-dir）完全解耦，讓多個 checkout 共享 object store 成為可能，這個設計思路可以借鑒到其他工具的設計中

2. **symlink 是 `repo` 的核心魔法**：理解了「`.git` 是 symlink 指向 `.repo/projects/`」，所有 git 指令在 repo-managed 目錄下能正常工作的原因就清楚了

3. **`git worktree` 和 `repo` 互補而非衝突**：`repo` 管理「哪些 repo、哪些版本」，`worktree` 管理「同一個 repo 的多個並行工作狀態」，兩者解決不同層次的問題

4. **本地 bare repo 是最好的實驗工具**：不需要 GitHub、不需要 server，`file://` 協定 + bare repo 就能模擬完整的 push/fetch 流程

---

## 相關連結（Related）

- [[GIT-INTERNALS]] — git 底層物件模型（commits、trees、blobs）的詳細說明
- [[MONOREPO-VS-MULTI-REPO]] — monorepo 與 multi-repo 的架構選型討論
- [[ANDROID-BUILD-SYSTEM]] — AOSP 的 repo 使用實踐，以及 `repo upload` 與 Gerrit 的整合

## References

- [Google repo tool 官方文件](https://gerrit.googlesource.com/git-repo)
- [git-worktree 官方手冊](https://git-scm.com/docs/git-worktree)
- 本地實驗環境：`~/lab/`（repo 2.62 + git 2.39.5 on macOS 24.3.0）
