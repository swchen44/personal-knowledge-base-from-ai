---
title: "Claude Session Analyzer — Claude Code 對話品質量化分析工具"
date: 2026-04-10
category: CodeAnalysis
tags:
  - "#ai/claude-code"
  - "#tools/cli"
  - "#ai/observability"
  - "#code-analysis/python"
source: "https://github.com/lucemia/claude-session-analyzer"
source_type: code
author: "lucemia"
status: reviewed
links:
  - "[[2026-04-02-CLAUDE-CODE-ISSUE-42796-EXTENDED-THINKING-REGRESSION]]"
  - "[[AI-Coding-Assistant-Observability]]"
  - "[[JSONL-Log-Analysis]]"
  - "[[CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]]"
github_stars: 6
github_language: Python
---

## 摘要（Summary）

Claude Session Analyzer 是一個純 Python 的量化分析工具，用來解析 Claude Code 的 JSONL 對話日誌檔（session logs），產出涵蓋思考深度（Thinking Depth）、工具使用模式（Tool Usage Patterns）、行為退化訊號（Behavioral Signals）、使用者情緒（User Sentiment）及成本估算（Cost Estimation）的完整品質報告。該工具複製了 [anthropics/claude-code#42796](https://github.com/anthropics/claude-code/issues/42796)（由 Stella Laurenzo 發布的量化退化分析）的方法論，並且同時提供三種使用模式：獨立 Python 腳本、Claude Code Plugin、以及 Slash Command 互動式分析。整個專案僅一個 1,348 行的 Python 檔案，零外部依賴（僅需 Python 3.7+ 標準庫）。

---

## Why — 為什麼存在？

2026 年 4 月，Stella Laurenzo（@stellaraccident）在 [anthropics/claude-code#42796](https://github.com/anthropics/claude-code/issues/42796) 發布了一份詳盡的量化分析，證明 Claude Code 的品質在某些時期有可測量的退化：

- 思考內容（Thinking Content）的遮蔽（Redaction）與品質退化精確相關
- Read:Edit 比率從 6.6 降至 2.0（編輯前的研究量減少 70%）
- 43.8% 的編輯是在模型尚未讀取該檔案的情況下進行的
- 使用者提示中的挫折指標翻倍
- 停止語防護鉤（stop-phrase-guard hook）在 17 天內從 0 違規飆升至 173 次

這個工具的存在是為了**讓任何 Claude Code 使用者都能在自己的對話日誌上重現這項分析**，不需要手動寫 jq 或 Python 腳本，只需一行指令即可獲得完整報告。

---

## What — 是什麼？

### 專案結構

```
claude-session-analyzer/
├── .claude-plugin/
│   └── plugin.json              # Claude Code Plugin 定義
├── .claude/
│   └── commands/
│       └── analyze-sessions.md  # Slash Command（互動式）
├── commands/
│   └── analyze-sessions.md      # 可複製的 Slash Command 副本
├── examples/
│   └── sample-report.md         # 完整報告範例
├── analyze_sessions.py          # 核心分析腳本（1,348 行）
├── .gitignore
└── README.md
```

### 檔案清單與行數

| 檔案 | 行數 | 說明 |
|------|------|------|
| `analyze_sessions.py` | 1,348 | 核心分析引擎，7 個分析階段 |
| `.claude/commands/analyze-sessions.md` | 169 | 互動式 Slash Command 定義 |
| `commands/analyze-sessions.md` | 169 | 上述的可攜副本 |
| `.claude-plugin/plugin.json` | 8 | Plugin 元資料 |
| `examples/sample-report.md` | 308 | 範例輸出報告 |
| `README.md` | 134 | 專案說明文件 |

### 衡量維度

| 類別 | 關鍵指標 |
|------|----------|
| 思考深度（Thinking Depth） | 遮蔽率（Redaction Rate）、簽名長度代理（Signature-Length Proxy）、Pearson 相關係數、每小時變化 |
| 工具使用（Tool Usage） | Read:Edit 比率、Research:Mutation 比率、Write 佔變動百分比、未讀取就編輯百分比、重複編輯 |
| 行為訊號（Behavioral Signals） | 推理迴圈（Reasoning Loops）、「最簡單」提及、過早停止、自承錯誤（皆以每 1K 工具呼叫計） |
| 使用者體驗（User Experience） | 挫折指標、使用者中斷、正/負面情緒比率、詞頻分析 |
| 成本（Cost） | Token 使用量、API 請求數、Bedrock 估算價格、每日成本趨勢、每提示成本 |
| 期間比較（Period Comparison） | 自動分割為兩半進行逐指標對比 |

---

## How — 如何運作？

### 架構圖

```
+-------------------------------------------------------------------+
|                    analyze_sessions.py                              |
|                                                                     |
|  +-----------+    +------------------------------------------+      |
|  | CLI Args  |--->|  Phase 1: Discovery & Loading            |      |
|  | --start   |    |  - os.walk() 遞迴尋找 .jsonl             |      |
|  | --end     |    |  - 日期範圍篩選（首行 timestamp）          |      |
|  | --output  |    |  - JSON 逐行解析到記憶體累加器             |      |
|  | [path]    |    +------------------------------------------+      |
|  +-----------+                    |                                  |
|                                   v                                  |
|  +------------------------------------------+                        |
|  |  Phase 2: Thinking Depth Analysis        |                        |
|  |  - 遮蔽率統計                             |                        |
|  |  - 每週/每小時 signature 長度             |                        |
|  |  - Pearson 相關係數計算                   |                        |
|  +------------------------------------------+                        |
|                                   |                                  |
|  +------------------------------------------+                        |
|  |  Phase 3: Tool Usage Analysis            |                        |
|  |  - 工具呼叫計數 (Counter)                 |                        |
|  |  - Read:Edit / Research:Mutation 比率     |                        |
|  |  - 未讀取就編輯追蹤（10-call window）      |                        |
|  |  - 每週趨勢                               |                        |
|  +------------------------------------------+                        |
|                                   |                                  |
|  +------------------------------------------+                        |
|  |  Phase 4: Behavioral Pattern Analysis    |                        |
|  |  - 正則模式匹配 (count_pattern)           |                        |
|  |  - 推理迴圈、最簡化、過早停止、自承錯誤   |                        |
|  +------------------------------------------+                        |
|                                   |                                  |
|  +------------------------------------------+                        |
|  |  Phase 5: User Prompt Analysis           |                        |
|  |  - 挫折詞檢測                             |                        |
|  |  - 正/負情緒比率                          |                        |
|  |  - 詞頻統計                               |                        |
|  |  - 使用者中斷計數                         |                        |
|  +------------------------------------------+                        |
|                                   |                                  |
|  +------------------------------------------+                        |
|  |  Phase 6: Cost Estimation                |                        |
|  |  - request_id 去重                        |                        |
|  |  - Bedrock Opus 定價模型                  |                        |
|  |  - 每日成本趨勢                           |                        |
|  +------------------------------------------+                        |
|                                   |                                  |
|  +------------------------------------------+                        |
|  |  Phase 7: Period Comparison              |                        |
|  |  - 日期中位數分割                         |                        |
|  |  - 所有指標的雙期比較                     |                        |
|  +------------------------------------------+                        |
|                                   |                                  |
|                                   v                                  |
|  +------------------------------------------+                        |
|  |  Report Generation                       |                        |
|  |  - Markdown 格式                          |                        |
|  |  - 摘要 → 7 個分析章節 → 方法論          |                        |
|  |  - 寫入 .md 檔案                          |                        |
|  +------------------------------------------+                        |
+-------------------------------------------------------------------+
```

### 資料流程圖

```
~/.claude/projects/**/*.jsonl
        |
        |  os.walk() + json.loads()
        v
+------------------+     +------------------+     +------------------+
| thinking_blocks  |     | tool_calls       |     | user_prompts     |
| [{ts, sig_len,   |     | [{ts, name,      |     | [{ts, text,      |
|   thinking_len,  |     |   session_id}]   |     |   session_id}]   |
|   redacted,      |     +------------------+     +------------------+
|   session_id}]   |            |                         |
+------------------+     +------+------+           +------+------+
        |                |             |           |             |
        v                v             v           v             v
  Phase 2          Phase 3       Phase 4     Phase 5       Phase 5
  Thinking         Tool Usage    Behavioral  Frustration   Sentiment
  Analysis         Ratios        Patterns    Detection     Ratio
        |                |             |           |             |
        +--------+-------+------+------+-----+-----+            |
                 |              |             |                   |
                 v              v             v                   v
+------------------+     +------------------+     +------------------+
| usage_records    |     | assistant_texts  |     | session_meta     |
| [{ts, input,     |     | [{ts, text,      |     | {session_id:     |
|   output,        |     |   session_id}]   |     |   {start, end,   |
|   cache_read,    |     +------------------+     |    project,      |
|   cache_creation,|                              |    file}}        |
|   request_id,    |                              +------------------+
|   session_id}]   |
+------------------+
        |
        v
  Phase 6: Cost
  Estimation
        |
        v
  Phase 7: Period
  Comparison
        |
        v
  +-----------------+
  | Markdown Report |
  | (.md file)      |
  +-----------------+
```

### JSONL 解析時序圖

```
使用者                 analyze_sessions.py           ~/.claude/projects/
  |                          |                              |
  |  python3 analyze...      |                              |
  |------------------------->|                              |
  |                          |  os.walk() 尋找 *.jsonl      |
  |                          |----------------------------->|
  |                          |  [file1.jsonl, file2.jsonl]  |
  |                          |<-----------------------------|
  |                          |                              |
  |                          |  逐檔讀取 + 逐行解析          |
  |                          |----------------------------->|
  |                          |                              |
  |                          |  首行 timestamp 檢查日期範圍  |
  |                          |  若不在範圍 → skip           |
  |                          |                              |
  |                          |  type=="user" → user_prompts |
  |                          |  type=="assistant" →          |
  |                          |    content[].type=="thinking" |
  |                          |      → thinking_blocks       |
  |                          |    content[].type=="tool_use" |
  |                          |      → tool_calls            |
  |                          |    content[].type=="text"     |
  |                          |      → assistant_texts       |
  |                          |    usage → usage_records     |
  |                          |                              |
  |                          |  7 個分析階段依序執行         |
  |                          |                              |
  |                          |  產出 Markdown 報告           |
  |  Report written to X.md |                              |
  |<-------------------------|                              |
```

---

## 關鍵設計決策

### 1. 零依賴架構

整個分析器僅使用 Python 標準庫（`json`, `os`, `sys`, `re`, `glob`, `collections`, `datetime`, `pathlib`, `statistics`）。沒有 pandas、numpy 或任何第三方套件。這是一個刻意的設計：

- **部署零摩擦**：任何有 Python 3.7+ 的機器都能直接執行
- **無需虛擬環境**：降低使用者的進入門檻
- **代價**：手動實作 Pearson 相關係數（第 510-522 行），統計功能有限

### 2. Signature Length 作為思考深度代理

Claude Code 的思考區塊（Thinking Block）在生產環境中會被遮蔽（`thinking` 欄位為空字串），但 `signature` 欄位會保留。根據原始分析，`signature` 長度與思考內容長度有 r > 0.95 的 Pearson 相關性。這個工具利用此特性，在思考內容不可見的情況下仍能估算思考深度。

### 3. 10-Call Window 啟發式

判定「未讀取就編輯」（Edit without prior Read）時，使用固定 10 個工具呼叫的回溯窗口。這是一個合理的啟發式：
- 太小（如 3）會誤報（中間插入了 Grep/Glob）
- 太大（如 50）會漏報（讀取太久以前的檔案不算有效參考）
- 10 是原始分析中使用的值

### 4. 雙期自動分割

日期範圍超過 14 天時，自動按日期中位數分割為兩半，進行所有指標的前後對比。這複製了原始分析中的方法論，能自動偵測趨勢變化。

### 5. 三種分發模式

- **獨立腳本**：`python3 analyze_sessions.py` — 最簡單，自動化友好
- **Plugin**：`.claude-plugin/plugin.json` — Claude Code 原生整合
- **Slash Command**：`.claude/commands/analyze-sessions.md` — 互動式，Claude 能即時解釋發現

### 6. Bedrock Opus 定價模型

成本估算使用 AWS Bedrock 的 Claude Opus 價格：
- Input: $15/MTok
- Output: $75/MTok
- Cache Read: $1.50/MTok
- Cache Write: $18.75/MTok

這是因為原始分析也使用此定價，且 Bedrock 是企業使用 Claude 的主要管道之一。

---

## 關鍵程式碼片段

### 1. JSONL 解析與資料累積（Phase 1 核心迴圈）

```python
for fpath in all_files:
    try:
        session_id = None
        session_start = None
        first_line_checked = False

        with open(fpath, 'r', errors='replace') as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    parse_errors += 1
                    continue

                ts = parse_timestamp(rec.get("timestamp"))
                if not first_line_checked and ts:
                    first_line_checked = True
                    # Check date range on first timestamped line
                    if ts < START_DATE or ts > END_DATE:
                        files_skipped += 1
                        break

                if not session_id:
                    session_id = rec.get("sessionId", os.path.basename(fpath).replace(".jsonl", ""))

                # ... 依據 rec_type 分類到不同累加器 ...
```

**設計要點**：
- 用首行 timestamp 做早期過濾，避免解析不在日期範圍內的大檔案
- `errors='replace'` 防止編碼問題導致崩潰
- Session ID 從 JSONL 內容取得，若無則以檔名為 fallback

### 2. Pearson 相關係數手動實作

```python
sig_think_corr = None
if visible_thinking >= 10:
    paired = [(t["sig_len"], t["thinking_len"]) for t in thinking_blocks
              if not t["redacted"] and t["thinking_len"] > 0 and t["sig_len"] > 0]
    if len(paired) >= 10:
        sigs = [p[0] for p in paired]
        thinks = [p[1] for p in paired]
        mean_s = statistics.mean(sigs)
        mean_t = statistics.mean(thinks)
        cov = sum((s - mean_s) * (t - mean_t) for s, t in zip(sigs, thinks)) / len(paired)
        std_s = (sum((s - mean_s) ** 2 for s in sigs) / len(sigs)) ** 0.5
        std_t = (sum((t - mean_t) ** 2 for t in thinks) / len(thinks)) ** 0.5
        if std_s > 0 and std_t > 0:
            sig_think_corr = cov / (std_s * std_t)
```

**設計要點**：最小樣本數門檻為 10，使用母體標準差（除以 N 而非 N-1），這是一個微小的統計偏差但對 r > 0.95 的強相關不影響結果。

### 3. 未讀取就編輯的偵測邏輯

```python
edits_without_read = 0
total_edits_checked = 0
for session_id, seq in tool_sequence_by_session.items():
    for i, (name, fpath) in enumerate(seq):
        if name == "Edit" and fpath:
            total_edits_checked += 1
            # Check preceding 10 tool calls for a Read of the same file
            found_read = False
            for j in range(max(0, i - 10), i):
                prev_name, prev_path = seq[j]
                if prev_name == "Read" and prev_path == fpath:
                    found_read = True
                    break
            if not found_read:
                edits_without_read += 1
```

**設計要點**：每個 session 維護一個 `(tool_name, file_path)` 序列，逐 Edit 呼叫向前回溯 10 步檢查是否有同檔 Read。這是 O(n * 10) = O(n) 的線性演算法。

### 4. 情緒分析與挫折偵測

```python
frustration_words = ["no,", "wrong", "stop", "don't", "terrible", "lazy", "fuck", "shit", "broken"]
frustration_prompts = 0
for p in user_prompts:
    text_lower = p["text"].lower()
    if any(w in text_lower for w in frustration_words):
        frustration_prompts += 1

positive_words = ["great", "good", "love", "nice", "fantastic", "wonderful", "cool", "excellent", "perfect", "beautiful"]
negative_words = ["fuck", "shit", "damn", "wrong", "broken", "terrible", "horrible", "awful", "bad", "lazy", "sloppy"]

positive_count = count_pattern(all_user_text, positive_words)
negative_count = count_pattern(all_user_text, negative_words)
sentiment_ratio = round(positive_count / negative_count, 1) if negative_count > 0 else float('inf')
```

**設計要點**：使用基於關鍵字的情緒分析（Keyword-based Sentiment Analysis），而非 NLP 模型。這與零依賴的設計決策一致。注意 "no," 帶逗號是刻意的——避免匹配 "node", "notion" 等常見詞。

> [!warning] 真實使用驗證：情感分析的系統性誤判
> 在 2026-04-29 的 30 天實際使用中，Python 腳本報告情感比率為 0.8:1（66 正面 : 86 負面），結論為「corrective relationship」。但逐句人工驗證後發現 **所有命中均為誤判**：
> - `broken` (14 次) → 全為 "broken wikilinks" 技術描述
> - `good` (15 次) → 全為 URL 路徑 `writing-a-good-claude-md`
> - `wrong` (3 次) → 全為研究修正記錄 "claim was WRONG"
> - `lazy` (2 次) → 全為 "lazy loading" 技術術語
>
> **零個有效情感表達**，結論完全錯誤。詳見下方「真實使用驗證」章節。

### 5. 報告產生器的品質基準敘事

```python
re_val = overall_ratios['read_edit'] if overall_ratios['read_edit'] != float('inf') else 0
summary_parts.append(
    f"\n\n**Tool usage**: The overall Read:Edit ratio is **{re_val:.1f}** — "
)
if re_val < 2.0:
    summary_parts.append(
        f"below the 2.0 threshold identified in prior research as the boundary of "
        f"\"degraded\" behavior, where the model edits without sufficient research. "
    )
elif re_val < 4.0:
    summary_parts.append(
        f"in the \"transition\" range between research-first and edit-first behavior. "
    )
else:
    summary_parts.append(
        f"in the \"good\" range indicating research-first behavior. "
    )
```

**設計要點**：報告不只輸出數字，還根據基準值（Good / Transition / Degraded）產生人類可讀的敘事判斷。這讓不熟悉基準的使用者也能理解報告含義。

---

## 安裝流程（Installation Flow）

### 安裝時序圖

```
使用者                                         系統
  |                                              |
  |  === 方式 1: 獨立腳本 ===                    |
  |  git clone / 下載 analyze_sessions.py        |
  |--------------------------------------------->|
  |  python3 analyze_sessions.py                 |
  |--------------------------------------------->|
  |  (零依賴，直接執行)                           |
  |                                              |
  |  === 方式 2: Plugin 安裝 ===                 |
  |  /plugin install session-analyzer            |
  |    from github:lucemia/claude-session-analyzer|
  |--------------------------------------------->|
  |  Claude Code 讀取 .claude-plugin/plugin.json |
  |  註冊 commands/ 下的指令                      |
  |<---------------------------------------------|
  |  /analyze-sessions                           |
  |--------------------------------------------->|
  |                                              |
  |  === 方式 3: 手動 Slash Command ===          |
  |  cp commands/analyze-sessions.md             |
  |     ~/.claude/commands/                      |
  |--------------------------------------------->|
  |  Claude Code 載入 commands 目錄              |
  |  /analyze-sessions 可用                      |
  |<---------------------------------------------|
```

### 產物清單

| 安裝方式 | 產物 | 位置 |
|----------|------|------|
| 獨立腳本 | `session-analysis-{date}.md` | 當前工作目錄（或 `--output` 指定） |
| Plugin | `session-analysis-{date}.md` | 由 Claude Code 在對話中產出 |
| Slash Command | 互動式 Markdown 報告 | Claude Code 對話輸出 |

### 環境變數

本專案**不使用任何環境變數**。所有設定透過 CLI 引數傳入：

| 引數 | 說明 | 預設值 |
|------|------|--------|
| `[path]` | 包含 `.jsonl` session 檔案的目錄 | `~/.claude/projects/` |
| `--start` | 起始日期 (YYYY-MM-DD) | 90 天前 |
| `--end` | 結束日期 (YYYY-MM-DD) | 今天 |
| `--output` | 輸出 Markdown 檔路徑 | `session-analysis-{date}.md` |

---

## 使用案例地圖（Use Case Map）

### 案例總覽表

| # | 使用案例 | 觸發方式 | 主要輸出 |
|---|---------|---------|---------|
| UC1 | 分析過去 90 天的所有 session | `python3 analyze_sessions.py` | 完整 Markdown 報告 |
| UC2 | 分析特定日期範圍 | `python3 analyze_sessions.py --start 2026-03-01 --end 2026-04-01` | 指定範圍報告 |
| UC3 | 分析特定專案 | `python3 analyze_sessions.py ~/.claude/projects/my-project/` | 單專案報告 |
| UC4 | Claude Code 內互動分析 | `/analyze-sessions` | 互動式報告 + 即時解釋 |
| UC5 | 偵測品質退化趨勢 | 任一方式，檢查 Period Comparison 章節 | 前後對比表 |
| UC6 | 成本監控 | 任一方式，檢查 Cost Estimation 章節 | 每日成本趨勢圖 |

### 案例詳解 1：偵測 Claude Code 品質退化

**場景**：使用者感覺 Claude Code 最近表現變差，編輯品質下降，需要更多手動修正。

**執行路徑**：

```
python3 analyze_sessions.py --start 2026-03-01 --end 2026-04-28

[Phase 1] 掃描 ~/.claude/projects/ → 發現 300 個 JSONL 檔案
          ↓ 首行 timestamp 篩選 → 保留 200 個在日期範圍內
[Phase 2] 解析 thinking blocks → 計算遮蔽率、signature 趨勢
[Phase 3] 統計工具呼叫 → 計算 Read:Edit = 1.8 (低於 2.0 = Degraded)
          ↓ 偵測到 45% 未讀取就編輯
[Phase 4] 掃描行為模式 → 推理迴圈 22/1K TC (高於 20 = Degraded)
[Phase 5] 分析使用者情緒 → 挫折率 12% (高於 10% = Degraded)
[Phase 6] 估算成本 → $85/天平均
[Phase 7] 前後比較 → Read:Edit 從 3.2 降至 1.4 (-56%)
                   → 挫折率從 5% 升至 12% (+140%)

→ 報告明確顯示退化，使用者可據此向 Anthropic 回報或調整工作流程
```

### 案例詳解 2：成本優化分析

**場景**：使用者想了解 Claude Code 的 API 成本結構，找出高成本日並優化使用習慣。

**執行路徑**：

```
python3 analyze_sessions.py --output cost-review.md

[Phase 1] 載入所有 session 檔案
[Phase 6] 成本估算核心流程：
          ↓ 用 request_id 去重 usage_records
          ↓ 計算 Token 用量：
              input_tokens × $15/MTok
              output_tokens × $75/MTok
              cache_read × $1.50/MTok
              cache_creation × $18.75/MTok
          ↓ 每日成本趨勢：
              2026-04-15: $12.50 (輕度使用)
              2026-04-16: $285.00 (密集多 agent 日)
              2026-04-17: $3.20 (純 review)
          ↓ 計算 API requests per prompt = 8.3
              → 高於 3 = 存在修正循環開銷
          ↓ 快取命中率 = 97%
              → 長 session 的 context window 被重複讀取

→ 使用者發現密集日的成本來自子 agent 呼叫和修正循環
→ 建議：更頻繁開新 session 以降低快取成本，使用 Plan Mode 減少盲目編輯
```

---

## 真實使用驗證（Real-World Validation）— 2026-04-29

> [!important] 以下為 30 天實際使用後的驗證結果（2026-03-30 ~ 04-29，51 個主 session + 199 個 subagent），揭露了三個結構性問題和一套改善方案。

### 驗證環境

| 指標 | 數值 |
|------|------|
| 日期範圍 | 2026-03-30 ~ 2026-04-29 |
| 主 Session | 51 (14,111 行) |
| Subagent 檔案 | 199 (16,156 行) |
| 總 Tool Calls | 10,356 (主 4,234 + 子 6,122) |
| User Prompts | 1,000 |
| 總成本 | $2,770 (requestId 去重後) |

### 發現 1：Subagent 混合計算扭曲品質指標

Python 腳本不過濾 subagent 檔案，將所有 JSONL 混合計算。這導致 **Read:Edit 比率被 subagent 美化**：

```
Read:Edit 比率的三種面貌：
├─ 1.44  主 Session only（使用者直接體驗到的品質）
├─ 1.9   Python 混合計算（主+子不區分）← 腳本產出的數字
└─ 2.17  系統級合計（主+子分開後合計）
```

**根因**：Subagent 的 Read:Edit = 2.88（研究導向），遠高於主 Session 的 1.44（退化區間）。混合後得到 1.9，看起來「還行」，實際掩蓋了主 session 的品質退化。

**影響量化**：

| 指標 | 主 Session | Subagent | 混合（Python 報告） |
|------|-----------|----------|------------------|
| Read:Edit | **1.44** | 2.88 | 1.9 |
| Research:Mutation | 1.64 | 3.53 | 2.3 |
| Write % mutations | 16.4% | 11.6% | 15.9% |

### 發現 2：成本存在 46% 重複計算

```
主 Session 成本:   $2,632.17
Subagent 成本:     $2,495.23
原始加總:          $5,127.40
Python 去重後:     $2,769.96  ← 正確值
重複比例:          46%
```

**根因**：主 session 的 usage 紀錄已包含 subagent 消耗的 token（相同 requestId）。分開加總即重複計算。Python 腳本的 **requestId 去重機制是正確做法**。

### 發現 3：情感分析在技術語境完全失效

| Python 報告 | 實際驗證 |
|------------|---------|
| 正面 66 次, 負面 86 次 | 有效正面 **0** 次, 有效負面 **0** 次 |
| 比率 0.8:1 | **N/A（無有效樣本）** |
| 結論：corrective relationship | **結論完全錯誤** |

逐句檢查 30 天內所有命中（以主 session 的 21 負面 + 15 正面為例）：

| 關鍵字 | 次數 | 實際用途 | 有效情感？ |
|--------|------|---------|-----------|
| broken | 14 | "broken wikilinks", "broken YAML" | ❌ 技術描述 |
| good | 15 | URL `writing-a-good-claude-md` | ❌ URL 路徑 |
| wrong | 3 | "claim was WRONG" 研究修正 | ❌ 客觀記錄 |
| lazy | 2 | "lazy loading" 機制討論 | ❌ 技術術語 |

> [!warning] 危險性
> 0.8:1 這個數字看起來精確（有小數點、有 benchmark 對比），容易被報告讀者當作事實。如果呈交給管理層，可能導致「使用者與 AI 關係不佳」的錯誤結論。**沒有驗證的量化分析比沒有分析更危險。**

### 改善方案：三層防線情感分析

基於真實使用發現，提出以下改善架構：

```
原始流程：
  關鍵字匹配 → 計數 → 報告數字 → 結論（可能完全錯誤）

改善後流程：
  多語言關鍵字 → 短 prompt 過濾 → 計數 → 抽樣列表 → 人工確認 → 結論
  ├─ 第一層：多語言覆蓋 + 去除技術術語
  ├─ 第二層：≤50 字 = 即時反應（有效），>50 字 = 設計規劃或貼上內容（排除）
  └─ 第三層：報告內建抽樣驗證表
```

#### 第一層：多語言關鍵字支援

使用者的對話混合繁體中文、簡體中文和英文。擴充為三語清單，並**移除高誤判詞**：

| 類別 | 英文 | 繁體中文 | 簡體中文 |
|------|------|---------|---------|
| 正面 | great, love, nice, perfect, excellent, wonderful, cool, fantastic | 讚、太棒了、很好、完美、漂亮、厲害、優秀、不錯 | 赞、太棒了、很好、完美、漂亮、厉害、优秀、不错 |
| 負面 | fuck, shit, damn, terrible, horrible, awful, sloppy | 爛、廢、靠、幹、糟糕、垃圾、難用 | 烂、废、靠、干、糟糕、垃圾、难用 |

**移除清單**：`broken`（wikilinks）、`wrong`（correction log）、`lazy`（lazy loading）、`bad`（太通用）、`good`（URL 路徑常見）

#### 第二層：短 prompt 過濾（1-50 字元）

```
有效情感 prompt 判定條件：
1. 長度 1-50 字元 → 使用者親手打的即時反應
   - ≤ 50 字元：即時糾正、短句回覆、情緒表達
   - > 50 字元：設計規劃、從別處複製貼上的程式碼/指令
2. 不含 URL（http://, https://）
3. 不含程式碼區塊（```）
4. 不含 frontmatter（---）或 skill 標記
```

**驗證範例**：
- "不對" (6字) ← ✅ 即時糾正
- "stop" (4字) ← ✅ 打斷指令
- "這什麼爛東西" (14字) ← ✅ 情緒表達
- "好，繼續" (8字) ← ✅ 正面肯定
- "Fix all broken wikilinks..." (200字) ← ❌ 排除（技術指令）
- "Base directory for this skill: ..." (500字) ← ❌ 排除（貼上的 prompt）

#### 第三層：報告內建抽樣驗證表

報告自動產出 10-20 個命中句子供人工快速判讀：

```markdown
| # | 詞 | 語言 | 長度 | Prompt 片段 | 有效? |
|---|-----|------|------|------------|-------|
| 1 | 爛 | zh-TW | 14字 | "這報告太爛了" | ❓ |
| 2 | broken | en | 85字 | "...fix broken wikilinks..." | ❓ |
```

讀報告的人花 30 秒掃一眼就能判斷可信度。若有效率 < 50%，情感指標標註為「低信心度」。

---

## 架構師觀點

### 優點評分表

| 維度 | 評分 (1-5) | 說明 |
|------|-----------|------|
| 可部署性 | 5 | 零依賴，Python 3.7+ 即可執行 |
| 方法論嚴謹性 | 4 | 直接複製學術等級的量化分析方法論 |
| 程式碼可讀性 | 4 | 7 個清晰標記的 Phase，每個約 50-100 行 |
| 報告可讀性 | 5 | 不只輸出數字，還有基準對比與敘事解釋 |
| 擴展性 | 2 | 單一 1,348 行檔案，新增指標需要手動插入 |
| 測試覆蓋率 | 1 | 無任何測試 |
| 多元分發 | 5 | 腳本 + Plugin + Slash Command 三模式 |
| 效能 | 3 | 全部載入記憶體，大量 session 時可能吃重 |

### 缺點清單

> [!warning] 以下第 4、9、10 項經 2026-04-29 實際使用驗證確認為真實問題。

1. **無測試**：1,348 行的分析邏輯沒有任何單元測試。Pearson 相關係數的手動實作、日期解析、模式匹配都可能有邊界情況 bug。
2. **記憶體效率**：所有資料都累積在 Python list 中（`thinking_blocks`, `tool_calls`, `user_prompts`, `assistant_texts`, `usage_records`）。對於有數千個 session 的重度使用者，可能消耗大量 RAM。
3. **單檔結構**：1,348 行的單一 Python 檔案違反了模組化原則。7 個 Phase 應該拆分為獨立模組。
4. **🔴 情緒分析在技術語境完全失效**（已驗證）：不只是「會產生誤報」——在 30 天實測中，**所有 36 個正面/負面命中都是誤判**（broken=wikilinks, good=URL, wrong=研究修正, lazy=lazy loading）。0.8:1 的情感比率結論完全錯誤，但因帶有數字和 benchmark 對比，極易被讀者當事實接受。這不只是準確度問題，是**方法論在此應用場景根本不適用**。
5. **時區處理不完整**：`parse_timestamp` 移除了時區資訊（`.replace(tzinfo=None)`），所有分析都假設 UTC，但使用者可能在不同時區工作。
6. **Period Comparison 固定二分法**：只能二等分，無法偵測中間的轉折點。更好的方法是使用滑動窗口或變點偵測（Change Point Detection）。
7. **期間比較中 edit-without-read 的效能問題**：第 560-589 行的雙迴圈嵌套使用了線性搜尋 `tc_matches`，在大量 session 時可能有 O(n^2) 效能問題。
8. **無 License 檔案**：README 聲稱 MIT 授權，但 repo 中沒有 LICENSE 檔案，GitHub 也顯示 License: None。
9. **🔴 不區分主 Session 與 Subagent**（已驗證）：腳本處理所有 JSONL 檔案（含 subagents/ 目錄下的子代理檔），不做任何區分。Subagent 佔 59.1% 的 tool calls 但行為模式完全不同（Read:Edit = 2.88），混合計算導致 Read:Edit 比率從 1.44 被美化到 1.9，掩蓋主 session 的品質退化。
10. **🔴 僅支援英文關鍵字**（已驗證）：情緒分析和行為偵測的關鍵字清單僅有英文。使用繁體中文或簡體中文的使用者（如本次驗證的台灣使用者），其真實情感表達（「爛」、「廢」、「讚」、「太棒了」）完全不會被偵測到。

### 改進建議

**原有建議**：
1. **加入測試**：至少為 `compute_ratios()`, `count_pattern()`, `parse_timestamp()`, Pearson 計算加入單元測試
2. **串流處理**：改用生成器（generator）逐行處理 JSONL，避免全部載入記憶體
3. **模組化**：拆分為 `parser.py`, `thinking.py`, `tools.py`, `behavioral.py`, `sentiment.py`, `cost.py`, `report.py`
4. **增加 `--project` 篩選**：Slash Command 定義中有此選項但 Python 腳本未實作
5. **加入 JSON 輸出**：除了 Markdown，也支援 `--format json` 以便程式化消費
6. **加入 LICENSE 檔案**

**基於真實使用的新建議（2026-04-29）**：

| 優先級 | 改進項 | 原因 | 發現來源 |
|--------|--------|------|---------|
| P0 | **`--separate-subagents` 模式** — 預設排除 subagent，或至少分開統計主/子指標 | Subagent 佔 59% tool calls，混合計算使 Read:Edit 從 1.44 被美化到 1.9 | 實際驗證 |
| P0 | **三層防線情感分析** — 多語言關鍵字 + 短 prompt 過濾(1-50字) + 抽樣驗證表 | 30 天內 0 個有效情感樣本，0.8:1 結論完全錯誤 | 實際驗證 |
| P0 | **移除高誤判關鍵字** — 從清單中移除 broken, wrong, lazy, bad, good | 這些詞在技術對話中幾乎 100% 為技術用語 | 逐句驗證 |
| P1 | **報告內建 10-20 句抽樣驗證表** — 列出情感命中的原始句子供人工判讀 | 讀者花 30 秒即可判斷結論可信度 | 改善設計 |
| P1 | **分別報告主/子 session 的 Read:Edit** — 在報告中同時展示兩個面向 | 不同評估目標需要不同指標：使用者體驗 vs 系統效率 | 比較分析 |
| P2 | **三語關鍵字配置檔** — 外部 config 管理英/繁中/簡中關鍵字，方便依專案調整 | 不同語言使用者的情感表達不同 | 使用者回饋 |

---

## 效能基準（Benchmark）

由於專案無內建 benchmark，以下基於程式碼結構推估：

| 情境 | 估計資料量 | 估計記憶體 | 估計耗時 |
|------|-----------|-----------|---------|
| 輕度使用者（30 天） | ~50 個 JSONL, ~5K 行 | <50 MB | <2 秒 |
| 中度使用者（90 天） | ~200 個 JSONL, ~60K 行 | ~200 MB | 5-10 秒 |
| 重度使用者（90 天） | ~1000 個 JSONL, ~500K 行 | ~1 GB | 30-60 秒 |
| 範例報告規模 | 210 檔, 59,757 行 | ~200 MB | ~10 秒 |

**效能瓶頸**：
- 主要瓶頸在 Phase 1 的 JSONL 逐行解析（I/O + JSON decode）
- Phase 7 的 Period Comparison 中 `edit-without-read` 的雙期分析有 O(n^2) 風險
- 報告產生本身是字串拼接，極快

**最佳化空間**：
- 使用 `orjson` 替代標準 `json` 可加速 ~3x 解析
- 改用 `mmap` 替代逐行讀取可減少 I/O 開銷
- 對大型資料集使用取樣而非全量分析（Slash Command 文件中有提及此策略）

---

## 快速上手（Quick Start）

### 最小可行使用

```bash
# 1. 下載腳本
curl -O https://raw.githubusercontent.com/lucemia/claude-session-analyzer/main/analyze_sessions.py

# 2. 執行分析（分析過去 90 天的所有 Claude Code session）
python3 analyze_sessions.py

# 3. 檢視報告
cat session-analysis-*.md
```

### 指定日期與輸出

```bash
python3 analyze_sessions.py --start 2026-03-01 --end 2026-04-01 --output march-report.md
```

### 分析特定專案

```bash
python3 analyze_sessions.py ~/.claude/projects/my-project/ --output project-report.md
```

### 作為 Claude Code Plugin 使用

```
/plugin install session-analyzer from github:lucemia/claude-session-analyzer
/analyze-sessions
```

### 作為 Slash Command 使用

```bash
mkdir -p ~/.claude/commands
curl -O https://raw.githubusercontent.com/lucemia/claude-session-analyzer/main/commands/analyze-sessions.md
mv analyze-sessions.md ~/.claude/commands/
# 在 Claude Code 中使用 /analyze-sessions
```

---

## 我的心得（My Takeaways）

1. **「讓資料說話」的典範**：這個工具最聰明的地方在於它不是主觀抱怨「Claude Code 變差了」，而是用量化指標證明。Read:Edit 比率從 6.6 降到 2.0、43.8% 的盲目編輯、挫折率翻倍——這些數字比任何 Issue 留言都有說服力。

2. **Signature Length Proxy 的巧妙**：Claude 會遮蔽思考內容但保留簽名欄位，利用 r > 0.95 的相關性從簽名長度反推思考深度，這是典型的「間接測量」（Indirect Measurement）策略。類似的手法在分散式系統中很常見（例如用延遲推估負載）。

3. **零依賴的極致**：手動實作 Pearson 相關係數而不引入 numpy，這在多數專案中是反模式，但在這個特定場景中完全合理——工具的價值在於「任何人隨時能執行」，numpy 的安裝依賴會打破這個承諾。

4. **三模式分發值得學習**：同一個分析邏輯提供獨立腳本（自動化）、Plugin（整合）、Slash Command（互動）三種介面，覆蓋了不同使用者的需求。Slash Command 的 `analyze-sessions.md` 實際上是一份給 Claude 的 prompt engineering，讓 Claude 自己跑分析——這是很有創意的 meta-usage。

5. **這是一個 observability 工具**：本質上，這是 AI Coding Assistant 的 observability 層——類似於 Datadog 之於微服務。AI assistant 的品質退化是漸進的、不容易察覺的，需要量化指標來偵測。這個方向值得關注。

### 2026-04-29 真實使用後的追加心得

6. **「看起來精確」是最危險的錯誤形態**：30 天實測的最大教訓不是情感分析「不夠準」，而是它給出了一個帶有小數點、benchmark 對比、敘事解釋的「完整結論」（0.8:1 = corrective relationship），但**每一個支撐這個結論的資料點都是誤判**。在資料分析中，「無法判斷」遠勝於「精確但錯誤」。

7. **Subagent 是看不見的大象**：Subagent 佔 59% 的 tool calls、49% 的成本，但在報告中完全不可見。它的高 Read:Edit (2.88) 美化了整體指標，讓主 session 的退化 (1.44) 被掩蓋。這類似於微服務架構中「一個健康的 sidecar 掩蓋了核心服務的問題」——指標要分層看。

8. **互動式驗證的不可替代性**：Python 腳本能在 2 分鐘產出完整報告，但它無法做到的是「使用者問『這些負面詞的句子是什麼？』」。正是這個互動式追問揭露了情感分析的完全失效。**最佳實踐不是二擇一，而是：Python 產數字 → Claude 驗結論。**

9. **短 prompt 過濾是最巧妙的啟發式**：使用者親手打出來的挫折永遠是短句（"不對"、"stop"、"這什麼爛東西"），貼上的技術指令永遠是長篇。1-50 字元的閾值簡單到幾乎不需要解釋，但能一刀切掉大部分誤判。好的啟發式不需要複雜——它需要洞察。

---

## 待補充（Open Questions）

1. **Signature Length 的穩定性**：Anthropic 未來是否可能也遮蔽 signature 欄位？若遮蔽，整個思考深度代理指標將失效。這個風險有多大？
2. **跨模型比較**：目前的基準值（Read:Edit > 6.0 = Good 等）是基於特定時期的 Claude Opus。當模型版本更新（如從 Opus 3.5 到 Opus 4），這些基準是否需要重新校正？
3. ~~**情緒分析的誤判率**：基於關鍵字的情緒分析在程式設計語境中有多少誤報？~~ → ✅ **已驗證（2026-04-29）**：30 天實測結果為 **100% 誤判率**（36/36 命中皆為技術用語）。關鍵字情感分析在技術對話語境中完全不適用。已提出三層防線改善方案：多語言關鍵字 + 短 prompt 過濾（1-50 字） + 抽樣驗證表。
4. **大規模使用者的效能**：對於每天產生 100+ session 的重度使用者（如企業團隊），90 天的資料量可能達到數 GB。目前的全載記憶體策略是否需要重構為串流處理？
5. **Plugin 安裝機制**：README 提到 `/plugin install session-analyzer from github:lucemia/claude-session-analyzer`，但 Claude Code 的 Plugin 系統是否已正式支援此語法？或者這是規劃中的功能？
6. ~~**Slash Command 的一致性**~~ → ⚠️ **部分驗證（2026-04-29）**：Slash Command（Claude 子代理執行分析）與獨立腳本確實產生不同結果。主要差異：(a) Slash Command 排除了 subagent 檔案而 Python 腳本包含；(b) Slash Command 無 requestId 去重導致成本重複計算 46%；(c) Slash Command 可互動驗證結論正確性。兩者各有優勢，建議搭配使用。
7. **基準值的地域性**：思考深度的每小時變化（如 05:00 UTC 最深、10:00 UTC 最淺）是否反映特定地域的伺服器負載？不同地區的使用者是否需要不同的基準？
8. **（新）Subagent 成本歸屬**：目前 requestId 去重可避免重複計算，但無法拆分「主 session 的成本」和「subagent 的成本」。如果想分析「哪些 subagent 呼叫最花錢」或「subagent 的 ROI」，需要什麼額外資料結構？搜尋關鍵字：session cost attribution, parent-child token tracking
9. **（新）短 prompt 過濾的最佳閾值**：1-50 字元的閾值是基於直覺設定。是否有更科學的方法確定最佳切分點？例如分析 prompt 長度分布的雙峰特性，找到自然分界。搜尋關鍵字：bimodal distribution, prompt length analysis

---

## 相關連結（Related）

- [[2026-04-02-CLAUDE-CODE-ISSUE-42796-EXTENDED-THINKING-REGRESSION]] — Stella Laurenzo 的原始量化退化分析，本工具的方法論來源
- [[CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]] — Claude Code Token 與成本計算管線研究
- [[AI-Coding-Assistant-Observability]] — AI 程式設計助手的可觀測性（Observability）方向
- [[JSONL-Log-Analysis]] — JSONL 格式日誌分析的通用技術

---

## 知識層次分析（Bloom's Taxonomy Analysis）

### 五個認知層次

| 層次 | 內容 |
|------|------|
| **記憶（Remember）** | Claude Code 的 session 日誌存放在 `~/.claude/projects/` 目錄下，格式為 JSONL。每行是一個 JSON 物件，包含 `type`（system/user/assistant）、`timestamp`、`sessionId`。Assistant 訊息的 `content` 陣列中，`thinking` 區塊的 `signature` 長度與思考內容長度有 r > 0.95 的 Pearson 相關性。品質基準：Read:Edit > 6.0 為 Good，< 2.0 為 Degraded。 |
| **理解（Understand）** | 當 Claude Code 的思考預算不足時，模型會跳過研究步驟（Read/Grep/Glob）直接編輯（Edit/Write），導致 Read:Edit 比率下降。這種行為退化會連鎖反應：盲目編輯 → 品質下降 → 使用者挫折增加 → 中斷次數增多 → 修正循環 → API 成本上升。Signature length 是一個間接代理指標（proxy metric），因為思考內容被遮蔽但簽名保留。 |
| **應用（Apply）** | 能夠在自己的 Claude Code 環境中執行分析、解讀報告中各指標的含義、根據 Period Comparison 判斷品質趨勢、根據 Cost Estimation 調整使用習慣（如更頻繁開新 session 降低快取成本、使用 Plan Mode 減少盲目編輯）。 |
| **分析（Analyze）** | 工具的核心洞察是「行為指標的關聯性分析」——思考深度下降與 Read:Edit 比率下降是共變的（covarying），而非獨立事件。10-call window 的回溯啟發式是一個經驗導向的設計選擇，平衡了精確度與計算成本。零依賴策略犧牲了統計嚴謹性（手動 Pearson 計算）換取了分發便利性。 |
| **評估（Evaluate）** | 這個工具是「AI observability」領域的早期探索者。它的方法論足夠嚴謹以偵測趨勢，但不足以做因果推斷（只能說「Read:Edit 下降了」，不能說「因為思考被限制所以 Read:Edit 下降」）。基於關鍵字的情緒分析在程式設計語境中有固有的精確度上限。作為一個 1,348 行零依賴的工具，它在「80/20 法則」上做出了正確的取捨。 |

### 分析型追問

1. **如果 Anthropic 改變了 JSONL 的結構（例如移除 signature 欄位、改變 content block 的格式），這個工具需要做哪些修改？影響範圍有多大？**
   - 回答方向：Phase 1 的解析邏輯需要更新，但 Phase 2-7 的分析邏輯可以保留。最大的風險是 signature 欄位消失，這會讓思考深度分析完全失效。這凸顯了依賴未文件化內部格式的脆弱性。

2. **比較「獨立腳本」與「Slash Command」兩種執行模式的優劣取捨。在什麼場景下應該選擇哪一種？**
   - 回答方向：獨立腳本適合 CI/CD 整合、定期排程、大量資料的批次處理。Slash Command 適合即時探索、需要 Claude 解釋發現的場景。獨立腳本結果可重現，Slash Command 的結果取決於 Claude 的即時推理。

3. **這個工具能否偵測到 Anthropic 刻意的品質控制行為（如 A/B 測試不同的思考預算）？需要什麼額外的分析方法？**
   - 回答方向：目前的時間序列分析可以偵測到突然的變化，但無法區分是 A/B 測試還是負載變化。需要增加統計顯著性檢驗（如 t-test）和變點偵測（如 CUSUM 或 Bayesian changepoint detection）。

### 方案批判三問

1. **這個方案最可能在哪裡失敗？**
   - Anthropic 更改 JSONL 格式、移除 signature 欄位、或改變 session 儲存位置。這些都是上游的單點故障，工具作者無法控制。此外，隨著 Claude Code 版本更新，品質基準可能需要重新校正，但目前沒有自動校正機制。
   - **（2026-04-29 追加）已確認的失敗模式**：情感分析在技術對話中 100% 誤判。Subagent 混合計算掩蓋主 session 品質退化。這兩個問題在工具原始設計中並未預見，因為原始分析（anthropics/claude-code#42796）可能未大量使用 subagent，且對話語言為英文而非中文。

2. **誰最不喜歡這個方案？為什麼？**
   - Anthropic 可能不希望使用者量化偵測品質退化，因為這會產生公關壓力。如果大量使用者都能用數據證明「你的產品在某個時期變差了」，這比主觀抱怨更難反駁。這也是為什麼 thinking content 被遮蔽——減少使用者的可觀測性。

3. **如果預算和時間翻倍，你會怎麼改進這個方案？**
   - (a) 加入 Web UI 儀表板（用 Streamlit 或 Plotly Dash），提供互動式圖表和時間序列瀏覽
   - (b) 加入統計顯著性檢驗，自動偵測變點而非固定二分
   - (c) 加入 PR-level 分析：追蹤每個 PR 的 session 品質，與 PR 被退回/合併的結果關聯
   - (d) 建立跨使用者的匿名基準資料庫，讓個人指標與社群基準對比
   - **（2026-04-29 追加）**
   - (e) 實作三層防線情感分析（多語言 + 短 prompt 過濾 + 抽樣驗證表）
   - (f) 增加 `--separate-subagents` 模式，分開報告主 session 和 subagent 的指標
   - (g) 在報告中自動對每個「結論型」指標列出 10-20 個原始樣本，內建人工可驗證性

---

## References

- GitHub Repo: https://github.com/lucemia/claude-session-analyzer
- 原始分析 Issue: https://github.com/anthropics/claude-code/issues/42796
- Stella Laurenzo (@stellaraccident) 的量化退化分析方法論
- AWS Bedrock Claude Opus 定價: https://aws.amazon.com/bedrock/pricing/
- Claude Code Session JSONL 格式（非官方文件，從工具程式碼中逆向整理）
