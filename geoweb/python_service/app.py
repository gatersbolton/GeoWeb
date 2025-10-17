from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import base64
import os
import tempfile
import shutil
import sys
from io import BytesIO
from typing import Optional
import matplotlib
import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

# 添加 borehole ellipticity 项目路径到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'python', 'Borehole ellipticity'))

# 导入现有的 borehole ellipticity 处理函数和可视化包装函数
try:
    from borehole_ellipticity import process_borehole_ellipticity
    from vis_wrapper import generate_all_plots, generate_enhanced_plots
    print("成功导入 borehole ellipticity 处理函数和可视化函数")
except ImportError as e:
    print(f"导入函数失败: {e}")
    print("请确保相关文件存在且可访问")

# 配置matplotlib使用支持中文的字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该指定具体的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/process')
async def process_csv(file: UploadFile = File(...)):
    # 读取上传文件为 DataFrame
    df = pd.read_csv(file.file, header=None)
    # 第一列求和
    col0 = df.iloc[:, 0]
    total = col0.sum()

    # 画折线图
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

    return JSONResponse(content={
        'sum': float(total),
        'plot': data_url
    })

# 存储计算结果的字典，键为session_id，值为结果数据和临时目录路径
calculation_results = {}

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_progress(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except:
                # 连接可能已断开
                self.disconnect(session_id)

manager = ConnectionManager()

# 线程池执行器用于运行计算任务
executor = ThreadPoolExecutor(max_workers=2)

# 进度回调函数
async def progress_callback(session_id: str, message: str, percentage: float = None):
    """发送进度更新消息"""
    progress_data = {
        "type": "progress",
        "message": message,
        "percentage": percentage,
        "timestamp": pd.Timestamp.now().isoformat()
    }
    await manager.send_progress(session_id, progress_data)

# 全局变量存储进度消息
progress_messages = {}
# 存储每个session的上次打印百分比
last_printed_percentage = {}

def run_borehole_calculation_with_progress(session_id: str, kwargs: dict):
    """在单独线程中运行钻孔计算，支持进度回调"""
    
    def borehole_progress_callback(message, percentage):
        # 将进度消息存储在全局字典中
        progress_messages[session_id] = {
            'message': message,
            'percentage': percentage,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        # 决定是否打印日志
        should_print = False
        
        if percentage is None:
            # 非百分比消息（如Loading, Saving等）总是打印
            should_print = True
        else:
            # 获取上次打印的百分比
            last_pct = last_printed_percentage.get(session_id, -1)
            
            # 每20%或重要消息才打印
            if (percentage - last_pct >= 20 or 
                percentage == 100 or
                'Loading' in message or 
                'Saving' in message or 
                '完成' in message or 
                '失败' in message):
                should_print = True
                last_printed_percentage[session_id] = percentage
        
        if should_print:
            print(f"进度更新 [{session_id[:8]}]: {message}")
    
    try:
        print(f"开始计算任务 [{session_id}]")
        progress_messages[session_id] = {
            'message': '开始计算钻孔椭圆度数据...',
            'percentage': 0,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        # 将进度回调传递给处理函数
        kwargs['progress_callback'] = borehole_progress_callback
        
        # 调用处理函数
        result = process_borehole_ellipticity(**kwargs)
        
        if result['success']:
            progress_messages[session_id] = {
                'message': '计算完成!',
                'percentage': 100,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            print(f"计算完成 [{session_id[:8]}]")
        else:
            progress_messages[session_id] = {
                'message': '计算失败',
                'percentage': None,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            print(f"计算失败 [{session_id[:8]}]")
        
        # 清理百分比跟踪
        if session_id in last_printed_percentage:
            del last_printed_percentage[session_id]
        
        return result
        
    except Exception as e:
        error_msg = f"计算失败: {str(e)}"
        progress_messages[session_id] = {
            'message': error_msg,
            'percentage': None,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        print(f"计算异常 [{session_id[:8]}]: {error_msg}")
        
        # 清理百分比跟踪
        if session_id in last_printed_percentage:
            del last_printed_percentage[session_id]
            
        return {'success': False, 'message': str(e)}

@app.get("/borehole/progress/{session_id}")
async def get_progress(session_id: str):
    """获取计算进度"""
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

@app.websocket("/ws/progress/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        # 保持连接活跃
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id)

@app.post('/borehole/calculate_async')
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
    """异步计算钻孔椭圆度数据"""
    
    try:
        # 生成session_id
        import uuid
        session_id = str(uuid.uuid4())
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, 'outputs')
        
        # 准备计算参数
        calc_kwargs = {
            'rp': rp,
            'vf': vf,
            'wtt': wtt,
            'beta': beta,
            'dir_out': output_dir
        }
        
        if use_demo == 'true':
            # 使用默认演示数据
            demo_data_dir = os.path.join(os.path.dirname(__file__), '..', 'python', 'Borehole ellipticity', 'data')
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
            # 使用用户上传的文件
            if tt_file is None:
                return JSONResponse(
                    status_code=400,
                    content={'error': 'ATV旅行时间文件是必需的'}
                )
            
            # 保存上传的文件到临时目录
            tt_path = os.path.join(temp_dir, 'tt_data.csv')
            with open(tt_path, 'wb') as f:
                shutil.copyfileobj(tt_file.file, f)
            
            calc_kwargs['fp_tt'] = tt_path
            
            # 处理可选文件
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
        
        # 在线程池中异步执行计算
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            executor, 
            run_borehole_calculation_with_progress,
            session_id,
            calc_kwargs  # 将kwargs作为一个参数传递
        )
        
        # 异步处理计算结果
        async def handle_result():
            try:
                result = await future
                if result['success']:
                    # 存储计算结果
                    calculation_results[session_id] = {
                        'result': result,
                        'temp_dir': temp_dir,
                        'output_dir': output_dir,
                        'use_demo': use_demo == 'true'
                    }
                    
                    # 发送完成消息
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
        
        # 启动异步任务
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

@app.get('/borehole/result/{session_id}')
async def get_calculation_result(session_id: str):
    """获取计算结果"""
    if session_id not in calculation_results:
        return JSONResponse(
            status_code=404,
            content={'error': '找不到对应的计算结果'}
        )
    
    try:
        stored_data = calculation_results[session_id]
        result = stored_data['result']
        
        # 读取处理结果的统计信息
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
                'ellipticity_parameters': f'http://localhost:8000/borehole/download/{session_id}/ellipticity_parameters.csv',
                'centralized_traveltime': f'http://localhost:8000/borehole/download/{session_id}/centralized_traveltime.csv',
                'borehole_radius': f'http://localhost:8000/borehole/download/{session_id}/borehole_radius.csv',
                'borehole_azimuths': f'http://localhost:8000/borehole/download/{session_id}/borehole_azimuths.csv'
            }
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'error': f'获取结果失败: {str(e)}'}
        )

@app.post('/borehole/calculate')
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
    """第一步：计算钻孔椭圆度数据"""
    
    try:
        print("开始计算钻孔椭圆度数据...")
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, 'outputs')
        
        # 生成session_id
        import uuid
        session_id = str(uuid.uuid4())
        
        try:
            if use_demo == 'true':
                # 使用默认演示数据
                print("使用默认演示数据...")
                demo_data_dir = os.path.join(os.path.dirname(__file__), '..', 'python', 'Borehole ellipticity', 'data')
                tt_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_TT_NM.csv')
                wtt_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_WNDTIME.csv')
                mask_path = None
                
                if not os.path.exists(tt_path):
                    return JSONResponse(
                        status_code=404,
                        content={'error': '演示数据文件不存在，请检查数据目录'}
                    )
            else:
                # 使用用户上传的文件
                if tt_file is None:
                    return JSONResponse(
                        status_code=400,
                        content={'error': 'ATV旅行时间文件是必需的'}
                    )
                
                # 检查文件大小
                tt_file.file.seek(0, 2)
                file_size = tt_file.file.tell()
                tt_file.file.seek(0)
                
                print(f"处理文件: {tt_file.filename}, 大小: {file_size / (1024*1024):.2f} MB")
                
                if file_size > 500 * 1024 * 1024:  # 500MB限制
                    return JSONResponse(
                        status_code=413,
                        content={'error': f'文件过大 ({file_size / (1024*1024):.2f} MB)，请上传小于500MB的文件'}
                    )
                
                # 保存上传的文件到临时目录
                tt_path = os.path.join(temp_dir, 'tt_data.csv')
                with open(tt_path, 'wb') as f:
                    shutil.copyfileobj(tt_file.file, f)
                
                # 处理可选的WTT文件
                wtt_path = None
                if wtt_file is not None:
                    wtt_path = os.path.join(temp_dir, 'wtt_data.csv')
                    with open(wtt_path, 'wb') as f:
                        shutil.copyfileobj(wtt_file.file, f)
                
                # 处理可选的mask文件
                mask_path = None
                if mask_file is not None:
                    mask_path = os.path.join(temp_dir, 'mask_data.csv')
                    with open(mask_path, 'wb') as f:
                        shutil.copyfileobj(mask_file.file, f)
            
            print("调用 borehole ellipticity 处理函数...")
            
            # 调用现有的处理函数
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
                return JSONResponse(
                    status_code=500,
                    content={'error': f'处理失败: {result.get("message", "未知错误")}'}
                )
            
            # 读取处理结果的统计信息
            param = result['data']['param']
            valid_idx = ~np.isnan(param[:, 1])
            
            # 存储计算结果
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
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            raise e
    
    except Exception as e:
        error_msg = str(e)
        print(f"计算错误: {error_msg}")
        
        # 根据错误类型返回不同的状态码和错误信息
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

@app.post('/borehole/visualize')
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
    """第二步：生成钻孔椭圆度可视化图表（支持深度窗口与预览质量）"""

    try:
        print(f"收到可视化请求 - session_id: {session_id}")
        print(f"可视化参数 - dz: {dz}, lenZ: {lenZ}, zTop: {zTop}, zCenter: {zCenter}, quality: {quality}")
        print(f"上传文件 - amp_file: {amp_file.filename if amp_file else None}, inc_file: {inc_file.filename if inc_file else None}, azi_file: {azi_file.filename if azi_file else None}")
        print(f"当前存储的计算结果: {list(calculation_results.keys())}")

        # 检查session_id是否存在
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
            # 准备可视化所需的文件路径
            viz_files = {}

            if use_viz_demo == 'true' or (use_demo and use_viz_demo != 'false'):
                # 使用演示数据的可视化文件
                demo_data_dir = os.path.join(os.path.dirname(__file__), '..', 'python', 'Borehole ellipticity', 'data')
                viz_files['amp_path'] = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_AMP_NM.csv')
                viz_files['inc_path'] = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_TILT.csv')
                viz_files['azi_path'] = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_AZIMUTH.csv')
                print("使用演示数据进行可视化...")
                # 缓存演示路径，便于后续窗口更新
                calc_data['viz_files'] = viz_files
            else:
                # 若本次未上传，则尝试复用之前缓存的可视化文件
                cached = calc_data.get('viz_files', {})
                viz_files.update(cached)

                # 保存本次上传的可视化文件（覆盖缓存）
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

            # 使用改进的可视化代码生成图表
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
            # 可视化完成后清理临时目录（但保留计算结果与缓存的viz_files）
            pass

    except Exception as e:
        error_msg = str(e)
        print(f"可视化错误: {error_msg}")

        return JSONResponse(
            status_code=500,
            content={'error': f'可视化生成过程中发生错误: {error_msg}'}
        )

@app.get('/borehole/download/{session_id}/{filename}')
async def download_result_file(session_id: str, filename: str):
    """下载计算结果文件"""
    
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
    
    from fastapi.responses import FileResponse
    return FileResponse(file_path, filename=filename)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000) 