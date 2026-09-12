"""Batch OCR using the supplied grayscale/HSV fallback algorithm."""
import csv
import os
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import pytesseract

ROOT = Path(__file__).resolve().parents[1]
LOCAL_TESSERACT = ROOT / '.tools/tesseract/tesseract.exe'
configured_command = os.environ.get('TESSERACT_CMD')
if configured_command:
    pytesseract.pytesseract.tesseract_cmd = configured_command
elif LOCAL_TESSERACT.exists():
    pytesseract.pytesseract.tesseract_cmd = str(LOCAL_TESSERACT)
    os.environ.setdefault('TESSDATA_PREFIX', str(LOCAL_TESSERACT.parent / 'tessdata'))
os.environ.setdefault('OMP_THREAD_LIMIT', '1')


def digits_only(text):
    return re.sub(r'\D', '', text)


def ocr_digits(img):
    return digits_only(pytesseract.image_to_string(
        img, config='--psm 7 -c tessedit_char_whitelist=0123456789', timeout=30))


def recognize(path):
    # imdecode supports Windows paths containing Chinese characters.
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError('Unable to decode image')
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    enlarged = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    result = ocr_digits(enlarged)
    if len(result) == 5:
        return result, '灰階 + 4x 放大'
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([145, 40, 80]), np.array([170, 255, 255]))
    bw = cv2.resize(255 - mask, None, fx=5, fy=5, interpolation=cv2.INTER_NEAREST)
    return ocr_digits(bw), 'HSV 分離 + 二值化 + 5x 放大'


def process(path):
    try:
        result, method = recognize(path)
        return [path.relative_to(ROOT / 'dataset').as_posix(), result, method,
                len(result), '是' if len(result) == 5 else '否', '']
    except Exception as exc:
        return [path.relative_to(ROOT / 'dataset').as_posix(), '', '', 0, '否', str(exc)]


def main():
    extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
    files = sorted(p for p in (ROOT / 'dataset').rglob('*') if p.suffix.lower() in extensions)
    if not files:
        raise SystemExit('No images in dataset')
    output = ROOT / 'reports/baseline.csv'
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    with output.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream)
        writer.writerow(['檔名', '辨識結果', '辨識方法', '數字位數', '是否5位數', '錯誤訊息'])
        with ThreadPoolExecutor(max_workers=4) as pool:
            for i, row in enumerate(pool.map(process, files), 1):
                writer.writerow(row)
                counts['five_digits' if row[4] == '是' else 'other_length'] += 1
                counts['errors'] += bool(row[5])
                if i % 100 == 0:
                    stream.flush()
                    print(f'{i}/{len(files)} {dict(counts)}', flush=True)
    print(f'Output: {output}', flush=True)


if __name__ == '__main__':
    main()
