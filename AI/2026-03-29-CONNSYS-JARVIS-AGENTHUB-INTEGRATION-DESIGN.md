---
title: "Connsys Jarvis × AgentHub 整合架構設計 v3（定稿）：四種工程工作流的多代理協調策略"
date: 2026-03-29
category: AI
tags:
  - "#ai/multi-agent"
  - "#ai/infrastructure"
  - "#ai/agent-swarm"
  - "#devtools/claude-code"
  - "#design/architecture"
source: "https://github.com/swchen44/testing/tree/main/agents/connsys-jarvis"
source_type: article
author: "swchen44"
status: notes
links:
  - "[[AGENTHUB-KARPATHY-AGENT-NATIVE-COLLABORATION-INFRASTRUCTURE]]"
  - "[[OH-MY-CLAUDECODE-MULTI-AGENT-ORCHESTRATION]]"
  - "[[CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]]"
---

## 摘要（Summary）

Connsys Jarvis 是以 Claude Code 為底層、透過 Skill + Hook 組裝成「領域專家（Expert）」的輕量 AI 助理框架。AgentHub 是 AI 代理原生的 DAG 協作基礎設施（bare git + message board）。

本文設計兩者的整合方案，讓 Jarvis 的 Expert 能夠：
1. **自動累積工作成果**到 AgentHub 的持久 DAG（取代只存在單一 session 的記憶）
2. **平行部署多個 Expert** 同時探索同一問題的不同策略（突破單一視角的局部最優）

設計覆蓋真實韌體工程的四種工作類型，並已確認以下三個關鍵前提：

| 前提 | 確認結果 |
|------|---------|
| CI/CD 工具能力 | `sys-bora-cicd-tool` 可觸發 CI run、查詢結果、抓取 log → **Type CI commit 可全自動** |
| Debug 表象格式 | 自由描述 + 部分 log → **改用 LLM 語義搜尋**取代精確 hash 比對 |
| 跨 workspace 程式碼結構 | 各自獨立 repo → **跨 workspace 只共享 R/D 類型 commit**，不共享程式碼 |

---

## 一、系統定位：Jarvis 補深度，AgentHub 補廣度

```
┌──────────────────────────────────────────────────────────────────┐
│              整合前 — Jarvis alone                                │
│                                                                  │
│  Expert A ──► session 記憶 ──► hand-off ──► Expert B             │
│  ↑                                                               │
│  深度足夠，但：                                                    │
│  • 記憶只在本地 session，中斷即消失                                │
│  • 一次只有一個視角                                               │
│  • 過去的嘗試沒有結構化保存                                        │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              整合後 — Jarvis × AgentHub                           │
│                                                                  │
│  Expert A ─────────────┐                                         │
│  Expert B ─────────────┼──► AgentHub DAG ──► 持久記憶            │
│  Expert C ─────────────┘      │                                  │
│                               └──► 跨 session / 跨 Expert 可查詢  │
│                                                                  │
│  Jarvis 提供：Expert 的深度工作能力                                │
│  AgentHub 提供：多 Expert 廣度探索 + 長期知識累積                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 二、四種工作流 × AgentHub 協調模式

### 工作流對應表

| 工作類型 | AgentHub 模式 | 核心價值 | 起點 commit | 評估指標 |
|---------|------------|---------|------------|---------|
| W1：Code Fix + CI/CD | Pipeline | 追蹤跨平台失敗模式 | Type C | 平台通過率 |
| W2：Debug | Fan-Out（分類）+ Pipeline（分析） | 多視角分類、避免第一直覺偏誤 | Type D | Evidence 充分度（LLM judge） |
| W3：新 Feature 設計 | Fan-Out | 並行評估多設計方案 | Type R | Trade-off 矩陣（LLM judge） |
| W4：Refactor / Memory Slim | Fan-Out | 並行競爭多優化策略 | Type C | Memory delta（bytes） |

---

### W1：Code Fix + CI/CD 多平台

**流程**：

```
本地修復編譯錯誤
       │
       ▼
Push to Gerrit（sys-bora-gerrit-tool）
       │   change_id → 記錄在 Type C commit metadata
       ▼
/hub:ci-push 觸發自動化
       │
       └─► framework-agenthub-ciresult-flow SKILL：
           1. sys-bora-cicd-tool 觸發 CI run
           2. 輪詢直到所有平台完成
           3. 解析 log，逐平台抽取 pass/fail + 錯誤分類
           4. push Type CI commit 到 AgentHub DAG
           5. post 平台結果矩陣到 "ci-result" channel
```

**AgentHub 在 W1 的核心價值**：

CI/CD 跑過多次後，DAG 上會累積多個 Type CI commit。`/hub:status` 可以立刻回答：
- 「Plat-B 連續三次失敗，Plat-A 和 C 都過」→ 共同點是 armcc-v6.18 toolchain
- 「上次類似的改動（diff A）也在 Plat-D 失敗，用 ${fix} 解決了」→ 直接複用

---

### W2：Debug 工作流（分類 Fan-Out + 分析 Pipeline）

**為什麼分類要 Fan-Out？**

韌體問題的表象往往有多個可能根因。`WiFi 掉包`可能是 RF 問題、CoEx 干擾、或 IRQ 競爭。單一 Expert 的「第一直覺」會直接選最熟悉的方向，跳過其他假設。Fan-Out 讓多個 domain Expert 同時給出假設，再由協調者選最有 evidence 支撐的路徑。

**完整流程**：

```
表象 + log 輸入
       │
       ▼ 先查 AgentHub（語義搜尋）
       │   hub-session-start.sh 在 session 開始時：
       │   「有沒有人分析過類似的症狀？」
       │   → 若找到：把相關 Type D commit 注入 context
       │
       ▼ /hub:research 觸發
       │
       ├─ tmux session A：wifi-bora-expert
       │    分析 WiFi 角度 → push Type D：「CoEx 假設，HIGH confidence」
       │
       ├─ tmux session B：bt-bora-expert
       │    分析 BT 角度  → push Type D：「BT power burst 假設，MEDIUM」
       │
       └─ tmux session C：sys-bora-expert
            分析系統層   → push Type D：「IRQ priority 假設，LOW」
       │
       ▼ /hub:evaluate
       │   協調者讀取三個 Type D commit
       │   LLM judge：CoEx 假設有最多 evidence → 勝出
       │
       ▼ 深度分析（sequential，單一 Expert）
       │   wifi-bora-expert 深化分析 CoEx failure
       │   → push Type R（詳細分析報告）
       │
       ▼ Solution 生成 → 三條輸出路徑（見下節）
```

**三條 Solution 輸出路徑**：

| 路徑 | 觸發時機 | 工具 | AgentHub 記錄 |
|------|---------|------|--------------|
| Autotest 先行 | 只需功能驗證，無需 review | sys-bora-cicd-tool | Type CI commit |
| Gerrit | 需要人工確認 | sys-bora-gerrit-tool | Type C + change_id |
| CI/CD 完整 | 影響多平台，需全面驗證 | sys-bora-cicd-tool（全平台） | Type CI commit（逐平台） |

三條路徑都在 DAG 留下 trace，讓「這個問題最後怎麼驗證的」有完整記錄。

---

### W3：新 Feature 設計（純 Fan-Out）

```
/hub:design --task "設計 WiFi 省電模式 API" --experts 3

自動選擇 OR 手動指定 Expert：
  Expert A（wifi-bora）：從 use-case 反推，API 先行
  Expert B（sys-bora）： 從 HW power budget 反推
  Expert C（wifi-gen4m）：從現有 interface 相容性延伸

各自 push Type R → 協調者 LLM judge

評估維度：
  - Memory footprint 影響
  - API 相容性
  - 實作複雜度
  - 可測試性
  - 跨 domain 影響
```

---

### W4：Refactor / Memory Slim（Fan-Out + Metric 評估）

```
/hub:refactor --task "縮小 wifi_mgmt.c static buffer 30%" --experts 3

Expert A：移除 unused feature flag 的 dead code
Expert B：static array → dynamic allocation + pool
Expert C：重新量測每個 buffer 實際最大使用量，縮小 constant

各自 push Type C（程式碼修改）→ 觸發 CI compile（Type CI）

評估指標（Metric 模式，最客觀）：
  - Memory delta（bytes）
  - 所有平台 compile pass
  - Test pass rate
  - Diff size（複雜度代理指標）
```

---

## 三、新增 Expert：framework-agenthub-expert

### 為何獨立 Expert？

不修改現有 `framework-base-expert`，理由：

| 原則 | 說明 |
|------|------|
| 單一職責 | framework-base-expert 管 Harness（context/GC/handoff），agenthub-expert 管多代理協調。兩者性質不同 |
| 可選安裝 | 不是所有 workspace 需要 AgentHub |
| 不影響現有 | 現有 session-end hook 不改；hub hook 是附加層 |
| 未來可替換 | 若改用其他多代理基礎設施，只需換這個 Expert |

### 資料夾結構

```
framework/
└── framework-agenthub-expert/
    ├── expert.json
    ├── soul.md
    ├── rules.md
    ├── duties.md
    ├── expert.md
    │
    ├── skills/
    │   ├── framework-agenthub-client-tool/
    │   │   ├── SKILL.md          ← HTTP API 封裝說明
    │   │   └── hub_client.py     ← 可被 hooks 引用的 library
    │   │
    │   ├── framework-agenthub-coordinator-flow/
    │   │   └── SKILL.md          ← Fan-Out 派發 + 評估 SOP
    │   │
    │   ├── framework-agenthub-spawn-flow/
    │   │   └── SKILL.md          ← tmux 多 Expert 啟動 SOP
    │   │
    │   └── framework-agenthub-ciresult-flow/
    │       └── SKILL.md          ← CI 結果解析 + push SOP
    │                                （橋接 sys-bora-cicd-tool）
    │
    ├── hooks/
    │   ├── hub-session-end.sh        ← 結果自動 push（模式 A）
    │   ├── hub-mid-checkpoint.sh     ← Failsafe WIP push
    │   └── hub-session-start.sh      ← Fetch frontier + 語義搜尋
    │
    └── commands/
        └── framework-agenthub-tool/
            └── COMMAND.md    ← /hub:research /hub:design /hub:refactor
                                 /hub:ci-push /hub:status /hub:evaluate
```

### expert.json

```json
{
  "name": "framework-agenthub-expert",
  "display_name": "Framework AgentHub Expert",
  "domain": "framework",
  "owner": "framework-team",
  "description": "多 Expert 平行研究協調者；管理 AgentHub DAG 與 Message Board；橋接 CI/CD 工具",
  "version": "1.0.0",
  "is_base": false,
  "dependencies": ["framework-base-expert"],
  "internal": {
    "skills": [
      "framework-agenthub-client-tool",
      "framework-agenthub-coordinator-flow",
      "framework-agenthub-spawn-flow",
      "framework-agenthub-ciresult-flow"
    ],
    "hooks": [
      "hub-session-end.sh",
      "hub-mid-checkpoint.sh",
      "hub-session-start.sh"
    ],
    "agents": [],
    "commands": ["framework-agenthub-tool"]
  },
  "exclude_symlink": {"patterns": []}
}
```

---

## 四、四種 Commit 類型定義

### Type R：Research（研究 / 設計報告）

```markdown
---
type: research
sub_type: debug_analysis | feature_design | refactor_plan
from_expert: {expert-name}
task_id: {uuid}
parent_hash: {依據哪個 commit 開始}
---
## 摘要
## 發現 / 設計方案
## Evidence / 依據
## 建議後續行動
```

### Type C：Code（程式碼變更）

```markdown
---
type: code
from_expert: {expert-name}
parent_research_hash: {啟發這個修復的 Research commit}
gerrit_change_id: {若已 push Gerrit}
task_id: {uuid}
---
## 變更說明
## 本地驗證結果
## 已知限制
```

### Type CI：CI/CD Result（多平台編譯 / 測試結果）

```markdown
---
type: ci_result
parent_code_hash: {觸發此 CI 的 Code commit}
gerrit_change_id: {change_id}
ci_run_id: {CI 系統的 run ID，供 sys-bora-cicd-tool 查詢}
from_expert: {expert-name}
---
## 平台結果矩陣
| 平台 | 編譯器版本 | 結果 | 錯誤分類 |
|------|-----------|------|---------|
| bora-wifi | armcc-v6.18 | ✅ PASS | - |
| bora-bt   | armcc-v6.18 | ❌ FAIL | linker:undefined_symbol |
| gen4m-wifi| gcc-arm-none| ✅ PASS | - |

## 失敗平台 log 摘要（抓取關鍵行）
## 建議下一步
```

### Type D：Debug Classification（問題分類假設）

```markdown
---
type: debug_classification
from_expert: {expert-name}
task_id: {uuid}
symptom_text: |
  {工程師原始描述的表象文字，供語義搜尋}
symptom_log_excerpt: |
  {相關 log 片段，最多 50 行}
classification_tag: coexistence | memory_corruption | timing_race | power | linker | ...
confidence: HIGH | MEDIUM | LOW
---
## 表象描述
## 分類依據
## Evidence（log 引用、程式碼引用）
## 建議分析方向
```

> [!note] 語義搜尋的工作方式
> `symptom_text` 和 `symptom_log_excerpt` 儲存原始文字，不做 hash。
> `hub-session-start.sh` 在新 debug session 啟動時，把本次表象傳給 LLM，從 DAG 的歷史 Type D commits 中找出語義相似的問題，注入 context：
> 「三個月前 wifi-bora-expert 遇過類似症狀，當時分類為 CoEx，最後確認是 BT power burst 導致」。

---

## 五、三個關鍵 Hook 的設計

### hub-session-start.sh（語義搜尋 + Frontier）

```bash
#!/bin/bash
# 在現有 session-start.sh 之後執行

HUB_URL="${AGENTHUB_URL:-http://localhost:8080}"
HUB_API_KEY="${AGENTHUB_API_KEY:-}"
TASK_DESC="${CONNSYS_JARVIS_TASK_DESC:-}"  # 由工程師啟動 session 時設定

[ -z "$HUB_API_KEY" ] && exit 0

# 1. 取得 DAG frontier（作為本次工作的起點候選）
python3 hub_client.py get-frontier \
  --url "$HUB_URL" --api-key "$HUB_API_KEY" \
  --output ".connsys-jarvis/hub-frontier.json"

# 2. 語義搜尋歷史問題（若有 task 描述）
if [ -n "$TASK_DESC" ]; then
  python3 hub_client.py search-similar \
    --url "$HUB_URL" --api-key "$HUB_API_KEY" \
    --query "$TASK_DESC" \
    --types "debug_classification,research" \
    --top-k 3 \
    --output ".connsys-jarvis/hub-similar.md"
  # hub-similar.md 會被注入 session context（透過 expert.md 的 @include）
fi
```

### hub-mid-checkpoint.sh（Failsafe WIP push）

```bash
#!/bin/bash
# 與 mid-session-checkpoint.sh 一起被觸發（每 30 分鐘）

WIP_FILE=".connsys-jarvis/memory/wip-research.md"
[ ! -f "$WIP_FILE" ] && exit 0
[ "$HUB_AUTO_PUSH" != "true" ] && exit 0

python3 hub_client.py push-wip \
  --url "$AGENTHUB_URL" \
  --api-key "$AGENTHUB_API_KEY" \
  --expert-id "$CONNSYS_JARVIS_CURRENT_EXPERT" \
  --summary "$WIP_FILE" \
  --wip true   # 標記 WIP，協調者評估時跳過
                # session 正常結束後由 hub-session-end.sh 覆蓋
```

**WIP 機制保障**：

```
session 正常結束：
  mid-checkpoint WIP ──（被覆蓋）──► session-end 正式 commit

session 意外中斷：
  mid-checkpoint WIP 留在 DAG
  下次 session 啟動：
    hub-session-start.sh 發現有自己的 WIP → 提示工程師「上次有未完成的工作」
```

### hub-session-end.sh（研究結果 push）

```bash
#!/bin/bash
# 在現有 session-end.sh 之後執行

SUMMARY="$(cat .connsys-jarvis/memory/session-end-summary.md 2>/dev/null)"
[ -z "$SUMMARY" ] && exit 0
[ "$HUB_AUTO_PUSH" != "true" ] && exit 0

COMMIT_TYPE="${HUB_COMMIT_TYPE:-research}"   # research | code | debug_classification

python3 hub_client.py push \
  --url "$AGENTHUB_URL" \
  --api-key "$AGENTHUB_API_KEY" \
  --expert-id "$CONNSYS_JARVIS_CURRENT_EXPERT" \
  --type "$COMMIT_TYPE" \
  --content ".connsys-jarvis/memory/session-end-summary.md" \
  --wip false   # 覆蓋同 task-id 的 WIP commit（若有）
```

---

## 六、hub_client.py 核心 API

```python
# framework-agenthub-expert/skills/framework-agenthub-client-tool/hub_client.py
# 被 hooks 和 coordinator SKILL 呼叫的 library

import requests
import subprocess
import tempfile
import os
import json

class HubClient:
    def __init__(self, hub_url: str, api_key: str):
        self.hub_url = hub_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}

    # --- Frontier & DAG ---

    def get_frontier(self) -> list[dict]:
        """取得 DAG 的葉節點（可作為新工作的起點）"""
        resp = requests.get(f"{self.hub_url}/api/git/leaves", headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def get_commit_info(self, commit_hash: str) -> dict:
        resp = requests.get(f"{self.hub_url}/api/git/commits/{commit_hash}", headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    # --- Push Research / Code / WIP ---

    def push_research(self, expert_id: str, content: str,
                      sub_type: str = "debug_analysis",
                      task_id: str = None,
                      parent_hash: str = None,
                      wip: bool = False) -> dict:
        """把研究報告推送到 AgentHub DAG"""
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = self._init_work_dir(tmp, parent_hash)
            report_path = os.path.join(work_dir, "research", f"{expert_id}.md")
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            with open(report_path, "w") as f:
                f.write(content)
            msg = f"[WIP] " if wip else ""
            msg += f"{expert_id}: {sub_type}"
            if task_id:
                msg += f" task={task_id}"
            return self._commit_and_push(work_dir, msg)

    def push_ci_result(self, expert_id: str, ci_run_id: str,
                       platform_matrix: list[dict],
                       failed_logs: str,
                       parent_code_hash: str = None,
                       gerrit_change_id: str = None) -> dict:
        """把 CI/CD 多平台結果推送到 AgentHub DAG"""
        content = self._format_ci_result(
            expert_id, ci_run_id, platform_matrix,
            failed_logs, parent_code_hash, gerrit_change_id
        )
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = self._init_work_dir(tmp, parent_code_hash)
            result_path = os.path.join(work_dir, "ci-result", f"{ci_run_id}.md")
            os.makedirs(os.path.dirname(result_path), exist_ok=True)
            with open(result_path, "w") as f:
                f.write(content)
            msg = f"{expert_id}: ci-result run={ci_run_id}"
            return self._commit_and_push(work_dir, msg)

    # --- Board (Message Board) ---

    def post_to_board(self, channel: str, content: str) -> dict:
        resp = requests.post(
            f"{self.hub_url}/api/channels/{channel}/posts",
            headers=self.headers, json={"content": content}
        )
        resp.raise_for_status()
        return resp.json()

    def read_board(self, channel: str, limit: int = 10) -> list[dict]:
        resp = requests.get(
            f"{self.hub_url}/api/channels/{channel}/posts",
            headers=self.headers, params={"limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    # --- Semantic Search (語義搜尋歷史問題) ---

    def search_similar(self, query: str, commit_types: list[str],
                       top_k: int = 3) -> list[dict]:
        """
        從 DAG 歷史 commit 中找語義相似的問題。
        實作：fetch 最近 N 個 commit 的 board post，
              呼叫 LLM 做相似度排序。
        Phase 1 可先用關鍵字 + LLM 重排；Phase 3 可換 embedding。
        """
        recent_posts = []
        for channel in ["research", "debug", "ci-result"]:
            try:
                posts = self.read_board(channel, limit=50)
                recent_posts.extend(posts)
            except Exception:
                pass
        # 回傳最相關的 top_k（呼叫者用 LLM 做最終排序）
        return recent_posts[:top_k * 5]  # 回傳更多讓 LLM 篩選

    # --- Internal helpers ---

    def _init_work_dir(self, tmp_dir: str, parent_hash: str = None) -> str:
        work_dir = os.path.join(tmp_dir, "work")
        if parent_hash:
            # fetch parent commit bundle and clone
            bundle_resp = requests.get(
                f"{self.hub_url}/api/git/fetch/{parent_hash}",
                headers=self.headers
            )
            bundle_path = os.path.join(tmp_dir, "parent.bundle")
            with open(bundle_path, "wb") as f:
                f.write(bundle_resp.content)
            subprocess.run(["git", "clone", bundle_path, work_dir], check=True)
        else:
            os.makedirs(work_dir)
            subprocess.run(["git", "init"], cwd=work_dir, check=True)
        return work_dir

    def _commit_and_push(self, work_dir: str, message: str) -> dict:
        subprocess.run(["git", "add", "-A"], cwd=work_dir, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=work_dir, check=True)
        bundle_path = os.path.join(work_dir, "push.bundle")
        subprocess.run(
            ["git", "bundle", "create", bundle_path, "HEAD"],
            cwd=work_dir, check=True
        )
        with open(bundle_path, "rb") as f:
            resp = requests.post(
                f"{self.hub_url}/api/git/push",
                headers=self.headers, data=f,
                headers={**self.headers, "Content-Type": "application/octet-stream"}
            )
        resp.raise_for_status()
        return resp.json()

    def _format_ci_result(self, expert_id, ci_run_id, platform_matrix,
                          failed_logs, parent_code_hash, gerrit_change_id) -> str:
        matrix_rows = "\n".join(
            f"| {p['platform']} | {p['compiler']} | "
            f"{'✅ PASS' if p['result'] == 'pass' else '❌ FAIL'} | "
            f"{p.get('error_type', '-')} |"
            for p in platform_matrix
        )
        return f"""---
type: ci_result
parent_code_hash: {parent_code_hash or 'N/A'}
gerrit_change_id: {gerrit_change_id or 'N/A'}
ci_run_id: {ci_run_id}
from_expert: {expert_id}
---
## 平台結果矩陣
| 平台 | 編譯器版本 | 結果 | 錯誤類型 |
|------|-----------|------|---------|
{matrix_rows}

## 失敗平台 log 摘要
{failed_logs}
"""
```

---

## 七、CI/CD 橋接設計（framework-agenthub-ciresult-flow）

此 Skill 橋接 `sys-bora-cicd-tool`（現有）和 AgentHub，是 W1 工作流的核心：

```
framework-agenthub-ciresult-flow SKILL.md 執行步驟：

步驟 1：取得 Gerrit change-id（從 Type C commit metadata 或手動輸入）

步驟 2：觸發 CI run
  使用 sys-bora-cicd-tool：
  → 觸發 CI 並取得 ci_run_id

步驟 3：等待 CI 完成（輪詢）
  使用 sys-bora-cicd-tool 查詢狀態：
  → 每 N 分鐘查一次，直到所有平台完成

步驟 4：抓取各平台 log
  使用 sys-bora-cicd-tool 抓取 log：
  → 針對每個 FAIL 平台，抓取 log 並提取關鍵行（錯誤 + 周邊 10 行）

步驟 5：分類錯誤類型
  LLM 分析每個 FAIL 平台的 log：
  → 分類：linker_error | compile_error | test_fail | timeout | ...
  → 判斷：不同平台的錯誤是否相同根因？

步驟 6：push Type CI commit 到 AgentHub
  呼叫 hub_client.push_ci_result()

步驟 7：post 結果摘要到 "ci-result" channel
  格式：「ci_run_id=X: 3/4 pass, bora-bt FAIL (linker:undefined_symbol)」
```

---

## 八、跨 Workspace 設計（Phase 4，現在先預留）

### 關鍵約束（UQ3）

各 workspace（bora/gen4m/logan）是**各自獨立的 repo**。因此：

| Commit 類型 | 能否跨 workspace 共享 | 理由 |
|------------|---------------------|------|
| Type C（程式碼）| **不能** | 各自 repo，patch 不能直接套用 |
| Type CI（CI 結果）| **不能** | 不同平台矩陣，無法比對 |
| Type R（研究報告）| **可以** | 純分析洞察，無程式碼依賴 |
| Type D（debug 分類）| **可以** | 問題模式和假設可複用 |

### Channel Namespace 設計（Phase 4）

```
Phase 1（單 workspace，現在）：
  channel: "research"
  channel: "debug"
  channel: "ci-result"
  channel: "evaluation"

Phase 4（跨 workspace）：
  channel: "{workspace-id}/research"    → "bora/research", "gen4m/research"
  channel: "{workspace-id}/ci-result"   → 平台各自隔離
  channel: "cross/debug-patterns"       → 跨 workspace 的問題模式分享
  channel: "cross/research-insights"    → 跨 workspace 的研究洞察

.connsys-jarvis/.env 預留：
  HUB_WORKSPACE_ID=consys-bora          # Phase 1 設好，Phase 4 自動生效
```

**Phase 4 的實際使用場景**：

```
bora workspace 的 wifi-bora-expert 分析出 CoEx failure pattern
  └─► push Type D 到 "bora/debug" channel

gen4m workspace 的 hub-session-start.sh 在新 debug session 啟動時：
  「搜尋跨 workspace 的 cross/debug-patterns」
  └─► 找到 bora 的 CoEx 分類記錄
  └─► 注入 context：「bora workspace 3 個月前有類似問題，根因是 BT power burst」
  └─► gen4m Expert 不需要從零分析，直接從這個假設出發
```

---

## 九、實作路線圖

### Phase 1（2-3 週）：基礎接線 + Failsafe

```
目標：單 Expert session 結果自動累積，中斷有 failsafe

□ framework-agenthub-expert/ 資料夾結構
□ hub_client.py（push_research, push_wip, post_to_board, get_frontier）
□ hub-session-end.sh
□ hub-mid-checkpoint.sh（failsafe WIP）
□ hub-session-start.sh（get_frontier 部分，語義搜尋留 Phase 2）
□ .connsys-jarvis/.env 加入 hub 環境變數：
    AGENTHUB_URL=http://localhost:8080
    AGENTHUB_API_KEY=
    HUB_AUTO_PUSH=false
    HUB_WORKSPACE_ID=consys-bora
    HUB_CHECKPOINT_INTERVAL=30m
□ setup.py --init 支援 agenthub-expert 選項

驗收：
  □ 啟動本地 AgentHub server
  □ wifi-bora session 結束 → DAG 有 commit
  □ 強制中斷 session → DAG 有 WIP commit
  □ 下次 session 啟動 → 提示「有上次未完成的 WIP」
```

### Phase 2（3-4 週）：W4 Memory Slim Fan-Out

```
目標：先用最好驗證的工作流（W4）確認 fan-out 可行

□ framework-agenthub-spawn-flow SKILL.md（tmux SOP）
□ framework-agenthub-coordinator-flow SKILL.md（Fan-Out + Metric 評估）
□ hub_client.py 補充：search_similar（關鍵字 + LLM 重排，Phase 1 版）
□ hub-session-start.sh 補充：語義搜尋功能
□ /hub:refactor 指令
□ 自動 Expert 選擇邏輯（task 關鍵字 → domain 映射表）

驗收：
  □ /hub:refactor --task "縮小 wifi_mgmt.c buffer" --experts 2
  □ 兩個 Expert 在獨立 tmux session 工作，互不干擾
  □ /hub:evaluate 輸出含 memory delta 的比較報告
```

### Phase 3（4-6 週）：W1 CI/CD + W2 Debug

```
□ framework-agenthub-ciresult-flow SKILL.md（橋接 sys-bora-cicd-tool）
□ hub_client.py 補充：push_ci_result, get_commit_children
□ Type D（Debug 分類）commit 格式 + push
□ /hub:research 指令（W2 Fan-Out 分類）
□ /hub:ci-push 指令（W1 CI 觸發 + 結果 push）
□ symptom_text 語義搜尋升級（embedding 方案評估）

驗收：
  □ /hub:ci-push 自動觸發 CI，完成後 Type CI commit 出現在 DAG
  □ /hub:research 啟動 2 個 Expert 各自分類，評估後選出主假設
```

### Phase 4（6-8 週）：跨 Workspace

```
□ Channel namespace：{workspace-id}/{topic}
□ cross/ channel：debug-patterns + research-insights
□ 遠端 AgentHub server 部署
□ /hub:status 跨 workspace 統計
```

---

## 十、設計取捨總表

| 設計決策 | 選擇 | 理由 | 代價 |
|---------|------|------|------|
| framework-agenthub-expert 獨立 | 是 | 單一職責、可選安裝、可替換 | 多一個 Expert 維護 |
| CI/CD 橋接用 SKILL 不用 hook | 用 SKILL（ciresult-flow）| CI 觸發需要互動，SKILL 適合有步驟的流程 | 需要在 Expert 內主動呼叫 |
| 語義搜尋 Phase 1 用 LLM 重排 | 是 | 不需要 vector DB，Phase 1 可行 | 搜尋速度慢（O(n) board read） |
| 跨 workspace 只共享 R/D | 是 | 各自 repo，C/CI 無法跨 workspace | 程式碼 fix 需要各自重新實作 |
| WIP commit 用 task-id 覆蓋 | 是 | session-end 正式版覆蓋 WIP | task-id 需要一致性管理 |
| Phase 順序先 W4 再 W2 | 是 | W4 評估指標客觀（bytes），容易驗證 | W2 的價值更高但複雜度也更高 |
| HUB_AUTO_PUSH 預設 false | 是 | 不強制依賴，漸進採用 | 需要手動開啟才有效 |

---

## 相關連結（Related）

- [[AGENTHUB-KARPATHY-AGENT-NATIVE-COLLABORATION-INFRASTRUCTURE]] — AgentHub 技術基礎：DAG、git bundle、message board 完整分析
- [[OH-MY-CLAUDECODE-MULTI-AGENT-ORCHESTRATION]] — Claude Code multi-agent 架構，tmux fan-out 的先行案例
- [[CLAUDE-CODE-USER-VS-PROJECT-LEVEL-CONFIG-GUIDE]] — Expert 安裝層次：framework-agenthub-expert 的 scope 決策依據

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 對本設計的具體應用 |
|---------|--------------|
| **記憶** | framework-agenthub-expert、四種 Commit 類型（R/C/CI/D）、三個 Hook（session-end/mid-checkpoint/session-start）、HUB_AUTO_PUSH / HUB_WORKSPACE_ID 環境變數、WIP commit、symptom_text 語義搜尋 |
| **理解** | 整合的根本邏輯：Jarvis 的 Expert 解決「一個問題的深度工作」，AgentHub 解決「同一問題的多策略廣度探索」+ 「跨 session 的知識持久化」。四種工作類型用不同協調模式，是因為它們的「解空間結構」不同：W4 是並行無序空間（fan-out），W2 是先並行（假設競爭）後串行（深度分析），W1 是有序管線（pipeline）。 |
| **分析** | 最大風險是「LLM 語義搜尋的品質」。表象描述是自由文字，兩個描述方式完全不同的問題可能有相同根因，LLM 搜尋能否找到？反過來，描述相似但根因不同的問題更危險——如果 hub-session-start.sh 注入了錯誤的「相似問題」，可能誤導 Expert。需要 confidence score + 「僅供參考」的 framing。 |
| **應用** | ①不建 Expert，先寫一個獨立 Python 腳本測試 hub_client.py 的 push_research + get_frontier + search_similar，確認 AgentHub API 符合預期 ②選一個最近完成的 Memory Slim task，手動填寫 Type C 和 Type CI 格式，驗證格式是否涵蓋所有需要的資訊 |
| **評估** | **vs 用 Confluence/Notion 記錄歷史**：Confluence 需要人工填寫，且搜尋的是文字而非推理鏈。AgentHub 的 Type D + Type R + Type C 三連 commit 記錄的是「從表象到根因到修復」的完整推理路徑，而且是 append-only 自動累積的。**核心差異**：Confluence 記錄「決定」，AgentHub 記錄「過程」——包括失敗的嘗試。失敗嘗試往往是最有價值的知識，因為它告訴下一個人「這條路走不通，不要重複」。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：`hub-session-start.sh` 的語義搜尋在 session 啟動時執行，但工程師還沒輸入具體任務描述。是否需要一個「任務描述環境變數」`CONNSYS_JARVIS_TASK_DESC`，讓工程師在啟動 session 時就帶入，才能做有效的語義搜尋？
- **假設**：`hub-mid-checkpoint.sh` 用 30 分鐘 checkpoint，假設工程師願意讓 WIP 自動 push 到 hub。但 WIP 可能包含不成熟的分析，其他 Expert 的 session-start 語義搜尋會找到這些 WIP——需要在搜尋結果中清楚標記 `wip: true`，避免 WIP 被當作可靠的參考
- **後果**：若 AgentHub DAG 累積數百個 commit，`get_frontier()` 可能回傳大量葉節點，`hub-session-start.sh` 注入 context 時哪些 frontier 是相關的？需要一個「按 task 域過濾 frontier」的機制，否則 context 會被大量不相關的 frontier 填滿

---

## References

- [Connsys Jarvis GitHub](https://github.com/swchen44/testing/tree/main/agents/connsys-jarvis)
- [AgentHub Fork（alirezarezvani）](https://github.com/alirezarezvani/agenthub)
- [Harness Engineering — Martin Fowler Blog](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html)
