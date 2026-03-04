from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from algorithms.artifacts.stick_pull.algorithm import StickPullArtifactRemoval
from algorithms.core.data_models import InputFrame, RunContext


def to_uint8(image: np.ndarray) -> np.ndarray:
    arr = np.asarray(image, dtype=np.float32)
    arr = np.clip(arr, 0.0, 255.0)
    return arr.astype(np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual visual check for stick-pull artifact correction.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("algorithms/artifacts/stick_pull/tests/stick_pull.png"),
        help="Input image path.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("datasets/processed/manual_stick_pull_visual"),
        help="Output directory.",
    )
    parser.add_argument(
        "--speed-csv",
        type=Path,
        default=None,
        help="Optional speed profile csv path.",
    )
    args = parser.parse_args()

    input_path = args.input.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    original = np.asarray(Image.open(input_path).convert("RGB"), dtype=np.float32)

    algorithm = StickPullArtifactRemoval()
    config = algorithm.get_default_config()
    if args.speed_csv is not None:
        config["safe"]["speed_profile_csv"] = str(args.speed_csv.resolve())
    config["experimental"]["enable_preview_assets"] = True
    config["experimental"]["preview_image_ext"] = "png"

    frame = InputFrame(
        data=original,
        data_layout="HWC",
        value_range=[0.0, 255.0],
        source_meta={
            "input_format": "png",
            "original_file_uri": str(input_path),
        },
    )
    context = RunContext(
        job_id="manual_stick_pull",
        step_index=1,
        created_by="manual_visual_check",
        service_version="manual",
        output_dir=str(out_dir),
    )

    output = algorithm.run(frame, config, context)
    fixed = np.asarray(output.result, dtype=np.float32)

    original_u8 = to_uint8(original)
    fixed_u8 = to_uint8(fixed)
    diff_u8 = np.abs(fixed_u8.astype(np.int16) - original_u8.astype(np.int16)).astype(np.uint8)
    side_by_side = np.concatenate([original_u8, fixed_u8], axis=1)

    original_path = out_dir / "original.png"
    fixed_path = out_dir / "fixed.png"
    compare_path = out_dir / "compare_side_by_side.png"
    diff_path = out_dir / "diff_abs.png"

    Image.fromarray(original_u8).save(original_path)
    Image.fromarray(fixed_u8).save(fixed_path)
    Image.fromarray(side_by_side).save(compare_path)
    Image.fromarray(diff_u8).save(diff_path)

    print(f"Input:      {input_path}")
    print(f"Original:   {original_path}")
    print(f"Fixed:      {fixed_path}")
    print(f"Compare:    {compare_path}")
    print(f"Diff(abs):  {diff_path}")
    print(f"Metrics:    {output.quality_metrics}")
    print(f"Warnings:   {output.run_report.warnings}")
    if output.preview_assets:
        print(f"Preview(s): {output.preview_assets}")


if __name__ == "__main__":
    main()
