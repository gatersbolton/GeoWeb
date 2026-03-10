from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

try:
    from pydantic import field_validator, model_validator
except ImportError:  # pydantic v1
    field_validator = None
    model_validator = None


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class GrooveMaskSafeConfig(BaseModel):
    enable: bool = True
    mode: Literal["clean", "detect-only"] = "clean"
    backend: Literal["groovemask_inpaint", "fourier_soft_notch", "variational_decompose"] = (
        "groovemask_inpaint"
    )
    polarity: Literal["dark", "bright", "auto"] = "dark"
    auto_crop: bool = True
    wrap_x: bool = True
    roi: list[int] | None = None
    fallback_to_identity_on_error: bool = True

    if field_validator is not None:

        @field_validator("roi")
        @classmethod
        def validate_roi(cls, value: list[int] | None) -> list[int] | None:
            if value is None:
                return None
            if len(value) != 4:
                raise ValueError("safe.roi must contain exactly four integers.")
            return [int(item) for item in value]

    else:
        from pydantic import validator

        @validator("roi")
        def validate_roi(cls, value: list[int] | None) -> list[int] | None:
            if value is None:
                return None
            if len(value) != 4:
                raise ValueError("safe.roi must contain exactly four integers.")
            return [int(item) for item in value]


class GrooveMaskAdvancedConfig(BaseModel):
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
    inpaint_radius: int = 2
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

    if model_validator is not None:

        @model_validator(mode="after")
        def validate_ranges(self) -> "GrooveMaskAdvancedConfig":
            if self.k_ref < 3 or self.k_bg < 3:
                raise ValueError("advanced.k_ref and advanced.k_bg must be >= 3")
            if self.k_ref > self.k_bg:
                raise ValueError("advanced.k_ref must be <= advanced.k_bg")
            if self.win_h is not None and self.win_h < 16:
                raise ValueError("advanced.win_h must be >= 16 when provided")
            if self.stride is not None and self.stride < 1:
                raise ValueError("advanced.stride must be >= 1 when provided")
            if self.tau_sigma <= 0:
                raise ValueError("advanced.tau_sigma must be > 0")
            if self.w_min < 1 or self.w_max < self.w_min:
                raise ValueError("advanced.w_min/w_max are inconsistent")
            if not 0 < self.persist_min <= 1:
                raise ValueError("advanced.persist_min must be in (0, 1]")
            if not 0 < self.min_span_frac <= 1:
                raise ValueError("advanced.min_span_frac must be in (0, 1]")
            if self.max_drift_per_window < 0:
                raise ValueError("advanced.max_drift_per_window must be >= 0")
            if self.dilate_x < 0 or self.dilate_y < 0:
                raise ValueError("advanced.dilate_x/dilate_y must be >= 0")
            if self.interp_context < 2:
                raise ValueError("advanced.interp_context must be >= 2")
            if self.inpaint_radius < 1:
                raise ValueError("advanced.inpaint_radius must be >= 1")
            if self.max_track_width_mad < 0:
                raise ValueError("advanced.max_track_width_mad must be >= 0")
            if not 0 <= self.min_track_iou <= 1:
                raise ValueError("advanced.min_track_iou must be in [0, 1]")
            if not 0 <= self.notch_strength <= 1:
                raise ValueError("advanced.notch_strength must be in [0, 1]")
            if self.ky_max <= 0 or self.kx_min <= 0:
                raise ValueError("advanced.ky_max and advanced.kx_min must be > 0")
            if self.notch_softness <= 0:
                raise ValueError("advanced.notch_softness must be > 0")
            if self.variational_iters < 1:
                raise ValueError("advanced.variational_iters must be >= 1")
            if self.variational_rho <= 0:
                raise ValueError("advanced.variational_rho must be > 0")
            for name in (
                "variational_lambda_u",
                "variational_lambda_sy",
                "variational_lambda_sg",
                "variational_lambda_sx",
            ):
                if float(getattr(self, name)) <= 0:
                    raise ValueError(f"advanced.{name} must be > 0")
            return self

    else:
        from pydantic import root_validator

        @root_validator
        def validate_ranges(cls, values: dict[str, Any]) -> dict[str, Any]:
            k_ref = values.get("k_ref", 21)
            k_bg = values.get("k_bg", 41)
            win_h = values.get("win_h", 128)
            stride = values.get("stride", 64)
            tau_sigma = values.get("tau_sigma", 2.5)
            w_min = values.get("w_min", 2)
            w_max = values.get("w_max", 10)
            persist_min = values.get("persist_min", 0.70)
            min_span_frac = values.get("min_span_frac", 0.15)
            max_drift_per_window = values.get("max_drift_per_window", 2.0)
            dilate_x = values.get("dilate_x", 2)
            dilate_y = values.get("dilate_y", 0)
            interp_context = values.get("interp_context", 12)
            inpaint_radius = values.get("inpaint_radius", 2)
            max_track_width_mad = values.get("max_track_width_mad", 1.5)
            min_track_iou = values.get("min_track_iou", 0.3)
            notch_strength = values.get("notch_strength", 0.85)
            ky_max = values.get("ky_max", 0.035)
            kx_min = values.get("kx_min", 0.08)
            notch_softness = values.get("notch_softness", 10.0)
            variational_iters = values.get("variational_iters", 30)
            variational_rho = values.get("variational_rho", 1.0)

            if k_ref < 3 or k_bg < 3:
                raise ValueError("advanced.k_ref and advanced.k_bg must be >= 3")
            if k_ref > k_bg:
                raise ValueError("advanced.k_ref must be <= advanced.k_bg")
            if win_h is not None and win_h < 16:
                raise ValueError("advanced.win_h must be >= 16 when provided")
            if stride is not None and stride < 1:
                raise ValueError("advanced.stride must be >= 1 when provided")
            if tau_sigma <= 0:
                raise ValueError("advanced.tau_sigma must be > 0")
            if w_min < 1 or w_max < w_min:
                raise ValueError("advanced.w_min/w_max are inconsistent")
            if not 0 < persist_min <= 1:
                raise ValueError("advanced.persist_min must be in (0, 1]")
            if not 0 < min_span_frac <= 1:
                raise ValueError("advanced.min_span_frac must be in (0, 1]")
            if max_drift_per_window < 0:
                raise ValueError("advanced.max_drift_per_window must be >= 0")
            if dilate_x < 0 or dilate_y < 0:
                raise ValueError("advanced.dilate_x/dilate_y must be >= 0")
            if interp_context < 2:
                raise ValueError("advanced.interp_context must be >= 2")
            if inpaint_radius < 1:
                raise ValueError("advanced.inpaint_radius must be >= 1")
            if max_track_width_mad < 0:
                raise ValueError("advanced.max_track_width_mad must be >= 0")
            if not 0 <= min_track_iou <= 1:
                raise ValueError("advanced.min_track_iou must be in [0, 1]")
            if not 0 <= notch_strength <= 1:
                raise ValueError("advanced.notch_strength must be in [0, 1]")
            if ky_max <= 0 or kx_min <= 0:
                raise ValueError("advanced.ky_max and advanced.kx_min must be > 0")
            if notch_softness <= 0:
                raise ValueError("advanced.notch_softness must be > 0")
            if variational_iters < 1:
                raise ValueError("advanced.variational_iters must be >= 1")
            if variational_rho <= 0:
                raise ValueError("advanced.variational_rho must be > 0")
            for name in (
                "variational_lambda_u",
                "variational_lambda_sy",
                "variational_lambda_sg",
                "variational_lambda_sx",
            ):
                if float(values.get(name, 1.0)) <= 0:
                    raise ValueError(f"advanced.{name} must be > 0")
            return values


class GrooveMaskExperimentalConfig(BaseModel):
    enable_preview_assets: bool = False
    save_auxiliary_assets: bool = True
    save_debug_assets: bool = False


class GrooveMaskConfigModel(BaseModel):
    safe: GrooveMaskSafeConfig = Field(default_factory=GrooveMaskSafeConfig)
    advanced: GrooveMaskAdvancedConfig = Field(default_factory=GrooveMaskAdvancedConfig)
    experimental: GrooveMaskExperimentalConfig = Field(default_factory=GrooveMaskExperimentalConfig)


def parse_config(raw: dict[str, Any] | None = None) -> GrooveMaskConfigModel:
    payload = raw or default_config()
    if hasattr(GrooveMaskConfigModel, "model_validate"):
        return GrooveMaskConfigModel.model_validate(payload)
    return GrooveMaskConfigModel.parse_obj(payload)


def default_config() -> dict[str, Any]:
    return _model_dump(GrooveMaskConfigModel())
