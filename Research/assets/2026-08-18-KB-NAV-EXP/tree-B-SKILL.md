---
type: skill
name: kb-navigator
title: 個人知識庫導航
description: 查詢個人知識庫時使用——涵蓋 Claude Code/Codex 原始碼分析、AI agent/skill/CLAUDE.md 工程實踐、工程師職涯策略三大領域。先讀對應領域的 index，再開筆記本文作答。
tags: [knowledge-base, navigation, claude-code, ai-engineering, career]
timestamp: 2026-08-18T00:00:00Z
---

# 個人知識庫導航

本知識庫共 30 篇筆記，分三個領域。**回答任何問題前：先讀對應領域的 index 檔，從中挑出最相關的筆記，開啟筆記本文後才能作答。**

## 領域路由表

| 領域 | 何時查 | Index 檔 |
|------|--------|----------|
| 程式碼分析（CodeAnalysis） | Claude Code／Codex 內部機制：hook、telemetry、記憶系統、token 成本、plugin、skill 參數規格、gstack 架構 | `index/code-analysis.md` |
| AI 工程（AI） | skill 怎麼寫、CLAUDE.md 最佳實踐、AGENTS.md vs skills 實驗、agent harness、Karpathy 觀點、一人公司工具鏈 | `index/ai-engineering.md` |
| 職涯（Career） | 工程師職涯定位、AI 對就業的衝擊、升遷卡關、利害關係人、管理階層變化 | `index/career.md` |

## 導航規則

1. 依問題挑 1–2 個領域，讀其 index 檔（每筆含路徑與特徵詞）。
2. 開啟最相關筆記的**本文**；跨域問題要開多個領域的筆記。
3. **接地規則：答案中的每個事實必須出自筆記本文，不可只憑 index 摘要作答**；註明引用了哪些筆記檔名。
4. 快速定位可用 grep，例如：`grep -ril "telemetry" corpus/CodeAnalysis/`
