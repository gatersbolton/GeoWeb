import numpy as np

from algorithms.bootstrap import build_default_registry
from algorithms.core.data_models import InputFrame, PipelineStep, RunContext
from algorithms.core.pipeline import PipelineExecutor


def test_pipeline_identity_flow() -> None:
    registry = build_default_registry()
    executor = PipelineExecutor(registry)
    input_data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    frame = InputFrame(data=input_data)
    steps = [
        PipelineStep(algo_id="artifact.stick_pull.v1"),
        PipelineStep(algo_id="artifact.decentralization.v1"),
        PipelineStep(algo_id="enhancement.super_resolution.v1"),
    ]
    result = executor.run(frame, steps, RunContext(job_id="int-j1", step_index=0))
    assert len(result.step_outputs) == 3
    assert result.final_output.result.shape == input_data.shape
    assert result.final_output.result.dtype == np.float32
    assert np.isfinite(result.final_output.result).all()
