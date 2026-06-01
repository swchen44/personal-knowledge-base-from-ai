---
title: "SkillsBench — 第一個評測「Agent 用 skill 用得多好」的基準（程式碼深度分析）"
date: 2025-12-29
category: CodeAnalysis
tags:
  - code-analysis
  - ai/agent
  - ai/skills
  - ai/benchmark
  - tools/eval
source: "https://github.com/benchflow-ai/skillsbench"
source_type: code
author: "benchflow-ai（社群協作）"
status: notes
links:
  - "[[2026-05-22-SKILLOPT-SELF-EVOLVING-AGENT-SKILLS-CODE-ANALYSIS]]"
  - "[[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]]"
  - "[[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]]"
  - "[[2026-05-20-CODEX-HOOK-AND-SKILLS-PARAMETERS-DEEP-DIVE]]"
  - "[[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]]"
github_stars: 1279
github_language: Python
---

> [!info] 本筆記性質
> 分析本地 clone `~/git/skillsbench_play/skillsbench`（GitHub: `benchflow-ai/skillsbench`，Apache-2.0，1,279 stars，2025-12-29 建立）。所有數字取自實際檔案（README、CONTRIBUTING.md、task.toml、docs/skills-research）與 GitHub API。
> **與 [[2026-05-22-SKILLOPT-SELF-EVOLVING-AGENT-SKILLS-CODE-ANALYSIS|SkillOpt]] 的關係**：兩者同屬「agent skills」主題但**不同層**——SkillOpt 是**優化器（產生 skill）**，SkillsBench 是**評測基準（衡量 skill 使用）**，是 skill 生命週期的上下游。詳見最末「與 SkillOpt 的比較」。

## 摘要（Summary）

SkillsBench 自稱「**第一個評測 AI agent 使用 skill 能力的基準（the first benchmark for evaluating how well AI agents use skills）**」。它用 **gym-style** 的方式，把「skill（一包含說明、腳本、資源的模組化資料夾）」放進容器化任務環境，衡量兩件事：**skill 本身有沒有效**、以及 **agent 會不會用 skill**。專案由社群 `benchflow-ai` 維護，建立在自家 **BenchFlow SDK** 與 **Harbor 任務格式** 上，目前有 **94 個預設任務 + 5 個外掛任務**，橫跨軟體工程、辦公白領、自然科學、工業物理系統等 8 大領域。

## Why — 為什麼存在？

> Skill 在 2025–2026 爆炸成長，但「skill 到底有沒有用、agent 會不會用」一直沒有公正的量尺。

- **核心動機**：repo 的 `docs/skills-research` 點出三個研究問題（RQ）：
  - **RQ1**：skill 真的讓 agent 變強嗎？（effectiveness，需 benchmark 資料佐證）
  - **RQ2**：agent 能組合多個 skill 嗎？（composition，設計目標：3+ skill、SOTA <39%）
  - **RQ3**：skills 生態現況如何？（ecosystem——**已完成**：分析了 **47,153+ 個 skill、5,985 個 GitHub repo**）
- **取代/改善什麼**：把「skill 好不好用」從口耳相傳、各說各話，變成**可重現、可比較的分數**。
- **目標用戶**：想客觀評估 skill/agent 的研究者與廠商；想貢獻任務換取論文共同作者署名的社群（CONTRIBUTING 明訂：首發後合併 1 個任務即可掛名）。

## What — 是什麼？

> 一個任務集 + 一套跑分框架，產物是「分數 / 排行」。

- **主要功能**：
  - **94 個 + 5 個** 容器化任務（Harbor 格式），每個任務 = 指令 + 環境 + oracle 解答 + 測試
  - **gym-style 評測**：給 agent 一個任務與一組 skill，跑完看 outcome-based 測試是否通過
  - **可比有/無 skill**：同一任務在「有 skill vs 無 skill」下對照（直接對應 RQ1）
  - **跨 harness**：審計了 claude-code / opencode / openhands / codex / pi 五種 harness「如何向模型暴露 skill」（tool call vs prompt injection、frontmatter 辨識差異）
  - **skills 生態研究**：附完整資料集（categories、duplicates、embedding 去重、t-SNE 叢集）
- **不做什麼（Non-goals）**：
  - **不訓練、不優化 skill**——它只「評測」，不負責「把 skill 變好」（那是 SkillOpt 的工作）
  - 不自帶模型；跑 agent 需自備 API key（ANTHROPIC/OPENAI 等）
- **技術棧（Tech Stack）**：Python 3.12、`uv`（鎖定 `uv.lock` 求可重現）、**BenchFlow SDK**（pin 特定 commit）、Daytona sandbox、`skills-ref`（來自 `agentskills/agentskills`）。任務目標模型：Claude Opus 4.5、GPT-5.2、MiniMax M2.1、GLM-4.7。

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌───────────────────────────────────────────────────────────┐
│                     bench CLI (BenchFlow SDK)              │
│   bench tasks init / check  ·  bench eval create -a <agent>│
└───────────────────────────────┬───────────────────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │        Task (Harbor format)         │
              │  instruction.md  ·  task.toml       │
              │  environment/Dockerfile             │
              │  environment/skills/  (可選, 給 agent)│
              │  solution/solve.sh   (oracle, 須100%)│
              │  tests/test_outputs.py (outcome 測試)│
              └──────────────────┬──────────────────┘
                                 │ 在 Daytona sandbox 容器執行
              ┌──────────────────▼──────────────────┐
              │   Agent harness (claude-code/codex/  │
              │   openhands/opencode/pi)             │
              │   ── 讀 skills → 嘗試完成任務 ──      │
              └──────────────────┬──────────────────┘
                                 │ 產出 /root/answer.* 等
              ┌──────────────────▼──────────────────┐
              │   Verifier: pytest (test_outputs.py)│
              │   → CTRF JSON 報告 → 分數           │
              └─────────────────────────────────────┘
```

### 執行流程圖（Execution Flowchart）— 一個任務的評測

```
 Start
   │
   ▼
[bench eval create -t tasks/<id> -a <agent> -s <skills>]
   │
   ▼
[建 Docker 環境] ── environment/Dockerfile (+可選 environment/skills/)
   │
   ▼
[agent 讀 instruction.md + 可用 skills] ── 在 sandbox 內工作
   │
   ├─ 用對 skill ──► 產生正確 answer
   │
   └─ 沒用/用錯 skill ──► 產生錯誤或缺漏 answer
   │
   ▼
[tests/test_outputs.py 跑 pytest] ── outcome-based，不看過程看結果
   │
   ├─ oracle (solve.sh) 必須 100% 通過 ── 確保任務本身可解
   │
   ▼
[CTRF JSON 報告 → 分數 / pass-fail]
   │
   ▼
 End（彙整成模型×任務的成績）
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式：Gym-style + Outcome-based + Oracle-gated
> 1. **Outcome-based 測試**：只驗最終產物（如 `/root/answer.json` 內容對不對），不看 agent 中間怎麼做——比對「過程」更客觀、更難作弊。
> 2. **Oracle 必須 100% 通過**：每個任務都附一份 `solve.sh` 標準解，CI 強制它全過，**確保「任務有解、不是無理題」**——這是任務品質的硬門檻。
> 3. **難度刻意拉高**：設計目標是「需組合 2+ skill、SOTA <50%（RQ 文件甚至寫 3+ skill、<39%）」——故意讓最強模型也吃癟，才有鑑別度。
> 4. **可重現優先**：`uv.lock` 鎖死依賴、BenchFlow pin 特定 commit（README 明說 `rev="main"` 會「每次 lock 都偷偷漂移、跑到一半換掉 CLI」）——這是踩過坑後的工程紀律。
> 5. **skill 與任務解耦**：skill 放 `environment/skills/`，跑評測時用 `-s` 指定，所以**同一任務可測「給不同 skill」或「不給 skill」**，直接服務 RQ1。

### 任務結構（Harbor 格式，逐檔）

```
tasks/<task-id>/
├── instruction.md          # 給 agent 的任務指令
├── task.toml               # 元資料 + 資源/逾時設定
├── environment/
│   ├── Dockerfile          # 容器環境
│   └── skills/             # (可選) 提供給 agent 的 skill
│       └── <skill>/SKILL.md
├── solution/solve.sh       # oracle 標準解（CI 須 100% 通過）
└── tests/
    ├── test.sh             # 安裝 pytest 並執行
    └── test_outputs.py     # outcome-based 測試
```

### 關鍵程式碼（task.toml 範例，完整保留）

`tasks/citation-check/task.toml`——一個「驗證 BibTeX 引用是否造假」的任務：

```toml
version = "1.0"

[metadata]
author_name = "Xuandong Zhao"
difficulty = "medium"
category = "office-white-collar"
subcategory = "academic-bibliography-verification"
task_type = ["verification", "search"]
modality = ["document", "json"]
interface = ["terminal", "python"]
skill_type = ["domain-procedure", "tool-workflow"]
tags = ["citation", "bibtex", "academic", "verification", "api", "crossref", "semantic-scholar"]

[verifier]
timeout_sec = 900.0
[agent]
timeout_sec = 900.0
[environment]
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
allow_internet = true
```

對應的 `instruction.md`（節錄）要求 agent 找出假引用、寫進 `/root/answer.json`：

```
The BibTeX file is located at `/root/test.bib` ... identify which citations
are fake or hallucinated. Write your findings to `/root/answer.json`:
{ "fake_citations": ["Title of first fake paper", ...] }
```

## 安裝流程（Installation Flow）

### 安裝觸發方式

```
git clone + uv sync --locked   → 依鎖定檔安裝 skillsbench + BenchFlow SDK
bench tasks init <name>        → 產生新任務骨架
bench eval create -t ... -a oracle → 跑 oracle 驗證任務可解
```

### 安裝產物 / 環境變數

| 項目 | 值 | 說明 |
|------|-----|------|
| `bench` CLI | 來自 BenchFlow SDK | 任務管理與評測入口 |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` … | 環境變數 | 跑 agent 必填（建議用 `.envrc` + direnv） |
| `MODAL_TOKEN_ID/SECRET` | 環境變數 | 僅 GPU 訓練類任務（`mhc-layer-impl`、`diff-transformer_impl`）需要 |
| `tasks/` | 94 個預設任務 | 預設可跑 |
| `tasks-extra/` | 5 個任務 | 需憑證或整合不相容，要 `--no-default-excludes` 才納入 |

## 使用案例地圖（Use Case Map）

| # | 使用案例 | 觸發方式 | 入口 | 核心 |
|---|---------|---------|------|------|
| 1 | 跑一個任務評測 | `bench eval create -t tasks/<id> -a <agent> -s <skills>` | BenchFlow CLI | Dockerfile → agent → pytest → CTRF |
| 2 | 驗證任務本身可解 | `bench eval create -t tasks/<id> -a oracle` | `solution/solve.sh` | oracle 須 100% |
| 3 | 新增任務 | `bench tasks init <name>` | `.agents/skills/task-creator/` | 照 Harbor 格式填五個檔 |
| 4 | 有/無 skill 對照（RQ1） | 同任務跑兩次（給 `-s` vs 不給） | `environment/skills/` | 比較通過率差異 |

## 效能基準（Benchmark）— 它本身就是 benchmark

> [!info] 注意
> SkillsBench **自己就是量尺**，所以「benchmark 數字」指的是各模型在它上面的成績。本 repo（截至分析時）主要提供**任務集與框架**；正式跑分結果以官網 skillsbench.ai 與未來論文為準。設計目標是 **SOTA <50%**（RQ 文件寫 <39%），目標模型 Claude Opus 4.5 / GPT-5.2 / MiniMax M2.1 / GLM-4.7。

**任務領域分佈（94 個預設任務，依 `task.toml` category 統計）**

| 領域（category） | 任務數 |
|---|---|
| software-engineering | 17 |
| office-white-collar | 15 |
| natural-science | 15 |
| industrial-physical-systems | 14 |
| media-content-production | 9 |
| finance-economics | 9 |
| mathematics-or-formal-reasoning | 8 |
| cybersecurity | 7 |

**skills 生態研究（`docs/skills-research/STATE_OF_SKILLS.md`，2026-01）**：分析 **47,153+ skill / 5,985 repo**，去重後 40,721 個語意獨立（重複率 13.6%）。各 harness 的 skill 目錄：claude-code `.claude/skills/`（5,897 repo）、codex `.codex/skills/`、opencode `.opencode/skill/`、portable `.agents/skills/`。

## 快速上手（Quick Start）

```bash
git clone https://github.com/benchflow-ai/skillsbench.git
cd skillsbench
uv sync --locked

# 建立 / 檢查任務
uv run bench tasks init my-task
uv run bench tasks check tasks/my-task
uv run bench eval create -t tasks/my-task -a oracle           # oracle 須 100%

# 用 agent + skills 實測
bench eval create -t tasks/my-task -a claude-agent-acp -s tasks/my-task/environment/skills/
```

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 評測嚴謹度 | ⭐⭐⭐⭐⭐ | outcome-based + oracle 100% 雙重把關，任務品質有硬門檻 |
| 可重現性 | ⭐⭐⭐⭐⭐ | `uv.lock` + BenchFlow pin commit，明說避免「lock 漂移」 |
| 領域廣度 | ⭐⭐⭐⭐ | 8 大領域 94 任務，且主動列出缺口（法律 0、醫療、機器人）招募貢獻 |
| 生態研究深度 | ⭐⭐⭐⭐⭐ | 47K skill 全量分析 + 五 harness skill 暴露機制原始碼審計，業界少見 |
| 社群治理 | ⭐⭐⭐⭐ | 共同作者署名制度、Discord/微信週會，社群動能強 |

> [!tip] 值得學習的設計
> **「oracle 必須 100% 通過」當任務品質閘門** + **outcome-based 不看過程** 是非常乾淨的評測哲學——和 [[2026-05-22-SKILLOPT-SELF-EVOLVING-AGENT-SKILLS-CODE-ANALYSIS|SkillOpt]] 的「validation gate 嚴格上升」異曲同工：都用一個**客觀、可自動判定的門檻**抵抗自我合理化。另外「五種 harness 如何暴露 skill」的原始碼審計（`docs/harnesses/skill-invocation-surfaces.md`）是理解 skill 跨工具相容性的稀有資料。

### ⚠️ 缺點與風險（Weaknesses & Risks）

- **外部依賴是採用障礙**：CONTRIBUTING 自承「無外部依賴的任務」最缺、最利於採用；許多任務 `allow_internet=true` 或需 Modal/API 憑證，會讓結果受外部服務波動影響。
- **快速演進、版本敏感**：harness 審計文件自注「OpenHands 兩週內實作大改」「pi 已不可公開存取需重驗」——benchmark 的有效性高度依賴 harness 版本。
- **正式跑分結果尚未完整公開**：repo 以任務集與框架為主，RQ1（skill 是否有效）標注「preliminary - needs benchmark data」，結論待後續論文。
- **語言標示為 PDDL/混雜**：GitHub 偵測語言為 PDDL（任務含規劃類），實際是 Python 為主的多語混合，依賴面較雜。

### 🔮 改進建議
1. 擴充「零外部依賴」任務池，降低結果雜訊與採用門檻。
2. 對每個任務標注「依賴的 harness 版本」，提升跨時間可比性。
3. 盡快公開 RQ1 的有/無 skill 對照官方數據。

## 我的心得（My Takeaways）

- **SkillsBench 補上了 skill 生態最缺的一塊：客觀量尺。** 過去大家爭論「skill 到底有沒有用」（参見 [[2026-01-27-VERCEL-AGENTS-MD-OUTPERFORMS-SKILLS-IN-AGENT-EVALS|Vercel: AGENTS.md vs Skills]] 的爭議），SkillsBench 把它變成可跑的 benchmark。
- **它和 SkillOpt 拼起來是完整的 skill 技術棧**：SkillOpt 負責「**把 skill 練好**」，SkillsBench 負責「**驗 skill 用得好不好**」。對 connsys-jarvis 這類自建 agent，理想流程是「用 SkillOpt 範式優化內部 skill → 用 SkillsBench 範式建驗證任務集把關」。
- **「oracle 100% + outcome-based」這套評測哲學可直接借用**：為自家 agent 任務寫一份標準解當品質閘門，只驗最終產物——比人工評審穩定得多。

## 待補充（Open Questions）

- SkillsBench 官方的 RQ1 對照數據（有 skill vs 無 skill 的通過率差）何時公開、差多少？（建議搜尋：`skillsbench.ai results`、HuggingFace `benchflow/skillsbench`）
- 它能否直接拿來評測 **SkillOpt 訓練出的 `best_skill.md`**？格式（SKILL.md vs SkillOpt 的單一 md）相容性如何？（需比對 `agentskills.io` spec）
- 設計目標 SOTA「<50%」（README）與「<39%」（RQ 文件）哪個是最終標準？兩份文件不一致。
- 94 任務裡有多少實際附了 `environment/skills/`（可做有/無 skill 對照）？本次未逐一清點。
- BenchFlow SDK 與 Harbor 格式的關係、與其他 agent eval 框架（如 [[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE|gstack eval]]）的差異為何？（建議搜尋：`BenchFlow Harbor task format`）

---

## 與 SkillOpt 的比較（互補，非競品）

> [!important] 一句話定位
> **SkillOpt 是「skill 的訓練器」，SkillsBench 是「skill 的考場」。** 一個產生 skill、一個評測 skill，位於同一條 skill 生命週期的上下游，不是同類可正面對決的東西。

| 維度 | [[2026-05-22-SKILLOPT-SELF-EVOLVING-AGENT-SKILLS-CODE-ANALYSIS\|SkillOpt]] | SkillsBench（本篇） |
|---|---|---|
| **本質** | 優化器（optimizer） | 評測基準（benchmark / gym） |
| **回答的問題** | 「我怎麼**做出**更好的 skill？」 | 「給定 skill，agent **用得**多好？」 |
| **輸入** | 任務 + 驗證集 + 初始 skill | 任務 + agent + （可選）skill |
| **輸出** | 一份優化過的 `best_skill.md` | 一個分數 / pass-fail / 排行 |
| **核心機制** | textual gradient + 驗證閘門 + 學習率裁剪 + epoch 整併 | Harbor 任務 + outcome 測試 + oracle 100% 閘門 |
| **來源** | Microsoft + 上海交大/復旦/同濟（論文） | benchflow-ai（社群，Apache-2.0） |
| **技術棧** | Python 3.10、自寫訓練迴圈 | Python 3.12、uv、BenchFlow SDK、Daytona |
| **目標模型** | GPT-5.x / Qwen | Claude Opus 4.5 / GPT-5.2 / MiniMax M2.1 / GLM-4.7 |
| **誰跟它正面比** | TextGrad / GEPA / DSPy / EvoSkill（都是 optimizer） | 其他 agent/skill eval（如 Harbor 生態、gstack eval） |

> [!tip] 兩者如何串起來用
> 1. 用 **SkillOpt** 把一份 skill 在訓練驗證集上練到收斂 → 得到 `best_skill.md`。
> 2. 把這份 skill 放進 **SkillsBench** 的 `environment/skills/`，在它的 94 個任務上跑「有 skill vs 無 skill」對照 → 得到**獨立、跨領域的泛化成效**。
> 3. 這正好補上 SkillOpt 的一個風險（對自己的 selection set 過擬合）——用第三方 benchmark 驗證才知道 skill 是否真泛化。

> [!warning] 共同的深層觀念
> 兩者都靠「一個**客觀、可自動判定的閘門**」抵抗 LLM 的自我合理化：SkillOpt 是「驗證分數須嚴格上升才接受編輯」，SkillsBench 是「oracle 須 100% 通過 + outcome 測試」。這也呼應 [[2026-05-22-SKILLOPT-SELF-EVOLVING-AGENT-SKILLS-CODE-ANALYSIS|SkillOpt]] 影片補充的範式轉移金句：「**驗證集設計會變成新的核心技能**」——而 SkillsBench 做的，本質就是把「驗證集設計」工程化、規模化。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確立基礎知識 | 核心術語：gym-style benchmark、Harbor 任務格式、oracle solution、outcome-based test、BenchFlow SDK、skill composition。關鍵數字：94+5 任務、8 領域、47,153 skill 生態分析、SOTA <50%。 |
| **理解（半被動）** | 串聯知識點 | SkillsBench 把「skill 好不好用」變成可跑的分數：任務（Harbor）→ 容器 → agent 帶 skill 執行 → outcome 測試 → 分數；oracle 100% 確保題目有解，難度刻意壓到 SOTA <50% 求鑑別度。 |
| **分析（主動）** | 找假設與漏洞 | 關鍵假設：(1) outcome 測試能完整代表「會用 skill」；(2) oracle 標準解涵蓋正解空間；(3) harness 版本穩定。漏洞：外部依賴帶來雜訊、harness 快速演進使結果易過時、RQ1 官方數據未出。 |
| **應用（主動）** | 轉為行動 | (1) 為自家 agent 任務寫「oracle + outcome 測試」當品質閘門；(2) 用「有/無 skill 對照」量化自己 skill 的真實貢獻；(3) 把 SkillOpt 產物丟進 SkillsBench 驗泛化。 |
| **評估（主動）** | 權衡取捨 | 相較自建臨時評測，SkillsBench 的 oracle-gated + 可重現是強項；但代價是外部依賴與版本敏感。若你要評「skill 使用」→ 用它；若要「優化 skill」→ 用 SkillOpt；兩者不互斥、應串用。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「會用 skill」如何精確定義？outcome 通過是否等於「真的因為 skill 才通過」（而非模型本來就會）？這正是 RQ1 對照組要回答的。
- **假設**：最關鍵前提是「oracle 標準解 = 唯一/完整正解」。若任務有多種正解而測試只認一種，會低估 agent。
- **證據**：「skill 讓 agent 變強」目前在 repo 仍是 preliminary，缺正式對照數據。
- **觀點**：反對者可說「這測的是『任務難度』不是『skill 使用』——拿掉 skill 也可能過」。對照組設計是回應此批評的關鍵。
- **後果**：若成為事實標準，12 個月後可能出現「為刷 SkillsBench 而設計的 skill」（Goodhart's law），偏離真實效用。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — **評測效度（validity）**：若 outcome 測試或 oracle 不夠周全，分數會誤導；外部依賴與 harness 版本漂移也會讓同一 benchmark 不同時間結果不可比。
2. **什麼情況下會失敗？** — (a) 任務有多正解但測試只認一種；(b) agent 不靠 skill 也能過（對照組沒設好）；(c) 依賴的外部 API/harness 改版；(d) 任務被資料污染（模型訓練時看過）。
3. **有沒有更好的替代方案？** — 若只需「優化 skill」→ 用 SkillOpt / GEPA / DSPy，不需 benchmark；若需「綜合 agent 能力」→ 用更廣的 agent eval（SWE-bench 類）；SkillsBench 的獨特定位是**專測「skill 使用」這一刀**，目前無直接替代品。

## 相關連結（Related）
- [[2026-05-22-SKILLOPT-SELF-EVOLVING-AGENT-SKILLS-CODE-ANALYSIS]] — **互補核心**：SkillOpt 產生 skill、SkillsBench 評測 skill，上下游關係（見本篇「與 SkillOpt 的比較」）
- [[2026-04-16-CLAUDE-CODE-SKILLS-VS-COMMANDS-VS-SUBAGENTS-COMPLETE-COMPARISON]] — skill 的定義與其他擴充機制的比較，理解 SkillsBench 測的「skill」是什麼
- [[2026-04-11-NPX-SKILLS-DEEP-DIVE-PARSE-DISCOVER-INSTALL-UPDATE]] — skill 的發現/安裝機制，對應 SkillsBench 審計的「各 harness 如何暴露 skill」
- [[2026-05-20-CODEX-HOOK-AND-SKILLS-PARAMETERS-DEEP-DIVE]] — Codex 的 skill 搜尋路徑，對照 SkillsBench 的 harness 審計表
- [[2026-04-07-GSTACK-AI-AGENT-EVAL-ARCHITECTURE]] — 另一套 agent eval 架構，可與 BenchFlow/Harbor 對照

## References
- [GitHub — benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench)
- [官網 — skillsbench.ai](https://www.skillsbench.ai)
- [HuggingFace Dataset — benchflow/skillsbench](https://huggingface.co/datasets/benchflow/skillsbench)
- [BenchFlow SDK](https://github.com/benchflow-ai/benchflow)
- 本地 clone：`~/git/skillsbench_play/skillsbench`
