from typing import Optional

import os
import shutil
import tempfile
import uuid

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse

from ..core.paths import stressinv_data_dir
from ..core.progress import calculation_results, progress_messages, executor
from ..thirdparty.stressinv import invert_global, invert_depthwise
from ..services.stressinv import run_stressinv_with_progress

router = APIRouter()


@router.post('/stressinv/run')
async def run_stress_inversion(
    ellip_traj_file: Optional[UploadFile] = File(None, description="含测深、椭圆参数与井轨迹的CSV"),
    mode: str = Form('global', description="global 或 depthwise"),
    dz: Optional[float] = Form(None, description="分段反演窗口厚度，单位与CSV深度单位一致"),
    sample_stride: Optional[int] = Form(None, description="全局反演采样跨距，>=1"),
    use_demo: Optional[str] = Form(None, description="true 使用演示数据")
):
    """
    地应力反演：
    - 输入为椭圆参数拼接井轨迹的CSV（示例：ellipticity_parameters_outlier_filtered_dz0.025m_borehole_trajectory.csv）
    - 提供全局（global）与分段（depthwise）两种模式
    - 支持勾选示例数据或用户自定义上传
    """
    try:
        session_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, 'outputs')
        os.makedirs(output_dir, exist_ok=True)

        # 选择输入CSV
        if use_demo == 'true':
            demo_dir = stressinv_data_dir()
            input_path = os.path.join(
                demo_dir,
                'ST1_20210305_borehole_ellipticity_outputs',
                'ellipticity_parameters_outlier_filtered_dz0.025m_borehole_trajectory.csv'
            )
            if not os.path.exists(input_path):
                return JSONResponse(
                    status_code=404,
                    content={'error': '演示数据文件不存在，请检查 stress inversion 数据目录'}
                )
            source_label = 'demo_data'
        else:
            if ellip_traj_file is None:
                return JSONResponse(
                    status_code=400,
                    content={'error': '必须上传带井轨迹的椭圆参数CSV或选择使用演示数据'}
                )
            input_path = os.path.join(temp_dir, 'ellip_traj.csv')
            with open(input_path, 'wb') as f:
                shutil.copyfileobj(ellip_traj_file.file, f)
            source_label = ellip_traj_file.filename or 'uploaded.csv'

        # 运行反演
        if mode not in ('global', 'depthwise'):
            return JSONResponse(status_code=400, content={'error': 'mode 仅支持 global 或 depthwise'})

        if mode == 'global':
            stride = 1 if (sample_stride is None or sample_stride < 1) else int(sample_stride)
            mat_name = 'EllipseStressInv_py.mat'
            output_mat = os.path.join(output_dir, mat_name)
            out = invert_global(input_filename=input_path, output_filename=output_mat, sample_stride=stride)

            # 结果JSON路径（由库内部一并保存）
            output_json = os.path.splitext(output_mat)[0] + '.json'

            # 简要摘要
            best = None
            try:
                import numpy as np  # 局部导入
                if isinstance(out, dict) and 'Rank_Top40' in out and out['Rank_Top40'] is not None:
                    arr = out['Rank_Top40']
                    if isinstance(arr, np.ndarray) and arr.size >= 6:
                        best = {
                            'a': float(arr[0, 0]),
                            'b': float(arr[0, 1]),
                            'c': float(arr[0, 2]),
                            'phi': float(arr[0, 3]),
                            's3': float(arr[0, 4]),
                            'rmse': float(arr[0, 5]),
                        }
            except Exception:
                pass

            calculation_results[session_id] = {
                'type': 'stressinv',
                'mode': mode,
                'temp_dir': temp_dir,
                'output_dir': output_dir,
                'files': {
                    'mat': output_mat,
                    'json': output_json
                }
            }

            return JSONResponse(content={
                'session_id': session_id,
                'mode': mode,
                'source': source_label,
                'summary': {'best': best},
                'download_urls': {
                    'result_mat': f'/stressinv/download/{session_id}/EllipseStressInv_py.mat',
                    'result_json': f'/stressinv/download/{session_id}/EllipseStressInv_py.json'
                }
            })

        else:
            # depthwise
            dz_val = 25.0 if dz is None else float(dz)
            mat_name = f'EllipseStressInv_win{int(dz_val)}m_py.mat'
            output_mat = os.path.join(output_dir, mat_name)
            out_list = invert_depthwise(input_filename=input_path, output_filename=output_mat, dz=dz_val)

            output_json = os.path.splitext(output_mat)[0] + '.json'

            # 简要摘要
            win_cnt = len(out_list) if isinstance(out_list, list) else 0

            calculation_results[session_id] = {
                'type': 'stressinv',
                'mode': mode,
                'dz': dz_val,
                'temp_dir': temp_dir,
                'output_dir': output_dir,
                'files': {
                    'mat': output_mat,
                    'json': output_json
                }
            }

            return JSONResponse(content={
                'session_id': session_id,
                'mode': mode,
                'source': source_label,
                'summary': {'window_count': win_cnt, 'dz': dz_val},
                'download_urls': {
                    'result_mat': f'/stressinv/download/{session_id}/{mat_name}',
                    'result_json': f'/stressinv/download/{session_id}/{os.path.splitext(mat_name)[0]}.json'
                }
            })

    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'反演失败: {str(e)}'})


@router.get('/stressinv/download/{session_id}/{filename}')
async def download_inversion_output(session_id: str, filename: str):
    if session_id not in calculation_results:
        return JSONResponse(status_code=404, content={'error': '未找到对应会话'})
    data = calculation_results[session_id]
    if data.get('type') != 'stressinv':
        return JSONResponse(status_code=400, content={'error': '会话类型不匹配'})

    output_dir = data['output_dir']

    # 允许下载的文件集合
    allowed = {
        'EllipseStressInv_py.mat',
        'EllipseStressInv_py.json',
    }
    # depthwise 动态文件名
    if data.get('mode') == 'depthwise' and 'dz' in data:
        z = int(data['dz'])
        allowed.add(f'EllipseStressInv_win{z}m_py.mat')
        allowed.add(f'EllipseStressInv_win{z}m_py.json')

    if filename not in allowed:
        return JSONResponse(status_code=404, content={'error': '文件不存在'})

    file_path = os.path.join(output_dir, filename if filename.endswith('.mat') else filename)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={'error': '文件不存在'})

    return FileResponse(file_path, filename=filename)


@router.post('/stressinv/run_async')
async def run_stress_inversion_async(
    ellip_traj_file: Optional[UploadFile] = File(None, description="含测深、椭圆参数与井轨迹的CSV"),
    mode: str = Form('global'),
    dz: Optional[float] = Form(None),
    sample_stride: Optional[int] = Form(None),
    use_demo: Optional[str] = Form(None)
):
    """启动异步地应力反演任务，返回 session_id，并可通过 /stressinv/progress/{session_id} 轮询进度"""
    try:
        session_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, 'outputs')
        os.makedirs(output_dir, exist_ok=True)

        # 选择输入CSV
        if use_demo == 'true':
            demo_dir = stressinv_data_dir()
            input_path = os.path.join(
                demo_dir,
                'ST1_20210305_borehole_ellipticity_outputs',
                'ellipticity_parameters_outlier_filtered_dz0.025m_borehole_trajectory.csv'
            )
            if not os.path.exists(input_path):
                return JSONResponse(
                    status_code=404,
                    content={'error': '演示数据文件不存在，请检查 stress inversion 数据目录'}
                )
        else:
            if ellip_traj_file is None:
                return JSONResponse(
                    status_code=400,
                    content={'error': '必须上传带井轨迹的椭圆参数CSV或选择使用演示数据'}
                )
            input_path = os.path.join(temp_dir, 'ellip_traj.csv')
            with open(input_path, 'wb') as f:
                shutil.copyfileobj(ellip_traj_file.file, f)

        # 异步执行
        task_kwargs = {
            'mode': mode,
            'input_path': input_path,
            'output_dir': output_dir,
        }
        if dz is not None:
            task_kwargs['dz'] = float(dz)
        if sample_stride is not None:
            task_kwargs['sample_stride'] = int(sample_stride)

        def task_wrapper():
            res = run_stressinv_with_progress(session_id, task_kwargs)
            if res.get('success'):
                calculation_results[session_id] = {
                    'type': 'stressinv',
                    'mode': res.get('mode'),
                    'dz': res.get('dz'),
                    'temp_dir': temp_dir,
                    'output_dir': output_dir,
                    'files': res.get('files'),
                    'result': res.get('out')
                }
            else:
                calculation_results[session_id] = {
                    'type': 'stressinv',
                    'error': res.get('message', '任务失败')
                }

        executor.submit(task_wrapper)

        return JSONResponse(content={
            'session_id': session_id,
            'status': 'started',
            'message': '任务已启动，请轮询进度接口获取进展'
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'启动失败: {str(e)}'})


@router.get('/stressinv/progress/{session_id}')
async def get_stressinv_progress(session_id: str):
    if session_id in progress_messages:
        p = progress_messages[session_id]
        return JSONResponse(content={
            'type': 'progress',
            'message': p['message'],
            'percentage': p['percentage'],
            'timestamp': p['timestamp']
        })
    return JSONResponse(status_code=404, content={'error': '找不到对应的计算任务'})


@router.get('/stressinv/result/{session_id}')
async def get_stressinv_result(session_id: str):
    if session_id not in calculation_results:
        return JSONResponse(status_code=404, content={'error': '找不到对应的计算结果'})
    data = calculation_results[session_id]
    if data.get('type') != 'stressinv':
        return JSONResponse(status_code=400, content={'error': '会话类型不匹配'})
    if 'error' in data:
        return JSONResponse(status_code=500, content={'error': data['error']})

    files = data.get('files', {})
    mode = data.get('mode')
    dz = data.get('dz')

    # 组装下载链接
    if mode == 'global':
        download = {
            'result_mat': f'/stressinv/download/{session_id}/EllipseStressInv_py.mat',
            'result_json': f'/stressinv/download/{session_id}/EllipseStressInv_py.json',
        }
        summary = {'mode': mode}
    else:
        download = {
            'result_mat': f'/stressinv/download/{session_id}/EllipseStressInv_win{int(dz)}m_py.mat',
            'result_json': f'/stressinv/download/{session_id}/EllipseStressInv_win{int(dz)}m_py.json',
        }
        summary = {'mode': mode, 'dz': dz}

    return JSONResponse(content={
        'session_id': session_id,
        'mode': mode,
        'summary': summary,
        'download_urls': download,
    })


