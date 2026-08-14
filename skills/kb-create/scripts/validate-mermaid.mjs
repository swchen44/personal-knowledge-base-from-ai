// Mermaid 語法直驗：jsdom 環境，只 parse 不渲染
// 由 validate-mermaid.sh 呼叫（它負責安裝 mermaid/jsdom 依賴）
import { readFileSync } from 'node:fs'
import { JSDOM } from 'jsdom'

const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', { pretendToBeVisual: true })
for (const key of ['window', 'document', 'navigator', 'DOMParser', 'XMLSerializer', 'SVGElement', 'HTMLElement', 'Element', 'Node']) {
  try {
    Object.defineProperty(globalThis, key, { value: dom.window[key] ?? dom.window, configurable: true })
  } catch {}
}

const mermaid = (await import('mermaid')).default
mermaid.initialize({ startOnLoad: false })

const BLOCK_RE = /```mermaid[^\n]*\n([\s\S]*?)```/g
let totalBlocks = 0
let failed = 0

for (const file of process.argv.slice(2)) {
  const content = readFileSync(file, 'utf-8')
  let m
  let idx = 0
  while ((m = BLOCK_RE.exec(content)) !== null) {
    idx++
    totalBlocks++
    const code = m[1]
    const startLine = content.slice(0, m.index).split('\n').length

    // GitHub 殺手模式：本地 parse 會過、GitHub 解碼實體後會炸
    if (/&quot;/.test(code)) {
      failed++
      console.log(`FAIL  ${file} [block ${idx} @ line ${startLine}]`)
      console.log('      label 內含 &quot; 實體 — GitHub 會解碼成引號導致 Parse error（本地 parse 抓不到）')
      continue
    }

    try {
      await mermaid.parse(code)
      console.log(`PASS  ${file} [block ${idx} @ line ${startLine}]`)
    } catch (e) {
      failed++
      console.log(`FAIL  ${file} [block ${idx} @ line ${startLine}]`)
      console.log(String(e.message ?? e).split('\n').slice(0, 6).map(l => '      ' + l).join('\n'))
    }
  }
}

console.log(`\n${totalBlocks} blocks checked, ${failed} failed`)
process.exit(failed > 0 ? 1 : 0)
