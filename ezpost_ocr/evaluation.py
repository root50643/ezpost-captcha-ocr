"""Reproduce exact-string evaluation and enforce image/hash train-test separation."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from .algorithm import DigitRecognizer, digit_scores, extract_features, load_image

ROOT = Path(__file__).resolve().parents[1]


def read_csv(name):
    with (ROOT / name).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    labels = read_csv('data/labels.csv')
    baseline = {r['檔名']: r for r in read_csv('reports/baseline.csv')}
    improved_rows = read_csv('reports/predictions.csv')
    improved = {r['檔名']: r for r in improved_rows}
    dataset = {p.name for p in (ROOT / 'dataset').glob('*.jpg')}
    assert len(improved_rows) == len(improved) == len(dataset) == 1000
    assert set(improved) == set(baseline) == dataset
    assert len({r['filename'] for r in labels}) == len(labels)
    model = DigitRecognizer(ROOT / 'models/ocr_model.npz')
    training = [r for r in labels if r['split'] == 'development']
    holdout = [r for r in labels if r['split'].startswith('holdout')]
    assert set(model.training_files) == {r['filename'] for r in training}
    assert not set(model.training_files).intersection(r['filename'] for r in holdout)
    digest = lambda r: hashlib.sha256((ROOT/'dataset'/r['filename']).read_bytes()).hexdigest()
    assert not {digest(r) for r in training}.intersection(digest(r) for r in holdout)
    with np.load(ROOT/'models/ocr_model.npz', allow_pickle=False) as packed:
        assert packed['training_sha256'].tolist() == [digest(r) for r in training]
    summary = {'training_images': len(training), 'holdout_images': len(holdout),
               'total_images': len(improved), 'review_images': sum(r['需人工複核']=='是' for r in improved_rows),
               'errors': sum(bool(r['錯誤訊息']) for r in improved_rows)}
    comparisons = []
    for row in labels:
        name = row['filename']
        prediction = model.recognize(ROOT/'dataset'/name)['text']
        assert prediction == improved[name]['辨識結果']
        comparisons.append({**row, 'baseline': baseline[name]['辨識結果'], 'improved': prediction,
                            'baseline_correct': baseline[name]['辨識結果']==row['label'],
                            'improved_correct': prediction==row['label'],
                            'review': improved[name]['需人工複核']})
    for split in ('development', 'holdout', 'holdout_extra'):
        subset = [r for r in comparisons if r['split']==split]
        summary[split] = {key: sum(r[key] for r in subset) for key in ('baseline_correct','improved_correct')}
        summary[split]['count'] = len(subset)
    # Development result with the entire source image excluded, not just one digit.
    loo_correct = 0
    for row in training:
        keep = np.repeat(np.array(model.training_files) != row['filename'], 5)
        features, _ = extract_features(load_image(ROOT/'dataset'/row['filename']))
        scores = digit_scores(features, model.soft[keep], model.labels[keep])
        prediction = ''.join(str(d) for d in scores.argmin(axis=1))
        loo_correct += prediction == row['label']
    summary['development_leave_one_image_out_correct'] = loo_correct
    # Leading zeros remain identifiers in CSV, not integers.
    assert all(r['辨識結果'].isascii() and r['辨識結果'].isdigit() and len(r['辨識結果'])==5 for r in improved_rows)
    assert all(improved[r['filename']]['辨識結果'].startswith('0') for r in holdout if r['label'].startswith('0'))
    with (ROOT/'reports/evaluation.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    (ROOT/'reports/evaluation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    for row in comparisons:
        if not row['improved_correct']:
            print('MISMATCH',row)


if __name__ == '__main__':
    main()
