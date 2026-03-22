---
title: "claude-code-hooks — 程式碼深度分析"
date: 2026-01-24
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#javascript"
  - "#tools/claude-code"
  - "#security"
source: "https://github.com/karanb192/claude-code-hooks"
source_type: code
author: "karanb192"
status: notes
links:
  - "[[CLAUDE-CODE-HOOKS-GUIDE]]"
  - "[[CLAUDE-CODE-SKILLS]]"
  - "[[AI-AGENT-SAFETY]]"
github_stars: 298
github_language: JavaScript
---

## 摘要（Summary）

`claude-code-hooks` 是一個 Claude Code Hooks 的開源集合，提供「複製即用（Copy-Paste-Ready）」的 hook 腳本，涵蓋安全防護、自動化工作流程（Automated Workflow）與 Slack 通知。共 262 個測試，**零外部依賴**（Pure Node.js），採用統一的 stdin/stdout JSON 管道（Pipe）架構。298 顆 stars，持續更新中。

## Why — 為什麼存在？

- **核心動機**：Claude Code 的 hook 系統功能強大，但官方文件缺乏實際可用範例。工程師看到 hook 概念後不知如何開始
- **取代/改善什麼**：取代「自己從頭寫 hook」的摸索成本，提供已測試、文件齊全的參考實作
- **目標用戶**：Claude Code 重度使用者，希望為 AI 助手加上安全護欄（Safety Guardrail）與工作流程自動化

## What — 是什麼？

- **主要功能**：
  - `block-dangerous-commands.js` — 阻擋 23 種危險 Bash 指令模式，3 個安全等級可設定
  - `protect-secrets.js` — 阻擋對敏感檔案的讀取/修改/外洩，覆蓋 50+ 種檔案模式與 Bash 指令
  - `auto-stage.js` — 每次 Claude 編輯檔案後自動 `git add`
  - `notify-permission.js` — Claude 等待輸入時推送 Slack 通知
  - `event-logger.py` — 記錄所有 hook 事件的完整 JSON 負載（Payload），用於開發/偵錯
- **不做什麼（Non-goals）**：不是 hook 框架，不抽象 hook API，每個腳本獨立運作
- **技術棧（Tech Stack）**：Node.js ≥18（JavaScript）、Python 3（event-logger 專用）、零 npm 依賴

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────┐
│                   Claude Code                           │
│  (觸發 PreToolUse / PostToolUse / Notification event)   │
└───────────────────────┬─────────────────────────────────┘
                        │ JSON via stdin
                        ▼
┌───────────────────────────────────────────────────────────┐
│              Hook Script（獨立 Node.js 程序）              │
│                                                           │
│  stdin JSON                                               │
│   ├─ session_id                                           │
│   ├─ tool_name        ┌──────────────────────────────┐   │
│   ├─ tool_input  ───► │  Pattern Matching / Logic    │   │
│   ├─ cwd             │  (SAFETY_LEVEL 可設定)        │   │
│   └─ hook_event_name  └──────────────────────────────┘   │
│                                │                         │
│                    ┌───────────▼────────────┐            │
│                    │  Log to JSONL file     │            │
│                    │  ~/.claude/hooks-logs/ │            │
│                    └───────────────────────┘            │
│                                │                         │
│                        stdout JSON                        │
│                         ├─ {} (允許)                      │
│                         └─ permissionDecision: deny       │
└──────────────────────────┬────────────────────────────────┘
                           │ JSON via stdout
                           ▼
┌─────────────────────────────────────────────────────────┐
│               Claude Code（繼續 or 阻斷）                │
└─────────────────────────────────────────────────────────┘
```

### 執行流程圖（Execution Flowchart，以 block-dangerous-commands 為例）

```
 Claude Code 嘗試執行 Bash 指令
           │
           ▼
  [hook 程序啟動 ~50-100ms]
           │
           ▼
  [讀取 stdin JSON]
           │
           ▼
  [解析 tool_name]
           │
    ┌──────▼──────┐
    │ tool_name   │
    │  == 'Bash'? │
    └──────┬──────┘
           │ 否 ──────────────────────► console.log('{}') → 允許
           │ 是
           ▼
  [取出 tool_input.command]
           │
           ▼
  [SAFETY_LEVEL 決定閾值]
  (critical=1 / high=2 / strict=3)
           │
           ▼
  [逐一比對 23 個 regex 模式]
           │
    ┌──────▼──────┐
    │  命中模式？  │
    └──────┬──────┘
           │ 否 ──────────────────────► console.log('{}') → 允許
           │ 是
           ▼
  [寫入日誌 ~/.claude/hooks-logs/]
           │
           ▼
  [輸出 permissionDecision: deny]
           │
           ▼
  Claude Code 看到阻斷原因，調整行動
```

### 時序圖（PreToolUse 攔截完整流程）

```
 Claude Code    block-dangerous-commands.js    ~/.claude/hooks-logs/
     │                     │                           │
     │── stdin JSON ───────►│                           │
     │   {tool_name:Bash,   │                           │
     │    command:          │                           │
     │    "rm -rf ~"}       │                           │
     │                     │                           │
     │                     │── appendFileSync() ───────►│
     │                     │   (BLOCKED 記錄)            │
     │                     │                           │
     │◄── stdout JSON ──────│                           │
     │    {permissionDecision:                          │
     │     "deny",          │                           │
     │     reason:          │                           │
     │     "🚨 rm-home..."}  │                           │
     │                     │                           │
     │ (不執行指令)          │                           │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 雙模組模式（Dual-Mode Module Pattern）
> 每個 Node.js 腳本都同時支援兩種使用方式：作為 CLI（`require.main === module` 時執行 `main()`）以及作為可 import 的模組（`module.exports` 匯出所有函式）。這使得單元測試（Unit Testing）無需啟動子程序（Subprocess）。

1. **零依賴（Zero Dependencies）** — 僅使用 Node.js 內建模組（`fs`、`path`、`child_process`），安裝步驟只需複製檔案，無需 `npm install`。對安全性至關重要：供應鏈攻擊（Supply Chain Attack）風險為零

2. **Regex 陣列 + 閾值過濾** — 所有模式以物件陣列定義（`{ level, id, regex, reason }`），`SAFETY_LEVEL` 常數決定過濾閾值。新增規則只需在陣列加一行，不需修改邏輯

3. **結構化日誌（Structured Logging）** — 所有操作寫入 `~/.claude/hooks-logs/YYYY-MM-DD.jsonl`，每行一個 JSON 事件。可直接用 `jq` 查詢，與任何監控系統相容

4. **允許清單（ALLOWLIST）優先** — `protect-secrets.js` 先檢查允許清單（`.env.example`、`.env.template` 等）再做阻斷，避免誤擋合法的範例檔案

### 關鍵程式碼（Key Code Snippets）

**雙模組模式（核心架構）：**

```javascript
// 同時支援 CLI 執行與模組 import
if (require.main === module) {
  main();
} else {
  module.exports = { PATTERNS, LEVELS, SAFETY_LEVEL, checkCommand };
}
```

**安全等級閾值過濾：**

```javascript
const LEVELS = { critical: 1, high: 2, strict: 3 };

function checkCommand(cmd, safetyLevel = SAFETY_LEVEL) {
  const threshold = LEVELS[safetyLevel] || 2;
  for (const p of PATTERNS) {
    if (LEVELS[p.level] <= threshold && p.regex.test(cmd)) {
      return { blocked: true, pattern: p };
    }
  }
  return { blocked: false, pattern: null };
}
```

**stdin 非同步讀取（所有 hook 共用模式）：**

```javascript
async function main() {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  
  try {
    const data = JSON.parse(input);
    // ... 處理邏輯
    console.log('{}'); // 允許繼續
  } catch (e) {
    log({ level: 'ERROR', error: e.message });
    console.log('{}'); // 錯誤時寬鬆處理，不阻斷正常工作流
  }
}
```

**阻斷輸出格式：**

```javascript
console.log(JSON.stringify({
  hookSpecificOutput: {
    hookEventName: 'PreToolUse',
    permissionDecision: 'deny',
    permissionDecisionReason: `🚨 [${p.id}] ${p.reason}`
  }
}));
```

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | 每個 hook 獨立檔案，模式以資料陣列定義，新增規則零邏輯修改 |
| 可測試性（Testability） | ⭐⭐⭐⭐⭐ | 雙模組模式讓所有邏輯函式可直接 import 測試，262 個測試通過 |
| 安全性（Security） | ⭐⭐⭐⭐⭐ | 零外部依賴，無供應鏈攻擊風險；錯誤時寬鬆處理，不中斷正常工作流 |
| 文件品質（Documentation） | ⭐⭐⭐⭐ | 每個 hook 頂部有完整 JSDoc 說明設定方式，README 有詳細表格 |
| 可擴展性（Extensibility） | ⭐⭐⭐⭐ | 標準 stdin/stdout 協議，任何語言皆可實作新 hook |

> [!tip] 值得學習的設計
> **雙模組模式（Dual-Mode Module Pattern）**——同一個腳本既可以直接執行，也可以被 `require()` 引入做測試，是 Node.js CLI 工具的最佳實踐。配合 `node --test` 內建測試框架，無需 Jest 等外部工具。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> - **正規表示式（Regex）誤判風險** — 複雜的 Bash 指令（多行、HERE-DOC、複雜管道）可能繞過或誤觸 regex 模式。影響：高安全需求環境下可能有漏網之魚
> - **同步阻塞** — hook 是同步執行，若腳本崩潰或超時，Claude Code 會等待直到逾時。影響：`protect-secrets.js` 中的 `fs.appendFileSync` 理論上可能在磁碟滿時卡住
> - **無共享狀態（Shared State）機制** — 跨 hook 事件無法共享記憶體狀態，只能透過檔案或外部儲存傳遞資訊。影響：無法實作「同一 session 的 hook 計數」等需要跨事件狀態的功能
> - **Slack 為唯一通知渠道** — `notify-permission.js` 只支援 Slack，Discord/ntfy 在 roadmap 但未實作

### 🔮 改進建議（Improvement Suggestions）

1. **加入 AST 解析** — 對高風險 Bash 指令使用 AST 解析（如 `mvdan/sh`）取代純 regex，提升準確率
2. **hook 組合器（Composer）** — 提供設定驅動（Config-Driven）的多 hook 組合機制，減少 `settings.json` 的重複設定
3. **通知渠道抽象化** — 將 `sendSlack` 抽象為通知介面，讓使用者插入任意渠道（Discord、ntfy、email）

## 效能基準（Benchmark）

> [!info] 資料來源
> 效能數據來自作者部落格文章與 Node.js 特性分析，非官方 benchmark。

| Hook | 啟動語言 | 預估每次呼叫開銷 | 觸發頻率 |
|------|---------|--------------|---------|
| `block-dangerous-commands.js` | Node.js | ~50–100ms | 每次 Bash 工具呼叫 |
| `protect-secrets.js` | Node.js | ~50–100ms | 每次 Read/Edit/Write/Bash |
| `auto-stage.js` | Node.js | ~50–100ms + `git add` | 每次 Edit/Write |
| `event-logger.py` | Python | ~200–400ms | 偵錯用，不建議長期啟用 |

**注意**：`auto-stage.js` 包含 `execSync('git add ...')` 子程序呼叫，實際開銷略高，視 repo 大小而定。

## 快速上手（Quick Start）

```bash
# 1. Clone
git clone https://github.com/karanb192/claude-code-hooks ~/.claude/hooks-repo

# 2. 複製到 hooks 目錄
mkdir -p ~/.claude/hooks
cp ~/.claude/hooks-repo/hook-scripts/pre-tool-use/block-dangerous-commands.js ~/.claude/hooks/
cp ~/.claude/hooks-repo/hook-scripts/pre-tool-use/protect-secrets.js ~/.claude/hooks/
cp ~/.claude/hooks-repo/hook-scripts/post-tool-use/auto-stage.js ~/.claude/hooks/

# 3. 在 ~/.claude/settings.json 加入（最小推薦設定）
```

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/block-dangerous-commands.js" }]
      },
      {
        "matcher": "Read|Edit|Write|Bash",
        "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/protect-secrets.js" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/auto-stage.js" }]
      }
    ]
  }
}
```

```bash
# 4. 執行測試（在 clone 目錄）
cd ~/.claude/hooks-repo && npm test
```

## 我的心得（My Takeaways）

**雙模組模式**是最值得學習的設計：`if (require.main === module) { main() } else { module.exports = {...} }`。這讓同一個腳本既可以直接執行，也可以在測試中 `require()` 並直接呼叫純函式，完全避免測試時啟動子程序的開銷與複雜度。

**零依賴原則**在安全工具中尤為重要。這個 repo 完全不依賴 npm 套件，安裝只需複製三個檔案，沒有 lockfile 問題，沒有套件漏洞掃描需求。

**Regex 陣列 + 等級過濾**的模式也值得借鑑：把「規則清單」和「處理邏輯」完全分離，新增或修改規則不觸碰業務邏輯，只改資料陣列。

## 相關連結（Related）

- [[CLAUDE-CODE-HOOKS-GUIDE]] — Hooks 完整概念指南，13 個事件類型詳解
- [[CLAUDE-CODE-SKILLS]] — Claude Code Skill 系統，與 Hooks 互補的自動化機制
- [[AI-AGENT-SAFETY]] — AI 代理安全控制模式，含護欄（Guardrail）設計思路

## References

- [GitHub Repo](https://github.com/karanb192/claude-code-hooks)
- [官方 Claude Code Hooks 文件](https://code.claude.com/docs/en/hooks)
- [作者部落格文章（Hooks 介紹）](https://karanbansal.in/blog/claude-code-hooks/)
