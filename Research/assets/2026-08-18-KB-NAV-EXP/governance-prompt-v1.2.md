# 個人知識庫治理規範 v1.2（建立＋檢查雙用 Prompt）

> 用法：把本文貼給任何 agent。**建立模式**：新增筆記時逐條遵循 A–E。**稽核模式**：對整個知識庫執行 F 檢查清單並輸出違規報告。
> 依據：2026-08-18 kb-skill 實驗（30 篇×10 題×3 組，詳見實驗筆記）＋ Anthropic skill 最佳實踐＋ Corpus2Skill 論文＋ OKF v0.1。
> 數字條款分兩級：【硬】違反即報告；【軟】單次實測的參考值，可依情況調整。

## A. 命名層——檔名是第一檢索面（實驗證實的最大功臣）

1. 【硬】檔名格式：`YYYY-MM-DD-ALL-CAPS-WITH-HYPHENS.md`，日期為內容發布日。
2. 【硬】檔名必含：主題專名（工具名/人名/公司名）＋ 2–4 個內容關鍵詞；有代表性數字直接入檔名（如 `-8-METRICS-`、`-100PCT-`）。
3. 【軟】自測法：只看檔名，能否判斷「這篇在講什麼、找什麼時候該開它」？不能就重命名。
4. 【軟】關鍵詞取多樣化同義詞（英文專名＋功能詞），因為查詢者用詞未必與你相同——檔名的檢索力對「詞彙不重合的查詢」會急遽下降（紅隊攻擊 #1 的對策）。

## B. Frontmatter 層——OKF 部分對齊

5. 【硬】必填欄位：`title`（中文完整標題）、`type`（article|video|paper|code|conversation|book|podcast|tool）、`category`、`tags`（3–5 個巢狀標籤）、`source`、`date`、`status`。
6. 【硬】`type` 為 OKF v0.1 唯一必填欄位，本庫從缺者補上。
7. 已知差距（接受，不改）：wikilink `[[...]]` 非標準 markdown 連結、INDEX.md/LOG.md 用大寫——Obsidian 生態優先於 OKF 完全相容；若未來要接 OKF 工具鏈，先寫轉換器而非改庫。

## C. 內文顆粒度層

8. 【軟】單篇目標 150–300 行；超過 400 行考慮拆分，或把長參考資料抽成該篇附屬的 `assets/`／獨立筆記互連。
9. 【硬】以 `##`/`###` 標題分節，每節單一主題；標題必含該節關鍵詞（節＝grep 命中單位，約 128–512 tokens）。
10. 【硬】關鍵數字與結論放在節的首句（front-load），不埋在段落中間。
11. 【硬】雙向連結 ≥3；Open Questions 3–7 條附搜尋關鍵字。
12. 【硬】mermaid 圖表交付前跑 `validate-mermaid.sh`；label 內禁引號與 `&quot;`，`>` 用 `&gt;`。

## D. 索引層——路由品質決定覆蓋率上限

13. 【硬】每分類維護 `INDEX.md`，一筆記一行：`| [[檔名]] | 摘要 | 日期 |`。
14. 【硬】摘要**前 60 字元**必含該篇最強的獨有識別碼：具體數字、專名、獨門術語（例：「1% 預算、250 vs 1536 字元」而非「skill 機制分析」）——這是對抗「導航窄化效應」的唯一防線（實驗中 index 描述缺漏直接導致 gold 引用漏抓）。
15. 【硬】每次 ingest 同步三件事：INDEX 行、LOG 行、README Recent Notes 行（現行 kb-create 流程已涵蓋，不新增負擔）。

## E. 導航層——閾值觸發，不預先建樹

16. 【硬】現況不建 SKILL.md 導航樹。實驗證實：30 篇規模、描述式檔名健全時，導航樹對正確率零貢獻且事實型查詢多付約 4k tokens 導航稅。
17. 【硬】觸發建樹的條件（任一成立才動工）：
    - 單一分類筆記數 > 50 篇；
    - 出現檔名無法自我描述的內容型態（如大量截圖、代號專案）；
    - 實際觀察到 agent 查詢常態性全庫掃描（跨域題耗時失控）。
18. 觸發後的建樹規格：入口 `SKILL.md` description ≤250 字元、觸發關鍵詞前置 60 字元；第二層直接沿用各分類 INDEX.md；導航檔單檔 ≤2KB；寫入接地規則「答案必須出自筆記本文，不可只憑 index 摘要」。
19. 【軟】模型選擇：導航式問答可用低價模型（實驗：Sonnet 與 Fable 正確率同為 10/10，僅 +18% tokens）——樹的品質決定表現，不是導航者。

## F. 稽核檢查清單（稽核模式執行；全部可機器檢查）

```bash
# F1 檔名合規
find . -name "*.md" -not -path "*/assets/*" | grep -vE "/[0-9]{4}-[0-9]{2}-[0-9]{2}-[A-Z0-9-]+\.md$" | grep -v "INDEX\|LOG\|README"
# F2 frontmatter 必填（含 type）
for f in $(find . -name "20*.md"); do head -20 "$f" | grep -q "^type:" || echo "缺 type: $f"; done
# F3 行數超標
find . -name "20*.md" -exec awk 'END{if(NR>400) print NR, FILENAME}' {} \;
# F4 INDEX 同步：每個筆記檔都有對應 INDEX 行
# F5 wikilink 數：grep -c "\[\[" 每篇 ≥3
# F6 mermaid：validate-mermaid.sh 全庫
# F7 孤立筆記：無任何其他檔案 wikilink 指向它
```

- 【軟】健檢頻率：每 6–7 次 ingest 執行一次完整稽核（沿用知識庫既有慣例）；輸出格式：違規清單＋修復建議，不自動修改。

## G. Eval 層——防止規範過擬合（紅隊要求新增）

20. 【硬】新筆記入庫後，用**一個改寫查詢**驗證可檢索性：查詢不得使用檔名中的詞彙，改用口語同義說法（模擬真實提問）。找不到→回頭修檔名關鍵詞或 INDEX 摘要。
21. 【軟】每季抽 5 題歷史查詢重跑，監控三個 KPI：來源命中率、平均 tool 呼叫數、平均 tokens。命中率下滑＝索引劣化訊號。
22. 本規範的量化數字（4k 導航稅、50 篇閾值等）出自 n=1 實驗，每次觸發 E17 或季度 eval 時重新校準，不視為永久真理。

23. 【硬】（D 系列實驗新增）eval 題目必須是「KB 特有事實」——出題後先用無工具的先驗基線測一次，模型憑既有知識能答對的題目作廢換題（實測案例：Stanford 就業 20% 屬公開研究，模型先驗可答，不能作為檢索能力的證據）。
24. 【軟】嚴格實驗的隔離注意事項：subagent 為 context 隔離但**磁碟可及**（可讀 session transcript 與 MEMORY.md 索引會注入）；發表級實驗需 OS 層 sandbox，日常 eval 用「指示約束＋引用接地檢查」即可。
25. 【軟】（E0 實測）macOS 硬隔離配方：`sandbox-exec -p '(version 1)(allow default)(deny file-read* (subpath "<要隔離的路徑>"))' <指令>`——嚴格實驗時以此包裹 agent 執行，拒讀 `~/.claude/projects`（transcript）同時保留 corpus 讀取；Linux 環境用 bwrap 等效達成。
26. 【硬】（攻擊 #9，使用者發現）實驗產出隔離：答案檔、結果表、報告**絕不可與受測 corpus 同樹**——agent 的檔案列舉會「看見」它們，指示級禁令擋不住主動探索。作法：產出放平行目錄（如 kb-exp-out/），或以 sandbox-exec deny 該子樹；事後以 transcript 稽核驗證（grep 全部 subagent transcript 的 tool_use 輸入，確認零讀取）。
