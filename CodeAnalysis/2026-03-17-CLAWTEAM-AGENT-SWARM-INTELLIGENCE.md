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

## 待補充（Open Questions）

- ClawTeam 的 `_wait_for_claude_ready()` 透過偵測 `❯` 符號判斷 Claude Code 就緒，這個偵測方式在 Claude Code 不同版本或不同終端主題設定下是否穩定？有沒有已知的失敗案例？（建議搜尋：`ClawTeam claude ready detection tmux prompt symbol reliability`）
- TOML 模板一鍵啟動 7-Agent 對沖基金（`hedge-fund.toml`）的成本是多少？若每個 Worker Agent 執行完整的金融分析任務，一次完整執行預計消耗多少 token 和 API 費用？（建議搜尋：`ClawTeam hedge fund template cost estimation token usage`）
- 8-Agent ML 實驗的 benchmark（30 GPU-hours，2430 experiments）是在什麼硬體規格和時間預算下完成的？這個數字是否具有可重複性（reproducibility）？（建議搜尋：`ClawTeam autoresearch benchmark reproducibility GPU experiment`）
- ClawTeam 的 File-based Transport 使用 `fcntl.flock()` 防止並發寫入，但 `flock` 在 NFS 或某些 Linux 核心版本下可能不可靠。在分散式檔案系統或容器環境中使用時有何注意事項？（建議搜尋：`fcntl flock NFS reliability container distributed filesystem`）
- ClawTeam 的 Leader Agent 與 Worker Agent 之間透過 `inbox send` 傳遞訊息，這個訊息格式是否有大小限制？若需要傳遞大量上下文（如程式碼片段、文件內容），最佳實踐是什麼？（建議搜尋：`ClawTeam inbox message size limit large context passing`）
- ZeroMQ P2P Transport 作為 File-based 的替代方案，啟用後對代理人間通訊延遲有多大改善？實際配置 ZeroMQ 的複雜度如何，有沒有完整的設定文件？（建議搜尋：`ClawTeam ZeroMQ P2P transport setup configuration performance`）

## 相關連結（Related）

- [[CLAUDE-CODE-AGENT]] — ClawTeam 原生支援 Claude Code 作為 Leader/Worker Agent
- [[MULTI-AGENT-SYSTEMS]] — ClawTeam 是「Agent Swarm」模式的具體實現
- [[AI-ORCHESTRATION]] — 與 LangChain、AutoGen 等框架的協調哲學比較
- [[2026-04-02-SAS-OUTPERFORM-MAS-MULTI-HOP-REASONING-EQUAL-TOKEN-BUDGETS]] — DPI 理論指出蜂群通訊瓶頸可能引入資訊損失，ClawTeam 的任務分解設計需考慮此理論限制

## References

- [GitHub Repo](https://github.com/HKUDS/ClawTeam)
- [autoresearch demo](https://github.com/novix-science/autoresearch)
- [ai-hedge-fund 靈感來源](https://github.com/virattt/ai-hedge-fund)
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch)

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 原子寫入（mkstemp + rename）；flock 互斥鎖；自動解除阻塞（_resolve_dependents_unlocked）；Agent 存活檢查（is_agent_alive）；tmux paste-buffer 提示詞注入；FileTransport / ZeroMQ P2P 雙傳輸；TOML 模板；Typer + Pydantic + Rich 技術棧；1,898 顆 GitHub Stars（三天內）；Python 3.10+ |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | ClawTeam 的核心哲學是「CLI 作為通訊協議」：每個 Worker 代理人只需要能執行 shell 指令，不需要知道 ClawTeam 的內部實作。Coordination Prompt 自動注入讓 Worker 在生成瞬間就知道如何報告進度、如何通訊，無需額外整合。原子寫入 + flock 的無伺服器協調模式用最簡單的技術解決了多進程並發的核心問題。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | ①`_wait_for_claude_ready()` 依賴 `❯` 符號偵測就緒狀態，假設 Claude Code 的提示符號不會改變，但這是一個脆弱的假設；②任務掃描（O(n)）假設任務數量在可控範圍，但大型多代理人團隊（50+ 任務）時效能會顯著下降；③tmux paste-buffer 注入假設 Worker 代理人在收到 prompt 前已完全就緒，但視窗切換和初始化的時序競爭條件（race condition）無法完全消除 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | ①用 ClawTeam 協調 3-5 個 Claude Code 實例平行開發一個全棧應用的不同模組；②借鑑 TOML 模板設計，為常見的開發場景（code review team、ML experiment team）建立可重用的團隊模板；③在多 Agent ML 實驗中用 ClawTeam 自動化超參數搜尋（autoresearch 模式） |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | ClawTeam 在「單機多代理人協調」場景下是設計最完整的工具（原子寫入 + flock + 自動解除阻塞 + Agent 存活檢查），比 GNAP（只有 RFC）更可用，比 OMC（單一 Claude Code 增強）更適合真正的多代理人場景。主要限制是單機（File Transport 不支援跨機器）和 Unix 專用（fcntl 依賴），但這些在 v0.4 路線圖中有規劃解決。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：ClawTeam 的 Coordination Prompt 自動注入（`build_agent_prompt()`）假設每個 Worker 都能理解並遵守協調協議指令。但若 Worker 是一個 Gemini CLI 或 Codex CLI，其對 `clawteam task update` 等 shell 指令的執行意願取決於自身的 system prompt 設定，這個假設的成立率有多高？
- **假設**：`_resolve_dependents_unlocked()` 掃描所有任務檔案以解除阻塞，這個 O(n) 掃描假設任務數量有限。若一個大型 ML 研究任務有 500+ 子任務，每次任務完成都觸發一次完整掃描，效能影響如何評估？
- **證據**：8-Agent ML 實驗（30 GPU-hours，2430 experiments，val_bpb 6.4% 改善）的數據來自 autoresearch demo，但這是在 ClawTeam 協調下完成還是手動協調後聲稱是 ClawTeam 的結果？實驗的可重複性文件在哪裡？
- **觀點**：從軟體架構師的角度，ClawTeam 的「無協調伺服器（Serverless Coordination）」設計在可靠性上其實是以「分散式狀態在多個代理人之間可能暫時不一致」為代價換取的簡單性。這個一致性保證是否足夠應用於需要嚴格原子性的任務（如資料庫遷移）？
- **後果**：若 tmux 版本更新改變了 `capture-pane` 的輸出格式或 paste-buffer 的行為，`_wait_for_claude_ready()` 和 `_inject_prompt_via_buffer()` 都可能靜默失敗，導致 Worker 代理人收到空白 prompt 後執行不可預期的操作。這個維護風險如何管理？

### 方案批判三問（Critical Evaluation）

> [!warning] 適用於技術方案類內容

1. **最大的風險是什麼？** — tmux 螢幕文字解析（screen scraping）是架構中最脆弱的部分。ClawTeam 通過讀取 tmux pane 的文字內容來偵測 Claude Code 就緒狀態（`❯` 符號）和確認 workspace trust 提示，這個方法完全依賴 CLI 介面的文字格式不改變。一旦 Claude Code 更新了終端機輸出格式（如更換提示符號、改變 trust 確認的措辭），所有代理人生成邏輯都可能靜默失敗，且沒有明確的錯誤訊息。
2. **什麼情況下會失敗？** — ①多個 Worker 同時完成並嘗試 push 任務狀態更新，若 flock 在 NFS 或 Docker volume 上不可靠，原子性保證失效，任務狀態可能損毀；②Leader Agent 中途崩潰（如 Claude Code 被強制關閉），Worker 繼續執行但沒有 Leader 收集結果，孤兒 Worker 在 tmux 中持續運行直到耗盡資源；③`clawteam workspace merge` 在多個 Worker 修改同一檔案時需要人工解決 merge conflict，若在自動化流程中無人值守，整個合併步驟阻塞
3. **有沒有更好的替代方案？** — ①若需要更健壯的跨進程通訊：用 SQLite（WAL mode）取代 JSON 檔案作為任務後端，提供更好的並發支援和查詢能力；②若需要跨機器協調：ClawTeam v0.4 的 Redis Transport 是官方規劃，或直接使用 GNAP（git-native 天然跨機器）；③若不需要 tmux 視覺化監控：用 ClawTeam 的 subprocess backend 取代 tmux backend，更適合 CI/CD 環境和無頭伺服器
