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
> 每個 prompt 提供**英文版**（可直接貼入 ChatGPT / Claude 等工具）與**中文版**（適合中文 AI 工具或偏好中文指令的場景），並附中文說明用途與最佳場景。

---

### P-01：輸出契約（Output Contract）

**英文版：**
```
Return exactly these sections in this order:
1. [SECTION_A] — max 100 words
2. [SECTION_B] — as JSON
3. [SECTION_C] — one sentence conclusion

Do not repeat the user's request. Do not add sections not listed above.
```

**中文版：**
```
請按照以下順序，精確回傳這些區塊，不多也不少：
1. [區塊A] — 最多 100 字
2. [區塊B] — 以 JSON 格式呈現
3. [區塊C] — 一句話結論

不要重複使用者的問題。不要加入上方未列出的區塊。
```

**中文說明**：用於需要精確控制輸出格式的場景，例如撰寫報告、生成結構化資料。明確告訴模型「輸出什麼、多少量、什麼格式」，可大幅減少模型亂加東西的問題。

---

### P-02：預設執行策略（Default Follow-Through Policy）

**英文版：**
```
Follow-through policy:
- Proceed without asking if the action is reversible and intent is clear.
- Ask permission if the action is irreversible, has external side effects, or requires sensitive info I haven't provided.
- After proceeding, state what you've done and what remains optional.
```

**中文版：**
```
執行策略如下：
- 如果動作可以復原且意圖明確，直接執行，不需詢問確認。
- 如果動作不可逆、有外部副作用，或需要我尚未提供的敏感資訊，才詢問確認。
- 執行後，告訴我已完成什麼，以及哪些步驟是可選的。
```

**中文說明**：適用於代理人（agent）場景，避免模型一直詢問確認而中斷工作流程，同時保留對高風險動作的把關。

---

### P-03：工具持久性（Tool Persistence）

**英文版：**
```
Tool use policy:
- Use tools whenever they materially improve correctness or completeness.
- Don't stop early if additional tool calls would improve results.
- Keep calling tools until the task is complete and verification passes.
- If results are empty or partial, retry with a different strategy.
```

**中文版：**
```
工具使用策略：
- 只要工具能實質提升正確性或完整性，就使用工具。
- 如果繼續呼叫工具能改善結果，不要提前停止。
- 持續呼叫工具，直到任務完成且驗證通過為止。
- 如果結果為空或不完整，換一個策略重試。
```

**中文說明**：適用於代理人需要搜尋、查詢資料庫或執行多步驟工具鏈的場景，防止模型在工作未完成時就停下來。

---

### P-04：完整性契約（Completeness Contract）

**英文版：**
```
Completeness policy:
- Treat this task as incomplete until ALL requested items are covered.
- Maintain an internal checklist of deliverables.
- Track which items you've processed.
- Mark any blocked items explicitly with the missing information noted.
```

**中文版：**
```
完整性策略：
- 在所有請求項目都完成之前，視此任務為未完成。
- 維護一份內部待辦清單，追蹤所有應交付的項目。
- 記錄哪些項目已處理完畢。
- 對於受阻的項目，明確標記並說明缺少哪些資訊。
```

**中文說明**：適用於需要模型處理清單、批次資料或多份文件的場景，確保模型不會遺漏任何項目。

---

### P-05：驗證循環（Verification Loop）

**英文版：**
```
Before finalizing your answer:
1. Verify it meets all stated requirements.
2. Confirm factual claims have context or tool backing.
3. Check formatting matches the requested schema.
4. Confirm safety before actions with external effects.
```

**中文版：**
```
在給出最終答案前，請先完成以下驗證：
1. 確認答案符合所有明確的需求。
2. 確認所有事實主張都有上下文或工具支撐。
3. 確認格式符合請求的 schema。
4. 對於有外部影響的動作，確認安全後再執行。
```

**中文說明**：適用於高精度需求場景，例如財務報告、法律文件、程式碼審查。讓模型在給出最終答案前自我檢核。

---

### P-06：研究三步驟法（Research Three-Pass）

**英文版：**
```
Research this topic using a three-pass approach:

Pass 1 - Plan: List 3-6 sub-questions to answer.
Pass 2 - Retrieve: Search each question; follow 1-2 second-order leads.
Pass 3 - Synthesize: Resolve contradictions; write with inline citations.

Stop when additional searching is unlikely to change conclusions.
```

**中文版：**
```
請用三步驟法研究這個主題：

第一步 - 規劃：列出 3-6 個需要回答的子問題。
第二步 - 檢索：搜尋每個問題，並追蹤 1-2 個延伸線索。
第三步 - 合成：解決矛盾之處，附上引用來源撰寫結論。

當繼續搜尋不太可能改變結論時，停止搜尋。
```

**中文說明**：適用於需要深度調研的場景，例如技術評估、市場分析。讓模型系統性地規劃、搜尋並合成資訊，而非直接給出第一印象答案。

---

### P-07：程式碼任務持久性（Coding Task Persistence）

**英文版：**
```
Coding policy:
- Persist until the task is fully handled end-to-end unless I explicitly pause you.
- Don't stop at analysis; carry changes through to implementation and verification.
- Assume I want code changes unless I'm clearly planning or brainstorming.
- Send a progress update (~1-2 sentences) roughly every 30 seconds of work.
```

**中文版：**
```
程式碼任務策略：
- 持續工作直到任務端到端完成，除非我明確叫你暫停。
- 不要停在分析階段；把改動落實到實作和驗證。
- 預設我想要程式碼改動，除非我明顯在規劃或腦力激盪。
- 工作過程中每約 30 秒發送一次進度更新，1-2 句話即可。
```

**中文說明**：適用於請模型完成完整程式碼任務的場景，解決模型「說一堆但不動手寫」的問題，同時要求定期更新進度。

---

### P-08：結構化輸出合規（Structured Output Compliance）

**英文版：**
```
Output format: JSON only.
Rules:
- Return only valid JSON. No prose before or after.
- Validate balanced braces and brackets before output.
- Do not invent fields not in the schema.
- If a field's value is unknown, use null — do not omit the field.
```

**中文版：**
```
輸出格式：僅限 JSON。
規則：
- 只回傳合法的 JSON，前後不加任何說明文字。
- 輸出前確認所有大括號和中括號都正確閉合。
- 不要發明 schema 中沒有的欄位。
- 如果某欄位的值未知，用 null，不要省略該欄位。
```

**中文說明**：適用於 API 串接或解析場景，確保模型輸出可直接被程式解析，不夾帶多餘文字。

---

### P-09：引用鎖定（Citation Locking）

**英文版：**
```
Citation policy:
- Cite only sources retrieved in this session.
- Never fabricate citations, URLs, or quote spans.
- Use format: [Author, Year, "Title"] for academic; [Source Name](URL) for web.
- Base all claims exclusively on the provided context or tool outputs.
```

**中文版：**
```
引用策略：
- 只引用本次對話中實際查詢到的來源。
- 絕對不要偽造引用、URL 或引文片段。
- 學術格式使用：[作者, 年份, 「標題」]；網頁格式使用：[來源名稱](URL)。
- 所有主張必須完全基於提供的上下文或工具輸出。
```

**中文說明**：適用於研究報告、文獻回顧等需要可溯源引用的場景，防止模型「幻覺引用（hallucinated citations）」。

---

### P-10：進度更新規格（User Update Spec）

**英文版：**
```
Progress update rules:
- Send updates only when starting a new major phase or when plans change.
- Each update: 1 sentence on outcome + 1 sentence on next step.
- Do not narrate routine tool calls.
- Keep updates brief; keep internal work exhaustive.
- Vary sentence structure to avoid repetition.
```

**中文版：**
```
進度更新規則：
- 只在開始新的重要階段，或計畫改變時，才發送更新。
- 每次更新格式：1 句描述完成結果 + 1 句說明下一步。
- 不要報告例行性的工具呼叫。
- 更新訊息保持簡短；內部工作盡量詳盡。
- 變換句子結構，避免重複。
```

**中文說明**：適用於長時程代理人任務，讓使用者了解進度但不被無用的更新淹沒。定義更新的時機與格式。

---

### P-11：小型模型結構指令（Small Model Structural Prompt）

**英文版：**
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

**中文版：**
```
請依照以下順序執行步驟，每個步驟完全完成後再進行下一步。

步驟一：[動作 A] — 輸出格式：[格式]
步驟二：[動作 B] — 輸出格式：[格式]
步驟三：[動作 C] — 輸出格式：[格式]

如果任何步驟的輸入有歧義，請採用以下處理方式：[預設行為 / 詢問使用者 / 跳過]。

以下是預期執行流程的範例：
輸入：[範例輸入]
輸出：[範例輸出]
```

**中文說明**：專為 GPT-5.4-mini 或其他較小模型設計，透過明確的步驟編號和範例，降低小型模型的歧義處理問題。

---

### P-12：專業備忘錄模式（Professional Memo Mode）

**英文版：**
```
Write in polished, professional memo style:
- Use exact names, dates, and entities when supported by records.
- Prefer precise conclusions over generic hedging.
- Tie uncertainty to specific missing facts or conflicting sources.
- Synthesize across documents rather than summarizing each independently.
```

**中文版：**
```
請以正式、專業的備忘錄風格撰寫：
- 有記錄支撐時，使用確切的姓名、日期和實體名稱。
- 偏好精確的結論，避免模糊的保守措辭。
- 將不確定性連結到具體缺少的事實或相互矛盾的來源。
- 跨文件進行合成分析，而不是逐份文件獨立摘要。
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

## 待補充（Open Questions）

- GPT-5.4 的「代理人工作流程穩健性（Agentic Workflow Robustness）」具體是如何測量的？官方有沒有公開的 agentic benchmark 數據（如 τ-bench、AgentBench）可以驗證這個主張？（建議搜尋：`GPT-5.4 agentic workflow benchmark tau-bench`）
- 「推理力度（Reasoning Effort）」的 none/low/medium/high/xhigh 等級，在 API 層面是如何實現的？是否對應到不同的 sampling temperature 或 chain-of-thought token 預算？（建議搜尋：`OpenAI reasoning effort API implementation mechanism`）
- 本文提到「Compaction 後保持 prompt 功能相同」，但 Compaction 的具體演算法為何？如何保證壓縮後不遺失關鍵指令（如輸出契約的格式約束）？（建議搜尋：`GPT-5.4 conversation compaction algorithm context preservation`）
- P-03「工具持久性（Tool Persistence）」規則在多工具並發場景下，如何防止工具呼叫的無限循環？有無官方建議的最大工具呼叫次數上限或超時機制？（建議搜尋：`OpenAI tool use infinite loop prevention max calls`）
- GPT-5.4-mini 的「更字面性解讀」特性，在中文提示詞場景下是否表現不同？本文的 prompt 模板是針對英文設計的，中文版本是否需要額外調整？（建議搜尋：`GPT-5.4-mini Chinese prompt literal interpretation`）
- 從 GPT-4o 遷移到 GPT-5.4 時，建議「先設推理力度為 none」——這個建議的背後假設是什麼？若任務原本依賴 GPT-4o 的隱式推理，直接設 none 是否會有品質退化風險？（建議搜尋：`GPT-4o to GPT-5.4 migration reasoning effort regression`）

## 相關連結（Related）

- [[PROMPT-ENGINEERING]] — OpenAI 的廣義提示工程策略
- [[AGENTIC-WORKFLOW]] — 代理人工作流程設計原則
- [[REASONING-EFFORT-TUNING]] — `reasoning_effort` 參數詳解
- [[OPENAI-GPT-MODELS]] — GPT 系列模型能力比較
- [[2026-03-25-ENGINEERS-FUTURE-MULTI-AGENT-ERA-STEVE-YEGGE]] — Steve Yegge 談多代理人時代的工程師角色
- [[2025-10-16-DESIGN-YOUR-SOCRATIC-AI-MENTOR-FRAMEWORK]] — 蘇格拉底式五維追問框架，與本文結構化提示詞設計的另一種提問導向實踐

## References

- [原文：GPT-5.4 Prompt Guidance](https://developers.openai.com/api/docs/guides/prompt-guidance)
- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
