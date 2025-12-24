# Stick-and-pull 去伪影

概览
- 去除成像数据中的 stick-and-pull 伪影，输出校正图像与速度曲线 CSV。

API
- POST `/api/augmentation/run`
  - `algorithm`: `stick-and-pull`
  - `image_file`: 输入图像（PNG/JPG）
  - `use_demo`: 传 `true` 使用默认示例图
- 返回：
  - `output_image`: base64 图片预览
  - `download_urls.image`: 校正图像 PNG
  - `download_urls.csv`: 速度曲线 CSV（`row_index`, `depth_norm`, `speed_rel`）

说明
- 默认示例图位于 `packages/geo-core/artifacts/stick-and-pull/stick_pull.png`。
