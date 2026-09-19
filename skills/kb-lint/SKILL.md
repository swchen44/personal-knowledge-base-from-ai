---
name: kb-lint
description: 個人知識庫健檢工具。掃描整個知識庫，找出孤立筆記、壞掉的 wikilink、缺少 cross-reference、frontmatter 不一致、已回答的 Open Questions，並產生修復建議。
disable-model-invocation: true
argument-hint: [--fix]
---

對個人知識庫執行健檢（lint），找出結構問題並產生報告。

> 加 `--fix` 參數會自動修復可安全處理的問題（如補回填連結）。不加則只產出報告。

---

## 環境變數

| 變數 | 用途 |
|------|------|
| `$KB_ROOT` | 個人知識庫本地 repo 路徑 |
| `$KB_GITHUB_REPO` | 知識庫 GitHub repo |
| `$GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub API 驗證（push 時使用） |

```bash
: "${KB_ROOT:?需設定 KB_ROOT 環境變數}"
```

---

## 步驟 1：同步知識庫

```bash
git -C "$KB_ROOT" fetch origin
git -C "$KB_ROOT" pull --rebase origin main
```

---

## 步驟 2：收集知識庫現況

```bash
# 列出所有筆記（排除 assets、LOG、INDEX、README）
find "$KB_ROOT" -name "*.md" \
  | grep -v assets/ \
  | grep -v LOG.md \
  | grep -v INDEX.md \
  | grep -v README.md \
  | grep -v ".git/" \
  | sort > /tmp/kb-lint-all-notes.txt

echo "筆記總數: $(wc -l < /tmp/kb-lint-all-notes.txt)"

# 列出所有分類資料夾
ls -d "$KB_ROOT"/*/  | grep -v ".git" | grep -v assets
```

---

## 步驟 3：執行五項檢查

### 檢查 A：孤立筆記（Orphan Notes）

找出**沒有任何其他筆記指向它**的筆記：

```bash
# 對每個筆記，檢查它的檔名是否被其他 .md 檔引用
while IFS= read -r note; do
  NOTE_NAME=$(basename "$note" .md)
  REFS=$(grep -rl "\[\[$NOTE_NAME" "$KB_ROOT" --include="*.md" \
    | grep -v "$(basename "$note")" \
    | grep -v LOG.md \
    | grep -v INDEX.md \
    | grep -v README.md \
    | wc -l)
  if [ "$REFS" -eq 0 ]; then
    echo "ORPHAN: $note"
  fi
done < /tmp/kb-lint-all-notes.txt
```

### 檢查 B：壞掉的 Wikilink（Broken Links）

找出指向不存在筆記的 `[[...]]`：

```bash
# 提取所有 wikilink 目標
grep -roh '\[\[[^]]*\]\]' "$KB_ROOT" --include="*.md" \
  | grep -v LOG.md \
  | sed 's/\[\[//;s/\]\]//;s/|.*//' \
  | sort -u > /tmp/kb-lint-all-links.txt

# 提取所有筆記名稱（不含 .md）
while IFS= read -r note; do
  basename "$note" .md
done < /tmp/kb-lint-all-notes.txt | sort -u > /tmp/kb-lint-all-names.txt

# 找差集：被引用但不存在的
comm -23 /tmp/kb-lint-all-links.txt /tmp/kb-lint-all-names.txt > /tmp/kb-lint-broken.txt
```

LLM 判斷每條 broken link：
- 是**筆錯名字**（可修復）→ 找出最接近的既有筆記名
- 是**尚未建立的概念**（正常）→ 標記為 "planned"
- 是**已刪除或重新命名**（需清理）→ 標記為 "stale"

### 檢查 C：缺少 Cross-Reference 的筆記對

找出**主題高度相關但沒有互相連結**的筆記：

LLM 讀取所有筆記的 frontmatter（tags、category、author），找出：
- 同 category + 同 tags 但沒互連的筆記對
- 同 author 但沒互連的筆記對
- 標題/摘要語意相近但沒互連的筆記對

> [!important] 只列出 LLM 判斷「確實應該互連」的，不是所有同 tag 的排列組合。

### 檢查 D：Frontmatter 一致性

掃描所有筆記的 frontmatter，找出：

```bash
# 找缺少必要欄位的筆記
for note in $(cat /tmp/kb-lint-all-notes.txt); do
  for field in title date category tags source source_type author status links; do
    if ! grep -q "^$field:" "$note"; then
      echo "MISSING $field: $note"
    fi
  done
done
```

額外檢查：
- `date` 格式是否為 `YYYY-MM-DD`
- `source_type` 是否為允許值之一
- `tags` 是否至少 3 個
- `links` 是否至少 1 個

### 檢查 E：已回答的 Open Questions

掃描所有筆記的 `## 待補充（Open Questions）` 段落，LLM 判斷：
- 該問題是否已被**後續攝入的其他筆記**回答
- 若已回答 → 標記為 "resolved"，附上回答筆記的 wikilink

---

## 步驟 4：產生 Lint 報告

在 `$KB_ROOT/LINT-REPORT.md` 寫入報告：

```markdown
---
title: "知識庫健檢報告"
date: {今天日期}
---

# Knowledge Base Lint Report — {YYYY-MM-DD}

## 總覽

| 項目 | 數量 |
|------|------|
| 筆記總數 | {N} |
| 分類數 | {N} |
| 孤立筆記 | {N} |
| 壞掉的連結 | {N} |
| 缺少互連的筆記對 | {N} |
| Frontmatter 問題 | {N} |
| 已解決的 Open Questions | {N} |

## A. 孤立筆記（Orphan Notes）

| 筆記 | 分類 | 建議 |
|------|------|------|
| [[NOTE-NAME]] | {category} | 建議連結至 [[X]], [[Y]] |

## B. 壞掉的連結（Broken Links）

| 來源筆記 | 壞連結 | 狀態 | 建議 |
|----------|--------|------|------|
| [[SOURCE]] | [[BROKEN]] | stale / planned / typo | {修復建議} |

## C. 缺少互連（Missing Cross-References）

| 筆記 A | 筆記 B | 關聯原因 | 建議 |
|--------|--------|----------|------|
| [[A]] | [[B]] | 同主題 / 同作者 | 雙向加連結 |

## D. Frontmatter 問題

| 筆記 | 缺少欄位 | 格式錯誤 |
|------|----------|----------|
| [[NOTE]] | links | date 格式非 YYYY-MM-DD |

## E. 已解決的 Open Questions

| 原筆記 | 問題 | 回答筆記 |
|--------|------|----------|
| [[NOTE]] | {問題文字} | [[ANSWER-NOTE]] |
```

---

## 步驟 5（僅 `--fix` 模式）：自動修復

若使用者傳入 `--fix`，自動處理以下**安全的**修復：

### 可自動修復
- **孤立筆記**：加入缺少的 cross-reference（用步驟 7 的邏輯回填，上限 8）
- **已解決的 Open Questions**：在問題後加 `✅ 已回答 → [[ANSWER-NOTE]]`
- **缺少互連**：雙向加連結（同 article-to-kb 步驟 7c 邏輯）
- **Frontmatter 缺 links**：根據文中既有 wikilink 補上

### 不自動修復（只提醒）
- 壞掉的連結（需人工判斷是 typo、planned 還是 stale）
- 缺少 date 或 source 等無法推斷的欄位

修復完成後：

```bash
git -C "$KB_ROOT" add .
git -C "$KB_ROOT" commit -m "$(cat <<EOF
kb: lint --fix — {YYYY-MM-DD}

- fixed orphans: {N}
- fixed cross-refs: {N}
- resolved questions: {N}
- frontmatter fixes: {N}
EOF
)"
git -C "$KB_ROOT" push
```

---

## 步驟 6：Append LOG.md

```bash
LOG_FILE="$KB_ROOT/LOG.md"

# append 一行到 LOG 表格
```

用 Edit 工具在表格末尾 append：
```
| {YYYY-MM-DD HH:MM} | lint | — | [[LINT-REPORT]] | — | {fixes applied 或 report only} | — |
```

---

## 步驟 7：回報結果

```
🔍 知識庫健檢完成
📊 筆記總數：{N}
🏝️ 孤立筆記：{N}
🔗 壞連結：{N}
🤝 缺少互連：{N}
📋 Frontmatter 問題：{N}
✅ 已解決的 Open Questions：{N}
{若 --fix} 🔧 自動修復了 {N} 個問題
📄 完整報告：LINT-REPORT.md
```
