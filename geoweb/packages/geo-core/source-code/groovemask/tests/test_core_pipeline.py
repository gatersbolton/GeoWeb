from __future__ import annotations

import time

import numpy as np

from borehole_groove_cleaner import GrooveMaskConfig, clean_grooves
from borehole_groove_cleaner.qc import synth_metrics
from borehole_groove_cleaner.synth import generate_synthetic_case


def _wraparound_case(height: int = 128, width: int = 96) -> np.ndarray:
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    clean = 0.55 + 0.15 * np.sin(2.0 * np.pi * (3.0 * y + 0.5 * x))
    clean += 0.05 * np.cos(2.0 * np.pi * (2.0 * x - 0.8 * y))
    artifact = np.clip(clean, 0.0, 1.0)
    artifact[:, [0, 1, width - 2, width - 1]] = np.clip(artifact[:, [0, 1, width - 2, width - 1]] - 0.22, 0.0, 1.0)
    return artifact.astype(np.float32)


def test_wraparound_groove_forms_single_track() -> None:
    cfg = GrooveMaskConfig(mode="detect-only", polarity="dark")
    result = clean_grooves(_wraparound_case(), cfg)
    tracks = result.debug_payload["tracks_serialized"]
    assert len(tracks) == 1
    assert result.mask[:, :2].any()
    assert result.mask[:, -2:].any()


def test_broad_shading_rejected() -> None:
    height, width = 128, 120
    image = np.full((height, width), 0.6, dtype=np.float32)
    image[:, 30:70] -= 0.25
    result = clean_grooves(image.astype(np.float32), GrooveMaskConfig(mode="detect-only", polarity="dark"))
    assert result.debug_payload["rejected_broad"]
    assert result.debug_payload["tracks_serialized"] == []


def test_default_backend_preserves_unmasked_and_meets_quality_targets() -> None:
    case = generate_synthetic_case(height=200, width=1200, seed=25, groove_count=(1, 1))
    cfg = GrooveMaskConfig(mode="clean", polarity="auto")
    started = time.perf_counter()
    result = clean_grooves(case.artifact, cfg)
    duration = time.perf_counter() - started
    metrics = synth_metrics(case.clean, case.artifact, result.clean_image.astype(np.float32), case.mask, result.mask, cfg)

    outside = result.mask == 0
    assert np.allclose(result.clean_image[outside], case.artifact[outside], atol=1.0e-6)
    assert duration < 2.0
    assert metrics["mask_iou"] > 0.10
    assert metrics["outside_mask_ssim"] > 0.95
    assert metrics["column_anomaly_reduction"] > 0.0
    assert metrics["stripe_spectral_energy_reduction"] > 0.0


def test_experimental_backends_return_stable_shapes() -> None:
    case = generate_synthetic_case(height=96, width=256, seed=9, groove_count=(1, 1))
    for backend in ("fourier_soft_notch", "variational_decompose"):
        result = clean_grooves(case.artifact, GrooveMaskConfig(mode="clean", backend=backend, polarity="auto"))
        assert result.clean_image.shape == case.artifact.shape
        assert result.mask.sum() == 0
        assert result.debug_payload["tracks_serialized"] == []


def test_rgba_roundtrip_keeps_alpha() -> None:
    artifact = _wraparound_case(height=64, width=48)
    rgb = np.clip(np.rint(np.stack([artifact, artifact * 0.8 + 0.1, artifact * 0.6 + 0.2], axis=-1) * 255.0), 0, 255).astype(np.uint8)
    alpha = np.full((artifact.shape[0], artifact.shape[1], 1), 127, dtype=np.uint8)
    rgba = np.concatenate([rgb, alpha], axis=2)
    result = clean_grooves(rgba, GrooveMaskConfig(mode="clean", polarity="dark"))
    assert result.clean_image.shape == rgba.shape
    assert np.array_equal(result.clean_image[..., 3], rgba[..., 3])
