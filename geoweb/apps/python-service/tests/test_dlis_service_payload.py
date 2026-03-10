from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from python_service.services.dlis import inspect_dlis_payload, render_dlis_payload


def _sample_dlis_path() -> Path:
    path = (
        APP_DIR.parents[1]
        / "packages"
        / "geo-core"
        / "source-code"
        / "dlis"
        / "raw"
        / "ST1_20210305_DEV_ATV_up_main.dlis"
    )
    if not path.exists():
        pytest.skip("DLIS sample file is not available in this workspace.")
    return path


def test_inspect_dlis_payload_returns_summary() -> None:
    payload = inspect_dlis_payload(_sample_dlis_path(), source_label="sample.dlis")
    assert payload["source"] == "sample.dlis"
    assert payload["summary"]["defaults"]["amplitude_channel_ref"] == "F0000:AMPLITUDE-NM"


def test_render_dlis_payload_returns_frontend_ready_outputs(tmp_path: Path) -> None:
    payload = render_dlis_payload(
        file_path=_sample_dlis_path(),
        input_name="sample.dlis",
        output_dir=tmp_path,
        session_id="dlis-api-test",
        options={
            "depth_min": 300.0,
            "depth_max": 300.5,
            "generate_atv": True,
            "generate_rose": False,
            "pixel_scale": 1,
        },
    )

    assert payload["source"] == "sample.dlis"
    assert len(payload["outputs"]) == 3
    assert payload["outputs"][0]["file_names"]["image"].endswith(".png")
    assert payload["outputs"][0]["file_names"]["npz"].endswith(".npz")
    assert payload["outputs"][0]["output_image"].startswith("data:image/png;base64,")
