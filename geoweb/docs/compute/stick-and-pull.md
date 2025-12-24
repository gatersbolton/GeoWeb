# Stick-and-pull artifact removal

Overview
- Removes stick-and-pull artifacts from imaging data and exports a corrected image plus a speed profile CSV.

API
- POST `/api/augmentation/run`
  - `algorithm`: `stick-and-pull`
  - `image_file`: input image (PNG/JPG)
  - `use_demo`: `true` to use the default sample image
- Response:
  - `output_image`: base64 data URL for quick preview
  - `download_urls.image`: corrected PNG
  - `download_urls.csv`: speed profile CSV (`row_index`, `depth_norm`, `speed_rel`)

Notes
- Default demo image resides in `packages/geo-core/artifacts/stick-and-pull/stick_pull.png`.
