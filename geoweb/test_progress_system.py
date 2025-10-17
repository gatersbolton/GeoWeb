#!/usr/bin/env python3
"""
测试钻孔椭圆度项目的进度监控系统
"""

import asyncio
import websockets
import json
import requests
import time

async def test_websocket_connection(session_id):
    """测试WebSocket连接和进度接收"""
    uri = f"ws://localhost:8000/ws/progress/{session_id}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"WebSocket连接已建立: {uri}")
            
            # 监听进度消息
            async for message in websocket:
                data = json.loads(message)
                print(f"收到进度更新: {data}")
                
                if data.get('type') == 'completed':
                    print("计算完成！")
                    break
                elif data.get('type') == 'error':
                    print(f"计算出错: {data.get('message')}")
                    break
    except Exception as e:
        print(f"WebSocket连接错误: {e}")

def test_async_calculation():
    """测试异步计算API"""
    try:
        # 准备请求数据
        data = {
            'use_demo': 'true',
            'rp': 0.019,
            'vf': 1480
        }
        
        print("发送异步计算请求...")
        response = requests.post('http://localhost:8000/borehole/calculate_async', data=data)
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get('session_id')
            print(f"计算已启动，Session ID: {session_id}")
            return session_id
        else:
            print(f"请求失败: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"请求错误: {e}")
        return None

async def main():
    """主测试函数"""
    print("=== 钻孔椭圆度进度监控系统测试 ===\n")
    
    # 1. 启动异步计算
    print("1. 启动异步计算...")
    session_id = test_async_calculation()
    
    if not session_id:
        print("无法启动计算，退出测试")
        return
    
    print(f"Session ID: {session_id}\n")
    
    # 2. 连接WebSocket监控进度
    print("2. 连接WebSocket监控进度...")
    await test_websocket_connection(session_id)
    
    # 3. 获取最终结果
    print("\n3. 获取计算结果...")
    try:
        result_response = requests.get(f'http://localhost:8000/borehole/result/{session_id}')
        if result_response.status_code == 200:
            result = result_response.json()
            print("计算结果摘要:")
            print(f"  - 总深度点数: {result.get('results_summary', {}).get('total_depths', 'N/A')}")
            print(f"  - 有效结果数: {result.get('results_summary', {}).get('valid_results', 'N/A')}")
            print(f"  - 平均长轴: {result.get('results_summary', {}).get('avg_major_axis', 'N/A'):.3f} mm")
            print(f"  - 平均短轴: {result.get('results_summary', {}).get('avg_minor_axis', 'N/A'):.3f} mm")
        else:
            print(f"获取结果失败: {result_response.status_code}")
    except Exception as e:
        print(f"获取结果出错: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    print("请确保以下服务正在运行:")
    print("1. Python服务: python python_service/app.py")
    print("2. 前端服务: cd frontend && npm run dev")
    print()
    
    # 检查服务是否可用
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        print("✓ Python服务正在运行")
    except:
        print("✗ Python服务未运行")
        exit(1)
    
    # 运行测试
    asyncio.run(main())