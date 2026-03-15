---
title: "Claude Memory Engine — Claude Code 的記憶學習系統"
date: 2026-03-16
category: AI
tags:
  - ai/claude-code
  - ai/memory
  - tools/hooks
  - productivity/learning-system
  - tools/claude
source: "https://github.com/HelloRuru/claude-memory-engine"
source_type: tool
author: "HelloRuru"
status: notes
links:
  - "[[CLAUDE-CODE-HOOKS]]"
  - "[[AI-AGENT-MEMORY]]"
  - "[[SECOND-BRAIN-WITH-AI-TOOLS]]"
  - "[[OBSIDIAN-POWER-TIPS]]"
---

## Summary

Claude Memory Engine 是一套用 hooks + markdown 打造的 Claude Code 記憶學習系統，完全不需要資料庫或外部 API。它解決了 Claude Code 最根本的問題：每次新對話都從零開始，之前花時間修的 bug、設定的偏好、踩過的坑全部消失。更特別的是，這個系統不只讓 Claude「記得」，而是讓它像學生一樣從錯誤中學習成長。

## Key Insights

- 記憶不等於學習 — 大多數記憶工具只是讓 AI 記住資訊，但這套系統透過「學生循環」讓 Claude 分析自己的錯誤、找出規律、不再犯同樣的錯，見 [[STUDENT-LOOP-LEARNING]]
- 三重保存點 — 不依賴單一時機：每 20 則訊息自動存、context 壓縮前存（最可靠）、對話結束後存，確保重要資訊不遺失
- Smart Context 自動切換 — 根據工作目錄自動載入對應的 project 記憶，切換專案不需手動設定，見 [[AI-CONTEXT-WINDOW]]
- 全透明設計 — 所有邏輯都是 .js 和 .md 檔案，沒有黑盒，想改什麼直接改
- 跨裝置同步 — 透過私人 GitHub repo 備份，換電腦跑 /recover 就還原所有記憶，見 [[GITHUB-BACKUP-STRATEGY]]
- 雙語指令 — 所有 36 個指令都有英文和繁體中文版本

## Details

### 核心架構：Student Loop（學生循環）

> [!note] 什麼是 Student Loop
> 把 Claude 當成期末考前猛K書的學生：每堂課做筆記（自動）、整理筆記找規律（手動 /reflect）、建立錯題本（/analyze）、考前複習（自動掃描錯題）。每個循環都比上一個聰明一點點。

自動執行（每次對話）：
- session-start hook → 載入上次摘要 + 當前 project 記憶 + 待接手任務
- 每 20 則訊息 → mid-session-checkpoint 存一個 checkpoint
- Context 壓縮前 → pre-compact 存快照 + 陷阱偵測 + 備份
- 對話結束 → session-end 存最終摘要（非必保證觸發）

手動執行（按需要）：

| 指令 | 中文 | 功能 |
|------|------|------|
| /reflect | /反思 | 回顧 7 天筆記，找出重複錯誤，升級成永久規則 |
| /analyze | /分析 | 你改了 AI 的輸出後立刻跑，比對兩版差異，建立錯題本 |
| /correct | /修正 | 隨時查看並複習錯題本，任務前自動掃描 |
| /save | /存記憶 | 手動儲存重要資訊到長期記憶 |
| /handoff | /交接 | 多視窗協作時，把當前進度傳給另一個 Claude 視窗 |

### 8 個 Hooks 說明

> [!tip] Hooks 是關鍵
> 這套系統的所有自動化都靠 Claude Code 的 hooks 機制。不需要手動輸入指令，hooks 在背景默默運行。

| Hook | 觸發時機 | 做什麼 |
|------|---------|--------|
| session-start | 新對話開始 | 載入上次摘要 + project 記憶 + 待接手任務 |
| session-end | 對話結束 | 存摘要 + 備份（盡力觸發） |
| pre-compact | Context 壓縮前 | 存快照 + 陷阱偵測 + 備份（最可靠的保存點） |
| memory-sync | 每則訊息發送時 | 偵測跨 session 記憶變化 + 新接手任務 |
| write-guard | 寫入檔案前 | 敏感檔案攔截警告 |
| pre-push-check | git push 前 | 安全檢查 |
| mid-session-checkpoint | 每 20 則訊息 | 存 checkpoint + mini 分析 |

### Token 成本

> [!warning] Token 注意事項
> 每次對話開始會多消耗 200–500 tokens（載入上次摘要 + project 記憶）。其他 hooks 幾乎不消耗額外 tokens。SKILL.md（136 行）只在相關對話中載入，不是每次都載。

### Correction Cycle（錯誤修正循環）

這是整套系統最創新的部分：

1. 你發現 AI 的輸出有問題，手動修正它
2. 立刻跑 /analyze → 系統比對你改前改後的版本，找出「已知規則沒遵守」和「新模式」
3. 下次任務開始前，自動掃描錯題本提醒 Claude
4. 同樣的錯犯 3 次以上 → 升級成永久規則

### 安裝步驟（5 步）

gh repo create claude-memory --private
git clone https://github.com/YOUR_USERNAME/claude-memory.git ~/.claude/claude-memory
cp hooks/*.js ~/.claude/scripts/hooks/
cp commands/*.md ~/.claude/commands/
cp -r skill/ ~/.claude/skills/learned/memory-engine/
mkdir -p ~/.claude/sessions/diary ~/.claude/scripts/hooks
# 設定 ~/.claude/settings.json 加入 hooks config（見 repo README）
# 重啟 Claude Code

需求：Claude Code（有 hooks 支援）、Node.js 18+、Zero dependencies

## My Takeaways

- 立刻要裝：這解決了每次開新對話都要重新解釋 context 的問題，完全透明可控
- /analyze 的習慣很重要：修完 AI 的輸出後立刻跑，才能讓錯題本真的有用
- pre-compact 才是真正的安全網：不要依賴 session-end（視窗關掉不一定觸發）
- 跟 Obsidian 整合：可以把 /diary 的輸出定期存入知識庫，建立「AI 協作日記」
- 自定義 PROTECTED_PATTERNS：把 .env、API keys 加入 write-guard 保護清單

## Related

- [[CLAUDE-CODE-HOOKS]] — 這套系統的底層機制，hooks 的原理和設定方式
- [[AI-AGENT-MEMORY]] — 更廣義的 AI 記憶架構，對比 vector DB vs markdown 方式
- [[SECOND-BRAIN-WITH-AI-TOOLS]] — Ali Abdaal 談 AI 工具建立第二大腦，理念相通
- [[OBSIDIAN-POWER-TIPS]] — Obsidian 知識圖譜技巧，可整合 Memory Engine 的日記輸出
- [[GITHUB-BACKUP-STRATEGY]] — 跨裝置同步的 GitHub repo 設定策略
- [[AI-CONTEXT-WINDOW]] — Context 壓縮問題是這套工具存在的根本原因
