# Connsys-Jarvis Stage 3 × ClawTeam：Expert Swarm 架構設計

**文件版本**：v1.0
**狀態**：Draft
**目標讀者**：Connsys 韌體工程師、AI 工具開發者
**適用範圍**：connsys-jarvis Stage 3（Multi-Agent Collaboration）實作規劃

---

## 目錄

- [為什麼要結合 ClawTeam？](#為什麼要結合-clawteam)
- [架構總覽](#架構總覽)
- [兩種整合模式比較](#兩種整合模式比較)
- [關鍵設計：Gerrit 作為 Code Exchange Bus](#關鍵設計gerrit-作為-code-exchange-bus)
- [Workspace 設計：Shared Reference Repo](#workspace-設計shared-reference-repo)
- [Leader 身份設計](#leader-身份設計)
- [四個 Use Case 詳細流程](#四個-use-case-詳細流程)
- [兩個月 Roadmap](#兩個月-roadmap)
- [已知限制與風險](#已知限制與風險)
- [名詞對照表](#名詞對照表)
- [延伸閱讀](#延伸閱讀)

---

## 為什麼要結合 ClawTeam？

connsys-jarvis 的設計文件中，Stage 3 的願景是：

> 多個 Expert 可平行運作，透過結構化 Hand-off 與共享記憶互相協調。
> 例如 build-expert 發現問題後，主動通知 debug-expert 接手。

但這個願景在 connsys-jarvis 的現有設計中缺少一個核心組件：**多 Agent 的生命週期管理引擎**。

[ClawTeam](https://github.com/HKUDS/ClawTeam) 正好補足這個缺口。它是一個成熟的 Multi-Agent 協調框架，提供：
- Leader Agent 分解任務、分派給 Worker
- Worker 在獨立的 tmux session 中平行執行
- JSON 檔案作為 inbox（訊息匯流排）
- 任務狀態追蹤（`~/.clawteam/tasks/`）

**結合後的定位**：

```
connsys-jarvis           提供「誰來做」——領域 Expert 的知識、工具、記憶
ClawTeam                 提供「怎麼協調」——多 Agent 生命週期、任務分派、訊息匯流排
Gerrit                   提供「程式碼怎麼交換」——Change 作為跨 Agent 的 worktree 替代品
```

---

## 架構總覽

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Connsys Expert Swarm（Stage 3）                        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Leader Agent（ClawTeam Leader + framework-base-expert）          │   │
│  │                                                                 │   │
│  │  • framework-expert-discovery-knowhow → 知道有哪些 Expert 可用   │   │
│  │  • framework-handoff-flow             → 懂得寫 Hand-off 文件     │   │
│  │  • ClawTeam task list                 → 追蹤所有 Worker 進度     │   │
│  └─────────────────┬────────────────────┬────────────────┬────────┘   │
│                    │ spawn              │ spawn          │ spawn       │
│          ┌─────────▼──────┐  ┌──────────▼─────┐  ┌──────▼──────────┐ │
│          │  Worker A      │  │  Worker B       │  │  Worker C       │ │
│          │  wifi-bora-    │  │  bt-bora-       │  │  wifi-gen4m-    │ │
│          │  cr-robot-     │  │  security-      │  │  base-expert    │ │
│          │  expert        │  │  expert         │  │                 │ │
│          │                │  │                 │  │                 │ │
│          │ workspace-A/   │  │ workspace-B/    │  │ workspace-C/    │ │
│          │  .claude/      │  │  .claude/       │  │  .claude/       │ │
│          │  codespace/    │  │  codespace/     │  │  codespace/     │ │
│          └──────┬─────────┘  └──────┬──────────┘  └──────┬──────────┘ │
│                 │                   │                     │             │
│         ┌───────▼───────────────────▼─────────────────────▼───────┐   │
│         │              Gerrit（Code Exchange Bus）                   │   │
│         │   Change-A: I3a4b5c  Change-B: I7d8e9f  Change-C: ...   │   │
│         │   topic: clawteam-{team-name}-{task-id}                  │   │
│         └──────────────────────────────────────────────────────────┘   │
│                                                                         │
│         ┌──────────────────────────────────────────────────────────┐   │
│         │              ClawTeam Inbox（~/.clawteam/）               │   │
│         │   Worker A → Leader: "Change-ID: I3a4b5c, status: done"  │   │
│         │   Leader → Worker B: "Download I3a4b5c, continue task"   │   │
│         └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 兩種整合模式比較

在實作上，有兩種方式可以讓 ClawTeam Worker 具備 connsys-jarvis Expert 的能力。選擇哪種模式取決於任務的複雜度與持續時間。

### 模式 A：完整 Expert 實例（推薦用於複雜任務）

每個 ClawTeam Worker 是一個完整的 Claude Code 實例，在自己的 workspace 執行，安裝了對應的 connsys-jarvis Expert。

```
ClawTeam spawn worker
  → tmux new-session in workspace-A/
  → claude 啟動
  → Worker prompt 包含指令：
      "First: python connsys-jarvis/scripts/setup.py --init
       wifi-bora/wifi-bora-cr-robot-expert/expert.json
       && source .connsys-jarvis/.env"
  → Claude 在 wifi-bora-cr-robot-expert 環境下工作
```

| 面向 | 說明 |
|------|------|
| **知識系統** | 完整 SKILL.md 庫，透過 `.claude/skills/` symlink 載入 |
| **記憶系統** | 完整三區記憶（shared/working/handoffs）+ connsys-memory |
| **Hooks** | pre-compact、session-end、mid-checkpoint 全部生效 |
| **程式碼隔離** | 各 Worker 有獨立 workspace，透過 Gerrit 交換程式碼 |
| **啟動成本** | 重（需 repo sync，視 manifest 大小可能 5–30 分鐘）|
| **最適場景** | 需要寫 code、跑 build、上傳 Gerrit 的完整任務 |

### 模式 B：Skills 注入到 Worker Prompt（推薦用於短暫分析）

ClawTeam 的 `build_agent_prompt()` 直接讀取 SKILL.md 內容，注入進 worker 的系統 prompt。不需要安裝 setup.py，不需要獨立 workspace。

```python
# spawn/prompt.py 修改（概念）
skill_content = read_skill("wifi-bora-build-flow")
prompt += f"\n## Expert Knowledge\n{skill_content}"
```

| 面向 | 說明 |
|------|------|
| **知識系統** | Skills 以文字注入，有 context 大小限制 |
| **記憶系統** | ✗ 無 Hooks，無持久記憶 |
| **Hooks** | ✗ 不支援 |
| **程式碼隔離** | ClawTeam 預設的 git worktree |
| **啟動成本** | 輕（秒級，直接 spawn）|
| **最適場景** | 分析 log、閱讀文件、產出報告等輸入輸出清晰的子任務 |

### Hybrid 策略（建議）

```
任務分類：
  複雜度高（需 build/patch/gerrit）→ 模式 A
  複雜度低（分析/報告/設計討論） → 模式 B

Leader 決策邏輯：
  if task.requires_code_change:
      spawn Mode-A worker（完整 Expert 實例）
  else:
      spawn Mode-B worker（Skills 注入）
```

---

## 關鍵設計：Gerrit 作為 Code Exchange Bus

### 為什麼不用 git worktree？

ClawTeam 預設使用 git worktree 隔離 Worker。但 connsys-jarvis 的韌體環境有特殊限制：

1. **多 repo 結構**：firmware 是透過 `repo` 工具管理的 Android-style multi-repo，git worktree 只能處理單一 git repo
2. **Gerrit 是既有工作流**：`sys-bora-preflight-expert` 已經知道如何操作 Gerrit，不需要額外工具
3. **人類可讀**：Gerrit Change 有 Web UI，工程師可以在 Gerrit 上看到 Agent 的修改，便於審查

### Gerrit Change 作為 Worktree 替代品

```
傳統 git worktree 流程：
  main branch → worktree-A (Worker A 的修改)
                worktree-B (Worker B 的修改)
  → 人工 merge 後進 main

Gerrit-based 流程（本設計）：
  main branch → Worker A → git push refs/for/main (Change I3a4b5c)
                          → ClawTeam inbox 通知 Leader Change-ID
             → Worker B → repo download <change-id>（取得 A 的修改）
                        → 繼續工作，git push refs/for/main (Change I7d8e9f, parent=I3a4b5c)
```

### 命名慣例

**Gerrit topic**（用於事後 debug，可在 Gerrit Web UI 查詢）：

```
clawteam-{team-name}-{task-id}

範例：
  clawteam-wifi-ci-fix-20260329-001   ← wifi CI 修復任務
  clawteam-bt-debug-20260329-002      ← BT debug 任務
```

**Change-ID 傳遞流程**：

```
1. Worker A 完成修改
   git push origin HEAD:refs/for/main%topic=clawteam-wifi-ci-fix-{task-id}

2. Worker A 送訊息給 Leader（ClawTeam inbox）
   clawteam inbox send {team} {leader} \
     "Task completed. Gerrit Change-ID: I3a4b5c6d. Topic: clawteam-wifi-ci-fix-{task-id}"

3. Leader 收到後，若需要 Worker B 接手：
   clawteam inbox send {team} worker-b \
     "Download and review: repo download {project} {change-number}. Continue task."

4. 事後 debug：
   在 Gerrit 搜尋 topic:clawteam-wifi-ci-fix-{task-id}
   → 看到所有 Agent 上傳的 Changes 及時序
```

---

## Workspace 設計：Shared Reference Repo

每個 Worker 有獨立的 `CONNSYS_JARVIS_WORKSPACE_ROOT_PATH`，但 repo sync 可能需要大量時間和頻寬。設計 Shared Reference Repo 來加速。

```
主機上的目錄結構：

/workspace-shared/               ← 共享參考 repo（唯讀，由 cron 定期 sync）
  └── .repo/
  └── bora/
      ├── wifi/ (git, read-only)
      ├── bt/   (git, read-only)
      └── build/(git, read-only)

/workspace-worker-A/             ← Worker A 的獨立 workspace
  ├── connsys-jarvis/ (git)
  ├── .connsys-jarvis/
  │   ├── .env
  │   └── memory/
  ├── CLAUDE.md
  ├── .claude/
  │   ├── skills/ → symlinks
  │   └── hooks/  → symlinks
  └── codespace/
      └── fw/
          └── bora/ ← 從 shared reference clone（速度快）

/workspace-worker-B/             ← Worker B 的獨立 workspace（同結構）
```

### Repo Sync 流程

```bash
# Worker 啟動腳本（ClawTeam spawn 時執行）

SHARED_REF="/workspace-shared"
WORKER_DIR="/workspace-worker-${WORKER_ID}"

# 1. 若 shared reference 存在，用 --reference 加速
if [ -d "$SHARED_REF/.repo" ]; then
    repo init -u {manifest-url} --reference="$SHARED_REF"
    repo sync -j8    # 大部分 object 從 local 複製，速度快 10x
else
    # 2. Fallback：完整下載
    repo init -u {manifest-url}
    repo sync -j4
fi

# 3. 安裝 Expert
python connsys-jarvis/scripts/setup.py \
    --init {domain}/{expert-name}/expert.json
source .connsys-jarvis/.env
```

### Shared Reference Repo 維護

```bash
# cron job（每天或每次 CI 後更新）
cd /workspace-shared
repo sync -j8 --force-sync
```

好處：Worker 的 repo sync 從「下載數 GB」變成「從本地複製 + 增量 fetch 新 commit」，啟動時間大幅縮短。

---

## Leader 身份設計

Leader 是一個特殊的 ClawTeam Agent，同時具備兩種能力：

### 1. ClawTeam Leader 能力（內建）
- 建立 Team、分派任務
- 監控 Worker 進度（`clawteam task list`）
- 接收 Worker 完工通知（ClawTeam inbox）

### 2. framework-base-expert 能力（connsys-jarvis 安裝）

```json
// framework-base-expert 的 expert.json（相關部分）
{
  "name": "framework-base-expert",
  "internal": {
    "skills": [
      "framework-expert-discovery-knowhow",  // ← 知道所有可用 Expert
      "framework-handoff-flow",              // ← 懂 Hand-off 協議
      "framework-memory-tool"                // ← 操作 connsys-memory
    ]
  }
}
```

`framework-expert-discovery-knowhow` skill 讓 Leader 能執行：

```bash
python connsys-jarvis/scripts/setup.py --list --format json
```

取得所有可用 Expert 的 JSON 清單，再根據任務決定要 spawn 哪個 Expert。

### Leader 決策流程（CI/CD error fixing 為例）

```
1. Leader 收到任務：「wifi-bora CI #1234 build failed, bt-bora CI #5678 test failed」

2. Leader 呼叫 framework-expert-discovery-knowhow：
   → 查到 wifi-bora-cr-robot-expert 擅長 build error 修復
   → 查到 bt-bora-security-expert 擅長 bt 測試修復

3. Leader 建立 ClawTeam 任務：
   clawteam task create {team} "Fix wifi-bora CI #1234" --assignee worker-wifi
   clawteam task create {team} "Fix bt-bora CI #5678"  --assignee worker-bt

4. Leader spawn Worker：
   clawteam spawn {team} worker-wifi \
     --expert wifi-bora/wifi-bora-cr-robot-expert/expert.json \
     --workspace /workspace-worker-wifi \
     --task "Download CI log from {url}, fix build error, upload to Gerrit"

   clawteam spawn {team} worker-bt \
     --expert bt-bora/bt-bora-security-expert/expert.json \
     --workspace /workspace-worker-bt \
     --task "Download CI log from {url}, fix test failure, upload to Gerrit"

5. Leader 等待 inbox 通知，彙整結果
```

---

## 四個 Use Case 詳細流程

### UC1：CI/CD Error Fixing（多平台平行修復）

**場景**：wifi-bora CI、bt-bora CI、wifi-gen4m CI 同時失敗，各自修復互不干擾。

```
Leader
  │
  ├── spawn wifi-bora-cr-robot-expert (workspace-A)
  │     └── 任務：分析 wifi-bora CI #1234 build log，修復 → Gerrit Change I-wifi-01
  │
  ├── spawn bt-bora-security-expert  (workspace-B)
  │     └── 任務：分析 bt-bora CI #5678 test log，修復  → Gerrit Change I-bt-01
  │
  └── spawn wifi-gen4m-base-expert   (workspace-C)
        └── 任務：分析 gen4m CI #9012 build log，修復  → Gerrit Change I-gen4m-01

[三個 Worker 平行進行]

Worker-A 完成 → ClawTeam inbox → Leader
  "wifi-bora CI fix done. Change: I-wifi-01. Preflight pending."

Worker-B 完成 → ClawTeam inbox → Leader
  "bt-bora CI fix done. Change: I-bt-01. Preflight passed."

Worker-C 完成 → ClawTeam inbox → Leader
  "gen4m CI fix done. Change: I-gen4m-01. Build pass."

Leader 彙整報告 → 送交人工確認（Human in the Loop）
  "3 CI failures fixed. Changes: I-wifi-01, I-bt-01, I-gen4m-01.
   Awaiting human review before Gerrit submit."
```

**Gerrit 在此的角色**：每個 Worker 的修改隔離在各自的 Change，不互相干擾。人工 Gerrit submit 是最後一道防線。

---

### UC2：Debug（跨 domain 平行分析）

**場景**：一個複雜 bug，懷疑跨越 WiFi firmware、BT firmware、System platform 三個層面。

```
Leader
  │
  ├── spawn wifi-bora-cr-robot-expert (workspace-A) [模式 A]
  │     └── 任務：分析 WiFi coredump + uart log
  │           → 產出分析報告，上傳為 Gerrit Comment 或 review
  │
  ├── spawn bt-bora-security-expert  (workspace-B) [模式 A]
  │     └── 任務：分析 BT HCI log + fw dump
  │           → 產出分析報告
  │
  └── spawn sys-bora-preflight-expert (workspace-C) [模式 B]
        └── 任務（輕量）：查詢 preflight dashboard，確認 platform 版本
              → 報告 platform 版本資訊（無需 Gerrit）

[Worker-A, B 平行分析，Worker-C 快速查詢]

Worker-C 先完成（模式 B，輕量）→ inbox → Leader
  "Platform: bora-v2.3, kernel: 5.15.0. No platform issue found."

Worker-A 完成（模式 A）→ inbox → Leader
  "WiFi side: NULL pointer in wifi_tx_queue_flush at 0x3a4b.
   Root cause likely in bt-wifi coexistence scheduler."

Worker-B 完成（模式 A）→ inbox → Leader
  "BT side: coex_sched timeout at 0x7c8d.
   Confirms coexistence scheduler issue."

Leader 整合分析 → 建議 debug 方向
  "Root cause: coex_sched race condition between WiFi and BT.
   Suggest spawning wifi-bora-cr-robot-expert for fix."
```

---

### UC3：New Feature Design（跨 domain 協作設計）

**場景**：新功能「WiFi/BT 動態 coexistence 優化」，需要 WiFi、BT、Platform 三個 domain 同時設計各自的 interface。

```
Leader（design kickoff）
  │
  ├── spawn wifi-bora-memory-slim-expert (workspace-A) [模式 A]
  │     └── 任務：設計 WiFi 側 coex API
  │           → 撰寫 interface spec 到 Gerrit
  │             git push: "Add wifi_coex_api.h skeleton"
  │             topic: clawteam-coex-feature-design-001
  │
  ├── spawn bt-bora-security-expert (workspace-B) [模式 A]
  │     └── 任務：設計 BT 側 coex API
  │           → 在 Gerrit 上留 Review Comment 於 Worker-A 的 Change
  │           → 另開 Change: "Add bt_coex_api.h skeleton"
  │
  └── spawn sys-bora-base-expert (workspace-C) [模式 A]
        └── 任務：設計 Platform coex scheduler interface
              → Review Worker-A 和 Worker-B 的 Changes
              → 開新 Change: "Add platform_coex_sched.h"

[Workers 透過 Gerrit Review 機制互相 review 設計]

所有 Worker 完成 → Leader 彙整
  "Design complete. 3 interface headers uploaded to Gerrit.
   Topic: clawteam-coex-feature-design-001.
   Recommend human review before implementation."
```

**Gerrit 在此的角色**：不只是程式碼隔離，也是設計協作的平台。Agent 之間透過 Gerrit Review Comment 互相給 feedback，形成跨 domain 的設計 review 循環。

---

### UC4：Code Refactor / Memory Slim（Sequential Pipeline）

**場景**：wifi-bora memory slim，需要分析 → patch → 驗證三個階段。各階段由不同 Expert 執行，透過 Gerrit 傳遞成果。

```
Stage 1：分析（Analyzer Worker）
  spawn wifi-bora-memory-slim-expert (workspace-A)
    任務：執行 symbol map 分析、AST 靜態分析
    → 產出 memory-slim-report.md + 候選優化清單
    → git push: "Add memory-slim-report and candidate list"
      Change: I-analysis-01, topic: clawteam-memslim-001

Leader 收到 → inbox：「分析完成，Change: I-analysis-01」

Stage 2：實作（Patcher Worker）
  spawn wifi-bora-memory-slim-expert (workspace-B，新 worker)
    任務：
      1. repo download I-analysis-01（取得分析報告）
      2. 根據候選清單，逐一 apply 優化 patch
      3. 本地 build 驗證 → pass
    → git push: "Apply memory optimization patches"
      Change: I-patch-01 (parent: I-analysis-01)
      topic: clawteam-memslim-001
    → inbox → Leader：「Patch 完成，Change: I-patch-01，build pass」

Stage 3：驗證（Validator Worker）
  spawn wifi-bora-memory-slim-expert (workspace-C，新 worker)
    任務：
      1. repo download I-patch-01
      2. 執行 WUT (googletest) + preflight CI
      3. 比對 memory footprint（before/after）
    → inbox → Leader：「WUT pass, memory reduced 12%. Change ready for review.」

Leader 最終報告：
  "Memory slim complete. 3 changes uploaded (I-analysis-01, I-patch-01, I-validate-01).
   Memory reduction: 12%. Awaiting human Gerrit review."
```

**這個 use case 的特色**：
- 三個階段是 **Sequential**，不平行
- 每個階段是**不同的 Expert 實例**（工作記憶乾淨，不被前一階段的上下文污染）
- Gerrit Change chain 形成完整的修改歷程，人工 review 時可逐層追蹤

---

## 兩個月 Roadmap

### Phase 1（M1）：基礎驗證（手動整合）

**目標**：驗證架構可行性，不改動 ClawTeam 和 connsys-jarvis 原始碼。

| 週次 | 工作項目 | 產出 |
|------|---------|------|
| W1 | 建立 shared reference repo 機制；撰寫 worker-init.sh | worker startup 腳本 |
| W2 | 手動執行 UC1（CI/CD fix），Leader 人工操作 ClawTeam CLI | 驗證 Gerrit bus 可行性 |
| W3 | 建立 Leader prompt template（含 expert-discovery skill）| 可複用的 Leader prompt |
| W4 | 執行 UC4（Memory slim sequential pipeline）端到端測試 | 驗證 Gerrit Change chain |

**Phase 1 的手動部分**：
- Leader 人工執行 `clawteam spawn` 指令
- Worker 的 expert 安裝步驟由 worker-init.sh 自動化
- Gerrit Change-ID 由 Worker 報告，Leader 人工轉發

---

### Phase 2（M2）：ClawTeam 整合（半自動）

**目標**：修改 ClawTeam 讓 Leader 能自動 spawn connsys-jarvis Expert Worker。

#### 2.1 expert.json 加入 ClawTeam 欄位

```json
// 新增欄位（不影響現有 setup.py 邏輯）
{
  "name": "wifi-bora-cr-robot-expert",
  "clawteam": {
    "agent_type": "wifi-bora-cr-robot",
    "workspace_template": "worker-wifi-bora",
    "spawn_mode": "full_expert",          // "full_expert" | "skill_inject"
    "required_env": ["CONNSYS_JARVIS_PATH", "GERRIT_URL"],
    "startup_script": "worker-init.sh"
  }
}
```

#### 2.2 ClawTeam spawn/prompt.py 修改

```python
# 在 build_agent_prompt() 新增 connsys-jarvis 初始化指令

def build_agent_prompt(..., expert_json: str = "", ...):
    lines = [...]  # 現有內容

    if expert_json:
        lines.extend([
            "",
            "## Expert Initialization",
            f"Before starting tasks, initialize your Expert environment:",
            f"```bash",
            f"python connsys-jarvis/scripts/setup.py --init {expert_json}",
            f"source .connsys-jarvis/.env",
            f"```",
            "You are now equipped with domain expert knowledge, skills, and hooks.",
        ])

    return "\n".join(lines)
```

#### 2.3 新增 ClawTeam spawn 參數

```bash
# 新增 --expert 和 --workspace 參數
clawteam spawn {team} {worker-name} \
    --expert wifi-bora/wifi-bora-cr-robot-expert/expert.json \
    --workspace /workspace-worker-wifi \
    --task "Fix CI #1234"
```

#### 2.4 Leader 自動 spawn 流程（ClawTeam skill）

在 `framework-base-expert` 新增一個 skill：`framework-clawteam-spawn-flow`，讓 Leader 知道如何呼叫 ClawTeam CLI 來 spawn Expert Worker。

```
framework-clawteam-spawn-flow SKILL.md 內容摘要：
  步驟 1：呼叫 setup.py --list --format json，取得可用 Expert 清單
  步驟 2：根據任務描述，選擇合適的 Expert
  步驟 3：呼叫 clawteam spawn --expert {json} --workspace {dir}
  步驟 4：監聽 inbox，等待 Worker 完工通知
  步驟 5：若 Worker 回報 Change-ID，轉發給需要的下一個 Worker
```

---

## 已知限制與風險

| 限制 | 說明 | 緩解策略 |
|------|------|---------|
| **Worker 啟動時間** | repo sync 可能需要 5–30 分鐘 | Shared reference repo 可縮短至 1–5 分鐘 |
| **資源消耗** | 多個完整 workspace 需要大量磁碟空間 | 限制同時 Worker 數量（建議 ≤ 3）；Worker 完成後清理 codespace/ |
| **Gerrit 權限** | 每個 Worker 需要有 Gerrit push 權限 | 使用統一的 CI bot 帳號；Agent 以該帳號操作 |
| **ClawTeam 不感知 Expert** | ClawTeam 目前不知道 connsys-jarvis Expert 的存在 | Phase 1 人工整合；Phase 2 再修改 ClawTeam |
| **Memory 隔離** | 各 Worker 有獨立 `.connsys-jarvis/memory/`，彼此不互通 | 透過 ClawTeam inbox + Gerrit 傳遞結論；memory 隔離反而避免污染 |
| **Gerrit submit 風險** | Agent 不應 submit Gerrit Change（不可逆）| expert.json 的 `human_in_the_loop` 欄位禁止 Agent 執行 `gerrit review --submit`；SKILL.md 規範明確禁止 |

---

## 名詞對照表

| 術語 | connsys-jarvis 含義 | ClawTeam 對應 |
|------|---------------------|---------------|
| Expert | 特定 domain 的 AI 專家角色 | Worker Agent |
| framework-base-expert | 跨 domain 共用的基礎 Expert | Leader Agent（加上 Expert 能力）|
| Hand-off | Expert 切換時的結構化上下文摘要 | ClawTeam inbox 訊息 |
| connsys-memory | 遠端 Git repo，收集 session 記錄 | 無直接對應（ClawTeam 有 cost/session 資料）|
| Gerrit Change | 程式碼修改的 review 單位 | （新增）Worker 間的 Code Exchange Bus |
| CONNSYS_JARVIS_WORKSPACE_ROOT_PATH | 單一 Expert 的 workspace 根目錄 | 每個 Worker 各有一個 |
| transitions（expert.json）| Expert 完成後的下一步 Expert | ClawTeam 任務依賴關係 |

---

## 延伸閱讀

- [ClawTeam 架構分析](../CodeAnalysis/2026-03-18-CLAWTEAM-AGENT-SWARM-INTELLIGENCE.md)
- connsys-jarvis agents-design.md §11（Expert 狀態機與交接流程）
- connsys-jarvis agents-requirements.md §1.5（三階段演進願景）
- [Harness Engineering — Martin Fowler Blog](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html)
