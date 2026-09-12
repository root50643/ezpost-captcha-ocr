import csv
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import pytesseract

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tesseract_baseline as baseline


def masks(img):
    b, g, r = cv2.split(img.astype(np.float32))
    difference = np.clip(r - g, 0, 255).astype(np.uint8)
    _, otsu = cv2.threshold(difference, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Keep weak red strokes too, especially at the dark end of a gradient.
    relative = np.clip((r - g) / (r + g + 1) * 255, 0, 255).astype(np.uint8)
    bg = np.median(img.reshape(-1,3),axis=0)
    if bg[1] > 100:
        signal = 255-img[:,:,1]
    else:
        signal = img[:,:,2]
    _, channel = cv2.threshold(signal,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    hybrid = (((g < bg[1]*0.55) & (bg[1]>100)) | (difference>20) | ((r>160)&(bg[1]<60))).astype(np.uint8)*255
    for m in (channel, hybrid):
        m[:3]=0
        m[-3:]=0
        m[:,:3]=0
        m[:,-3:]=0
    return {'channel': channel,
            'channel_open': cv2.morphologyEx(channel,cv2.MORPH_OPEN,np.ones((2,2),np.uint8)),
            'hybrid':hybrid,
            'hybrid_open':cv2.morphologyEx(hybrid,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))}


def prepare(mask):
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    clean = np.zeros_like(mask)
    for i in range(1, count):
        if stats[i, cv2.CC_STAT_AREA] >= 6:
            clean[labels == i] = 255
    points = cv2.findNonZero(clean)
    if points is None:
        return np.full((100,300),255,np.uint8)
    x,y,w,h = cv2.boundingRect(points)
    cropped = clean[y:y+h, x:x+w]
    enlarged = cv2.resize(255-cropped,None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(enlarged,20,20,20,20,cv2.BORDER_CONSTANT,value=255)


def run(row):
    img = cv2.imdecode(np.fromfile(str(ROOT/'dataset'/row['filename']), np.uint8),cv2.IMREAD_COLOR)
    outputs={}
    for name, mask in masks(img).items():
        prepared=prepare(mask)
        for psm in (7,8):
            text=baseline.digits_only(pytesseract.image_to_string(prepared,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789',timeout=30))
            outputs[f'{name}_psm{psm}']=text
    return {**row,'outputs':outputs}


if __name__=='__main__':
    (ROOT / '.local/ocr-experiments').mkdir(parents=True, exist_ok=True)
    rows=list(csv.DictReader((ROOT/'data/labels.csv').open(encoding='utf-8-sig')))
    rows=[r for r in rows if r['split']=='development']
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(run,rows))
    (ROOT/'.local/ocr-experiments/development_candidates.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    counts=Counter()
    for row in results:
        for key,text in row['outputs'].items():
            counts[key]+=text==row['label']
    print(counts)
    for row in results:
        if not all(s==row['label'] for s in row['outputs'].values()):
            print(row['filename'],row['label'],row['outputs'])
