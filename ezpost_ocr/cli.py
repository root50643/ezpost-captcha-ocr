"""Batch OCR: python -m ezpost_ocr [--dataset PATH] [--output PATH]."""
import argparse
import csv
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from .algorithm import DigitRecognizer

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['檔名', '辨識結果', '辨識方法', '數字位數', '是否5位數', '需人工複核',
          '複核原因', '二值版本結果', '最小候選分差', '最大字形距離', '錯誤訊息']


@lru_cache(maxsize=1)
def default_model():
    return DigitRecognizer(ROOT / 'models/ocr_model.npz')


def recognize(path):
    """Keep the original (text, method) interface for callers."""
    result = default_model().recognize(path)
    return result['text'], '自適應色彩分離 + 逐字模板比對'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT / 'dataset')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/predictions.csv')
    parser.add_argument('--model', type=Path, default=ROOT / 'models/ocr_model.npz')
    args = parser.parse_args()
    extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
    files = sorted(p for p in args.dataset.rglob('*') if p.is_file() and p.suffix.lower() in extensions)
    if not files:
        raise SystemExit('No images in dataset')
    model = DigitRecognizer(args.model)

    def process(path):
        row = dict.fromkeys(FIELDS, '')
        row['檔名'] = path.relative_to(args.dataset).as_posix()
        try:
            result = model.recognize(path)
            row.update({'辨識結果': result['text'], '辨識方法': '自適應色彩分離 + 逐字模板比對',
                        '數字位數': len(result['text']), '是否5位數': '是',
                        '需人工複核': '是' if result['review_reasons'] else '否',
                        '複核原因': result['review_reasons'], '二值版本結果': result['alternative'],
                        '最小候選分差': f"{result['margin']:.6f}",
                        '最大字形距離': f"{result['distance']:.6f}"})
        except Exception as exc:
            row.update({'數字位數': 0, '是否5位數': '否', '需人工複核': '是', '錯誤訊息': str(exc)})
        return row

    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    with args.output.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        with ThreadPoolExecutor(max_workers=4) as pool:
            for row in pool.map(process, files):
                writer.writerow(row)
                counts['total'] += 1
                counts['review'] += row['需人工複核'] == '是'
                counts['errors'] += bool(row['錯誤訊息'])
    print(dict(counts))
    print(f'Output: {args.output}')


if __name__ == '__main__':
    main()
