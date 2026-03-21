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

## 相關連結（Related）

- [[CLAUDE-CODE-HOOKS]] — Claude Code Hooks 機制，本系統的基礎設施
- [[AI-AGENT-MEMORY]] — AI Agent 記憶系統的各種設計模式比較
- [[PERSONAL-KNOWLEDGE-BASE]] — 個人知識庫系統，與此工具在「知識持久化」目標上互補

---

## References

- [GitHub Repo](https://github.com/HelloRuru/claude-memory-engine)
- [繁體中文 README](https://github.com/HelloRuru/claude-memory-engine/blob/main/README.zh-TW.md)
