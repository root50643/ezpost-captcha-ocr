"""Check repository Markdown links and model/extension synchronization offline."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    documents = [ROOT/'README.md']
    for folder in ('docs', 'extension', 'data', 'models'):
        documents.extend((ROOT/folder).rglob('*.md'))
    failures = []
    references = 0
    for path in documents:
        content = path.read_text(encoding='utf-8')
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', content):
            if target.startswith(('https://', 'http://', '#', 'mailto:')):
                continue
            relative = unquote(target.split('#', 1)[0])
            references += 1
            if not (path.parent/relative).exists():
                failures.append(f'{path.relative_to(ROOT)}: missing {target}')
    source = (ROOT/'extension/model.js').read_text(encoding='utf-8')
    packed = json.loads(source.split('Object.freeze(', 1)[1].rsplit(');', 1)[0])
    digest = hashlib.sha256((ROOT/'models/ocr_model.npz').read_bytes()).hexdigest()
    if packed['sourceSha256'] != digest:
        failures.append('Extension model is out of sync; run scripts/export_extension_model.py')
    if failures:
        raise SystemExit('\n'.join(failures))
    print(f'PASS: {len(documents)} Markdown files, {references} local links, synchronized extension model.')


if __name__ == '__main__':
    main()
