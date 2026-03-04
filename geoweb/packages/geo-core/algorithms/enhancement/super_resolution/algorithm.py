from __future__ import annotations

import time

import numpy as np

from algorithms.core.data_models import AlgorithmRunReport, InputFrame, OutputFrame, RunContext
from algorithms.core.exceptions import InputValidationError
from algorithms.core.utils.logging import hash_config
from algorithms.enhancement.super_resolution.config_schema import default_config, parse_config


class SuperResolutionEnhancement:
    algo_id = "enhancement.super_resolution.v1"
    version = "1.0.0"

    def validate_input(self, input_data: InputFrame, config: dict) -> None:
        parse_config(config)
        if input_data.data.size == 0:
            raise InputValidationError("Input data is empty.")

    def run(self, input_data: InputFrame, config: dict, context: RunContext) -> OutputFrame:
        parsed = parse_config(config)
        if hasattr(parsed, "model_dump"):
            parsed_config = parsed.model_dump()
        else:
            parsed_config = parsed.dict()

        start = time.perf_counter()
        result = np.asarray(input_data.data, dtype=np.float32).copy()
        runtime_ms = (time.perf_counter() - start) * 1000

        report = AlgorithmRunReport(
            algo_id=self.algo_id,
            algo_version=self.version,
            config_hash=hash_config(parsed_config),
            runtime_ms=runtime_ms,
            warnings=["placeholder identity pass-through"],
        )
        return OutputFrame(
            result=result,
            quality_metrics={"sharpness_delta": 0.0, "contrast_delta": 0.0},
            artifact_detected={},
            run_report=report,
            preview_assets=[],
        )

    def get_default_config(self) -> dict:
        return default_config()

