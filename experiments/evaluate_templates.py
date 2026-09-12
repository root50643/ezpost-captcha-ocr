import csv
from pathlib import Path
import cv2
import numpy as np
from evaluate_candidates import masks, ROOT


def features(path,variant='hybrid'):
    img=cv2.imdecode(np.fromfile(str(path),np.uint8),1)
    if variant in ('hybrid','hybrid_open'):
        mask=masks(img)[variant]
    else:
        b,g,r=cv2.split(img.astype(np.float32))
        bg=np.median(img.reshape(-1,3),axis=0)
        if bg[1]>190:
            signal=(bg[1]-g)/(bg[1]+1)
        elif bg[1]>85:
            signal=(r-g)/(255-bg[1]+1)
        else:
            signal=(r-g)/(np.arange(img.shape[1])[None,:]*2.5+15)
            signal[r<100]=0
        if variant=='adaptive_binary':
            mask=(signal>0.4).astype(np.uint8)*255
        else:
            mask=np.clip(signal,0,1)*255
    return np.stack([mask[6:28,6+i*15:21+i*15].astype(np.float32).ravel()/255 for i in range(5)])


def classify(f,train,labels):
    distance=((f[:,None,:]-train[None,:,:])**2).mean(axis=2)
    scores=np.stack([np.sort(distance[:,labels==d],axis=1)[:,:3].mean(axis=1) for d in range(10)],axis=1)
    pred=scores.argmin(axis=1)
    margin=np.sort(scores,axis=1)[:,1]-scores.min(axis=1)
    return ''.join(map(str,pred)),margin.min()


if __name__=='__main__':
    rows=[r for r in csv.DictReader((ROOT/'data/labels.csv').open(encoding='utf-8-sig')) if r['split']=='development']
    y=np.array([[int(d) for d in r['label']] for r in rows])
    for variant in ('hybrid','hybrid_open','adaptive_binary','adaptive_soft'):
        x=np.stack([features(ROOT/'dataset'/r['filename'],variant) for r in rows])
        correct=0
        for i,r in enumerate(rows):
            keep=np.arange(len(rows))!=i
            pred,margin=classify(x[i],x[keep].reshape(-1,330),y[keep].ravel())
            correct+=pred==r['label']
            if pred!=r['label']:
                print(variant,r['filename'],r['label'],pred,float(margin))
        print(variant,'Leave-one-image-out development exact match:',correct,'/',len(rows))
