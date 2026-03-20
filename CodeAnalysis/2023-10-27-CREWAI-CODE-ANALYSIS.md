---
title: "CrewAI — 多代理人協作編排框架深度分析"
date: 2023-10-27
category: CodeAnalysis
tags:
  - "#code-analysis"
  - "#ai/agent"
  - "#ai/framework"
  - "#ai/llm"
  - "#python"
source: "https://github.com/crewaiinc/crewai"
source_type: code
author: "CrewAI Inc. (Joao Moura)"
status: notes
links:
  - "[[AI-AGENT-DESIGN]]"
  - "[[CLAUDE-MEM-CODE-ANALYSIS]]"
  - "[[BUILD-AGENT-WITH-CLAUDE-CODE-IN-20-MINUTES]]"
github_stars: 46627
github_language: Python
---

## 摘要（Summary）

CrewAI 是一個完全從零打造的 Python 多代理人（multi-agent）編排框架，不依賴 LangChain 或其他 agent 框架。它提供兩種互補的核心抽象：**Crews**（由角色扮演的自主 AI 代理人（Agent）組成的團隊，適合自由協作）與 **Flows**（事件驅動的精確工作流程（workflow），適合生產環境）。擁有 46,627 顆 ⭐，是目前最受歡迎的多代理人 Python 框架之一，有超過 100,000 名認證開發者。

## Why — 為什麼存在？

- **核心動機**：LangChain 等框架在 Agent 場景下過於複雜、效能不佳，且難以做低層級自定義。開發者需要一個輕量、快速、從底層掌控每個細節的多 Agent 協作框架
- **取代/改善什麼**：取代 LangChain Agents 的重量級抽象；相較 LangGraph，CrewAI Flows 提供更直覺的 Pythonic 語法（裝飾器而非圖節點）
- **目標用戶**：需要快速建立多 Agent 系統的 Python 開發者；需要在生產環境部署可靠 AI 自動化工作流的企業

## What — 是什麼？

- **主要功能**：
  - **Crews**：定義具備角色（role）、目標（goal）、背景（backstory）的 Agent，並指派 Task，由 Crew 自動協調執行順序
  - **Flows**：用 `@start`、`@listen`、`@router` 裝飾器建立事件驅動工作流，支援條件分支、狀態管理
  - **Memory 系統**：短期記憶（short-term memory）、長期記憶（long-term memory）、實體記憶（entity memory）、使用者記憶
  - **Knowledge Sources**：PDF、網頁、資料庫等知識來源的 RAG（Retrieval-Augmented Generation）整合
  - **MCP 整合**：支援 MCP（Model Context Protocol）Server 工具
  - **A2A 協定**：Agent-to-Agent 企業通訊協定，支援跨服務 Agent 呼叫
  - **CLI**：`crewai` 指令快速建立專案模板（Crew 或 Flow）
  - **觀測性（Observability）**：OpenTelemetry 追蹤，整合 Crew Control Plane 雲端儀表板
- **不做什麼（Non-goals）**：不自行管理向量資料庫；不內建 UI；不提供 LLM 本身（整合 OpenAI、Anthropic、Bedrock 等）
- **技術棧（Tech Stack）**：Python 3.10+、Pydantic（所有模型）、OpenTelemetry、UV（依賴管理）、LiteLLM（多 LLM 支援）、Rich（終端機輸出）

## How — 如何運作？

### 系統架構圖（System Architecture）

```
┌────────────────────────────────────────────────────────────────────┐
│                        使用者 Python Code                           │
│                                                                      │
│    ┌──────────────────────┐    ┌──────────────────────────────┐    │
│    │       Crews          │    │           Flows               │    │
│    │                      │    │                               │    │
│    │  Agent1 ─► Task1    │    │  @start def begin():          │    │
│    │  Agent2 ─► Task2    │    │  @listen(begin) def step():   │    │
│    │  Agent3 ─► Task3    │    │  @router def branch():        │    │
│    │                      │    │                               │    │
│    └──────────┬───────────┘    └────────────┬─────────────────┘    │
└───────────────┼────────────────────────────┼──────────────────────-┘
                │                             │
                ▼                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                      Core Engine Layer                              │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐    │
│  │  Agent Core  │  │  Task Engine  │  │  Flow Execution Engine │    │
│  │  (Pydantic)  │  │  (Pydantic)  │  │  (事件驅動, 裝飾器)  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬────────────┘    │
│         │                  │                       │                 │
│  ┌──────▼───────────────────────────────────────▼─┘                │
│  │              Event Bus (crewai_event_bus)                        │
│  └──────────────────────┬──────────────────────────────────────────┘
│                          │                                           │
│  ┌───────────────────────▼──────────────────────────────────────┐  │
│  │                    Provider Layer                             │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │  │
│  │  │  LiteLLM │ │ Memory   │ │Knowledge │ │ Tools / MCP    │  │  │
│  │  │(多LLM)  │ │(短/長期) │ │(RAG)    │ │ A2A / Cache    │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
              OpenTelemetry / Crew Control Plane
```

### 執行流程圖（Execution Flowchart）

**Crew 執行流程：**

```
 crew.kickoff(inputs={"topic": "AI"})
         │
         ▼
   [prepare_kickoff]
   注入 inputs 到 Task 描述
   初始化 Memory、Cache、Telemetry
         │
         ▼
   [依序執行 Tasks]
         │
         ├─ Sequential 模式 ──► Task1 → Task2 → Task3（依序）
         │                           ↑ context 傳遞
         │
         └─ Hierarchical 模式 ──► Manager Agent 分配與協調
                                        ↓
                                   Agent 自主選擇工具、委派

   每個 Task：
   │
   ├─ Agent 收到 Task 描述 + context
   ├─ 呼叫 LLM 決定動作（ReAct 迴圈）
   │     ├─ 選擇工具 → 執行工具 → 觀察結果
   │     └─ 重複直到完成
   └─ 輸出 TaskOutput（含 raw / pydantic / json）
         │
         ▼
   [CrewOutput]
   彙整所有 Task 輸出，
   觸發 CrewKickoffCompletedEvent
```

**Flow 執行流程：**

```
 flow.kickoff()
       │
       ▼
 [找到 @start 方法] ──► 執行
       │
       ▼
 [crewai_event_bus 發出完成事件]
       │
       ├─ 有 @listen(start_method) 的方法 ──► 依序觸發
       │
       ├─ @router 方法 ──► 根據回傳值決定路由（字串對應分支）
       │
       └─ and_(m1, m2) / or_(m1, m2) ──► 等待多個方法完成
                                          才觸發下游方法
       │
       ▼
 [所有方法執行完畢]
 觸發 FlowFinishedEvent
```

### 關鍵設計決策（Key Design Decisions）

> [!note] 設計模式（Design Pattern）：事件驅動架構（Event-Driven Architecture）+ 裝飾器模式（Decorator Pattern）
> `crewai_event_bus` 作為全域事件總線，所有元件（Crew、Agent、Task、Flow）通過事件溝通，解耦各元件的直接依賴。Flow 的裝飾器（`@start`、`@listen`、`@router`）將方法間的依賴關係聲明式地表達，比傳統命令式圖建構更 Pythonic。

1. **Pydantic 全面採用**：所有核心物件（Agent、Task、Crew、Flow 狀態）都是 Pydantic BaseModel，天然支援 JSON 序列化、型別驗證、schema 生成
2. **不依賴 LangChain**：從零實作 LLM 呼叫（透過 LiteLLM），避免 LangChain 的過度抽象和版本依賴問題
3. **Crews vs Flows 的雙軌設計**：Crews 給代理人最大自主空間（autonomy），Flows 給開發者精確控制（precise control）。兩者可嵌套——Flow 的某個步驟可以是一個 Crew
4. **YAML 配置分離**：Agent 和 Task 的定義可完全放在 `agents.yaml` / `tasks.yaml`，Python 程式碼只負責組裝邏輯，關注點分離（separation of concerns）
5. **OpenTelemetry 原生整合**：框架層級的 span 追蹤，每個 Agent 執行、Task 完成都有對應的 trace，便於偵錯和效能分析

### 資料流（Data Flow）

1. 使用者定義 Agent（角色、LLM、工具）和 Task（描述、期望輸出、assigned_agent）
2. `Crew.kickoff(inputs)` 開始執行：inputs 注入 Task 描述的模板變數
3. 按照 `process`（sequential 或 hierarchical）依序執行每個 Task
4. 每個 Task 由 assigned Agent 執行：Agent 呼叫 LLM → LLM 回應 → 解析 Action → 執行工具 → 觀察 → 重複（ReAct loop）
5. Task 完成後輸出存入 `TaskOutput`，作為下一個 Task 的 context
6. 所有 Task 完成後生成 `CrewOutput`，包含最終結果

### 關鍵程式碼（Key Code Snippets）

**最簡 Crew 範例：**

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class ResearchCrew:
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def researcher(self) -> Agent:
        return Agent(config=self.agents_config['researcher'])

    @agent
    def writer(self) -> Agent:
        return Agent(config=self.agents_config['writer'])

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config['research_task'])

    @task
    def writing_task(self) -> Task:
        return Task(config=self.tasks_config['writing_task'])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
        )

# 執行
result = ResearchCrew().crew().kickoff(inputs={"topic": "AI Agents"})
```

**Flow 事件驅動範例：**

```python
from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

class ResearchState(BaseModel):
    topic: str = ""
    research: str = ""
    article: str = ""

class ResearchFlow(Flow[ResearchState]):

    @start()
    def get_topic(self):
        self.state.topic = "AI Agents"

    @listen(get_topic)
    def research(self):
        # 可以在這裡呼叫 Crew 或直接呼叫 LLM
        self.state.research = "Research results..."

    @router(research)
    def check_quality(self):
        if len(self.state.research) > 100:
            return "write"
        return "retry"

    @listen("write")
    def write_article(self):
        self.state.article = f"Article about {self.state.topic}"

flow = ResearchFlow()
result = flow.kickoff()
```

**YAML 配置（agents.yaml）：**

```yaml
researcher:
  role: >
    {topic} Senior Data Researcher
  goal: >
    Uncover cutting-edge developments in {topic}
  backstory: >
    You're a seasoned researcher with a knack for uncovering
    the latest developments in {topic}.
  llm: openai/gpt-4o
  tools:
    - SerperDevTool
```

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可維護性（Maintainability） | ⭐⭐⭐⭐ | Pydantic 模型 + YAML 配置分離，核心元件職責清晰；1021 個 Python 檔案規模較大，部分模組較複雜 |
| 可擴展性（Scalability） | ⭐⭐⭐⭐⭐ | LiteLLM 支援 100+ LLM、自定義工具介面、Memory 插件、A2A 企業擴展，幾乎可以接入任何 AI 服務 |
| 測試覆蓋（Test Coverage） | ⭐⭐⭐⭐ | 有大量測試，覆蓋 VCR cassettes（記錄/回放 API 呼叫）、pytest-xdist 平行測試，品質有保障 |
| 文件品質（Documentation） | ⭐⭐⭐⭐⭐ | 官方文件網站（docs.crewai.com）完整，DeepLearning.AI 課程，100,000+ 認證社群 |
| 依賴管理（Dependency Management） | ⭐⭐⭐ | 採用 UV 管理，但依賴較多（LiteLLM、Pydantic、OpenTelemetry 等），安裝體積較大 |

> [!tip] 值得學習的設計
> **Crews + Flows 雙軌設計**的哲學非常值得借鑒：高自主性（Crew）和精確控制（Flow）不是互斥的，而是根據場景選擇——不確定性高、需要創意的任務用 Crew；流程確定、需要可靠執行的用 Flow。兩者可以嵌套組合，這個設計思路可以應用到任何 AI 應用架構。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 已知缺陷
> - **問題一：Agent 執行成本難以控制**：Crew 的自主性代表 LLM 呼叫次數不確定，複雜任務可能觸發大量 ReAct 迴圈，造成 Token 費用暴增 — 影響：生產環境需要設定 `max_iter` 和 token limits
> - **問題二：Agent 輸出不穩定**：LLM 生成的 Action 格式偶爾不符合預期，會觸發重試，且不同 LLM 的行為差異大 — 影響：需要仔細設定 Pydantic output schema 或使用 `expected_output` 約束
> - **問題三：Hierarchical 模式的 Manager Agent 成本高**：需要額外 LLM 呼叫來分配任務，且 Manager Agent 的決策品質依賴 LLM 能力 — 影響：小型任務不值得用 hierarchical，盡量用 sequential
> - **問題四：Framework 版本迭代快**：v1.11.0 相較早期版本 API 已有多次重大變更（breaking changes），文件有時跟不上最新版 — 影響：依賴固定版本，升級需謹慎測試

### 🔮 改進建議（Improvement Suggestions）

1. **更細粒度的 Token 預算控制**：在 Task 層級設定 Token 上限，防止失控的 ReAct 迴圈
2. **Flow 的視覺化除錯工具**：目前有 `flow.plot()` 生成靜態圖，若能有即時執行狀態顯示（例如 DAG 高亮當前步驟）會大幅提升除錯效率

## 效能基準（Benchmark）

> [!info] 資料來源
> 來自官方 README 的比較和社群評測，無完整的公開 benchmark 數據。

| 面向 | CrewAI | LangGraph | AutoGen |
|------|--------|-----------|---------|
| 上手難度 | 低（YAML + 裝飾器） | 中（圖節點建構） | 低（conversational） |
| 自主性（Autonomy） | 高（Crews） | 低（明確圖定義） | 高 |
| 精確控制 | 高（Flows） | 高 | 低 |
| 框架依賴 | 獨立 | LangChain | 獨立 |
| 社群規模 | 46,627 ⭐ | 12,000+ ⭐ | 35,000+ ⭐ |
| 企業支援 | 有（AMP Suite） | 有（LangSmith） | 有（Azure） |

{CrewAI 在「自主性 + 精確控制兼得」的設計上明顯優於競品；但執行成本（Token 用量）在高自主模式下難以預測是共同痛點}

## 快速上手（Quick Start）

```bash
# 安裝
uv pip install crewai

# 建立新的 Crew 專案
crewai create crew my-research-crew
cd my-research-crew

# 設定 LLM API Key
export OPENAI_API_KEY=your-key-here

# 編輯 config/agents.yaml 和 config/tasks.yaml
# 執行
uv run crewai run

# 建立 Flow 專案
crewai create flow my-research-flow
cd my-research-flow
uv run python src/my_research_flow/main.py
```

## 我的心得（My Takeaways）

- **Crews + Flows 雙軌設計**是目前我見過最優雅的 AI 工作流架構：不強迫開發者在「完全自主」和「完全手動控制」之間二選一，而是提供兩個互補的抽象，按場景選用
- **Pydantic 全面採用**是正確的賭注：它同時解決了型別安全、JSON 序列化、LLM structured output、API schema 生成四個問題，比自製資料類別節省大量工作
- **YAML 與 Python 的責任分離**值得在自己的 AI 應用中借鑒：業務配置（Agent 角色、Task 描述）放 YAML，程式邏輯放 Python，讓非工程師也能修改 Agent 行為
- 事件驅動架構（Event-Driven Architecture）讓所有元件可以獨立演化，觀測性（Observability）的插入也更自然，參見 [[AI-AGENT-DESIGN]]
- CrewAI Flows 的裝飾器語法比 LangGraph 的圖建構更直覺，若下次需要建立確定性 AI 工作流，Flow 是比 LangGraph 更值得考慮的選項

## 相關連結（Related）

- [[AI-AGENT-DESIGN]] — 多代理人系統的設計原則，CrewAI 是最佳實踐範例
- [[CLAUDE-MEM-CODE-ANALYSIS]] — Claude Code 的持久記憶插件，與 CrewAI 的 Memory 系統概念互補
- [[BUILD-AGENT-WITH-CLAUDE-CODE-IN-20-MINUTES]] — 用 Claude Code 建立 Agent 的實務教程，可對比 CrewAI 的架構選擇

## References

- [GitHub Repo](https://github.com/crewaiinc/crewai)
- [官方文件](https://docs.crewai.com)
- [CrewAI 雲端平台](https://app.crewai.com)
- [DeepLearning.AI 課程](https://www.deeplearning.ai/short-courses/multi-ai-agent-systems-with-crewai/)
