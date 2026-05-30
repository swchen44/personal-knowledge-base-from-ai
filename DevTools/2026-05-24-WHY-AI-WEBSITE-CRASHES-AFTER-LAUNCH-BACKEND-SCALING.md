---
title: "為什麼 AI 寫的網站一上線就掛：後端擴展與系統瓶頸入門"
date: 2026-05-24
category: DevTools
tags:
  - "#devtools/backend"
  - "#architecture/scalability"
  - "#ai/software-development"
  - "#tools/claude-code"
source: "https://www.youtube.com/watch?v=t5CtfUWJjm4"
source_type: video
author: "Debug Tuboshu"
status: notes
channel: "Debug Tuboshu"
duration: "12:07"
transcript_method: youtube-transcript-api
links:
  - "[[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]]"
  - "[[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]]"
  - "[[2026-02-12-EVALUATING-AGENTS-MD-CONTEXT-FILES-HELPFUL-FOR-CODING-AGENTS]]"
---

## 摘要（Summary）

這支影片用「手搖飲店從一人小店成長到全台連鎖」的比喻，解釋網站後端系統（Backend System）如何從最簡單的前端、後端、資料庫架構，逐步演化出資料庫優化（Database Optimization）、快取（Cache）、水平擴展（Horizontal Scaling）、資料庫副本（Replica）、微服務（Microservice）、CDN、限流（Rate Limiter）與佇列（Queue）。核心提醒是：用 Claude Code 或其他 AI 工具把 SaaS 做出來，不等於系統已經能承受真實流量；真正關鍵不是背熟技術名詞，而是知道產品變慢、卡住、當機時，瓶頸到底在哪裡。

## 關鍵洞察（Key Insights）

- **能動（it works）不等於能撐（it scales）**：本機測試或少量用戶能正常運作，只代表功能路徑成立，不代表後端能承受並發流量、資料量成長或尖峰活動。
- **先盤點瓶頸，再升級架構**：影片反覆用手搖店 SOP 比喻工程排查流程；真正優先順序不是先上雲端服務，而是找出慢在 CPU、資料庫查詢、檔案讀取、網路傳輸、部署流程，還是寫入衝突。
- **資料庫通常是最早被忽略的瓶頸**：資料量小時看不出問題，資料一多，缺索引（Index）、N+1 query、`select *` 這些問題會立刻放大。
- **Cache 解的是重複讀取，不是所有問題**：把熱門資料放到記憶體能大幅降低資料庫壓力，但會引入資料過期（Staleness）、更新策略與容量限制。
- **水平擴展前要先外部化狀態**：若資料庫、快取、圖片檔案都綁在單一機器上，就算多開幾台後端也無法共享狀態；影片用 AWS RDS、ElastiCache、S3 作為例子。
- **AI 可以代做設定，但不能替你判斷問題定義**：你可以請 AI 加 cache、優化資料庫或設 CI/CD，但前提是你知道現在真正要解的是什麼瓶頸。這和 [[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]] 的生產環境觀點相呼應：AI 工作流需要明確邊界與監控，而不是只追求快速生成。

## 詳細內容（Details）

### 系統演化路徑

影片的核心不是列出所有架構元件，而是呈現「每個元件都是被問題逼出來的」。可以整理成下列順序：

| 階段 | 手搖店比喻 | 工程對應 | 解決的瓶頸 | 新增的代價 |
|------|------------|----------|------------|------------|
| 1 | 丁丁一人開店 | 前端 + 後端 + 資料庫 + 檔案儲存 | 功能能跑起來 | 單點故障、無擴展性 |
| 2 | 多請人幫忙 | 垂直擴展（Scale Up） | 單機 CPU / 記憶體不足 | 成本高、閒置資源多 |
| 3 | 整理倉庫 | 資料庫索引、查詢優化 | 查詢慢 | 需要理解資料模型與 query pattern |
| 4 | 前場放保溫桶 / 冰桶 | Cache | 重複讀資料太慢 | 資料過期、容量有限 |
| 5 | 開分店前 SOP 化 | Docker、CI/CD、監控、Load Balancer | 多台機器部署與流量分散 | 維運複雜度上升 |
| 6 | 分店共用主資料庫塞爆 | Replica、讀寫分離 | 讀取壓力集中 | 一致性延遲、寫入仍是瓶頸 |
| 7 | 茶葉工廠獨立成公司 | Microservice | 業務邊界混雜 | 分散式系統複雜度 |
| 8 | 活動素材配送到各門市 | CDN | 靜態內容集中下載 | 快取失效與版本管理 |
| 9 | 一元搶珍奶排隊 | Rate Limiter + Queue | 寫入尖峰打爆資料庫 | 非同步狀態與使用者等待體驗 |

### 架構流程圖

```
最小可用網站
  │
  ▼
[前端] ──API──► [後端] ──► [資料庫 / 檔案]
  │                         │
  │                         └─ 資料變多後查詢變慢
  ▼
先優化資料庫：Index / 避免 N+1 / 避免 select *
  │
  ▼
加入 Cache：把熱門資料放到記憶體
  │
  ▼
外部化狀態：RDS / ElastiCache / S3
  │
  ▼
容器化 + CI/CD + Health Check + Logs
  │
  ▼
Load Balancer + Horizontal Scaling / Auto Scaling
  │
  ▼
Replica / Microservice / CDN / Queue / Rate Limiter
```

> [!note] 關鍵術語（Key Term）
> **水平擴展（Horizontal Scaling）** 是透過增加多台機器分散負載；**垂直擴展（Scale Up）** 則是把同一台機器升級得更強。前者通常需要先把狀態外部化，否則多台機器會各自拿不到一致的資料。

### 問題診斷順序

影片隱含的工程診斷流程可以整理成：

1. **先確認慢在哪一段**：前端載入、API、後端計算、資料庫查詢、檔案下載、第三方服務，還是部署流程。
2. **先做低成本優化**：資料庫索引、查詢模式、避免 N+1 query、避免不必要的全欄位查詢。
3. **再加快取層**：只 cache 熱門、可容忍短暫過期、讀多寫少的資料。
4. **準備多機部署前置條件**：Docker 化、外部化資料庫/快取/檔案、CI/CD、health check、log aggregation。
5. **用負載平衡與自動擴展處理流量波動**：流量可分散的前提是各實例具備一致環境與共享狀態。
6. **針對資料庫讀壓力加 replica**：讀多寫少適用；大量同時寫入仍需 queue、限流或資料模型重設計。
7. **最後才拆 microservice**：當業務邊界清楚、團隊或部署節奏需要分離時再拆，否則只是把單體問題變成分散式問題。

> [!warning] 注意事項（Watch Out）
> 「請 AI 幫我上 microservice」通常不是好起點。若瓶頸其實是缺索引、cache 策略錯誤或沒有監控，拆服務只會讓除錯更難。

### AI 寫網站的真正風險

這支影片點出一個很實用的現象：AI 讓「做出一個能 demo 的網站」成本大幅下降，但也讓很多人跳過了系統設計（System Design）與營運可靠性（Operational Reliability）的基本功。

對 AI-assisted development 來說，較安全的工作方式是：

- 讓 AI 先產出功能，但要求它補上負載假設（Traffic Assumptions）、資料量假設（Data Volume Assumptions）與失敗模式（Failure Modes）。
- 對每個外部服務與資料庫 query 建立觀測點（Observability），這和 [[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]] 提到的「先有數據再做判斷」一致。
- 把「部署後會怎麼壞」寫進 AGENTS.md / CLAUDE.md 或專案文件，但要維持精簡；[[2026-02-12-EVALUATING-AGENTS-MD-CONTEXT-FILES-HELPFUL-FOR-CODING-AGENTS]] 顯示過度膨脹的 context files 不一定有效。

> [!tip] 可執行建議（Actionable Tip）
> 下次用 AI 做 SaaS MVP 時，在完成核心功能後立刻追加一輪 prompt：「請找出這個系統在 100、1,000、10,000 同時在線使用者下最可能先壞掉的三個地方，並按低成本到高成本列出改善順序。」

## 我的心得（My Takeaways）

這支影片最有價值的地方，是把 system design 從「堆技術名詞」拉回「問題驅動」。很多 AI coding 的失敗不是模型不會寫程式，而是人沒有描述清楚產品在真實世界會遇到的壓力：同時讀、同時寫、靜態資產流量、資料庫一致性、部署頻率、監控與回滾。

我會把它當成一個 AI 產品上線前的檢查框架：功能完成只是第一層，接著要問資料怎麼長、流量怎麼尖峰、哪裡可以 cache、哪些請求一定要同步、哪些可以排隊，以及出了問題要去哪裡看 log。

## 待補充（Open Questions）

- 影片沒有提供具體壓測（Load Testing）方法；對一般小型 SaaS，應該用 k6、Artillery、Locust 還是雲端壓測服務？（建議搜尋：`SaaS MVP load testing k6 Artillery Locust comparison`）
- 影片提到 AI 可以檢查索引與 N+1 query，但不同框架（Rails、Django、Next.js、Prisma）各自最可靠的偵測工具是什麼？（建議搜尋：`Prisma N+1 query detection index analysis AI code review`）
- Cache 的更新策略沒有細談；對社群貼文、會員資料、商品庫存這三種資料，TTL、write-through、write-behind、cache invalidation 應該如何取捨？（建議搜尋：`cache invalidation patterns social feed inventory user profile`）
- Replica 的同步延遲（Replication Lag）在會員身份、庫存、搶票等場景下會造成什麼一致性問題？（建議搜尋：`read replica replication lag consistency user account inventory`）
- 影片用 AWS 服務作例子；若部署在 Vercel、Fly.io、Render、Supabase 或 Cloudflare Workers 上，等價架構該怎麼映射？（建議搜尋：`Vercel Supabase scalable SaaS architecture cache queue rate limiter`）

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索，確立基礎知識 | 必記概念：垂直擴展（Scale Up）、水平擴展（Horizontal Scaling）、資料庫索引（Index）、快取（Cache）、資料庫副本（Replica）、微服務（Microservice）、CDN、限流（Rate Limiter）、佇列（Queue）。 |
| **理解（半被動）** | 解釋概念的含義及關聯，串聯知識點，掌握核心邏輯 | 影片的核心邏輯是「架構不是一次到位，而是被瓶頸推著長出來」：一開始單機能跑，流量上來後先找人手/CPU 瓶頸，再整理資料庫，接著把熱門資料 cache，然後外部化狀態做水平擴展，最後才處理讀寫分離、服務拆分、靜態內容配送與尖峰寫入排隊。 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設，批判性思維，看透策略底層邏輯 | 影片假設多數早期產品的瓶頸可透過常見後端手段逐步解決，但沒有討論資料模型錯誤、商業模式造成的流量尖峰、第三方 API 限制、成本上限與團隊維運能力。它也偏向讀多寫少的典型網站情境，對協作編輯、即時遊戲、金融交易這類高一致性系統不夠完整。 |
| **應用（主動）** | 將知識套用情境，規劃執行方案，實戰決策力，將理論轉為行動 | 可立即執行：（1）為自己的 AI 生成 SaaS 列出前 5 個可能瓶頸與觀測指標；（2）要求 AI 檢查資料庫索引、N+1 query、`select *`、慢查詢；（3）在上線前加上最小監控：health check、error log、latency、DB query time、cache hit ratio。 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡，在不確定的情境中做出最佳選擇 | 本文觀點適合早期 SaaS 與一般內容型網站，優點是問題驅動、避免過早工程化；限制是未提供量化門檻。與「一開始就上 Kubernetes / microservice」相比，影片路徑更務實；與「完全依賴平台如 Vercel/Supabase」相比，它能建立較完整的系統理解，但需要更多工程判斷。 |

### 分析型追問（Socratic Follow-up）

- **澄清**：影片中的「網站變慢」應該拆成哪些可量測指標：p95 latency、error rate、DB query time、CPU、memory、queue depth，還是轉換率下降？
- **假設**：影片假設瓶頸可以被逐步定位；若系統沒有 log、trace、metrics，這個前提是否成立？
- **證據**：影片主張「大部分網站到資料庫優化 + cache 就夠了」，這是否有公開案例或流量級距作支持？
- **觀點**：若站在平台工程師立場，會不會認為影片低估了 CI/CD、secret management、rollback、migration 的難度？
- **後果**：若創業者聽完後過度相信 AI 可以代設 infrastructure，12 個月後最可能累積哪些隱性維運債？

### 方案批判三問（Critical Evaluation — 適用於程式碼或做事方法類內容）

1. **最大的風險是什麼？** — 最大風險是把架構元件當成檢查清單，而不是瓶頸對應工具；例如沒有讀取瓶頸卻加 replica，沒有靜態資產壓力卻花時間調 CDN，或在單體還沒穩定前就拆 microservice。
2. **什麼情況下會失敗？** — 當系統缺乏觀測性、資料模型本身錯誤、寫入一致性要求極高、第三方服務是主要瓶頸，或團隊沒有維運多服務架構的能力時，影片的漸進路徑需要補上更嚴格的可靠性工程（Reliability Engineering）。
3. **有沒有更好的替代方案？** — 對小型團隊，替代方案是先選擇 managed platform（如 Vercel + Supabase + Cloudflare）並設定清楚的流量門檻；優點是少維運、快上線，缺點是可控性與成本曲線受平台限制。當產品已驗證需求，再逐步抽出資料庫、queue、cache 與部署管線會更合理。

## 相關連結（Related）

- [[2026-03-31-BUILD-CLAUDE-CODE-AGENTS-10-STEP-FRAMEWORK]] — 同樣討論 Claude Code / AI-assisted development 進入生產環境後需要的邊界、安全與工作流設計。
- [[2026-04-11-CLAUDE-CODE-MONITORING-OPENTELEMETRY-TEAM-DATA]] — 本影片強調「先知道瓶頸在哪」，這篇提供 Claude Code 團隊與生產工作流的監控觀點。
- [[2026-02-12-EVALUATING-AGENTS-MD-CONTEXT-FILES-HELPFUL-FOR-CODING-AGENTS]] — 可補充「把架構知識寫給 AI」時，context files 應精簡且任務關鍵，而不是無限制膨脹。

## References

- [原影片](https://www.youtube.com/watch?v=t5CtfUWJjm4) — Debug Tuboshu，2026-05-24
