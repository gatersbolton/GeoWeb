from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from algorithms.artifacts.groovemask.backend import load_backend
from algorithms.artifacts.groovemask.config_schema import (
    GrooveMaskAdvancedConfig,
    GrooveMaskSafeConfig,
    default_config,
    parse_config,
)
from algorithms.core.data_models import AlgorithmRunReport, InputFrame, OutputFrame, RunContext
from algorithms.core.exceptions import AlgorithmExecutionError, InputValidationError
from algorithms.core.utils.logging import hash_config


class GrooveMaskArtifactRemoval:
    algo_id = "artifact.groovemask.v1"
    version = "1.0.0"

    def validate_input(self, input_data: InputFrame, config: dict) -> None:
        parse_config(config)
        if input_data.data.size == 0:
            raise InputValidationError("Input data is empty.")
        if input_data.data.ndim not in (2, 3):
            raise InputValidationError("GrooveMask expects 2D(HW) or 3D(HWC/CHW) image data.")
        if not np.issubdtype(input_data.data.dtype, np.number):
            raise InputValidationError("Input data must be numeric.")
        if input_data.data.ndim == 3:
            layout = (input_data.data_layout or "HWC").upper()
            channels = int(input_data.data.shape[0] if layout == "CHW" else input_data.data.shape[2])
            if channels not in (1, 3, 4):
                raise InputValidationError("GrooveMask only supports 1/3/4-channel images.")

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
                quality_metrics=_identity_metrics(),
                artifact_detected={"groovemask": 0.0},
                run_report=report,
                preview_assets=[],
            )

        warnings: list[str] = []
        try:
            prepared = _prepare_input_frame(
                data=original,
                data_layout=input_data.data_layout,
                value_range=input_data.value_range,
            )
            result = _run_backend(
                prepared=prepared,
                safe_cfg=parsed.safe,
                advanced_cfg=parsed.advanced,
            )
            restored = _restore_output(result.clean_image, prepared, original, input_data.value_range)
            metrics = _build_quality_metrics(original, restored, result.meta)
            confidence = _estimate_confidence(result.meta)
            preview_assets = _collect_preview_assets(result=result, parsed_config=parsed, context=context)
            if parsed.safe.mode == "detect-only":
                warnings.append("safe.mode=detect-only -> output image is not inpainted.")
            if parsed.safe.backend != "groovemask_inpaint":
                warnings.append(f"experimental backend in use: {parsed.safe.backend}")

            runtime_ms = (time.perf_counter() - start) * 1000
            report = AlgorithmRunReport(
                algo_id=self.algo_id,
                algo_version=self.version,
                config_hash=hash_config(parsed_config),
                runtime_ms=runtime_ms,
                warnings=warnings,
            )
            return OutputFrame(
                result=restored.astype(np.float32),
                quality_metrics=metrics,
                artifact_detected={"groovemask": confidence},
                run_report=report,
                preview_assets=preview_assets,
            )
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
                    quality_metrics=_identity_metrics(),
                    artifact_detected={"groovemask": 0.0},
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


class _PreparedInput:
    def __init__(
        self,
        *,
        source: np.ndarray,
        is_color: bool,
        is_chw: bool,
        single_channel_3d: bool,
        scale_from_unit: bool,
    ) -> None:
        self.source = source
        self.is_color = is_color
        self.is_chw = is_chw
        self.single_channel_3d = single_channel_3d
        self.scale_from_unit = scale_from_unit


def _prepare_input_frame(
    *,
    data: np.ndarray,
    data_layout: str,
    value_range: list[float],
) -> _PreparedInput:
    if data.ndim == 2:
        return _PreparedInput(
            source=np.asarray(data, dtype=np.float32),
            is_color=False,
            is_chw=False,
            single_channel_3d=False,
            scale_from_unit=False,
        )

    layout = (data_layout or "HWC").upper()
    is_chw = layout == "CHW"
    hwc = np.transpose(data, (1, 2, 0)) if is_chw else np.asarray(data, dtype=np.float32)
    channels = int(hwc.shape[2])
    if channels == 1:
        return _PreparedInput(
            source=np.asarray(hwc[:, :, 0], dtype=np.float32),
            is_color=False,
            is_chw=is_chw,
            single_channel_3d=True,
            scale_from_unit=False,
        )

    scale_from_unit = _looks_like_unit_range(data, value_range)
    source = np.clip(np.rint(hwc * 255.0 if scale_from_unit else hwc), 0.0, 255.0).astype(np.uint8)
    return _PreparedInput(
        source=source,
        is_color=True,
        is_chw=is_chw,
        single_channel_3d=False,
        scale_from_unit=scale_from_unit,
    )


def _looks_like_unit_range(data: np.ndarray, value_range: list[float]) -> bool:
    if value_range and len(value_range) == 2:
        lo, hi = float(value_range[0]), float(value_range[1])
        if 0.0 <= lo <= 1.0 and 0.0 < hi <= 1.5:
            return True
    return 0.0 <= float(np.nanmin(data)) and float(np.nanmax(data)) <= 1.5


def _run_backend(
    *,
    prepared: _PreparedInput,
    safe_cfg: GrooveMaskSafeConfig,
    advanced_cfg: GrooveMaskAdvancedConfig,
):
    backend = load_backend()
    GrooveMaskConfig = backend["GrooveMaskConfig"]
    clean_grooves = backend["clean_grooves"]
    auto_crop_bbox = backend["auto_crop_bbox"]

    cfg = GrooveMaskConfig(
        mode=safe_cfg.mode,
        backend=safe_cfg.backend,
        polarity=safe_cfg.polarity,
        roi=tuple(safe_cfg.roi) if safe_cfg.roi is not None else None,
        auto_crop=False,
        wrap_x=safe_cfg.wrap_x,
        k_ref=advanced_cfg.k_ref,
        k_bg=advanced_cfg.k_bg,
        win_h=advanced_cfg.win_h,
        stride=advanced_cfg.stride,
        tau_sigma=advanced_cfg.tau_sigma,
        w_min=advanced_cfg.w_min,
        w_max=advanced_cfg.w_max,
        persist_min=advanced_cfg.persist_min,
        min_span_frac=advanced_cfg.min_span_frac,
        max_drift_per_window=advanced_cfg.max_drift_per_window,
        dilate_x=advanced_cfg.dilate_x,
        dilate_y=advanced_cfg.dilate_y,
        interp_context=advanced_cfg.interp_context,
        inpaint_radius=advanced_cfg.inpaint_radius,
        max_track_width_mad=advanced_cfg.max_track_width_mad,
        min_track_iou=advanced_cfg.min_track_iou,
        notch_strength=advanced_cfg.notch_strength,
        ky_max=advanced_cfg.ky_max,
        kx_min=advanced_cfg.kx_min,
        notch_softness=advanced_cfg.notch_softness,
        variational_iters=advanced_cfg.variational_iters,
        variational_rho=advanced_cfg.variational_rho,
        variational_lambda_u=advanced_cfg.variational_lambda_u,
        variational_lambda_sy=advanced_cfg.variational_lambda_sy,
        variational_lambda_sg=advanced_cfg.variational_lambda_sg,
        variational_lambda_sx=advanced_cfg.variational_lambda_sx,
        random_seed=advanced_cfg.random_seed,
    )
    if safe_cfg.auto_crop and cfg.roi is None:
        cfg = replace(cfg, roi=auto_crop_bbox(prepared.source))
    return clean_grooves(prepared.source, cfg)


def _restore_output(
    clean_image: np.ndarray,
    prepared: _PreparedInput,
    original: np.ndarray,
    value_range: list[float],
) -> np.ndarray:
    clean = np.asarray(clean_image, dtype=np.float32)
    if not prepared.is_color:
        restored = _clip_to_value_range(clean, value_range, original)
        if prepared.single_channel_3d:
            restored = restored[:, :, None]
            if prepared.is_chw:
                restored = np.transpose(restored, (2, 0, 1))
        return restored.astype(np.float32)

    restored = clean / 255.0 if prepared.scale_from_unit else clean
    if prepared.is_chw:
        restored = np.transpose(restored, (2, 0, 1))
    return restored.astype(np.float32)


def _clip_to_value_range(data: np.ndarray, value_range: list[float], original: np.ndarray) -> np.ndarray:
    if value_range and len(value_range) == 2:
        lo, hi = float(value_range[0]), float(value_range[1])
        if hi > lo:
            return np.clip(data, lo, hi).astype(np.float32)
    orig_min = float(np.nanmin(original))
    orig_max = float(np.nanmax(original))
    if orig_max > orig_min:
        return np.clip(data, orig_min, orig_max).astype(np.float32)
    return data.astype(np.float32)


def _build_quality_metrics(original: np.ndarray, restored: np.ndarray, meta: dict[str, Any]) -> dict[str, float]:
    column_before = float(meta.get("column_anomaly_before", 0.0))
    column_after = float(meta.get("column_anomaly_after", 0.0))
    stripe_before = float(meta.get("stripe_spectral_energy_before", 0.0))
    stripe_after = float(meta.get("stripe_spectral_energy_after", 0.0))
    return {
        "mean_abs_delta": float(np.mean(np.abs(restored - original))),
        "mask_fraction": float(meta.get("mask_fraction", 0.0)),
        "track_count": float(meta.get("track_count", 0.0)),
        "column_anomaly_before": column_before,
        "column_anomaly_after": column_after,
        "column_anomaly_reduction": float(column_before - column_after),
        "stripe_spectral_energy_before": stripe_before,
        "stripe_spectral_energy_after": stripe_after,
        "stripe_spectral_energy_reduction": float(stripe_before - stripe_after),
    }


def _estimate_confidence(meta: dict[str, Any]) -> float:
    mask_fraction = float(meta.get("mask_fraction", 0.0))
    track_count = float(meta.get("track_count", 0.0))
    column_before = float(meta.get("column_anomaly_before", 0.0))
    column_after = float(meta.get("column_anomaly_after", 0.0))
    stripe_before = float(meta.get("stripe_spectral_energy_before", 0.0))
    stripe_after = float(meta.get("stripe_spectral_energy_after", 0.0))

    column_signal = 0.0 if abs(column_before) <= 1.0e-6 else max(
        0.0,
        min(1.0, (column_before - column_after) / abs(column_before)),
    )
    stripe_signal = 0.0 if abs(stripe_before) <= 1.0e-6 else max(
        0.0,
        min(1.0, (stripe_before - stripe_after) / abs(stripe_before)),
    )
    confidence = max(
        min(1.0, mask_fraction * 8.0),
        min(1.0, track_count / 2.0),
        0.5 * (column_signal + stripe_signal),
    )
    return float(np.clip(confidence, 0.0, 1.0))


def _collect_preview_assets(*, result, parsed_config, context: RunContext) -> list[str]:
    if not parsed_config.experimental.enable_preview_assets or not context.output_dir:
        return []

    backend = load_backend()
    save_result_bundle = backend["save_result_bundle"]
    bundle_dir = (
        Path(context.output_dir)
        / f"job_{context.job_id}_step_{context.step_index}_{GrooveMaskArtifactRemoval.algo_id}_assets"
    )
    paths = save_result_bundle(result, bundle_dir)
    preview_assets: list[str] = []
    if parsed_config.experimental.save_auxiliary_assets:
        for key in ("clean", "mask", "overlay", "diff", "tracks", "meta"):
            path = paths.get(key)
            if path:
                preview_assets.append(str(path))
    if parsed_config.experimental.save_debug_assets and paths.get("debug_dir"):
        preview_assets.extend(
            str(path)
            for path in sorted(Path(paths["debug_dir"]).rglob("*"))
            if path.is_file()
        )
    return preview_assets


def _identity_metrics() -> dict[str, float]:
    return {
        "mean_abs_delta": 0.0,
        "mask_fraction": 0.0,
        "track_count": 0.0,
        "column_anomaly_before": 0.0,
        "column_anomaly_after": 0.0,
        "column_anomaly_reduction": 0.0,
        "stripe_spectral_energy_before": 0.0,
        "stripe_spectral_energy_after": 0.0,
        "stripe_spectral_energy_reduction": 0.0,
    }
