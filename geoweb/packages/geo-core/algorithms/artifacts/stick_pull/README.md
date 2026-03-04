# stick_pull

`artifact.stick_pull.v1` has been migrated from `source-code/stick-and-pull`.

## Behavior
- Input: `InputFrame.data` in `HW/HWC/CHW`
- Flow:
  - estimate speed profile from image, or load it from `safe.speed_profile_csv`
  - build depth axis by integrating speed
  - resample image along depth (stick-and-pull correction)
- Output: corrected array in the same layout and numeric range style as input

## Config keys
- `safe.enable`: enable/disable correction
- `safe.speed_profile_csv`: optional CSV path
- `safe.speed_column`: optional CSV column name
- `advanced.power/q_clip_*/smooth_window`: speed profile shaping
- `experimental.enable_preview_assets`: write preview image when `RunContext.output_dir` is provided
