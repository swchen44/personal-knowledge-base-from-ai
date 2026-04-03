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

# 7. 開發自訂 Adapter（寫到 ~/.opencli/clis/ 即自動載入）
# 參考 src/clis/twitter/trending.ts 的格式
```

## 我的心得（My Takeaways）

這個 repo 回答了用戶問的問題：**「如果要控制瀏覽器某些網站有 CLI 功能，要怎麼做？」**

OpenCLI 給了一個非常完整的答案：

1. **讓 AI Agent 控制瀏覽器**：安裝 `opencli-operate` skill，Claude Code 就能直接用 `opencli operate open/click/type/state` 控制真實 Chrome
2. **把網站變成 CLI 命令**：寫一個 TypeScript Adapter（繼承 `cli()` 函式），放到 `~/.opencli/clis/` 就自動生效
3. **安全地重用登入 Session**：不用管密碼，用 `strategy: Strategy.COOKIE` 讓 OpenCLI 透過 Browser Bridge 借用 Chrome 的 cookies

這個「Daemon 做橋接」的架構設計值得借鑑：把長連線（WebSocket）和短連線（HTTP）的職責分開——CLI 只需要做 HTTP POST，複雜的狀態管理交給 Daemon。這讓 CLI 本身非常簡單，但功能卻不受限制。

---

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
