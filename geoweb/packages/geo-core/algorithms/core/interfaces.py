from __future__ import annotations

from typing import Protocol

from algorithms.core.data_models import InputFrame, OutputFrame, RunContext


class ArtifactRemovalAlgorithm(Protocol):
    algo_id: str
    version: str

    def validate_input(self, input_data: InputFrame, config: dict) -> None:
        ...

    def run(self, input_data: InputFrame, config: dict, context: RunContext) -> OutputFrame:
        ...

    def get_default_config(self) -> dict:
        ...


class EnhancementAlgorithm(Protocol):
    algo_id: str
    version: str

    def validate_input(self, input_data: InputFrame, config: dict) -> None:
        ...

    def run(self, input_data: InputFrame, config: dict, context: RunContext) -> OutputFrame:
        ...

    def get_default_config(self) -> dict:
        ...
