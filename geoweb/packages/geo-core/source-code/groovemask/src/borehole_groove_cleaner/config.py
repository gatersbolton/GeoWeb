from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from borehole_groove_cleaner.utils import Rect


VALID_BACKENDS = {"groovemask_inpaint", "fourier_soft_notch", "variational_decompose"}
VALID_MODES = {"detect-only", "review", "clean", "batch"}
VALID_POLARITIES = {"dark", "bright", "auto"}


@dataclass(slots=True)
class GrooveMaskConfig:
    mode: str = "clean"
    backend: str = "groovemask_inpaint"
    polarity: str = "dark"
    roi: Rect | None = None
    auto_crop: bool = True
    wrap_x: bool = True
    k_ref: int = 21
    k_bg: int = 41
    win_h: int | None = 128
    stride: int | None = 64
    tau_sigma: float = 2.5
    w_min: int = 2
    w_max: int = 10
    persist_min: float = 0.70
    min_span_frac: float = 0.15
    max_drift_per_window: float = 2.0
    dilate_x: int = 2
    dilate_y: int = 0
    interp_context: int = 12
    interp_kind: str = "pchip"
    blend_method: str = "telea"
    inpaint_radius: int = 2
    tau_row_factor: float = 0.8
    max_track_width_mad: float = 1.5
    min_track_iou: float = 0.3
    notch_strength: float = 0.85
    ky_max: float = 0.035
    kx_min: float = 0.08
    notch_softness: float = 10.0
    variational_iters: int = 30
    variational_rho: float = 1.0
    variational_lambda_u: float = 0.08
    variational_lambda_sy: float = 0.04
    variational_lambda_sg: float = 0.10
    variational_lambda_sx: float = 0.02
    random_seed: int = 42

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode: {self.mode}")
        if self.backend not in VALID_BACKENDS:
            raise ValueError(f"Unsupported backend: {self.backend}")
        if self.polarity not in VALID_POLARITIES:
            raise ValueError(f"Unsupported polarity: {self.polarity}")
        if self.mode == "review":
            self.mode = "detect-only"
        if self.backend != "groovemask_inpaint" and self.mode == "detect-only":
            raise ValueError("Experimental backends only support clean or batch modes.")
        if self.w_min < 1 or self.w_max < self.w_min:
            raise ValueError("w_min/w_max are inconsistent.")
        if self.persist_min <= 0 or self.persist_min > 1:
            raise ValueError("persist_min must be in (0, 1].")
        if self.dilate_x < 0 or self.dilate_y < 0:
            raise ValueError("dilation must be non-negative.")
        if self.interp_context < 2:
            raise ValueError("interp_context must be >= 2.")
        if self.variational_iters < 1:
            raise ValueError("variational_iters must be >= 1.")

    @property
    def pad_x(self) -> int:
        return int(max(self.k_bg // 2, self.interp_context + self.w_max + self.dilate_x + 2))

    def resolved_win_h(self, height: int) -> int:
        if self.win_h is None:
            return max(96, round(0.12 * height))
        return max(16, min(height, int(self.win_h)))

    def resolved_stride(self, height: int) -> int:
        if self.stride is None:
            return max(1, self.resolved_win_h(height) // 2)
        return max(1, int(self.stride))

    def resolved_w_max(self, width: int) -> int:
        return int(min(self.w_max, max(self.w_min, round(0.08 * width))))

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pad_x"] = self.pad_x
        return data


def parse_roi(value: Any) -> Rect | None:
    if value is None:
        return None
    if isinstance(value, str):
        tokens = value.replace(",", " ").split()
        if len(tokens) != 4:
            raise ValueError("ROI string must contain four integers: x0 x1 y0 y1")
        return tuple(int(token) for token in tokens)  # type: ignore[return-value]
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return tuple(int(token) for token in value)  # type: ignore[return-value]
    raise ValueError("ROI must be a four-value tuple/list/string.")


def load_config_file(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("YAML config must decode to a mapping.")
    return data


def merge_config(base: GrooveMaskConfig, overrides: dict[str, Any]) -> GrooveMaskConfig:
    payload = base.as_dict()
    payload.update({key: value for key, value in overrides.items() if value is not None})
    payload.pop("pad_x", None)
    if "roi" in payload:
        payload["roi"] = parse_roi(payload["roi"])
    return GrooveMaskConfig(**payload)


def build_config(*, config_path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> GrooveMaskConfig:
    cfg = GrooveMaskConfig()
    yaml_data = load_config_file(config_path)
    cfg = merge_config(cfg, yaml_data)
    if overrides:
        cfg = merge_config(cfg, overrides)
    return cfg


def with_mode(cfg: GrooveMaskConfig, mode: str) -> GrooveMaskConfig:
    return replace(cfg, mode=mode)
