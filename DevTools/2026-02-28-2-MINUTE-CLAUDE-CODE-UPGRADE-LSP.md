---
title: "2 分鐘啟用 Claude Code LSP：你可能錯過的最重要升級"
date: 2026-02-28
category: DevTools
tags:
  - "#tools/claude-code"
  - "#ai/code-intelligence"
  - "#tools/lsp"
  - "#productivity/developer-experience"
source: "https://karanbansal.in/blog/claude-code-lsp/"
source_type: article
author: "Karan Bansal"
status: notes
links:
  - "[[CLAUDE-CODE-SKILLS]]"
  - "[[LANGUAGE-SERVER-PROTOCOL]]"
  - "[[CLAUDE-CODE-PERFORMANCE]]"
---

## 摘要（Summary）

Claude Code 預設不啟用 LSP（Language Server Protocol），導致所有程式碼導覽都依賴 `grep` 文字搜索——每次查詢耗時 30–60 秒，且容易搜出數百個不相關結果。啟用 LSP 後，同樣的查詢（如「processPayment 定義在哪？」）只需 **50 毫秒**，準確率 100%。設定只需 2 分鐘，一次即可，效能差異極為顯著。

## 關鍵洞察（Key Insights）

- **LSP vs Grep 的根本差異**：grep 把程式碼當文字，LSP 理解程式碼的結構與語意——這是 IDE 優於記事本的同一條鴻溝，現在也決定了 AI 助手的能力上限
- **`ENABLE_LSP_TOOL` 環境變數未正式記錄**，是透過社群在 GitHub Issue #15619 發現的，截至 2026 年 2 月仍如此
- **被動診斷（Passive Diagnostics）是最高價值功能**：每次編輯後 LSP 自動推送錯誤，Claude 在同一輪次內修復——消除「編輯→看錯誤→再問 Claude→再修」的迭代循環
- **LSP 伺服器啟動時就立即索引整個專案**，不需先開啟檔案，因此首次查詢就已是「熱索引（Warm Index）」狀態
- **即使設定完成，Claude 可能仍習慣用 grep**，需要在 `CLAUDE.md` 或 Auto Memory 中明確指示優先使用 LSP

> [!warning] 注意事項（Watch Out）
> 「已安裝但未啟用」是最常見的失敗原因。`claude plugin list` 確認 `Status: enabled`，若為 `disabled` 需執行 `claude plugin enable <name>` 並重啟。

> [!important] `ENABLE_LSP_TOOL` 旗標
> 此為**非官方文件的實驗性旗標**，可能在未來版本中更改或自動啟用。需在 `~/.claude/settings.json` 的 `"env"` 區塊中設定。

## 詳細內容（Details）

### 為何需要 LSP：效能差距

**不用 LSP 的搜索流程：**
- 搜尋 `User` → 847 個結果，橫跨 203 個檔案
- Claude 必須逐一讀取篩選 → 30–60 秒
- 結果不保證找到正確的那一個

**使用 LSP 的搜索流程：**
- `goToDefinition("User")` → `user-service.ts` 第 42 行
- 耗時：~50ms，準確率：100%
- 速度差距：約 **900 倍**

### 安裝步驟（2 分鐘）

**步驟一：啟用 LSP 工具**

在 `~/.claude/settings.json` 加入：

```json
{
  "env": {
    "ENABLE_LSP_TOOL": "1"
  }
}
```

同時建議在 shell profile（`~/.zshrc` 或 `~/.bashrc`）加入備用設定：
```bash
export ENABLE_LSP_TOOL=1
```

**步驟二：安裝語言伺服器（Language Server）二進位檔**

| 語言 | 外掛名稱 | 安裝指令 |
|------|---------|---------|
| Python | `pyright-lsp` | `npm i -g pyright` |
| TypeScript/JS | `typescript-lsp` | `npm i -g typescript-language-server typescript` |
| Go | `gopls-lsp` | `go install golang.org/x/tools/gopls@latest` |
| Rust | `rust-analyzer-lsp` | `rustup component add rust-analyzer` |
| Java | `jdtls-lsp` | `brew install jdtls` |
| C/C++ | `clangd-lsp` | `brew install llvm` |
| C# | `csharp-lsp` | `dotnet tool install -g csharp-ls` |
| PHP | `php-lsp` | `npm i -g intelephense` |
| Swift | `swift-lsp` | 內建於 Xcode |

**步驟三：安裝並啟用外掛（Plugin）**

```bash
# 更新市集目錄
claude plugin marketplace update claude-plugins-official

# 安裝所需語言的外掛（以 Python + TypeScript 為例）
claude plugin install pyright-lsp
claude plugin install typescript-lsp

# 確認已啟用
claude plugin list
```

`settings.json` 完整範例：

```json
{
  "env": {
    "ENABLE_LSP_TOOL": "1"
  },
  "enabledPlugins": {
    "pyright-lsp@claude-plugins-official": true,
    "typescript-lsp@claude-plugins-official": true,
    "gopls-lsp@claude-plugins-official": true
  }
}
```

**步驟四：重啟 Claude Code**

LSP 伺服器在啟動時初始化。完整重啟後，詢問 Claude「某個變數的型別是什麼？」——若它使用 LSP `hover` 而非讀取檔案，即表示設定成功。

### 啟動時序：實際 Debug 日誌

```
# 來自 ~/.claude/debug/ — 2026-02-23 session

05:53:56.216  [LSP MANAGER] Starting async initialization
05:53:56.573  Total LSP servers loaded: 4
05:53:56.757  gopls initialized          (+0.5s)
05:53:56.762  typescript initialized     (+0.5s)
05:53:56.819  pyright initialized        (+0.6s)
05:54:04.791  jdtls initialized          (+8.6s)
              Index is warm — all LSP operations now ~50ms
```

> [!note] Java 伺服器（jdtls）
> 因 JVM 預熱（Warmup）需要約 8.6 秒，這是正常現象，不是臭蟲。其餘語言伺服器啟動時間約 0.5–0.6 秒。

### LSP 提供的能力

**被動（Passive）— 自動診斷：**
- 每次編輯後，語言伺服器推送型別錯誤、未定義變數、缺少 import
- Claude 在**同一輪次**內看到這些錯誤並修復，使用者看到的結果已零錯誤
- 例：新增 `email` 參數到 `createUser()` → LSP 立即報告 3 個呼叫端（Call Site）錯誤 → Claude 一次全部修復

**主動（Active）— 按需查詢：**

| 你說... | Claude 使用... |
|---------|--------------|
| "authenticate 定義在哪？" | `goToDefinition` |
| "找所有使用 UserService 的地方" | `findReferences` |
| "response 的型別是什麼？" | `hover` |
| "auth.ts 裡有哪些函式？" | `documentSymbol` |
| "找 PaymentService 類別" | `workspaceSymbol` |
| "什麼實作了 AuthProvider？" | `goToImplementation` |
| "誰呼叫 processPayment？" | `incomingCalls` |
| "handleOrder 呼叫了什麼？" | `outgoingCalls` |

### 讓 Claude 優先使用 LSP：CLAUDE.md 設定

加入以下內容到 `~/.claude/CLAUDE.md`（全域生效）或專案的 `CLAUDE.md`：

```markdown
### Code Intelligence

Prefer LSP over Grep/Glob/Read for code navigation:
- `goToDefinition` / `goToImplementation` to jump to source
- `findReferences` to see all usages across the codebase
- `workspaceSymbol` to find where something is defined
- `documentSymbol` to list all symbols in a file
- `hover` for type info without reading the file
- `incomingCalls` / `outgoingCalls` for call hierarchy

Before renaming or changing a function signature, use
`findReferences` to find all call sites first.

Use Grep/Glob only for text/pattern searches (comments,
strings, config values) where LSP doesn't help.

After writing or editing code, check LSP diagnostics before
moving on. Fix any type errors or missing imports immediately.
```

### 常見問題排查

| 問題 | 原因 | 解決方式 |
|------|------|---------|
| LSP 工具完全不出現 | `ENABLE_LSP_TOOL` 未設定 | 加入 `settings.json` 的 `"env"` 區塊，重啟 |
| "Plugin not found in any marketplace" | 市集目錄過舊 | `claude plugin marketplace update claude-plugins-official` |
| 外掛已安裝但未作用 | 安裝後未啟用 | `claude plugin enable <name>` + 重啟 |
| "Executable not found in $PATH" | 二進位檔未安裝或不在 PATH | 安裝後執行 `which <binary>` 確認 |
| "Total LSP servers loaded: 0" | 外掛全部禁用 | 啟用外掛後重啟 |

**Debug 檢查清單：**
1. 確認二進位檔已安裝：`which pyright-langserver`
2. 確認外掛狀態：`claude plugin list` → 看 `Status: enabled`
3. 查看 debug 日誌：`~/.claude/debug/latest` → 搜尋 `Total LSP servers loaded: N`（N 應 > 0）

> [!tip] 查看即時診斷
> 按 `Ctrl+O` 可查看 LSP 伺服器正在推送的診斷訊息，即時掌握語言伺服器的狀態。

## 我的心得（My Takeaways）

LSP 設定立即執行。關鍵操作清單：

1. 在 `~/.claude/settings.json` 加入 `"ENABLE_LSP_TOOL": "1"`
2. 安裝常用語言的伺服器二進位檔（Python → pyright，TypeScript → typescript-language-server）
3. `claude plugin install pyright-lsp typescript-lsp`（依需要替換）
4. 在 `~/.claude/CLAUDE.md` 加入 LSP 優先指示，確保 Claude 不會退回 grep

最有價值的功能是**被動診斷**——重構時新增參數，Claude 在同一輪次內自動修復所有呼叫端，不需要我手動迭代。

注意：此旗標（`ENABLE_LSP_TOOL`）目前非官方文件，未來版本可能改變。但根據文章資訊，截至 2026 年 2 月仍有效。

## 相關連結（Related）

- [[CLAUDE-CODE-SKILLS]] — Claude Code 技能系統，LSP 外掛亦屬其中
- [[LANGUAGE-SERVER-PROTOCOL]] — LSP 的設計原理與 M×N → M+N 的架構優勢
- [[CLAUDE-CODE-PERFORMANCE]] — Claude Code 效能優化，含 Plugin 重複載入問題

## References

- [原文](https://karanbansal.in/blog/claude-code-lsp/)
- [GitHub Issue #15619 — ENABLE_LSP_TOOL 發現來源](https://github.com/anthropics/claude-code/issues/15619)
