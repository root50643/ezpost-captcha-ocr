"""Templates for 100x40 images with five digits at fixed positions.

No filename-to-answer lookup. Scores are distances, not probabilities.
"""
from pathlib import Path
import cv2
import numpy as np

MODEL_VERSION = 'adaptive-template-v1'


def load_image(path):
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('無法解碼圖片')
    if image.shape[:2] != (40, 100):
        raise ValueError('此模型適用 100x40、固定五字位置的圖片')
    return image


def preprocess_image(image):
    """Return the actual full-image intermediate arrays used for recognition."""
    _, green, red = cv2.split(image.astype(np.float32))
    bg = float(np.median(image[:, :, 1]))
    if bg > 190:
        mode = 'green_contrast'
        signal = (bg - green) / (bg + 1)
    elif bg > 85:
        mode = 'red_green_difference'
        signal = (red - green) / (256 - bg)
    else:
        mode = 'gradient_corrected_difference'
        # White-to-magenta text gains chroma from left to right.
        signal = (red - green) / (np.arange(100)[None, :] * 2.5 + 15)
        signal[red < 100] = 0
    soft = np.clip(signal, 0, 1).astype(np.float32)
    binary = (signal > 0.4).astype(np.float32)
    return {'background_green': bg, 'mode': mode, 'signal': signal,
            'soft': soft, 'binary': binary}


def extract_features(image):
    stages = preprocess_image(image)

    def cells(mask):
        return np.stack([mask[6:28, 6 + 15*i:21 + 15*i].ravel() for i in range(5)])

    return cells(stages['soft']), cells(stages['binary'])


def digit_scores(features, templates, labels):
    distances = np.mean((features[:, None, :] - templates[None, :, :])**2, axis=2)
    return np.stack([np.sort(distances[:, labels == d], axis=1)[:, :3].mean(axis=1)
                     for d in range(10)], axis=1)


class DigitRecognizer:
    def __init__(self, model_path):
        with np.load(Path(model_path), allow_pickle=False) as model:
            self.soft = model['soft'].copy()
            self.binary = model['binary'].copy()
            self.labels = model['labels'].copy()
            self.training_files = model['training_files'].tolist()
            version = str(model['version'].item())
        if version != MODEL_VERSION:
            raise ValueError('Unsupported OCR model version')
        if self.soft.shape != self.binary.shape or self.soft.shape != (len(self.labels), 330):
            raise ValueError('Invalid OCR model dimensions')
        if any(np.count_nonzero(self.labels == d) < 3 for d in range(10)):
            raise ValueError('Each digit needs at least three development templates')

    def recognize(self, path):
        soft, binary = extract_features(load_image(path))
        if np.any(soft.mean(axis=1) < 0.03):
            raise ValueError('部分字元位置沒有足夠前景筆畫，需人工複核')
        scores = digit_scores(soft, self.soft, self.labels)
        binary_scores = digit_scores(binary, self.binary, self.labels)
        text = ''.join(str(d) for d in scores.argmin(axis=1))
        alternative = ''.join(str(d) for d in binary_scores.argmin(axis=1))
        ordered = np.sort(scores, axis=1)
        margin = float(np.min(ordered[:, 1] - ordered[:, 0]))
        distance = float(np.max(ordered[:, 0]))
        reasons = []
        if text != alternative:
            reasons.append('灰度與二值版本結果不一致')
        if margin < 0.02:
            reasons.append('候選字形分數接近')
        if distance > 0.20:
            reasons.append('字形與訓練樣本差距較大')
        return {'text': text, 'alternative': alternative, 'margin': margin,
                'distance': distance, 'review_reasons': '；'.join(reasons)}
