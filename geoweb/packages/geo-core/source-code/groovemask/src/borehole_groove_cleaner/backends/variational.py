from __future__ import annotations

import numpy as np

from borehole_groove_cleaner.config import GrooveMaskConfig


def _grad_x(arr: np.ndarray) -> np.ndarray:
    return np.roll(arr, -1, axis=1) - arr


def _grad_y(arr: np.ndarray) -> np.ndarray:
    return np.roll(arr, -1, axis=0) - arr


def _div(px: np.ndarray, py: np.ndarray) -> np.ndarray:
    return (px - np.roll(px, 1, axis=1)) + (py - np.roll(py, 1, axis=0))


def _soft_threshold(values: np.ndarray, thresh: float) -> np.ndarray:
    return np.sign(values) * np.maximum(np.abs(values) - thresh, 0.0)


def _vector_soft_threshold(px: np.ndarray, py: np.ndarray, thresh: float) -> tuple[np.ndarray, np.ndarray]:
    mag = np.sqrt(px * px + py * py)
    scale = np.maximum(0.0, 1.0 - thresh / np.maximum(mag, 1.0e-6))
    return px * scale, py * scale


def _column_group_shrink(values: np.ndarray, thresh: float) -> np.ndarray:
    norms = np.linalg.norm(values, axis=0)
    scale = np.maximum(0.0, 1.0 - thresh / np.maximum(norms, 1.0e-6))
    return values * scale[None, :]


def run_variational_decompose(gray: np.ndarray, cfg: GrooveMaskConfig) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float | bool]]:
    gray = np.asarray(gray, dtype=np.float32)
    height, width = gray.shape
    rho = float(cfg.variational_rho)

    ky = 2.0 * np.pi * np.fft.fftfreq(height)
    kx = 2.0 * np.pi * np.fft.fftfreq(width)
    eig_x = np.exp(-1j * kx) - 1.0
    eig_y = np.exp(-1j * ky) - 1.0
    lap = (np.abs(eig_y)[:, None] ** 2) + (np.abs(eig_x)[None, :] ** 2)
    denom_u = 1.0 + rho * lap
    denom_s = 1.0 + rho * (lap + 1.0)

    u = gray.copy()
    s = np.zeros_like(gray)
    px = np.zeros_like(gray)
    py = np.zeros_like(gray)
    ax = np.zeros_like(gray)
    ay = np.zeros_like(gray)
    c = np.zeros_like(gray)
    bx = np.zeros_like(gray)
    by = np.zeros_like(gray)
    ux = np.zeros_like(gray)
    uy = np.zeros_like(gray)
    sx = np.zeros_like(gray)
    sy = np.zeros_like(gray)
    cs = np.zeros_like(gray)

    for _ in range(cfg.variational_iters):
        rhs_u = gray - s + rho * _div(px - bx, py - by)
        u = np.real(np.fft.ifft2(np.fft.fft2(rhs_u) / denom_u)).astype(np.float32)

        rhs_s = gray - u + rho * (_div(ax - sx, ay - sy) + (c - cs))
        s = np.real(np.fft.ifft2(np.fft.fft2(rhs_s) / denom_s)).astype(np.float32)

        gux = _grad_x(u)
        guy = _grad_y(u)
        px, py = _vector_soft_threshold(gux + bx, guy + by, cfg.variational_lambda_u / rho)

        gsx = _grad_x(s)
        gsy = _grad_y(s)
        ax = _soft_threshold(gsx + sx, cfg.variational_lambda_sx / rho)
        ay = _soft_threshold(gsy + sy, cfg.variational_lambda_sy / rho)
        c = _column_group_shrink(s + cs, cfg.variational_lambda_sg / rho)

        bx = bx + gux - px
        by = by + guy - py
        sx = sx + gsx - ax
        sy = sy + gsy - ay
        cs = cs + s - c

    clean = np.clip(u, 0.0, 1.0).astype(np.float32)
    stripe = gray - clean
    debug = {
        "stripe_component": stripe,
        "clean_component": clean,
        "group_component": c,
    }
    meta = {
        "experimental_backend": True,
        "backend": "variational_decompose",
        "iterations": int(cfg.variational_iters),
    }
    return clean, debug, meta
