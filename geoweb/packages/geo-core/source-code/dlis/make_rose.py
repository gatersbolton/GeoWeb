import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    from dlisio import dlis
except ImportError as exc:
    raise SystemExit(
        "缺少依赖 dlisio，请先安装：pip install dlisio"
    ) from exc


CANDIDATE_KEYWORDS = (
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


def to_numpy_1d(values):
    arr = np.asarray(values)
    if arr.size == 0:
        return np.asarray([], dtype=float)
    if arr.dtype.names:
        # structured array: flatten numeric fields
        cols = []
        for name in arr.dtype.names:
            col = np.asarray(arr[name])
            if np.issubdtype(col.dtype, np.number):
                cols.append(col.reshape(-1))
        if not cols:
            return np.asarray([], dtype=float)
        return np.concatenate(cols).astype(float, copy=False)
    return arr.reshape(-1).astype(float, copy=False)


def score_channel(name: str, unit: str | None) -> int:
    lname = (name or "").lower()
    lunit = (unit or "").lower()
    score = 0
    for kw in CANDIDATE_KEYWORDS:
        if kw in lname:
            score += 3
    if "deg" in lunit or "rad" in lunit:
        score += 2
    return score


def extract_angle_series(path: Path):
    logical_files = dlis.load(str(path))
    best = None

    for logical in logical_files:
        for frame in logical.frames:
            try:
                curves = frame.curves()
            except Exception:
                continue

            for channel in frame.channels:
                ch_name = getattr(channel, "name", None)
                if not ch_name:
                    continue

                if ch_name not in curves.dtype.names:
                    continue

                unit = getattr(channel, "units", "")
                score = score_channel(ch_name, unit)
                data = to_numpy_1d(curves[ch_name])
                data = data[np.isfinite(data)]
                if data.size == 0:
                    continue

                if unit and str(unit).lower().startswith("rad"):
                    data = np.degrees(data)

                # 归一化到 [0, 360)
                data = np.mod(data, 360.0)

                # 增加合理性: 角度分布应在0~360
                valid_ratio = float(np.mean((data >= 0) & (data < 360)))
                score += int(valid_ratio * 2)

                if best is None or score > best[0] or (score == best[0] and data.size > best[3]):
                    best = (score, ch_name, unit, data.size, data)

    if best is None:
        raise RuntimeError(f"未在 {path.name} 中找到可用角度通道")

    _, name, unit, _, data = best
    return name, unit, data


def plot_rose(angles_deg: np.ndarray, title: str, bins: int, out_path: Path):
    theta = np.deg2rad(angles_deg)
    edges = np.linspace(0.0, 2 * np.pi, bins + 1)
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


def process_one(dlis_path: Path, output_dir: Path, bins: int):
    ch_name, unit, angles = extract_angle_series(dlis_path)
    out_name = dlis_path.stem + "_rose.png"
    out_path = output_dir / out_name
    title = f"{dlis_path.name} | channel: {ch_name} ({unit or 'unknown'})"
    plot_rose(angles, title, bins, out_path)
    return out_path, ch_name, unit, angles.size


def main():
    parser = argparse.ArgumentParser(description="从 raw 目录读取 DLIS 并生成玫瑰图")
    parser.add_argument("--raw", default="raw", help="DLIS 输入目录")
    parser.add_argument("--output", default="output", help="玫瑰图输出目录")
    parser.add_argument("--bins", type=int, default=36, help="玫瑰图扇区数，默认 36")
    args = parser.parse_args()

    raw_dir = Path(args.raw)
    out_dir = Path(args.output)

    files = sorted(raw_dir.glob("*.dlis"))
    if not files:
        raise SystemExit(f"未在 {raw_dir} 找到 .dlis 文件")

    for f in files:
        try:
            out_path, ch_name, unit, n = process_one(f, out_dir, args.bins)
            print(f"[OK] {f.name} -> {out_path} | channel={ch_name} unit={unit or 'unknown'} samples={n}")
        except Exception as exc:
            print(f"[FAIL] {f.name}: {exc}")


if __name__ == "__main__":
    main()
