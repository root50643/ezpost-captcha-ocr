"""Render documentation figures from the production pipeline and saved templates.

Run from a checkout installed with: python -m pip install -e ".[docs]"
"""
import json
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ezpost_ocr.algorithm import DigitRecognizer, digit_scores, extract_features, load_image, preprocess_image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs/assets'
INK, MUTED, ACCENT, PAPER = '#142d38', '#5c6b73', '#087e78', '#f2f6f7'
CASES = [('0966', 'BRIGHT BACKGROUND'), ('0845', 'MID-TONE BACKGROUND'), ('0848', 'DARK BACKGROUND')]


def font(size):
    paths = [os.environ.get('DOCS_FONT', ''), 'C:/Windows/Fonts/segoeui.ttf',
             '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/System/Library/Fonts/Helvetica.ttc']
    for path in paths:
        if path and Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def text(canvas, position, value, size=26, color=INK):
    ImageDraw.Draw(canvas).text(position, value, font=font(size), fill=color)


def sheet(width, height, title, subtitle=''):
    canvas = Image.new('RGB', (width, height), PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, 100), fill=INK)
    text(canvas, (28, 12), title, 30, 'white')
    text(canvas, (28, 56), subtitle, 21, '#c7dde0')
    return canvas


def picture(canvas, image, box):
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)
    x, y, width, height = box
    scale = min(width/image.width, height/image.height)
    size = (round(image.width*scale), round(image.height*scale))
    image = image.convert('RGB').resize(size, Image.Resampling.NEAREST)
    canvas.paste(image, (x+(width-size[0])//2, y+(height-size[1])//2))


def mask_image(mask):
    return Image.fromarray(np.round(np.clip(mask,0,1)*255).astype(np.uint8))


def save(name, canvas):
    canvas.save(OUTPUT/name, optimize=True)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    model = DigitRecognizer(ROOT/'models/ocr_model.npz')
    metadata = []
    overview = sheet(1360, 865, 'ADAPTIVE COLOR SEPARATION',
                     'Real dataset images -> continuous foreground -> binary mask -> five digit cells')
    for column, title in enumerate(['SOURCE IMAGE', 'FOREGROUND STRENGTH', 'BINARY MASK', 'DIGIT CELLS']):
        text(overview, (25+column*337, 119), title, 22)
    for row, (number, title) in enumerate(CASES):
        path = ROOT/f'dataset/captcha_{number}.jpg'
        image = load_image(path)
        stages = preprocess_image(image)
        soft, binary = extract_features(image)
        result = model.recognize(path)
        metadata.append({'filename': path.name, 'mode': stages['mode'],
                         'background_green': stages['background_green'], 'prediction': result['text']})
        y = 170+row*225
        text(overview, (25, y), f"{title}  /  G median: {stages['background_green']:g}", 24, ACCENT)
        panels = [Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)), mask_image(stages['soft']),
                  mask_image(stages['binary']), mask_image(soft.reshape(5,22,15).transpose(1,0,2).reshape(22,75))]
        for column, panel in enumerate(panels):
            picture(overview, panel, (25+column*337,y+40,305,125))
        text(overview, (1040,y+168), 'Result: '+result['text'], 23, ACCENT)
    save('pipeline-overview.png', overview)

    image = load_image(ROOT/'dataset/captcha_0966.jpg')
    rgb = Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB))
    stages = preprocess_image(image)
    soft, binary = extract_features(image)
    result = model.recognize(ROOT/'dataset/captcha_0966.jpg')

    panel = sheet(1120, 410, '01 / ORIGINAL IMAGE', 'captcha_0966.jpg | 100 x 40 pixels | label: 30607')
    picture(panel,rgb,(160,125,800,255));save('stage-01-original.png',panel)
    panel = sheet(1200, 380, '02 / COLOR CHANNELS', f"Background estimate: median(G) = {stages['background_green']:g}")
    for i,(label,index) in enumerate([('RED',2),('GREEN',1),('BLUE',0)]):
        text(panel,(30+i*395,122),label,25)
        picture(panel,Image.fromarray(image[:,:,index]),(30+i*395,170,350,155))
    save('stage-02-channels.png',panel)
    panel = sheet(1120,410,'03 / CONTINUOUS FOREGROUND','Bright background: S = (b - G) / (b + 1); clip to [0, 1]')
    picture(panel,mask_image(stages['soft']),(160,125,800,255));save('stage-03-foreground.png',panel)
    panel = sheet(1120,410,'04 / BINARY FOREGROUND','B = 1 when S > 0.4, otherwise 0; white pixels represent strokes')
    picture(panel,mask_image(stages['binary']),(160,125,800,255));save('stage-04-binary.png',panel)
    panel = sheet(1120,450,'05 / FIXED DIGIT WINDOWS','Five 15 x 22 cells | x = 6 + 15i | y = 6..27 | zero-based coordinates')
    scaled = rgb.resize((800,320),Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(scaled)
    for i in range(5):
        draw.rectangle(((6+15*i)*8,6*8,(21+15*i)*8-1,28*8-1),outline='#ffc640',width=3)
    panel.paste(scaled,(160,115));save('stage-05-windows.png',panel)
    panel = sheet(1200,660,'06 / PER-DIGIT FEATURES','Each cell becomes a 330-value vector; continuous and binary versions use the same windows')
    for row,(name,features) in enumerate([('CONTINUOUS',soft),('BINARY',binary)]):
        y=130+row*255
        text(panel,(25,y),name,23,ACCENT)
        for i,vector in enumerate(features):
            x=225+i*185
            picture(panel,mask_image(vector.reshape(22,15)),(x,y,125,184))
            text(panel,(x,y+197),f'{i+1}: {result["text"][i]}',24)
    save('stage-06-glyphs.png',panel)

    scores = digit_scores(soft,model.soft,model.labels)
    ordering = np.argsort(scores[0])
    panel = sheet(1360,705,'07 / TEMPLATE MATCHING',
                  'First digit: compare the three closest templates of each class; lower mean squared distance wins')
    for row,digit in enumerate(ordering[:2]):
        y=127+row*245
        text(panel,(25,y),f'CANDIDATE {digit}',26,ACCENT if row==0 else MUTED)
        picture(panel,mask_image(soft[0].reshape(22,15)),(28,y+47,112,165))
        eligible=np.flatnonzero(model.labels==digit)
        distances=np.mean((model.soft[eligible]-soft[0])**2,axis=1)
        nearest=eligible[np.argsort(distances)[:3]]
        text(panel,(175,y+107),'vs.',27,MUTED)
        for j,index in enumerate(nearest):
            x=280+j*235
            picture(panel,mask_image(model.soft[index].reshape(22,15)),(x,y+47,112,165))
            text(panel,(x,y+3),f'Template {j+1}',23)
        text(panel,(1010,y+60),f'Mean distance',24)
        text(panel,(1010,y+102),f'{scores[0,digit]:.6f}',34,ACCENT if row==0 else MUTED)
    text(panel,(28,644),'FULL RESULT: '+result['text']+'    |    This figure shows the actual model neighbours.',26,ACCENT)
    save('stage-07-matching.png',panel)
    (OUTPUT/'examples.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print('Rendered pipeline overview and seven production-stage figures.')


if __name__ == '__main__':
    main()
