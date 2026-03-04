from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class SuperResolutionSafeConfig(BaseModel):
    enable: bool = True


class SuperResolutionAdvancedConfig(BaseModel):
    upscale_ratio: float = 1.0


class SuperResolutionExperimentalConfig(BaseModel):
    use_tile_mode: bool = False


class SuperResolutionConfig(BaseModel):
    safe: SuperResolutionSafeConfig = Field(default_factory=SuperResolutionSafeConfig)
    advanced: SuperResolutionAdvancedConfig = Field(default_factory=SuperResolutionAdvancedConfig)
    experimental: SuperResolutionExperimentalConfig = Field(
        default_factory=SuperResolutionExperimentalConfig
    )


def parse_config(raw: dict[str, Any] | None = None) -> SuperResolutionConfig:
    payload = raw or default_config()
    if hasattr(SuperResolutionConfig, "model_validate"):
        return SuperResolutionConfig.model_validate(payload)
    return SuperResolutionConfig.parse_obj(payload)


def default_config() -> dict[str, Any]:
    return _model_dump(SuperResolutionConfig())

