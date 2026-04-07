---
title: "Claude Code Team Memory 深度解析 — Server、REST API、分類規則與啟用方式"
date: 2026-04-08
date_uncertain: false
category: CodeAnalysis
tags:
  - code-analysis
  - ai/agent
  - memory-system
  - team-collaboration
  - context-engineering
source: "本地反編譯版 /Users/swchen.tw/git/claude-code/src"
source_type: code
author: "Anthropic (decompiled / reverse-engineered)"
status: notes
links:
  - "[[CLAUDE-CODE-MEMORY-SYSTEM]]"
  - "[[CLAUDE-MEMORY-ENGINE]]"
  - "[[FORKED-SUBAGENT-PATTERN]]"
---

## 摘要（Summary）

本筆記整理 2026-04-08 針對 Claude Code **Team Memory 系統**的深度原始碼探索結果，涵蓋四大主題：
1. Team Memory 上傳到哪個 Server 及 REST API 契約
2. 其他 Team 成員如何共享同一份記憶
3. `memory/team/` 目錄的更新時機、存放內容與分類決策規則
4. `feature('TEAMMEM')` 的本質與啟用方式

所有結論均直接對應到本地反編譯版的具體檔案路徑。

## 關鍵洞察（Key Insights）

- **Team Memory Server = `https://api.anthropic.com`**，這是 Anthropic 官方 API 伺服器，並非某個隱藏的內部服務 — 參見 [[CLAUDE-CODE-MEMORY-SYSTEM]]
- **「Anthropic Org」≠ Anthropic 公司**，而是任何購買 claude.ai Team/Enterprise 方案的公司組織
- **分類決策由 extraction sub-agent 在 query 結束後自動判斷**，依據是各記憶類型的 `<scope>` 指示，人工不需介入
- **`feature('TEAMMEM')` 是 build-time 靜態開關**，反編譯版全部關閉，需手動修改 polyfill 才能本地啟用

## 詳細內容（Details）

### 一、Team Memory 的 Server 與 REST API

**Server 位址**：

```typescript
// src/constants/oauth.ts:85
BASE_API_URL: 'https://api.anthropic.com'

// 端點格式 (src/services/teamMemorySync/index.ts:163)
`${BASE_API_URL}/api/claude_code/team_memory?repo=${encodeURIComponent(repoSlug)}`
// 可用環境變數覆寫：TEAM_MEMORY_SYNC_URL
```

**完整 REST API 契約**：

```
GET  /api/claude_code/team_memory?repo={owner/repo}            → 完整記憶資料 + 每個 key 的 sha256
GET  /api/claude_code/team_memory?repo={owner/repo}&view=hashes → 只有 metadata（無內容，省流量）
PUT  /api/claude_code/team_memory?repo={owner/repo}            → upsert 上傳（只傳 hash 有差異的 key）
404  → 尚無資料（第一次使用時正常）
```

**身份驗證（Authentication）**：需 claude.ai OAuth Bearer token，且必須同時有兩個 scope：
- `user:inference`
- `user:profile`

> [!warning] API key 模式不支援
> 若使用 `ANTHROPIC_API_KEY` 直接呼叫而非 `claude login` OAuth 登入，`isUsingOAuth()` 回傳 `false`，Team Memory Sync 完全不啟動。

**Repo 識別方式**：`getGithubRepo()` 解析當前工作目錄的 git remote URL，取出 `owner/repo`（**只支援 github.com**，不支援 GitLab、Bitbucket 等）。

---

### 二、其他 Team 成員如何取得同一份記憶

**三個必要條件同時滿足**：

| 條件 | 說明 |
|------|------|
| **同一 GitHub repo** | 所有人的工作目錄 git remote 指向同一個 `owner/repo` |
| **同一 Anthropic 組織帳號** | Server 端以 org 成員資格控管存取（claude.ai Team/Enterprise 方案） |
| **claude.ai OAuth 登入** | 必須執行 `claude login`，不能只用 API key |

**自動同步流程**（不需手動操作）：

```
每位成員 session 啟動
  → startTeamMemoryWatcher()
  → pullTeamMemory()             ← 自動從 server 拉最新版本到本地
  → fs.watch(teamDir)            ← 監聽本地變動
        │
        ├─ 有檔案變動 → debounce 2 秒 → pushTeamMemory()  ← 上傳 hash 差異的檔案
        └─ 無變動 → 等待
```

**重要同步語義**：
- Pull 時 server 優先（server wins per-key）
- Push 只上傳 hash 有差異的 key（delta upload），不上傳整個目錄
- **刪除本地檔案不會同步刪除 server 端**，下次 pull 還會把它拉回來

> [!important] 「Anthropic Org」的正確理解
> 程式碼中的 `org` 指 **Anthropic 帳號平台上的組織（Organization）**，即在 `platform.claude.com` 建立的公司帳號。**任何公司**訂閱 claude.ai Team/Enterprise 方案後，旗下所有成員都能共享同一 GitHub repo 的 team memory，不限於 Anthropic 內部使用。

---

### 三、`memory/team/` 的更新時機

**三個觸發點**：

```
觸發點 1：Session 啟動
  → pullTeamMemory()：拉取 server 最新版本

觸發點 2：Query loop 結束（模型產出 final response）
  → executeExtractMemories()
  → 背景子代理（extraction sub-agent）決定哪些寫 team/、哪些寫 private 目錄

觸發點 3：本地 team/ 目錄有檔案變動（fs.watch）
  → debounce 2 秒
  → pushTeamMemory()：上傳變更到 server
```

---

### 四、存放什麼 — 四種記憶類型的 Team/Private 分類規則

分類決策由 **extraction sub-agent** 自動判斷，依據 `src/memdir/memoryTypes.ts` 中各類型的 `<scope>` 標籤：

| 類型 | scope 規則 | 典型 team 案例 | 典型 private 案例 |
|------|-----------|--------------|-----------------|
| **user** | **永遠 private** | — | 使用者溝通偏好、個人背景 |
| **feedback** | **預設 private**，僅「全專案慣例、所有貢獻者應遵守」才存 team | 「不能 mock DB」的測試政策 | 「你的回應要簡短」個人風格 |
| **project** | **強烈傾向 team** | merge freeze 日期、架構決策動機 | 私人 spike 進度 |
| **reference** | **通常 team** | Linear 專案 URL、Grafana dashboard | 個人筆記連結 |

**安全限制（硬性規則）**：

```
You MUST avoid saving sensitive data within shared team memories.
For example, never save API keys or user credentials.
```

加上 `secretScanner` 在 push 前掃描所有檔案，偵測到 secret 的檔案會被跳過不上傳。

**目錄結構**（啟用後）：

```
~/.claude/projects/<slug>/memory/
├── MEMORY.md              ← private 索引（≤200 行）
├── user_profile.md        ← 永遠 private
├── feedback_my_style.md   ← private
└── team/
    ├── MEMORY.md          ← team 索引（同步到 server，≤200 行）
    ├── feedback_testing_policy.md
    ├── project_arch_decisions.md
    └── reference_linear.md
```

兩個 `MEMORY.md` 都會被載入 system prompt，各自有 200 行上限。

---

### 五、`feature('TEAMMEM')` 的本質與啟用方式

**根本原因**：`feature()` 是 Bun **編譯期巨集（build-time macro）**，來自 `bun:bundle`。Anthropic 官方在打包時決定哪些 flag 為 `true`，反編譯版 polyfill 一律回傳 `false`：

```typescript
// src/entrypoints/cli.tsx:3（反編譯版 polyfill）
const feature = (_name: string) => false;  // 所有 feature flag 全關
```

**本地啟用方式**（僅修改一行）：

```typescript
// 改為：
const feature = (name: string) => {
  const enabled = new Set(['TEAMMEM'])
  return enabled.has(name)
}
```

然後重啟：`bun run dev`

**但還需要通過第二層運行時檢查**：

```typescript
isTeamMemorySyncAvailable() = isUsingOAuth()
// → 需 claude.ai OAuth 登入（user:inference + user:profile scope）

isTeamMemoryEnabled()
// → isAutoMemoryEnabled() === true（沒設 CLAUDE_CODE_DISABLE_AUTO_MEMORY）
// → 不在 KAIROS 模式（KAIROS 的 append-only log 與 team sync 不相容）
```

**可用 mock server 本地測試**：

```bash
# 指向自己的 mock server
export TEAM_MEMORY_SYNC_URL="http://localhost:3000"
bun run dev
```

> [!warning] KAIROS 與 Team Memory 互斥
> `src/memdir/memdir.ts:427`：KAIROS 的 append-only log 模式與 team sync 設計上不相容。若同時啟用，KAIROS 優先，Team Memory sync 停止。

---

### 六、各方案支援矩陣

| 使用情境 | Team Memory 可用？ |
|---------|-----------------|
| 個人 claude.ai Pro，獨自使用 | ❌ 無 org 可共享 |
| claude.ai Team 方案，多人同帳號 | ✅ 同 org + 同 GitHub repo |
| claude.ai Enterprise | ✅ |
| API key 直接呼叫（無 OAuth） | ❌ |
| AWS Bedrock / GCP Vertex | ❌ non-firstParty provider |
| 本地反編譯版（未改 polyfill） | ❌ feature flag 關閉 |
| 本地反編譯版（改 polyfill + mock server） | ✅ 可測試 code path |

## 我的心得（My Takeaways）

Team Memory 的設計揭示了一個重要的 **「共享知識 vs 個人偏好」分離原則**：
- **個人偏好**（user type、個人 feedback）永遠私有，不干擾他人的 Claude 行為
- **專案知識**（project、reference、全專案 feedback）自動共享，讓整個團隊的 Claude 都擁有相同的專案脈絡

這個設計解決了「讓 AI 了解我的同時，不把我的個人風格強加給同事」的根本矛盾。

另一個洞察是 `feature('TEAMMEM')` 作為 build-time 開關的設計哲學 — 未發布的功能在反編譯版中雖然程式碼完整存在，但透過靜態分析可知它們全部被死碼消除（DCE）。要「解鎖」這些功能，改 polyfill 是最直接的路徑，但需要配套的 OAuth + Team 帳號才能真正運作。

## 相關連結（Related）

- [[CLAUDE-CODE-MEMORY-SYSTEM]] — 完整六層記憶架構概覽，本筆記是其 team memory 子章節的深化
- [[CLAUDE-MEMORY-ENGINE]] — 個人記憶引擎設計，與 team memory 的私有側設計呼應
- [[FORKED-SUBAGENT-PATTERN]] — extraction sub-agent 用來寫 team memory 的背後技術

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | Server：`https://api.anthropic.com/api/claude_code/team_memory`；三個同步觸發點（啟動/query結束/檔案變動）；四種記憶類型的 scope 規則；`feature('TEAMMEM')` polyfill 位置 `cli.tsx:3` |
| **理解（半被動）** | 解釋概念與關聯 | Team memory 的「共享條件」（同 org + 同 repo + OAuth）與「分類邏輯」（sub-agent 自動判斷 scope）是兩個獨立層次；feature flag 的 build-time 本質決定了「改 polyfill」是唯一本地啟用路徑 |
| **分析（主動）** | 找出假設與漏洞 | 假設 1：所有人都用 github.com（不支援 GitLab）。假設 2：deletion 不傳播是有意設計（防誤刪），但可能造成「刪不掉」的問題。假設 3：KAIROS 與 team sync 真的完全不相容，還是只是當前 tradeoff？ |
| **應用（主動）** | 規劃可執行行動 | 行動 1：若要本地測試 team memory，改 `cli.tsx:3` polyfill + 設 `TEAM_MEMORY_SYNC_URL` 指向 mock server。行動 2：設計自己的 Agent 時，可借鑑「user type 永遠 private，project type 預設共享」的分類框架 |
| **評估（主動）** | 比較替代方案 | vs 把 team memory 存在 git repo 本身（CLAUDE.md）：git 方案對所有人立即可見但需 commit，team memory 是自動累積但刪除不傳播；vs Notion/Confluence 等知識庫：後者需手動維護，team memory 是 AI 自動提取 |

### 分析型追問（Socratic Follow-up）

- **澄清**：`per-org tunable` 的 `max_entries` 上限實際數值是多少？不同方案有無差異？
- **假設**：若兩位 team 成員同時寫同一個 team memory key（race condition），server 的 upsert 如何解決衝突？409 之後的重試邏輯是否足夠？
- **證據**：`feedback` type 的「全專案慣例 vs 個人偏好」邊界由 LLM 自行判斷，這個判斷的準確率是多少？有無 benchmark？
- **觀點**：「刪除不傳播」對安全是好設計（防誤刪），但若需要刪除洩漏的 secret 記憶，應如何操作？
- **後果**：若 team memory 累積了大量過時決策（如：已廢棄的架構方向），12 個月後 AutoDream 能否有效清除它們？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？**
   - **刪除不可逆傳播**：若有人在本地刪掉一個 team memory 檔案，下次 pull 會從 server 還原，永遠刪不掉（除非有 server 端的管理 API）。若該檔案包含錯誤資訊，全 team 成員都會持續受影響。

2. **什麼情況下會失敗？**
   - **OAuth token 過期**：`isUsingOAuth()` 失效，sync 靜默停止，無任何錯誤提示
   - **非 github.com remote**：`getGithubRepo()` 回傳 `null`，無法形成 `owner/repo` key，sync 不啟動
   - **KAIROS 模式啟用**：`KAIROS` 優先，team sync 停用
   - **413 超過 org 上限**：push 被拒，需等 server 通知 `max_entries` 後才能自動裁切重試
   - **反編譯版未改 polyfill**：`feature('TEAMMEM') === false`，整個功能被靜態消除

3. **有沒有更好的替代方案？**
   - **替代方案：CLAUDE.md + git**：所有 team 共識直接寫入 `CLAUDE.md` 並 commit，透明度最高、版本追蹤最完整，但需要人工維護
   - **何時選替代**：對於穩定的、不常變動的 team 規範（如 coding style），CLAUDE.md 更可靠；對於動態的、會快速累積的專案狀態（如誰在做什麼），team memory 自動化更有優勢

## References

- 原始碼檔案：
  - `src/services/teamMemorySync/index.ts`（REST API + sync 邏輯）
  - `src/services/teamMemorySync/watcher.ts`（fs.watch + debounce）
  - `src/memdir/teamMemPaths.ts`（路徑驗證 + 安全防護）
  - `src/memdir/memoryTypes.ts`（四種記憶類型的 scope 定義）
  - `src/services/extractMemories/prompts.ts`（extraction sub-agent 的分類提示）
  - `src/constants/oauth.ts`（server URL + OAuth scope）
  - `src/entrypoints/cli.tsx:3`（feature flag polyfill）
- 相關討論：本對話 2026-04-08
