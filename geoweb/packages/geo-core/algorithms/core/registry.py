from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from algorithms.core.exceptions import InvalidAlgorithmParamsError
from algorithms.core.interfaces import ArtifactRemovalAlgorithm, EnhancementAlgorithm

AlgorithmLike = ArtifactRemovalAlgorithm | EnhancementAlgorithm


@dataclass
class AlgorithmDescriptor:
    algorithm: AlgorithmLike
    capability: dict[str, Any]


class AlgorithmRegistry:
    def __init__(self) -> None:
        self._algorithms: dict[str, AlgorithmDescriptor] = {}

    def register(self, algorithm: AlgorithmLike, capability: dict[str, Any] | None = None) -> None:
        if algorithm.algo_id in self._algorithms:
            raise InvalidAlgorithmParamsError(f"Duplicate algo_id: {algorithm.algo_id}")
        self._algorithms[algorithm.algo_id] = AlgorithmDescriptor(
            algorithm=algorithm,
            capability=capability or {},
        )

    def get(self, algo_id: str) -> AlgorithmLike:
        descriptor = self._algorithms.get(algo_id)
        if descriptor is None:
            raise InvalidAlgorithmParamsError(f"Algorithm is not registered: {algo_id}")
        return descriptor.algorithm

    def describe(self, algo_id: str) -> AlgorithmDescriptor:
        descriptor = self._algorithms.get(algo_id)
        if descriptor is None:
            raise InvalidAlgorithmParamsError(f"Algorithm is not registered: {algo_id}")
        return descriptor

    def list_descriptors(self) -> list[AlgorithmDescriptor]:
        return list(self._algorithms.values())

    def list_algo_ids(self) -> list[str]:
        return list(self._algorithms.keys())


def load_capability_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

