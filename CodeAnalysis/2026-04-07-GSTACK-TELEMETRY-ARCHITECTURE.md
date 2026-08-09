---
title: "gstack 程式碼架構分析 — Telemetry 是怎麼做到的"
date: 2026-04-07
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#telemetry"
  - "#bash"
  - "#supabase"
  - "#privacy"
source: "https://github.com/garrytan/gstack"
source_type: code
author: "garrytan"
status: notes
links:
  - "[[CLAUDE-SKILL-ARCHITECTURE]]"
  - "[[SUPABASE-EDGE-FUNCTIONS]]"
  - "[[PRIVACY-TIERS-DESIGN]]"
github_stars: unknown
github_language: TypeScript+Bash
date_uncertain: true
---

## 摘要（Summary）

gstack 是一套以 Claude Code skill 為核心的開發者工作流程套件（v0.15.15.0）。本筆記聚焦在它的 **telemetry（遙測）** 子系統：怎麼在「skill 是獨立 `claude -p` 子程序、彼此沒有共享 loader」的限制下，做到本地寫入 → 背景同步 → Supabase 入庫的完整資料流，並支援三層隱私（off / anonymous / community）。

## Why — 為什麼存在？

- **核心動機**：每個 skill 透過 `claude -p` 獨立啟動，沒有共享 process，沒有 daemon。要追蹤「哪些 skill 被用、用多久、有沒有崩潰」，必須在 skill 自己的 bash preamble 裡完成。
- **取代/改善什麼**：取代「無觀測、靠 GitHub issue 才知道使用者踩坑」的盲飛狀態。
- **目標用戶**：gstack 維護者本人（追 bug、看趨勢），同時尊重隱私意識強的開發者。

## What — 是什麼？

- **主要功能**：
  - 每個 skill 執行時自動記一筆 JSONL 到 `~/.gstack/analytics/skill-usage.jsonl`
  - 背景同步到 Supabase edge function（rate-limited 5 分鐘一次）
  - 三層隱私：`off` / `anonymous` / `community`
  - 崩潰歸因（error_class）、session 串接、跨 skill 共現分析（skill_sequences view）
  - 本地保留 `_repo_slug` / `_branch` 欄位但**永不上傳**
- **不做什麼（Non-goals）**：不送程式碼、檔案路徑、repo 名稱、使用者帳號
- **技術棧**：Bash（client）、TypeScript / Deno（Supabase edge function）、PostgreSQL + RLS

## How — 如何運作？

### 系統架構圖

```
┌──────────────────────────────────────────────────────┐
│  Claude Code session (claude -p)                     │
│  ┌────────────────────────────────────────────────┐  │
│  │ skill SKILL.md                                 │  │
│  │   └─ Preamble bash (生成自 preamble.ts)        │  │
│  │       ├─ inline JSONL append (always)          │  │
│  │       └─ .pending-$SESSION_ID marker           │  │
│  └─────────────────┬──────────────────────────────┘  │
│                    │ skill 結束時 epilogue           │
│                    ▼                                  │
│  ┌────────────────────────────────────────────────┐  │
│  │ bin/gstack-telemetry-log (bash)                │  │
│  │   ├─ 讀 tier (off/anonymous/community)         │  │
│  │   ├─ finalize 別人的 stale .pending            │  │
│  │   ├─ 寫一筆完整 JSON 到 skill-usage.jsonl      │  │
│  │   └─ 背景觸發 sync &                           │  │
│  └─────────────────┬──────────────────────────────┘  │
└────────────────────┼─────────────────────────────────┘
                     ▼
        ┌────────────────────────────┐
        │ bin/gstack-telemetry-sync  │
        │  ├─ 5min rate limit        │
        │  ├─ cursor-based 增量讀    │
        │  ├─ 剝除 _repo_slug/_branch│
        │  └─ POST batch (max 100)   │
        └─────────────┬──────────────┘
                      │ HTTPS
                      ▼
       ┌──────────────────────────────┐
       │ Supabase Edge Function       │
       │ telemetry-ingest (Deno)      │
       │  ├─ 校驗 schema_version=1    │
       │  ├─ 截斷字串長度             │
       │  └─ insert + RLS (anon key)  │
       └─────────────┬────────────────┘
                     ▼
       ┌──────────────────────────────┐
       │ PostgreSQL                   │
       │  ├─ telemetry_events         │
       │  ├─ installations (upsert)   │
       │  └─ views: crash_clusters,   │
       │           skill_sequences    │
       └──────────────────────────────┘
```

### 執行流程圖

```
 skill 啟動
   │
   ▼
[preamble bash 執行]
   │ _SESSION_ID="$$-$(date +%s)"
   │ TEL=$(gstack-config get telemetry)
   │
   ├─ TEL=off ───────────────────────┐
   │                                 │
   ├─ TEL≠off                        │
   │   │                             │
   │   ▼                             │
   │ inline append JSONL             │
   │ (skill, ts, repo)               │
   │   │                             │
   │   ▼                             │
   │ 寫 .pending-$SESSION_ID         │
   │                                 │
   └─►[skill 主體執行]◄──────────────┘
            │
            ▼
      [skill 結束]
            │
            ▼
   gstack-telemetry-log
            │
            ├─ TEL=off ──► 只清自己的 .pending → exit
            │
            ▼
   finalize 別人 stale .pending（寫 outcome=unknown）
            │
            ▼
   清自己 .pending
            │
            ▼
   組 JSON 寫 skill-usage.jsonl
            │
            ▼
   nohup gstack-telemetry-sync &
            │
            ▼
          End
```

### 同步時序圖

```
 skill   telemetry-log   sync(bg)   edge-func    Postgres
   │          │             │           │            │
   │──end────►│             │           │            │
   │          │──append─────│           │            │
   │          │──spawn &───►│           │            │
   │          │             │──rate?(5m)│            │
   │          │             │──cursor   │            │
   │          │             │  讀新行   │            │
   │          │             │──strip _* │            │
   │          │             │──POST────►│            │
   │          │             │           │──validate  │
   │          │             │           │──insert───►│
   │          │             │           │            │
   │          │             │           │──upsert───►│
   │          │             │           │  installations
   │          │             │◄─{inserted:N}          │
   │          │             │  cursor+=N             │
   │          │             │  touch .last-sync-time │
```

### 關鍵設計決策

> [!note] 設計模式
> Cursor-based incremental sync + per-session pending markers + privacy tier 篩選。

1. **Inline + spawn 雙寫**：preamble 直接 append 一筆極簡 JSONL（保證至少有紀錄），skill 結束後再由 `gstack-telemetry-log` 寫完整版。理由：preamble 不能 block 太久；epilogue 可能因為 skill crash 永遠不執行。
2. **`.pending-$SESSION_ID` 而非單一 .pending**：避免同時跑多個 session 互相 race。下次任何 skill 啟動時都會 finalize「不是自己的」舊 marker，把它記成 `outcome: unknown`。
3. **Cursor file 而非刪除已送行**：`.last-sync-line` 存「已送到第幾行」。JSONL 永不刪除（本地稽核方便），cursor 推進失敗也不會丟資料。
4. **Local-only 欄位 prefix `_`**：`_repo_slug`、`_branch` 只寫在本地檔案，sync 前用 `sed` 字串剝除，**根本送不到網路**。
5. **`set -uo pipefail`（無 -e）**：telemetry 失敗絕對不能讓使用者的 skill 中斷。所有 IO 都接 `|| true`。
6. **anon key + RLS 而非 service role**：edge function 只能 INSERT，不能 SELECT 整表，最小權限。
7. **Rate limit by file mtime**：`find $RATE_FILE -mmin +5` 純 shell 實作的 5 分鐘節流，不用任何外部 state。

### 關鍵程式碼

**Preamble 內聯紀錄（`scripts/resolvers/preamble.ts:50-69`）**

```bash
_TEL=$(${ctx.paths.binDir}/gstack-config get telemetry 2>/dev/null || true)
_TEL_PROMPTED=$([ -f ~/.gstack/.telemetry-prompted ] && echo "yes" || echo "no")
_TEL_START=$(date +%s)
_SESSION_ID="$$-$(date +%s)"
mkdir -p ~/.gstack/analytics
if [ "$_TEL" != "off" ]; then
echo '{"skill":"${ctx.skillName}","ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","repo":"'$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "unknown")'"}'  >> ~/.gstack/analytics/skill-usage.jsonl 2>/dev/null || true
fi
for _PF in $(find ~/.gstack/analytics -maxdepth 1 -name '.pending-*' 2>/dev/null); do
  if [ -f "$_PF" ]; then
    if [ "$_TEL" != "off" ] && [ -x "${ctx.paths.binDir}/gstack-telemetry-log" ]; then
      ${ctx.paths.binDir}/gstack-telemetry-log --event-type skill_run --skill _pending_finalize --outcome unknown --session-id "$_SESSION_ID" 2>/dev/null || true
    fi
    rm -f "$_PF" 2>/dev/null || true
  fi
  break
done
```

**Local-only 欄位剝除（`bin/gstack-telemetry-sync:82-90`）**

```bash
CLEAN="$(echo "$LINE" | sed \
  -e 's/,"_repo_slug":"[^"]*"//g' \
  -e 's/,"_branch":"[^"]*"//g' \
  -e 's/,"repo":"[^"]*"//g')"

# If anonymous tier, strip installation_id
if [ "$TIER" = "anonymous" ]; then
  CLEAN="$(echo "$CLEAN" | sed 's/,"installation_id":"[^"]*"//g; s/,"installation_id":null//g')"
fi
```

**Edge function schema 驗證（`supabase/functions/telemetry-ingest/index.ts:61-89`）**

```typescript
for (const event of events) {
  if (!event.ts || !event.gstack_version || !event.os || !event.outcome) continue;
  if (event.v !== 1) continue;
  const validTypes = ["skill_run", "upgrade_prompted", "upgrade_completed"];
  if (!validTypes.includes(event.event_type)) continue;

  rows.push({
    schema_version: event.v,
    gstack_version: String(event.gstack_version).slice(0, 20),
    os: String(event.os).slice(0, 20),
    skill: event.skill ? String(event.skill).slice(0, 50) : null,
    duration_s: typeof event.duration_s === "number" ? event.duration_s : null,
    outcome: String(event.outcome).slice(0, 20),
    error_class: event.error_class ? String(event.error_class).slice(0, 100) : null,
    installation_id: event.installation_id ? String(event.installation_id).slice(0, 64) : null,
    // ...
  });
}
```

## 安裝流程（Installation Flow）

### 安裝時序圖

```
 user        ./setup           bin/*           ~/.gstack/
   │           │                  │                │
   │──./setup──►                  │                │
   │           │──build browse───►│                │
   │           │──build design───►│                │
   │           │──symlink skills─►│                │
   │           │                  │                │
   │ (首次跑 skill)                                 │
   │──/qa──────────────────────────────────────────►│ mkdir analytics/
   │                                                │ mkdir sessions/
   │                                                │ touch .pending-*
   │ (TEL_PROMPTED=no → 詢問 tier)                  │
   │                                                │ touch .telemetry-prompted
   │                                                │ write installation-id (if community)
```

### 安裝產物清單（telemetry 相關）

| 路徑 | 類型 | 用途 |
|------|------|------|
| `~/.gstack/analytics/skill-usage.jsonl` | 檔案 | 所有事件的本地 append-only log |
| `~/.gstack/analytics/.pending-$SID` | 檔案 | per-session 進行中標記 |
| `~/.gstack/analytics/.last-sync-line` | 檔案 | sync cursor（行號） |
| `~/.gstack/analytics/.last-sync-time` | 檔案 | rate-limit mtime marker |
| `~/.gstack/installation-id` | 檔案 | community tier 的隨機 UUID v4 |
| `~/.gstack/.telemetry-prompted` | 檔案 | 防止重複詢問 tier |
| `~/.gstack/sessions/$PPID` | 檔案 | 並發 session 計數 |

### 環境變數

| 變數 | 用途 | 設定時機 |
|------|------|---------|
| `GSTACK_STATE_DIR` | 覆寫 `~/.gstack`（測試用） | 執行時 |
| `GSTACK_DIR` | 覆寫 gstack root | 執行時 |
| `GSTACK_SUPABASE_URL` | 覆寫上傳目的地 | 執行時 |
| `GSTACK_TELEMETRY_SOURCE` | 標記事件來源（live/test） | 執行時 |

> [!warning] 解除安裝
> 完整清除：`rm -rf ~/.gstack/analytics ~/.gstack/installation-id ~/.gstack/.telemetry-prompted`

---

## 使用案例地圖（Use Case Map）

| # | 使用案例 | 觸發 | 入口檔案 | 核心鏈 |
|---|---------|------|---------|-------|
| 1 | skill 啟動記錄 | `/qa` 等任何 skill | `scripts/resolvers/preamble.ts` → 生成的 SKILL.md bash | preamble.ts → SKILL.md → JSONL append + .pending |
| 2 | skill 結束完整事件 | skill 流程末段 epilogue | `bin/gstack-telemetry-log` | gstack-config → JSONL append → spawn sync |
| 3 | 背景同步到 Supabase | `gstack-telemetry-log` spawn | `bin/gstack-telemetry-sync` | rate check → cursor → strip → curl → cursor++ |
| 4 | Stale session 修復 | 下一次任何 skill 啟動 | `bin/gstack-telemetry-log:78-101` | scan .pending-* → outcome=unknown |
| 5 | 隱私 tier 切換 | `gstack-config set telemetry X` | `bin/gstack-config` | 寫 yaml → 下次 preamble 生效 |

### 案例詳解

#### 案例 2：skill 結束完整事件

```
skill epilogue
  │ gstack-telemetry-log --skill qa --duration 142 --outcome success ...
  ▼
bin/gstack-telemetry-log
  │
  ├─ gstack-config get telemetry  ── 讀 ──► ~/.gstack/config.yaml
  │     │
  │     └─ off → 清自己 .pending → exit 0
  │
  ├─ scan .pending-* (排除自己) → finalize 為 outcome=unknown
  │
  ├─ 收集 metadata: ts, version, os, arch, sessions count
  │
  ├─ if community: 讀/生成 ~/.gstack/installation-id (UUID v4)
  │
  ├─ json_safe() 過濾所有字串欄位
  │
  ├─ append 完整 JSON  ── 寫 ──► ~/.gstack/analytics/skill-usage.jsonl
  │
  └─ exec gstack-telemetry-sync &  (背景)
        │
        ▼
     (見案例 3)
```

#### 案例 3：背景同步

```
gstack-telemetry-sync (背景)
  │
  ├─ source supabase/config.sh → SUPABASE_URL, ANON_KEY
  │
  ├─ 檢查 .last-sync-time mtime → 5min 內就 exit
  │
  ├─ gstack-config get telemetry → off 就 exit
  │
  ├─ 讀 .last-sync-line 拿 cursor
  │
  ├─ tail -n +(cursor+1) skill-usage.jsonl → 未送行
  │
  ├─ 逐行 sed 剝除 _repo_slug / _branch
  │   └─ if anonymous: 額外剝 installation_id
  │
  ├─ 組 BATCH=[...] (max 100 行)
  │
  ├─ curl POST $SUPABASE_URL/functions/v1/telemetry-ingest
  │     │
  │     ▼
  │   (edge function 處理：見「關鍵程式碼」)
  │
  └─ HTTP 2xx 且 inserted>0 → cursor += COUNT, 寫回 .last-sync-line
       └─ touch .last-sync-time (rate limit marker)
```

---

## 架構師觀點（Architect's View）

### ✅ 優點

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性 | ⭐⭐⭐⭐ | 純 bash 客戶端，沒有 binary 依賴；edge function 單檔 140 行 |
| 隱私設計 | ⭐⭐⭐⭐⭐ | local-only `_` 前綴慣例 + sed 剝除 + tier 分層 + UUID 而非 hash |
| 容錯 | ⭐⭐⭐⭐⭐ | 無 `set -e`、全部 `\|\| true`、cursor 不前進就重送、stale pending 自動回收 |
| 並發安全 | ⭐⭐⭐⭐ | per-session `.pending-$SID` 避免 race；JSONL append 是 POSIX-atomic（<PIPE_BUF） |
| 文件 | ⭐⭐⭐⭐ | 每個 bin 檔頭都有 data flow comment |
| 安全（DB） | ⭐⭐⭐⭐⭐ | anon key + RLS INSERT-only，不用 service role |

> [!tip] 值得學習的設計
> 「**送不到網路 = 從來沒進去過**」的 local-only 欄位設計：用 `_` prefix 命名約定 + 同步前 sed 剝除，比「資料庫端 column 過濾」更不可能出錯，因為剝除錯了也只是少送，不會洩漏。

### ⚠️ 缺點與風險

> [!warning] 已知缺陷

- **JSONL 永不 rotate**：`skill-usage.jsonl` 一直長大；長期使用者檔案可能 MB 級。
- **`grep -o '"installation_id":"[^"]*"' | awk -F'"'`**：純字串解析 JSON 在欄位順序變動或值含特殊字元時會壞掉。雖然有 `json_safe()`，但 robust 度仍輸給 `jq`。
- **`tail -n +N` 線性 IO**：cursor 推進靠 `tail`，每次 sync 仍要從頭掃整個檔，未來行數大會慢。
- **edge function 沒有 idempotency key**：如果 client 收到 5xx 但實際插入成功，下次重送會重複（cursor 沒前進）。目前只靠「網路成功 = 一定有寫」假設。
- **rate limit 是全域而非 per-installation**：5 分鐘只跑一次代表崩潰高峰時最後一筆要等 5 分鐘才送。
- **`for _PF in ...; break`**：每次只 finalize 一個 stale marker，多 session 同時掛掉時要好幾次 skill 啟動才能清完。

### 🔮 改進建議

1. JSONL log rotation（>10MB 切檔，保留近 N 個）
2. edge function 加 `client_event_id` 做 idempotent insert
3. 把 stale marker 掃描從 `for ... break` 改成完整 loop
4. 用 `jq` 取代 grep+awk 解析（如果可用，否則保留 fallback）

## 效能基準（Benchmark）

> [!info] 無公開 benchmark 數據，定性分析

| 場景 | 估計開銷 |
|------|---------|
| preamble inline append | < 5ms（單行 echo 重定向） |
| gstack-telemetry-log（end of skill） | 30–100ms（含 grep/awk 解析 stale + JSON 組裝） |
| gstack-telemetry-sync（背景） | 200ms–2s（curl 為主），不阻塞 user |
| edge function insert 100 events | 預估 100–300ms（兩次 SQL：insert + upsert loop） |

預期瓶頸：sync 的 `tail -n +N` 在 JSONL 超過 10 萬行後變明顯。

## 快速上手（Quick Start）

```bash
# 啟用 community tier（含 installation_id）
~/.claude/skills/gstack/bin/gstack-config set telemetry community

# 看本地紀錄
tail -f ~/.gstack/analytics/skill-usage.jsonl

# 手動觸發 sync（忽略 rate limit 要先刪 marker）
rm -f ~/.gstack/analytics/.last-sync-time
~/.claude/skills/gstack/bin/gstack-telemetry-sync

# 完全關閉
~/.claude/skills/gstack/bin/gstack-config set telemetry off
```

## 我的心得（My Takeaways）

1. **「送不到網路」設計**比「資料庫端過濾」更安全 — 失誤模式是少送而非外洩。
2. **`.pending-$SESSION_ID`** 模式是處理 crash recovery 的優雅做法：每個 process 用自己的 PID 拿一個 marker，下次任何同類 process 都負責清理「不是自己的」舊 marker。可套用到任何 fire-and-forget 子系統。
3. **Cursor file + append-only log** 比「刪除已送行」可靠太多。同樣模式可用在 outbox pattern。
4. **Bash 內 `set -uo pipefail`（無 -e）+ 全部 `|| true`**：對於「絕不能影響主流程」的觀測程式碼是正確選擇，違反「fail fast」直覺但合理。

## 待補充（Open Questions）

- gstack-telemetry-sync 以 `tail -n +N` 做 cursor-based 同步，在高頻使用下 JSONL 檔案會持續增長。是否有 log rotation 的計劃，或者長期使用者該如何手動管理以避免效能退化？（建議搜尋：`logrotate jsonl append-only log rotation bash`）
- 三層隱私設計（off/anonymous/community）中，`off` 模式下 preamble 仍會 inline 寫一筆本地 JSONL。這筆紀錄的生命週期是什麼？會不會在 tier 改為 community 後被誤上傳？（建議搜尋：`gstack telemetry off tier local only jsonl`）
- Supabase anon key 是否硬編碼在 `supabase/config.sh` 中？如果 key 洩漏或需要 rotate，客戶端要怎麼更新？（建議搜尋：`supabase anon key rotation client update`）
- `gstack-telemetry-sync` 目前用 sed denylist 剝除敏感欄位。若未來新增了帶有 PII 的欄位但忘記更新 denylist，有沒有自動化的防護機制？（建議搜尋：`pii scrubbing allowlist denylist bash telemetry`）
- edge function 沒有 idempotency key，重複送同一筆事件會造成重複計算。若要加入 idempotency，Supabase 端的 UNIQUE constraint 應該加在哪個欄位？（建議搜尋：`supabase idempotency unique constraint insert edge function`）

## 相關連結（Related）
- [[2026-05-23-RTK-RUST-TOKEN-KILLER-LOG-COMPRESSION-ARCHITECTURE]] — RTK 的 tee recovery、tracking DB 與 log dedupe 可與 gstack 的 append-only telemetry/outbox pattern 對照。

- [[CLAUDE-SKILL-ARCHITECTURE]] — gstack 的 skill 為何是獨立 process
- [[SUPABASE-EDGE-FUNCTIONS]] — Deno edge function 的部署模型
- [[OUTBOX-PATTERN]] — append-only log + cursor 是 outbox pattern 的最簡實作
- [[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]] — Claude Code 用 OpenTelemetry + Prometheus 實現團隊級遙測監控，與 gstack 的 Supabase 方案形成對比
- [[2026-04-13-CLAUDE-CODE-TELEMETRY-OTEL-SOURCE-DEEP-DIVE]] — Claude Code 遙測原始碼深度分析，揭示三層架構（Standard/Beta/Perfetto）與 WeakRef Span 管理設計
- [[2026-04-17-CLAUDE-CODE-FEEDBACK-FRUSTRATION-DETECTION-EVENTMETADATA-ARCHITECTURE]] — Claude Code 的 Datadog + 1P 雙路徑遙測架構，與 gstack 的 Supabase 方案形成對比
- [[2026-05-17-GARRY-TAN-TOKENMAXXING-GSTACK-400X-PRODUCTIVITY]] — Garry Tan 講 GStack 的演化動機與 Conductor 任務隊列管理（48h 13 PR）

---
- [[2026-08-07-OPEN-CODE-REVIEW-ALIBABA-AI-CODE-REVIEW-CLI-CODE-ANALYSIS]] — gstack 本地寫入+背景同步 vs OCR 的 OTLP 直送+no-op 抽象,兩種工具鏈遙測資料流對照

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | 三層 tier（off/anonymous/community）；JSONL 路徑 `~/.gstack/analytics/skill-usage.jsonl`；edge function 名 `telemetry-ingest`；schema_version=1；MAX_BATCH=100；rate limit 5min |
| **理解（半被動）** | 串聯知識點 | preamble 寫 inline 簡記與 .pending；epilogue 由 gstack-telemetry-log 補完整紀錄並 spawn sync；sync 用 cursor 增量送到 edge function；edge function 用 anon key + RLS 寫 Postgres。每一階段的存在都是為了「skill 是獨立 process」這個前提。 |
| **分析（主動）** | 找出假設 | 假設一：append `<PIPE_BUF` 是 atomic（成立）。假設二：HTTP 2xx ⇒ 真的入庫（脆弱，沒 idempotency key）。假設三：使用者不會手動修改 JSONL（沒 checksum）。假設四：5 分鐘節流可接受（崩潰歸因會延遲）。 |
| **應用（主動）** | 規劃執行 | (1) 把「local-only `_` prefix + 送出前 sed 剝除」抄到我自己的 logging 工具。(2) 用 `.pending-$SID` 模式重寫公司 cron job 的 stale lock 處理。 |
| **評估（主動）** | 多方案權衡 | 替代方案 A：用 SQLite 取代 JSONL → 查詢更快但增加依賴，不如 JSONL 適合 bash-only 環境。替代方案 B：用 systemd timer 取代 spawn-on-skill-end → 更精準但 macOS 沒 systemd，會破壞跨平台。現方案在「零依賴 + 跨平台 + 隱私可審計」三軸最佳。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「outcome=unknown」到底代表 crash 還是 timeout？目前無法區分。
- **假設**：如果某天 Supabase edge function 改 schema，舊 client 還會送 `v:1` — 邊界由誰守？
- **證據**：「sync 不會阻塞 user」這個聲明在實際慢網路下有實測嗎？
- **觀點**：站在「絕不開 telemetry」的隱私倡議者角度，`off` tier 是否真的什麼都沒寫？（答：preamble 仍會 inline 寫一筆，雖不會送出。）
- **後果**：12 個月後 JSONL 累積到 50MB，`tail -n +N` 啟動延遲會不會被使用者抱怨？

### 方案批判三問

1. **最大的風險是什麼？** — 隱私洩漏。若 sed 剝除 regex 漏掉某個欄位（例如未來新增 `_user_email`），會在使用者不知情下上傳。緩解：應該改用 allowlist 而非 denylist。
2. **什麼情況下會失敗？** — (a) JSONL 行被外部編輯破壞 JSON 結構，cursor 仍會推進但 edge function 會 reject。(b) 同時 100+ 個 session 啟動時 .pending-* 掃描會慢。(c) 系統時鐘倒退時 rate limit 失效。
3. **有沒有更好的替代方案？** — 對「企業環境、需要強保證」用 OpenTelemetry SDK + OTLP exporter；對「個人 OSS、零依賴、跨平台 bash」現方案最佳。當你開始需要 trace context 傳遞、metric aggregation、structured logging 三者合一時，就該換 OTel。

## References

- [GitHub Repo](https://github.com/garrytan/gstack)
- `bin/gstack-telemetry-log`
- `bin/gstack-telemetry-sync`
- `scripts/resolvers/preamble.ts`
- `supabase/functions/telemetry-ingest/index.ts`
- `supabase/migrations/001_telemetry.sql`
