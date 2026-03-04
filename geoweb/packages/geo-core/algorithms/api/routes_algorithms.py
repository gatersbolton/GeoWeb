from __future__ import annotations

from fastapi import APIRouter

from algorithms.api.runtime import REGISTRY
from algorithms.api.schemas import AlgorithmInfoSchema

router = APIRouter()


@router.get("/algorithms", response_model=list[AlgorithmInfoSchema])
def get_algorithms() -> list[AlgorithmInfoSchema]:
    result = []
    for descriptor in REGISTRY.list_descriptors():
        algorithm = descriptor.algorithm
        result.append(
            AlgorithmInfoSchema(
                algo_id=algorithm.algo_id,
                version=algorithm.version,
                capability=descriptor.capability,
                default_config=algorithm.get_default_config(),
            )
        )
    return result

