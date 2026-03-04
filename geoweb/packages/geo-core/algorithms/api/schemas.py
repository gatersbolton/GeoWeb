from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from algorithms.agents.contracts import (
    AgentChatRequest,
    AgentChatResponse,
    AgentRecommendRequest,
    AgentRecommendResponse,
    AgentToolSpec,
)


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class PipelineStepSchema(BaseModel):
    algo_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class FrameSchema(BaseModel):
    data: list[Any]
    data_layout: str = "HW"
    dtype: str = "float32"
    value_range: list[float] = Field(default_factory=lambda: [0.0, 1.0])
    spatial_meta: dict[str, Any] = Field(default_factory=dict)
    source_meta: dict[str, Any] = Field(default_factory=dict)
    artifact_tags: list[str] = Field(default_factory=list)


class JobCreateRequest(BaseModel):
    job_id: str | None = None
    frame: FrameSchema
    pipeline: list[PipelineStepSchema] = Field(default_factory=list)
    created_by: str = "api"


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStateResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float
    error: str | None = None


class JobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    result_data: list[Any] | None = None
    npz_files: list[str] = Field(default_factory=list)
    run_report_path: str | None = None


class AlgorithmInfoSchema(BaseModel):
    algo_id: str
    version: str
    capability: dict[str, Any] = Field(default_factory=dict)
    default_config: dict[str, Any] = Field(default_factory=dict)


class AgentRecommendRequestSchema(AgentRecommendRequest):
    pass


class AgentRecommendResponseSchema(AgentRecommendResponse):
    pass


class AgentChatRequestSchema(AgentChatRequest):
    pass


class AgentChatResponseSchema(AgentChatResponse):
    pass


class AgentToolSchema(AgentToolSpec):
    pass
