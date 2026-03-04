import numpy as np
import pytest

from algorithms.artifacts.stick_pull.algorithm import StickPullArtifactRemoval
from algorithms.core.data_models import InputFrame, RunContext
from algorithms.core.exceptions import InputValidationError


def _build_frame(data: np.ndarray) -> InputFrame:
    return InputFrame(data=data, source_meta={"input_format": "npy"})


def test_stick_pull_default_config_has_three_levels() -> None:
    algorithm = StickPullArtifactRemoval()
    config = algorithm.get_default_config()
    assert "safe" in config
    assert "advanced" in config
    assert "experimental" in config
    assert "power" in config["advanced"]


def test_stick_pull_runs_and_preserves_shape_and_dtype() -> None:
    algorithm = StickPullArtifactRemoval()
    frame = _build_frame(np.array([[1, 2, 3], [4, 5, 6], [4, 3, 2]], dtype=np.float32))
    output = algorithm.run(frame, algorithm.get_default_config(), RunContext(job_id="j1", step_index=1))
    assert output.result.shape == frame.data.shape
    assert output.result.dtype == np.float32
    assert np.isfinite(output.result).all()
    assert output.run_report.algo_id == "artifact.stick_pull.v1"


def test_stick_pull_can_fallback_to_identity_when_disabled() -> None:
    algorithm = StickPullArtifactRemoval()
    frame = _build_frame(np.array([[1, 2], [3, 4]], dtype=np.float32))
    config = algorithm.get_default_config()
    config["safe"]["enable"] = False
    output = algorithm.run(frame, config, RunContext(job_id="j2", step_index=1))
    assert np.array_equal(output.result, frame.data)
    assert output.artifact_detected["stick_pull"] == 0.0


def test_stick_pull_accepts_external_speed_profile_csv(tmp_path) -> None:
    algorithm = StickPullArtifactRemoval()
    frame = _build_frame(np.array([[1, 3], [2, 8], [3, 2], [4, 6]], dtype=np.float32))
    speed_csv = tmp_path / "speed.csv"
    speed_csv.write_text("row_index,v_norm\n0,0.2\n1,0.3\n2,0.6\n3,0.9\n", encoding="utf-8")

    config = algorithm.get_default_config()
    config["safe"]["speed_profile_csv"] = str(speed_csv)
    config["safe"]["speed_column"] = "v_norm"
    output = algorithm.run(frame, config, RunContext(job_id="j3", step_index=1))

    assert output.result.shape == frame.data.shape
    assert np.isfinite(output.result).all()


def test_stick_pull_rejects_empty_input() -> None:
    algorithm = StickPullArtifactRemoval()
    frame = _build_frame(np.array([], dtype=np.float32))
    with pytest.raises(InputValidationError):
        algorithm.validate_input(frame, algorithm.get_default_config())
