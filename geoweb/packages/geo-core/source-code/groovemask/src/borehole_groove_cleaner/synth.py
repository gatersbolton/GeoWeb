from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(slots=True)
class SyntheticCase:
    clean: np.ndarray
    artifact: np.ndarray
    mask: np.ndarray
    tracks: list[dict[str, Any]]
    metadata: dict[str, Any]


def _base_image(height: int, width: int, rng: np.random.Generator) -> np.ndarray:
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    structure = 0.48 + 0.18 * np.sin(2.0 * np.pi * (3.8 * y + 0.12 * np.sin(2.0 * np.pi * x)))
    structure += 0.10 * np.sin(2.0 * np.pi * (7.0 * y + 0.10 * x))
    structure += 0.06 * np.cos(2.0 * np.pi * (1.8 * y - 0.08 * x))
    structure += 0.05 * rng.normal(size=(height, width)).astype(np.float32)
    structure = np.clip(structure, 0.0, 1.0)
    broad_shading = 0.08 * np.cos(2.0 * np.pi * (x - 0.25))
    return np.clip(structure + broad_shading, 0.0, 1.0).astype(np.float32)


def generate_synthetic_case(
    *,
    height: int = 200,
    width: int = 1200,
    seed: int = 42,
    groove_count: tuple[int, int] = (1, 4),
) -> SyntheticCase:
    rng = np.random.default_rng(seed)
    clean = _base_image(height, width, rng)
    artifact = clean.copy()
    mask = np.zeros((height, width), dtype=np.uint8)
    tracks: list[dict[str, Any]] = []

    for groove_id in range(rng.integers(groove_count[0], groove_count[1] + 1)):
        polarity = "dark" if rng.random() < 0.7 else "bright"
        groove_width = int(rng.integers(2, min(11, max(3, width // 20))))
        base_center = int(rng.integers(0, width))
        drift = rng.integers(-2, 3, size=height)
        start_row = int(rng.integers(0, max(1, height // 3)))
        end_row = int(rng.integers(max(start_row + height // 5, start_row + 1), height))
        strength = float(rng.uniform(0.10, 0.22))

        per_row_strength = strength * (0.7 + 0.3 * np.sin(np.linspace(0.0, np.pi, end_row - start_row, dtype=np.float32)))
        anchor_rows = []
        for offset, row in enumerate(range(start_row, end_row)):
            center = (base_center + int(drift[row])) % width
            start = center - groove_width // 2
            indices = np.arange(start, start + groove_width) % width
            if polarity == "dark":
                artifact[row, indices] = np.clip(artifact[row, indices] - per_row_strength[offset], 0.0, 1.0)
            else:
                artifact[row, indices] = np.clip(artifact[row, indices] + per_row_strength[offset], 0.0, 1.0)
            mask[row, indices] = 1
            if row % max(1, (end_row - start_row) // 6) == 0:
                anchor_rows.append({"row": float(row), "center_col": float(center), "width": float(groove_width)})

        tracks.append(
            {
                "track_id": groove_id + 1,
                "polarity": polarity,
                "center_col": float(base_center),
                "width": float(groove_width),
                "depth_start": start_row,
                "depth_end": end_row,
                "confidence": 1.0,
                "anchors": anchor_rows,
            }
        )

    interference_center = int(rng.integers(0, width))
    interference_width = int(rng.integers(max(12, width // 16), max(18, width // 10)))
    start = interference_center - interference_width // 2
    cols = np.arange(start, start + interference_width) % width
    broad_delta = (0.08 * np.cos(np.linspace(-np.pi, np.pi, interference_width, dtype=np.float32)))[None, :]
    artifact[:, cols] = np.clip(artifact[:, cols] + broad_delta, 0.0, 1.0)

    metadata = {
        "seed": seed,
        "broad_interference": {
            "center_col": interference_center,
            "width": interference_width,
        },
    }
    return SyntheticCase(clean=clean, artifact=artifact, mask=mask, tracks=tracks, metadata=metadata)
