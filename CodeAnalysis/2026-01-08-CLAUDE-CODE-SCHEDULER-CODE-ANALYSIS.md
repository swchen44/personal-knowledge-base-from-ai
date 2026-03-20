---
title: "claude-code-scheduler — Claude Code 跨平台定時任務排程系統深度分析"
date: 2026-01-08
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#ai/claude-code"
  - "#tools/cli"
  - "#productivity/workflows"
source: "https://github.com/jshchnz/claude-code-scheduler"
source_type: code
author: "jshchnz"
status: notes
links:
  - "[[CLAUDE-CODE-SETUP]]"
  - "[[AI-AGENT-DESIGN]]"
  - "[[CLAUDE-MEM-CODE-ANALYSIS]]"
github_stars: 485
github_language: TypeScript
---

## 摘要（Summary）

`claude-code-scheduler` 是一個 Claude Code 插件，讓使用者用自然語言（natural language）設定定時任務（scheduled tasks），底層對接作業系統的原生排程器（native schedulers）——macOS 用 launchd、Linux 用 crontab、Windows 用 Task Scheduler。排程到時後，插件自動執行 `claude -p "你的指令"`，讓 Claude 在無人值守的情況下完成程式碼審查、安全掃描、定時摘要等重複性工作。

這個插件正是本知識庫教程中 Nico 的投研 Agent 實現「每日定時財經日報」的技術核心，參見 [[BUILD-AGENT-WITH-CLAUDE-CODE-IN-20-MINUTES]]。

## Why — 為什麼存在？

- **核心動機**：Claude Code 本身只能在用戶主動對話時執行任務，無法在背景自動運行。使用者需要一個機制，讓 Claude 在固定時間自動完成重複性工作——無論用戶在不在電腦前
- **取代/改善什麼**：取代手動設定 crontab 或 launchd plist 的繁瑣操作；傳統定時任務只能跑腳本，此插件讓 Claude AI 作為執行者，能理解和處理自然語言的任務描述
- **目標用戶**：使用 Claude Code 進行日常開發的工程師；需要自動化重複性 AI 分析工作的使用者（每日 code review、週報、安全掃描）

## What — 是什麼？

- **主要功能**：
  - 自然語言轉 cron 表達式（"every weekday at 9am" → `0 9 * * 1-5`）
  - 支援一次性任務（one-time tasks，完成後自動刪除）與週期性任務（recurring tasks）
  - 三種執行模式：唯讀分析、自主執行（autonomous，`--dangerously-skip-permissions`）、Git Worktree 隔離執行
  - 跨平台：macOS（launchd）、Linux（crontab）、Windows（Task Scheduler）
  - Slash commands：`/scheduler:schedule-add`、`/scheduler:schedule-list` 等 6 個指令
  - 執行歷史（execution history）查看與日誌（log）記錄
- **不做什麼（Non-goals）**：不管理 Claude 的對話記憶（那是 claude-mem 的職責）；不提供 Web UI 或視覺化排程介面；不支援複雜的條件觸發（只有 cron 時間觸發）
- **技術棧（Tech Stack）**：TypeScript、Node.js 18+、croner（cron 解析）、cronstrue（cron 轉人類可讀字串）、zod（Schema 驗證）、execa（Shell 執行）、fs-extra、vitest（測試）

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌──────────────────────────────────────────────────────────────────┐
│                     Claude Code（使用者對話）                     │
│                                                                    │
│  自然語言："每個平日早上9點幫我做 code review"                    │
│        │                                                           │
│        ▼                                                           │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │            Scheduler Skill / Slash Commands              │     │
│  │  schedule-add / schedule-list / schedule-remove /        │     │
│  │  schedule-status / schedule-run / schedule-logs          │     │
│  └──────────────────────┬──────────────────────────────────┘     │
│                          │                                         │
│        ┌─────────────────┼────────────────────┐                  │
│        ▼                 ▼                     ▼                  │
│  ┌──────────┐    ┌──────────────┐   ┌──────────────────┐         │
│  │ CronParser│   │ScheduledTask │   │   VCS / Worktree │         │
│  │(croner+  │   │Config (JSON) │   │  (Git isolation) │         │
│  │cronstrue)│   │.claude/      │   └──────────────────┘         │
│  └──────────┘   │schedules.json│                                  │
└─────────────────┴──────┬───────┴───────────────────────────────  ┘
                          │ 寫入排程
                          ▼
         ┌────────────────────────────────────┐
         │      Platform Scheduler Layer       │
         │                                     │
         │  macOS ──► launchd (plist 檔案)    │
         │  Linux ──► crontab                  │
         │  Windows ► Task Scheduler           │
         └───────────────┬─────────────────────┘
                          │ 時間到時觸發
                          ▼
         ┌────────────────────────────────────┐
         │   claude -p "task command"          │
         │   [--dangerously-skip-permissions]  │
         │   [在 worktree 中執行]              │
         └───────────────┬─────────────────────┘
                          │ 輸出
                          ▼
         ~/.claude/logs/<task-id>.log
```

### 執行流程圖（Execution Flowchart）

```
 用戶下指令："每天 9am code review"
         │
         ▼
   [Scheduler Skill 觸發]
   自然語言解析 → cron expression
   "0 9 * * *"
         │
         ▼
   [詢問執行模式]
         │
         ├─ 唯讀分析 ──────────────────────────────────┐
         │   skipPermissions: false                     │
         │                                              │
         ├─ 自主執行 ─────────────────────────────┐   │
         │   skipPermissions: true                │   │
         │   (+dangerously-skip-permissions)      │   │
         │                                        │   │
         └─ Git Worktree 隔離執行 ──────────┐    │   │
             worktree.enabled: true         │    │   │
                                            ▼    ▼   ▼
                                    ┌──────────────────┐
                                    │ 寫入 schedules.json│
                                    └─────────┬────────┘
                                              │
                                              ▼
                                    [向 OS 排程器註冊]
                                    macOS: 寫 plist + launchctl load
                                    Linux: crontab -e 追加行
                                    Windows: schtasks /create
                                              │
                    ─────────────────────────►│ 時間到！
                                              ▼
                                    [claude -p "Review..."]
                                              │
                              ┌───────────────┼───────────────┐
                              │               │               │
                              ▼               ▼               ▼
                        唯讀模式       自主執行模式     Worktree 模式
                        輸出日誌       修改檔案         建立 branch
                                       輸出日誌         commit + push
                                                        清理 worktree
                                                        輸出日誌
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）：策略模式（Strategy Pattern）+ 平台抽象層
> `BaseScheduler` 抽象類別定義介面，`DarwinScheduler`、`LinuxScheduler`、`WindowsScheduler` 各自實作，運行時動態選擇對應平台的實作。這讓平台擴展只需新增一個 Scheduler 子類別，不影響其他程式碼。

1. **對接 OS 原生排程器而非自行實作 daemon**：直接用 launchd/crontab/Task Scheduler，這些系統服務在機器重啟後自動恢復，比自行維護 background process 更可靠
2. **Zod Schema 驗證**：所有設定（ScheduledTask、WorktreeConfig）都有 zod schema，確保 JSON 設定檔格式正確，錯誤在解析時即被捕捉
3. **Shell 注入防護（Shell Injection Prevention）**：`shellEscape()` 工具函式確保 Claude prompt 中的特殊字元被正確轉義，避免命令注入（command injection）風險
4. **One-time tasks 自動清除**：任務 ID 帶 `once.` 前綴標記為一次性，執行後自動從 schedules.json 刪除並從 OS 排程器取消登錄
5. **Git Worktree 隔離**：自主執行任務可在獨立 git worktree 中運行，變更提交到新分支（branch）並 push，避免直接汙染主分支（main branch）

### 資料流（Data Flow）

1. 用戶用自然語言描述排程需求 → Skill 解析為 cron expression + 執行設定
2. 生成 `ScheduledTask` JSON 物件，寫入 `.claude/schedules.json`（專案級）或 `~/.claude/schedules.json`（全域）
3. 呼叫對應平台的 Scheduler 實作（`DarwinScheduler.register(task)`），寫入 plist/crontab/schtasks
4. 時間到時，OS 排程器觸發：執行 `claude -p "task.execution.command"` 在 `task.execution.workingDirectory`
5. 輸出寫入 `~/.claude/logs/<task-id>.log`，執行記錄寫入 history

### 關鍵程式碼（Key Code Snippets）

**型別定義（src/types.ts）— ScheduledTask Schema：**

```typescript
export const ScheduledTaskSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  enabled: z.boolean().default(true),
  trigger: TriggerConfigSchema,  // 目前只有 CronTrigger
  execution: ExecutionConfigSchema,
  tags: z.array(z.string()).optional().default([]),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export const ExecutionConfigSchema = z.object({
  command: z.string().min(1),
  workingDirectory: z.string().optional().default('.'),
  timeout: z.number().positive().optional().default(300),
  env: z.record(z.string()).optional(),
  skipPermissions: z.boolean().optional().default(false),
  worktree: WorktreeConfigSchema.optional(),
});
```

**macOS launchd 排程器（src/schedulers/darwin.ts）核心：**

```typescript
async register(task: ScheduledTask): Promise<void> {
  await fs.ensureDir(this.launchAgentsDir);

  // 若啟用 worktree，先產生 shell script
  if (this.usesWorktree(task)) {
    const script = this.generateWorktreeScript(task, logDir);
    if (script) {
      const scriptPath = this.getWorktreeScriptPath(task.id);
      await fs.writeFile(scriptPath, script, { mode: 0o755 });
    }
  }

  const plistContent = this.generatePlist(task);
  const plistPath = this.getPlistPath(task.id);

  // 先 unload 舊的（若存在）
  try { await execa('launchctl', ['unload', plistPath]); } catch {}

  await fs.writeFile(plistPath, plistContent, 'utf-8');
  await execa('launchctl', ['load', plistPath]);
}
```

**Git Worktree 隔離執行（src/vcs/index.ts）：**

```typescript
export async function createWorktree(params: CreateWorktreeParams): Promise<WorktreeContext> {
  const name = generateWorktreeName(taskId);
  const branchName = `${branchPrefix}${name}`;  // e.g. "claude-task/task-abc12345-1234567890"
  const worktreePath = path.join(worktreeBase, name);

  await fs.ensureDir(worktreeBase);
  // 用 git worktree add 建立隔離環境
  await execa('git', ['worktree', 'add', worktreePath, '-b', branchName], {
    cwd: mainRepoPath,
  });

  return { mainRepoPath, worktreePath, branchName, createdAt: new Date() };
}
```

**JSON 設定範例（examples/daily-review.json）：**

```json
{
  "version": 1,
  "tasks": [{
    "id": "daily-code-review",
    "name": "Daily Code Review",
    "enabled": true,
    "trigger": {
      "type": "cron",
      "expression": "0 9 * * 1-5",
      "timezone": "local"
    },
    "execution": {
      "command": "Review all commits from yesterday...",
      "workingDirectory": ".",
      "timeout": 300
    },
    "tags": ["code-quality", "daily"]
  }]
}
```

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | 策略模式讓各平台實作完全獨立，BaseScheduler 定義清晰介面；TypeScript + zod 確保型別安全 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐ | 新增平台只需加一個 Scheduler 子類別；TriggerConfig 用 discriminatedUnion 預留 FileWatch、GitHook 擴展點 |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐ | 有 cron、history、types 的 vitest 測試；但 scheduler 平台實作的整合測試依賴 OS 環境，有 test-worktrees/ 目錄但測試較難自動化 |
| 文件品質（Documentation） | ⭐⭐⭐⭐ | README 詳細、有範例設定、SKILL.md 定義自然語言觸發場景；CRON_REFERENCE.md 和 PLATFORM_SETUP.md 提供額外說明 |
| 依賴管理（Dependency Management） | ⭐⭐⭐⭐⭐ | 依賴數量少且精準：croner、cronstrue、zod、execa、fs-extra，全部成熟穩定的套件，無重型框架 |

> [!tip] 值得學習的設計
> **Shell 注入防護**的處理方式：所有用戶輸入的 Claude prompt 都通過 `shellEscape()` 和 `sanitizeForComment()` 處理，再插入 plist/crontab 命令字串。這是 CLI 工具處理外部輸入的正確姿勢，值得在任何需要動態組裝 shell 命令的場景借鑒。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> - **問題一：需要 `claude` CLI 在 PATH 中**：若使用者的 PATH 設定不正確（常見於 launchd 環境中，PATH 比 interactive shell 少很多），任務會靜默失敗 — 影響：macOS launchd 特別容易遇到此問題，因 launchd 啟動時 PATH 與終端不同
> - **問題二：`--dangerously-skip-permissions` 的安全風險**：自主執行模式讓 Claude 可以執行任意指令，若 prompt 被惡意輸入（prompt injection）影響，後果難以預料 — 影響：生產環境謹慎使用，建議搭配 Git Worktree 隔離降低風險
> - **問題三：無 UI 管理介面**：所有管理操作都要在 Claude Code 對話中進行，不能直接編輯 schedules.json 然後即時生效（需重新 register） — 影響：偶爾需要手動修復設定時較不方便
> - **問題四：單機排程，無分散式保證**：任務直接在本機執行，機器關機或睡眠時任務不會執行（launchd 可設定 `RunAtLoad`，但錯過的排程不會補跑） — 影響：需要高可靠性的任務不適合用此方案

### 🔮 改進建議（Improvement Suggestions）

1. **PATH 問題的標準解法**：在 plist/shell script 中明確設定 PATH，或在安裝時偵測並記錄 `claude` 的完整路徑，寫死到排程命令中
2. **新增 FileWatch 觸發器**：已在 `TriggerConfig` 的 discriminatedUnion 中預留位置，實作「當 `src/` 有檔案變更時觸發 code review」會非常實用

## 效能基準（Benchmark）

> [!info] 資料來源
> 無公開 benchmark 數據。以下為定性分析。

| 面向 | 說明 |
|------|------|
| 排程精度 | 依賴 OS 原生排程器，通常在預定時間 ±1 秒內觸發 |
| 任務執行開銷 | 主要是 `claude -p` 的啟動時間（通常 1-3 秒）+ AI 推理時間 |
| Log 儲存 | 預設保留 30 天，超過 logRetentionDays 自動清理 |
| 最大並發 | 無內建並發限制，依 OS 排程器特性；多任務同時觸發時各自獨立執行 |

## 快速上手（Quick Start）

```bash
# 在 Claude Code 中安裝插件
/plugin marketplace add jshchnz/claude-code-scheduler
/plugin install scheduler@claude-code-scheduler

# 用自然語言建立排程（在 Claude Code 對話中）
# "每個平日早上9點幫我做 code review"
# Claude 會引導你完成設定

# 查看所有排程
/scheduler:schedule-list

# 查看執行歷史
/scheduler:schedule-logs

# 立即執行某個任務
/scheduler:schedule-run <task-id>

# 移除任務
/scheduler:schedule-remove <task-id>

# 範例：建立投研日報（對應 Nico 教程的使用場景）
# "每天早上8點，搜尋過去24小時的宏觀新聞和美股動態，整理成日報存到 daily-report.md"
# → Claude 詢問是否需要自主執行（需要，因為要寫入檔案）
# → 設定 skipPermissions: true
# → 排程建立完成
```

## 我的心得（My Takeaways）

- **OS 原生排程器是正確選擇**：不要自己實作 background daemon，launchd/crontab 的可靠性和重啟恢復能力遠超自製方案
- **策略模式（Strategy Pattern）的教科書應用**：`BaseScheduler` + 三個平台實作，是非常乾淨的跨平台 CLI 工具架構範本
- **Zod Schema 即是文件**：`ScheduledTaskSchema` 和 `ExecutionConfigSchema` 同時作為型別定義、執行時驗證和 API 文件，一份程式碼三用
- **Git Worktree 隔離是自主 AI 任務的安全底線**：讓 AI 在隔離分支做變更，人類 review PR 後才合入，這個模式值得在所有自主 AI 執行任務時採用
- 與 [[CLAUDE-MEM-CODE-ANALYSIS]] 配合使用：claude-mem 提供跨 session 記憶，claude-code-scheduler 提供定時觸發，兩者組合構成完整的自主 Agent 框架

## 相關連結（Related）

- [[CLAUDE-MEM-CODE-ANALYSIS]] — claude-mem 持久記憶系統，兩者常搭配使用構成完整 Agent
- [[CLAUDE-CODE-SETUP]] — Claude Code 安裝設定（含此插件安裝步驟）
- [[AI-AGENT-DESIGN]] — Agent 設計原則，定時任務是 Agent 自主化的核心能力之一

## References

- [GitHub Repo](https://github.com/jshchnz/claude-code-scheduler)
- [Plugin Marketplace](https://github.com/jshchnz/claude-code-scheduler)
