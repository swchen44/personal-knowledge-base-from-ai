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

技能 1.0（Skills 1.0，2025 年 10 月）是靜態範本（static template），你寫指令、Claude 照著做。技能 2.0（Skills 2.0，2026 年 1 月）是一個**回饋循環（feedback loop）**：自動建立技能（skill）、自動測試、自動 A/B 比較、自動優化觸發描述（trigger description）。一位開發者透過兩次優化循環（optimization cycle），把技能成功率（skill success rate）從 67% 提升到 94%。

## Key Insights

- **技能 2.0（Skills 2.0）的本質是回饋循環（feedback loop），不是工具** — 技能建立器（Skill Creator）建立、評估（eval）測試、A/B 量化、描述優化（description optimization），四個環節形成自我改善系統
- **描述（description）決定技能（skill）能否被載入** — 描述不夠廣，再好的技能（skill）也不會被觸發；優化後觸發準確率（trigger accuracy）可從 40% 提升到 95%+
- **分叉模式（fork mode）解決情境污染（context pollution）問題** — 重型技能（skill）在獨立子代理（subagent）執行，結果傳回主對話，主情境（main context）保持乾淨
- **兩種技能（skill）的壽命截然不同** — 能力提升型（Capability Uplift）隨模型進步而退休（retire）；工作流程型（Workflow）隨時間累積成競爭優勢
- **測試方法決定成功率** — 不測試 45%、手動測試 67%、結構化評估（structured eval）89%、評估（eval）+ A/B 94%
- **技能建立器（Skill Creator）比手動快 12 倍** — 手動建立 30-60 分鐘，技能建立器（Skill Creator）2-5 分鐘，且品質更高

## Details

### Skills 1.0 vs Skills 2.0 對比

| 面向 | Skills 1.0 | Skills 2.0 |
|------|-----------|-----------|
| 建立方式 | 手動建立資料夾、寫 SKILL.md | 技能建立器（Skill Creator）自動生成 |
| 測試 | 手動試幾次 | 結構化評估（structured eval），自動跑測試案例（test case） |
| 改善 | 靠感覺 | A/B 測試（A/B testing），數據量化 |
| 觸發優化 | 無 | 自動測試描述準確率（description accuracy） |
| 執行隔離 | 無（共用情境（context）） | 分叉模式（fork mode）（獨立子代理（subagent）） |
| 更新生效 | 重啟 Claude | 熱更新（hot reload）（即時生效） |

---

### 功能 1：技能建立器（Skill Creator）（描述即建立）

**使用方式**：用自然語言描述需求，技能建立器（Skill Creator）提問澄清後自動生成完整技能（skill）。

**自動生成的內容**：
- 完整資料夾結構
- SKILL.md（含前置資訊（frontmatter））
- 輔助腳本（Python、bash 等）
- 範本（template）與範例
- 測試案例（test case）
- README 文件

**實際案例（SEO 審查技能（SEO Audit Skill））**：
- 輸入：「Create a skill to audit website SEO」
- 輸出：分析元標籤（meta tags）、標頭（headers）、行動裝置相容性、結構化資料標記（Schema markup），生成建議報告
- 建立時間：2 分鐘（vs 手動 45 分鐘）

---

### 功能 2：結構化評估（Structured Evals）（自動化測試）

**解決的問題**：技能 1.0（Skills 1.0）沒有系統性測試，只能靠感覺判斷技能（skill）好不好。

**評估（Eval）流程**：
1. 技能建立器（Skill Creator）根據技能（skill）目的自動生成測試案例（test case）
2. 對每個測試案例（test case）執行技能（skill）
3. 比對輸出與預期結果
4. 回報通過率（pass rate）、失敗原因
5. 根據失敗模式（failure pattern）提出優化建議

**案例：保險理賠分類技能（Insurance Claim Triage Skill）**
- 初始成功率：67%
- 優化後：94%
- 改善幅度：+40%

---

### 功能 3：A/B 測試（A/B Testing）（量化改善效果）

**設計**：同樣的任務，有無技能（skill）各跑 10 個測試案例（test case），比較結果。

**實測數據**：

| 任務 | 無 Skill | 有 Skill | 改善 |
|------|---------|---------|------|
| SEO 審查（SEO Audit） | 34% | 87% | +156% |
| 保險理賠分類（Insurance Triage） | 67% | 94% | +40% |
| PDF 表單處理（PDF Forms） | 23% | 89% | +287% |
| **平均** | | | **+161%** |

**PDF 表單技能（PDF Form Skill）詳細數據**：
- 成功率：23% → 89%（+287%）
- 處理時間：45 秒 → 12 秒（快 3.75 倍）

---

### 功能 4：觸發描述優化（Trigger Description Optimization）

**問題**：技能（skill）完美，但 Claude 從不載入它——因為描述（description）不夠廣。

**優化前後對比**：

```
❌ 差的描述（description）：
description: Analyzes surveys

✅ 好的描述（description）：
description: Process customer feedback surveys, user satisfaction surveys,
NPS forms, or response data from CSV/JSON/Excel. Generate sentiment analysis
and summary reports. Use when user mentions surveys, feedback, responses,
or satisfaction data.
```

**觸發準確率（Trigger Accuracy）**：差的描述 40%，好的描述 95%+

**好描述（description）的要素**：
- 包含同義詞（synonyms）（surveys/feedback/responses）
- 提及檔案格式（file formats）（CSV/JSON/Excel）
- 說明輸出（output）（sentiment/summary）
- 解釋何時應觸發

**Anthropic 的測試結果**：對 6 個公開技能（skill）進行優化，5 個改善觸發準確率（trigger accuracy），平均提升 33%。

---

### 功能 5：分叉情境模式（Fork Context Mode）（隔離執行）

**三種情境模式（Context Mode）**：

**內嵌模式（Inline Mode）**（預設，Skills 1.0 行為）
- 技能（skill）指令加入主對話情境（context）
- 問題：指令一直佔用詞元（token），可能影響不相關的任務

**分叉模式（Fork Mode）**（Skills 2.0 新增）
```yaml
---
name: my-skill
context: fork
---
```
- 建立獨立子代理（subagent）執行技能（skill）
- 只有結果傳回主對話
- 主情境（main context）保持乾淨

**何時用分叉模式（Fork Mode）**：
- 技能（skill）指令超過 2000 詞元（token）
- 需要處理大型文件
- 不希望技能（skill）邏輯留在主對話
- 技能（skill）會被反覆呼叫

**情境（Context）節省**：重型技能（skill）用分叉模式（fork mode）可節省約 20% 主情境（main context）。

**僅手動呼叫（Manual Invoke Only）**（防止自動觸發）：
```yaml
disable-model-invocation: true  # 使用者必須明確呼叫 /skill-name
```
適用於：破壞性操作（destructive operation）、部署腳本（deployment script）、財務交易。

---

### 功能 6：熱更新（Hot Reload）（不需重啟）

| | Skills 1.0 | Skills 2.0 |
|---|-----------|-----------|
| 流程 | 編輯 → 重啟 Claude → 測試 | 編輯 → 直接測試 |
| 時間 | 約 45 秒 | 約 2 秒 |
| 速度 | 基準 | **快 23 倍** |

---

### 功能 7：前置資訊整合鉤子與代理（Frontmatter Hooks & Agent）

```yaml
---
name: deploy-to-prod
description: Deploy application to production
hooks:
  before: ./pre-deploy-checks.sh   # 執行前驗證（pre-execution validation）
  after: ./post-deploy-notify.sh   # 執行後通知（post-execution notification）
allowed-tools:
  - Bash(git*)
  - Bash(docker*)
---
```

**自訂代理（Agent）模型**：
```yaml
agent: gpt-4-turbo  # 指定此技能（skill）使用的模型（model）
```

應用場景：
- 成本優化（cost optimization）（簡單技能（skill）用 Haiku）
- 能力匹配（capability matching）（複雜推理用 Opus）
- 跨模型效能比較（cross-model performance comparison）

---

### 兩種 Skill 類型

**能力提升型（Capability Uplift）**
- 目的：填補模型（model）能力缺口（暫時性）
- 例：PDF 表單處理、PowerPoint 生成、Excel 公式
- 壽命：有限，模型（model）進步後自然退休（retire）
- 判斷退休（retire）時機：基準測試（benchmark）顯示基礎模型（base model）已通過評估（eval）

**工作流程型（Workflow/Preference）**
- 目的：將特定流程（workflow）自動化（永久性）
- 例：品牌語調（brand voice）、保密協議審查（NDA review）、財務報告格式、程式碼審查（code review）標準
- 壽命：無限期，隨時間累積成組織知識（organizational knowledge）
- 價值：隨使用增加而增長

---

### 真實案例

**Rakuten 財務團隊**：
- 月度會計報告：8 小時 → 1 小時（節省 87.5%）
- 額外效益：發現人工審閱漏掉的異常值（anomaly）

**Box 內容轉換**：
- 將 Box 儲存的文件自動轉換成 PowerPoint、Excel、Word
- 從幾小時縮短到幾分鐘

**醫療生命科學（2026 年 2 月新 Skills）**：
- FHIR 開發技能（FHIR Development Skill）（醫療資料交換標準）
- 預授權審查（Prior Authorization Review）（保險預授權審查）
- 臨床試驗協議草稿（Clinical Trial Protocol Draft）
- 生物資訊學套件（Bioinformatics Bundle）（scVI-tools、Nextflow）

---

### 測試方法與成功率對照

| 測試方法 | 成功率 |
|---------|-------|
| 不測試 | 45% |
| 手動測試（5 個案例） | 67% |
| 結構化評估（structured eval）（10+ 個案例） | 89% |
| 評估（eval）+ A/B 測試（A/B testing） | 94% |

---

### Skills 2.0 vs 其他工具

| 工具 | 特點 | 限制 |
|------|------|------|
| **提示詞（Prompts）** | 一次性指令，每次重寫 | 無優化回饋（optimization feedback），手動維護 |
| **專案（Projects）（Claude.ai）** | 持久化情境（persistent context） | 所有指令始終載入，無結構化測試 |
| **自訂 GPT（Custom GPTs）（OpenAI）** | 獨立機器人（bot） | 平台鎖定（platform lock-in），無版本控制 |
| **模型情境協議（MCP, Model Context Protocol）** | 連接外部工具（tool）/即時資料 | 整合導向，非工作流程（workflow）導向 |
| **Skills 2.0** | 模組化、可跨平台、有評估（eval） | — |

> [!note] MCP 與 Skills 2.0 是互補的
> MCP：「這是來自 Slack 的即時資料」
> Skills：「這是處理那份 Slack 資料的方式」

---

### 建議開發流程

```
1. 更新到 Claude Code 2.1+
2. 用技能建立器（Skill Creator）描述工作流程（workflow）（不要手動建立）
3. 讓它自動生成技能（skill）+ 測試案例（test case）
4. 執行結構化評估（structured eval）
5. 優化後重新測試（re-test）
6. 可選：跑 A/B 測試（A/B testing）量化效益
7. 部署（deploy）給團隊
```

**版本控制（Version Control）技能（Skills）**：
```bash
cd ~/.claude/skills
git init && git add . && git commit -m "Initial skills"
# 修改後
git commit -m "Improved error handling"
git push  # 分享給團隊
```

---

### 2026 年路線圖（已公告）

- **簡化建立流程**：視覺化技能建立介面（visual skill builder）（無程式碼）、技能模板庫（skill template library）
- **企業管理（Enterprise Management）**：細粒度權限（granular permissions）、使用分析（usage analytics）、合規控制（compliance controls）、審核流程（approval workflow）
- **技能市集（Skill Marketplace）**：社群提交（community submissions）、評分評論、品質驗證（quality verification）

## 待補充（Open Questions）

- Skills 2.0 的 A/B 測試結果（如 PDF 表單 +287%）是否有控制組設計？不同資料集或不同 Claude 版本下，這些數字的可重現性如何？（建議搜尋：`Claude skill A/B test reproducibility benchmark variance`）
- 技能建立器（Skill Creator）自動生成的測試案例品質如何驗證？若自動生成的測試案例本身有盲點，會不會導致一種「循環自我欺騙」的假高分？（建議搜尋：`automated test case quality validation AI skill creator`）
- 分叉模式（fork mode）中，子代理人與主對話的資料傳遞邊界為何？若子代理人輸出中包含敏感資訊，傳回主對話後如何管理隱私？（建議搜尋：`Claude skill fork mode context isolation data privacy`）
- 2026 年路線圖提到「企業管理」中的細粒度權限（granular permissions），具體控制粒度是否包含資料分類（如 PII 欄位）？（建議搜尋：`Claude skill enterprise permissions granular data classification`）
- 工作流程型 Skill（Workflow/Preference）隨時間「累積成組織知識」，但若組織工作流程改變，如何系統性審計並更新已有 Skill？（建議搜尋：`organizational skill audit workflow change management`）

## 相關連結（Related）

- [[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]] — 同日期發布的 Skill Eval 實戰文章
- [[2026-03-07-CLAUDE-MEMORY-ENGINE]] — Claude Memory Engine 的程式碼分析，記憶系統是 Skills 2.0 自我改善的基礎
- [[2026-03-16-SELF-EVOLVING-AGENT-CORE-MECHANISMS]] — 自我進化代理人的核心機制，與 Skills 2.0 的自動建立、測試、優化循環理念相通

## References

- [原文](https://medium.com/@reliabledataengineering/claude-skills-2-0-the-self-improving-ai-capabilities-that-actually-work-dc3525eb391b)
- 相關文章：[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | Skills 1.0 vs 2.0 對比（靜態範本 vs 回饋循環）、技能建立器（Skill Creator）、結構化評估（Structured Evals）、A/B 測試、觸發描述優化（Trigger Description Optimization）、分叉情境模式（Fork Context Mode）、熱更新（Hot Reload）、能力提升型（Capability Uplift）vs 工作流程型（Workflow）skill 分類、測試方法與成功率對照（不測試 45% → eval + A/B 94%）、Anthropic 公告的 2026 年路線圖 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Skills 2.0 的本質是將 skill 開發從「靜態指令撰寫」升級為「自我改善的回饋循環」：技能建立器自動生成結構，結構化評估量化成效，A/B 比較排除確認偏誤，描述優化確保正確觸發，分叉模式隔離執行防止上下文污染；這五個環節形成閉環，讓 skill 品質可以在沒有人工主觀判斷的情況下，透過數據驅動的迭代持續改善。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | （1）A/B 測試的量化結果（如 PDF 表單 +287%）未說明控制組設計，不同資料集或任務類型下的可重現性存疑；（2）「技能建立器比手動快 12 倍」的聲稱缺乏品質對比——快速生成的 skill 初始品質可能低於有經驗者手動撰寫的版本，需要更多迭代才能達到相同品質；（3）文章假設工作流程型 skill 會隨使用「累積成組織知識」，但若工作流程本身發生改變，未被及時更新的 skill 反而會成為組織的技術債。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | （1）對現有手動建立的 skill 使用技能建立器重新生成，取得自動生成的測試案例集，補充過去缺乏的測試覆蓋率；（2）對指令超過 2000 token 或需要處理大型文件的 skill，在 frontmatter 中加入 `context: fork` 切換至分叉模式，降低主上下文佔用；（3）建立 skill 版本控制（`cd ~/.claude/skills && git init`），讓 skill 迭代可追蹤並便於跨團隊分享。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | Skills 2.0 的核心優勢是將 skill 品質的判斷從「感覺」轉化為「數字」，但自動化測試案例本身的品質仍是瓶頸——若技能建立器生成的測試案例覆蓋範圍不足，高通過率反映的是測試設計的局限而非 skill 的真正品質；與 MCP 相比，skill 更適合「過程導向的工作流程」，MCP 更適合「資料存取」，兩者互補而非競爭，在設計架構時應明確區分兩類工具的使用邊界。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：技能建立器（Skill Creator）自動生成的測試案例，是基於 skill 的描述文字推斷而來，還是需要開發者提供額外的業務脈絡輸入？兩者的測試案例品質差距為何？
- **假設**：文章假設「工作流程型 skill 的價值隨時間增加」，但此假設依賴工作流程的穩定性——若組織工作流程每季都在大幅調整，此假設是否仍然成立？
- **證據**：Anthropic 對 6 個公開 skill 執行描述優化後，5 個改善且平均提升 33%，但這 6 個 skill 是如何選取的？是否代表了不同類型 skill 的典型案例，還是存在選擇偏誤？
- **觀點**：從組織管理角度，若 skill 庫由個別開發者各自維護，缺乏統一的品質審核機制，skill 質量的離散程度是否會逐漸成為組織效率的新瓶頸？
- **後果**：若大量組織採用 Skills 2.0 的自我改善框架，skill 的演化方向是否會逐漸趨同於「AI 更容易執行的工作流程」而非「人類業務真正需要的工作流程」，形成一種新的技術對業務的反向馴化？
