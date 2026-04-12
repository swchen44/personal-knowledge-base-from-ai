---
title: "Claude Memory Engine — 以 Hooks + Markdown 打造的 Claude Code 記憶與學習系統"
date: 2026-03-07
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#javascript"
  - "#ai/llm"
  - "#tools/cli"
  - "#ai/memory"
source: "https://github.com/HelloRuru/claude-memory-engine"
source_type: code
author: "HelloRuru"
status: notes
links:
  - "[[CLAUDE-CODE-HOOKS]]"
  - "[[AI-AGENT-MEMORY]]"
  - "[[PERSONAL-KNOWLEDGE-BASE]]"
github_stars: 98
github_language: JavaScript
---

## 摘要（Summary）

Claude Memory Engine 是一個用 Claude Code Hooks（鉤子）和 Markdown 檔案打造的**記憶與學習系統**。它讓 Claude Code 在每次對話結束後自動儲存工作摘要、偵測踩坑（pitfall）紀錄，並在下次對話開始時自動載入上次的脈絡——完全不依賴資料庫或外部 API，零依賴、透明可控。核心理念是讓 AI 像學生一樣從錯誤中學習，而不只是記憶。

---

## Why — 為什麼存在？

- **核心動機**：Claude Code 每次新對話都從零開始，無法記得上次修復的 bug、使用者偏好或專案規則
- **取代/改善什麼**：一般 memory 工具只能「記住」，無法「學習」；這套系統加入了踩坑偵測（pitfall detection）、反思迴圈（reflection loop）與錯誤筆記本（error notebook）
- **目標用戶**：重度使用 Claude Code 的開發者，尤其需要跨 session 保持上下文（context）、多視窗協作，或長期維護同一個專案者

---

## What — 是什麼？

- **主要功能**：
  - 自動儲存每次 session 摘要（三個觸發點：每 20 則訊息、壓縮前、session 結束）
  - 智慧脈絡（Smart Context）：根據工作目錄自動載入對應專案的記憶檔
  - 踩坑自動學習（Auto Learn）：偵測重複錯誤，建立錯誤筆記本
  - 反思迴圈（Student Loop）：8 步驟學習週期，手動執行 `/reflect` 整合知識
  - 跨裝置同步：透過私有 GitHub Repo 備份，新機器 `/recover` 即可還原
  - Session 交接（Handoff）：多視窗協作時傳遞工作狀態
  - 36 個雙語（英/繁中）指令檔
- **不做什麼（Non-goals）**：不提供向量搜尋（vector search）、語意相似度比對，或任何雲端 AI 服務整合
- **技術棧（Tech Stack）**：Node.js（JavaScript）、Claude Code Hooks、Markdown、GitHub CLI（可選）

---

## How — 如何運作？

> [!important] 本節包含 3 種 ASCII 圖表，讓讀者不看程式碼也能快速理解系統全貌。

### 系統架構圖（System Architecture）

```
┌─────────────────────────────────────────────────────────┐
│                  Claude Code 對話介面                    │
└──────────────┬──────────────────────────────────────────┘
               │  Hook 事件
               ▼
┌─────────────────────────────────────────────────────────┐
│                  Claude Memory Engine                    │
│                                                         │
│  ┌─────────────────┐    ┌──────────────────────────┐   │
│  │  session-start  │    │  mid-session-checkpoint  │   │
│  │  (context 注入) │    │  (每 20 則訊息存檔)       │   │
│  └────────┬────────┘    └──────────┬───────────────┘   │
│           │                        │                    │
│  ┌────────▼────────┐    ┌──────────▼───────────────┐   │
│  │  memory-sync   │    │      pre-compact         │   │
│  │  (跨 session   │    │  (壓縮前快照 + 踩坑偵測)   │   │
│  │   記憶同步)     │    └──────────┬───────────────┘   │
│  └─────────────────┘               │                   │
│                        ┌──────────▼───────────────┐   │
│  ┌─────────────────┐   │      session-end         │   │
│  │  write-guard   │   │  (session 摘要 + 備份)     │   │
│  │  pre-push-check│   └──────────────────────────┘   │
│  └─────────────────┘                                   │
└──────────────┬──────────────────────────────────────────┘
               │ 讀寫
               ▼
┌─────────────────────────────────────────────────────────┐
│                  本地 Markdown 儲存                      │
│  ~/.claude/sessions/     — session 摘要、compact 快照   │
│  ~/.claude/skills/learned/ — 踩坑自動學習紀錄            │
│  {project}/memory/       — 專案記憶檔、待辦、交接檔       │
└──────────────┬──────────────────────────────────────────┘
               │ Git Push（可選）
               ▼
┌─────────────────────────────────────────────────────────┐
│           私有 GitHub Repo（跨裝置備份）                  │
└─────────────────────────────────────────────────────────┘
```

### 執行流程圖（三重儲存安全網）

```
 對話開始（SessionStart）
      │
      ▼
 [session-start.js]
 ┌─────────────────────────────┐
 │ 1. 載入上次 session 摘要     │
 │ 2. Smart Context 載入專案記憶│
 │ 3. 踩坑紀錄提醒              │
 │ 4. Handoff 偵測             │
 └───────────────┬─────────────┘
                 │ stdout → 注入 Claude context
                 ▼
         對話進行中
          │        │
          ▼        ▼
  [每 20 則]  [每則訊息]
  checkpoint  memory-sync
  存檔        跨 session 同步偵測
          │
          ▼
   上下文快滿（PreCompact）← 最重要的安全點
          │
          ▼
 [pre-compact.js]
 ┌─────────────────────────────┐
 │ 1. 存壓縮前快照              │
 │ 2. 踩坑偵測（context 最完整）│
 │ 3. 自動備份至 GitHub         │
 └─────────────────────────────┘
          │
          ▼
   對話結束（SessionEnd，非必然觸發）
          │
          ▼
 [session-end.js]
 ┌─────────────────────────────┐
 │ 1. 存 session 摘要           │
 │ 2. 更新專案索引              │
 │ 3. 自動備份（best-effort）   │
 └─────────────────────────────┘
```

### 反思迴圈時序圖（/reflect Student Loop）

```
 使用者       /reflect 指令      Memory Engine
    │               │                 │
    │── /reflect ──►│                 │
    │               │── 讀過去 7 天 ──►│
    │               │◄── 摘要 + 踩坑 ──│
    │               │                 │
    │               │ [Review]        │
    │               │ 標記有用/過時   │
    │               │                 │
    │               │ [Refine]        │
    │               │ 4 題決策樹      │
    │               │ 保留/濃縮/規則化/刪除
    │               │                 │
    │               │ [Slim down]     │
    │◄──待確認刪除──│                 │
    │── 確認 ───────►│                 │
    │               │ [Wrap up]       │
    │◄── 學習報告 ──│                 │
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）
> 採用「鉤子驅動（Hook-driven）」架構，所有行為由 Claude Code 的生命週期事件觸發，而非依賴 Claude 自行記住要執行動作。這是關鍵——因為 Claude 可能忘記，但 Hook 不會。

1. **三重儲存點而非單一結束點**：不依賴 SessionEnd（可能不觸發），改用 mid-session-checkpoint + pre-compact 作為主要儲存點，大幅提升可靠性
2. **踩坑偵測移至 pre-compact**：在 context 最完整時偵測，比 session 結束後再回溯準確得多
3. **Markdown over Database**：所有記憶以 `.md` 儲存，Claude Code 原生就能讀取，且使用者可直接編輯、git 版本控管，完全透明
4. **shared-utils.js 重構**：將 `parseTranscript`、`detectPitfalls`、`autoBackup` 等共用函式抽出，消除約 80% 重複程式碼

### 踩坑偵測核心邏輯（Key Code Snippet）

```javascript
// shared-utils.js — detectPitfalls
const correctionKeywords = [
  'retry', 'again', 'wrong', 'error', 'failed', 'fix', 'broken',
  '不對', '錯了', '再試', '失敗', '修復', '又來了'
];

function detectPitfalls(parsed) {
  const pitfalls = [];
  for (let i = 0; i < parsed.userMessages.length - 1; i++) {
    const msg = parsed.userMessages[i].toLowerCase();
    if (correctionKeywords.some(kw => msg.includes(kw))) {
      pitfalls.push({ type: 'correction', description: parsed.userMessages[i] });
    }
  }
  return pitfalls;
}
```

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐⭐ | 純 JS + Markdown，8 個 hook 檔，邏輯清晰可自訂 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐ | Project Context、踩坑關鍵字均可自訂 |
| 測試覆蓋（Test Coverage） | ⭐⭐ | 無自動化測試 |
| 文件品質（Documentation） | ⭐⭐⭐⭐⭐ | README 詳盡，有繁中/日文版 |
| 依賴管理（Dependency Management） | ⭐⭐⭐⭐⭐ | 零外部依賴，只用 Node.js 內建模組 |

> [!tip] 值得學習的設計
> **三重儲存安全網**：不依賴任何單一觸發點，在 mid-session / pre-compact / session-end 三個時機各自備份。這種「降級容忍（graceful degradation）」設計值得在其他需要可靠性的系統中借鑑。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> - **問題一**：SessionEnd hook 在視窗直接關閉時可能不觸發 — 影響：最後一段工作可能未存檔
> - **問題二**：踩坑偵測使用簡單關鍵字比對，誤判率較高 — 影響：noise 較多
> - **問題三**：無自動清理機制，長期使用後記憶檔可能膨脹
> - **問題四**：跨裝置同步需手動執行 `/backup` — 影響：若忘記執行，換機後可能遺失最近記憶

### 🔮 改進建議（Improvement Suggestions）

1. 踩坑偵測加入語意分類（semantic clustering），降低誤判率
2. 加入定期自動 `/reflect` 提醒機制（如每 50 個 session）
3. 記憶容量警告：當 session 摘要超過一定數量時主動提醒整理

---

## 效能基準（Benchmark）

> [!info] 資料來源
> 來自官方 README 的 token 使用說明。

| Hook | 觸發時機 | Token 成本 |
|------|---------|-----------|
| session-start | 每次對話開始 | ~200–500 tokens |
| memory-sync | 每則訊息 | **0**（除非跨 session 有變更）|
| mid-session-checkpoint | 每則訊息 | **0**（除非是第 20 則）|
| write-guard / pre-push-check | 寫檔/push 前 | **0**（除非觸發）|
| session-end / pre-compact | 對話結束/壓縮前 | 不注入 context，無額外成本 |

**底線**：每次對話開頭多約 200–500 tokens，其餘幾乎為零。

---

## 快速上手（Quick Start）

```bash
# 1. 建立 GitHub 私有 Repo（跨裝置備份用）
gh repo create claude-memory --private
git clone https://github.com/YOUR_USERNAME/claude-memory.git ~/.claude/claude-memory

# 2. 複製 hooks 與 commands
git clone --depth=1 https://github.com/HelloRuru/claude-memory-engine /tmp/memory-engine
cp /tmp/memory-engine/hooks/*.js ~/.claude/scripts/hooks/
cp /tmp/memory-engine/commands/*.md ~/.claude/commands/
cp -r /tmp/memory-engine/skill/ ~/.claude/skills/learned/memory-engine/

# 3. 建立必要目錄
mkdir -p ~/.claude/sessions/diary ~/.claude/scripts/hooks

# 4. 在 ~/.claude/settings.json 加入 Hooks 設定（見 README）

# 5. 重啟 Claude Code — 完成！
```

---

## 我的心得（My Takeaways）

1. **Hook-driven 架構是關鍵洞察**：讓系統行為由生命週期事件驅動，而不依賴 AI 主動記得執行，這才是可靠的設計。可應用在任何「AI 應該自動做 X」的場景。
2. **降級容忍（Graceful Degradation）設計**：三重儲存點的概念——不依賴任何單一最佳時機，而是在多個次佳時機各自備份，整體可靠性反而更高。
3. **透明性勝過便利性**：選擇 Markdown + 本地檔案，放棄向量資料庫的語意搜尋，換來完全可控、可稽核的設計。對個人開發工具而言，這是正確的取捨。
4. **shared-utils.js 的重構時機**：從兩個 hook 抽出 80% 重複程式碼，這是典型的「DRY 重構時機」——當兩個以上地方有相同邏輯且需要同步修改時才抽象。

---

## 待補充（Open Questions）

- 踩坑偵測（pitfall detection）使用關鍵字比對（`retry`、`wrong`、`失敗` 等），這個方法的誤判率（false positive）在實際使用中有多高？社群是否有回報過哪些常見的誤判場景？（建議搜尋：`claude memory engine pitfall detection false positive accuracy`）
- `/reflect` 的 8 步驟學習週期需要手動執行，是否有方法設定自動觸發（例如每 X 次 session 後自動提醒）？或者與 claude-code-scheduler 搭配使用的配置範例？（建議搜尋：`claude memory engine reflect automation scheduler trigger`）
- 記憶檔案儲存在本地 Markdown，長期使用後（例如 6 個月、1,000+ session）檔案會膨脹到多大？對 SessionStart 注入的 ~200-500 tokens 成本有何影響？（建議搜尋：`claude memory engine scaling long term storage markdown growth`）
- 這個工具沒有自動化測試，若 Claude Code 官方更新了 Hooks 的 JSON schema 或新增了生命週期事件，系統是否會靜默失敗？如何監控升級相容性問題？（建議搜尋：`claude code hooks version compatibility breaking changes monitoring`）
- `write-guard` 和 `pre-push-check` 兩個防護 Hook 的具體攔截條件是什麼？與 `claude-code-hooks` 的 `protect-secrets.js` 相比，哪些場景各有優劣？（建議搜尋：`claude memory engine write-guard pre-push-check protection rules`）

## 相關連結（Related）

- [[CLAUDE-CODE-HOOKS]] — Claude Code Hooks 機制，本系統的基礎設施
- [[AI-AGENT-MEMORY]] — AI Agent 記憶系統的各種設計模式比較
- [[PERSONAL-KNOWLEDGE-BASE]] — 個人知識庫系統，與此工具在「知識持久化」目標上互補

---

## References

- [GitHub Repo](https://github.com/HelloRuru/claude-memory-engine)
- [繁體中文 README](https://github.com/HelloRuru/claude-memory-engine/blob/main/README.zh-TW.md)

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 三重儲存安全網（mid-session-checkpoint / pre-compact / session-end）；踩坑關鍵字偵測（detectPitfalls）；8 步驟反思迴圈（/reflect）；shared-utils.js 共用函式抽象；36 個雙語指令；Smart Context 智慧脈絡載入；零外部依賴；Hook-driven 架構 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | Claude Memory Engine 的核心洞察是「Hook 不會遺忘，AI 會」——將記憶系統的觸發交給生命週期 Hook 而非 Claude 自身決策，確保記憶行為的可靠性不受 LLM 隨機性影響。三重儲存安全網的設計哲學是「降級容忍（Graceful Degradation）」：不依賴任何單一最佳觸發點，在多個次佳時機各自備份，整體可靠性反而更高。Markdown over Database 的選擇犧牲語意搜尋換取透明度與可審計性。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維 | ①踩坑偵測假設「包含 retry/wrong/失敗等關鍵字的用戶訊息必然是在回應 AI 錯誤」，但這些關鍵字大量出現在正常的技術討論中（如「如何處理 retry 邏輯」），假陽性率可能很高；②三重儲存假設「pre-compact 時機是最完整的 context」，但 PreCompact hook 觸發時間不由使用者控制，可能在不合適的時機截取 context；③無自動化測試假設「hook 腳本邏輯足夠簡單不需要測試」，但若 Claude Code 官方更新 Hook JSON schema，靜默失敗難以察覺 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | ①安裝此工具作為個人 Claude Code 記憶系統的基礎，特別是用於長期維護的專案；②定期執行 `/reflect` 整合知識，防止記憶檔案無限膨脹；③借鑑三重儲存安全網設計，在自己的系統中實作多重備份而非依賴單一觸發點 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | Claude Memory Engine 在「簡單、透明、零依賴」上是最佳選擇，比 claude-mem 的安裝門檻低得多（無需 Bun / uv / Chroma）。然而它缺乏語意搜尋能力，記憶查詢完全依賴 Claude 在 context 中讀取 Markdown 文字，在記憶量大時效率下降。對於只需要「不忘記上次做了什麼」的個人開發者，此工具是比 claude-mem 更務實的選擇。 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：`session-start.js` 在 SessionStart 時注入 200-500 tokens 的記憶摘要，這個注入是通過 `additionalContext` 機制還是直接修改 system prompt？兩者在 Claude 處理優先級上是否有差異？
- **假設**：系統假設「使用者願意定期執行 `/reflect` 整理記憶」，但反思迴圈需要主動執行且耗時。實際使用中，有多少用戶真的建立了定期反思習慣，而非讓記憶檔案無限增長？
- **證據**：踩坑偵測（detectPitfalls）使用關鍵字比對，但沒有公開的準確率數據。在不同的開發場景（前端、後端、ML）中，誤判率是否差異顯著？是否有更好的替代指標（如連續修正同一行代碼）？
- **觀點**：從知識管理研究者的角度，「記住做了什麼」（過程記憶）和「理解為什麼這樣做」（概念記憶）是兩種不同的知識類型。Claude Memory Engine 主要捕捉前者，但 AI 輔助開發中「為什麼選擇這個架構」可能更有長期價值。系統是否有機制捕捉後者？
- **後果**：若 Claude Code 在某次更新後修改了 PreCompact hook 的觸發時機或 JSON 格式，而 Claude Memory Engine 未同步更新，會導致什麼？系統是否有版本相容性檢查機制？

### 方案批判三問（Critical Evaluation）

> [!warning] 適用於技術方案類內容

1. **最大的風險是什麼？** — 無自動化測試是最大的長期風險。Claude Memory Engine 依賴 Claude Code 的 Hook 系統，但 Hook 的 JSON 輸入/輸出格式、生命週期事件的觸發時機、以及 hook 腳本的執行環境都可能在 Claude Code 版本更新後改變。沒有自動化測試意味著這些變化只能在用戶實際遭遇問題後才被發現，而記憶系統的靜默失敗特別難以察覺——使用者可能數週後才意識到記憶一直沒有被儲存。
2. **什麼情況下會失敗？** — ①視窗直接關閉時 SessionEnd hook 可能不觸發，若 PreCompact 也未觸發（context 不夠長），整個 session 的工作記憶全部遺失；②長期使用後（1000+ sessions），session 摘要檔案累積到 MB 級別，SessionStart 的注入時間從 2-5 秒拉長，影響對話流暢度；③踩坑偵測的高假陽性率使錯誤筆記本充斥無關記錄，降低提醒的實際價值，使用者開始忽略錯誤筆記本
3. **有沒有更好的替代方案？** — ①若需要語意搜尋能力：claude-mem 提供 SQLite FTS5 + Chroma 的混合搜尋，代價是更高的安裝複雜度；②若需要結構化知識管理：直接維護 CLAUDE.md（手動，但完全可控）+ 定期用 Claude 整理成結構化文件；③若需要自動化測試：基於此 repo fork 並補充測試，或直接採用 claude-mem（有更完整的測試覆蓋）
