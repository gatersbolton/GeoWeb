from __future__ import annotations

import base64
import json
import os
import re
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
from ..services.dlis import inspect_dlis_payload, render_dlis_payload

ensure_geo_core_path()

from algorithms.agents.contracts import AgentChatMessage, AgentChatRequest, AgentRecommendRequest
from algorithms.api.runtime import AGENT_SERVICE, REGISTRY
from algorithms.core.data_models import InputFrame, OutputFrame, PipelineStep, RunContext
from algorithms.core.pipeline import PipelineExecutor
from algorithms.core.utils.io import build_output_filename, save_npz
from algorithms.core.utils.metadata import build_minimal_metadata

router = APIRouter()
DEFAULT_ENHANCEMENT_ALGO = "enhancement.super_resolution.v1"


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


def _format_scale_label(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return f"{int(numeric)}倍"
    return f"{numeric:g}倍"


def _build_step_summary(algo_id: str, config: dict[str, Any], step_index: int) -> dict[str, str]:
    if algo_id == "artifact.groovemask.v1":
        backend = str(config.get("safe", {}).get("backend", "")).strip()
        suffix = f"（backend={backend}）" if backend else ""
        title = "去除槽沟伪影"
        summary = f"已完成槽沟去伪影{suffix}。"
        return {
            "title": title,
            "summary": summary,
            "message": f"子任务 {step_index} 已完成：{summary}",
        }
    if algo_id == "artifact.decentralization.v1":
        method = str(config.get("safe", {}).get("method", "")).strip()
        suffix = f"（method={method}）" if method else ""
        title = "去除去中心化伪影"
        summary = f"已完成去除去中心化伪影{suffix}。"
        return {
            "title": title,
            "summary": summary,
            "message": f"子任务 {step_index} 已完成：{summary}",
        }
    if algo_id == "artifact.stick_pull.v1":
        title = "去除 stick_pull 伪影"
        summary = "已完成 stick_pull 去伪影。"
        return {
            "title": title,
            "summary": summary,
            "message": f"子任务 {step_index} 已完成：{summary}",
        }
    if algo_id == "enhancement.super_resolution.v1":
        outscale = config.get("advanced", {}).get("outscale", 1.0)
        try:
            outscale_value = float(outscale)
        except (TypeError, ValueError):
            outscale_value = 1.0
        if outscale_value > 1.0:
            scale_label = _format_scale_label(outscale_value)
            title = f"{scale_label}超分增强"
            summary = f"已完成 {scale_label}超分增强。"
        else:
            title = "图像增强"
            summary = "已完成图像增强。"
        return {
            "title": title,
            "summary": summary,
            "message": f"子任务 {step_index} 已完成：{summary}",
        }

    title = f"步骤 {step_index}"
    summary = f"已完成算法 {algo_id}。"
    return {
        "title": title,
        "summary": summary,
        "message": f"子任务 {step_index} 已完成：{summary}",
    }


def _infer_artifact_tags(message: str, explicit_tags: list[str]) -> list[str]:
    tags = {tag for tag in explicit_tags if tag in {"groovemask", "stick_pull", "decentralization"}}
    lower_text = (message or "").lower()
    if any(token in lower_text for token in ("groovemask", "groove", "slot artifact", "stabilizer groove")):
        tags.add("groovemask")
    if "stick_pull" in lower_text or "stick pull" in lower_text or "stick-and-pull" in lower_text:
        tags.add("stick_pull")
    if "decentralization" in lower_text:
        tags.add("decentralization")
    if any(token in message for token in ["槽沟", "沟槽", "稳定器槽", "竖槽"]):
        tags.add("groovemask")
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
            "groovemask",
            "groove",
            "decentralization",
            "stick_pull",
            "stick pull",
            "stick-and-pull",
            "artifact",
            "enhance",
            "enhancement",
            "super resolution",
            "super-resolution",
            "upscale",
        )
    ):
        return True
    if any(
        token in text
        for token in ("推荐", "去伪影", "算法", "流程", "槽沟", "沟槽", "稳定器槽", "去中心", "偏心", "拉伸", "拖拽", "增强", "超分", "放大")
    ):
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
    step_outputs: list[OutputFrame],
    steps: list[PipelineStep],
    recommendation: dict[str, Any],
    chat_response: dict[str, Any],
    source_meta: dict[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    step_reports = [step_output.run_report.to_dict() for step_output in step_outputs]
    storage_steps: list[dict[str, Any]] = []
    execution_outputs: list[dict[str, Any]] = []
    download_map: dict[str, str] = {}
    algo_chain: list[str] = []

    for step_index, (step, step_output) in enumerate(zip(steps, step_outputs), start=1):
        algo_id = str(step_output.run_report.algo_id or step.algo_id)
        algo_chain.append(algo_id)
        png_name = build_output_filename(session_id, step_index, algo_id, "png")
        npz_name = build_output_filename(session_id, step_index, algo_id, "npz")
        png_path = output_dir / png_name
        npz_path = output_dir / npz_name

        Image.fromarray(_to_png_uint8(step_output.result)).save(png_path)
        metadata = build_minimal_metadata(
            job_id=session_id,
            created_by="agent-chat",
            service_version="python-service.agent.v1",
            source_meta=source_meta,
        )
        metadata["algo_chain"] = algo_chain[:]
        metadata["current_algo_id"] = algo_id
        metadata["step_index"] = step_index
        save_npz(npz_path, np.asarray(step_output.result, dtype=np.float32), metadata)

        titles = _build_step_summary(algo_id, step.config or {}, step_index)
        download_urls = {
            "image": f"/api/agent/download/{session_id}/{png_name}",
            "npz": f"/api/agent/download/{session_id}/{npz_name}",
        }
        execution_outputs.append(
            {
                "step_index": step_index,
                "algo_id": algo_id,
                "title": titles["title"],
                "summary": titles["summary"],
                "message": titles["message"],
                "quality_metrics": step_output.quality_metrics,
                "warnings": list(step_output.run_report.warnings),
                "step_report": step_output.run_report.to_dict(),
                "output_image": _to_data_url_png(step_output.result),
                "download_urls": download_urls,
            }
        )
        storage_steps.append(
            {
                "step_index": step_index,
                "algo_id": algo_id,
                "image": {"name": png_name, "path": str(png_path)},
                "npz": {"name": npz_name, "path": str(npz_path)},
            }
        )
        download_map[png_name] = str(png_path)
        download_map[npz_name] = str(npz_path)

    final_storage_step = storage_steps[-1] if storage_steps else {}
    final_image = final_storage_step.get("image", {})
    final_npz = final_storage_step.get("npz", {})
    report_name = f"job_{session_id}_run_report.json"
    rec_name = f"job_{session_id}_recommendation.json"
    report_path = output_dir / report_name
    rec_path = output_dir / rec_name
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
    download_map[report_name] = str(report_path)
    download_map[rec_name] = str(rec_path)

    return {
        "files": {
            "image": final_image,
            "npz": final_npz,
            "report": {"name": report_name, "path": str(report_path)},
            "recommendation": {"name": rec_name, "path": str(rec_path)},
            "steps": storage_steps,
            "download_map": download_map,
        },
        "execution_outputs": execution_outputs,
        "step_reports": step_reports,
    }


_DLIS_HINTS = ("dlis", "玫瑰图", "rose", "通道", "channel", "幅度图", "振幅图", "时差图", "走时图")
_DLIS_ATV_HINTS = (
    "atv",
    "幅度",
    "振幅",
    "时差",
    "走时",
    "traveltime",
    "travel-time",
    "travel time",
    "amplitude",
    "成像",
)
_DLIS_ROSE_HINTS = ("rose", "玫瑰图", "方位图", "方位统计", "azimuth")
_DLIS_INSPECT_HINTS = ("通道", "channels", "channel", "frame", "帧", "摘要", "概览", "元数据", "metadata")
_ENHANCEMENT_REQUEST_HINTS = (
    "enhance",
    "enhancement",
    "super resolution",
    "super-resolution",
    "upscale",
    "超分",
    "增强",
    "锐化",
    "清晰",
    "放大",
)
_ENHANCEMENT_DISABLE_HINTS = ("不要增强", "不做增强", "without enhancement", "no enhancement")
_DEPTH_WINDOW_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:m|米)?\s*(?:-|~|到|至)\s*(\d+(?:\.\d+)?)\s*(?:m|米)?",
    re.IGNORECASE,
)


def _resolve_reused_input(session_id: str | None) -> dict[str, str] | None:
    if not session_id:
        return None
    data = calculation_results.get(session_id)
    if not data:
        return None
    path = data.get("input_image") or data.get("input_file")
    if not path:
        return None
    path = str(path)
    if not os.path.exists(path):
        return None
    return {
        "path": path,
        "kind": "dlis" if path.lower().endswith(".dlis") else "image",
        "source": str(data.get("source") or Path(path).name),
        "session_type": str(data.get("type") or ""),
    }


def _infer_uploaded_kind(*, upload: UploadFile | None, reused_input: dict[str, str] | None, message: str) -> str | None:
    if upload is not None:
        file_name = str(upload.filename or "").lower()
        return "dlis" if file_name.endswith(".dlis") else "image"
    if reused_input is not None:
        return reused_input.get("kind")
    text = (message or "").lower()
    if any(token in text for token in _DLIS_HINTS):
        return "dlis"
    return None


def _infer_dlis_operation(message: str) -> dict[str, Any]:
    text = (message or "").strip()
    lower = text.lower()

    wants_rose = any(token in lower for token in _DLIS_ROSE_HINTS) or "玫瑰图" in text
    wants_atv = any(token in lower for token in _DLIS_ATV_HINTS) or any(
        token in text for token in ("幅度", "振幅", "时差", "走时", "成像")
    )
    inspect_only = any(token in lower for token in _DLIS_INSPECT_HINTS) or any(
        token in text for token in ("通道", "摘要", "概览", "元数据")
    )
    has_render_keyword = wants_rose or wants_atv

    if inspect_only and not has_render_keyword:
        generate_atv = False
        generate_rose = False
    elif wants_rose and not wants_atv:
        generate_atv = False
        generate_rose = True
    elif wants_atv and not wants_rose:
        generate_atv = True
        generate_rose = False
    else:
        generate_atv = True
        generate_rose = True

    depth_min = None
    depth_max = None
    match = _DEPTH_WINDOW_PATTERN.search(text)
    if match:
        try:
            depth_min = float(match.group(1))
            depth_max = float(match.group(2))
        except (TypeError, ValueError):
            depth_min = None
            depth_max = None

    return {
        "inspect_only": inspect_only and not has_render_keyword,
        "generate_atv": generate_atv,
        "generate_rose": generate_rose,
        "depth_min": depth_min,
        "depth_max": depth_max,
    }


def _build_dlis_summary_text(summary: dict[str, Any]) -> str:
    defaults = summary.get("defaults", {})
    lines = [
        "已解析 DLIS 文件。",
        f"默认振幅通道：{defaults.get('amplitude_channel_ref') or '未识别'}",
        f"默认走时通道：{defaults.get('traveltime_channel_ref') or '未识别'}",
        f"默认角度通道：{defaults.get('angle_channel_ref') or '未识别'}",
    ]
    depth_min = defaults.get("depth_min")
    depth_max = defaults.get("depth_max")
    if depth_min is not None and depth_max is not None:
        lines.append(f"深度范围：{depth_min:.2f} m ~ {depth_max:.2f} m")
    top_channels = summary.get("channel_options", [])[:6]
    if top_channels:
        lines.append(
            "可用通道示例："
            + "、".join(str(item.get("label") or item.get("channel_ref")) for item in top_channels)
        )
    return "\n".join(lines)


def _message_requests_enhancement(message: str) -> bool:
    text = (message or "").lower()
    return any(token in text for token in _ENHANCEMENT_REQUEST_HINTS)


def _message_disables_enhancement(message: str) -> bool:
    text = (message or "").lower()
    return any(token in text for token in _ENHANCEMENT_DISABLE_HINTS)


def _should_offer_enhancement_follow_up(
    *,
    message: str,
    recommendation: dict[str, Any] | None,
) -> bool:
    if _message_requests_enhancement(message) or _message_disables_enhancement(message):
        return False
    pipeline = recommendation.get("recommended_pipeline", []) if isinstance(recommendation, dict) else []
    if not pipeline:
        return False
    has_artifact_step = any(str(algo_id).startswith("artifact.") for algo_id in pipeline)
    has_enhancement_step = DEFAULT_ENHANCEMENT_ALGO in pipeline
    return has_artifact_step and not has_enhancement_step


def _append_enhancement_follow_up(answer: str) -> str:
    suggestion = "如需的话，我可以继续基于当前结果做图像增强或超分处理。是否需要我继续？"
    base = (answer or "").strip()
    if not base:
        return suggestion
    if suggestion in base:
        return base
    return f"{base}\n\n{suggestion}"


def _build_agent_dlis_outputs(
    *,
    session_id: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    manifest_name = payload.get("manifest", {}).get("name")
    for index, item in enumerate(payload.get("outputs", []), start=1):
        file_names = item.get("file_names", {})
        download_urls = {
            "image": (
                f"/api/agent/download/{session_id}/{file_names['image']}"
                if file_names.get("image")
                else None
            ),
            "npz": (
                f"/api/agent/download/{session_id}/{file_names['npz']}"
                if file_names.get("npz")
                else None
            ),
        }
        if manifest_name and index == len(payload.get("outputs", [])):
            download_urls["report"] = f"/api/agent/download/{session_id}/{manifest_name}"
        outputs.append(
            {
                "step_index": index,
                "algo_id": item.get("tool_id"),
                "title": item.get("title"),
                "summary": item.get("summary"),
                "message": f"子任务 {index} 已完成：{item.get('title')}",
                "quality_metrics": {},
                "warnings": [],
                "step_report": {"algo_id": item.get("tool_id"), "runtime_ms": 0.0, "warnings": []},
                "output_image": item.get("output_image"),
                "download_urls": download_urls,
                "metadata": item.get("metadata", {}),
            }
        )
    return outputs


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
    reused_input = _resolve_reused_input(reuse_session_id)
    input_available = image_file is not None or reused_input is not None
    input_kind = _infer_uploaded_kind(upload=image_file, reused_input=reused_input, message=message)
    should_recommend = (
        input_kind != "dlis"
        and _should_attach_recommend_request(
            message=message,
            tags=tags,
            image_uploaded=input_available,
        )
    )
    message_for_agent = message
    if input_available and input_kind == "dlis":
        message_for_agent = (
            f"{message}\n\n"
            "[系统信息] 本轮请求已提供 DLIS 文件数据，可直接给出解析/可视化方案并假定后端会执行处理。"
        )
    elif input_available:
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

    if not input_available or not should_execute:
        response_payload["execution"] = {
            "executed": False,
            "reason": "no_uploaded_or_reused_input" if not input_available else "execute_on_upload=false",
        }
        return _json_response(response_payload)

    temp_dir = tempfile.mkdtemp(prefix="agent_chat_")
    output_dir = Path(temp_dir) / "outputs"
    session_id = uuid.uuid4().hex

    try:
        image_source = "uploaded"
        if image_file is not None:
            input_name = image_file.filename or ("uploaded.dlis" if input_kind == "dlis" else "uploaded_image.png")
            suffix = Path(input_name).suffix or (".dlis" if input_kind == "dlis" else ".png")
            input_path = Path(temp_dir) / f"input{suffix}"
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
        elif reused_input is not None:
            image_source = "reused"
            source_suffix = Path(reused_input["path"]).suffix or (".dlis" if input_kind == "dlis" else ".png")
            input_name = str(reused_input.get("source") or f"reused_from_{reuse_session_id}{source_suffix}")
            suffix = source_suffix
            input_path = Path(temp_dir) / f"input{suffix}"
            shutil.copyfile(reused_input["path"], input_path)
        else:
            return _json_response({"error": "未找到可执行输入数据。"}, status_code=400)

        if input_kind == "dlis":
            dlis_plan = _infer_dlis_operation(message)
            if dlis_plan["inspect_only"]:
                inspection = inspect_dlis_payload(str(input_path), source_label=input_name)
                response_payload["used_tools"] = list(
                    dict.fromkeys(list(response_payload.get("used_tools", [])) + ["dlis.visualize.v1"])
                )
                response_payload["answer"] = (
                    f"{response_payload.get('answer', '').strip()}\n\n{_build_dlis_summary_text(inspection['summary'])}"
                ).strip()
                calculation_results[session_id] = {
                    "type": "agent",
                    "temp_dir": temp_dir,
                    "output_dir": str(output_dir),
                    "source": input_name,
                    "input_file": str(input_path),
                    "files": {},
                    "download_files": {},
                    "dlis_summary": inspection["summary"],
                }
                response_payload["execution"] = {
                    "executed": True,
                    "session_id": session_id,
                    "source": input_name,
                    "image_source": image_source,
                    "input_kind": "dlis",
                    "outputs": [],
                    "subtasks": [],
                    "summary": inspection["summary"],
                    "download_urls": {},
                }
                return _json_response(response_payload)

            dlis_payload = render_dlis_payload(
                file_path=str(input_path),
                input_name=input_name,
                output_dir=str(output_dir),
                session_id=session_id,
                options={
                    "generate_atv": dlis_plan["generate_atv"],
                    "generate_rose": dlis_plan["generate_rose"],
                    "depth_min": dlis_plan["depth_min"],
                    "depth_max": dlis_plan["depth_max"],
                },
            )
            execution_outputs = _build_agent_dlis_outputs(session_id=session_id, payload=dlis_payload)
            final_output = execution_outputs[-1] if execution_outputs else None
            manifest_name = dlis_payload.get("manifest", {}).get("name")
            response_payload["used_tools"] = list(
                dict.fromkeys(list(response_payload.get("used_tools", [])) + ["dlis.visualize.v1"])
            )
            calculation_results[session_id] = {
                "type": "agent",
                "temp_dir": temp_dir,
                "output_dir": str(output_dir),
                "source": input_name,
                "input_file": str(input_path),
                "files": {
                    "manifest": dlis_payload.get("manifest"),
                    "outputs": dlis_payload.get("outputs", []),
                },
                "download_files": dlis_payload.get("download_map", {}),
                "dlis_summary": dlis_payload.get("inspection"),
                "dlis_options": dlis_payload.get("options"),
            }
            response_payload["execution"] = {
                "executed": True,
                "session_id": session_id,
                "source": input_name,
                "image_source": image_source,
                "input_kind": "dlis",
                "pipeline": [item.get("tool_id") for item in dlis_payload.get("outputs", [])],
                "step_reports": [item.get("step_report") for item in execution_outputs],
                "quality_metrics": {},
                "output_image": final_output.get("output_image") if final_output else None,
                "outputs": execution_outputs,
                "subtasks": execution_outputs,
                "summary": dlis_payload.get("inspection"),
                "options": dlis_payload.get("options"),
                "download_urls": {
                    "report": (
                        f"/api/agent/download/{session_id}/{manifest_name}"
                        if manifest_name
                        else None
                    ),
                },
            }
            return _json_response(response_payload)

        image_data, layout = _load_uploaded_image(str(input_path))
        frame = InputFrame(
            data=image_data,
            data_layout=layout,
            value_range=[0.0, 255.0],
            source_meta={
                "filename": input_name,
                "input_format": "image",
                "original_file_uri": str(input_path),
                "preprocess_ops": [],
            },
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
        saved_outputs = _save_agent_outputs(
            session_id=session_id,
            output_dir=output_dir,
            input_file_name=input_name,
            step_outputs=pipeline_result.step_outputs,
            steps=steps,
            recommendation=recommendation,
            chat_response=response_payload,
            source_meta=frame.source_meta,
        )
        files = saved_outputs["files"]
        execution_outputs = saved_outputs["execution_outputs"]
        step_reports = saved_outputs["step_reports"]
        final_output = execution_outputs[-1] if execution_outputs else None

        response_payload["used_tools"] = list(
            dict.fromkeys(
                list(response_payload.get("used_tools", []))
                + [f"algo:{step.algo_id}" for step in steps]
            )
        )

        calculation_results[session_id] = {
            "type": "agent",
            "temp_dir": temp_dir,
            "output_dir": str(output_dir),
            "source": input_name,
            "input_image": str(input_path),
            "files": files,
            "download_files": files.get("download_map", {}),
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
            "output_image": final_output.get("output_image") if final_output else None,
            "outputs": execution_outputs,
            "subtasks": execution_outputs,
            "download_urls": {
                "image": (
                    f"/api/agent/download/{session_id}/{files['image']['name']}"
                    if files.get("image", {}).get("name")
                    else None
                ),
                "npz": (
                    f"/api/agent/download/{session_id}/{files['npz']['name']}"
                    if files.get("npz", {}).get("name")
                    else None
                ),
                "report": f"/api/agent/download/{session_id}/{files['report']['name']}",
                "recommendation": f"/api/agent/download/{session_id}/{files['recommendation']['name']}",
            },
        }
        if _should_offer_enhancement_follow_up(
            message=message,
            recommendation=recommendation,
        ):
            response_payload["answer"] = _append_enhancement_follow_up(response_payload.get("answer", ""))
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

    allowed = data.get("download_files", {})
    if not allowed:
        files = data.get("files", {})
        allowed = {
            files.get("image", {}).get("name"): files.get("image", {}).get("path"),
            files.get("npz", {}).get("name"): files.get("npz", {}).get("path"),
            files.get("report", {}).get("name"): files.get("report", {}).get("path"),
            files.get("recommendation", {}).get("name"): files.get("recommendation", {}).get("path"),
        }
    path = allowed.get(filename)
    if not path or not os.path.exists(path):
        return _json_response({"error": "文件不存在。"}, status_code=404)
    return FileResponse(path, filename=filename)
