#!/usr/bin/env python3
"""
测试演示数据的计算功能
"""

import os
import sys
import requests
import json

# 测试演示数据计算
def test_demo_calculation():
    url = "http://localhost:8000/borehole/calculate"
    
    # 演示数据请求
    data = {
        'rp': 0.019,
        'vf': 1480,
        'use_demo': 'true'
    }
    
    print("正在测试演示数据计算...")
    print(f"请求URL: {url}")
    print(f"请求数据: {data}")
    
    try:
        response = requests.post(url, data=data)
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 计算成功!")
            print(f"Session ID: {result.get('session_id')}")
            print(f"处理信息: {json.dumps(result.get('processing_info', {}), indent=2, ensure_ascii=False)}")
            return result.get('session_id')
        else:
            print("❌ 计算失败!")
            print(f"错误响应: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def test_demo_visualization(session_id):
    if not session_id:
        print("❌ 没有有效的session_id，跳过可视化测试")
        return
        
    url = "http://localhost:8000/borehole/visualize"
    
    data = {
        'session_id': session_id,
        'lenZ': 5,
        'cmapAmp': 'gray',
        'cmapRad': 'gray_r'
    }
    
    print("\n正在测试演示数据可视化...")
    print(f"请求URL: {url}")
    print(f"请求数据: {data}")
    
    try:
        response = requests.post(url, data=data)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 可视化成功!")
            
            # 检查返回的图片数据
            for key in ['ellipticity_plot', 'polar_plot']:
                if key in result and result[key]:
                    print(f"✅ {key}: 已生成 (长度: {len(result[key])} 字符)")
                else:
                    print(f"❌ {key}: 未生成")
        else:
            print("❌ 可视化失败!")
            print(f"错误响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("演示数据计算和可视化测试")
    print("=" * 50)
    
    # 测试计算
    session_id = test_demo_calculation()
    
    # 测试可视化
    test_demo_visualization(session_id)
    
    print("\n测试完成!")