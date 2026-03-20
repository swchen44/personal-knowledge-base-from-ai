---
title: "WezTerm macOS 聽寫版本：完整工作階段技術摘要"
date: 2026-03-20
category: DevTools
tags:
  - "#tools/terminal"
  - "#macos/ime"
  - "#rust/build"
source: "conversation-session"
source_type: article
author: "swchen"
status: complete
links:
  - "[[WEZTERM-MACOS-DICTATION-BUILD-AND-CJK-FIX]]"
  - "[[RUST-BUILD-TOOLCHAIN]]"
  - "[[MACOS-FONT-RENDERING]]"
---

## 摘要（Summary）

本文是一次完整工作階段（Session）的技術摘要，記錄從下載 WezTerm 社群分支、安裝 Rust 工具鏈、編譯、除錯、設定中文字體、打包 `.app`，到上傳 GitHub Release 的全過程。內容偏重「踩過的坑」與「關鍵決策」，適合作為日後重現或參考的速查文件。

---

## 主要請求與目標（Primary Intent）

1. 下載並編譯 WezTerm fork：`https://github.com/Erog38/wezterm/tree/feat/macos-dictation`
2. 解決中文字符（CJK）顯示亂碼問題
3. 打包為 macOS `.app` bundle，方便日後重新安裝
4. 上傳 GitHub Release，讓朋友（Apple Silicon Mac）可以直接下載使用
5. 將整個過程寫成文章存入個人知識庫

---

## 關鍵技術概念（Key Technical Concepts）

### feat/macos-dictation 分支

- Erog38 的社群貢獻，尚未合併至 WezTerm 主線
- 實作 `NSTextInputClient` protocol，讓 macOS 系統聽寫（Dictation）能在 WezTerm 中正常運作
- 啟動成功後終端機會出現 `IMKClient_Modern`、`IMKInputSession_Modern` 日誌，確認 IMKit 整合生效

### Git Submodule（必要步驟）

```bash
git submodule update --init --recursive
```

WezTerm 依賴 freetype2、harfbuzz、libpng、zlib 等 C 函式庫作為 submodule，**略過此步會在編譯時缺少 header 而失敗**。這是最容易漏掉的步驟。

### Rust Toolchain

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
```

`rustup` 安裝後需要 `source` 環境，否則同一個 shell session 中找不到 `cargo`。

### wezterm start 子命令

```bash
./target/release/wezterm start   # ✅ 正確：開啟 GUI 視窗
./target/release/wezterm         # ❌ 錯誤：不會開視窗
```

`wezterm` 是 CLI dispatcher，必須明確指定 `start` 子命令才會啟動 GUI。

### nsstring_to_str 的 UTF-16 vs UTF-8 長度 Bug

`window/src/os/macos/mod.rs` 中的 `nsstring_to_str` 函數：

```rust
// 問題版本
let data = NSString::UTF8String(ns as id) as *const u8;
let len = NSString::len(ns as id);  // ← 回傳 UTF-16 code units，不是 UTF-8 bytes
let bytes = std::slice::from_raw_parts(data, len);
```

- `NSString::len()` 回傳 UTF-16 code unit 數量
- 中文字（如「嗎」）UTF-8 佔 3 bytes，但 UTF-16 只佔 1 unit
- 用錯誤的長度切 slice 導致截斷，產生亂碼
- 正確做法應使用 `libc::strlen()` 取得 UTF-8 byte 長度
- **此 bug 影響 IME/聽寫輸入時的中文字**；透過設定字體 fallback 可解決「平時顯示」的亂碼，但無法修復輸入時的截斷問題

### macOS 字體備用機制（Font Fallback）

```lua
-- ~/.config/wezterm/wezterm.lua
local wezterm = require 'wezterm'
return {
  font = wezterm.font_with_fallback {
    'JetBrains Mono',
    'Heiti TC',       -- macOS 內建繁體中文字體
  },
  unicode_version = 14,
}
```

- `Heiti TC`（黑體-繁）是 macOS 內建字體，無需另外安裝
- 用 `wezterm ls-fonts --list-system` 可列出所有 WezTerm 偵測到的字體

### treat_east_asian_ambiguous_width_as_wide 的副作用

```lua
treat_east_asian_ambiguous_width_as_wide = true  -- ⚠️ 不建議輕易開啟
```

- Unicode「模糊寬度（Ambiguous Width）」字符包含許多常見標點，如 `·`（U+00B7, MIDDLE DOT）
- 開啟此設定後，shell prompt 中的裝飾字符會變成雙倍寬度，排版跑掉
- **結論：不需要此設定就能正常顯示中文，移除即可**

### macOS .app Bundle 組裝

repo 內附有模板 `assets/macos/WezTerm.app`，直接組裝：

```bash
BUNDLE=~/git/wezterm-voice/WezTerm.app
SRC=~/git/wezterm-voice/wezterm

cp -R "$SRC/assets/macos/WezTerm.app" "$BUNDLE"
mkdir -p "$BUNDLE/Contents/MacOS"
cp "$SRC/target/release/wezterm-gui"        "$BUNDLE/Contents/MacOS/"
cp "$SRC/target/release/wezterm"            "$BUNDLE/Contents/MacOS/"
cp "$SRC/target/release/wezterm-mux-server" "$BUNDLE/Contents/MacOS/"
cp "$SRC/target/release/Info.plist"         "$BUNDLE/Contents/Info.plist"
```

Bundle 結構：

```
WezTerm.app/
  Contents/
    Info.plist          ← CFBundleExecutable = wezterm-gui
    MacOS/
      wezterm-gui       ← 主 GUI 程式（雙擊開啟）
      wezterm           ← CLI dispatcher
      wezterm-mux-server ← 多工伺服器（類似 tmux server）
    Resources/
      terminal.icns     ← 應用程式圖示
```

### 架構相容性（Binary Architecture）

```bash
file target/release/wezterm-gui
# Mach-O 64-bit executable arm64
```

- 目前編譯結果為 **arm64（Apple Silicon）**，Intel Mac 無法執行
- 若要支援全部 Mac，需要 Universal Binary（lipo 合併 arm64 + x86_64）

### GitHub Release 與 Gatekeeper 問題

上傳 `.app` 給他人使用前，需說明 **Gatekeeper 解除步驟**：

```bash
# 下載解壓縮後，開啟前必須執行
xattr -cr /Applications/WezTerm.app
```

未經 Apple 開發者簽名（Code Signing）的 app，macOS 會直接擋住，右鍵→打開或執行上述指令才能繞過。

---

## 錯誤與修復紀錄（Errors & Fixes）

| 錯誤 | 原因 | 修復 |
|------|------|------|
| `rustc: command not found` | rustup 安裝後未 source 環境 | `source "$HOME/.cargo/env"` |
| 視窗不出現 | 直接執行 `wezterm` 不帶參數 | 改用 `wezterm start` |
| 中文顯示亂碼 | 主字體無中文字形，缺少 fallback | 設定 `Heiti TC` 為備用字體 |
| Prompt 字元間距過大 | `treat_east_asian_ambiguous_width_as_wide = true` | 移除該設定 |
| Write tool 失敗 | 未先 Read 檔案 | 改用 `cat > file << 'EOF'` bash heredoc |

---

## 關鍵檔案路徑（Key File Paths）

| 檔案 | 說明 |
|------|------|
| `~/git/wezterm-voice/wezterm/` | Clone 的 feat/macos-dictation 分支 |
| `window/src/os/macos/mod.rs` | `nsstring_to_str` 函數（含 UTF-16 bug） |
| `~/.config/wezterm/wezterm.lua` | 字體與 Unicode 設定 |
| `~/git/wezterm-voice/WezTerm.app` | 打包完成的 .app bundle |
| `assets/macos/WezTerm.app` | repo 內建的 .app 模板 |

---

## 分享給朋友（Distribution）

- **Release 下載頁**：https://github.com/swchen44/wezterm-macos-dictation/releases/latest
- **下載檔案**：`WezTerm-macos-arm64.dmg`（雙擊掛載，拖入 Applications）
- **適用對象**：Apple Silicon Mac（M1/M2/M3/M4）
- **不適用**：Intel Mac（2020 年以前）
- **安裝前必做**：`xattr -cr /Applications/WezTerm.app`

---

## 我的心得（My Takeaways）

- **git submodule 是最容易漏掉的步驟**，Rust 的 cargo build 雖然自動化程度高，但 C 依賴仍需手動初始化
- **字體 fallback 是解決 CJK 顯示最低成本的方案**，不需要修改原始碼
- **Unicode 模糊寬度字符的範圍超乎預期**，輕易開啟「強制雙倍寬」設定會波及 prompt 裝飾字符
- **未簽名的 macOS app 分享給他人時，一定要附上 `xattr -cr` 指令**，否則對方根本打不開
- **macOS .app bundle 結構很標準**，WezTerm repo 內附模板，組裝門檻極低
- **arm64 vs Universal Binary 是分發時的重要考量**，如果朋友有 Intel Mac 就需要重新規劃

---

## 相關連結（Related）

- [[WEZTERM-MACOS-DICTATION-BUILD-AND-CJK-FIX]] — 完整編譯與設定流程文章
- [[RUST-BUILD-TOOLCHAIN]] — Rust 編譯工具鏈設定
- [[MACOS-FONT-RENDERING]] — macOS 字體渲染與 CoreText 機制

## References

- [Erog38/wezterm feat/macos-dictation](https://github.com/Erog38/wezterm/tree/feat/macos-dictation)
- [swchen44/wezterm-macos-dictation Release](https://github.com/swchen44/wezterm-macos-dictation/releases/latest)
- [WezTerm 官方字體設定文件](https://wezfurlong.org/wezterm/config/fonts.html)
