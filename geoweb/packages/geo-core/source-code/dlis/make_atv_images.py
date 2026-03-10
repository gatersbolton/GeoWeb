import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

try:
    from dlisio import dlis
except ImportError as exc:
    raise SystemExit("Missing dependency 'dlisio'. Install with: pip install dlisio") from exc


# Typical ATV display style: black -> dark brown -> orange -> yellow.
ATV_ORANGE_CMAP = LinearSegmentedColormap.from_list(
    "atv_orange",
    ["#000000", "#211200", "#5f3300", "#b35f00", "#f08d00", "#ffd34d"],
)

AMP_KEYWORDS = ("amplitude", "amp", "atten", "imageamp", "ampl")
TT_KEYWORDS = ("traveltime", "travel", "transit", "tt", "time", "dt")
DEPTH_KEYWORDS = ("depth", "dept")
BAD_IMAGE_HINTS = ("wnd", "window")


@dataclass
class ChannelCandidate:
    frame_name: str
    channel_name: str
    unit: str
    data: np.ndarray
    depth: Optional[np.ndarray]


def normalize_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def pick_depth_channel(frame, curves) -> Optional[np.ndarray]:
    names = list(curves.dtype.names or [])
    if not names:
        return None

    depth_names: list[str] = []
    for ch in frame.channels:
        ch_name = str(getattr(ch, "name", ""))
        key = normalize_name(ch_name)
        if any(k in key for k in DEPTH_KEYWORDS) and ch_name in names:
            depth_names.append(ch_name)

    if not depth_names and "DEPTH" in names:
        depth_names = ["DEPTH"]

    for name in depth_names:
        arr = np.asarray(curves[name])
        if arr.ndim != 1:
            continue
        if not np.issubdtype(arr.dtype, np.number):
            continue
        return arr.astype(float, copy=False)

    return None


def to_float_array(data: np.ndarray) -> np.ndarray:
    arr = np.asarray(data)

    if arr.dtype.names:
        numeric_cols = []
        for key in arr.dtype.names:
            col = np.asarray(arr[key])
            if np.issubdtype(col.dtype, np.number):
                numeric_cols.append(col.reshape(arr.shape[0], -1))
        if not numeric_cols:
            return np.asarray([], dtype=float)
        arr = np.concatenate(numeric_cols, axis=1)

    if not np.issubdtype(arr.dtype, np.number):
        return np.asarray([], dtype=float)

    if arr.ndim > 2:
        arr = arr.reshape(arr.shape[0], -1)

    return arr.astype(float, copy=False)


def collect_candidates(logical_files: Iterable) -> list[ChannelCandidate]:
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

            depth = pick_depth_channel(frame, curves)

            for channel in frame.channels:
                ch_name = str(getattr(channel, "name", ""))
                if not ch_name or ch_name not in curve_names:
                    continue

                arr = to_float_array(np.asarray(curves[ch_name]))
                if arr.size == 0 or arr.ndim == 0:
                    continue

                unit = str(getattr(channel, "units", "") or "")
                candidates.append(
                    ChannelCandidate(
                        frame_name=str(getattr(frame, "name", "")),
                        channel_name=ch_name,
                        unit=unit,
                        data=arr,
                        depth=depth,
                    )
                )

    return candidates


def score_candidate(candidate: ChannelCandidate, kind: str) -> float:
    name_key = normalize_name(candidate.channel_name)
    unit_key = normalize_name(candidate.unit)
    arr = candidate.data
    score = 0.0

    if arr.ndim == 2:
        score += 12.0
        rows, cols = arr.shape
        if rows > cols:
            score += 2.0
        if 16 <= cols <= 720:
            score += 4.0
        if rows >= 500:
            score += 2.0
    elif arr.ndim == 1:
        score -= 8.0

    keywords = AMP_KEYWORDS if kind == "amplitude" else TT_KEYWORDS
    for kw in keywords:
        if kw in name_key:
            score += 5.0

    for bad_kw in BAD_IMAGE_HINTS:
        if bad_kw in name_key:
            score -= 8.0

    if kind == "traveltime":
        if "us" in candidate.unit.lower() or "ms" in candidate.unit.lower():
            score += 4.0
        if "time" in name_key:
            score += 2.0

    if kind == "amplitude" and "db" in unit_key:
        score += 2.0

    score += 3.0 * float(np.isfinite(arr).mean())
    return score


def select_best_channel(candidates: list[ChannelCandidate], kind: str) -> ChannelCandidate:
    best: Optional[tuple[float, ChannelCandidate]] = None

    for cand in candidates:
        s = score_candidate(cand, kind)
        if best is None or s > best[0]:
            best = (s, cand)

    if best is None:
        raise RuntimeError(f"No usable channel found for {kind}")

    return best[1]


def robust_normalize(
    image: np.ndarray,
    clip_low: float,
    clip_high: float,
    gamma: float,
    invert: bool,
) -> np.ndarray:
    finite = np.isfinite(image)
    if not finite.any():
        raise RuntimeError("Image channel contains no finite values")

    lo, hi = np.nanpercentile(image, [clip_low, clip_high])
    if (not np.isfinite(lo)) or (not np.isfinite(hi)) or hi <= lo:
        lo = float(np.nanmin(image))
        hi = float(np.nanmax(image))
        if hi <= lo:
            hi = lo + 1.0

    x = np.clip((image - lo) / (hi - lo), 0.0, 1.0)
    x = np.power(x, max(gamma, 1e-6))
    if invert:
        x = 1.0 - x

    return np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)


def crop_by_depth(
    image: np.ndarray,
    depth: Optional[np.ndarray],
    depth_min: Optional[float],
    depth_max: Optional[float],
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    if depth is None:
        if depth_min is not None or depth_max is not None:
            raise RuntimeError("Depth channel not found, cannot apply depth range.")
        return image, None

    lo = float(np.nanmin(depth)) if depth_min is None else float(depth_min)
    hi = float(np.nanmax(depth)) if depth_max is None else float(depth_max)

    if lo > hi:
        lo, hi = hi, lo

    mask = (depth >= lo) & (depth <= hi)
    if not np.any(mask):
        raise RuntimeError(f"Depth range [{lo}, {hi}] has no samples in this file.")

    idx = np.flatnonzero(mask)
    start, end = int(idx[0]), int(idx[-1]) + 1
    return image[start:end, :], depth[start:end]


def prepare_image(
    data: np.ndarray,
    depth: Optional[np.ndarray],
    clip_low: float,
    clip_high: float,
    gamma: float,
    invert: bool,
    depth_min: Optional[float],
    depth_max: Optional[float],
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    if data.ndim != 2:
        raise RuntimeError(f"Expected 2D image channel, got shape={data.shape}")

    img = data.copy()
    depth_axis = depth.copy() if depth is not None else None

    if depth_axis is not None:
        if depth_axis.shape[0] == img.shape[1] and depth_axis.shape[0] != img.shape[0]:
            img = img.T
        if depth_axis.shape[0] != img.shape[0]:
            depth_axis = None

    if depth_axis is not None:
        order = np.argsort(depth_axis)
        img = img[order, :]
        depth_axis = depth_axis[order]

    img, depth_axis = crop_by_depth(img, depth_axis, depth_min, depth_max)

    norm = robust_normalize(
        image=img,
        clip_low=clip_low,
        clip_high=clip_high,
        gamma=gamma,
        invert=invert,
    )
    return norm, depth_axis


def upscale_image(image: np.ndarray, pixel_scale: int) -> np.ndarray:
    if pixel_scale <= 1:
        return image
    out = np.repeat(image, pixel_scale, axis=0)
    out = np.repeat(out, pixel_scale, axis=1)
    return out


def save_png(image: np.ndarray, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(out_path, image, cmap=ATV_ORANGE_CMAP, vmin=0.0, vmax=1.0)


def make_panel(amp_image: np.ndarray, tt_image: np.ndarray) -> np.ndarray:
    if amp_image.shape[0] != tt_image.shape[0]:
        # Keep native sampling: no vertical interpolation, crop to common rows.
        rows = min(amp_image.shape[0], tt_image.shape[0])
        amp_image = amp_image[:rows, :]
        tt_image = tt_image[:rows, :]

    gap = np.zeros((amp_image.shape[0], 8), dtype=float)
    return np.concatenate([amp_image, gap, tt_image], axis=1)


def process_file(
    path: Path,
    output_dir: Path,
    clip_low: float,
    clip_high: float,
    gamma: float,
    depth_min: Optional[float],
    depth_max: Optional[float],
    pixel_scale: int,
):
    logical_files = dlis.load(str(path))
    candidates = collect_candidates(logical_files)
    if not candidates:
        raise RuntimeError("No numeric channels found")

    amp = select_best_channel(candidates, "amplitude")
    tt = select_best_channel(candidates, "traveltime")

    amp_image, amp_depth = prepare_image(
        amp.data,
        amp.depth,
        clip_low=clip_low,
        clip_high=clip_high,
        gamma=gamma,
        invert=False,
        depth_min=depth_min,
        depth_max=depth_max,
    )
    tt_image, tt_depth = prepare_image(
        tt.data,
        tt.depth,
        clip_low=clip_low,
        clip_high=clip_high,
        gamma=gamma,
        invert=False,
        depth_min=depth_min,
        depth_max=depth_max,
    )

    amp_image = upscale_image(amp_image, pixel_scale)
    tt_image = upscale_image(tt_image, pixel_scale)

    panel = make_panel(amp_image, tt_image)

    stem = path.stem
    depth_tag = "full"
    if amp_depth is not None:
        depth_tag = f"{float(np.nanmin(amp_depth)):.2f}_{float(np.nanmax(amp_depth)):.2f}m"
    amp_out = output_dir / f"{stem}_amplitude_atv_orange_{depth_tag}.png"
    tt_out = output_dir / f"{stem}_traveltime_atv_orange_{depth_tag}.png"
    panel_out = output_dir / f"{stem}_amplitude_traveltime_atv_orange_panel_{depth_tag}.png"

    save_png(amp_image, amp_out)
    save_png(tt_image, tt_out)
    save_png(panel, panel_out)

    return {
        "file": path.name,
        "amp_channel": amp.channel_name,
        "tt_channel": tt.channel_name,
        "amp_shape": amp_image.shape,
        "tt_shape": tt_image.shape,
        "panel_shape": panel.shape,
        "amp_out": str(amp_out),
        "tt_out": str(tt_out),
        "panel_out": str(panel_out),
        "depth_min": float(np.nanmin(amp_depth)) if amp_depth is not None else None,
        "depth_max": float(np.nanmax(amp_depth)) if amp_depth is not None else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Read DLIS from raw/ and export ATV-style orange amplitude/travel-time images to output/."
    )
    parser.add_argument("--raw", default="raw", help="Input folder containing .dlis files")
    parser.add_argument("--output", default="output", help="Output folder for PNG images")
    parser.add_argument("--depth-min", type=float, default=None, help="Lower depth bound (m)")
    parser.add_argument("--depth-max", type=float, default=None, help="Upper depth bound (m)")
    parser.add_argument(
        "--pixel-scale",
        type=int,
        default=2,
        help="Isotropic upscale factor (same factor for width/height, default: 2).",
    )
    parser.add_argument("--clip-low", type=float, default=1.0, help="Lower percentile clip (default: 1)")
    parser.add_argument("--clip-high", type=float, default=99.0, help="Upper percentile clip (default: 99)")
    parser.add_argument(
        "--gamma",
        type=float,
        default=0.85,
        help="Gamma for contrast shaping (<1 brighter, >1 darker; default: 0.85)",
    )
    args = parser.parse_args()

    if args.clip_low < 0 or args.clip_high > 100 or args.clip_low >= args.clip_high:
        raise SystemExit("Invalid clip range: require 0 <= clip-low < clip-high <= 100")
    if args.pixel_scale <= 0:
        raise SystemExit("pixel-scale must be > 0")

    raw_dir = Path(args.raw)
    output_dir = Path(args.output)

    files = sorted(raw_dir.glob("*.dlis"))
    if not files:
        raise SystemExit(f"No .dlis files found in: {raw_dir}")

    for path in files:
        try:
            info = process_file(
                path=path,
                output_dir=output_dir,
                clip_low=args.clip_low,
                clip_high=args.clip_high,
                gamma=args.gamma,
                depth_min=args.depth_min,
                depth_max=args.depth_max,
                pixel_scale=args.pixel_scale,
            )
            print(
                f"[OK] {info['file']} | amp={info['amp_channel']} {info['amp_shape']} | "
                f"tt={info['tt_channel']} {info['tt_shape']} | panel={info['panel_shape']}"
            )
            if info["depth_min"] is not None:
                print(f"     depth window: {info['depth_min']:.3f} m ~ {info['depth_max']:.3f} m")
            print(f"     amplitude: {info['amp_out']}")
            print(f"     traveltime: {info['tt_out']}")
            print(f"     panel:      {info['panel_out']}")
        except Exception as exc:
            print(f"[FAIL] {path.name}: {exc}")


if __name__ == "__main__":
    main()
