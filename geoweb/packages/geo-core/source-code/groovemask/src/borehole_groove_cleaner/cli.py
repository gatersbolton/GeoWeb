from __future__ import annotations

import argparse
import json
from pathlib import Path

from borehole_groove_cleaner.api import clean_grooves
from borehole_groove_cleaner.config import GrooveMaskConfig, build_config
from borehole_groove_cleaner.io import discover_images, save_result_bundle


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="borehole-groove-cleaner")
    parser.add_argument("input", help="Input image path or input directory for batch mode.")
    parser.add_argument("--out", required=True, help="Output directory.")
    parser.add_argument("--mode", default=None, choices=["detect-only", "review", "clean", "batch"])
    parser.add_argument(
        "--backend",
        default=None,
        choices=["groovemask_inpaint", "fourier_soft_notch", "variational_decompose"],
    )
    parser.add_argument("--roi", nargs=4, type=int, metavar=("X0", "X1", "Y0", "Y1"))
    parser.add_argument("--polarity", default=None, choices=["dark", "bright", "auto"])
    parser.add_argument("--config", default=None, help="Optional YAML config.")
    parser.add_argument("--auto-crop", dest="auto_crop", action="store_true")
    parser.add_argument("--no-auto-crop", dest="auto_crop", action="store_false")
    parser.set_defaults(auto_crop=None)
    return parser


def _config_from_args(args: argparse.Namespace) -> GrooveMaskConfig:
    overrides = {
        "mode": args.mode,
        "backend": args.backend,
        "roi": tuple(args.roi) if args.roi is not None else None,
        "polarity": args.polarity,
        "auto_crop": args.auto_crop,
    }
    return build_config(config_path=args.config, overrides=overrides)


def _run_single(input_path: Path, out_dir: Path, cfg: GrooveMaskConfig) -> dict[str, str]:
    result = clean_grooves(str(input_path), cfg)
    artifacts = save_result_bundle(result, out_dir)
    summary = {
        "input": str(input_path),
        "backend": cfg.backend,
        "mode": cfg.mode,
        "track_count": len(result.debug_payload.get("tracks_serialized", [])),
        "artifacts": artifacts,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifacts


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cfg = _config_from_args(args)
    input_path = Path(args.input)
    out_dir = Path(args.out)

    if cfg.mode == "batch":
        images = discover_images(input_path)
        if not images:
            raise SystemExit(f"No images found under {input_path}")
        for image_path in images:
            target_dir = out_dir / image_path.stem
            batch_cfg = GrooveMaskConfig(**{key: value for key, value in cfg.as_dict().items() if key != "pad_x" and key != "mode"})
            _run_single(image_path, target_dir, batch_cfg)
        return 0

    if not input_path.is_file():
        raise SystemExit("Single-image mode requires an input image file.")
    out_dir.mkdir(parents=True, exist_ok=True)
    _run_single(input_path, out_dir, cfg)
    return 0
