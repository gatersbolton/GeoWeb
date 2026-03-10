from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator

from borehole_groove_cleaner.config import GrooveMaskConfig
from borehole_groove_cleaner.utils import contiguous_runs


@dataclass(slots=True)
class RepairStats:
    pchip_rows: int = 0
    linear_rows: int = 0
    nearest_rows: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "pchip_rows": self.pchip_rows,
            "linear_rows": self.linear_rows,
            "nearest_rows": self.nearest_rows,
        }


def _collect_context(mask_row: np.ndarray, start: int, end: int, context: int) -> tuple[np.ndarray, np.ndarray]:
    indices = np.arange(mask_row.size)
    left_mask = (indices < start) & (~mask_row)
    right_mask = (indices >= end) & (~mask_row)
    left_indices = indices[left_mask][-context:]
    right_indices = indices[right_mask][:context]
    return left_indices.astype(np.int32), right_indices.astype(np.int32)


def rowwise_pchip_fill(gray: np.ndarray, mask: np.ndarray, cfg: GrooveMaskConfig) -> tuple[np.ndarray, RepairStats]:
    gray = np.asarray(gray, dtype=np.float32)
    mask = np.asarray(mask, dtype=bool)
    filled = gray.copy()
    stats = RepairStats()

    for row in range(gray.shape[0]):
        row_mask = mask[row]
        if not row_mask.any():
            continue
        runs = contiguous_runs(row_mask)
        for start, end in runs:
            left_idx, right_idx = _collect_context(row_mask, start, end, cfg.interp_context)
            x_points = np.concatenate([left_idx, right_idx]).astype(np.float32)
            if x_points.size == 0:
                continue
            y_points = gray[row, x_points.astype(int)]
            target_x = np.arange(start, end, dtype=np.float32)

            if left_idx.size >= 4 and right_idx.size >= 4 and np.unique(x_points).size >= 4:
                interpolator = PchipInterpolator(x_points, y_points, extrapolate=True)
                filled[row, start:end] = interpolator(target_x).astype(np.float32)
                stats.pchip_rows += 1
            elif left_idx.size >= 1 and right_idx.size >= 1:
                x_lr = np.asarray([left_idx[-1], right_idx[0]], dtype=np.float32)
                y_lr = np.asarray([gray[row, left_idx[-1]], gray[row, right_idx[0]]], dtype=np.float32)
                filled[row, start:end] = np.interp(target_x, x_lr, y_lr).astype(np.float32)
                stats.linear_rows += 1
            elif left_idx.size >= 1:
                filled[row, start:end] = gray[row, left_idx[-1]]
                stats.nearest_rows += 1
            else:
                filled[row, start:end] = gray[row, right_idx[0]]
                stats.nearest_rows += 1

    filled[~mask] = gray[~mask]
    return filled, stats


def small_radius_blend(prefill: np.ndarray, original: np.ndarray, mask: np.ndarray, cfg: GrooveMaskConfig) -> np.ndarray:
    prefill = np.asarray(prefill, dtype=np.float32)
    original = np.asarray(original, dtype=np.float32)
    mask_u8 = (np.asarray(mask) > 0).astype(np.uint8) * 255
    if mask_u8.max() == 0:
        return original.copy()

    src_u8 = np.clip(np.rint(prefill * 255.0), 0, 255).astype(np.uint8)
    blended = cv2.inpaint(src_u8, mask_u8, float(cfg.inpaint_radius), cv2.INPAINT_TELEA)
    clean = blended.astype(np.float32) / 255.0
    clean[mask_u8 == 0] = original[mask_u8 == 0]
    return clean
