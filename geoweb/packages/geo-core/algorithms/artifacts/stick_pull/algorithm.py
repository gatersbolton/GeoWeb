from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

import numpy as np

from algorithms.artifacts.stick_pull.config_schema import default_config, parse_config
from algorithms.core.data_models import AlgorithmRunReport, InputFrame, OutputFrame, RunContext
from algorithms.core.exceptions import AlgorithmExecutionError, InputValidationError
from algorithms.core.utils.io import build_output_filename, save_preview_png
from algorithms.core.utils.logging import hash_config


class StickPullArtifactRemoval:
    algo_id = "artifact.stick_pull.v1"
    version = "1.0.0"

    def validate_input(self, input_data: InputFrame, config: dict) -> None:
        parse_config(config)
        if input_data.data.size == 0:
            raise InputValidationError("Input data is empty.")
        if input_data.data.ndim not in (2, 3):
            raise InputValidationError("Stick-pull expects 2D(HW) or 3D(HWC/CHW) image data.")
        if not np.issubdtype(input_data.data.dtype, np.number):
            raise InputValidationError("Input data must be numeric.")

    def run(self, input_data: InputFrame, config: dict, context: RunContext) -> OutputFrame:
        parsed = parse_config(config)
        parsed_config = _model_dump(parsed)
        start = time.perf_counter()
        warnings: list[str] = []

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
                quality_metrics={"mean_abs_delta": 0.0, "edge_preservation": 1.0},
                artifact_detected={"stick_pull": 0.0},
                run_report=report,
                preview_assets=[],
            )

        try:
            work = _to_working_image(np.asarray(input_data.data, dtype=np.float32), input_data.data_layout)
            col_mask = valid_column_mask(
                work["gray_norm"],
                thr=parsed.advanced.valid_threshold,
                min_frac=parsed.advanced.min_valid_fraction,
            )
            speed = _load_speed_profile_csv(
                parsed.safe.speed_profile_csv,
                parsed.safe.speed_column,
                work["gray_norm"].shape[0],
            )
            if speed is None:
                speed = estimate_speed_from_image(
                    work["gray_norm"],
                    col_mask=col_mask,
                    smooth_window=parsed.advanced.smooth_window,
                )

            v_prepared = prepare_speed(
                speed,
                power=parsed.advanced.power,
                q_clip=(parsed.advanced.q_clip_low, parsed.advanced.q_clip_high),
            )
            depth_axis = depth_axis_from_speed(v_prepared)

            corrected_gray = warp_image_along_depth(work["gray_norm"], depth_axis)
            corrected_hwc = warp_rgb_along_depth(work["rgb_255"], depth_axis)
            result = _restore_layout_and_range(
                corrected_gray=corrected_gray,
                corrected_hwc=corrected_hwc,
                original=np.asarray(input_data.data, dtype=np.float32),
                data_layout=input_data.data_layout,
                value_range=input_data.value_range,
            )

            preview_assets = []
            if parsed.experimental.enable_preview_assets and context.output_dir:
                preview_name = build_output_filename(
                    context.job_id,
                    context.step_index,
                    self.algo_id,
                    parsed.experimental.preview_image_ext,
                )
                preview_path = Path(context.output_dir) / preview_name
                saved_preview = save_preview_png(preview_path, result)
                if saved_preview is not None:
                    preview_assets.append(str(saved_preview))

            if parsed.experimental.save_speed_profile_csv and context.output_dir:
                speed_csv = Path(context.output_dir) / build_output_filename(
                    context.job_id,
                    context.step_index,
                    self.algo_id + "_speed_profile",
                    "csv",
                )
                _save_speed_profile_csv(speed_csv, v_prepared)
                preview_assets.append(str(speed_csv))

            runtime_ms = (time.perf_counter() - start) * 1000
            metrics = _build_quality_metrics(
                original=np.asarray(input_data.data, dtype=np.float32),
                restored=result,
                original_gray=work["gray_norm"],
                corrected_gray=corrected_gray,
            )
            confidence = _estimate_artifact_confidence(v_prepared)

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
                artifact_detected={"stick_pull": confidence},
                run_report=report,
                preview_assets=preview_assets,
            )
        except Exception as exc:
            if parsed.safe.fallback_to_identity_on_error:
                runtime_ms = (time.perf_counter() - start) * 1000
                result = np.asarray(input_data.data, dtype=np.float32).copy()
                report = AlgorithmRunReport(
                    algo_id=self.algo_id,
                    algo_version=self.version,
                    config_hash=hash_config(parsed_config),
                    runtime_ms=runtime_ms,
                    warnings=[f"fallback to identity because of processing error: {exc}"],
                )
                return OutputFrame(
                    result=result,
                    quality_metrics={"mean_abs_delta": 0.0, "edge_preservation": 1.0},
                    artifact_detected={"stick_pull": 0.0},
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


def _normalize_01(data: np.ndarray) -> np.ndarray:
    data = np.asarray(data, dtype=np.float32)
    min_value = float(data.min())
    max_value = float(data.max())
    if max_value - min_value <= 1e-8:
        return np.zeros_like(data, dtype=np.float32)
    return ((data - min_value) / (max_value - min_value)).astype(np.float32)


def _to_hwc(data: np.ndarray, data_layout: str) -> np.ndarray:
    if data.ndim == 2:
        return np.repeat(data[..., None], 3, axis=2)

    layout = (data_layout or "HWC").upper()
    if layout == "CHW":
        if data.shape[0] not in (1, 3, 4):
            raise InputValidationError("CHW input must have 1/3/4 channels.")
        hwc = np.transpose(data[:3], (1, 2, 0))
        if hwc.shape[2] == 1:
            return np.repeat(hwc, 3, axis=2)
        return hwc

    if data.shape[2] not in (1, 3, 4):
        raise InputValidationError("HWC input must have 1/3/4 channels.")
    hwc = data[..., :3]
    if hwc.shape[2] == 1:
        return np.repeat(hwc, 3, axis=2)
    return hwc


def _to_working_image(data: np.ndarray, data_layout: str) -> dict[str, np.ndarray]:
    hwc = _to_hwc(data, data_layout).astype(np.float32)
    if float(hwc.max()) <= 1.5:
        rgb_255 = np.clip(hwc * 255.0, 0.0, 255.0)
    else:
        rgb_255 = np.clip(hwc, 0.0, 255.0)
    gray = (0.299 * rgb_255[..., 0] + 0.587 * rgb_255[..., 1] + 0.114 * rgb_255[..., 2]) / 255.0
    gray_norm = _normalize_01(gray)
    return {"gray_norm": gray_norm, "rgb_255": rgb_255}


def _restore_layout_and_range(
    *,
    corrected_gray: np.ndarray,
    corrected_hwc: np.ndarray,
    original: np.ndarray,
    data_layout: str,
    value_range: list[float],
) -> np.ndarray:
    if original.ndim == 2:
        lo, hi = _resolve_value_range(original, value_range)
        restored = corrected_gray * (hi - lo) + lo
        return restored.astype(np.float32)

    if float(original.max()) <= 1.5 and float(original.min()) >= 0:
        restored_hwc = corrected_hwc / 255.0
    else:
        restored_hwc = corrected_hwc
    if (data_layout or "HWC").upper() == "CHW":
        return np.transpose(restored_hwc, (2, 0, 1)).astype(np.float32)
    return restored_hwc.astype(np.float32)


def _resolve_value_range(original: np.ndarray, declared_range: list[float]) -> tuple[float, float]:
    if declared_range and len(declared_range) == 2:
        lo, hi = float(declared_range[0]), float(declared_range[1])
        if hi > lo:
            return lo, hi
    lo = float(np.min(original))
    hi = float(np.max(original))
    if hi <= lo:
        return lo, lo + 1.0
    return lo, hi


def valid_column_mask(gray: np.ndarray, thr: float = 0.02, min_frac: float = 0.75) -> np.ndarray:
    valid_px = gray > thr
    col_valid_ratio = valid_px.mean(axis=0)
    mask = col_valid_ratio >= min_frac
    if float(mask.mean()) < 0.05:
        mask[:] = True
    return mask


def moving_average_1d(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return values.astype(np.float32)
    if window % 2 == 0:
        window += 1
    pad = window // 2
    padded = np.pad(values, (pad, pad), mode="edge")
    kernel = np.ones(window, dtype=np.float32) / window
    return np.convolve(padded, kernel, mode="valid").astype(np.float32)


def estimate_speed_from_image(
    gray: np.ndarray,
    col_mask: np.ndarray | None = None,
    smooth_window: int = 31,
) -> np.ndarray:
    _, width = gray.shape
    if col_mask is None:
        col_mask = np.ones(width, dtype=bool)
    g = gray[:, col_mask]
    gy = np.abs(np.gradient(g, axis=0))
    energy = np.median(gy, axis=1)
    smooth = moving_average_1d(energy, smooth_window)
    smooth = smooth - np.min(smooth)
    smooth = smooth / (np.mean(smooth) + 1e-6)
    return np.clip(smooth, 1e-3, None).astype(np.float32)


def _load_speed_profile_csv(
    csv_path: str | None,
    speed_colname: str | None,
    target_height: int,
) -> np.ndarray | None:
    if not csv_path:
        return None
    path = Path(csv_path)
    if not path.exists():
        return None

    column = _read_speed_column(path, speed_colname)
    if column.size == 0:
        return None
    if column.size != target_height:
        old_axis = np.linspace(0.0, 1.0, column.size, dtype=np.float32)
        new_axis = np.linspace(0.0, 1.0, target_height, dtype=np.float32)
        column = np.interp(new_axis, old_axis, column).astype(np.float32)
    return column


def _read_speed_column(path: Path, speed_colname: str | None) -> np.ndarray:
    try:
        import pandas as pd  # type: ignore
    except Exception:
        pd = None

    if pd is not None:
        try:
            df = pd.read_csv(path)
            if speed_colname and speed_colname in df.columns:
                return df[speed_colname].to_numpy(dtype=np.float32)
            for name in [
                "v_norm",
                "v",
                "speed",
                "velocity",
                "tool_speed",
                "toolspeed",
                "v_raw",
            ]:
                if name in df.columns:
                    return df[name].to_numpy(dtype=np.float32)
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                return df[numeric_cols[-1]].to_numpy(dtype=np.float32)
        except Exception:
            pass

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
        if not rows:
            return np.array([], dtype=np.float32)
        if speed_colname and speed_colname in fieldnames:
            selected = speed_colname
        else:
            priority = {
                "v_norm",
                "v",
                "speed",
                "velocity",
                "tool_speed",
                "toolspeed",
                "v_raw",
            }
            selected = next((name for name in fieldnames if name in priority), fieldnames[-1])
        values = []
        for row in rows:
            raw = row.get(selected, "")
            try:
                values.append(float(raw))
            except Exception:
                values.append(np.nan)
    series = np.asarray(values, dtype=np.float32)
    valid = np.isfinite(series)
    if not valid.any():
        return np.array([], dtype=np.float32)
    if not valid.all():
        median = float(np.nanmedian(series))
        series = np.where(valid, series, median)
    return series


def prepare_speed(
    speed: np.ndarray,
    power: float = 1.6,
    q_clip: tuple[float, float] = (2.0, 98.0),
) -> np.ndarray:
    speed = np.asarray(speed, dtype=np.float32).reshape(-1)
    lo, hi = np.percentile(speed, q_clip)
    speed = np.clip(speed, lo, hi)
    speed = _normalize_01(speed)
    speed = 0.1 + 0.9 * speed
    speed = speed**power
    speed /= float(np.mean(speed) + 1e-6)
    return np.clip(speed, 1e-3, None).astype(np.float32)


def depth_axis_from_speed(speed: np.ndarray) -> np.ndarray:
    depth = np.cumsum(speed.astype(np.float32))
    depth = (depth - depth[0]) / (depth[-1] - depth[0] + 1e-6)
    return np.maximum.accumulate(depth).astype(np.float32)


def warp_image_along_depth(gray: np.ndarray, depth_axis: np.ndarray) -> np.ndarray:
    height, width = gray.shape
    target_depth = np.linspace(0.0, 1.0, height, dtype=np.float32)
    source_rows = np.arange(height, dtype=np.float32)
    remapped_rows = np.interp(target_depth, depth_axis, source_rows).astype(np.float32)

    output = np.empty_like(gray, dtype=np.float32)
    for x in range(width):
        output[:, x] = np.interp(remapped_rows, source_rows, gray[:, x]).astype(np.float32)
    return _normalize_01(output)


def warp_rgb_along_depth(rgb_255: np.ndarray, depth_axis: np.ndarray) -> np.ndarray:
    height, width, channels = rgb_255.shape
    target_depth = np.linspace(0.0, 1.0, height, dtype=np.float32)
    source_rows = np.arange(height, dtype=np.float32)
    remapped_rows = np.interp(target_depth, depth_axis, source_rows).astype(np.float32)

    output = np.empty((height, width, channels), dtype=np.float32)
    for c in range(channels):
        for x in range(width):
            output[:, x, c] = np.interp(remapped_rows, source_rows, rgb_255[:, x, c]).astype(
                np.float32
            )
    return np.clip(output, 0.0, 255.0).astype(np.float32)


def _build_quality_metrics(
    *,
    original: np.ndarray,
    restored: np.ndarray,
    original_gray: np.ndarray,
    corrected_gray: np.ndarray,
) -> dict[str, float]:
    mean_abs_delta = float(np.mean(np.abs(restored - original)))
    orig_edge = float(np.mean(np.abs(np.gradient(original_gray, axis=0))))
    corr_edge = float(np.mean(np.abs(np.gradient(corrected_gray, axis=0))))
    edge_preservation = corr_edge / (orig_edge + 1e-6)
    return {
        "mean_abs_delta": mean_abs_delta,
        "edge_preservation": float(edge_preservation),
    }


def _estimate_artifact_confidence(speed_prepared: np.ndarray) -> float:
    ratio = float(np.std(speed_prepared) / (np.mean(speed_prepared) + 1e-6))
    return float(np.clip(ratio, 0.0, 1.0))


def _save_speed_profile_csv(path: Path, speed_prepared: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    y = np.arange(speed_prepared.size, dtype=np.float32)
    data = np.column_stack([y, speed_prepared])
    header = "row_index,v_prepared"
    np.savetxt(path, data, delimiter=",", header=header, comments="", fmt="%.6f")
