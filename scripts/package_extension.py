"""Build a deterministic unpacked-extension ZIP from a fixed file allowlist."""
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('manifest.json', 'content.js', 'ocr.js', 'model.js', 'README.md')


def main():
    source = ROOT / 'extension'
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['manifest_version'] == 3
    assert set(manifest['content_scripts'][0]['js']).issubset(FILES)
    destination = ROOT / 'dist/ezpost-captcha-extension.zip'
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (source / name).read_bytes())
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    print(f'Packaged {len(FILES)} files: {destination}')


if __name__ == '__main__':
    main()
