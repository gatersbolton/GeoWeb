from __future__ import annotations

from pathlib import Path

from algorithms.artifacts.decentralization.algorithm import DecentralizationArtifactRemoval
from algorithms.artifacts.stick_pull.algorithm import StickPullArtifactRemoval
from algorithms.core.registry import AlgorithmRegistry, load_capability_file
from algorithms.enhancement.super_resolution.algorithm import SuperResolutionEnhancement


def build_default_registry() -> AlgorithmRegistry:
    registry = AlgorithmRegistry()
    package_root = Path(__file__).resolve().parent

    stick_pull = StickPullArtifactRemoval()
    registry.register(
        stick_pull,
        load_capability_file(package_root / "artifacts" / "stick_pull" / "capability.json"),
    )

    decentralization = DecentralizationArtifactRemoval()
    registry.register(
        decentralization,
        load_capability_file(package_root / "artifacts" / "decentralization" / "capability.json"),
    )

    super_resolution = SuperResolutionEnhancement()
    registry.register(
        super_resolution,
        load_capability_file(
            package_root / "enhancement" / "super_resolution" / "capability.json"
        ),
    )

    return registry
