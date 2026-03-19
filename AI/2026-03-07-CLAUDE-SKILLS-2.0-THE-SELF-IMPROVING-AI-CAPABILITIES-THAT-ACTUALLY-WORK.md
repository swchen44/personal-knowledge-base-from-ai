---
title: "Claude Skills 2.0：真正有效的自我改善 AI 能力"
date: 2026-03-07
category: AI
tags:
  - ai/claude-code
  - ai/skills
  - ai/eval
  - tools/claude
  - productivity/skill-building
  - ai/workflow
source: "https://medium.com/@reliabledataengineering/claude-skills-2-0-the-self-improving-ai-capabilities-that-actually-work-dc3525eb391b"
source_type: article
author: "Reliable Data Engineering"
status: notes
links:
  - "[[CLAUDE-MEMORY-ENGINE]]"
  - "[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]"
  - "[[CLAUDE-CODE-141-AGENTS-SETUP]]"
---

## Summary

Skills 1.0（2025 年 10 月）是靜態範本，你寫指令、Claude 照著做。Skills 2.0（2026 年 1 月）是一個**回饋循環**：自動建立 skill、自動測試、自動 A/B 比較、自動優化觸發描述。一位開發者透過兩次優化循環，把 skill 成功率從 67% 提升到 94%。

## Key Insights

- **Skills 2.0 的本質是回饋循環，不是工具** — Skill Creator 建立、Eval 測試、A/B 量化、Description 優化，四個環節形成自我改善系統
- **描述（Description）決定 skill 能否被載入** — 描述不夠廣，再好的 skill 也不會被觸發；優化後觸發準確率可從 40% 提升到 95%+
- **Fork 模式解決 context 污染問題** — 重型 skill 在獨立 subagent 執行，結果傳回主對話，主 context 保持乾淨
- **兩種 skill 的壽命截然不同** — 能力提升型（Capability Uplift）隨模型進步而退休；工作流程型（Workflow）隨時間累積成競爭優勢
- **測試方法決定成功率** — 不測試 45%、手動測試 67%、結構化 eval 89%、eval + A/B 94%
- **Skill Creator 比手動快 12 倍** — 手動建立 30-60 分鐘，Skill Creator 2-5 分鐘，且品質更高

## Details

### Skills 1.0 vs Skills 2.0 對比

| 面向 | Skills 1.0 | Skills 2.0 |
|------|-----------|-----------|
| 建立方式 | 手動建立資料夾、寫 SKILL.md | Skill Creator 自動生成 |
| 測試 | 手動試幾次 | 結構化 eval，自動跑測試案例 |
| 改善 | 靠感覺 | A/B testing，數據量化 |
| 觸發優化 | 無 | 自動測試描述準確率 |
| 執行隔離 | 無（共用 context） | Fork 模式（獨立 subagent） |
| 更新生效 | 重啟 Claude | 熱更新（即時生效） |

---

### 功能 1：Skill Creator（描述即建立）

**使用方式**：用自然語言描述需求，Skill Creator 提問澄清後自動生成完整 skill。

**自動生成的內容**：
- 完整資料夾結構
- SKILL.md（含 frontmatter）
- 輔助腳本（Python、bash 等）
- 範本與範例
- 測試案例
- README 文件

**實際案例（SEO Audit Skill）**：
- 輸入：「Create a skill to audit website SEO」
- 輸出：分析 meta tags、headers、行動裝置相容性、Schema 標記，生成建議報告
- 建立時間：2 分鐘（vs 手動 45 分鐘）

---

### 功能 2：結構化 Eval（自動化測試）

**解決的問題**：Skills 1.0 沒有系統性測試，只能靠感覺判斷 skill 好不好。

**Eval 流程**：
1. Skill Creator 根據 skill 目的自動生成測試案例
2. 對每個測試案例執行 skill
3. 比對輸出與預期結果
4. 回報通過率、失敗原因
5. 根據失敗模式提出優化建議

**案例：保險理賠分類 Skill**
- 初始成功率：67%
- 優化後：94%
- 改善幅度：+40%

---

### 功能 3：A/B Testing（量化改善效果）

**設計**：同樣的任務，有無 skill 各跑 10 個測試案例，比較結果。

**實測數據**：

| 任務 | 無 Skill | 有 Skill | 改善 |
|------|---------|---------|------|
| SEO Audit | 34% | 87% | +156% |
| 保險理賠分類 | 67% | 94% | +40% |
| PDF 表單處理 | 23% | 89% | +287% |
| **平均** | | | **+161%** |

**PDF 表單 Skill 詳細數據**：
- 成功率：23% → 89%（+287%）
- 處理時間：45 秒 → 12 秒（快 3.75 倍）

---

### 功能 4：觸發描述優化

**問題**：Skill 完美，但 Claude 從不載入它——因為描述不夠廣。

**優化前後對比**：

```
❌ 差的描述：
description: Analyzes surveys

✅ 好的描述：
description: Process customer feedback surveys, user satisfaction surveys,
NPS forms, or response data from CSV/JSON/Excel. Generate sentiment analysis
and summary reports. Use when user mentions surveys, feedback, responses,
or satisfaction data.
```

**觸發準確率**：差的描述 40%，好的描述 95%+

**好描述的要素**：
- 包含同義詞（surveys/feedback/responses）
- 提及檔案格式（CSV/JSON/Excel）
- 說明輸出（sentiment/summary）
- 解釋何時應觸發

**Anthropic 的測試結果**：對 6 個公開 skill 進行優化，5 個改善觸發準確率，平均提升 33%。

---

### 功能 5：Fork Context 模式（隔離執行）

**三種 Context 模式**：

**Inline（預設，Skills 1.0 行為）**
- Skill 指令加入主對話 context
- 問題：指令一直佔用 token，可能影響不相關的任務

**Fork（Skills 2.0 新增）**
```yaml
---
name: my-skill
context: fork
---
```
- 建立獨立 subagent 執行 skill
- 只有結果傳回主對話
- 主 context 保持乾淨

**何時用 Fork 模式**：
- Skill 指令超過 2000 tokens
- 需要處理大型文件
- 不希望 skill 邏輯留在主對話
- Skill 會被反覆呼叫

**Context 節省**：重型 skill 用 Fork 模式可節省約 20% 主 context。

**Manual invoke only（防止自動觸發）**：
```yaml
disable-model-invocation: true  # 使用者必須明確呼叫 /skill-name
```
適用於：破壞性操作、部署腳本、財務交易。

---

### 功能 6：熱更新（不需重啟）

| | Skills 1.0 | Skills 2.0 |
|---|-----------|-----------|
| 流程 | 編輯 → 重啟 Claude → 測試 | 編輯 → 直接測試 |
| 時間 | 約 45 秒 | 約 2 秒 |
| 速度 | 基準 | **快 23 倍** |

---

### 功能 7：Frontmatter 整合 Hooks 與 Agent

```yaml
---
name: deploy-to-prod
description: Deploy application to production
hooks:
  before: ./pre-deploy-checks.sh   # 執行前驗證
  after: ./post-deploy-notify.sh   # 執行後通知
allowed-tools:
  - Bash(git*)
  - Bash(docker*)
---
```

**自訂 Agent 模型**：
```yaml
agent: gpt-4-turbo  # 指定此 skill 使用的模型
```

應用場景：
- 成本優化（簡單 skill 用 Haiku）
- 能力匹配（複雜推理用 Opus）
- 跨模型效能比較

---

### 兩種 Skill 類型

**能力提升型（Capability Uplift）**
- 目的：填補模型能力缺口（暫時性）
- 例：PDF 表單處理、PowerPoint 生成、Excel 公式
- 壽命：有限，模型進步後自然退休
- 判斷退休時機：Benchmark 顯示基礎模型已通過 eval

**工作流程型（Workflow/Preference）**
- 目的：將特定流程自動化（永久性）
- 例：品牌語調、NDA 審查、財務報告格式、Code Review 標準
- 壽命：無限期，隨時間累積成組織知識
- 價值：隨使用增加而增長

---

### 真實案例

**Rakuten 財務團隊**：
- 月度會計報告：8 小時 → 1 小時（節省 87.5%）
- 額外效益：發現人工審閱漏掉的異常

**Box 內容轉換**：
- 將 Box 儲存的文件自動轉換成 PowerPoint、Excel、Word
- 從幾小時縮短到幾分鐘

**醫療生命科學（2026 年 2 月新 Skills）**：
- FHIR Development Skill（醫療資料交換標準）
- Prior Authorization Review（保險預授權審查）
- Clinical Trial Protocol Draft（臨床試驗協議草稿）
- 生物資訊學套件（scVI-tools、Nextflow）

---

### 測試方法與成功率對照

| 測試方法 | 成功率 |
|---------|-------|
| 不測試 | 45% |
| 手動測試（5 個案例） | 67% |
| 結構化 eval（10+ 個案例） | 89% |
| Eval + A/B 測試 | 94% |

---

### Skills 2.0 vs 其他工具

| 工具 | 特點 | 限制 |
|------|------|------|
| **Prompts** | 一次性指令，每次重寫 | 無優化回饋，手動維護 |
| **Projects（Claude.ai）** | 持久化 context | 所有指令始終載入，無結構化測試 |
| **Custom GPTs（OpenAI）** | 獨立 bot | 平台鎖定，無版本控制 |
| **MCP** | 連接外部工具/即時資料 | 整合導向，非工作流程導向 |
| **Skills 2.0** | 模組化、可跨平台、有 eval | — |

> [!note] MCP 與 Skills 2.0 是互補的
> MCP：「這是來自 Slack 的即時資料」
> Skills：「這是處理那份 Slack 資料的方式」

---

### 建議開發流程

```
1. 更新到 Claude Code 2.1+
2. 用 Skill Creator 描述工作流程（不要手動建立）
3. 讓它自動生成 skill + 測試案例
4. 執行結構化 eval
5. 優化後 re-test
6. 可選：跑 A/B test 量化效益
7. 部署給團隊
```

**版本控制 Skills**：
```bash
cd ~/.claude/skills
git init && git add . && git commit -m "Initial skills"
# 修改後
git commit -m "Improved error handling"
git push  # 分享給團隊
```

---

### 2026 年路線圖（已公告）

- **簡化建立流程**：視覺化 skill 建立介面（無程式碼）、Skill 模板庫
- **企業管理**：細粒度權限、使用分析、合規控制、審核流程
- **Skill Marketplace**：社群提交、評分評論、品質驗證

## References

- [原文](https://medium.com/@reliabledataengineering/claude-skills-2-0-the-self-improving-ai-capabilities-that-actually-work-dc3525eb391b)
- 相關文章：[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]
