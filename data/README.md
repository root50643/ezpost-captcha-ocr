# 標註資料

`labels.csv` 包含 120 張目視標註：40 張 development、60 張 holdout、20 張 holdout_extra。

- `filename`：相對於 `dataset/` 的檔名。
- `label`：五位數文字，須保留前導零。
- `split`：用途分組，只有 development 用於建立模板。

標註來源、抽樣方式與一次修正紀錄見 [驗證說明](../docs/VALIDATION.md)。
