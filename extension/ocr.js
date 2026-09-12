/* Adaptive-template-v1, ported from ocr_algorithm.py. No network or DOM access. */
(() => {
  "use strict";
  function decodeBytes(base64) {
    const text = atob(base64);
    return Uint8Array.from(text, ch => ch.charCodeAt(0));
  }
  function loadModel(packed) {
    if (packed.version !== "adaptive-template-v1") throw new Error("模型版本不符");
    const bytes = decodeBytes(packed.soft);
    const view = new DataView(bytes.buffer);
    const soft = new Float32Array(bytes.length / 4);
    for (let i = 0; i < soft.length; i++) soft[i] = view.getFloat32(i * 4, true);
    const binary = decodeBytes(packed.binary);
    const labels = Uint8Array.from(packed.labels);
    if (soft.length !== labels.length * 330 || binary.length !== soft.length)
      throw new Error("模型資料不完整");
    const groups = Array.from({length: 10}, (_, d) =>
      Array.from(labels.keys()).filter(i => labels[i] === d));
    if (groups.some(group => group.length < 3)) throw new Error("字元模板不足");
    return {soft, binary, groups};
  }
  function extractFeatures(image) {
    if (image.width !== 100 || image.height !== 40 || image.data.length !== 16000)
      throw new Error("圖片尺寸或格式已改變，請手動輸入");
    const histogram = new Uint32Array(256);
    for (let i = 1; i < image.data.length; i += 4) histogram[image.data[i]]++;
    let count = 0, lower = -1, upper = 0;
    for (let value = 0; value < 256; value++) {
      count += histogram[value];
      if (count >= 2000 && lower < 0) lower = value;
      if (count >= 2001) { upper = value; break; }
    }
    const bg = (lower + upper) / 2;
    const soft = new Float32Array(1650), binary = new Uint8Array(1650);
    for (let digit = 0; digit < 5; digit++) {
      let sum = 0;
      for (let y = 6; y < 28; y++) for (let dx = 0; dx < 15; dx++) {
        const x = 6 + 15 * digit + dx, pixel = (y * 100 + x) * 4;
        const red = image.data[pixel], green = image.data[pixel + 1];
        let signal;
        if (bg > 190) signal = (bg - green) / (bg + 1);
        else if (bg > 85) signal = (red - green) / (256 - bg);
        else signal = red < 100 ? 0 : (red - green) / (x * 2.5 + 15);
        const index = digit * 330 + (y - 6) * 15 + dx;
        soft[index] = Math.max(0, Math.min(1, signal));
        binary[index] = signal > 0.4 ? 1 : 0;
        sum += soft[index];
      }
      if (sum / 330 < 0.03) throw new Error("字元筆畫不足，請手動輸入");
    }
    return {soft, binary};
  }
  function classify(features, templates, groups) {
    let text = "", margin = Infinity, distance = 0;
    for (let position = 0; position < 5; position++) {
      const scores = groups.map((indices, digit) => {
        const best = [Infinity, Infinity, Infinity];
        for (const index of indices) {
          let sum = 0;
          for (let k = 0; k < 330; k++) {
            const difference = features[position * 330 + k] - templates[index * 330 + k];
            sum += difference * difference;
          }
          const value = sum / 330;
          if (value < best[2]) {
            best[2] = value;
            best.sort((a, b) => a - b);
          }
        }
        return {digit, score: (best[0] + best[1] + best[2]) / 3};
      }).sort((a, b) => a.score - b.score || a.digit - b.digit);
      text += scores[0].digit;
      margin = Math.min(margin, scores[1].score - scores[0].score);
      distance = Math.max(distance, scores[0].score);
    }
    return {text, margin, distance};
  }
  function recognize(image, model) {
    const features = extractFeatures(image);
    const soft = classify(features.soft, model.soft, model.groups);
    const binary = classify(features.binary, model.binary, model.groups);
    const reasons = [];
    if (soft.text !== binary.text) reasons.push("兩種處理結果不一致");
    if (soft.margin < 0.02) reasons.push("候選字形接近");
    if (soft.distance > 0.20) reasons.push("字形差距較大");
    return {...soft, alternative: binary.text, review: reasons.length > 0, reasons};
  }
  globalThis.EZPostOCR = Object.freeze({loadModel, extractFeatures, recognize});
})();
