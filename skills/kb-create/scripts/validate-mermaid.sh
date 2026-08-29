#!/bin/sh
# Mermaid 圖表驗證（jsdom + mermaid.parse，只 parse 不渲染）
# 用法: validate-mermaid.sh <file1.md> [file2.md ...]
# 依賴自動安裝在 ${TMPDIR:-/tmp}/kb-mermaid-check，跨次執行重用。
# temp 目錄可能被系統部分清理（bun install 依 lockfile 不會校驗檔案完整性），
# 因此偵測到「Cannot find module/package」執行期錯誤時，全清重裝後重試一次。
SKILL_SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
WORK="${TMPDIR:-/tmp}/kb-mermaid-check"

install_deps() {
  mkdir -p "$WORK"
  (cd "$WORK" && bun add mermaid jsdom >/dev/null 2>&1)
}

run_validator() {
  cp "$SKILL_SCRIPTS/validate-mermaid.mjs" "$WORK/"
  (cd "$WORK" && bun run "$WORK/validate-mermaid.mjs" "$@" 2>&1)
}

[ -d "$WORK/node_modules" ] || { echo "首次安裝 mermaid + jsdom 到 $WORK ..."; install_deps; }

OUTPUT=$(run_validator "$@")
STATUS=$?
if [ $STATUS -ne 0 ] && printf '%s' "$OUTPUT" | grep -q "Cannot find"; then
  echo "依賴不完整（temp 被部分清理），全清重裝後重試 ..."
  rm -rf "$WORK"
  install_deps
  OUTPUT=$(run_validator "$@")
  STATUS=$?
fi
printf '%s\n' "$OUTPUT"
exit $STATUS
