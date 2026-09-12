# 字形模板

`ocr_model.npz` 是由 40 張 development 圖片擷取的 200 個數字字格，包含：

- `soft`：200 × 330 的連續前景特徵。
- `binary`：200 × 330 的二值特徵。
- `labels`：每個字格的 0–9 類別。
- `training_files`、`training_sha256`：來源圖片與雜湊，用於重現與分組檢查。
- `version`：`adaptive-template-v1`。

重建：`python -m ezpost_ocr.training`。同步瀏覽器模板：`python scripts/export_extension_model.py`。

辨識階段比對字格像素，不使用 `training_files` 查詢答案。此格式透過 `allow_pickle=False` 讀取。
