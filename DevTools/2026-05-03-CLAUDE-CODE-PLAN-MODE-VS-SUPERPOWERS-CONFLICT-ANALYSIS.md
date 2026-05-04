---
title: "Claude Code Plan Mode vs SuperPowers 外掛衝突深度分析 — 原始碼追蹤 + 社群經驗 + 架構級不相容全解"
date: 2026-05-03
category: DevTools
tags:
  - "#ai/claude-code"
  - "#ai/skill-design"
  - "#tools/cli"
  - "#devtools/workflow"
  - "#ai/agent"
source: "conversation research: Plan Mode vs SuperPowers 原始碼分析 + 網路社群調查"
source_type: article
author: "swchen（原始研究）"
status: notes
links:
  - "[[SUPERPOWERS-OBRA]]"
  - "[[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]]"
  - "[[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-19-CLAUDE-CODE-PLUGIN-JSON-DEPENDENCIES-SHARED-SKILLS-SOURCE-ANALYSIS]]"
  - "[[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
---

## 摘要（Summary）

本文從**原始碼追蹤**與**網路社群經驗**兩個面向，深入分析 Claude Code 內建 Plan Mode（計畫模式）與 SuperPowers 外掛之間的衝突。Plan Mode 是一套**權限系統**（Permission System），透過 `EnterPlanMode` / `ExitPlanMode` 延遲工具（Deferred Tool）控制唯讀/讀寫模式切換；SuperPowers 則是一套**方法論框架**（Methodology Framework），透過 brainstorming → writing-plans → executing-plans 的技能鏈管理開發流程。兩者在架構層級存在不相容：SuperPowers v4.3.0 起**刻意攔截 `EnterPlanMode`**，將流程導向自己的 brainstorming skill；Plan Mode 的唯讀限制會阻止 SuperPowers 寫入 spec/plan 檔案；Auto Mode 在意外觸發 Plan Mode 循環後會被停用。

> [!important] 核心結論
> 兩套系統**本質不同**（權限系統 vs 方法論框架），不應同時啟動。SuperPowers 已內建攔截機制避免進入原生 Plan Mode，但仍有邊緣情況會導致衝突。

## 關鍵洞察（Key Insights）

- **Plan Mode 是權限系統，不是規劃方法論** — 它的核心是將工具權限切換到唯讀模式（`mode: 'plan'`），透過 `ToolPermissionContext` 管理狀態，退出時恢復先前權限。參見 [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]]
- **SuperPowers 是方法論框架，不是權限系統** — 它靠 prompt 指示（而非系統級工具限制）控制行為，計畫存在專案目錄而非系統目錄。參見 [[SUPERPOWERS-OBRA]]
- **SuperPowers v4.3.0 刻意攔截 `EnterPlanMode`** — `using-superpowers` 的 flow graph 包含 `"About to EnterPlanMode?"` 節點，將流程導向 brainstorming skill，**Plan Mode 永遠不會被進入**
- **Auto Mode 停用是最嚴重的衝突** — Issue #49947 記錄了 SuperPowers 觸發 Plan Mode 循環後 Auto Mode 自動停用的問題
- **Plan 側邊面板永遠空白** — SuperPowers 的計畫存在 `docs/superpowers/plans/` 而非 `~/.claude/plans/{slug}.md`，桌面版面板無法渲染

## 詳細內容（Details）

### 一、兩套系統的本質差異

| 面向 | Claude Code 內建 Plan Mode | SuperPowers 外掛 |
|------|---------------------------|-----------------|
| **本質** | 權限系統（Permission System） — 切換到唯讀模式 | 方法論框架（Methodology Framework） — 結構化開發流程 |
| **觸發方式** | `Shift+Tab` 兩次或 Claude 主動呼叫 `EnterPlanMode` | Skill 自動觸發（brainstorming → writing-plans → executing-plans） |
| **計畫儲存位置** | `~/.claude/plans/{slug}.md` | `docs/superpowers/plans/YYYY-MM-DD-<name>.md` |
| **工具限制** | 進入後**只允許唯讀工具**（Read, Glob, Grep），透過 `ToolPermissionContext.mode = 'plan'` 強制 | 無系統級工具限制，靠 prompt 指示控制 |
| **退出機制** | `ExitPlanMode` → 使用者在面板核准/拒絕 → 恢復 `prePlanMode` | 寫完 plan 後聊天確認 → 進入 executing-plans |
| **執行哲學** | 核准後直接執行，無強制 checkpoint | 每 2–5 分鐘一個 step，TDD 驅動，頻繁 commit |
| **狀態管理** | 系統級：`ToolPermissionContext`、`prePlanMode`、`strippedDangerousRules` | Prompt 級：skill 指示 + TodoWrite 追蹤 |

### 二、原始碼追蹤：Plan Mode 的實現機制

#### 2.1 工具定義與入口

Plan Mode 的核心由兩個**延遲工具**（Deferred Tool）組成：

**`EnterPlanModeTool`**（`src/tools/EnterPlanModeTool/EnterPlanModeTool.ts`）：

```typescript
// shouldDefer: true — 不在預設工具列表中，透過 ToolSearch 發現
export const EnterPlanModeTool: Tool<InputSchema, Output> = buildTool({
  name: ENTER_PLAN_MODE_TOOL_NAME,
  shouldDefer: true,
  isReadOnly() { return true },
  async call(_input, context) {
    if (context.agentId) {
      throw new Error('EnterPlanMode tool cannot be used in agent contexts')
    }
    // 關鍵：切換權限模式
    handlePlanModeTransition(appState.toolPermissionContext.mode, 'plan')
    context.setAppState(prev => ({
      ...prev,
      toolPermissionContext: applyPermissionUpdate(
        prepareContextForPlanMode(prev.toolPermissionContext),
        { type: 'setMode', mode: 'plan', destination: 'session' },
      ),
    }))
    return { data: { message: 'Entered plan mode...' } }
  },
})
```

> [!note] 關鍵限制
> `EnterPlanMode` **不能在 Agent（子代理人）上下文中使用**（`context.agentId` 存在時拋出錯誤），且不能在 `--channels` 模式下使用（會造成 UI 掛起）。

**`ExitPlanModeV2Tool`**（`src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts`）：

```typescript
async validateInput(_input, { getAppState }) {
  const mode = getAppState().toolPermissionContext.mode
  if (mode !== 'plan') {
    return {
      result: false,
      message: 'You are not in plan mode...',
      errorCode: 1,
    }
  }
  return { result: true }
},

async call(input, context) {
  // 1. 讀取 plan 檔案
  const plan = inputPlan ?? getPlan(context.agentId)
  
  // 2. 恢復先前權限模式
  context.setAppState(prev => {
    let restoreMode = prev.toolPermissionContext.prePlanMode ?? 'default'
    // Auto Mode gate 防禦：若 circuit breaker 已觸發，回退到 default
    if (restoreMode === 'auto' && !isAutoModeGateEnabled()) {
      restoreMode = 'default'
    }
    return {
      ...prev,
      toolPermissionContext: {
        ...baseContext,
        mode: restoreMode,
        prePlanMode: undefined,
      },
    }
  })
}
```

#### 2.2 系統提示注入（System Prompt Injection）

進入 Plan Mode 後，系統透過 **attachment 機制**注入唯讀指示（`src/utils/messages.ts:3366`）：

```
Plan mode is active. The user indicated that they do not want you to execute yet -- 
you MUST NOT make any edits (with the exception of the plan file mentioned below), 
run any non-readonly tools (including changing configs or making commits), 
or otherwise make any changes to the system. 
This supercedes any other instructions you have received.
```

attachment 類型包括：
- `plan_mode` — 首次進入時的完整指示
- `plan_mode_reentry` — 重新進入時的指示（含既有 plan 參考）
- `plan_mode_exit` — 退出通知
- sparse 版本 — 後續 turn 的精簡提醒（避免 token 浪費）

#### 2.3 權限狀態生命週期

```
┌──────────────────────────────────────────────────────────────────┐
│                    Plan Mode 狀態機                               │
└──────────────────────────────────────────────────────────────────┘

 [default/auto mode]
       │
       │ EnterPlanMode.call()
       ▼
 ┌─────────────────────────────────────────┐
 │  prepareContextForPlanMode()            │
 │  ├─ 儲存 prePlanMode = 當前 mode       │
 │  ├─ 若 auto mode：                     │
 │  │   └─ stripDangerousPermissionsForAutoMode() │
 │  │      (移除 bash wildcard、python 等)│
 │  └─ 設定 mode = 'plan'                 │
 └─────────────────┬───────────────────────┘
                   │
                   ▼
 [Plan Mode 唯讀探索階段]
   ├─ 允許：Read, Glob, Grep, AskUserQuestion
   ├─ 允許：寫入 plan 檔案（~/.claude/plans/{slug}.md）
   └─ 禁止：FileEdit, FileWrite, Bash（寫入類）
                   │
                   │ ExitPlanMode.call()
                   ▼
 ┌─────────────────────────────────────────┐
 │  恢復權限                               │
 │  ├─ restoreMode = prePlanMode ?? 'default' │
 │  ├─ Auto Mode gate 檢查：              │
 │  │   若 circuit breaker 觸發 → default  │
 │  ├─ 恢復 strippedDangerousRules        │
 │  └─ setNeedsPlanModeExitAttachment(true)│
 └─────────────────┬───────────────────────┘
                   │
                   ▼
 [恢復原始 mode，開始實作]
```

### 三、原始碼追蹤：SuperPowers 的攔截機制

#### 3.1 using-superpowers flow graph 的 EnterPlanMode 攔截

SuperPowers v4.3.0（2026-02-12）在 `using-superpowers` skill 的 flow graph 中加入了攔截節點：

```
digraph skill_flow {
    "About to EnterPlanMode?" → "Already brainstormed?"
    "Already brainstormed?" →[no]→ "Invoke brainstorming skill"
    "Already brainstormed?" →[yes]→ "Might any skill apply?"
}
```

> [!warning] 攔截行為
> 當 Claude 即將呼叫 `EnterPlanMode` 時，SuperPowers 檢查是否已完成 brainstorming。若未完成，強制進入 brainstorming skill；若已完成，跳過 Plan Mode 直接進入 skill 選擇流程。**原生 Plan Mode 永遠不會被進入。**

Release Notes 原文（`RELEASE-NOTES.md:335-337`）：

> [!quote] SuperPowers v4.3.0 Release Note
> Added an `EnterPlanMode` intercept to the skill flow graph. When the model is about to enter Claude's native plan mode, it checks whether brainstorming has happened and routes through the brainstorming skill instead. Plan mode is never entered.

#### 3.2 SuperPowers 的計畫流程 vs Plan Mode

```
┌─────────────────────────────────────────────────────────────────┐
│              SuperPowers 流程                                    │
│                                                                 │
│  brainstorming ──► writing-plans ──► executing-plans            │
│  (探索+設計)       (TDD計畫)         (逐步執行)                  │
│                                                                 │
│  spec 存入：docs/superpowers/specs/YYYY-MM-DD-<topic>.md        │
│  plan 存入：docs/superpowers/plans/YYYY-MM-DD-<name>.md         │
│  每個 step 2-5 分鐘，TDD 驅動                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              原生 Plan Mode 流程                                 │
│                                                                 │
│  EnterPlanMode ──► 唯讀探索 ──► ExitPlanMode ──► 執行           │
│  (權限切換)        (Read/Glob)    (權限恢復)                      │
│                                                                 │
│  plan 存入：~/.claude/plans/{word-slug}.md                       │
│  核准後一次性執行，無強制 checkpoint                               │
└─────────────────────────────────────────────────────────────────┘
```

### 四、具體衝突分析

#### 衝突 1：EnterPlanMode 攔截（嚴重度：🟡 設計如此）

**現象**：SuperPowers 故意不讓 Claude 進入原生 Plan Mode。

**原始碼證據**：
- `using-superpowers` skill 的 flow graph 包含 `"About to EnterPlanMode?"` 節點
- 所有規劃需求被導向 brainstorming skill

**影響**：
- 使用者無法透過 Claude 自發行為進入原生 Plan Mode
- 但仍可手動按 `Shift+Tab` 兩次強制進入
- 手動進入後，SuperPowers 的 plan_mode attachment 指示（唯讀限制）會與 SuperPowers skill 的寫檔需求衝突

#### 衝突 2：Plan 側邊面板空白（嚴重度：🟡 體驗問題）

**現象**：桌面版的 Plan 側邊面板只讀取 `~/.claude/plans/{slug}.md`，SuperPowers 的計畫存在專案目錄。

**原始碼證據**：`src/utils/plans.ts` 的 `getPlanFilePath()` 硬編碼路徑為 `~/.claude/plans/`。

**GitHub Issue**：obra/superpowers#1260 提出三個整合方案（事後掛鉤、平行寫入、配置開關），尚未實作。

#### 衝突 3：Auto Mode 停用（嚴重度：🔴 嚴重）

**現象**：SuperPowers 的 `using-superpowers` skill 在每次會話啟動時自動注入「先計畫再執行」指示，可能觸發 `EnterPlanMode` → `ExitPlanMode` 循環。退出後 Auto Mode 被停用。

**原始碼根因**：`ExitPlanModeV2Tool.ts:362-379` — 退出時恢復 `prePlanMode`，若 Auto Mode 的 circuit breaker 已觸發（`isAutoModeGateEnabled()` 回傳 `false`），`restoreMode` 會被強制設為 `'default'`：

```typescript
if (restoreMode === 'auto' && !isAutoModeGateEnabled()) {
  restoreMode = 'default' // Auto Mode 被停用！
}
```

**GitHub Issue**：anthropics/claude-code#49947

#### 衝突 4：唯讀限制 vs 寫檔需求（嚴重度：🟡 理論存在）

**現象**：若使用者手動進入 Plan Mode，同時 SuperPowers 的 brainstorming skill 嘗試寫入 spec 檔案到 `docs/superpowers/specs/`，Plan Mode 的唯讀限制只允許寫入 `~/.claude/plans/{slug}.md`。

**系統提示原文**（`src/utils/messages.ts:3366`）：
> "you MUST NOT make any edits (with the exception of the plan file mentioned below)"

#### 衝突 5：流程重疊造成 Token 浪費（嚴重度：🟡 效率問題）

兩套系統都在做類似的事（探索 → 規劃 → 執行），如果兩者同時啟動，Token 消耗可能加倍。

### 五、社群經驗與 GitHub Issues

#### 已知 Issues

| Issue | 嚴重度 | 狀態 | 描述 |
|-------|--------|------|------|
| obra/superpowers#1260 | 🟡 | 開放 | Plan 側邊面板不顯示 SuperPowers 的計畫 |
| anthropics/claude-code#49947 | 🔴 | 開放 | Auto Mode 在 Plan Mode 循環後自動停用 |
| anthropics/claude-code#2988 | 🟡 | 開放 | 退出 Plan Mode 時 Auto-Accept 自動啟用 |
| anthropics/claude-code#30042 | 🟡 | 開放 | 無法完全停用 Plan Mode |

#### 社群評價

> [!quote] Hacker News 使用者
> 「我之前同時使用 Plan Mode 和 Superpowers，但最終 Plan Mode 就夠用了，我就不再用了。」

> [!quote] Builder.io 部落格
> 在大型重構中，SuperPowers 的結構化規劃可比無規劃的直接執行**節省 40-60% 的 Token 用量**。

> [!quote] mejba.me 測評
> SuperPowers 降低了 14% 的 Token 使用量並提升了程式碼品質——但不是對每個任務都有效。對小型任務，brainstorming 階段的開銷可能反而浪費更多 Token。

### 六、建議與最佳實踐

| 情境 | 建議 |
|------|------|
| **小型任務**（修 bug、改一行） | 不用任何規劃，或只用原生 Plan Mode |
| **中型任務**（加功能、跨 2-3 檔） | 原生 Plan Mode 即可 |
| **大型任務**（重構、新系統） | SuperPowers 完整流程（brainstorming → plan → execute） |
| **依賴 Auto Mode** | 注意 SuperPowers 可能觸發 Plan Mode 循環；可在 CLAUDE.md 加 `skip brainstorming for simple tasks` |
| **需要桌面版 Plan 面板** | 目前只能用原生 Plan Mode，等待 SuperPowers 整合 |
| **團隊協作**（Team Lead + Teammate） | 原生 Plan Mode 有內建的 mailbox 核准流程；SuperPowers 無此功能 |

> [!tip] 實用建議
> 在 CLAUDE.md 中加入以下指示，可以減少兩套系統的衝突：
> ```
> # Plan Mode 使用規則
> - 小型變更（< 3 檔案）：不進入 Plan Mode，不觸發 brainstorming
> - 中型變更：使用原生 Plan Mode
> - 大型變更（> 5 檔案或架構改動）：使用 SuperPowers 完整流程
> ```

## 我的心得（My Takeaways）

1. **兩套系統的本質完全不同**：Plan Mode 是「權限閘門」，SuperPowers 是「工作流程」。理解這個差異是避免衝突的關鍵。
2. **SuperPowers 的攔截是刻意設計**：v4.3.0 的 Release Notes 明確說明這是有意為之，而非 bug。SuperPowers 團隊認為自己的流程比原生 Plan Mode 更完整。
3. **Auto Mode 衝突是最大的痛點**：從原始碼可以看到 `ExitPlanMode` 的 circuit breaker 機制相當複雜，edge case 很多。依賴 Auto Mode 的使用者需要特別注意。
4. **Plan 面板整合是未來方向**：Issue #1260 提出的三個方案都可行，只是需要 SuperPowers 團隊實作。在那之前，兩套系統的計畫儲存是完全分離的。
5. **原始碼分析的價值**：許多衝突點只有通過閱讀原始碼才能發現（如 `isAutoModeGateEnabled()` 的 circuit breaker 行為），網路文章通常只描述表面現象。

## 待補充（Open Questions）

- SuperPowers 的 `EnterPlanMode` 攔截是在 prompt 層面實現的（flow graph），如果 Claude 的模型行為變化導致忽略 flow graph 指示，攔截是否會失效？建議搜尋：`superpowers skill compliance rate`
- `ExitPlanMode` 的 `isAutoModeGateEnabled()` 具體在什麼條件下回傳 `false`（circuit breaker 觸發條件）？需要追蹤 `src/utils/permissions/autoModeState.ts` 和 GrowthBook 的 gate 設定。建議搜尋：`claude code auto mode circuit breaker`
- obra/superpowers#1260 提出的三個整合方案何時會落地？SuperPowers 團隊的優先級如何？建議搜尋：`superpowers plan panel integration roadmap`
- 若在 Plan Mode 中手動呼叫 SuperPowers 的 `writing-plans` skill，系統會如何處理唯讀限制 vs skill 的寫檔需求？這是未被測試的 edge case。建議搜尋：`plan mode skill conflict file write`
- Claude Code 未來是否會提供 Plan Mode 的 API/Hook 接口，讓第三方外掛可以整合？參見 [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]]。建議搜尋：`claude code plan mode hook api`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 1. Plan Mode 透過 `EnterPlanMode` / `ExitPlanMode` 延遲工具切換權限 2. SuperPowers 用 brainstorming → writing-plans → executing-plans 技能鏈 3. Plan 檔存在 `~/.claude/plans/` vs `docs/superpowers/plans/` 4. SuperPowers v4.3.0 攔截 `EnterPlanMode` 5. Auto Mode 可能在 Plan Mode 循環後被停用 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Plan Mode 的唯讀限制是透過 `ToolPermissionContext.mode = 'plan'` 在系統級強制執行的，而 SuperPowers 只靠 prompt 指示控制。這意味著 Plan Mode 的約束**不可被 prompt 覆蓋**，但 SuperPowers 的約束可能被忽略。SuperPowers 選擇攔截而非整合，是因為它認為自己的流程更完整（含 TDD、checkpoint、spec 文件），不需要原生 Plan Mode 的權限閘門。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | **關鍵假設**：SuperPowers 假設 prompt 層面的攔截足夠可靠（flow graph 中的 `"About to EnterPlanMode?"` 節點）。但 LLM 的行為不確定性意味著攔截可能失效——特別是在長對話或 context compaction 後。**潛在漏洞**：使用者手動按 `Shift+Tab` 進入 Plan Mode 時，SuperPowers 無法攔截（這是 UI 層面的操作，不經過 skill flow graph）。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. 在 CLAUDE.md 中明確規定何時用原生 Plan Mode、何時用 SuperPowers 2. 對於依賴 Auto Mode 的工作流，在 SuperPowers brainstorming 結束後手動檢查 Auto Mode 是否仍啟用 3. 考慮為 SuperPowers 寫一個 post-plan hook，將計畫同步到 `~/.claude/plans/` 以支援桌面面板 |
| **評估（主動）** | 判斷多個方案的優劣，權衡決策 | **原生 Plan Mode 的優勢**：系統級強制、桌面面板可視化、Team Lead 核准流程、與 Auto Mode 整合完整。**SuperPowers 的優勢**：更結構化的開發流程、TDD 驅動、spec 文件留存在專案中（可 git 追蹤）、每步 checkpoint 降低失控風險。**結論**：小中型任務用原生 Plan Mode（快速、系統整合好），大型任務用 SuperPowers（流程完整、品質高）。兩者不應同時啟動。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「唯讀模式」在 Plan Mode 中的精確邊界是什麼？Plan 檔案本身的寫入是透過什麼機制允許的？
- **假設**：SuperPowers 假設 prompt 層面的攔截足夠可靠。若模型更新導致 skill compliance 下降，攔截失效後會發生什麼連鎖反應？
- **證據**：SuperPowers 聲稱可節省 40-60% Token，但此數據來自 Builder.io 的單一測評。在不同任務類型（修 bug vs 新功能 vs 重構）中，數據是否一致？
- **觀點**：Anthropic 的 Plan Mode 團隊是否考慮過提供外掛整合 API？從 `ExitPlanMode` 的 `allowedPrompts` 參數設計來看，系統正朝向更細粒度的權限控制發展。
- **後果**：若依照「大型任務用 SuperPowers」的建議執行，長期下來專案中會累積大量 `docs/superpowers/specs/` 和 `docs/superpowers/plans/` 檔案。這些檔案的維護成本如何？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 同時安裝 SuperPowers 並依賴 Auto Mode 時，Auto Mode 被意外停用可能導致工作流中斷。使用者可能不知道原因（需要查看權限模式狀態），浪費時間排查。
2. **什麼情況下會失敗？** — 手動按 `Shift+Tab` 進入 Plan Mode → SuperPowers brainstorming skill 嘗試寫 spec 檔案 → 被唯讀限制阻止 → 流程卡住。或：context compaction 後 SuperPowers 的攔截指示被丟棄 → Claude 自發進入原生 Plan Mode → 退出時 Auto Mode 被停用。
3. **有沒有更好的替代方案？** — 理想方案是 Anthropic 提供 Plan Mode 的 Hook API（類似 `onPlanModeEnter` / `onPlanModeExit`），讓第三方外掛可以整合。或者 SuperPowers 實作 Issue #1260 的方案 A（事後掛鉤），在自己的流程結束後將計畫同步到原生路徑。

## 相關連結（Related）

- [[SUPERPOWERS-OBRA]] — SuperPowers 外掛的完整介紹與功能分析
- [[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]] — SuperPowers、GSD、gstack 三大框架比較
- [[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]] — Skill 載入、壓縮與撰寫技巧，理解 SuperPowers 如何被載入
- [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] — Skill frontmatter 與安全機制，Plan Mode 的工具限制基礎
- [[2026-04-19-CLAUDE-CODE-PLUGIN-JSON-DEPENDENCIES-SHARED-SKILLS-SOURCE-ANALYSIS]] — Plugin 依賴系統，SuperPowers 的載入機制
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — Claude Code 原始碼分析基礎
- [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]] — Hook API 分析，Plan Mode 未來可能的整合接口
- [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] — CLAUDE.md 最佳實踐，含 Skills 按需載入比較

## References

- [SuperPowers GitHub Repo](https://github.com/obra/superpowers)
- [Issue #1260: Integrate writing-plans with Claude Code's native Plan Mode](https://github.com/obra/superpowers/issues/1260)
- [Issue #49947: Auto Mode auto-disables after Plan Mode cycle](https://github.com/anthropics/claude-code/issues/49947)
- [Issue #2988: Prevent Auto-Accept Mode from Automatically Enabling When Exiting Plan Mode](https://github.com/anthropics/claude-code/issues/2988)
- [Superpowers Plugin vs Claude Code Ultra Plan: Which Should You Use? (MindStudio)](https://www.mindstudio.ai/blog/superpowers-plugin-vs-claude-code-ultra-plan)
- [I Tested Superpowers for Claude Code — Here's the Truth (mejba.me)](https://www.mejba.me/blog/superpowers-plugin-claude-code-review)
- [The Superpowers Plugin for Claude Code (Builder.io)](https://www.builder.io/blog/claude-code-superpowers-plugin)
- [Claude Code Plan Mode 原始碼](https://github.com/anthropics/claude-code) — `src/tools/EnterPlanModeTool/`、`src/tools/ExitPlanModeTool/`、`src/utils/messages.ts`、`src/utils/permissions/permissionSetup.ts`
