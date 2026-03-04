from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from algorithms.artifacts.decentralization.algorithm import DecentralizationArtifactRemoval
from algorithms.core.data_models import InputFrame, RunContext


SUPPORTED_METHODS = ("harmonic", "azimuth_equalization", "agc")


def to_uint8(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image, dtype=np.float32)
    array = np.clip(array, 0.0, 255.0)
    return array.astype(np.uint8)


def run_single_method(
    *,
    method: str,
    original_rgb: np.ndarray,
    input_path: Path,
    output_root: Path,
) -> dict:
    algorithm = DecentralizationArtifactRemoval()
    config = algorithm.get_default_config()
    config["safe"]["method"] = method
    config["experimental"]["enable_preview_assets"] = True
    config["experimental"]["preview_image_ext"] = "png"
    config = _apply_aggressive_visual_profile(config, method)

    method_dir = output_root / method
    method_dir.mkdir(parents=True, exist_ok=True)

    frame = InputFrame(
        data=original_rgb,
        data_layout="HWC",
        value_range=[0.0, 255.0],
        source_meta={
            "input_format": "png",
            "original_file_uri": str(input_path),
        },
    )
    context = RunContext(
        job_id=f"manual_decentralization_{method}",
        step_index=1,
        created_by="manual_visual_check",
        service_version="manual",
        output_dir=str(method_dir),
    )

    output = algorithm.run(frame, config, context)
    fixed = np.asarray(output.result, dtype=np.float32)

    original_u8 = to_uint8(original_rgb)
    fixed_u8 = to_uint8(fixed)
    diff_u8 = np.abs(fixed_u8.astype(np.int16) - original_u8.astype(np.int16)).astype(np.uint8)
    side_by_side = np.concatenate([original_u8, fixed_u8], axis=1)

    original_path = method_dir / "original.png"
    fixed_path = method_dir / "fixed.png"
    compare_path = method_dir / "compare_side_by_side.png"
    diff_path = method_dir / "diff_abs.png"
    report_path = method_dir / "manual_report.json"

    Image.fromarray(original_u8).save(original_path)
    Image.fromarray(fixed_u8).save(fixed_path)
    Image.fromarray(side_by_side).save(compare_path)
    Image.fromarray(diff_u8).save(diff_path)

    report_payload = {
        "method": method,
        "input": str(input_path),
        "config": config,
        "output_files": {
            "original": str(original_path),
            "fixed": str(fixed_path),
            "compare_side_by_side": str(compare_path),
            "diff_abs": str(diff_path),
        },
        "quality_metrics": output.quality_metrics,
        "warnings": output.run_report.warnings,
        "preview_assets": output.preview_assets,
    }
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_payload


def _apply_aggressive_visual_profile(config: dict, method: str) -> dict:
    cfg = json.loads(json.dumps(config))
    if method == "harmonic":
        cfg["advanced"]["harmonic_orders"] = [1, 2, 3, 4, 5, 6]
        cfg["advanced"]["harmonic_depth_smooth_window"] = 11
        cfg["advanced"]["harmonic_strength"] = 1.0
    elif method == "azimuth_equalization":
        cfg["advanced"]["equalization_depth_window"] = 101
        cfg["advanced"]["equalization_clip_gain_min"] = 0.3
        cfg["advanced"]["equalization_clip_gain_max"] = 2.8
        cfg["advanced"]["equalization_strength"] = 1.0
    elif method == "agc":
        cfg["advanced"]["agc_axis"] = "azimuth"
        cfg["advanced"]["agc_window"] = 31
        cfg["advanced"]["agc_clip_gain_min"] = 0.3
        cfg["advanced"]["agc_clip_gain_max"] = 2.8
        cfg["advanced"]["agc_strength"] = 1.0
        cfg["advanced"]["agc_target_rms"] = 1.0
        cfg["advanced"]["agc_preserve_row_mean"] = True
    cfg["advanced"]["column_debias_strength"] = 1.0
    cfg["advanced"]["column_debias_stat"] = "median"
    cfg["advanced"]["column_debias_smooth_window"] = 1
    cfg["advanced"]["column_debias_preserve_row_mean"] = True
    return cfg


def _build_grid(output_root: Path, methods: list[str]) -> Path:
    row_images = []
    for method in methods:
        method_dir = output_root / method
        original = Image.open(method_dir / "original.png").convert("RGB")
        fixed = Image.open(method_dir / "fixed.png").convert("RGB")
        diff = Image.open(method_dir / "diff_abs.png").convert("RGB")
        row = Image.new("RGB", (original.width * 3, original.height))
        row.paste(original, (0, 0))
        row.paste(fixed, (original.width, 0))
        row.paste(diff, (original.width * 2, 0))
        row_images.append((method, row))

    total_width = row_images[0][1].width
    total_height = sum(row.height for _, row in row_images)
    canvas = Image.new("RGB", (total_width, total_height), color=(0, 0, 0))

    y = 0
    for _, row in row_images:
        canvas.paste(row, (0, y))
        y += row.height

    grid_path = output_root / "all_methods_grid.png"
    canvas.save(grid_path)
    return grid_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual visual check for decentralization artifact methods.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("algorithms/artifacts/decentralization/decentralization_test.png"),
        help="Input image path.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("datasets/processed/manual_decentralization_visual"),
        help="Output directory.",
    )
    parser.add_argument(
        "--methods",
        type=str,
        default="harmonic,azimuth_equalization,agc",
        help="Comma separated methods from harmonic,azimuth_equalization,agc.",
    )
    args = parser.parse_args()

    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    for method in methods:
        if method not in SUPPORTED_METHODS:
            raise ValueError(f"Unsupported method: {method}")

    input_path = args.input.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")
    output_root = args.out_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    original_rgb = np.asarray(Image.open(input_path).convert("RGB"), dtype=np.float32)
    summaries = []
    for method in methods:
        summaries.append(
            run_single_method(
                method=method,
                original_rgb=original_rgb,
                input_path=input_path,
                output_root=output_root,
            )
        )
    grid_path = _build_grid(output_root, methods)

    print(f"Input: {input_path}")
    for item in summaries:
        print(f"[{item['method']}]")
        print(f"  fixed:   {item['output_files']['fixed']}")
        print(f"  compare: {item['output_files']['compare_side_by_side']}")
        print(f"  diff:    {item['output_files']['diff_abs']}")
        print(f"  metrics: {item['quality_metrics']}")
    print(f"Grid: {grid_path}")


if __name__ == "__main__":
    main()
