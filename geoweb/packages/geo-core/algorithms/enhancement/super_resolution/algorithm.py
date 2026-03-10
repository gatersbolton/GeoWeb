from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from algorithms.core.data_models import AlgorithmRunReport, InputFrame, OutputFrame, RunContext
from algorithms.core.exceptions import AlgorithmExecutionError, InputValidationError
from algorithms.core.utils.io import build_output_filename, save_preview_png
from algorithms.core.utils.logging import hash_config
from algorithms.enhancement.super_resolution.config_schema import default_config, parse_config
from algorithms.enhancement.super_resolution.realesrgan_backend import (
    get_realesrgan_runner,
    resolve_model_path,
)


class SuperResolutionEnhancement:
    algo_id = "enhancement.super_resolution.v1"
    version = "1.1.0"

    def validate_input(self, input_data: InputFrame, config: dict) -> None:
        parsed = parse_config(config)
        data = np.asarray(input_data.data)
        if data.size == 0:
            raise InputValidationError("Input data is empty.")
        if data.ndim not in (2, 3):
            raise InputValidationError("Super-resolution expects 2D(HW) or 3D(HWC/CHW) image data.")
        if not np.issubdtype(data.dtype, np.number):
            raise InputValidationError("Input data must be numeric.")

        layout = (input_data.data_layout or "HW").upper()
        if data.ndim == 3:
            if layout not in {"HWC", "CHW"}:
                raise InputValidationError("3D input must declare HWC or CHW layout.")
            channels = data.shape[0] if layout == "CHW" else data.shape[2]
            if channels not in (1, 3, 4):
                raise InputValidationError("Super-resolution supports 1/3/4-channel inputs only.")

        try:
            resolve_model_path(parsed.safe.model_name, parsed.advanced.model_path)
        except Exception as exc:
            raise InputValidationError(str(exc)) from exc

    def run(self, input_data: InputFrame, config: dict, context: RunContext) -> OutputFrame:
        parsed = parse_config(config)
        parsed_config = _model_dump(parsed)

        start = time.perf_counter()
        original = np.asarray(input_data.data, dtype=np.float32)

        if not parsed.safe.enable:
            runtime_ms = (time.perf_counter() - start) * 1000
            report = AlgorithmRunReport(
                algo_id=self.algo_id,
                algo_version=self.version,
                config_hash=hash_config(parsed_config),
                runtime_ms=runtime_ms,
                warnings=["safe.enable=false -> identity output"],
            )
            return OutputFrame(
                result=original.copy(),
                quality_metrics={
                    "mean_abs_delta": 0.0,
                    "sharpness_delta": 0.0,
                    "contrast_delta": 0.0,
                    "applied_outscale": float(parsed.advanced.outscale),
                },
                artifact_detected={},
                run_report=report,
                preview_assets=[],
            )

        warnings: list[str] = []
        try:
            prepared = _prepare_model_input(
                original,
                data_layout=input_data.data_layout,
                value_range=input_data.value_range,
            )
            model_path = resolve_model_path(parsed.safe.model_name, parsed.advanced.model_path)
            runner = get_realesrgan_runner(
                model_name=parsed.safe.model_name,
                model_path=str(model_path),
                tile=parsed.advanced.tile,
                tile_pad=parsed.advanced.tile_pad,
                pre_pad=parsed.advanced.pre_pad,
                prefer_device=parsed.advanced.prefer_device,
                gpu_id=parsed.advanced.gpu_id,
                use_fp32=parsed.advanced.use_fp32,
            )
            if runner.device_label == "cpu":
                warnings.append("running Real-ESRGAN on CPU; enable CUDA for faster inference")

            enhanced = runner.enhance(
                prepared["model_input"],
                outscale=float(parsed.advanced.outscale),
                alpha_upsampler=parsed.advanced.alpha_upsampler,
            )
            blended = _apply_detail_strength_blend(
                enhanced,
                base_input=prepared["model_input"],
                detail_strength=float(parsed.advanced.detail_strength),
            )
            result = _restore_result(
                blended,
                prepared=prepared,
                data_layout=input_data.data_layout,
                value_range=input_data.value_range,
            )
            metrics = _build_quality_metrics(
                original=original,
                restored=result,
                data_layout=input_data.data_layout,
                value_range=input_data.value_range,
                outscale=float(parsed.advanced.outscale),
                detail_strength=float(parsed.advanced.detail_strength),
            )

            preview_assets: list[str] = []
            if parsed.experimental.save_preview_assets and context.output_dir:
                preview_name = build_output_filename(
                    context.job_id,
                    context.step_index,
                    self.algo_id,
                    parsed.experimental.preview_image_ext,
                )
                preview_path = Path(context.output_dir) / preview_name
                preview_data = _to_preview_array(result, input_data.data_layout)
                saved_preview = save_preview_png(preview_path, preview_data)
                if saved_preview is not None:
                    preview_assets.append(str(saved_preview))
        except Exception as exc:
            if parsed.safe.fallback_to_identity_on_error:
                runtime_ms = (time.perf_counter() - start) * 1000
                report = AlgorithmRunReport(
                    algo_id=self.algo_id,
                    algo_version=self.version,
                    config_hash=hash_config(parsed_config),
                    runtime_ms=runtime_ms,
                    warnings=[f"fallback to identity because of processing error: {exc}"],
                )
                return OutputFrame(
                    result=original.copy(),
                    quality_metrics={
                        "mean_abs_delta": 0.0,
                        "sharpness_delta": 0.0,
                        "contrast_delta": 0.0,
                        "applied_outscale": float(parsed.advanced.outscale),
                    },
                    artifact_detected={},
                    run_report=report,
                    preview_assets=[],
                )
            raise AlgorithmExecutionError(str(exc)) from exc

        runtime_ms = (time.perf_counter() - start) * 1000
        report = AlgorithmRunReport(
            algo_id=self.algo_id,
            algo_version=self.version,
            config_hash=hash_config(parsed_config),
            runtime_ms=runtime_ms,
            warnings=warnings,
        )
        return OutputFrame(
            result=result,
            quality_metrics=metrics,
            artifact_detected={},
            run_report=report,
            preview_assets=preview_assets,
        )

    def get_default_config(self) -> dict:
        return default_config()


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _resolve_value_range(data: np.ndarray, declared_range: list[float]) -> tuple[float, float]:
    if declared_range and len(declared_range) == 2:
        lo, hi = float(declared_range[0]), float(declared_range[1])
        if hi > lo:
            return lo, hi
    lo = float(np.min(data))
    hi = float(np.max(data))
    if hi <= lo:
        return lo, lo + 1.0
    return lo, hi


def _to_hwc_or_hw(data: np.ndarray, data_layout: str) -> tuple[np.ndarray, int | None]:
    if data.ndim == 2:
        return data.astype(np.float32), None

    layout = (data_layout or "HWC").upper()
    if layout == "CHW":
        channels = data.shape[0]
        if channels not in (1, 3, 4):
            raise InputValidationError("CHW input must have 1/3/4 channels.")
        hwc = np.transpose(data, (1, 2, 0)).astype(np.float32)
    elif layout == "HWC":
        channels = data.shape[2]
        if channels not in (1, 3, 4):
            raise InputValidationError("HWC input must have 1/3/4 channels.")
        hwc = data.astype(np.float32)
    else:
        raise InputValidationError(f"Unsupported data_layout '{data_layout}'.")

    if channels == 1:
        return hwc[..., 0].astype(np.float32), 1
    return hwc, channels


def _prepare_model_input(
    data: np.ndarray,
    *,
    data_layout: str,
    value_range: list[float],
) -> dict[str, Any]:
    working, channel_count = _to_hwc_or_hw(data, data_layout)
    target_lo, target_hi = _resolve_value_range(data, value_range)
    value_span = max(target_hi - target_lo, 1e-6)

    model_max_range = 255.0 if target_hi <= 255.0 and target_lo >= 0.0 else 65535.0
    normalized = np.clip((working - target_lo) / value_span, 0.0, 1.0)
    scaled = np.round(normalized * model_max_range)
    if model_max_range > 255.0:
        model_input = scaled.astype(np.uint16)
    else:
        model_input = scaled.astype(np.uint8)

    if model_input.ndim == 3 and channel_count == 3:
        model_input = model_input[..., ::-1]
    elif model_input.ndim == 3 and channel_count == 4:
        model_input = model_input[..., [2, 1, 0, 3]]

    return {
        "channel_count": channel_count,
        "model_input": model_input,
        "model_max_range": model_max_range,
        "original_ndim": data.ndim,
        "target_lo": target_lo,
        "target_hi": target_hi,
    }


def _restore_result(
    output: np.ndarray,
    *,
    prepared: dict[str, Any],
    data_layout: str,
    value_range: list[float],
) -> np.ndarray:
    restored = np.asarray(output)
    channel_count = prepared["channel_count"]

    if restored.ndim == 3 and channel_count == 3:
        restored = restored[..., ::-1]
    elif restored.ndim == 3 and channel_count == 4:
        restored = restored[..., [2, 1, 0, 3]]

    target_lo, target_hi = prepared["target_lo"], prepared["target_hi"]
    value_span = max(target_hi - target_lo, 1e-6)
    restored = restored.astype(np.float32) / float(prepared["model_max_range"])
    restored = restored * value_span + target_lo

    if prepared["original_ndim"] == 2:
        return restored.astype(np.float32)

    layout = (data_layout or "HWC").upper()
    if channel_count == 1 and restored.ndim == 2:
        if layout == "CHW":
            return restored[None, ...].astype(np.float32)
        return restored[..., None].astype(np.float32)

    if layout == "CHW":
        return np.transpose(restored, (2, 0, 1)).astype(np.float32)
    return restored.astype(np.float32)


def _to_preview_array(data: np.ndarray, data_layout: str) -> np.ndarray:
    if data.ndim == 2:
        return data.astype(np.float32)
    layout = (data_layout or "HWC").upper()
    if layout == "CHW":
        preview = np.transpose(data, (1, 2, 0))
    else:
        preview = data
    if preview.shape[2] == 1:
        return preview[..., 0].astype(np.float32)
    if preview.shape[2] >= 3:
        return preview[..., :3].astype(np.float32)
    return preview.astype(np.float32)


def _to_gray01(data: np.ndarray, data_layout: str, value_range: list[float]) -> np.ndarray:
    preview = _to_preview_array(data, data_layout)
    lo, hi = _resolve_value_range(preview, value_range)
    normalized = np.clip((preview - lo) / max(hi - lo, 1e-6), 0.0, 1.0).astype(np.float32)
    if normalized.ndim == 2:
        return normalized
    return (
        0.299 * normalized[..., 0]
        + 0.587 * normalized[..., 1]
        + 0.114 * normalized[..., 2]
    ).astype(np.float32)


def _resize_gray(gray: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    if gray.shape == shape:
        return gray.astype(np.float32)
    resample = Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC
    image = Image.fromarray(np.clip(gray * 255.0, 0.0, 255.0).astype(np.uint8))
    image = image.resize((shape[1], shape[0]), resample=resample)
    return (np.asarray(image, dtype=np.float32) / 255.0).astype(np.float32)


def _resize_channel(channel: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    if channel.shape == shape:
        return channel
    resample = Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC
    image = Image.fromarray(channel)
    resized = image.resize((shape[1], shape[0]), resample=resample)
    return np.asarray(resized, dtype=channel.dtype)


def _resize_like(data: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    array = np.asarray(data)
    if array.ndim == 2:
        return _resize_channel(array, shape)
    if array.ndim != 3:
        raise AlgorithmExecutionError("Unsupported image shape for detail-strength blending.")
    resized_channels = [_resize_channel(array[..., index], shape) for index in range(array.shape[2])]
    return np.stack(resized_channels, axis=2).astype(array.dtype)


def _apply_detail_strength_blend(
    enhanced: np.ndarray,
    *,
    base_input: np.ndarray,
    detail_strength: float,
) -> np.ndarray:
    weight = float(np.clip(detail_strength, 0.0, 1.0))
    enhanced_array = np.asarray(enhanced)
    if weight >= 0.999:
        return enhanced_array

    target_shape = enhanced_array.shape[:2]
    reference = _resize_like(np.asarray(base_input), target_shape).astype(np.float32)
    blended = enhanced_array.astype(np.float32) * weight + reference * (1.0 - weight)

    if np.issubdtype(enhanced_array.dtype, np.integer):
        dtype_info = np.iinfo(enhanced_array.dtype)
        return np.clip(np.round(blended), dtype_info.min, dtype_info.max).astype(enhanced_array.dtype)
    return blended.astype(enhanced_array.dtype)


def _edge_energy(gray: np.ndarray) -> float:
    grad_y = np.abs(np.gradient(gray, axis=0))
    grad_x = np.abs(np.gradient(gray, axis=1))
    return float(np.mean(grad_y) + np.mean(grad_x))


def _build_quality_metrics(
    *,
    original: np.ndarray,
    restored: np.ndarray,
    data_layout: str,
    value_range: list[float],
    outscale: float,
    detail_strength: float,
) -> dict[str, float]:
    original_gray = _to_gray01(original, data_layout, value_range)
    restored_gray = _to_gray01(restored, data_layout, value_range)
    restored_resized = _resize_gray(restored_gray, original_gray.shape)

    mean_abs_delta = float(np.mean(np.abs(restored_resized - original_gray)))
    original_sharpness = _edge_energy(original_gray)
    restored_sharpness = _edge_energy(restored_gray)
    original_contrast = float(np.std(original_gray))
    restored_contrast = float(np.std(restored_gray))

    return {
        "mean_abs_delta": mean_abs_delta,
        "sharpness_delta": float(restored_sharpness - original_sharpness),
        "sharpness_gain": float(restored_sharpness / (original_sharpness + 1e-6)),
        "contrast_delta": float(restored_contrast - original_contrast),
        "contrast_gain": float(restored_contrast / (original_contrast + 1e-6)),
        "applied_outscale": float(outscale),
        "detail_strength": float(detail_strength),
        "output_height": float(restored_gray.shape[0]),
        "output_width": float(restored_gray.shape[1]),
    }
