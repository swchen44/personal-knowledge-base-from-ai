---
title: "Claude Code Skill 完全指南：從原始碼追蹤載入、注入、壓縮到撰寫技巧的全面研究"
date: 2026-04-17
category: DevTools
tags:
  - "#devtools/claude-code"
  - "#ai/prompt-engineering"
  - "#devtools/configuration"
  - "#ai/context-engineering"
source: "conversation"
source_type: article
author: "swchen44 + Claude"
status: notes
links:
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]]"
  - "[[2026-04-17-CLAUDEMD-MYTHS-DEBUNKED-SOURCE-CODE-VERIFICATION]]"
  - "[[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]]"
---

## 摘要（Summary）

基於 Claude Code 反編譯原始碼的多 session 深度研究，完整整理 Skill 系統的全生命週期：**載入機制**（閉包捕獲 + chokidar 熱載入）、**Token 注入策略**（索引 1% + 按需注入完整內容）、**壓縮後保留機制**（invoked_skills 截斷重注入）、**撰寫技巧**（7 個原始碼驗證的最佳實踐），以及**常見迷思修正**。本文是跨 4 篇知識庫筆記研究成果的綜合版，適合作為 Skill 開發的**單一參考手冊**。

## 關鍵洞察（Key Insights）

- **Skill 內容在載入時就被閉包（Closure）捕獲**，不是每次呼叫從磁碟讀取。chokidar 監控清除 memoize 快取後才整體重新載入 — 參見 [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]
- **Token 按需注入**：skill_listing 只放 name+description（佔上下文 1%），完整 SKILL.md 內容只在呼叫時才注入，節省 ~97% Token
- **壓縮後 skill_listing ❌ 不重新注入**（刻意設計），但 **invoked_skills ✅ 截斷版重新注入**（每個 5K tokens，總計 25K，最多 ~5 個）
- **指名呼叫比自動發現更可靠**：原始碼支援 `nested-skill`（`queryDepth > 0`），壓縮後 skill_listing 消失但指名指令仍在 invoked_skills 中

## 詳細內容（Details）

### 一、Skill 載入機制

#### 1.1 閉包捕獲（非 Lazy Loading）

```
 啟動 / chokidar 清除快取後
   │
   ▼
 getSkillDirCommands(cwd)  ← memoize
   │
   └── loadSkillsFromSkillsDir()
         │
         ├── fs.readFile(SKILL.md)     ← 讀完整檔案到記憶體
         ├── parseFrontmatter()        ← 分離 YAML + 內容
         └── createSkillCommand({
               markdownContent,        ← 內容封裝進閉包
             })
               └── getPromptForCommand(args) {
                     // 從閉包取出，不再讀磁碟
                     return markdownContent
                   }
```

> [!warning] 勘誤
> 初版研究誤以為「skill 內容每次呼叫從磁碟讀取（lazy loading）」。經追蹤原始碼確認為**閉包捕獲 + chokidar 觸發整體重新載入**。

#### 1.2 chokidar 熱載入

```
 檔案變更 → chokidar 偵測（含 symlink）
   → 300ms debounce
   → clearSkillCaches() + clearCommandsCache()
   → 下次存取時從磁碟整體重新載入
```

對比 CLAUDE.md（無 chokidar，需 `--resume` 刷新）。

#### 1.3 載入層架構圖

```
┌─────────────────────────────────────────────────────────┐
│  loadAllCommands(cwd)  ← memoize 層 1                   │
│    │                                                     │
│    ▼                                                     │
│  getSkillDirCommands(cwd) ← memoize 層 2                │
│    │                                                     │
│    ▼                                                     │
│  loadSkillsFromSkillsDir()                              │
│    → fs.readFile(SKILL.md)                              │
│    → createSkillCommand() → markdownContent 進入閉包     │
│                                                         │
│  chokidar 觸發時清除：層 1 + 層 2 + 索引全部清除          │
└─────────────────────────────────────────────────────────┘
```

### 二、Token 注入策略（按需注入）

#### 2.1 兩階段注入

```
 階段 1：索引注入（每次 API call）
   formatCommandsWithinBudget()
   → name + description（最多 250 字/條）
   → 預算：上下文 1%（200K → 8,000 字元）
   → Token 消耗：~1,000（50 個 skills）

 階段 2：完整內容注入（呼叫時）
   SkillTool.call() → getPromptForCommand()
   → 從閉包取出完整 SKILL.md
   → Token 消耗：~750（3,000 字 skill）

 節省率：~97%
```

#### 2.2 索引超出預算的三級降級

```
 策略 1：完整描述（≤250 字/條）
   ↓ 超出
 策略 2：截斷描述（bundled 不截）
   ↓ maxDescLen < 20
 策略 3：只放名稱（bundled 例外）
```

### 三、壓縮後的 Skill 保留機制

#### 3.1 兩種 Skill 內容的壓縮行為

| 內容 | 壓縮後 | 原因 |
|------|-------|------|
| **skill_listing**（索引） | ❌ 不重新注入 | 省 ~4K tokens；SkillTool 仍在 schema |
| **invoked_skills**（已呼叫的完整內容） | ✅ 截斷版重新注入 | `createSkillAttachmentIfNeeded()` |

#### 3.2 invoked_skills 的預算

```
POST_COMPACT_MAX_TOKENS_PER_SKILL = 5,000    ← 每個 skill
POST_COMPACT_SKILLS_TOKEN_BUDGET = 25,000     ← 所有 skill
→ 最多 ~5 個 skills 存活
→ 按 invokedAt 排序（最近的優先）
→ 截斷保留頭部，加截斷標記
```

#### 3.3 壓縮後的 messages 結構

```
messages[0]: <system-reminder>CLAUDE.md + rules</...>   ← prependUserContext
messages[1]: 壓縮摘要
messages[2]: invoked_skills attachment                   ← 截斷版 skill
messages[3]: 最新對話
```

#### 3.4 skill_listing 何時才會重新注入

| 觸發 | 效果 |
|------|------|
| `/clear` | 重發 |
| Plugin reload / chokidar | 重發 |
| `--resume` | 抑制（transcript 中已有） |
| **壓縮** | **不重發**（刻意設計） |

#### 3.5 同一 Skill 多次呼叫

`invokedSkills` 是 Map → 同 key 覆蓋，不重複佔空間。更新 `invokedAt` 讓它在排序中更靠前。

#### 3.6 壓縮時三種 Skill 附件的完整定義與行為（2026-04-22 原始碼驗證）

> [!important] 壓縮涉及三種不同的 skill 相關附件（attachment），它們的定義、內容、觸發時機和壓縮後行為完全不同。

##### `skill_listing` — 靜態可用 Skill 清單

**定義**：系統在每個 turn 開頭檢查所有已載入的 skills，把**尚未送出過**的 skill 名稱 + 描述組成清單，注入到對話中。

**產生函式**：`getSkillListingAttachments()`（`src/utils/attachments.ts` line 2662）

**注入到對話的格式**（`src/utils/messages.ts` line 3769）：

```
<system-reminder>
The following skills are available for use with the Skill tool:

- kb-create: 讀取網頁文章或 YouTube 影片，翻譯成台灣繁體中文...
- commit: Use this skill to create git commits...
- boris: Claude Code workflow tips from Boris Cherny...
</system-reminder>
```

**每條格式**（`src/tools/SkillTool/prompt.ts` line 52-65）：

```
- {skill.name}: {skill.description} - {skill.whenToUse}
```

**預算控制**（`formatCommandsWithinBudget()`，`prompt.ts` line 70）：
- 佔 context window 的一定比例（`SKILL_BUDGET_CONTEXT_PERCENT`）
- Bundled skills（內建）**永不截斷**
- User/project/plugin skills 先嘗試完整描述，超出預算則截斷描述，極端情況只保留名稱
- `sentSkillNames` Map 追蹤已送 skill，避免重複

**壓縮後行為**：❌ **不重新注入**。`postCompactCleanup.ts` line 65-69 明確註解：

```typescript
// Intentionally NOT calling resetSentSkillNames(): re-injecting the full
// skill_listing (~4K tokens) post-compact is pure cache_creation.
```

##### `skill_discovery` — AI 驅動的動態 Skill 推薦

**定義**：根據用戶輸入內容，用 AI（Haiku）**即時判斷哪些 skill 跟當前任務相關**，推薦給模型。

**注入到對話的格式**（`src/utils/messages.ts` line 3544-3550）：

```
<system-reminder>
Skills relevant to your task:

- kb-create: 讀取網頁文章或 YouTube 影片...

These skills encode project-specific conventions.
Invoke via Skill("<name>") for complete instructions.
</system-reminder>
```

**壓縮後行為**：❌ 不重新注入（一次性推薦）。

> [!warning] 在 decompiled 版本中，`skill_discovery` 被 `feature('EXPERIMENTAL_SKILL_SEARCH')` 保護，`feature()` 永遠回傳 `false`，所以此功能是死代碼（dead code）。`prefetch.ts` 也是 stub（回傳 `null`）。

##### `invoked_skills` — 已呼叫 Skill 的截斷全文

**定義**：session 中被呼叫過的 skill 完整內容（截斷版），從 `STATE.invokedSkills` 重建。

**注入到對話的格式**（`src/utils/messages.ts` line 3679-3697）：

```
<system-reminder>
The following skills were invoked in this session.
Continue to follow these guidelines:

{截斷後的 skill 全文}
</system-reminder>
```

**壓縮後行為**：✅ **重新注入**。`postCompactCleanup.ts` line 17-20：

```typescript
// Note: We intentionally do NOT clear invoked skill content here.
// Skill content must survive across multiple compactions so that
// createSkillAttachmentIfNeeded() can include the full skill text
// in subsequent compaction attachments.
```

##### 三種附件對照表

| 面向 | `skill_listing` | `skill_discovery` | `invoked_skills` |
|------|----------------|-------------------|-------------------|
| **內容** | 所有可用 skill 的 name + description | AI 篩選的相關 skill 子集 | 已呼叫 skill 的截斷全文 |
| **觸發** | 每個 turn（有新 skill 時） | Turn 0 + turn 間 prefetch | 壓縮後重建 |
| **篩選** | 無，列出全部未送過的 | Haiku 模型判斷相關性 | 按 `invokedAt` 排序 |
| **預算** | context window 比例 | 固定條數 | 5K/個，總 25K |
| **壓縮後** | ❌ 消失且不重建 | ❌ 消失 | ✅ 截斷重新注入 |
| **本 repo** | ✅ 活躍 | ❌ 死代碼 | ✅ 活躍 |

#### 3.7 SkillTool Schema 與 skill_listing 的關係

> [!note] 常見誤解
> 「自訂 skill 是否出現在 API 的 `tools` 陣列中？」——**不是**。

API 的 `tools` 參數中只有**一個**工具叫 `Skill`：

```json
{
  "tools": [
    { "name": "Read", ... },
    { "name": "Edit", ... },
    { "name": "Bash", ... },
    { "name": "Skill",
      "input_schema": { "skill": "string", "args": "string" }
    }
  ]
}
```

`Skill` 工具的 prompt（`src/tools/SkillTool/prompt.ts` line 173-195）告訴模型語法和用法，但**不包含具體有哪些 skill 可選**。具體清單完全靠 `skill_listing` 在對話訊息中提供。

```
SkillTool Schema（tools 參數）     skill_listing（對話訊息）
┌──────────────────────────┐   ┌──────────────────────────┐
│ 告訴模型：                │   │ 告訴模型：                │
│ 「你有 Skill 這個工具」    │   │ 「目前有這些 skill 可選」  │
│ 「語法：Skill("name")」   │   │ 「kb-create、commit...」  │
│                          │   │                          │
│ 每次 API call 都帶  ✅    │   │ 只在對話歷史中  ❌         │
│ 壓縮不影響               │   │ 壓縮後消失且不重建         │
└──────────────────────────┘   └──────────────────────────┘
```

**壓縮後的實際效果**：模型知道「我可以呼叫 `Skill("某個名字")`」，但**不知道可以填什麼名字**——除非用戶明確指名（如 `/kb-create`），或 `invoked_skills` 中的截斷內容提到了其他 skill 名稱。

#### 3.8 壓縮後 `sentSkillNames` 不重置的原始碼證據

兩處程式碼確認這是**刻意設計**：

**`postCompactCleanup.ts` line 65-69**：

```typescript
// Intentionally NOT calling resetSentSkillNames(): re-injecting the full
// skill_listing (~4K tokens) post-compact is pure cache_creation. The
// model still has SkillTool in schema, invoked_skills preserves used
// skills, and dynamic additions are handled by skillChangeDetector /
// cacheUtils resets. See compactConversation() for full rationale.
```

**`compact.ts` line 526-531**：

```typescript
// Intentionally NOT resetting sentSkillNames: re-injecting the full
// skill_listing (~4K tokens) post-compact is pure cache_creation with
// marginal benefit. The model still has SkillTool in its schema and
// invoked_skills attachment (below) preserves used-skill content.
```

官方權衡：重新注入 ~4K tokens 的 listing 是「純粹的 cache 建立成本」，而壓縮後模型仍可透過三種途徑呼叫 skill：
1. **用戶指名**：`/my-skill` → 模型看到文字直接呼叫
2. **invoked_skills 中的交叉引用**：skill A 內容提到 `/skill-B`
3. **SkillTool schema 仍在**：模型知道工具存在，只是不知道選項

> [!tip] **實務建議**：在 CLAUDE.md 中寫觸發條件（如「當用戶提到 XX 時，呼叫 `/my-skill`」），壓縮後 CLAUDE.md 會被 `prependUserContext` 重新注入，等於間接恢復了 skill 的可發現性（discoverability）。

### 四、Skill Frontmatter 完整欄位

```yaml
---
# 基本
name: my-skill
description: "做什麼用的"
when_to_use: "觸發提示"

# 執行控制
context: fork               # fork | 省略=inline
agent: Explore              # 搭配 fork
model: claude-sonnet-4-6
effort: high
shell: bash

# 工具與安全
allowed-tools: ["Bash(npm *)"]
disable-model-invocation: false
user-invocable: true

# 條件觸發
paths: ["src/components/**"]

# 參數
arguments: ["query"]
argument-hint: "<query>"

# Hooks（呼叫後註冊到 session，持續到結束）
hooks:
  PostToolUse:
    - matcher: "Write"
      hooks:
        - type: command
          command: "eslint --fix ${TOOL_INPUT_file_path}"
---
```

### 五、Inline vs Fork 執行模式

```
┌──────────────────┬──────────────────────┬──────────────────────┐
│                  │    Inline（預設）      │   Fork（context:fork）│
├──────────────────┼──────────────────────┼──────────────────────┤
│ 上下文            │ 共享主對話            │ 獨立隔離              │
│ 工具集            │ 主模型全部            │ agent 定義            │
│ 結果回傳          │ 注入對話              │ 只回傳摘要            │
│ Token 消耗        │ 佔用主上下文          │ 獨立計算              │
│ 適用場景          │ 需要修改檔案          │ 純研究/分析           │
└──────────────────┴──────────────────────┴──────────────────────┘
```

### 六、Skill Hooks 的累積特性

> [!important] Hooks 在呼叫後持續存在直到 session 結束
> 不是一次性的。呼叫其他 skill 不會清除。多個 skill 的 hooks 會累積。

```
/lint-on-save ← 註冊 PostToolUse hook
  ↓
Edit 檔案 ← hook 觸發
  ↓
/kb-create ← hook 仍然存在
  ↓
Write 檔案 ← hook 仍然觸發
  ↓
/exit ← 全部清除
```

唯一例外：`once: true` 的 hook 在第一次成功後自動移除。

### 七、`when_to_use` 的寫法（官方原始碼指引）

官方 `skillify.ts` 的唯一要求：`Start with "Use when..." and include trigger phrases`

12 個官方 bundled skill 統計：
- 83% 只寫正面（`Use when...`）
- 8% 正面 + 單句反例（`loop`：`Do NOT invoke for one-off tasks`）
- 8% 完整 TRIGGER/DO NOT TRIGGER（`claude-api`）

### 八、撰寫技巧（原始碼驗證）

> [!tip] 1. 關鍵指令放在 SKILL.md 前面
> 壓縮截斷保留頭部（`truncateToTokens` 保留前 5K tokens）。

> [!tip] 2. 控制在 5,000 tokens（~400 行）以內
> 超過會在壓縮後被截斷。

> [!tip] 3. 一個 Session 最多 ~5 個 Skill 存活壓縮
> 長期規則放 CLAUDE.md（每次重新注入，不受限制）。

> [!tip] 4. 壓縮後 skill_listing 消失
> 在 CLAUDE.md 中寫觸發條件作為備援。

> [!tip] 5. 指名呼叫比自動發現更可靠
> `使用 /kb-create 完成下一步` 比依賴 description 匹配更確定。原始碼支援 `nested-skill`。

> [!tip] 6. 同一 Skill 不重複佔空間
> Map.set 覆蓋同 key。呼叫 10 次只佔 1 份。

> [!tip] 7. 規則存放位置決策
> ```
> 每次 API call 生效？ → CLAUDE.md
> 特定檔案時？ → 有條件 rules（paths:）
> 特定任務時？ → Skill
> 壓縮後完整存活？ → CLAUDE.md
> 強制執行？ → Settings hooks
> ```

### 九、注意事項總覽

| 注意事項 | 影響 | 對策 |
|---------|------|------|
| Skill > 5K tokens | 壓縮後截斷 | 關鍵放前面 |
| Session 用 > 5 skill | 最早的被丟棄 | 長期規則放 CLAUDE.md |
| 壓縮後 listing 消失 | 模型不主動觸發 | CLAUDE.md 寫觸發條件 / 指名呼叫 |
| Description > 250 字 | 索引截斷 | 精簡 |
| 指名呼叫在 5K 後 | 壓縮截斷 | 移到前面 |
| 循環呼叫 A→B→A | 無限循環 | 避免 |
| Fork skill 指名呼叫 | 子 agent 不一定有 SkillTool | 確認 agent |
| Plugin skill 的進階欄位 | hooks/context/agent/paths 不生效 | 複製到 .claude/skills/ |
| Hooks 累積 | 意外副作用 | 控制數量，用 once:true |

### 十、Skill 完整生命週期圖

```
 Session 啟動
   ├── getSkillDirCommands() → memoize → 閉包捕獲所有 SKILL.md
   ├── skill_listing 注入 → name+desc（~1% token）
   │
   ▼
 模型決定呼叫 /my-skill
   ├── Inline: 完整內容注入主對話
   │   或 Fork: 內容傳給子 agent
   ├── addInvokedSkill() → 存入 STATE
   ├── registerSkillHooks() → hooks 註冊到 session
   │
   ▼
 對話繼續（Token 累積）
   │
   ▼
 Micro-compact: 清除舊工具結果（Read/Bash/Grep）
   │
   ▼
 達到 ~83% → Auto-compact 觸發
   ├── skill_listing ❌ 不重新注入
   ├── invoked_skills ✅ 截斷重新注入（前 5K tokens）
   ├── CLAUDE.md + rules ✅ prependUserContext 重新注入
   └── hooks ✅ 仍在 session 中（不受壓縮影響）
   │
   ▼
 壓縮後
   ├── 模型仍可呼叫任何 skill（SkillTool 在 schema）
   ├── 已用 skill 規則仍在（invoked_skills attachment）
   └── 未用 skill 索引消失（但可按名稱呼叫）
   │
   ▼
 chokidar 偵測 SKILL.md 變更
   → 清除 memoize 快取
   → 下次存取時重新載入
   │
   ▼
 Session 結束
   └── clearSessionHooks() → 所有 skill hooks 清除
```

## 我的心得（My Takeaways）

1. **Skill 的「按需」不在磁碟 I/O，在 Token 注入**。閉包捕獲 + 索引 1% + 呼叫時注入 = 三層最佳化。
2. **壓縮是 Skill 設計的關鍵約束**。5K tokens/skill、~5 個存活、頭部優先截斷——這三個數字決定了你該怎麼寫 SKILL.md。
3. **指名呼叫是壓縮後的救生繩**。skill_listing 消失後，模型無法自動發現 skill。但如果 Skill A 寫了 `/skill-B`，這段文字在 invoked_skills 中仍然存在。
4. **Plugin skill 有功能缺口**。hooks/context/agent/paths 全部不生效（`createPluginCommand` 沒解析）。需要這些功能必須複製到 `.claude/skills/`。

## 待補充（Open Questions）

- `invoked_skills` 的截斷標記 `[... skill content truncated for compaction; use Read on the skill path if you need the full text]` — 模型真的會去 Read 嗎？還是忽略？建議搜尋：`truncation marker Read skill path model behavior`
- 壓縮後 `invoked_skills` attachment 中的 skill 內容是否參與下一次壓縮的摘要？還是也被 `stripReinjectedAttachments()` 移除？建議搜尋：`stripReinjectedAttachments invoked_skills compact`
- `nested-skill`（skill 中呼叫 skill）有沒有深度限制？`queryDepth` 最多可以到多少？建議搜尋：`queryDepth max nested skill limit`
- 如果 5 個 skill 都很大（各 5K tokens = 25K），加上 CLAUDE.md（messages[0]）和壓縮摘要，壓縮後的總 Token 會不會再次超過閾值觸發二次壓縮？建議搜尋：`recompaction invoked_skills double compact`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確立基礎知識 | `SKILL_BUDGET = 1%`、`MAX_LISTING_DESC = 250`、`POST_COMPACT_MAX_TOKENS_PER_SKILL = 5,000`、`addInvokedSkill()`、`prependUserContext()`、`nested-skill`、`createSkillCommand` 閉包 |
| **理解（半被動）** | 串聯知識點 | Skill 有三層 Token 最佳化：索引（1%）→ 閉包（啟動讀取）→ 注入（呼叫時）。壓縮時 skill_listing 消失但 invoked_skills 保留前 5K，CLAUDE.md 每次重新注入。指名呼叫繞過 listing 消失。 |
| **分析（主動）** | 找出假設 | 「~5 個 skill 存活」假設每個都用滿 5K，但大多數 skill 遠小於 5K → 實際可能存活更多。另外假設指名呼叫在前 5K 內 → 如果放在 SKILL.md 尾部就會被截斷。 |
| **應用（主動）** | 規劃執行方案 | (1) 重新檢查所有 SKILL.md，確保關鍵指令在前 400 行內；(2) 為長 skill 加壓縮友好結構（規則在前、參考在後）；(3) 在工作流 skill 中用指名呼叫替代依賴自動發現 |
| **評估（主動）** | 判斷方案優劣 | CLAUDE.md 規則：永遠在、每次佔 Token。Skill 規則：按需但壓縮後截斷。hooks：強制執行但無法控制輸出風格。三者互補：行為準則用 CLAUDE.md、任務流程用 Skill、格式強制用 hooks。 |

### 方案批判三問

1. **最大的風險是什麼？** — 過度依賴 Skill 的壓縮後保留，但 5 個上限可能導致關鍵 skill 被丟棄。
2. **什麼情況下會失敗？** — (a) 1M context 模型下壓縮很少觸發，invoked_skills 機制幾乎不啟用；(b) skill 超過 400 行，關鍵指令被截斷；(c) fork skill 中指名呼叫，但子 agent 沒有 SkillTool。
3. **有沒有更好的替代方案？** — 對於「必須永遠遵守」的規則，CLAUDE.md 比 Skill 更可靠（`prependUserContext` 每次重新注入，無截斷上限）。Skill 適合「可選的工作流程」而非「強制的行為規範」。

## 相關連結（Related）

- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — Skill 閉包捕獲 + chokidar 的原始碼驗證，以及 CLAUDE.md/@include/Rules 的完整載入機制
- [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] — Frontmatter 進階欄位（fork/agent/hooks）+ Plugin Bug + 命名防護 + 企業部署
- [[2026-04-17-CLAUDEMD-MYTHS-DEBUNKED-SOURCE-CODE-VERIFICATION]] — 社群迷思核實（CLAUDE.md 是 User Message、壓縮後重新注入、rules 按需載入真相）
- [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]] — Skills 官方文件整理
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — Skills/Commands/Subagents 完整比較
- [[2026-01-27-KARPATHY-GUIDELINES-VS-CLAUDE-CODE-BUILTIN-SYSTEM-PROMPT]] — Karpathy 準則 vs 內建 prompt 的重疊分析
- [[2026-04-18-CLAUDE-CODE-TOKEN-QUOTA-THREE-TRAPS-AND-FIXES]] — 額度管理實戰，建議把規則從 CLAUDE.md 移到 Skill 降低起始成本
- [[2026-04-19-CLAUDE-CODE-PLUGIN-JSON-DEPENDENCIES-SHARED-SKILLS-SOURCE-ANALYSIS]] — Plugin manifest 的 skills 欄位如何補充預設 skills/ 目錄的載入邏輯
- [[2026-04-29-CLAUDE-CODE-DISABLE-MODEL-INVOCATION-SKILL-VISIBILITY-SOURCE-ANALYSIS]] — disable-model-invocation 雙道防線原始碼解析：模型清單過濾 + validateInput 硬性拒絕，跨 Skill 呼叫限制

## References

- Claude Code 反編譯原始碼（基於 v2.1.88 source map 洩漏版本）
- 關鍵檔案：
  - `src/skills/loadSkillsDir.ts` — Skill 載入、閉包捕獲、frontmatter 解析
  - `src/tools/SkillTool/SkillTool.ts` — Inline/Fork 分岔、nested-skill 追蹤
  - `src/tools/SkillTool/prompt.ts` — Token 預算（1%）、三級降級
  - `src/services/compact/compact.ts` — invoked_skills 壓縮保留（5K/25K）
  - `src/services/compact/postCompactCleanup.ts` — 刻意不重置 sentSkillNames
  - `src/utils/api.ts` — `prependUserContext()` 每次 API call 重新注入
  - `src/utils/forkedAgent.ts` — Fork 隔離環境建立
  - `src/utils/hooks/registerSkillHooks.ts` — Hooks 累積註冊到 session
  - `src/bootstrap/state.ts` — `addInvokedSkill()` Map 覆蓋機制
