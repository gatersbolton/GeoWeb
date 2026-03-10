from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from borehole_groove_cleaner.cli import main
from borehole_groove_cleaner.io import auto_crop_bbox


def _write_test_image(path: Path) -> None:
    height, width = 96, 64
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    image = 0.5 + 0.18 * np.sin(2.0 * np.pi * (2.0 * y + 0.4 * x))
    image[:, 20:24] -= 0.20
    panel = np.clip(np.rint(image * 255.0), 0, 255).astype(np.uint8)
    canvas = np.full((height, width + 20), 255, dtype=np.uint8)
    canvas[:, 10:-10] = panel
    Image.fromarray(canvas).save(path)


def test_cli_clean_and_batch_outputs(tmp_path: Path) -> None:
    single_input = tmp_path / "single.png"
    _write_test_image(single_input)
    single_out = tmp_path / "single_out"
    assert main([str(single_input), "--out", str(single_out), "--mode", "clean", "--auto-crop"]) == 0
    assert (single_out / "clean.png").exists()
    assert (single_out / "mask.png").exists()
    assert (single_out / "overlay.png").exists()
    assert (single_out / "diff.png").exists()
    assert (single_out / "tracks.json").exists()
    assert (single_out / "debug").exists()

    batch_input = tmp_path / "batch"
    batch_input.mkdir()
    _write_test_image(batch_input / "a.png")
    _write_test_image(batch_input / "b.png")
    batch_out = tmp_path / "batch_out"
    assert main([str(batch_input), "--out", str(batch_out), "--mode", "batch", "--auto-crop"]) == 0
    assert (batch_out / "a" / "clean.png").exists()
    assert (batch_out / "b" / "tracks.json").exists()


def test_auto_crop_does_not_overcrop_real_sample() -> None:
    image = np.asarray(Image.open("tests/groovemask_test.png"))
    x0, x1, y0, y1 = auto_crop_bbox(image)
    assert y0 == 0
    assert y1 == image.shape[0]
    assert x1 - x0 >= int(round(image.shape[1] * 0.60))
