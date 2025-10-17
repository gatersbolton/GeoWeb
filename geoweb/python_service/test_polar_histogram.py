#!/usr/bin/env python3
"""
测试极坐标直方图生成
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'python', 'Borehole ellipticity'))

try:
    from vis_wrapper import generate_orientation_histogram
    print("成功导入 generate_orientation_histogram 函数")
except ImportError as e:
    print(f"导入函数失败: {e}")
    exit(1)

def test_polar_histogram():
    """测试极坐标直方图生成"""
    print("=" * 50)
    print("测试极坐标直方图生成")
    print("=" * 50)
    
    # 使用演示数据
    demo_data_dir = os.path.join(os.path.dirname(__file__), '..', 'python', 'Borehole ellipticity', 'data', 'borehole_ellipticity_outputs')
    ellip_fpath = os.path.join(demo_data_dir, 'ellipticity_parameters.csv')
    
    if not os.path.exists(ellip_fpath):
        print(f"❌ 演示数据文件不存在: {ellip_fpath}")
        return
    
    try:
        # 读取椭圆度参数
        df = pd.read_csv(ellip_fpath, dtype=object)
        units = df.iloc[0, :]
        data = df.iloc[1:, :]
        
        phi_major = data['Azimuth_MajorAxis'].values.astype(np.float64)  
        phi_minor = data['Azimuth_MinorAxis'].values.astype(np.float64)
        
        print(f"✅ 成功读取数据")
        print(f"   主轴方位角数量: {len(phi_major[~np.isnan(phi_major)])}")
        print(f"   次轴方位角数量: {len(phi_minor[~np.isnan(phi_minor)])}")
        print(f"   主轴方位角范围: {np.nanmin(phi_major):.1f} - {np.nanmax(phi_major):.1f}°")
        print(f"   次轴方位角范围: {np.nanmin(phi_minor):.1f} - {np.nanmax(phi_minor):.1f}°")
        
        # 生成极坐标直方图
        print("\n正在生成极坐标直方图...")
        plot_base64 = generate_orientation_histogram(phi_major, phi_minor, output_dir='.')
        
        if plot_base64:
            print("✅ 极坐标直方图生成成功!")
            print(f"   Base64数据长度: {len(plot_base64)} 字符")
            print(f"   图片保存为: ellipse_orientations.png")
        else:
            print("❌ 极坐标直方图生成失败!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_polar_histogram()