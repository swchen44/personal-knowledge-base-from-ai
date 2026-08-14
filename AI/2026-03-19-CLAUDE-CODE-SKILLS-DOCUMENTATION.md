---
title: "Claude Code 官方文件：用 Skill 擴充 Claude 的能力（Extend Claude with Skills）"
date: 2026-03-19
date_uncertain: true
category: AI
tags:
  - ai/skill-design
  - tools/claude-code
  - tools/adk
source: "https://code.claude.com/docs/en/skills"
source_type: article
author: "Anthropic"
status: notes
links:
  - "[[SKILL-MD-SPECIFICATION]]"
  - "[[AGENT-SKILL-PATTERNS]]"
  - "[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]"
---

## 摘要（Summary）

Claude Code 官方文件中關於 Skills 的完整說明。Skills 讓 Claude 能做到更多：建立一個含有指令的 `SKILL.md` 檔案，Claude 就會將其加入工具箱。Claude 會在相關情境下自動使用，或你可以用 `/skill-name` 直接呼叫。

> [!note] Custom Commands 已合併進 Skills
> `.claude/commands/deploy.md` 和 `.claude/skills/deploy/SKILL.md` 都會建立 `/deploy` 且運作方式相同。舊的 `.claude/commands/` 檔案繼續有效。Skills 新增了支援檔案目錄、控制誰可以呼叫、以及讓 Claude 在相關時自動載入等功能。

## 關鍵洞察（Key Insights）

- **Skills 遵循 Agent Skills 開放標準（open standard）**，可跨多個 AI 工具運作；Claude Code 在此基礎上擴充了呼叫控制、子代理人執行和動態上下文注入等功能
- **Bundled skills 是提示詞驅動的**，不是固定邏輯：它們給 Claude 一份詳細的操作手冊，讓 Claude 用工具自行協調工作，因此可以生成平行代理人、讀取檔案、適應程式碼庫
- **`disable-model-invocation: true`** 防止 Claude 自動觸發 skill，適合有副作用的操作（deploy、commit）
- **`context: fork`** 讓 skill 在隔離的子代理人中執行，不共用對話歷史
- **Skill 描述的字元預算**：動態為上下文視窗（Context Window）的 2%，預設後備為 16,000 字元

## 詳細內容（Details）

### 內建 Bundled Skills

| Skill | 用途 |
|-------|------|
| `/batch <instruction>` | 大規模並行修改程式碼庫：拆分成 5–30 個獨立單元，每個生成一個背景代理人在隔離 git worktree 中執行，完成後各自開 PR |
| `/claude-api` | 載入 Claude API 參考資料（Python、TypeScript、Java、Go 等），涵蓋 tool use、streaming、batches |
| `/debug [description]` | 讀取 session debug log 排查問題 |
| `/loop [interval] <prompt>` | 按間隔重複執行提示詞，例如輪詢部署狀態 |
| `/simplify [focus]` | 審查近期修改的檔案，平行生成 3 個審查代理人，彙總發現並套用修正 |

---

### 快速開始：建立第一個 Skill

#### 步驟 1：建立 skill 目錄

```bash
mkdir -p ~/.claude/skills/explain-code
```

#### 步驟 2：撰寫 SKILL.md

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

#### 步驟 3：測試

```bash
# 讓 Claude 自動偵測（符合 description 關鍵字）
How does this code work?

# 或直接呼叫
/explain-code src/auth/login.ts
```

---

### Skill 的存放位置

| 層級 | 路徑 | 適用範圍 |
|------|------|---------|
| Enterprise | 見 managed settings | 組織所有使用者 |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` | 你的所有專案 |
| Project | `.claude/skills/<skill-name>/SKILL.md` | 此專案 |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` | 啟用該 plugin 之處 |

優先順序：enterprise > personal > project。Plugin skills 使用 `plugin-name:skill-name` 命名空間，不會衝突。

> [!note] Monorepo 支援：自動探索巢狀目錄
> 編輯 `packages/frontend/` 中的檔案時，Claude Code 也會自動在 `packages/frontend/.claude/skills/` 中尋找 skills。

#### Skill 目錄結構

```
my-skill/
├── SKILL.md           # 主要指令（必要）
├── template.md        # 供 Claude 填入的模板
├── examples/
│   └── sample.md      # 展示預期格式的範例輸出
└── scripts/
    └── validate.sh    # Claude 可執行的腳本
```

---

### 設定 Skill（Frontmatter Reference）

```yaml
---
name: my-skill
description: What this skill does
disable-model-invocation: true
allowed-tools: Read, Grep
---

Your skill instructions here...
```

| 欄位 | 必要 | 說明 |
|------|------|------|
| `name` | 否 | Skill 顯示名稱。省略時使用目錄名稱。只允許小寫字母、數字、連字號（最多 64 字元）。 |
| `description` | 建議 | Skill 的功能與使用時機。Claude 用此判斷何時套用。省略時使用 markdown 內容第一段。 |
| `argument-hint` | 否 | 自動完成時顯示的參數提示，例如 `[issue-number]` 或 `[filename] [format]`。 |
| `disable-model-invocation` | 否 | 設為 `true` 防止 Claude 自動載入此 skill。用於想以 `/name` 手動觸發的工作流程。預設：false。 |
| `user-invocable` | 否 | 設為 `false` 隱藏於 `/` 選單。用於使用者不應直接呼叫的背景知識。預設：true。 |
| `allowed-tools` | 否 | 此 skill 啟用時 Claude 可無需詢問即使用的工具。 |
| `model` | 否 | 此 skill 啟用時使用的模型。 |
| `context` | 否 | 設為 `fork` 在分叉的子代理人上下文中執行。 |
| `agent` | 否 | `context: fork` 時使用哪種子代理人類型。 |
| `hooks` | 否 | 限定於此 skill 生命週期的 hooks。 |

---

### 字串替換（String Substitutions）

| 變數 | 說明 |
|------|------|
| `$ARGUMENTS` | 呼叫 skill 時傳入的所有參數 |
| `$ARGUMENTS[N]` | 以 0 為基底的索引取得特定參數 |
| `$N` | `$ARGUMENTS[N]` 的縮寫（如 `$0`、`$1`） |
| `${CLAUDE_SESSION_ID}` | 當前 session ID，適合 log、建立 session 專屬檔案 |
| `${CLAUDE_SKILL_DIR}` | 包含此 skill 的 `SKILL.md` 的目錄路徑，無論當前工作目錄為何 |

範例：

```yaml
---
name: session-logger
description: Log activity for this session
---

Log the following to logs/${CLAUDE_SESSION_ID}.log:

$ARGUMENTS
```

---

### Skill 內容的兩種類型

**參考內容（Reference Content）**：將知識套用到當前工作。慣例、模式、風格指南、領域知識。

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

**任務內容（Task Content）**：給 Claude 特定動作的逐步指令，如部署、commit、程式碼生成。這類 skill 通常你想用 `/skill-name` 直接呼叫而非讓 Claude 自行決定。加上 `disable-model-invocation: true`：

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

---

### 控制誰可以呼叫 Skill

#### 只有你可以呼叫（`disable-model-invocation: true`）

```yaml
---
name: deploy
description: Deploy the application to production
disable-model-invocation: true
---

Deploy $ARGUMENTS to production:

1. Run the test suite
2. Build the application
3. Push to the deployment target
4. Verify the deployment succeeded
```

| Frontmatter | 你可以呼叫 | Claude 可以呼叫 | 何時載入上下文 |
|-------------|-----------|---------------|--------------|
| （預設） | ✅ | ✅ | description 永遠在上下文，呼叫時完整載入 |
| `disable-model-invocation: true` | ✅ | ❌ | description 不在上下文，你呼叫時才載入 |
| `user-invocable: false` | ❌ | ✅ | description 永遠在上下文，呼叫時完整載入 |

> [!important] 重要區別
> `user-invocable: false` 只控制選單可見性，不控制 Skill tool 存取。要阻止程式化呼叫，使用 `disable-model-invocation: true`。

---

### 限制工具存取（Restrict Tool Access）

建立只能讀取檔案的唯讀模式 skill：

```yaml
---
name: safe-reader
description: Read files without making changes
allowed-tools: Read, Grep, Glob
---
```

---

### 傳入參數給 Skill

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

執行 `/fix-issue 123`，Claude 收到「Fix GitHub issue 123 following our coding standards…」

**多個具名參數**：

```yaml
---
name: migrate-component
description: Migrate a component from one framework to another
---

Migrate the $ARGUMENTS[0] component from $ARGUMENTS[1] to $ARGUMENTS[2].
Preserve all existing behavior and tests.
```

或用縮寫 `$N`：

```yaml
---
name: migrate-component
description: Migrate a component from one framework to another
---

Migrate the $0 component from $1 to $2.
Preserve all existing behavior and tests.
```

---

### 進階模式：注入動態上下文（Inject Dynamic Context）

`` !`command` `` 語法在 skill 內容傳給 Claude 之前先執行 shell 指令，輸出結果替換佔位符。Claude 只看到最終渲染結果，不是指令本身。

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

> [!tip] 啟用 Extended Thinking
> 在 skill 內容中加入 `ultrathink` 這個詞，即可啟用該 skill 的 extended thinking。

---

### 在子代理人中執行 Skill（context: fork）

加入 `context: fork` 讓 skill 在隔離的環境中執行，不共用對話歷史。

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

| 方式 | System Prompt | 任務 | 也載入 |
|------|--------------|------|--------|
| Skill with `context: fork` | 來自 agent 類型（Explore、Plan 等） | SKILL.md 內容 | CLAUDE.md |
| Subagent with `skills` field | Subagent 的 markdown 主體 | Claude 的委派訊息 | 預載 skills + CLAUDE.md |

`agent` 欄位可指定內建代理人（Explore、Plan、general-purpose）或 `.claude/agents/` 中的自訂 subagent。省略時使用 general-purpose。

---

### 限制 Claude 的 Skill 存取

```bash
# 拒絕所有 skills
Skill

# 只允許特定 skills
Skill(commit)
Skill(review-pr *)

# 拒絕特定 skills
Skill(deploy *)
```

權限語法：`Skill(name)` 精確比對，`Skill(name *)` 前綴比對（允許任意參數）。

---

### 生成視覺輸出（Generate Visual Output）範例

完整的 codebase 視覺化工具，展示如何在 skill 中打包並執行腳本：

**SKILL.md**：

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

## What the visualization shows

- **Collapsible directories**: Click folders to expand/collapse
- **File sizes**: Displayed next to each file
- **Colors**: Different colors for different file types
- **Directory totals**: Shows aggregate size of each folder
```

**scripts/visualize.py**：

```python
#!/usr/bin/env python3
"""Generate an interactive collapsible tree visualization of a codebase."""

import json
import sys
import webbrowser
from pathlib import Path
from collections import Counter

IGNORE = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}

def scan(path: Path, stats: dict) -> dict:
    result = {"name": path.name, "children": [], "size": 0}
    try:
        for item in sorted(path.iterdir()):
            if item.name in IGNORE or item.name.startswith('.'):
                continue
            if item.is_file():
                size = item.stat().st_size
                ext = item.suffix.lower() or '(no ext)'
                result["children"].append({"name": item.name, "size": size, "ext": ext})
                result["size"] += size
                stats["files"] += 1
                stats["extensions"][ext] += 1
                stats["ext_sizes"][ext] += size
            elif item.is_dir():
                stats["dirs"] += 1
                child = scan(item, stats)
                if child["children"]:
                    result["children"].append(child)
                    result["size"] += child["size"]
    except PermissionError:
        pass
    return result

def generate_html(data: dict, stats: dict, output: Path) -> None:
    ext_sizes = stats["ext_sizes"]
    total_size = sum(ext_sizes.values()) or 1
    sorted_exts = sorted(ext_sizes.items(), key=lambda x: -x[1])[:8]
    colors = {
        '.js': '#f7df1e', '.ts': '#3178c6', '.py': '#3776ab', '.go': '#00add8',
        '.rs': '#dea584', '.rb': '#cc342d', '.css': '#264de4', '.html': '#e34c26',
        '.json': '#6b7280', '.md': '#083fa1', '.yaml': '#cb171e', '.yml': '#cb171e',
        '.mdx': '#083fa1', '.tsx': '#3178c6', '.jsx': '#61dafb', '.sh': '#4eaa25',
    }
    lang_bars = "".join(
        f'<div class="bar-row"><span class="bar-label">{ext}</span>'
        f'<div class="bar" style="width:{(size/total_size)*100}%;background:{colors.get(ext,"#6b7280")}"></div>'
        f'<span class="bar-pct">{(size/total_size)*100:.1f}%</span></div>'
        for ext, size in sorted_exts
    )
    def fmt(b):
        if b < 1024: return f"{b} B"
        if b < 1048576: return f"{b/1024:.1f} KB"
        return f"{b/1048576:.1f} MB"

    html = f'''<!DOCTYPE html>
<html><head>
  <meta charset="utf-8"><title>Codebase Explorer</title>
  <style>
    body {{ font: 14px/1.5 system-ui, sans-serif; margin: 0; background: #1a1a2e; color: #eee; }}
    .container {{ display: flex; height: 100vh; }}
    .sidebar {{ width: 280px; background: #252542; padding: 20px; border-right: 1px solid #3d3d5c; overflow-y: auto; flex-shrink: 0; }}
    .main {{ flex: 1; padding: 20px; overflow-y: auto; }}
    h1 {{ margin: 0 0 10px 0; font-size: 18px; }}
    h2 {{ margin: 20px 0 10px 0; font-size: 14px; color: #888; text-transform: uppercase; }}
    .stat {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #3d3d5c; }}
    .stat-value {{ font-weight: bold; }}
    .bar-row {{ display: flex; align-items: center; margin: 6px 0; }}
    .bar-label {{ width: 55px; font-size: 12px; color: #aaa; }}
    .bar {{ height: 18px; border-radius: 3px; }}
    .bar-pct {{ margin-left: 8px; font-size: 12px; color: #666; }}
    .tree {{ list-style: none; padding-left: 20px; }}
    details {{ cursor: pointer; }}
    summary {{ padding: 4px 8px; border-radius: 4px; }}
    summary:hover {{ background: #2d2d44; }}
    .folder {{ color: #ffd700; }}
    .file {{ display: flex; align-items: center; padding: 4px 8px; border-radius: 4px; }}
    .file:hover {{ background: #2d2d44; }}
    .size {{ color: #888; margin-left: auto; font-size: 12px; }}
    .dot {{ width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }}
  </style>
</head><body>
  <div class="container">
    <div class="sidebar">
      <h1>📊 Summary</h1>
      <div class="stat"><span>Files</span><span class="stat-value">{stats["files"]:,}</span></div>
      <div class="stat"><span>Directories</span><span class="stat-value">{stats["dirs"]:,}</span></div>
      <div class="stat"><span>Total size</span><span class="stat-value">{fmt(data["size"])}</span></div>
      <div class="stat"><span>File types</span><span class="stat-value">{len(stats["extensions"])}</span></div>
      <h2>By file type</h2>
      {lang_bars}
    </div>
    <div class="main">
      <h1>📁 {data["name"]}</h1>
      <ul class="tree" id="root"></ul>
    </div>
  </div>
  <script>
    const data = {json.dumps(data)};
    const colors = {json.dumps(colors)};
    function fmt(b) {{ if (b < 1024) return b + \' B\'; if (b < 1048576) return (b/1024).toFixed(1) + \' KB\'; return (b/1048576).toFixed(1) + \' MB\'; }}
    function render(node, parent) {{
      if (node.children) {{
        const det = document.createElement(\'details\');
        det.open = parent === document.getElementById(\'root\');
        det.innerHTML = `<summary><span class="folder">📁 ${{node.name}}</span><span class="size">${{fmt(node.size)}}</span></summary>`;
        const ul = document.createElement(\'ul\'); ul.className = \'tree\';
        node.children.sort((a,b) => (b.children?1:0)-(a.children?1:0) || a.name.localeCompare(b.name));
        node.children.forEach(c => render(c, ul));
        det.appendChild(ul);
        const li = document.createElement(\'li\'); li.appendChild(det); parent.appendChild(li);
      }} else {{
        const li = document.createElement(\'li\'); li.className = \'file\';
        li.innerHTML = `<span class="dot" style="background:${{colors[node.ext]||\'#6b7280\'}}"></span>${{node.name}}<span class="size">${{fmt(node.size)}}</span>`;
        parent.appendChild(li);
      }}
    }}
    data.children.forEach(c => render(c, document.getElementById(\'root\')));
  </script>
</body></html>'''
    output.write_text(html)

if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    stats = {"files": 0, "dirs": 0, "extensions": Counter(), "ext_sizes": Counter()}
    data = scan(target, stats)
    out = Path('codebase-map.html')
    generate_html(data, stats, out)
    print(f'Generated {out.absolute()}')
    webbrowser.open(f'file://{out.absolute()}')
```

---

### 疑難排解（Troubleshooting）

> [!warning] Skill 不觸發
> - 確認 description 包含使用者會自然說出的關鍵字
> - 用 `What skills are available?` 確認 skill 是否出現在清單中
> - 嘗試改寫你的請求以更符合 description 的措辭
> - 若 skill 是 user-invocable，可直接用 `/skill-name` 呼叫

> [!warning] Skill 觸發太頻繁
> - 讓 description 更具體
> - 加上 `disable-model-invocation: true`，改為只允許手動呼叫

> [!warning] Claude 看不到所有 Skills
> Skill descriptions 載入上下文有字元預算：動態為上下文視窗的 2%，後備為 16,000 字元。執行 `/context` 檢查是否有 skill 被排除的警告。若要覆蓋限制，設定環境變數 `SLASH_COMMAND_TOOL_CHAR_BUDGET`。

---

### `--add-dir` 中的 Skills

在 `--add-dir` 加入的目錄中定義的 skills 會自動載入，並支援即時變更偵測（live change detection），可在 session 進行中編輯無需重啟。

## 我的心得（My Takeaways）

這份官方文件確立了幾個重要的設計原則：

1. **`disable-model-invocation: true` 是有副作用操作的必要防護**：deploy、send-slack-message 這類 skill 不能讓 Claude 自己決定何時執行
2. **`context: fork` + `agent: Explore` 是 read-only 研究任務的標準模式**：隔離執行、不汙染主對話
3. **`` !`command` `` 注入是動態上下文的正確方式**：不是讓 Claude 去呼叫，而是預處理後直接給 Claude 最終結果
4. **Skill 字元預算要注意**：skill 多了之後可能會有 skill 被 context 排除，要定期檢查 `/context`

## 待補充（Open Questions）

- `context: fork` 的子代理人實際上是如何計費的？與主對話共用 token 預算，還是獨立計算？在大量使用 `/batch` 產生數百個子代理時，成本控制機制為何？（建議搜尋：`Claude Code context fork token billing subagent cost`）
- Skill 的「字元預算（2% of context window）」在多個 skill 競爭時是否有優先順序機制？如何確保關鍵 skill 不被排除在 context 之外？（建議搜尋：`Claude Code skill context budget priority`）
- `agent` 欄位所提到的「內建代理人類型」（Explore、Plan、general-purpose）之間有何具體能力差異？官方是否有各類型的能力基準測試（Benchmark）？（建議搜尋：`Claude Code built-in agent types Explore Plan capabilities`）
- Plugin skills 的 `plugin-name:skill-name` 命名空間機制，與企業級 skill 的衝突解決優先順序文件在哪裡？當 plugin skill 和 enterprise skill 有相同觸發描述時，哪個優先？（建議搜尋：`Claude Code plugin skill enterprise skill priority conflict`）
- `!`command`` 動態注入語法的安全性如何？若 skill 被惡意改寫，是否存在命令注入（Command Injection）風險？官方的 skill 驗證機制是否有針對此風險的防護？（建議搜尋：`Claude Code skill dynamic context injection security`）
- `disable-model-invocation: true` 的執行語意是「Claude 不會自動觸發」，但若使用者在對話中間接暗示觸發條件，Claude 是否仍有可能執行？這個控制的邊界條件為何？（建議搜尋：`Claude Code disable-model-invocation edge case`）

## 相關連結（Related）

- [[SKILL-MD-SPECIFICATION]] — SKILL.md 格式規格完整參考
- [[AGENT-SKILL-PATTERNS]] — 5 種代理人技能設計模式（Tool Wrapper、Generator、Reviewer、Inversion、Pipeline）
- [[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]] — 如何用 skill-creator 評估和迭代改善 skill
- [[CLAUDE-CODE-SUBAGENTS]] — Claude Code subagents 架構，與 `context: fork` 搭配使用
- [[2026-03-07-CLAUDE-SKILLS-2.0-THE-SELF-IMPROVING-AI-CAPABILITIES-THAT-ACTUALLY-WORK]] — Skills 2.0 的回饋循環與自我改善機制，是本文 skill 系統的進階實踐
- [[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]] — npx skills CLI 深度分析，展示 parseSource/discoverSkills/installSkillForAgent 如何管理外部 skill
- [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] — Skills 與 CLAUDE.md 的分工策略比較，含 Vercel 實驗數據與混合架構建議
- [[2026-03-31-AI-WORKFLOW-AGENTS-SKILLS-STANDARDS]] — Agents/Skills/Standards 三層式架構，將本文的 skill 機制放入組織級工作流設計
- [[2026-04-12-HARNESS-ENGINEERING-HUNGYI-LEE-NTU-LLM-GUIDANCE]] — 李宏毅講解的工作流程控制概念，在 Claude Code Skills 中得到實踐
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — Skills 內部載入機制的原始碼分析：chokidar 監控 + lazy load 實現熱載入
- [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]] — Vercel 實驗證明 skills 自動觸發 56% 未被調用，提出 /docs/ 引用作為替代方案
- [[2026-01-27-VERCEL-AGENTS-MD-OUTPERFORMS-SKILLS-IN-AGENT-EVALS]] — Vercel 原始實驗：skills 預設行為 0% 改善、56% 未調用，挑戰 skills 自動觸發可靠性
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — Skills vs Commands vs Subagents 完整比較，含 frontmatter 控制矩陣與 description 工程實驗
- [[2026-04-25-CLAUDE-SKILLS-PLAYBOOK-DESCRIPTION-SUBAGENT-DEBUG-PROMPTS]] — Gary Chen 的 Skill 實戰手冊，含 Description 五類範例、三層除錯 Playbook 與完整維護迭代節奏
- [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] — context:fork、agent、hooks 三個進階 frontmatter 欄位的原始碼解析與 FAQ
- [[2026-03-23-GRILL-ME-SKILL-DEEP-DIVE]] — 428-byte 的 grill-me skill 是 Claude Code skill 規範的極簡實踐範例
- [[2026-08-14-CLAUDE-CODE-SKILL-BUDGET-MECHANISM-AND-REDUCTION-FLOW]] — 官方文件所述 listing 預算／compaction 保留機制的原始碼核實與 200K/1M 實算

## References

- [原文](https://code.claude.com/docs/en/skills)

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | SKILL.md、`disable-model-invocation: true`、`user-invocable: false`、`context: fork`、`allowed-tools`、`$ARGUMENTS`、`${CLAUDE_SKILL_DIR}`、`${CLAUDE_SESSION_ID}`、`!`command`` 動態注入語法、Skill 字元預算（上下文視窗的 2%）、內建 Skills（`/batch`、`/simplify`、`/loop`、`/debug`、`/claude-api`）、四層存放位置（Enterprise/Personal/Project/Plugin）、`CLAUDE_PLUGIN_DATA` |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Claude Code Skills 系統的設計邏輯建立在「控制誰在何時看到什麼」這個核心上：`disable-model-invocation` 控制觸發主體（人 vs. 模型），`context: fork` 控制執行隔離程度，`allowed-tools` 控制工具存取範圍，而 `!`command`` 語法讓 skill 在執行前先完成資料準備，避免讓模型在對話中多一次工具呼叫。四層存放位置（Enterprise→Personal→Project→Plugin）形成優先順序明確的繼承結構，讓組織可以強制執行標準，個人可以客製化，專案可以覆蓋。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 1. `disable-model-invocation: true` 和 `user-invocable: false` 的命名方式讓兩者的行為邊界容易混淆——前者防止 Claude 自動觸發，後者隱藏選單可見性但不阻止程式化呼叫，這個設計可能導致安全假設錯誤；2. Skill 字元預算（2% of context window）是動態的，意味著當模型版本或 context window 大小改變時，哪些 skill 被包含的結果也會不同，這種隱性不確定性在生產環境中難以預測；3. `!`command`` 動態注入在 skill 被惡意篡改時是命令注入（Command Injection）的潛在向量，但文件對此風險著墨極少。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. 對所有有副作用的 skills（deploy、commit、send-message）加上 `disable-model-invocation: true`，確保只有明確的 `/skill-name` 呼叫才能觸發；2. 利用 `context: fork` + `agent: Explore` 建立唯讀研究 skill，既不汙染主對話又能安全探索程式碼庫；3. 定期執行 `/context` 指令確認所有 skills 都在字元預算內，避免關鍵 skill 被靜默排除。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | Claude Code Skills 系統相較於直接使用 CLAUDE.md 的優勢在於可組合性與精細控制，但複雜性顯著更高（frontmatter 選項多、行為模式細微差異需要熟悉）。內建的 `/batch` skill 可以生成平行子代理人，這是最強大但也最昂貴的功能，在預算有限時應謹慎使用。對比自建工具鏈：若已有 CI/CD 系統，維運手冊型 skill（Runbook skills）可以取代部分人工操作；但若組織缺乏 Claude Code 的使用文化，skill 的維護成本（Gotchas 更新、字元預算監控）可能超過其帶來的效率收益。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：`context: fork` 讓 skill 在「隔離的子代理人上下文中執行，不共用對話歷史」——這個隔離在計費層面是否也是獨立的？若子代理人的 token 使用算在主對話的預算裡，「隔離」的語義是否會讓使用者誤解成本邊界？
- **假設**：文章假設「description 欄位讓 Claude 判斷何時套用 skill」是可靠的觸發機制，但這個機制的可靠性本質上依賴模型的語義理解，而非確定性邏輯。在高可靠性需求場景（如自動部署），這個假設是否過於樂觀？
- **證據**：「Skill 描述的字元預算動態為上下文視窗的 2%，預設後備為 16,000 字元」——這個設計決策的依據是什麼？是基於實驗數據還是工程估算？當 skill 數量增加時，2% 是否足夠？
- **觀點**：從企業資安角度，`!`command`` 動態注入語法允許 skill 在執行前運行任意 shell 指令。若 skill 檔案被篡改（如供應鏈攻擊），這個機制是否成為攻擊面？官方對此有無沙盒或驗簽機制？
- **後果**：若 `/batch` skill 被廣泛用於生成數十個平行子代理人，Claude Code 的計費模式在大規模使用下會如何影響組織的 AI 採用決策？Token 成本的不可預測性是否會成為企業推廣的障礙？
