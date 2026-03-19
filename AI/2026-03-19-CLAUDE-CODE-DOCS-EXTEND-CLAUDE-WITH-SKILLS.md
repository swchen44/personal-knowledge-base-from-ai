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

建立、管理並分享技能（skills），以在 Claude Code 中擴展 Claude 的能力。涵蓋自訂指令（custom commands）與捆綁技能（bundled skills）。

技能（skills）擴展了 Claude 的能力範疇。建立一個含指令的 SKILL.md 檔案，Claude 就會將其納入工具箱。Claude 會在相關時機自動使用技能（skills），也可以直接用 `/skill-name` 呼叫。

> 內建指令（built-in commands）如 `/help` 與 `/compact`，請參閱內建指令參考文件。

自訂指令（custom commands）已合併進技能（skills）。`.claude/commands/deploy.md` 與 `.claude/skills/deploy/SKILL.md` 都會建立 `/deploy`，效果完全相同。現有的 `.claude/commands/` 檔案繼續有效。技能（skills）新增了選用功能：一個放置支援檔案的目錄、可控制由你或 Claude 呼叫的前置資訊（frontmatter），以及讓 Claude 在相關時機自動載入的能力。

Claude Code 的技能（skills）遵循代理技能開放標準（Agent Skills open standard），可跨多個 AI 工具使用。Claude Code 在此標準上延伸了額外功能，包括呼叫控制（invocation control）、子代理執行（subagent execution）與動態情境注入（dynamic context injection）。

---

## 捆綁技能（Bundled Skills）

捆綁技能（bundled skills）隨 Claude Code 一起出貨，在每個工作階段（session）中皆可使用。與直接執行固定邏輯的內建指令（built-in commands）不同，捆綁技能（bundled skills）是提示詞驅動（prompt-based）的：它們提供 Claude 一份詳細的執行手冊，讓 Claude 用自己的工具（tools）來協調工作。這意味著捆綁技能（bundled skills）可以啟動平行代理（parallel agents）、讀取檔案，並適應你的程式碼庫。

呼叫捆綁技能（bundled skills）的方式與其他技能（skills）相同：輸入 `/` 加上技能名稱。下表中，`<arg>` 表示必填參數，`[arg]` 表示選填參數。

| 技能（Skill） | 用途 |
|-------|------|
| `/batch <instruction>` | 在程式碼庫中大規模平行執行變更。研究程式碼庫、將工作分解成 5 至 30 個獨立單元並提出計劃。核准後，為每個單元在隔離的 git 工作樹（git worktree）中啟動一個背景代理（background agent）。每個代理實作其單元、執行測試並開啟一個 pull request。需要 git 儲存庫。範例：`/batch migrate src/ from Solid to React` |
| `/claude-api` | 為你的專案語言（Python、TypeScript、Java、Go、Ruby、C#、PHP 或 cURL）載入 Claude API 參考資料，以及 Python 和 TypeScript 的 Agent SDK 參考。涵蓋工具使用（tool use）、串流（streaming）、批次（batches）、結構化輸出（structured outputs）與常見陷阱。當你的程式碼匯入 `anthropic`、`@anthropic-ai/sdk` 或 `claude_agent_sdk` 時也會自動啟動。 |
| `/debug [description]` | 透過讀取工作階段偵錯日誌（session debug log）來排查當前 Claude Code 工作階段。可選擇性描述問題以聚焦分析。 |
| `/loop [interval] <prompt>` | 在工作階段開啟期間，按間隔重複執行一個提示詞（prompt）。適用於輪詢部署狀態（polling a deployment）、守護一個 PR，或定期重新執行另一個技能（skill）。範例：`/loop 5m check if the deploy finished`。 |
| `/simplify [focus]` | 審查最近變更的檔案中的程式碼重用、品質與效率問題，然後修正它們。平行啟動三個審查代理（review agents），彙總發現並套用修正。傳入文字可聚焦特定問題：`/simplify focus on memory efficiency`。 |

---

## 入門

### 建立你的第一個技能（Skill）

這個範例建立一個技能（skill），教 Claude 用視覺圖表（visual diagrams）和類比（analogies）來解釋程式碼。由於使用預設前置資訊（frontmatter），當你詢問某個東西如何運作時，Claude 可以自動載入它，你也可以直接用 `/explain-code` 呼叫。

**步驟 1：建立技能目錄（skill directory）**

在你的個人技能資料夾中建立目錄。個人技能（personal skills）可在你所有的專案中使用。

```bash
mkdir -p ~/.claude/skills/explain-code
```

**步驟 2：撰寫 SKILL.md**

每個技能（skill）都需要一個 SKILL.md 檔案，包含兩個部分：YAML 前置資訊（frontmatter）（在 `---` 標記之間）告訴 Claude 何時使用該技能（skill），以及 Claude 被呼叫時所遵循的 markdown 指令內容。`name` 欄位會成為斜線指令（slash command），`description` 幫助 Claude 決定何時自動載入。

建立 `~/.claude/skills/explain-code/SKILL.md`：

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

Keep explanations conversational. For complex concepts, use multiple analogies.
```

**步驟 3：測試技能（skill）**

有兩種測試方式：

讓 Claude 透過詢問符合描述（description）的問題來自動呼叫：
```
How does this code work?
```

或直接用技能名稱呼叫：
```
/explain-code src/auth/login.ts
```

無論哪種方式，Claude 都應該在解釋中包含類比（analogy）和 ASCII 圖表。

---

## 技能（Skills）的存放位置

技能（skill）的存放位置決定了誰可以使用它：

| 位置 | 路徑 | 適用範圍 |
|------|------|---------|
| 企業（Enterprise） | 參見受管設定（managed settings） | 組織中的所有使用者 |
| 個人（Personal） | `~/.claude/skills/<skill-name>/SKILL.md` | 你的所有專案 |
| 專案（Project） | `.claude/skills/<skill-name>/SKILL.md` | 僅此專案 |
| 外掛（Plugin） | `<plugin>/skills/<skill-name>/SKILL.md` | 外掛（plugin）啟用的地方 |

當不同層級的技能（skills）同名時，優先級較高的位置獲勝：enterprise > personal > project。外掛技能（plugin skills）使用 `plugin-name:skill-name` 命名空間，因此不會與其他層級衝突。若你在 `.claude/commands/` 中有檔案，其運作方式相同，但若技能（skill）與指令（command）同名，技能（skill）優先。

### 從巢狀目錄自動探索（Automatic Discovery from Nested Directories）

當你在子目錄中處理檔案時，Claude Code 會自動從巢狀的 `.claude/skills/` 目錄探索技能（skills）。例如，若你正在編輯 `packages/frontend/` 中的檔案，Claude Code 也會在 `packages/frontend/.claude/skills/` 中尋找技能（skills）。這支援各套件擁有自己技能（skills）的單體式儲存庫（monorepo）設定。

每個技能（skill）都是一個以 SKILL.md 為進入點（entrypoint）的目錄：

```
my-skill/
├── SKILL.md           # 主指令（main instructions）（必要）
├── template.md        # 供 Claude 填寫的範本（template）
├── examples/
│   └── sample.md      # 展示預期格式的範例輸出（example output）
└── scripts/
    └── validate.sh    # Claude 可執行的腳本（script）
```

SKILL.md 包含主要指令且是必要的。其他檔案為選用，可讓你建立更強大的技能（skills）：供 Claude 填寫的範本（templates）、展示預期格式的範例輸出（example outputs）、Claude 可執行的腳本（scripts），或詳細的參考文件。從你的 SKILL.md 中引用這些檔案，讓 Claude 知道它們包含什麼以及何時載入。詳見「新增支援檔案（Add supporting files）」。

`.claude/commands/` 中的檔案仍然有效並支援相同的前置資訊（frontmatter）。建議使用技能（skills），因為它們支援支援檔案（supporting files）等額外功能。

---

## 設定技能（Configure Skills）

技能（skills）透過 SKILL.md 頂端的 YAML 前置資訊（frontmatter）與其後的 markdown 內容來設定。

### 技能內容的類型（Types of Skill Content）

技能（skill）檔案可以包含任何指令，但思考你希望如何呼叫它有助於引導要包含什麼：

**參考內容（Reference content）** 新增 Claude 應用於當前工作的知識——慣例（conventions）、模式（patterns）、風格指南（style guides）、領域知識。此內容以內嵌（inline）方式執行，讓 Claude 可在對話情境（conversation context）旁使用它。

```yaml
---
name: api-conventions
description: API design patterns for this codebase
---

When writing API endpoints:
- Use RESTful naming conventions
- Return consistent error formats
- Include request validation
```

**任務內容（Task content）** 給 Claude 執行特定動作的逐步指令，例如部署（deployments）、提交（commits）或程式碼生成。這些通常是你希望直接用 `/skill-name` 呼叫的動作，而非讓 Claude 自行決定何時執行。加入 `disable-model-invocation: true` 可防止 Claude 自動觸發它。

```yaml
---
name: deploy
description: Deploy the application to production
context: fork
disable-model-invocation: true
---

Deploy the application:
1. Run the test suite
2. Build the application
3. Push to the deployment target
```

### 前置資訊參考（Frontmatter Reference）

除了 markdown 內容，你可以使用 SKILL.md 頂端 `---` 標記之間的 YAML 前置資訊（frontmatter）欄位來設定技能（skill）行為：

```yaml
---
name: my-skill
description: What this skill does
disable-model-invocation: true
allowed-tools: Read, Grep
---

Your skill instructions here...
```

所有欄位皆為選用。建議填寫 `description`，讓 Claude 知道何時使用此技能（skill）。

| 欄位 | 必要 | 說明 |
|------|------|------|
| `name` | 否 | 技能（skill）的顯示名稱。若省略，使用目錄名稱。僅限小寫字母、數字和連字號（最多 64 個字元）。 |
| `description` | 建議填寫 | 技能（skill）的功能與使用時機。Claude 用此來決定何時套用技能（skill）。若省略，使用 markdown 內容的第一段。 |
| `argument-hint` | 否 | 自動完成（autocomplete）期間顯示的提示，說明預期的參數。例如：`[issue-number]` 或 `[filename] [format]`。 |
| `disable-model-invocation` | 否 | 設為 `true` 可防止 Claude 自動載入此技能（skill）。用於你希望用 `/name` 手動觸發的工作流程（workflows）。預設：`false`。 |
| `user-invocable` | 否 | 設為 `false` 可從 `/` 選單隱藏。用於使用者不應直接呼叫的背景知識（background knowledge）。預設：`true`。 |
| `allowed-tools` | 否 | 此技能（skill）啟用時，Claude 可在無需詢問許可的情況下使用的工具（tools）。 |
| `model` | 否 | 此技能（skill）啟用時使用的模型（model）。 |
| `context` | 否 | 設為 `fork` 可在分叉子代理（forked subagent）情境中執行。 |
| `agent` | 否 | `context: fork` 設定時使用哪種子代理（subagent）類型。 |
| `hooks` | 否 | 此技能（skill）生命週期範圍的鉤子（hooks）。設定格式請參閱「技能與代理中的鉤子（Hooks in skills and agents）」。 |

### 可用的字串替換（Available String Substitutions）

技能（skills）支援動態值的字串替換（string substitution）：

| 變數 | 說明 |
|------|------|
| `$ARGUMENTS` | 呼叫技能（skill）時傳入的所有參數。若 `$ARGUMENTS` 未出現在內容中，參數會以 `ARGUMENTS: <value>` 的形式附加。 |
| `$ARGUMENTS[N]` | 以 0 為基底的索引存取特定參數，例如 `$ARGUMENTS[0]` 為第一個參數。 |
| `$N` | `$ARGUMENTS[N]` 的簡寫，例如 `$0` 為第一個參數，`$1` 為第二個。 |
| `${CLAUDE_SESSION_ID}` | 當前工作階段（session）ID。適用於記錄（logging）、建立工作階段特定檔案，或關聯技能（skill）輸出與工作階段。 |
| `${CLAUDE_SKILL_DIR}` | 包含技能（skill）SKILL.md 檔案的目錄。用於在 bash 注入指令中引用與技能（skill）捆綁的腳本（scripts）或檔案，無論當前工作目錄為何。 |

---

## 新增支援檔案（Add Supporting Files）

技能（skills）可以在其目錄中包含多個檔案。這讓 SKILL.md 聚焦於要點，同時讓 Claude 在需要時才存取詳細參考資料。大型參考文件（reference docs）、API 規格（API specifications）或範例集（example collections）不需要在每次技能（skill）執行時都載入情境（context）。

```
my-skill/
├── SKILL.md        （必要——概覽與導覽）
├── reference.md    （詳細 API 文件——按需載入）
├── examples.md     （使用範例——按需載入）
└── scripts/
    └── helper.py   （工具腳本——執行，不載入）
```

從 SKILL.md 引用支援檔案，讓 Claude 知道每個檔案的內容及何時載入：

```markdown
## Additional resources

- For complete API details, see [reference.md](reference.md)
- For usage examples, see [examples.md](examples.md)
```

> [!tip] 保持 SKILL.md 在 500 行以內。將詳細參考資料移至獨立檔案。

---

## 控制誰呼叫技能（Control Who Invokes a Skill）

預設情況下，你和 Claude 都可以呼叫任何技能（skill）。你可以輸入 `/skill-name` 直接呼叫，Claude 也可以在與對話相關時自動載入。兩個前置資訊（frontmatter）欄位可以限制這一點：

- **`disable-model-invocation: true`**：只有你能呼叫此技能（skill）。用於有副作用（side effects）或你想控制時機的工作流程（workflows），例如 `/commit`、`/deploy` 或 `/send-slack-message`。你不會希望 Claude 因為看到程式碼準備好了就決定部署。
- **`user-invocable: false`**：只有 Claude 能呼叫此技能（skill）。用於不構成動作的背景知識（background knowledge）。一個 `legacy-system-context` 技能（skill）解釋舊系統的運作方式。Claude 應在相關時知道這些，但 `/legacy-system-context` 對使用者來說不是有意義的動作。

以下欄位組合對呼叫（invocation）和情境載入（context loading）的影響：

| 前置資訊（Frontmatter） | 你可以呼叫 | Claude 可以呼叫 | 何時載入到情境（context） |
|------------|------------|-------------|------------------|
| （預設） | 是 | 是 | 描述（description）始終在情境（context），完整技能（skill）在呼叫時載入 |
| `disable-model-invocation: true` | 是 | 否 | 描述（description）不在情境（context），完整技能（skill）在你呼叫時載入 |
| `user-invocable: false` | 否 | 是 | 描述（description）始終在情境（context），完整技能（skill）在呼叫時載入 |

在一般工作階段（session）中，技能描述（skill descriptions）會載入情境（context），讓 Claude 知道有哪些可用，但完整的技能（skill）內容只有在呼叫時才載入。預載技能（preloaded skills）的子代理（subagents）運作方式不同：完整的技能（skill）內容在啟動時注入。

---

## 限制工具存取（Restrict Tool Access）

使用 `allowed-tools` 欄位來限制技能（skill）啟用時 Claude 可使用的工具（tools）。這個技能（skill）建立了一個唯讀模式（read-only mode），Claude 可以探索檔案但不能修改它們：

```yaml
---
name: safe-reader
description: Read files without making changes
allowed-tools: Read, Grep, Glob
---
```

---

## 傳遞參數給技能（Pass Arguments to Skills）

你和 Claude 都可以在呼叫技能（skill）時傳遞參數。參數可透過 `$ARGUMENTS` 佔位符（placeholder）取得。

這個技能（skill）透過編號修復 GitHub 議題（issue）。`$ARGUMENTS` 佔位符（placeholder）會被技能名稱後面的任何內容取代：

```yaml
---
name: fix-issue
description: Fix a GitHub issue
disable-model-invocation: true
---

Fix GitHub issue $ARGUMENTS following our coding standards.

1. Read the issue description
2. Understand the requirements
3. Implement the fix
4. Write tests
5. Create a commit
```

執行 `/fix-issue 123` 時，Claude 收到「Fix GitHub issue 123 following our coding standards…」

若你呼叫技能（skill）時帶有參數，但技能（skill）未包含 `$ARGUMENTS`，Claude Code 會將 `ARGUMENTS: <your input>` 附加到技能（skill）內容末尾，讓 Claude 仍能看到你輸入的內容。

使用 `$ARGUMENTS[N]` 或更短的 `$N` 按位置存取個別參數：

```yaml
---
name: migrate-component
description: Migrate a component from one framework to another
---

Migrate the $0 component from $1 to $2.
Preserve all existing behavior and tests.
```

執行 `/migrate-component SearchBar React Vue` 時，`$0` 替換為 SearchBar，`$1` 替換為 React，`$2` 替換為 Vue。

---

## 進階模式（Advanced Patterns）

### 注入動態情境（Inject Dynamic Context）

`` !`command` `` 語法會在技能（skill）內容傳送給 Claude 之前先執行 shell 指令。指令輸出取代佔位符（placeholder），讓 Claude 收到的是實際資料，而非指令本身。

這個技能（skill）透過 GitHub CLI 抓取即時 PR 資料來摘要 pull request。`` !`gh pr diff` `` 等指令會先執行，其輸出被插入提示詞（prompt）：

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

此技能（skill）執行時：
1. 每個 `` !`command` `` 立即執行（在 Claude 看到任何內容之前）
2. 輸出取代技能（skill）內容中的佔位符（placeholder）
3. Claude 收到帶有實際 PR 資料的完整渲染提示詞（prompt）

這是預處理（preprocessing），不是 Claude 執行的東西。Claude 只看到最終結果。

> [!tip] 若要在技能（skill）中啟用延伸思考（extended thinking），在技能（skill）內容的任何地方加入 "ultrathink" 即可。

### 在子代理（Subagent）中執行技能（Run Skills in a Subagent）

在前置資訊（frontmatter）中加入 `context: fork`，讓技能（skill）在隔離環境中執行。技能（skill）內容成為驅動子代理（subagent）的提示詞（prompt），它將無法存取你的對話歷史。

`context: fork` 只對有明確指令的技能（skills）有意義。若你的技能（skill）包含「使用這些 API conventions」之類的指引而沒有任務，子代理（subagent）收到指引但沒有可執行的提示詞（prompt），並會在沒有有意義輸出的情況下返回。

技能（skills）與子代理（subagents）以兩個方向相互配合：

| 方式 | 系統提示詞（System Prompt） | 任務（Task） | 也載入 |
|------|-------------|------|--------|
| 有 `context: fork` 的技能（Skill） | 來自代理類型（agent type）（Explore、Plan 等） | SKILL.md 內容 | CLAUDE.md |
| 有 `skills` 欄位的子代理（Subagent） | 子代理（subagent）的 markdown 主體 | Claude 的委派訊息 | 預載技能（preloaded skills）+ CLAUDE.md |

有了 `context: fork`，你在技能（skill）中撰寫任務並選擇代理類型（agent type）來執行。反過來（定義使用技能（skills）作為參考資料的自訂子代理（subagent）），請參閱子代理（Subagents）文件。

**範例：使用 Explore 代理的研究技能（Research skill using Explore agent）**

這個技能（skill）在分叉的 Explore 代理（forked Explore agent）中執行研究。技能（skill）內容成為任務，代理（agent）提供針對程式碼庫探索最佳化的唯讀工具（read-only tools）：

```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly:

1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

此技能（skill）執行時：
- 建立一個新的隔離情境（isolated context）
- 子代理（subagent）收到技能（skill）內容作為提示詞（「Research $ARGUMENTS thoroughly…」）
- `agent` 欄位決定執行環境（模型、工具（tools）與權限）
- 結果被摘要並返回到你的主對話

`agent` 欄位指定使用哪種子代理（subagent）設定。選項包括內建代理（built-in agents）（Explore、Plan、general-purpose）或 `.claude/agents/` 中的任何自訂子代理（custom subagent）。若省略，使用 general-purpose。

---

## 限制 Claude 的技能（Skill）存取

預設情況下，Claude 可以呼叫任何未設定 `disable-model-invocation: true` 的技能（skill）。定義了 `allowed-tools` 的技能（skills）在技能（skill）啟用時授予 Claude 存取那些工具（tools）而無需逐次核准。你的權限設定（permission settings）仍然管控所有其他工具（tools）的基準核准行為。內建指令（built-in commands）如 `/compact` 和 `/init` 無法透過技能（Skill）工具（tool）取得。

三種控制 Claude 可呼叫哪些技能（skills）的方式：

在 `/permissions` 中拒絕技能（Skill）工具（tool）來停用所有技能（skills）：
```
Skill
```

使用權限規則（permission rules）允許或拒絕特定技能（skills）：
```
# 只允許特定技能（skills）
Skill(commit)
Skill(review-pr *)

# 拒絕特定技能（skills）
Skill(deploy *)
```

權限語法（permission syntax）：`Skill(name)` 完全匹配，`Skill(name *)` 前綴匹配（任意參數）。

在前置資訊（frontmatter）中加入 `disable-model-invocation: true` 來隱藏個別技能（skills）。這會從 Claude 的情境（context）中完全移除該技能（skill）。

`user-invocable` 欄位只控制選單可見性，不控制技能（Skill）工具（tool）的存取。使用 `disable-model-invocation: true` 來封鎖程式化呼叫（programmatic invocation）。

---

## 分享技能（Share Skills）

技能（skills）可以根據你的受眾在不同範圍分發：

- **專案技能（Project skills）**：將 `.claude/skills/` 提交（commit）到版本控制（version control）
- **外掛（Plugins）**：在你的外掛（plugin）中建立 `skills/` 目錄
- **受管（Managed）**：透過受管設定（managed settings）在組織範圍部署

---

## 生成視覺輸出（Generate Visual Output）

技能（skills）可以捆綁並執行任何語言的腳本（scripts），給 Claude 超越單一提示詞（prompt）所能做到的能力。一個強大的模式是生成視覺輸出（visual output）：在瀏覽器中開啟的互動式 HTML 檔案，用於探索資料、偵錯或建立報告。

這個範例建立一個程式碼庫探索器（codebase explorer）：一個互動式樹狀視圖，你可以展開和摺疊目錄、一眼看出檔案大小，並用顏色識別檔案類型。

```yaml
---
name: codebase-visualizer
description: Generate an interactive collapsible tree visualization of your codebase. Use when exploring a new repo, understanding project structure, or identifying large files.
allowed-tools: Bash(python *)
---

# Codebase Visualizer

Generate an interactive HTML tree view that shows your project's file structure with collapsible directories.

## Usage

Run the visualization script from your project root:

```bash
python ~/.claude/skills/codebase-visualizer/scripts/visualize.py .
```

This creates `codebase-map.html` in the current directory and opens it in your default browser.
```

搭配 Python 腳本（script）掃描目錄樹，並生成一個自包含的 HTML 檔案，包含：摘要側欄（summary sidebar）、依檔案類型分類的長條圖（bar chart），以及可展開摺疊的樹狀結構。

在任何專案中開啟 Claude Code 並詢問「Visualize this codebase.」即可測試。Claude 執行腳本（script）、生成 `codebase-map.html` 並在瀏覽器中開啟。

此模式適用於任何視覺輸出（visual output）：相依性圖（dependency graphs）、測試覆蓋率報告（test coverage reports）、API 文件，或資料庫綱要視覺化（database schema visualizations）。捆綁腳本（bundled script）承擔繁重的工作，而 Claude 處理協調（orchestration）。

---

## 故障排除（Troubleshooting）

### 技能（Skill）沒有觸發

若 Claude 未在預期時使用你的技能（skill）：
- 檢查描述（description）是否包含使用者自然會說的關鍵字
- 確認技能（skill）出現在「What skills are available?」中
- 嘗試重新措辭你的請求以更接近描述（description）
- 若技能（skill）是使用者可呼叫（user-invocable）的，直接用 `/skill-name` 呼叫

### 技能（Skill）觸發太頻繁

若 Claude 在你不希望的時候使用你的技能（skill）：
- 讓描述（description）更具體
- 若你只要手動呼叫，加入 `disable-model-invocation: true`

### Claude 看不到我所有的技能（Skills）

技能描述（skill descriptions）會載入情境（context），讓 Claude 知道有哪些可用。若你有很多技能（skills），它們可能超出字元預算（character budget）。預算依情境視窗（context window）的 2% 動態擴展，最少為 16,000 個字元。執行 `/context` 檢查是否有關於被排除技能（excluded skills）的警告。

若要覆蓋上限，設定環境變數 `SLASH_COMMAND_TOOL_CHAR_BUDGET`。

---

## 相關資源（Related Resources）

- **子代理（Subagents）**：將任務委派給專業代理（specialized agents）
- **外掛（Plugins）**：將技能（skills）與其他擴展打包並分發
- **鉤子（Hooks）**：圍繞工具事件（tool events）自動化工作流程（workflows）
- **記憶（Memory）**：管理 CLAUDE.md 檔案以持久化情境（persistent context）
- **內建指令（Built-in commands）**：內建 `/` 指令的參考
- **權限（Permissions）**：控制工具（tool）與技能（skill）的存取

## References

- [官方文件（原文）](https://code.claude.com/docs/en/skills)
- 相關文章：[[2026-03-07-CLAUDE-SKILLS-2.0-THE-SELF-IMPROVING-AI-CAPABILITIES-THAT-ACTUALLY-WORK]]
- 相關文章：[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]
