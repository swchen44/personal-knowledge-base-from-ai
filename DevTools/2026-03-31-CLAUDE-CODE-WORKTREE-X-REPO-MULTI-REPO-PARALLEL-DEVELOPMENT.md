---
title: "Claude Code Worktree × repo Multi-Repo 並行開發完全指南"
date: 2026-03-31
category: DevTools
tags:
  - "#tools/claude-code"
  - "#tools/repo"
  - "#git/worktree"
  - "#devtools/multi-repo"
  - "#devtools/parallel-development"
source: "本地實驗紀錄"
source_type: article
author: "swchen"
status: notes
links:
  - "[[2026-03-31-REPO-MULTI-REPO-MANAGEMENT-AND-GIT-WORKTREE-ADVANCED-GUIDE]]"
  - "[[GIT-INTERNALS]]"
  - "[[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]]"
---

> **前置閱讀**：本文是 [[2026-03-31-REPO-MULTI-REPO-MANAGEMENT-AND-GIT-WORKTREE-ADVANCED-GUIDE]] 的續集，建議先閱讀了解 `repo` 的三層儲存架構與 git worktree 原理。

## 摘要（Summary）

`Claude Code` 從 v2.1.50 起原生支援 `--worktree` 旗標，讓每個 Claude session 有獨立的工作目錄，AI agent 可以並行工作而不互相干擾。當這個能力碰上 `repo` Multi-repo 管理時，架構變得更為立體——本文透過**完整的本地實驗**，揭示三層 worktree 巢狀結構的底層邏輯、WorktreeCreate/WorktreeRemove hooks 的客製化方式，以及在 Multi-repo 環境下協調跨 project 並行開發的最佳實踐。

---

## 第一部分：底層邏輯與實驗

### Claude Code `--worktree` 的運作原理

當你執行 `claude --worktree feature-auth` 時，Claude Code 做了以下幾件事：

```
1. git rev-parse --show-toplevel → 找到 git root
2. git symbolic-ref refs/remotes/origin/HEAD → 取得預設 base branch
3. git worktree add -b worktree-<name> <root>/.claude/worktrees/<name> origin/<base>
4. cd 到新 worktree 目錄，啟動 Claude session
```

**預設 worktree 路徑**：`<git-root>/.claude/worktrees/<name>/`
**預設 branch 名稱**：`worktree-<name>`（追蹤 `origin/HEAD` 所指的分支）

> [!warning] 常見陷阱：origin/HEAD 未設定
> 本地 bare repo（或剛 clone 的 repo）可能沒有設定 `origin/HEAD`，導致 `claude --worktree` 找不到 base branch。
> 解決方法：
> ```bash
> git remote set-head origin -a   # 自動偵測遠端預設 branch
> # 或
> git remote set-head origin main  # 手動指定
> ```

---

### 在 repo `--worktree` 模式下的三層巢狀結構

這是本文最核心的實驗發現。當 `repo init --worktree` + `claude --worktree` 同時使用時，會形成**三層 worktree 巢狀**：

```
workspace-wt/（repo --worktree 模式）
│
├── .repo/worktrees/project-a.git/        ← 【層 1】bare git dir（repo 管理）
│   ├── objects/                           ← 所有 layers 共享的 object store
│   └── worktrees/                         ← git worktree metadata
│       ├── project-a/                     ← 層 2 的 metadata（locked）
│       │   ├── HEAD  → feature/wt-experiment
│       │   └── refs/worktree/m/main       ← repo 的 pseudo-ref（per-worktree）
│       └── feature-auth/                  ← 層 3 的 metadata
│           ├── HEAD  → worktree-feature-auth
│           └── commondir → ../..          ← 回指層 1
│
├── apps/project-a/                        ← 【層 2】repo 主工作目錄
│   └── .git  (gitdir 指標檔)
│       → .repo/worktrees/project-a.git/worktrees/project-a
│
└── apps/project-a/.claude/worktrees/
    └── feature-auth/                      ← 【層 3】Claude Code worktree
        └── .git  (gitdir 指標檔)
            → .repo/worktrees/project-a.git/worktrees/feature-auth
```

**關鍵洞察**：不論有幾層 worktree，所有層都共享同一個 `objects/` 目錄。層 2 和層 3 的 `.git` 都是純文字的 gitdir 指標檔，最終都指向層 1 的 bare git dir。

用 `git worktree list` 從任一層都能看到全貌：

```bash
$ cd apps/project-a && git worktree list

# 層 1：bare git dir（detached HEAD）
.repo/worktrees/project-a.git                    376b8e3 (detached HEAD)

# 層 2：repo 管理的主工作目錄（locked，防止誤刪）
../../../../../apps/project-a                    4c87a81 [feature/wt-experiment] locked

# 層 3：claude --worktree 建立的工作目錄
apps/project-a/.claude/worktrees/feature-auth    376b8e3 [worktree-feature-auth]
```

---

### tmux 實驗：模擬多 Claude Agent 並行工作

在實際開發中，會用 tmux 開多個 pane，每個 pane 是一個獨立的 Claude session：

```bash
# 建立三 pane 的 tmux session
tmux new-session -d -s claude-wt-lab -x 220 -y 50
tmux split-window -h -t claude-wt-lab       # 左右分割
tmux split-window -v -t claude-wt-lab:0.0  # 左側再上下分割

# Pane 0（左上）：repo workspace 主控
tmux send-keys -t claude-wt-lab:0.0 "cd ~/workspace && repo forall -c 'echo [\$REPO_PROJECT] \$(git branch --show-current)'" Enter

# Pane 1（左下）：project-a 的 Claude session
tmux send-keys -t claude-wt-lab:0.1 "cd apps/project-a && claude --worktree feature-auth" Enter

# Pane 2（右）：project-b 的 Claude session（同一個 feature 的另一個 project）
tmux send-keys -t claude-wt-lab:0.2 "cd libs/project-b && claude --worktree feature-auth" Enter
```

tmux 實驗截圖輸出（`tmux capture-pane` 的實際結果）：

```
# Pane 1（project-a worktree）工作中：
[worktree-feature-auth 4d0668a] feat: OAuth2 implementation [claude-worktree]
 1 file changed, 1 insertion(+)
 create mode 100644 auth.py

# Pane 2（project-b worktree）同時工作：
[worktree-feature-auth 6fcce6f] feat: auth helper lib for project-b [claude-worktree]
 1 file changed, 1 insertion(+)
 create mode 100644 auth_helper.py
```

兩個 Claude session 各自在不同 project 的 `worktree-feature-auth` branch 上獨立工作，commits 完全隔離。

---

### WorktreeCreate / WorktreeRemove Hooks

Claude Code 提供兩個 hook 事件讓你完全自訂 worktree 的建立與清除行為：

#### Hook 事件說明

| 事件 | 觸發時機 | 能否阻擋 | 用途 |
|------|---------|---------|------|
| `WorktreeCreate` | `claude --worktree` 或 subagent `isolation: worktree` | ✅ 可以（透過 exit code 和 stdout 控制） | 自訂路徑、複製 .env、初始化 DB |
| `WorktreeRemove` | session 結束或 subagent 完成 | ❌ 不行（失敗只記 debug log） | 清理 DB、清理暫存資源 |

#### Input / Output 格式

**WorktreeCreate** stdin：
```json
{
  "hook_event_name": "WorktreeCreate",
  "session_id": "abc123",
  "cwd": "/path/to/project",
  "name": "feature-auth"
}
```

**WorktreeCreate** stdout（必須輸出 worktree 的絕對路徑）：
```
/path/to/project/.claude/worktrees/feature-auth
```

**WorktreeRemove** stdin：
```json
{
  "hook_event_name": "WorktreeRemove",
  "session_id": "abc123",
  "cwd": "/path/to/project",
  "worktree_path": "/path/to/project/.claude/worktrees/feature-auth"
}
```

#### settings.json 配置

```json
{
  "hooks": {
    "WorktreeCreate": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/worktree-create.sh",
            "timeout": 30
          }
        ]
      }
    ],
    "WorktreeRemove": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/worktree-remove.sh",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

> [!warning] 已知 Bug（v2.1.72）
> 在 session 內部用 `EnterWorktree` 工具（或 Agent `isolation: worktree`）時，會**忽略** WorktreeCreate/WorktreeRemove hooks，直接呼叫原生 `git worktree add`。這個 bug 已被回報（#36205）。目前只有 `claude --worktree` CLI flag 能觸發 hooks。

---

## 第二部分：實戰最佳實踐

### 架構一：單一 project 的 Claude 並行 Agent

最簡單的場景：同一個 git repo，多個 Claude session 各跑一個 feature。

```
project-a/
├── .git
├── src/
└── .claude/worktrees/
    ├── feature-auth/      ← Claude Session 1
    ├── feature-payment/   ← Claude Session 2
    └── bugfix-crash/      ← Claude Session 3（hotfix）
```

```bash
# 同時啟動三個 Claude session
claude --worktree feature-auth    # 終端機 1
claude --worktree feature-payment # 終端機 2
claude --worktree bugfix-crash    # 終端機 3
```

每個 session 在獨立 branch 工作，不需要 `git stash`，隨時可以切換注意力。

---

### 架構二：repo Multi-repo × Claude 跨 project 並行

當一個 feature 橫跨多個 repo（如前端 + 後端 + 共用 lib），這是最能發揮 repo + Claude 組合優勢的場景：

```
workspace-wt/（repo --worktree 模式）
├── apps/project-frontend/
│   └── .claude/worktrees/feature-new-login/   ← Claude Session A
├── apps/project-backend/
│   └── .claude/worktrees/feature-new-login/   ← Claude Session B
└── libs/project-auth-lib/
    └── .claude/worktrees/feature-new-login/   ← Claude Session C
```

**操作流程**：

```bash
# 步驟 1：repo start 在所有 project 建立同名 branch
cd workspace-wt
repo start feature/new-login project-frontend project-backend project-auth-lib

# 步驟 2：在各 project 啟動 Claude worktree session
cd apps/project-frontend && claude --worktree new-login   # tmux pane 1
cd apps/project-backend && claude --worktree new-login    # tmux pane 2
cd libs/project-auth-lib && claude --worktree new-login   # tmux pane 3

# 步驟 3：各 Claude session 各自工作，最後在主工作目錄 merge
cd apps/project-frontend
git merge worktree-new-login
git push

# 步驟 4：清理
git worktree remove .claude/worktrees/new-login
git branch -d worktree-new-login
```

---

### WorktreeCreate Hook 進階腳本（repo 環境版）

以下是針對 repo 環境客製的 `worktree-create.sh`，處理了 `origin/HEAD` 未設定的問題，並自動複製 `.env`：

```bash
#!/usr/bin/env bash
# .claude/hooks/worktree-create.sh
# WorktreeCreate hook for repo --worktree workspace

set -euo pipefail

INPUT=$(cat)
HOOK_EVENT=$(echo "$INPUT" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('hook_event_name',''))")
CWD=$(echo "$INPUT" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('cwd',''))")
NAME=$(echo "$INPUT" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('name',''))")

[ "$HOOK_EVENT" = "WorktreeCreate" ] || exit 0

GIT_ROOT=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || echo "$CWD")
WORKTREE_PATH="$GIT_ROOT/.claude/worktrees/$NAME"
BRANCH_NAME="worktree-$NAME"

# 確保 origin/HEAD 已設定（repo bare repo 初始可能沒有）
git -C "$CWD" remote set-head origin -a 2>/dev/null || true
BASE=$(git -C "$CWD" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
  | sed 's|refs/remotes/origin/||' || echo "main")

# 建立 worktree（若已存在則重用）
mkdir -p "$GIT_ROOT/.claude/worktrees"
if [ -d "$WORKTREE_PATH" ]; then
  : # 已存在，直接重用
elif git -C "$CWD" show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
  # branch 已存在但目錄不在
  git -C "$CWD" worktree add "$WORKTREE_PATH" "$BRANCH_NAME" 2>/dev/null
else
  # 全新建立
  git -C "$CWD" worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" "origin/$BASE"
fi

# 複製 .env（gitignored 的設定檔）
for f in .env .env.local .env.development; do
  [ -f "$GIT_ROOT/$f" ] && cp "$GIT_ROOT/$f" "$WORKTREE_PATH/$f" || true
done

# 輸出路徑（Claude Code 必須讀到這個）
echo "$WORKTREE_PATH"
```

```bash
#!/usr/bin/env bash
# .claude/hooks/worktree-remove.sh

set -euo pipefail

INPUT=$(cat)
WORKTREE_PATH=$(echo "$INPUT" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('worktree_path',''))")

[ -n "$WORKTREE_PATH" ] && [ -d "$WORKTREE_PATH" ] || exit 0

GIT_ROOT=$(git -C "$WORKTREE_PATH" rev-parse --show-toplevel 2>/dev/null || true)
BRANCH=$(git -C "$WORKTREE_PATH" branch --show-current 2>/dev/null || true)

git -C "${GIT_ROOT:-$WORKTREE_PATH}" worktree remove --force "$WORKTREE_PATH" 2>/dev/null || true

# 清除 worktree-* 分支
[[ "$BRANCH" == worktree-* ]] && \
  git -C "${GIT_ROOT:-$WORKTREE_PATH}" branch -D "$BRANCH" 2>/dev/null || true
```

---

### `.worktreeinclude` 自動複製 gitignored 檔案

Claude Code 內建支援 `.worktreeinclude` 檔案（使用 `.gitignore` 語法），列出的檔案在建立 worktree 時會自動複製：

```text
# .worktreeinclude（放在 project git root）
.env
.env.local
config/secrets.json
demo/
*.user
```

> [!note] `.worktreeinclude` vs Hook
> - **`.worktreeinclude`**：簡單易用，只複製檔案
> - **WorktreeCreate hook**：完全自訂，可以執行任意腳本（如初始化 DB、安裝依賴）
> - 兩者**不能同時使用**：設定了 WorktreeCreate hook 後，`.worktreeinclude` 會被忽略，需在 hook 腳本裡手動處理複製邏輯

---

### Subagent worktree isolation

在 Claude Code 的自訂 subagent（`.claude/agents/` 目錄下的 markdown 檔）中，可以設定 `isolation: worktree`，讓每個 subagent 在獨立 worktree 中執行：

```markdown
---
name: feature-implementer
description: 實作新功能的 subagent，使用 worktree 隔離
isolation: worktree
tools:
  - Read
  - Write
  - Bash
---

你是一個專注於實作功能的 subagent。你在獨立的 worktree 中工作，完成後你的 worktree 會被自動清理（若沒有 commit）。
```

啟動方式：

```bash
# 明確要求 Claude 使用 worktrees
claude -p "用 worktrees 讓你的 agents 並行處理以下三個 feature..."

# 或在 claude 對話中
> 使用 worktrees 為每個功能啟動獨立的 subagent
```

---

### 完整操作流程最佳實踐

#### 情境一：跨 repo 的 feature 開發（最常見）

```bash
# 1. 確保 workspace 使用 repo --worktree 模式
cd workspace-wt
cat .repo/manifest.xml  # 確認 manifest

# 2. 確認所有 project 的 origin/HEAD 都設定好
repo forall -c 'git remote set-head origin -a 2>/dev/null; echo "[$REPO_PROJECT] origin/HEAD: $(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed s|refs/remotes/origin/||)"'

# 3. 用 repo start 在所有 project 建立統一的開發 branch
repo start feature/new-payment-flow project-a project-b

# 4. 在各 project 啟動 Claude worktree session（tmux）
tmux new-session -d -s dev -x 220 -y 50
tmux split-window -h -t dev
tmux send-keys -t dev:0.0 "cd apps/project-a && claude --worktree payment-flow" Enter
tmux send-keys -t dev:0.1 "cd libs/project-b && claude --worktree payment-flow" Enter

# 5. 工作完成後合併回 feature branch
cd apps/project-a
git checkout feature/new-payment-flow
git merge worktree-payment-flow

# 6. 清理 claude worktrees
git worktree remove .claude/worktrees/payment-flow
git branch -d worktree-payment-flow

# 7. repo upload 準備 code review（若有 Gerrit）
repo upload
```

#### 情境二：緊急 hotfix（不中斷 feature 工作）

```bash
# feature 開發中的 worktree 繼續跑著
# 在同一個 project 另開 hotfix worktree
cd apps/project-a
claude --worktree hotfix-login-crash

# hotfix 做完，merge 到 main 並 push
cd .claude/worktrees/hotfix-login-crash
git checkout main  # 注意：這會失敗，因為同一 branch 不能兩個 worktree
# 正確做法：在主工作目錄操作
cd apps/project-a        # 主工作目錄在 feature 上
git fetch origin
git checkout -b hotfix-login-crash-merge origin/main
git merge worktree-hotfix-login-crash
git push origin hotfix-login-crash-merge
```

---

### 操作注意事項與限制

| 限制 | 說明 | 解決方法 |
|------|------|---------|
| **同 branch 不能雙 worktree** | 兩個 worktree 不能 checkout 同一個 branch | 永遠用新 branch 建立 worktree |
| **origin/HEAD 必須設定** | repo bare repo 初始沒有 origin/HEAD | `git remote set-head origin -a` |
| **`locked` worktree 保護** | repo 的主工作目錄有 `locked`，`git worktree remove` 無效 | 這是 repo 的設計，不要手動刪 |
| **EnterWorktree 忽略 hooks** | 在 session 內用 EnterWorktree 不觸發 WorktreeCreate hook | 用 `claude --worktree` CLI flag 取代 |
| **`.worktreeinclude` 被 hook 覆蓋** | 設定 hook 後 `.worktreeinclude` 失效 | 在 hook 腳本裡手動 cp |
| **`repo forall` 不感知 worktrees** | `repo forall` 只跑主工作目錄 | 自己用 `find` 遍歷 .claude/worktrees/ |
| **`.claude/worktrees/` 加 .gitignore** | worktree 內容會出現在主 repo 的 untracked 裡 | 加 `.gitignore` 忽略 `.claude/worktrees/` |

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 對本文的具體應用 |
|---------|--------------|
| **記憶** | `claude --worktree <name>`、WorktreeCreate/WorktreeRemove hook 事件名、預設路徑 `.claude/worktrees/`、`isolation: worktree`、`.worktreeinclude` 語法 |
| **理解** | 三層 worktree 巢狀的原理：repo bare git dir（層1） → repo 主工作目錄（層2） → Claude worktree（層3），三層共享同一 objects store，.git 都是 gitdir 指標檔 |
| **分析** | 核心假設：每個 worktree 對應一個獨立的 branch。限制：origin/HEAD 必須先設定；EnterWorktree 的 hook bug；`.worktreeinclude` 與 hook 互斥 |
| **應用** | 1. 跨 repo feature：`repo start` 建統一 branch + `claude --worktree` 在各 project 並行；2. hotfix 不中斷 feature：同一 project 開兩個不同名的 worktree；3. WorktreeCreate hook 自動複製 .env |
| **評估** | 優勢：AI agent 真正隔離，無 `git stash` 需求，objects 共享節省空間；缺點：三層架構複雜度高，需要手動管理 worktree 生命週期，EnterWorktree hook bug 未修 |

### 分析型追問（Socratic Follow-up）

- **澄清**：`claude --worktree` 建立的 branch `worktree-<name>` 和 `repo start` 建立的 `feature/<name>` 之間是什麼關係？什麼時候要 merge，什麼時候應該讓它們獨立？
- **假設**：本文假設所有 Claude session 都在不同目錄工作。但如果兩個 Claude session 在同一 worktree 目錄同時寫同一個檔案，會發生什麼？
- **證據**：「三層架構共享 objects store」這個結論是在 repo 2.62 + git 2.39.5 測試的，不同版本的 git 對 `worktreeConfig = true` 的處理是否一致？
- **觀點**：有人主張「直接用多個 git clone 比 worktree 更簡單可靠，不需要管這些複雜性」。這個觀點在什麼情況下是對的？
- **後果**：如果一個 50 人的 AOSP 開發團隊全面採用這套架構，磁碟管理、CI/CD 配置、code review 流程會有什麼新的複雜度？

### 方案批判三問

> [!warning] 這個方案的風險與限制

1. **最大的風險**：三層巢狀結構下，若 `.repo/worktrees/project-a.git/` 目錄被意外破壞或 `repo sync --force-sync` 重置，**所有三層的 worktree 狀態都會消失**，包括 Claude session 的 uncommitted 工作。建議在重要的 Claude worktree 中頻繁 commit，或用 `git stash` 先保存。

2. **什麼情況會失敗**：
   - `origin/HEAD` 未設定（local bare repo 預設沒有）
   - 試圖在 `repo sync` 正在執行時操作 worktree（race condition）
   - Claude session 在 worktree 裡跑耗時操作時，另一個 `repo sync` 可能更新 objects，導致 HEAD 指向的 commit 在 GC 後消失

3. **替代方案**：
   - **多個獨立 workspace**（`repo sync` 到不同目錄）：隔離更徹底，但磁碟佔用翻倍，需維護多份 manifest sync
   - **Git clone --reference**（shared object store 但完全獨立 git dir）：比 worktree 更安全，但不能切 branch，適合 read-only 對比
   - **DevContainer/Docker per worktree**：真正的檔案系統隔離，配合 Claude Code 的 devcontainer 支援，但 overhead 更大

---

## 我的心得（My Takeaways）

1. **`claude --worktree` 建立的是標準 git worktree**，和手動 `git worktree add` 完全等價。知道這一點後，所有關於 git worktree 的知識都可以直接套用

2. **三層巢狀不是 repo 的問題，而是架構演進的自然結果**：repo 用 worktree 替代 symlink（層 1→2），Claude 再用 worktree 建立 AI session 隔離（層 2→3）。每一層都解決不同粒度的問題

3. **WorktreeCreate hook 是連接 Claude Code 和 repo 環境的橋樑**：透過 hook，可以讓 `claude --worktree` 感知 repo 環境的特殊需求（如自動設定 origin/HEAD、複製 .env）

4. **tmux 是這套工作流的完美搭檔**：多個 Claude session 在不同 pane 並行工作，用 `tmux capture-pane` 可以截圖記錄過程，`tmux send-keys` 可以批量控制所有 session

5. **EnterWorktree hook bug 是重要的已知限制**：目前在 session 內用 AI 自動觸發 worktree 時不走 hook，這讓 DB 隔離、自訂路徑等進階用法只能透過 CLI flag 而非 agent 自主決策觸發

---

## 相關連結（Related）

- [[2026-03-31-REPO-MULTI-REPO-MANAGEMENT-AND-GIT-WORKTREE-ADVANCED-GUIDE]] — 本文的前篇，repo 三層架構與 git worktree 原理
- [[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]] — Claude Code Hooks 完整指南，含 WorktreeCreate 詳解
- [[GIT-INTERNALS]] — git objects、refs、worktree 底層機制

## References

- [Claude Code common-workflows: Parallel sessions with git worktrees](https://code.claude.com/docs/en/common-workflows)
- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- [Boris Cherny: Introducing built-in git worktree support for Claude Code](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj/)
- [Creating worktrees with Claude Code in a custom directory](https://www.sabatino.dev/creating-worktrees-with-claude-code-in-a-custom-directory/)
- [Replacing My Custom Git Worktree Skill with Claude Code Hooks](https://mattbrailsford.dev/replacing-my-custom-git-worktree-skill-with-claude-code-hooks)
- [Extending Claude Code Worktrees for True Database Isolation](https://www.damiangalarza.com/posts/2026-03-10-extending-claude-code-worktrees-for-true-database-isolation/)
- [Bug #36205: EnterWorktree ignores WorktreeCreate/WorktreeRemove hooks](https://github.com/anthropics/claude-code/issues/36205)
- 本地實驗環境：`~/lab/workspace-wt/`（Claude Code, repo 2.62, git 2.39.5, tmux 3.6a on macOS 24.3.0）
