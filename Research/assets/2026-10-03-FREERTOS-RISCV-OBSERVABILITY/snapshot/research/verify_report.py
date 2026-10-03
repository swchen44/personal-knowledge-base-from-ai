"""Verify report structure, local evidence, diagrams and calculation examples."""
from pathlib import Path
from urllib.parse import unquote, urlparse
import hashlib
import json
import math
import re
from markdown_it import MarkdownIt
from PIL import Image

base = Path(__file__).resolve().parent
root = base.parent
report = base / 'FreeRTOS-RISC-V-Observability-研究報告.md'
source = report.read_text()
tokens = MarkdownIt('commonmark').enable('table').parse(source)
anchors = set(re.findall(r'<a id="([^"]+)"', source))
broken = []
link_count = 0
image_count = 0
for path in [root / 'README.md', report, base / 'README.md', base / '內部AI-接續研究任務.md', base / 'images/mermaid/README.md', root / 'percepio/TraceRecorder/README.md', root / 'Tracealyzer-SDK-demos/README.md', root / 'Tracealyzer-SDK-demos/GCC_MinGW_x86_64/README.md', root / 'Tracealyzer-STM32CubeIDE-SWO/README.md']:
    for token in MarkdownIt('commonmark').enable('table').parse(path.read_text()):
        for child in token.children or []:
            if child.type not in ('link_open', 'image'):
                continue
            attr = 'src' if child.type == 'image' else 'href'
            href = child.attrGet(attr)
            link_count += 1
            image_count += child.type == 'image' and path == report
            if urlparse(href).scheme:
                continue
            if href.startswith('#'):
                if path == report and href[1:] not in anchors:
                    broken.append(href)
                continue
            target = path.parent / unquote(href.split('#')[0])
            # This check itself writes verification.json below.
            if not target.exists() and target.resolve() != (base / 'verification.json'):
                broken.append(str(target))
            if '#' in href and target.exists():
                fragment = unquote(href.split('#', 1)[1])
                if target.resolve() == report and fragment not in anchors:
                    broken.append(href)
    for href in re.findall(r'<img\b[^>]*\bsrc=[\"\x27]([^\"\x27]+)[\"\x27]', path.read_text(), re.I):
        link_count += 1
        image_count += path == report
        if not urlparse(href).scheme:
            target = path.parent / unquote(href.split('#')[0])
            if not target.exists():
                broken.append(str(target))
assert not broken, broken

sections = [int(x) for x in re.findall(r'^## (\d+)\.', source, re.M)]
assert sections == list(range(24)), sections
diagrams = [t.content for t in tokens if t.type == 'fence' and t.info == 'mermaid']
assert len(diagrams) == 12
for i, code in enumerate(diagrams, 1):
    stem = base / 'images/mermaid' / f'diagram-{i:02}'
    assert stem.with_suffix('.mmd').read_text() == code
    assert stem.with_suffix('.svg').stat().st_size > 100
    with Image.open(stem.with_suffix('.png')) as img:
        img.verify()
mermaid = json.loads((base / 'mermaid-verification.json').read_text())
assert len(mermaid['results']) == len(diagrams)
assert all(x['passed'] for x in mermaid['results'])

pdfs = json.loads((base / 'pdf-manifest.json').read_text())
assert (pdfs['pdf_count'], pdfs['page_count'], pdfs['unique_extracted_text_count']) == (8, 61, 7)
for item in pdfs['files']:
    assert hashlib.sha256((root / item['file']).read_bytes()).hexdigest() == item['pdf_sha256']
    assert hashlib.sha256((root / item['extracted_text']).read_bytes()).hexdigest() == item['text_sha256']
visual = json.loads((base / 'pdf-visual-review.json').read_text())
assert visual['rendered_pdf_pages'] == 61
assert len(visual['selected_page_images']) == 13
for path in visual['selected_page_images']:
    with Image.open(root / path) as img:
        img.verify()

manifest = json.loads((base / 'source-manifest.json').read_text())
for item in manifest['files']:
    assert hashlib.sha256((root / item['path']).read_bytes()).hexdigest() == item['sha256']
footprint = json.loads((base / 'measurements/rv32-object-size.json').read_text())
rerun = json.loads(Path('/private/tmp/percepio-research/rv32-objects/result.json').read_text())
assert footprint == rerun
assert footprint['objects'] == 28
assert footprint['totals'] == {'text': 12633, 'data': 0, 'bss': 13880}
api = json.loads((base / 'api-link-check.json').read_text())
assert len(api['results']) == 9 and all(x.get('status') == 200 for x in api['results'])

audit = json.loads((base / 'requirements-audit.json').read_text())
readme = (root / 'README.md').read_text()
requirement_ids = re.findall(r'^\| (R\d{2}) \|', readme, re.M)
pending_ids = re.findall(r'^\| (U\d{2}) \|', readme, re.M)
assert requirement_ids == [f'R{i:02}' for i in range(1, 28)]
assert pending_ids == [f'U{i:02}' for i in range(1, 17)]
assert [item['id'] for item in audit['requirements']] == requirement_ids
assert [item['id'] for item in audit['pending_tasks']] == pending_ids
categories = audit['mece']['primary_categories']
assert [item['id'] for item in categories] == [f'M{i}' for i in range(1, 9)]
classified_requirements = [r for item in categories for r in item['requirements']]
classified_tasks = [u for item in categories for u in item['pending_tasks']]
assert len(classified_requirements) == len(set(classified_requirements)) == 27
assert len(classified_tasks) == len(set(classified_tasks)) == 16
assert set(classified_requirements) == set(requirement_ids)
assert set(classified_tasks) == set(pending_ids)
mece_rows = [line for line in source.splitlines() if re.match(r'^\| M\d ', line)]
assert len(mece_rows) == 8
for row, item in zip(mece_rows, categories):
    cells = row.split('|')
    assert re.findall(r'R\d{2}', cells[3]) == item['requirements']
    assert re.findall(r'U\d{2}', cells[4]) == item['pending_tasks']
handoff = (base / '內部AI-接續研究任務.md').read_text()
assert re.findall(r'^\| (U\d{2}) ', handoff, re.M) == pending_ids
case_rows = re.findall(r'^\| (C\d{2}) ', source, re.M)
assert case_rows == [f'C{i:02}' for i in range(1, 10)]
demo = json.loads((base / 'cases/desktop-demo-evidence.json').read_text())
demo_trace = root / demo['trace']
assert demo['build_exit_code'] == demo['run_exit_code'] == 0
assert demo_trace.stat().st_size == demo['trace_bytes'] == 7152
assert hashlib.sha256(demo_trace.read_bytes()).hexdigest() == demo['trace_sha256']
assert demo['tracealyzer_gui_verified'] is False
assert demo['board_measurement'] is False
source_images = json.loads((base / 'cases/source-image-review.json').read_text())
assert source_images['images_in_package'] == 15
assert source_images['missed_events_screen']['not_product_sdk_cpu_overhead'] is True
for path in (root / 'Tracealyzer-STM32CubeIDE-SWO/img').glob('*.png'):
    with Image.open(path) as img:
        img.verify()

examples = {
    'binary_bytes_per_second_5000_events_16_bytes': 5000 * 16,
    'uart_921600_8n1_bytes_per_second': 921600 / 10,
    'uart_80KBs_at_921600_occupancy_percent': 80000 / (921600 / 10) * 100,
    'recorder_5000_events_at_2us_cpu_percent': 5000 * 2 / 10000,
    'isr_5us_plus_4us_relative_overhead_percent': 4 / 5 * 100,
    'dma_100KBs_512byte_2us_callback_only_cpu_percent': (100000 / 512) * 2 / 10000,
    'ring_10KiB_at_80KBs_seconds': 10240 / 80000,
    'snapshot_64KiB_uart115200_seconds': 65536 / 11520,
    'trace_100KBs_per_day_GB_decimal': 100000 * 86400 / 10**9,
    'video_44000_events_at_16bytes_KBs': 44000 * 16 / 1000,
    'video_assumed_2us_per_event_cpu_percent': 44000 * 2 / 10000,
}
assert examples['binary_bytes_per_second_5000_events_16_bytes'] == 80000
assert math.isclose(examples['uart_80KBs_at_921600_occupancy_percent'], 86.8055555556)
assert examples['recorder_5000_events_at_2us_cpu_percent'] == 1
assert examples['ring_10KiB_at_80KBs_seconds'] == .128
assert examples['trace_100KBs_per_day_GB_decimal'] == 8.64

result = {
    'date': '2026-10-03',
    'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest(),
    'root_readme_sha256': hashlib.sha256((root / 'README.md').read_bytes()).hexdigest(),
    'sections': len(sections), 'checked_links': link_count,
    'root_readme_checked': True,
    'inline_report_images': image_count, 'broken_local_links': broken,
    'mermaid_diagrams': len(diagrams),
    'mermaid_syntax': 'All passed Mermaid 11.12.0 parse',
    'mermaid_render': 'All rendered to SVG/PNG with Mermaid CLI; contact sheet visually reviewed',
    'pdf_count': 8, 'rendered_pdf_pages': 61,
    'selected_pdf_page_images': 13,
    'source_files_hash_checked': len(manifest['files']),
    'official_api_urls_checked': 9,
    'rv32_objects_compiled': 28, 'rv32_object_totals_match_rerun': True,
    'requirements_audited': len(requirement_ids),
    'pending_product_tasks': len(pending_ids),
    'mece_primary_categories': len(categories),
    'mece_unassigned_or_duplicate_ids': [],
    'case_groups': len(case_rows),
    'desktop_demo_build_and_run_passed': True,
    'desktop_demo_psf_bytes': demo['trace_bytes'],
    'desktop_demo_gui_decode_verified': False,
    'swo_original_attached_images': source_images['images_in_package'],
    'calculation_examples': examples,
    'scope_limits': ['No product firmware link', 'No board CPU measurement', 'No hardware UART benchmark'],
}
(base / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
