#!/bin/sh
# Mermaid 圖表驗證（jsdom + mermaid.parse，只 parse 不渲染）
# 用法: validate-mermaid.sh <file1.md> [file2.md ...]
# 依賴自動安裝在 ${TMPDIR:-/tmp}/kb-mermaid-check，跨次執行重用
set -e
SKILL_SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
WORK="${TMPDIR:-/tmp}/kb-mermaid-check"
mkdir -p "$WORK"
# temp 目錄可能被系統部分清理（連傳遞依賴都會缺），一律用 bun install 依 lockfile 還原
if [ ! -f "$WORK/package.json" ]; then
  echo "首次安裝 mermaid + jsdom 到 $WORK ..."
  (cd "$WORK" && bun add mermaid jsdom >/dev/null 2>&1)
else
  (cd "$WORK" && bun install >/dev/null 2>&1)
fi
cp "$SKILL_SCRIPTS/validate-mermaid.mjs" "$WORK/"
cd "$WORK"
exec bun run "$WORK/validate-mermaid.mjs" "$@"
