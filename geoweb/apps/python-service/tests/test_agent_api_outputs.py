from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from python_service.api.agent import (
    _append_enhancement_follow_up,
    _infer_artifact_tags,
    _save_agent_outputs,
    _should_offer_enhancement_follow_up,
)

from algorithms.core.data_models import AlgorithmRunReport, OutputFrame, PipelineStep


def _build_output(
    *,
    algo_id: str,
    data: np.ndarray,
    quality_metrics: dict[str, float],
    warnings: list[str] | None = None,
) -> OutputFrame:
    return OutputFrame(
        result=np.asarray(data, dtype=np.float32),
        quality_metrics=quality_metrics,
        artifact_detected={},
        run_report=AlgorithmRunReport(
            algo_id=algo_id,
            algo_version="v1",
            config_hash="cfg-hash",
            runtime_ms=1.0,
            warnings=warnings or [],
        ),
    )


def test_save_agent_outputs_preserves_each_pipeline_step(tmp_path: Path) -> None:
    step_outputs = [
        _build_output(
            algo_id="artifact.decentralization.v1",
            data=np.ones((6, 6), dtype=np.float32),
            quality_metrics={"mean_abs_delta": 0.1},
            warnings=["ring bias corrected"],
        ),
        _build_output(
            algo_id="enhancement.super_resolution.v1",
            data=np.ones((12, 12), dtype=np.float32),
            quality_metrics={"sharpness_gain": 4.0},
        ),
    ]
    steps = [
        PipelineStep(
            algo_id="artifact.decentralization.v1",
            config={"safe": {"method": "harmonic"}},
        ),
        PipelineStep(
            algo_id="enhancement.super_resolution.v1",
            config={"advanced": {"outscale": 4.0}},
        ),
    ]

    saved = _save_agent_outputs(
        session_id="sess001",
        output_dir=tmp_path,
        input_file_name="input.png",
        step_outputs=step_outputs,
        steps=steps,
        recommendation={
            "recommended_pipeline": [
                "artifact.decentralization.v1",
                "enhancement.super_resolution.v1",
            ]
        },
        chat_response={"decision_log": {"llm_used": False}},
        source_meta={"filename": "input.png"},
    )

    outputs = saved["execution_outputs"]
    assert len(outputs) == 2
    assert outputs[0]["title"] == "去除去中心化伪影"
    assert outputs[0]["warnings"] == ["ring bias corrected"]
    assert outputs[1]["title"] == "4倍超分增强"
    assert outputs[1]["quality_metrics"]["sharpness_gain"] == 4.0

    files = saved["files"]
    assert files["image"]["name"].endswith("enhancement.super_resolution.v1.png")
    assert files["npz"]["name"].endswith("enhancement.super_resolution.v1.npz")
    assert files["report"]["name"] in files["download_map"]
    assert files["recommendation"]["name"] in files["download_map"]
    assert len(files["steps"]) == 2
    assert Path(files["steps"][0]["image"]["path"]).exists()
    assert Path(files["steps"][1]["npz"]["path"]).exists()


def test_artifact_only_request_offers_optional_enhancement_follow_up() -> None:
    should_offer = _should_offer_enhancement_follow_up(
        message="帮我给它去除去中心化的伪影",
        recommendation={"recommended_pipeline": ["artifact.decentralization.v1"]},
    )
    assert should_offer is True
    answer = _append_enhancement_follow_up("已完成去除去中心化伪影。")
    assert "是否需要我继续" in answer


def test_explicit_enhancement_request_does_not_offer_follow_up() -> None:
    should_offer = _should_offer_enhancement_follow_up(
        message="帮我给它去除去中心化的伪影，然后再做增强",
        recommendation={
            "recommended_pipeline": [
                "artifact.decentralization.v1",
                "enhancement.super_resolution.v1",
            ]
        },
    )
    assert should_offer is False


def test_infer_artifact_tags_detects_groovemask_prompt() -> None:
    tags = _infer_artifact_tags("这张图里有稳定器槽沟伪影，帮我去掉", [])
    assert "groovemask" in tags
