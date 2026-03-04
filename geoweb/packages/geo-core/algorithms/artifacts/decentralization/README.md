# decentralization

`artifact.decentralization.v1` supports three parameter-selectable methods.

## How To Select Method
- config key: `safe.method`
- values:
  - `harmonic` (method A)
  - `azimuth_equalization` (method B)
  - `agc` (method C)

Example:

```json
{
  "safe": {
    "enable": true,
    "method": "harmonic",
    "fallback_to_identity_on_error": true
  }
}
```

## Method A: Low-Order Azimuth Harmonic Removal
Core idea:
- For each depth, model azimuth response `A(theta)` as low-order background + high-frequency detail.
- Fit first and second azimuth harmonics, then subtract them.

Discrete form (`M` azimuth samples, fixed depth):
- `a1 = (2/M) * sum(A_m * cos(theta_m))`
- `b1 = (2/M) * sum(A_m * sin(theta_m))`
- `a2 = (2/M) * sum(A_m * cos(2*theta_m))`
- `b2 = (2/M) * sum(A_m * sin(2*theta_m))`
- `A_bg(theta) = a1*cos(theta) + b1*sin(theta) + a2*cos(2*theta) + b2*sin(2*theta)`
- `A_corr(theta) = A(theta) - A_bg(theta)`

Engineering note:
- Coefficients are smoothed along depth (`advanced.harmonic_depth_smooth_window`) to reduce jitter.

Relevant params:
- `advanced.harmonic_orders`
- `advanced.harmonic_depth_smooth_window`
- `advanced.harmonic_preserve_row_mean`
- `advanced.harmonic_strength`

## Method B: Azimuth Equalization
Core idea:
- In a depth window, estimate per-azimuth background level `mu_m`.
- Use azimuth reference `mu_ref` (median over azimuth) and equalize.

Typical multiplicative form:
- `A_corr(theta_m, z) = A(theta_m, z) * mu_ref(z) / (mu_m(z) + eps)`

Characteristics:
- Good for suppressing long-term fixed azimuth bright/dark bias.
- Less direct than method A when eccentric direction changes rapidly with depth.

Relevant params:
- `advanced.equalization_depth_window`
- `advanced.equalization_stat` (`median` or `mean`)
- `advanced.equalization_mode` (`multiplicative` or `additive`)
- `advanced.equalization_epsilon`
- `advanced.equalization_clip_gain_min/max`
- `advanced.equalization_strength`
- `advanced.equalization_preserve_row_mean`

## Method C: RMS/Envelope AGC
Core idea:
- Normalize local energy in a moving window so local RMS is close to target.

For sequence `x[i]`:
- `RMS[i] = sqrt(mean(x[j]^2, j in win(i)))`
- `g[i] = T / (RMS[i] + eps)`
- `y[i] = g[i] * x[i]`

Characteristics:
- Enhances visual uniformity.
- May weaken quantitative amplitude comparability.

Relevant params:
- `advanced.agc_window`
- `advanced.agc_axis` (`depth` or `azimuth`)
- `advanced.agc_target_rms` (relative target scale around each trace's median local RMS)
- `advanced.agc_epsilon`
- `advanced.agc_clip_gain_min/max`
- `advanced.agc_strength`
- `advanced.agc_preserve_row_mean`

## Shared Stripe Debias Post-Step
After A/B/C, the implementation applies an optional column debias stage to suppress
persistent bright/dark azimuth stripes.

Key params:
- `advanced.column_debias_strength`
- `advanced.column_debias_stat`
- `advanced.column_debias_smooth_window`
- `advanced.column_debias_preserve_row_mean`

## API/Framework Notes
- Input layout supports `HW`, `HWC`, `CHW`.
- Output keeps input layout.
- Optional preview output can be enabled by:
  - `experimental.enable_preview_assets=true`
  - providing `RunContext.output_dir`
