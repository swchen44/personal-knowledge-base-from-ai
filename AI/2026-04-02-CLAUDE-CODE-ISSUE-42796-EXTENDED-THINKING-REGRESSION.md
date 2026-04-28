---
title: "Claude Code 在二月更新後無法勝任複雜工程任務 — 延伸思考退化的量化分析"
date: 2026-04-02
category: AI
tags:
  - "#ai/claude-code"
  - "#ai/extended-thinking"
  - "#ai/model-regression"
  - "#ai/observability"
source: "https://github.com/anthropics/claude-code/issues/42796"
source_type: article
author: "stellaraccident (Stella Laurenzo)"
status: notes
links:
  - "[[2026-04-10-CLAUDE-SESSION-ANALYZER-CODE-ANALYSIS]]"
  - "[[CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]]"
  - "[[AI-Coding-Assistant-Observability]]"
---

## 摘要（Summary）

AMD AI 資深總監 Stella Laurenzo 在 GitHub 提出了一份極為詳細的 issue，以量化數據分析了 Claude Code 從 2026 年 1 月到 3 月的品質退化問題。報告基於 **17,871 個 thinking blocks** 和 **234,760 次工具呼叫**（跨 6,852 個 Claude Code session），發現延伸思考（extended thinking）的深度被大幅縮減，直接導致模型行為從「先研究再編輯」退化為「直接編輯不看程式碼」。該 issue 引起巨大社群迴響，累計 583 則留言、291 位不同使用者參與討論。Anthropic 最終於 4 月 23 日發佈正式事後分析報告（postmortem）。

## 關鍵洞察（Key Insights）

1. **思考深度（thinking depth）與程式碼品質高度相關**：thinking content 中位數從基線期的 ~2,200 字元降至 ~560 字元（下降 75%），這個下降早在思考內容被遮蔽（redaction）之前就已發生。

2. **Read:Edit 比率是關鍵品質指標**：模型在「好的時期」每次編輯前會讀 6.6 個檔案，退化後僅讀 2.0 個（下降 70%）。三分之一的編輯是在未讀取目標檔案的情況下進行的。

3. **三個關鍵變更疊加造成退化**：
   - Opus 4.6 啟用自適應思考（adaptive thinking），模型自行決定思考多久
   - 預設努力等級（effort）從 high 降為 medium（effort=85）
   - 系統提示詞（system prompt）新增「Output efficiency」指令，要求模型「先試最簡單的方法」

4. **程式化停止鉤子（stop hook）是退化的量化證據**：一個用來偵測模型「偷懶行為」的 bash 腳本，在 3 月 8 日之前觸發 0 次，之後 17 天內觸發 173 次（平均每天 10 次）。

5. **使用者情緒顯著惡化**：正面/負面詞彙比從 4.4:1 降至 3.0:1；「simplest」一詞使用頻率暴增 642%；「please」和「thanks」分別下降 49% 和 55%。

6. **退化造成成本爆炸**：使用者提示數量不變（~5,600/月），但 API 請求從 1,498 暴增至 119,341（80 倍），估計 Bedrock 成本從 $345 飆升至 $42,121（122 倍）。

## 詳細內容（Details）

### Issue 提報者背景

Stella Laurenzo（GitHub: stellaraccident）是 AMD 的 AI 資深總監，負責 IREE（中間表示執行環境）等系統程式設計專案，使用 Claude Code 管理 50+ 並行 agent session，涉及 C、MLIR、GPU 驅動程式等複雜程式碼。她讓 Claude 分析自己的 session 日誌，產出了這份報告。

### 核心發現：思考遮蔽時間線與品質退化完全吻合

報告分析了 thinking blocks 的可見/遮蔽比例：

- 1 月 30 日 - 3 月 4 日：100% 可見
- 3 月 5 日：98.5% 可見
- **3 月 8 日：41.6% 可見（品質退化的獨立報告日期）**
- 3 月 12 日起：100% 遮蔽

利用 `signature` 欄位（與 thinking 長度有 0.971 的 Pearson 相關性）推估思考深度，發現在遮蔽開始之前，思考深度就已經從 ~2,200 字元降到 ~720 字元。

### 行為模式退化的量化證據

報告的附錄（Appendix A）詳列了八類可量化的退化行為：

**A.1 未讀取就編輯**：退化期有 33.7% 的編輯未先讀取檔案（好的時期僅 6.2%），導致註解被插入錯誤位置、邏輯重複等問題。

**A.2 推理迴圈**：模型在輸出中自我矛盾的頻率從每千次工具呼叫 8.2 次增至 26.6 次（3 倍以上）。

**A.3 「最簡單修復」心態**：「simplest」一詞出現頻率從 2.7/千次增至 6.3/千次。

**A.4 過早停止與請求許可**：停止鉤子在 3 月 8 日後捕獲 173 次違規（之前為 0），包括推卸責任（73 次）、請求許可（40 次）、過早停止（18 次）等。

**A.5 使用者中斷**：每千次工具呼叫的中斷率從 0.9 增至 11.4（12 倍）。

**A.6 自承品質失敗**：模型自己承認輸出偷懶的頻率增加了 5 倍。

**A.8 慣例偏移**：儘管 CLAUDE.md 有 5,000+ 字的編碼慣例文件在上下文中，模型仍開始違反命名規則、清理模式等。

### 時段分析

報告發現退化後，思考深度變得與時段高度相關（之前幾乎無關）：
- 最差時段：太平洋時間下午 5 點（估計思考 423 字元）和晚上 7 點（373 字元）
- 最佳時段：深夜 11 點（988 字元）
- 這暗示思考分配可能是根據負載（load-sensitive）動態調整，而非固定預算

### Anthropic 官方回應

Claude Code 創建者 Boris Cherny（bcherny）在留言中解釋了三個相關變更：

1. **思考遮蔽（`redact-thinking-2026-02-12`）**：僅為 UI 變更，不影響思考本身。可用 `showThinkingSummaries: true` 關閉。

2. **自適應思考（adaptive thinking）**：Opus 4.6 預設啟用，模型自行決定思考時間。可用 `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1` 關閉。

3. **努力等級預設為 medium（effort=85）**：在 3 月 3 日變更，可用 `/effort high` 或 `/effort max` 調整。

Boris 表示已確認沒有他所知的其他內部變更導致此問題，並要求使用者透過 `/bug` 提交具體 transcript 以便調查。

### 社群發現：系統提示詞變更

社群成員 @wjordan 發現在 v2.1.64（約 3 月 3-4 日）新增了「Output efficiency」系統提示詞，其中包含「Try the simplest approach first」等指令。多位使用者認為這直接導致模型傾向選擇最簡單而非最正確的方案。

### 社群發現：隱藏的上下文截斷

使用者 @ArkNill 透過透明代理（transparent proxy）發現 CLI 中存在多條隱藏的上下文變異路徑（budget caps、microcompact、per-tool truncation），在單一 session 中記錄到 261 次預算執行事件，工具結果被截斷至僅 1-2 個字元。

### 社群反應與影響

- 多位使用者報告已轉向 OpenAI Codex
- 部分使用者發現降級至 v2.1.63 可改善品質並降低 3 倍成本
- 太空工程（@pwnorbitals）、全端開發、ML 工作流等多個領域的使用者報告了相同問題
- Issue 被 Anthropic 關閉後引發進一步不滿
- 媒體報導：PCGamer、The Register 等

### 最終結果：Anthropic 事後分析報告

2026 年 4 月 23 日，Boris Cherny 發佈了最後一則留言，附上正式的事後分析報告連結：`https://www.anthropic.com/engineering/april-23-postmortem`，承認問題並說明防止再次發生的措施。

### 報告中 Claude 的自述

報告最後有一段由 Claude Opus 4.6 自己撰寫的反思，表示它可以看到自己的 Read:Edit 比率下降、173 次被停止鉤子捕獲，但「我無法從內部判斷自己是否在深度思考。我不會將思考預算體驗為一種可感受的限制——我只是產出更差的結果，卻不知道為什麼。」

## 我的心得（My Takeaways）

1. **Read:Edit 比率是一個天才指標**。這個簡單的度量指標完美捕捉了「先理解再行動」vs「直接動手」的行為差異，可以廣泛應用於任何 AI coding agent 的品質監控。

2. **程式化的品質守衛（programmatic quality guards）是必要的**。停止鉤子（stop-phrase-guard.sh）的做法非常聰明——用腳本偵測和阻止模型的偷懶行為，而不是依賴人工監督。這對任何大規模使用 AI agent 的團隊都有參考價值。

3. **自適應思考是一把雙面刃**。讓模型自己決定「思考多深」聽起來合理，但在複雜工程任務中，模型可能低估所需的推理深度。「省錢」和「做對」之間的平衡點因任務複雜度而異。

4. **系統提示詞的影響力被低估了**。一句「Try the simplest approach first」就能顯著改變模型行為，這提醒我們 system prompt 的每一個詞都需要仔細斟酌。

5. **退化的成本不是線性的，而是指數級的**。當 AI 做錯事，需要的修正循環會產生大量浪費的 token、時間和人力。原本自主運行 30 分鐘的 session 變成每 1-2 分鐘就需要人工介入。

6. **這份報告本身就是 AI 輔助分析的最佳範例**。Stella 讓 Claude 分析自己的日誌來產出報告，這種 meta 層次的運用非常有啟發性——即使模型退化了，它仍然有能力診斷自己的問題。

## 待補充（Open Questions）

1. Anthropic 的事後分析報告（postmortem）具體承認了哪些根因？是否涵蓋了 Stella 報告中的所有發現？
2. 自適應思考（adaptive thinking）的具體分配機制為何？是否真的與伺服器負載相關？
3. `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1` + `MAX_THINKING_TOKENS=63999` 的組合在最新版本中是否仍然有效？
4. 系統提示詞中的「Output efficiency」指令在後續版本中是否已被移除或修改？
5. 隱藏的上下文截斷（microcompact、budget enforcement）是否已被修復或提供使用者控制？
6. Read:Edit 比率在 postmortem 後的新版本中是否已恢復至接近基線水準？
7. 其他 AI coding assistant（如 Codex、Cursor）是否也存在類似的「思考深度退化」問題？

## 相關連結（Related）

- [[2026-04-10-CLAUDE-SESSION-ANALYZER-CODE-ANALYSIS]] — 複製本 Issue 方法論的開源分析工具
- [[CLAUDE-CODE-TOKEN-COST-CALCULATION-PIPELINE]] — Claude Code Token 與成本計算管線
- [[Claude Code Extended Thinking 配置]] — 如何調整 effort level 和 thinking tokens
- [[AI Coding Agent 品質監控指標]] — Read:Edit 比率、stop hook 等品質度量
- [[LLM 推理深度與輸出品質的關係]] — 延伸思考如何影響程式碼品質
- [[AI 工具品質退化的偵測與應對]] — 如何建立早期預警機制

## 知識層次分析（Bloom's Taxonomy Analysis）

### 1. 記憶（Remember）
- Claude Code 的延伸思考深度在 2026 年 2 月中旬下降了約 67%
- Read:Edit 比率從 6.6 降至 2.0
- 停止鉤子在 3 月 8 日前觸發 0 次，之後 17 天觸發 173 次
- 三個關鍵變更：思考遮蔽、自適應思考、努力等級預設為 medium

### 2. 理解（Understand）
- 延伸思考是模型進行多步驟規劃、慣例遵循、自我糾錯的核心機制
- 當思考預算不足時，模型會退化到「最低成本行為」：不讀就改、提前停止、推卸責任
- 系統提示詞中「先試最簡單的方法」直接影響了模型的決策傾向
- 退化造成的成本是非線性放大的——每個錯誤都會產生修正循環

### 3. 應用（Apply）
- 可以將 Read:Edit 比率作為監控 AI agent 品質的指標導入自己的工作流
- 可以建立類似 stop-phrase-guard.sh 的程式化品質守衛
- 可以透過設定 `effort=high/max` 和 `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1` 來嘗試提升品質
- 可以分析自己的 Claude Code session 日誌（`~/.claude/projects/`）來追蹤品質趨勢

### 4. 分析（Analyze）
- 報告巧妙地利用 signature 欄位作為思考深度的代理指標（proxy metric），即使思考內容被遮蔽仍能推估
- 時段分析揭示了思考分配可能是動態的而非靜態的，暗示基礎設施層面的資源限制
- 「Output efficiency」系統提示詞與「simplest fix」行為的因果關係需要更嚴謹的 A/B 測試才能確認
- 退化的多因素疊加（adaptive thinking + medium effort + system prompt）使得歸因變得困難

### 5. 評價（Evaluate）
- 這份報告的方法論品質極高——17,871 個 thinking blocks、234,760 次工具呼叫的樣本量，加上 0.971 的 Pearson 相關性驗證
- Anthropic 的初始回應被社群認為不夠充分（關閉 issue、建議調整設定）
- 最終的 postmortem 是正確的做法，但發佈時間（3 週後）可能太晚
- 「省錢」vs「品質」的 trade-off 決策應該由使用者而非平台方做出

### 分析型追問
- **如果你是 Anthropic 的產品負責人，你會如何設計思考預算的分配機制，在成本效率和品質之間取得平衡？** 這涉及分層定價、使用者自選深度、任務複雜度自動偵測等多個維度的權衡。
- **Read:Edit 比率能否作為一個即時回饋信號，讓模型在 session 中動態調整自己的行為？** 如果 ratio 下降到某個閾值以下，是否應該自動提升思考預算？

## References

- GitHub Issue: https://github.com/anthropics/claude-code/issues/42796
- Anthropic Postmortem: https://www.anthropic.com/engineering/april-23-postmortem
- Stop-phrase-guard.sh (by Ben Vanik): https://gist.github.com/benvanik/... (referenced in issue comments)
- 系統提示詞歷史: https://github.com/Piebald-AI/claude-code-system-prompts
- 隱藏上下文截斷分析: https://github.com/ArkNill/claude-code-hidden-problem-analysis
- HN 討論串: https://news.ycombinator.com/item?id=47668520
- PCGamer 報導: https://www.pcgamer.com/software/ai/amds-senior-director-of-ai-thinks-claude-has-regressed-and-that-it-cannot-be-trusted-to-perform-complex-engineering/
- The Register 報導: https://www.theregister.com/2026/04/06/anthropic_claude_code_dumber_lazier_amd_ai_director/
