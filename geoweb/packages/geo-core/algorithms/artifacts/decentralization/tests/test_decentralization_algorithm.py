import numpy as np
import pytest

from algorithms.artifacts.decentralization.algorithm import DecentralizationArtifactRemoval
from algorithms.core.data_models import InputFrame, RunContext
from algorithms.core.exceptions import InputValidationError


def _build_frame(data: np.ndarray) -> InputFrame:
    return InputFrame(data=data, source_meta={"input_format": "npy"})


def _low_order_harmonic_energy(matrix: np.ndarray) -> float:
    depth, azimuth = matrix.shape
    theta = 2 * np.pi * np.arange(azimuth, dtype=np.float32) / azimuth
    c1 = np.cos(theta)
    s1 = np.sin(theta)
    c2 = np.cos(2 * theta)
    s2 = np.sin(2 * theta)
    scale = 2.0 / azimuth
    a1 = scale * matrix @ c1
    b1 = scale * matrix @ s1
    a2 = scale * matrix @ c2
    b2 = scale * matrix @ s2
    return float(np.mean(a1**2 + b1**2 + a2**2 + b2**2))


def test_decentralization_default_config_has_three_levels() -> None:
    algorithm = DecentralizationArtifactRemoval()
    config = algorithm.get_default_config()
    assert "safe" in config
    assert "advanced" in config
    assert "experimental" in config
    assert config["safe"]["method"] == "harmonic"


def test_decentralization_harmonic_reduces_low_order_background() -> None:
    algorithm = DecentralizationArtifactRemoval()
    depth, azimuth = 40, 64
    theta = 2 * np.pi * np.arange(azimuth, dtype=np.float32) / azimuth
    base = np.random.default_rng(42).normal(0.0, 0.2, size=(depth, azimuth)).astype(np.float32)
    bias = (2.0 * np.cos(theta) + 1.5 * np.sin(2 * theta)).astype(np.float32)
    image = base + bias[None, :]

    frame = _build_frame(image)
    config = algorithm.get_default_config()
    config["safe"]["method"] = "harmonic"
    output = algorithm.run(frame, config, RunContext(job_id="d1", step_index=1))

    before = _low_order_harmonic_energy(image)
    after = _low_order_harmonic_energy(output.result)
    assert after < before
    assert output.result.shape == image.shape


def test_decentralization_azimuth_equalization_reduces_column_bias() -> None:
    algorithm = DecentralizationArtifactRemoval()
    depth, azimuth = 60, 24
    image = np.ones((depth, azimuth), dtype=np.float32)
    image[:, 4] *= 3.0
    image[:, 10] *= 0.5
    frame = _build_frame(image)

    config = algorithm.get_default_config()
    config["safe"]["method"] = "azimuth_equalization"
    config["advanced"]["equalization_depth_window"] = 31
    output = algorithm.run(frame, config, RunContext(job_id="d2", step_index=1))

    before = float(np.std(np.median(image, axis=0)))
    after = float(np.std(np.median(output.result, axis=0)))
    assert after < before


def test_decentralization_agc_reduces_rms_variation_along_depth() -> None:
    algorithm = DecentralizationArtifactRemoval()
    depth, azimuth = 80, 16
    amp = np.linspace(0.2, 2.0, depth, dtype=np.float32)[:, None]
    signal = amp * np.sin(np.linspace(0, 10 * np.pi, depth, dtype=np.float32)[:, None])
    image = np.repeat(signal, azimuth, axis=1).astype(np.float32)
    frame = _build_frame(image)

    config = algorithm.get_default_config()
    config["safe"]["method"] = "agc"
    config["advanced"]["agc_axis"] = "depth"
    config["advanced"]["agc_window"] = 21
    config["advanced"]["agc_preserve_row_mean"] = False
    output = algorithm.run(frame, config, RunContext(job_id="d3", step_index=1))

    before_rms = np.sqrt(np.mean(image**2, axis=1))
    after_rms = np.sqrt(np.mean(output.result**2, axis=1))
    assert float(np.std(after_rms)) < float(np.std(before_rms))


def test_decentralization_can_fallback_to_identity_when_disabled() -> None:
    algorithm = DecentralizationArtifactRemoval()
    frame = _build_frame(np.array([[5, 6], [7, 8]], dtype=np.float32))
    config = algorithm.get_default_config()
    config["safe"]["enable"] = False
    output = algorithm.run(frame, config, RunContext(job_id="d4", step_index=1))
    assert np.array_equal(output.result, frame.data)


def test_decentralization_rejects_empty_input() -> None:
    algorithm = DecentralizationArtifactRemoval()
    frame = _build_frame(np.array([], dtype=np.float32))
    with pytest.raises(InputValidationError):
        algorithm.validate_input(frame, algorithm.get_default_config())
