from __future__ import annotations

import asyncio
import json
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from fastapi import UploadFile
from PIL import Image

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from python_service.api.augmentation import run_augmentation


def _make_groove_png_bytes() -> bytes:
    height, width = 128, 96
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    image = 0.55 + 0.15 * np.sin(2.0 * np.pi * (3.0 * y + 0.5 * x))
    image += 0.05 * np.cos(2.0 * np.pi * (2.0 * x - 0.8 * y))
    image = np.clip(image, 0.0, 1.0)
    image[:, [0, 1, width - 2, width - 1]] = np.clip(
        image[:, [0, 1, width - 2, width - 1]] - 0.22,
        0.0,
        1.0,
    )
    panel = np.clip(np.rint(image * 255.0), 0, 255).astype(np.uint8)
    buffer = BytesIO()
    Image.fromarray(panel).save(buffer, format="PNG")
    return buffer.getvalue()


def test_augmentation_run_groovemask_returns_auxiliary_outputs() -> None:
    upload = UploadFile(
        filename="groove.png",
        file=BytesIO(_make_groove_png_bytes()),
    )
    response = asyncio.run(
        run_augmentation(
            algorithm="groovemask",
            config_json=json.dumps({"safe": {"mode": "detect-only"}}),
            image_file=upload,
            use_demo=None,
        )
    )

    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["algo_id"] == "artifact.groovemask.v1"
    assert payload["outputs"][0]["kind"] == "image"
    titles = {item["title"] for item in payload["outputs"]}
    assert "检测掩膜" in titles
    assert "掩膜叠加图" in titles
    assert "差异热力图" in titles
    assert payload["download_urls"]["image"].startswith("/api/augmentation/download/")
