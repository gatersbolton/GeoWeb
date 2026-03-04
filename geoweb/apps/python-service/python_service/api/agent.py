from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import numpy as np
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

from ..core.paths import ensure_geo_core_path
from ..core.progress import calculation_results

ensure_geo_core_path()

from algorithms.agents.contracts import AgentChatMessage, AgentChatRequest, AgentRecommendRequest
from algorithms.api.runtime import AGENT_SERVICE, REGISTRY
from algorithms.core.data_models import InputFrame, PipelineStep, RunContext
from algorithms.core.pipeline import PipelineExecutor

router = APIRouter()


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _json_response(content: dict[str, Any], *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=content)


def _parse_json_list(raw: Optional[str], *, fallback: list[Any] | None = None) -> list[Any]:
    if not raw:
        return fallback or []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return value
    except json.JSONDecodeError:
        pass
    return fallback or []


def _parse_bool(raw: Optional[str], default: bool = False) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _history_from_payload(raw_history: Optional[str]) -> list[AgentChatMessage]:
    items = _parse_json_list(raw_history, fallback=[])
    parsed: list[AgentChatMessage] = []
    for item in items[:30]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user"))
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        try:
            parsed.append(AgentChatMessage(role=role, content=content))
        except Exception:
            continue
    return parsed


def _load_uploaded_image(file_path: str) -> tuple[np.ndarray, str]:
    image = Image.open(file_path)
    if image.mode in {"L", "I;16", "I", "F"}:
        matrix = np.asarray(image, dtype=np.float32)
        return matrix, "HW"
    rgb_image = image.convert("RGB")
    matrix = np.asarray(rgb_image, dtype=np.float32)
    return matrix, "HWC"


def _to_png_uint8(array: np.ndarray) -> np.ndarray:
    data = np.asarray(array, dtype=np.float32)
    if data.ndim == 3 and data.shape[0] in (1, 3, 4) and data.shape[2] not in (1, 3, 4):
        data = np.transpose(data, (1, 2, 0))
    if data.ndim == 3 and data.shape[2] == 1:
        data = np.repeat(data, 3, axis=2)

    if data.ndim not in (2, 3):
        raise ValueError("Unsupported output shape for image preview.")
    if float(np.max(data)) <= 1.5 and float(np.min(data)) >= 0.0:
        data = data * 255.0
    data = np.clip(data, 0.0, 255.0).astype(np.uint8)
    return data


def _to_data_url_png(array: np.ndarray) -> str:
    image = Image.fromarray(_to_png_uint8(array))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _infer_artifact_tags(message: str, explicit_tags: list[str]) -> list[str]:
    tags = {tag for tag in explicit_tags if tag in {"stick_pull", "decentralization"}}
    lower_text = (message or "").lower()
    if "stick_pull" in lower_text or "stick pull" in lower_text or "stick-and-pull" in lower_text:
        tags.add("stick_pull")
    if "decentralization" in lower_text:
        tags.add("decentralization")
    if any(token in message for token in ["拉伸", "拖拽", "纵向畸变", "粘滞", "提放伪影"]):
        tags.add("stick_pull")
    if any(token in message for token in ["去中心", "偏心", "环向偏置", "方位偏置"]):
        tags.add("decentralization")
    return sorted(tags)


def _looks_like_recommendation_prompt(message: str) -> bool:
    text = (message or "").strip()
    lower = text.lower()
    if not text:
        return False
    if any(
        token in lower
        for token in (
            "recommend",
            "pipeline",
            "algorithm",
            "decentralization",
            "stick_pull",
            "stick pull",
            "stick-and-pull",
            "artifact",
        )
    ):
        return True
    if any(token in text for token in ("推荐", "去伪影", "算法", "流程", "去中心", "偏心", "拉伸", "拖拽")):
        return True
    return False


def _should_attach_recommend_request(
    *,
    message: str,
    tags: list[str],
    image_uploaded: bool,
) -> bool:
    if image_uploaded:
        return True
    if tags:
        return True
    return _looks_like_recommendation_prompt(message)


def _build_steps_from_recommendation(recommendation: dict[str, Any]) -> list[PipelineStep]:
    pipeline = recommendation.get("recommended_pipeline", [])
    configs = recommendation.get("recommended_configs", {})
    steps: list[PipelineStep] = []
    for algo_id in pipeline:
        step_cfg = configs.get(algo_id, {}) if isinstance(configs, dict) else {}
        steps.append(PipelineStep(algo_id=str(algo_id), config=step_cfg))
    return steps


def _save_agent_outputs(
    *,
    session_id: str,
    output_dir: Path,
    input_file_name: str,
    result_array: np.ndarray,
    recommendation: dict[str, Any],
    chat_response: dict[str, Any],
    step_reports: list[dict[str, Any]],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    png_name = "agent_output.png"
    npz_name = "agent_output.npz"
    report_name = "agent_report.json"
    rec_name = "agent_recommendation.json"

    png_path = output_dir / png_name
    npz_path = output_dir / npz_name
    report_path = output_dir / report_name
    rec_path = output_dir / rec_name

    Image.fromarray(_to_png_uint8(result_array)).save(png_path)
    np.savez_compressed(npz_path, data=np.asarray(result_array, dtype=np.float32))
    report_path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "source_file": input_file_name,
                "step_reports": step_reports,
                "chat_decision_log": chat_response.get("decision_log", {}),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    rec_path.write_text(json.dumps(recommendation, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "image": str(png_path),
        "npz": str(npz_path),
        "report": str(report_path),
        "recommendation": str(rec_path),
    }


def _resolve_reused_image_path(session_id: str | None) -> str | None:
    if not session_id:
        return None
    data = calculation_results.get(session_id)
    if not data or data.get("type") != "agent":
        return None
    path = data.get("input_image")
    if not path:
        return None
    path = str(path)
    if not os.path.exists(path):
        return None
    return path


@router.get("/agent/tools")
async def list_agent_tools() -> JSONResponse:
    tools = [_model_dump(item) for item in AGENT_SERVICE.list_tools()]
    return _json_response({"tools": tools})


@router.get("/agent/runtime")
async def agent_runtime() -> JSONResponse:
    return _json_response({"runtime": AGENT_SERVICE.runtime_status()})


@router.post("/agent/recommend")
async def agent_recommend(payload: dict[str, Any]) -> JSONResponse:
    try:
        request = AgentRecommendRequest(**payload)
        response = AGENT_SERVICE.recommend(request)
        return _json_response(_model_dump(response))
    except Exception as exc:
        return _json_response({"error": f"推荐失败: {exc}"}, status_code=400)


@router.post("/agent/chat")
async def agent_chat(
    message: str = Form(...),
    history_json: Optional[str] = Form(None),
    artifact_tags_json: Optional[str] = Form(None),
    include_enhancement: Optional[str] = Form("true"),
    execute_on_upload: Optional[str] = Form("true"),
    reuse_session_id: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
) -> JSONResponse:
    chat_history = _history_from_payload(history_json)
    raw_tags = _parse_json_list(artifact_tags_json, fallback=[])
    tags = _infer_artifact_tags(message, [str(tag) for tag in raw_tags])
    enable_enhancement = _parse_bool(include_enhancement, default=True)
    should_execute = _parse_bool(execute_on_upload, default=True)
    reused_image_path = _resolve_reused_image_path(reuse_session_id)
    image_available = image_file is not None or reused_image_path is not None
    image_uploaded = image_file is not None
    should_recommend = _should_attach_recommend_request(
        message=message,
        tags=tags,
        image_uploaded=image_available,
    )
    message_for_agent = message
    if image_available:
        message_for_agent = (
            f"{message}\n\n"
            "[系统信息] 本轮请求已提供 ATV 图像数据，可直接给出执行方案并假定后端会执行处理。"
        )

    recommend_request = None
    if should_recommend:
        recommend_request = AgentRecommendRequest(
            user_prompt=message,
            artifact_tags=tags,
            include_enhancement=enable_enhancement,
        )
    chat_request = AgentChatRequest(
        message=message_for_agent,
        history=chat_history,
        recommend=recommend_request,
    )
    chat_response = AGENT_SERVICE.chat(chat_request)
    response_payload: dict[str, Any] = _model_dump(chat_response)

    if not image_available or not should_execute:
        response_payload["execution"] = {
            "executed": False,
            "reason": "no_uploaded_or_reused_image" if not image_available else "execute_on_upload=false",
        }
        return _json_response(response_payload)

    temp_dir = tempfile.mkdtemp(prefix="agent_chat_")
    output_dir = Path(temp_dir) / "outputs"
    session_id = uuid.uuid4().hex

    try:
        image_source = "uploaded"
        if image_file is not None:
            input_name = image_file.filename or "uploaded_image.png"
            suffix = Path(input_name).suffix or ".png"
            input_path = Path(temp_dir) / f"input{suffix}"
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
        elif reused_image_path is not None:
            image_source = "reused"
            input_name = f"reused_from_{reuse_session_id}.png"
            suffix = Path(reused_image_path).suffix or ".png"
            input_path = Path(temp_dir) / f"input{suffix}"
            shutil.copyfile(reused_image_path, input_path)
        else:
            return _json_response({"error": "未找到可执行图像数据。"}, status_code=400)

        image_data, layout = _load_uploaded_image(str(input_path))
        frame = InputFrame(
            data=image_data,
            data_layout=layout,
            value_range=[0.0, 255.0],
            source_meta={"filename": input_name, "input_format": "image"},
            artifact_tags=tags,
        )

        execution_recommend_request = recommend_request or AgentRecommendRequest(
            user_prompt=message,
            artifact_tags=tags,
            include_enhancement=enable_enhancement,
        )
        recommendation = response_payload.get("recommendation") or _model_dump(
            AGENT_SERVICE.recommend(execution_recommend_request)
        )
        steps = _build_steps_from_recommendation(recommendation)
        if not steps:
            return _json_response({"error": "未获取到可执行算法流程。"}, status_code=400)

        executor = PipelineExecutor(REGISTRY)
        context = RunContext(
            job_id=session_id,
            step_index=0,
            created_by="agent-chat",
            service_version="python-service.agent.v1",
            output_dir=str(output_dir),
        )
        pipeline_result = executor.run(input_frame=frame, steps=steps, context=context)
        final_array = pipeline_result.final_output.result
        step_reports = [step.run_report.to_dict() for step in pipeline_result.step_outputs]

        files = _save_agent_outputs(
            session_id=session_id,
            output_dir=output_dir,
            input_file_name=input_name,
            result_array=final_array,
            recommendation=recommendation,
            chat_response=response_payload,
            step_reports=step_reports,
        )

        calculation_results[session_id] = {
            "type": "agent",
            "temp_dir": temp_dir,
            "output_dir": str(output_dir),
            "source": input_name,
            "input_image": str(input_path),
            "files": files,
            "recommendation": recommendation,
        }

        response_payload["execution"] = {
            "executed": True,
            "session_id": session_id,
            "source": input_name,
            "image_source": image_source,
            "pipeline": recommendation.get("recommended_pipeline", []),
            "step_reports": step_reports,
            "quality_metrics": {
                step.run_report.algo_id: step.quality_metrics for step in pipeline_result.step_outputs
            },
            "output_image": _to_data_url_png(final_array),
            "download_urls": {
                "image": f"/api/agent/download/{session_id}/agent_output.png",
                "npz": f"/api/agent/download/{session_id}/agent_output.npz",
                "report": f"/api/agent/download/{session_id}/agent_report.json",
                "recommendation": f"/api/agent/download/{session_id}/agent_recommendation.json",
            },
        }
        return _json_response(response_payload)
    except Exception as exc:
        return _json_response({"error": f"Agent 执行失败: {exc}"}, status_code=500)


@router.get("/agent/download/{session_id}/{filename}")
async def download_agent_output(session_id: str, filename: str):
    data = calculation_results.get(session_id)
    if data is None:
        return _json_response({"error": "未找到对应会话。"}, status_code=404)
    if data.get("type") != "agent":
        return _json_response({"error": "会话类型不匹配。"}, status_code=400)

    files = data.get("files", {})
    allowed = {
        "agent_output.png": files.get("image"),
        "agent_output.npz": files.get("npz"),
        "agent_report.json": files.get("report"),
        "agent_recommendation.json": files.get("recommendation"),
    }
    path = allowed.get(filename)
    if not path or not os.path.exists(path):
        return _json_response({"error": "文件不存在。"}, status_code=404)
    return FileResponse(path, filename=filename)
