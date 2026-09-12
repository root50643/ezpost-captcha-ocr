"""Build templates only from split=development in data/labels.csv."""
import csv
import hashlib
from pathlib import Path
import numpy as np
from .algorithm import MODEL_VERSION, extract_features, load_image

ROOT = Path(__file__).resolve().parents[1]


def main():
    with (ROOT / 'data/labels.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = [r for r in csv.DictReader(stream) if r['split'] == 'development']
    if len({r['filename'] for r in rows}) != len(rows):
        raise ValueError('Duplicate training files')
    soft, binary, labels, hashes = [], [], [], []
    for row in rows:
        if len(row['label']) != 5 or any(c not in '0123456789' for c in row['label']):
            raise ValueError(f"Invalid label: {row['filename']}")
        path = ROOT / 'dataset' / row['filename']
        a, b = extract_features(load_image(path))
        soft.append(a)
        binary.append(b)
        labels.extend(int(d) for d in row['label'])
        hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
    if any(labels.count(d) < 3 for d in range(10)):
        raise ValueError('Each digit needs at least three training examples')
    (ROOT / 'models').mkdir(exist_ok=True)
    np.savez_compressed(ROOT / 'models/ocr_model.npz', version=MODEL_VERSION,
                        soft=np.concatenate(soft), binary=np.concatenate(binary),
                        labels=np.array(labels, dtype=np.uint8),
                        training_files=np.array([r['filename'] for r in rows]),
                        training_sha256=np.array(hashes))
    print(f'Trained on {len(rows)} images / {len(labels)} digits; no holdout images used.')


if __name__ == '__main__':
    main()
