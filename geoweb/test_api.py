#!/usr/bin/env python3
"""
测试API功能
"""

import requests
import json

# 测试计算API
print("测试计算API...")
try:
    url = "http://localhost:8000/borehole/calculate"
    data = {
        'use_demo': 'true',
        'rp': 0.019,
        'vf': 1480
    }
    
    response = requests.post(url, data=data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 计算成功!")
        print(f"Session ID: {result.get('session_id')}")
        print(f"总深度点数: {result['processing_info']['depth_count']}")
        print(f"有效结果数: {result['processing_info']['valid_depths']}")
        
        # 保存session_id用于测试可视化
        session_id = result.get('session_id')
        
        # 测试可视化API
        print("\n测试可视化API...")
        viz_url = "http://localhost:8000/borehole/visualize"
        viz_data = {
            'session_id': session_id,
            'dz': 0.1,
            'lenZ': 5,
            'cmapAmp': 'gray',
            'cmapRad': 'gray_r'
        }
        
        viz_response = requests.post(viz_url, data=viz_data)
        print(f"可视化状态码: {viz_response.status_code}")
        
        if viz_response.status_code == 200:
            viz_result = viz_response.json()
            print(f"✅ 可视化成功!")
            
            if viz_result.get('ellipticity_plot'):
                print(f"椭圆度图表长度: {len(viz_result['ellipticity_plot'])} 字符")
                print(f"图表开头: {viz_result['ellipticity_plot'][:50]}...")
            else:
                print("❌ 没有椭圆度图表")
                
            if viz_result.get('orientation_plot'):
                print(f"方位角图表长度: {len(viz_result['orientation_plot'])} 字符")
                print(f"图表开头: {viz_result['orientation_plot'][:50]}...")
            else:
                print("❌ 没有方位角图表")
        else:
            print(f"❌ 可视化失败: {viz_response.text}")
    else:
        print(f"❌ 计算失败: {response.text}")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")

print("\nAPI测试完成!")