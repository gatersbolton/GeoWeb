from __future__ import annotations

from typing import Iterable

import cv2
import numpy as np

from borehole_groove_cleaner.config import GrooveMaskConfig
from borehole_groove_cleaner.utils import CandidateBand, GrooveTrack, interval_iou, wrap_center


def _compatible(track: GrooveTrack, candidate: CandidateBand, cfg: GrooveMaskConfig) -> bool:
    if not track.candidates or track.polarity != candidate.polarity:
        return False
    last = track.candidates[-1]
    if abs(candidate.center - last.center) > cfg.max_drift_per_window:
        return False
    if interval_iou(last.start, last.end, candidate.start, candidate.end) <= cfg.min_track_iou:
        return False
    widths = np.asarray([item.width for item in track.candidates] + [candidate.width], dtype=np.float32)
    width_mad = float(np.median(np.abs(widths - np.median(widths))))
    return width_mad <= cfg.max_track_width_mad


def link_candidates_into_tracks(candidates: Iterable[CandidateBand], cfg: GrooveMaskConfig, height: int) -> list[GrooveTrack]:
    ordered = sorted(candidates, key=lambda item: (item.y0, item.center, item.polarity))
    tracks: list[GrooveTrack] = []
    next_id = 1
    for candidate in ordered:
        best_track: GrooveTrack | None = None
        best_cost = float("inf")
        for track in tracks:
            if not _compatible(track, candidate, cfg):
                continue
            last = track.candidates[-1]
            cost = abs(last.center - candidate.center) + 0.25 * abs(last.width - candidate.width)
            if cost < best_cost:
                best_cost = cost
                best_track = track
        if best_track is None:
            best_track = GrooveTrack(track_id=next_id, polarity=candidate.polarity, candidates=[])
            tracks.append(best_track)
            next_id += 1
        best_track.candidates.append(candidate)

    final_tracks: list[GrooveTrack] = []
    min_span = max(1, int(round(cfg.min_span_frac * height)))
    min_candidates = 1 if height <= cfg.resolved_win_h(height) else 3
    for track in tracks:
        track.candidates.sort(key=lambda item: item.mid_y)
        amp_floor = float(np.mean([item.amp_min for item in track.candidates])) if track.candidates else 0.0
        if (
            track.span_pixels >= min_span
            and len(track.candidates) >= min_candidates
            and track.mean_persistence >= cfg.persist_min
            and track.width_mad <= cfg.max_track_width_mad
            and track.max_step_drift <= cfg.max_drift_per_window
            and track.mean_amplitude >= amp_floor
        ):
            final_tracks.append(track)
    if not final_tracks:
        return final_tracks

    keep = [True] * len(final_tracks)
    for i, track_i in enumerate(final_tracks):
        if not keep[i]:
            continue
        start_i = min(item.y0 for item in track_i.candidates)
        end_i = max(item.y1 for item in track_i.candidates)
        for j in range(i + 1, len(final_tracks)):
            if not keep[j]:
                continue
            track_j = final_tracks[j]
            if track_i.polarity == track_j.polarity:
                continue
            start_j = min(item.y0 for item in track_j.candidates)
            end_j = max(item.y1 for item in track_j.candidates)
            overlap = max(0, min(end_i, end_j) - max(start_i, start_j))
            if overlap <= 0:
                continue
            overlap_frac = overlap / max(1, min(track_i.span_pixels, track_j.span_pixels))
            center_gap = abs(track_i.mean_center - track_j.mean_center)
            width_scale = max(track_i.mean_width, track_j.mean_width)
            if overlap_frac >= 0.7 and center_gap <= max(8.0, 1.5 * width_scale):
                if track_i.mean_amplitude >= track_j.mean_amplitude:
                    keep[j] = False
                else:
                    keep[i] = False
                    break
    return [track for index, track in enumerate(final_tracks) if keep[index]]


def filter_tracks_to_central_region(tracks: Iterable[GrooveTrack], width: int, pad_x: int) -> list[GrooveTrack]:
    filtered: list[GrooveTrack] = []
    left = pad_x
    right = pad_x + width
    for track in tracks:
        center = track.mean_center
        if left <= center < right:
            filtered.append(track)
    return filtered


def build_mask_from_tracks(shape: tuple[int, int], tracks: Iterable[GrooveTrack], cfg: GrooveMaskConfig) -> np.ndarray:
    height, width = shape
    mask = np.zeros((height, width), dtype=np.uint8)
    for track in tracks:
        for candidate in track.candidates:
            half = candidate.width / 2.0 + cfg.dilate_x
            start = max(0, int(np.floor(candidate.center - half)))
            end = min(width, int(np.ceil(candidate.center + half + 1)))
            mask[candidate.y0:candidate.y1, start:end] = 1

    if cfg.dilate_y > 0 or cfg.dilate_x > 0:
        kernel = np.ones((max(1, 2 * cfg.dilate_y + 1), max(1, 2 * cfg.dilate_x + 1)), dtype=np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)

    close_kernel = np.ones((max(1, 2 * max(1, cfg.dilate_y) + 1), 3), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)
    return (mask > 0).astype(np.uint8)


def serialize_tracks(tracks: Iterable[GrooveTrack], *, width: int, pad_x: int) -> list[dict[str, float | int | list[dict[str, float]]]]:
    return [track.as_dict(width=width, pad_x=pad_x) for track in tracks]


def remap_mask_to_original(mask: np.ndarray, pad_x: int) -> np.ndarray:
    if pad_x <= 0:
        return mask
    return mask[:, pad_x:-pad_x]
