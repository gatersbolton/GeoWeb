from __future__ import annotations

from copy import deepcopy
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

from algorithms.enhancement.super_resolution.realesrgan_backend import SUPPORTED_MODEL_NAMES


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class SuperResolutionSafeConfig(BaseModel):
    enable: bool = True
    model_name: str = "RealESRGAN_x4plus"
    fallback_to_identity_on_error: bool = False

    @classmethod
    def _validate_model_name(cls, value: str) -> str:
        model_name = str(value).strip()
        if model_name not in SUPPORTED_MODEL_NAMES:
            supported = ", ".join(SUPPORTED_MODEL_NAMES)
            raise ValueError(f"Unsupported model_name '{model_name}'. Supported: {supported}.")
        return model_name

    if hasattr(BaseModel, "model_validate"):
        from pydantic import field_validator

        _model_name_validator = field_validator("model_name")(_validate_model_name)
    else:
        from pydantic import validator

        _model_name_validator = validator("model_name", allow_reuse=True)(_validate_model_name)


class SuperResolutionAdvancedConfig(BaseModel):
    outscale: float = Field(default=1.0, ge=1.0, le=8.0)
    detail_strength: float = Field(default=0.72, ge=0.0, le=1.0)
    tile: int = Field(default=0, ge=0)
    tile_pad: int = Field(default=10, ge=0, le=128)
    pre_pad: int = Field(default=0, ge=0, le=128)
    alpha_upsampler: Literal["realesrgan", "bicubic"] = "realesrgan"
    prefer_device: Literal["auto", "cpu", "cuda"] = "auto"
    gpu_id: int | None = Field(default=None, ge=0)
    use_fp32: bool = False
    model_path: str | None = None


class SuperResolutionExperimentalConfig(BaseModel):
    save_preview_assets: bool = False
    preview_image_ext: Literal["png", "jpg"] = "png"


class SuperResolutionConfig(BaseModel):
    safe: SuperResolutionSafeConfig = Field(default_factory=SuperResolutionSafeConfig)
    advanced: SuperResolutionAdvancedConfig = Field(default_factory=SuperResolutionAdvancedConfig)
    experimental: SuperResolutionExperimentalConfig = Field(
        default_factory=SuperResolutionExperimentalConfig
    )


def _normalize_legacy_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    payload = deepcopy(raw or default_config())
    advanced = payload.setdefault("advanced", {})
    experimental = payload.setdefault("experimental", {})

    if "upscale_ratio" in advanced and "outscale" not in advanced:
        advanced["outscale"] = advanced.pop("upscale_ratio")
    if experimental.pop("use_tile_mode", False) and "tile" not in advanced:
        advanced["tile"] = 256

    return payload


def parse_config(raw: dict[str, Any] | None = None) -> SuperResolutionConfig:
    payload = _normalize_legacy_payload(raw)
    if hasattr(SuperResolutionConfig, "model_validate"):
        return SuperResolutionConfig.model_validate(payload)
    return SuperResolutionConfig.parse_obj(payload)


def default_config() -> dict[str, Any]:
    return _model_dump(SuperResolutionConfig())
