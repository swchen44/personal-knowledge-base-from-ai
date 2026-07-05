---
title: "終端機記憶體管理與跨平台持久化方案研究報告"
date: 2026-07-05
date_uncertain: true
category: DevTools
tags:
  - "#tools/terminal"
  - "#devtools/claude-code"
  - "#tools/tmux"
  - "#productivity/workflows"
  - "#windows/conpty"
source: "manual:user-pasted-report"
source_type: report
author: "使用者提供"
status: notes
links:
  - "[[2026-03-20-WEZTERM-SESSION-TECHNICAL-SUMMARY]]"
  - "[[2026-03-20-WEZTERM-MACOS-DICTATION-BUILD-AND-CJK-FIX]]"
  - "[[2026-05-30-MOSHI-MOBILE-TERMINAL-FOR-CODING-AGENTS]]"
  - "[[2026-05-16-CLAUDE-CODE-HEADLESS-MODE-AUTO-MEMORY-DISABLE]]"
---

## 摘要（Summary）

這份報告整理現代 GPU 加速終端機（GPU-accelerated terminal）在長時間執行 AI 命令列工具（AI CLI），尤其是 Claude Code 時，可能出現的記憶體暴增（Memory Leak / Memory Growth）問題。核心觀點是：終端機記憶體異常不一定只來自終端本體，也可能來自字形快取（glyph cache）、TUI 動態重繪、子進程記憶體歸帳、自動更新模組，以及缺少工作階段持久化（session persistence）的操作方式。

> [!warning] 來源狀態
> 本筆記根據使用者貼上的報告整理，未逐條驗證所有 issue 編號與上游 bug 狀態。涉及 Ghostty、Claude Code、psmux 等「最新」狀態時，正式採用前應再查官方 repo 或 release notes。

## 關鍵洞察（Key Insights）

- **記憶體暴增要先分辨「真洩漏」與「歸帳假象」**：Activity Monitor / Task Manager 可能把 Node.js、Language Server、watcher 等子進程記憶體算在終端機名下。
- **AI CLI 會放大終端機渲染邊界問題**：Claude Code 這類工具會大量輸出多碼點字形（multi-codepoint glyph）、TUI 重繪與長 scrollback，容易撞到字形快取與 scrollback 策略的缺陷。
- **環境變數是單向隔離的修復槓桿**：在 shell 設定的變數只會傳給後續子進程，可精準關閉單一工具行為，例如停用自動更新模組，而不改變終端機本身。
- **tmux / psmux 的價值不是分頁，而是把任務從 GUI 終端機生命週期中解耦**：關閉終端視窗只斷開顯示連線，背景 daemon 仍保留工作階段。
- **跨平台策略應分層**：macOS / Linux 可用 `tmux`；Windows 原生可評估 psmux、Windows Terminal Preview 或 Alacritty + ConPTY 路線。

## 詳細內容（Details）

### 一、核心問題診斷（Why）

#### 1. 終端機與 AI CLI 的渲染衝突

報告指出，Ghostty 在處理大量多碼點（multi-codepoint）複雜字形與 TUI 動態重繪時，可能觸發 PageList 雙向鏈表與標準記憶體池以外的配置路徑，造成記憶體洩漏或成長異常。這類問題在一般 shell 使用時不一定明顯，但 Claude Code 這種高頻刷新、長時間輸出、包含 Markdown / Unicode / spinner / diff 的工具會把問題放大。

另一個相關因素是字型紋理快取（font texture cache）：若各分頁或視窗無法共享快取，記憶體會隨分頁數線性增加。這不是單一命令造成的問題，而是終端渲染架構與工作負載交會後的結果。

#### 2. 進程隔離設計的副作用

macOS 或 Windows 的系統監控工具可能把終端機啟動的所有子進程記憶體歸到宿主終端機下。例如 Claude Code 背後的 Node.js、Language Server、watcher、子 shell 都可能被視覺化成「終端機吃掉很多 RAM」。

> [!tip] 診斷順序
> 先用 `ps`、Activity Monitor 的子進程視圖，或 Windows 的 Process Explorer 拆開 process tree。不要只看終端 App 的總 RAM 就判斷是終端本體洩漏。

#### 3. Claude Code 自動更新模組風險

報告提到 Claude Code 自動更新模組在部分終端環境下可能快速消耗記憶體。建議作為止血手段，先以環境變數關閉自動更新，再觀察記憶體曲線是否停止成長。

```bash
echo 'export DISABLE_AUTOUPDATER=1' >> ~/.zshrc
source ~/.zshrc
```

這與 [[2026-05-16-CLAUDE-CODE-HEADLESS-MODE-AUTO-MEMORY-DISABLE]] 的主題相同：環境變數不是全域修復魔法，而是針對子進程行為建立一條可控的邊界。

### 二、技術防禦架構（What）

#### 1. 環境變數的單向傳遞特性

Unix 與 Windows 的環境變數傳遞是父進程到子進程的單向複製：

```text
Terminal / Shell
    │ export DISABLE_AUTOUPDATER=1
    ▼
Claude Code 子進程
    │ 只能讀到父進程給它的環境
    ▼
無法修改父進程或其他同輩分頁
```

也可以只針對單次命令使用：

```bash
DISABLE_AUTOUPDATER=1 claude
```

#### 2. 終端多路復用的防自殺機制

傳統架構中，GUI 終端機是父進程，Claude Code 是子進程。關閉視窗等於殺掉子進程。

```text
傳統模式

Ghostty / WezTerm / Terminal
    └── shell
        └── claude

關閉終端視窗 -> shell 與 claude 一起結束
```

引入 tmux / psmux 後，工作階段由背景 server 持有：

```text
持久化模式

tmux server / psmux server
    └── shell
        └── claude

Ghostty / Alacritty / Windows Terminal
    └── tmux client

關閉終端視窗 -> 只斷開 client；server 與 claude 繼續跑
```

這個設計讓「清空終端 App 記憶體」與「保留 AI CLI 任務」不再衝突。關閉或重啟終端 App 只是重建顯示端，底層任務不受影響。這也和 [[2026-05-30-MOSHI-MOBILE-TERMINAL-FOR-CODING-AGENTS]] 的核心相同：長時間 agent 任務應該活在 tmux 類 daemon 裡，而不是綁死在單一前景視窗。

### 三、實戰處置與配置指南（How）

#### 1. Ghostty + Claude Code 即時止血

macOS 緊急釋放快取：

```bash
sudo purge
```

停用 Claude Code 自動更新：

```bash
echo 'export DISABLE_AUTOUPDATER=1' >> ~/.zshrc
source ~/.zshrc
```

限制 Ghostty scrollback：

```ini
# ~/.config/ghostty/config
scrollback-limit = 10000
```

> [!warning] `sudo purge` 不是根治
> 這只是要求系統回收可回收快取，若底層是應用程式洩漏或子進程持續成長，記憶體仍會再次升高。

#### 2. tmux 常用高頻指令

tmux 的預設前綴鍵（Prefix）是 `Ctrl + b`。以下快捷鍵皆為先按 `Ctrl + b`、放開後再按下一個鍵。

##### Session：一般 shell 中執行

| 操作 | 指令 |
|------|------|
| 建立並命名新 session | `tmux new -s <session_name>` |
| 查看所有背景 session | `tmux ls` |
| 連回指定 session | `tmux a -t <session_name>` |
| 安全脫離目前 session | `Ctrl + b` → `d` |
| 刪除指定 session | `tmux kill-session -t <session_name>` |

##### Window：tmux 內使用

| 操作 | 快捷鍵 |
|------|--------|
| 建立新視窗 | `Ctrl + b` → `c` |
| 下一個視窗 | `Ctrl + b` → `n` |
| 上一個視窗 | `Ctrl + b` → `p` |
| 互動式選單切換視窗 / session | `Ctrl + b` → `w` |
| 重新命名目前視窗 | `Ctrl + b` → `,` |
| 關閉目前視窗 | `Ctrl + b` → `&` |

##### Pane：tmux 內使用

| 操作 | 快捷鍵 |
|------|--------|
| 左右分割 | `Ctrl + b` → `%` |
| 上下分割 | `Ctrl + b` → `"` |
| 移動窗格焦點 | `Ctrl + b` → `方向鍵` |
| 最大化 / 還原目前窗格 | `Ctrl + b` → `z` |
| 關閉目前窗格 | `Ctrl + b` → `x` |

##### `~/.tmux.conf` 建議設定

```tmux
# 啟用滑鼠支援：滾動歷史、點擊切換窗格與調整大小
set -g mouse on

# 修正 macOS 剪貼簿與現代終端機 alternate screen 滾動快取相容性
set -g terminal-overrides 'xterm*:smcup@:rmcup@'
```

套用設定：

```text
Ctrl + b -> :
source-file ~/.tmux.conf
```

#### 3. Windows 原生環境持久化方案

若是 Windows 原生 PowerShell / CMD 環境，報告建議避免把所有職責塞進一個終端 App 的分頁與 named pipe 設計中，改採職責分離：

| 方案 | 適用情境 | 核心想法 |
|------|----------|----------|
| Alacritty + psmux | 追求純 GPU 渲染與原生 ConPTY 工作階段持久化 | Alacritty 負責畫面，psmux 負責 session |
| Windows Terminal Preview | 需要官方生態與 DirectX / Atlas 渲染路線 | 用微軟官方終端吸收大量 TUI 輸出 |

psmux 安裝與啟動範例：

```powershell
winget install psmux
pmux new-session -s claude-work
```

> [!note] 指令名稱待確認
> 報告同時提到 `psmux` 與 `pmux new-session`。正式採用前應確認實際 CLI 名稱與目前 release 文件。

## 我的心得（My Takeaways）

這份報告最實用的部分不是某一個終端機的 bug，而是「把顯示端、工作階段、AI CLI 行為控制」拆成三層來看：

1. **顯示端**：Ghostty、WezTerm、Alacritty、Windows Terminal 負責渲染與輸入。
2. **工作階段層**：tmux / psmux 負責持久化與復原。
3. **AI CLI 行為層**：環境變數、設定檔、auto updater、memory、scrollback 共同決定資源曲線。

如果只換終端機，可能只是把問題推遲；如果只設定環境變數，仍然無法解決視窗關閉造成任務死亡。穩定的做法是三層一起處理：限制 scrollback、關閉已知高風險背景模組、把長任務放到 tmux / psmux 中。

## 待補充（Open Questions）

- Ghostty 的 PageList / glyph cache 記憶體問題在目前最新 release 是否已修復？建議搜尋：`Ghostty PageList multi-codepoint memory leak`
- `DISABLE_AUTOUPDATER=1` 對 Claude Code 目前版本是否仍有效？是否已有官方替代設定？建議搜尋：`Claude Code DISABLE_AUTOUPDATER memory leak`
- 報告引用的 Claude Code issue 編號 `#51077` 是否存在於 Anthropic 官方公開 repo？若不存在，實際對應討論在哪？建議搜尋：`Claude Code memory leak auto updater issue`
- psmux 的實際 CLI 名稱、穩定度、session recovery 行為是否與 tmux 對齊？建議搜尋：`psmux Windows ConPTY tmux alternative`
- `terminal-overrides 'xterm*:smcup@:rmcup@'` 在 Ghostty / WezTerm / Alacritty 的副作用是否一致？建議搜尋：`tmux smcup rmcup alternate screen scrollback`

## 相關連結（Related）

- [[2026-03-20-WEZTERM-SESSION-TECHNICAL-SUMMARY]] — WezTerm 工作階段與 mux server 的既有技術摘要，可補足終端多工層的背景。
- [[2026-03-20-WEZTERM-MACOS-DICTATION-BUILD-AND-CJK-FIX]] — 同樣處理終端機渲染、CJK 字形與 macOS 輸入邊界問題。
- [[2026-05-30-MOSHI-MOBILE-TERMINAL-FOR-CODING-AGENTS]] — Moshi 也把 tmux 視為長時間 AI agent 任務的持久化基礎。
- [[2026-05-16-CLAUDE-CODE-HEADLESS-MODE-AUTO-MEMORY-DISABLE]] — 環境變數控制 Claude Code 子進程行為的相鄰案例。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | 必記概念：Memory Leak、glyph cache、scrollback-limit、environment variable、tmux daemon、psmux、ConPTY、alternate screen |
| **理解（半被動）** | 解釋概念的含義及關聯 | 終端機 RAM 暴增可能來自渲染快取、子進程歸帳、AI CLI 背景模組或 scrollback；tmux / psmux 透過 daemon 把工作階段從 GUI 視窗中解耦 |
| **分析（主動）** | 檢驗論點、拆解流程、找出假設 | 關鍵假設有三個：Ghostty 問題仍存在、Claude Code 自動更新仍可用 `DISABLE_AUTOUPDATER` 控制、psmux 已足夠穩定。三者都需要用當前版本驗證 |
| **應用（主動）** | 將知識套用情境，規劃執行方案 | 1. 先把 Claude Code 長任務搬進 tmux；2. 對 Ghostty 設 scrollback limit 並重啟觀察記憶體曲線；3. 用環境變數關閉可疑背景模組後做 A/B 對照 |
| **評估（主動）** | 判斷多個方案的優劣，進行決策和權衡 | Ghostty + tmux 適合想保留 Ghostty 體驗但降低風險；Alacritty + psmux 適合 Windows 原生效能優先；Windows Terminal Preview 適合穩定與官方生態優先。若需求是遠端 babysit agent，Moshi + tmux 是不同層級的補充 |

### 分析型追問（Socratic Follow-up）

- **澄清**：本文中的「記憶體洩漏」哪些是確定無法回收的 leak，哪些只是 cache 或子進程歸帳？
- **假設**：若 Claude Code 自動更新 bug 已在新版本修復，本文的最佳止血方案是否應改為版本升級而不是永久停用 updater？
- **證據**：是否有可重現 benchmark：同一個 Claude Code 任務在 Ghostty / WezTerm / Alacritty / Windows Terminal 下的 RAM 曲線比較？
- **觀點**：站在終端機開發者角度，應該優先限制 scrollback、修 glyph cache，還是提示使用者使用 tmux 類持久化工具？
- **後果**：若長期停用自動更新，12 個月後可能累積安全修補缺口或相容性問題，如何建立手動更新節奏？

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 把所有記憶體異常都歸因於終端機或 Claude Code 單一 bug，導致忽略子進程、Language Server、watcher、scrollback 與字型快取的綜合影響。
2. **什麼情況下會失敗？** — 若真正耗 RAM 的是 project watcher、Language Server 或 node 子進程，`sudo purge`、scrollback limit 與換終端機都只能緩解表象；若使用者沒有養成 tmux detach / attach 習慣，持久化方案也會失效。
3. **有沒有更好的替代方案？** — 更嚴謹的方案是建立觀測流程：固定任務、固定終端、記錄 parent/child RSS、逐一切換變因（updater、scrollback、tmux、terminal）。只有確認瓶頸後再決定要換終端、關 updater、還是拆子進程。

## References

- [Ghostty 官方網站](https://ghostty.org/)
- [Kitty GitHub 倉庫](https://github.com/kovidgoyal/kitty)
- [WezTerm GitHub 倉庫](https://github.com/wez/wezterm)
- [Alacritty GitHub 倉庫](https://github.com/alacritty/alacritty)
- [Windows Terminal GitHub 倉庫](https://github.com/microsoft/terminal)
- [tmux GitHub 倉庫](https://github.com/tmux/tmux)
- [psmux GitHub 倉庫](https://github.com/psmux/psmux)
- [Ghostty 內存洩漏與 PageList 討論（原報告列出）](https://github.com/zigcc/forum/issues/300)
- [Claude Code 內存洩漏災情（原報告列出）](https://github.com/anthropics/claude-code/issues/51077)
