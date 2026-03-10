from __future__ import annotations

from typing import Any

import numpy as np

from borehole_groove_cleaner.backends.fourier import run_fourier_soft_notch
from borehole_groove_cleaner.backends.variational import run_variational_decompose
from borehole_groove_cleaner.config import GrooveMaskConfig
from borehole_groove_cleaner.detect import detect_candidates
from borehole_groove_cleaner.io import auto_crop_bbox, crop_loaded_image, gray_from_image, load_image, restore_clean_image
from borehole_groove_cleaner.preprocess import circular_pad_x, compute_reference_and_residual, unpad_x
from borehole_groove_cleaner.qc import backend_summary, diff_heatmap, log_power_spectrum, overlay_mask
from borehole_groove_cleaner.repair import rowwise_pchip_fill, small_radius_blend
from borehole_groove_cleaner.tracking import build_mask_from_tracks, filter_tracks_to_central_region, link_candidates_into_tracks, serialize_tracks
from borehole_groove_cleaner.utils import ChannelArtifacts, GrooveMaskResult, normalize_to_unit, restore_from_unit


def _default_backend(gray_unit: np.ndarray, cfg: GrooveMaskConfig) -> ChannelArtifacts:
    gray_padded = circular_pad_x(gray_unit, cfg.pad_x if cfg.wrap_x else 0)
    _, residual = compute_reference_and_residual(gray_padded, cfg.k_ref)
    detection = detect_candidates(residual, cfg, gray=gray_padded)
    tracks = link_candidates_into_tracks(detection.candidates, cfg, gray_padded.shape[0])
    tracks = filter_tracks_to_central_region(tracks, gray_unit.shape[1], cfg.pad_x if cfg.wrap_x else 0)
    mask_padded = build_mask_from_tracks(gray_padded.shape, tracks, cfg)

    if cfg.mode == "detect-only":
        clean_padded = gray_padded.copy()
        repair_meta = {"pchip_rows": 0, "linear_rows": 0, "nearest_rows": 0}
    else:
        prefill, repair_stats = rowwise_pchip_fill(gray_padded, mask_padded, cfg)
        clean_padded = small_radius_blend(prefill, gray_padded, mask_padded, cfg)
        clean_padded[mask_padded == 0] = gray_padded[mask_padded == 0]
        repair_meta = repair_stats.as_dict()

    if cfg.wrap_x:
        clean = unpad_x(clean_padded, cfg.pad_x)
        mask = unpad_x(mask_padded, cfg.pad_x)
        edge = min(cfg.pad_x, clean.shape[1])
        if edge > 0:
            right_pad_mask = mask_padded[:, -edge:] > 0
            left_pad_mask = mask_padded[:, :edge] > 0
            clean[:, :edge][right_pad_mask] = clean_padded[:, -edge:][right_pad_mask]
            clean[:, -edge:][left_pad_mask] = clean_padded[:, :edge][left_pad_mask]
            mask[:, :edge] = np.maximum(mask[:, :edge], mask_padded[:, -edge:])
            mask[:, -edge:] = np.maximum(mask[:, -edge:], mask_padded[:, :edge])
        residual_raw = unpad_x(residual, cfg.pad_x)
        score_map = unpad_x(detection.score_map, cfg.pad_x) if detection.score_map is not None else np.zeros_like(clean)
    else:
        clean = clean_padded
        mask = mask_padded
        residual_raw = residual
        score_map = detection.score_map if detection.score_map is not None else np.zeros_like(clean)

    serialized_tracks = serialize_tracks(tracks, width=gray_unit.shape[1], pad_x=cfg.pad_x if cfg.wrap_x else 0)
    summary = backend_summary(gray_unit, clean, mask, cfg)
    debug_images = {
        "residual": np.clip(np.rint(np.abs(residual_raw) * 255.0), 0, 255).astype(np.uint8),
        "score_map": np.clip(np.rint(np.maximum(score_map, 0.0) / max(cfg.tau_sigma, 1.0) * 255.0), 0, 255).astype(np.uint8),
        "spectrum_before": log_power_spectrum(gray_unit),
        "spectrum_after": log_power_spectrum(clean),
    }
    debug_payload = {
        "config": cfg.as_dict(),
        "rejected_broad": detection.rejected_broad,
        "tracks_serialized": serialized_tracks,
        "backend_summary": summary,
        "repair_stats": repair_meta,
        "mask_fraction": float(np.mean(mask)),
    }
    meta = {
        "backend": cfg.backend,
        "experimental_backend": False,
        "track_count": len(tracks),
        "rejected_broad_count": len(detection.rejected_broad),
        **summary,
    }
    return ChannelArtifacts(
        raw=gray_unit,
        clean=clean,
        mask=(mask > 0).astype(np.uint8),
        tracks=tracks,
        overlay=overlay_mask(gray_unit, mask),
        diff=diff_heatmap(clean, gray_unit),
        debug_images=debug_images,
        debug_payload=debug_payload,
        meta=meta,
    )


def _experimental_backend(gray_unit: np.ndarray, cfg: GrooveMaskConfig) -> ChannelArtifacts:
    gray_padded = circular_pad_x(gray_unit, cfg.pad_x if cfg.wrap_x else 0)
    if cfg.backend == "fourier_soft_notch":
        clean_padded, backend_debug, meta = run_fourier_soft_notch(gray_padded, cfg)
    else:
        clean_padded, backend_debug, meta = run_variational_decompose(gray_padded, cfg)

    clean = unpad_x(clean_padded, cfg.pad_x) if cfg.wrap_x else clean_padded
    debug_images = {
        "spectrum_before": log_power_spectrum(gray_unit),
        "spectrum_after": log_power_spectrum(clean),
    }
    for name, image in backend_debug.items():
        debug_images[name] = np.asarray(image)

    summary = backend_summary(gray_unit, clean, np.zeros_like(clean, dtype=np.uint8), cfg)
    debug_payload = {
        "config": cfg.as_dict(),
        "tracks_serialized": [],
        "backend_summary": summary,
    }
    clean = np.clip(clean, 0.0, 1.0)
    return ChannelArtifacts(
        raw=gray_unit,
        clean=clean.astype(np.float32),
        mask=np.zeros_like(gray_unit, dtype=np.uint8),
        tracks=[],
        overlay=overlay_mask(gray_unit, np.zeros_like(gray_unit, dtype=np.uint8)),
        diff=diff_heatmap(clean, gray_unit),
        debug_images=debug_images,
        debug_payload=debug_payload,
        meta={**summary, **meta},
    )


def run_channel_pipeline(channel: np.ndarray, cfg: GrooveMaskConfig) -> ChannelArtifacts:
    raw = np.asarray(channel)
    unit, src_range = normalize_to_unit(raw)
    if cfg.backend == "groovemask_inpaint":
        artifacts = _default_backend(unit, cfg)
    else:
        artifacts = _experimental_backend(unit, cfg)

    clean_restored = restore_from_unit(artifacts.clean, src_range, raw.dtype)
    return ChannelArtifacts(
        raw=raw.copy(),
        clean=clean_restored,
        mask=artifacts.mask,
        tracks=artifacts.tracks,
        overlay=artifacts.overlay,
        diff=artifacts.diff,
        debug_images=artifacts.debug_images,
        debug_payload=artifacts.debug_payload,
        meta={**artifacts.meta, "source_range": src_range},
    )


def clean_grooves(image_or_array: str | np.ndarray, cfg: GrooveMaskConfig | None = None) -> GrooveMaskResult:
    cfg = cfg or GrooveMaskConfig()
    loaded = load_image(image_or_array)
    roi = cfg.roi if cfg.roi is not None else (auto_crop_bbox(loaded.source) if cfg.auto_crop and loaded.is_color and loaded.source_path is not None else loaded.roi)
    cropped = crop_loaded_image(loaded, roi)
    raw_gray = gray_from_image(cropped.source)

    if cropped.is_color:
        channel_artifacts = _default_backend(raw_gray, cfg) if cfg.backend == "groovemask_inpaint" else _experimental_backend(raw_gray, cfg)
        clean_image = restore_clean_image(cropped, channel_artifacts.clean, raw_gray)
    else:
        channel_artifacts = run_channel_pipeline(cropped.source.astype(np.float32), cfg)
        clean_image = channel_artifacts.clean

    result_meta = {
        "backend": cfg.backend,
        "mode": cfg.mode,
        "crop_applied": cropped.crop_applied,
        "source_path": str(cropped.source_path) if cropped.source_path is not None else None,
        **channel_artifacts.meta,
    }

    return GrooveMaskResult(
        raw_image=cropped.source,
        clean_image=clean_image,
        mask=channel_artifacts.mask,
        tracks=channel_artifacts.tracks,
        overlay=overlay_mask(cropped.source, channel_artifacts.mask),
        diff=channel_artifacts.diff,
        debug_images=channel_artifacts.debug_images,
        debug_payload=channel_artifacts.debug_payload,
        meta=result_meta,
    )
