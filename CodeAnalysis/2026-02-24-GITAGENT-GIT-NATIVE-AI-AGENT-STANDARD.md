---
title: "gitagent — Git 原生 AI 代理人框架無關標準深度分析"
date: 2026-02-24
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#typescript"
  - "#ai/agent"
  - "#tools/cli"
  - "#ai/framework"
source: "https://github.com/open-gitagent/gitagent"
source_type: code
author: "open-gitagent / shreyaskapale"
status: notes
links:
  - "[[CLAUDE-MEMORY-ENGINE]]"
  - "[[AI-AGENT-PATTERNS]]"
  - "[[COMPLIANCE-AI-FINRA]]"
github_stars: 570
github_language: TypeScript
---

## 摘要（Summary）

gitagent 是一個框架無關（Framework-agnostic）的 Git 原生（git-native）AI 代理人定義標準。核心主張是：**你的 Git Repository 就是你的 Agent**。Clone 一個 repo 即可取得一個可攜帶、可版本控制、可跨框架運行的 AI 代理人定義。

目前有 570 顆星（2026-03-19），第一個公開版本 v0.1.7 發布於 2026-02-24。以 TypeScript 實作 CLI 工具，提供 `init`、`validate`、`export`、`run`、`audit` 等指令，支援匯出至 Claude Code、OpenAI、CrewAI、Lyzr 等多種框架。

---

## Why — 為什麼存在？

> 這個專案要解決的根本問題是什麼？現有方案的哪些痛點促使它被創造？

- **核心動機**：每個 AI 框架（LangChain、CrewAI、OpenAI Agents SDK、Claude Code）都有自己的結構和設定格式，導致代理人定義無法跨框架移植。沒有一個通用的、可攜帶的標準。
- **取代/改善什麼**：取代各框架各自為政的設定檔（Jinja2 模板、Python 類別、YAML config），改以 Git repository 作為代理人的唯一真實來源（Single Source of Truth）。
- **目標用戶**：
  - AI 應用開發者（想要跨框架移植代理人）
  - 金融業合規（Compliance）團隊（需要 FINRA、SEC、Federal Reserve 法規遵從）
  - DevOps 工程師（想把代理人當程式碼管理：版本控制、CI/CD、分支策略）

---

## What — 是什麼？

> 這個專案的功能邊界與核心能力。

- **主要功能**：
  - 定義 Git 原生代理人標準（`agent.yaml` + `SOUL.md` 最小化必要檔案）
  - CLI 工具：`init`（建立）、`validate`（驗證）、`export`（匯出）、`run`（執行）、`audit`（合規審計）
  - 多框架轉接器（Adapter）：system-prompt、claude-code、openai、crewai、lyzr、github、openclaw、nanobot
  - 法規合規（Regulatory Compliance）一等公民支援：FINRA、Federal Reserve、SEC、CFPB
  - 職責分離（Segregation of Duties）機制：角色（role）、衝突矩陣（conflict matrix）、強制執行（enforcement）
- **不做什麼（Non-goals）**：
  - 不替代運行時框架的狀態機、圖接線（graph wiring）等實際執行邏輯
  - 不實作 LLM API 呼叫本身
  - 不管理 embedding 或向量資料庫
- **技術棧（Tech Stack）**：TypeScript、Node.js ≥18、Commander.js（CLI 框架）、AJV（JSON Schema 驗證）、js-yaml（YAML 解析）

---

## How — 如何運作？

> [!important] 以下包含三種 ASCII 圖表，讓你不看程式碼也能快速掌握全貌。

### 系統架構圖（System Architecture）

```
┌──────────────────────────────────────────────────────────────────┐
│                        Git Repository                            │
│                                                                  │
│  ┌────────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  agent.yaml    │  │ SOUL.md  │  │ RULES.md │  │DUTIES.md │  │
│  │ (唯一嚴格Schema)│  │(身份/人格)│  │(硬性約束)│  │(職責分離)│  │
│  └────────────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                                  │
│  skills/    tools/    knowledge/    memory/    compliance/       │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   gitagent CLI    │
                    │  (TypeScript)     │
                    └─────────┬─────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   ┌──────▼──────┐    ┌───────▼──────┐   ┌───────▼──────┐
   │  Adapters   │    │  Validators  │   │   Runners    │
   │ ─────────── │    │ ──────────── │   │ ──────────── │
   │ system-     │    │ agent.yaml   │   │ claude       │
   │ prompt      │    │ schema (AJV) │   │ openai       │
   │ claude-code │    │ SOUL.md      │   │ crewai       │
   │ openai      │    │ skills/      │   │ lyzr         │
   │ crewai      │    │ hooks/       │   │ nanobot      │
   │ lyzr        │    │ tools/       │   │ git          │
   │ github      │    │ compliance   │   └──────────────┘
   │ openclaw    │    └──────────────┘
   └─────────────┘
```

### 執行流程圖（Execution Flowchart）：`gitagent export`

```
 gitagent export --format claude-code
          │
          ▼
   [resolve agent dir]
          │
          ▼
   [loadAgentManifest()]  ─── 失敗 ──► [Error: agent.yaml not found]
   讀取並解析 agent.yaml                          │
          │成功                                   ▼
          ▼                               [process.exit(1)]
   [讀取 SOUL.md / RULES.md / AGENTS.md]
          │
          ▼
   [根據 --format 選擇 Adapter]
          │
          ├─ system-prompt ──► [拼接所有 .md 為純文字 system prompt]
          │
          ├─ claude-code   ──► [生成 CLAUDE.md 相容格式]
          │
          ├─ openai        ──► [生成 Python OpenAI Agents SDK 程式碼]
          │
          ├─ crewai        ──► [生成 CrewAI YAML 設定]
          │
          └─ lyzr / github / openclaw / nanobot ...
                    │
                    ▼
           [--output 指定路徑？]
                    │
          ┌─────────┴──────────┐
          │ 是                  │ 否
          ▼                    ▼
   [writeFileSync()]    [console.log()]
          │
          ▼
   [success 訊息]
```

### 時序圖（Sequence Diagram）：`gitagent validate --compliance`

```
  使用者       CLI          Validator        AJV          Filesystem
    │           │                │             │               │
    │─run cmd──►│                │             │               │
    │           │──loadManifest()►             │               │
    │           │                │─read agent.yaml────────────►│
    │           │                │◄──yaml content──────────────│
    │           │◄──manifest─────│             │               │
    │           │                │             │               │
    │           │──validateAgentYaml()─────────►               │
    │           │                │◄──valid/errors──────────────│
    │           │                │             │               │
    │           │──validateSoulMd()──────────────────────────►│
    │           │                │◄──exists/content────────────│
    │           │                │             │               │
    │           │──validateCompliance()        │               │
    │           │  检查 FINRA 3110             │               │
    │           │  检查 SR 11-7 (Fed Reserve)  │               │
    │           │  检查 SOD 衝突矩陣           │               │
    │           │◄──errors / warnings──────────│               │
    │           │                │             │               │
    │◄──summary─│                │             │               │
  (pass/fail + error/warning counts)
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> gitagent 採用的是**開放標準模式（Open Standard Pattern）**：先定義規格（`spec/SPECIFICATION.md`）、再提供參考實作（CLI），允許任何人自由實作轉接器。類似 OpenAPI Spec 對 REST API 的角色。

1. **只有 `agent.yaml` 有嚴格 Schema**：其他所有檔案（`SOUL.md`、`RULES.md`）只有建議結構，不強制格式——降低上手門檻，同時保持核心驗證嚴謹性。
2. **Adapter 與 Runner 分離**：`export` 指令用 Adapter 將代理人定義轉成目標格式；`run` 指令在 Adapter 基礎上再呼叫 Runner 執行——關注點分離（Separation of Concerns）清晰。
3. **AJV 做 JSON Schema 驗證**：`validate` 命令載入 `spec/schemas/` 下的 JSON Schema，用 AJV 驗證所有 YAML 設定檔——驗證邏輯與業務邏輯完全分離。
4. **職責分離（SOD）嵌入框架本身**：不只是文件，而是在 `agent.yaml` 的 `compliance.segregation_of_duties` 區塊定義角色衝突，然後在 `validate --compliance` 時**程式化執行**衝突檢查——把合規需求變成可測試的程式碼。

### 資料流（Data Flow）：Adapter 匯出流程

1. `loadAgentManifest(dir)` — 讀取並解析 `agent.yaml` 為 `AgentManifest` TypeScript 介面
2. 各 Adapter 讀取對應 `.md` 文件（`SOUL.md`、`RULES.md`、`DUTIES.md`、`AGENTS.md`）
3. 按目標格式拼接/生成輸出字串（system prompt、Python 程式碼、YAML 設定）
4. 寫入指定檔案路徑或直接輸出至 stdout

### 關鍵程式碼（Key Code Snippets）

**AJV Schema 驗證核心（src/commands/validate.ts）**：

```typescript
function validateSchema(data: unknown, schemaName: string): { valid: boolean; errors: string[] } {
  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);
  const schema = loadSchema(schemaName) as Record<string, unknown>;
  // Remove $schema and $id that Ajv doesn't handle by default
  delete schema['$schema'];
  delete schema['$id'];
  const validate = ajv.compile(schema);
  const valid = validate(data);
  const errors = validate.errors?.map((e: any) => {
    const path = e.instancePath || '/';
    return `${path}: ${e.message}`;
  }) ?? [];
  return { valid: valid === true, errors };
}
```

**職責分離衝突檢查（src/commands/validate.ts）**：

```typescript
// Core SOD check: no agent holds conflicting roles
if (sod.conflicts) {
  for (const [roleA, roleB] of sod.conflicts) {
    if (assignedRoles.includes(roleA) && assignedRoles.includes(roleB)) {
      const msg = `[SOD] Agent "${agentName}" holds conflicting roles: "${roleA}" and "${roleB}"`;
      if (sod.enforcement === 'advisory') {
        result.warnings.push(msg);
      } else {
        result.valid = false;
        result.errors.push(msg);
      }
    }
  }
}
```

**SkillsFlow YAML 工作流定義（README 範例）**：

```yaml
name: code-review-flow
description: Full code review pipeline
triggers:
  - pull_request

steps:
  lint:
    skill: static-analysis
    inputs:
      path: ${{ trigger.changed_files }}

  review:
    agent: code-reviewer
    depends_on: [lint]
    prompt: |
      Focus on security and performance.
      Flag any use of eval() or raw SQL.
    inputs:
      findings: ${{ steps.lint.outputs.issues }}

  test:
    tool: bash
    depends_on: [lint]
    inputs:
      command: "npm test -- --coverage"

  report:
    skill: review-summary
    depends_on: [review, test]
    conditions:
      - ${{ steps.review.outputs.severity != 'none' }}
    inputs:
      review: ${{ steps.review.outputs.comments }}
      coverage: ${{ steps.test.outputs.report }}

error_handling:
  on_failure: notify
  channel: "#eng-reviews"
```

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可移植性（Portability） | ⭐⭐⭐⭐⭐ | 同一份代理人定義可匯出為 9 種框架格式，是最大亮點 |
| 可維護性（Maintainability） | ⭐⭐⭐⭐ | Adapter / Runner / Validator 關注點分離清晰 |
| 合規設計（Compliance Design） | ⭐⭐⭐⭐⭐ | 把 FINRA、SOD 等法規需求轉為可驗證的程式碼，業界罕見 |
| 文件品質（Documentation） | ⭐⭐⭐⭐⭐ | README 詳盡含 12 種架構模式圖，SPECIFICATION.md 完整 |
| 版本控制整合（VCS Integration） | ⭐⭐⭐⭐⭐ | git diff/blame/branch 直接用於代理人版本管理，概念一致 |
| 測試覆蓋（Test Coverage） | ⭐⭐ | 核心驗證邏輯有測試，但範圍有限 |

> [!tip] 值得學習的設計
> **把法規合規（Regulatory Compliance）程式化**是 gitagent 最值得借鑑的設計。將 FINRA Rule 3110 的監督要求轉成 `if (c.risk_tier === 'high' && !c.supervision?.human_in_the_loop)` 的可測試條件——合規不再只是文件，而是 CI/CD 流水線的一部分。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> 以下是架構層面的問題或技術債（Technical Debt）。

- **問題一：Runtime 執行能力薄弱** — 目前 `run` 命令主要依賴外部框架（Claude API、OpenAI API 等）實際執行，gitagent 本身無法獨立完成完整對話流程。影響：宣稱「clone repo 即可得到代理人」在實際執行上仍需額外設定。
- **問題二：spec_version 只有 0.1.0** — 規格才剛開始，`agent.yaml` schema 在未來可能大幅變動，現有代理人定義可能需要遷移。影響：早期採用者的技術債（Technical Debt）風險。
- **問題三：github.ts 未整合至 adapters/index.ts** — `src/adapters/github.ts` 未包含在主要 export 清單中，顯示部分功能尚未完全整合。影響：`--format github` 可能存在潛在 bug。
- **問題四：記憶體系統（memory/）純靠慣例** — `memory/` 資料夾只是 Markdown 檔案的約定，沒有向量資料庫（vector database）或語義搜尋（semantic search）整合。影響：長期記憶的可靠性完全取決於框架實作。

### 🔮 改進建議（Improvement Suggestions）

1. **增加 Runtime 執行能力**：提供至少一個內建的 LLM 呼叫實作，讓使用者不需要外部框架也能跑起來。
2. **引入語義版本鎖定（Semver Pinning）**：為 `spec_version` 加入嚴格的向後相容（backward compatibility）承諾，避免規格升級破壞現有代理人定義。
3. **記憶體語義搜尋整合**：在 `memory/` 系統加入可選的向量索引（vector index）支援，讓代理人能做語義查詢而非只靠全文載入。
4. **完成 GitHub Actions 轉接器**：將 `github.ts` 整合進標準匯出流程，並補充對應測試。

---

## 效能基準（Benchmark）

> [!info] 資料來源
> gitagent 目前無公開效能基準測試數據。以下為定性分析。

| 場景 | gitagent | 傳統框架設定 | 手動撰寫 |
|------|----------|-------------|---------|
| 建立新代理人 | `gitagent init`（秒） | 各框架不同（分鐘~小時） | 無輔助（小時） |
| 跨框架移植 | `gitagent export --format X`（秒） | 需手動重寫（小時~天） | 幾乎不可行 |
| 合規驗證 | `gitagent validate --compliance`（秒） | 無內建支援 | 人工審查（天） |

**效能特性**：CLI 工具本身是純本地操作（讀 YAML、生成文字），執行速度極快，無網路延遲。`gitagent run` 的效能瓶頸在外部 LLM API 呼叫，與 gitagent 本身無關。

---

## 快速上手（Quick Start）

```bash
# 安裝
npm install -g gitagent

# 建立標準代理人（standard 模板）
gitagent init --template standard

# 驗證（含合規檢查）
gitagent validate --compliance

# 匯出為 Claude Code 格式
gitagent export --format claude-code

# 匯出為通用 system prompt
gitagent export --format system-prompt

# 執行代理人（使用 Claude）
gitagent run --dir ./my-agent --adapter claude --prompt "Hello"

# 直接從 GitHub repo 執行
gitagent run --repo https://github.com/example/my-agent --adapter claude
```

**最小可執行代理人（2 個檔案）**：

```yaml
# agent.yaml
spec_version: "0.1.0"
name: my-agent
version: 0.1.0
description: A helpful assistant agent
```

```markdown
# SOUL.md
You are a helpful, honest, and harmless assistant.
You communicate clearly and concisely.
```

---

## 我的心得（My Takeaways）

gitagent 最讓我眼睛一亮的是**把「合規」變成「測試」**的思路。傳統上，FINRA Rule 3110 是一份 PDF 文件，現在它變成了 `validate --compliance` 的一個 if 判斷式。這個模式——把人類可讀的規範（specification）轉化成機器可執行的驗證（validation）——完全可以應用到任何需要規範遵從的場景。

另一個值得借鑑的是**開放標準（Open Standard）策略**：先定義規格（spec），再提供參考實作（CLI），讓社群可以自由開發轉接器。這讓 gitagent 的生態系能以低門檻快速擴張。

對於自己的專案，我會考慮採用 `agent.yaml` + `SOUL.md` 的最小化模式來管理 AI 代理人，並將 `gitagent validate` 加入 CI/CD 流水線。

---

## 相關連結（Related）

- [[CLAUDE-MEMORY-ENGINE]] — Claude Code 的記憶系統設計與 gitagent 的 `memory/` 資料夾概念高度重疊
- [[AI-AGENT-PATTERNS]] — gitagent 定義的 12 種架構模式（Human-in-the-Loop、Agent Forking 等）
- [[COMPLIANCE-AI-FINRA]] — gitagent 的 FINRA/Federal Reserve 合規支援詳細說明

---

## References

- [GitHub Repo](https://github.com/open-gitagent/gitagent)
- [官方網站 gitagent.sh](https://gitagent.sh)
- [規格文件 SPECIFICATION.md](https://github.com/open-gitagent/gitagent/blob/main/spec/SPECIFICATION.md)
- [npm @shreyaskapale/gitagent](https://www.npmjs.com/package/@shreyaskapale/gitagent)
