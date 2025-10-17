#!/usr/bin/env python3
"""
测试Spring Boot后端的API
"""

import requests
import json

def test_spring_boot_calculate():
    """测试Spring Boot的calculate端点"""
    url = "http://localhost:8081/api/borehole/calculate"
    
    # 模拟前端发送的请求
    data = {
        'rp': 0.019,
        'vf': 1480,
        'use_demo': 'true'
    }
    
    print("正在测试Spring Boot的calculate端点...")
    print(f"请求URL: {url}")
    print(f"请求数据: {data}")
    
    try:
        response = requests.post(url, data=data)
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Spring Boot计算成功!")
            print(f"Session ID: {result.get('session_id')}")
            return result.get('session_id')
        else:
            print("❌ Spring Boot计算失败!")
            print(f"错误响应: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def test_spring_boot_visualize(session_id):
    """测试Spring Boot的visualize端点"""
    if not session_id:
        print("❌ 没有有效的session_id，跳过可视化测试")
        return
        
    url = "http://localhost:8081/api/borehole/visualize"
    
    data = {
        'session_id': session_id,
        'lenZ': 5,
        'cmapAmp': 'gray',
        'cmapRad': 'gray_r'
    }
    
    print("\n正在测试Spring Boot的visualize端点...")
    print(f"请求URL: {url}")
    print(f"请求数据: {data}")
    
    try:
        response = requests.post(url, data=data)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Spring Boot可视化成功!")
            
            # 检查返回的图片数据
            for key in ['ellipticity_plot', 'polar_plot']:
                if key in result and result[key]:
                    print(f"✅ {key}: 已生成 (长度: {len(result[key])} 字符)")
                else:
                    print(f"❌ {key}: 未生成")
        else:
            print("❌ Spring Boot可视化失败!")
            print(f"错误响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Spring Boot API测试")
    print("=" * 60)
    
    # 测试计算
    session_id = test_spring_boot_calculate()
    
    # 测试可视化
    test_spring_boot_visualize(session_id)
    
    print("\nSpring Boot API测试完成!")