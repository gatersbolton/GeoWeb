#!/usr/bin/env python3
"""
测试演示数据和可视化功能
"""

import os
import sys

# 添加路径
sys.path.append('./python/Borehole ellipticity')

try:
    from borehole_ellipticity import process_borehole_ellipticity
    from vis_wrapper import generate_enhanced_plots
    print("✅ 成功导入所有必需模块")
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    sys.exit(1)

# 检查演示数据文件
demo_data_dir = './python/Borehole ellipticity/data'
required_files = [
    'ST1_20210305_DEV_ATV_up_main_TT_NM.csv',
    'ST1_20210305_DEV_ATV_up_main_WNDTIME.csv',
    'ST1_20210305_DEV_ATV_up_main_AMP_NM.csv',
    'ST1_20210305_DEV_ATV_up_main_TILT.csv',
    'ST1_20210305_DEV_ATV_up_main_AZIMUTH.csv'
]

print(f"\n检查演示数据目录: {demo_data_dir}")
if not os.path.exists(demo_data_dir):
    print(f"❌ 演示数据目录不存在: {demo_data_dir}")
    sys.exit(1)

for file in required_files:
    file_path = os.path.join(demo_data_dir, file)
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        print(f"✅ {file} ({file_size} bytes)")
    else:
        print(f"❌ 缺少文件: {file}")

# 测试椭圆度计算
print("\n开始测试椭圆度计算...")
try:
    output_dir = './test_output'
    os.makedirs(output_dir, exist_ok=True)
    
    tt_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_TT_NM.csv')
    wtt_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_WNDTIME.csv')
    
    result = process_borehole_ellipticity(
        fp_tt=tt_path,
        fp_wtt=wtt_path,
        wtt=None,
        rp=0.019,
        vf=1480,
        beta=None,
        fp_mask=None,
        dir_out=output_dir
    )
    
    if result['success']:
        print("✅ 椭圆度计算成功")
        print(f"   总深度点数: {result['processing_info']['total_depths']}")
        print(f"   有效结果数: {result['processing_info']['valid_results']}")
    else:
        print(f"❌ 椭圆度计算失败: {result.get('message', '未知错误')}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ 椭圆度计算异常: {e}")
    sys.exit(1)

# 测试可视化生成
print("\n开始测试可视化生成...")
try:
    amp_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_AMP_NM.csv')
    inc_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_TILT.csv')
    azi_path = os.path.join(demo_data_dir, 'ST1_20210305_DEV_ATV_up_main_AZIMUTH.csv')
    
    plots = generate_enhanced_plots(
        ellip_dir=output_dir,
        amp_path=amp_path,
        inc_path=inc_path,
        azi_path=azi_path,
        dz=0.1,
        lenZ=5,
        cmapAmp='gray',
        cmapRad='gray_r'
    )
    
    if plots['ellipticity_plot']:
        print("✅ 椭圆度图表生成成功")
    else:
        print("❌ 椭圆度图表生成失败")
        
    if plots['orientation_plot']:
        print("✅ 方位角分布图生成成功")
    else:
        print("❌ 方位角分布图生成失败")
        
except Exception as e:
    print(f"❌ 可视化生成异常: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成!")