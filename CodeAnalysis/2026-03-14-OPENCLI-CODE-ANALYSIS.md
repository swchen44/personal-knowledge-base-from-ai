---
title: "OpenCLI — 程式碼深度分析：把任何網站變成 CLI 的 AI 原生工具"
date: 2026-03-14
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#tools/cli"
  - "#ai/agent-architecture"
  - "#devtools/browser-automation"
source: "https://github.com/jackwener/opencli"
source_type: code
author: "jackwener"
status: notes
links:
  - "[[CLAUDE-CODE-ARCHITECTURE]]"
  - "[[BROWSER-AUTOMATION-CDP]]"
  - "[[AI-AGENT-TOOLS]]"
github_stars: 12016
github_language: TypeScript
---

## 摘要（Summary）

OpenCLI 是一個把「任何網站、Electron App 或本地 CLI 工具」轉成統一命令列介面（CLI）的框架。核心創新是透過 Chrome Extension + 微型 Daemon 中繼服務，讓 CLI 命令能安全重用瀏覽器的已登入狀態（cookies），完全不需要在程式碼中儲存密碼。它提供了 73+ 個網站的預建 Adapter（Bilibili、Twitter、Xiaohongshu、Reddit 等），並可讓 AI Agent（Claude Code、Cursor）直接透過 `operate` 子命令控制瀏覽器——click、type、screenshot、extract，一切皆可腳本化。

## Why — 為什麼存在？

- **核心動機**：大量網站沒有公開 API，或 API 需要付費授權。想要自動化這些網站的操作，傳統方式（Selenium、Playwright）需要管理獨立的瀏覽器 session，且容易被反爬蟲機制偵測
- **取代/改善什麼**：取代 Puppeteer/Playwright 的「另開瀏覽器」模式，改為重用使用者已登入的真實 Chrome session；讓 AI Agent 不再需要人工操作瀏覽器
- **目標用戶**：AI Agent 開發者、需要自動化網站互動的工程師、想要給 Claude Code / Cursor 瀏覽器控制能力的用戶

## What — 是什麼？

- **主要功能**：
  - 73+ 預建網站 Adapter（`opencli twitter trending`、`opencli bilibili hot` 等）
  - `opencli operate` — AI Agent 直接控制瀏覽器（open, click, type, get, screenshot, eval...）
  - `opencli record` — 錄製使用者操作，自動生成 Adapter
  - `opencli explore` / `synthesize` — AI 自動發現 API 並生成 Adapter
  - `opencli register <mycli>` — 將任何本地 CLI 納入 CLI Hub，讓 AI Agent 可統一發現與呼叫
  - 多種輸出格式：`--format table|json|yaml|md|csv`
- **不做什麼（Non-goals）**：不包含 AI 模型（runtime 無 LLM 成本）；不保存密碼（只借用 Chrome cookies）；不管理獨立的瀏覽器 session
- **技術棧（Tech Stack）**：TypeScript、Node.js ≥20、Commander.js、WebSocket（ws）、Chrome DevTools Protocol（CDP）

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────────┐
│                  opencli CLI（使用者入口）                    │
│            Commander.js entry point (src/main.ts)            │
├──────────────────────────┬──────────────────────────────────┤
│          引擎層（Engine Layer）                               │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────────────┐  │
│  │   Registry   │ │ Dynamic Loader│ │  Output Formatter  │  │
│  │ (src/registry│ │(src/discovery │ │ table/json/yaml/   │  │
│  │    .ts)      │ │     .ts)      │ │   md/csv           │  │
│  └──────────────┘ └───────────────┘ └────────────────────┘  │
├──────────────────────────┬──────────────────────────────────┤
│          Adapter 層（網站 / App 轉接器）                      │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │  YAML Pipeline 宣告式 │  │  TypeScript Adapters 程式式  │ │
│  │  (fetch/map/filter)  │  │  (src/clis/twitter/bilibili) │ │
│  └──────────────────────┘  └──────────────────────────────┘ │
├──────────────────────────┬──────────────────────────────────┤
│          連線層（Connection Layer）                           │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │  Browser Bridge Mode │  │  CDP Direct Mode             │ │
│  │  Chrome Extension    │  │  Electron App CDP WebSocket  │ │
│  │  + Daemon (WS :19825)│  │  (--remote-debugging-port)   │ │
│  └──────────────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 執行流程圖（Browser Bridge 模式）

```
 使用者或 AI Agent
       │
       │ $ opencli twitter trending
       ▼
 main.ts (entry point)
   │ discoverClis() → Registry 載入所有 adapter
   │
   ▼
 commanderAdapter.ts
   │ 解析 CLI 參數 → 找到對應 adapter 函式
   │
   ▼
 twitter/trending.ts : func(page, kwargs)
   │ 呼叫 page.goto() / page.evaluate()
   │
   ▼
 browser/page.ts : sendCommand('navigate'/'exec', ...)
   │ HTTP POST → localhost:19825
   │
   ▼
 daemon.ts（微型 HTTP+WebSocket 中繼服務）
   │ WebSocket → Chrome Extension
   │
   ▼
 extension/background.js
   │ chrome.debugger.sendCommand() 或 chrome.tabs API
   │ 在真實已登入的 Chrome Tab 中執行 JS
   │
   ▼
 結果回傳（WebSocket → daemon → HTTP response → CLI）
   │
   ▼
 output.ts : 格式化輸出（table / json / yaml / md）
```

### 時序圖（Daemon 通信機制）

```
 CLI Command    Daemon(:19825)    Chrome Extension    Browser Tab
      │               │                  │                 │
      │──POST /cmd────►│                  │                 │
      │                │──WebSocket msg──►│                 │
      │                │                  │──CDP/tabs API──►│
      │                │                  │◄──DOM result────│
      │                │◄──WebSocket msg──│                 │
      │◄──HTTP result──│                  │                 │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 雙引擎架構（Dual-Engine Architecture）
> YAML Pipeline（宣告式）適合純 HTTP API 的網站；TypeScript Adapter（程式式）適合需要瀏覽器互動的複雜場景。兩者統一透過 Registry 管理，使用者看到的是同一個介面。

1. **Daemon 做 HTTP ↔ WebSocket 橋接**：CLI 透過 HTTP POST 發命令，Daemon 透過 WebSocket 轉發給 Extension——讓 CLI（Node.js）不需直接處理 WebSocket 連線管理
2. **Extension 保管瀏覽器 Session**：Cookie 和登入狀態永遠留在 Chrome 裡，Daemon 只傳指令，避免憑證外洩
3. **Stealth 注入（stealth.ts）**：每次導航後自動注入反偵測 JS（`navigator.webdriver = false`、偽裝 `window.chrome`、填充 plugin 清單），讓自動化操作看起來像正常用戶
4. **Fail-closed 安全設計**：Daemon 拒絕非 `chrome-extension://` 來源的連線、要求 `X-OpenCLI` 自訂 Header（瀏覽器 JS 無法跨域發送），防止 CSRF 攻擊

### 認證策略（Authentication Strategies）

| 策略 | 運作方式 | 適用場景 |
|------|---------|---------|
| `public` | 直接 HTTP fetch，無認證 | 公開 API（HackerNews、arXiv） |
| `cookie` | 透過 Browser Bridge 重用 Chrome cookies | 需登入的網站（Bilibili、Zhihu） |
| `header` | 自訂 auth header | API Key 服務 |
| `intercept` | 攔截 XHR/GraphQL 網路請求 | Twitter（GraphQL API） |
| `ui` | DOM 互動 via accessibility snapshot | 桌面 App、寫入操作 |

### 關鍵程式碼（Key Code Snippets）

**Adapter 定義（twitter/trending.ts）**：
```typescript
import { cli, Strategy } from '../../registry.js';

cli({
  site: 'twitter',
  name: 'trending',
  description: 'Twitter/X trending topics',
  domain: 'x.com',
  strategy: Strategy.COOKIE,
  browser: true,
  args: [
    { name: 'limit', type: 'int', default: 20, help: 'Number of trends to show' },
  ],
  columns: ['rank', 'topic', 'tweets', 'category'],
  func: async (page, kwargs) => {
    await page.goto('https://x.com/explore/tabs/trending');
    await page.wait(3);
    const ct0 = await page.evaluate(`(() => {
      return document.cookie.split(';')...
    })()`);
    if (!ct0) throw new AuthRequiredError('x.com', 'Not logged into x.com');
    // ... scrape DOM
  },
});
```

**Stealth 反偵測注入（stealth.ts）**：
```typescript
export function generateStealthJs(): string {
  return `
    (() => {
      // 1. navigator.webdriver → false（最常見的自動化偵測點）
      Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
        configurable: true,
      });
      // 2. window.chrome stub（headless Chrome 缺少此物件）
      if (!window.chrome) {
        window.chrome = { runtime: {...}, loadTimes: () => ({}), csi: () => ({}) };
      }
      // 3. 偽裝 navigator.plugins（空列表是偵測信號）
      // ...
    })();
  `;
}
```

## 安裝流程（Installation Flow）

### 安裝觸發方式

```
npm install -g @jackwener/opencli
  → scripts/postinstall.js 執行
    → 偵測 shell（bash/zsh/fish）
    → 寫入 tab completion 腳本
      → ~/.zshrc (zsh)
      → ~/.bash_completion.d/ (bash)
      → ~/.config/fish/completions/ (fish)
```

### 安裝時序圖

```
 用戶               npm                  postinstall.js        目標系統
   │                 │                        │                    │
   │─npm install -g──►│                        │                    │
   │                 │──scripts/postinstall──►│                    │
   │                 │                        │──寫入 completion──►│ ~/.zshrc
   │                 │                        │──寫入 completion──►│ ~/.config/fish/
   │                 │◄───────────────────────│                    │
   │◄────────────────│                        │                    │
   │                 │                        │                    │
   │ 安裝 Chrome Extension（手動，下載 zip）                         │
   │────────────────────────────────────────────────────────────►│
```

### 安裝產物清單

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.opencli/clis/` | 目錄 | 使用者自訂 Adapter 存放處 |
| `/usr/local/bin/opencli` | 執行檔 | CLI 入口點（npm -g 安裝） |
| `~/.zshrc`（或 bash/fish 等） | 文字檔 | Tab completion 腳本注入 |
| Chrome Extension（手動安裝） | 瀏覽器擴充套件 | Browser Bridge，監聽 `localhost:19825` WebSocket |

### 環境變數

| 變數名 | 值 | 設定時機 |
|--------|-----|---------|
| `OPENCLI_DAEMON_PORT` | 預設 `19825` | 執行時，自訂 daemon 監聽埠 |
| `OPENCLI_DAEMON_TIMEOUT` | 預設 `14400000`（4小時）| 執行時，daemon 閒置後自動關閉時間 |
| `OPENCLI_VERBOSE` | `1` | 執行時，顯示詳細 debug 訊息 |
| `OPENCLI_CDP_ENDPOINT` | CDP URL | 執行時，直接連 CDP（Electron/headless Chrome） |

> [!warning] 解除安裝
> 需手動移除：`npm uninstall -g @jackwener/opencli`；從 Chrome 移除 Browser Bridge Extension；清除 `~/.opencli/` 目錄；從 shell config 檔移除 completion 腳本。

---

## 使用案例地圖（Use Case Map）

### 案例總覽

| # | 使用案例 | 觸發方式 | 入口檔案 | 核心模組 |
|---|---------|---------|---------|---------|
| 1 | 抓 Twitter 熱門話題 | `opencli twitter trending` | `src/main.ts` | `discovery → registry → twitter/trending.ts → page.ts → daemon` |
| 2 | AI Agent 控制瀏覽器 | `opencli operate open/click/type` | `src/cli.ts` | `operate命令 → page.ts → daemon.ts → Extension → Chrome Tab` |
| 3 | 抓公開 API 資料 | `opencli hackernews top` | `src/main.ts` | `discovery → YAML pipeline → fetch step → output` |
| 4 | 自訂 Adapter 開發 | 寫 `.ts` 到 `~/.opencli/clis/` | `src/discovery.ts` | `dynamic loader → registry → execution` |

### 案例詳解

#### 案例 1：AI Agent 透過 `operate` 控制網頁

```
用戶/AI Agent：
  $ opencli operate open https://example.com
  $ opencli operate state
  $ opencli operate click 3
  $ opencli operate type 5 "hello world"
       │
       ▼
 src/cli.ts : operate 子命令定義
       │
       ▼
 src/browser/bridge.ts : BrowserBridge.connect()
   ├── _ensureDaemon() → 檢查 daemon 是否運行
   │   ├── 已運行 → 直接連線
   │   └── 未運行 → spawn daemon.ts 子程序（detached）
   │
   ▼
 src/browser/page.ts : Page
   ├── goto(url) → sendCommand('navigate') → daemon
   ├── evaluate(js) → sendCommand('exec') → daemon
   ├── click(selector) → sendCommand('click') → daemon
   └── type(selector, text) → sendCommand('type') → daemon
       │
       ▼
 daemon.ts (localhost:19825)
   │ HTTP POST → 轉發 WebSocket 給 Extension
   │
   ▼
 extension/background.js
   │ chrome.debugger.sendCommand('Runtime.evaluate', ...)
   │ 在真實 Chrome Tab 執行 JS
   │
   ▼
 結果返回 CLI，格式化輸出
```

#### 案例 2：直接用 CDP 控制 Electron App（如 Cursor IDE）

```
用戶：$ opencli cursor send "重寫這個函式"
       │
       ▼
 src/clis/antigravity/send.ts (或 cursor/send.ts)
       │
       ▼
 src/browser/cdp.ts : CDPBridge.connect({ cdpEndpoint })
   ├── 連接 Electron App 的 CDP WebSocket
   │   (通常是 http://localhost:9222)
   ├── Page.addScriptToEvaluateOnNewDocument → 注入 stealth
   │
   ▼
 CDPPage : IPage 實作
   ├── send('Runtime.evaluate', { expression }) → 執行 JS
   ├── send('Input.dispatchMouseEvent') → 模擬滑鼠點擊
   └── send('Input.dispatchKeyEvent') → 模擬鍵盤輸入
```

> [!tip] 如何用 OpenCLI 給 AI Agent 加上瀏覽器控制能力
> 在 `AGENT.md` 或 `.cursorrules` 裡加入：
> ```
> opencli list  # 讓 AI 自動發現所有可用工具
> ```
> 安裝 `opencli-operate` skill：
> ```bash
> npx skills add jackwener/opencli --skill opencli-operate
> ```
> Claude Code 或 Cursor 就能直接呼叫 `opencli operate open/click/type/get/screenshot` 控制你的 Chrome。

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | Dual-Engine 清楚分離宣告式(YAML)/程式式(TS) Adapter；Registry 模式讓新增 site 完全不改核心 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐⭐ | Dynamic Loader 支援用戶將自訂 `.ts` 丟進 `~/.opencli/clis/` 即自動載入；`opencli register` 可納入任何外部 CLI |
| 安全設計（Security） | ⭐⭐⭐⭐ | Daemon 多層 CSRF 防護；Fail-closed Origin 檢查；Cookie 不離開 Chrome；Stealth 反偵測 |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐⭐ | 每個 adapter 都有對應 `.test.ts`；有獨立的 unit/adapter/e2e test project 分組 |
| 文件品質（Documentation） | ⭐⭐⭐⭐ | README 詳細、有 SKILL.md AI Agent 整合指南、有 VitePress 文件站 |

> [!tip] 最值得學習的設計
> **「借用已登入 Session」模式**：不另外維護登入狀態，直接用瀏覽器已有的 Cookie，既安全又零摩擦。這個設計對於「需要登入才能抓的網站」是最優雅的解法。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知問題與限制

- **Chrome 依賴**：必須有正在運行的 Chrome + Extension，無法在純 headless CI 環境用 Browser Bridge 模式（可改用 CDP Direct Mode，但需要另起 Chrome）
- **Extension 手動安裝**：每次用戶設定都需要手動下載 zip 安裝 Extension，onboarding 有摩擦
- **反爬蟲對抗軍備競賽**：stealth.ts 的偽裝技術有時效性，隨著反爬蟲技術演進需持續更新
- **Adapter 數量 vs 維護成本**：73+ adapters，網站 UI/API 更新時大量 adapter 可能同時失效

### 🔮 改進建議（Improvement Suggestions）

1. 提供 Docker/一鍵安裝腳本，自動完成 Extension 安裝（Selenium Manager 的思路）
2. 加入 Adapter 健康監控——定期自動測試所有 adapter，失效時自動標記或發 PR 修復

## 效能基準（Benchmark）

> [!info] 無公開 Benchmark 數據
> 根據架構推斷的效能特性：

| 場景 | 效能特性 |
|------|---------|
| 公開 API 命令（hackernews、arxiv） | 極快，純 HTTP fetch，無瀏覽器啟動開銷 |
| Browser Bridge 命令（首次） | daemon 冷啟動約 2-5 秒 |
| Browser Bridge 命令（後續） | 毫秒級（daemon 持續運行 4 小時），等同直接 HTTP 呼叫 |
| operate 操作 | 每個命令 100-500ms（HTTP→WS→CDP 鏈路延遲） |
| 並發呼叫 | 單 daemon 單連線，無並發設計（串行執行） |

## 快速上手（Quick Start）

```bash
# 1. 安裝
npm install -g @jackwener/opencli

# 2. 安裝 Chrome Extension（從 GitHub Releases 下載 zip → chrome://extensions）

# 3. 診斷連線
opencli doctor

# 4. 試用公開 API 命令（不需登入）
opencli hackernews top --limit 5

# 5. 試用需登入的命令（先在 Chrome 登入 Bilibili）
opencli bilibili hot --limit 5

# 6. 給 AI Agent 加上瀏覽器控制能力
npx skills add jackwener/opencli --skill opencli-operate
# 之後 Claude Code 可直接呼叫：
opencli operate open https://example.com && opencli operate state
opencli operate click 3
opencli operate type 5 "hello"

# 7. 開發自訂 Adapter（見下方完整教學）
```

## 自訂 Adapter 開發教學（Custom Adapter Development Guide）

> [!important] 核心概念
> 所有自訂 Adapter 放到 `~/.opencli/clis/` 目錄，OpenCLI 啟動時由 `src/discovery.ts` 自動掃描並載入——不需要修改任何設定檔。

### 目錄結構

```
~/.opencli/clis/
  └── mysite/               ← 以網站名命名的資料夾
       ├── search.ts         ← TypeScript adapter（需要瀏覽器互動）
       ├── trending.yaml     ← YAML adapter（純 API 抓取）
       └── detail.ts
```

使用時：`opencli mysite search "關鍵字"` / `opencli mysite trending`

### 方法一：TypeScript Adapter（需要瀏覽器互動時使用）

適用場景：需要登入的網站、DOM 操作、多步驟流程、複雜資料擷取。

```typescript
import { cli, Strategy } from '../../registry.js';
import { AuthRequiredError, EmptyResultError, CommandExecutionError } from '../../errors.js';

cli({
  site: 'mysite',                    // 網站識別名
  name: 'search',                    // 子命令名 → opencli mysite search
  description: 'Search MySite',
  domain: 'www.mysite.com',
  strategy: Strategy.COOKIE,         // PUBLIC | COOKIE | HEADER
  args: [
    { name: 'query', required: true, help: 'Search query' },  // 位置參數
    { name: 'limit', type: 'int', default: 10, help: 'Max results' },  // 命名參數
  ],
  columns: ['title', 'url', 'date'], // 輸出欄位定義

  func: async (page, kwargs) => {
    const { query, limit = 10 } = kwargs;

    // 導航到目標頁面（自動注入 stealth 反偵測 + 等待 DOM 穩定）
    await page.goto('https://www.mysite.com');

    // 在頁面 context 中執行 JS（借用已登入的 cookie）
    const data = await page.evaluate(`
      (async () => {
        const res = await fetch('/api/search?q=${encodeURIComponent(String(query))}', {
          credentials: 'include'
        });
        return (await res.json()).results;
      })()
    `);

    // 錯誤處理：使用內建 Error 類別
    if (!Array.isArray(data)) throw new CommandExecutionError('MySite returned unexpected response');
    if (!data.length) throw new EmptyResultError('mysite search', 'Try a different keyword');

    // 回傳格式化資料（對應 columns 欄位）
    return data.slice(0, Number(limit)).map((item: any) => ({
      title: item.title,
      url: item.url,
      date: item.created_at,
    }));
  },
});
```

#### `page` 物件 API 參考

| 方法 | 說明 | 範例 |
|------|------|------|
| `page.goto(url)` | 導航到頁面 | `await page.goto('https://x.com')` |
| `page.evaluate(js)` | 在頁面 context 執行 JS | `await page.evaluate('document.title')` |
| `page.click(selector)` | 點擊元素 | `await page.click('.submit-btn')` |
| `page.type(selector, text)` | 輸入文字 | `await page.type('#search', 'hello')` |
| `page.waitForSelector(sel)` | 等待元素出現 | `await page.waitForSelector('.results')` |
| `page.wait(seconds)` | 等待指定秒數 | `await page.wait(3)` |
| `page.cookies()` | 取得當前頁面 cookies | 驗證登入狀態 |

#### Strategy 選擇指南

| Strategy | 常數 | 適用場景 | 範例網站 |
|----------|------|---------|---------|
| Public | `Strategy.PUBLIC` | 公開 API，無需登入 | HackerNews、arXiv、BBC |
| Cookie | `Strategy.COOKIE` | 需要登入的網站 | Bilibili、Zhihu、Twitter |
| Header | `Strategy.HEADER` | 需要 API Key | 第三方付費 API |

#### 錯誤處理最佳實踐

> [!warning] 請用內建 Error 類別，不要用原生 `Error`
> 內建類別會讓 CLI 輸出統一的錯誤提示，包含修復建議。

```typescript
import {
  AuthRequiredError,       // 未登入 → 提示使用者去 Chrome 登入
  EmptyResultError,        // 結果為空 → 提示換關鍵字
  CommandExecutionError,   // API 異常 → 顯示技術錯誤
  TimeoutError,            // 超時
  ArgumentError,           // 參數無效
} from '../../errors.js';

// 範例：檢查登入狀態
const ct0 = await page.evaluate(`(() => {
  return document.cookie.split(';').find(c => c.trim().startsWith('ct0='));
})()`);
if (!ct0) throw new AuthRequiredError('x.com', 'Not logged into x.com (no ct0 cookie)');
```

### 方法二：YAML Adapter（純 API 抓取，不需瀏覽器）

適用場景：網站有公開 API、簡單的 HTTP fetch + 資料轉換，不需要瀏覽器。

```yaml
site: mysite
name: trending
description: Get trending posts from MySite
domain: www.mysite.com
strategy: public           # public | cookie | header
browser: false             # true 則需要 Browser Bridge

args:
  limit:
    type: int
    default: 20
    description: Number of items

pipeline:                  # 宣告式資料處理管線
  - fetch:
      url: https://api.mysite.com/trending

  - map:                   # 轉換每筆資料
      rank: ${{ index + 1 }}
      title: ${{ item.title }}
      url: ${{ item.url }}
      score: ${{ item.score }}

  - filter: ${{ item.score > 100 }}    # 過濾（選用）

  - limit: ${{ args.limit }}            # 截斷筆數

columns: [rank, title, score, url]
```

#### Pipeline 步驟參考

| 步驟 | 用途 | 語法 |
|------|------|------|
| `fetch` | HTTP 請求取資料 | `url:` + 可選 `headers:` |
| `map` | 轉換每筆資料 | `${{ item.xxx }}`、`${{ index }}` |
| `filter` | 條件過濾 | `${{ item.score > 100 }}` |
| `limit` | 截斷筆數 | `${{ args.limit }}` |
| `download` | 下載媒體檔案 | `url:` + `dir:` + `filename:` |

#### 模板表達式

| 表達式 | 說明 |
|--------|------|
| `${{ args.limit }}` | CLI 參數值 |
| `${{ item.title }}` | 當前資料項的欄位 |
| `${{ index }}` | 當前索引（從 0 開始） |
| `${{ item.x \| sanitize }}` | Pipe 過濾器 |

> [!tip] 何時用 YAML vs TypeScript？
> YAML 表達式開始像寫程式（多行 JS、巢狀判斷）→ 改用 TypeScript。
> 經驗法則：`fetch → map → limit` 三步以內的場景用 YAML 最合適。

### 方法三：AI 自動生成 Adapter

```bash
# 1. AI 自動探索網站的 API 結構（分析 XHR/fetch 請求）
opencli explore https://example.com --site mysite

# 2. 根據探索結果自動生成 adapter 程式碼
opencli synthesize mysite

# 3. 一步到位：explore → synthesize → register
opencli generate https://example.com --goal "trending"
```

### 測試與驗證

```bash
# 確認 adapter 已被自動發現
opencli list | grep mysite

# 執行測試
opencli mysite search "rust" --limit 5
opencli mysite trending --format json    # 切換輸出格式
opencli mysite trending --format csv     # CSV 格式

# 搭配其他工具使用（pipe-friendly）
opencli mysite trending --format json | jq '.[0]'
```

### 實際範例：Twitter Trending Adapter（摘自原始碼）

> [!example] `src/clis/twitter/trending.ts` 的核心邏輯

```typescript
cli({
  site: 'twitter',
  name: 'trending',
  description: 'Twitter/X trending topics',
  domain: 'x.com',
  strategy: Strategy.COOKIE,
  browser: true,
  args: [
    { name: 'limit', type: 'int', default: 20, help: 'Number of trends to show' },
  ],
  columns: ['rank', 'topic', 'tweets', 'category'],
  func: async (page, kwargs) => {
    const limit = kwargs.limit || 20;

    // 導航到 Twitter Trending 頁面
    await page.goto('https://x.com/explore/tabs/trending');
    await page.wait(3);

    // 驗證登入：檢查 ct0 cookie 是否存在
    const ct0 = await page.evaluate(`(() => {
      return document.cookie.split(';').map(c=>c.trim())
        .find(c=>c.startsWith('ct0='))?.split('=')[1] || null;
    })()`);
    if (!ct0) throw new AuthRequiredError('x.com', 'Not logged into x.com (no ct0 cookie)');

    // 從 DOM 擷取 trending topics
    await page.wait(2);
    const trends = await page.evaluate(`(() => {
      const items = [];
      const cells = document.querySelectorAll('[data-testid="trend"]');
      cells.forEach((cell) => {
        const text = cell.textContent || '';
        if (text.includes('Promoted')) return;  // 跳過廣告
        const container = cell.querySelector(':scope > div');
        if (!container) return;
        const divs = container.children;
        if (divs.length < 2) return;
        const topic = divs[1].textContent.trim();
        if (!topic) return;
        // ... 擷取排名、分類、推文數
        items.push({ rank, topic, tweets, category });
      });
      return items;
    })()`);

    return trends.slice(0, limit);
  },
});
```

## `operate` 實戰指南（Operate Practical Guide）

> [!important] 核心觀念
> 你不需要事先知道參數是什麼——`state` 就是你的眼睛，每次操作後重新 `state` 一次就能看到新的元素索引。整個流程就是：**探索 → 互動 → 擷取**。

### 從零開始控制一個網站：三步流程

```bash
# 步驟 0：確保環境正常（只需跑一次）
opencli doctor

# 步驟 1：打開網站 + 看 DOM 結構
opencli operate open https://目標網站.com && opencli operate state
```

`state` 回傳結構化 DOM，每個可互動元素都有 `[N]` 索引號碼：
```
[1] a "首頁"
[2] input "搜尋..."
[3] button "登入"
[4] div "文章標題一"
[5] div "文章標題二"
```

```bash
# 步驟 2：用索引互動
opencli operate type 2 "AI agent" && opencli operate click 3   # 在搜尋框輸入 → 按按鈕
opencli operate state                                           # 看結果頁面的新索引

# 步驟 3：擷取資料
opencli operate eval "JSON.stringify([...document.querySelectorAll('.result')].map(e => e.textContent))"
```

### 進階技巧：用 `network` 發現隱藏 API

> [!tip] 最重要的實戰技巧
> 大多數網站背後都有 JSON API，比抓 DOM 穩定得多。先用 `network` 探索 API，再決定用 API 還是 DOM 擷取。

```bash
opencli operate open https://目標網站.com
opencli operate state                        # 觸發頁面載入
opencli operate network                      # 查看攔截到的 API 請求
opencli operate network --detail 0           # 看第 0 筆請求的完整 response body
```

如果發現了 API，就能直接用 `eval + fetch()` 呼叫，不需要慢慢點 DOM。

### 完整指令速查表

| 類型 | 指令 | 說明 |
|------|------|------|
| **導航** | `open <url>` | 打開網頁 |
| | `back` | 上一頁 |
| | `scroll down/up` | 捲動（可加 `--amount 1000`） |
| **探索** | `state` | 看 DOM 結構（**最重要的指令，免費即時**） |
| | `network` | 看攔截到的 API 請求 |
| | `network --detail N` | 看第 N 筆請求的完整內容 |
| | `screenshot [path.png]` | 截圖（**昂貴，僅用戶明確要求時才用**） |
| **互動** | `click <N>` | 點擊索引 N 的元素 |
| | `type <N> "text"` | 在索引 N 輸入文字 |
| | `select <N> "option"` | 下拉選單選擇 |
| | `keys "Enter"` | 按鍵（Enter/Escape/Tab/Control+a） |
| **讀取** | `get title` | 頁面標題 |
| | `get url` | 當前 URL |
| | `get text <N>` | 元素文字內容 |
| | `get value <N>` | 輸入框的值（用於驗證輸入） |
| | `get html --selector "h1"` | 特定元素 HTML |
| | `get attributes <N>` | 元素屬性 |
| | `eval "JS程式碼"` | 執行 JS 擷取資料（**唯讀，禁止用於點擊/導航**） |
| **等待** | `wait selector ".loaded"` | 等元素出現 |
| | `wait text "成功"` | 等文字出現 |
| | `wait time 3` | 等 3 秒 |
| **固化** | `init site/cmd` | 生成 Adapter 骨架到 `~/.opencli/clis/` |
| | `verify site/cmd` | 測試 Adapter 是否正常 |
| | `close` | 關閉自動化視窗 |

### 操作原則

1. **每次操作後都 `state`**——不要猜索引，看到才操作
2. **指令可用 `&&` 串接**——`type 3 "hello" && type 4 "world" && click 7` 一次送出，減少延遲
3. **`eval` 只用於讀取**——點擊和輸入一律用 `click`/`type`，因為 `eval` 不會觸發滾動和 CDP 點擊管線
4. **先探索 API 再決定策略**——`network` 找到 JSON API 後，直接用 `fetch()` 比 DOM scraping 穩定十倍
5. **別名**：`opencli op` = `opencli operate`

### 完整工作流範例：從探索到固化

```bash
# 1. 探索網站
opencli operate open https://news.ycombinator.com
opencli operate state

# 2. 發現 API
opencli operate network
opencli operate network --detail 0

# 3. 用 eval 驗證資料擷取
opencli operate eval "JSON.stringify([...document.querySelectorAll('.titleline a')].slice(0,5).map(a => ({title: a.textContent, url: a.href})))"

# 4. 固化為 CLI Adapter
opencli operate init hn/top              # 生成骨架 → ~/.opencli/clis/hn/top.ts
# （編輯檔案，填入 func 邏輯）
opencli operate verify hn/top            # 測試

# 5. 之後一行搞定
opencli hn top --limit 5 --format json
```

### 疑難排解

| 問題 | 解法 |
|------|------|
| "Browser not connected" | `opencli doctor` 診斷 |
| "attach failed: chrome-extension://" | 暫時停用 1Password 等擴充套件 |
| 找不到元素 | `opencli operate scroll down && opencli operate state`（可能在畫面外） |
| 操作後索引失效 | 頁面變化後必須重新 `state` 取得新索引 |

---

## 替代方案比較（Alternative Approaches）

> [!info] 不一定需要 OpenCLI
> 如果你的環境已有其他瀏覽器控制工具，可以根據需求選擇最適合的方案。

### OpenCLI operate vs claude-in-chrome（MCP）vs Playwright

| 比較維度 | OpenCLI operate | claude-in-chrome MCP | Playwright / Puppeteer |
|---------|----------------|---------------------|----------------------|
| **安裝** | 需裝 npm + Chrome Extension | Chrome Extension（可能已裝） | npm/pip 安裝 |
| **操控方式** | CLI 指令 | MCP 工具直接在對話中呼叫 | 程式碼（Node.js/Python） |
| **登入 Session** | 重用 Chrome cookies | 重用 Chrome 當前分頁 | 需手動匯入 cookies |
| **AI Agent 整合** | 透過 skill + AGENT.md | 原生整合 Claude Code | 需自行封裝 |
| **反偵測** | 內建 stealth.ts | 無（用真實 Chrome） | 需額外安裝 stealth plugin |
| **可固化為 CLI** | ✅ `init` → Adapter | ❌ | ❌（需自行封裝） |
| **API 探索** | ✅ `network` 指令 | ✅ `read_network_requests` | ✅ request interception |
| **Headless CI** | ❌（Browser Bridge 需 GUI） | ❌（需 Chrome GUI） | ✅ headless 模式 |
| **LLM Token 成本** | 零（runtime 無 LLM 呼叫） | 零 | 零 |

### 選擇建議

> [!tip] 快速決策指南

- **只想在當前對話快速控制瀏覽器讀資料** → 用 **claude-in-chrome**（已安裝，零設定）
- **想把操作固化成可重複執行的 CLI 命令**（每天自動抓資料、CI 排程） → 用 **OpenCLI**
- **需要 headless 環境 / CI/CD** → 用 **Playwright**
- **需要控制 Electron App**（Cursor、ChatGPT、Notion） → 用 **OpenCLI CDP Direct Mode**

---

## 我的心得（My Takeaways）

這個 repo 回答了用戶問的問題：**「如果要控制瀏覽器某些網站有 CLI 功能，要怎麼做？」**

OpenCLI 給了一個非常完整的答案：

1. **讓 AI Agent 控制瀏覽器**：安裝 `opencli-operate` skill，Claude Code 就能直接用 `opencli operate open/click/type/state` 控制真實 Chrome
2. **把網站變成 CLI 命令**：寫一個 TypeScript Adapter（繼承 `cli()` 函式），放到 `~/.opencli/clis/` 就自動生效
3. **安全地重用登入 Session**：不用管密碼，用 `strategy: Strategy.COOKIE` 讓 OpenCLI 透過 Browser Bridge 借用 Chrome 的 cookies

實戰上的關鍵心得：**先用 `network` 探索 API，再決定用 API 還是 DOM**——這個順序能省下大量的維護成本。DOM scraping 會因為網站改版而壞掉，但 API 通常更穩定。

「Daemon 做橋接」的架構設計值得借鑑：把長連線（WebSocket）和短連線（HTTP）的職責分開——CLI 只需要做 HTTP POST，複雜的狀態管理交給 Daemon。這讓 CLI 本身非常簡單，但功能卻不受限制。

如果只是臨時性的瀏覽器操作，claude-in-chrome MCP 工具已經夠用；OpenCLI 的真正價值在於「固化」——把一次性操作變成可重複、可分享的 CLI 命令。

---

## 待補充（Open Questions）

- Browser Bridge 模式必須有正在執行的 Chrome + Extension，這在 CI/CD 環境中無法使用。OpenCLI 的 CDP Direct Mode 在實際自動化測試或定時排程場景中的完整設定流程是什麼？（建議搜尋：`opencli CDP direct mode headless CI/CD setup`）
- `opencli operate state` 回傳結構化 DOM 帶 `[N]` 索引，這個 DOM 序列化的方式是完整 DOM tree 還是 accessibility tree？對於複雜頁面（上千個元素），token 消耗量是否會成為瓶頸？（建議搜尋：`chrome CDP accessibility tree DOM serialization token cost`）
- 73+ 個預建 Adapter 隨著各網站 UI 和 API 更新可能同時失效，作者如何維護這些 Adapter？是否有自動化健康檢查（health check）或社群貢獻機制？（建議搜尋：`opencli adapter maintenance automated testing health check community`）
- `opencli record` 功能宣稱可以錄製使用者操作並自動生成 Adapter，生成的程式碼品質如何？與手動撰寫的 Adapter 相比，是否需要大量手動修改才能穩定運行？（建議搜尋：`opencli record adapter generation quality automation`）
- OpenCLI 在 Chrome Extension 安裝後，所有通過 Daemon 的操作都有 CSRF 防護。但若 Daemon 在 localhost:19825 上運行，本機的其他惡意程序是否有辦法透過同樣的 HTTP 介面控制瀏覽器？（建議搜尋：`localhost daemon security CSRF protection attack surface`）

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | Browser Bridge（Chrome Extension + Daemon）、CDP Direct Mode、Stealth 反偵測、5 種認證策略（public/cookie/header/intercept/ui）、Daemon 埠號 19825、`opencli operate` 指令集 |
| **理解（半被動）** | 解釋概念含義及關聯 | CLI → HTTP → Daemon → WebSocket → Extension → CDP 的完整鏈路；「借用已登入 Session」解決了認證問題；Dual-Engine（YAML/TS）讓簡單場景和複雜場景都有最優的表達方式 |
| **分析（主動）** | 檢驗論點、找出假設 | 反偵測依賴 stealth.ts 的特定技術，當反爬蟲系統升級（如行為分析、TLS 指紋）時可能失效；73+ adapter 的維護成本是長期隱患；架構假設用戶有 Chrome 且已登入，對 CI/CD headless 場景需要另一套方案 |
| **應用（主動）** | 將知識套用情境 | (1) 在 AGENT.md 加入 `opencli list`，讓 Claude Code 能發現並呼叫所有工具；(2) 仿照 `cli()` 工廠函式設計，為自己的專案開發網站 Adapter |
| **評估（主動）** | 判斷方案優劣 | Browser Bridge 模式 vs CDP Direct 模式：前者更安全（憑證留在 Chrome）、更易用（不需特殊啟動參數），但需手動安裝 Extension；後者適合 CI/headless 環境，但需要 `--remote-debugging-port` 啟動 Chrome，且需要自行管理登入狀態 |

### 分析型追問（Socratic Follow-up）

- **澄清**：`opencli operate state` 回傳的「結構化 DOM 帶 `[N]` 索引」是如何生成的？是完整 DOM 還是 accessibility tree？這對 token 消耗有何影響？
- **假設**：Stealth 反偵測的核心假設是「反爬蟲只看 JS 全域變數」——若目標網站升級到行為指紋分析（滑鼠移動軌跡、打字節奏），stealth.ts 的效果會如何？
- **證據**：12k Stars 在 3 週內達成（2026-03-14 到 2026-04-03）——這個成長速度是否代表市場有真實需求，還是主要來自 AI/自動化社群的話題效應？
- **觀點**：若從網站方（如 Bilibili、Twitter）的立場看，OpenCLI 對他們的服務條款（Terms of Service）有何影響？這個工具的合規性邊界在哪裡？
- **後果**：若大量 AI Agent 使用 OpenCLI 自動化操作，對目標網站的伺服器負載和反爬蟲策略升級有何影響？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** Stealth 反偵測機制可能在沒有預警的情況下失效（網站升級反爬蟲），導致大量 Adapter 同時無聲失敗——CLI 命令不報錯但回傳空資料或錯誤資料

2. **什麼情況下會失敗？**
   - Chrome 未運行或未登入目標網站
   - Chrome Extension 未安裝（onboarding 最常見的失敗點）
   - 目標網站啟用了 CSP（Content Security Policy）阻擋 JS 注入
   - CI/CD 無 GUI 環境（需要改用 CDP Direct Mode + headless Chrome）
   - Daemon port 19825 被其他程序佔用

3. **有沒有更好的替代方案？**
   - **Playwright / Puppeteer**：更成熟的生態、更好的 headless 支援，但需要另管登入 session（cookies 要手動匯出/匯入）
   - **Browser Use（Python）**：同樣針對 AI Agent 的瀏覽器控制，以 LLM 做更智慧的 DOM 理解，但有 LLM API 成本
   - **OpenCLI 的優勢**：零 token 成本、重用已登入 Chrome、統一 CLI 介面給 AI Agent 發現和呼叫

## 相關連結（Related）

- [[CLAUDE-CODE-ARCHITECTURE]] — Claude Code 如何整合外部 CLI 工具（AGENT.md 機制）
- [[BROWSER-AUTOMATION-CDP]] — Chrome DevTools Protocol（CDP）的核心 API 與使用方式
- [[AI-AGENT-TOOLS]] — AI Agent 工具發現與呼叫的設計模式
- [[STEALTH-BROWSER-AUTOMATION]] — 瀏覽器自動化的反偵測技術全景

## References

- [GitHub Repo](https://github.com/jackwener/opencli) — jackwener/opencli, Apache 2.0
- [npm Package](https://www.npmjs.com/package/@jackwener/opencli) — @jackwener/opencli
- [官方文件](https://jackwener.github.io/opencli/) — VitePress 文件站
- [operate Skill 說明](https://github.com/jackwener/opencli/blob/main/skills/opencli-operate/SKILL.md) — AI Agent 瀏覽器控制完整指南
