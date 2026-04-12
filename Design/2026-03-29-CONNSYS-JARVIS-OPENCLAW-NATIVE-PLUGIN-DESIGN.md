---
title: "Connsys-Jarvis × OpenClaw：原生整合設計"
date: 2026-03-29
category: Design
tags:
  - "#ai/agent"
  - "#tools/openclaw"
  - "#connsys-jarvis"
source: "內部設計文件"
source_type: article
author: "Shaowei Chen"
status: notes
links:
  - "[[2026-03-29-CONNSYS-JARVIS-STAGE3-CLAWTEAM-EXPERT-SWARM-DESIGN]]"
  - "[[2026-03-29-CONNSYS-JARVIS-AGENTHUB-INTEGRATION-DESIGN]]"
---

# Connsys-Jarvis × OpenClaw：原生整合設計

**文件版本**：v1.0
**狀態**：Draft
**目標讀者**：Connsys 韌體工程師、AI 工具開發者
**適用範圍**：connsys-jarvis Phase 2 — OpenClaw 作為執行平台

---

## 目錄

- [為什麼是 OpenClaw？](#為什麼是-openclaw)
- [架構總覽](#架構總覽)
- [三個核心設計決策](#三個核心設計決策)
  - [決策一：原生 Plugin 路線（非 ACP 橋接）](#決策一原生-plugin-路線非-acp-橋接)
  - [決策二：每個 Expert 是 OpenClaw 的一個 Agent](#決策二每個-expert-是-openclaw-的一個-agent)
  - [決策三：Gerrit 仍是 Code Exchange Bus](#決策三gerrit-仍是-code-exchange-bus)
- [OpenClaw Plugin 結構設計](#openclaw-plugin-結構設計)
  - [connsys-jarvis Plugin 目錄結構](#connsys-jarvis-plugin-目錄結構)
  - [openclaw.plugin.json](#openclaw-plugin-json)
  - [Hooks 重寫：Shell → TypeScript](#hooks-重寫shell--typescript)
- [記憶系統遷移：Git → LanceDB](#記憶系統遷移git--lancedb)
  - [三階段遷移路線](#三階段遷移路線)
  - [LanceDB 記憶架構](#lancedb-記憶架構)
- [四個 Use Case 流程](#四個-use-case-流程)
  - [UC1：CI/CD Error Fixing（多平台平行）](#uc1cicd-error-fixing多平台平行)
  - [UC2：Debug（跨 domain 平行分析）](#uc2debug跨-domain-平行分析)
  - [UC3：New Feature Design（跨 domain 協作）](#uc3new-feature-design跨-domain-協作)
  - [UC4：Memory Slim（Sequential Pipeline）](#uc4memory-slimsequential-pipeline)
- [安裝流程](#安裝流程)
- [兩個月 Roadmap](#兩個月-roadmap)
- [已知限制與風險](#已知限制與風險)
- [附錄：OpenClaw vs ClawTeam 決策指南](#附錄openclaw-vs-clawteam-決策指南)
- [延伸閱讀](#延伸閱讀)

---

## 為什麼是 OpenClaw？

connsys-jarvis 設計文件中，Phase 2 的目標是從 Claude Code 遷移到 OpenClaw：

> Phase 2：OpenClaw
> - `setup.py --target openclaw`
> - SKILL.md 直接相容
> - Shell/Python hooks → TypeScript handler.ts（此階段重寫 hooks）
> - connsys-memory → workspace/MEMORY.md + LanceDB

OpenClaw 不是工具替換——它是一個**完整的個人 AI 助理平台**：
- 常駐 daemon（launchd/systemd）
- 支援 20+ 通訊頻道（Slack、Teams、WhatsApp、Telegram 等）
- 內建 Multi-Agent 架構（`agents.list`）
- 原生 sub-agent 支援（`sessions_spawn`）
- Plugin SDK（TypeScript）
- LanceDB 記憶系統

這讓 connsys Expert 可以做到之前做不到的事：**工程師在辦公室外用手機發 Slack 訊息，Expert 在開發機上自動執行任務，結果回傳到同一個 Slack thread。**

---

## 架構總覽

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Connsys Expert × OpenClaw Gateway                     │
│                           （常駐 daemon）                                 │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Main Agent：framework-base-expert                                │  │
│  │                                                                  │  │
│  │  • framework-expert-discovery-knowhow skill                      │  │
│  │    → 知道所有可用 Expert，決定 spawn 哪個                           │  │
│  │  • framework-handoff-flow skill                                  │  │
│  │    → 寫 Hand-off 文件，傳給 sub-agent                              │  │
│  │  • LanceDB memory（shared zone）                                  │  │
│  │    → 跨 Expert 共用知識                                            │  │
│  └──────────┬──────────────┬──────────────┬───────────────────────┘  │
│             │ sessions_spawn│ sessions_spawn│ sessions_spawn           │
│   ┌─────────▼──────┐ ┌─────▼──────────┐  ┌▼────────────────────┐    │
│   │ Agent:          │ │ Agent:          │  │ Agent:              │    │
│   │ wifi-bora-      │ │ bt-bora-        │  │ wifi-gen4m-         │    │
│   │ cr-robot-expert │ │ security-expert │  │ base-expert         │    │
│   │                 │ │                 │  │                     │    │
│   │ workspace-wifi/ │ │ workspace-bt/   │  │ workspace-gen4m/    │    │
│   │ LanceDB memory  │ │ LanceDB memory  │  │ LanceDB memory      │    │
│   └────────┬────────┘ └────────┬────────┘  └──────┬─────────────┘    │
│            │ announce           │ announce          │ announce          │
│            └───────────────────┴──────────────────┘                   │
│                                 ↓                                      │
│                     Main Agent 接收結果，回報工程師                       │
└─────────────────────────────────────────────────────────────────────────┘
              ↑ Channels（任意一種或多種同時開啟）
              Slack ● Teams ● WhatsApp ● Telegram ● CLI ● Web
```

---

## 三個核心設計決策

### 決策一：原生 Plugin 路線（非 ACP 橋接）

**ACP 橋接（輕量但受限）**：
OpenClaw 能透過 `sessions_spawn --runtime acp` 啟動 Claude Code 實例作為 sub-agent。這讓 connsys-jarvis 的 Shell hooks 完全不需要修改。

**原生 Plugin 路線（本文採用）**：
直接把 connsys-jarvis 做成 OpenClaw 原生 plugin。Hooks 改寫為 TypeScript `handler.ts`，深度整合到 OpenClaw 的 Gateway 生命週期。

| 比較面向 | ACP 橋接 | 原生 Plugin |
|---------|---------|------------|
| 改動幅度 | 小（Hooks 不動）| 中（Hooks 重寫為 TypeScript）|
| OpenClaw 整合深度 | 淺（Claude Code 是黑盒）| 深（lifecycle hook 完整掌控）|
| LanceDB 記憶整合 | ✗（仍用 Git）| ✓（直接寫入）|
| Session 管理 | Claude Code 自己管 | OpenClaw Gateway 統一管理 |
| 頻道觸發 | ✓（通過 OpenClaw relay）| ✓（深度整合）|
| 未來擴充性 | 受限（Claude Code 版本耦合）| 高（Plugin SDK 完整 API）|

**選擇原生 Plugin 的理由**：每次 Shell hooks 要讀寫 LanceDB 都需要額外 bridge；`session-end.sh` 無法得知 OpenClaw 的 token 用量；記憶系統遷移到 LanceDB 後兩套並存會造成混亂。

---

### 決策二：每個 Expert 是 OpenClaw 的一個 Agent

```json
// ~/.openclaw/config.json（相關部分）
{
  "agents": {
    "list": [
      {
        "id": "framework-base",
        "name": "Connsys Framework Base Expert",
        "default": true,
        "workspace": "~/.openclaw/workspaces/framework",
        "description": "跨 domain 協調者，知道如何 spawn 其他 Expert",
        "skills": ["@connsys/framework-base-plugin"],
        "sandbox": { "mode": "off" }
      },
      {
        "id": "wifi-bora-cr-robot",
        "name": "WiFi Bora CR Robot Expert",
        "workspace": "~/.openclaw/workspaces/wifi-bora",
        "description": "WiFi bora CI/CD 錯誤修復、debug、code review",
        "skills": ["@connsys/wifi-bora-cr-robot-plugin"],
        "sandbox": { "mode": "off" }
      },
      {
        "id": "bt-bora-security",
        "name": "BT Bora Security Expert",
        "workspace": "~/.openclaw/workspaces/bt-bora",
        "description": "BT bora security rule 檢查、debug、gerrit 上傳",
        "skills": ["@connsys/bt-bora-security-plugin"]
      },
      {
        "id": "wifi-gen4m-base",
        "name": "WiFi Gen4M Base Expert",
        "workspace": "~/.openclaw/workspaces/wifi-gen4m",
        "description": "WiFi gen4m driver build、debug"
      }
    ]
  },
  "bindings": [
    {
      "agentId": "framework-base",
      "match": { "provider": "slack", "accountId": "*" }
    }
  ]
}
```

**Binding 設計**：Slack/Teams 訊息預設路由到 `framework-base` agent。framework-base 判斷任務後 spawn 對應的 Expert sub-agent，結果 announce 回 Slack thread。

---

### 決策三：Gerrit 仍是 Code Exchange Bus

OpenClaw sub-agent 的通訊方式是「announce 完工結果回主 agent 的 chat」——這和 ClawTeam 的 JSON inbox 不同，但對 Gerrit Change-ID 傳遞完全足夠：

```
Sub-agent 完成修改
  → git push refs/for/main%topic=connsys-{task-id}
  → announce 回 framework-base：
    "CI fix done. Change-ID: I3a4b5c6d. Topic: connsys-wifi-ci-{task-id}"

Framework-base 收到
  → 若需要 B 接手：對 bt-bora-security sub-agent 發送任務
    "Download I3a4b5c6d, continue task"
  → 或直接回報 Slack：「WiFi CI 修完，Gerrit Change 待 review」
```

---

## OpenClaw Plugin 結構設計

### connsys-jarvis Plugin 目錄結構

每個 Expert 成為一個獨立的 npm package：

```
@connsys/wifi-bora-cr-robot-plugin/
├── openclaw.plugin.json          ← OpenClaw 原生 plugin manifest
├── package.json
├── src/
│   ├── index.ts                  ← Plugin 入口（register capabilities）
│   └── hooks/
│       ├── session-start.ts      ← 取代 session-start.sh
│       ├── session-end.ts        ← 取代 session-end.sh
│       ├── pre-compact.ts        ← 取代 pre-compact.sh
│       └── mid-checkpoint.ts     ← 取代 mid-session-checkpoint.sh
├── skills/                       ← SKILL.md 格式，直接相容
│   ├── wifi-bora-build-flow/
│   │   └── SKILL.md
│   ├── wifi-bora-coredump-knowhow/
│   │   └── SKILL.md
│   └── wifi-bora-cr-robot-flow/
│       └── SKILL.md
├── commands/                     ← COMMAND.md（Claude bundle 相容）
│   └── wifi-bora-cr-robot-tool/
│       └── COMMAND.md
└── soul.md                       ← Expert 身份定義（注入 system prompt）
```

### openclaw.plugin.json

```json
{
  "id": "wifi-bora-cr-robot-plugin",
  "version": "1.0.0",
  "name": "WiFi Bora CR Robot Expert",
  "description": "WiFi bora firmware CI/CD error fix, debug, code review",
  "openclaw": {
    "runtime": "1.x",
    "entrypoint": "src/index.ts"
  },
  "capabilities": {
    "skills": true,
    "hooks": true,
    "systemPrompt": "soul.md"
  }
}
```

### Hooks 重寫：Shell → TypeScript

**session-start.sh 改寫範例**（原本的 Bash → TypeScript）：

```typescript
// src/hooks/session-start.ts
import type { SessionStartHook } from 'openclaw/plugin-sdk';
import { readHandoff, readSharedMemory } from '../memory/lancedb-adapter';

export const onSessionStart: SessionStartHook = async (ctx) => {
  const agentId = ctx.agent.id;

  // 1. 偵測是否有待接的 hand-off（取最近一筆）
  const latestHandoff = await readHandoff(agentId);
  if (latestHandoff) {
    ctx.injectContext([
      `## 來自上一個 Expert 的交接`,
      latestHandoff.content,
      '',
    ].join('\n'));
  }

  // 2. 載入共用記憶（project.md, conventions.md）
  const sharedMemory = await readSharedMemory();
  if (sharedMemory.project) {
    ctx.injectContext([
      `## 專案共用知識`,
      sharedMemory.project,
      '',
    ].join('\n'));
  }
};
```

**session-end.ts**（取代 session-end.sh）：

```typescript
// src/hooks/session-end.ts
import type { SessionEndHook } from 'openclaw/plugin-sdk';
import { writeSummary, writeHandoff } from '../memory/lancedb-adapter';

export const onSessionEnd: SessionEndHook = async (ctx) => {
  const summary = await ctx.summarizeSession({ maxTokens: 2000 });
  const agentId = ctx.agent.id;

  // 1. 寫入工作記憶（LanceDB）
  await writeSummary(agentId, {
    timestamp: new Date().toISOString(),
    summary: summary.text,
    tokens: ctx.usage.totalTokens,
  });

  // 2. 若需要手交接（有 next expert 設定）
  if (ctx.session.nextAgent) {
    await writeHandoff(agentId, ctx.session.nextAgent, {
      runId: ctx.session.id,
      summary: summary.text,
      gerritChanges: ctx.session.metadata?.gerritChanges ?? [],
    });
  }
};
```

**pre-compact.ts**（取代 pre-compact.sh）：

```typescript
// src/hooks/pre-compact.ts
import type { PreCompactHook } from 'openclaw/plugin-sdk';
import { writeWorkingMemory } from '../memory/lancedb-adapter';

export const onPreCompact: PreCompactHook = async (ctx) => {
  // Context 壓縮前存快照（最可靠的存檔點）
  const snapshot = await ctx.snapshotContext();
  await writeWorkingMemory(ctx.agent.id, snapshot);
};
```

---

## 記憶系統遷移：Git → LanceDB

### 三階段遷移路線

```
Phase 1（現在）：Git-based connsys-memory
  → session-end.sh 寫入 Markdown + git push
  → 本地三區記憶（shared/working/handoffs）

Phase 2（OpenClaw 整合，M1–M2）：雙軌並存
  → session-end.ts 同時寫 Markdown 和 LanceDB
  → LanceDB 開始累積向量索引
  → 驗證 LanceDB 記憶品質

Phase 3（M3+）：全面 LanceDB
  → 移除 Git 路徑的 memory 寫入
  → 改用 LanceDB semantic search 查詢相似 session
  → framework-base-expert 可以跨時間做語意檢索：
    「上次 wifi coredump 的修法是什麼？」
```

### LanceDB 記憶架構

```
LanceDB（~/.openclaw/workspaces/{agentId}/memory.lance）
├── table: sessions
│   ├── id (str)           ← session UUID
│   ├── agent_id (str)
│   ├── timestamp (str)
│   ├── summary (str)      ← 壓縮摘要（< 2000 tokens）
│   ├── summary_vec (vec)  ← 向量索引，供語意搜尋
│   └── gerrit_changes     ← 關聯的 Gerrit Change-ID 清單
│
├── table: handoffs
│   ├── run_id (str)
│   ├── from_agent (str)
│   ├── to_agent (str)
│   ├── content (str)      ← 交接文件
│   ├── content_vec (vec)
│   └── status (str)       ← read / unread
│
└── table: shared          ← 跨 Expert 共用知識（原 Zone 1）
    ├── key (str)          ← 'project', 'conventions', 'decisions'
    ├── content (str)
    └── content_vec (vec)
```

**LanceDB 的新能力**（Git 做不到的）：

```typescript
// 語意搜尋：找最相關的歷史 session
const results = await lancedb.sessions.search(
  "wifi coredump NULL pointer bora",
  { limit: 3 }
);
// 回傳最相似的 3 個歷史 session，注入 context
```

---

## 四個 Use Case 流程

### UC1：CI/CD Error Fixing（多平台平行）

```
工程師 (Slack): "wifi-bora CI #1234 失敗，bt-bora CI #5678 也失敗了"
  │
  ▼
OpenClaw Gateway → framework-base-expert 收到訊息
  │
  │ sessions_spawn (parallel, mode: "run")
  ├──────────────────────────────────────────────────────┐
  │                                                      │
  ▼                                                      ▼
wifi-bora-cr-robot sub-agent                    bt-bora-security sub-agent
  workspace: ~/.openclaw/workspaces/wifi-bora    workspace: ...bt-bora
  task: 分析 CI #1234 log，修復，上傳 Gerrit      task: 分析 CI #5678 log
    │                                                      │
    ├─ repo sync (shared ref repo 加速)                    ├─ repo sync
    ├─ analyze build log                                   ├─ analyze test log
    ├─ fix build error                                     ├─ fix test failure
    ├─ git push refs/for/main%topic=connsys-{id}           ├─ git push ...
    └─ announce → framework-base:                          └─ announce:
       "Done. Change: I3a4b5c. Build pass."                   "Done. Change: I7d8e9f."
  │
  ▼
framework-base 彙整
  → Slack reply (thread): "兩個 CI 修完了！
    WiFi: I3a4b5c https://gerrit/c/...
    BT:   I7d8e9f https://gerrit/c/...
    待 human review 後 submit。"
```

**工程師體驗**：發一條 Slack 訊息，兩個 Expert 平行工作，幾分鐘後同一個 thread 收到結果。

---

### UC2：Debug（跨 domain 平行分析）

```
工程師 (Teams): "WiFi/BT coexistence 有問題，附上 uart log 和 hci log"
  │
  ▼
framework-base-expert 分析訊息 → 決定 spawn 兩個分析 sub-agent
  │
  ├─ sessions_spawn wifi-bora-cr-robot
  │    task: "分析附件 uart log，找 WiFi 側問題"
  │    → announce: "WiFi: NULL ptr in coex_sched 0x3a4b"
  │
  └─ sessions_spawn bt-bora-security
       task: "分析附件 hci log，找 BT 側問題"
       → announce: "BT: coex timeout at 0x7c8d"
  │
  ▼
framework-base 整合兩份分析
  → Teams reply: "確認是 coex_sched race condition。
    建議 spawn wifi-bora-cr-robot 進行修復。
    [需要嗎？]"

工程師: "好，開始修"
  → framework-base spawn wifi-bora-cr-robot（修復任務）
```

**關鍵差異**：分析用輕量 sub-agent（mode: "run"，快速完成），修復用完整 Expert（有 workspace + memory）。

---

### UC3：New Feature Design（跨 domain 協作）

```
工程師 (Slack): "設計一個新的 WiFi/BT dynamic coexistence 機制，需要三個 domain 的 interface"
  │
  ▼
framework-base spawn 三個設計 sub-agent（parallel）：
  ├─ wifi-bora：設計 wifi_coex_api.h → push Gerrit，topic: connsys-coex-design-001
  ├─ bt-bora：  設計 bt_coex_api.h  → Gerrit review wifi 的 Change，回覆 comment
  └─ sys-bora： 設計 platform sched  → review 兩者，push platform_coex_sched.h
  │
  ▼
各 sub-agent announce 完成
  → framework-base 整合設計
  → Slack: "設計完成。3 個 interface headers 已上傳 Gerrit。
    topic: connsys-coex-design-001
    建議下一步：人工 review interface 後開始實作。"
```

---

### UC4：Memory Slim（Sequential Pipeline）

```
工程師 (WhatsApp): "bora wifi memory 超了，幫我做 slim"
  │
  ▼
framework-base → 啟動 3 段 sequential pipeline

[Stage 1] spawn wifi-bora-memory-slim sub-agent（分析）
  mode: "run"（一次性任務）
  task: 分析 symbol map + AST，找出 bloat
  → 產出 memory-slim-report.md
  → push Gerrit Change: I-analysis-01, topic: connsys-memslim-{id}
  → announce: "分析完成。Change: I-analysis-01。候選清單：20 個函式。"

[Stage 2] framework-base 收到 → spawn wifi-bora-memory-slim（實作）
  task: "Download I-analysis-01，套用優化 patch，build 驗證"
  → repo download I-analysis-01
  → apply patches
  → local build pass
  → push Change: I-patch-01（parent: I-analysis-01）
  → announce: "Patch 完成。Build pass. Change: I-patch-01"

[Stage 3] spawn wifi-bora-memory-slim（驗證）
  task: "Download I-patch-01，執行 WUT + preflight CI"
  → WUT pass
  → memory footprint: -12%
  → announce: "驗證通過。記憶體減少 12%。Change 待 review。"

framework-base → WhatsApp 回報：
  "Memory slim 完成！-12%。
   3 個 Changes：I-analysis-01 → I-patch-01 → I-validate-01
   等你 Gerrit review 後 submit。"
```

**工程師體驗**：出門在外用手機發一條 WhatsApp，回到辦公室開 Gerrit 就看到 3 個整理好的 Change。

---

## 安裝流程

### Step 1：在開發機安裝 OpenClaw Gateway

```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon

# daemon 安裝後，開發機永遠在線
# 工程師可從任何裝置透過 Slack/Teams 觸發任務
```

### Step 2：安裝 connsys-jarvis OpenClaw Plugin

```bash
# 從 connsys-jarvis repo 安裝各 Expert plugin
openclaw plugins install ./connsys-jarvis/framework/framework-base-expert
openclaw plugins install ./connsys-jarvis/wifi-bora/wifi-bora-cr-robot-expert
openclaw plugins install ./connsys-jarvis/bt-bora/bt-bora-security-expert
openclaw plugins install ./connsys-jarvis/wifi-bora/wifi-gen4m-base-expert

openclaw gateway restart
```

### Step 3：設定 Agents + Channel Binding

編輯 `~/.openclaw/config.json`，加入 agents 清單和 Slack/Teams binding（見前文設計）。

### Step 4：Shared Reference Repo

```bash
# 建立 shared reference repo（加速 Expert workspace 的 repo sync）
mkdir /workspace-shared
cd /workspace-shared
repo init -u {manifest-url}
repo sync -j8

# cron：每天凌晨更新 shared reference
echo "0 3 * * * cd /workspace-shared && repo sync -j8" | crontab -
```

### Step 5：Shared Reference 環境變數

```json
// ~/.openclaw/config.json 加入
{
  "agents": {
    "env": {
      "CONNSYS_SHARED_REF_PATH": "/workspace-shared",
      "GERRIT_URL": "https://gerrit.example.com"
    }
  }
}
```

---

## 兩個月 Roadmap

### Phase 1（M1）：基礎連通

| 週次 | 工作項目 | 產出 |
|------|---------|------|
| W1 | 安裝 OpenClaw Gateway；以 Claude bundle format 安裝 skills | Skills 從 Slack 可觸發 |
| W1 | 設定 agents.list（framework-base + 2 個 Expert agents）| Multi-agent 基本可用 |
| W2 | 實作 TypeScript session-start.ts（讀 LanceDB handoff）| Hand-off 機制可用 |
| W2 | 實作 TypeScript session-end.ts（寫 LanceDB）| 記憶系統開始累積 |
| W3 | 測試 UC1（CI/CD fix）端到端，從 Slack 觸發 | 驗證 parallel spawn + Gerrit |
| W4 | 測試 UC4（Memory slim）sequential pipeline | 驗證 announce 鏈條 |

**Phase 1 風險**：OpenClaw Plugin SDK 的 hook 事件名稱可能需要查閱最新文件確認（`onSessionStart`、`onSessionEnd`、`onPreCompact` 的確切 API）。

---

### Phase 2（M2）：完整原生整合

| 週次 | 工作項目 | 產出 |
|------|---------|------|
| W5 | 實作 pre-compact.ts（snapshot）| 最可靠的存檔點可用 |
| W5 | 實作 mid-checkpoint.ts（每 20 訊息）| 長 session 不遺失 |
| W6 | 加入 LanceDB memory plugin；雙軌寫入驗證 | Git + LanceDB 並存 |
| W6 | 把所有 Expert plugins npm publish 到內部 registry | 標準安裝流程可用 |
| W7 | 測試 UC2（debug）和 UC3（feature design）| 4 個 use case 全部驗證 |
| W8 | 移除 Git memory 寫入路徑，全面 LanceDB | Phase 2 完成 |

---

## 已知限制與風險

| 限制 | 說明 | 緩解策略 |
|------|------|---------|
| **TypeScript 學習成本** | Hooks 從 Shell 改寫為 TypeScript，韌體工程師需要學 TS | 提供完整的 hook 範本；初期可用 ACP 橋接過渡 |
| **OpenClaw Plugin SDK 相容性** | SDK API 可能隨版本變動（`handler.ts` 介面）| 釘定 OpenClaw 版本；升版前先跑 integration test |
| **Sub-agent 無共享 inbox** | OpenClaw sub-agent 只能 announce 回主 agent，不能主動互發訊息 | Worker 間協調透過 Gerrit Change-ID 傳遞（via 主 agent relay）|
| **LanceDB 遷移資料損失** | 遷移期間若 Git 和 LanceDB 同時寫入，可能有競爭 | Phase 2 期間維持雙軌並存；Phase 3 才停 Git 路徑 |
| **Gerrit submit 風險** | Sub-agent 不應執行 `gerrit review --submit` | soul.md 明確禁止；skill 的 must-never 規則加入 |
| **Daemon 安全** | OpenClaw 常駐在線，攻擊面較大 | 依 OpenClaw 官方 security hardening 設定；只開放 Slack/Teams allowlist |

---

## 附錄：OpenClaw vs ClawTeam 決策指南

> **你只選一個，這個比較幫你做決定。**

| 決策面向 | OpenClaw | ClawTeam |
|---------|----------|----------|
| **架構複雜度** | 高（daemon + plugin SDK + TypeScript）| 低（CLI + Python + JSON）|
| **啟動時間** | 1–2 個月才能完整原生整合 | 2–3 週可驗證基本流程 |
| **Hooks 重寫** | 需要（Shell → TypeScript）| 不需要（Shell/Python 直接用）|
| **多 Agent 協調** | 內建（sessions_spawn + announce）| 需整合 ClawTeam spawn + inbox |
| **頻道整合** | 原生（Slack/Teams/WhatsApp/Telegram/etc.）| ✗（純 CLI）|
| **記憶系統** | LanceDB（向量語意搜尋）| ✗（需外掛 connsys-memory）|
| **Always-on 能力** | ✓（daemon）| ✗（手動觸發）|
| **手機觸發任務** | ✓ | ✗ |
| **對韌體工程師的門檻** | 高（TypeScript、plugin API）| 低（Python CLI）|
| **connsys-jarvis 長期路線** | ✓（Phase 2 設計目標）| 非設計路線（ClawTeam 是社群工具）|
| **社群生態** | OpenClaw 有活躍社群和 ClawHub 市場 | ClawTeam 3800+ stars 但較少整合文件 |

### 快速決策樹

```
你的首要需求是什麼？
│
├── 工程師能用手機 / Slack 遠端觸發任務
│   → 選 OpenClaw
│
├── 盡快（2–3 週）驗證 Multi-Agent 概念
│   → 選 ClawTeam
│
├── 不想碰 TypeScript，全用 Python/Shell
│   → 選 ClawTeam
│
├── 記憶體系統要有語意搜尋能力
│   → 選 OpenClaw
│
└── connsys-jarvis 的長期演進路線要統一
    → 選 OpenClaw（Phase 2 設計目標）
```

### 我的建議

**如果你有 2 個月，選 OpenClaw。**
理由：它是 connsys-jarvis 設計文件裡本來就寫好的 Phase 2 目標，代表設計本身已經考慮過這條路的可行性；LanceDB 的語意記憶系統會讓 Expert 越用越聰明；頻道整合讓工程師的使用體驗大幅提升。

**如果你只有 2–3 週想先驗證概念，選 ClawTeam。**
理由：ClawTeam 的 Worker 直接用 Claude Code + connsys-jarvis 不需任何修改；JSON inbox 比 announce 更直覺；Python/Shell 對韌體工程師更親切。

**最終提醒**：兩者都採用 Gerrit 作為 Code Exchange Bus，這個設計不受平台選擇影響，可以先確定。

---

## 待補充（Open Questions）

- OpenClaw Plugin SDK 目前處於哪個穩定版本？`onSessionStart`、`onSessionEnd`、`onPreCompact` 等 hook API 在過去的 minor version 之間是否曾有 breaking change？（建議搜尋：`openclaw plugin sdk hook api changelog breaking change`）
- LanceDB 的向量索引在 macOS 上的 ARM 架構（Apple Silicon）和 x86 Linux 上的效能差異如何？韌體工程師的開發機環境是否需要特別的建置設定？（建議搜尋：`lancedb apple silicon arm performance setup`）
- OpenClaw 常駐 daemon 的安全模型為何？外部攻擊者若能存取開發機的 Slack/Teams 帳號，是否可以讓 Expert 執行任意指令？allowlist 的邊界怎麼設定才安全？（建議搜尋：`openclaw daemon security model allowlist command injection`）
- Gerrit Change-ID 傳遞是透過 announce 訊息（純文字），若 framework-base-expert 誤解 Change-ID 格式或 sub-agent announce 訊息結構改變，整個 pipeline 會如何失效？是否應該有結構化的 handoff 格式？（建議搜尋：`openclaw sub-agent announce structured output contract`）
- 多個 Expert sub-agent 同時寫入 LanceDB 的同一個 shared table 時，是否有 write contention 問題？LanceDB 的並發寫入模型是什麼？（建議搜尋：`lancedb concurrent write transaction isolation`）
- OpenClaw 的 `sessions_spawn` 在 sub-agent 執行期間若主 agent session 超時或被重啟，sub-agent 的執行狀態與 LanceDB 寫入是否能保持一致？（建議搜尋：`openclaw sessions spawn parent session timeout recovery`）

## 延伸閱讀

- [Connsys-Jarvis Stage 3 × ClawTeam 設計](2026-03-29-CONNSYS-JARVIS-STAGE3-CLAWTEAM-EXPERT-SWARM-DESIGN.md)
- connsys-jarvis agents-design.md §14（遷移路線）
- [OpenClaw Plugin SDK 文件](https://docs.openclaw.ai/plugins/sdk-overview)
- [OpenClaw Sub-agents 文件](https://docs.openclaw.ai/tools/subagents)
- [OpenClaw ACP Agents 文件](https://docs.openclaw.ai/tools/acp-agents)
- [OpenClaw LanceDB Memory Plugin](https://docs.openclaw.ai/memory/lancedb)

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 三個核心設計決策（原生 Plugin 路線、每個 Expert 是 OpenClaw 的一個 Agent、Gerrit 仍是 Code Exchange Bus）、connsys-jarvis Plugin 目錄結構（`openclaw.plugin.json`、`soul.md`、TypeScript hooks）、LanceDB 三個 table（sessions、handoffs、shared）、三階段記憶系統遷移路線（Git-based → 雙軌並存 → 全面 LanceDB）、四個 Use Case（UC1 CI/CD、UC2 Debug、UC3 Feature Design、UC4 Memory Slim）、OpenClaw vs ClawTeam 決策矩陣 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | 本設計文件的核心邏輯是：將 connsys-jarvis 從「Claude Code 的技能集合」升級為「以 OpenClaw 為執行平台的原生多代理人系統」。這個升級的關鍵價值是三層解耦：(1) 任務定義（SKILL.md）與執行平台解耦，(2) Agent 身份（soul.md）與通訊頻道解耦，(3) 記憶系統從 Git 的版本控制語意遷移到 LanceDB 的向量語意搜尋。Gerrit 作為 Code Exchange Bus 的設計則讓「平台無關的 Agent 協作」能透過既有的程式碼審查流程自然落地。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 1. **原生 Plugin 路線的風險集中化假設**：選擇深度整合 OpenClaw 的原生 Plugin 路線，假設 OpenClaw 的 Plugin SDK API 足夠穩定；但文件本身在「已知限制」中承認 SDK API 可能有 breaking change，這意味著一旦 OpenClaw 升版或停止維護，整個 hooks 層需要重寫，風險被集中化而非分散。2. **Gerrit 純文字 announce 的脆弱性**：sub-agent 透過純文字 announce 傳遞 Change-ID（如 "Change-ID: I3a4b5c6d"），framework-base 再解析文字提取 ID，這個設計高度依賴 announce 訊息格式的一致性，任何 sub-agent prompt 的細微改動都可能破壞整個 pipeline，缺乏結構化的 handoff 合約。3. **LanceDB 並發寫入的假設**：四個 Use Case 中多個 sub-agent 同時執行並寫入 LanceDB 的 shared table，但文件未確認 LanceDB 的並發寫入模型，可能存在 write contention 或資料一致性問題。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. **Phase 1 驗證的最小可行路徑**：按照 Roadmap 的 W1-W2，先以 Claude bundle format 安裝 skills（不重寫 hooks），驗證從 Slack 觸發 framework-base 的基本流程，再逐步加入 TypeScript session-start.ts，避免一次性引入太多未知變數。2. **建立 announce 訊息的結構化合約**：在 soul.md 和每個 Expert 的 SKILL.md 中定義標準化的 announce 格式（如 JSON 格式的完工報告），讓 framework-base 能可靠地解析而不依賴自然語言 pattern matching。3. **先做 ACP 橋接的 spike**：在投入完整原生 Plugin 重寫之前，用 `sessions_spawn --runtime acp` 快速驗證多代理人的基本協作流程是否如預期運作，降低技術假設風險後再做完整重寫。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | **原生 Plugin vs ACP 橋接**：原生 Plugin 在功能完整性（LanceDB 整合、lifecycle hook 完整掌控）和長期維護性上更優，但引入了 TypeScript 學習成本、SDK 版本耦合風險、以及更長的初期實作時間；ACP 橋接在短期驗證速度和風險隔離上更優，但犧牲了記憶系統整合和頻道觸發的深度。**OpenClaw vs ClawTeam**：OpenClaw 是 connsys-jarvis Phase 2 的設計目標，長期路線明確，但 2 個月才能完整整合，且對韌體工程師有較高的 TypeScript 門檻；ClawTeam 在 2-3 週可驗證基本概念，Shell/Python 對韌體工程師更親切，但缺乏 Always-on daemon 和頻道整合能力。決策樹建議：若主要目標是「工程師能從手機遠端觸發任務」，選 OpenClaw；若主要目標是「快速驗證 Multi-Agent 概念」，選 ClawTeam。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：設計文件選擇「Gerrit 作為 Code Exchange Bus」而非讓 sub-agent 直接透過 LanceDB 傳遞任務上下文——這個選擇的核心假設是什麼？在哪些情境下，Gerrit Change-ID 傳遞的方式會比直接的 Agent-to-Agent 通訊更可靠，哪些情境下反而更脆弱？
- **假設**：本設計假設韌體工程師會接受學習 TypeScript 來重寫 hooks——但韌體工程師通常的技術棧是 C/C++/Python，TypeScript 的學習曲線是一個現實阻力。若這個假設不成立，回退到 ACP 橋接路線時，哪些核心功能會永久缺失，這個取捨是否可以接受？
- **證據**：LanceDB 的「語意搜尋」（「上次 wifi coredump 的修法是什麼？」）被列為 Git 記憶系統做不到的新能力——但目前 Phase 1 的目標是完成基本連通，LanceDB 的向量索引在韌體工程師的實際查詢場景中是否有足夠的召回率（recall）？是否有對工程 log 和程式碼摘要的向量化效果的實驗數據？
- **觀點**：框架選擇了「每個 Expert 是 OpenClaw 的一個獨立 Agent」的設計——另一種可能是「單一 Agent 搭配豐富的 skills」（更接近現在的 Claude Code + connsys-jarvis 設計）。在什麼條件下，「多 Agent 隔離」比「單 Agent 豐富技能」更優？記憶隔離的邊界如何在韌體工程師的日常工作中實際體現？
- **後果**：OpenClaw daemon 常駐在開發機上，開放 Slack/Teams 頻道接收任何已授權帳號的指令——若一個合法帳號（如工程師的手機）被社交工程攻擊（如偽造的「請幫我 push 這個緊急修復」訊息），Expert 執行惡意任務的最壞情境是什麼？soul.md 的禁止規則和 skill 的 must-never 約束在這個情境下是否足夠作為安全防線？
