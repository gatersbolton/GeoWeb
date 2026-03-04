from __future__ import annotations

from copy import deepcopy

from algorithms.core.data_models import InputFrame, PipelineResult, PipelineStep, RunContext
from algorithms.core.exceptions import AlgorithmExecutionError
from algorithms.core.registry import AlgorithmRegistry
from algorithms.core.utils.metadata import append_algo_chain


class PipelineExecutor:
    def __init__(self, registry: AlgorithmRegistry) -> None:
        self._registry = registry

    def run(
        self,
        input_frame: InputFrame,
        steps: list[PipelineStep],
        context: RunContext,
    ) -> PipelineResult:
        if not steps:
            raise AlgorithmExecutionError("Pipeline is empty.")

        current_input = deepcopy(input_frame)
        step_outputs = []
        for index, step in enumerate(steps, start=1):
            algorithm = self._registry.get(step.algo_id)
            effective_config = step.config or algorithm.get_default_config()
            step_context = RunContext(
                job_id=context.job_id,
                step_index=index,
                created_by=context.created_by,
                service_version=context.service_version,
                commit_hash=context.commit_hash,
                output_dir=context.output_dir,
            )
            algorithm.validate_input(current_input, effective_config)
            output_frame = algorithm.run(current_input, effective_config, step_context)
            step_outputs.append(output_frame)

            next_source_meta = append_algo_chain(current_input.source_meta, step.algo_id)
            current_input = InputFrame(
                data=output_frame.result.copy(),
                data_layout=current_input.data_layout,
                value_range=current_input.value_range[:],
                spatial_meta=deepcopy(current_input.spatial_meta),
                source_meta=next_source_meta,
                artifact_tags=list(output_frame.artifact_detected.keys()),
            )

        return PipelineResult(final_output=step_outputs[-1], step_outputs=step_outputs)

