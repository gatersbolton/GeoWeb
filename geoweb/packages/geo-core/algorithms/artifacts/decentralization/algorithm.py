from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from algorithms.artifacts.decentralization.config_schema import (
    DecentralizationAdvancedConfig,
    default_config,
    parse_config,
)
from algorithms.core.data_models import AlgorithmRunReport, InputFrame, OutputFrame, RunContext
from algorithms.core.exceptions import AlgorithmExecutionError, InputValidationError
from algorithms.core.utils.io import build_output_filename, save_preview_png
from algorithms.core.utils.logging import hash_config


class DecentralizationArtifactRemoval:
    algo_id = "artifact.decentralization.v1"
    version = "1.0.0"

    def validate_input(self, input_data: InputFrame, config: dict) -> None:
        parse_config(config)
        if input_data.data.size == 0:
            raise InputValidationError("Input data is empty.")
        if input_data.data.ndim not in (2, 3):
            raise InputValidationError("Decentralization expects 2D(HW) or 3D(HWC/CHW) data.")
        if not np.issubdtype(input_data.data.dtype, np.number):
            raise InputValidationError("Input data must be numeric.")

    def run(self, input_data: InputFrame, config: dict, context: RunContext) -> OutputFrame:
        parsed = parse_config(config)
        parsed_config = _model_dump(parsed)
        start = time.perf_counter()

        if not parsed.safe.enable:
            result = np.asarray(input_data.data, dtype=np.float32).copy()
            runtime_ms = (time.perf_counter() - start) * 1000
            report = AlgorithmRunReport(
                algo_id=self.algo_id,
                algo_version=self.version,
                config_hash=hash_config(parsed_config),
                runtime_ms=runtime_ms,
                warnings=["safe.enable=false -> identity output"],
            )
            return OutputFrame(
                result=result,
                quality_metrics={"mean_abs_delta": 0.0, "bias_before": 0.0, "bias_after": 0.0},
                artifact_detected={"decentralization": 0.0},
                run_report=report,
                preview_assets=[],
            )

        warnings: list[str] = []
        method = parsed.safe.method
        original = np.asarray(input_data.data, dtype=np.float32)
        try:
            corrected = _apply_decentralization(
                original,
                data_layout=input_data.data_layout,
                method=method,
                params=parsed.advanced,
            )
            corrected = _clip_to_value_range(corrected, input_data.value_range, original)

            metrics = _build_quality_metrics(original, corrected)
            confidence = float(np.clip(metrics["bias_before"], 0.0, 1.0))
            preview_assets = []
            if parsed.experimental.enable_preview_assets and context.output_dir:
                preview_name = build_output_filename(
                    context.job_id,
                    context.step_index,
                    self.algo_id,
                    parsed.experimental.preview_image_ext,
                )
                preview_path = Path(context.output_dir) / preview_name
                saved_preview = save_preview_png(preview_path, corrected)
                if saved_preview is not None:
                    preview_assets.append(str(saved_preview))

            runtime_ms = (time.perf_counter() - start) * 1000
            report = AlgorithmRunReport(
                algo_id=self.algo_id,
                algo_version=self.version,
                config_hash=hash_config(parsed_config),
                runtime_ms=runtime_ms,
                warnings=warnings,
            )
            return OutputFrame(
                result=corrected.astype(np.float32),
                quality_metrics=metrics,
                artifact_detected={"decentralization": confidence},
                run_report=report,
                preview_assets=preview_assets,
            )
        except Exception as exc:
            if parsed.safe.fallback_to_identity_on_error:
                runtime_ms = (time.perf_counter() - start) * 1000
                fallback = original.copy()
                report = AlgorithmRunReport(
                    algo_id=self.algo_id,
                    algo_version=self.version,
                    config_hash=hash_config(parsed_config),
                    runtime_ms=runtime_ms,
                    warnings=[f"fallback to identity because of processing error: {exc}"],
                )
                return OutputFrame(
                    result=fallback.astype(np.float32),
                    quality_metrics={"mean_abs_delta": 0.0, "bias_before": 0.0, "bias_after": 0.0},
                    artifact_detected={"decentralization": 0.0},
                    run_report=report,
                    preview_assets=[],
                )
            raise AlgorithmExecutionError(str(exc)) from exc

    def get_default_config(self) -> dict:
        return default_config()


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _apply_decentralization(
    data: np.ndarray,
    *,
    data_layout: str,
    method: str,
    params: DecentralizationAdvancedConfig,
) -> np.ndarray:
    if data.ndim == 2:
        return _apply_2d_method(data, method=method, params=params).astype(np.float32)

    layout = (data_layout or "HWC").upper()
    is_chw = layout == "CHW"
    work_hwc = np.transpose(data, (1, 2, 0)) if is_chw else data
    if work_hwc.ndim != 3:
        raise InputValidationError("3D input must be HWC or CHW.")

    channels = work_hwc.shape[2]
    corrected = work_hwc.astype(np.float32).copy()
    process_channels = channels if channels != 4 else 3
    for channel in range(process_channels):
        corrected[:, :, channel] = _apply_2d_method(
            work_hwc[:, :, channel].astype(np.float32),
            method=method,
            params=params,
        )
    if is_chw:
        return np.transpose(corrected, (2, 0, 1)).astype(np.float32)
    return corrected.astype(np.float32)


def _apply_2d_method(
    matrix: np.ndarray,
    *,
    method: str,
    params: DecentralizationAdvancedConfig,
) -> np.ndarray:
    method_key = method.lower()
    if method_key == "harmonic":
        corrected = _harmonic_background_removal(
            matrix,
            orders=params.harmonic_orders,
            smooth_window=params.harmonic_depth_smooth_window,
            preserve_row_mean=params.harmonic_preserve_row_mean,
            strength=params.harmonic_strength,
        )
    elif method_key == "azimuth_equalization":
        corrected = _azimuth_equalization(
            matrix,
            depth_window=params.equalization_depth_window,
            stat=params.equalization_stat,
            mode=params.equalization_mode,
            epsilon=params.equalization_epsilon,
            clip_gain=(params.equalization_clip_gain_min, params.equalization_clip_gain_max),
            strength=params.equalization_strength,
            preserve_row_mean=params.equalization_preserve_row_mean,
        )
    elif method_key == "agc":
        corrected = _agc(
            matrix,
            window=params.agc_window,
            axis=params.agc_axis,
            target_rms=params.agc_target_rms,
            epsilon=params.agc_epsilon,
            clip_gain=(params.agc_clip_gain_min, params.agc_clip_gain_max),
            strength=params.agc_strength,
            preserve_row_mean=params.agc_preserve_row_mean,
        )
    else:
        raise InputValidationError(f"Unsupported decentralization method: {method}")

    corrected = _column_debias(
        corrected,
        strength=params.column_debias_strength,
        stat=params.column_debias_stat,
        smooth_window=params.column_debias_smooth_window,
        preserve_row_mean=params.column_debias_preserve_row_mean,
    )
    return corrected


def _harmonic_background_removal(
    matrix: np.ndarray,
    *,
    orders: list[int],
    smooth_window: int,
    preserve_row_mean: bool,
    strength: float,
) -> np.ndarray:
    depth, azimuth = matrix.shape
    theta = 2 * np.pi * np.arange(azimuth, dtype=np.float32) / max(azimuth, 1)
    cos_basis = np.stack([np.cos(order * theta) for order in orders], axis=0).astype(np.float32)
    sin_basis = np.stack([np.sin(order * theta) for order in orders], axis=0).astype(np.float32)

    scale = 2.0 / max(azimuth, 1)
    a_coeff = scale * matrix @ cos_basis.T
    b_coeff = scale * matrix @ sin_basis.T
    a_coeff = _moving_average_depth(a_coeff, smooth_window)
    b_coeff = _moving_average_depth(b_coeff, smooth_window)

    background = a_coeff @ cos_basis + b_coeff @ sin_basis
    corrected = matrix - strength * background
    if preserve_row_mean:
        corrected = _preserve_row_mean(corrected, matrix)
    return corrected.astype(np.float32)


def _azimuth_equalization(
    matrix: np.ndarray,
    *,
    depth_window: int,
    stat: str,
    mode: str,
    epsilon: float,
    clip_gain: tuple[float, float],
    strength: float,
    preserve_row_mean: bool,
) -> np.ndarray:
    local_bg = _rolling_depth_stat(matrix, depth_window, stat=stat)
    if stat == "median":
        reference = np.median(local_bg, axis=1, keepdims=True)
    else:
        reference = np.mean(local_bg, axis=1, keepdims=True)

    if mode == "multiplicative":
        gain = reference / (local_bg + epsilon)
        gain = np.clip(gain, clip_gain[0], clip_gain[1])
        blend_gain = 1.0 + strength * (gain - 1.0)
        corrected = matrix * blend_gain
    else:
        corrected = matrix + strength * (reference - local_bg)
    if preserve_row_mean:
        corrected = _preserve_row_mean(corrected, matrix)
    return corrected.astype(np.float32)


def _agc(
    matrix: np.ndarray,
    *,
    window: int,
    axis: str,
    target_rms: float,
    epsilon: float,
    clip_gain: tuple[float, float],
    strength: float,
    preserve_row_mean: bool,
) -> np.ndarray:
    corrected = np.empty_like(matrix, dtype=np.float32)
    if axis == "depth":
        for col in range(matrix.shape[1]):
            corrected[:, col] = _agc_1d(
                matrix[:, col],
                window=window,
                target_rms=target_rms,
                epsilon=epsilon,
                clip_gain=clip_gain,
                strength=strength,
            )
    else:
        for row in range(matrix.shape[0]):
            corrected[row, :] = _agc_1d(
                matrix[row, :],
                window=window,
                target_rms=target_rms,
                epsilon=epsilon,
                clip_gain=clip_gain,
                strength=strength,
            )
    if preserve_row_mean:
        corrected = _preserve_row_mean(corrected, matrix)
    return corrected


def _column_debias(
    matrix: np.ndarray,
    *,
    strength: float,
    stat: str,
    smooth_window: int,
    preserve_row_mean: bool,
) -> np.ndarray:
    if strength <= 0:
        return matrix.astype(np.float32)

    if stat == "median":
        profile = np.median(matrix, axis=0).astype(np.float32)
        reference = float(np.median(profile))
    else:
        profile = np.mean(matrix, axis=0).astype(np.float32)
        reference = float(np.mean(profile))

    deviation = profile - reference
    if smooth_window > 1:
        deviation = _moving_average_1d(deviation, smooth_window)

    corrected = matrix - strength * deviation[None, :]
    if preserve_row_mean:
        corrected = _preserve_row_mean(corrected, matrix)
    return corrected.astype(np.float32)


def _agc_1d(
    vector: np.ndarray,
    *,
    window: int,
    target_rms: float,
    epsilon: float,
    clip_gain: tuple[float, float],
    strength: float,
) -> np.ndarray:
    energy = vector.astype(np.float32) ** 2
    mean_energy = _moving_average_1d(energy, window)
    rms = np.sqrt(mean_energy + epsilon)
    reference_rms = float(np.median(rms))
    target_level = max(target_rms * reference_rms, epsilon)
    gain = target_level / (rms + epsilon)
    gain = np.clip(gain, clip_gain[0], clip_gain[1]).astype(np.float32)
    blend_gain = 1.0 + strength * (gain - 1.0)
    return (vector * blend_gain).astype(np.float32)


def _rolling_depth_stat(matrix: np.ndarray, window: int, *, stat: str) -> np.ndarray:
    if window <= 1:
        return matrix.astype(np.float32)
    if window % 2 == 0:
        window += 1
    pad = window // 2
    padded = np.pad(matrix, ((pad, pad), (0, 0)), mode="edge")
    out = np.empty_like(matrix, dtype=np.float32)
    for idx in range(matrix.shape[0]):
        chunk = padded[idx : idx + window, :]
        if stat == "median":
            out[idx, :] = np.median(chunk, axis=0)
        else:
            out[idx, :] = np.mean(chunk, axis=0)
    return out


def _moving_average_depth(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return values.astype(np.float32)
    if window % 2 == 0:
        window += 1
    pad = window // 2
    padded = np.pad(values, ((pad, pad), (0, 0)), mode="edge")
    kernel = np.ones(window, dtype=np.float32) / window
    out = np.empty_like(values, dtype=np.float32)
    for idx in range(values.shape[1]):
        out[:, idx] = np.convolve(padded[:, idx], kernel, mode="valid")
    return out


def _moving_average_1d(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return values.astype(np.float32)
    if window % 2 == 0:
        window += 1
    pad = window // 2
    padded = np.pad(values, (pad, pad), mode="edge")
    kernel = np.ones(window, dtype=np.float32) / window
    return np.convolve(padded, kernel, mode="valid").astype(np.float32)


def _clip_to_value_range(data: np.ndarray, value_range: list[float], original: np.ndarray) -> np.ndarray:
    if value_range and len(value_range) == 2:
        low, high = float(value_range[0]), float(value_range[1])
        if high > low and not _looks_like_range_mismatch(low, high, original):
            return np.clip(data, low, high).astype(np.float32)
    orig_low = float(np.min(original))
    orig_high = float(np.max(original))
    if orig_high > orig_low:
        return np.clip(data, orig_low, orig_high).astype(np.float32)
    return data.astype(np.float32)


def _looks_like_range_mismatch(low: float, high: float, original: np.ndarray) -> bool:
    data_max = float(np.max(original))
    data_min = float(np.min(original))
    declared_span = high - low
    actual_span = data_max - data_min
    if declared_span <= 1.5 and actual_span > 2.0:
        return True
    return False


def _preserve_row_mean(corrected: np.ndarray, original: np.ndarray) -> np.ndarray:
    row_shift = original.mean(axis=1, keepdims=True) - corrected.mean(axis=1, keepdims=True)
    return corrected + row_shift


def _build_quality_metrics(original: np.ndarray, corrected: np.ndarray) -> dict[str, float]:
    mean_abs_delta = float(np.mean(np.abs(corrected - original)))
    bias_before = _azimuth_bias_score(original)
    bias_after = _azimuth_bias_score(corrected)
    bias_reduction = float((bias_before - bias_after) / (abs(bias_before) + 1e-6))
    return {
        "mean_abs_delta": mean_abs_delta,
        "bias_before": float(bias_before),
        "bias_after": float(bias_after),
        "bias_reduction": bias_reduction,
    }


def _azimuth_bias_score(data: np.ndarray) -> float:
    matrix = np.asarray(data, dtype=np.float32)
    if matrix.ndim == 3:
        matrix = np.mean(matrix, axis=2)
    background = np.median(matrix, axis=0)
    denom = float(np.mean(np.abs(matrix)) + 1e-6)
    return float(np.std(background) / denom)
