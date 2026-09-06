---
title: "Claude Code Skill 觸發權限矩陣：自動組合、User Only 與 Human Approval Gate"
date: 2026-09-06
date_uncertain: true
category: AI
tags:
  - ai/claude-code
  - ai/skill-design
  - ai/agent-architecture
  - ai/human-in-the-loop
  - tools/permissions
source: "https://code.claude.com/docs/en/skills"
source_type: article
author: "Anthropic；GitHub community reports；AI 討論整理"
status: notes
links:
  - "[[2026-04-29-CLAUDE-CODE-DISABLE-MODEL-INVOCATION-SKILL-VISIBILITY-SOURCE-ANALYSIS]]"
  - "[[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]]"
  - "[[2026-03-31-AI-WORKFLOW-AGENTS-SKILLS-STANDARDS]]"
---

## 摘要（Summary）

Claude Code 的 Skill 權限同時取決於「誰觸發」與「已啟動後可使用哪些工具」。`user-invocable` 控制使用者能否用 `/skill` 手動啟動；`disable-model-invocation` 阻止 Claude 透過 `Skill` tool 自動或程式化載入。這形成一般流程可雙方觸發、背景知識只給模型、部署與發布等副作用操作只給使用者的 2×2 矩陣。

Workflow A 執行時若叫用 Skill B，真正觸發 B 的是 Claude 的 `Skill(B)`，不是使用者。因此 B 設為 `disable-model-invocation: true` 時，A→B 會被阻擋。若 B 是自動流程依賴，應允許模型呼叫；若 B 是特權操作，A 應在準備完成後停止，要求人類輸入 `/B` 作為批准閘門（Human Approval Gate）。

本篇以 2026-09-06 查閱的官方文件和 GitHub bug reports 為基礎。規格模型與版本相依的 issue 必須分開看：issue 是重現與回歸風險，不是跨版本保證。

## 關鍵洞察（Key Insights）

- **真正的呼叫者決定權限**：A 的文字要求「使用 B」不會把 Claude→`Skill(B)` 變成使用者觸發。
- **組合性與 User Only 互斥**：A 必須自動執行 B 時，B 不可禁止模型呼叫；要由人類批准 B 時，A 必須停止而非自行跨越 B。
- **`skillOverrides` 適合集中治理**：不修改共享 `SKILL.md` 也能把 Skill 設為 `user-invocable-only` 或 `off`。
- **`allowed-tools` 是第二條軸**：它限制已啟動 Skill 的能力，不能取代觸發權限控制。

> [!important] 規格與實作狀態分離
> 官方文件定義意圖與目前設定模型。GitHub issue 涵蓋特定版本、plugin reload 或 subagent 路徑的實際問題；上線前應在團隊使用的版本驗證。

## 詳細內容（Details）

### 觸發權限 2×2 矩陣

| `user-invocable` | `disable-model-invocation` | 使用者 `/skill` | Claude／`Skill` tool | 適合內容 |
|---|---|---:|---:|---|
| `true`（預設） | `false`（預設） | ✅ | ✅ | 可組合 Workflow、測試、審查 |
| `false` | `false` | ❌ | ✅ | 架構說明、編碼規範、背景上下文 |
| `true` | `true` | ✅ | ❌ | 部署、發布、寄送、合併 |
| `false` | `true` | ❌ | ❌ | 幾乎等同停用 |

```text
                         Claude 自動／程式化觸發
                         可                    不可
                    ┌──────────────────┬───────────────────┐
使用者可手動觸發    │ Both             │ User Only         │
                    │ workflow / test  │ deploy / publish  │
                    ├──────────────────┼───────────────────┤
使用者不可手動觸發  │ Claude Only      │ Disabled-ish      │
                    │ context / policy │ 避免使用          │
                    └──────────────────┴───────────────────┘
```

### A→B：為何「A 說要用 B」仍會被擋

假設 B 被設為 User Only：

```yaml
---
name: deploy
description: Deploy application
disable-model-invocation: true
---
```

A 的內容要求使用 B：

```markdown
---
name: release
description: Release workflow
---

# Release

1. Run tests
2. Build artifacts
3. Use the deploy skill
4. Verify deployment
```

使用者輸入：

```text
/release
```

```text
User
 │
 ▼
Skill A: release
 │
 │ "Use deploy skill"
 ▼
Claude
 │
 │ Skill(deploy)
 ▼
❌ BLOCKED

Skill B:
disable-model-invocation: true
```

預期的拒絕訊息：

```text
Error:
Skill cc-use-subagents cannot be used with Skill tool
due to disable-model-invocation
```

這和 [[2026-04-29-CLAUDE-CODE-DISABLE-MODEL-INVOCATION-SKILL-VISIBILITY-SOURCE-ANALYSIS|既有原始碼分析]]中的模型可見性過濾與 `Skill` tool 驗證雙重防線相符。

### 兩種正確的工作流設計

**B 是可組合 Workflow：** A 需要自動執行 B 時，B 必須允許模型呼叫。

```yaml
---
name: B
description: ...
disable-model-invocation: false
---
```

省略欄位也相同，因為預設是 `false`。

```text
Skill A
 ├─ Step 1
 ├─ Step 2
 ├─ Skill(B)   ← Claude 必須有權 invoke
 └─ Step 4
```

**B 是特權操作（Privileged Action）：** A 完成低風險工作後停止，要求人類明確批准。

```text
Skill A
 ├─ build
 ├─ test
 ├─ package
 └─ STOP
       │
       ▼
"Ready to deploy. Run /deploy-production to continue."
       │
       ▼
Human ── /deploy-production ──► Skill B ──► Execute
```

這讓 Skill 層本身成為 Human Approval Gate，可與 [[2026-03-31-AI-WORKFLOW-AGENTS-SKILLS-STANDARDS|Agents／Skills／Standards 三層架構]]的治理邊界搭配。

### 三類 Skill 的權限分類

| 類型 | 範例 | 模型可呼叫 | 使用者可呼叫 | 建議設定 |
|---|---|---:|---:|---|
| Knowledge | architecture、coding-standard | ✅ | 不重要 | `user-invocable: false` |
| Composable Workflow | test、review、bug-analysis | ✅ | ✅ | 預設 |
| Privileged Action | deploy、publish、merge | ❌ | ✅ | `disable-model-invocation: true` |

```text
                 Skill A
                    │
       ┌────────────┴────────────┐
       ▼                         ▼
 Knowledge B                Workflow C
       │ AUTO                    │ AUTO
       └────────────┬────────────┘
                    ▼
          Privileged Skill D
                    │
             MODEL BLOCKED ✕
                    │
             Human: /skill-D
                    ▼
                 Execute
```

### `skillOverrides`：設定檔的集中覆寫

```json
{
  "skillOverrides": {
    "B": "user-invocable-only"
  }
}
```

| 值 | Claude 看到 | `/` 選單 | 意義 |
|---|---:|---:|---|
| `"on"` | 名稱與描述 | ✅ | 正常啟用 |
| `"name-only"` | 只有名稱 | ✅ | 降低常駐上下文成本 |
| `"user-invocable-only"` | ❌ | ✅ | User Only |
| `"off"` | ❌ | ❌ | 完全關閉 |

> [!note] 覆寫層級
> 若 A 必須自動執行 B，就不要把 B 覆寫成 `user-invocable-only`。這會把 A 的依賴改成必須由人類接手的關卡。

### `user-invocable: false` 與 `allowed-tools`

```yaml
---
name: legacy-system-context
description: Explain legacy system architecture.
user-invocable: false
---
```

這類 Skill 不出現在使用者的 `/` 選單，但 Claude 仍可在相關情境載入。它適合 `coding-guidelines`、`architecture-context`、`legacy-system-context`、`security-rules` 和 `team-conventions`。

```yaml
---
name: deploy
description: Deploy application to production.
disable-model-invocation: true
---
```

```yaml
---
name: code-review
description: Review code without modifying files.
allowed-tools:
  - Read
  - Grep
  - Glob
---
```

```text
SKILL.md
├─ Invocation Control
│  ├─ user-invocable
│  └─ disable-model-invocation
├─ Visibility Override
│  └─ settings.json → skillOverrides
└─ Capability Control
   └─ allowed-tools
```

`allowed-tools` 限制已啟動 Skill 的能力；前兩者限制誰可啟動。兩者應一起設計。更多 frontmatter 與架構取捨請參見 [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION|官方文件筆記]]與 [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON|機制比較筆記]]。

### 版本相依的已知問題與驗證

GitHub issue [#43809](https://github.com/anthropics/claude-code/issues/43809) 回報：parent agent 即使明確提及一個 `disable-model-invocation: true` 的 Skill，subagent 仍可能因經由 `Skill` tool 載入而被拒絕。另有 [#32817](https://github.com/anthropics/claude-code/issues/32817)、[#59363](https://github.com/anthropics/claude-code/issues/59363) 和 [#87536](https://github.com/anthropics/claude-code/issues/87536) 等回報，涵蓋 slash command 被阻擋、slash command 載入後重複呼叫 `Skill` tool，與可見性回歸。

> [!warning] 上線前測試
> 對每個 User Only Skill，在團隊實際使用的 Claude Code 版本驗證三條路徑：`/B`、A→B、parent agent→subagent→B。記錄版本、安裝／reload 狀態與最小重現案例。

## 我的心得（My Takeaways）

1. 先問 B 是「自動依賴」還是「批准閘門」，就能直接決定是否允許模型呼叫。
2. 部署前的 build、test、package 可自動化；部署本身由 `/deploy-production` 接住人類批准，能同時降低誤觸發與保留流程效率。
3. 不應把所有 Skill 視為同一種 prompt。Knowledge、Workflow 和 Privileged Action 需要不同權限模型。

## 待補充（Open Questions）

- 目前團隊使用的 Claude Code 版本，對 `/B`、A→B、subagent→B 三條路徑各自結果為何？建議搜尋：`Claude Code disable-model-invocation version regression`。
- `skillOverrides` 與 frontmatter 衝突時，特定版本的優先順序與錯誤訊息為何？建議搜尋：`Claude Code skillOverrides precedence frontmatter`。
- `user-invocable-only` 能否表達 A 明確委派後僅允許一次 B 的暫時授權？建議搜尋：`Claude Code delegated skill authorization`。
- 哪些資料應顯示在 deploy 批准訊息，才能讓批准可稽核（auditable）？建議搜尋：`human approval gate deployment audit trail`。
- `allowed-tools` 與專案權限規則衝突時，最小權限（least privilege）結果如何驗證？建議搜尋：`Claude Code allowed-tools permissions precedence`。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---|---|---|
| **記憶（被動）** | 確立基礎知識 | `user-invocable`、`disable-model-invocation`、`skillOverrides`、`allowed-tools`、Human Approval Gate。 |
| **理解（半被動）** | 解釋概念關聯 | 觸發權限與工具權限是正交維度；A 提及 B 不會改變 Claude 透過 `Skill(B)` 呼叫時的身分。 |
| **分析（主動）** | 拆解流程與假設 | A→B 假設使用者授權會沿呼叫鏈傳遞，但設計刻意把使用者直接觸發與模型下一跳分開。issue 也顯示部分版本混淆了 slash command 與工具路徑。 |
| **應用（主動）** | 轉為行動 | (1) 盤點現有 Skill 並分類；(2) 將 deploy 類設為 User Only；(3) 對三條觸發路徑建立版本化 smoke test。 |
| **評估（主動）** | 權衡取捨 | 自動組合降低摩擦，但不適合不可逆動作；Human Approval Gate 多一次互動，換得決策可見性與較低誤部署風險。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：`deploy` 的批准是開始部署，還是指定環境與版本的部署？slash command 參數如何明確表達？
- **假設**：使用者輸入 `/deploy-production` 是否代表充分知情批准？若部署版本或環境已變更，這個假設還成立嗎？
- **證據**：哪些特權 Skill 的人為批准確實降低事故？需要蒐集哪些 audit log 與 rollback 資料？
- **觀點**：若 CI/CD policy 已有批准，Skill 層 gate 能否補足模型選擇何時採取動作的風險？
- **後果**：所有 Skill 都設為 User Only，是否會形成手動瓶頸並導致使用者繞過流程？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** 特權 B 誤設為模型可呼叫，可能在不合適的環境部署、發布、寄送或合併；過度限制也會讓必要流程被繞過。
2. **什麼情況下會失敗？** A 依賴 B 自動執行卻把 B 設成 User Only 時，A→B 必然中斷。特定版本也可能出現 slash command 重複呼叫、plugin reload 或 subagent 承接意圖失敗。
3. **有沒有更好的替代方案？** 對高風險操作，可拆成模型可執行的 `deploy-plan` 與人類觸發的 `deploy-execute`。這保留自動驗證與計畫階段，並讓批准綁定明確版本和環境。

## 相關連結（Related）

- [[2026-04-29-CLAUDE-CODE-DISABLE-MODEL-INVOCATION-SKILL-VISIBILITY-SOURCE-ANALYSIS]] — 原始碼說明模型可見性與 `Skill` tool 驗證的雙重防線。
- [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]] — 官方 Skills frontmatter 與載入生命週期的基礎筆記。
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — 將觸發權限放入 Skills、Commands、Subagents 的架構選型。
- [[2026-03-31-AI-WORKFLOW-AGENTS-SKILLS-STANDARDS]] — 將 Privileged Action 放入 Agent 路由、Skill 能力包與流程標準的治理架構。

## References

- [Claude Code Skills 官方文件](https://code.claude.com/docs/en/skills)
- [Claude Code Slash Commands 文件](https://code.claude.com/docs/en/slash-commands)
- [GitHub issue #43809](https://github.com/anthropics/claude-code/issues/43809)
- [GitHub issue #32817](https://github.com/anthropics/claude-code/issues/32817)
- [GitHub issue #59363](https://github.com/anthropics/claude-code/issues/59363)
- [GitHub issue #87536](https://github.com/anthropics/claude-code/issues/87536)
