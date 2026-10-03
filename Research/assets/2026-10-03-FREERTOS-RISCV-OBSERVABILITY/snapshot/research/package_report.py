"""Bundle the report, evidence and referenced local sources without changing them."""
from pathlib import Path
from urllib.parse import unquote, urlparse
from markdown_it import MarkdownIt
import hashlib
import json
import posixpath
import re
import zipfile

root = Path(__file__).resolve().parent.parent
prefix = Path('percepio-observability-research')
target = root / 'percepio-observability-research.zip'
files = set()
for folder in ('research', 'percepio', 'data_from_web/whitepaper', 'Tracealyzer-SDK-demos/GCC_MinGW_x86_64', 'Tracealyzer-STM32CubeIDE-SWO/img'):
    for path in (root / folder).rglob('*'):
        if path.is_file() and '.git' not in path.parts and path.name != '.DS_Store':
            files.add(path)
files.update(root / path for path in (
    'Tracealyzer-STM32CubeIDE-SWO/README.md',
    'Tracealyzer-SDK-demos/README.md',
))

readme = (root / 'README.md').read_text()

with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr(str(prefix / 'README.md'), readme)
    for path in sorted(files):
        archive.write(path, str(prefix / path.relative_to(root)))
    bad = archive.testzip()
    if bad:
        raise RuntimeError(f'Corrupt archive entry: {bad}')
    names = set(archive.namelist())
    checked_links = 0
    markdown_files = 0
    broken = []
    for name in sorted(names):
        if not name.endswith('.md'):
            continue
        markdown_files += 1
        source = archive.read(name).decode('utf-8')
        refs = []
        for token in MarkdownIt('commonmark').enable('table').parse(source):
            for child in token.children or []:
                if child.type in ('link_open', 'image'):
                    refs.append(child.attrGet('src' if child.type == 'image' else 'href'))
        refs.extend(re.findall(r'<img\b[^>]*\bsrc=[\"\x27]([^\"\x27]+)[\"\x27]', source, re.I))
        for href in refs:
            if urlparse(href).scheme or href.startswith('#'):
                continue
            checked_links += 1
            destination = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(href.split('#')[0])))
            if destination not in names and not any(item.startswith(destination.rstrip('/') + '/') for item in names):
                broken.append((name, href))
    if broken:
        raise RuntimeError(f'Broken links in archive: {broken}')
    archive_prefix = str(prefix) + '/'
    assert archive.read(archive_prefix + 'README.md') == (root / 'README.md').read_bytes()
    verified = json.loads(archive.read(archive_prefix + 'research/verification.json'))
    for name, key in (('README.md', 'root_readme_sha256'), ('research/FreeRTOS-RISC-V-Observability-研究報告.md', 'report_sha256')):
        assert hashlib.sha256(archive.read(archive_prefix + name)).hexdigest() == verified[key], f'Run verify_report.py before packaging: {name}'
    manifest = json.loads(archive.read(archive_prefix + 'research/source-manifest.json'))
    for item in manifest['files']:
        assert hashlib.sha256(archive.read(archive_prefix + item['path'])).hexdigest() == item['sha256'], item['path']

print(f'{target.name}: {len(files) + 1} entries, {target.stat().st_size} bytes')
print(f'Archive CRC, {markdown_files} Markdown files, {checked_links} relative Markdown/HTML links, report/README hashes and {len(manifest["files"])} source hashes passed.')
