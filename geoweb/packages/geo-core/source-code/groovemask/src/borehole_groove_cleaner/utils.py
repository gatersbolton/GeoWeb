from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ArrayLike = np.ndarray
Rect = tuple[int, int, int, int]


@dataclass(slots=True)
class CandidateBand:
    y0: int
    y1: int
    start: int
    end: int
    polarity: str
    persistence: float
    amplitude: float
    amp_min: float
    z_peak: float
    q_peak: float

    @property
    def width(self) -> int:
        return int(self.end - self.start)

    @property
    def center(self) -> float:
        return float((self.start + self.end - 1) / 2.0)

    @property
    def mid_y(self) -> float:
        return float((self.y0 + self.y1 - 1) / 2.0)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["width"] = self.width
        payload["center"] = self.center
        payload["mid_y"] = self.mid_y
        return payload


@dataclass(slots=True)
class GrooveTrack:
    track_id: int
    polarity: str
    candidates: list[CandidateBand] = field(default_factory=list)

    @property
    def span_pixels(self) -> int:
        if not self.candidates:
            return 0
        return int(max(item.y1 for item in self.candidates) - min(item.y0 for item in self.candidates))

    @property
    def mean_center(self) -> float:
        if not self.candidates:
            return 0.0
        return float(np.mean([item.center for item in self.candidates]))

    @property
    def mean_width(self) -> float:
        if not self.candidates:
            return 0.0
        return float(np.mean([item.width for item in self.candidates]))

    @property
    def width_mad(self) -> float:
        widths = np.asarray([item.width for item in self.candidates], dtype=np.float32)
        if widths.size == 0:
            return 0.0
        return float(np.median(np.abs(widths - np.median(widths))))

    @property
    def mean_persistence(self) -> float:
        if not self.candidates:
            return 0.0
        return float(np.mean([item.persistence for item in self.candidates]))

    @property
    def mean_amplitude(self) -> float:
        if not self.candidates:
            return 0.0
        return float(np.mean([item.amplitude for item in self.candidates]))

    @property
    def max_step_drift(self) -> float:
        if len(self.candidates) < 2:
            return 0.0
        centers = np.asarray([item.center for item in self.candidates], dtype=np.float32)
        return float(np.max(np.abs(np.diff(centers))))

    def as_dict(self, *, width: int, pad_x: int = 0) -> dict[str, Any]:
        centers = [wrap_center(item.center - pad_x, width) for item in self.candidates]
        rows = [item.mid_y for item in self.candidates]
        widths = [item.width for item in self.candidates]
        return {
            "track_id": self.track_id,
            "polarity": self.polarity,
            "center_col": float(np.mean(centers)) if centers else 0.0,
            "width": float(np.mean(widths)) if widths else 0.0,
            "depth_start": int(min(item.y0 for item in self.candidates)) if self.candidates else 0,
            "depth_end": int(max(item.y1 for item in self.candidates)) if self.candidates else 0,
            "confidence": float(min(1.0, 0.5 * self.mean_persistence + 0.5 * min(1.0, self.mean_amplitude * 4.0))),
            "span_pixels": self.span_pixels,
            "anchors": [
                {
                    "row": float(row),
                    "center_col": float(center),
                    "width": float(width_value),
                }
                for row, center, width_value in zip(rows, centers, widths)
            ],
        }


@dataclass(slots=True)
class ChannelArtifacts:
    raw: np.ndarray
    clean: np.ndarray
    mask: np.ndarray
    tracks: list[GrooveTrack]
    overlay: np.ndarray
    diff: np.ndarray
    debug_images: dict[str, np.ndarray] = field(default_factory=dict)
    debug_payload: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GrooveMaskResult:
    raw_image: np.ndarray
    clean_image: np.ndarray
    mask: np.ndarray
    tracks: list[GrooveTrack]
    overlay: np.ndarray
    diff: np.ndarray
    debug_images: dict[str, np.ndarray] = field(default_factory=dict)
    debug_payload: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LoadedImage:
    source: np.ndarray
    source_path: Path | None
    is_color: bool
    has_alpha: bool
    source_dtype: np.dtype
    original_mode: str
    source_range: tuple[float, float]
    roi: Rect
    crop_applied: Rect


def ensure_odd(value: int) -> int:
    return int(value if value % 2 == 1 else value + 1)


def mad(values: np.ndarray, eps: float = 1.0e-8) -> float:
    arr = np.asarray(values, dtype=np.float32)
    if arr.size == 0:
        return 0.0
    med = float(np.median(arr))
    return float(np.median(np.abs(arr - med)) + eps)


def robust_zscore(values: np.ndarray, eps: float = 1.0e-8) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    med = np.median(arr)
    scale = 1.4826 * mad(arr, eps=eps)
    return (arr - med) / max(scale, eps)


def contiguous_runs(mask: Sequence[bool] | np.ndarray) -> list[tuple[int, int]]:
    arr = np.asarray(mask, dtype=bool)
    if arr.ndim != 1 or arr.size == 0:
        return []
    padded = np.pad(arr.astype(np.int8), (1, 1))
    diff = np.diff(padded)
    starts = np.flatnonzero(diff == 1)
    ends = np.flatnonzero(diff == -1)
    return [(int(start), int(end)) for start, end in zip(starts, ends)]


def normalize_to_unit(arr: np.ndarray) -> tuple[np.ndarray, tuple[float, float]]:
    src = np.asarray(arr, dtype=np.float32)
    mn = float(np.nanmin(src))
    mx = float(np.nanmax(src))
    if mx <= mn:
        return np.zeros_like(src, dtype=np.float32), (mn, mx)
    return (src - mn) / (mx - mn), (mn, mx)


def restore_from_unit(unit: np.ndarray, src_range: tuple[float, float], dtype: np.dtype | None = None) -> np.ndarray:
    mn, mx = src_range
    if mx <= mn:
        restored = np.full_like(unit, mn, dtype=np.float32)
    else:
        restored = np.asarray(unit, dtype=np.float32) * (mx - mn) + mn
    if dtype is None:
        return restored
    if np.issubdtype(dtype, np.integer):
        info = np.iinfo(dtype)
        return np.clip(np.rint(restored), info.min, info.max).astype(dtype)
    return restored.astype(dtype)


def wrap_center(center: float, width: int) -> float:
    if width <= 0:
        return center
    return float(center % width)


def interval_iou(a0: int, a1: int, b0: int, b1: int) -> float:
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    if union <= 0:
        return 0.0
    return float(inter / union)


def serializable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if is_dataclass(value):
        return serializable(asdict(value))
    if isinstance(value, dict):
        return {str(key): serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    return value


def clip_roi(rect: Rect, height: int, width: int) -> Rect:
    x0, x1, y0, y1 = rect
    x0 = int(np.clip(x0, 0, width))
    x1 = int(np.clip(x1, x0 + 1, width))
    y0 = int(np.clip(y0, 0, height))
    y1 = int(np.clip(y1, y0 + 1, height))
    return x0, x1, y0, y1
