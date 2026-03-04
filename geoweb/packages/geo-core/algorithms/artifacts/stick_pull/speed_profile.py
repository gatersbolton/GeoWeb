from __future__ import annotations

from pathlib import Path

import numpy as np

from algorithms.artifacts.stick_pull.algorithm import (
    estimate_speed_from_image,
    prepare_speed,
    valid_column_mask,
)


def estimate_prepared_speed_from_gray(
    gray_01: np.ndarray,
    *,
    smooth_window: int = 31,
    valid_threshold: float = 0.02,
    min_valid_fraction: float = 0.75,
    power: float = 1.6,
    q_clip: tuple[float, float] = (2.0, 98.0),
) -> np.ndarray:
    mask = valid_column_mask(
        gray_01,
        thr=valid_threshold,
        min_frac=min_valid_fraction,
    )
    speed = estimate_speed_from_image(
        gray_01,
        col_mask=mask,
        smooth_window=smooth_window,
    )
    return prepare_speed(speed, power=power, q_clip=q_clip)


def export_speed_profile_csv(path: Path, speed: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = np.arange(speed.size, dtype=np.float32)
    payload = np.column_stack([rows, speed.astype(np.float32)])
    np.savetxt(path, payload, delimiter=",", header="row_index,v_prepared", comments="", fmt="%.6f")
    return path

