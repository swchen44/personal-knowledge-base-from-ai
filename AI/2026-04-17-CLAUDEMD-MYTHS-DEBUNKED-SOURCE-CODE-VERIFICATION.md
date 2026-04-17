---
title: "CLAUDE.md 社群迷思原始碼核實：User Message 注入、Rules 按需載入、壓縮後重新注入的真相"
date: 2026-04-17
category: AI
tags:
  - "#ai/claude-code"
  - "#ai/prompt-engineering"
  - "#devtools/configuration"
  - "#ai/context-engineering"
source: "conversation"
source_type: article
author: "swchen44 + Claude"
status: notes
links:
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
  - "[[2026-01-27-KARPATHY-GUIDELINES-VS-CLAUDE-CODE-BUILTIN-SYSTEM-PROMPT]]"
  - "[[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]]"
  - "[[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]]"
---

## 摘要（Summary）

社群流傳一篇 CLAUDE.md 最佳化指南，主張「35 行 CLAUDE.md 比 100 行表現更好」、「CLAUDE.md 是 User Message 不是 System Prompt」、「rules 按需注入所以效果更強」。本文**逐條比對 Claude Code 反編譯原始碼**（`api.ts`、`query.ts`、`claudemd.ts`、`autoCompact.ts`），驗證 8 項聲明的真偽。核心發現：**CLAUDE.md 確實是 User Message（透過 `createUserMessage`），但被 `<system-reminder>` tag 包裹，非普通 user message**；**無條件 rules 與 CLAUDE.md 注入位置完全相同**（只有加 `paths:` 的才真正按需）；**壓縮後 CLAUDE.md 和所有 rules 都會透過 `prependUserContext()` 重新注入**。

## 關鍵洞察（Key Insights）

- **CLAUDE.md 是 User Message，但不是普通的**：透過 `createUserMessage({ isMeta: true })` 注入為 `messages[0]`，被 `<system-reminder>` 包裹。模型對此 tag 的遵守程度介於 system prompt 和普通 user message 之間 — 參見 [[CLAUDE-CODE-CONTEXT-ENGINEERING]]
- **壓縮後會重新注入**：`prependUserContext()` 在**每次 API call** 都會執行（`query.ts:660`），壓縮只替換 messages，不影響 `userContext` 快取
- **無條件 rules 跟 CLAUDE.md 完全一樣**：都在 `getMemoryFiles()` → `getUserContext()` → `prependUserContext()` 的同一條路徑上，**注入位置相同**
- **只有 `paths:` rules 才是真正按需**：透過 `FileReadTool` → `nested_memory` attachment 注入在最新位置
- **「35 行比 100 行好」的真正原因是砍掉了與內建 prompt 重疊的規則**，不是「拆去 rules/」的功勞

## 詳細內容（Details）

### 一、社群文章 8 項聲明逐條核實

#### 核實結果總覽

| # | 聲明 | 結果 | 修正 |
|---|------|------|------|
| 1 | CLAUDE.md 是 User Message | ✅ 正確 | 但被 `<system-reminder>` 包裹，非普通 user message |
| 2 | 被 auto memory/MCP/skills 淹沒 | ⚠️ 半對 | 固定在 messages[0]，不會被「蓋掉」，但離焦點遠 |
| 3 | Recency Bias | ✅ 正確 | LLM 已知現象，但 `<system-reminder>` 有緩解 |
| 4 | Attention Dilution | ✅ 正確 | Anthropic 的 `SKILL_BUDGET = 1%` 設計也遵循此原則 |
| 5 | Instruction Drift | ✅ 正確 | 但非 CLAUDE.md 特有問題 |
| 6 | 壓縮時消失 | ❌ **不正確** | 壓縮後 `prependUserContext()` 會**重新注入** |
| 7 | rules 按需注入更強 | ❌ **嚴重誤導** | 只有 `paths:` 的才按需，無條件 rules 跟 CLAUDE.md 完全一樣 |
| 8 | 35 行 > 100 行 | ⚠️ 合理但歸因錯誤 | 真正原因是減少與內建 prompt 重疊的內容 |

### 二、CLAUDE.md 的注入機制（原始碼驗證）

```typescript
// api.ts:461-473 — CLAUDE.md 被包在 <system-reminder> 中，作為第一個 user message
return [
    createUserMessage({
        content: `<system-reminder>
As you answer the user's questions, you can use the following context:
# claudeMd
${CLAUDE.md 內容 + 無條件 rules 內容}

IMPORTANT: this context may or may not be relevant to your tasks.
</system-reminder>`,
        isMeta: true,  // ← UI 中不顯示
    }),
    ...messages,  // ← 用戶的實際對話
]
```

```
 API call 的完整 messages 結構：
 
 systemPrompt: [內建 prompts.ts 的內容 + git status]  ← 真正的 system prompt
 messages[0]:  <system-reminder>CLAUDE.md + rules/*</...>  ← User Message（meta）
 messages[1]:  用戶第一個問題
 messages[2]:  assistant 回覆
 messages[3]:  skill_listing / attachments
 ...
 messages[N]:  最新的對話
```

> [!important] `<system-reminder>` 的特殊地位
> 雖然技術上是 user message，但 `<system-reminder>` 是 Claude 模型訓練時的特殊 tag。模型對此內容的遵守程度**高於**普通 user message，但**低於** system prompt。不等同於「被當作普通訊息忽略」。

### 三、壓縮後的重新注入機制

> [!warning] 社群文章最大的錯誤
> 原文說「壓縮時 CLAUDE.md 細節會消失」。事實上壓縮後 `prependUserContext()` 會**重新注入完整的 CLAUDE.md + 無條件 rules**。

```
 壓縮前：
 messages[0]: <system-reminder>CLAUDE.md + rules</...>
 messages[1-N]: 長對話...
 
 壓縮時：
 autoCompactIfNeeded() → compactConversation()
   → messagesForQuery = postCompactMessages（摘要替換舊對話）
 
 壓縮後的下一次 API call（query.ts:660）：
 messages = prependUserContext(postCompactMessages, userContext)
   → messages[0]: <system-reminder>CLAUDE.md + rules</...>  ← 重新注入！
   → messages[1]: 壓縮摘要
   → messages[2]: 最新對話
```

```typescript
// query.ts:660 — 每次 API call 都會重新 prepend
for await (const message of deps.callModel({
    messages: prependUserContext(messagesForQuery, userContext),
    //        ↑ 無論壓縮與否，每次都重新注入 userContext
    systemPrompt: fullSystemPrompt,
    ...
}))
```

**CLAUDE.md、無條件 rules、有條件 rules 壓縮後的行為對比**：

| 類型 | 壓縮後重新注入？ | 機制 |
|------|---------------|------|
| CLAUDE.md | ✅ 每次 API call | `prependUserContext()`（userContext memoize） |
| 無條件 rules（無 paths:） | ✅ 每次 API call | 包含在同一個 `userContext` 中 |
| 有條件 rules（有 paths:） | ✅ 下次讀檔時 | `FileReadTool` → `nested_memory` attachment |

### 四、Rules 注入位置的真相（最關鍵修正）

```
 社群文章宣稱：
 ❌ "rules/ 是在用到的當下，插在最新位置，所以效果更強"
 
 原始碼事實：
 ┌─────────────────────────────────────────────────────────┐
 │ 無條件 rules（.claude/rules/style.md，無 paths:）       │
 │                                                         │
 │ 載入：getMemoryFiles() → 啟動時 eager + memoize         │
 │ 注入：包含在 userContext → messages[0] 的 <system-reminder> │
 │ 位置：跟 CLAUDE.md 完全相同                              │
 │                                                         │
 │ → 移去 rules/ 不加 paths: = 跟留在 CLAUDE.md 沒差       │
 └─────────────────────────────────────────────────────────┘
 
 ┌─────────────────────────────────────────────────────────┐
 │ 有條件 rules（.claude/rules/react.md，有 paths:）       │
 │                                                         │
 │ 載入：FileReadTool 觸發時 → 從磁碟讀取（非 memoize）    │
 │ 注入：nested_memory attachment → 靠近最新對話位置         │
 │ 位置：比 messages[0] 更接近模型焦點                      │
 │                                                         │
 │ → 這才是真正的「按需注入」，效果確實更強                 │
 └─────────────────────────────────────────────────────────┘
```

> [!tip] 正確的拆分策略
> ```yaml
> # ✅ 有效（加了 paths: 才有按需效果）
> # .claude/rules/react-patterns.md
> ---
> paths:
>   - "src/components/**"
>   - "src/hooks/**"
> ---
> React 元件必須使用 functional component...
> 
> # ❌ 無效（跟留在 CLAUDE.md 一樣）
> # .claude/rules/react-patterns.md（無 paths:）
> React 元件必須使用 functional component...
> ```

### 五、「35 行比 100 行好」的真正原因

文章的觀察（35 行表現更好）可能是真的，但**歸因錯誤**：

| 錯誤歸因 | 正確原因 |
|---------|---------|
| 「拆去 rules/ 按需注入」 | 無條件 rules 跟 CLAUDE.md 注入位置一樣 |
| 「rules/ 在最新位置」 | 只有 `paths:` rules 才在最新位置 |

**真正的原因**（基於我們的 Karpathy 準則比對研究）：

1. **砍掉了與 `prompts.ts` 內建重疊的規則**（如 Simplicity First、Surgical Changes 已內建）
2. **減少了 messages[0] 的長度** → 每行分到更多 attention
3. **移除了冗餘指令**（「寫乾淨 code」之類模型本來就會的）

這跟「拆去 rules/」無關，純粹是**減少總量**的效果。

### 六、CLAUDE.md 最佳化 Recap：原始碼驗證的技巧

#### 技巧 1：精簡 CLAUDE.md，只放「注意力 CP 值」最高的內容

```markdown
# 留在 CLAUDE.md 的（每次 API call 都佔 Token）
- 專案定義（1-2 行）
- 技術棧 + 版本（1 行）
- 行動原則（最重要！控制思考方式）
- 不確定就問（內建 prompt 沒有的補充）
- 目標驅動（步驟→驗證→迴圈）

# 不要寫的（已內建在 prompts.ts）
- 「不加未被要求的功能」 → prompts.ts:201 已有
- 「不為假設性需求設計」 → prompts.ts:203 已有
- 「三行比抽象好」 → prompts.ts:203 已有
- 「寫乾淨的 code」 → 模型本來就會
```

#### 技巧 2：把檔案類型相關規則加 `paths:` 變成有條件 rules

```yaml
# .claude/rules/react.md — 只在碰到 React 檔案時注入
---
paths:
  - "src/components/**"
  - "src/hooks/**"
  - "**/*.tsx"
---
React 規範：functional component、TypeScript strict...
```

```yaml
# .claude/rules/testing.md — 只在碰到測試檔案時注入
---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
---
測試規範：每個 describe 要有 setup/teardown...
```

#### 技巧 3：理解三層注入的 Token 效率

```
 效率最高                                          效率最低
 ──────────────────────────────────────────────────►
 
 有條件 rules     Skill（按需）    CLAUDE.md + 無條件 rules
 paths: ["*.tsx"]  索引 1% + 呼叫   每次 API call 都全量注入
 只在讀 .tsx 時注入  時才注入
```

#### 技巧 4：壓縮不是問題，行數才是

由於壓縮後 `prependUserContext()` 會重新注入，**壓縮不會讓 CLAUDE.md 消失**。真正的問題是：
- 每次 API call 都要佔 Token → 越短越好
- messages[0] 越長 → 每行分到的 attention 越少

#### 技巧 5：用 `--resume` 刷新 CLAUDE.md 修改

修改 CLAUDE.md 後不需要開新 session：
```bash
# 修改 CLAUDE.md
vim CLAUDE.md

# exit + resume → CLAUDE.md 重新讀取，對話歷史保留
claude --resume
```

## 我的心得（My Takeaways）

1. **社群文章的觀察可能正確，但歸因經常錯誤**。「35 行比 100 行好」是真的，但原因不是「rules 按需注入」，而是「砍掉了重疊內容」。不讀原始碼就無法區分兩者。
2. **`<system-reminder>` 是被低估的關鍵機制**。CLAUDE.md 雖然是 user message，但因為這個 tag，模型的遵守程度遠高於普通 user message。把它等同「普通聊天訊息」是嚴重低估。
3. **`paths:` 是 CLAUDE.md 最佳化的真正殺手鐗**。大多數社群文章只說「拆去 rules/」，但不提 `paths:` 這個關鍵差異。沒有 `paths:` 的 rules 跟留在 CLAUDE.md 完全一樣。
4. **壓縮後重新注入是設計，不是 bug**。`prependUserContext()` 每次 API call 都執行，確保 CLAUDE.md 永遠在 messages[0]。這是刻意的——Anthropic 認為這些指令值得每次都重新注入。

## 待補充（Open Questions）

- `<system-reminder>` tag 的遵守權重在模型訓練中具體是多少？相對 system prompt 和普通 user message 的 attention 比例？建議搜尋：`system-reminder tag training weight anthropic`
- 壓縮摘要中是否會保留「CLAUDE.md 提到的規則被遵守」的語意？如果摘要丟失了「使用 TypeScript strict」的上下文，重新注入的 CLAUDE.md 能否補回？建議搜尋：`compact summary rule preservation`
- `prependUserContext` 每次都注入完整 CLAUDE.md，是否有 prompt cache 機制避免重複計費？建議搜尋：`prompt cache prependUserContext cache_creation`
- 有條件 rules 的 `nested_memory` attachment 在壓縮時是否被保留？還是也需要下次 FileReadTool 觸發才重新注入？建議搜尋：`nested_memory compact preserve attachment`
- 如果 CLAUDE.md 超過某個 Token 閾值，`prependUserContext()` 是否會截斷？或者它總是注入完整內容？建議搜尋：`prependUserContext truncation MAX_MEMORY_CHARACTER_COUNT`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確立基礎知識 | `prependUserContext()`、`<system-reminder>`、`createUserMessage({ isMeta: true })`、`paths:` frontmatter、`nested_memory` attachment |
| **理解（半被動）** | 串聯知識點 | CLAUDE.md 是 user message 但有 `<system-reminder>` 加持；無條件 rules = CLAUDE.md 同路徑；有條件 rules = 按需注入在最新位置；壓縮後 `prependUserContext()` 每次重新注入 |
| **分析（主動）** | 找出假設 | 社群文章假設「拆去 rules/ = 按需注入」，但原始碼證明無 `paths:` 的 rules 與 CLAUDE.md 完全相同。真正的改善來自減少總量，不是注入位置。 |
| **應用（主動）** | 規劃執行方案 | (1) 精簡 CLAUDE.md 到 ~35 行核心規則；(2) 把檔案類型規則加 `paths:` 做成有條件 rules；(3) 用 Karpathy 準則比對表砍掉與內建重疊的規則 |
| **評估（主動）** | 判斷方案優劣 | 「全放 CLAUDE.md」：簡單但浪費 Token。「拆去 rules/ 不加 paths:」：跟不拆一樣。「拆去 rules/ 加 paths:」：最佳方案，按需注入省 Token + 靠近焦點。代價是要正確設定 glob 模式。 |

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 依照錯誤歸因（以為「拆去 rules/ 就好」）執行，結果無條件 rules 跟 CLAUDE.md 行為完全相同，但用戶**以為**已經最佳化了，不再進一步改善。
2. **什麼情況下會失敗？** — (a) `paths:` glob 模式設太窄，規則永遠不觸發；(b) 過度精簡 CLAUDE.md 導致關鍵規則被砍（如專案特有的安全要求）；(c) 依賴壓縮後重新注入，但在 1M context 模型下壓縮很少觸發。
3. **有沒有更好的替代方案？** — 對於「確保模型遵守規則」的需求，settings.json 中的 `hooks`（`PostToolUse` 自動 lint）比 CLAUDE.md 中的文字規則更可靠——前者是**強制執行**，後者是**建議遵守**。

## 七、Skill 壓縮後的注入機制與撰寫技巧

### 壓縮時 Skill 經歷什麼？

Skill 相關有兩種內容，壓縮時處理方式不同：

| 內容 | 壓縮後行為 | 原因 |
|------|-----------|------|
| **skill_listing**（索引：name + desc） | ❌ **不重新注入** | 省 ~4K tokens；模型仍有 SkillTool schema |
| **invoked_skills**（已呼叫的完整內容） | ✅ **截斷版重新注入** | `createSkillAttachmentIfNeeded()` |

**invoked_skills 預算限制**：

```
POST_COMPACT_MAX_TOKENS_PER_SKILL = 5,000    ← 每個 skill 截斷上限
POST_COMPACT_SKILLS_TOKEN_BUDGET = 25,000     ← 所有 skill 總預算
→ 最多保留 ~5 個 skills
→ 按呼叫時間排序（最近的優先保留）
→ 截斷保留頭部，加 "[... skill content truncated for compaction]"
```

壓縮後的 messages 結構：

```
messages[0]: <system-reminder>CLAUDE.md + rules</...>   ← prependUserContext 重新注入
messages[1]: 壓縮摘要
messages[2]: invoked_skills attachment                   ← 截斷版 skill 內容
              "The following skills were invoked in
               this session. Continue to follow
               these guidelines:
               ### Skill: kb-create
               {前 5,000 tokens 的內容}
               [... skill content truncated...]"
messages[3]: 最新對話
```

### Skill 撰寫 7 個技巧

> [!tip] 技巧 1：最重要的指令放在 SKILL.md 前面
> 壓縮截斷保留**頭部**。如果「必須用繁體中文」寫在第 200 行，壓縮後可能被截斷。把核心規則放在 frontmatter 之後的最前面。

> [!tip] 技巧 2：單個 Skill 控制在 5,000 tokens（~400 行）以內
> 超過會在壓縮後被截斷。大 skill 考慮拆分，或把參考資料放外部檔案。

> [!tip] 技巧 3：一個 Session 最多 ~5 個 Skill 在壓縮後存活
> 25K 總預算 ÷ 5K/skill ≈ 5 個。如果某規則需要整個 session 都遵守，放 CLAUDE.md（每次重新注入，不受 5 個限制）。

> [!tip] 技巧 4：壓縮後 skill_listing 消失，模型不再主動觸發
> Skill 索引不重新注入。解法：在 CLAUDE.md 中寫觸發條件（如「用戶提到『寫知識庫』時，使用 /kb-create」）。

> [!tip] 技巧 5：指名呼叫比自動發現更可靠
> 在 Skill A 中直接寫 `使用 /skill-B 完成下一步`，而非依賴模型從 skill_listing 自動匹配。原始碼支援 `nested-skill`（`queryDepth > 0`），是正式機制。
> - 繞過 skill_listing 消失的問題
> - 消除 description 匹配的不確定性
> - 壓縮後 invoked_skills 中仍保留指名指令（前提：在前 5K tokens 內）

> [!tip] 技巧 6：同一 Skill 多次呼叫不會重複佔空間
> `invokedSkills` 是 Map，相同 key 覆蓋。呼叫 10 次只佔 1 份 5K tokens。但會更新 `invokedAt` 時間戳，讓它在排序中更靠前。

> [!tip] 技巧 7：長期規則的最佳存放位置決策
> ```
>  這條規則需要...
>    ├── 每次 API call 都生效？ → CLAUDE.md 或無條件 rules
>    ├── 只在特定檔案時？ → 有條件 rules（paths:）
>    ├── 只在特定任務時？ → Skill
>    ├── 壓縮後必須完整存活？ → CLAUDE.md（永遠在 messages[0]）
>    └── 需要強制執行？ → Settings hooks（不是建議，是強制）
> ```

### Skill 撰寫注意事項

| 注意事項 | 影響 | 對策 |
|---------|------|------|
| Skill > 5K tokens | 壓縮後尾部被截斷 | 關鍵指令放前面 |
| Session 用 > 5 個 skill | 最早的被丟棄 | 長期規則放 CLAUDE.md |
| 壓縮後 skill_listing 消失 | 模型不再主動觸發 | CLAUDE.md 寫觸發條件 / 指名呼叫 |
| Description > 250 字 | 索引中被截斷 | 250 字以內 |
| Skill A 指名呼叫 B 在 5K 後 | 壓縮後截斷 | 移到 SKILL.md 前面 |
| 循環呼叫（A→B→A） | 可能無限循環 | 避免 |
| Fork skill 指名呼叫 | 子 agent 不一定有 SkillTool | 確認 agent 設定 |

### 指名呼叫 vs 自動發現的比較

```
 自動發現（依賴 skill_listing）：
 用戶需求 → 模型看索引 → 匹配 description → 決定呼叫
              壓縮後消失 ❌     可能選錯 ⚠️

 指名呼叫（Skill 內容直接寫死）：
 用戶呼叫 /A → A 內容說「用 /B」→ 模型呼叫 B
               壓縮後仍在 ✅       零歧義 ✅
```

## 相關連結（Related）

- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — CLAUDE.md 載入時機、@include、Rules 無條件/有條件注入、壓縮後行為的完整原始碼分析
- [[2026-01-27-KARPATHY-GUIDELINES-VS-CLAUDE-CODE-BUILTIN-SYSTEM-PROMPT]] — Karpathy 四準則與 prompts.ts 的逐條比對，證明 50% 規則已內建
- [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]] — Opalic 的漸進式揭露方案，提出「減少常駐、按需載入」策略
- [[2026-04-17-CLAUDE-CODE-SETTINGS-FILES-COMPLETE-GUIDE]] — settings.json hooks 可作為 CLAUDE.md 規則的強制執行替代方案
- [[2026-04-13-KARPATHY-CLAUDE-MD-WHAT-EACH-PRINCIPLE-REALLY-FIXES]] — Simplicity First 最有效的實測，支持精簡策略

## References

- Claude Code 反編譯原始碼（基於 v2.1.88 source map 洩漏版本）
- 關鍵檔案：
  - `src/utils/api.ts` — `prependUserContext()` 注入 CLAUDE.md 為 messages[0]
  - `src/query.ts` — 每次 API call 都呼叫 `prependUserContext()`（line 660）
  - `src/context.ts` — `getUserContext()` memoize（包含 CLAUDE.md + 無條件 rules）
  - `src/utils/claudemd.ts` — `getMemoryFiles()` 載入所有 CLAUDE.md + rules
  - `src/services/compact/autoCompact.ts` — 壓縮觸發閾值（~83% of 200K）
