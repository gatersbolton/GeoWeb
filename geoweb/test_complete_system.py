#!/usr/bin/env python3
"""
测试完整的进度监控系统
"""

import requests
import time
import json

def test_complete_workflow():
    """测试完整的工作流程"""
    print("=== 测试钻孔椭圆度进度监控系统 ===\n")
    
    # 1. 启动异步计算
    print("1. 启动异步计算...")
    try:
        response = requests.post('http://localhost:8000/borehole/calculate_async', 
                               data={'use_demo': 'true', 'rp': 0.019, 'vf': 1480})
        
        if response.status_code != 200:
            print(f"❌ 启动计算失败: {response.status_code} - {response.text}")
            return False
            
        result = response.json()
        session_id = result.get('session_id')
        
        if not session_id:
            print("❌ 未获取到session_id")
            return False
            
        print(f"✅ 计算已启动，Session ID: {session_id}")
        
    except Exception as e:
        print(f"❌ 启动计算出错: {e}")
        return False
    
    # 2. 轮询进度
    print("\n2. 监控计算进度...")
    last_percentage = -1
    max_polls = 60  # 最多轮询60次（60秒）
    
    for i in range(max_polls):
        try:
            progress_response = requests.get(f'http://localhost:8000/borehole/progress/{session_id}')
            
            if progress_response.status_code == 200:
                progress_data = progress_response.json()
                message = progress_data.get('message', 'N/A')
                percentage = progress_data.get('percentage')
                
                if percentage != last_percentage:
                    if percentage is not None:
                        print(f"   进度: {percentage:.1f}% - {message}")
                    else:
                        print(f"   状态: {message}")
                    last_percentage = percentage
                
                # 检查是否完成
                if percentage == 100 or '完成' in message:
                    print("✅ 计算完成!")
                    break
                elif '失败' in message or '错误' in message:
                    print(f"❌ 计算失败: {message}")
                    return False
                    
            elif progress_response.status_code == 404:
                if i < 5:  # 前5次轮询允许404（任务可能还没开始）
                    print("   等待任务开始...")
                else:
                    print("❌ 任务未找到")
                    return False
            else:
                print(f"❌ 获取进度失败: {progress_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 轮询进度出错: {e}")
            return False
        
        time.sleep(1)
    else:
        print("❌ 轮询超时")
        return False
    
    # 3. 获取最终结果
    print("\n3. 获取计算结果...")
    try:
        result_response = requests.get(f'http://localhost:8000/borehole/result/{session_id}')
        
        if result_response.status_code == 200:
            result_data = result_response.json()
            summary = result_data.get('results_summary', {})
            
            print("✅ 结果获取成功!")
            print(f"   总深度点数: {summary.get('total_depths', 'N/A')}")
            print(f"   有效结果数: {summary.get('valid_results', 'N/A')}")
            print(f"   平均长轴: {summary.get('avg_major_axis', 0):.3f} mm")
            print(f"   平均短轴: {summary.get('avg_minor_axis', 0):.3f} mm")
            
        else:
            print(f"❌ 获取结果失败: {result_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 获取结果出错: {e}")
        return False
    
    print("\n🎉 系统测试完全成功!")
    return True

if __name__ == "__main__":
    # 检查服务是否运行
    try:
        response = requests.get('http://localhost:8000/docs', timeout=5)
        print("✅ Python服务正在运行")
    except:
        print("❌ Python服务未运行，请先启动：python python_service/app.py")
        exit(1)
    
    # 运行完整测试
    success = test_complete_workflow()
    
    if success:
        print("\n📋 前端使用说明:")
        print("1. 启动前端服务：cd frontend && npm run dev")
        print("2. 访问：http://localhost:3000")
        print("3. 导航到'钻孔椭圆度项目'")
        print("4. 点击'开始计算'观察实时进度")
    else:
        print("\n❌ 系统测试失败，请检查错误信息")