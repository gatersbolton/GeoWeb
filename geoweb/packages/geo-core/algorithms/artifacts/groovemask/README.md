# groovemask

`artifact.groovemask.v1` wraps the `source-code/groovemask` pipeline and exposes it as a unified GeoWeb artifact-removal algorithm.

- Targets stabilizer groove / slot-like vertical artifacts on unwrapped borehole images.
- Preserves GeoWeb `InputFrame`/`OutputFrame` conventions for `HW/HWC/CHW` float32 data.
- Supports `detect-only` and `clean` modes.
- Can emit auxiliary preview assets including `mask`, `overlay`, `diff`, `tracks`, and `meta`.
