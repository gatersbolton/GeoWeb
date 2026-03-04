from pathlib import Path

import numpy as np
from PIL import Image

from algorithms.api.routes_jobs import create_job, get_job_result
from algorithms.api.schemas import JobCreateRequest


def test_stick_pull_png_input_via_job_api_flow() -> None:
    image_path = (
        Path(__file__).resolve().parents[2]
        / "algorithms"
        / "artifacts"
        / "stick_pull"
        / "tests"
        / "stick_pull.png"
    )
    image = Image.open(image_path).convert("L")
    input_data = np.asarray(image, dtype=np.float32)

    created = create_job(
        JobCreateRequest(
            frame={
                "data": input_data.tolist(),
                "data_layout": "HW",
                "dtype": "float32",
                "value_range": [0, 255],
                "source_meta": {
                    "well_id": "W-IMG",
                    "input_format": "png",
                    "original_file_uri": str(image_path),
                },
            },
            pipeline=[{"algo_id": "artifact.stick_pull.v1", "config": {}}],
            created_by="integration_test",
        )
    )

    result = get_job_result(created.job_id)
    output_data = np.asarray(result.result_data, dtype=np.float32)

    assert output_data.shape == input_data.shape
    assert np.isfinite(output_data).all()
    assert np.mean(np.abs(output_data - input_data)) > 0.0
    assert len(result.npz_files) == 1
    assert Path(result.npz_files[0]).exists()
    assert result.run_report_path is not None
    assert Path(result.run_report_path).exists()
