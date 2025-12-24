from typing import Optional

import asyncio
import base64
import os
import shutil
import tempfile
import uuid
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse

from ..core.paths import borehole_data_dir
from ..core.progress import (
    manager,
    executor,
    calculation_results,
    progress_messages,
)
from ..services.borehole import run_borehole_calculation_with_progress
from ..thirdparty.borehole_ellip import (
    process_borehole_ellipticity,
    generate_enhanced_plots,
)

router = APIRouter()


@router.post('/process')
async def process_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file, header=None)
    col0 = df.iloc[:, 0]
    total = col0.sum()

    plt.figure()
    col0.plot(kind='line')
    plt.title('Column 0 Line Plot')
    plt.xlabel('Index')
    plt.ylabel('Value')
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    data_url = f'data:image/png;base64,{img_base64}'
    return JSONResponse(content={'sum': float(total), 'plot': data_url})


@router.get("/borehole/progress/{session_id}")
async def get_progress(session_id: str):
    if session_id in progress_messages:
        progress_data = progress_messages[session_id]
        return JSONResponse(content={
            "type": "progress",
            "message": progress_data['message'],
            "percentage": progress_data['percentage'],
            "timestamp": progress_data['timestamp']
        })
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "找不到对应的计算任务"}
        )


@router.websocket("/ws/progress/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id)


@router.post('/borehole/calculate_async')
async def calculate_borehole_ellipticity_async(
    tt_file: Optional[UploadFile] = None,
    wtt_file: Optional[UploadFile] = None,
    mask_file: Optional[UploadFile] = None,
    rp: float = Form(...),
    vf: float = Form(...),
    wtt: Optional[float] = Form(None),
    beta: Optional[float] = Form(None),
    use_demo: Optional[str] = Form(None)
):
    try:
        session_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, 'outputs')

        calc_kwargs = {
            'rp': rp,
            'vf': vf,
            'wtt': wtt,
            'beta': beta,
            'dir_out': output_dir
        }

        if use_demo == 'true':
            demo_data_dir = borehole_data_dir()
            tt_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_TT_NM.csv')
            wtt_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_WNDTIME.csv')
            if not os.path.exists(tt_path):
                return JSONResponse(
                    status_code=404,
                    content={'error': '演示数据文件不存在，请检查数据目录'}
                )
            calc_kwargs.update({
                'fp_tt': tt_path,
                'fp_wtt': wtt_path,
                'fp_mask': None
            })
        else:
            if tt_file is None:
                return JSONResponse(
                    status_code=400,
                    content={'error': 'ATV旅行时间文件是必需的'}
                )
            tt_path = os.path.join(temp_dir, 'tt_data.csv')
            with open(tt_path, 'wb') as f:
                shutil.copyfileobj(tt_file.file, f)
            calc_kwargs['fp_tt'] = tt_path

            if wtt_file is not None:
                wtt_path = os.path.join(temp_dir, 'wtt_data.csv')
                with open(wtt_path, 'wb') as f:
                    shutil.copyfileobj(wtt_file.file, f)
                calc_kwargs['fp_wtt'] = wtt_path

            if mask_file is not None:
                mask_path = os.path.join(temp_dir, 'mask_data.csv')
                with open(mask_path, 'wb') as f:
                    shutil.copyfileobj(mask_file.file, f)
                calc_kwargs['fp_mask'] = mask_path

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            executor,
            run_borehole_calculation_with_progress,
            session_id,
            calc_kwargs
        )

        async def handle_result():
            try:
                result = await future
                if result['success']:
                    calculation_results[session_id] = {
                        'result': result,
                        'temp_dir': temp_dir,
                        'output_dir': output_dir,
                        'use_demo': use_demo == 'true'
                    }
                    await manager.send_progress(session_id, {
                        "type": "completed",
                        "message": "计算完成！",
                        "session_id": session_id,
                        "percentage": 100
                    })
                else:
                    await manager.send_progress(session_id, {
                        "type": "error",
                        "message": result.get('message', '计算失败'),
                        "percentage": None
                    })
            except Exception as e:
                await manager.send_progress(session_id, {
                    "type": "error",
                    "message": f"计算异常: {str(e)}",
                    "percentage": None
                })

        asyncio.create_task(handle_result())

        return JSONResponse(content={
            'session_id': session_id,
            'status': 'started',
            'message': '计算已开始，请通过WebSocket连接监控进度',
            'websocket_url': f'/ws/progress/{session_id}'
        })

    except Exception as e:
        print(f"启动计算失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={'error': f'启动计算失败: {str(e)}'}
        )


@router.get('/borehole/result/{session_id}')
async def get_calculation_result(session_id: str):
    if session_id not in calculation_results:
        return JSONResponse(
            status_code=404,
            content={'error': '找不到对应的计算结果'}
        )
    try:
        stored_data = calculation_results[session_id]
        result = stored_data['result']
        param = result['data']['param']
        valid_idx = ~np.isnan(param[:, 1])
        return JSONResponse(content={
            'session_id': session_id,
            'processing_info': {
                'depth_count': result['processing_info']['total_depths'],
                'azimuth_count': result['processing_info']['azimuth_count'],
                'valid_depths': result['processing_info']['valid_results'],
                'depth_range': result['processing_info']['depth_range'],
                'depth_unit': result['processing_info']['depth_unit'],
                'traveltime_unit': result['processing_info']['traveltime_unit']
            },
            'results_summary': {
                'total_depths': len(param),
                'valid_results': int(valid_idx.sum()),
                'avg_major_axis': float(np.nanmean(param[:, 1])) if valid_idx.any() else 0,
                'avg_minor_axis': float(np.nanmean(param[:, 2])) if valid_idx.any() else 0,
                'avg_ellipticity_ratio': float(np.nanmean(param[:, 1] / param[:, 2])) if valid_idx.any() else 0,
                'avg_fitting_error': float(np.nanmean(param[:, -1])) if valid_idx.any() else 0
            },
            'download_urls': {
                'ellipticity_parameters': f'/api/borehole/download/{session_id}/ellipticity_parameters.csv',
                'centralized_traveltime': f'/api/borehole/download/{session_id}/centralized_traveltime.csv',
                'borehole_radius': f'/api/borehole/download/{session_id}/borehole_radius.csv',
                'borehole_azimuths': f'/api/borehole/download/{session_id}/borehole_azimuths.csv'
            }
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'error': f'获取结果失败: {str(e)}'}
        )


@router.post('/borehole/calculate')
async def calculate_borehole_ellipticity(
    tt_file: Optional[UploadFile] = None,
    wtt_file: Optional[UploadFile] = None,
    mask_file: Optional[UploadFile] = None,
    rp: float = Form(...),
    vf: float = Form(...),
    wtt: Optional[float] = Form(None),
    beta: Optional[float] = Form(None),
    use_demo: Optional[str] = Form(None)
):
    try:
        print("开始计算钻孔椭圆度数据...")
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, 'outputs')
        session_id = str(uuid.uuid4())

        try:
            if use_demo == 'true':
                print("使用默认演示数据...")
                demo_data_dir = borehole_data_dir()
                tt_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_TT_NM.csv')
                wtt_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_WNDTIME.csv')
                mask_path = None
                if not os.path.exists(tt_path):
                    return JSONResponse(
                        status_code=404,
                        content={'error': '演示数据文件不存在，请检查数据目录'}
                    )
            else:
                if tt_file is None:
                    return JSONResponse(
                        status_code=400,
                        content={'error': 'ATV旅行时间文件是必需的'}
                    )
                tt_file.file.seek(0, 2)
                file_size = tt_file.file.tell()
                tt_file.file.seek(0)
                print(f"处理文件: {tt_file.filename}, 大小: {file_size / (1024*1024):.2f} MB")
                if file_size > 500 * 1024 * 1024:
                    return JSONResponse(
                        status_code=413,
                        content={'error': f'文件过大 ({file_size / (1024*1024):.2f} MB)，请上传小于500MB的文件'}
                    )
                tt_path = os.path.join(temp_dir, 'tt_data.csv')
                with open(tt_path, 'wb') as f:
                    shutil.copyfileobj(tt_file.file, f)
                wtt_path = None
                if wtt_file is not None:
                    wtt_path = os.path.join(temp_dir, 'wtt_data.csv')
                    with open(wtt_path, 'wb') as f:
                        shutil.copyfileobj(wtt_file.file, f)
                mask_path = None
                if mask_file is not None:
                    mask_path = os.path.join(temp_dir, 'mask_data.csv')
                    with open(mask_path, 'wb') as f:
                        shutil.copyfileobj(mask_file.file, f)

            print("调用 borehole ellipticity 处理函数...")
            result = process_borehole_ellipticity(
                fp_tt=tt_path,
                fp_wtt=wtt_path,
                wtt=wtt,
                rp=rp,
                vf=vf,
                beta=beta,
                fp_mask=mask_path,
                dir_out=output_dir
            )

            if not result['success']:
                # 避免 f-string 中转义字符问题，先取出消息
                err_msg = result.get("message", "未知错误")
                return JSONResponse(
                    status_code=500,
                    content={'error': f'处理失败: {err_msg}'}
                )

            param = result['data']['param']
            valid_idx = ~np.isnan(param[:, 1])

            calculation_results[session_id] = {
                'result': result,
                'temp_dir': temp_dir,
                'output_dir': output_dir,
                'use_demo': use_demo == 'true'
            }

            print("计算完成!")
            return JSONResponse(content={
                'session_id': session_id,
                'processing_info': {
                    'depth_count': result['processing_info']['total_depths'],
                    'azimuth_count': result['processing_info']['azimuth_count'],
                    'valid_depths': result['processing_info']['valid_results'],
                    'depth_range': result['processing_info']['depth_range'],
                    'depth_unit': result['processing_info']['depth_unit'],
                    'traveltime_unit': result['processing_info']['traveltime_unit'],
                    'rp': rp,
                    'vf': vf,
                    'wtt': wtt,
                    'beta': beta,
                    'files_processed': {
                        'tt_file': tt_file.filename if tt_file else 'demo_data',
                        'wtt_file': wtt_file.filename if wtt_file else 'demo_data' if use_demo == 'true' else None,
                        'mask_file': mask_file.filename if mask_file else None
                    }
                },
                'results_summary': {
                    'total_depths': result['processing_info']['total_depths'],
                    'valid_results': result['processing_info']['valid_results'],
                    'avg_major_axis': float(np.nanmean(param[:, 3])) if np.sum(valid_idx) > 0 else 0,
                    'avg_minor_axis': float(np.nanmean(param[:, 4])) if np.sum(valid_idx) > 0 else 0,
                    'avg_ellipticity_ratio': float(np.nanmean(param[valid_idx, 3] / param[valid_idx, 4])) if np.sum(valid_idx) > 0 else 0,
                    'avg_fitting_error': float(np.nanmean(param[:, 7])) if np.sum(valid_idx) > 0 else 0
                },
                'output_files': result['output_files'],
                'download_urls': {
                    'ellipticity_parameters': f'/borehole/download/{session_id}/ellipticity_parameters.csv',
                    'centralized_traveltime': f'/borehole/download/{session_id}/centralized_traveltime.csv',
                    'borehole_radius': f'/borehole/download/{session_id}/borehole_radius.csv',
                    'borehole_azimuths': f'/borehole/download/{session_id}/borehole_azimuths.csv'
                }
            })

        except Exception as e:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            raise e

    except Exception as e:
        error_msg = str(e)
        print(f"计算错误: {error_msg}")
        if "memory" in error_msg.lower() or "memoryerror" in error_msg.lower():
            return JSONResponse(
                status_code=413,
                content={'error': '文件过大导致内存不足，请尝试上传较小的文件'}
            )
        elif "csv" in error_msg.lower() or "parse" in error_msg.lower() or "read_csv" in error_msg.lower():
            return JSONResponse(
                status_code=400,
                content={'error': f'CSV文件格式错误: {error_msg}'}
            )
        elif "permission" in error_msg.lower():
            return JSONResponse(
                status_code=500,
                content={'error': '服务器文件权限错误，请联系管理员'}
            )
        elif "process_borehole_ellipticity" in error_msg:
            return JSONResponse(
                status_code=500,
                content={'error': f'钻孔椭圆度处理算法错误: {error_msg}'}
            )
        else:
            return JSONResponse(
                status_code=500,
                content={'error': f'处理过程中发生错误: {error_msg}'}
            )


@router.post('/borehole/visualize')
async def visualize_borehole_ellipticity(
    session_id: str = Form(...),
    amp_file: Optional[UploadFile] = None,
    inc_file: Optional[UploadFile] = None,
    azi_file: Optional[UploadFile] = None,
    dz: Optional[float] = Form(None),
    lenZ: float = Form(5),
    cmapAmp: str = Form('gray'),
    cmapRad: str = Form('gray_r'),
    use_viz_demo: Optional[str] = Form(None),
    zTop: Optional[float] = Form(None),
    zCenter: Optional[float] = Form(None),
    quality: str = Form('final')
):
    try:
        print(f"收到可视化请求 - session_id: {session_id}")
        print(f"可视化参数 - dz: {dz}, lenZ: {lenZ}, zTop: {zTop}, zCenter: {zCenter}, quality: {quality}")
        print(f"上传文件 - amp_file: {amp_file.filename if amp_file else None}, inc_file: {inc_file.filename if inc_file else None}, azi_file: {azi_file.filename if azi_file else None}")
        print(f"当前存储的计算结果: {list(calculation_results.keys())}")

        if session_id not in calculation_results:
            return JSONResponse(
                status_code=404,
                content={'error': '未找到计算结果，请先进行椭圆度计算'}
            )

        calc_data = calculation_results[session_id]
        result = calc_data['result']
        temp_dir = calc_data['temp_dir']
        output_dir = calc_data['output_dir']
        use_demo = calc_data['use_demo']

        try:
            viz_files = {}
            if use_viz_demo == 'true' or (use_demo and use_viz_demo != 'false'):
                demo_data_dir = borehole_data_dir()
                viz_files['amp_path'] = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_AMP_NM.csv')
                viz_files['inc_path'] = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_TILT.csv')
                viz_files['azi_path'] = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_AZIMUTH.csv')
                print("使用演示数据进行可视化...")
                calc_data['viz_files'] = viz_files
            else:
                cached = calc_data.get('viz_files', {})
                viz_files.update(cached)

                updated = False
                if amp_file is not None:
                    viz_files['amp_path'] = os.path.join(temp_dir, 'amp_data.csv')
                    with open(viz_files['amp_path'], 'wb') as f:
                        shutil.copyfileobj(amp_file.file, f)
                    updated = True
                if inc_file is not None:
                    viz_files['inc_path'] = os.path.join(temp_dir, 'inc_data.csv')
                    with open(viz_files['inc_path'], 'wb') as f:
                        shutil.copyfileobj(inc_file.file, f)
                    updated = True
                if azi_file is not None:
                    viz_files['azi_path'] = os.path.join(temp_dir, 'azi_data.csv')
                    with open(viz_files['azi_path'], 'wb') as f:
                        shutil.copyfileobj(azi_file.file, f)
                    updated = True
                if updated:
                    calc_data['viz_files'] = viz_files

            print("生成可视化图表...")
            plots = generate_enhanced_plots(
                ellip_dir=output_dir,
                amp_path=viz_files.get('amp_path'),
                inc_path=viz_files.get('inc_path'),
                azi_path=viz_files.get('azi_path'),
                dz=dz,
                lenZ=lenZ,
                cmapAmp=cmapAmp,
                cmapRad=cmapRad,
                zTop=zTop,
                zCenter=zCenter,
                quality=quality
            )

            if not plots.get('ellipticity_plot'):
                print("警告: 椭圆度图表生成失败")

            print("可视化完成!")
            return JSONResponse(content={
                'ellipticity_plot': plots.get('ellipticity_plot', ''),
                'orientation_plot': plots.get('orientation_plot', ''),
                'cross_section_plot': plots.get('cross_section_plot', ''),
                'radius_plot': plots.get('radius_plot', ''),
                'meta': plots.get('meta', None),
                'visualization_info': {
                    'dz': dz,
                    'lenZ': lenZ,
                    'cmapAmp': cmapAmp,
                    'cmapRad': cmapRad,
                    'window': plots.get('meta', {}).get('window') if plots.get('meta') else None,
                    'files_used': {
                        'amp': viz_files.get('amp_path'),
                        'inc': viz_files.get('inc_path'),
                        'azi': viz_files.get('azi_path')
                    }
                }
            })
        finally:
            pass
    except Exception as e:
        error_msg = str(e)
        print(f"可视化错误: {error_msg}")
        return JSONResponse(
            status_code=500,
            content={'error': f'可视化生成过程中发生错误: {error_msg}'}
        )


@router.get('/borehole/download/{session_id}/{filename}')
async def download_result_file(session_id: str, filename: str):
    if session_id not in calculation_results:
        return JSONResponse(
            status_code=404,
            content={'error': '未找到计算结果'}
        )
    calc_data = calculation_results[session_id]
    output_dir = calc_data['output_dir']
    file_mapping = {
        'ellipticity_parameters.csv': 'ellipticity_parameters.csv',
        'centralized_traveltime.csv': 'centralized_traveltime.csv',
        'borehole_radius.csv': 'borehole_radius.csv',
        'borehole_azimuths.csv': 'borehole_cross_section_azimuths.csv'
    }
    if filename not in file_mapping:
        return JSONResponse(
            status_code=404,
            content={'error': '文件不存在'}
        )
    file_path = os.path.join(output_dir, file_mapping[filename])
    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404,
            content={'error': '文件不存在'}
        )
    return FileResponse(file_path, filename=filename)


