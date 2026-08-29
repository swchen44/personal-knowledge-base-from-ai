---
title: "macOS .localized 資料夾顯示名稱本地化機制 — 顯示層翻譯的設計哲學與跨平台對照"
date: 2026-08-30
category: OS
tags:
  - os/macos
  - os/internals
  - i18n
  - filesystem
  - design/philosophy
source: "original-research (Claude Code 實機實驗 session, 2026-08-28)"
source_type: article
author: "swchen44 (with Claude Code)"
status: notes
links:
  - "[[2026-03-20-WEZTERM-MACOS-DICTATION-BUILD-AND-CJK-FIX]]"
  - "[[2026-07-05-TERMINAL-MEMORY-MANAGEMENT-AND-CROSS-PLATFORM-PERSISTENCE]]"
  - "[[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]]"
---

## 摘要（Summary）

macOS 的 Finder 會把 `~/Documents` 顯示成「文件」、把 `Chrome Apps.localized` 顯示成「Chrome 應用程式」，但磁碟上的真實名稱從頭到尾都是英文 —— 翻譯只發生在**顯示層（display layer）**。本文源自一次實際偵查：Launchpad 上突然出現一個「文件」圖示，追查後發現是 Chrome 建立的 Google Docs 網頁應用程式捷徑（PWA shortcut），進而挖出 macOS 兩種資料夾名稱本地化機制，並以 `NSFileManager.displayNameAtPath`（Finder 實際使用的 API）做了五組對照實驗，實測出衝突時的優先順序。文末對照 Windows（`desktop.ini` 顯示層翻譯）與 Linux（`xdg-user-dirs` 實際改名）的設計，三大作業系統對同一問題給出了兩種截然不同的哲學答案。

## 關鍵洞察（Key Insights）

- macOS 判斷「有哪些 App」靠的是**自動掃描固定資料夾**（`/Applications`、`~/Applications` 等），任何 `.app` 包放進去就會出現在 Launchpad，不需要安裝登記程序。
- 資料夾名稱本地化有**兩種形式**：`.localized` 字尾資料夾（自帶 `.strings` 對照表）與空的 `.localized` 檔案（查系統內建對照表）。
- 衝突時的優先順序（實測）：**資料夾自帶對照表 > 系統對照表 > 不翻譯**。
- 翻譯**只影響顯示層**：Finder、開啟／儲存對話框、Spotlight 看得到；Terminal、POSIX API、shell script 永遠看到真實英文名。
- 對照 Linux 的 `xdg-user-dirs` 是**真的改資料夾名稱**（`~/Documents` 在德文系統就叫 `~/Dokumente`），與 macOS/Windows 的顯示層路線是兩種相反的設計哲學。

## 詳細內容（Details）

### 起點：Launchpad 上突然出現的「文件」圖示

Launchpad 出現一個 Google Docs 樣式的「文件」圖示。追查步驟與結果：

```bash
# 1. 找到實體位置
ls ~/Applications/"Chrome Apps.localized"/
# → 文件.app  簡報.app  試算表.app  Gmail.app  YouTube.app ...

# 2. 查出現時間（建立時間 + Spotlight 加入日期）
stat -f "%SB" ~/Applications/"Chrome Apps.localized"/文件.app
mdls -name kMDItemDateAdded ~/Applications/"Chrome Apps.localized"/文件.app

# 3. 查它是什麼
plutil -p ~/Applications/"Chrome Apps.localized"/文件.app/Contents/Info.plist
# → CrBundleIdentifier = com.google.Chrome
# → CrAppModeShortcutURL = https://docs.google.com/document/?usp=installed_webapp
```

結論：這是使用者在 Chrome 網址列點了「安裝」後，Chrome 動態產生的一個小型 `.app` 殼程式（開啟後導向 docs.google.com）。URL 中的 `usp=installed_webapp` 參數即是證據。Chrome 把它放進 `~/Applications/Chrome Apps.localized/`，macOS 掃描到後就自然出現在 Launchpad。

> [!note] 關鍵術語（Key Term）：Launchpad 的 App 發現機制
> macOS 由 Spotlight 與 Launch Services 自動掃描 `/Applications`、`/System/Applications`、`~/Applications`（含子資料夾）。`.app` 包（bundle）放進去即被索引、移出即消失 —— 沒有「安裝登記」這回事。

### 機制一：`.localized` 字尾資料夾（第三方 App 常用）

資料夾名稱以 `.localized` 結尾，裡面藏一個隱藏子資料夾 `.localized/`，內含各語言的 `.strings` 對照檔（plist 格式）：

```
~/Applications/Chrome Apps.localized/
├── .localized/
│   └── zh_TW.strings        ← "Chrome Apps" → "Chrome 應用程式"
├── 文件.app
└── ...
```

實際的對照檔內容：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Chrome Apps</key>
	<string>Chrome 應用程式</string>
</dict>
</plist>
```

Finder 看到這個結構就會：隱藏 `.localized` 字尾 → 以資料夾原名（去字尾）為 key 查當前語言的 `.strings` → 顯示翻譯後的名稱。Microsoft Office 也大量使用此機制（`Templates.localized` → 範本、`Themes.localized` → 佈景主題）。

### 機制二：空的 `.localized` 檔案（Apple 系統資料夾用）

資料夾內放一個 0 byte 的隱藏檔 `.localized`，Finder 看到後改查**系統內建對照表**：

```bash
plutil -p /System/Library/CoreServices/SystemFolderLocalizations/zh_TW.lproj/SystemFolderLocalizations.strings
# "Applications" => "應用程式"
# "Desktop"      => "桌面"
# "Documents"    => "文件"
# "Downloads"    => "下載項目"
```

`~/Desktop`、`~/Documents`、`~/Downloads`、`/Applications`、`/Library` 全走這條路。這也是切換系統語言後這些資料夾「馬上改名」的原因 —— 磁碟上根本沒改，只是顯示層換了查表結果。

### 五組對照實驗（實測優先順序）

用 Finder 實際使用的 API `NSFileManager.displayNameAtPath` 驗證（JXA / `osascript -l JavaScript`）：

| # | 測試情境 | 顯示結果 | 結論 |
|---|---------|---------|------|
| A | `TestFoo.localized` + 正確 key 的對照表 | 測試甲 | 自帶對照表生效 |
| B | `TestBar.localized` + key 打錯 | TestBar | 只藏字尾、不翻譯（安全退回） |
| C | 任意位置的 `Documents` + 空 `.localized` 檔 | 文件 | 系統表**不限標準位置**，任何地方都生效 |
| D | `Documents.localized` + 自訂對照「我的自訂名稱」 | 我的自訂名稱 | **自訂表壓過系統表** |
| E | `RandomName` + 空 `.localized` 檔 | RandomName | 系統表查無此名 → 不翻譯 |

查找優先順序（衝突裁決規則）：

```
資料夾名稱以 .localized 結尾且有 .localized/ 對照目錄？
   │
   ├─ 是 ──► 依使用者語言偏好找對應 .strings，以原名（去字尾）為 key 查表
   │           ├─ 查到 ──► 顯示翻譯【到此為止，不再看系統表】
   │           └─ 查不到（key 錯／語言檔缺）──► 顯示去字尾的原名
   │
   └─ 否 ──► 資料夾內有空的 .localized 檔？
               ├─ 是 ──► 查系統表 SystemFolderLocalizations
               │           ├─ 有此名 ──► 顯示系統翻譯
               │           └─ 無此名 ──► 顯示原名
               └─ 否 ──► 顯示原名
```

### 影響範圍（Scope）

- **只影響單一資料夾自己**：對照表不影響子資料夾、不影響別處同名資料夾；每個資料夾各帶各的表（Office 每層都放一個 `.localized` 就是這個原因）。
- **只影響顯示層**：走 `NSFileManager` display name 的地方（Finder、開啟／儲存對話框、Spotlight）看得到翻譯；Terminal、shell script、任何以路徑存取檔案的程式看到的永遠是真實英文名。所以腳本裡永遠寫 `~/Documents`，不能寫 `~/文件`。
- **允許顯示名稱重複**：兩個真實名稱不同的資料夾可以顯示成同一個中文名 —— 檔案系統只認真實名稱。

> [!warning] 注意事項（Watch Out）：視覺欺騙（spoofing）風險
> 正因為「顯示名稱可以自訂、且可與系統資料夾同名」，惡意程式可以做一個顯示為「文件」的假資料夾放在真資料夾旁邊誘導點擊。看到可疑的同名資料夾時，用 Terminal `ls` 看真實名稱最可靠。這與 Windows `desktop.ini` 的偽裝手法（malware 常藉它改資料夾顯示名與圖示）是同一類攻擊面。

> [!tip] 可執行建議（Actionable Tip）：自己做一個本地化資料夾
> 建立 `MyStuff.localized/`，裡面放 `.localized/zh_TW.strings`（plist 格式，key 為 `MyStuff`），Finder 立即顯示你指定的中文名 —— 不需重開機、不需任何工具。

## 延伸研究地圖：macOS 還有哪些 localized 機制值得挖

同一套「顯示層翻譯」哲學貫穿整個 macOS，以下是同族機制：

| 機制 | 位置 | 作用對象 | 備註 |
|------|------|---------|------|
| `.lproj` 語言包 | `App.app/Contents/Resources/{lang}.lproj/` | App 內所有 UI 字串 | Bundle 本地化的基礎建設 |
| `InfoPlist.strings` / `CFBundleDisplayName` | 各語言 `.lproj` 內 | **App 顯示名稱**（Calendar.app → 行事曆） | 實測 `displayNameAtPath` 對 `/System/Applications/Calendar.app` 回傳「行事曆」 |
| `.loctable` | `App.app/Contents/Resources/*.loctable` | 同上（新格式） | 現代 macOS 把所有語言的 `.strings` 合併成單一 plist 檔，實測 Calendar.app 已採用 |
| 附檔名隱藏 | `NSFileManager` display name 同一層 | `.app`、使用者勾選的附檔名 | 「行事曆」連 `.app` 都藏掉了 —— 顯示層改寫不只翻譯 |
| `SystemFolderLocalizations` | `/System/Library/CoreServices/SystemFolderLocalizations/` | 系統標準資料夾名 | 機制二的資料來源，每語言一份 `.strings` |
| Launch Services 掃描 | `/Applications`、`~/Applications` 等 | Launchpad / 「打開方式」清單 | 與本地化無關但同屬「約定優於登記」設計 |

值得繼續深挖的方向（見文末 Open Questions）：`.loctable` 的格式與工具鏈、`CFBundleDevelopmentRegion` 的 fallback 順序、iCloud Drive 資料夾的本地化行為。

## 跨平台對照：三大 OS 的兩種哲學

### Windows：`desktop.ini`（顯示層，指標式）

資料夾內放隱藏的 `desktop.ini`，`[.ShellClassInfo]` 區段的 `LocalizedResourceName` 指向「某個 DLL 裡的字串資源 ID」：

```ini
[.ShellClassInfo]
LocalizedResourceName=@%SystemRoot%\system32\shell32.dll,-21770
```

File Explorer 顯示前先讀這個檔，把顯示名稱重導向到 DLL 資源（隨系統語言切換）。也提供 `SHSetLocalizedName` API 程式化設定。與 macOS 同屬顯示層翻譯，但實作是**指標式**（指向編譯進 DLL 的資源）而非 macOS 的**資料式**（明文 `.strings` 對照表）—— 前者難以手工修改與檢視，後者一個文字編輯器就能讀寫。附帶一提：2026 年 1 月的更新 KB5074109 曾弄壞這個機制，導致部分使用者的系統資料夾顯示回英文名，正好證明了「真實名稱從未改變」。

### Linux：`xdg-user-dirs`（真實改名）

freedesktop.org 的 `xdg-user-dirs` 走完全相反的路：**首次登入時依 locale 真的建立本地化名稱的資料夾**，並把對應關係寫進 `~/.config/user-dirs.dirs`：

```bash
# 德文系統的 ~/.config/user-dirs.dirs
XDG_DOCUMENTS_DIR="$HOME/Dokumente"
XDG_DOWNLOAD_DIR="$HOME/Downloads"
```

程式不寫死路徑，改用 `xdg-user-dir DOCUMENTS` 查詢。切換系統語言時，GNOME 的 `xdg-user-dirs-gtk` 會跳出對話框問你要不要**把資料夾實際改名**。

### 設計取捨比較

| 面向 | macOS / Windows（顯示層） | Linux xdg-user-dirs（真實改名） |
|------|--------------------------|-------------------------------|
| 腳本相容性 | ✅ 路徑永遠是英文，跨機器可攜 | ⚠️ 路徑隨 locale 變，必須查 `user-dirs.dirs` |
| 使用者直覺 | ⚠️ Terminal 看到的名字與 Finder 不同，新手困惑 | ✅ 所見即所得，GUI 與 shell 一致 |
| 切換語言成本 | ✅ 零成本，查表結果即時改變 | ⚠️ 需實際改名（或保留舊名造成混用） |
| 額外查詢層 | 需要（display name API） | 需要（`xdg-user-dir` 指令） |
| 欺騙攻擊面 | 顯示名可偽造（spoofing） | 較小（名稱即實體） |

> [!important] 核心洞察：這是「識別碼 vs 標籤」的經典分離
> macOS/Windows 把「機器用的識別碼（真實路徑）」與「人看的標籤（顯示名稱）」分成兩層 —— 和資料庫的 surrogate key vs display column、程式語言的變數名 vs UI 文案是同一個設計模式。Linux 則選擇「名稱即實體」的單層哲學。兩者都自洽，痛點只是轉移了位置：前者痛在「GUI 與 shell 不一致」，後者痛在「路徑不可攜」。

## 我的心得（My Takeaways）

1. 「約定優於登記」（convention over registration）在 OS 層的威力：Launchpad 不需要安裝資料庫，掃資料夾就夠了 —— Chrome 只要丟一個 `.app` 進 `~/Applications` 就完成「安裝」。
2. 偵查未知程式的三板斧可以複用：`stat`/`mdls` 查時間、`plutil -p Info.plist` 查身分、`kMDItemDateAdded` 查 Spotlight 加入時點。
3. 做跨平台工具（如 dotfiles、備份腳本）時，macOS 可以寫死 `~/Documents`，Linux 必須查 `xdg-user-dir` —— 這個差異的根源就是本文的兩種哲學。
4. 驗證顯示層行為不需要開 Finder 截圖：`osascript -l JavaScript` 呼叫 `NSFileManager.displayNameAtPath` 就是 Finder 的同一條路徑，可自動化、可寫進測試。

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，確立基礎知識 | ① `.localized` 兩種形式（字尾資料夾＋`.strings` vs 空檔案＋系統表）② 系統表路徑 `/System/Library/CoreServices/SystemFolderLocalizations/` ③ `NSFileManager.displayNameAtPath` 是 Finder 顯示名稱的 API ④ Windows 對應物是 `desktop.ini` 的 `LocalizedResourceName` ⑤ Linux 的 `xdg-user-dirs` 是真實改名 |
| **理解（半被動）** | 解釋概念的含義及關聯 | macOS 把「真實路徑」與「顯示名稱」分離成兩層：檔案系統只認英文真名（identifier），Finder 查對照表產生人看的標籤（label）。Launchpad 的 App 發現機制與此同源 —— 都是「掃描＋約定」而非「登記＋資料庫」 |
| **分析（主動）** | 檢驗論點、找出假設 | 實驗只驗證了 `displayNameAtPath` 這一條 API 路徑，隱含假設是「Finder 與所有 GUI 元件都走同一條路」—— 實際上 Spotlight 索引（`kMDItemDisplayName`）是另一條獨立管線，兩者是否永遠一致並未驗證。另外實驗 D 的「自訂表壓過系統表」只測了 zh_TW 單一語言，多語言偏好序列下的 fallback 行為未測 |
| **應用（主動）** | 將知識轉為行動 | ① 為自己的專案資料夾做中文顯示名（`MyStuff.localized` + `.strings`）② 把「偵查三板斧」（`stat`/`mdls`/`plutil`）寫成 shell alias，下次看到不明 App 直接用 ③ 跨平台腳本改用 `xdg-user-dir DOCUMENTS`（Linux）＋寫死路徑（macOS）的分支處理 |
| **評估（主動）** | 判斷方案優劣與取捨 | 顯示層翻譯 vs 真實改名：前者對腳本友善、對新手殘忍（GUI 與 shell 名稱不一致），後者相反。若今天設計新 OS，顯示層方案較優 —— 因為「標籤變更頻率 >> 識別碼變更頻率」，把易變的放顯示層、穩定的放檔案系統符合變更隔離原則；但必須配套「顯示名不可與同目錄下其他系統資料夾同名」的防偽規則，補上 spoofing 這個最大弱點 |

### 分析型追問（Socratic Follow-up）

> 以下問題供進一步反思，可用來與 AI 展開蘇格拉底式對話：

- **澄清**：「顯示層」的邊界到底在哪？`ls` 不翻譯、Finder 翻譯，那 `open` 指令、AppleScript 的 `POSIX path`、拖放到 Terminal 時各是哪一層？
- **假設**：本文假設 Finder 與 `displayNameAtPath` 行為完全一致 —— 有沒有 Finder 特有的覆寫（如使用者在 Finder 手動改名系統資料夾）會打破這個假設？
- **證據**：「Launchpad 靠 Spotlight 掃描」是社群共識，但 Apple 沒有官方文件明說 —— 關掉 Spotlight 索引後 Launchpad 還會更新嗎？
- **觀點**：站在 Linux 陣營立場，最有力的批評是：顯示層翻譯讓「教學文件」永遠要寫兩套名稱（跟著 GUI 說「文件」、跟著 Terminal 說 `Documents`），這個認知稅由全體使用者永久支付。
- **後果**：若 Apple 未來讓使用者自由改系統資料夾顯示名，12 個月後可能出現的副作用是 spoofing 攻擊常態化 —— 目前的安全性其實依賴「多數人不知道這個機制」。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 把 `.localized` 機制用於自己的工具時，最大風險是**視覺欺騙攻擊面**：任何能寫入資料夾的程式都能讓它偽裝成系統資料夾的顯示名稱，使用者無法從 Finder 分辨真偽。
2. **什麼情況下會失敗？** — ① key 與資料夾名不符時靜默失效（實驗 B），除錯困難因為沒有任何錯誤訊息；② 使用者語言不在你提供的 `.strings` 清單內時退回英文名；③ 非 Apple 生態的檔案管理器（如部分跨平台同步工具）不認得此機制，會把 `.localized` 字尾與隱藏目錄原樣暴露。
3. **有沒有更好的替代方案？** — 若目的只是「給資料夾一個友善名稱」，Finder 的標籤（tag）或替身（alias）更簡單且無欺騙疑慮；`.localized` 機制的正當使用場景限於「需要隨系統語言自動切換」的多語言發佈情境。

## 待補充（Open Questions）

- Launchpad 的掃描是否完全依賴 Spotlight 索引？關閉 `mdutil -i off` 後新放入的 `.app` 還會出現嗎？（建議搜尋：`Launchpad mdutil spotlight app discovery`）
- `.loctable` 的確切格式與官方工具鏈為何？開發者能否手工產生，或只能由 Xcode 的 localization export 流程生成？（建議搜尋：`loctable format xcstrings localization apple`）
- 多語言偏好序列（如 zh-TW > ja > en）下，`.localized/` 內語言檔的 fallback 是逐一嘗試還是只看第一偏好？`CFBundleDevelopmentRegion` 在資料夾（非 App bundle）情境有無作用？（建議搜尋：`NSFileManager displayNameAtPath language fallback order`）
- 實驗 C 顯示空 `.localized` 檔在任意位置生效 —— 這在 iCloud Drive、外接磁碟、SMB 網路磁碟上行為是否一致？（建議搜尋：`localized folder name iCloud Drive network volume`）
- Windows KB5074109 弄壞 `LocalizedResourceName` 的根因是什麼？是安全加固（刻意限縮 desktop.ini 解析）還是 regression？這對「顯示層翻譯依賴 shell 解析使用者可控檔案」的架構風險有何啟示？（建議搜尋：`KB5074109 desktop.ini LocalizedResourceName root cause`）
- macOS 是否有公開 API 可列舉「目前系統支援本地化的資料夾名稱全集」，還是只能直接讀 `SystemFolderLocalizations.strings`？（建議搜尋：`NSLocalizedFileNames API SystemFolderLocalizations`）

## 相關連結（Related）

- [[2026-03-20-WEZTERM-MACOS-DICTATION-BUILD-AND-CJK-FIX]] — 同為 macOS 系統層機制與 CJK 中文顯示情境的實戰筆記
- [[2026-07-05-TERMINAL-MEMORY-MANAGEMENT-AND-CROSS-PLATFORM-PERSISTENCE]] — 同樣採「跨平台機制對照」方法論分析系統層行為
- [[2026-04-14-CLAUDE-CODE-CLAUDEMD-SKILLS-HOT-RELOAD-MECHANISM]] — 「檔案系統掃描＋約定」的應用層版本：chokidar 監控 vs Launch Services 掃描，同一設計模式

## References

- [Windows: Customizing Folders with Desktop.ini（Microsoft Learn）](https://learn.microsoft.com/en-us/previous-versions/windows/embedded/ms906608(v=msdn.10))
- [Windows: SHSetLocalizedName function（Microsoft Learn）](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shsetlocalizedname)
- [Windows: KB5074109 breaks LocalizedResourceName parsing（Microsoft Q&A）](https://learn.microsoft.com/en-us/answers/questions/5708363/kb5074109-breaks-localizedresourcename-parsing-in)
- [Linux: xdg-user-dirs（freedesktop.org）](https://www.freedesktop.org/wiki/Software/xdg-user-dirs/)
- [Linux: XDG user directories（ArchWiki）](https://wiki.archlinux.org/title/XDG_user_directories)
- [GNOME GLib issue #2228: Localise display names for well-known user directories](https://gitlab.gnome.org/GNOME/glib/-/issues/2228)
