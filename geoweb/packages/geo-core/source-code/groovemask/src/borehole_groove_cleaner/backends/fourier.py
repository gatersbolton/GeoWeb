from __future__ import annotations

import numpy as np

from borehole_groove_cleaner.config import GrooveMaskConfig
from borehole_groove_cleaner.preprocess import compute_reference_and_residual


def run_fourier_soft_notch(gray: np.ndarray, cfg: GrooveMaskConfig) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float | bool]]:
    gray = np.asarray(gray, dtype=np.float32)
    y_ref, residual = compute_reference_and_residual(gray, cfg.k_ref)
    freq = np.fft.fftshift(np.fft.fft2(residual))

    height, width = residual.shape
    ky = np.fft.fftshift(np.fft.fftfreq(height))
    kx = np.fft.fftshift(np.fft.fftfreq(width))
    kx_grid, ky_grid = np.meshgrid(kx, ky)

    within_wedge = (np.abs(ky_grid) <= cfg.ky_max) & (np.abs(kx_grid) >= cfg.kx_min)
    ky_weight = np.clip(1.0 - np.abs(ky_grid) / max(cfg.ky_max, 1.0e-6), 0.0, 1.0)
    kx_weight = 1.0 - np.exp(-cfg.notch_softness * np.maximum(np.abs(kx_grid) - cfg.kx_min, 0.0))
    attenuation = 1.0 - cfg.notch_strength * ky_weight * kx_weight
    attenuation = np.where(within_wedge, attenuation, 1.0).astype(np.float32)

    freq_filtered = freq * attenuation
    residual_clean = np.real(np.fft.ifft2(np.fft.ifftshift(freq_filtered))).astype(np.float32)
    clean = np.clip(y_ref + residual_clean, 0.0, 1.0).astype(np.float32)

    debug = {
        "residual_before": residual,
        "residual_after": residual_clean,
        "notch_mask": 1.0 - attenuation,
    }
    meta = {
        "experimental_backend": True,
        "backend": "fourier_soft_notch",
        "notch_strength": float(cfg.notch_strength),
    }
    return clean, debug, meta
