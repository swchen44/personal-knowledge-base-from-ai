---
title: "別再亂裝 Skill！四組頂級 Agent Skill 才是生產力上限"
date: 2026-05-09
category: AI
tags:
  - "#ai/agent"
  - "#tools/skill"
  - "#productivity/workflows"
source: "https://www.youtube.com/watch?v=0BacrKhaRJI"
source_type: video
author: "Juang_42號搭車客（俊望）"
status: notes
channel: "Juang_42号搭车客"
duration: "12:32"
transcript_method: notebooklm
links:
  - "[[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]]"
  - "[[2026-04-08-7-RULES-FOR-CREATING-EFFECTIVE-CLAUDE-CODE-SKILL]]"
  - "[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]]"
---

## 摘要（Summary）

決定 AI Agent（人工智能代理）生產力上限的，不是用哪個 Agent 工具（如 Claude Code 或 Cursor），而是你的 **Skill 配置組合**。本影片作者俊望實測數十個 Agent，篩選出四組平台無關、實戰驗證的頂級 Skill：原能力擴展（Foundational Expansion）、工程化開發（Engineering Development）、前端設計（Frontend Design）、內容創作（Content Creation）。

---

## 關鍵洞察（Key Insights）

- **Skill 配置是天花板**：Agent 工具再強，Skill 沒對就是浪費，正確 Skill 組合才是決定輸出品質的核心變數 — 參見 [[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]
- **原能力是元技能**：Skill creator 和 f skills 是讓 AI「自我進化」的基礎，其他 Skill 建立在這兩個之上
- **TDD 讓 Agent 工程化**：Superpowers 把測試驅動開發（TDD）變成 Agent 的硬規則，第一遍就能寫到 80 分以上，省掉後期無數 debug
- **23 個專家角色**：JSack 把 YC 創業流程裡的多角色審計搬進 Agent，一人抵一支小團隊
- **UI 不再「一眼 AI」**：frontend design + UX Pro Max 讓 AI 生成的介面（Interface）從千篇一律變成有設計質感
- **內容生產到發布一體化**：寶玉老師的 Skill 組涵蓋封面、信息圖（Infographic）、格式轉換到一鍵跨平台發布

---

## 詳細內容（Details）

### 第一組：原能力擴展（Foundational Capability Expansion）

> [!note] 元技能定義
> 「原能力」不負責完成具體任務，而是專門擴展 Agent 的能力邊界，讓 AI 能夠自我進化。

#### Skill Creator（Anthropic 官方出品）

讓 AI 自動把工作流變成可複用的 Skill：

- **以前的做法**：手動研究複雜格式，費時費力
- **現在的做法**：用大白話描述流程，或直接把操作手冊丟給它
- **效果**：自動起草 + 測試，一分鐘寫出既標準又好用的 Skill
- **安裝建議**：直接全局安裝（global install），以便隨時調用

> [!tip] 使用方式
> 安裝完成後，在 Agent 裡選中 Skill Creator，輸入需求，一步步進行溝通即可。

#### f skills（Find Skills）

讓 AI 自動去外部尋找並安裝現成 Skill：

- **正確用法**：直接給它拍任務，不是普通搜尋插件（plugin）
- **運作邏輯**：發現自己不會 → 自動拆解關鍵字 → 去 skill.sh 平台找裝機量最大的 Skill → 一行命令安裝
- **組合效果**：Skill Creator 負責「自己造工具」，f skills 負責「去外面找現成的」，兩者配合大幅提升效率

---

### 第二組：工程化開發（Engineering Development）

解決代碼邏輯看似閉環、卻無法落地的問題。

#### Superpowers（Anthropic 官方）

把測試驅動開發（TDD）變成 Agent 必須遵守的硬規則：

> [!important] 核心機制：紅綠重構循環（Red-Green-Refactor Cycle）
> 1. **紅**：先寫一個必敗的測試，證明功能尚未實現
> 2. **綠**：寫最少量代碼讓測試通過
> 3. **重構（Refactor）**：優化代碼品質

**完整流程**：

```
需求磨合
    ↓
設計文件（Design Document）
    ↓
拆解小任務（每個都有驗證標準）
    ↓
子 Agent 自動執行 + 兩輪內部審計
  ├─ 第一輪：代碼實現 vs 需求對齊
  └─ 第二輪：代碼品質檢查
    ↓
人工確認是否合併代碼
```

**效益**：雖然多花一點時間，但第一遍就能寫到 80 分以上，省掉後期無數次 debug，長期更省成本。

#### JSack（YC 總裁 Gary 出品）

在 Agent 裡內置 23 個不同的專家角色（Expert Roles），從 CEO、設計師到發布工程師，透過斜槓命令直接調用：

| 命令 | 角色 | 用途 |
|------|------|------|
| `/office hours` | 嚴厲導師 | 動手前問六個尖銳問題，掐死不靠譜的假設 |
| `/CEO review` | CEO | 從高層視角審視計劃 |
| `/review` | 資深工程師 | 代碼覆核，盯著潛在隱患 |
| `/QA` | 真人測試員 | 打開瀏覽器點擊驗證，抓出真實 bug |
| `/SP` | 發布工程師 | 自動跑測試、推代碼（push code）、開 PR，一氣呵成 |

> [!tip] 實測效果
> Gary 統計，JSack 讓他的代碼產出提升了 **240 倍**，一個人能頂一支小團隊。

#### 前端大神 M 的 Skill（TypeScript 佈道者）

重點解決「人與 Agent 溝通對不齊」的問題：

> [!quote] 核心哲學
> 「寧可在前期多花幾分鐘對齊需求，也不要在後期花幾小時處理劣質代碼。」

| 命令 | 功能 |
|------|------|
| `/G me`（拷問模式） | 確保需求細節精確，防止理解偏差 |
| `/align` | 任務排序，確保優先處理核心問題 |
| `/prove` | 架構急救包，從全局視角審視代碼庫並給出重構建議 |

---

### 第三組：前端頁面設計（Frontend Design）

解決 AI 生成 UI 千篇一律、「一眼 AI」的問題。

#### frontend design（Anthropic 官方出品）

根據產品調性推敲質感：

- 更有質感的紋理（texture）
- 有呼吸感的佈局（layout）
- 讓 UI 從「一眼 AI」變成「純手工設計」感

#### UX Pro Max

相當於給 Agent 配了一個設計總監（Design Director）：

- **內置 160+ 個行業的深度設計規則**：金融、醫療等行業各有不同的安全感配色和避坑指南
- **可持久化的設計系統（Design System）**：生成後可複用，下次開發新專案直接套用
- **分工**：frontend design 負責「畫得出彩」，UX Pro Max 負責「做得專業」

---

### 第四組：內容創作（Content Creation）— 寶玉老師 Skill 組

涵蓋從高質量內容產出、格式轉換、排版到一鍵發布的全流程：

| Skill | 功能 |
|-------|------|
| **cover image Skill** | 五維控制系統（構圖、色調、渲染、排版、情緒），封面效果專業且不隨機 |
| **信息圖（Infographic）Skill** | 內置 21 種專業佈局（魚骨圖、漏斗圖、金字塔圖等），自動讀懂文案邏輯，產出出版級視覺成果 |
| **小紅書 image Skill** | 長文自動拆解為 1–10 張卡通風格輪播卡片 |
| **markdown to ml** | 解決微信公眾號（WeChat Official Account）等平台不支持 Markdown 的問題，自動處理代碼高亮、數學公式及外鏈轉換 |
| **翻譯 Skill** | 出版級模式，四步流程：分析 → 翻譯 → 校正 → 潤色，可指定讀者身份（如「資深開發者」）調整語氣 |
| **發布微信 / 微博命令** | 一鍵跨平台分發 |

---

## 我的心得（My Takeaways）

這部影片從「哪些 Skill 最值得裝」的實戰視角切入，提供了很好的分類框架。最有啟發的是兩點：

1. **原能力是乘數**：先裝好 Skill creator + f skills，後續所有 Skill 都更容易擴展，而不是一次性死配置。
2. **工程化 ≠ 慢**：Superpowers 的 TDD 看似嚴苛，但從第一遍就能寫到 80 分，整體節省大量後期 debug 時間，這是很反直覺但值得採納的工程思維。

---

## 待補充（Open Questions）

- JSack 的 23 個專家角色完整清單是什麼？每個角色的使用時機為何？（建議搜尋：JSack skill roles list）
- Superpowers 的兩輪內部審計是由同一個 Agent 執行，還是兩個不同的子 Agent？架構細節為何？（建議搜尋：Superpowers TDD skill internal audit）
- f skills 在 skill.sh 以外是否支援其他 Skill 來源？（建議搜尋：f skills skill registry）
- UX Pro Max 的 160+ 行業規則是手動維護還是動態更新的？（建議搜尋：UX Pro Max skill industry rules）
- 寶玉老師的翻譯 Skill 四步流程的「分析」步驟具體分析什麼維度？（建議搜尋：寶玉 翻譯 skill 出版級模式）

---

## 相關連結（Related）

- [[2026-03-25-THREE-AI-CODING-FRAMEWORKS-SUPERPOWERS-GSD-GSTACK]] — 本文中的 Superpowers 在此有更深入的框架比較
- [[2026-04-08-7-RULES-FOR-CREATING-EFFECTIVE-CLAUDE-CODE-SKILL]] — Skill 設計規則，與 Skill Creator 的使用方法互補
- [[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]] — Skill 評估框架，可用來驗證本文推薦的 Skill 是否適合自己場景
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — 釐清 Skill / Command / Subagent 三者邊界，有助於判斷何時用 Skill

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 四組 Skill 名稱：Skill creator、f skills、Superpowers、JSack、M 的 Skill、frontend design、UX Pro Max、寶玉老師 Skill 組；JSack 有 23 個專家角色；Gary 統計提升 240 倍 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | 這四組 Skill 構成「元技能 → 工程品質 → 視覺品質 → 內容分發」的完整生產鏈，前一組是後一組的前提；Skill creator 是「自造工具」，f skills 是「外購工具」，兩者互補 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維，看透策略底層邏輯 | 作者隱含的假設是「Skill 是平台無關的」，但不同 Agent（Claude Code、Cursor、Windsurf）對 Skill 格式的支援程度可能不同；JSack 的「240 倍」數據來自作者自身情境，缺乏泛化驗證 |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力，將理論轉為行動 | 1. 立即安裝 Skill creator + f skills，作為所有後續 Skill 的基礎；2. 在下一個工程任務中試用 Superpowers 的 TDD 流程，記錄 debug 時間節省量 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡，在不確定的情境中做出最佳選擇 | Superpowers 的 TDD 流程需要更長的前置時間，對於快速原型（rapid prototyping）場景可能不划算；JSack 的 23 個角色切換對新手可能門檻偏高，學習成本需納入評估 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「原能力」的定義邊界在哪裡？Skill creator 本身也是一個 Skill，它的「原能力」身份是否自我指涉（self-referential）？
- **假設**：本文論點成立的前提是「工作流足夠穩定，值得封裝成 Skill」。若工作流每週都在變，頻繁造 Skill 的邊際成本（marginal cost）是否大於收益？
- **證據**：JSack 「240 倍提升」的測量基準是什麼？是代碼行數、任務完成時間，還是 PR merge 數量？不同指標的意義差異很大。
- **觀點**：若站在反對者立場，可以說「裝越多 Skill，Agent 的 context window 負擔越重，反而降低每個 Skill 的執行品質」，如何回應這個批評？
- **後果**：若大量採用 UX Pro Max 的 160+ 行業規則，12 個月後是否會導致產出風格過於均質（homogenized），失去設計獨特性？

---

## References

- [YouTube 影片](https://www.youtube.com/watch?v=0BacrKhaRJI)
- [skill.sh 平台](https://skill.sh)（f skills 的 Skill 來源）
