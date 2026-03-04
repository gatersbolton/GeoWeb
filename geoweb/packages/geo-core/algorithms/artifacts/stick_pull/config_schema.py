from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

try:
    from pydantic import model_validator
except ImportError:  # pydantic v1
    model_validator = None


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class StickPullSafeConfig(BaseModel):
    enable: bool = True
    speed_profile_csv: str | None = None
    speed_column: str | None = None
    fallback_to_identity_on_error: bool = True


class StickPullAdvancedConfig(BaseModel):
    power: float = 1.6
    q_clip_low: float = 2.0
    q_clip_high: float = 98.0
    smooth_window: int = 31
    valid_threshold: float = 0.02
    min_valid_fraction: float = 0.75

    if model_validator is not None:
        @model_validator(mode="after")
        def validate_ranges(self) -> "StickPullAdvancedConfig":
            if self.power <= 0:
                raise ValueError("advanced.power must be > 0")
            if self.smooth_window < 1:
                raise ValueError("advanced.smooth_window must be >= 1")
            if self.q_clip_low >= self.q_clip_high:
                raise ValueError("advanced.q_clip_low must be < advanced.q_clip_high")
            if not 0 <= self.valid_threshold <= 1:
                raise ValueError("advanced.valid_threshold must be in [0, 1]")
            if not 0 <= self.min_valid_fraction <= 1:
                raise ValueError("advanced.min_valid_fraction must be in [0, 1]")
            return self
    else:  # pydantic v1 compatibility
        from pydantic import root_validator

        @root_validator
        def validate_ranges(cls, values: dict[str, Any]) -> dict[str, Any]:
            power = values.get("power", 1.6)
            smooth_window = values.get("smooth_window", 31)
            q_clip_low = values.get("q_clip_low", 2.0)
            q_clip_high = values.get("q_clip_high", 98.0)
            valid_threshold = values.get("valid_threshold", 0.02)
            min_valid_fraction = values.get("min_valid_fraction", 0.75)

            if power <= 0:
                raise ValueError("advanced.power must be > 0")
            if smooth_window < 1:
                raise ValueError("advanced.smooth_window must be >= 1")
            if q_clip_low >= q_clip_high:
                raise ValueError("advanced.q_clip_low must be < advanced.q_clip_high")
            if not 0 <= valid_threshold <= 1:
                raise ValueError("advanced.valid_threshold must be in [0, 1]")
            if not 0 <= min_valid_fraction <= 1:
                raise ValueError("advanced.min_valid_fraction must be in [0, 1]")
            return values


class StickPullExperimentalConfig(BaseModel):
    enable_preview_assets: bool = False
    preview_image_ext: str = "png"
    save_speed_profile_csv: bool = False


class StickPullConfig(BaseModel):
    safe: StickPullSafeConfig = Field(default_factory=StickPullSafeConfig)
    advanced: StickPullAdvancedConfig = Field(default_factory=StickPullAdvancedConfig)
    experimental: StickPullExperimentalConfig = Field(default_factory=StickPullExperimentalConfig)


def parse_config(raw: dict[str, Any] | None = None) -> StickPullConfig:
    payload = raw or default_config()
    if hasattr(StickPullConfig, "model_validate"):
        return StickPullConfig.model_validate(payload)
    return StickPullConfig.parse_obj(payload)


def default_config() -> dict[str, Any]:
    return _model_dump(StickPullConfig())
