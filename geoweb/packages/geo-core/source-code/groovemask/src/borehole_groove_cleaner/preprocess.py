from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter

from borehole_groove_cleaner.utils import ensure_odd, robust_zscore


def circular_pad_x(arr: np.ndarray, pad_x: int) -> np.ndarray:
    if pad_x <= 0:
        return np.asarray(arr)
    return np.pad(arr, ((0, 0), (pad_x, pad_x)), mode="wrap")


def unpad_x(arr: np.ndarray, pad_x: int) -> np.ndarray:
    if pad_x <= 0:
        return np.asarray(arr)
    return np.asarray(arr)[:, pad_x:-pad_x]


def unwrap_periodic_x(arr: np.ndarray, pad_x: int) -> np.ndarray:
    if pad_x <= 0:
        return np.asarray(arr)
    src = np.asarray(arr)
    core = src[:, pad_x:-pad_x].copy()
    edge = min(pad_x, core.shape[1])
    if edge <= 0:
        return core
    core[:, :edge] = src[:, -edge:]
    core[:, -edge:] = src[:, :edge]
    return core


def median_filter_x(arr: np.ndarray, ksize: int) -> np.ndarray:
    return median_filter(np.asarray(arr, dtype=np.float32), size=(1, ensure_odd(int(ksize))), mode="wrap")


def median_filter_1d(values: np.ndarray, ksize: int) -> np.ndarray:
    size = ensure_odd(int(ksize))
    return median_filter(np.asarray(values, dtype=np.float32), size=size, mode="wrap")


def compute_reference_and_residual(gray: np.ndarray, k_ref: int) -> tuple[np.ndarray, np.ndarray]:
    y_ref = median_filter_x(gray, k_ref)
    residual = np.asarray(gray, dtype=np.float32) - y_ref
    return y_ref.astype(np.float32), residual.astype(np.float32)


def normalize_gray(arr: np.ndarray) -> tuple[np.ndarray, tuple[float, float]]:
    src = np.asarray(arr, dtype=np.float32)
    mn = float(np.nanmin(src))
    mx = float(np.nanmax(src))
    if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
        return np.zeros_like(src, dtype=np.float32), (mn, mx)
    return ((src - mn) / (mx - mn)).astype(np.float32), (mn, mx)


def choose_polarity_scores(
    profile: np.ndarray,
    background: np.ndarray,
    polarity: str,
) -> list[tuple[str, np.ndarray, np.ndarray]]:
    profile = np.asarray(profile, dtype=np.float32)
    background = np.asarray(background, dtype=np.float32)
    dark_q = background - profile
    bright_q = profile - background
    if polarity == "dark":
        return [("dark", dark_q, robust_zscore(dark_q))]
    if polarity == "bright":
        return [("bright", bright_q, robust_zscore(bright_q))]
    return [
        ("dark", dark_q, robust_zscore(dark_q)),
        ("bright", bright_q, robust_zscore(bright_q)),
    ]
