---
title: "PSA：你的 Claude Code 外掛（Plugin）可能一直重複載入，正在耗盡你的上下文視窗（Context Window）"
date: 2026-03-02
category: DevTools
tags:
  - "#tools/claude-code"
  - "#ai/context-optimization"
  - "#productivity/debugging"
source: "https://www.reddit.com/r/ClaudeAI/comments/1rij9tr/psa_your_claude_code_plugins_are_probably_loading/"
source_type: article
author: "Massfeller (Reddit)"
status: notes
links:
  - "[[CLAUDE-CODE-SKILLS]]"
  - "[[MCP-CONTEXT-MANAGEMENT]]"
  - "[[CONTEXT-COMPACTION]]"
---

## 摘要（Summary）

Claude Code 的外掛（Plugin）系統存在兩個已知臭蟲（Bug），導致所有技能（Skill）在系統提示（System Prompt）中重複出現，嚴重消耗上下文視窗（Context Window），造成壓縮（Compaction）過早觸發。本文提供診斷腳本與修復方案，修復後可減少 **50–60% 的前置開銷（Preamble Overhead）**。

## 關鍵洞察（Key Insights）

- **臭蟲一：舊版快取（Stale Cache）** — 外掛更新後，舊版目錄殘留在 `~/.claude/plugins/cache/`，Claude Code 會掃描所有版本而非只用最新版，導致每個技能重複出現
- **臭蟲二：提示建構（Prompt Construction）** — 即使只有一個快取目錄，技能注入程式碼本身就會把每個技能登錄兩次（#29520 確認）
- **符號連結（Symlink）問題** — 外掛安裝時在 `~/.claude/skills/` 建立指向快取的符號連結，導致技能被發現兩次（一次為 "user"，一次為外掛名稱）
- **MCP 工具（Tool）** — Gmail、GCal 等雲端 MCP 連接器每次 session 都無條件載入，`/context` 卻不顯示其 token 開銷
- **`ENABLE_TOOL_SEARCH`** — 隱藏實驗性旗標，可將 MCP 工具定義延遲（Defer）載入，節省約 32K tokens，但不影響技能重複問題

> [!warning] 注意事項（Watch Out）
> 清除舊版快取後重啟，技能仍可能重複出現——因為這是兩個獨立臭蟲，快取清理只解決其一。

> [!tip] 可執行建議（Actionable Tip）
> 停用當前專案不需要的外掛：編輯 `~/.claude/settings.json` → `enabledPlugins`，以及斷開未使用的 MCP 連接器（如 Gmail、GCal）。

## 詳細內容（Details）

### 診斷：確認是否受影響（30 秒）

**檢查一：舊版外掛**

```bash
for d in ~/.claude/plugins/cache/claude-plugins-official/*/; do
    name=$(basename "$d")
    count=$(ls -d "$d"*/ 2>/dev/null | wc -l)
    if [ "$count" -gt 1 ]; then
        echo "AFFECTED: $name has $count versions (should be 1)"
        ls -d "$d"*/
    fi
done
```

**檢查二：重複符號連結（Duplicate Symlinks）**

```bash
ls -la ~/.claude/skills/ 2>/dev/null | grep -c "plugins/"
# 若回傳數字 > 0，表示有符號連結重複問題
```

**檢查三：在 session 內執行**

執行 `/context` 查看 Skills 表格。若每個技能出現兩次，表示已受影響。

### 修復方案

**修復舊版快取：**

```bash
python3 << 'EOF'
import json, os, shutil

with open(os.path.expanduser("~/.claude/plugins/installed_plugins.json")) as f:
    data = json.load(f)

cache = os.path.expanduser("~/.claude/plugins/cache/claude-plugins-official")

for full_name, installs in data["plugins"].items():
    plugin = full_name.split("@")[0]
    active = installs[0]["version"]
    plugin_dir = os.path.join(cache, plugin)
    if os.path.isdir(plugin_dir):
        for ver in os.listdir(plugin_dir):
            path = os.path.join(plugin_dir, ver)
            if os.path.isdir(path) and ver != active:
                print(f"Removing stale: {plugin}/{ver}")
                shutil.rmtree(path)
EOF
```

**修復重複符號連結：**

```bash
# 移除 skills/ 中指向 plugins/ 的符號連結（外掛登錄自行處理發現）
find ~/.claude/skills/ -type l -lname "*/plugins/*" -delete 2>/dev/null
```

修復後重啟 Claude Code。

### 其他上下文節省方法

| 問題 | 影響 | 解決方式 |
|------|------|---------|
| 未使用外掛仍載入工具定義 | 每個外掛多耗數百至數千 tokens | 在 `settings.json` 的 `enabledPlugins` 停用不需要的 |
| 雲端 MCP 連接器無條件載入 | Gmail 6 個工具 + GCal 9 個工具 = 15 個工具定義 | 斷開未主動使用的 MCP 連接器 |
| MCP 開銷隱藏於 `/context` | `/context` 顯示 13%，實際 `/doctor` 警告約 40K tokens | 使用 `enable_tool_search` 旗標延遲載入 |
| 權限（Permission）條目累積 | `.claude/settings.local.json` 可能有 100+ 條目 | 在寬鬆（Permissive）模式下可安全清除 |

> [!note] `enable_tool_search` 旗標
> 現在可在 `~/.claude/settings.json` 中設定 `enable_tool_search`（正式文件：https://code.claude.com/docs/en/mcp）。當 MCP 工具超過上下文 10% 時自動啟用。**只延遲 MCP 工具定義，不影響技能重複臭蟲。**

### 已知 GitHub Issues 追蹤（18+ 個報告，橫跨 4 個月）

**技能/外掛重複（Skill/Plugin Duplication）：**

| Issue | 狀態 |
|-------|------|
| [#27721](https://github.com/anthropics/claude-code/issues/27721) Skills from plugins registered twice | **OPEN — 無受理人，無回應** |
| [#29520](https://github.com/anthropics/claude-code/issues/29520) Plugin skills duplicated | Open（重複） |
| [#23819](https://github.com/anthropics/claude-code/issues/23819) Plugin symlinks cause duplicate slash commands | **OPEN** |

**MCP 上下文開銷：**

| Issue | 狀態 |
|-------|------|
| [#20412](https://github.com/anthropics/claude-code/issues/20412) 雲端 MCP 自動注入，造成 OOM | **OPEN** |
| [#28660](https://github.com/anthropics/claude-code/issues/28660) Skill injection O(n) per tool call | **OPEN** |
| [#21966](https://github.com/anthropics/claude-code/issues/21966) MCP 工具開銷隱藏於 `/context` | **OPEN** |

> [!important] 根本問題（Root Issue）
> 整體模式：**無去重（No Deduplication）、無清理（No Cleanup）、無作用域（No Scoping）、無可見性（No Visibility）**。核心追蹤 issue：[#27721](https://github.com/anthropics/claude-code/issues/27721)。

### 兩個獨立臭蟲的實證

作者清除舊版快取後重啟，技能仍然重複：

| 外掛 | 快取版本數 | 清理後仍重複？ |
|------|-----------|--------------|
| claude-md-management | **1 個版本** | 是（2x） |
| claude-code-setup | **1 個版本** | 是（2x） |
| superpowers | 2 個版本（舊版） | 是（仍 2x） |
| commit-commands | 3 個版本（舊版） | 是（仍 2x） |

## 我的心得（My Takeaways）

這篇文章直接解釋了為什麼每次 session 的技能（Skill）數量看起來比安裝的還多。修復步驟：

1. 執行舊版快取清理腳本
2. 執行符號連結清理
3. 在 `settings.json` 停用當前專案不需要的外掛
4. 斷開未使用的 MCP 連接器（Gmail、GCal）

在 `/context` 指令的 Skills 區塊確認改善效果。**臭蟲二（提示建構）需等待 Anthropic 修復，目前無法從使用者端完全解決。**

## 相關連結（Related）

- [[CLAUDE-CODE-SKILLS]] — Claude Code 技能系統架構與設計
- [[MCP-CONTEXT-MANAGEMENT]] — MCP 工具上下文管理策略
- [[CONTEXT-COMPACTION]] — 上下文壓縮（Context Compaction）機制與觸發條件

## References

- [原文 Reddit 貼文](https://www.reddit.com/r/ClaudeAI/comments/1rij9tr/psa_your_claude_code_plugins_are_probably_loading/)
- [GitHub Issue #27721 — 根本問題](https://github.com/anthropics/claude-code/issues/27721)
- [GitHub Issue #29971 — 綜合追蹤](https://github.com/anthropics/claude-code/issues/29971)
- [Claude Code MCP 文件](https://code.claude.com/docs/en/mcp)
