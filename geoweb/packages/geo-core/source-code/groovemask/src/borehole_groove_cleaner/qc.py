from __future__ import annotations

from typing import Any

import numpy as np
from matplotlib import colormaps
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from borehole_groove_cleaner.config import GrooveMaskConfig
from borehole_groove_cleaner.preprocess import compute_reference_and_residual


def _to_rgb(arr: np.ndarray) -> np.ndarray:
    src = np.asarray(arr)
    if src.ndim == 2:
        norm = normalize_image(src)
        return np.stack([norm, norm, norm], axis=-1)
    if src.ndim == 3 and src.shape[2] >= 3:
        return src[..., :3].astype(np.uint8)
    raise ValueError("Unsupported array shape for RGB conversion.")


def normalize_image(arr: np.ndarray) -> np.ndarray:
    src = np.asarray(arr, dtype=np.float32)
    mn = float(np.nanmin(src))
    mx = float(np.nanmax(src))
    if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
        return np.zeros_like(src, dtype=np.uint8)
    norm = (src - mn) / (mx - mn)
    return np.clip(np.rint(norm * 255.0), 0, 255).astype(np.uint8)


def diff_heatmap(clean: np.ndarray, raw: np.ndarray) -> np.ndarray:
    delta = np.asarray(clean, dtype=np.float32) - np.asarray(raw, dtype=np.float32)
    scale = np.max(np.abs(delta))
    if scale <= 0:
        scale = 1.0
    norm = np.clip(delta / scale * 0.5 + 0.5, 0.0, 1.0)
    cmap = colormaps["coolwarm"]
    rgba = cmap(norm)
    return np.clip(np.rint(rgba[..., :3] * 255.0), 0, 255).astype(np.uint8)


def overlay_mask(image: np.ndarray, mask: np.ndarray, color: tuple[int, int, int] = (255, 64, 64)) -> np.ndarray:
    rgb = _to_rgb(image).astype(np.float32)
    overlay = rgb.copy()
    alpha = (np.asarray(mask, dtype=np.float32) > 0)[..., None] * 0.45
    tint = np.asarray(color, dtype=np.float32)[None, None, :]
    overlay = overlay * (1.0 - alpha) + tint * alpha
    return np.clip(np.rint(overlay), 0, 255).astype(np.uint8)


def log_power_spectrum(arr: np.ndarray) -> np.ndarray:
    freq = np.fft.fftshift(np.fft.fft2(np.asarray(arr, dtype=np.float32)))
    power = np.log1p(np.abs(freq))
    return normalize_image(power)


def spectral_strip_energy(arr: np.ndarray, cfg: GrooveMaskConfig) -> float:
    freq = np.fft.fftshift(np.fft.fft2(np.asarray(arr, dtype=np.float32)))
    power = np.abs(freq) ** 2
    height, width = arr.shape
    ky = np.fft.fftshift(np.fft.fftfreq(height))
    kx = np.fft.fftshift(np.fft.fftfreq(width))
    kx_grid, ky_grid = np.meshgrid(kx, ky)
    mask = (np.abs(ky_grid) <= cfg.ky_max) & (np.abs(kx_grid) >= cfg.kx_min)
    return float(power[mask].sum())


def column_anomaly_score(arr: np.ndarray, cfg: GrooveMaskConfig) -> float:
    _, residual = compute_reference_and_residual(np.asarray(arr, dtype=np.float32), cfg.k_ref)
    return float(np.mean(np.abs(np.median(residual, axis=0))))


def synth_metrics(
    clean_gt: np.ndarray,
    artifact: np.ndarray,
    restored: np.ndarray,
    mask_gt: np.ndarray,
    mask_pred: np.ndarray,
    cfg: GrooveMaskConfig,
) -> dict[str, float]:
    gt = np.asarray(clean_gt, dtype=np.float32)
    art = np.asarray(artifact, dtype=np.float32)
    restored_arr = np.asarray(restored, dtype=np.float32)
    gt_mask = np.asarray(mask_gt, dtype=bool)
    pred_mask = np.asarray(mask_pred, dtype=bool)

    inter = np.logical_and(gt_mask, pred_mask).sum()
    union = np.logical_or(gt_mask, pred_mask).sum()
    outside = ~gt_mask
    outside_ssim = 1.0
    if outside.any():
        outside_ssim = structural_similarity(gt * outside, restored_arr * outside, data_range=1.0)

    return {
        "mask_iou": float(inter / union) if union > 0 else 1.0,
        "psnr": float(peak_signal_noise_ratio(gt, restored_arr, data_range=1.0)),
        "ssim": float(structural_similarity(gt, restored_arr, data_range=1.0)),
        "outside_mask_ssim": float(outside_ssim),
        "column_anomaly_reduction": float(column_anomaly_score(art, cfg) - column_anomaly_score(restored_arr, cfg)),
        "stripe_spectral_energy_reduction": float(spectral_strip_energy(art, cfg) - spectral_strip_energy(restored_arr, cfg)),
    }


def backend_summary(raw_gray: np.ndarray, clean_gray: np.ndarray, mask: np.ndarray, cfg: GrooveMaskConfig) -> dict[str, Any]:
    return {
        "mask_fraction": float(np.mean(np.asarray(mask, dtype=np.float32))),
        "column_anomaly_before": column_anomaly_score(raw_gray, cfg),
        "column_anomaly_after": column_anomaly_score(clean_gray, cfg),
        "stripe_spectral_energy_before": spectral_strip_energy(raw_gray, cfg),
        "stripe_spectral_energy_after": spectral_strip_energy(clean_gray, cfg),
    }
