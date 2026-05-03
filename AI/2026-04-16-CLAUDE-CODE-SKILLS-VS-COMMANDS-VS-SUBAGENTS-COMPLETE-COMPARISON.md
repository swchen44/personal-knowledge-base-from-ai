---
title: "Claude Code 擴充機制完整比較：Skills vs Commands vs Subagents vs Plugins 最佳實踐與實驗數據"
date: 2026-04-16
category: AI
tags:
  - "#ai/claude-code"
  - "#ai/skill-design"
  - "#ai/agent-architecture"
  - "#ai/context-engineering"
  - "#tools/cli"
source: "conversation"
source_type: article
author: "swchen44 + Claude（綜合 Anthropic, Conneely, Villega, Trensee, Vercel 等多來源）"
status: notes
links:
  - "[[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]]"
  - "[[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]]"
  - "[[2026-01-27-VERCEL-AGENTS-MD-OUTPERFORMS-SKILLS-IN-AGENT-EVALS]]"
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
  - "[[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]]"
  - "[[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]]"
---

## 摘要（Summary）

綜合 Anthropic 官方文件、John Conneely（Young Leaders in Tech）、Pere Villega（Skills 2.0 深度分析）、Trensee（進階模式指南）與 Vercel（Agent Evals 實驗）等多來源，系統性比較 Claude Code 的四大擴充機制：**Skills、Commands、Subagents、Plugins**。核心發現：**Commands 已被官方合併進 Skills**（新開發應只用 Skills）；Skills 透過 `context: fork` 可部分取代 Subagents，但完整 Subagents（自訂系統提示 + 預載多 skills）仍有不可替代的價值；**Description 工程是 Skills 成敗的關鍵**——Conneely 的實驗證明 WHEN + WHEN NOT 模式從「完全失敗」變為「每次都觸發」；每個專案建議 **5-8 個 active skills**，超過此閾值 description budget 會飽和導致所有 skills 觸發率下降。

## 關鍵洞察（Key Insights）

- **Commands 已死，Skills 萬歲** — 官方已合併兩者，`.claude/commands/` 僅向後相容。Skills 比 Commands 多出：附屬資源目錄、YAML frontmatter 控制、自動觸發、`context: fork`、`paths` 路徑觸發 — 參見 [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]]
- **Skills + `context: fork` = 輕量級 Subagent** — 但完整 Subagents 仍需用於「自訂系統提示 + 預載多 skills + 獨立工具權限」的場景
- **Description 是觸發機制，不是摘要** — Conneely 實驗：generic description 完全失敗，WHEN + WHEN NOT 模式每次都成功觸發
- **每專案 5-8 個 active skills** — 超過此閾值 description budget（context window 的 ~1-2%）飽和，所有 skills 觸發率下降（Pere Villega 2026）
- **Subagent 精簡到 300 行以內** — Conneely 的瘦身實驗：1,285 行 → 587 行（54% 縮減），零功能損失，品質從 62 分提升到 82-85 分
- **被動上下文勝過按需檢索** — Vercel 實驗：AGENTS.md 100% vs Skills 預設 53%，通用知識應放 CLAUDE.md 而非 Skills — 參見 [[2026-01-27-VERCEL-AGENTS-MD-OUTPERFORMS-SKILLS-IN-AGENT-EVALS]]

## 詳細內容（Details）

### 第一章：四大擴充機制定位比較

根據 [Anthropic 官方](https://claude.com/blog/skills-explained) 與 [Conneely (2025-10)](https://www.youngleaders.tech/p/claude-skills-commands-subagents-plugins)：

| 機制 | 本質 | 觸發方式 | Context 隔離 | 適用場景 |
|------|------|---------|-------------|---------|
| **Skills** | 資料夾（SKILL.md + 附屬資源） | Claude 自動 or `/skill-name` 手動 | 可選（`context: fork`） | 可重用的知識/流程，跨對話可攜 |
| **Commands** | **已合併進 Skills** | `/command-name` 手動 | 無 | **已棄用**，舊檔案仍相容 |
| **Subagents** | `.claude/agents/*.md` | Claude 委派 or 明確指示 | **永遠隔離**（獨立 context window） | 需要獨立 context + 自訂系統提示 |
| **Plugins** | 打包發行單位 | 安裝後自動啟用 | 取決於內含的 skills/agents | 分享完整工具集給他人 |

Conneely 的決策心智模型（Mental Model）：

- **Skills**：「我希望 Claude 自動記住 X」
- **Subagents**：「我希望自動化 Y 的多步驟工作流」
- **Commands**：「我常用某個 subagent Z，想要一個快捷方式」→ 現在用 skill 的 `/name` 即可
- **Plugins**：「我想把我的設定分享給別人」

> [!important] 官方合併聲明
> `.claude/commands/deploy.md` 和 `.claude/skills/deploy/SKILL.md` 都會建立 `/deploy`，運作方式完全相同。**新開發應該只用 Skills**。Skills 比 Commands 額外支援：附屬資源目錄、frontmatter 控制（`disable-model-invocation`、`context: fork`、`paths`、`allowed-tools`）、模型自動觸發。

### 第二章：Skills 能否取代 Subagents？

**答案：部分可以，但不完全。** 兩者是互補而非替代關係。

#### Skills + `context: fork` = 輕量級 Subagent

根據 [官方文件](https://code.claude.com/docs/en/skills) 和 [Trensee (2026-03)](https://www.trensee.com/en/blog/explainer-claude-code-skills-fork-subagents-2026-03-31)：

```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork        # ← 在獨立 context 中執行
agent: Explore       # ← 使用 Explore 類型的 subagent
---
Research $ARGUMENTS thoroughly:
1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

這等效於一個 subagent，但用 skill 的方式定義和觸發。

#### 何時用 Skill、何時用 Subagent？

| 選擇 | 條件 | 理由 |
|------|------|------|
| **Skill（inline）** | 任務需要存取對話 context | 共享 context，能看到之前說的話 |
| **Skill + `context: fork`** | 任務獨立且不需對話歷史 | 隔離 context，避免污染主對話 |
| **Subagent（`.claude/agents/`）** | 需要自訂系統提示 + 多個 skill 預載 + 獨立工具權限 | 最大彈性：自訂人格、工具限制、預載 skills |

> [!note] 架構模式：Subagent 分析，Main Claude 執行
> Conneely 提出的 hybrid 模式：
> - **Subagents 工具**：Read, Grep, Glob, TodoWrite（唯讀分析）
> - **Main Claude 工具**：Write, Edit, Bash（修改執行）
> - 保持安全控制的同時實現自動化

#### Skills 與 Subagents 的雙向整合

根據 [官方文件](https://code.claude.com/docs/en/sub-agents)，兩者可以互相嵌入：

| 方向 | 系統提示 | 任務 | 額外載入 |
|------|---------|------|---------|
| **Skill → Subagent**（`context: fork`） | 來自 agent 類型（Explore, Plan 等） | SKILL.md 內容 | CLAUDE.md |
| **Subagent → Skill**（`skills` 欄位） | subagent 的 markdown body | Claude 的委派訊息 | 預載的 skills + CLAUDE.md |

### 第三章：Frontmatter 控制矩陣

Skills 的 YAML frontmatter 是最強大的控制機制：

| Frontmatter 欄位 | 功能 | 使用建議 |
|------------------|------|---------|
| `description` | Claude 自動觸發的匹配依據 | **最重要的欄位**，用 WHEN + WHEN NOT 模式 |
| `disable-model-invocation: true` | 禁止 Claude 自動觸發 | 有副作用的操作（deploy, commit, send） |
| `user-invocable: false` | 從 `/` 選單隱藏 | 背景知識，使用者不會直接執行 |
| `context: fork` | 在獨立 subagent 中執行 | 探索性任務、不需主對話 context |
| `agent: Explore/Plan` | 指定 fork 使用的 agent 類型 | 搭配 `context: fork` |
| `allowed-tools` | 授權工具白名單 | 限制 skill 只能讀取 or 只能執行特定指令 |
| `paths` | 路徑 glob 觸發條件 | 編輯特定目錄時才載入（Monorepo 必備） |
| `model` | 覆蓋使用的模型 | 簡單 skill 用 Haiku 省錢 |
| `effort` | 推理強度（low/medium/high/max） | 關鍵 skill 用 `max`（Opus 4.6 限定） |
| `hooks` | Skill 專屬的生命週期 hooks | 執行前/後的自動化檢查 |

> [!tip] Frontmatter 組合範例
> ```yaml
> # 部署 skill：手動觸發、限制工具、fork 執行
> ---
> name: deploy-check
> description: Pre-deployment validation
> disable-model-invocation: true
> context: fork
> allowed-tools: Bash(npm run *) Read Grep
> ---
> ```
>
> ```yaml
> # API 規範 skill：自動觸發、路徑限制、inline 執行
> ---
> name: api-conventions
> description: REST API design patterns. Auto-invoke when writing API endpoints or route handlers. Do NOT load for frontend or CSS work.
> paths: "src/api/**,src/routes/**"
> ---
> ```

### 第四章：Description 工程 — Skills 成敗的關鍵

#### Conneely 的實驗（2025-10）

> [!warning] 核心發現
> 「Generic descriptions failed completely. But when I structured descriptions with a WHEN + WHEN NOT pattern, the skills were being invoked each time.」

| Description 類型 | 範例 | 觸發率 |
|-----------------|------|--------|
| **Generic**（失敗） | `"API design conventions"` | ~0%（幾乎從不觸發） |
| **WHEN + WHEN NOT**（成功） | `"API design conventions for our REST services. Auto-invoke when writing API endpoints. Do NOT load for frontend."` | ~100%（每次都觸發） |

**有效 description 的結構：**

```
{做什麼} for {什麼情境}.
Auto-invoke when {WHEN 條件1}, {WHEN 條件2}.
Do NOT load for {WHEN NOT 條件1}, {WHEN NOT 條件2}.
```

**額外技巧：**
- 用所有格代名詞（HIS/HER/THEIR）防止跨 skill 污染
- 多個互補 skills 可以同時載入，不會衝突
- description 必須保持**單行**——多行 description 會靜默破壞 skill 可見性（Pere Villega 2026）

#### Pere Villega 的 Description Budget 警告（2026-04）

> [!warning] 5-8 個 Active Skills 是上限
> Description budget ≈ context window 的 1-2%。超過 8 個 active skills → 各 skill 的 description 被截斷 → Claude 缺少匹配關鍵字 → 觸發失敗。
> 
> 「Installing 5-8 active skills per project represents a reasonable threshold; beyond this, descriptions truncate and Claude loses matching keywords.」

每個 skill 的 `description` + `when_to_use` 合計上限 **1,536 字元**，且會被截斷。將關鍵使用場景放在 description 開頭（front-load the key use case）。

### 第五章：實驗數據總覽

#### 數據 1：Vercel Agent Evals（2026-01-27）

| 配置 | Pass Rate | vs 基線 |
|------|-----------|---------|
| 基線（無文件） | 53% | — |
| **Skills 預設** | **53%（+0pp）** | 56% 從未被調用 |
| Skills + 明確指示 | 79% | +26pp |
| **AGENTS.md 壓縮索引** | **100%** | +47pp |

**結論**：Skills 適合「流程性工作流」，不適合「通用知識檢索」。通用知識放 CLAUDE.md/AGENTS.md。

#### 數據 2：Conneely Subagent 瘦身實驗（2025-10）

| 元件 | 精簡前 | 精簡後 | 減少 |
|------|--------|--------|------|
| skill-creator-agent | 803 行 | 281 行 | 65% |
| skill-validator-agent | 698 行 | 306 行 | 56% |
| **合計** | **1,285 行** | **587 行** | **54%** |

評委評分：62/100 → 估計 82-85/100。**零功能損失**。

**主要問題：**
- 5 個重複的 TODO 結構 → 1 個可重用模式
- 130 行錯位的模板區塊 → 提取為獨立 skill 檔案
- 合併的驗證清單自我重複 → 精簡

#### 數據 3：Skills 2.0 Eval 框架（Pere Villega 2026-04）

- **A/B 測試**：用獨立評估 agent 做盲測比較
- **觸發優化**：自動重寫 description 並用樣本 prompt 測試
- **基準追蹤**：跨版本測量 pass rate、執行時間、token 消耗

> [!important] 測試 prompt 要求
> 測試 prompt 必須反映真實使用模式——包含錯字、縮寫、缺少 context、實際檔案路徑。抽象、完美的 prompt 會產生誤導結果。Vercel Labs 建議直接從 session 歷史複製真實 prompt。

### 第六章：Anthropic 官方比較矩陣

| 特性 | Skills | Prompts | Projects | Subagents | MCP |
|------|--------|---------|----------|-----------|-----|
| **持久性** | 跨對話 | 單次對話 | 專案內 | 跨 session | 持續 |
| **包含** | 指令 + 程式碼 + 資源 | 自然語言 | 文件 + context | 完整 agent 邏輯 | 工具定義 |
| **載入** | 動態，按需 | 每一輪 | 永遠在專案中 | 被調用時 | 永遠可用 |
| **程式碼能力** | 是 | 否 | 否 | 是 | 是 |

**官方分工原則：**
- **Skills vs Prompts**：重複的用 Skills，一次性的用 Prompts
- **Skills vs Subagents**：可攜式專業知識用 Skills，完整獨立任務用 Subagents
- **Skills + Subagents**：Subagents 可以存取和使用 Skills（如 Python 開發 subagent 使用 pandas-analysis skill）
- **Skills + MCP**：「MCP connects Claude to data; Skills teach Claude what to do with that data」

### 第七章：開發 Skills 的決策流程

```
你有一個重複執行的任務？
  │
  ├─ 否 → 直接用 prompt，不需要 skill
  │
  └─ 是 → 這個任務有副作用（寫入/部署/發送）？
        │
        ├─ 是 → disable-model-invocation: true（手動觸發）
        │       └─ 需要獨立 context？
        │           ├─ 是 → 加 context: fork
        │           └─ 否 → inline 執行
        │
        └─ 否 → Claude 應該自動判斷何時載入？
              │
              ├─ 是 → 寫好 WHEN/WHEN NOT description
              │       └─ 需要獨立 context？
              │           ├─ 是 → context: fork + agent: Explore
              │           └─ 否 → inline 執行
              │
              └─ 否（純背景知識）→ user-invocable: false
```

### 第八章：Trensee 四層 Harness 模型

[Trensee (2026-03)](https://www.trensee.com/en/blog/explainer-claude-code-skills-fork-subagents-2026-03-31) 建議的採用順序：

| 優先級 | 層 | 行動 |
|--------|-----|------|
| 1 | CLAUDE.md | 建立最小的硬約束檔（通用事實、規則） |
| 2 | Skills | 將 2 個最常重複的指令轉為 Skills |
| 3 | Hooks | 為 test/lint/policy 檢查加入 lifecycle gates |
| 4 | Fork/Subagents | 為混合意圖（Mixed-Intent）任務引入 context 隔離 |

> [!quote]
> 「If rules are unclear, automation only scales confusion.」

### 第九章：跨平台相容性

SKILL.md 遵循 [Agent Skills 開放標準](https://agentskills.io)，可跨工具使用：

- Claude Code
- Cursor
- OpenAI Codex CLI
- Gemini CLI
- GitHub Copilot
- 其他支援 Agent Skills 標準的工具

> [!tip] 可執行建議
> 用 symlink 讓同一份設定在多個工具間共享：
> ```bash
> ln -s CLAUDE.md agents.md
> ```
> Claude Code、Copilot、Cursor 都能讀取同一份設定——「one source of truth, no drift between tools」。

### 第十章：安全考量

> [!warning] Skills 可以執行任意腳本
> Skills 能執行任意 shell 命令和安裝套件。**第三方 skill 安裝前必須審查**。
> 
> 安全起點：Anthropic 官方 skills repo（github.com/anthropics/skills）。
> 
> 多個非官方市場（skills.sh, skillsmp.com, mcpmarket.com）品質控制最低限度。

## 我的心得（My Takeaways）

1. **Commands 已死** — 全面轉向 Skills，不要再建 `.claude/commands/` 了。
2. **`context: fork` 讓 Skills 吞噬了簡單 Subagents 的用途** — 但「自訂系統提示 + 預載多 skills」的完整 Subagents 仍不可替代。
3. **Description 工程 > SKILL.md 內容** — 56% 未觸發不是 skill 內容的問題，是 description 匹配失敗。投入 80% 的精力在 description 上。
4. **5-8 個 active skills 是甜蜜點** — 超過就開始互相干擾。不需要的 skill 加 `disable-model-invocation: true` 移出 description budget。
5. **「先建 eval 再建 skill」** — Pere Villega 的建議：用真實 session 歷史中的 prompt 測試觸發，而非精心構造的理想 prompt。

## 待補充（Open Questions）

- **`context: fork` 的 skill 與 `.claude/agents/` 的 subagent 在 token 消耗上有何差異？** 兩者都用獨立 context，但 skill fork 是否有額外的 SKILL.md 載入開銷？建議搜尋：`Claude Code context fork token consumption vs subagent overhead`
- **多個 `paths` 觸發條件重疊時的行為？** 如果 skill A 的 `paths: "src/**"` 和 skill B 的 `paths: "src/api/**"` 同時匹配，是否兩個都載入？description budget 如何分配？建議搜尋：`Claude Code skill paths overlap multiple trigger resolution`
- **Plugin 內的 skills 是否支援 `disable-model-invocation`？** GitHub Issue #22345 顯示 plugin skills 不支援此設定。這會導致 plugin 中的危險操作被 Claude 自動觸發。目前狀態？建議搜尋：`Claude Code plugin skill disable-model-invocation issue 22345`
- **Agent Teams（實驗性功能）與 Skills 的關係？** Agent Teams 需要 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 環境變數。它如何與 Skills 互動？team 中的 agent 能存取哪些 skills？建議搜尋：`Claude Code agent teams experimental skills interaction`
- **Capability Uplift Skills 何時會被基礎模型吸收？** Pere Villega 提出：隨著模型改進，教 Claude 新技能的 skills 可能變得多餘。如何偵測並移除已被模型內建的 skills？建議搜尋：`Claude Code skill capability uplift model improvement deprecation detection`

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | Commands 已合併進 Skills、5-8 active skills 上限、description budget = context window 的 1-2%、WHEN + WHEN NOT 模式、`context: fork` 讓 skill 在獨立 context 執行、Subagent 瘦身 54%（1,285→587 行）零功能損失、Vercel 實驗 Skills 預設 53% = 基線 |
| **理解（半被動）** | 解釋概念的含義及關聯 | 四大擴充機制形成一個「控制力 vs 自動化」的光譜：Prompts（最彈性、最短暫）→ Skills（自動觸發、可重用）→ Subagents（獨立 context、專門化）→ Plugins（打包分享）。Skills 的 frontmatter 是「旋鈕」——調整 `disable-model-invocation`、`context`、`paths` 就能在這個光譜上定位。「通用知識放 CLAUDE.md、流程放 Skills、獨立任務放 Subagents」是三層分工的核心邏輯。 |
| **分析（主動）** | 檢驗論點、拆解假設 | **Conneely 的 WHEN/WHEN NOT 實驗**缺乏控制組的量化數據——「完全失敗」vs「每次都成功」可能受任務類型影響。**Pere Villega 的 5-8 上限**缺乏不同 context window 大小（100K vs 200K vs 1M）下的差異數據。**Vercel 的 56% 未觸發**可能部分歸因於 skill description 品質而非機制問題——但 Vercel 有動機證明自家 AGENTS.md 方案更優。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | **立即可做：**（1）將現有 `.claude/commands/` 遷移到 `.claude/skills/`（2）為每個 skill 的 description 加上 WHEN + WHEN NOT 模式（3）審計 active skills 數量，超過 8 個的用 `disable-model-invocation: true` 降載（4）為有副作用的操作（deploy, commit）加上 `disable-model-invocation: true` + `allowed-tools` 限制 |
| **評估（主動）** | 判斷多個方案的優劣 | **Skills-only 架構**（全部用 skills + fork 取代 subagents）：簡單，但失去自訂系統提示和多 skill 預載的彈性。**Skills + Subagents 混合架構**：最大彈性，但維護兩套機制的認知負擔更高。**最佳折衷**：簡單的獨立任務用 skill + `context: fork`，複雜的多步驟工作流用完整 subagent，通用知識放 CLAUDE.md。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「Skills 自動觸發」的「自動」到底是什麼機制？是基於 embedding 相似度、關鍵字匹配、還是 LLM 推理？不同機制下，description 的最佳撰寫策略會有根本差異。
- **假設**：所有建議都假設 Skills 機制的行為在未來版本中保持穩定。但 Anthropic 從 Commands 到 Skills 的合併顯示這個系統仍在快速演化——12 個月後現在的 frontmatter 欄位是否還有效？
- **證據**：Conneely 的「54% 瘦身零功能損失」只有一個樣本（他自己的 skill-creator + validator）。這個比例在其他類型的 subagent（如 code-review、security-audit）上是否也成立？
- **觀點**：反對 Skills 統一論者可能說：「Skills 的 YAML frontmatter 已經有 12+ 個欄位，比起 Commands 的零配置簡單性，Skills 實際上增加了認知負擔。對小團隊來說，Commands 的直覺性更高。」
- **後果**：如果團隊全面採用 Skills 架構但不投資 description 工程和 eval 測試，12 個月後可能發現：skills 從未自動觸發，團隊成員都在用 `/skill-name` 手動觸發——此時 Skills 退化為更複雜的 Commands。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — Description budget 飽和是無聲的。不會有錯誤訊息告訴你「你的 skills 太多了」——只會觀察到 skills 停止自動觸發，而你不知道原因。這可能被誤診為「Skills 不好用」而非「Skills 太多」。
2. **什麼情況下會失敗？** — （1）Active skills > 8 且 description budget 飽和（2）description 使用多行格式（靜默破壞可見性）（3）Plugin 安裝引入大量你不知道的 skills，稀釋 budget（4）`context: fork` 的 skill 無法存取主對話 context，但任務實際需要前文資訊。
3. **有沒有更好的替代方案？** — 對於「需要按條件載入不同知識」的場景，CLAUDE.md 的 `@import` + 子目錄 CLAUDE.md 可能比 Skills 更可靠（100% 被讀取 vs 56% 未觸發）。權衡：佔用更多啟動 context 但可靠性更高。適合在「可靠性 > token 效率」的場景使用。

## 相關連結（Related）

- [[2026-03-19-CLAUDE-CODE-SKILLS-DOCUMENTATION]] — Claude Code Skills 官方文件完整筆記，本文的基礎架構定義來源
- [[2026-04-15-CLAUDE-MD-BEST-PRACTICES-EXPERT-GUIDE-SKILLS-VS-CLAUDEMD]] — CLAUDE.md 最佳實踐全攻略，Skills 與 CLAUDE.md 的分工策略
- [[2026-01-27-VERCEL-AGENTS-MD-OUTPERFORMS-SKILLS-IN-AGENT-EVALS]] — Vercel 原始實驗數據：Skills 53% vs AGENTS.md 100%，56% 未觸發
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — Skills 的 chokidar 熱載入機制原始碼分析
- [[2026-03-07-CLAUDE-SKILL-EVAL-FRAMEWORK-3-SKILLS-ONE-AFTERNOON-REAL-DATA]] — Skill 評估框架與 A/B 測試方法論
- [[2026-01-18-STOP-BLOATING-YOUR-CLAUDE-MD-PROGRESSIVE-DISCLOSURE-AI-CODING-TOOLS]] — Opalic 的漸進式揭露策略，Skills 的替代方案
- [[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]] — 10 步 Agent 建構框架，Subagent 設計的實戰指南
- [[2026-04-16-CLAUDE-CODE-SKILL-FRONTMATTER-FORK-AGENT-HOOKS-SOURCE-DEEP-DIVE]] — 本文提到的 context:fork 和 agent 欄位的原始碼級深度解析
- [[2026-04-25-CLAUDE-SKILLS-PLAYBOOK-DESCRIPTION-SUBAGENT-DEBUG-PROMPTS]] — Gary Chen 的 Description 三規則 + 三技術陷阱 + Subagent 品管完整架構，與本文的 Subagent 比較互補
- [[2026-04-29-CLAUDE-CODE-DISABLE-MODEL-INVOCATION-SKILL-VISIBILITY-SOURCE-ANALYSIS]] — Skill 可見性控制的原始碼級解析：getSkillToolCommands vs getSlashCommandToolSkills 過濾差異
- [[2026-04-08-7-RULES-FOR-CREATING-EFFECTIVE-CLAUDE-CODE-SKILL]] — Skill 內容撰寫的七條規則，補充本文著重的機制層比較

## References

- [Understanding Claude Code: Skills vs Commands vs Subagents vs Plugins — John Conneely (2025-10)](https://www.youngleaders.tech/p/claude-skills-commands-subagents-plugins)
- [Skills Explained: How Skills Compares to Prompts, Projects, MCP, and Subagents — Anthropic](https://claude.com/blog/skills-explained)
- [Claude Code Skills 2.0: What Changed, What Works — Pere Villega (2026-04)](https://perevillega.com/posts/2026-04-01-claude-code-skills-2-what-changed-what-works-what-to-watch-out-for/)
- [Claude Code Advanced Patterns: Skills, Fork, and Subagents — Trensee (2026-03)](https://www.trensee.com/en/blog/explainer-claude-code-skills-fork-subagents-2026-03-31)
- [Extend Claude with Skills — Anthropic 官方文件](https://code.claude.com/docs/en/skills)
- [Create Custom Subagents — Anthropic 官方文件](https://code.claude.com/docs/en/sub-agents)
- [AGENTS.md Outperforms Skills in Agent Evals — Jude Gao, Vercel (2026-01)](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)
