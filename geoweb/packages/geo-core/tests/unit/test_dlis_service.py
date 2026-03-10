from pathlib import Path

import pytest

import numpy as np

from algorithms.dlis.service import _prepare_image, inspect_dlis_file, render_dlis_outputs


def _sample_dlis_path() -> Path:
    path = (
        Path(__file__).resolve().parents[2]
        / "source-code"
        / "dlis"
        / "raw"
        / "ST1_20210305_DEV_ATV_up_main.dlis"
    )
    if not path.exists():
        pytest.skip("DLIS sample file is not available in this workspace.")
    return path


def test_inspect_dlis_file_detects_default_channels() -> None:
    summary = inspect_dlis_file(_sample_dlis_path())

    assert summary["defaults"]["amplitude_channel_ref"] == "F0000:AMPLITUDE-NM"
    assert summary["defaults"]["traveltime_channel_ref"] == "F0000:TRAVELTIME-NM"
    assert summary["defaults"]["angle_channel_ref"] in {"F0000:AZIMUTH", "F0002:AZIMUT"}
    assert summary["defaults"]["depth_min"] is not None
    assert summary["defaults"]["depth_max"] is not None
    assert len(summary["frames"]) >= 1
    assert len(summary["channel_options"]) >= 3


def test_render_dlis_outputs_generates_previews_and_npz(tmp_path: Path) -> None:
    rendered = render_dlis_outputs(
        path=_sample_dlis_path(),
        job_id="dlis-test",
        output_dir=tmp_path,
        options={
            "depth_min": 300.0,
            "depth_max": 300.5,
            "pixel_scale": 1,
            "rose_bins": 18,
            "generate_atv": True,
            "generate_rose": True,
        },
    )

    assert len(rendered["outputs"]) == 4
    output_titles = {item["title"] for item in rendered["outputs"]}
    assert "DLIS 振幅 ATV 图" in output_titles
    assert "DLIS 走时 ATV 图" in output_titles
    assert "DLIS 振幅/走时拼接图" in output_titles
    assert "DLIS 方位玫瑰图" in output_titles

    for output in rendered["outputs"]:
        assert Path(output["image_path"]).exists()
        assert Path(output["npz_path"]).exists()

    assert Path(rendered["manifest"]["path"]).exists()
    assert rendered["manifest"]["name"] in rendered["download_map"]


def test_prepare_image_invert_flips_amplitude_tone_mapping() -> None:
    data = np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32)

    normal, _ = _prepare_image(
        data,
        depth=None,
        clip_low=0.0,
        clip_high=100.0,
        gamma=1.0,
        invert=False,
        depth_min=None,
        depth_max=None,
    )
    inverted, _ = _prepare_image(
        data,
        depth=None,
        clip_low=0.0,
        clip_high=100.0,
        gamma=1.0,
        invert=True,
        depth_min=None,
        depth_max=None,
    )

    assert np.allclose(inverted, 1.0 - normal)
