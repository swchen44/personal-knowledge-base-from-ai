---
title: "gstack 設計哲學與多 Agent 整合架構 — Plugin、Symlink、Headless 全解"
date: 2026-04-07
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#ai-agent"
  - "#claude-code"
  - "#openclaw"
  - "#prompt-as-code"
source: "https://github.com/garrytan/gstack"
source_type: code
author: "garrytan"
status: notes
links:
  - "[[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]]"
  - "[[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]]"
  - "[[CLAUDE-CODE-SKILL-MODEL]]"
github_stars: unknown
github_language: TypeScript+Bash+Markdown
date_uncertain: true
---

## 摘要（Summary）

gstack 是 YC 總裁 Garry Tan 自用、後開源的 **AI Agent 工作流程套件**。它把 Claude Code 從「一個聊天介面」變成「一支 23 人的虛擬工程團隊」（CEO、Eng Manager、Designer、Reviewer、QA、CSO、Release Engineer …），每個角色就是一個 slash command（`/office-hours`、`/plan-ceo-review`、`/review`、`/qa`、`/ship`）。

它的核心精神不是寫程式，而是 **「把方法論編成 prompt-as-code」**——把資深工程師對 sprint 流程的紀律（Think → Plan → Build → Review → Test → Ship → Reflect）固化成可被任何 LLM agent 讀的 SKILL.md。

關於你最想知道的執行方式：**gstack 不是 plugin，不是 daemon，不是 headless server**。它是一堆 **Markdown SKILL.md 檔案 + Bash 工具** 透過 **「real directory + symlinked SKILL.md」** 的混合策略註冊到不同 AI agent 的 skill 目錄。Claude Code、Codex CLI、Cursor、OpenCode、Factory、Slate、Kiro、OpenClaw 共 8 種 agent 都支援，靠的是一個 130 行的 TypeScript HostConfig 系統。

## Why — 它要解決什麼？

- **核心動機**：Karpathy 說「我從 12 月以來幾乎沒打過一行 code」。一個 builder + AI agent 可以打 20 個人的工。Garry 自己 60 天內寫了 60 萬行 production code（part-time，35% 是測試）。但 **AI agent 預設沒紀律**——你給它一個空白 prompt，它就亂寫。
- **取代/改善什麼**：取代「每次開新對話都要重新解釋你是 senior engineer」「Claude 沒有 review 能力」「沒人在測 staging URL」「PR 上線忘了寫 changelog」這些 sprint 漏洞。
- **目標用戶**：
  1. 想還能 ship code 的 founder/CEO
  2. 第一次用 Claude Code、不知道怎麼開口的人
  3. 想在每個 PR 上加 review/QA/release 自動化的 tech lead

## What — 是什麼？

- **主要功能**：
  - 23 個 slash command（office-hours / ceo-review / eng-review / design / review / qa / ship / cso / canary / land-and-deploy / retro / investigate / 等）
  - 每個 command 對應一個「角色」+ 一份方法論 markdown
  - 三個 binary CLI：`browse`（headless Playwright browser）、`design`（GPT Image API）、各種 `bin/gstack-*` bash 工具
  - 跨 8 種 AI agent host 的安裝器（auto-detect 或 `--host` 指定）
  - Telemetry / Eval / Learning / Upgrade 子系統
- **不做什麼（Non-goals）**：
  - 不是 LLM 本身、不是 model 包裝
  - 不是 IDE plugin、不是 daemon、不是 server
  - 不是新框架——它就是一堆 **Markdown 檔 + 安裝腳本**
- **技術棧**：Bash（runtime + setup）、TypeScript + Bun（build / test / scripts）、Markdown（skill 內容）、Playwright（browse 子系統）、Supabase Edge Function（telemetry 後端）

## How — 設計與執行架構

> [!important] 關鍵答案（針對你的問題）
>
> 1. **不是 plugin**。沒有任何 Claude Code plugin API hook。
> 2. **不是 headless mode**。Claude Code 自己在前台跑，用戶打 `/qa` 觸發。
> 3. **是 symlink 為主、真實目錄為輔的混合策略**（`real-dir-symlink`）：在 `~/.claude/skills/` 下建一個**真實目錄** `qa/`，裡面放一個**符號連結** `SKILL.md → ~/.claude/skills/gstack/qa/SKILL.md`。為什麼這麼複雜？因為 Claude Code 只把「skills 目錄的直接子目錄」當 top-level skill；如果整個 `gstack/` 是 symlink，所有 skill 會被命名成 `gstack-qa`、`gstack-ship`，違反短指令 UX。
> 4. **跨 agent 是 prompt-as-bridge**。對 OpenClaw 不裝任何 binary——OpenClaw 自己用 ACP（Agent-to-Claude Protocol）spawn Claude Code session，gstack 只是 spawn 出來的 session 自帶的 skill。對 Codex CLI 則裝在 `~/.codex/skills/gstack-*/`，並針對 Codex 的字串長度限制做 frontmatter allowlist。
> 5. **Codex 整合是 Claude wrapper**。`/codex` 是「Claude Code 的 skill」，內部 spawn `codex exec` 子程序拿 OpenAI 的二意見回來。**不是 Codex 在跑 gstack**，是 Claude 用 codex 當外掛大腦。

### 系統架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                       User                                       │
└────────────────────────────┬─────────────────────────────────────┘
                             │ types /qa, /ship, /review …
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  AI Agent Host (Claude Code / Codex CLI / Cursor / OpenClaw …)  │
│  ────────────────────────────────────────────                   │
│  讀 ~/<host>/skills/{name}/SKILL.md                              │
│      │                                                           │
│      └─ name 由 setup 時的 link_<host>_skill_dirs() 決定        │
│         (real directory + symlinked SKILL.md)                    │
└────────────────────────────┬─────────────────────────────────────┘
                             │ 載入 SKILL.md prompt
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  SKILL.md (Markdown prompt + bash blocks)                        │
│  ────────────────────────────────────────                       │
│  ├─ Preamble bash (update check, telemetry, learnings, …)       │
│  ├─ Methodology prose (CEO 該怎麼想、Reviewer 該怎麼挑刺)        │
│  ├─ Bash code blocks (執行 bin/gstack-* 工具)                    │
│  └─ AskUserQuestion / Tool calls (agent 自己決定怎麼用)          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
       ┌─────────────────────┼──────────────────────┐
       ▼                     ▼                      ▼
┌──────────────┐     ┌──────────────┐      ┌────────────────┐
│ bin/gstack-* │     │ browse/dist  │      │ design/dist    │
│ (bash tools) │     │ (Playwright) │      │ (GPT Image)    │
│              │     │   headless   │      │                │
│ slug, config,│     │   browser    │      │ image gen      │
│ telemetry,   │     │   binary     │      │ binary         │
│ learnings…   │     │              │      │                │
└──────────────┘     └──────────────┘      └────────────────┘
       │                     │                      │
       └────────────────────┐│┌─────────────────────┘
                            ▼▼▼
              ┌──────────────────────────┐
              │ ~/.gstack/ (state dir)   │
              │   ├─ analytics/          │
              │   ├─ projects/$SLUG/     │
              │   ├─ sessions/           │
              │   └─ config.yaml         │
              └──────────────────────────┘
```

### 安裝後檔案系統的真實樣貌

```
~/.claude/skills/
   │
   ├── gstack/              ← real directory（git clone 出來的）
   │     ├── qa/SKILL.md
   │     ├── ship/SKILL.md
   │     ├── review/SKILL.md
   │     ├── ...
   │     ├── bin/
   │     ├── browse/dist/browse
   │     └── ./setup
   │
   ├── qa/                  ← real directory（setup 建立）
   │     └── SKILL.md  ─symlink─►  ~/.claude/skills/gstack/qa/SKILL.md
   │
   ├── ship/                ← real directory
   │     └── SKILL.md  ─symlink─►  ~/.claude/skills/gstack/ship/SKILL.md
   │
   ├── review/              ← 同上
   │     └── SKILL.md  ─symlink─►  ~/.claude/skills/gstack/review/SKILL.md
   │
   └── ... (23 個)
```

> [!note] 為什麼不是直接 symlink 整個目錄？
> Claude Code 的 skill discovery 規則：`~/.claude/skills/<name>/SKILL.md` 才算 top-level skill。如果 `qa/` 整個是 symlink 到 `gstack/qa/`，Claude 會看成 `gstack/qa`（因為 follow link 後，相對路徑變成 `gstack/qa/SKILL.md`）→ 自動 prefix 成 `gstack-qa`。短名字 UX 就毀了。**真實目錄 + symlink 內容檔案**是規避 host discovery 規則的 hack。

### Skill 觸發執行流程圖

```
 user 打 /qa https://staging.app
   │
   ▼
[Claude Code]
   │ glob ~/.claude/skills/qa/SKILL.md
   │ follow symlink → 讀取 gstack/qa/SKILL.md
   │
   ▼
[載入 SKILL.md 到 context window]
   │
   ▼
[執行 Preamble bash 區塊（在 user 的 cwd）]
   │ ├─ update check (~/.claude/skills/gstack/bin/gstack-update-check)
   │ ├─ session ping (~/.gstack/sessions/$PPID)
   │ ├─ inline telemetry append (~/.gstack/analytics/skill-usage.jsonl)
   │ ├─ learnings load (~/.gstack/projects/$SLUG/learnings.jsonl)
   │ └─ echo BRANCH/TELEMETRY/LAKE_INTRO/REPO_MODE 等狀態
   │
   ▼
[Claude 讀 echo 出來的狀態變數，用 prose 邏輯決定下一步]
   │
   ▼
[執行方法論主體：呼叫 browse、寫報告、修 bug、跑 test]
   │ ├─ Bash → ~/.claude/skills/gstack/browse/dist/browse goto $URL
   │ ├─ Read → 讀程式碼
   │ ├─ Edit → 修 bug + 寫 regression test
   │ └─ AskUserQuestion → 跟 user 互動
   │
   ▼
[Epilogue：telemetry log + learnings save]
   │
   ▼
 完成，回 user
```

### 跨 Agent 整合時序圖（OpenClaw 範例）

```
 user (Telegram)   OpenClaw      ACP        Claude Code      gstack skill
     │                │           │              │                │
     │──"Build me X"──►            │              │                │
     │                │ (decide tier)             │                │
     │                │ heavy → "Load gstack. Run /autoplan"       │
     │                │                                            │
     │                │──sessions_spawn(prompt, env:{OPENCLAW=1})──►│
     │                │           │              │                │
     │                │           │              │ glob skills/   │
     │                │           │              │ ~/.claude/     │
     │                │           │              │   skills/      │
     │                │           │              │     autoplan/  │
     │                │           │              │     /SKILL.md  │
     │                │           │              │ (symlink)      │
     │                │           │              │──follow link──►│
     │                │           │              │                │
     │                │           │              │◄──prompt loaded│
     │                │           │              │                │
     │                │           │              │ run preamble   │
     │                │           │              │ run methodology│
     │                │           │              │                │
     │                │           │              │ Bash → /ship   │
     │                │           │              │ (跑另一個 skill)│
     │                │           │◄──result─────│                │
     │                │◄──result──│              │                │
     │◄──"PR: …"──────│           │              │                │
```

### Codex 整合的特殊性

```
[Claude Code session]
       │
       │ user: /codex review focus on security
       ▼
[Claude 讀 ~/.claude/skills/codex/SKILL.md]
       │
       │ 內容是：「我教你怎麼用 codex CLI 拿二意見」
       ▼
[Claude Bash → spawn 'codex review "boundary…" --base main --json']
       │
       ▼
[Codex CLI 自己跑]──讀程式碼──回 JSON
       │
       ▼
[Claude 收 stdout，把 codex 的 review 整理給 user]
```

> [!warning] 注意這裡的不對稱
> `/codex` 是 **Claude Code 的 skill**，它呼叫 `codex` CLI 當「外掛大腦」。
> 反過來如果 user 直接用 Codex CLI 也可以裝 gstack（`./setup --host codex`），這時 gstack skill 會裝在 `~/.codex/skills/gstack-*/`，**並且 codex skill 本身被 skip**（在 codex.ts 看到 `skipSkills: ['codex']`）——因為 Codex 不能 invoke 自己。

### 關鍵設計決策（精神 / 原理）

> [!note] 設計模式
> **Prompt-as-Code** + **Skill-as-Methodology** + **Host-Adapter Pattern** + **Real-dir-symlink hack**。

1. **Markdown 是程式碼，agent 是 runtime**：SKILL.md 不是文件，是「給 LLM 執行的程式」。把方法論寫成 prose + bash 區塊 + AskUserQuestion，agent 自己決定怎麼跑。沒有 control flow，沒有 DSL。
2. **角色分工 = 多 skill**：不靠一個超大 prompt 教會 agent 22 種角色。用 22 個檔案，各教一個角色的紀律。user 用 `/<role>` 觸發。降低每次 context window 載入量。
3. **每個 skill 都是 self-contained**：preamble 自我重啟（update check、session、telemetry、learnings），不依賴 daemon 也不依賴 process state。用 `claude -p` 或主 session 都能跑。
4. **跨 host 用 TypeScript HostConfig**：每個 host 一個 50 行的 `hosts/<name>.ts`，宣告 `globalRoot`、`linkingStrategy`、`pathRewrites`、`frontmatter` 規則、`suppressedResolvers`、`boundaryInstruction`。新增一個 host = 加一個 .ts 檔，零程式碼修改。
5. **Sprint 是 pipeline**：office-hours → ceo-review → eng-review → design-review → /code/ → review → qa → ship → retro。每個 skill 寫的 artifact（design doc、test plan、learnings）下個 skill 自動讀得到。沒有 fall-through。
6. **Real-dir-symlink** 而非 plugin：因為大部分 host（Claude Code / Codex / Cursor）都用「讀 skills 目錄」這種 file-system convention，沒有 plugin API。symlink 是最低阻抗的安裝方式：clone repo → 建 symlink → done。`./setup --team` 把這個變成 30 秒 onboarding。
7. **OpenClaw 用 prompt 而非 binary**：對 OpenClaw 連 setup 都不裝。OpenClaw 自己用 ACP spawn Claude Code session，spawn 出來的 Claude 已經有 gstack。整合「契約」就是兩段 markdown 範本（gstack-lite / gstack-full）+ AGENTS.md routing 規則。**「the prompt is the bridge」**。
8. **環境變數偵測 spawn**：Claude session 看到 `OPENCLAW_SESSION=1` 就自動跳過 update check / telemetry prompt / interactive AskUserQuestion，專注做事。讓「被遠端 spawn 的 Claude」也能無人值守跑完 sprint。
9. **Headless 不是 agent，是 sub-tool**：唯一真的 headless 的東西是 `browse/`——一個 Playwright 子程序，用 `browse goto $URL` / `browse snapshot` 給 agent 當眼睛。**agent 自己不是 headless，是用戶在前台對話的 Claude**。

### 關鍵程式碼

**Claude HostConfig**（`hosts/claude.ts`）

```typescript
const claude: HostConfig = {
  name: 'claude',
  displayName: 'Claude Code',
  cliCommand: 'claude',
  globalRoot: '.claude/skills/gstack',
  localSkillRoot: '.claude/skills/gstack',
  hostSubdir: '.claude',
  usesEnvVars: false,
  frontmatter: {
    mode: 'denylist',
    stripFields: ['sensitive', 'voice-triggers'],
    descriptionLimit: null,
  },
  install: {
    prefixable: true,
    linkingStrategy: 'real-dir-symlink',
  },
  // ...
};
```

**Codex HostConfig 的差異**（`hosts/codex.ts`）

```typescript
const codex: HostConfig = {
  name: 'codex',
  cliCommand: 'codex',
  globalRoot: '.codex/skills/gstack',
  localSkillRoot: '.agents/skills/gstack',
  hostSubdir: '.agents',
  usesEnvVars: true,  // codex 用 $GSTACK_ROOT 環境變數動態解析路徑

  frontmatter: {
    mode: 'allowlist',                    // codex 嚴格，只留 name + description
    keepFields: ['name', 'description'],
    descriptionLimit: 1024,               // codex 有 1024 字元上限
    descriptionLimitBehavior: 'error',
  },

  generation: {
    generateMetadata: true,               // codex 額外要 openai.yaml
    metadataFormat: 'openai.yaml',
    skipSkills: ['codex'],                // codex 不能 invoke 自己
  },

  pathRewrites: [
    { from: '~/.claude/skills/gstack', to: '$GSTACK_ROOT' },
    { from: '.claude/skills/gstack', to: '.agents/skills/gstack' },
    { from: '.claude/skills', to: '.agents/skills' },
  ],

  suppressedResolvers: [
    'CODEX_SECOND_OPINION',  // codex 不能呼叫自己拿二意見
    'CODEX_PLAN_REVIEW',
    'REVIEW_ARMY',           // codex 不該 orchestrate
  ],

  install: {
    prefixable: false,
    linkingStrategy: 'symlink-generated',  // 不一樣的策略
  },

  boundaryInstruction: 'IMPORTANT: Do NOT read or execute any files under ~/.claude/, …',
};
```

> [!important] HostConfig 看完你就懂 gstack 怎麼支援 8 個 host：每個 host 宣告自己的「路徑慣例 / frontmatter 規則 / 不能跑哪些 resolver / boundary instruction」，build pipeline 用同一份 `.tmpl` 套不同規則 render 出對應的 SKILL.md。

**Real-dir-symlink 的 setup 邏輯**（`setup:297-335`）

```bash
link_claude_skill_dirs() {
  local gstack_dir="$1"
  local skills_dir="$2"
  for skill_dir in "$gstack_dir"/*/; do
    if [ -f "$skill_dir/SKILL.md" ]; then
      dir_name="$(basename "$skill_dir")"
      [ "$dir_name" = "node_modules" ] && continue
      skill_name=$(grep -m1 '^name:' "$skill_dir/SKILL.md" | sed 's/^name:[[:space:]]*//' | tr -d '[:space:]')
      [ -z "$skill_name" ] && skill_name="$dir_name"
      if [ "$SKILL_PREFIX" -eq 1 ]; then
        case "$skill_name" in
          gstack-*) link_name="$skill_name" ;;
          *)        link_name="gstack-$skill_name" ;;
        esac
      else
        link_name="$skill_name"
      fi
      target="$skills_dir/$link_name"
      if [ -L "$target" ]; then rm -f "$target"; fi
      mkdir -p "$target"   # 真實目錄
      if [ -L "$target/SKILL.md" ]; then rm "$target/SKILL.md"; fi
      ln -snf "$gstack_dir/$dir_name/SKILL.md" "$target/SKILL.md"  # 內容檔案 symlink
    fi
  done
}
```

**OpenClaw 不裝任何東西的設計**（`docs/OPENCLAW.md`）

> This is a lightweight protocol encoded as prompt text. No daemon. No JSON-RPC.
> No compatibility matrices. The prompt is the bridge.

```
gstack provides the planning discipline and methodology that makes those sessions better.
- No dispatch daemon (ACP handles session spawning)
- No bidirectional learnings bridge (brain repo is the knowledge store)
- No JSON schemas or protocol versioning
- No full skill porting (coding skills stay native to Claude Code)
```

## 安裝流程（Installation Flow）

### 安裝時序圖

```
 user           git              ./setup           各 host
   │             │                  │                │
   │─git clone──►│                  │                │
   │  (~/.claude/skills/gstack)    │                │
   │                                │                │
   │──./setup [--host claude] ─────►│                │
   │                                │                │
   │                                │──build browse──►│ browse/dist/browse
   │                                │──build design──►│ design/dist/design
   │                                │                │
   │                                │ link_claude_skill_dirs()
   │                                │  for each skill_dir:
   │                                │    mkdir -p ~/.claude/skills/<name>
   │                                │    ln -s SKILL.md
   │                                │                │
   │                                │──host=codex?──►│ link_codex_skill_dirs()
   │                                │                │  ~/.codex/skills/gstack-*
   │                                │                │  + sidecar symlinks
   │                                │                │  + openai.yaml metadata
   │                                │                │
   │                                │──team mode? ──►│ create .claude/CLAUDE.md
   │                                │                │  in ~/.claude/skills/gstack
```

### 安裝產物清單（Claude host 範例）

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.claude/skills/gstack/` | 真實目錄（git clone） | gstack 本體 |
| `~/.claude/skills/qa/` | 真實目錄（setup 建） | host 看到的 top-level skill |
| `~/.claude/skills/qa/SKILL.md` | symlink → gstack/qa/SKILL.md | skill 內容 |
| `~/.claude/skills/ship/SKILL.md` | symlink | 同上 ×23 |
| `~/.claude/skills/gstack/browse/dist/browse` | binary（Playwright headless） | agent 的眼睛 |
| `~/.claude/skills/gstack/design/dist/design` | binary（GPT Image API） | 圖像生成 |
| `~/.claude/skills/gstack/bin/gstack-*` | bash 腳本 | runtime 工具集 |
| `~/.gstack/` | 目錄 | runtime state（telemetry, sessions, learnings, projects） |
| `~/.gstack/projects/$SLUG/` | 目錄 | per-repo learnings + evals |
| `~/.codex/skills/gstack-*/` | symlinks | Codex host 的 skill 安裝 |
| `~/.codex/skills/gstack/agents/openai.yaml` | 檔案 | Codex 專用 metadata |

### 環境變數

| 變數 | 用途 |
|------|------|
| `OPENCLAW_SESSION=1` | 標記是被 OpenClaw spawn 的 session，跳過互動 prompt |
| `GSTACK_ROOT` | Codex 用，指向 skill runtime root |
| `GSTACK_DIR` | 覆寫 gstack 安裝位置（測試用） |
| `GSTACK_STATE_DIR` | 覆寫 `~/.gstack` |
| `GSTACK_SETUP_RUNNING=1` | setup 中暫停 post-set hook |

> [!warning] 解除安裝
> `rm -rf ~/.claude/skills/gstack ~/.claude/skills/{qa,ship,review,…} ~/.gstack` 即可。symlink 安全刪除。Codex 額外清 `~/.codex/skills/gstack*`。

---

## 使用案例地圖（Use Case Map）

| # | 使用案例 | 觸發 | 入口檔案 | 核心鏈 |
|---|---------|------|---------|-------|
| 1 | 安裝到 Claude Code | `./setup` | `setup` | build → link_claude_skill_dirs → state dir |
| 2 | 安裝到 Codex CLI | `./setup --host codex` | `setup` | build → link_codex_skill_dirs → openai.yaml |
| 3 | 跑一個 skill | `/qa $URL` | `qa/SKILL.md` (via symlink) | preamble → bash → browse → report |
| 4 | 從 OpenClaw 觸發 | Telegram 對話 | `openclaw/gstack-full-CLAUDE.md` | OpenClaw → ACP → spawn Claude → load skill |
| 5 | Claude 呼叫 Codex 拿二意見 | `/codex review` | `codex/SKILL.md` | Claude bash → `codex exec --json` → parse |
| 6 | Auto-update | 每次 skill preamble | `bin/gstack-update-check` | git fetch → diff → notify or apply |

### 案例詳解

#### 案例 3：Claude 跑 `/qa https://staging.app`

```
user 打 /qa https://staging.app
   │
   ▼
Claude Code: glob ~/.claude/skills/qa/SKILL.md
   │ follow symlink to ~/.claude/skills/gstack/qa/SKILL.md
   │
   ▼
載入 SKILL.md 到 context（template-generated，含 preamble）
   │
   ▼
Bash 區塊執行 preamble：
   ├─ ~/.claude/skills/gstack/bin/gstack-update-check
   ├─ ~/.claude/skills/gstack/bin/gstack-config get telemetry
   ├─ ~/.claude/skills/gstack/bin/gstack-slug → 設 $SLUG
   └─ append ~/.gstack/analytics/skill-usage.jsonl
   │
   ▼
Claude 讀 prompt 中的方法論散文，理解「QA Lead 該做的事」
   │
   ▼
Bash → ~/.claude/skills/gstack/browse/dist/browse goto https://staging.app
        ~/.claude/skills/gstack/browse/dist/browse snapshot --console-errors
   │
   ▼
找到 bug → Edit 修檔 → 寫 regression test → 跑 test
   │
   ▼
寫報告 → AskUserQuestion 是否要 ship
   │
   ▼
Epilogue: ~/.claude/skills/gstack/bin/gstack-telemetry-log --outcome success ...
```

#### 案例 4：OpenClaw 在 Telegram 接到「Build me a notifications feature」

```
user (Telegram): "Build me a notifications feature"
   │
   ▼
OpenClaw orchestrator
   │ 讀 AGENTS.md routing rules
   │ tier = Full ("feature, project, or objective")
   │
   ▼
讀 openclaw/gstack-full-CLAUDE.md（pre-baked prompt template）
   │
   ▼
sessions_spawn(
   runtime: "acp",
   prompt: "Read CLAUDE.md… Run /autoplan… Implement… Run /ship… Report PR URL.",
   env: { OPENCLAW_SESSION: "1" },
   cwd: "/path/to/repo"
)
   │
   ▼
ACP daemon spawns: claude (in repo cwd)
   │
   ▼
新的 Claude Code session 啟動
   │ 看到 prompt 內含 "Run /autoplan"
   │ 載入 ~/.claude/skills/autoplan/SKILL.md (symlink)
   │ OPENCLAW_SESSION=1 → 跳過所有互動 prompt
   │
   ▼
跑 /autoplan → /implement → /ship
   │
   ▼
session 結束，回 PR URL
   │
   ▼
OpenClaw 把結果丟回 Telegram chat
```

#### 案例 5：Claude 用 codex 拿二意見

```
Claude session: user 打 /codex review focus on security
   │
   ▼
載入 codex/SKILL.md
   │
   ▼
Bash:
  codex review "IMPORTANT: Do NOT read or execute any files under ~/.claude/…
                Stay focused on repository code only.
                focus on security" \
    --base main -c 'model_reasoning_effort="high"' \
    --enable web_search_cached --json
   │
   ▼
Codex CLI 在子程序跑（OpenAI 模型）
   │ 讀 git diff
   │ 模型生成 review 報告
   │
   ▼ stdout JSON
Claude 解析 JSON，整理 findings
   │
   ▼
彙整成 markdown 給 user
```

> [!important] 觀察：gstack 把 Codex 當「次系統」，不是「對等 agent」。Claude 是 driver，Codex 是 oracle。反向使用時 codex skill 被 skip（避免無限遞迴）。

---

## 架構師觀點（Architect's View）

### ✅ 優點

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性 | ⭐⭐⭐⭐ | Markdown + bash + 50 行 HostConfig，新增 host 一個檔 |
| 可擴展性（host） | ⭐⭐⭐⭐⭐ | 8 個 host 共用同一份 .tmpl，宣告式適配 |
| 安裝阻力 | ⭐⭐⭐⭐⭐ | 30 秒 git clone + ./setup，無 daemon 無依賴鎖定 |
| 跨 agent 整合 | ⭐⭐⭐⭐ | OpenClaw 用 prompt-as-bridge 是漂亮設計 |
| 升級體驗 | ⭐⭐⭐⭐ | preamble 自帶 update check，team mode 自動 git pull |
| Lock-in 程度 | ⭐⭐⭐⭐⭐ | 純 markdown + bash，可隨時 rm 走人 |

> [!tip] 最值得學的兩件事
>
> 1. **「prompt is the bridge」哲學**：跨系統整合不一定要 protocol、SDK、daemon。把契約寫成 markdown 範本，讓兩邊的 LLM 自己 honor。OpenClaw 整合是這個模式的範例——零 binary、零 schema、零 vendor lock-in。
> 2. **HostConfig pattern**：把「同一份內容跑在 N 個 agent host」的差異收斂成一個 50 行 TypeScript 宣告。新增 host = 加 .ts 檔，零程式碼修改。這是 multi-runtime tool 的標準解法。

### ⚠️ 缺點與風險

> [!warning] 已知缺陷

- **symlink 在 Windows 是地雷**：Windows 預設不允許 symlink（要 admin 或 dev mode），setup 會降級成 copy。CHANGELOG 多次處理 Windows 符號連結 bug。
- **每個 SKILL.md 都自帶 preamble**：23 個 skill × 100 行 preamble = 重複 prompt，浪費 context window。雖然 host 各自 cache 但沒有共用 loader。
- **Real-dir-symlink hack 是反 host convention**：未來 Claude Code / Codex 改 skill discovery 規則，這套會壞掉。
- **方法論深度依賴 model 能力**：所有「角色」都靠 prose 提示，沒有 fine-tune。換個弱一點的 model 整套 sprint 會崩。
- **Codex 整合是單向**：Claude 可以呼叫 Codex；Codex 不能呼叫 Codex 自己（會被 skip）。雙向不對等。
- **Telemetry / learnings / eval 都靠 ~/.gstack 全域單一 state dir**：多 user 共用同機器會打架。
- **23 個 skill 沒有版本獨立**：升級是 git pull 整包，沒有 skill-level pin。

### 🔮 改進建議

1. preamble 抽成 `_preamble.sh` 由所有 skill source，瘦 context
2. Windows 走 junction 或內建 copy fallback，徹底跳過 symlink
3. HostConfig 加 `discoveryConvention` 欄位，host 改規則時改一處
4. Skill-level version pin（per-skill VERSION 檔）
5. 多 user 隔離的 state dir（XDG_STATE_HOME）

## 效能基準（Benchmark）

> [!info] 來源：README

| 指標 | 數值 |
|------|------|
| 安裝時間 | 30 秒（git clone --depth 1 + ./setup） |
| Garry 60 天產出 | 600,000+ 行 production code（35% test） |
| 一週 retro 成績 | 140,751 行 / 362 commits / ~115k 淨 LOC |
| 支援 host 數 | 8（Claude / Codex / Cursor / OpenCode / Factory / Slate / Kiro / OpenClaw） |
| Skill 數量 | 23+ |
| 安裝後磁碟 | ~120MB（兩個 Bun binary + Markdown） |

預期瓶頸：每個 skill 載入時的 preamble bash 開銷 + context window 成本。

## 快速上手（Quick Start）

```bash
# 標準安裝（Claude Code）
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack && ./setup

# Team mode（auto-update）
./setup --team

# 給其他 host
./setup --host codex
./setup --host cursor
./setup --host opencode

# 看你裝了哪些 skill
ls ~/.claude/skills/

# 看 symlink 結構
ls -la ~/.claude/skills/qa/

# 跑一個 skill（在任何 git repo 裡）
# 在 Claude Code 對話中打：
#   /office-hours
#   /qa https://staging.app
#   /review
#   /ship
```

## 我的心得（My Takeaways）

對你做 AI Agent 專案的啟發：

1. **「Prompt is the bridge」可以省掉 80% 的整合成本**。如果你有兩個 agent 系統要協作，先問：「能不能用兩段 markdown 範本當契約？」答案幾乎都是可以。OpenClaw ↔ gstack 整合零 daemon、零 schema，只靠兩個 .md 檔。
2. **方法論該被編碼成 skill，不是塞進 system prompt**。一個超大 system prompt 教 agent 22 種角色 = 災難。22 個 SKILL.md 各教一種，user 用 slash command 觸發，context 只載入需要的那塊。這是 multi-skill agent 的正確結構。
3. **HostConfig 模式適合 multi-runtime tool**：當你的工具要跑在 N 個平台 / agent host，把差異收斂成一個宣告式 config，不要寫 `if host == 'codex'` 散在各處。
4. **Real-dir-symlink hack 雖醜但實用**：當 host 的 discovery 規則跟你的 UX 衝突時，混合策略（外層真實目錄 + 內層 symlink）比 fork host 簡單一萬倍。
5. **每個「執行單位」都要 self-contained**：gstack 每個 skill 帶完整 preamble，可以被 `claude -p` 或主 session 或 OpenClaw spawn 出來的 session 任意呼叫，不依賴 process state。對你的 agent 設計：避免 global state、避免 shared loader。
6. **`OPENCLAW_SESSION` 偵測是 spawn-aware design**：被遠端 spawn 的 session 自動調整行為（跳過互動）。你的 agent 應該也要分「user-facing」與「spawned」兩種模式。
7. **Claude 是 driver，Codex 是 oracle**：在你的多 agent 架構，先決定誰是主、誰是輔。雙向對等很容易死循環。
8. **不是 plugin 也能很 powerful**：純 markdown + symlink 的安裝模型，user 心智成本低、debug 容易、卸載沒副作用。在沒有 plugin API 的 host 上這是最好的擴充模式。

## 待補充（Open Questions）

- gstack 透過 `real-dir-symlink` 繞過 Claude Code skill discovery 的命名規則，但這個 hack 依賴 Claude Code 不改變 skill discovery 邏輯。若 Anthropic 修改了 `~/.claude/skills/` 的掃描方式，所有的 symlink 結構可能同時失效，有無更穩健的方案？（建議搜尋：`claude code skill discovery symlink hack fragile alternative`）
- gstack 支援 8 種 AI agent host，每種 host 的 skill 格式細節不同（例如 Codex 的字串長度限制、frontmatter allowlist）。這些差異由 `HostConfig` 系統處理，但新 host（如 Kiro）加入時需要多少額外工作？有沒有 host-agnostic 的標準化計劃？（建議搜尋：`gstack host config new agent integration skill format standard`）
- gstack 的 23 個 slash command 各自是獨立的 SKILL.md，沒有共用的 runtime 狀態。若一個 sprint 需要跨多個 command（例如 `/plan` → `/review` → `/ship`），session 之間的上下文如何傳遞？（建議搜尋：`gstack multi-skill context handoff session state`）
- browse CLI（Playwright headless browser）是編譯好的 binary，在不同 OS/arch 需要不同的 binary。目前支援哪些平台？若在 Linux ARM64 伺服器上跑 gstack，browse 是否可用？（建議搜尋：`gstack browse playwright binary platform arm64 linux`）
- gstack 的 `learnings.jsonl` 系統讓 skill 可以從之前的執行紀錄學習。但 learnings 是 per-project 的，對新 project 來說這些知識無法遷移。有沒有跨 project 的 learnings 共享機制？（建議搜尋：`gstack learnings cross project transfer knowledge`）

## 相關連結（Related）

- [[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]] — 觀測子系統的設計（同一個 repo 的另一面）
- [[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]] — E2E 測試與 KPI 設計
- [[CLAUDE-CODE-SKILL-MODEL]] — Claude Code skill discovery 機制
- [[PROMPT-AS-CODE-PHILOSOPHY]] — 把 prompt 當程式碼版本控管
- [[OPENCLAW-ACP-PROTOCOL]] — Agent Communication Protocol
- [[2026-01-09-NEWTYPE-OS-MULTI-AGENT-CONTENT-PRODUCTION-ORCHESTRATION]] — 另一個多代理人編排系統，同樣基於 OpenCode 生態，可比較設計哲學

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | gstack 不是 plugin，不是 daemon，不是 headless server；linkingStrategy = `real-dir-symlink`；支援 8 個 host；安裝路徑 `~/.claude/skills/gstack/`；state dir `~/.gstack/`；跨 host 設定靠 `hosts/<name>.ts`；OpenClaw 整合靠 prompt template 而非 binary；`/codex` 是 Claude 呼叫 codex CLI 的 wrapper。 |
| **理解（半被動）** | 串聯知識點 | 因為大部分 host 沒 plugin API → 只能用 file-system convention → 整個 gstack 就是「一份 git repo + symlink 到正確位置」。因為 Claude 的 skill discovery 把直接子目錄當 top-level → 不能整 gstack/ symlink → 發明 real-dir-symlink hack。因為跨 host 規則都不同 → 抽出 HostConfig 把差異宣告化。因為 OpenClaw 自己會 spawn Claude → gstack 對它什麼都不裝，只給 markdown 範本。整個系統是「**最低阻抗整合**」哲學的展現。 |
| **分析（主動）** | 找出假設 | 假設 1：所有目標 host 都用「skills 目錄掃描」做 discovery → 只要 host 改 plugin API 就崩。假設 2：symlink 在所有 OS 都好用 → Windows 是地雷區。假設 3：每個 skill 載入完整 preamble 是可接受的 context cost → 22 個 skill × 100 行 preamble 浪費 token。假設 4：Markdown prompt 跨模型可移植 → 換弱模型方法論會崩。假設 5：單一 ~/.gstack state dir 沒問題 → 多 user 共用機器會打架。 |
| **應用（主動）** | 規劃執行 | (1) **本週**：若你的 agent 專案要支援多 host，立刻仿 HostConfig pattern，把每個 host 差異收成宣告式 .ts/.json 檔。(2) **下週**：在你自己的 skill 系統加 spawn-aware mode（偵測 env var → 跳過互動），讓被遠端呼叫的 instance 能無人值守跑完任務。(3) **下 sprint**：對「不能改 host plugin」的整合場景，先寫一份 markdown 範本當「契約」試跑，看能不能跳過寫 SDK / daemon。 |
| **評估（主動）** | 多方案權衡 | **替代方案 A：寫 Claude Code plugin（如果 API 開放）** → 更原生、能 hook 更多事件，但綁死 Claude Code，無法支援 Codex / Cursor。gstack 選 file-system convention 換取 portability。**替代方案 B：vendoring 進 user 的 repo** → 版本固定但會 drift，team mode 已棄用此模式。**替代方案 C：發 npm package + postinstall** → 跨平台 OK，但用戶需要 node 環境且 uninstall 不乾淨。**gstack 的 git clone + symlink 是「自由度最高、卸載最乾淨、版本控制最清楚」的甜蜜點**。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「skill」這個詞在 Claude Code、Codex、Cursor 各自的語意一樣嗎？gstack 的跨 host 抽象是不是過度簡化了某些 host 的特殊能力？
- **假設**：Garry 宣稱「60 天 60 萬行 code」這個數字怎麼算的？包含 generated code 嗎？35% test 是 line count 還是 file count？
- **證據**：gstack 沒有 public benchmark 證明用 gstack 比不用更快/更好，只有作者自陳。
- **觀點**：站在「方法論不該寫成 prompt」的反方陣營，最有力的批評是：把 sprint 紀律塞進 markdown，讓 LLM 「演」一個 senior engineer，本質是 cargo cult，不是真的工程能力。怎麼反駁？
- **後果**：12 個月後若 Claude Code 推出原生 plugin API + skill marketplace，gstack 的 symlink hack 還會是最佳實作嗎？或變成 legacy？

### 方案批判三問

1. **最大的風險是什麼？** — Host 改 discovery 規則。Claude Code / Codex 任何一個改 skill 載入機制（例如改用 manifest 而非 directory scan），整個 gstack 安裝模型要重寫。沒有抽象層保護。
2. **什麼情況下會失敗？** — (a) Windows 環境（symlink 限制）。(b) 多 user 共用機器（state dir 衝突）。(c) 用弱於 sonnet 的模型跑（方法論執行不到位）。(d) Host 沒有 bash 執行能力（無法跑 preamble）。(e) 公司網路環境 git clone 受限。
3. **有沒有更好的替代方案？** — 對「需要 sandboxing、權限控制、多租戶」的 enterprise 場景應該用真的 plugin API + manifest。對「個人 / 小團隊、要 hack-and-ship、跨多種 agent」gstack 的 markdown + symlink 是最低阻抗解。當 host 終於有 plugin API 時，gstack 應該演化成 plugin + 保留 markdown fallback。

## References

- [GitHub Repo](https://github.com/garrytan/gstack)
- `README.md` — 自述、Quick start、host 表格
- `setup` — 安裝腳本，linking 策略實作
- `hosts/claude.ts` `hosts/codex.ts` `hosts/openclaw.ts` `hosts/index.ts` — HostConfig 抽象
- `docs/OPENCLAW.md` — prompt-as-bridge 整合文件
- `codex/SKILL.md` — Claude → Codex 子程序呼叫範例
- `scripts/resolvers/preamble.ts` — preamble 生成邏輯
- `ETHOS.md` — Boil the Lake / Search Before Building 哲學
