---
title: "三大 AI 編程框架深度拆解：Superpowers、GSD、gstack 做對了什麼？還能怎麼優化？"
date: 2026-03-25
category: AI
tags:
  - "#ai/agent"
  - "#ai/coding-framework"
  - "#ai/harness-engineering"
  - "#tools/cli"
source: "https://www.youtube.com/watch?v=Y9hR2M4FE4I"
source_type: video
author: "系统在建"
channel: "系统在建"
duration: "11:41"
transcript_method: youtube-transcript-api
status: notes
links:
  - "[[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]]"
  - "[[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
  - "[[2026-03-17-CLAWTEAM-AGENT-SWARM-INTELLIGENCE]]"
---

## 摘要（Summary）

AI 寫程式碼最大的痛點已不是「寫不出來」，而是**寫完之後我們心裡沒底**——沒有測試、安全問題、改起來比重寫還慢。社群的解法是用框架給 AI 加上約束。本影片拆解三大框架的原始碼：**Superpowers**（9 萬+ stars）約束「過程」、**GSD**（3.5 萬 stars）約束「環境」、**gstack**（2.6 萬 stars）約束「視角」。三者互補而非競爭，但跨框架整合存在技術瓶頸。影片還揭露了 gstack 在「構建階段」的結構性缺陷，以及 Karpathy 的 Auto Research 模式如何補上這個缺口。

## 關鍵洞察（Key Insights）

- **三個框架解決不同維度的問題**：Superpowers 約束過程、GSD 約束環境、gstack 約束視角 — 參見 [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]]
- **gstack 的構建階段是空白的**：規劃和審查做得很好，但構建時 Claude Code 回到默認模式，沒有 TDD、任務拆分或增量審查
- **上下文窗口（Context Window）用到 50% 以上品質開始下滑，70% 以上幻覺明顯增加** — 這是 GSD 存在的根本原因
- **Auto Research 循環模式**可能是「無人值守持續優化（Unattended Continuous Optimization）」的突破方向

## 詳細內容（Details）

### 一、三大框架的定位差異

```
              約束什麼？        核心假設
┌──────────┬─────────────┬──────────────────────────────────┐
│Superpowers│  過程（Process）│ AI 的問題不是能力不夠，是太散漫    │
│          │              │ 定好規矩，輸出就穩定              │
├──────────┼─────────────┼──────────────────────────────────┤
│  GSD     │  環境（Context）│ AI 的品質完全取決於上下文的乾淨度   │
│          │              │ 環境乾淨，輸出就穩定              │
├──────────┼─────────────┼──────────────────────────────────┤
│ gstack   │  視角（Perspective）│ AI 的品質取決於用什麼角色來思考    │
│          │              │ 用對視角，判斷品質就會好很多        │
└──────────┴─────────────┴──────────────────────────────────┘
```

### 二、Superpowers — 流程紀律系統

> [!note] 核心理念
> 像管理「寫程式很快但從不做測試的初級工程師」一樣管理 AI。

**開發流水線**：
1. **結構化需求對話（Structured Brainstorm）**：按模組展示設計，每部分需用戶確認才繼續
2. **詳細實施計劃（Implementation Plan）**：精確到每一步改哪個檔案、預期結果、驗證方式
3. **強制測試驅動開發（TDD）**：實現時必須同步撰寫測試

### 三、GSD — 上下文工程系統

> [!warning] 上下文腐爛（Context Rot）
> 上下文窗口用到 50% 以上品質開始下滑，70% 以上幻覺明顯增加。專案越大、對話越長，問題越嚴重。

**解決方案：徹底隔離上下文**
- 把工作拆成**原子任務（Atomic Tasks）**
- 每個任務開一個全新的 Claude 實例（乾淨的 200K/1M 窗口）
- 主會話（Main Session）只做調度，負載保持在 30%–40%
- 所有專案狀態、需求、路線圖、進度**存成文字檔在磁碟上**，不依賴上下文記憶
- 新 session 可以讀回狀態，接續未完成的任務

### 四、gstack — 角色治理系統（五層設計）

gstack 定義了 **15 個角色**，每個角色對應一個特定命令：

| 角色 | 功能 |
|------|------|
| `office hours` | 挑戰產品方向（如：你要做日曆 App？也許你想做的是 AI 行政助理） |
| `plan engineer review` | 鎖定框架、畫數據流、列邊界情況 |
| `review` | 程式碼審核，小問題自行修復 |
| `QA` | 打開真實瀏覽器，以用戶視角找 Bug |
| `/ship` | 推程式碼、開 PR |
| 設計審查角色（×3） | 識別 AI 生成的千篇一律 UI，保證設計獨特性 |

> [!important] gstack 不是簡單的角色扮演，而是五層流程治理體系

**第一層：角色聚焦（Role Focus）**
- 以工程經理身份審查 → 自動忽略「顏色不好看」，專注框架和可維護性（Maintainability）
- 相當於給 AI 的注意力做一次聚焦

**第二層：數據編排（Data Orchestration）**
```
office hours → 設計文件
      │
      ▼
plan CEO review → 產品審核
      │
      ▼
plan engineer review → 鎖定框架/架構
      │
      ▼
review → 手握完整上下文（產品定位 + 架構決策 + 設計標準）
```

**第三層：品質管控（Quality Gate）**
- `/ship` 之前展示**審查就緒面板（Review Ready Panel）**：跑過哪些審查、缺了什麼、PR 是否通過對應審查

**第四層：決策偏好注入（Decision Bias Injection）**

> [!note] Boil the Lake（煮沸湖泊）哲學
> - **湖泊（Lake）** = 可以被煮沸的事：一個模組的測試覆蓋率做到 100%、所有邊界情況處理乾淨 → AI 做這些成本極低
> - **海洋（Ocean）** = 永遠煮不開的事：從頭寫一個完整系統、跨季度平台遷移 → AI 搞不定，不該讓它做
> - 策略：煮沸每一個湖泊，標記海洋為超出範圍（Out of Scope）

規劃時會展示兩個時間估計：
- 「這個功能人工做大概要兩週，Claude 做大概一小時」
- 然後問：「為了省幾分鐘跳過測試覆蓋率，你覺得值得嗎？」

**第五層：認知負載適配（Cognitive Load Adaptation）**
- 偵測到用戶開了 3 個以上會話時，自動進入 **ELI16 模式**（Explain Like I'm 16）
- 每次互動重新交代上下文，因為用戶可能正在多窗口切換

> [!tip] 這是唯一一個會主動適配人類工作狀態的 AI 編碼工具

### 五、gstack 的結構性缺陷：構建階段空白

gstack 的流程：**思考 → 規劃 → 構建 → 審查 → 測試 → 發布**

| 階段 | Skill 數量 | 備註 |
|------|-----------|------|
| 思考 + 規劃 | 5 | 充實 |
| 構建 | **0** | 空白！回到 Claude Code 默認模式 |
| 審查 | 3 | 充實 |
| 測試 | 2 | 充實 |
| 發布 | 2 | 充實 |

```
gstack 流程圖（含缺陷標示）：

 [思考] ──► [規劃] ──► [構建] ──► [審查] ──► [測試] ──► [發布]
   5個         ↑          ⚠️ 0個        3個        2個        2個
 skills    skills     無約束！     skills    skills    skills
                    ┌──────────┐
                    │ 沒有 TDD  │
                    │ 沒有拆分  │
                    │ 沒有增量  │
                    │ 審查      │
                    └──────────┘
          ← Superpowers/GSD 最擅長的領域 →
```

### 六、跨框架整合的技術瓶頸

理論上可以：gstack 做規劃和審查 + Superpowers 做構建。

但實際問題：Superpowers 在構建過程中會彈出**互動式問答（Interactive Prompts）**，此時 Claude Code 的輸入被卡住，就算用 Agent Teams，被卡住的會話也收不到其他 Agent 的消息。

### 七、Auto Research 模式 — 新的可能性

> [!info] 來自 Andrej Karpathy 的 auto-research 專案

**循環模式**：
```
  ┌──────────────────────────────────────┐
  │                                      │
  ▼                                      │
修改程式碼 → 跑實驗 → 測量指標 → 改善？ ──┤
                                   │     │
                                 是│   否│
                                   ▼     │
                                保留   重置
                                   │     │
                                   └──┬──┘
                                      │
                                  循環直到
                                  實驗次數用完
```

**兩個關鍵優勢**：
1. 單個 Agent 的緊密循環（Tight Loop），不需要多 Agent 通信，不存在卡住問題
2. 用**可量化的單一數字**做保留/丟棄決策，沒有模糊判斷

**應用到軟體工程**：想像一個 `optimize` skill —
- 自動修改程式碼 → 跑測試 → 測量覆蓋率/Lighthouse 分數/打包體積
- 指標漲了就提交，沒漲就重置循環
- 睡前啟動，早上起來指標就提升了

> [!warning] 開放問題
> ML 訓練的指標（loss）是天然的數字，但軟體工程的「程式碼品質」很難用一個數字完全代表。覆蓋率漲了，但新增測試可能是無用的斷言（Assertion）。

### 八、並行開發：Conductor 的替代方案

gstack 推薦用 Conductor 做並行開發（作者同時跑 10–15 個任務），但 Conductor 只支援 macOS/Linux。

**替代方案**：Claude Code 原生支援 `--worktree` 參數，開幾個 tmux 窗口就能達到一樣效果。影片作者已提交 Sprint skill PR 給 gstack。

## 我的心得（My Takeaways）

1. 三個框架的定位差異非常清楚：**過程（Superpowers）、環境（GSD）、視角（gstack）**，選框架前先想清楚你的痛點在哪
2. gstack 的 Boil the Lake 哲學很有啟發：AI 時代不該因為「夠用就好」而跳過測試，因為 AI 做這些邊際成本幾乎為零
3. Auto Research 的循環模式是「無人值守 CI」的雛形，值得在自己的專案中實驗
4. 上下文窗口 50%/70% 的品質拐點是一個很實用的經驗法則

## 待補充（Open Questions）

- 影片引用的「上下文窗口 50%/70% 品質拐點」數據從何而來？是有控制變因的 A/B 測試，還是工程師的主觀觀察？不同模型（Sonnet vs Opus）在這個拐點上是否有顯著差異？（建議搜尋：`context window quality degradation benchmark LLM`）
- gstack 的 15 個角色中，「設計審查角色×3」如何避免「千篇一律 UI」的問題？這類角色扮演提示（Role Prompting）對不同視覺風格任務的效果是否有評估數據？（建議搜尋：`gstack design review roles AI UI uniqueness evaluation`）
- Conductor（並行任務管理工具）只支援 macOS/Linux 的原因是什麼？有無 Windows 上可達到同等效果的替代工具？`claude -w` 在不同 shell 環境的相容性如何？（建議搜尋：`Conductor parallel AI tasks Windows alternative`）
- Superpowers 的「強制 TDD」機制是在 prompt 層面實施，還是有工具層面的強制執行（如攔截 commit）？若 Claude 跳過測試，框架有沒有偵測和回滾機制？（建議搜尋：`Superpowers AI coding framework TDD enforcement mechanism`）
- Auto Research 的「可量化單一指標」概念在軟體工程中的可行性有多高？當優化目標互相衝突時（如覆蓋率 vs 執行速度），循環如何決定「保留 vs 重置」？（建議搜尋：`auto research software optimization multi-objective metric`）
- GSD 的「原子任務（Atomic Tasks）」拆分策略是否有輔助工具自動建議拆分點？人工拆分在大型重構中是否本身就是瓶頸，且難以預先完整定義？（建議搜尋：`GSD atomic task decomposition AI coding workflow`）

## 相關連結（Related）

- [[2026-04-02-HARNESS-ENGINEERING-COMPLETE-GUIDE]] — 本影片討論的三個框架正是 Harness Engineering 的具體實踐
- [[2026-04-02-CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — Claude Code 內部的上下文壓縮與多代理機制，與 GSD 的設計思路相關
- [[2026-03-17-CLAWTEAM-AGENT-SWARM-INTELLIGENCE]] — 另一個多代理協作框架，可對比 gstack 的角色治理方式
- [[2026-04-04-GSTACK-SECURITY-TELEMETRY-CONTROVERSY]] — gstack 遙測爭議的深度分析，揭露治理跟不上成長的風險
- [[SUPERPOWERS-OBRA]] — Superpowers 框架的完整拆解，含可組合技能與子代理人審查模式的設計細節
- [[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]] — gstack 三層測試金字塔的程式碼分析，量化驗證 AI Agent 品質的方法
- [[2026-04-07-GSTACK-DESIGN-PHILOSOPHY-AND-INTEGRATION]] — gstack prompt-as-code 設計哲學的程式碼分析
- [[2026-04-07-GSTACK-TELEMETRY-ARCHITECTURE]] — gstack telemetry 子系統的程式碼分析

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，確立基礎知識 | Superpowers = 過程約束（TDD）；GSD = 上下文隔離（原子任務）；gstack = 角色治理（15 角色 / 5 層）；上下文窗口 50% 品質拐點；Boil the Lake vs Boil the Ocean |
| **理解（半被動）** | 解釋概念的含義及關聯 | 三個框架分別在 Harness 六層架構的不同層次發力：Superpowers 對應「執行編排」層，GSD 對應「信息邊界 + 記憶狀態」層，gstack 對應「評估觀測 + 約束恢復」層。它們的互補性來自各自填補了不同的架構空白 |
| **分析（主動）** | 檢驗論點、找出假設 | gstack 的 15 角色本質上仍依賴 Claude 能正確「角色扮演」的能力——但研究顯示角色提示的效果高度依賴模型和任務類型。此外，50%/70% 上下文品質拐點缺乏嚴謹的實驗數據佐證，可能因模型版本和任務複雜度而異 |
| **應用（主動）** | 將知識套用情境 | 1. 對現有 Agent 系統做「三維診斷」：過程紀律夠不夠？上下文乾不乾淨？視角是否對準？找出最弱的維度優先改進；2. 在 CLAUDE.md 中實驗 Boil the Lake 策略，對每個 PR 要求 AI 跑完測試覆蓋率才能 ship；3. 建立簡易 Auto Research 循環：寫一個 shell script 跑「修改→測試→量指標→決定」的循環 |
| **評估（主動）** | 判斷多個方案的優劣 | Superpowers 的 TDD 強制流程對探索性開發（Prototyping）可能過於沉重；GSD 的原子任務拆分增加了任務排程的額外開銷；gstack 的 15 角色可能在小專案中過度設計。選擇依據：個人/小專案用 Superpowers（輕量）；大專案長對話用 GSD（保鮮）；團隊協作/產品級用 gstack（治理）|

### 分析型追問（Socratic Follow-up）

- **澄清**：gstack 的「角色聚焦」和傳統 system prompt 中的角色設定有何本質區別？是否只是更精心設計的 prompt，還是有結構性差異？
- **假設**：GSD 假設「乾淨上下文 = 穩定輸出」，但如果任務本身需要大量跨模組的上下文（如大型重構），強制隔離是否反而損害品質？
- **證據**：50%/70% 上下文品質拐點的數據來源是什麼？是否有公開的基準測試（Benchmark）可以驗證？
- **觀點**：反對者可能認為框架增加的認知開銷和學習成本，對個人開發者而言得不償失——直接用好的 CLAUDE.md + 手動 prompt 可能更靈活
- **後果**：若團隊同時採用三個框架的互補方案（gstack 規劃 + Superpowers 構建 + GSD 環境），工具鏈的複雜度和維護成本會不會反過來成為新的瓶頸？

## References

- [原始影片 — 三大AI编程框架 - 做对了什么？还可以如何优化？](https://www.youtube.com/watch?v=Y9hR2M4FE4I)
