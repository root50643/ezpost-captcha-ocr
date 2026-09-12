# 驗證與資料說明

## 資料與分組

[`dataset/manifest.csv`](../dataset/manifest.csv) 記錄原始下載來源、日期、尺寸、大小與 SHA-256。現有資料共 1,000 張；重新下載同一網址會取得不同圖片，不能以新下載內容覆蓋現有檔名後繼續沿用標註。

使用 NumPy 亂數產生器 `default_rng(20260912)`，從按檔名排序的 1,000 張圖片中不重複抽取 120 張，將抽中索引排序。前 40 張為 development，接續 60 張為 holdout，最後 20 張為 holdout_extra。這是一次固定抽樣，不是多次交叉驗證或跨網站測試。

[`data/labels.csv`](../data/labels.csv) 欄位為 `filename`、`label`、`split`。標註由助手目視核對，沒有官方 ground truth；可開啟對應原圖再次複核。

## 標註修正紀錄

最初縮圖核對時，`captcha_0688.jpg` 被標為 `81268`。第一次 holdout 評估時，連續與二值模板均輸出 `81266`。查看原始圖片後確認最後一字為 `6`，因此將標註改為 `81266`。

![曾修正標註的原始圖片，內容為 81266](../dataset/captcha_0688.jpg)

這次修正只更正答案，沒有將該圖片加入模板，也沒有據此調整演算法。20 張 holdout_extra 在演算法定案後才核對，結果為 20 / 20。報告中的 80 / 80 使用修正後標註；此程序仍有目視標註與小樣本的不確定性。

## 計分方式

只有整個五位數字串與標註完全相同，才計為正確，包含前導零。空字串、錯誤位數或任何一位錯誤都計為不正確。

40 張 development 圖片只提供模板。評估另外執行逐張排除：辨識某張 development 圖片時，先刪去來自該圖片的所有五個模板，避免只排除單字卻仍留下同圖模板。

[`ezpost_ocr/evaluation.py`](../ezpost_ocr/evaluation.py) 會檢查：

- 輸出 CSV 與 1,000 張資料集的檔名集合相符。
- 標註檔名唯一，且 development 與 holdout 的檔名及圖片 SHA-256 不重疊。
- 模型紀錄的來源圖片雜湊仍與 development 檔案一致。
- 已存 CSV 與當前模型重算的標註樣本預測一致。
- 前導零與五位數字串保持為文字。

## 報告

| 輸出 | 內容 |
| --- | --- |
| [baseline.csv](../reports/baseline.csv) | 原版 Tesseract 的 1,000 張輸出 |
| [predictions.csv](../reports/predictions.csv) | 新版輸出及複核原因 |
| [evaluation.csv](../reports/evaluation.csv) | 120 張標註樣本的逐筆比較 |
| [evaluation.json](../reports/evaluation.json) | 分組、交叉驗證與全批統計 |
| [integration_results.json](../reports/integration_results.json) | 真正載入擴充套件的瀏覽器測試及 Python 一致性 |
| [live_results.json](../reports/live_results.json) | 2026-09-12 實際登入頁三次圖片填入結果 |

瀏覽器測試使用隔離的 Chrome for Testing 個人資料目錄。實際頁面截圖保留空白帳號與密碼；只確認圖片顯示、辨識、事件觸發與欄位填入，未驗證伺服器接受驗證碼或登入成功。Edge 尚未單獨執行動態測試。
