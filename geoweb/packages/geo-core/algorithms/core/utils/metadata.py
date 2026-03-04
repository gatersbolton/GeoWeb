from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

REQUIRED_METADATA_FIELDS = [
    "job_id",
    "well_id",
    "depth_start",
    "depth_end",
    "sampling_rate_depth",
    "sampling_rate_azimuth",
    "input_format",
    "original_file_uri",
    "preprocess_ops",
    "algo_chain",
    "created_at",
    "created_by",
    "service_version",
]


def utcnow_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def build_minimal_metadata(
    *,
    job_id: str,
    created_by: str,
    service_version: str,
    source_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_meta = source_meta or {}
    return {
        "job_id": job_id,
        "well_id": source_meta.get("well_id", "unknown"),
        "depth_start": source_meta.get("depth_start", 0.0),
        "depth_end": source_meta.get("depth_end", 0.0),
        "sampling_rate_depth": source_meta.get("sampling_rate_depth", 0.0),
        "sampling_rate_azimuth": source_meta.get("sampling_rate_azimuth", 0.0),
        "input_format": source_meta.get("input_format", "npy"),
        "original_file_uri": source_meta.get("original_file_uri", ""),
        "preprocess_ops": source_meta.get("preprocess_ops", []),
        "algo_chain": source_meta.get("algo_chain", []),
        "created_at": utcnow_iso(),
        "created_by": created_by,
        "service_version": service_version,
    }


def append_algo_chain(source_meta: dict[str, Any], algo_id: str) -> dict[str, Any]:
    output = deepcopy(source_meta)
    chain = list(output.get("algo_chain", []))
    chain.append(algo_id)
    output["algo_chain"] = chain
    return output


def missing_required_metadata(metadata: dict[str, Any]) -> list[str]:
    return [field for field in REQUIRED_METADATA_FIELDS if field not in metadata]

