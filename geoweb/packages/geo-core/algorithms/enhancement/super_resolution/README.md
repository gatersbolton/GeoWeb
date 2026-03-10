# super_resolution

Real-ESRGAN-backed implementation for `enhancement.super_resolution.v1`.

- Unified input contract: `InputFrame.data` uses `numpy.ndarray(float32)` with `HW/HWC/CHW`.
- Unified output contract: returns `OutputFrame.result` as `float32`, preserves declared `value_range`, and can emit preview assets.
- Local source dependency: wraps `packages/geo-core/source-code/Real-ESRGAN`.
- Default behavior keeps output size unchanged with `advanced.outscale=1.0`; Agent or API can request larger scales like `2.0` or `4.0`.
- Default `advanced.detail_strength=0.72` blends the Real-ESRGAN output with a bicubic resize baseline, reducing over-sharpened results in common ATV use cases.
