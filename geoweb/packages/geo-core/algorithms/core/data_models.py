from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np


@dataclass
class InputFrame:
    data: np.ndarray
    data_layout: str = "HW"
    dtype: str = "float32"
    value_range: list[float] = field(default_factory=lambda: [0.0, 1.0])
    spatial_meta: dict[str, Any] = field(default_factory=dict)
    source_meta: dict[str, Any] = field(default_factory=dict)
    artifact_tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.data, np.ndarray):
            raise TypeError("InputFrame.data must be np.ndarray")
        if self.data.dtype != np.float32:
            self.data = self.data.astype(np.float32)
        self.dtype = str(self.data.dtype)


@dataclass
class RunContext:
    job_id: str
    step_index: int
    created_by: str = "system"
    service_version: str = "v1"
    commit_hash: str | None = None
    output_dir: str | None = None


@dataclass
class AlgorithmRunReport:
    algo_id: str
    algo_version: str
    config_hash: str
    runtime_ms: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutputFrame:
    result: np.ndarray
    quality_metrics: dict[str, float]
    artifact_detected: dict[str, float]
    run_report: AlgorithmRunReport
    preview_assets: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.result, np.ndarray):
            raise TypeError("OutputFrame.result must be np.ndarray")
        if self.result.dtype != np.float32:
            self.result = self.result.astype(np.float32)


@dataclass
class PipelineStep:
    algo_id: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    final_output: OutputFrame
    step_outputs: list[OutputFrame]

