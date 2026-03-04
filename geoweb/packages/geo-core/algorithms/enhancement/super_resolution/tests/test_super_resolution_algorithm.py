import numpy as np
import pytest

from algorithms.core.data_models import InputFrame, RunContext
from algorithms.core.exceptions import InputValidationError
from algorithms.enhancement.super_resolution.algorithm import SuperResolutionEnhancement


def _build_frame(data: np.ndarray) -> InputFrame:
    return InputFrame(data=data, source_meta={"input_format": "npy"})


def test_super_resolution_default_config_has_three_levels() -> None:
    algorithm = SuperResolutionEnhancement()
    config = algorithm.get_default_config()
    assert "safe" in config
    assert "advanced" in config
    assert "experimental" in config


def test_super_resolution_returns_identity_output() -> None:
    algorithm = SuperResolutionEnhancement()
    frame = _build_frame(np.array([[9, 10], [11, 12]], dtype=np.float32))
    output = algorithm.run(frame, algorithm.get_default_config(), RunContext(job_id="j3", step_index=1))
    assert np.array_equal(output.result, frame.data)
    assert output.result.dtype == np.float32


def test_super_resolution_rejects_empty_input() -> None:
    algorithm = SuperResolutionEnhancement()
    frame = _build_frame(np.array([], dtype=np.float32))
    with pytest.raises(InputValidationError):
        algorithm.validate_input(frame, algorithm.get_default_config())

