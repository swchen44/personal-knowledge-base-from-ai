---
title: "ClawTeam — Agent 蜂群智能框架程式碼深度分析"
date: 2026-03-17
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#python"
  - "#ai/agent"
  - "#ai/multi-agent"
  - "#tools/cli"
source: "https://github.com/HKUDS/ClawTeam"
source_type: code
author: "HKUDS"
status: notes
links:
  - "[[CLAUDE-CODE-AGENT]]"
  - "[[MULTI-AGENT-SYSTEMS]]"
  - "[[AI-ORCHESTRATION]]"
github_stars: 1898
github_language: Python
---

## 摘要（Summary）

ClawTeam 是一個以 CLI 為核心的多代理人（Multi-Agent）協作框架，讓 AI Agent 能夠自我組織成蜂群（Swarm），分工合作完成複雜任務。核心設計哲學是「零基礎設施」——所有狀態存成本地 JSON 檔案，透過 tmux 視覺化監控，不需要 Redis、Docker 或雲端 API。

截至 2026-03-20，發布僅三天就累積 **1,898 Stars**，顯示社群對 Agent 蜂群自動化的強烈需求。

## Why — 為什麼存在？

> 現有 AI Agent 功能強大，但各自孤立運作。面對複雜任務，人類必須手動協調多個 Agent，切換上下文（Context），拼接零散結果——這是痛點所在。

- **核心動機**：讓 AI Agent 自主形成團隊、分配任務、互相溝通，不需要人類介入協調
- **取代/改善什麼**：取代 LangChain、AutoGen 等框架中需要人類撰寫協調程式碼（orchestration code）的模式；改善「單一 Agent 上下文視窗（Context Window）有限」的瓶頸
- **目標用戶**：使用 Claude Code、Codex 等 CLI Agent 的開發者與 AI 研究者

## What — 是什麼？

- **主要功能**：
  - Leader Agent 自動生成 Worker Agent（`clawteam spawn`）
  - 每個 Worker 取得獨立的 git worktree 與 tmux 視窗
  - 共享看板（Kanban）任務系統，支援依賴鏈（`--blocked-by`）
  - 點對點訊息信箱（Inbox），支援 File-based 或 ZeroMQ P2P 傳輸（Transport）
  - TOML 模板一鍵啟動完整團隊（如 7-Agent 對沖基金）
  - Web UI 即時監控儀表板（Dashboard）

- **不做什麼（Non-goals）**：
  - 不是 LLM 框架（不處理 prompt chaining 或 RAG）
  - 不提供 Agent 本身的智能（Agent 仍需外部 CLI 工具如 claude、codex）
  - 不做雲端部署或身份驗證（v1.0 路線圖才規劃）

- **技術棧（Tech Stack）**：Python 3.10+、Typer（CLI）、Pydantic（資料驗證）、Rich（終端渲染）、tmux、ZeroMQ（選用 P2P 傳輸）

## How — 如何運作？

> [!important] 本節包含系統架構圖、執行流程圖與時序圖，讓你不看程式碼也能理解系統全貌。

### 系統架構圖（System Architecture）

```
  ┌─────────────────────────────────────────────────────────┐
  │                    ClawTeam CLI                         │
  │   spawn │ task │ inbox │ board │ workspace │ lifecycle   │
  └─────────────────────┬───────────────────────────────────┘
                        │
          ┌─────────────▼─────────────┐
          │       Core Modules        │
          │                           │
          │  ┌──────────┐ ┌────────┐  │
          │  │  spawn/  │ │ team/  │  │
          │  │ TmuxBack │ │Manager │  │
          │  │ SubprocB │ │TaskStr │  │
          │  │ Adapters │ │Mailbox │  │
          │  └────┬─────┘ └───┬────┘  │
          │       │           │       │
          │  ┌────▼───────────▼────┐  │
          │  │    transport/       │  │
          │  │  FileTransport      │  │
          │  │  P2PTransport(ZMQ)  │  │
          │  └─────────┬───────────┘  │
          └────────────┼──────────────┘
                       │
          ┌────────────▼──────────────┐
          │    ~/.clawteam/           │
          │  ├── teams/               │
          │  │    └── {team}/         │
          │  │         ├── config.json│
          │  │         └── inboxes/   │
          │  ├── tasks/{team}/        │
          │  │    └── task-{id}.json  │
          │  ├── workspaces/          │
          │  ├── sessions/            │
          │  └── costs/               │
          └───────────────────────────┘
```

### 執行流程圖（Execution Flowchart）

```
 Human: "Build a web app"
   │
   ▼
[Leader Agent (Claude Code)]
   │
   ├─► clawteam team spawn-team webapp
   │       │
   │       ▼
   │   [team/manager.py] 建立 config.json + inboxes/
   │
   ├─► clawteam task create webapp "Design API" -o architect
   │       │
   │       ▼
   │   [team/tasks.py] TaskStore.create() → task-{id}.json
   │
   ├─► clawteam spawn --agent-name architect --task "..."
   │       │
   │       ├─ [spawn/adapters.py] 正規化命令（claude/codex/nanobot）
   │       ├─ [workspace/manager.py] 建立 git worktree
   │       ├─ [spawn/prompt.py] 注入 Identity + Task + Coordination Protocol
   │       └─ [spawn/tmux_backend.py] 啟動 tmux 視窗
   │               │
   │               ├─ 偵測 workspace trust prompt → 自動 Enter 確認
   │               ├─ 等待 Claude Ready（輪詢 ❯ 符號）
   │               └─ paste-buffer 注入提示詞（Prompt）
   │
   ▼
[Worker Agent 執行中]
   │
   ├─► clawteam task update webapp T1 --status completed
   │       │
   │       └─ [tasks.py] _resolve_dependents_unlocked()
   │           → 自動解除依賴 T2、T3 的 blocked 狀態
   │
   ├─► clawteam inbox send webapp leader "Done: API schema at docs/api.yaml"
   │       │
   │       └─ [transport/file.py] FileTransport.deliver()
   │           → msg-{ts}-{uid}.json 原子寫入（tmp + rename）
   │
   └─► clawteam lifecycle idle webapp
           └─ 通知 Leader 可接受新任務
```

### 時序圖（Sequence Diagram）

```
 Human      Leader        ClawTeam          Worker1      Worker2
   │           │              │                │             │
   │──提示────►│              │                │             │
   │           │──spawn-team─►│                │             │
   │           │◄─team created│                │             │
   │           │──spawn w1───►│                │             │
   │           │              │──git worktree──►│            │
   │           │              │──tmux window───►│            │
   │           │              │──inject prompt─►│            │
   │           │──spawn w2───►│                │             │
   │           │              │──git worktree──────────────►│
   │           │              │──inject prompt─────────────►│
   │           │              │                │             │
   │           │              │◄──task done────│             │
   │           │              │  (T1 complete) │             │
   │           │              │  auto-unblock T2────────────►│
   │           │◄──inbox msg──│                │             │
   │           │  "API done"  │                │             │
   │           │──inbox send──────────────────►│             │
   │           │  "Start T2 using docs/api.yaml"             │
   │           │              │                │             │
   │◄──result──│              │                │             │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）：無協調伺服器（Serverless Coordination）
> 所有狀態存成本地 JSON 檔案，Agent 之間透過檔案系統協調，不需要中央協調伺服器。

1. **原子寫入（Atomic Write）**：所有 JSON 寫入先寫到 `.tmp` 再用 `rename()` 完成，防止 Agent 讀到半寫入的狀態。對應程式碼：`tasks.py:277-288`、`file.py:38-44`
2. **flock 互斥鎖（Exclusive Lock）**：任務更新使用 `fcntl.flock()` 防止多 Agent 競爭寫入同一任務。對應程式碼：`tasks.py:49-58`
3. **自動解除阻塞（Auto-Unblock）**：任務完成時自動掃描並解除依賴此任務的其他任務的 blocked 狀態。對應程式碼：`tasks.py:290-303`
4. **Agent 存活檢查（Liveness Check）**：任務被鎖定時，先檢查鎖定者是否還存活，已死亡的 Agent 鎖定自動釋放。對應程式碼：`tasks.py:166-178`
5. **Prompt 注入（Prompt Injection）**：透過 tmux paste-buffer 將協調協議（Coordination Protocol）自動注入到每個 Worker Agent 的提示詞，零手動設定。對應程式碼：`tmux_backend.py:147-187`

### 資料流（Data Flow）

1. Leader Agent 執行 `clawteam spawn` → `TmuxBackend.spawn()` 建立 git worktree
2. `build_agent_prompt()` 組裝 Identity + Task + Coordination Protocol 文字
3. tmux paste-buffer 將提示詞注入 Worker Agent 的 TUI
4. Worker 完成工作後呼叫 `task update --status completed`
5. `_resolve_dependents_unlocked()` 自動掃描解除下游任務阻塞
6. Worker 透過 `inbox send` 傳送訊息 → `FileTransport.deliver()` 原子寫入 JSON 訊息檔
7. Leader 透過 `inbox receive` 取得訊息（消費後刪除）

### 關鍵程式碼（Key Code Snippets）

**自動協調提示詞注入（`spawn/prompt.py`）：**
```python
def build_agent_prompt(
    agent_name: str,
    agent_id: str,
    agent_type: str,
    team_name: str,
    leader_name: str,
    task: str,
    ...
) -> str:
    """Build agent prompt: identity + task + context + coordination."""
    lines = [
        "## Identity\n",
        f"- Name: {agent_name}",
        f"- ID: {agent_id}",
        f"- Type: {agent_type}",
        f"- Team: {team_name}",
        f"- Leader: {leader_name}",
    ]
    if workspace_dir:
        lines.extend([
            "## Workspace",
            f"- Working directory: {workspace_dir}",
            f"- Branch: {workspace_branch}",
            "- This is an isolated git worktree. Your changes do not affect the main branch.",
        ])
    lines.extend([
        "## Task\n",
        task,
        "## Coordination Protocol\n",
        f"- Use `clawteam task list {team_name} --owner {agent_name}` to see your tasks.",
        f"- Starting a task: `clawteam task update {team_name} <task-id> --status in_progress`",
        f"- Finishing a task: `clawteam task update {team_name} <task-id> --status completed`",
        ...
    ])
    return "\n".join(lines)
```

**任務鎖定與存活檢查（`team/tasks.py`）：**
```python
def _acquire_lock(self, task: TaskItem, caller: str, force: bool) -> None:
    """Acquire lock on a task for the caller agent."""
    if task.locked_by and task.locked_by != caller and not force:
        from clawteam.spawn.registry import is_agent_alive
        alive = is_agent_alive(self.team_name, task.locked_by)
        if alive is not False:
            raise TaskLockError(
                f"Task '{task.id}' is locked by '{task.locked_by}' "
                f"(since {task.locked_at}). Use --force to override."
            )
        # Lock holder is dead — release and continue
    task.locked_by = caller or ""
    task.locked_at = _now_iso() if caller else ""
```

**自動解除阻塞（`team/tasks.py`）：**
```python
def _resolve_dependents_unlocked(self, completed_task_id: str) -> None:
    root = _tasks_root(self.team_name)
    for f in root.glob("task-*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            task = TaskItem.model_validate(data)
            if completed_task_id in task.blocked_by:
                task.blocked_by.remove(completed_task_id)
                if not task.blocked_by and task.status == TaskStatus.blocked:
                    task.status = TaskStatus.pending
                task.updated_at = _now_iso()
                self._save_unlocked(task)
        except Exception:
            continue
```

**Claude Code 啟動就緒偵測（`spawn/tmux_backend.py`）：**
```python
def _wait_for_claude_ready(target: str, timeout_seconds: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        pane = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", target],
            capture_output=True, text=True,
        )
        if pane.returncode == 0:
            lines = [ln.strip() for ln in pane.stdout.splitlines() if ln.strip()]
            tail = lines[-10:] if len(lines) >= 10 else lines
            for line in tail:
                if line.startswith(("❯", ">", "›")):
                    return True
                if "Try " in line and "write a test" in line:
                    return True
        time.sleep(1.0)
    return False
```

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | 模組邊界清晰：spawn/team/transport/workspace 各司其職，單一職責原則（Single Responsibility Principle）執行徹底 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐ | Transport 抽象層讓 File→ZeroMQ→Redis 切換零改動核心邏輯；SpawnBackend ABC 讓新 backend 實作容易 |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐ | 核心邏輯有單元測試，但 tmux 整合部分難以自動化測試 |
| 文件品質（Documentation） | ⭐⭐⭐⭐⭐ | README 有完整的 ASCII 架構圖、三個 Use Case 範例、命令參考手冊，對新手極友好 |
| 依賴管理（Dependency Management） | ⭐⭐⭐⭐⭐ | 核心依賴極簡（typer、pydantic、rich），ZeroMQ 為選用依賴（optional extras） |

> [!tip] 值得學習的設計
> **原子寫入 + flock** 的組合在多 Process 並發（Concurrent）寫入場景中非常實用，且不依賴任何外部鎖服務。這個模式可以直接應用到任何需要多進程共享狀態的 Python 專案。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> - **問題一：單機限制**：File-based Transport 只能在同一台機器或共享掛載的檔案系統（NFS/SSHFS）上運作，真正的分散式部署需等 v0.4 的 Redis Transport — 影響：無法輕鬆跨機部署
> - **問題二：tmux 輪詢時序（Race Condition）風險**：`_wait_for_claude_ready()` 依賴螢幕文字特徵（`❯`），若 Claude 版本更新改變提示符格式則靜默失敗 — 影響：Worker 可能在 Agent 未就緒時收到提示
> - **問題三：任務掃描效能**：`release_stale_locks()` 掃描所有任務檔案，任務數量大時是 O(n) 操作，沒有索引 — 影響：大型團隊效能下降
> - **問題四：Windows 不相容**：大量使用 `fcntl`（Unix 專用）和 tmux — 影響：不支援 Windows 環境

### 🔮 改進建議（Improvement Suggestions）

1. **加入 SQLite 作為可選任務後端**：替代純檔案掃描，可大幅改善大型團隊的任務查詢效能
2. **tmux 就緒偵測改用 tmux hooks**：用 `tmux set-hook` 偵測 pane 事件，比輪詢更可靠
3. **加入 Agent 心跳機制（Heartbeat）**：Worker 定期更新時間戳，Leader 可主動偵測失聯 Agent

## 效能基準（Benchmark）

> [!info] 資料來源
> 官方 README 的 autoresearch demo 數據（8 H100 GPU 場景）

| 場景 | ClawTeam | 手動協調 |
|------|---------|---------|
| 8-Agent ML 實驗 | 30 GPU-hours / 2430 experiments | 數週人工調參 |
| val_bpb 改善 | 1.044 → 0.977（6.4% 提升） | 取決於人類直覺 |
| 全棧 App（5 Agent） | 平行開發，Leader 自動 merge | 需人工手動整合 |
| 7-Agent 對沖基金啟動 | 1 條指令（`clawteam launch hedge-fund`） | 需逐一設定每個 Agent |

> [!note] 框架開銷
> 由於所有協調透過本地檔案系統，框架本身的額外負擔（Overhead）極低（毫秒級），瓶頸幾乎全在 Agent 本身的執行時間。

## 快速上手（Quick Start）

```bash
# 安裝
pip install clawteam

# 確認 tmux 與 Agent CLI 可用
tmux -V
claude --version

# 建立團隊並生成兩個 Worker
clawteam team spawn-team my-team -d "Build auth module" -n leader
clawteam spawn --team my-team --agent-name alice --task "Implement OAuth2 flow"
clawteam spawn --team my-team --agent-name bob   --task "Write unit tests for auth"

# 監控所有 Agent 並排工作
clawteam board attach my-team

# 一鍵啟動對沖基金模板
clawteam launch hedge-fund --team fund1 --goal "Analyze AAPL, MSFT, NVDA for Q2 2026"
```

## 我的心得（My Takeaways）

1. **「CLI 作為通訊協議（Protocol）」是個精妙設計**：Agent 不需要知道 ClawTeam 的內部，只需要能執行 shell 指令。這讓任何 CLI Agent 都能加入，包括未來還不存在的 Agent。

2. **無伺服器協調（Serverless Coordination）真的可行**：用 JSON 檔案 + flock 取代 Redis/消息佇列（Message Queue），在單機場景下反而更簡單、更可靠、更易 debug（直接 `cat` 就能看狀態）。

3. **Prompt 注入是讓 Agent「學會協作」的關鍵**：`build_agent_prompt()` 自動注入協調協議讓每個 Worker 知道如何報告狀態、如何溝通，這解決了 Multi-Agent 系統中「如何讓 Agent 理解自己的角色」的核心問題。

4. **TOML 模板的威力**：hedge-fund.toml 用不到 200 行宣告式設定就定義了一個 7-Agent 金融分析系統，這種「把 Agent 團隊當成軟體套件來打包發布」的思路很有啟發性。

## 相關連結（Related）

- [[CLAUDE-CODE-AGENT]] — ClawTeam 原生支援 Claude Code 作為 Leader/Worker Agent
- [[MULTI-AGENT-SYSTEMS]] — ClawTeam 是「Agent Swarm」模式的具體實現
- [[AI-ORCHESTRATION]] — 與 LangChain、AutoGen 等框架的協調哲學比較

## References

- [GitHub Repo](https://github.com/HKUDS/ClawTeam)
- [autoresearch demo](https://github.com/novix-science/autoresearch)
- [ai-hedge-fund 靈感來源](https://github.com/virattt/ai-hedge-fund)
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
