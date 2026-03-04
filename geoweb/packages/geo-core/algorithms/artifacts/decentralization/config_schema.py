from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

try:
    from pydantic import model_validator
except ImportError:  # pydantic v1
    model_validator = None


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class DecentralizationSafeConfig(BaseModel):
    enable: bool = True
    method: Literal["harmonic", "azimuth_equalization", "agc"] = "harmonic"
    fallback_to_identity_on_error: bool = True


class DecentralizationAdvancedConfig(BaseModel):
    harmonic_orders: list[int] = Field(default_factory=lambda: [1, 2, 3, 4])
    harmonic_depth_smooth_window: int = 15
    harmonic_preserve_row_mean: bool = True
    harmonic_strength: float = 1.0

    equalization_depth_window: int = 121
    equalization_stat: Literal["median", "mean"] = "median"
    equalization_mode: Literal["multiplicative", "additive"] = "multiplicative"
    equalization_epsilon: float = 1e-6
    equalization_clip_gain_min: float = 0.4
    equalization_clip_gain_max: float = 2.2
    equalization_strength: float = 1.0
    equalization_preserve_row_mean: bool = True

    agc_window: int = 41
    agc_axis: Literal["depth", "azimuth"] = "azimuth"
    agc_target_rms: float = 1.0
    agc_epsilon: float = 1e-6
    agc_clip_gain_min: float = 0.4
    agc_clip_gain_max: float = 2.2
    agc_strength: float = 1.0
    agc_preserve_row_mean: bool = True

    column_debias_strength: float = 0.8
    column_debias_stat: Literal["median", "mean"] = "median"
    column_debias_smooth_window: int = 1
    column_debias_preserve_row_mean: bool = True

    if model_validator is not None:
        @model_validator(mode="after")
        def validate_ranges(self) -> "DecentralizationAdvancedConfig":
            if not self.harmonic_orders:
                raise ValueError("advanced.harmonic_orders must not be empty")
            if any(order < 1 for order in self.harmonic_orders):
                raise ValueError("advanced.harmonic_orders values must be >= 1")
            if self.harmonic_depth_smooth_window < 1:
                raise ValueError("advanced.harmonic_depth_smooth_window must be >= 1")
            if not 0 <= self.harmonic_strength <= 1:
                raise ValueError("advanced.harmonic_strength must be in [0, 1]")
            if self.equalization_depth_window < 1:
                raise ValueError("advanced.equalization_depth_window must be >= 1")
            if self.equalization_epsilon <= 0:
                raise ValueError("advanced.equalization_epsilon must be > 0")
            if self.equalization_clip_gain_min <= 0:
                raise ValueError("advanced.equalization_clip_gain_min must be > 0")
            if self.equalization_clip_gain_min >= self.equalization_clip_gain_max:
                raise ValueError(
                    "advanced.equalization_clip_gain_min must be < "
                    "advanced.equalization_clip_gain_max"
                )
            if not 0 <= self.equalization_strength <= 1:
                raise ValueError("advanced.equalization_strength must be in [0, 1]")
            if self.agc_window < 1:
                raise ValueError("advanced.agc_window must be >= 1")
            if self.agc_target_rms <= 0:
                raise ValueError("advanced.agc_target_rms must be > 0")
            if self.agc_epsilon <= 0:
                raise ValueError("advanced.agc_epsilon must be > 0")
            if self.agc_clip_gain_min <= 0:
                raise ValueError("advanced.agc_clip_gain_min must be > 0")
            if self.agc_clip_gain_min >= self.agc_clip_gain_max:
                raise ValueError("advanced.agc_clip_gain_min must be < advanced.agc_clip_gain_max")
            if not 0 <= self.agc_strength <= 1:
                raise ValueError("advanced.agc_strength must be in [0, 1]")
            if not 0 <= self.column_debias_strength <= 1:
                raise ValueError("advanced.column_debias_strength must be in [0, 1]")
            if self.column_debias_smooth_window < 1:
                raise ValueError("advanced.column_debias_smooth_window must be >= 1")
            return self
    else:  # pydantic v1 compatibility
        from pydantic import root_validator

        @root_validator
        def validate_ranges(cls, values: dict[str, Any]) -> dict[str, Any]:
            harmonic_orders = values.get("harmonic_orders", [1, 2])
            harmonic_depth_smooth_window = values.get("harmonic_depth_smooth_window", 15)
            harmonic_strength = values.get("harmonic_strength", 1.0)
            equalization_depth_window = values.get("equalization_depth_window", 121)
            equalization_epsilon = values.get("equalization_epsilon", 1e-6)
            equalization_clip_gain_min = values.get("equalization_clip_gain_min", 0.4)
            equalization_clip_gain_max = values.get("equalization_clip_gain_max", 2.2)
            equalization_strength = values.get("equalization_strength", 1.0)
            agc_window = values.get("agc_window", 41)
            agc_target_rms = values.get("agc_target_rms", 1.0)
            agc_epsilon = values.get("agc_epsilon", 1e-6)
            agc_clip_gain_min = values.get("agc_clip_gain_min", 0.4)
            agc_clip_gain_max = values.get("agc_clip_gain_max", 2.2)
            agc_strength = values.get("agc_strength", 1.0)
            column_debias_strength = values.get("column_debias_strength", 0.8)
            column_debias_smooth_window = values.get("column_debias_smooth_window", 1)

            if not harmonic_orders:
                raise ValueError("advanced.harmonic_orders must not be empty")
            if any(order < 1 for order in harmonic_orders):
                raise ValueError("advanced.harmonic_orders values must be >= 1")
            if harmonic_depth_smooth_window < 1:
                raise ValueError("advanced.harmonic_depth_smooth_window must be >= 1")
            if not 0 <= harmonic_strength <= 1:
                raise ValueError("advanced.harmonic_strength must be in [0, 1]")
            if equalization_depth_window < 1:
                raise ValueError("advanced.equalization_depth_window must be >= 1")
            if equalization_epsilon <= 0:
                raise ValueError("advanced.equalization_epsilon must be > 0")
            if equalization_clip_gain_min <= 0:
                raise ValueError("advanced.equalization_clip_gain_min must be > 0")
            if equalization_clip_gain_min >= equalization_clip_gain_max:
                raise ValueError(
                    "advanced.equalization_clip_gain_min must be < "
                    "advanced.equalization_clip_gain_max"
                )
            if not 0 <= equalization_strength <= 1:
                raise ValueError("advanced.equalization_strength must be in [0, 1]")
            if agc_window < 1:
                raise ValueError("advanced.agc_window must be >= 1")
            if agc_target_rms <= 0:
                raise ValueError("advanced.agc_target_rms must be > 0")
            if agc_epsilon <= 0:
                raise ValueError("advanced.agc_epsilon must be > 0")
            if agc_clip_gain_min <= 0:
                raise ValueError("advanced.agc_clip_gain_min must be > 0")
            if agc_clip_gain_min >= agc_clip_gain_max:
                raise ValueError("advanced.agc_clip_gain_min must be < advanced.agc_clip_gain_max")
            if not 0 <= agc_strength <= 1:
                raise ValueError("advanced.agc_strength must be in [0, 1]")
            if not 0 <= column_debias_strength <= 1:
                raise ValueError("advanced.column_debias_strength must be in [0, 1]")
            if column_debias_smooth_window < 1:
                raise ValueError("advanced.column_debias_smooth_window must be >= 1")
            return values


class DecentralizationExperimentalConfig(BaseModel):
    enable_preview_assets: bool = False
    preview_image_ext: str = "png"


class DecentralizationConfig(BaseModel):
    safe: DecentralizationSafeConfig = Field(default_factory=DecentralizationSafeConfig)
    advanced: DecentralizationAdvancedConfig = Field(default_factory=DecentralizationAdvancedConfig)
    experimental: DecentralizationExperimentalConfig = Field(
        default_factory=DecentralizationExperimentalConfig
    )


def parse_config(raw: dict[str, Any] | None = None) -> DecentralizationConfig:
    payload = raw or default_config()
    if hasattr(DecentralizationConfig, "model_validate"):
        return DecentralizationConfig.model_validate(payload)
    return DecentralizationConfig.parse_obj(payload)


def default_config() -> dict[str, Any]:
    return _model_dump(DecentralizationConfig())
