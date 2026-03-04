from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from algorithms.agents.service import ATVExpertAgentService
from algorithms.agents.tools.registry import build_default_tool_registry
from algorithms.bootstrap import build_default_registry
from algorithms.core.data_models import PipelineResult


def now_iso() -> str:
    return datetime.utcnow().isoformat()


@dataclass
class JobRecord:
    job_id: str
    status: str
    progress: float
    created_at: str
    updated_at: str
    error: str | None = None
    npz_files: list[str] = field(default_factory=list)
    run_report_path: str | None = None
    result: PipelineResult | None = None
    extra: dict[str, Any] = field(default_factory=dict)


REGISTRY = build_default_registry()
AGENT_TOOL_REGISTRY = build_default_tool_registry(REGISTRY)
AGENT_SERVICE = ATVExpertAgentService(REGISTRY, tool_registry=AGENT_TOOL_REGISTRY)
JOB_STORE: dict[str, JobRecord] = {}


def new_job_id() -> str:
    return uuid4().hex


def update_job(
    record: JobRecord,
    *,
    status: str | None = None,
    progress: float | None = None,
    error: str | None = None,
) -> None:
    if status is not None:
        record.status = status
    if progress is not None:
        record.progress = progress
    if error is not None:
        record.error = error
    record.updated_at = now_iso()


def package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def processed_root() -> Path:
    path = package_root() / "datasets" / "processed"
    path.mkdir(parents=True, exist_ok=True)
    return path
