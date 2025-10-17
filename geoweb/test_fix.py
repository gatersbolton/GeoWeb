#!/usr/bin/env python3
"""
测试修复后的异步计算API
"""

import requests
import json

def test_async_api():
    url = 'http://localhost:8000/borehole/calculate_async'
    
    data = {
        'use_demo': 'true',
        'rp': 0.019,
        'vf': 1480
    }
    
    try:
        print("发送测试请求...")
        response = requests.post(url, data=data)
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get('session_id')
            print(f"✓ 成功启动计算，Session ID: {session_id}")
            return True
        else:
            print(f"✗ 请求失败")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False

if __name__ == "__main__":
    success = test_async_api()
    if success:
        print("\n🎉 API修复成功！")
    else:
        print("\n❌ API仍有问题")