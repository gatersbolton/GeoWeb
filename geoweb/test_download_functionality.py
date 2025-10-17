#!/usr/bin/env python3
"""
测试下载功能
"""

import requests
import time

def test_download_functionality():
    """测试完整的计算和下载流程"""
    print("=== 测试钻孔椭圆度下载功能 ===\n")
    
    # 1. 启动计算
    print("🚀 启动计算...")
    try:
        response = requests.post('http://localhost:8000/borehole/calculate_async', 
                               data={'use_demo': 'true', 'rp': 0.019, 'vf': 1480})
        
        if response.status_code != 200:
            print(f"❌ 启动失败: {response.text}")
            return
            
        session_id = response.json().get('session_id')
        print(f"✅ 计算启动，Session: {session_id[:8]}...")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return
    
    # 2. 等待计算完成
    print("\n⏳ 等待计算完成...")
    for i in range(60):  # 最多等待60秒
        try:
            progress_response = requests.get(f'http://localhost:8000/borehole/progress/{session_id}')
            if progress_response.status_code == 200:
                data = progress_response.json()
                if data.get('percentage') == 100 or '完成' in data.get('message', ''):
                    print("✅ 计算完成!")
                    break
        except:
            pass
        time.sleep(1)
    else:
        print("❌ 计算超时")
        return
    
    # 3. 获取计算结果
    print("\n📊 获取计算结果...")
    try:
        result_response = requests.get(f'http://localhost:8000/borehole/result/{session_id}')
        if result_response.status_code == 200:
            result_data = result_response.json()
            download_urls = result_data.get('download_urls', {})
            
            print(f"✅ 获取到 {len(download_urls)} 个下载链接:")
            for name, url in download_urls.items():
                print(f"   - {name}: {url}")
                
        else:
            print(f"❌ 获取结果失败: {result_response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ 获取结果错误: {e}")
        return
    
    # 4. 测试下载文件
    print("\n📥 测试文件下载...")
    for name, url in download_urls.items():
        try:
            download_response = requests.get(url)
            if download_response.status_code == 200:
                print(f"   ✅ {name}: {len(download_response.content)} bytes")
            else:
                print(f"   ❌ {name}: {download_response.status_code}")
        except Exception as e:
            print(f"   ❌ {name}: {e}")
    
    print(f"\n🎉 下载功能测试完成!")
    print("\n💡 前端使用提示:")
    print("1. 运行计算直到完成")
    print("2. 在计算结果页面应该能看到下载按钮")
    print("3. 点击下载按钮应该能下载相应的CSV文件")

if __name__ == "__main__":
    test_download_functionality()