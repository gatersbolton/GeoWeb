# stick-and-pull artifact removal

Purpose
- Remove stick-and-pull artifacts from imaging data.

Inputs
- Image (PNG/JPG). Optional speed CSV if available.

Outputs
- Corrected image (PNG).
- CSV with `row_index`, `depth_norm`, `speed_rel`.

Notes
- Reference implementation: `fix_stick_pull.py`.
- Demo image: `stick_pull.png`.
