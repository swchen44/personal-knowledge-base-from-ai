---
title: "用 Skills 擴展 Claude 能力 — Claude Code 官方文件"
date: 2026-03-19
category: AI
tags:
  - ai/claude-code
  - ai/skills
  - tools/claude
  - reference/official-docs
source: "https://code.claude.com/docs/en/skills"
source_type: official-docs
author: "Anthropic"
status: reference
links:
  - "[[2026-03-07-CLAUDE-SKILLS-2.0-THE-SELF-IMPROVING-AI-CAPABILITIES-THAT-ACTUALLY-WORK]]"
  - "[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]"
  - "[[CLAUDE-CODE-141-AGENTS-SETUP]]"
---

## Summary

Claude Code Skills 官方文件完整參考。Skills 是可重複使用的 Claude 能力擴展，透過 SKILL.md 檔案定義。支援自動觸發、手動呼叫、Fork 隔離執行、動態 context 注入等進階功能，遵循 Agent Skills 開放標準，可跨多個 AI 工具使用。

## Key Insights

- **Custom commands 已合併進 Skills** — `.claude/commands/deploy.md` 和 `.claude/skills/deploy/SKILL.md` 效果完全相同，舊檔案繼續有效
- **Description 決定自動觸發** — Claude 根據 description 決定何時載入 skill；沒有 description 則用 markdown 第一段
- **兩種呼叫控制方向** — `disable-model-invocation: true` 防止 Claude 自動觸發；`user-invocable: false` 隱藏使用者選單但 Claude 仍可呼叫
- **Skill description 有 context 預算限制** — 預算為 context window 的 2%（最少 16,000 字元），超出時部分 skill 不被載入
- **Fork 模式不會繼承對話歷史** — 適合有明確指令的任務型 skill，不適合純參考型 skill

## Details

### 內建 Bundled Skills

> [!note] 與 built-in commands 的差異
> Built-in commands 執行固定邏輯；Bundled skills 是 prompt-based，Claude 用工具動態執行，可以啟動平行 agents、讀取檔案、適應程式碼庫。

| Skill | 用途 |
|-------|------|
| `/batch <instruction>` | 大規模程式碼變更，分解成 5-30 個獨立單元，每個在隔離 git worktree 執行 |
| `/claude-api` | 載入 Claude API 參考資料（Python/TS/Java/Go 等），也可自動觸發 |
| `/debug [description]` | 讀取 session debug log 排除問題 |
| `/loop [interval] <prompt>` | 按間隔重複執行 prompt，適合輪詢部署狀態 |
| `/simplify [focus]` | 平行啟動三個 review agents 找程式碼問題並修正 |

---

### 建立第一個 Skill

```bash
# 1. 建立 skill 目錄（個人 skills，所有專案可用）
mkdir -p ~/.claude/skills/explain-code

# 2. 建立 SKILL.md
```

```yaml
---
name: explain-code
description: Explains code with visual diagrams and analogies. Use when explaining how code works, teaching about a codebase, or when the user asks "how does this work?"
---

When explaining code, always include:

1. **Start with an analogy**: Compare the code to something from everyday life
2. **Draw a diagram**: Use ASCII art to show the flow, structure, or relationships
3. **Walk through the code**: Explain step-by-step what happens
4. **Highlight a gotcha**: What's a common mistake or misconception?
```

```bash
# 3. 測試（兩種方式）
# 自動觸發
"How does this code work?"

# 直接呼叫
/explain-code src/auth/login.ts
```

---

### Skill 存放位置與優先級

| 層級 | 路徑 | 適用範圍 |
|------|------|---------|
| Enterprise | 透過 managed settings | 組織所有使用者 |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` | 你的所有專案 |
| Project | `.claude/skills/<skill-name>/SKILL.md` | 此專案限定 |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` | 啟用該 plugin 的地方 |

**優先級**：enterprise > personal > project
**Plugin namespace**：使用 `plugin-name:skill-name`，不會與其他層級衝突

> [!tip] Monorepo 支援
> 編輯 `packages/frontend/` 內的檔案時，Claude Code 也會自動尋找 `packages/frontend/.claude/skills/` 中的 skills。

---

### Skill 目錄結構

```
my-skill/
├── SKILL.md           # 主指令（必要）
├── template.md        # 範本
├── examples/
│   └── sample.md      # 範例輸出
└── scripts/
    └── validate.sh    # Claude 可執行的腳本
```

> [!important] SKILL.md 建議在 500 行以內
> 詳細參考資料移到獨立檔案，在 SKILL.md 中用連結引用，Claude 按需載入。

---

### Frontmatter 完整參考

```yaml
---
name: my-skill                    # 選填，預設用目錄名
description: 說明與觸發時機         # 強烈建議填寫
argument-hint: [issue-number]     # 自動完成提示
disable-model-invocation: true    # 防止 Claude 自動觸發
user-invocable: false             # 從 / 選單隱藏
allowed-tools: Read, Grep         # 無需確認可用的工具
model: claude-opus-4-6            # 指定使用的模型
context: fork                     # 在獨立 subagent 執行
agent: Explore                    # context: fork 時使用的 agent 類型
hooks:                            # 此 skill 生命週期的 hooks
  before: ./pre-check.sh
---
```

---

### 呼叫控制矩陣

| Frontmatter | 使用者可呼叫 | Claude 可呼叫 | 何時載入到 context |
|------------|------------|-------------|------------------|
| （預設） | ✅ | ✅ | Description 始終在 context，完整內容在呼叫時載入 |
| `disable-model-invocation: true` | ✅ | ❌ | Description **不**在 context，完整內容在使用者呼叫時載入 |
| `user-invocable: false` | ❌ | ✅ | Description 始終在 context，完整內容在呼叫時載入 |

**應用場景**：
- `disable-model-invocation: true`：部署腳本、commit、Slack 訊息（不希望 Claude 自動執行）
- `user-invocable: false`：背景知識型 skill（如 legacy-system-context），Claude 需要但使用者不需要直接呼叫

---

### 字串替換變數

| 變數 | 說明 |
|------|------|
| `$ARGUMENTS` | 呼叫 skill 時傳入的所有參數 |
| `$ARGUMENTS[N]` | 第 N 個參數（0-based） |
| `$N` | `$ARGUMENTS[N]` 的簡寫（`$0`, `$1`...） |
| `${CLAUDE_SESSION_ID}` | 當前 session ID |
| `${CLAUDE_SKILL_DIR}` | skill 的 SKILL.md 所在目錄（引用 skill 內的腳本用） |

**範例**：
```yaml
---
name: migrate-component
description: Migrate a component from one framework to another
---

Migrate the $0 component from $1 to $2.
Preserve all existing behavior and tests.
```
執行 `/migrate-component SearchBar React Vue` → $0=SearchBar, $1=React, $2=Vue

---

### 進階：動態 Context 注入

使用 `!command`` 語法在 skill 執行前先執行 shell 指令，輸出注入到 prompt：

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

> [!warning] 這是預處理，不是 Claude 執行
> shell 指令在 Claude 看到任何內容之前就已執行完畢，Claude 只看到最終結果。

> [!tip] 啟用 Extended Thinking
> 在 skill 內容中加入 "ultrathink" 即可啟用 extended thinking。

---

### Fork Context 模式

```yaml
context: fork   # 在獨立 subagent 中執行
agent: Explore  # 使用的 agent 類型（內建或自訂）
```

**兩種搭配方式**：

| 方式 | System prompt | Task | 也載入 |
|------|-------------|------|--------|
| Skill with `context: fork` | 來自 agent 類型 | SKILL.md 內容 | CLAUDE.md |
| Subagent with `skills` field | Subagent 的 markdown | Claude 的委派訊息 | 預載 skills + CLAUDE.md |

> [!warning] Fork 適合任務型 skill，不適合純參考型
> 若 skill 只有「使用這些 API conventions」這類指引而無明確任務，subagent 收到後無從執行，會空手而返。

---

### 限制 Claude 的 Skill 存取

```bash
# 在 /permissions 中拒絕所有 skills
Skill

# 只允許特定 skills
Skill(commit)
Skill(review-pr *)   # 前綴萬用字元

# 拒絕特定 skills
Skill(deploy *)
```

**語法**：`Skill(name)` 完全匹配；`Skill(name *)` 前綴匹配（任意參數）

---

### 分享 Skills

| 方式 | 做法 |
|------|------|
| 專案內共享 | commit `.claude/skills/` 到版本控制 |
| Plugin 發佈 | 在 plugin 中建立 `skills/` 目錄 |
| 企業部署 | 透過 managed settings 組織範圍部署 |

---

### 故障排除

**Skill 沒有觸發**
- 確認 description 包含使用者自然會說的關鍵字
- 確認 skill 出現在「What skills are available?」
- 直接用 `/skill-name` 呼叫測試

**Skill 觸發太頻繁**
- 讓 description 更精確
- 加入 `disable-model-invocation: true` 改為手動呼叫

**Claude 看不到所有 Skills**
- Description 有 context 預算（context window 的 2%，最少 16,000 字元）
- 執行 `/context` 查看是否有 excluded skills 警告
- 設定環境變數 `SLASH_COMMAND_TOOL_CHAR_BUDGET` 覆蓋上限

---

### 視覺化輸出範例（Codebase Visualizer）

Skills 可以捆綁任意語言的腳本，產生互動式 HTML 輸出：

```yaml
---
name: codebase-visualizer
description: Generate an interactive collapsible tree visualization of your codebase.
allowed-tools: Bash(python *)
---
```

搭配 Python 腳本，掃描專案目錄並生成含可展開目錄樹、檔案大小、檔案類型色彩標示的互動式 HTML 頁面。

**適用模式**：dependency graphs、test coverage reports、API 文件、資料庫 schema 視覺化。

## References

- [官方文件](https://code.claude.com/docs/en/skills)
- 相關文章：[[2026-03-07-CLAUDE-SKILLS-2.0-THE-SELF-IMPROVING-AI-CAPABILITIES-THAT-ACTUALLY-WORK]]
- 相關文章：[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]
