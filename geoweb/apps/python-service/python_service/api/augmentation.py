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

from ..core.paths import ensure_geo_core_path, groovemask_demo_image, stick_pull_demo_image
from ..core.progress import calculation_results

ensure_geo_core_path()

from algorithms.api.runtime import REGISTRY
from algorithms.core.data_models import InputFrame, PipelineStep, RunContext
from algorithms.core.pipeline import PipelineExecutor
from algorithms.core.utils.io import build_output_filename, save_npz
from algorithms.core.utils.metadata import build_minimal_metadata

router = APIRouter()

ALGORITHM_SPECS: dict[str, dict[str, Any]] = {
    "stick-and-pull": {
        "label": "Stick & Pull 去伪影",
        "algo_id": "artifact.stick_pull.v1",
        "demo_path": stick_pull_demo_image,
        "default_config_patch": {
            "experimental": {
                "enable_preview_assets": False,
                "save_speed_profile_csv": True,
            }
        },
    },
    "groovemask": {
        "label": "GrooveMask 槽沟去伪影",
        "algo_id": "artifact.groovemask.v1",
        "demo_path": groovemask_demo_image,
        "default_config_patch": {
            "experimental": {
                "enable_preview_assets": True,
                "save_auxiliary_assets": True,
                "save_debug_assets": False,
            }
        },
    },
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _json_response(content: dict[str, Any], *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=content)


def _parse_config_json(raw: Optional[str]) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"配置 JSON 解析失败: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("config_json 必须是 JSON 对象。")
    return payload


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _infer_value_range(array: np.ndarray) -> list[float]:
    data = np.asarray(array, dtype=np.float32)
    if data.size == 0:
        return [0.0, 1.0]
    if 0.0 <= float(np.nanmin(data)) and float(np.nanmax(data)) <= 1.5:
        return [0.0, 1.0]
    return [float(np.nanmin(data)), float(np.nanmax(data))]


def _load_uploaded_image(file_path: str) -> tuple[np.ndarray, str, list[float]]:
    image = Image.open(file_path)
    if image.mode in {"L", "I;16", "I", "F"}:
        matrix = np.asarray(image, dtype=np.float32)
        return matrix, "HW", _infer_value_range(matrix)
    if image.mode == "RGBA":
        rgba = np.asarray(image.convert("RGBA"), dtype=np.float32)
        return rgba, "HWC", [0.0, 255.0]
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    return rgb, "HWC", [0.0, 255.0]


def _to_png_uint8(array: np.ndarray) -> np.ndarray:
    data = np.asarray(array, dtype=np.float32)
    if data.ndim == 3 and data.shape[0] in (1, 3, 4) and data.shape[2] not in (1, 3, 4):
        data = np.transpose(data, (1, 2, 0))
    if data.ndim == 3 and data.shape[2] == 1:
        data = np.repeat(data, 3, axis=2)
    if data.ndim not in (2, 3):
        raise ValueError("Unsupported output shape for image preview.")
    if float(np.nanmax(data)) <= 1.5 and float(np.nanmin(data)) >= 0.0:
        data = data * 255.0
    return np.clip(data, 0.0, 255.0).astype(np.uint8)


def _to_data_url_png(array: np.ndarray) -> str:
    image = Image.fromarray(_to_png_uint8(array))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _file_to_data_url(path: Path) -> str:
    image = Image.open(path)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _asset_title(name: str) -> str:
    lower = name.lower()
    if lower == "clean.png":
        return "清理结果"
    if lower == "mask.png":
        return "检测掩膜"
    if lower == "overlay.png":
        return "掩膜叠加图"
    if lower == "diff.png":
        return "差异热力图"
    if lower == "tracks.json":
        return "槽沟轨迹"
    if lower == "meta.json":
        return "算法元数据"
    if "speed_profile" in lower:
        return "速度曲线"
    return name


def _asset_kind(path: Path) -> str:
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return "image"
    if path.suffix.lower() == ".csv":
        return "csv"
    if path.suffix.lower() == ".json":
        return "json"
    if path.suffix.lower() == ".npz":
        return "npz"
    return "file"


def _build_output_item(
    *,
    session_id: str,
    key: str,
    title: str,
    file_path: Path,
) -> dict[str, Any]:
    item = {
        "key": key,
        "title": title,
        "kind": _asset_kind(file_path),
        "file_name": file_path.name,
        "download_url": f"/api/augmentation/download/{session_id}/{file_path.name}",
    }
    if item["kind"] == "image":
        item["output_image"] = _file_to_data_url(file_path)
    return item


def _build_main_output(
    *,
    session_id: str,
    algo_label: str,
    result_array: np.ndarray,
    file_path: Path,
) -> dict[str, Any]:
    return {
        "key": "clean",
        "title": f"{algo_label}结果",
        "kind": "image",
        "file_name": file_path.name,
        "output_image": _to_data_url_png(result_array),
        "download_url": f"/api/augmentation/download/{session_id}/{file_path.name}",
    }


def _save_main_outputs(
    *,
    session_id: str,
    output_dir: Path,
    algo_id: str,
    result_array: np.ndarray,
    source_meta: dict[str, Any],
) -> dict[str, Path]:
    png_name = build_output_filename(session_id, 1, algo_id, "png")
    npz_name = build_output_filename(session_id, 1, algo_id, "npz")
    png_path = output_dir / png_name
    npz_path = output_dir / npz_name

    Image.fromarray(_to_png_uint8(result_array)).save(png_path)
    metadata = build_minimal_metadata(
        job_id=session_id,
        created_by="augmentation-api",
        service_version="python-service.augmentation.v1",
        source_meta=source_meta,
    )
    metadata["algo_chain"] = [algo_id]
    metadata["current_algo_id"] = algo_id
    save_npz(npz_path, np.asarray(result_array, dtype=np.float32), metadata)
    return {"image": png_path, "npz": npz_path}


def _prepare_session_input(
    *,
    temp_dir: str,
    image_file: Optional[UploadFile],
    use_demo: Optional[str],
    algorithm_spec: dict[str, Any],
) -> tuple[Path, str]:
    if use_demo == "true":
        image_path = Path(algorithm_spec["demo_path"]())
        if not image_path.exists():
            raise FileNotFoundError(f"默认示例图片不存在: {image_path}")
        return image_path, "demo_image"

    if image_file is None:
        raise ValueError("请上传输入图片或选择使用默认图片")

    suffix = Path(image_file.filename or "uploaded.png").suffix or ".png"
    target_path = Path(temp_dir) / f"input{suffix}"
    with target_path.open("wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)
    return target_path, image_file.filename or "uploaded_image"


@router.post("/augmentation/run")
async def run_augmentation(
    algorithm: str = Form("stick-and-pull"),
    config_json: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    use_demo: Optional[str] = Form(None),
):
    algorithm_spec = ALGORITHM_SPECS.get(algorithm)
    if algorithm_spec is None:
        return _json_response({"error": f"不支持的算法: {algorithm}"}, status_code=400)

    temp_dir = tempfile.mkdtemp(prefix="augmentation_")
    output_dir = Path(temp_dir) / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    session_id = str(uuid.uuid4())

    try:
        input_path, source_label = _prepare_session_input(
            temp_dir=temp_dir,
            image_file=image_file,
            use_demo=use_demo,
            algorithm_spec=algorithm_spec,
        )
        image_data, layout, value_range = _load_uploaded_image(str(input_path))
        config = REGISTRY.get(algorithm_spec["algo_id"]).get_default_config()
        config = _deep_merge(config, algorithm_spec.get("default_config_patch", {}))
        config = _deep_merge(config, _parse_config_json(config_json))

        frame = InputFrame(
            data=image_data,
            data_layout=layout,
            value_range=value_range,
            source_meta={
                "filename": Path(source_label).name,
                "input_format": Path(input_path).suffix.lstrip(".").lower() or "image",
                "original_file_uri": str(input_path),
                "preprocess_ops": [],
            },
        )
        executor = PipelineExecutor(REGISTRY)
        step = PipelineStep(algo_id=algorithm_spec["algo_id"], config=config)
        pipeline_result = executor.run(
            frame,
            [step],
            RunContext(
                job_id=session_id,
                step_index=0,
                created_by="augmentation-api",
                service_version="python-service.augmentation.v1",
                output_dir=str(output_dir),
            ),
        )
        output = pipeline_result.final_output
        main_files = _save_main_outputs(
            session_id=session_id,
            output_dir=output_dir,
            algo_id=algorithm_spec["algo_id"],
            result_array=output.result,
            source_meta=frame.source_meta,
        )

        outputs: list[dict[str, Any]] = [
            _build_main_output(
                session_id=session_id,
                algo_label=algorithm_spec["label"],
                result_array=output.result,
                file_path=main_files["image"],
            )
        ]
        download_files = {
            main_files["image"].name: str(main_files["image"]),
            main_files["npz"].name: str(main_files["npz"]),
        }

        for asset_path_raw in output.preview_assets:
            asset_path = Path(asset_path_raw)
            if not asset_path.exists():
                continue
            if asset_path.name == main_files["image"].name or asset_path.name == "clean.png":
                download_files[asset_path.name] = str(asset_path)
                continue
            download_files[asset_path.name] = str(asset_path)
            outputs.append(
                _build_output_item(
                    session_id=session_id,
                    key=asset_path.stem,
                    title=_asset_title(asset_path.name),
                    file_path=asset_path,
                )
            )

        calculation_results[session_id] = {
            "type": "augmentation",
            "algorithm": algorithm,
            "algo_id": algorithm_spec["algo_id"],
            "temp_dir": temp_dir,
            "output_dir": str(output_dir),
            "source": source_label,
            "input_image": str(input_path),
            "download_files": download_files,
            "files": {
                "image": {"name": main_files["image"].name, "path": str(main_files["image"])},
                "npz": {"name": main_files["npz"].name, "path": str(main_files["npz"])},
                "outputs": outputs,
            },
            "config": config,
        }

        return _json_response(
            {
                "session_id": session_id,
                "algorithm": algorithm,
                "algo_id": algorithm_spec["algo_id"],
                "source": source_label,
                "output_image": outputs[0]["output_image"],
                "outputs": outputs,
                "quality_metrics": output.quality_metrics,
                "run_report": output.run_report.to_dict(),
                "download_urls": {
                    "image": outputs[0]["download_url"],
                    "npz": f"/api/augmentation/download/{session_id}/{main_files['npz'].name}",
                },
                "config": config,
            }
        )
    except ValueError as exc:
        return _json_response({"error": str(exc)}, status_code=400)
    except FileNotFoundError as exc:
        return _json_response({"error": str(exc)}, status_code=404)
    except Exception as exc:
        return _json_response({"error": f"处理失败: {exc}"}, status_code=500)


@router.get("/augmentation/download/{session_id}/{filename}")
async def download_augmentation_output(session_id: str, filename: str):
    data = calculation_results.get(session_id)
    if data is None:
        return _json_response({"error": "未找到对应会话"}, status_code=404)
    if data.get("type") != "augmentation":
        return _json_response({"error": "会话类型不匹配"}, status_code=400)

    download_files = data.get("download_files", {})
    file_path = download_files.get(filename)
    if not file_path or not os.path.exists(file_path):
        return _json_response({"error": "文件不存在"}, status_code=404)
    return FileResponse(file_path, filename=filename)
