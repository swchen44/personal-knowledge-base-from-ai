---
title: "從源碼編譯 WezTerm macOS 聽寫分支，並解決中文字型顯示問題"
date: 2026-03-20
category: DevTools
tags:
  - "#tools/terminal"
  - "#tools/cli"
  - "#macos/ime"
source: "https://github.com/Erog38/wezterm/tree/feat/macos-dictation"
source_type: article
author: "swchen"
status: notes
links:
  - "[[WEZTERM-CONFIG]]"
  - "[[MACOS-FONT-RENDERING]]"
  - "[[RUST-BUILD-TOOLCHAIN]]"
---

## 摘要（Summary）

本文記錄從 WezTerm 社群分支（`feat/macos-dictation`）編譯原始碼、啟動 GUI，並解決中文字符（CJK）顯示亂碼與字寬異常問題的完整過程，最後將成果打包為標準的 macOS `.app` bundle，方便未來重新安裝。

---

## 背景（Background）

WezTerm 官方版本在 macOS 上尚未完整支援系統內建的聽寫（Dictation）功能。社群貢獻者 Erog38 在 `feat/macos-dictation` 分支中實作了對應的 IMKit 整合（`NSTextInputClient` protocol）。為了使用此功能，需要自行從原始碼編譯。

---

## 關鍵洞察（Key Insights）

- 自編譯 WezTerm 需要初始化 Git submodule，缺少這步會導致 C 依賴缺失
- WezTerm 的 GUI 程式入口是 `wezterm-gui`，直接執行 `wezterm` 不帶參數不會開視窗，需要加上 `start` 子命令
- macOS 內建中文字體 `Heiti TC` 可直接作為備用字體（fallback），不需要另外安裝
- `treat_east_asian_ambiguous_width_as_wide = true` 會把 Unicode 寬度不確定的字符（如 `·` 中點）視為雙倍寬度，造成 shell prompt 排版跑掉

---

## 詳細流程（Details）

### 1. Clone 並初始化 Submodule

```bash
git clone --branch feat/macos-dictation \
  https://github.com/Erog38/wezterm.git \
  ~/git/wezterm-voice/wezterm

cd ~/git/wezterm-voice/wezterm
git submodule update --init --recursive
```

> [!important] 必須執行 `--recursive`
> WezTerm 依賴 freetype2、harfbuzz、libpng、zlib 等 C 函式庫作為 submodule，略過此步會在編譯時缺少 header 而失敗。

### 2. 安裝 Rust Toolchain

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
rustc --version  # 確認：rustc 1.94.0
```

### 3. 編譯 Release 版本

```bash
cd ~/git/wezterm-voice/wezterm
cargo build --release
```

編譯完成後產生三個執行檔（位於 `target/release/`）：

| 執行檔 | 用途 |
|--------|------|
| `wezterm` | CLI 主程式，用於控制 GUI（傳送指令、開新視窗） |
| `wezterm-gui` | 實際的 GUI 視窗程式 |
| `wezterm-mux-server` | 多工伺服器，讓多個 client 共用 session（類似 tmux server） |

### 4. 啟動 GUI

直接執行 `wezterm-gui` 或透過 CLI 的 `start` 子命令：

```bash
./target/release/wezterm start
```

> [!warning] 常見誤解
> 直接執行 `./target/release/wezterm` 不帶參數，不會開啟視窗。必須加上 `start` 子命令。啟動成功後可以在終端機看到 `IMKClient_Modern` 與 `IMKInputSession_Modern` 日誌，確認 IMKit 整合生效。

### 5. 解決中文字符亂碼

**問題現象**：部分中文字（如「嗎」）顯示為亂碼或方塊。

**根本原因分析**：
有兩種可能原因：

1. **字體缺少字形（Glyph Missing）** — 主字體 JetBrains Mono 沒有中文字形，WezTerm 找不到備用字體時會顯示「豆腐塊」
2. **`nsstring_to_str` UTF-16 vs UTF-8 長度錯誤** — 程式碼中使用 `NSString::len()`（回傳 UTF-16 code units）作為 UTF-8 byte slice 的長度，中文字一個字 UTF-8 佔 3 bytes 但 UTF-16 只算 1，導致截斷後產生亂碼

**解決方案（設定字體備用清單）**：

建立 `~/.config/wezterm/wezterm.lua`：

```lua
local wezterm = require 'wezterm'

return {
  font = wezterm.font_with_fallback {
    'JetBrains Mono',
    'Heiti TC',       -- macOS 內建繁體中文字體
  },
  unicode_version = 14,
}
```

> [!tip] 確認可用的中文字體
> 可用以下指令列出 WezTerm 偵測到的字體：
> ```bash
> ./target/release/wezterm ls-fonts --list-system 2>&1 | grep -i "heiti\|pingfang"
> ```
> macOS 上通常有 `Heiti TC`（繁體）與 `Heiti SC`（簡體）可用。

### 6. 解決 Shell Prompt 字元寬度異常

**問題現象**：加入 `treat_east_asian_ambiguous_width_as_wide = true` 後，shell prompt 中的中點 `·` 字符間距特別寬，排版跑掉。

**原因**：`·`（U+00B7, MIDDLE DOT）屬於 Unicode「模糊寬度（Ambiguous Width）」字符。這個設定會把所有模糊寬度字符（包含許多標點）都視為雙倍寬度，影響不只是 CJK 文字。

**解決方案**：移除該設定，不需要它就能正常顯示中文。

```lua
return {
  font = wezterm.font_with_fallback {
    'JetBrains Mono',
    'Heiti TC',
  },
  unicode_version = 14,
  -- 不加 treat_east_asian_ambiguous_width_as_wide
}
```

### 7. 打包為 macOS .app Bundle

WezTerm repo 本身附有 `.app` 模板（位於 `assets/macos/WezTerm.app`），直接組裝：

```bash
BUNDLE=~/git/wezterm-voice/WezTerm.app
SRC=~/git/wezterm-voice/wezterm

cp -R "$SRC/assets/macos/WezTerm.app" "$BUNDLE"
mkdir -p "$BUNDLE/Contents/MacOS"
cp "$SRC/target/release/wezterm-gui"       "$BUNDLE/Contents/MacOS/"
cp "$SRC/target/release/wezterm"           "$BUNDLE/Contents/MacOS/"
cp "$SRC/target/release/wezterm-mux-server" "$BUNDLE/Contents/MacOS/"
cp "$SRC/target/release/Info.plist"        "$BUNDLE/Contents/Info.plist"
```

安裝到系統：

```bash
cp -R ~/git/wezterm-voice/WezTerm.app /Applications/
```

`.app` bundle 結構：

```
WezTerm.app/
  Contents/
    Info.plist          ← CFBundleExecutable = wezterm-gui
    MacOS/
      wezterm-gui       ← 主 GUI 程式（雙擊開啟）
      wezterm           ← CLI 工具
      wezterm-mux-server
    Resources/
      terminal.icns     ← 應用程式圖示
```

---

## 預編譯版本下載與安裝（給朋友用）

> [!warning] 限制：僅支援 Apple Silicon Mac（M1/M2/M3/M4）
> 這個預編譯版本是 **arm64 架構**，Intel Mac（2020 年以前）無法執行。

### 下載

前往 GitHub Release 下載最新版本：

**[⬇️ 下載 WezTerm-macos-arm64.zip](https://github.com/swchen44/wezterm-macos-dictation/releases/latest)**

原始碼分支：[Erog38/wezterm feat/macos-dictation](https://github.com/Erog38/wezterm/tree/feat/macos-dictation)

### 安裝步驟

**1. 解除 macOS Gatekeeper 封鎖（必要）**

因為此版本沒有 Apple 開發者簽名，macOS 會擋住它。下載解壓縮後，**開啟前必須先執行：**

```bash
xattr -cr /Applications/WezTerm.app
```

**2. 安裝**

```bash
# 解壓縮後將 .app 拖入 Applications
cp -R ~/Downloads/WezTerm.app /Applications/

# 移除 Gatekeeper 封鎖
xattr -cr /Applications/WezTerm.app
```

**3. 開啟**

雙擊 `/Applications/WezTerm.app` 即可。

### 中文顯示設定（可選但建議）

建立 `~/.config/wezterm/wezterm.lua` 以正確顯示中文字符：

```bash
mkdir -p ~/.config/wezterm
```

```lua
local wezterm = require 'wezterm'

return {
  font = wezterm.font_with_fallback {
    'JetBrains Mono',
    'Heiti TC',       -- macOS 內建繁體中文字體
  },
  unicode_version = 14,
}
```

### 使用 macOS 聽寫功能

WezTerm 視窗開啟後，按 **連按兩下 `Fn` 鍵**（或麥克風按鈕）啟動系統聽寫，即可語音輸入文字。

### 已知限制

| 限制 | 說明 |
|------|------|
| 僅支援 Apple Silicon | M1/M2/M3/M4 Mac，Intel Mac 不支援 |
| 未經 Apple 簽名 | 需手動執行 `xattr -cr` 解除 Gatekeeper |
| 社群分支，非官方版 | 基於 feat/macos-dictation，尚未合併至 WezTerm 主線 |
| 聽寫功能限制 | 依賴 macOS 系統語言設定，需在系統設定中啟用聽寫 |

---

## 我的心得（My Takeaways）

- Rust 的 cargo build 過程非常自動化，不需要手動處理 C 依賴的 configure/make，但 **git submodule 仍是手動步驟**，容易被跳過
- macOS 字體備用機制（font fallback）是解決 CJK 顯示問題最簡單可靠的方法，不需要修改程式碼
- Unicode 的「模糊寬度」字符（Ambiguous Width Characters）範圍比想像中廣，不只是中文字——強制將其設為寬字符的設定需要謹慎使用
- WezTerm 的 macOS `.app` bundle 結構標準且清晰，repo 內附有完整模板，自行打包的門檻很低

---

## 相關連結（Related）

- [[WEZTERM-CONFIG]] — WezTerm 進階設定參考
- [[MACOS-FONT-RENDERING]] — macOS 字體渲染與 CoreText 機制
- [[RUST-BUILD-TOOLCHAIN]] — Rust 編譯工具鏈設定與常見問題

## References

- [Erog38/wezterm feat/macos-dictation](https://github.com/Erog38/wezterm/tree/feat/macos-dictation)
- [WezTerm 官方字體設定文件](https://wezfurlong.org/wezterm/config/fonts.html)
