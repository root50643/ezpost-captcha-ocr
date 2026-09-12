# EZPost 登入驗證碼自動填入

Chrome／Microsoft Edge 的 Manifest V3 擴充套件。開啟指定登入頁後，會辨識頁面已顯示的驗證碼圖片並填入欄位；按網站的「重新整理」換圖時，也會更新結果。

## 安裝

1. 解壓縮 ZIP。選用專案中的 `extension` 資料夾亦可。
2. Chrome 開啟 `chrome://extensions`；Edge 開啟 `edge://extensions`。
3. 開啟「開發人員模式」。
4. 按「載入未封裝項目」或「載入解壓縮」，選擇**直接包含 `manifest.json` 的資料夾**。
5. 開啟或重新整理 https://ezpost.post.gov.tw/Account/Login 。驗證碼欄位下方出現「驗證碼已自動填入」即表示完成。

ZIP 無法直接拖入安裝。載入後請保留該資料夾；更新套件檔案後，先在擴充功能管理頁按「重新載入」，再重新整理登入頁。

## 啟用範圍與行為

- 限定 `https://ezpost.post.gov.tw/Account/Login`，同一路徑的查詢參數與頁面錨點亦適用。
- `/Account/LoginExtra`、`/Account/Login/`、其他路徑、其他主機或 HTTP 均不啟用；嵌入框架亦不啟用。
- 目標為登入表單 `#form-login` 的圖片 `#imgCode` 與欄位 `#inputCaptcha[name='Code']`。
- 將頁面已載入的圖片畫到本機 Canvas 後辨識，沒有另發驗證碼請求，不會因重新下載圖片而改變該次驗證碼。
- 辨識與模型都在瀏覽器內執行，不需 Python、Tesseract、伺服器或 API 金鑰。
- 只填入圖形驗證碼，不讀取帳號或密碼、不提交登入表單，也不傳送辨識資料。
- 換圖會重新辨識。已填入後手動修改欄位，同一張圖片不會因無關的頁面變動被重複覆寫。
- 出現「建議核對圖片」時，可直接修正欄位；無法辨識或圖片載入失敗時會顯示手動處理提示。

## 模型與測試

模型移植自此專案的 `adaptive-template-v1`：依背景調整色彩分離，擷取五個固定字格，各比對 0–9 的最近三個字形模板。模板由 40 張圖片建立，適用本批 100×40、固定字型與位置的圖片。

驗證日期：2026-09-12。

- 在隔離的 Chrome for Testing 中實際載入擴充套件，驗證初次填入、前導零、換圖、連續換圖、圖片 DOM 替換、手動修正保留、錯誤提示，以及限定網址。
- 瀏覽器 Canvas 解碼並辨識全部 1,000 張資料集圖片，輸出與 Python 版完全一致。
- 未參與模板建立的 80 張目視核對樣本：80/80 正確。這是抽樣結果，不代表每張新圖片都會正確。
- 實際 EZPost 登入頁載入及換圖共三次，輸出 `54623`、`97448`、`20364`，均與畫面圖片核對一致。測試只確認填入，未提交登入，也未驗證伺服器接受結果。
- Edge 使用相同的 Chromium 擴充套件格式；本次動態測試使用 Chrome for Testing。

如果網站改變驗證碼字型、大小、位置、色彩或頁面結構，需要重新調整模型或選擇器。分數接近提示不是正確機率。

## 檔案

`manifest.json` 限定頁面與載入順序；`model.js` 內嵌數字模板；`ocr.js` 負責辨識；`content.js` 處理換圖監聽、填入與狀態提示。

完整專案內的 `scripts/export_extension_model.py` 可由 `models/ocr_model.npz` 重建 `model.js`。開發驗證程式位於 `tests/browser/`，結果位於 `reports/`，不包含在安裝套件中。根目錄 README 另有完整演算法圖例與實際頁面截圖。

## 官方參考

- [Chrome content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)
- [Chrome URL match patterns](https://developer.chrome.com/docs/extensions/develop/concepts/match-patterns)
- [Edge 載入未封裝擴充套件](https://learn.microsoft.com/en-us/microsoft-edge/extensions/getting-started/extension-sideloading)
