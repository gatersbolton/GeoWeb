from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from borehole_groove_cleaner.config import GrooveMaskConfig
from borehole_groove_cleaner.preprocess import choose_polarity_scores, median_filter_1d
from borehole_groove_cleaner.utils import CandidateBand, contiguous_runs, mad, robust_zscore


@dataclass(slots=True)
class DetectionResult:
    candidates: list[CandidateBand] = field(default_factory=list)
    rejected_broad: list[dict[str, Any]] = field(default_factory=list)
    score_map: np.ndarray | None = None
    profile_map: np.ndarray | None = None
    window_rows: list[tuple[int, int]] = field(default_factory=list)


def sliding_windows(height: int, win: int, stride: int) -> list[tuple[int, int]]:
    if height <= win:
        return [(0, height)]
    windows: list[tuple[int, int]] = []
    y0 = 0
    while y0 < height:
        y1 = min(height, y0 + win)
        if y1 - y0 < win and windows:
            y0 = max(0, height - win)
            y1 = height
        windows.append((int(y0), int(y1)))
        if y1 >= height:
            break
        y0 += stride
    return windows


def _candidate_stats(window: np.ndarray, start: int, end: int, polarity: str, cfg: GrooveMaskConfig) -> tuple[float, float, float]:
    ry = np.mean(window[:, start:end], axis=1)
    row_thr = cfg.tau_row_factor * mad(ry)
    if polarity == "dark":
        persistence = float(np.mean(ry < -row_thr))
        amplitude = float(np.median(-ry))
    else:
        persistence = float(np.mean(ry > row_thr))
        amplitude = float(np.median(ry))
    return persistence, amplitude, float(row_thr)


def detect_candidates(residual: np.ndarray, cfg: GrooveMaskConfig, gray: np.ndarray | None = None) -> DetectionResult:
    residual = np.asarray(residual, dtype=np.float32)
    gray_source = np.asarray(gray, dtype=np.float32) if gray is not None else None
    height, width = residual.shape
    score_acc = np.zeros_like(residual, dtype=np.float32)
    score_hits = np.zeros_like(residual, dtype=np.float32)
    profile_map = np.zeros_like(residual, dtype=np.float32)
    result = DetectionResult()
    win_h = cfg.resolved_win_h(height)
    stride = cfg.resolved_stride(height)
    w_max = cfg.resolved_w_max(width)

    for y0, y1 in sliding_windows(height, win_h, stride):
        window = residual[y0:y1, :]
        gray_window = gray_source[y0:y1, :] if gray_source is not None else None
        profile = np.median(window, axis=0)
        background = median_filter_1d(profile, cfg.k_bg)
        per_window_score = np.zeros(width, dtype=np.float32)
        result.window_rows.append((y0, y1))
        rejection_threshold = max(1.25, cfg.tau_sigma * 0.5)

        for polarity_name, q_values, z_values in choose_polarity_scores(profile, background, cfg.polarity):
            per_window_score = np.maximum(per_window_score, z_values)
            if gray_window is not None:
                raw_profile = np.median(gray_window, axis=0)
                raw_background = median_filter_1d(raw_profile, max(61, cfg.k_bg * 2 + 1))
                broad_signal = (raw_background - raw_profile) if polarity_name == "dark" else (raw_profile - raw_background)
                broad_z = robust_zscore(broad_signal)
                for start, end in contiguous_runs(broad_z > 1.0):
                    band_width = end - start
                    if band_width <= w_max:
                        continue
                    result.rejected_broad.append(
                        {
                            "window": [y0, y1],
                            "start": int(start),
                            "end": int(end),
                            "width": int(band_width),
                            "polarity": polarity_name,
                            "reason": "rejected_as_broad_shading_or_non_groove",
                        }
                    )
            for start, end in contiguous_runs(z_values > rejection_threshold):
                band_width = end - start
                band_payload = {
                    "window": [y0, y1],
                    "start": int(start),
                    "end": int(end),
                    "width": int(band_width),
                    "polarity": polarity_name,
                }
                if band_width > w_max:
                    band_payload["reason"] = "rejected_as_broad_shading_or_non_groove"
                    result.rejected_broad.append(band_payload)
                    continue
                if np.max(z_values[start:end]) <= cfg.tau_sigma:
                    continue
                if band_width < cfg.w_min:
                    continue
                persistence, amplitude, amp_min = _candidate_stats(window, start, end, polarity_name, cfg)
                if persistence < cfg.persist_min or amplitude < amp_min:
                    continue
                result.candidates.append(
                    CandidateBand(
                        y0=y0,
                        y1=y1,
                        start=int(start),
                        end=int(end),
                        polarity=polarity_name,
                        persistence=float(persistence),
                        amplitude=float(amplitude),
                        amp_min=float(amp_min),
                        z_peak=float(np.max(z_values[start:end])),
                        q_peak=float(np.max(q_values[start:end])),
                    )
                )

        score_acc[y0:y1, :] += per_window_score[None, :]
        score_hits[y0:y1, :] += 1.0
        profile_map[y0:y1, :] = profile[None, :]

    score_hits[score_hits == 0.0] = 1.0
    result.score_map = score_acc / score_hits
    result.profile_map = profile_map
    return result
