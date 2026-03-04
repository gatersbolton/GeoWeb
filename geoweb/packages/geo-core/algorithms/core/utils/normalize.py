from __future__ import annotations

import numpy as np


def normalize_to_unit(
    data: np.ndarray,
    value_range: tuple[float, float] | None = None,
) -> tuple[np.ndarray, tuple[float, float]]:
    array = np.asarray(data, dtype=np.float32)
    if value_range is None:
        min_value = float(array.min())
        max_value = float(array.max())
    else:
        min_value, max_value = value_range
    if max_value - min_value == 0:
        return np.zeros_like(array, dtype=np.float32), (min_value, max_value)
    normalized = (array - min_value) / (max_value - min_value)
    return normalized.astype(np.float32), (min_value, max_value)


def denormalize_from_unit(data: np.ndarray, value_range: tuple[float, float]) -> np.ndarray:
    min_value, max_value = value_range
    return (np.asarray(data, dtype=np.float32) * (max_value - min_value) + min_value).astype(
        np.float32
    )

