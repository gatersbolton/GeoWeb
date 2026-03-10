from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ..core.paths import dlis_demo_file
from ..core.progress import calculation_results
from ..services.dlis import inspect_dlis_payload, render_dlis_payload

router = APIRouter()


def _json_response(content: dict[str, Any], *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=content)


def _parse_bool(raw: Optional[str], default: bool = False) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _resolve_reused_dlis_path(session_id: str | None) -> tuple[str | None, str | None]:
    if not session_id:
        return None, None
    data = calculation_results.get(session_id)
    if not data:
        return None, None
    input_path = data.get("input_file")
    if not input_path or not str(input_path).lower().endswith(".dlis"):
        return None, None
    if not os.path.exists(str(input_path)):
        return None, None
    return str(input_path), str(data.get("source") or Path(str(input_path)).name)


def _prepare_dlis_input(
    *,
    dlis_file: UploadFile | None,
    use_demo: bool,
    reuse_session_id: str | None = None,
) -> tuple[str, str, str]:
    reused_path, reused_name = _resolve_reused_dlis_path(reuse_session_id)
    if reused_path:
        return reused_path, reused_name or Path(reused_path).name, tempfile.mkdtemp(prefix="dlis_reuse_")

    temp_dir = tempfile.mkdtemp(prefix="dlis_")
    if use_demo:
        source_path = dlis_demo_file()
        if not os.path.exists(source_path):
            raise FileNotFoundError("默认 DLIS 示例文件不存在。")
        input_name = Path(source_path).name
        input_path = os.path.join(temp_dir, input_name)
        shutil.copyfile(source_path, input_path)
        return input_path, input_name, temp_dir

    if dlis_file is None:
        raise ValueError("请上传 .dlis 文件或选择使用默认示例文件。")

    input_name = dlis_file.filename or "uploaded.dlis"
    if not input_name.lower().endswith(".dlis"):
        raise ValueError("仅支持 .dlis 文件。")
    input_path = os.path.join(temp_dir, input_name)
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(dlis_file.file, buffer)
    return input_path, input_name, temp_dir


def _render_options_from_form(
    *,
    depth_min: Optional[str],
    depth_max: Optional[str],
    pixel_scale: Optional[str],
    clip_low: Optional[str],
    clip_high: Optional[str],
    gamma: Optional[str],
    rose_bins: Optional[str],
    generate_atv: Optional[str],
    generate_rose: Optional[str],
    amplitude_channel_ref: Optional[str],
    traveltime_channel_ref: Optional[str],
    angle_channel_ref: Optional[str],
) -> dict[str, Any]:
    return {
        "depth_min": depth_min,
        "depth_max": depth_max,
        "pixel_scale": pixel_scale,
        "clip_low": clip_low,
        "clip_high": clip_high,
        "gamma": gamma,
        "rose_bins": rose_bins,
        "generate_atv": _parse_bool(generate_atv, default=True),
        "generate_rose": _parse_bool(generate_rose, default=True),
        "amplitude_channel_ref": amplitude_channel_ref,
        "traveltime_channel_ref": traveltime_channel_ref,
        "angle_channel_ref": angle_channel_ref,
    }


def _with_download_urls(*, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    outputs: list[dict[str, Any]] = []
    for output in payload.get("outputs", []):
        file_names = output.get("file_names", {})
        outputs.append(
            {
                **output,
                "download_urls": {
                    "image": (
                        f"/api/dlis/download/{session_id}/{file_names['image']}"
                        if file_names.get("image")
                        else None
                    ),
                    "npz": (
                        f"/api/dlis/download/{session_id}/{file_names['npz']}"
                        if file_names.get("npz")
                        else None
                    ),
                },
            }
        )
    return {
        **payload,
        "outputs": outputs,
        "download_urls": {
            "manifest": f"/api/dlis/download/{session_id}/{payload['manifest']['name']}",
        },
    }


@router.post("/dlis/inspect")
async def inspect_dlis(
    dlis_file: Optional[UploadFile] = File(None),
    use_demo: Optional[str] = Form(None),
    reuse_session_id: Optional[str] = Form(None),
) -> JSONResponse:
    try:
        input_path, input_name, temp_dir = _prepare_dlis_input(
            dlis_file=dlis_file,
            use_demo=_parse_bool(use_demo, default=False),
            reuse_session_id=reuse_session_id,
        )
        session_id = uuid.uuid4().hex
        payload = inspect_dlis_payload(input_path, source_label=input_name)
        calculation_results[session_id] = {
            "type": "dlis",
            "temp_dir": temp_dir,
            "input_file": input_path,
            "source": input_name,
            "inspection": payload["summary"],
            "files": {},
            "download_files": {},
        }
        return _json_response(
            {
                "session_id": session_id,
                "source": input_name,
                "summary": payload["summary"],
            }
        )
    except Exception as exc:
        return _json_response({"error": f"DLIS 解析失败: {exc}"}, status_code=400)


@router.post("/dlis/render")
async def render_dlis(
    session_id: Optional[str] = Form(None),
    dlis_file: Optional[UploadFile] = File(None),
    use_demo: Optional[str] = Form(None),
    reuse_session_id: Optional[str] = Form(None),
    depth_min: Optional[str] = Form(None),
    depth_max: Optional[str] = Form(None),
    pixel_scale: Optional[str] = Form(None),
    clip_low: Optional[str] = Form(None),
    clip_high: Optional[str] = Form(None),
    gamma: Optional[str] = Form(None),
    rose_bins: Optional[str] = Form(None),
    generate_atv: Optional[str] = Form("true"),
    generate_rose: Optional[str] = Form("true"),
    amplitude_channel_ref: Optional[str] = Form(None),
    traveltime_channel_ref: Optional[str] = Form(None),
    angle_channel_ref: Optional[str] = Form(None),
) -> JSONResponse:
    try:
        current_session_id = session_id or uuid.uuid4().hex
        existing = calculation_results.get(current_session_id)
        if existing and existing.get("type") == "dlis" and existing.get("input_file"):
            input_path = str(existing["input_file"])
            input_name = str(existing.get("source") or Path(input_path).name)
            temp_dir = str(existing.get("temp_dir") or tempfile.mkdtemp(prefix="dlis_render_"))
        else:
            input_path, input_name, temp_dir = _prepare_dlis_input(
                dlis_file=dlis_file,
                use_demo=_parse_bool(use_demo, default=False),
                reuse_session_id=reuse_session_id,
            )

        output_dir = os.path.join(temp_dir, "outputs")
        os.makedirs(output_dir, exist_ok=True)
        options = _render_options_from_form(
            depth_min=depth_min,
            depth_max=depth_max,
            pixel_scale=pixel_scale,
            clip_low=clip_low,
            clip_high=clip_high,
            gamma=gamma,
            rose_bins=rose_bins,
            generate_atv=generate_atv,
            generate_rose=generate_rose,
            amplitude_channel_ref=amplitude_channel_ref,
            traveltime_channel_ref=traveltime_channel_ref,
            angle_channel_ref=angle_channel_ref,
        )
        payload = render_dlis_payload(
            file_path=input_path,
            input_name=input_name,
            output_dir=output_dir,
            session_id=current_session_id,
            options=options,
        )
        payload_with_urls = _with_download_urls(session_id=current_session_id, payload=payload)
        calculation_results[current_session_id] = {
            "type": "dlis",
            "temp_dir": temp_dir,
            "input_file": input_path,
            "source": input_name,
            "inspection": payload["inspection"],
            "options": payload["options"],
            "files": {
                "manifest": payload["manifest"],
                "outputs": payload["outputs"],
            },
            "download_files": payload["download_map"],
        }
        return _json_response(
            {
                "session_id": current_session_id,
                "source": input_name,
                "summary": payload["inspection"],
                "options": payload["options"],
                "outputs": payload_with_urls["outputs"],
                "download_urls": payload_with_urls["download_urls"],
            }
        )
    except Exception as exc:
        return _json_response({"error": f"DLIS 渲染失败: {exc}"}, status_code=400)


@router.get("/dlis/download/{session_id}/{filename}")
async def download_dlis_output(session_id: str, filename: str):
    data = calculation_results.get(session_id)
    if data is None:
        return _json_response({"error": "未找到对应会话。"}, status_code=404)
    if data.get("type") != "dlis":
        return _json_response({"error": "会话类型不匹配。"}, status_code=400)

    allowed = data.get("download_files", {})
    path = allowed.get(filename)
    if not path or not os.path.exists(path):
        return _json_response({"error": "文件不存在。"}, status_code=404)
    return FileResponse(path, filename=filename)
