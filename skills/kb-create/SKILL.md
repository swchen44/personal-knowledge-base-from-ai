---
name: kb-create
description: 讀取網頁文章（含需登入的頁面）或 YouTube 影片，翻譯成台灣繁體中文 Obsidian markdown 格式，連同圖片一起上傳到 GitHub 個人知識庫。自動維護雙向連結、LOG.md 日誌、INDEX.md 索引與 Open Questions。輸入一個 URL，自動完成全流程。
disable-model-invocation: false
argument-hint: <url>
---

將 $ARGUMENTS 存入個人知識庫，完整執行以下步驟。

> [!important] **URL 類型偵測**：請先判斷 `$ARGUMENTS` 的類型，再選擇對應流程：
> - **GitHub Repo URL**（如 `https://github.com/owner/repo`）→ 執行 **程式碼分析流程**（步驟 A1–A5），然後跳到步驟 3
> - **YouTube URL** → 步驟 1（YouTube 分支）→ 步驟 2 跳過 → 步驟 3 開始
> - **一般網頁文章** → 步驟 1（文章分支）→ 步驟 2 → 步驟 3 開始

---

## 環境變數

本 skill 依賴以下環境變數：

| 變數 | 用途 |
|------|------|
| `$GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub API 驗證 |
| `$KB_ROOT` | 個人知識庫本地 repo 路徑（如 `~/git/personal-knowledge-base-from-ai`） |
| `$KB_GITHUB_REPO` | 知識庫 GitHub repo（如 `swchen44/personal-knowledge-base-from-ai`） |

> [!warning] 執行前先驗證環境變數存在：
> ```bash
> : "${KB_ROOT:?需設定 KB_ROOT 環境變數}" \
>   "${KB_GITHUB_REPO:?需設定 KB_GITHUB_REPO 環境變數}" \
>   "${GITHUB_PERSONAL_ACCESS_TOKEN:?需設定 GITHUB_PERSONAL_ACCESS_TOKEN 環境變數}"
> ```

---

## 🔧 程式碼分析流程（GitHub Repo 專用）

> 僅當 `$ARGUMENTS` 為 GitHub Repo URL 時執行此區塊，完成後跳至步驟 3。

### 步驟 A1：Clone 目標 Repo 到暫存目錄

```bash
REPO_URL="$ARGUMENTS"
REPO_NAME=$(basename "$REPO_URL" .git)
TMP_CODE_DIR="/tmp/kb-code-$REPO_NAME"
# 暫存文章路徑：以 repo 名稱命名，避免多篇文章互相覆寫
TMP_ARTICLE="/tmp/kb-article-${REPO_NAME}.md"
TMP_ASSETS="/tmp/kb-assets-${REPO_NAME}"

# 淺層 clone（節省時間與空間）
git clone --depth=1 "$REPO_URL" "$TMP_CODE_DIR"
```

### 步驟 A2：收集 Repo 基本資訊

```bash
cd "$TMP_CODE_DIR"

# 取得語言統計
find . -name "*.py" -o -name "*.ts" -o -name "*.go" -o -name "*.rs" -o -name "*.java" \
  | grep -v node_modules | grep -v ".git" \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20

# 取得目錄結構（2層深）
find . -maxdepth 2 -not -path './.git*' -not -path './node_modules*' \
  | sort | head -60

# 讀取 README
cat README.md 2>/dev/null || cat README.rst 2>/dev/null || echo "無 README"

# 讀取主要設定檔
cat pyproject.toml 2>/dev/null
cat package.json 2>/dev/null
cat go.mod 2>/dev/null
cat Cargo.toml 2>/dev/null
cat pom.xml 2>/dev/null

# 統計程式碼行數
find . -name "*.py" -o -name "*.ts" -o -name "*.go" -o -name "*.rs" -o -name "*.java" \
  | grep -v node_modules | grep -v ".git" \
  | xargs wc -l 2>/dev/null | tail -1

# 讀取 CHANGELOG 或 release notes（了解演進歷史）
cat CHANGELOG.md 2>/dev/null | head -100
```

### 步驟 A3：深入分析核心程式碼

識別並閱讀關鍵檔案：

```bash
cd "$TMP_CODE_DIR"

# 找入口點（entry points）
find . -name "main.py" -o -name "main.go" -o -name "index.ts" -o -name "index.js" \
       -o -name "app.py" -o -name "server.py" -o -name "main.rs" \
  | grep -v node_modules | grep -v ".git" | head -5

# 找核心模組（排除 test/docs）
find . -name "*.py" -o -name "*.go" -o -name "*.ts" \
  | grep -v test | grep -v spec | grep -v docs | grep -v node_modules | grep -v ".git" \
  | head -20

# 找 benchmark / perf 相關測試
find . -name "*bench*" -o -name "*benchmark*" -o -name "*perf*" \
  | grep -v ".git" | head -10

# 找架構設計文件
find . -name "ARCHITECTURE*" -o -name "DESIGN*" -o -name "RFC*" \
  -o -name "ADR*" -o -path "*/docs/architecture*" \
  | grep -v ".git" | head -10
```

逐一閱讀上面找到的重要檔案，理解程式邏輯。

---

### 步驟 A3.5：安裝流程與使用案例追蹤

> [!important] 這是程式碼分析最關鍵的兩個維度：**「裝了什麼」** 與 **「用的時候動了什麼」**。
> 兩者都必須追蹤到具體的檔案層級，不能停在概念層。

#### A3.5a：安裝流程追蹤（Installation Flow）

找出所有與安裝/初始化相關的腳本與設定：

```bash
cd "$TMP_CODE_DIR"

# 找 package.json scripts（install、postinstall、setup、prepare）
cat package.json 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
scripts = d.get('scripts', {})
install_scripts = {k: v for k, v in scripts.items()
                   if any(kw in k for kw in ['install', 'setup', 'prepare', 'init', 'build'])}
for k, v in install_scripts.items():
    print(f'{k}: {v}')
" 2>/dev/null

# 找安裝腳本（installer、setup、init 相關）
find . -name "*install*" -o -name "*setup*" -o -name "*init*" -o -name "*postinstall*" \
  | grep -v node_modules | grep -v ".git" | grep -v ".md" | head -20

# 找「寫入目標目錄」的程式碼（fs.copyFile / shutil.copy / cp / writeFile 等）
grep -r "copyFile\|copy_tree\|shutil\.copy\|fs\.write\|writeFileSync\|mkdir.*-p\|cp -r" \
  --include="*.ts" --include="*.js" --include="*.py" --include="*.sh" \
  . | grep -v node_modules | grep -v ".git" | grep -v ".map" | head -30

# 找環境變數設定（什麼變數在安裝時被建立）
grep -r "process\.env\.\|os\.environ\|\$HOME\|\$XDG\|\.config\|\.local" \
  --include="*.ts" --include="*.js" --include="*.sh" \
  . | grep -v node_modules | grep -v ".git" | grep -v ".map" | head -20
```

逐一閱讀找到的安裝腳本，建立以下資訊：
- **安裝觸發點**：哪個指令啟動安裝（npm install、CLI 指令、腳本）
- **檔案寫入清單**：安裝後哪些路徑會有新檔案（絕對路徑層級）
- **環境變數**：安裝後設定了哪些 env vars
- **前置條件**：需要哪些依賴才能安裝成功

#### A3.5b：使用案例→檔案映射（Use Case → File Map）

從 README 或文件中找出所有主要使用案例，並追蹤每個案例的執行路徑：

```bash
cd "$TMP_CODE_DIR"

# 從 README 找使用案例關鍵字（命令、功能、use case 標題）
grep -E "^##|^###|\`[a-z].*\`|Usage|Example|Command|Quick Start" README.md \
  2>/dev/null | head -60

# 找 CLI 的命令定義（commander / argparse / cobra / clap）
grep -r "\.command\(\"\\|addCommand\|program\.command\|subcommand\|add_parser" \
  --include="*.ts" --include="*.js" --include="*.py" \
  . | grep -v node_modules | grep -v ".git" | grep -v test | head -30

# 找 Hook / Event 對應關係（event → handler）
grep -r "on(\|addEventListener\|register.*hook\|\.hook\|EventEmitter" \
  --include="*.ts" --include="*.js" \
  . | grep -v node_modules | grep -v ".git" | grep -v ".map" | head -20

# 找路由設定（router / routes / handlers）
find . -name "router*" -o -name "routes*" -o -name "handlers*" \
  | grep -v node_modules | grep -v ".git" | head -10
```

針對每個找到的主要使用案例，逐一追蹤：
1. **用戶觸發方式**（CLI 指令 / API 呼叫 / Hook 事件）
2. **入口檔案**（第一個被呼叫的檔案）
3. **核心處理鏈**（A → B → C，最多 5 層）
4. **輸出/副作用**（寫了什麼檔案、呼叫了什麼外部服務）

### 步驟 A4：查詢 GitHub API 取得補充資訊

```bash
# 從 URL 解析 owner/repo
GITHUB_OWNER=$(echo "$REPO_URL" | sed 's|https://github.com/||' | cut -d'/' -f1)
GITHUB_REPO=$(echo "$REPO_URL" | sed 's|https://github.com/||' | cut -d'/' -f2)

# 取得 repo 元資料（stars, forks, description, topics）
curl -s "https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Stars:', d.get('stargazers_count'))
print('Forks:', d.get('forks_count'))
print('Language:', d.get('language'))
print('Description:', d.get('description'))
print('Topics:', d.get('topics'))
print('Created:', d.get('created_at'))
print('Updated:', d.get('updated_at'))
print('License:', d.get('license', {}).get('name') if d.get('license') else 'None')
"

# 取得最新 releases
curl -s "https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/releases?per_page=3" \
  | python3 -c "
import sys, json
releases = json.load(sys.stdin)
for r in releases[:3]:
    print(r.get('tag_name'), '-', r.get('name'))
    print(r.get('body', '')[:300])
    print('---')
"

# 取得 issues / discussions 中的 benchmark 討論（選用）
curl -s "https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/issues?labels=performance,benchmark&state=all&per_page=5" \
  | python3 -c "
import sys, json
issues = json.load(sys.stdin)
for i in issues[:5]:
    print('#', i.get('number'), i.get('title'))
"
```

### 步驟 A5：合成分析報告，填入筆記模板

根據以上收集的資訊，撰寫完整的程式碼分析筆記，格式如下：

```markdown
---
title: "{Repo 名稱} — 程式碼深度分析"
date: {repo 建立或最新 release 日期}
category: CodeAnalysis
tags:
  - #code-analysis
  - #{主要程式語言}
  - #{領域，如 ai/framework、tools/cli、web/backend}
source: "{GitHub Repo URL}"
source_type: code
author: "{GitHub Owner/Org}"
status: notes
links:
  - "[[相關筆記1]]"
  - "[[相關筆記2]]"
github_stars: {star 數}
github_language: {主要語言}
---

## 摘要（Summary）
一段說明：這個 repo 是什麼、解決什麼問題、為何重要。

## Why — 為什麼存在？
> 這個專案要解決的根本問題是什麼？現有方案的哪些痛點促使它被創造？

- **核心動機**：...
- **取代/改善什麼**：...
- **目標用戶**：...

## What — 是什麼？
> 這個專案的功能邊界與核心能力。

- **主要功能**：
  - 功能一
  - 功能二
- **不做什麼（Non-goals）**：...
- **技術棧（Tech Stack）**：{語言、框架、主要依賴}

## How — 如何運作？

> [!important] 本節必須包含至少 **2 種 ASCII 圖表**，用 code block 呈現，讓讀者不看程式碼也能快速理解系統全貌。

### 系統架構圖（System Architecture）

用 ASCII art 描繪模組邊界與依賴關係：

```
{範例格式 — 請依實際架構替換}

┌─────────────────────────────────────────┐
│                  CLI / API              │
└──────────────────┬──────────────────────┘
                   │
       ┌───────────▼───────────┐
       │      Core Engine      │
       │  ┌─────┐  ┌────────┐  │
       │  │ A   │→│   B    │  │
       │  └─────┘  └────────┘  │
       └───────────┬───────────┘
                   │
       ┌───────────▼───────────┐
       │      Storage / IO     │
       └───────────────────────┘
```

### 執行流程圖（Execution Flowchart）

用 ASCII flowchart 描述主要執行路徑與分支：

```
{範例格式}

 Start
   │
   ▼
[讀取輸入] ──失敗──► [回報錯誤] ──► End
   │成功
   ▼
[處理步驟 A]
   │
   ├─ 條件 X ──► [路徑 X]
   │                  │
   └─ 條件 Y ──► [路徑 Y]
                      │
                      ▼
                  [合併結果]
                      │
                      ▼
                    End
```

### 時序圖（Sequence Diagram）

描述元件間的呼叫順序（適用於涉及多元件互動的系統）：

```
{範例格式}

 Client        Core         External API
   │             │                │
   │──請求──────►│                │
   │             │──查詢──────────►│
   │             │◄──回應─────────│
   │◄──結果──────│                │
   │             │                │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> 說明使用的核心設計模式與原因。

1. **決策一**：{描述} — {原因}
2. **決策二**：{描述} — {原因}

### 資料流（Data Flow）
1. 步驟一
2. 步驟二
3. 步驟三

### 關鍵程式碼（Key Code Snippets）

{摘錄最能說明設計理念的程式碼片段，完整保留不省略}

## 安裝流程（Installation Flow）

> [!info] 追蹤層級
> 本節追蹤到**具體檔案路徑**，而非停在概念層。讀者應能根據本節直接找到安裝後的產物。

### 安裝觸發方式

```
{安裝指令1} → {執行腳本} → {寫入路徑}
{安裝指令2} → {執行腳本} → {寫入路徑}
```

### 安裝時序圖

```
{安裝者}    {Package Manager}   {安裝腳本}        {目標系統}
    │               │                 │                 │
    │──install──────►│                 │                 │
    │               │──postinstall────►│                 │
    │               │                 │──寫入 A ────────►│ ~/.config/A
    │               │                 │──寫入 B ────────►│ ~/.local/B
    │               │                 │──patch C ───────►│ ~/.config/C
    │               │◄────────────────│                 │
    │◄──────────────│                 │                 │
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `{絕對路徑1}` | 檔案/目錄 | {用途說明} |
| `{絕對路徑2}` | 檔案/目錄 | {用途說明} |

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| `{VAR_NAME}` | `{值或描述}` | {安裝 / 執行時} |

> [!warning] 解除安裝
> 說明移除此工具需要手動清理哪些路徑（若文件有提及）。

---

## 使用案例地圖（Use Case Map）

> [!important] 本節針對每個主要使用案例，追蹤從**用戶觸發**到**最終效果**的完整檔案路徑。
> 是快速理解「用的時候動了什麼」的最直接索引。

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | {案例名稱} | `{指令/事件}` | `{入口檔案}` | `{A → B → C}` |
| 2 | {案例名稱} | `{指令/事件}` | `{入口檔案}` | `{A → B → C}` |

### 案例詳解

#### 案例 1：{名稱}

```
用戶：{觸發方式}
  │
  ▼
{入口檔案}:{函式名}
  │
  ▼
{核心模組 A}  ── 讀取 ──► {設定檔路徑}
  │
  ▼
{核心模組 B}  ── 寫入 ──► {輸出路徑}
  │
  ▼
{最終效果}
```

#### 案例 2：{名稱}

```
{同上格式}
```

> [!note] 閱讀建議
> 若要快速驗證某功能，從「入口檔案」欄直接跳去讀對應的源碼最有效率。

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | ... |
| 可擴展性（Scalability） | ⭐⭐⭐⭐ | ... |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐ | ... |
| 文件品質（Documentation） | ⭐⭐⭐⭐ | ... |
| 依賴管理（Dependency Management） | ⭐⭐⭐⭐ | ... |

> [!tip] 值得學習的設計
> 描述最值得借鏡的架構決策或程式碼品質。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> 列出架構層面的問題或技術債（Technical Debt）。

- **問題一**：{描述} — 影響：{影響}
- **問題二**：{描述} — 影響：{影響}

### 🔮 改進建議（Improvement Suggestions）
1. 建議一
2. 建議二

## 效能基準（Benchmark）

> [!info] 資料來源
> 說明 benchmark 數據來源（官方文件、issue、第三方評測）。

| 場景 | 此專案 | 競品 A | 競品 B |
|------|--------|--------|--------|
| 操作一 | {數值} | {數值} | {數值} |
| 操作二 | {數值} | {數值} | {數值} |

{若無公開 benchmark 數據，說明效能特性與預期瓶頸}

## 快速上手（Quick Start）

```bash
{最小可執行範例}
```

## 我的心得（My Takeaways）
我從這個 codebase 學到什麼？哪些設計可以應用到自己的專案？

## 待補充（Open Questions）
- {讀完後仍不清楚的問題}

## 相關連結（Related）
- [[RELATED-NOTE-1]] — 連結理由
- [[RELATED-NOTE-2]] — 連結理由
- [[RELATED-NOTE-3]] — 連結理由

## References
- [GitHub Repo]({URL})
- [官方文件]({docs URL if available})
```

> [!important] 步驟 A5 結尾：將筆記存到 `$TMP_ARTICLE`（即 `/tmp/kb-article-{REPO_NAME}.md`），圖片（若有 repo banner/截圖）存到 `$TMP_ASSETS/`（即 `/tmp/kb-assets-{REPO_NAME}/`），然後繼續步驟 3。

---

## 🌐 語言規則（Language Rule）：台灣繁體中文 + 保留英文專有名詞

> [!important] 所有筆記內容一律以**台灣繁體中文**撰寫，遵守以下規則：

**規則一：中文翻譯 + 括號保留英文原文**

| ✅ 正確寫法 | ❌ 錯誤寫法 |
|-----------|-----------|
| 知識圖譜（Knowledge Graph） | 知識圖譜 |
| 回饋循環（feedback loop） | feedback loop |
| 分叉模式（fork mode） | fork mode |
| 提示工程（Prompt Engineering） | prompt engineering |
| 上下文視窗（Context Window） | context window |

**規則二：工具名稱、品牌名稱直接使用英文**（不翻譯）
- 工具 / 軟體：Obsidian、Claude、GitHub、yt-dlp、Whisper
- 程式語言 / 框架：Python、JavaScript、YAML、Markdown
- 縮寫廣為人知者：API、CLI、SDK、LLM、AI

**規則三：雙向連結（Wikilink）檔名維持英文全大寫**
`[[CLAUDE-MEMORY-ENGINE]]` — 檔名格式不變，可在正文以中文描述

**規則四：引用原文時保留原語言**，區塊引用或程式碼中的英文不需翻譯。

**規則五：程式碼範例完整保留，不得省略**
- 原文中的程式碼區塊（code block）必須**完整複製**，不得用註解（comment）或摘要取代
- 程式碼內容保持英文原文，不翻譯
- 若原文有多個範例，每個都要完整收錄

---

## 步驟 1：讀取文章內容

**優先**：用 agent-browser 透過 Chrome CDP（port 9222）讀取，可存取需要登入的頁面：

> [!important] 前提條件：Chrome 必須以 remote debugging mode 啟動。若 CDP 連線失敗，請告知用戶用以下指令重開 Chrome（macOS 範例）：
> ```bash
> /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
>   --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
> ```
> Chrome 開啟後，用戶登入目標網站，再回來繼續執行。

```bash
agent-browser --cdp 9222 open "$ARGUMENTS"
agent-browser --cdp 9222 wait --load networkidle
agent-browser --cdp 9222 get text body
```

**退而求其次**（CDP 失敗時）：
```bash
defuddle parse "$ARGUMENTS" --md
```

### YouTube 影片特別處理

若 URL 為 YouTube，**同時執行**以下兩步取得影片元資訊與逐字稿：

**步驟 Y1：取得影片元資訊（標題、頻道、上傳日期、時長）**
```bash
yt-dlp --skip-download --print "%(title)s|%(uploader)s|%(upload_date)s|%(duration_string)s" "$ARGUMENTS"
```

**步驟 Y2：取得逐字稿（transcript）— 依序嘗試以下方法，成功即停止**

**方法一：youtube-transcript-api（推薦，最穩定）**
```bash
# 確認已安裝
pip3 install youtube-transcript-api -q 2>/dev/null || true

# 從 URL 取出 VIDEO_ID 並傳入 Python
VIDEO_ID=$(python3 -c "
import sys, re
url = '$ARGUMENTS'
m = re.search(r'(?:v=|youtu\.be/)([^&?/]+)', url)
print(m.group(1) if m else '')
")
echo "VIDEO_ID: $VIDEO_ID"

python3 -c "
from youtube_transcript_api import YouTubeTranscriptApi
video_id = '$VIDEO_ID'
api = YouTubeTranscriptApi()
transcripts = api.list(video_id)
for t in transcripts:
    print(f'Available: {t.language} ({t.language_code}) generated={t.is_generated}')
t = transcripts.find_transcript(['zh-TW', 'zh-Hant', 'zh-Hans', 'zh', 'en'])
data = t.fetch()
full_text = '\n'.join([s.text for s in data])
print(full_text)
"
```

> [!important] API 版本注意：`youtube-transcript-api` 新版（≥0.7）已移除 `YouTubeTranscriptApi.get_transcript()` 類別方法，必須用 `api = YouTubeTranscriptApi()` 實例化後呼叫 `api.list(video_id)`。

**方法二：yt-dlp 下載字幕**（youtube-transcript-api 失敗時）
```bash
# 先列出可用字幕語言代碼
yt-dlp --list-subs "$ARGUMENTS" 2>&1 | grep -E "zh|en"

# 使用正確的語言代碼（如 zh-TW、zh-Hant-zh-TW）下載
yt-dlp --write-auto-sub --sub-lang "zh-TW,zh-Hant-zh-TW,zh-Hans-zh-TW,en" \
  --convert-subs srt --skip-download -o "/tmp/kb-video" "$ARGUMENTS"

# 讀取下載的字幕
cat /tmp/kb-video.*.srt 2>/dev/null || cat /tmp/kb-video.*.vtt 2>/dev/null
```

**方法三：Google NotebookLM（推薦，即使無字幕也能提取逐字稿）**

> [!important] NotebookLM 即使影片沒有字幕也能提取完整逐字稿，品質優於 Whisper 且速度極快（數秒 vs 數十分鐘）。**優先使用此方法**，僅在 Chrome 擴充功能無法連線時才退回方法四（Whisper）。

使用 Chrome 瀏覽器自動化操作 NotebookLM：

```
步驟 1：確認 Chrome 擴充功能已連線
  → mcp__claude-in-chrome__tabs_context_mcp(createIfEmpty=true)
  → 若回傳 "Browser extension is not connected"，提示用戶重新連接後再試

步驟 2：建立新分頁並前往 NotebookLM
  → mcp__claude-in-chrome__tabs_create_mcp()
  → mcp__claude-in-chrome__navigate(url="https://notebooklm.google.com/", tabId=新分頁ID)

步驟 3：建立新筆記本
  → mcp__claude-in-chrome__read_page(tabId, filter="interactive") 找到「建立新的筆記本」按鈕
  → mcp__claude-in-chrome__computer(action="left_click", ref=按鈕ref)
  → 等待 3 秒

步驟 4：在「新增來源」對話框中輸入 YouTube URL
  → mcp__claude-in-chrome__read_page(tabId, filter="interactive") 找到對話框中的搜尋框（ref_50）
  → mcp__claude-in-chrome__form_input(ref=搜尋框ref, value="YouTube URL")
  → mcp__claude-in-chrome__computer(action="left_click", ref=提交按鈕ref)
  → 等待 5 秒讓 NotebookLM 處理影片

步驟 5：提取逐字稿
  → 確認頁面標題已更新（表示來源匯入成功）
  → mcp__claude-in-chrome__javascript_tool 提取 document.body.innerText
  → 由於文字量可能很大，分段提取：substring(0, 10000) 和 substring(10000, ...) 等
  → NotebookLM 的「來源指南」摘要可直接作為筆記的 Summary 參考

步驟 6：清理 — 刪除 NotebookLM 筆記本
  → 逐字稿提取完成後，必須刪除剛建立的 NotebookLM 筆記本，避免帳號中累積無用筆記本
  → 回到 NotebookLM 首頁 → 找到該筆記本 → 點「⋮」選單 → 刪除
  → 若 Chrome 擴充功能斷線無法自動操作，提醒用戶手動刪除
```

**方法四：Whisper AI 自動轉錄**（Chrome 無法連線時的退路）

> [!warning] Whisper medium 模型在 CPU 上極慢（8 分鐘影片可能需要 60+ 分鐘）。若有 GPU 可用會快很多。建議使用 `--model base` 加速（品質略降但速度快 10 倍以上）。

```bash
yt-dlp -f "bestaudio" -o "/tmp/kb-audio.%(ext)s" "$ARGUMENTS"

# 優先嘗試 base 模型（快），若品質不佳再用 medium
whisper /tmp/kb-audio.* --language Chinese --model base --output_format txt --output_dir /tmp/

# 若 base 品質不足，改用 medium（慢但品質好）
# whisper /tmp/kb-audio.* --language Chinese --model medium --output_format txt --output_dir /tmp/
```

> [!tip] 若 Whisper 因 SSL 憑證問題無法下載模型，可手動設定環境變數繞過：
> ```bash
> PYTHONHTTPSVERIFY=0 whisper /tmp/kb-audio.* --language Chinese --output_format txt
> ```
> 或確認 `~/.cache/whisper/` 中是否已有快取的模型檔案（如 `medium.pt`、`base.pt`），直接指定 `--model` 使用已有模型。

---

## 步驟 2：下載文章圖片

讀取頁面後，擷取文章本文中的圖片（排除 icon、avatar、廣告等非內容圖片）：

```bash
agent-browser --cdp 9222 eval --stdin <<'EOF'
JSON.stringify(
  Array.from(document.querySelectorAll(
    'article img, .article img, [data-testid="post-content"] img, .pw-post-body-paragraph img, figure img'
  ))
  .filter(img => img.width > 200 && img.src && !img.src.includes('avatar') && !img.src.includes('icon'))
  .map(img => ({ src: img.src, alt: img.alt }))
)
EOF
```

下載圖片到暫存目錄：
```bash
mkdir -p /tmp/kb-assets/
curl -L -o /tmp/kb-assets/{圖片檔名} "{圖片URL}"
```

圖片檔名：保留原檔名；若無副檔名則加 `.jpg`。

> [!important] 圖片分兩類處理：表格截圖 vs 真圖
> 下載後**先別急著把每張圖都當內容圖引用**。很多文章（尤其 Medium）把「表格」做成截圖——頁面純文字版會把表格替換成佔位符（如 `table-three-layers`），導致你在文字稿裡**看不到表格內容、誤以為它只是張圖**。
> 這類**表格截圖**應在步驟 4 用 Read 工具看圖後**轉成原生 Markdown 表格**（可搜尋、可複製、可被 Obsidian Bases 過濾），並**移除該圖檔與引用**；只有**真正的示意圖／流程圖／架構圖／插畫／封面／照片**才保留為圖片。判斷與轉換規則見步驟 4。

---

## 步驟 3：決定分類、檔名與路徑

### 分類選擇

> [!important] 分類依據**內容主題**，而非來源格式。YouTube 影片、部落格文章、論文都應依內容歸入對應主題資料夾。若現有分類都不適合，**直接新增一個語意明確的分類資料夾**，不需詢問。

| 分類 | 使用時機 |
|------|---------|
| `AI/` | AI 框架、LLM、代理人（Agent）、提示工程（Prompt Engineering）、機器學習（ML） |
| `Career/` | 職涯發展、職場策略、利害關係人管理（Stakeholder Management）、升遷、求職 |
| `Productivity/` | 工作流程（Workflow）、個人系統、GTD、時間管理、習慣 |
| `DevTools/` | 開發者工具、CLI、SDK、編輯器 |
| `Finance/` | 投資、經濟學（Economics）、金融科技（Fintech） |
| `Design/` | UI/UX、產品設計、視覺思考（Visual Thinking） |
| `Science/` | 物理、生物、天文、普通科學 |
| `Research/` | 學術論文、技術深入探討 |
| `Books/` | 書籍摘要與重點整理 |
| `OpenSource/` | 開源專案（Open Source Project）與社群 |
| `Security/` | 資訊安全（Cybersecurity）、隱私（Privacy） |
| `CodeAnalysis/` | GitHub Repo 程式碼深度分析、架構評估、Benchmark |

若內容不符合上列任何分類，根據主題自行建立新資料夾，例如 `Leadership/`、`Marketing/`、`Health/` 等。

### 檔名規則

格式：`{YYYY-MM-DD}-{原文標題大寫加連字號}.md`

- **日期**：使用文章或影片的**發布日期**（不是今天的日期），從以下來源依序尋找：
  1. 文章頁面中明確標示的發布日期（如 "Mar 7, 2026"、"2026-03-07"）
  2. HTML 的 `<time>` 元素或 `datetime` 屬性
  3. 文章 URL 中的日期（如 `/2026/03/07/`）
  4. YouTube 影片的上傳日期
  5. 若完全找不到，才使用今天日期，並在 frontmatter 加上 `date_uncertain: true`

**用 agent-browser 擷取發布日期的標準指令**（在步驟 1 讀完頁面後執行）：
```bash
agent-browser --cdp 9222 eval \
  'document.querySelector("meta[property=\"article:published_time\"]")?.content
   || document.querySelector("time[datetime]")?.getAttribute("datetime")
   || document.querySelector("meta[name=\"date\"]")?.content'
```
- **標題**：只保留英數字和連字號，去掉特殊符號，全部大寫
- 例：`2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA.md`

> [!warning] 日期來源必須是**原文發布日期**，不可使用執行此 skill 的當天日期

### 圖片存放路徑

`{分類}/assets/{YYYY-MM-DD}-{簡短標題}/`

例：`AI/assets/2026-03-07-SKILL-EVAL/`

---

## 步驟 4：撰寫 Obsidian Markdown 筆記

### 前置資料（Frontmatter）格式（Bases 相容）

```yaml
---
title: "筆記完整標題（台灣繁體中文）"
date: YYYY-MM-DD        # 原文或影片的發布日期，非執行 skill 的當天日期
category: AI
tags:
  - tag1
  - tag2
  - tag3
source: "https://original-url.com"
source_type: article   # article | video | paper | tool | book | podcast | code
author: "原作者姓名"
status: notes          # notes | reviewed | complete
links:
  - "[[RELATED-NOTE-1]]"
  - "[[RELATED-NOTE-2]]"
---
```

影片筆記（`source_type: video`）額外欄位：
```yaml
channel: "頻道名稱（Channel Name）"
duration: "00:00"
transcript_method: youtube-transcript-api   # youtube-transcript-api | yt-dlp | whisper | notebooklm | manual
```

### 正文結構

```markdown
## 摘要（Summary）
一段說明：這是什麼、為何重要。

## 關鍵洞察（Key Insights）
- 洞察一 — 參見 [[RELATED-CONCEPT]]
- 洞察二
- 洞察三

## 詳細內容（Details）
更深入的筆記、引用、程式碼片段、圖表。

> [!note] 關鍵術語（Key Term）
> 用 callout 定義重要術語。

> [!tip] 可執行建議（Actionable Tip）
> 用 tip callout 記錄實際可以做的事。

> [!warning] 注意事項（Watch Out）
> 用 warning callout 記錄陷阱、限制或風險。

## 我的心得（My Takeaways）
我學到了什麼，以及如何應用。

## 待補充（Open Questions）
- {讀完原文後仍無法回答的問題}
- {原文沒交代的前提或假設}
- {值得進一步追的延伸來源，附建議搜尋關鍵字}

## 相關連結（Related）
- [[RELATED-NOTE-1]] — 連結理由簡述
- [[RELATED-NOTE-2]] — 連結理由簡述
- [[RELATED-NOTE-3]] — 連結理由簡述

## References
- [原文]({URL})
```

> [!important] **Open Questions 規則**：
> - 寫 3–7 條
> - 每條必須是「讀完原文後仍無法回答」的問題，不是原文重點的改寫
> - LLM 應誠實列出自己的不確定處與知識缺口
> - 標注建議搜尋關鍵字，方便未來追蹤

### 圖片引用格式

```markdown
![圖片中文說明](assets/{YYYY-MM-DD}-{簡短標題}/{圖片檔名})
```

> [!important] 引用前先用 Read 工具逐一看圖，表格截圖一律轉 Markdown
> 在引用任何圖片前，**用 Read 工具逐一看過下載的每張圖**（你能直接讀 PNG/JPG），依內容分流：
>
> | 圖片類型 | 處理方式 |
> |---------|---------|
> | **表格截圖**（標題列 + 資料列的格狀資料） | **轉成原生 Markdown 表格**內嵌正文，**不保留圖片引用**，並在步驟 6 複製前／步驟 11 提交前刪除該圖檔 |
> | 流程圖／架構圖／時序圖／心智圖 | 保留圖片引用（純空間關係，ASCII 難完整重現） |
> | 插畫／封面／照片／螢幕截圖（非表格） | 保留圖片引用，alt 用中文說明圖片實際內容 |
>
> **判斷準則**：若圖中資訊「可用 `| 欄 | 欄 |` 表達」就轉 Markdown；若是空間關係、視覺示意或裝飾就保留圖片。
> **轉換規則**：忠實照抄圖中文字，不自行增刪欄位或列；路徑、指令、程式碼保留原樣（用反引號）。轉完後該圖即為冗餘，從 `assets/` 刪除以免佔空間。

> [!important] 步驟 4 結尾：撰寫完成後，將 markdown 存到 `/tmp/kb-article-{ALL-CAPS-TITLE}.md`（即以步驟 3 決定的檔名標題命名），供後續步驟使用。例：`/tmp/kb-article-CLAWTEAM-AGENT-SWARM-INTELLIGENCE.md`。在後續步驟中以變數 `TMP_ARTICLE` 引用此路徑。

---

## 步驟 4.5：知識層次深化分析（Bloom's Taxonomy Analysis）

> [!important] 此步驟在**所有內容類型（文章、影片、程式碼）**皆須執行，在步驟 4 撰寫完成後、步驟 5 上傳前執行。
> 目的是從「記憶→評估」五個認知層次，對本篇內容進行結構化分析，讓筆記從被動摘要升級為主動思辨記錄。

在已完成的筆記最末（`## References` 之前）插入以下區塊，並根據內容具體填寫每個層次的應用：

```markdown
---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | {列出本文 3–5 個必記的核心術語或概念} |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | {用自己的話解釋本文核心論點，及各概念間的關係} |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維，看透策略底層邏輯 | {指出本文的關鍵假設、潛在邏輯漏洞或未論及的前提} |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力，將理論轉為行動 | {列出 2–3 個可立即在工作／專案中執行的具體行動} |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡，在不確定的情境中做出最佳選擇 | {評估本文觀點的優缺點，與其他替代方案的取捨比較} |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：本文中哪個核心術語的定義最模糊？如何精確化它？
- **假設**：本文論點成立的最關鍵前提是什麼？若此前提不成立，結論如何改變？
- **證據**：本文有哪些主張缺乏足夠的實證支持？如何補強？
- **觀點**：若站在反對者的立場，最有力的批評是什麼？
- **後果**：若依照本文建議執行，12 個月後可能出現什麼預期外的副作用？

### 方案批判三問（Critical Evaluation — 適用於程式碼或做事方法類內容）

> [!warning] 僅當內容為**程式碼實作、技術方案、或具體做事方法**時才加入此區塊

1. **最大的風險是什麼？** — 這個方案在最壞情況下會造成什麼損失？是資料遺失、系統停擺、安全漏洞、還是人力浪費？
2. **什麼情況下會失敗？** — 列出此方案失效的具體前提條件（如：規模、環境、前置依賴、時機）
3. **有沒有更好的替代方案？** — 比較至少一個替代選項的優缺點，說明何時該選替代方案而非本方案
```

### 各內容類型的分析重點差異

**📰 文章分析重點**
- 記憶層：作者的核心主張、關鍵數據、重要術語定義
- 理解層：文章的論證結構（問題→主張→支持論據）
- 分析層：作者的立場偏見、未被挑戰的假設、反例
- 應用層：可直接套用的框架、工具、流程
- 評估層：與同領域其他觀點的差異與優劣

**📺 YouTube 影片分析重點**
- 記憶層：影片的核心論點、關鍵時間點（timestamp）、提到的工具或資源
- 理解層：講者的世界觀與思維框架、各段落之間的邏輯關係
- 分析層：講者的個人經驗偏誤、哪些主張是觀點而非事實
- 應用層：影片中演示的具體步驟、可複製的工作流程
- 評估層：影片論點在不同情境下的適用性限制

**💻 程式碼分析重點**
- 記憶層：核心 API、主要 CLI 指令、關鍵設定參數
- 理解層：架構設計決策的邏輯、各模組的職責邊界
- 分析層：設計取捨（Trade-offs）、技術債、潛在的延伸性問題
- 應用層：如何整合進自己的專案、需要修改哪些部分才能適用
- 評估層：與同類工具的比較、何時選用、何時不用

> [!important] 程式碼或方法類內容必須額外加入 `### 方案批判三問` 區塊，回答：**最大的風險？什麼情況下失敗？有沒有更好的替代方案？**

### Callout 類型參考

| Callout | 用途 |
|---------|------|
| `[!note]` | 一般筆記、觀察 |
| `[!tip]` | 可執行建議 |
| `[!warning]` | 注意事項、風險 |
| `[!info]` | 背景資訊 |
| `[!example]` | 具體範例 |
| `[!quote]` | 值得保留的直接引用 |
| `[!important]` | 重要規則或必讀資訊 |
| `[!faq]-` | 折疊式 FAQ（加 `-` 預設折疊） |

### 雙向連結（Wikilink）策略

- 在 `## 相關連結` 至少連結 **3 篇相關筆記**
- 在正文中提及已有獨立筆記的概念時即時連結：`[[CONCEPT-NAME]]`
- 若相關筆記尚未存在，仍可先寫下——會顯示為待建立的紅色連結
- 使用 `[[Note Name|顯示文字]]` 當檔名不適合直接出現在句子中

**標籤（Tag）策略**：每篇筆記 3–5 個標籤，使用巢狀標籤提升精確度：
`#ai/llm`、`#tools/cli`、`#productivity/workflows`

---

## 步驟 4.6：Mermaid 圖表驗證（筆記含 mermaid 區塊時必做）

> [!warning] 實際踩過的雷（2026-08-14）
> label 內寫 `&quot;` 實體，本地 mermaid v10/v11 `parse()` 都 PASS，但 GitHub 渲染管線會先把它解碼成 `"`，造成引號巢狀 → `Parse error ... got 'STR'`。**本地驗證通過 ≠ GitHub 渲染通過**，所以撰寫時就要用防禦性寫法，再加驗證雙保險。

### 防禦性寫法（撰寫 mermaid 時直接遵守）

合法的 label 長這樣：
- 含特殊字元（`/`、`：`、`（）`、逗號）的 label **一律用雙引號包裹**：`A["..."]`、`B{"..."}`
- label 內**不出現引號字元、也不出現 `&quot;`** —— 需要表達引號時改寫句子避開（如寫 `設為 name-only` 而非 `設為 "name-only"`）
- label 內的 `>`、`<` 寫成 `&gt;`、`&lt;`（`<br/>` 換行標籤除外，安全）

### 驗證指令（進入步驟 5 前執行，FAIL 就修到 PASS）

```bash
~/.claude/skills/kb-create/scripts/validate-mermaid.sh "$TMP_ARTICLE"
```

腳本會做兩件事：(1) 掃描 mermaid 區塊內的 `&quot;` 殺手模式（本地 parse 抓不到的 GitHub 失敗）；(2) 在 jsdom 環境用 `mermaid.parse()` 直驗每個區塊（只 parse 不渲染）。依賴自動安裝在 temp 目錄、跨次重用。

> [!important] 步驟 11 push 之後，開 GitHub blob 頁面確認圖表實際渲染成功、沒有出現「Unable to render rich display」——這是最終防線（步驟 12 回報時一併附上結果）。

---

## 步驟 5：同步知識庫 Repo

```bash
REPO_URL="https://${GITHUB_PERSONAL_ACCESS_TOKEN}@github.com/${KB_GITHUB_REPO}.git"

if [ -d "$KB_ROOT/.git" ]; then
  echo "正在同步最新版本..."
  git -C "$KB_ROOT" fetch origin
  git -C "$KB_ROOT" pull --rebase origin main
  echo "同步完成，目前為最新版本"
else
  echo "首次 clone..."
  git clone "$REPO_URL" "$KB_ROOT"
fi
```

---

## 步驟 6：複製圖片與文章到知識庫

```bash
# 建立圖片目錄並複製圖片
mkdir -p "$KB_ROOT/{分類}/assets/{YYYY-MM-DD}-{簡短標題}/"
cp /tmp/kb-assets/* "$KB_ROOT/{分類}/assets/{YYYY-MM-DD}-{簡短標題}/" 2>/dev/null || true

# 複製 Markdown 文章（TMP_ARTICLE 為步驟 A1 或步驟 4 結尾設定的暫存路徑）
cp "$TMP_ARTICLE" "$KB_ROOT/{分類}/{YYYY-MM-DD}-{ALL-CAPS-TITLE}.md"
```

記下新檔案路徑，後續步驟需要：
```bash
NEW_NOTE_PATH="{分類}/{YYYY-MM-DD}-{ALL-CAPS-TITLE}.md"
NEW_NOTE_NAME="{YYYY-MM-DD}-{ALL-CAPS-TITLE}"  # 不含 .md，用於 wikilink
CATEGORY="{分類}"
```

---

## 🆕 步驟 7：Cross-Reference 雙向連結維護

> [!important] 本步驟是 v2 新增的核心功能。每次攝入不只寫一個孤立檔，要主動連結既有知識網絡。

### 7a. 搜尋相關舊筆記

從新筆記抽出搜尋詞：frontmatter 的 `tags`、`category`、`author`，以及標題與摘要中的命名實體（人名、產品名、技術名）。

```bash
# 對每個搜尋詞，找出同分類與跨分類的既有筆記
CANDIDATES=$(mktemp)
for term in {tag1} {tag2} {author} {entity1} {entity2}; do
  grep -rl -i "$term" "$KB_ROOT" --include="*.md" \
    | grep -v assets/ \
    | grep -v LOG.md \
    | grep -v INDEX.md \
    | grep -v README.md \
    | head -5
done | sort -u > "$CANDIDATES"
```

LLM 逐一讀取候選筆記的 frontmatter + 摘要段落，**判斷哪些真正語意相關**（不只是字面命中），產出最終清單。

> [!warning] **上限 8 個**：最多回填 8 個既有筆記，避免單次攝入過度污染。
> 優先選擇：同主題 > 同作者 > 同標籤。

### 7b. 正向填入新筆記

用 Edit 工具更新 `/tmp/kb-article.md`（已複製到 KB_ROOT）：

1. **frontmatter `links:`** — 填入真實找到的 `[[NOTE-NAME]]`
2. **`## 相關連結（Related）`** — 每條附上一句連結理由

### 7c. 反向回填既有筆記

對最終清單裡的每個既有筆記，用 Edit 工具：

1. 找到 `## 相關連結（Related）` 段落
2. **先 grep 檢查**：該檔是否已包含新筆記的 wikilink，若已存在則跳過
3. 在段落末尾 append 一行：`- [[NEW-NOTE-NAME]] — {連結理由}`
4. 若該段不存在，在文件末尾新增：
   ```markdown

   ## 相關連結（Related）
   - [[NEW-NOTE-NAME]] — {連結理由}
   ```

> [!warning] 安全規則
> - 反向回填前先確認檔案存在且為 .md
> - **只新增、不刪改既有內容**
> - 不修改 frontmatter 既有欄位
> - 一檔只插入一行，避免重複

記下被回填的檔案清單與數量：
```bash
CROSSLINK_COUNT={N}
CROSSLINKED_FILES="{file1}, {file2}, ..."
```

---

## 🆕 步驟 8：更新 INDEX.md

在 `$KB_ROOT/{分類}/INDEX.md` 追加一行（若檔案不存在則建立）。

```bash
INDEX_FILE="$KB_ROOT/$CATEGORY/INDEX.md"

if [ ! -f "$INDEX_FILE" ]; then
  echo "# $CATEGORY Index" > "$INDEX_FILE"
  echo "" >> "$INDEX_FILE"
  echo "| 筆記 | 摘要 | 日期 |" >> "$INDEX_FILE"
  echo "|------|------|------|" >> "$INDEX_FILE"
fi
```

用 Edit 工具在表格末尾 append 一行：
```
| [[{NOTE-NAME}]] | {一句話摘要} | {YYYY-MM-DD} |
```

---

## 🆕 步驟 9：Append LOG.md

```bash
LOG_FILE="$KB_ROOT/LOG.md"

if [ ! -f "$LOG_FILE" ]; then
  cat > "$LOG_FILE" <<'HEADER'
# Knowledge Base Ingest Log

每次攝入（ingest）自動記錄於此，append-only。

| 時間 | 操作 | 來源 | 筆記 | 分類 | 回填數 | Open Questions |
|------|------|------|------|------|--------|----------------|
HEADER
fi
```

用 Edit 工具在表格末尾 append 一行：
```
| {YYYY-MM-DD HH:MM} | ingest | {URL 或標題} | [[{NOTE-NAME}]] | {CATEGORY} | {CROSSLINK_COUNT} | {OPEN_Q_COUNT} |
```

> [!warning] LOG.md 是 append-only，**禁止刪改舊條目**。

---

## 步驟 10：更新根目錄 README.md

```python
python3 << 'PYEOF'
import os
KB_ROOT = os.environ["KB_ROOT"]
readme_path = f"{KB_ROOT}/README.md"

with open(readme_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_line = "- [{NOTE-TITLE}](./{CATEGORY}/{FILENAME}.md) — {一行繁體中文說明}\n"

if "## 📌 Recent Notes" in content:
    content = content.replace(
        "## 📌 Recent Notes\n",
        "## 📌 Recent Notes\n" + new_line
    )
else:
    content += "\n## 📌 Recent Notes\n" + new_line

with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("README.md updated")
PYEOF
```

---

## 步驟 11：Git Commit & Push

commit message 格式包含影響範圍：

```bash
git -C "$KB_ROOT" add .
git -C "$KB_ROOT" commit -m "$(cat <<EOF
kb: ingest — {文章標題}

- new: $CATEGORY/$NEW_NOTE_PATH
- images: $CATEGORY/assets/{YYYY-MM-DD}-{簡短標題}/
- cross-links: $CROSSLINK_COUNT files updated ($CROSSLINKED_FILES)
- log: 1 entry appended
- index: $CATEGORY/INDEX.md updated
EOF
)"
git -C "$KB_ROOT" push
```

push 成功後顯示 GitHub 連結：
`https://github.com/${KB_GITHUB_REPO}/blob/main/{分類}/{YYYY-MM-DD}-{ALL-CAPS-TITLE}.md`

---

## 步驟 12：回報結果

完成後對使用者輸出摘要：

```
📄 新增筆記：{分類}/{檔名}
🖼️ 圖片：{N} 張 → {分類}/assets/{路徑}/
🔗 雙向連結：回填了 {N} 個既有筆記
   - {file1} — {理由}
   - {file2} — {理由}
   - ...
❓ Open Questions：{N} 條
📝 LOG.md：已記錄
📑 INDEX.md：{分類}/INDEX.md 已更新
🔗 GitHub：{URL}
⚠️ {若有任何失敗步驟請說明原因}
```

---

## ✅ 完整品質檢查清單（Quality Checklist）

### 🌐 語言規則確認
- [ ] 正文全程使用**台灣繁體中文**
- [ ] 所有翻譯成中文的專有名詞均已加括號標示英文原文
- [ ] 工具名稱、品牌名稱、程式語言保持英文原文

### 📋 前置資料（Frontmatter）確認
- [ ] 包含 `title`（台灣繁體中文標題）
- [ ] 包含 `date`、`tags`（至少 3 個）、`source`、`source_type`、`author`、`status`、`links`
- [ ] 影片筆記額外包含 `channel`、`duration`、`transcript_method`

### 🔗 知識圖譜（Knowledge Graph）確認
- [ ] 至少 **3 個雙向連結（wikilinks）**（即使目標筆記尚未存在）
- [ ] 至少 **1 個 callout** 用於關鍵洞察、術語或建議
- [ ] 包含 `## 相關連結` 區塊，附簡短連結理由

### 🆕 Cross-Reference 確認
- [ ] 步驟 7a 搜尋了既有筆記
- [ ] 正向連結已填入新筆記的 frontmatter 與正文
- [ ] 反向連結已回填到既有筆記（上限 8 個）
- [ ] 回填前已用 grep 確認無重複

### 🆕 索引與日誌確認
- [ ] LOG.md 已 append 一行（未刪改舊條目）
- [ ] INDEX.md 已更新（對應分類）
- [ ] commit message 包含影響範圍

### 🆕 Open Questions 確認
- [ ] 包含 3–7 條
- [ ] 每條是「讀完仍無法回答」的問題，不是重點改寫
- [ ] 含建議搜尋關鍵字

### 🖼️ 圖片確認
- [ ] 已用 Read 工具**逐一看過每張下載的圖**，並分類（表格截圖／示意圖／插畫）
- [ ] **表格截圖已轉成原生 Markdown 表格**，且對應圖檔已從 `assets/` 刪除（不留冗餘截圖）
- [ ] 非表格圖片（流程圖／架構圖／插畫／封面／照片）才保留，已下載並上傳到 `assets/` 子目錄
- [ ] Markdown 中以相對路徑引用圖片
- [ ] 圖片 alt text 使用中文說明圖片實際內容

### 🧜 Mermaid 圖表確認（筆記含 mermaid 區塊時）
- [ ] label 內無引號字元與 `&quot;` 實體（GitHub 會解碼成引號導致 Parse error——本地 parse 抓不到）
- [ ] label 內 `>`/`<` 已寫成 `&gt;`/`&lt;`（`<br/>` 除外）；含特殊字元的 label 已用雙引號包裹
- [ ] 已執行 `scripts/validate-mermaid.sh` 且全部 PASS（步驟 4.6）
- [ ] push 後已開 GitHub blob 頁確認渲染成功、無「Unable to render rich display」

### 📁 檔案結構確認
- [ ] 檔名格式：`{YYYY-MM-DD}-{ALL-CAPS-WITH-HYPHENS}.md`
- [ ] 放置於正確的分類資料夾
- [ ] 根目錄 README.md 的 Recent Notes 區塊已更新

### 📺 影片筆記（source_type: video）額外確認
- [ ] 分類依**影片內容主題**決定，而非固定放 `Videos/`
- [ ] 已記錄取得逐字稿（transcript）的方法
- [ ] `channel`、`duration`、`transcript_method` 欄位已填寫

### 💻 程式碼分析筆記額外確認
- [ ] 包含 **Why / What / How** 三個主要區塊
- [ ] **How** 區塊包含至少 **2 種 ASCII 圖表**（架構圖、流程圖、時序圖擇二以上）
- [ ] ASCII 圖表使用 code block 包住，正確使用 `┌┐└┘│─►◄▼▲` 等字元
- [ ] **架構師觀點** 有評分表格（優點）與具體問題清單（缺點）
- [ ] **Benchmark** 區塊已填寫（即使只有定性描述）
- [ ] 有 `github_stars` 與 `github_language` frontmatter 欄位
- [ ] 有 **Quick Start** 可執行範例
- [ ] 分類放在 `CodeAnalysis/` 資料夾
- [ ] `source_type: code`

### 📦 安裝流程確認（Installation Flow）
- [ ] **安裝時序圖**已繪製，顯示觸發指令 → 腳本 → 寫入路徑的完整鏈
- [ ] **安裝產物清單**有具體的絕對路徑（不只是概念描述）
- [ ] **環境變數表格**已填寫（若有）
- [ ] 說明了解除安裝/清理的方式（若文件有提及）

### 🗺️ 使用案例地圖確認（Use Case Map）
- [ ] **案例總覽表格**涵蓋 README 中提到的所有主要功能
- [ ] 每個案例都追蹤到**入口檔案**層級（不停在功能名稱）
- [ ] 至少 2 個案例有**詳解 ASCII 流程**（從觸發到輸出）
- [ ] 案例中的核心模組鏈不超過 5 層（太深要分段）

### 🧠 知識層次分析確認（Bloom's Taxonomy）
- [ ] 筆記包含 `## 知識層次分析（Bloom's Taxonomy Analysis）` 區塊（所有內容類型必填）
- [ ] 五個認知層次（記憶／理解／分析／應用／評估）皆已填入**針對本文的具體內容**，非通用描述
- [ ] `### 分析型追問（Socratic Follow-up）` 的五個問題已根據文章內容具體化
- [ ] 應用層至少列出 **2 個可立即執行的具體行動**
- [ ] 評估層包含與其他替代方案的取捨比較（不只列優點）
- [ ] **（程式碼／方法類內容）** `### 方案批判三問` 已加入：最大風險、失敗條件、替代方案
