---
title: "Claude Code disable-model-invocation 原始碼解析：Skill 可見性雙道防線、跨 Skill 呼叫限制與繞過方案"
date: 2026-04-29
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#devtools/claude-code"
  - "#ai/agent-architecture"
  - "#devtools/skills"
  - "#typescript"
source: "conversation"
source_type: code
author: "swchen44 + Claude"
status: notes
links:
  - "[[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]]"
  - "[[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]]"
  - "[[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]]"
  - "[[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]]"
github_stars: N/A
github_language: TypeScript
---

## 摘要（Summary）

基於 Claude Code 反編譯原始碼逐行追蹤，完整解析 `disable-model-invocation` frontmatter 欄位的內部運作機制。核心發現：該旗標實施**兩道獨立防線**——第一道在 `getSkillToolCommands()` 從 Skill 清單中完全移除（模型看不到）；第二道在 `SkillTool.validateInput()` 硬性拒絕（即使猜到名字也無法呼叫）。但使用者手動輸入 `/skill-name` 的路徑（`processSlashCommand()`）**完全不檢查此旗標**，且 typeahead 建議（`getSlashCommandToolSkills()`）**刻意包含**被禁用的 Skill。本文涵蓋跨 Skill 呼叫、Hook 中呼叫 Skill、Command 中呼叫 Skill 等多種 Use Case 的可行性分析與替代方案。

## 關鍵洞察（Key Insights）

- **`disable-model-invocation: true` = 「只允許人類手動觸發」**——這是安全設計，不是 bug。內建的 `debug`、`batch`、`skillify` 都使用此旗標
- **兩道防線完全獨立**：即使模型繞過第一道（猜到 Skill 名字），第二道 `validateInput` 仍會硬性拒絕（errorCode 4）
- **使用者路徑完全不受限**：`processSlashCommand()` 中**零行程式碼**檢查 `disableModelInvocation`，typeahead 甚至刻意將其加入建議清單
- **Hook 無法直接呼叫 Skill**——Hook 系統（stdin/stdout JSON 管道）和 Skill 系統（SkillTool + processSlashCommand）是完全獨立的子系統，沒有交叉呼叫的 API
- **`userInvocable` 是另一個獨立旗標**——預設為 `true`，若設為 `false` 則 Skill 從 typeahead 和 `/help` 中隱藏（`isHidden: !userInvocable`），但模型仍可能透過 SkillTool 呼叫（若沒設 `disable-model-invocation`）

## 詳細內容（Details）

### 系統架構圖：Skill 可見性的三層過濾

```
┌─────────────────────────────────────────────────────────────────────┐
│                    所有 Skill（allCommands）                         │
│  來源：getCommands(cwd)                                             │
│  合併 skills/ + commands/ + bundled + plugin + mcp                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│ getSkillTool    │  │ getSlashCommand │  │ processSlashCommand │
│ Commands()      │  │ ToolSkills()    │  │ ()                  │
│ src/commands.ts │  │ src/commands.ts │  │ processSlashCommand │
│ :563            │  │ :586            │  │ .tsx:309            │
├─────────────────┤  ├─────────────────┤  ├─────────────────────┤
│ 用途：模型看到  │  │ 用途：使用者    │  │ 用途：使用者手動    │
│ 的 Skill 清單   │  │ typeahead 建議  │  │ 輸入 /skill-name    │
│ + skill_listing │  │ + /help 列表    │  │ 的執行路徑          │
├─────────────────┤  ├─────────────────┤  ├─────────────────────┤
│ 過濾條件：      │  │ 過濾條件：      │  │ 過濾條件：          │
│ ✅ type=prompt  │  │ ✅ type=prompt  │  │ ✅ hasCommand() 即可│
│ ✅ !disable-    │  │ ✅ source≠      │  │ ❌ 不檢查 disable-  │
│    ModelInvoc.  │  │    builtin      │  │    ModelInvocation   │
│ ✅ source≠      │  │ ✅ 有 desc 或   │  │                     │
│    builtin      │  │    whenToUse    │  │                     │
│ ✅ 有 desc/     │  │ ✅ skills/      │  │                     │
│    whenToUse    │  │    plugin/      │  │                     │
│                 │  │    bundled/     │  │                     │
│                 │  │    OR disable-  │  │                     │
│                 │  │    ModelInvoc.  │  │                     │
│                 │  │    ← ★ 刻意    │  │                     │
│                 │  │      包含！     │  │                     │
├─────────────────┤  ├─────────────────┤  ├─────────────────────┤
│ 消費者：        │  │ 消費者：        │  │ 消費者：            │
│ • SkillTool     │  │ • REPL typeahead│  │ • 使用者 prompt     │
│   prompt        │  │ • /help         │  │   直接打 /xxx       │
│ • skill_listing │  │ • Bridge        │  │                     │
│   attachment    │  │                 │  │                     │
│ • system-       │  │                 │  │                     │
│   reminder      │  │                 │  │                     │
└────────┬────────┘  └─────────────────┘  └─────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              SkillTool.validateInput()                          │
│              src/tools/SkillTool/SkillTool.ts:412-418           │
│                                                                 │
│  if (foundCommand.disableModelInvocation) {                     │
│    return { result: false, errorCode: 4,                        │
│      message: "cannot be used with Skill tool                   │
│               due to disable-model-invocation" }                │
│  }                                                              │
│                        ← ★ 第二道防線：即使模型猜到名字也拒絕    │
└─────────────────────────────────────────────────────────────────┘
```

### 執行流程圖：模型呼叫 vs 使用者呼叫

```
═══════════════════════════════════════════════════════════════
  路徑 A：模型透過 SkillTool 呼叫 Skill（被阻擋）
═══════════════════════════════════════════════════════════════

模型回應 tool_use: { name: "Skill", input: { skill: "batch" } }
  │
  ▼
SkillTool.validateInput()  (SkillTool.ts:370)
  │
  ├── 1. 找到 command？ → YES
  │
  ├── 2. foundCommand.disableModelInvocation？
  │      │
  │      └── YES → return { result: false, errorCode: 4,
  │                  message: "cannot be used with Skill tool
  │                           due to disable-model-invocation" }
  │                  │
  │                  ▼
  │              模型收到 error → 無法執行
  │              （模型可能會告訴使用者「請手動執行 /batch」）
  │
  └── NO → 繼續檢查 type === 'prompt' → call()

═══════════════════════════════════════════════════════════════
  路徑 B：使用者手動輸入 /batch（正常執行）
═══════════════════════════════════════════════════════════════

使用者在 prompt 輸入：/batch migrate *.js to TypeScript
  │
  ▼
processUserInput()  (processUserInput.ts:480)
  │
  ▼
processSlashCommand()  (processSlashCommand.tsx:309)
  │
  ├── parseSlashCommand("/batch migrate...") → { commandName: "batch", args: "..." }
  │
  ├── hasCommand("batch", commands) → YES
  │
  ├── ❌ 完全不檢查 disableModelInvocation ← ★ 關鍵差異
  │
  ▼
processPromptSlashCommand("batch", args, commands, context)
  │
  ▼
Skill 正常展開為 prompt → 注入對話 → 模型開始執行
```

### 時序圖：兩道防線的作用時機

```
 模型(API)      system-reminder      SkillTool        processSlashCommand
    │                 │                  │                      │
    │  ┌──────────────┤                  │                      │
    │  │ skill_listing│                  │                      │
    │  │ 使用 getSkill│                  │                      │
    │  │ ToolCommands │                  │                      │
    │  │ (已過濾掉    │                  │                      │
    │  │ disable-MI)  │                  │                      │
    │  └──────────────┤                  │                      │
    │◄─ "Available    │                  │                      │
    │   skills: ..."  │                  │                      │
    │  (看不到 batch) │                  │                      │
    │                 │                  │                      │
    │  [若模型猜到]   │                  │                      │
    │─ tool_use ──────────────────────►│                      │
    │  Skill("batch") │                  │                      │
    │                 │        validateInput()                  │
    │                 │        disableModelInvocation?          │
    │                 │          → YES → reject                 │
    │◄─ error ────────────────────────│                      │
    │  "cannot be                      │                      │
    │   used..."                       │                      │
    │                 │                  │                      │
    │                 │                  │    [使用者手動打]     │
    │                 │                  │    /batch args        │
    │                 │                  │         │             │
    │                 │                  │         ▼             │
    │                 │                  │    不檢查 disable-MI  │
    │                 │                  │    正常展開 prompt     │
    │                 │                  │         │             │
    │◄────────────────────────────────────────────│             │
    │  [接收到展開的 Skill prompt，開始執行]        │             │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式：Principle of Least Authority（最小權限原則）
> `disable-model-invocation` 實踐的是「人類在迴圈中（Human-in-the-Loop）」模式——某些高影響力操作（如 `batch` 批量修改、`debug` 啟用日誌）需要人類明確意圖。

1. **兩道防線而非一道**：第一道（清單過濾）是「看不到」，第二道（validateInput）是「猜到也不行」。Defense in depth 思維——如果模型從對話上下文推斷出 Skill 名字（如使用者提到過），第二道防線仍能阻擋
2. **typeahead 刻意包含被禁用的 Skill**（`getSlashCommandToolSkills` 的 `cmd.disableModelInvocation` 條件）——使用者需要知道這些 Skill 存在且可用，只是不讓模型自主呼叫
3. **`userInvocable` 和 `disableModelInvocation` 是正交的兩個旗標**：`userInvocable: false` 隱藏 Skill 讓使用者也看不到（typeahead 消失），`disableModelInvocation: true` 只阻擋模型但使用者可見
4. **`isHidden: !userInvocable`**（`loadSkillsDir.ts:335`）——`userInvocable` 控制 UI 可見性，`disableModelInvocation` 控制模型可呼叫性，兩者完全解耦

### 關鍵程式碼（Key Code Snippets）

**防線一：模型清單過濾**（`src/commands.ts:563-580`）：

```typescript
// SkillTool shows ALL prompt-based commands that the model can invoke
export const getSkillToolCommands = memoize(
  async (cwd: string): Promise<Command[]> => {
    const allCommands = await getCommands(cwd)
    return allCommands.filter(
      cmd =>
        cmd.type === 'prompt' &&
        !cmd.disableModelInvocation &&    // ← 防線一：直接排除
        cmd.source !== 'builtin' &&
        (cmd.loadedFrom === 'bundled' ||
          cmd.loadedFrom === 'skills' ||
          cmd.loadedFrom === 'commands_DEPRECATED' ||
          cmd.hasUserSpecifiedDescription ||
          cmd.whenToUse),
    )
  },
)
```

**防線二：validateInput 硬性拒絕**（`src/tools/SkillTool/SkillTool.ts:412-418`）：

```typescript
// Check if command has model invocation disabled
if (foundCommand.disableModelInvocation) {
  return {
    result: false,
    message: `Skill ${normalizedCommandName} cannot be used with ${SKILL_TOOL_NAME} tool due to disable-model-invocation`,
    errorCode: 4,
  }
}
```

**使用者 typeahead 刻意包含**（`src/commands.ts:586-598`）：

```typescript
export const getSlashCommandToolSkills = memoize(
  async (cwd: string): Promise<Command[]> => {
    const allCommands = await getCommands(cwd)
    return allCommands.filter(
      cmd =>
        cmd.type === 'prompt' &&
        cmd.source !== 'builtin' &&
        (cmd.hasUserSpecifiedDescription || cmd.whenToUse) &&
        (cmd.loadedFrom === 'skills' ||
          cmd.loadedFrom === 'plugin' ||
          cmd.loadedFrom === 'bundled' ||
          cmd.disableModelInvocation),  // ← 刻意包含！讓使用者能在 typeahead 看到
    )
  },
)
```

**Frontmatter 解析**（`src/skills/loadSkillsDir.ts:255-258`）：

```typescript
disableModelInvocation: parseBooleanFrontmatter(
  frontmatter['disable-model-invocation'],
),
```

**內建範例：`batch`、`debug`、`skillify`**（`src/skills/bundled/`）：

```typescript
// batch.ts:108-109
userInvocable: true,
disableModelInvocation: true,

// debug.ts:21-24
// disableModelInvocation so that the user has to explicitly request it in
// interactive mode and so the description does not take up context.
disableModelInvocation: true,
userInvocable: true,

// skillify.ts:177-178
userInvocable: true,
disableModelInvocation: true,
```

---

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | Use Case | 能否成功？ | 原因 |
|---|---------|-----------|------|
| 1 | 使用者手動 `/skill-a` | ✅ 可以 | `processSlashCommand` 不檢查 `disableModelInvocation` |
| 2 | 模型透過 SkillTool 呼叫 | ❌ 不行 | 防線一 + 防線二 |
| 3 | Skill B prompt 叫模型去呼叫 Skill A | ❌ 不行 | 走的是 SkillTool 路徑 |
| 4 | Skill B prompt 提示使用者手動 `/skill-a` | ✅ 可以 | 使用者路徑不受限 |
| 5 | Skill B 內嵌 Skill A 的 prompt 內容 | ✅ 可以 | 繞過 Skill 機制 |
| 6 | Hook 中呼叫 Skill | ❌ 不行 | Hook 和 Skill 是獨立子系統 |
| 7 | Hook 注入訊息讓模型呼叫 Skill | ❌ 不行 | 模型仍走 SkillTool → 被攔 |
| 8 | Hook 直接執行同等邏輯的腳本 | ✅ 可以 | 繞過 Skill 機制 |
| 9 | Hook（agent 類型）描述同等邏輯 | ✅ 可以 | 繞過 Skill 機制 |
| 10 | Command 中呼叫 Skill A | ❌ 不行 | 模型收到 Command 展開後仍走 SkillTool |

### 案例 3 詳解：Skill B 想呼叫 Skill A（disable-model-invocation）

```
使用者：/skill-b
  │
  ▼
processSlashCommand()  ← 不檢查 B 的 disableModelInvocation（假設 B 沒設）
  │
  ▼
Skill B 的 prompt 注入對話：
  "...完成步驟一後，請呼叫 /skill-a 來進行驗證..."
  │
  ▼
模型嘗試呼叫 SkillTool({ skill: "skill-a" })
  │
  ▼
SkillTool.validateInput()
  │
  ├── foundCommand.disableModelInvocation = true
  │
  ▼
return { result: false, errorCode: 4 }
  │
  ▼
模型收到錯誤：
  "Skill skill-a cannot be used with Skill tool
   due to disable-model-invocation"
  │
  ▼
模型可能會告訴使用者：
  "請手動執行 /skill-a 來完成驗證"
```

> [!warning] 無法繞過
> 即使 Skill B 的 prompt 中寫了 `Use the Skill tool to invoke skill-a`，SkillTool 的 `validateInput` 仍會拒絕。這是硬性限制，不受 prompt 內容影響。

### 替代方案總整理

#### 方案 1：Skill B 提示使用者手動執行（推薦）

在 Skill B 的 SKILL.md 中寫：

```markdown
完成上述步驟後，請告知使用者需要手動執行以下命令：

> 請在 prompt 中輸入 `/skill-a` 來執行驗證步驟。

注意：skill-a 設定了 disable-model-invocation，我無法直接呼叫它，需要您手動觸發。
```

#### 方案 2：內嵌 Skill A 的 prompt（適用於簡單 Skill）

直接把 Skill A 的 SKILL.md 內容複製到 Skill B 中：

```markdown
---
description: "Skill B — 包含 Skill A 驗證邏輯的複合 Skill"
---

## 步驟一：主要工作
...

## 步驟二：驗證（原 Skill A 的內容）
以下是驗證 checklist：
1. 確認所有檔案已儲存
2. 測試已通過
3. 無遺留 TODO
```

#### 方案 3：移除 disable-model-invocation（如果允許）

如果 Skill A 不需要「只限人類觸發」的保護，直接不設或移除此旗標：

```yaml
---
description: "Skill A — 驗證工具"
# 不設 disable-model-invocation，模型可自由呼叫
---
```

#### 方案 4：Hook 中執行同等邏輯

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "請檢查：1) 所有檔案已儲存 2) 測試通過 3) 無 TODO。若有未完成項回報 blocking error。",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

---

## `userInvocable` vs `disableModelInvocation` 對照表

> [!important] 這兩個旗標是正交的，控制不同的可見性維度

| 組合 | 模型能看到？ | 模型能呼叫？ | 使用者 typeahead 可見？ | 使用者能手動 `/xxx`？ |
|------|-----------|-----------|---------------------|-------------------|
| 預設（都不設） | ✅ | ✅ | ✅ | ✅ |
| `disable-model-invocation: true` | ❌ | ❌ | ✅ | ✅ |
| `user-invocable: false` | ✅ | ✅ | ❌（isHidden=true） | ✅（知道名字即可） |
| 兩者都設 | ❌ | ❌ | ❌ | ✅（知道名字即可） |

> [!note] `user-invocable` 預設為 `true`
> 來源 `loadSkillsDir.ts:216-219`：`frontmatter['user-invocable'] === undefined ? true : parseBooleanFrontmatter(...)`

---

## 我的心得（My Takeaways）

1. **`disable-model-invocation` 的設計意圖很明確**：某些高影響力操作（批量修改、啟用 debug、自動建立 Skill）需要人類明確意圖。這不是限制，是安全設計
2. **兩道防線是 Defense in Depth**：第一道「看不到」是最有效的防護（模型不會主動呼叫不知道的東西），第二道「猜到也不行」是兜底
3. **如果你需要 Skill 間串接，不要在被呼叫的 Skill 上設 `disable-model-invocation`**。這個旗標的語意就是「只有人類能觸發」
4. **Hook 和 Skill 是兩個完全獨立的世界**。Hook 透過 stdin/stdout JSON 管道與 Claude Code 通訊；Skill 透過 SkillTool 或 processSlashCommand 路徑。兩者沒有交叉呼叫的 API

## 待補充（Open Questions）

- `disableModelInvocation` 是否影響 subagent（`context: fork`）的行為？Fork 子 agent 是否也被阻擋？需追蹤 `executeForkedSkill()` 的檢查邏輯（建議搜尋：`executeForkedSkill disableModelInvocation`）
- 如果 Plugin 註冊了一個 `disableModelInvocation: true` 的 Skill，是否仍出現在 `getSlashCommandToolSkills()` 中？`loadedFrom === 'plugin'` 的條件是否與 `disableModelInvocation` 條件互斥？（建議搜尋：`getSlashCommandToolSkills plugin disableModelInvocation`）
- MCP Skill（`loadedFrom === 'mcp'`）是否支援 `disableModelInvocation`？`getMcpSkillCommands()` 明確過濾 `!cmd.disableModelInvocation`，但 MCP Server 是否有辦法在註冊時設定此欄位？（建議搜尋：`mcp skill disableModelInvocation register`）
- 是否有 API 或 SDK 層級的方式讓 Hook 觸發 Skill？例如透過 `callback` 類型的 Hook 存取 `AppState` 後呼叫 `processPromptSlashCommand()`？（建議搜尋：`HookCallbackContext processPromptSlashCommand`）
- `userInvocable: false` + `disableModelInvocation: true` 的組合在實際場景中有什麼用途？一個完全隱藏且模型不能呼叫的 Skill，只有知道名字的使用者能用——是否用於內部工具或除錯？（建議搜尋：`userInvocable false disableModelInvocation true use case`）

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | ① `disable-model-invocation` 有兩道防線 ② `getSkillToolCommands` 過濾模型清單 ③ `validateInput` errorCode 4 硬性拒絕 ④ `processSlashCommand` 不檢查此旗標 ⑤ `userInvocable` 和 `disableModelInvocation` 是正交的 |
| **理解（半被動）** | 解釋概念的含義及關聯 | `disable-model-invocation` 將 Skill 的呼叫路徑分為兩條：模型路徑（SkillTool → validateInput → 拒絕）和使用者路徑（processSlashCommand → 直接執行）。兩條路徑在 `commands.ts` 中由不同的過濾函式控制，共享相同的 `Command` 資料結構但施加不同的存取控制 |
| **分析（主動）** | 批判性思維 | ① `getSlashCommandToolSkills` 刻意包含 `disableModelInvocation` 的 Skill 暴露了設計意圖——這不是忘記過濾，是有意為之，讓使用者知道這些 Skill 存在 ② `processSlashCommand` 完全不檢查此旗標意味著：任何知道 Skill 名字的使用者都能執行，安全邊界是「模型不能自主觸發」而非「完全禁止執行」 |
| **應用（主動）** | 將理論轉為行動 | ① **立即可做**：為自己的 Skill 決定是否需要 `disable-model-invocation`——如果 Skill 有破壞性操作（如批量修改、刪除），加上此旗標 ② **設計複合 Skill**：如果需要 A→B 串接，把 A 的 prompt 直接內嵌到 B，避免跨 Skill 呼叫限制 ③ **用 Hook agent 替代 Skill**：如果需要在 Stop 時自動驗證，用 agent hook 而非試圖呼叫 Skill |
| **評估（主動）** | 判斷多個方案的優劣 | 跨 Skill 呼叫的三種方案比較：(a) 提示使用者手動執行——最安全但中斷工作流程 (b) 內嵌 prompt——簡單但會膨脹 Skill 大小和 token 消耗 (c) 移除 disable-model-invocation——最靈活但失去安全防護。選擇取決於 Skill 的風險等級：高風險用 (a)，低風險用 (c)，中等用 (b) |

### 分析型追問（Socratic Follow-up）

- **澄清**：「模型不能呼叫」的精確邊界是什麼？如果模型在回應中寫出 `/skill-a` 的純文字，使用者看到後複製貼上執行，算是繞過了嗎？
- **假設**：本設計假設使用者的手動觸發等同於明確意圖。但如果使用者盲目跟從 AI 的建議打 `/batch`，這個假設是否仍然成立？
- **證據**：目前只看到 `debug`、`batch`、`skillify` 三個內建 Skill 使用此旗標。是否有社群 Skill 或 Plugin 大量使用？需要更多實證
- **觀點**：若站在自動化優先的角度，`disable-model-invocation` 是否過於保守？自動批量操作（batch）在 CI/CD 場景中不需要人類確認
- **後果**：若未來 Claude Code 支援 Skill 間的直接呼叫 API（繞過 SkillTool），`disable-model-invocation` 的語意需要重新定義——是禁止「模型自主呼叫」還是禁止「所有非人類觸發」？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 如果開發者忘記在高破壞性 Skill 上設 `disable-model-invocation`，模型可能在不適當的時機自主觸發。例如模型判斷需要批量修改，呼叫了未保護的 Skill，導致大量檔案被修改且無法 undo
2. **什麼情況下會失敗？** — (a) 使用者盲目跟從 AI 建議手動執行高風險 Skill（`disable-model-invocation` 防模型不防人）(b) Skill 的 prompt 內容被另一個 Skill 內嵌後，失去了原始 Skill 的版本控制——A 更新了 B 不知道 (c) MCP Skill 可能無法設定此旗標，安全邊界不一致
3. **有沒有更好的替代方案？** — 更精細的權限系統：不是二元的「模型能/不能呼叫」，而是「模型需要使用者確認後才能呼叫」。類似現有的 Permission 機制（ask/allow/deny），讓使用者在 Skill 觸發前確認而非完全阻擋。Claude Code 的 `PermissionRequest` Hook 已有此能力，但尚未與 Skill 系統整合

---

## 相關連結（Related）

- [[2026-04-17-CLAUDE-CODE-SKILL-COMPLETE-GUIDE-LOADING-COMPACTION-WRITING-TIPS]] — Skill 完整指南，涵蓋載入機制和壓縮策略，本文補充 disable-model-invocation 的內部原理
- [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] — Skill frontmatter 進階欄位（fork/agent/hooks），本文補充 disable-model-invocation 和 userInvocable
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — Skills/Commands/Subagents 完整比較，本文深入 Skill 可見性控制
- [[2026-04-29-CLAUDE-CODE-HOOK-API-SOURCE-DEEP-DIVE]] — Hook API 完整解析，說明 Hook 為何無法直接呼叫 Skill
- [[2026-01-25-CLAUDE-CODE-MOST-UNDERRATED-FEATURE-HOOKS]] — Hook 入門指南，本文分析 Hook 與 Skill 的交叉呼叫限制
- [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]] — Settings 層級指南，本文涉及 Skill 設定的載入路徑

## References

- 反編譯原始碼：`src/commands.ts`（`getSkillToolCommands`, `getSlashCommandToolSkills`）
- Skill 載入：`src/skills/loadSkillsDir.ts`（frontmatter 解析）
- SkillTool 驗證：`src/tools/SkillTool/SkillTool.ts:412-418`（validateInput 第二道防線）
- SkillTool prompt 建構：`src/tools/SkillTool/prompt.ts`（skill_listing 使用 getSkillToolCommands）
- skill_listing attachment：`src/utils/attachments.ts:2677`（注入 system-reminder）
- 使用者 slash command 處理：`src/utils/processUserInput/processSlashCommand.tsx:309`
- 內建範例：`src/skills/bundled/batch.ts`, `debug.ts`, `skillify.ts`
- Command 型別定義：`src/types/command.ts:189-190`（`disableModelInvocation`, `userInvocable`）
