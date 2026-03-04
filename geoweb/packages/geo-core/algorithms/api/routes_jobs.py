from __future__ import annotations

import json
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException

from algorithms.api.runtime import (
    AGENT_SERVICE,
    JOB_STORE,
    REGISTRY,
    JobRecord,
    new_job_id,
    now_iso,
    processed_root,
    update_job,
)
from algorithms.api.schemas import (
    AgentRecommendRequestSchema,
    AgentRecommendResponseSchema,
    JobCreateRequest,
    JobCreateResponse,
    JobResultResponse,
    JobStateResponse,
    JobStatus,
)
from algorithms.core.data_models import InputFrame, PipelineStep, RunContext
from algorithms.core.exceptions import AppError
from algorithms.core.pipeline import PipelineExecutor
from algorithms.core.utils.io import build_output_filename, save_npz
from algorithms.core.utils.metadata import build_minimal_metadata

router = APIRouter()

DEFAULT_PIPELINE = [
    "artifact.stick_pull.v1",
    "artifact.decentralization.v1",
    "enhancement.super_resolution.v1",
]


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _to_input_frame(request: JobCreateRequest) -> InputFrame:
    array = np.asarray(request.frame.data, dtype=np.float32)
    return InputFrame(
        data=array,
        data_layout=request.frame.data_layout,
        value_range=request.frame.value_range,
        spatial_meta=request.frame.spatial_meta,
        source_meta=request.frame.source_meta,
        artifact_tags=request.frame.artifact_tags,
    )


def _to_steps(request: JobCreateRequest) -> list[PipelineStep]:
    if request.pipeline:
        return [PipelineStep(algo_id=step.algo_id, config=step.config) for step in request.pipeline]
    return [PipelineStep(algo_id=algo_id, config={}) for algo_id in DEFAULT_PIPELINE]


@router.post("/jobs", response_model=JobCreateResponse)
def create_job(request: JobCreateRequest) -> JobCreateResponse:
    job_id = request.job_id or new_job_id()
    record = JobRecord(
        job_id=job_id,
        status=JobStatus.PENDING.value,
        progress=0.0,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    JOB_STORE[job_id] = record

    try:
        update_job(record, status=JobStatus.RUNNING.value, progress=0.1)

        input_frame = _to_input_frame(request)
        steps = _to_steps(request)
        executor = PipelineExecutor(REGISTRY)

        context = RunContext(
            job_id=job_id,
            step_index=0,
            created_by=request.created_by,
            service_version="framework.v1",
        )
        result = executor.run(input_frame=input_frame, steps=steps, context=context)
        record.result = result
        update_job(record, progress=0.8)

        job_output_dir = processed_root() / f"job_{job_id}"
        job_output_dir.mkdir(parents=True, exist_ok=True)
        npz_files = []
        for index, output in enumerate(result.step_outputs, start=1):
            file_name = build_output_filename(job_id, index, output.run_report.algo_id, "npz")
            file_path = job_output_dir / file_name
            metadata = build_minimal_metadata(
                job_id=job_id,
                created_by=request.created_by,
                service_version="framework.v1",
                source_meta=input_frame.source_meta,
            )
            metadata["algo_chain"] = [step.run_report.algo_id for step in result.step_outputs[:index]]
            save_npz(file_path, output.result, metadata)
            npz_files.append(str(file_path))

        run_report_path = job_output_dir / "run_report.json"
        report_payload = {
            "job_id": job_id,
            "status": JobStatus.SUCCEEDED.value,
            "step_reports": [step.run_report.to_dict() for step in result.step_outputs],
        }
        run_report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        record.npz_files = npz_files
        record.run_report_path = str(run_report_path)
        update_job(record, status=JobStatus.SUCCEEDED.value, progress=1.0)
    except AppError as exc:
        update_job(record, status=JobStatus.FAILED.value, progress=1.0, error=str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        update_job(record, status=JobStatus.FAILED.value, progress=1.0, error=f"A3001: {exc}")

    return JobCreateResponse(job_id=job_id, status=JobStatus(record.status))


@router.get("/jobs/{job_id}", response_model=JobStateResponse)
def get_job(job_id: str) -> JobStateResponse:
    record = JOB_STORE.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"job_id not found: {job_id}")
    return JobStateResponse(
        job_id=job_id,
        status=JobStatus(record.status),
        progress=record.progress,
        error=record.error,
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
def get_job_result(job_id: str) -> JobResultResponse:
    record = JOB_STORE.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"job_id not found: {job_id}")

    result_data = None
    if record.result is not None:
        result_data = record.result.final_output.result.tolist()
    return JobResultResponse(
        job_id=job_id,
        status=JobStatus(record.status),
        result_data=result_data,
        npz_files=record.npz_files,
        run_report_path=record.run_report_path,
    )


def agent_recommend(request: AgentRecommendRequestSchema) -> AgentRecommendResponseSchema:
    response = AGENT_SERVICE.recommend(request)
    return AgentRecommendResponseSchema(**_model_dump(response))
