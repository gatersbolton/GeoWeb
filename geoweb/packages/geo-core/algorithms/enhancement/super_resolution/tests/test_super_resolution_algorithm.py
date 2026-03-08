from pathlib import Path

import numpy as np
import pytest

from algorithms.core.data_models import InputFrame, RunContext
from algorithms.core.exceptions import InputValidationError
from algorithms.enhancement.super_resolution import algorithm as superres_algorithm
from algorithms.enhancement.super_resolution.config_schema import parse_config


def _build_frame(data: np.ndarray) -> InputFrame:
    return InputFrame(data=data, source_meta={"input_format": "npy"})


def test_super_resolution_default_config_has_three_levels() -> None:
    algorithm = superres_algorithm.SuperResolutionEnhancement()
    config = algorithm.get_default_config()
    assert "safe" in config
    assert "advanced" in config
    assert "experimental" in config
    assert config["safe"]["model_name"] == "RealESRGAN_x4plus"
    assert config["advanced"]["outscale"] == 1.0


def test_super_resolution_legacy_config_is_normalized() -> None:
    config = parse_config(
        {
            "advanced": {"upscale_ratio": 2.0},
            "experimental": {"use_tile_mode": True},
        }
    )
    assert config.advanced.outscale == 2.0
    assert config.advanced.tile == 256


def test_super_resolution_run_uses_backend_and_returns_float32(monkeypatch: pytest.MonkeyPatch) -> None:
    algorithm = superres_algorithm.SuperResolutionEnhancement()
    frame = _build_frame(np.array([[0, 32], [96, 255]], dtype=np.float32))
    config = algorithm.get_default_config()
    config["advanced"]["outscale"] = 2.0

    class _FakeRunner:
        device_label = "cpu"

        def enhance(self, image, *, outscale: float, alpha_upsampler: str) -> np.ndarray:
            factor = max(int(round(outscale)), 1)
            return np.repeat(np.repeat(image, factor, axis=0), factor, axis=1)

    monkeypatch.setattr(superres_algorithm, "resolve_model_path", lambda *args, **kwargs: Path("mock.pth"))
    monkeypatch.setattr(superres_algorithm, "get_realesrgan_runner", lambda **kwargs: _FakeRunner())

    output = algorithm.run(frame, config, RunContext(job_id="j3", step_index=1))
    assert output.result.shape == (4, 4)
    assert output.result.dtype == np.float32
    assert output.quality_metrics["applied_outscale"] == 2.0
    assert "running Real-ESRGAN on CPU" in output.run_report.warnings[0]


def test_super_resolution_rejects_empty_input() -> None:
    algorithm = superres_algorithm.SuperResolutionEnhancement()
    frame = _build_frame(np.array([], dtype=np.float32))
    with pytest.raises(InputValidationError):
        algorithm.validate_input(frame, algorithm.get_default_config())


def test_super_resolution_rejects_unsupported_channel_count() -> None:
    algorithm = superres_algorithm.SuperResolutionEnhancement()
    frame = InputFrame(
        data=np.zeros((8, 8, 2), dtype=np.float32),
        data_layout="HWC",
        source_meta={"input_format": "npy"},
    )
    with pytest.raises(InputValidationError):
        algorithm.validate_input(frame, algorithm.get_default_config())
