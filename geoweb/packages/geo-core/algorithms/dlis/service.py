from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

from algorithms.core.utils.io import build_output_filename, save_npz
from algorithms.core.utils.metadata import build_minimal_metadata

try:
    from dlisio import dlis
except ImportError as exc:  # pragma: no cover - runtime environment guard
    dlis = None
    _DLIS_IMPORT_ERROR = exc
else:  # pragma: no cover - simple assignment
    _DLIS_IMPORT_ERROR = None


ATV_ORANGE_CMAP = LinearSegmentedColormap.from_list(
    "atv_orange",
    ["#000000", "#211200", "#5f3300", "#b35f00", "#f08d00", "#ffd34d"],
)

AMP_KEYWORDS = ("amplitude", "amp", "atten", "imageamp", "ampl")
TT_KEYWORDS = ("traveltime", "travel", "transit", "tt", "time", "dt")
ANGLE_KEYWORDS = (
    "azimuth",
    "azi",
    "bearing",
    "orientation",
    "toolface",
    "tf",
    "heading",
    "angle",
    "deg",
)
DEPTH_KEYWORDS = ("depth", "dept")
BAD_IMAGE_HINTS = ("wnd", "window")


@dataclass
class ChannelCandidate:
    frame_name: str
    channel_name: str
    channel_ref: str
    unit: str
    data: np.ndarray
    depth: np.ndarray | None
    raw_shape: tuple[int, ...]
    raw_dtype: str


def inspect_dlis_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    logical_files = _load_dlis_file(file_path)
    candidates = _collect_candidates(logical_files)
    if not candidates:
        raise RuntimeError("No numeric channels found in DLIS file.")

    amplitude_ranked = _rank_candidates(candidates, kind="amplitude", top_k=8)
    traveltime_ranked = _rank_candidates(candidates, kind="traveltime", top_k=8)
    angle_ranked = _rank_candidates(candidates, kind="angle", top_k=8)

    default_amp = amplitude_ranked[0] if amplitude_ranked else None
    default_tt = traveltime_ranked[0] if traveltime_ranked else None
    default_angle = angle_ranked[0] if angle_ranked else None

    default_depth = None
    if default_amp is not None:
        amp_candidate = _find_candidate(candidates, default_amp["channel_ref"])
        default_depth = _depth_stats(amp_candidate.depth)
    elif default_tt is not None:
        tt_candidate = _find_candidate(candidates, default_tt["channel_ref"])
        default_depth = _depth_stats(tt_candidate.depth)

    return {
        "file_name": file_path.name,
        "file_size_bytes": file_path.stat().st_size if file_path.exists() else 0,
        "frames": _build_frame_summary(candidates),
        "channel_options": _build_channel_options(candidates),
        "candidates": {
            "amplitude": amplitude_ranked,
            "traveltime": traveltime_ranked,
            "angle": angle_ranked,
        },
        "defaults": {
            "amplitude_channel_ref": default_amp["channel_ref"] if default_amp else None,
            "traveltime_channel_ref": default_tt["channel_ref"] if default_tt else None,
            "angle_channel_ref": default_angle["channel_ref"] if default_angle else None,
            "depth_min": default_depth["depth_min"] if default_depth else None,
            "depth_max": default_depth["depth_max"] if default_depth else None,
            "clip_low": 1.0,
            "clip_high": 99.0,
            "gamma": 0.85,
            "pixel_scale": 2,
            "rose_bins": 36,
        },
    }


def render_dlis_outputs(
    *,
    path: str | Path,
    job_id: str,
    output_dir: str | Path,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    file_path = Path(path)
    settings = _normalize_render_options(options or {})
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    inspection = inspect_dlis_file(file_path)
    logical_files = _load_dlis_file(file_path)
    candidates = _collect_candidates(logical_files)

    outputs: list[dict[str, Any]] = []
    download_map: dict[str, str] = {}
    step_index = 1

    if settings["generate_atv"]:
        amp_ref = settings["amplitude_channel_ref"] or inspection["defaults"]["amplitude_channel_ref"]
        tt_ref = settings["traveltime_channel_ref"] or inspection["defaults"]["traveltime_channel_ref"]
        amp_candidate = _find_candidate(candidates, amp_ref)
        tt_candidate = _find_candidate(candidates, tt_ref)

        amp_image, amp_depth = _prepare_image(
            amp_candidate.data,
            amp_candidate.depth,
            clip_low=settings["clip_low"],
            clip_high=settings["clip_high"],
            gamma=settings["gamma"],
            invert=True,
            depth_min=settings["depth_min"],
            depth_max=settings["depth_max"],
        )
        tt_image, tt_depth = _prepare_image(
            tt_candidate.data,
            tt_candidate.depth,
            clip_low=settings["clip_low"],
            clip_high=settings["clip_high"],
            gamma=settings["gamma"],
            invert=False,
            depth_min=settings["depth_min"],
            depth_max=settings["depth_max"],
        )

        amp_image = _upscale_image(amp_image, settings["pixel_scale"])
        tt_image = _upscale_image(tt_image, settings["pixel_scale"])
        panel_image = _make_panel(amp_image, tt_image)

        amp_source_meta = _build_source_meta(
            file_path=file_path,
            depth_axis=amp_depth,
            image_shape=amp_image.shape,
            preprocess_ops=_build_preprocess_ops(settings, output_kind="amplitude_atv"),
        )
        tt_source_meta = _build_source_meta(
            file_path=file_path,
            depth_axis=tt_depth,
            image_shape=tt_image.shape,
            preprocess_ops=_build_preprocess_ops(settings, output_kind="traveltime_atv"),
        )
        panel_source_meta = _build_source_meta(
            file_path=file_path,
            depth_axis=amp_depth if amp_depth is not None else tt_depth,
            image_shape=panel_image.shape,
            preprocess_ops=_build_preprocess_ops(settings, output_kind="atv_panel"),
        )

        outputs.append(
            _save_image_output(
                job_id=job_id,
                step_index=step_index,
                tool_id="dlis.atv_amplitude.v1",
                title="DLIS 振幅 ATV 图",
                summary=f"振幅通道：{amp_candidate.channel_ref}",
                image=amp_image,
                output_dir=output_root,
                source_meta=amp_source_meta,
                extra_metadata={
                    "channel_ref": amp_candidate.channel_ref,
                    "frame_name": amp_candidate.frame_name,
                    "channel_name": amp_candidate.channel_name,
                    "unit": amp_candidate.unit,
                },
            )
        )
        step_index += 1
        outputs.append(
            _save_image_output(
                job_id=job_id,
                step_index=step_index,
                tool_id="dlis.atv_traveltime.v1",
                title="DLIS 走时 ATV 图",
                summary=f"走时通道：{tt_candidate.channel_ref}",
                image=tt_image,
                output_dir=output_root,
                source_meta=tt_source_meta,
                extra_metadata={
                    "channel_ref": tt_candidate.channel_ref,
                    "frame_name": tt_candidate.frame_name,
                    "channel_name": tt_candidate.channel_name,
                    "unit": tt_candidate.unit,
                },
            )
        )
        step_index += 1
        outputs.append(
            _save_image_output(
                job_id=job_id,
                step_index=step_index,
                tool_id="dlis.atv_panel.v1",
                title="DLIS 振幅/走时拼接图",
                summary=f"拼接通道：{amp_candidate.channel_ref} + {tt_candidate.channel_ref}",
                image=panel_image,
                output_dir=output_root,
                source_meta=panel_source_meta,
                extra_metadata={
                    "amplitude_channel_ref": amp_candidate.channel_ref,
                    "traveltime_channel_ref": tt_candidate.channel_ref,
                },
            )
        )
        step_index += 1

    if settings["generate_rose"]:
        angle_ref = settings["angle_channel_ref"] or inspection["defaults"]["angle_channel_ref"]
        angle_candidate = _find_candidate(candidates, angle_ref)
        angles = _prepare_angle_series(angle_candidate.data, angle_candidate.unit)
        rose_source_meta = _build_source_meta(
            file_path=file_path,
            depth_axis=angle_candidate.depth,
            image_shape=None,
            preprocess_ops=_build_preprocess_ops(settings, output_kind="rose_plot"),
        )
        outputs.append(
            _save_rose_output(
                job_id=job_id,
                step_index=step_index,
                tool_id="dlis.rose_plot.v1",
                title="DLIS 方位玫瑰图",
                summary=f"角度通道：{angle_candidate.channel_ref}",
                output_dir=output_root,
                source_meta=rose_source_meta,
                angles_deg=angles,
                bins=settings["rose_bins"],
                extra_metadata={
                    "channel_ref": angle_candidate.channel_ref,
                    "frame_name": angle_candidate.frame_name,
                    "channel_name": angle_candidate.channel_name,
                    "unit": angle_candidate.unit,
                },
            )
        )

    if not outputs:
        raise RuntimeError("No DLIS outputs were generated.")

    manifest_name = f"job_{job_id}_dlis_manifest.json"
    manifest_path = output_root / manifest_name
    manifest = {
        "job_id": job_id,
        "source_file": file_path.name,
        "options": settings,
        "inspection": inspection,
        "outputs": [
            {
                key: value
                for key, value in output.items()
                if key not in {"image_path", "npz_path", "preview_path"}
            }
            for output in outputs
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    for output in outputs:
        download_map[Path(output["image_path"]).name] = str(output["image_path"])
        download_map[Path(output["npz_path"]).name] = str(output["npz_path"])
    download_map[manifest_name] = str(manifest_path)

    return {
        "job_id": job_id,
        "source_file": file_path.name,
        "inspection": inspection,
        "options": settings,
        "outputs": outputs,
        "manifest": {"name": manifest_name, "path": str(manifest_path)},
        "download_map": download_map,
    }


def _load_dlis_file(path: Path):
    if dlis is None:  # pragma: no cover - runtime dependency guard
        raise RuntimeError(
            "Missing dependency 'dlisio'. Install with: pip install dlisio"
        ) from _DLIS_IMPORT_ERROR
    if not path.exists():
        raise FileNotFoundError(f"DLIS file not found: {path}")
    return dlis.load(str(path))


def _normalize_name(name: str) -> str:
    return "".join(char for char in str(name).lower() if char.isalnum())


def _channel_ref(frame_name: str, channel_name: str) -> str:
    return f"{frame_name}:{channel_name}"


def _pick_depth_channel(frame: Any, curves: Any) -> np.ndarray | None:
    names = list(curves.dtype.names or [])
    if not names:
        return None

    depth_names: list[str] = []
    for channel in frame.channels:
        channel_name = str(getattr(channel, "name", ""))
        key = _normalize_name(channel_name)
        if any(token in key for token in DEPTH_KEYWORDS) and channel_name in names:
            depth_names.append(channel_name)

    if not depth_names and "DEPTH" in names:
        depth_names = ["DEPTH"]

    for name in depth_names:
        arr = np.asarray(curves[name])
        if arr.ndim != 1:
            continue
        if not np.issubdtype(arr.dtype, np.number):
            continue
        return arr.astype(np.float32, copy=False)

    return None


def _to_float_array(data: np.ndarray) -> np.ndarray:
    arr = np.asarray(data)

    if arr.dtype.names:
        numeric_cols = []
        for key in arr.dtype.names:
            col = np.asarray(arr[key])
            if np.issubdtype(col.dtype, np.number):
                numeric_cols.append(col.reshape(arr.shape[0], -1))
        if not numeric_cols:
            return np.asarray([], dtype=np.float32)
        arr = np.concatenate(numeric_cols, axis=1)

    if not np.issubdtype(arr.dtype, np.number):
        return np.asarray([], dtype=np.float32)

    if arr.ndim > 2:
        arr = arr.reshape(arr.shape[0], -1)

    return arr.astype(np.float32, copy=False)


def _collect_candidates(logical_files: Iterable[Any]) -> list[ChannelCandidate]:
    candidates: list[ChannelCandidate] = []

    for logical in logical_files:
        for frame in logical.frames:
            try:
                curves = frame.curves()
            except Exception:
                continue

            curve_names = list(curves.dtype.names or [])
            if not curve_names:
                continue

            depth = _pick_depth_channel(frame, curves)
            frame_name = str(getattr(frame, "name", "") or "unknown_frame")

            for channel in frame.channels:
                channel_name = str(getattr(channel, "name", "") or "")
                if not channel_name or channel_name not in curve_names:
                    continue

                raw_array = np.asarray(curves[channel_name])
                data = _to_float_array(raw_array)
                if data.size == 0 or data.ndim == 0:
                    continue

                candidates.append(
                    ChannelCandidate(
                        frame_name=frame_name,
                        channel_name=channel_name,
                        channel_ref=_channel_ref(frame_name, channel_name),
                        unit=str(getattr(channel, "units", "") or ""),
                        data=data,
                        depth=depth,
                        raw_shape=tuple(int(item) for item in raw_array.shape),
                        raw_dtype=str(raw_array.dtype),
                    )
                )

    return candidates


def _score_candidate(candidate: ChannelCandidate, kind: str) -> float:
    name_key = _normalize_name(candidate.channel_name)
    unit_key = _normalize_name(candidate.unit)
    data = candidate.data
    score = 0.0

    if kind in {"amplitude", "traveltime"}:
        if data.ndim == 2:
            score += 12.0
            rows, cols = data.shape
            if rows > cols:
                score += 2.0
            if 16 <= cols <= 720:
                score += 4.0
            if rows >= 500:
                score += 2.0
        else:
            score -= 8.0

        keywords = AMP_KEYWORDS if kind == "amplitude" else TT_KEYWORDS
        for keyword in keywords:
            if keyword in name_key:
                score += 5.0

        for bad_keyword in BAD_IMAGE_HINTS:
            if bad_keyword in name_key:
                score -= 8.0

        if kind == "traveltime":
            if "us" in candidate.unit.lower() or "ms" in candidate.unit.lower():
                score += 4.0
            if "time" in name_key:
                score += 2.0
        if kind == "amplitude" and "db" in unit_key:
            score += 2.0
    elif kind == "angle":
        if data.ndim == 1:
            score += 8.0
        else:
            score -= 8.0
        for keyword in ANGLE_KEYWORDS:
            if keyword in name_key:
                score += 3.0
        if "deg" in candidate.unit.lower() or "rad" in candidate.unit.lower():
            score += 2.0

    score += 3.0 * float(np.isfinite(data).mean())
    return score


def _rank_candidates(
    candidates: list[ChannelCandidate],
    *,
    kind: str,
    top_k: int,
) -> list[dict[str, Any]]:
    scored = [
        (_score_candidate(candidate, kind), candidate)
        for candidate in candidates
        if candidate.data.ndim == (1 if kind == "angle" else 2)
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    output: list[dict[str, Any]] = []
    for score, candidate in scored[:top_k]:
        output.append(
            {
                "channel_ref": candidate.channel_ref,
                "frame_name": candidate.frame_name,
                "channel_name": candidate.channel_name,
                "unit": candidate.unit,
                "shape": list(candidate.data.shape),
                "score": round(float(score), 4),
            }
        )
    return output


def _build_frame_summary(candidates: list[ChannelCandidate]) -> list[dict[str, Any]]:
    frames: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        frame_summary = frames.setdefault(
            candidate.frame_name,
            {
                "frame_name": candidate.frame_name,
                "depth": _depth_stats(candidate.depth),
                "channels": [],
            },
        )
        frame_summary["channels"].append(
            {
                "channel_ref": candidate.channel_ref,
                "channel_name": candidate.channel_name,
                "unit": candidate.unit,
                "shape": list(candidate.data.shape),
                "raw_shape": list(candidate.raw_shape),
                "dtype": candidate.raw_dtype,
                "rank": int(candidate.data.ndim),
                "finite_ratio": round(float(np.isfinite(candidate.data).mean()), 4),
                "is_amplitude_candidate": _score_candidate(candidate, "amplitude") > 0,
                "is_traveltime_candidate": _score_candidate(candidate, "traveltime") > 0,
                "is_angle_candidate": _score_candidate(candidate, "angle") > 0,
            }
        )

    return list(frames.values())


def _build_channel_options(candidates: list[ChannelCandidate]) -> list[dict[str, Any]]:
    return [
        {
            "channel_ref": candidate.channel_ref,
            "frame_name": candidate.frame_name,
            "channel_name": candidate.channel_name,
            "label": f"{candidate.frame_name} / {candidate.channel_name}",
            "unit": candidate.unit,
            "shape": list(candidate.data.shape),
            "rank": int(candidate.data.ndim),
        }
        for candidate in candidates
    ]


def _find_candidate(candidates: list[ChannelCandidate], channel_ref: str | None) -> ChannelCandidate:
    if not channel_ref:
        raise RuntimeError("Channel reference is required.")
    for candidate in candidates:
        if candidate.channel_ref == channel_ref:
            return candidate
    raise RuntimeError(f"Channel not found in DLIS file: {channel_ref}")


def _depth_stats(depth: np.ndarray | None) -> dict[str, Any] | None:
    if depth is None or depth.size == 0:
        return None
    finite = depth[np.isfinite(depth)]
    if finite.size == 0:
        return None
    sampling = 0.0
    if finite.size > 1:
        diffs = np.diff(np.sort(finite))
        diffs = diffs[np.isfinite(diffs)]
        if diffs.size:
            sampling = float(np.median(np.abs(diffs)))
    return {
        "depth_min": float(np.min(finite)),
        "depth_max": float(np.max(finite)),
        "sample_count": int(finite.size),
        "sampling_rate_depth": sampling,
    }


def _normalize_render_options(raw: dict[str, Any]) -> dict[str, Any]:
    generate_atv = _to_bool(raw.get("generate_atv"), default=True)
    generate_rose = _to_bool(raw.get("generate_rose"), default=True)
    if not generate_atv and not generate_rose:
        raise RuntimeError("At least one of generate_atv / generate_rose must be enabled.")

    clip_low = _to_float(raw.get("clip_low"), default=1.0)
    clip_high = _to_float(raw.get("clip_high"), default=99.0)
    gamma = _to_float(raw.get("gamma"), default=0.85)
    pixel_scale = _to_int(raw.get("pixel_scale"), default=2)
    rose_bins = _to_int(raw.get("rose_bins"), default=36)
    if clip_low < 0 or clip_high > 100 or clip_low >= clip_high:
        raise RuntimeError("Invalid clip range. Require 0 <= clip_low < clip_high <= 100.")
    if pixel_scale <= 0:
        raise RuntimeError("pixel_scale must be > 0.")
    if rose_bins <= 0:
        raise RuntimeError("rose_bins must be > 0.")

    return {
        "depth_min": _to_optional_float(raw.get("depth_min")),
        "depth_max": _to_optional_float(raw.get("depth_max")),
        "clip_low": clip_low,
        "clip_high": clip_high,
        "gamma": gamma,
        "pixel_scale": pixel_scale,
        "rose_bins": rose_bins,
        "generate_atv": generate_atv,
        "generate_rose": generate_rose,
        "amplitude_channel_ref": _to_optional_str(raw.get("amplitude_channel_ref")),
        "traveltime_channel_ref": _to_optional_str(raw.get("traveltime_channel_ref")),
        "angle_channel_ref": _to_optional_str(raw.get("angle_channel_ref")),
    }


def _prepare_image(
    data: np.ndarray,
    depth: np.ndarray | None,
    *,
    clip_low: float,
    clip_high: float,
    gamma: float,
    invert: bool,
    depth_min: float | None,
    depth_max: float | None,
) -> tuple[np.ndarray, np.ndarray | None]:
    if data.ndim != 2:
        raise RuntimeError(f"Expected 2D image channel, got shape={data.shape}")

    image = np.asarray(data, dtype=np.float32).copy()
    depth_axis = np.asarray(depth, dtype=np.float32).copy() if depth is not None else None

    if depth_axis is not None:
        if depth_axis.shape[0] == image.shape[1] and depth_axis.shape[0] != image.shape[0]:
            image = image.T
        if depth_axis.shape[0] != image.shape[0]:
            depth_axis = None

    if depth_axis is not None:
        order = np.argsort(depth_axis)
        image = image[order, :]
        depth_axis = depth_axis[order]

    image, depth_axis = _crop_by_depth(image, depth_axis, depth_min, depth_max)
    norm = _robust_normalize(
        image=image,
        clip_low=clip_low,
        clip_high=clip_high,
        gamma=gamma,
        invert=invert,
    )
    return norm, depth_axis


def _prepare_angle_series(data: np.ndarray, unit: str) -> np.ndarray:
    values = np.asarray(data, dtype=np.float32).reshape(-1)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise RuntimeError("Angle channel contains no finite samples.")
    if unit and str(unit).lower().startswith("rad"):
        values = np.degrees(values)
    return np.mod(values, 360.0).astype(np.float32)


def _robust_normalize(
    *,
    image: np.ndarray,
    clip_low: float,
    clip_high: float,
    gamma: float,
    invert: bool,
) -> np.ndarray:
    finite = np.isfinite(image)
    if not finite.any():
        raise RuntimeError("Image channel contains no finite values.")

    low_value, high_value = np.nanpercentile(image, [clip_low, clip_high])
    if not np.isfinite(low_value) or not np.isfinite(high_value) or high_value <= low_value:
        low_value = float(np.nanmin(image))
        high_value = float(np.nanmax(image))
        if high_value <= low_value:
            high_value = low_value + 1.0

    normalized = np.clip((image - low_value) / (high_value - low_value), 0.0, 1.0)
    normalized = np.power(normalized, max(gamma, 1e-6))
    if invert:
        normalized = 1.0 - normalized
    return np.nan_to_num(normalized, nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)


def _crop_by_depth(
    image: np.ndarray,
    depth: np.ndarray | None,
    depth_min: float | None,
    depth_max: float | None,
) -> tuple[np.ndarray, np.ndarray | None]:
    if depth is None:
        if depth_min is not None or depth_max is not None:
            raise RuntimeError("Depth channel not found, cannot apply depth range.")
        return image, None

    low_value = float(np.nanmin(depth)) if depth_min is None else float(depth_min)
    high_value = float(np.nanmax(depth)) if depth_max is None else float(depth_max)
    if low_value > high_value:
        low_value, high_value = high_value, low_value

    mask = (depth >= low_value) & (depth <= high_value)
    if not np.any(mask):
        raise RuntimeError(f"Depth range [{low_value}, {high_value}] has no samples in this file.")

    indices = np.flatnonzero(mask)
    start, end = int(indices[0]), int(indices[-1]) + 1
    return image[start:end, :], depth[start:end]


def _upscale_image(image: np.ndarray, pixel_scale: int) -> np.ndarray:
    if pixel_scale <= 1:
        return image.astype(np.float32)
    output = np.repeat(image, pixel_scale, axis=0)
    output = np.repeat(output, pixel_scale, axis=1)
    return output.astype(np.float32)


def _make_panel(amp_image: np.ndarray, tt_image: np.ndarray) -> np.ndarray:
    if amp_image.shape[0] != tt_image.shape[0]:
        rows = min(amp_image.shape[0], tt_image.shape[0])
        amp_image = amp_image[:rows, :]
        tt_image = tt_image[:rows, :]
    gap = np.zeros((amp_image.shape[0], 8), dtype=np.float32)
    return np.concatenate([amp_image, gap, tt_image], axis=1).astype(np.float32)


def _save_image_output(
    *,
    job_id: str,
    step_index: int,
    tool_id: str,
    title: str,
    summary: str,
    image: np.ndarray,
    output_dir: Path,
    source_meta: dict[str, Any],
    extra_metadata: dict[str, Any],
) -> dict[str, Any]:
    png_name = build_output_filename(job_id, step_index, tool_id, "png")
    npz_name = build_output_filename(job_id, step_index, tool_id, "npz")
    png_path = output_dir / png_name
    npz_path = output_dir / npz_name

    _save_png(image, png_path)
    metadata = build_minimal_metadata(
        job_id=job_id,
        created_by="dlis-service",
        service_version="geo-core.dlis.v1",
        source_meta=source_meta,
    )
    metadata["algo_chain"] = [tool_id]
    metadata["dlis"] = extra_metadata
    save_npz(npz_path, image.astype(np.float32), metadata)

    return {
        "tool_id": tool_id,
        "kind": tool_id,
        "title": title,
        "summary": summary,
        "shape": list(image.shape),
        "image_path": str(png_path),
        "npz_path": str(npz_path),
        "preview_path": str(png_path),
        "metadata": metadata,
    }


def _save_rose_output(
    *,
    job_id: str,
    step_index: int,
    tool_id: str,
    title: str,
    summary: str,
    output_dir: Path,
    source_meta: dict[str, Any],
    angles_deg: np.ndarray,
    bins: int,
    extra_metadata: dict[str, Any],
) -> dict[str, Any]:
    png_name = build_output_filename(job_id, step_index, tool_id, "png")
    npz_name = build_output_filename(job_id, step_index, tool_id, "npz")
    png_path = output_dir / png_name
    npz_path = output_dir / npz_name

    plot_title = f"DLIS rose plot | {extra_metadata.get('channel_ref', 'angle channel')}"
    _plot_rose(angles_deg=angles_deg, title=plot_title, bins=bins, out_path=png_path)
    metadata = build_minimal_metadata(
        job_id=job_id,
        created_by="dlis-service",
        service_version="geo-core.dlis.v1",
        source_meta=source_meta,
    )
    metadata["algo_chain"] = [tool_id]
    metadata["dlis"] = {**extra_metadata, "rose_bins": bins}
    save_npz(npz_path, angles_deg.astype(np.float32), metadata)

    return {
        "tool_id": tool_id,
        "kind": tool_id,
        "title": title,
        "summary": summary,
        "shape": [int(angles_deg.shape[0])],
        "image_path": str(png_path),
        "npz_path": str(npz_path),
        "preview_path": str(png_path),
        "metadata": metadata,
    }


def _plot_rose(*, angles_deg: np.ndarray, title: str, bins: int, out_path: Path) -> None:
    theta = np.deg2rad(angles_deg)
    edges = np.linspace(0.0, 2.0 * np.pi, bins + 1)
    counts, _ = np.histogram(theta, bins=edges)
    widths = np.diff(edges)
    centers = edges[:-1]

    fig = plt.figure(figsize=(8, 8), dpi=140)
    ax = fig.add_subplot(111, projection="polar")
    ax.bar(centers, counts, width=widths, align="edge", edgecolor="white", linewidth=0.6, alpha=0.9)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title(title, pad=16)
    ax.set_rlabel_position(225)
    ax.grid(alpha=0.4)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def _save_png(image: np.ndarray, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(out_path, image, cmap=ATV_ORANGE_CMAP, vmin=0.0, vmax=1.0)


def _build_source_meta(
    *,
    file_path: Path,
    depth_axis: np.ndarray | None,
    image_shape: tuple[int, ...] | None,
    preprocess_ops: list[dict[str, Any]],
) -> dict[str, Any]:
    depth_info = _depth_stats(depth_axis)
    azimuth_sampling = 0.0
    if image_shape and len(image_shape) >= 2 and image_shape[1] > 0:
        azimuth_sampling = 360.0 / float(image_shape[1])
    return {
        "well_id": file_path.stem.split("_")[0] if "_" in file_path.stem else file_path.stem,
        "depth_start": depth_info["depth_min"] if depth_info else 0.0,
        "depth_end": depth_info["depth_max"] if depth_info else 0.0,
        "sampling_rate_depth": depth_info["sampling_rate_depth"] if depth_info else 0.0,
        "sampling_rate_azimuth": azimuth_sampling,
        "input_format": "dlis",
        "original_file_uri": str(file_path),
        "preprocess_ops": preprocess_ops,
    }


def _build_preprocess_ops(settings: dict[str, Any], *, output_kind: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "dlis_render",
            "output_kind": output_kind,
            "clip_low": settings["clip_low"],
            "clip_high": settings["clip_high"],
            "gamma": settings["gamma"],
            "pixel_scale": settings["pixel_scale"],
            "depth_min": settings["depth_min"],
            "depth_max": settings["depth_max"],
            "rose_bins": settings["rose_bins"],
        }
    ]


def _to_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _to_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_optional_float(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
