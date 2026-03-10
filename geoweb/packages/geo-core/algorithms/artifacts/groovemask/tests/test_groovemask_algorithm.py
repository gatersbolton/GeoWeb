import numpy as np
import pytest

from algorithms.artifacts.groovemask.algorithm import GrooveMaskArtifactRemoval
from algorithms.core.data_models import InputFrame, RunContext
from algorithms.core.exceptions import InputValidationError


def _build_frame(data: np.ndarray, *, layout: str = "HW", value_range: list[float] | None = None) -> InputFrame:
    return InputFrame(
        data=np.asarray(data, dtype=np.float32),
        data_layout=layout,
        value_range=value_range or [0.0, 1.0],
        source_meta={"input_format": "npy"},
    )


def _wraparound_case(height: int = 128, width: int = 96) -> np.ndarray:
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    clean = 0.55 + 0.15 * np.sin(2.0 * np.pi * (3.0 * y + 0.5 * x))
    clean += 0.05 * np.cos(2.0 * np.pi * (2.0 * x - 0.8 * y))
    artifact = np.clip(clean, 0.0, 1.0)
    artifact[:, [0, 1, width - 2, width - 1]] = np.clip(
        artifact[:, [0, 1, width - 2, width - 1]] - 0.22,
        0.0,
        1.0,
    )
    return artifact.astype(np.float32)


def test_groovemask_default_config_has_three_levels() -> None:
    algorithm = GrooveMaskArtifactRemoval()
    config = algorithm.get_default_config()
    assert "safe" in config
    assert "advanced" in config
    assert "experimental" in config
    assert config["safe"]["backend"] == "groovemask_inpaint"


def test_groovemask_runs_and_preserves_shape_and_dtype() -> None:
    algorithm = GrooveMaskArtifactRemoval()
    frame = _build_frame(_wraparound_case())
    output = algorithm.run(frame, algorithm.get_default_config(), RunContext(job_id="gm1", step_index=1))
    assert output.result.shape == frame.data.shape
    assert output.result.dtype == np.float32
    assert np.isfinite(output.result).all()
    assert output.run_report.algo_id == "artifact.groovemask.v1"


def test_groovemask_detect_only_can_save_auxiliary_assets(tmp_path) -> None:
    algorithm = GrooveMaskArtifactRemoval()
    frame = _build_frame(_wraparound_case())
    config = algorithm.get_default_config()
    config["safe"]["mode"] = "detect-only"
    config["experimental"]["enable_preview_assets"] = True
    output = algorithm.run(
        frame,
        config,
        RunContext(job_id="gm2", step_index=1, output_dir=str(tmp_path)),
    )
    asset_names = {path.split("\\")[-1].split("/")[-1] for path in output.preview_assets}
    assert "mask.png" in asset_names
    assert "overlay.png" in asset_names
    assert "diff.png" in asset_names
    assert output.artifact_detected["groovemask"] >= 0.0


def test_groovemask_accepts_rgb_hwc_input() -> None:
    algorithm = GrooveMaskArtifactRemoval()
    gray = _wraparound_case(height=64, width=48)
    rgb = np.stack([gray, gray * 0.85 + 0.05, gray * 0.7 + 0.1], axis=-1).astype(np.float32)
    frame = _build_frame(rgb, layout="HWC", value_range=[0.0, 1.0])
    output = algorithm.run(frame, algorithm.get_default_config(), RunContext(job_id="gm3", step_index=1))
    assert output.result.shape == frame.data.shape
    assert float(output.result.max()) <= 1.0 + 1.0e-6


def test_groovemask_rejects_empty_input() -> None:
    algorithm = GrooveMaskArtifactRemoval()
    frame = _build_frame(np.array([], dtype=np.float32))
    with pytest.raises(InputValidationError):
        algorithm.validate_input(frame, algorithm.get_default_config())
