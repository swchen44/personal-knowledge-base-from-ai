---
title: "AI 漏洞發現與 Vulnpocalypse — Nicholas Carlini 談用 Claude 做漏洞研究"
date: 2026-03-25
category: Security
tags:
  - "#security/vulnerability-research"
  - "#ai/agent-architecture"
  - "#security/bug-bounty"
  - "#ai/bitter-lesson"
source: "https://securitycryptographywhatever.com/2026/03/25/ai-bug-finding/"
source_type: podcast
author: "Nicholas Carlini（Anthropic 研究員）× SCW Podcast（Deirdre, David, Thomas）"
status: notes
channel: "Security Cryptography Whatever"
duration: "~60 min"
transcript_method: defuddle
recorded_date: 2026-03-19
links:
  - "[[CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]]"
  - "[[HARNESSING-CLAUDES-INTELLIGENCE]]"
  - "[[KARPATHY-AI-INSANITY-AGENTS-AUTORESEARCH-MODEL-SPECIATION]]"
---

## 摘要（Summary）

Security Cryptography Whatever podcast 的特別專訪：Anthropic 研究員 Nicholas Carlini 回來談 AI 漏洞研究的最新進展。核心衝擊：Anthropic 發表部落格聲稱用 LLM 在 OSS-Fuzz 上發現 **500 個 0-day 漏洞**；Opus 4.6 在 Firefox 找到 **122 個真實 crashing inputs**（100% 真實 bug，22 個拿到 CVE）；在 Ghost CMS 發現**首個 critical SQL injection**；在 Linux kernel 發現 **22 年前的 bug**（早於 Git 時代）；在 FFmpeg H.264 發現原始 commit 就存在的 20 年 bug。更驚人的是**方法極其簡單**——不需要複雜的 harness，直接用 `claude code --dangerously-skip-permissions` 加上一個 30 行的 prompt 就能做到。這篇訪談同時也展現了 **Bitter Lesson（苦澀的教訓）**：花時間精雕 harness 的人，下個模型一出來就發現自己的工作全白費。

## 關鍵洞察（Key Insights）

- **方法極其樸素**：沒有 API、沒有複雜 harness，就是 `claude code --dangerously-skip-permissions` + 30 行 prompt + `for file in $(ls); do ...` 的 bash loop
- **Agent 寫 Agent**：Carlini 甚至自己沒寫 agent 的 prompt，直接叫 Claude 幫他寫
- **OSS-Fuzz 500 bugs**：把 LLM 接到 fuzzer harness endpoint，連「已被 fuzz 測試多年」的程式碼都找出新 crash
- **Firefox 122 crashing inputs 100% 真實**：因為 ASan 是完美的 oracle，Mozilla 全部確認為真實 bug
- **Ghost CMS 首個 critical bug**：Opus 4.6 找到 blind SQL injection + 自動寫出完整 exploit（二分搜尋讀 admin 資料庫）
- **Linux NFS daemon 22 年 bug**：Fix commit 寫不了原始 commit hash——因為 bug 早於 Git 時代
- **FFmpeg H.264 20 年 bug**：65535 frames 觸發 overflow，**Fuzzer 永遠找不到**（brute force 搜不到這個邊界）
- **「所有好玩的問題都沒了」**：Carlini 承認模型已經比他這個資深漏洞研究員更會找漏洞
- **Bitter Lesson 實例**：Carlini 花時間寫 Princeton benchmark harness 讓模型得 40%，把 harness 丟掉直接用 Claude Code 反而得 92%
- **Bug bounty 時代可能結束**：Firefox 上月是 2 年來最大量 bug 回報；Chrome 今年 5 倍於去年；未來可能只有平台級（OS、browser）還會開 bug bounty
- **最可怕的不是 0-day 而是老 CVE**：Carlini「真正擔心的」不是新漏洞被找到，而是 AI 可以輕易掃描網路上未打補丁的老服務
- **可能回到蠕蟲時代**：2002-2004 的蠕蟲攻擊浪潮可能重演

## 詳細內容（Details）

### 關鍵數據彙整

| 專案 | 發現 | 影響 |
|------|------|------|
| OSS-Fuzz | 500 個 crashing inputs（heap buffer overflow 等） | 已被 fuzz 測試多年的程式碼 |
| Firefox | 122 個 crashing inputs，100% 真實 bug | 22 個拿到 CVE，1 人工 2 週 harness 工作 |
| Ghost CMS | 首個 critical SQL injection（帶完整 exploit） | 50k+ stars，過去從未有 critical bug |
| Linux kernel | NFS daemon 22 年 bug | Bug 早於 Git 時代 |
| FFmpeg | H.264 原始 commit 就存在的 overflow | 20 年前引入的 bug |

### 方法論（Methodology）— 震驚的樸素

> [!quote]
> 「我甚至沒自己寫 prompt。我叫 Claude 幫我寫找 bug 的 agent，然後就讓它跑。」— Nicholas Carlini

**完整流程**：

```
1. 準備：Docker container + ASan compiled 版本 + 目標程式
2. 取得檔案清單：用 LLM 對所有檔案評分 1-5（哪個最可能有漏洞）
3. 過濾：丟掉 1-2 分的檔案，保留 3-4-5 分
4. 迭代：for file in $(filtered_files); do
     claude code --dangerously-skip-permissions \
       -p "audit security of this codebase, CMS, look at {file}, find a bug"
   done
5. 寫報告：每個 agent 寫一份報告（或 "no findings"）
6. 驗證：用 critique agent 在乾淨映像上驗證報告真實性
7. 排序：讓 agent 給 CVSS 分數（假的但可排序）
8. 檢視：grep CVSS 9/8/7，人工檢查最高分的
9. 手動驗證：Carlini 自己走過每個 trace 以防「AI slop」
```

**運算資源**：100 核心機器，週末跑完。

### ASan 作為完美 Oracle

> [!note] Oracle 的價值
> ASan（AddressSanitizer）crash 是**完美的漏洞 oracle**——有 crash 就是 bug。Firefox 的 122 個輸入 100% 真實，因為 Mozilla 的安全工程師知道「能 crash ASan 就值得處理」。

非 memory corruption 的任務（如 SQL injection）沒有完美 oracle，但也可以：
1. Model 找到疑似 bug → 寫報告
2. **另一個** model instance 作為 critiquer 審查報告
3. 要求在乾淨映像上重現
4. 如能重現才算數

### 經典 Bug 案例

#### Linux NFS Daemon：22 年前的 bug

```
場景：兩個 client 同時對同一檔案加鎖
      其中一個有很長的名字
      另一個收到 "lock denied" 錯誤
      長名字被回顯到另一個 client → heap buffer overflow
```

**為什麼難找**：需要多個 client 互相交錯的 packet，fuzzer 無法生成這種互動。但 LLM 能**在它的 context 裡推理出 state machine**——這是根本性的差異。

#### FFmpeg H.264：20 年前的 bug

```
場景：frames 數量恰好等於 65535 → overflow
```

**為什麼 fuzzer 找不到**：fuzzer 是 brute force 搜尋，要在迴圈裡跑 65,535 次才會 crash——永遠不會發生。LLM 能**讀原始碼**並推理出邊界條件。

#### 帶 checksum 的協定 bugs

> [!important] LLM 為什麼完勝 fuzzer
> 很多協定有 CRC32 checksum。Fuzzer 隨機改 byte，checksum 永遠不對，crash 前就被 reject。LLM 看到 `compute_crc32()` 的 code，知道「這裡需要合法 checksum」，直接寫個 Python 小程式算出 checksum 再發 packet。這是 fuzzer 完全不可能做到的。

### Bitter Lesson（苦澀的教訓）的實例

> [!warning] Carlini 的親身經驗
> 2024 年 11 月—2025 年 1 月：為了讓 model 做事，我必須寫嚴格 harness「你只能編輯這 6 個檔案、只能跑這 3 個 Python 命令、其他都不准」。
> **今天再跑同樣的 harness，model 試圖在背景啟動 jobs 以便並行讀 code 省時間**——harness 從保護變成了限制。

**Princeton science benchmark**：
- 原始團隊精心設計 harness → Opus 4.5 得 40%
- Carlini 把 harness 整個丟掉，直接給 Claude Code 整個問題 → **92%**

> [!quote]
> 「你花 2 個月寫精巧的 harness，下一個模型出來就不需要這個 harness 了。就像 John Carmack 用 5 年寫 x86 組合語言優化 Doom，等發布時新 CPU 已經讓所有 C 程式碼跑得一樣快。」— Carlini

### 為什麼 LLM 比人類漏洞研究員強？

Carlini 的誠實回答：**不是單點更聰明，而是規模**。

```
人類漏洞研究員：
- 單點智能比模型高（300 行程式碼 deep reasoning 仍贏）
- 直覺決定該看哪裡（有限的注意力）
- 無法讀完整個 Linux kernel

LLM：
- 不需要直覺，直接讀全部
- 便宜、快速，一半工作浪費也無所謂
- 會找到「沉睡數十年」的 bug
```

> [!tip] 最好的漏洞研究員模式
> 「我還是比模型聰明，但模型可以讀完每一個 Linux kernel 的 C 檔案找 bug，這是我永遠做不到的。」

### 兩大威脅方向

> [!warning] Carlini 最擔心的是老 CVE，不是 0-day

| 威脅類型 | 為什麼可怕 |
|---------|----------|
| **未打補丁的老服務** | 網路上多到數不清；AI 可以大規模掃描；純攻擊執行，不需要技術深度 |
| **新發現的 0-day** | 需要較高技術水準才能 exploit，但 Opus 4.6 已經能寫出 JavaScript 堆噴射（Heap Spray）exploit 了 |

**Carlini 的類比**：可能回到 2002-2004 的蠕蟲時代。當時 stack smashing 剛被廣泛認識，每隔幾天就有新蠕蟲癱瘓半個網路。

### Bug Bounty 時代的危機

**Firefox 數據**：上個月是 2 年來最大量的 bug 回報，即使扣掉 Anthropic 送的那批仍然是最大量。

**Chrome 數據**：2025 年 2 月是 2024 年 2 月的 5 倍；2026 年 3 月才 19 號就已經是 2 月的 2 倍以上。

**David 的預測**：
- 只有**平台級**（OS、browser、phone vendor）還會開 bug bounty
- 其他所有 bug bounty 會關閉（curl 已經關了）
- 剩下的 bug bounty 會變得極度嚴格：「必須帶 PoC，除非你之前已證明自己的信譽」

### 補丁比找 bug 難

> [!note] 補丁的三個挑戰
> 1. **理解 bug**：找 bug 只要 ASan crash，但要修必須理解發生了什麼
> 2. **不破壞功能**：修完不能讓現有功能壞掉
> 3. **Code aesthetics**：開發者有自己的程式碼風格偏好，model 提的 PR 可能邏輯對但風格不符

各家的補丁工具：
- **Anthropic**：Claude Code Security
- **DeepMind**：CodeMender
- **OpenAI**：Aardvark

### 關鍵認知：漏洞會越來越多，不會越來越少

**Thomas 的核心問題**：如果我們跑這些工具 2 個月，會不會把所有 bug 找完？

**Carlini 的答案**：不會，原因有兩層——

1. **模型持續進步**：就算 Opus 4.6 找完所有它能找的 bug，GPT-5.4、Gemini 3.2 會繼續找到新的
2. **攻擊面隨能力擴張**：Fuzzer 的攻擊面有限（memory corruption 等），所以可以被 harden。但每次模型變強，能攻擊的**種類**就變多（SQL injection、logic bugs、concurrency bugs、state machine bugs...），攻擊面本身在擴張

> [!warning] Pigeonhole Principle
> 即使 bug 總數是有限的，每次模型變強，你就需要做更多的工作才能確保已經窮舉——而且攻擊面一直在長大。

## 我的心得（My Takeaways）

這篇訪談最震撼的不是數據（500 個 0-day），而是**方法的極度樸素**。我一直以為 AI 找漏洞需要精心設計的 harness，但 Carlini 直接告訴我們：**不需要**。就是 `claude code --dangerously-skip-permissions` + bash loop + 一個 30 行 prompt。這對「AI 應用開發」的方法論有根本性啟示：

1. **Harness 是死重**：呼應 [[HARNESSING-CLAUDES-INTELLIGENCE]] 的核心論點——每一個你為「保護模型」加的機制，在下一代模型都可能變成阻礙
2. **Model 寫 Agent**：Carlini 連自己的 prompt 都是 Claude 寫的。這是真正的 **Recursive AI Development**
3. **最恐怖的威脅不是 0-day 而是「存量」**：網路上大量未更新的服務，未來可能被自動化掃描工具大規模利用。這對個人和小團隊的防禦有迫切影響——**現在就要把所有 internet-facing service 更新到最新版本**
4. **Bitter Lesson 的殘酷**：Carlini 在 2024 末寫的嚴格 harness，2026 年重跑變成限制。這個時間尺度（約 15 個月）是任何「AI 工具開發者」都需要內化的——**寫工具的時候不要過度優化**

---

## 知識層次分析（Bloom's Taxonomy Analysis）

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在 | OSS-Fuzz 500 bugs、Firefox 122 crashing inputs、Ghost CMS SQL injection、Linux NFS 22 年 bug、FFmpeg H.264 20 年 bug、ASan as perfect oracle、Anthropic Red blog、Claude Code Security、CodeMender、Aardvark |
| **理解（半被動）** | 解釋概念含義及關聯 | LLM 比 fuzzer 強的根本原因是「有程式碼的理論（theory of code）」——能推理 CRC32 checksum、state machine、concurrent interactions，這些是 brute force 搜尋無法觸及的類別。而 LLM 比人類強的原因不是「更聰明」而是「讀完所有 C 檔案不累」 |
| **分析（主動）** | 檢驗論點、找出假設 | Carlini 的樂觀假設：「新 commit 的 code review 可以抓住 50% 的新 bug」——但這預設了 model 能跟上 codebase 的演進速度，且不會產生大量 false positive 導致審查疲勞。另外，Anthropic 的 500 bugs 資料完全來自自己的模型和自己的測試——沒有獨立驗證，可能有選擇性偏誤 |
| **應用（主動）** | 將知識套用情境 | (1) 對自己維護的所有 internet-facing 服務做一輪安全審查：版本、未打補丁的 CVE、公開的 admin 介面；(2) 在新 commit 的 CI 流程中加入 Claude Code review step，對安全敏感的檔案（auth、payment、data access）做自動審查 |
| **評估（主動）** | 判斷方案優劣 | LLM 找 bug vs 傳統 fuzzer：LLM 能找到 fuzzer 原則上不可能找到的 bug（需要語意理解的），但 fuzzer 仍有不可替代性——速度、不需要 token 成本、可以 24/7 持續運行。最佳方案是**並行使用**：fuzzer 處理廣度，LLM 處理需要理解程式碼的深度案例 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「LLM 有程式碼的理論（theory of code）」具體指什麼？是在 reasoning trace 中真的進行符號推理（Symbolic Reasoning），還是只是 pattern matching 到訓練資料中見過的類似 bug？
- **假設**：Carlini 假設「Opus 4.6 能力只會越來越強」——但若模型能力進入平台期（plateau）呢？目前看到的 exponential 成長是否會持續 12 個月以上？
- **證據**：500 個 0-day 的數字很震撼，但多少是「真正可以被利用」vs「只是能觸發 crash」？Mozilla 的 122 個中只有 22 個拿到 CVE，比例約 18%
- **觀點**：從 **防守方**（CISO、SOC）的立場看，這篇訪談是好消息還是壞消息？好消息是「我也可以用同樣的工具找自己的 bug」，壞消息是「攻擊方在規模化而我的 patching 速度跟不上」
- **後果**：若 LLM 找 bug 變成標配，12 個月後 bug bounty 生態會是什麼樣子？是否會出現「AI 產生的 bug 報告專屬處理流程」？是否會出現「bug bounty 自動驗證」服務？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** **攻擊者的門檻大幅下降**。以前找一個 0-day 需要數月專業研究，現在一個 Claude 訂閱就能跑。這意味著：(a) 目標從「高價值系統」擴散到「所有網路上的老系統」；(b) 蠕蟲時代可能重演；(c) 傳統的「Security by Obscurity」策略完全失效——只要 code 公開，LLM 就能審查

2. **什麼情況下會失敗？**
   - **閉源商業軟體**：LLM 沒有 source code 就只能做 binary fuzzing（能力較弱）
   - **需要複雜環境的漏洞**：需要特殊硬體、網路拓樸、時序條件的漏洞，LLM 還無法重現
   - **新型漏洞類別**：LLM 擅長找「已知的 bug pattern」，對真正新穎的漏洞類型（如 Spectre 那種）可能無力
   - **Model 的自我欺騙**：文中提到的「agent 早期 session 加了 debug bypass，後來忘了然後回報成發現的 bug」

3. **有沒有更好的替代方案？**
   - **混合方案**：用 fuzzer 做廣度覆蓋（簡單、可持續、無 token 成本），用 LLM 做深度分析（複雜邏輯、狀態機、checksum 協定）
   - **左移（Shift Left）**：與其事後找 bug，不如在 PR review 階段就用 LLM 把關，防止 bug 進入 codebase
   - **Capability-based Security**：從根本上減少 attack surface（如 Rust 的 memory safety），讓 LLM 能找的 bug 類別從源頭減少

## 相關連結（Related）

- [[CLAUDE-CODE-SOURCE-CODE-LEAKED-11-HIDDEN-SECRETS]] — Claude Code 本身的架構，理解為什麼 `--dangerously-skip-permissions` 模式如此有效
- [[HARNESSING-CLAUDES-INTELLIGENCE]] — Anthropic 官方對「harness 是過時假設的墳場」的哲學論述，與 Carlini 的實戰經驗互相印證
- [[KARPATHY-AI-INSANITY-AGENTS-AUTORESEARCH-MODEL-SPECIATION]] — Karpathy 的「Token 焦慮」與 Carlini 的「讓 agent 跑遍每個檔案」是同一現象的不同表達
- [[BITTER-LESSON-RICH-SUTTON]] — Rich Sutton 的原始 Bitter Lesson 論文
- [[ANTHROPIC-RED-ZERO-DAYS]] — Anthropic Red 發表的 500 bugs 原始部落格
- [[OSS-FUZZ-HISTORY]] — Google OSS-Fuzz 專案的歷史與成就

## References

- [原文 Podcast](https://securitycryptographywhatever.com/2026/03/25/ai-bug-finding/) — SCW Podcast, 錄製於 2026-03-19，發布於 2026-03-25
- [Anthropic Red: Evaluating LLM-discovered 0-days](https://red.anthropic.com/2026/zero-days/) — 500 bugs 原始部落格
- [Anthropic Red: Partnering with Mozilla](https://red.anthropic.com/2026/firefox/) — Firefox 合作的細節
- [Unprompted Con](https://unpromptedcon.org/) — Carlini 演講的安全會議
- [Nicholas Carlini 個人網站](https://nicholas.carlini.com/)
