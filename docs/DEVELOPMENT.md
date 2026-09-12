# 開發與重現

所有命令均從專案根目錄執行。Python 使用 editable 安裝，讓腳本、測試與文件產生器共用 `ezpost_ocr` 套件。

## Python 環境

```bash
python -m pip install -e ".[docs]"
python -m unittest discover -s tests -v
python -m ezpost_ocr
python -m ezpost_ocr.evaluation
```

也可以在既有 Conda 環境中安裝；需有 NumPy 與 OpenCV。`docs` 額外安裝 Pillow。

此次實測 Python 3.12、NumPy 2.5.3、OpenCV 5.0.0.93。相依範圍定義於 [`pyproject.toml`](../pyproject.toml)；其他版本仍應重新執行測試。

## 重建模板與擴充套件

```bash
python -m ezpost_ocr.training
python scripts/export_extension_model.py
python scripts/package_extension.py
```

模板建立只讀取 `split=development` 的標註。產物是 `models/ocr_model.npz`；匯出器再產生 `extension/model.js`。更新模板後需同步匯出，避免 Python 與擴充套件使用不同模型。

ZIP 輸出至 `dist/ezpost-captcha-extension.zip`，使用固定檔案清單，只含 manifest、三個 JavaScript 檔案與安裝說明。`dist/` 不列入 Git，可在使用者要求發布時附到 GitHub Release。

## 瀏覽器測試

```bash
npm install
npx playwright install chromium
npm test
```

Linux CI 可改用 `npx playwright install --with-deps chromium` 安裝系統相依項目。測試真正載入未封裝的擴充套件，使用本機資料集供應測試圖片，並檢查 1,000 張結果與 Python 輸出的對應關係。

若已安裝相容的 Chrome for Testing，可透過 `EZPOST_CHROMIUM_EXECUTABLE` 指定執行檔；或依 Playwright 設定 `PLAYWRIGHT_BROWSERS_PATH`。程式沒有寫死個人使用者目錄或瀏覽器版本路徑。

一般 `npm test` 不連線至實際網站。下列測試會主動開啟 EZPost 登入頁，初次載入後換圖兩次，保存圖片、表單截圖與 JSON 結果：

```bash
npm run test:live
```

輸出為 `docs/assets/live-form.png`、`docs/assets/live-captcha-*.png` 與 `reports/live_results.json`。執行後請目視核對圖片與數字，並更新 README 中的日期、圖例文字及實測值。測試不輸入帳密、不送出登入表單。

## 重建演算法圖例

```bash
python -m pip install -e ".[docs]"
python scripts/build_docs_images.py
```

產生流程總覽與七張階段圖至 `docs/assets/`。使用正式的 `preprocess_image`、`extract_features`、`digit_scores` 和已存模板；沒有另寫一套視覺效果取代真實演算法。原圖均來自現有資料集，最近鄰放大用於顯示。`examples.json` 記錄三個圖例的來源、背景值與結果。

預設尋找常見系統字型，也可用 `DOCS_FONT` 指定 TTF／TTC 路徑。圖中的短標題採英文，README 以繁體中文說明各階段。

## 原版與開發實驗

`experiments/` 保留 Tesseract 基準、色彩處理候選比較與模板逐張排除實驗。這些不會被擴充套件或正式 Python 辨識流程載入。

```bash
python -m pip install -e ".[baseline]"
python experiments/tesseract_baseline.py
python experiments/evaluate_candidates.py
python experiments/evaluate_templates.py
```

Tesseract 基準另需系統安裝 Tesseract 和英文模型。可將 `tesseract` 加入 PATH，或以 `TESSERACT_CMD` 指定執行檔；如使用非標準語言資料位置，可設定 `TESSDATA_PREFIX`。Windows 上建議 Tesseract 的執行檔與模型放在純英文路徑。候選實驗輸出至 `.local/ocr-experiments/`。

## 額外下載資料

現有 1,000 張圖片已包含在 `dataset/`，一般使用不需要重新下載。收集新的測試樣本可執行：

```powershell
pwsh -File scripts/download_dataset.ps1 -Count 20 -OutputDirectory .local/new-dataset -DelayMs 500
```

此工具只接受空目錄，預設輸出到 `.local/downloads/`，避免覆蓋已標註的資料集。新圖片需重新標註，不能因為檔名相同就套用既有答案。

## 舊檔名對照

| 舊入口／位置 | 整理後 |
| --- | --- |
| `recognize_dataset.py` | `python -m ezpost_ocr` |
| `ocr_algorithm.py` | `ezpost_ocr/algorithm.py` |
| `train_ocr_model.py` | `python -m ezpost_ocr.training` |
| `evaluate_ocr.py` | `python -m ezpost_ocr.evaluation` |
| `export_extension_model.py` | `scripts/export_extension_model.py` |
| `ocr_model.npz` | `models/ocr_model.npz` |
| `ocr_labels.csv` | `data/labels.csv` |
| `ocr_results.csv` | `reports/baseline.csv` |
| `ocr_results_improved.csv` | `reports/predictions.csv` |
| `extension_work/test_*.mjs` | `tests/browser/` |
| `OCR_README.md` | 根目錄 `README.md` 與 `docs/` |

舊的暫存網頁、瀏覽器個人資料與實驗中間檔保留在本機 `.local/`，不納入 Git。`extension/` 目錄位置維持不變，已載入的擴充套件可直接重新載入。
