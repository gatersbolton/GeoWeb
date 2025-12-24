from typing import Optional

import base64
import os
import shutil
import tempfile
import uuid
from io import BytesIO

import numpy as np
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image

from ..core.paths import stick_pull_demo_image
from ..core.progress import calculation_results
from ..thirdparty.stickpull import fix_stick_pull

router = APIRouter()

ALLOWED_ALGOS = {
    "stick-and-pull": "Stick & Pull 去伪影",
}


@router.post('/augmentation/run')
async def run_augmentation(
    algorithm: str = Form('stick-and-pull'),
    image_file: Optional[UploadFile] = File(None),
    use_demo: Optional[str] = Form(None)
):
    if algorithm not in ALLOWED_ALGOS:
        return JSONResponse(
            status_code=400,
            content={'error': f'不支持的算法: {algorithm}'}
        )

    temp_dir = tempfile.mkdtemp()
    output_dir = os.path.join(temp_dir, 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    session_id = str(uuid.uuid4())

    try:
        if use_demo == 'true':
            image_path = stick_pull_demo_image()
            if not os.path.exists(image_path):
                return JSONResponse(
                    status_code=404,
                    content={'error': '默认示例图片不存在，请检查 geo-core 目录'}
                )
            source_label = 'demo_image'
        else:
            if image_file is None:
                return JSONResponse(
                    status_code=400,
                    content={'error': '请上传输入图片或选择使用默认图片'}
                )
            _, ext = os.path.splitext(image_file.filename or '')
            if not ext:
                ext = '.png'
            image_path = os.path.join(temp_dir, f'input_image{ext}')
            with open(image_path, 'wb') as f:
                shutil.copyfileobj(image_file.file, f)
            source_label = image_file.filename or 'uploaded_image'

        corrected_rgb, depth_axis, speed_rel = fix_stick_pull(
            image_path=image_path,
            speed_csv=None,
            show=False,
            save_path=None
        )

        image_out = os.path.join(output_dir, 'stick_pull_fixed.png')
        Image.fromarray(corrected_rgb).save(image_out)

        csv_out = os.path.join(output_dir, 'stick_pull_profile.csv')
        df = pd.DataFrame({
            'row_index': np.arange(len(depth_axis), dtype=np.int64),
            'depth_norm': depth_axis,
            'speed_rel': speed_rel,
        })
        df.to_csv(csv_out, index=False)

        buf = BytesIO()
        Image.fromarray(corrected_rgb).save(buf, format='PNG')
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        data_url = f'data:image/png;base64,{img_base64}'

        calculation_results[session_id] = {
            'type': 'augmentation',
            'algorithm': algorithm,
            'temp_dir': temp_dir,
            'output_dir': output_dir,
            'files': {
                'image': image_out,
                'csv': csv_out,
            },
            'source': source_label
        }

        return JSONResponse(content={
            'session_id': session_id,
            'algorithm': algorithm,
            'source': source_label,
            'output_image': data_url,
            'download_urls': {
                'image': f'/api/augmentation/download/{session_id}/stick_pull_fixed.png',
                'csv': f'/api/augmentation/download/{session_id}/stick_pull_profile.csv'
            }
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'error': f'处理失败: {str(e)}'}
        )


@router.get('/augmentation/download/{session_id}/{filename}')
async def download_augmentation_output(session_id: str, filename: str):
    if session_id not in calculation_results:
        return JSONResponse(status_code=404, content={'error': '未找到对应会话'})
    data = calculation_results[session_id]
    if data.get('type') != 'augmentation':
        return JSONResponse(status_code=400, content={'error': '会话类型不匹配'})

    allowed = {
        'stick_pull_fixed.png': data['files'].get('image'),
        'stick_pull_profile.csv': data['files'].get('csv'),
    }
    if filename not in allowed:
        return JSONResponse(status_code=404, content={'error': '文件不存在'})

    file_path = allowed[filename]
    if not file_path or not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={'error': '文件不存在'})

    return FileResponse(file_path, filename=filename)
