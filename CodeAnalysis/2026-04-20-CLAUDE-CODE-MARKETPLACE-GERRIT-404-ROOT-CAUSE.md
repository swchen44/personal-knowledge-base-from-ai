---
title: "Claude Code Marketplace 連線 Gerrit Server 回傳 404 — 根因分析與完整驗證流程"
date: 2026-04-20
category: CodeAnalysis
tags:
  - code-analysis
  - ai/claude-code
  - gerrit
  - debugging
  - tools/cli
source: "本地實驗 + Claude Code 原始碼分析 (/Users/swchen.tw/git/claude-code/src)"
source_type: code
author: "Anthropic (source code) + 本地 Gerrit 實驗"
status: notes
links:
  - "[[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]]"
  - "[[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]]"
  - "[[2026-01-22-THE-LONGFORM-GUIDE-TO-EVERYTHING-CLAUDE-CODE]]"
github_stars: 0
github_language: TypeScript
---

## 摘要（Summary）

在公司使用 Gerrit Server 架設 Claude Code Marketplace 時，執行 `claude plugin marketplace add` 回傳 HTTP 404 錯誤，但同一個 HTTPS URL 用 `git clone` 可以正常下載。本文透過**本地架設 Gerrit 3.11.1**、**原始碼分析**與 **CLI 實測**三管齊下，定位根因為 `parseMarketplaceInput.ts` 的 URL 分類邏輯缺陷：非 GitHub 的 HTTPS URL 若不以 `.git` 結尾，會被歸類為 `source: 'url'`，導致 Claude Code 用 `axios.get()` 直接 HTTP GET 該 URL，而非 `git clone`。Gerrit 對直接 GET repo 路徑回 404（因不支援 Dumb HTTP），造成了此錯誤。

**解法**：在 Marketplace URL 後面加上 `.git` 後綴即可。

## Why — 為什麼存在？

> 這個問題源自 Claude Code Marketplace 的 URL 解析邏輯對非 GitHub Git server 的相容性不足。

- **核心動機**：企業環境常用 Gerrit 作為程式碼審查（Code Review）與 Git hosting 系統，需要將內部 Marketplace 架設在 Gerrit 上
- **痛點**：Claude Code 的 URL 解析邏輯以 GitHub 為中心設計，對 Gerrit、自建 GitLab 等非 GitHub 伺服器的 URL 格式缺乏完整支援
- **影響範圍**：所有使用非 GitHub Git server 且 URL 不以 `.git` 結尾的 Marketplace 使用者

## What — 是什麼？

- **問題現象**：`claude plugin marketplace add "https://gerrit.company.com/repo"` 回傳 404
- **根因**：URL 解析函式 `parseMarketplaceInput()` 將該 URL 錯誤分類為 `source: 'url'`（HTTP 下載 JSON），而非 `source: 'git'`（git clone）
- **不影響的情境**：GitHub URL（有特殊處理）、以 `.git` 結尾的 URL、SSH URL

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────┐
│                 claude plugin marketplace add            │
│                    (CLI 入口)                             │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│           parseMarketplaceInput.ts                       │
│                                                         │
│  輸入 URL → 判斷 source 類型：                            │
│  ┌─────────────────────────────────────────────────┐    │
│  │ .git 結尾？     → source: 'git'    ✅ git clone │    │
│  │ /_git/ 含？     → source: 'git'    ✅ git clone │    │
│  │ github.com？    → source: 'git'    ✅ git clone │    │
│  │ 其他 HTTPS？    → source: 'url'    ❌ HTTP GET  │    │
│  └─────────────────────────────────────────────────┘    │
└───────────────┬─────────────────────┬───────────────────┘
                │                     │
       source: 'git'          source: 'url'
                │                     │
                ▼                     ▼
┌───────────────────────┐  ┌──────────────────────────┐
│ cacheMarketplaceFromGit│  │ cacheMarketplaceFromUrl  │
│                       │  │                          │
│ gitClone()            │  │ axios.get(url)           │
│ → git clone --depth 1 │  │ → HTTP GET 下載 JSON     │
│ → 讀取 marketplace.json│  │ → 解析回應為 JSON        │
└───────────────────────┘  └──────────────────────────┘
                                      │
                                      ▼
                           Gerrit 對 GET /repo 回 404
                           ❌ 失敗！
```

### 執行流程圖（Execution Flowchart）

```
 用戶輸入 URL
      │
      ▼
 parseMarketplaceInput(url)
      │
      ├─ 以 .git 結尾？─── Yes ──► source: 'git' ──► gitClone() ──► ✅ 成功
      │
      ├─ 含 /_git/？────── Yes ──► source: 'git' ──► gitClone() ──► ✅ 成功
      │
      ├─ github.com？───── Yes ──► source: 'git' ──► gitClone() ──► ✅ 成功
      │                           (自動加 .git 後綴)
      │
      └─ 其他 HTTPS ────── Yes ──► source: 'url' ──► axios.get()
                                                        │
                                                        ├─ GitHub → 200 (HTML)
                                                        │   → schema 驗證失敗
                                                        │
                                                        └─ Gerrit → 404
                                                            → "HTTP 404 error
                                                               while downloading
                                                               marketplace"
```

### 時序圖 — 404 錯誤場景（Sequence Diagram）

```
 Claude Code CLI         parseMarketplaceInput     axios          Gerrit Server
       │                        │                    │                 │
       │── add "https://        │                    │                 │
       │   gerrit/repo" ──────► │                    │                 │
       │                        │                    │                 │
       │                        │── 判斷：不含 .git  │                 │
       │                        │   不是 github.com  │                 │
       │                        │── return {         │                 │
       │                        │     source: 'url'  │                 │
       │                        │   }                │                 │
       │                        │                    │                 │
       │── cacheFromUrl() ─────────────────────────► │                 │
       │                        │                    │── GET /repo ───►│
       │                        │                    │                 │
       │                        │                    │◄── 404 ────────│
       │                        │                    │                 │
       │◄── throw Error ────────────────────────────│                 │
       │   "HTTP 404 error..."  │                    │                 │
```

### 時序圖 — 正確場景（加 .git 後綴）

```
 Claude Code CLI         parseMarketplaceInput     git CLI        Gerrit Server
       │                        │                    │                 │
       │── add "https://        │                    │                 │
       │   gerrit/repo.git" ──► │                    │                 │
       │                        │                    │                 │
       │                        │── 判斷：含 .git    │                 │
       │                        │── return {         │                 │
       │                        │     source: 'git'  │                 │
       │                        │   }                │                 │
       │                        │                    │                 │
       │── cacheFromGit() ─────────────────────────► │                 │
       │                        │                    │── GET /repo.git/│
       │                        │                    │   info/refs?    │
       │                        │                    │   service=      │
       │                        │                    │   git-upload-   │
       │                        │                    │   pack ────────►│
       │                        │                    │                 │
       │                        │                    │◄── 200 ────────│
       │                        │                    │   (Smart HTTP)  │
       │                        │                    │                 │
       │◄── 成功 ───────────────────────────────────│                 │
       │   "Successfully added" │                    │                 │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> Claude Code 使用**策略模式（Strategy Pattern）**：根據 URL 格式選擇不同的取得策略（git clone vs HTTP GET）。問題在於策略選擇的判斷條件不夠完善。

1. **GitHub 優先設計** — `parseMarketplaceInput` 對 `github.com` hostname 有特殊處理（自動加 `.git` 後綴），但其他 Git server 沒有同等待遇
2. **`.git` 後綴作為 Git repo 判斷依據** — 這是 GitHub/GitLab/Bitbucket 的慣例，但 Gerrit 預設 URL 不含 `.git` 後綴
3. **Azure DevOps 特例** — `/_git/` 路徑被特別處理（因為 ADO 加 `.git` 會報 TF401019），但 Gerrit 沒有類似的特例

### 關鍵程式碼（Key Code Snippets）

**`parseMarketplaceInput.ts:42-87` — URL 分類邏輯（根因所在）**

```typescript
// Handle URLs
if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
  // Extract fragment (ref) from URL if present
  const fragmentMatch = trimmed.match(/^([^#]+)(#(.+))?$/)
  const urlWithoutFragment = fragmentMatch?.[1] || trimmed
  const ref = fragmentMatch?.[3]

  // When user explicitly provides an HTTPS/HTTP URL that looks like a git
  // repo, use the git source type so we clone rather than fetch-as-JSON.
  // The .git suffix is a GitHub/GitLab/Bitbucket convention. Azure DevOps
  // uses /_git/ in the path with NO suffix (appending .git breaks ADO:
  // TF401019 "repo does not exist"). Without this check, an ADO URL falls
  // through to source:'url' below, which tries to fetch it as a raw
  // marketplace.json — the HTML response parses as "expected object,
  // received string". (gh-31256 / CC-299)
  if (
    urlWithoutFragment.endsWith('.git') ||
    urlWithoutFragment.includes('/_git/')
  ) {
    return ref
      ? { source: 'git', url: urlWithoutFragment, ref }
      : { source: 'git', url: urlWithoutFragment }
  }
  // Parse URL to check hostname
  let url: URL
  try {
    url = new URL(urlWithoutFragment)
  } catch (_err) {
    return { source: 'url', url: urlWithoutFragment }
  }

  if (url.hostname === 'github.com' || url.hostname === 'www.github.com') {
    const match = url.pathname.match(/^\/([^/]+\/[^/]+?)(\/|\.git|$)/)
    if (match?.[1]) {
      const gitUrl = urlWithoutFragment.endsWith('.git')
        ? urlWithoutFragment
        : `${urlWithoutFragment}.git`
      return ref
        ? { source: 'git', url: gitUrl, ref }
        : { source: 'git', url: gitUrl }
    }
  }
  return { source: 'url', url: urlWithoutFragment } // ← 非 GitHub 的 HTTPS 落到這裡
}
```

**`marketplaceManager.ts:803-832` — gitClone 函式（正確路徑）**

```typescript
export async function gitClone(
  gitUrl: string,
  targetPath: string,
  ref?: string,
  sparsePaths?: string[],
): Promise<{ code: number; stderr: string }> {
  const args = [
    '-c',
    'core.sshCommand=ssh -o BatchMode=yes -o StrictHostKeyChecking=yes',
    'clone',
    '--depth',
    '1',
  ]

  if (useSparse) {
    args.push('--filter=blob:none', '--no-checkout')
  } else {
    args.push('--recurse-submodules', '--shallow-submodules')
  }

  if (ref) {
    args.push('--branch', ref)
  }

  args.push(gitUrl, targetPath)
  // ... 執行 git clone
}
```

**`marketplaceManager.ts:1256-1308` — cacheMarketplaceFromUrl（錯誤路徑）**

```typescript
async function cacheMarketplaceFromUrl(
  url: string,
  cachePath: string,
  customHeaders?: Record<string, string>,
  onProgress?: MarketplaceProgressCallback,
): Promise<void> {
  // ...
  try {
    response = await axios.get(url, {     // ← 直接 HTTP GET repo URL
      timeout: 10000,
      headers,
    })
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        throw new Error(
          `HTTP ${error.response.status} error while downloading marketplace from ${redactedUrl}. The marketplace file may not exist at this URL.\n\nTechnical details: ${error.message}`,
        )                                 // ← 這就是使用者看到的 404 錯誤訊息
      }
    }
  }
}
```

## 驗證流程（Verification Process）

> [!important] 完整重現步驟
> 本節記錄從零到成功重現問題的完整流程，包含環境搭建、測試方法與關鍵發現。

### Phase 1：本地 Gerrit 環境搭建

#### 1.1 安裝 Java 21

Gerrit 3.11.x 需要 Java 21（class file version 65），Java 8 和 Java 11 都不夠：

```bash
# Java 8 → UnsupportedClassVersionError (max version 52)
# Java 11 → UnsupportedClassVersionError (max version 55)
# Java 21 → ✅ 正確

brew install openjdk@21
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
```

#### 1.2 下載與初始化 Gerrit

```bash
cd ~/git/gerrit_testing
curl -LO https://gerrit-releases.storage.googleapis.com/gerrit-3.11.1.war

$JAVA_HOME/bin/java -jar gerrit-3.11.1.war init -d gerrit_site --batch --dev
# --batch: 使用預設值
# --dev: 啟用 DEVELOPMENT_BECOME_ANY_ACCOUNT 認證模式
```

初始化後 Gerrit 自動啟動，存取 `http://localhost:8080`。

#### 1.3 建立測試 Repo

```bash
# 透過 REST API 建立專案
curl -s -X PUT 'http://localhost:8080/a/projects/test-marketplace' \
  -H 'Content-Type: application/json' \
  -u admin:secret \
  -d '{"create_empty_commit": true}'

# Clone（匿名路徑，不帶 /a/ 或 /r/ 前綴）
git clone http://localhost:8080/test-marketplace test-marketplace-clone
```

#### 1.4 建立 Marketplace Manifest

```json
{
  "name": "gerrit-test",
  "owner": {
    "name": "Test Admin"
  },
  "plugins": [],
  "metadata": {
    "description": "Gerrit test marketplace for Claude Code"
  }
}
```

> [!warning] Schema 必要欄位
> `name` 和 `owner` 是必填。初次測試時只有 `name`、`description`、`plugins` 導致 schema 驗證失敗：`owner: Invalid input: expected object, received undefined`。

### Phase 2：Gerrit HTTP 端點測試

#### 2.1 Smart HTTP 端點行為對照表

| # | URL Pattern | HTTP Status | 說明 |
|---|-------------|-------------|------|
| 1 | `GET /test-marketplace` | **404** | 直接存取 repo 根 → Not Found |
| 2 | `GET /test-marketplace.git` | **404** | 加 .git 後綴也一樣 |
| 3 | `GET /test-marketplace/info/refs?service=git-upload-pack` | **200** | Smart HTTP ✅ |
| 4 | `GET /test-marketplace.git/info/refs?service=git-upload-pack` | **200** | 加 .git 也行 ✅ |
| 5 | `GET /a/test-marketplace/info/refs` (無認證) | **401** | 需要認證 |
| 6 | `GET /a/test-marketplace/info/refs` (有認證) | **200** | ✅ |
| 7 | `GET /r/test-marketplace/info/refs` | **403** | `/r/` 路徑被拒 |
| 8 | `GET /test-marketplace/info/refs` (無 service 參數) | **406** | Dumb HTTP 不支援 |
| 9 | `GET /test-marketplace/HEAD` | **404** | Dumb HTTP 不支援 |

> [!note] 關鍵發現
> Gerrit 只對 Smart HTTP 的 `/info/refs?service=git-upload-pack` 端點回 200。直接 GET repo URL 一律回 404。這與 GitHub（會回 HTML 頁面或 redirect）行為完全不同。

#### 2.2 git clone 路徑測試

| URL Pattern | 結果 |
|-------------|------|
| `http://localhost:8080/test-marketplace` | ✅ 成功（git 內部走 Smart HTTP） |
| `http://localhost:8080/test-marketplace.git` | ✅ 成功 |
| `http://admin:secret@localhost:8080/a/test-marketplace` | ✅ 成功 |
| `http://localhost:8080/r/test-marketplace` | ❌ 403 Forbidden |

> [!tip] 為什麼 git clone 不帶 .git 也能成功？
> `git clone` 底層會自動嘗試 `/info/refs?service=git-upload-pack`，所以即使 URL 不以 `.git` 結尾也能正確走 Smart HTTP 協定。問題在於 Claude Code 的 `cacheMarketplaceFromUrl()` 是用 `axios.get()` 直接 GET URL，而不是用 git clone。

### Phase 3：原始碼分析

追蹤程式碼路徑，確認根因：

```
parseMarketplaceInput.ts:56-87
  ↓ URL 不以 .git 結尾且非 github.com
  ↓ return { source: 'url', url }
  ↓
marketplaceManager.ts:1466-1616 (switch case)
  ↓ case 'url':
  ↓ cacheMarketplaceFromUrl()
  ↓
marketplaceManager.ts:1282
  ↓ axios.get(url, { timeout: 10000 })
  ↓ Gerrit 回 404
  ↓
marketplaceManager.ts:1305-1308
  → throw "HTTP 404 error while downloading marketplace..."
```

### Phase 4：CLI 實測驗證

```bash
# ❌ 不加 .git — 重現 404
$ claude plugin marketplace add "http://localhost:8080/test-marketplace" --scope user
Adding marketplace...
Downloading marketplace from http://localhost:8080/test-marketplace
✘ Failed to add marketplace: HTTP 404 error while downloading marketplace...

# ✅ 加 .git — 成功
$ claude plugin marketplace add "http://localhost:8080/test-marketplace.git" --scope user
Adding marketplace...
Cloning repository (timeout: 120s): http://localhost:8080/test-marketplace.git
Clone complete, validating marketplace…
✔ Successfully added marketplace: gerrit-test (declared in user settings)
```

## 測試方法（Testing Methodology）

> [!important] 三管齊下的除錯策略
> 本次除錯同時使用了三種互補的方法，缺一不可。

### 方法 1：本地環境模擬（Black Box）

- **目的**：在可控環境中重現問題
- **工具**：Gerrit 3.11.1 WAR + Java 21
- **優點**：不依賴公司網路，可以自由修改設定、反覆測試
- **侷限**：不能 100% 確認公司 Gerrit 的行為與本地一致

### 方法 2：原始碼分析（White Box）

- **目的**：確認 Claude Code 內部的 URL 處理邏輯
- **關鍵檔案**：
  - `src/utils/plugins/parseMarketplaceInput.ts` — URL 分類邏輯
  - `src/utils/plugins/marketplaceManager.ts` — git clone vs HTTP GET 路徑
  - `src/utils/plugins/schemas.ts` — Marketplace JSON schema 定義
- **優點**：能精確定位根因到具體程式碼行
- **侷限**：需要有原始碼

### 方法 3：CLI 端到端測試（Integration）

- **目的**：用真實的 `claude plugin marketplace add` 指令驗證假設
- **優點**：最終確認修復是否有效
- **指令**：`claude plugin marketplace add "URL" --scope user`

### 除錯思路時間軸

```
1. 初步假設：Gerrit Smart HTTP 端點問題
   → 用 curl 測試各種 URL pattern
   → 發現 git clone 正常，但直接 GET repo URL 回 404
   
2. 中間假設：Claude Code 可能先 HTTP 探測再 git clone
   → 讀原始碼 → 發現沒有預檢（pre-flight check）
   → 但發現 URL 分類邏輯有問題
   
3. 最終定位：parseMarketplaceInput 的 source 分類
   → 非 GitHub + 不含 .git → source: 'url' → axios.get()
   → Gerrit 不支援直接 GET repo URL → 404
   
4. 驗證修復：URL 加 .git 後綴
   → parseMarketplaceInput 正確分類為 source: 'git'
   → gitClone() 走 Smart HTTP → 成功
```

## 安裝流程（Installation Flow）

### 本地 Gerrit 測試環境安裝

```
brew install openjdk@21
    │
    ▼
curl -LO gerrit-3.11.1.war
    │
    ▼
java -jar gerrit-3.11.1.war init -d gerrit_site --batch --dev
    │
    ├── 建立 gerrit_site/ 目錄結構
    ├── 生成 SSH host keys
    ├── 初始化 Lucene 索引（Index）
    └── 自動啟動 Gerrit（HTTP:8080, SSH:29418）
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/git/gerrit_testing/gerrit-3.11.1.war` | 檔案 | Gerrit WAR 執行檔 |
| `~/git/gerrit_testing/gerrit_site/` | 目錄 | Gerrit site 根目錄 |
| `~/git/gerrit_testing/gerrit_site/etc/gerrit.config` | 檔案 | Gerrit 主設定檔 |
| `~/git/gerrit_testing/gerrit_site/git/` | 目錄 | Git bare repo 儲存位置 |
| `~/git/gerrit_testing/gerrit_site/bin/gerrit.sh` | 檔案 | 啟動/停止指令碼 |

> [!warning] 解除安裝
> ```bash
> gerrit_site/bin/gerrit.sh stop
> rm -rf gerrit_site gerrit-3.11.1.war
> brew uninstall openjdk@21   # 如不再需要
> brew uninstall openjdk@11   # 如不再需要
> ```

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 加入 Marketplace（失敗） | `claude plugin marketplace add "https://gerrit/repo"` | `parseMarketplaceInput.ts` | `parseMarketplaceInput → cacheMarketplaceFromUrl → axios.get → 404` |
| 2 | 加入 Marketplace（成功） | `claude plugin marketplace add "https://gerrit/repo.git"` | `parseMarketplaceInput.ts` | `parseMarketplaceInput → cacheMarketplaceFromGit → gitClone → 200` |
| 3 | 列出 Marketplace | `claude plugin marketplace list` | `marketplaceManager.ts` | 讀取 settings.json 中的 marketplace 設定 |

### 案例詳解

#### 案例 1：加入 Marketplace（404 失敗路徑）

```
用戶：claude plugin marketplace add "https://gerrit.company.com/test-marketplace"
  │
  ▼
parseMarketplaceInput.ts:42
  │ URL 以 https:// 開頭
  │ 不以 .git 結尾 → 不符合第 56 行條件
  │ hostname 不是 github.com → 不符合第 74 行條件
  │
  ▼
parseMarketplaceInput.ts:87
  │ return { source: 'url', url: '...' }
  │
  ▼
marketplaceManager.ts:1440 (switch case 'url')
  │
  ▼
cacheMarketplaceFromUrl() :1256
  │ axios.get(url) → GET https://gerrit.company.com/test-marketplace
  │
  ▼
Gerrit Server → 404 Not Found
  │
  ▼
"HTTP 404 error while downloading marketplace..."  ❌
```

#### 案例 2：加入 Marketplace（成功路徑）

```
用戶：claude plugin marketplace add "https://gerrit.company.com/test-marketplace.git"
  │
  ▼
parseMarketplaceInput.ts:42
  │ URL 以 https:// 開頭
  │ 以 .git 結尾 → 符合第 56 行條件 ✅
  │
  ▼
parseMarketplaceInput.ts:60
  │ return { source: 'git', url: '...' }
  │
  ▼
marketplaceManager.ts:1601 (switch case 'git')
  │
  ▼
cacheMarketplaceFromGit() :1084
  │ gitClone(url, cachePath) → git clone --depth 1
  │ git 內部走 Smart HTTP: GET /repo.git/info/refs?service=git-upload-pack → 200
  │
  ▼
"Successfully added marketplace: gerrit-test"  ✅
```

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐ | 程式碼結構清晰，策略模式分離 git/url/npm 路徑 |
| 可擴展性（Scalability） | ⭐⭐⭐ | 新增 Git server 支援需修改 parseMarketplaceInput |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐ | 有 unit test 但缺乏非 GitHub server 的整合測試 |
| 文件品質（Documentation） | ⭐⭐⭐⭐ | 程式碼註解清楚，包含 issue 引用（如 gh-31256） |
| 錯誤訊息品質（Error Messages） | ⭐⭐ | 404 訊息「marketplace file may not exist at this URL」有誤導性，真正原因是 URL 被錯誤分類 |

> [!tip] 值得學習的設計
> Azure DevOps 的 `/_git/` 特例處理展示了如何為特定 Git server 新增相容性（見 gh-31256 / CC-299 註解），是 Gerrit 修復的參考模板。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> URL 分類邏輯以「URL 外觀」判斷是 git repo 還是 JSON 文件，而不是嘗試 git clone 後 fallback。

- **問題一**：非 GitHub/ADO 的 Git server（Gerrit、自建 GitLab、Gitea 等）URL 不以 `.git` 結尾時，被錯誤分類為 HTTP JSON 下載 — 影響：所有企業內部 Marketplace
- **問題二**：錯誤訊息「marketplace file may not exist at this URL」未提示使用者嘗試加 `.git` 後綴 — 影響：使用者無法自行排除問題
- **問題三**：`/r/` 前綴在 Gerrit 上回 403 — 如果使用者的公司 Gerrit 設定了 `download.scheme = http` 帶 `/r/` 前綴，需要知道不能用 `/r/`

### 🔮 改進建議（Improvement Suggestions）

1. **Fallback 策略**：當 `source: 'url'` 的 `axios.get()` 回 404 時，自動 fallback 嘗試 `git clone`
2. **啟發式判斷（Heuristic）**：檢查 URL path 是否看起來像 repo 名稱（如沒有 `.json` 後綴），優先嘗試 git clone
3. **改善錯誤訊息**：在 404 錯誤中加入提示「If this is a Git repository, try adding .git to the URL」
4. **文件補充**：在 Marketplace 文件中明確說明非 GitHub server 需要 `.git` 後綴

## 效能基準（Benchmark）

| 操作 | 時間 |
|------|------|
| Gerrit WAR 初始化（init） | ~5 秒 |
| git clone（shallow） | < 1 秒 |
| axios.get() 到 404 失敗 | < 0.1 秒 |
| `claude plugin marketplace add`（成功路徑） | ~3 秒 |

## 快速上手（Quick Start）

```bash
# 在公司 Gerrit 上架設 Marketplace — 加 .git 後綴即可
claude plugin marketplace add "https://gerrit.company.com/your-marketplace-repo.git" --scope user

# 若需要特定 branch
claude plugin marketplace add "https://gerrit.company.com/your-marketplace-repo.git#main" --scope user

# 確認結果
claude plugin marketplace list
```

## 我的心得（My Takeaways）

1. **三管齊下的除錯法**（本地模擬 + 原始碼分析 + 端到端測試）是解決跨系統相容性問題的最有效策略
2. **URL 外觀不等於意圖** — `parseMarketplaceInput` 用 URL 後綴判斷是 git repo 還是 JSON 文件，這在 GitHub 生態系統中成立，但在企業環境（Gerrit、自建 GitLab）中失效
3. **Gerrit 的 HTTP 行為與 GitHub 截然不同** — 不支援 Dumb HTTP、不支援直接 GET repo URL、`/r/` 前綴行為特殊，這些都是非 GitHub Git server 的常見陷阱
4. **看到 404 不要只想網路問題** — 真正的根因可能在 client 端（選錯了請求方式），而非 server 端

## 待補充（Open Questions）

- Claude Code 是否計畫改善非 GitHub Git server 的 Marketplace 相容性？可搜尋 GitHub issues: `gerrit marketplace 404`
- 如果公司 Gerrit 設定了 `auth.type = LDAP`（非 DEVELOPMENT_BECOME_ANY_ACCOUNT），`.netrc` 的帳密格式是否正確？需確認 Gerrit HTTP Password 與 LDAP 密碼是否不同
- Gerrit 的 `download.scheme` 設定（`http`/`ssh`/`anon_http`）是否影響 Marketplace clone 路徑？
- Claude Code 未來是否會新增 `--git` flag 讓使用者明確指定 source type？
- 有些公司的 Gerrit 在反向代理（Reverse Proxy）後面，URL 路徑可能被改寫，這是否也會造成 404？可搜尋：`gerrit reverse proxy git smart http`

## 相關連結（Related）

- [[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]] — 同樣分析了 Claude Code 生態系統中的 Gerrit 相容性問題，但聚焦在 npx skills 的解析邏輯
- [[2026-04-08-CLAUDE-CODE-TEAM-MEMORY-DEEP-DIVE]] — 另一個 Claude Code 原始碼深度分析，展示了 TypeScript 原始碼追蹤的方法論
- [[2026-01-22-THE-LONGFORM-GUIDE-TO-EVERYTHING-CLAUDE-CODE]] — Claude Code 進階使用指南，涵蓋 plugin 與 marketplace 的使用情境

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 1. `parseMarketplaceInput` 是 URL 分類的核心函式 2. `.git` 後綴決定 `source: 'git'` vs `source: 'url'` 3. Gerrit 不支援 Dumb HTTP，直接 GET repo URL 回 404 4. `cacheMarketplaceFromGit` 用 git clone、`cacheMarketplaceFromUrl` 用 axios.get |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Claude Code 的 Marketplace 系統有兩條取得路徑（git clone vs HTTP GET），路徑選擇由 URL 外觀決定而非協定探測。GitHub 有特殊處理（自動加 .git），但其他 Git server 被當成 JSON URL 處理。Gerrit 的 HTTP 端點只支援 Smart HTTP 協定的特定路徑（`/info/refs?service=git-upload-pack`），不支援直接 GET repo 根 URL。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | 核心假設：「URL 後綴是判斷 git repo 的可靠指標」— 這在 GitHub 生態有效，但在 Gerrit（URL 不帶 .git）、Gitea、自建 GitLab 等環境中失效。邏輯漏洞：沒有 fallback 機制（axios.get 失敗時不嘗試 git clone）。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. **立即可做**：在公司 Gerrit Marketplace URL 後加 `.git` 後綴解決 404 2. **分享團隊**：將此發現寫入公司內部文件，避免其他同事踩坑 3. **回報 Issue**：向 Claude Code repo 提交 bug report，建議改善 URL 分類邏輯 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | 加 `.git` 後綴是最快的 workaround，但治標不治本。改善 `parseMarketplaceInput` 的 URL 分類邏輯（如加入 fallback 或啟發式判斷）是根本解法，但需要等 Anthropic 接受 PR。長遠來看，Claude Code 應參考 ADO 的處理方式，為更多 Git server 新增 URL pattern 支援。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Smart HTTP」與「Dumb HTTP」的差異在哪？為什麼 `git clone` 可以自動處理但 `axios.get` 不行？
- **假設**：如果 Claude Code 假設所有 HTTPS URL 都先嘗試 git clone，會有什麼副作用？（提示：對非 git 的 JSON URL 會浪費 120 秒 timeout）
- **證據**：是否有其他非 GitHub Git server 的使用者也遇到同樣問題？搜尋 `claude-code marketplace 404 gitlab gitea`
- **觀點**：從 Gerrit 管理員的角度，是否應該設定 URL rewrite 讓直接 GET repo URL 也能回應？（可能不是好主意：安全考量）
- **後果**：如果大量企業使用者都遇到這個問題，Anthropic 可能會如何改變 URL 解析邏輯？是否會破壞現有 JSON URL 使用者的行為？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 加 `.git` 後綴是 workaround，如果 Gerrit 管理員關閉了 `.git` 後綴的 URL 支援（雖然不太常見），此方法會失效。更大的風險是：使用者可能不知道需要加 `.git`，直接放棄使用 Marketplace。
2. **什麼情況下會失敗？** — 如果公司 Gerrit 在反向代理後面且 URL 路徑被改寫；如果 Gerrit 版本太舊不支援 Smart HTTP；如果公司網路需要代理（proxy）存取 Gerrit 但 git clone 沒有設定 proxy。
3. **有沒有更好的替代方案？** — 可以直接在 Gerrit 上 host 一個 `marketplace.json` 靜態檔案（透過 Gerrit 的 web plugin 或另一個 HTTP server），讓 `source: 'url'` 路徑直接下載 JSON，完全繞過 git clone。但這需要額外維護一個靜態檔案。

## References

- [Claude Code 原始碼 — parseMarketplaceInput.ts](file:///Users/swchen.tw/git/claude-code/src/utils/plugins/parseMarketplaceInput.ts)
- [Claude Code 原始碼 — marketplaceManager.ts](file:///Users/swchen.tw/git/claude-code/src/utils/plugins/marketplaceManager.ts)
- [Gerrit Code Review — Docker Image](https://hub.docker.com/r/gerritcodereview/gerrit)
- [Git Smart HTTP Protocol](https://git-scm.com/docs/http-protocol)
- [Claude Code Marketplace 文件](https://code.claude.com/docs/en/plugin-marketplaces)
- [GitHub Issue #31930 — Plugin installer HTTPS](https://github.com/anthropics/claude-code/issues/31930)
- [GitHub Issue #26588 — Marketplace SSH vs HTTPS](https://github.com/anthropics/claude-code/issues/26588)
