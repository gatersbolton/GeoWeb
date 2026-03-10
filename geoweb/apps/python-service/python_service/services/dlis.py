from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from ..core.paths import ensure_geo_core_path

ensure_geo_core_path()

from algorithms.dlis.service import inspect_dlis_file, render_dlis_outputs


def inspect_dlis_payload(file_path: str | Path, *, source_label: str) -> dict[str, Any]:
    summary = inspect_dlis_file(file_path)
    return {
        "source": source_label,
        "file_name": Path(file_path).name,
        "summary": summary,
    }


def render_dlis_payload(
    *,
    file_path: str | Path,
    input_name: str,
    output_dir: str | Path,
    session_id: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rendered = render_dlis_outputs(
        path=file_path,
        job_id=session_id,
        output_dir=output_dir,
        options=options,
    )
    outputs: list[dict[str, Any]] = []
    for index, output in enumerate(rendered["outputs"], start=1):
        image_path = Path(output["image_path"])
        npz_path = Path(output["npz_path"])
        outputs.append(
            {
                "step_index": index,
                "tool_id": output["tool_id"],
                "kind": output["kind"],
                "title": output["title"],
                "summary": output["summary"],
                "shape": output["shape"],
                "metadata": output["metadata"],
                "output_image": encode_png_data_url(image_path),
                "file_names": {
                    "image": image_path.name,
                    "npz": npz_path.name,
                },
            }
        )
    return {
        "source": input_name,
        "inspection": rendered["inspection"],
        "options": rendered["options"],
        "outputs": outputs,
        "manifest": rendered["manifest"],
        "download_map": rendered["download_map"],
    }


def encode_png_data_url(path: str | Path) -> str:
    file_path = Path(path)
    encoded = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
