from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from borehole_groove_cleaner.qc import normalize_image
from borehole_groove_cleaner.utils import GrooveMaskResult, LoadedImage, Rect, clip_roi, serializable


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def _as_numpy(source: str | Path | np.ndarray) -> tuple[np.ndarray, Path | None, str]:
    if isinstance(source, np.ndarray):
        arr = np.asarray(source)
        return arr.copy(), None, "array"
    path = Path(source)
    image = Image.open(path)
    arr = np.asarray(image)
    return arr, path, image.mode


def load_image(source: str | Path | np.ndarray) -> LoadedImage:
    arr, path, mode = _as_numpy(source)
    is_color = arr.ndim == 3 and arr.shape[2] >= 3
    has_alpha = arr.ndim == 3 and arr.shape[2] == 4
    height = int(arr.shape[0])
    width = int(arr.shape[1])
    src_range = (float(np.nanmin(arr)), float(np.nanmax(arr)))
    full_roi = (0, width, 0, height)
    return LoadedImage(
        source=arr,
        source_path=path,
        is_color=is_color,
        has_alpha=has_alpha,
        source_dtype=arr.dtype,
        original_mode=mode,
        source_range=src_range,
        roi=full_roi,
        crop_applied=full_roi,
    )


def gray_from_image(image: np.ndarray) -> np.ndarray:
    src = np.asarray(image)
    if src.ndim == 2:
        gray = src.astype(np.float32)
        mn = float(np.nanmin(gray))
        mx = float(np.nanmax(gray))
        if mx <= mn:
            return np.zeros_like(gray, dtype=np.float32)
        return ((gray - mn) / (mx - mn)).astype(np.float32)
    rgb = src[..., :3].astype(np.float32)
    if rgb.max() > 1.0:
        rgb /= 255.0
    gray = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return np.clip(gray, 0.0, 1.0).astype(np.float32)


def auto_crop_bbox(image: np.ndarray) -> Rect:
    gray = gray_from_image(image)
    height, width = gray.shape
    non_white = np.mean(gray < 0.98, axis=0)
    variance = np.var(gray, axis=0)
    non_black = np.mean(gray > 0.02, axis=0)
    quantized = np.clip((gray * 31.0).astype(np.int32), 0, 31)
    entropy = np.zeros(width, dtype=np.float32)
    for idx in range(width):
        hist = np.bincount(quantized[:, idx], minlength=32).astype(np.float32)
        probs = hist / max(1.0, hist.sum())
        entropy[idx] = -np.sum(probs * np.log2(np.maximum(probs, 1.0e-6)))

    # Crop only low-content borders; never shrink to a narrow high-texture slice.
    presence = (non_white > 0.05) & (non_black > 0.05)
    if not np.any(presence):
        return 0, width, 0, height

    presence_idx = np.flatnonzero(presence)
    base_start = int(presence_idx[0])
    base_end = int(presence_idx[-1] + 1)

    var_floor = float(np.quantile(variance[presence], 0.10))
    ent_floor = float(np.quantile(entropy[presence], 0.10))
    content = presence & ((variance >= var_floor) | (entropy >= ent_floor))
    content = np.convolve(content.astype(np.int32), np.ones(5, dtype=np.int32), mode="same") > 0

    if np.any(content):
        content_idx = np.flatnonzero(content)
        best_start = int(content_idx[0])
        best_end = int(content_idx[-1] + 1)
    else:
        best_start, best_end = base_start, base_end

    # Safety fallback: do not over-crop otherwise full-width panels become thin slivers.
    if best_end - best_start < max(32, int(round(width * 0.60))):
        best_start, best_end = base_start, base_end
    if best_end - best_start < max(32, int(round(width * 0.60))):
        best_start, best_end = 0, width

    trim_left = 0
    while trim_left < 3 and best_start + trim_left < best_end and float(np.mean(gray[:, best_start + trim_left])) < 0.08:
        trim_left += 1
    trim_right = 0
    while trim_right < 3 and best_end - trim_right - 1 > best_start and float(np.mean(gray[:, best_end - trim_right - 1])) < 0.08:
        trim_right += 1
    x0 = max(0, best_start + trim_left)
    x1 = min(width, best_end - trim_right)
    if x1 <= x0:
        x0, x1 = 0, width
    return x0, x1, 0, height


def crop_loaded_image(loaded: LoadedImage, roi: Rect) -> LoadedImage:
    x0, x1, y0, y1 = clip_roi(roi, loaded.source.shape[0], loaded.source.shape[1])
    cropped = loaded.source[y0:y1, x0:x1].copy()
    return LoadedImage(
        source=cropped,
        source_path=loaded.source_path,
        is_color=loaded.is_color,
        has_alpha=loaded.has_alpha,
        source_dtype=loaded.source_dtype,
        original_mode=loaded.original_mode,
        source_range=(float(np.nanmin(cropped)), float(np.nanmax(cropped))),
        roi=loaded.roi,
        crop_applied=(x0, x1, y0, y1),
    )


def restore_clean_image(loaded: LoadedImage, clean_gray: np.ndarray, raw_gray: np.ndarray) -> np.ndarray:
    clean_gray = np.asarray(clean_gray, dtype=np.float32)
    raw_gray = np.asarray(raw_gray, dtype=np.float32)
    source = loaded.source
    if loaded.is_color:
        rgb = source[..., :3].astype(np.float32)
        if rgb.max() > 1.0:
            rgb /= 255.0
        delta = clean_gray - raw_gray
        clean_rgb = np.clip(rgb + delta[..., None], 0.0, 1.0)
        clean_u8 = np.clip(np.rint(clean_rgb * 255.0), 0, 255).astype(np.uint8)
        if loaded.has_alpha:
            alpha = source[..., 3:4].copy()
            return np.concatenate([clean_u8, alpha], axis=2)
        return clean_u8

    mn, mx = loaded.source_range
    if mx <= mn:
        restored = np.full_like(clean_gray, mn, dtype=np.float32)
    else:
        restored = clean_gray * (mx - mn) + mn
    if np.issubdtype(loaded.source_dtype, np.integer):
        info = np.iinfo(loaded.source_dtype)
        return np.clip(np.rint(restored), info.min, info.max).astype(loaded.source_dtype)
    return restored.astype(loaded.source_dtype)


def _save_pil_image(arr: np.ndarray, path: Path) -> None:
    if arr.ndim == 2:
        if arr.dtype == np.uint16:
            Image.fromarray(arr).save(path)
        elif arr.dtype == np.uint8:
            Image.fromarray(arr).save(path)
        else:
            Image.fromarray(normalize_image(arr)).save(path)
        return
    if arr.ndim == 3 and arr.shape[2] == 4:
        Image.fromarray(arr.astype(np.uint8)).save(path)
        return
    if arr.ndim == 3 and arr.shape[2] >= 3:
        Image.fromarray(arr[..., :3].astype(np.uint8)).save(path)
        return
    raise ValueError(f"Unsupported image shape for saving: {arr.shape}")


def save_result_bundle(result: GrooveMaskResult, out_dir: str | Path) -> dict[str, str]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    debug_dir = out_path / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    clean_path = out_path / "clean.png"
    mask_path = out_path / "mask.png"
    overlay_path = out_path / "overlay.png"
    diff_path = out_path / "diff.png"
    tracks_path = out_path / "tracks.json"
    meta_path = out_path / "meta.json"

    _save_pil_image(result.clean_image, clean_path)
    _save_pil_image((result.mask > 0).astype(np.uint8) * 255, mask_path)
    _save_pil_image(result.overlay, overlay_path)
    _save_pil_image(result.diff, diff_path)
    tracks_path.write_text(
        json.dumps(serializable(result.debug_payload.get("tracks_serialized", [])), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    meta_path.write_text(json.dumps(serializable(result.meta), ensure_ascii=False, indent=2), encoding="utf-8")

    for name, image in result.debug_images.items():
        suffix = ".png"
        _save_pil_image(image, debug_dir / f"{name}{suffix}")
    for name, payload in result.debug_payload.items():
        if name == "tracks_serialized":
            continue
        if isinstance(payload, np.ndarray):
            _save_pil_image(payload, debug_dir / f"{name}.png")
        else:
            (debug_dir / f"{name}.json").write_text(
                json.dumps(serializable(payload), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    return {
        "clean": str(clean_path),
        "mask": str(mask_path),
        "overlay": str(overlay_path),
        "diff": str(diff_path),
        "tracks": str(tracks_path),
        "debug_dir": str(debug_dir),
        "meta": str(meta_path),
    }


def discover_images(input_path: str | Path) -> list[Path]:
    path = Path(input_path)
    if path.is_file():
        return [path]
    return sorted(candidate for candidate in path.iterdir() if candidate.suffix.lower() in IMAGE_SUFFIXES)
