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
  - "[[2025-08-31-CLAUDE-MEM-CODE-ANALYSIS]]"
github_stars: 485
github_language: TypeScript
---

## 摘要（Summary）

`claude-code-scheduler` 是一個 Claude Code 插件，讓使用者用自然語言（natural language）設定定時任務（scheduled tasks），底層對接作業系統的原生排程器（native schedulers）——macOS 用 launchd、Linux 用 crontab、Windows 用 Task Scheduler。排程到時後，插件自動執行 `claude -p "你的指令"`，讓 Claude 在無人值守的情況下完成程式碼審查、安全掃描、定時摘要等重複性工作。

這個插件正是本知識庫教程中 Nico 的投研 Agent 實現「每日定時財經日報」的技術核心，參見 [[2026-03-16-BUILD-AGENT-WITH-CLAUDE-CODE-IN-20-MINUTES]]。

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
- 與 [[2025-08-31-CLAUDE-MEM-CODE-ANALYSIS]] 配合使用：claude-mem 提供跨 session 記憶，claude-code-scheduler 提供定時觸發，兩者組合構成完整的自主 Agent 框架

## 待補充（Open Questions）

- launchd 在 macOS 上的 PATH 問題是已知痛點，但文件提到的修復方案（記錄完整路徑）在 `nvm`、`fnm` 等版本管理工具頻繁更新的情況下是否足夠穩定？（建議搜尋：`launchd macOS PATH nvm fnm node version manager workaround`）
- `--dangerously-skip-permissions` 模式搭配 Git Worktree 隔離的安全性邊界在哪裡？若 Claude 在 Worktree 中意外修改了共用的 `.env` 或 git config，有無防護機制？（建議搜尋：`claude code skip permissions security git worktree isolation`）
- 這個插件依賴 `claude -p` 的非互動模式（print mode），這個模式的 API 費用計算方式與互動模式是否相同？排程任務累積下來的月費成本如何估算？（建議搜尋：`claude code print mode API cost billing non-interactive`）
- Windows Task Scheduler 的排程精度和行為與 macOS launchd 有哪些實質差異？特別是電腦睡眠後的補跑（missed run）行為，跨平台使用者應如何設定？（建議搜尋：`Windows Task Scheduler vs launchd crontab missed job behavior`）
- 若同一個 Git Worktree 中有多個定時任務同時觸發，任務之間是否會有衝突？插件是否有並發執行保護機制？（建議搜尋：`claude code scheduler concurrent tasks git worktree conflict`）

## 相關連結（Related）

- [[2025-08-31-CLAUDE-MEM-CODE-ANALYSIS]] — claude-mem 持久記憶系統，兩者常搭配使用構成完整 Agent
- [[CLAUDE-CODE-SETUP]] — Claude Code 安裝設定（含此插件安裝步驟）
- [[AI-AGENT-DESIGN]] — Agent 設計原則，定時任務是 Agent 自主化的核心能力之一

## References

- [GitHub Repo](https://github.com/jshchnz/claude-code-scheduler)
- [Plugin Marketplace](https://github.com/jshchnz/claude-code-scheduler)

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 三種執行模式（唯讀 / 自主執行 / Git Worktree 隔離）；策略模式（Strategy Pattern）的 BaseScheduler 抽象；Zod Schema 驗證；croner + cronstrue 函式庫；macOS launchd / Linux crontab / Windows Task Scheduler；shellEscape() 注入防護；6 個 Slash commands；485 顆 GitHub Stars |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | claude-code-scheduler 的核心設計選擇是「委託作業系統原生排程器管理任務生命週期，而非自行實作 daemon」。這讓框架本身極度輕量（只負責翻譯自然語言為 cron 表達式並寫入設定），而系統重啟恢復、睡眠喚醒等複雜場景由 launchd/crontab 原生處理。自然語言 → cron 的轉換橋接了人類描述與系統執行之間的語義鴻溝。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | ①「OS 排程器比自製 daemon 更可靠」成立的前提是 PATH 設定正確，但 launchd 啟動時的 PATH 與 interactive shell 不同，此假設在 macOS nvm/fnm 環境中頻繁失敗；②`--dangerously-skip-permissions` 假設「用戶信任自己設定的 prompt」，但 prompt injection 威脅模型未被分析；③Git Worktree 隔離假設 main branch 的 .env 和 git config 在 worktree 中不可存取，此假設需要驗證 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | ①設定每日 9am 的程式碼審查排程，用唯讀模式確保安全；②設定每週報告生成任務，搭配 Git Worktree 隔離讓 Claude 自主生成並 commit 到新分支，人工 review PR 後合入；③參考此插件的策略模式架構，在自己的跨平台 CLI 工具中實作平台抽象層 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | claude-code-scheduler 在「單機定時任務」場景下是最輕量的選擇（無 daemon、無資料庫、無伺服器）；但在需要高可靠性（機器關機時任務不執行）或跨機器協調的場景下完全不適用。與 GNAP 的 heartbeat 模式相比，scheduler 更適合「固定時間觸發」，GNAP 更適合「事件驅動協調」。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：`DarwinScheduler.register()` 在寫入 plist 前先執行 `launchctl unload`，若 plist 從未被 load 過，unload 會失敗但被 `try/catch` 吞掉。這個設計是否可能遮蔽真正的排程器問題？
- **假設**：插件假設使用者的 `claude` CLI 在 launchd 啟動環境中可用，但 launchd 的 PATH 遠比 interactive shell 少。在不同的版本管理工具（nvm、fnm、mise）下，這個假設的成立率有多高？
- **證據**：自然語言轉 cron 表達式的準確率沒有公開測試數據。「每個工作日早上 9 點」轉換成 `0 9 * * 1-5` 是正確的，但「每季度最後一個工作日下午 3 點」是否能被正確解析？
- **觀點**：從 DevOps 角度，「任務狀態存在 JSON 檔案」的設計在多人協作環境中缺乏版本控制語義。若兩個工程師在同一台機器上管理 schedules.json，是否會產生 git merge conflict？
- **後果**：若 `--dangerously-skip-permissions` 的自主執行任務被 prompt injection 影響（例如任務描述中包含惡意指令），Claude 在 worktree 中可以執行任意 shell 指令，後果如何估計？

### 方案批判三問（Critical Evaluation）

> [!warning] 適用於技術方案類內容

1. **最大的風險是什麼？** — `--dangerously-skip-permissions` 與 OS 排程器的組合創造了一個「無人值守的自主 AI 執行環境」。若排程任務的 prompt 被間接修改（例如 task description 從外部來源讀取），Claude 能在無任何人工確認的情況下執行任意系統命令，包括刪除檔案、推送程式碼、發送請求到外部服務。這個風險在文件中被嚴重低估。
2. **什麼情況下會失敗？** — ①macOS 系統更新重設 launchd PATH，導致所有排程任務靜默失敗，使用者在數天後才發現；②Claude Code CLI 版本更新後指令介面改變，`claude -p "..."` 的 print mode 格式不相容，所有任務以非零錯誤碼退出但無警報機制；③機器睡眠或關機期間觸發的任務不會補跑，使用者誤以為任務已執行但日誌為空
3. **有沒有更好的替代方案？** — ①若需要更高可靠性：改用雲端排程服務（AWS EventBridge、GitHub Actions scheduled workflow）搭配 `claude -p` 的 API 呼叫；②若需要更安全的自主執行：在 Docker 容器中以受限權限執行 Claude，而非使用 `--dangerously-skip-permissions`；③若排程需求簡單：直接用 crontab 手動設定，避免插件引入的 PATH 和版本相容性複雜度
