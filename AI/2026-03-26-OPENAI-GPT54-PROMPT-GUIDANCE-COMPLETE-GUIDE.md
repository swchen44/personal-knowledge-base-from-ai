---
title: "OpenAI GPT-5.4 提示詞指南（Prompt Guidance）完整翻譯與重點整理"
date: 2026-03-26
date_uncertain: true
category: AI
tags:
  - #ai/llm
  - #ai/prompt-engineering
  - #tools/openai
source: "https://developers.openai.com/api/docs/guides/prompt-guidance"
source_type: article
author: "OpenAI"
status: notes
links:
  - "[[PROMPT-ENGINEERING]]"
  - "[[OPENAI-GPT-MODELS]]"
  - "[[AGENTIC-WORKFLOW]]"
  - "[[REASONING-EFFORT-TUNING]]"
---

## 摘要（Summary）

本文為 OpenAI 官方 GPT-5.4 提示詞指南（Prompt Guidance）的完整中文翻譯與重點整理。GPT-5.4 是 OpenAI 最新主線模型，針對長任務執行（long-running tasks）、工具呼叫（tool use）和可靠執行（reliable execution）進行了最佳化，在多步驟推理（multi-step reasoning）與 token 效率之間取得了良好平衡。

本文最後整理了**實用 prompt 模板**，可直接套用至日常 AI 協作場景。

---

## 一、GPT-5.4 的核心優勢

GPT-5.4 在以下場景特別出色：

- **個性與語氣一致性（Personality and Tone Consistency）**：即使在長篇回覆中，也能維持穩定的風格
- **代理人工作流程穩健性（Agentic Workflow Robustness）**：提升任務完成率，減少中途放棄的情況
- **多工具場景的資訊合成（Evidence-rich Synthesis）**：在同時使用多個工具時，能整合資訊並給出有依據的結論
- **明確輸出契約下的指令遵從（Instruction Adherence）**：當你清楚定義輸出格式時，它能精確遵從
- **長上下文分析（Long-context Analysis）**：能處理複雜的大量輸入
- **批次或並行工具呼叫（Batched or Parallel Tool Calling）**：同時呼叫多個工具且保持準確性
- **財務與試算表工作流程（Finance and Spreadsheet Workflows）**：需要精確格式的場景

---

## 二、核心提示詞模式（Core Prompt Patterns）

### 2.1 輸出契約（Output Contract）

明確定義模型應該回傳什麼：

> [!important] 輸出契約原則
> - 按指定順序回傳確切的請求區塊
> - 長度限制只應用於其目標區塊
> - 需要時強制指定格式（JSON、Markdown、SQL、XML）
> - 避免不必要地重複使用者的請求

### 2.2 預設執行策略（Default Follow-Through Policy）

定義何時自主執行，何時需要確認：

> [!tip] 執行決策樹
> - **直接執行**：動作可逆（reversible）且意圖明確時
> - **詢問確認**：不可逆動作、有外部副作用（side effects）、或缺少關鍵敏感資訊時
> - **執行後告知**：說明已完成的事項和剩餘的選項

### 2.3 指令優先順序（Instruction Priority）

明確定義層級：

- 使用者指令優先於預設風格和格式
- 安全（safety）、隱私（privacy）和權限（permission）約束始終有效
- 較新的使用者指令優先於較早的衝突指令
- 較早的非衝突指令持續有效

### 2.4 工具持久性規則（Tool Persistence Rules）

針對依賴工具準確性的工作流程：

> [!note] 工具使用原則
> - 當工具能實質提升正確性或完整性時，一律使用工具
> - 若額外的工具呼叫能改善結果，不要提前停止
> - 持續呼叫工具直到任務完成且驗證通過
> - 若結果為空或不完整，用不同策略重試

### 2.5 完整性契約（Completeness Contract）

針對多步驟工作流程：

- 在所有請求項目都涵蓋之前，視任務為未完成
- 維護一份內部待辦清單（internal checklist）
- 追蹤清單或分頁結果中已處理的項目
- 明確標記受阻項目並注明缺少的資訊

### 2.6 驗證循環（Verification Loop）

在最終確認答案或執行高影響力動作前：

- 驗證是否符合所有需求
- 確保事實主張有上下文或工具支撐
- 確認格式符合請求的 schema
- 在有外部影響的動作前確認安全性

---

## 三、特定場景工作流程

### 3.1 視覺與電腦使用（Vision & Computer Use）

| 參數 | 使用情境 |
|------|---------|
| `detail: "high"` | 標準高保真度理解 |
| `detail: "original"` | 大型密集圖像或需要點擊精度的任務 |
| `detail: "low"` | 速度和成本優先於精度時 |

### 3.2 研究與引用（Research & Citations）

> [!warning] 引用鐵律
> - 只引用當前工作流程中檢索到的來源
> - 永遠不要偽造引用（citations）、URL 或引文
> - 使用應用程式要求的確切引用格式
> - 所有主張必須完全基於提供的上下文或工具輸出

### 3.3 程式碼任務（Coding Tasks）

程式碼生成的關鍵原則：

- **持續到底**：除非明確暫停，否則端到端處理任務到完成
- **不只是分析**：將分析結果落實到實作和驗證
- **預設寫程式碼**：除非使用者在規劃或腦力激盪，否則假設他們想要程式碼改動
- **進度更新**：工作中每約 30 秒發送一次進度更新，1-2 句話，避免元評論（meta-commentary）

### 3.4 研究模式（Research Mode）

使用三步驟法（three-pass approach）：

```
Step 1 - Plan（規劃）
   └─ 列出 3-6 個需要回答的子問題

Step 2 - Retrieve（檢索）
   └─ 搜尋每個問題並追蹤 1-2 個二階線索（second-order leads）

Step 3 - Synthesize（合成）
   └─ 解決矛盾並附引用撰寫結論
```

當繼續搜尋不太可能改變結論時停止。

### 3.5 結構化輸出（Structured Output）

針對解析敏感格式（parse-sensitive formats）：

- 只輸出請求的格式
- 除非被要求否則不加散文（prose）
- 驗證括號和方括號是否閉合平衡
- 不要發明 schema 中沒有的表格或欄位

---

## 四、推理力度調整（Reasoning Effort Tuning）

> [!important] 核心觀念
> 把推理（reasoning）當作最後一哩的微調旋鈕，而不是主要的品質驅動器。**先完善 prompt 結構，再增加推理力度。**

| 等級 | 適用場景 |
|------|---------|
| `none` | 快速、成本敏感、不需深度思考的任務 |
| `low` | 延遲敏感且需要適度精度提升的工作 |
| `medium` / `high` | 需要更強推理的任務；根據效能提升選擇 |
| `xhigh` | 保留給長時間、代理人式、推理密集的任務 |

**調整順序建議**（先用 prompt 結構，再調推理力度）：

1. 加入完整性契約（completeness contracts）
2. 加入驗證循環（verification loops）
3. 加入工具持久性規則（tool persistence rules）
4. 如果 prompt 仍然表現不佳，才增加推理力度

---

## 五、小型模型指南（Small Model Guidance）

### GPT-5.4-mini 的差異

- **更字面性的解讀（More Literal Interpretation）**：較少隱性假設
- **結構化任務表現佳**：對清楚結構化的任務表現強
- **可能會追問**：除非明確抑制，否則可能問後續問題
- **需要更明確的執行順序**：需要更清楚地指定工具使用的執行順序

### 小型模型的最佳實踐

- 將關鍵規則放在最前面
- 明確指定工具使用的完整執行順序
- 使用結構性框架（編號步驟、決策規則）
- 定義模糊行為：何時詢問、何時棄權、何時繼續
- 提供一個正確範例，展示預期的執行流程

---

## 六、個性與寫作控制（Personality & Writing Controls）

將持久個性（persistent personality）與每次回應的控制（per-response controls）分開：

**持久元素**（寫入系統提示）：
- 預設語氣（tone）、詳細程度（verbosity）和決策風格（decision style）

**每次回應元素**（在使用者訊息中指定）：
- 頻道（channel）：Slack、email、memo、blog
- 情感基調（emotional register）
- 格式限制（formatting constraints）
- 硬性長度限制（hard length limits）

> [!warning] 重要提醒
> 任務特定的輸出需求覆蓋個性設定。如果請求 JSON，就回傳 JSON。

---

## 七、從舊模型遷移

### 一次只改一件事

1. 先換模型
2. 固定推理力度到目前的設定
3. 執行評測（evals）
4. 根據結果迭代

### 不同前版模型的起始點

| 目前設定 | GPT-5.4 起始推理力度 | 備注 |
|---------|---------------------|------|
| GPT-5.2 | 對應推理力度 | 先保留現有延遲設定 |
| GPT-5.3-Codex | 對應推理力度 | 保持程式碼工作流程推理不變 |
| GPT-4.1 或 4o | `none` | 先維持快速回應行為 |
| 研究密集型 | `medium` 或 `high` | 加入明確的研究多步驟流程 |
| 長時程代理人 | `medium` 或 `high` | 加入工具持久性和完成追蹤 |

---

## 八、長時程會話管理

使用 Compaction 進行長對話（extended conversations）：

- 在重要里程碑後進行 compaction
- 將 compacted 項目視為不透明狀態（opaque state）
- Compaction 後保持 prompt 功能相同
- GPT-5.4 在較長的多輪對話中保持更高的連貫性

---

## 九、格式規則（Formatting Rules）

- **不要使用嵌套列表（nested bullets）**；保持列表扁平（單層）
- 編號列表使用 `1. 2. 3.` 格式加句點
- 如果需要層次，拆分為獨立的列表或區塊
- 指定散文（prose）時，明確禁止列表符號和標題

---

## 十、實用 Prompt 模板速查（Actionable Prompt Library）

> [!tip] 使用說明
> 以下 prompt 以英文呈現（供直接複製使用），每個 prompt 附中文說明其用途與最佳場景。

---

### P-01：輸出契約（Output Contract）

```
Return exactly these sections in this order:
1. [SECTION_A] — max 100 words
2. [SECTION_B] — as JSON
3. [SECTION_C] — one sentence conclusion

Do not repeat the user's request. Do not add sections not listed above.
```

**中文說明**：用於需要精確控制輸出格式的場景，例如撰寫報告、生成結構化資料。明確告訴模型「輸出什麼、多少量、什麼格式」，可大幅減少模型亂加東西的問題。

---

### P-02：預設執行策略（Default Follow-Through Policy）

```
Follow-through policy:
- Proceed without asking if the action is reversible and intent is clear.
- Ask permission if the action is irreversible, has external side effects, or requires sensitive info I haven't provided.
- After proceeding, state what you've done and what remains optional.
```

**中文說明**：適用於代理人（agent）場景，避免模型一直詢問確認而中斷工作流程，同時保留對高風險動作的把關。

---

### P-03：工具持久性（Tool Persistence）

```
Tool use policy:
- Use tools whenever they materially improve correctness or completeness.
- Don't stop early if additional tool calls would improve results.
- Keep calling tools until the task is complete and verification passes.
- If results are empty or partial, retry with a different strategy.
```

**中文說明**：適用於代理人需要搜尋、查詢資料庫或執行多步驟工具鏈的場景，防止模型在工作未完成時就停下來。

---

### P-04：完整性契約（Completeness Contract）

```
Completeness policy:
- Treat this task as incomplete until ALL requested items are covered.
- Maintain an internal checklist of deliverables.
- Track which items you've processed.
- Mark any blocked items explicitly with the missing information noted.
```

**中文說明**：適用於需要模型處理清單、批次資料或多份文件的場景，確保模型不會遺漏任何項目。

---

### P-05：驗證循環（Verification Loop）

```
Before finalizing your answer:
1. Verify it meets all stated requirements.
2. Confirm factual claims have context or tool backing.
3. Check formatting matches the requested schema.
4. Confirm safety before actions with external effects.
```

**中文說明**：適用於高精度需求場景，例如財務報告、法律文件、程式碼審查。讓模型在給出最終答案前自我檢核。

---

### P-06：研究三步驟法（Research Three-Pass）

```
Research this topic using a three-pass approach:

Pass 1 - Plan: List 3-6 sub-questions to answer.
Pass 2 - Retrieve: Search each question; follow 1-2 second-order leads.
Pass 3 - Synthesize: Resolve contradictions; write with inline citations.

Stop when additional searching is unlikely to change conclusions.
```

**中文說明**：適用於需要深度調研的場景，例如技術評估、市場分析。讓模型系統性地規劃、搜尋並合成資訊，而非直接給出第一印象答案。

---

### P-07：程式碼任務持久性（Coding Task Persistence）

```
Coding policy:
- Persist until the task is fully handled end-to-end unless I explicitly pause you.
- Don't stop at analysis; carry changes through to implementation and verification.
- Assume I want code changes unless I'm clearly planning or brainstorming.
- Send a progress update (~1-2 sentences) roughly every 30 seconds of work.
```

**中文說明**：適用於請模型完成完整程式碼任務的場景，解決模型「說一堆但不動手寫」的問題，同時要求定期更新進度。

---

### P-08：結構化輸出合規（Structured Output Compliance）

```
Output format: JSON only.
Rules:
- Return only valid JSON. No prose before or after.
- Validate balanced braces and brackets before output.
- Do not invent fields not in the schema.
- If a field's value is unknown, use null — do not omit the field.
```

**中文說明**：適用於 API 串接或解析場景，確保模型輸出可直接被程式解析，不夾帶多餘文字。

---

### P-09：引用鎖定（Citation Locking）

```
Citation policy:
- Cite only sources retrieved in this session.
- Never fabricate citations, URLs, or quote spans.
- Use format: [Author, Year, "Title"] for academic; [Source Name](URL) for web.
- Base all claims exclusively on the provided context or tool outputs.
```

**中文說明**：適用於研究報告、文獻回顧等需要可溯源引用的場景，防止模型「幻覺引用（hallucinated citations）」。

---

### P-10：進度更新規格（User Update Spec）

```
Progress update rules:
- Send updates only when starting a new major phase or when plans change.
- Each update: 1 sentence on outcome + 1 sentence on next step.
- Do not narrate routine tool calls.
- Keep updates brief; keep internal work exhaustive.
- Vary sentence structure to avoid repetition.
```

**中文說明**：適用於長時程代理人任務，讓使用者了解進度但不被無用的更新淹沒。定義更新的時機與格式。

---

### P-11：小型模型結構指令（Small Model Structural Prompt）

```
Execute the following steps in order. Complete each step fully before moving to the next.

Step 1: [Action A] — output: [format]
Step 2: [Action B] — output: [format]  
Step 3: [Action C] — output: [format]

If input is ambiguous at any step, use [default behavior / ask / abstain].

Here is an example of the expected flow:
Input: [example input]
Output: [example output]
```

**中文說明**：專為 GPT-5.4-mini 或其他較小模型設計，透過明確的步驟編號和範例，降低小型模型的歧義處理問題。

---

### P-12：專業備忘錄模式（Professional Memo Mode）

```
Write in polished, professional memo style:
- Use exact names, dates, and entities when supported by records.
- Prefer precise conclusions over generic hedging.
- Tie uncertainty to specific missing facts or conflicting sources.
- Synthesize across documents rather than summarizing each independently.
```

**中文說明**：適用於需要撰寫執行長摘要、法務備忘錄或高層報告的場景，讓模型輸出具有決策品質的文件，而非模糊的概括。

---

## 我的心得（My Takeaways）

這份指南最值得注意的是它把所有的「好 prompt 習慣」系統化了。過去我們靠直覺摸索的東西，現在有了官方的命名和結構：

1. **「輸出契約（Output Contract）」概念非常實用**——與其說「幫我寫一份報告」，不如說「按照以下順序回傳這些區塊，每塊有字數限制」。這能消除大量無謂的來回確認。

2. **「先加 prompt 結構，最後才調推理力度」**這個建議非常反直覺但有道理。很多人遇到模型表現差就直接去調參數，但問題往往出在 prompt 設計本身。

3. **研究三步驟法（Plan → Retrieve → Synthesize）**是個簡單但強大的框架，可以直接套用到任何需要調研的任務上。

4. **吸血鬼效應的解法之一**就藏在「進度更新規格（P-10）」裡——告訴模型不要報告每個小動作，只在重要里程碑更新，讓人類能專注在重要決策點而不是被資訊淹沒。

---

## 關鍵洞察（Key Insights）

- **輸出契約優先於個性設定**：任何格式要求都能覆蓋模型的預設行為——參見 [[PROMPT-ENGINEERING]]
- **推理力度是最後手段**：先完善 prompt 結構，才調整 `reasoning_effort` 參數——參見 [[REASONING-EFFORT-TUNING]]
- **工具持久性防止早退**：明確告訴模型「繼續呼叫工具直到完成」能顯著改善代理人任務品質——參見 [[AGENTIC-WORKFLOW]]
- **小模型需要更多鷹架（scaffolding）**：GPT-5.4-mini 需要明確的步驟順序和範例，不能靠隱性推論

---

## 相關連結（Related）

- [[PROMPT-ENGINEERING]] — OpenAI 的廣義提示工程策略
- [[AGENTIC-WORKFLOW]] — 代理人工作流程設計原則
- [[REASONING-EFFORT-TUNING]] — `reasoning_effort` 參數詳解
- [[OPENAI-GPT-MODELS]] — GPT 系列模型能力比較
- [[ENGINEERS-FUTURE-MULTI-AGENT-ERA-STEVE-YEGGE]] — Steve Yegge 談多代理人時代的工程師角色

## References

- [原文：GPT-5.4 Prompt Guidance](https://developers.openai.com/api/docs/guides/prompt-guidance)
- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
