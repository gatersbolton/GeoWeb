from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from algorithms.core.exceptions import ResultSerializationError


def build_output_filename(job_id: str, step_index: int, algo_id: str, ext: str) -> str:
    return f"job_{job_id}_step_{step_index}_{algo_id}.{ext}"


def save_npz(path: Path, data: np.ndarray, metadata: dict[str, Any]) -> Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            data=np.asarray(data, dtype=np.float32),
            metadata=np.array([json.dumps(metadata, ensure_ascii=False)]),
        )
    except Exception as exc:  # pragma: no cover - defensive branch
        raise ResultSerializationError(str(exc)) from exc
    return path


def load_npz(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    loaded = np.load(path, allow_pickle=False)
    data = np.asarray(loaded["data"], dtype=np.float32)
    metadata_raw = str(loaded["metadata"][0]) if "metadata" in loaded else "{}"
    metadata = json.loads(metadata_raw)
    return data, metadata


def save_preview_png(path: Path, data: np.ndarray) -> Path | None:
    try:
        from PIL import Image
    except Exception:
        return None

    array = np.asarray(data, dtype=np.float32)
    if array.size == 0:
        return None
    min_value = float(array.min())
    max_value = float(array.max())
    if max_value - min_value == 0:
        normalized = np.zeros_like(array, dtype=np.uint8)
    else:
        normalized = ((array - min_value) / (max_value - min_value) * 255).astype(np.uint8)
    image = Image.fromarray(normalized)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path

