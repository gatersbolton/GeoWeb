"""
包装现有的可视化代码，用于web应用
基于 vis/dispEllip.py 生成正确的图表
"""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # 设置为非交互式后端
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from functions import *
import base64
from io import BytesIO

def generate_ellipticity_multi_column_plot(ellip_dir, output_dir=None):
    """
    生成多列椭圆度参数图表
    基于 vis/dispEllip.py 的第一个图表（多列图表）
    """
    try:
        # 设置matplotlib
        plt.rcParams['savefig.dpi'] = 150
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['font.size'] = 10

        # 读取椭圆度参数
        ellip_fpath = os.path.join(ellip_dir, 'ellipticity_parameters.csv')
        df = pd.read_csv(ellip_fpath, dtype=object)
        units = df.iloc[0, :]
        data = df.iloc[1:, :]

        z = data['Depth'].values.astype(np.float64)
        phi_major = data['Azimuth_MajorAxis'].values.astype(np.float64)
        phi_minor = data['Azimuth_MinorAxis'].values.astype(np.float64)
        d_major = data['Diameter_MajorAxis'].values.astype(np.float64)
        d_minor = data['Diameter_MinorAxis'].values.astype(np.float64)
        center_x = data['Center_x'].values.astype(np.float64)
        center_y = data['Center_y'].values.astype(np.float64)
        fitting_error = data['FittingError'].values.astype(np.float64)

        # 计算衍生参数
        ratio = d_major / d_minor  # 轴比
        ed = np.sqrt(center_x**2 + center_y**2)  # 偏心距离
        ea = np.degrees(np.arctan2(center_y, center_x))  # 偏心方位角
        ea = (ea + 360) % 360  # 转换为0-360度

        # 处理phi_major的360度循环
        phi_major0 = phi_major.copy()
        phi_major1 = phi_major + 180
        phi_major1[phi_major1 >= 360] -= 360

        phi_minor0 = phi_minor.copy()
        phi_minor1 = phi_minor + 180
        phi_minor1[phi_minor1 >= 360] -= 360

        # 创建图表 - 简化版本，只包含我们有数据的列
        fig, axes = plt.subplots(1, 5, figsize=(18, 8))

        # 设置共同属性
        for i in range(5):
            axes[i].invert_yaxis()
            axes[i].xaxis.set_ticks_position('top')
            axes[i].xaxis.set_label_position('top')
            axes[i].grid(True, alpha=0.3)
            if i > 0:
                axes[i].set_yticklabels([])

        # 列0: 椭圆轴方位角散点图
        axes[0].set_xlabel('Azimuth [°]')
        axes[0].set_xticks([0, 90, 180, 270, 360])
        axes[0].set_xlim(0, 360)
        axes[0].set_ylabel(f'Depth [{units["Depth"]}]')

        # 绘制主轴和次轴方位角
        axes[0].plot(phi_major0, z, 'o', color='skyblue', markersize=3,
                    label='Major axis', alpha=0.7)
        axes[0].plot(phi_major1, z, 'o', color='skyblue', markersize=3, alpha=0.7)
        axes[0].plot(phi_minor0, z, 'o', color='springgreen', markersize=3,
                    label='Minor axis', alpha=0.7)
        axes[0].plot(phi_minor1, z, 'o', color='springgreen', markersize=3, alpha=0.7)
        axes[0].legend(loc='upper right')

        # 列1: 轴比
        axes[1].set_xlabel('Axis Ratio [-]')
        ratio_min, ratio_max = np.nanmin(ratio), np.nanmax(ratio)
        axes[1].set_xlim(ratio_min - 0.05 * (ratio_max - ratio_min),
                        ratio_max + 0.05 * (ratio_max - ratio_min))
        axes[1].plot(ratio, z, 'r-', linewidth=2)

        # 列2: 拟合误差
        axes[2].set_xlabel(f'Fitting Error [{units["FittingError"]}]')
        error_min, error_max = np.nanmin(fitting_error), np.nanmax(fitting_error)
        axes[2].set_xlim(error_min - 0.05 * (error_max - error_min),
                        error_max + 0.05 * (error_max - error_min))
        axes[2].plot(fitting_error, z, color='#ff7f0e', linewidth=2)

        # 列3: 偏心距离
        axes[3].set_xlabel(f'Eccentric Distance [{units["Center_x"]}]')
        ed_min, ed_max = np.nanmin(ed), np.nanmax(ed)
        axes[3].set_xlim(ed_min - 0.05 * (ed_max - ed_min),
                        ed_max + 0.05 * (ed_max - ed_min))
        axes[3].plot(ed, z, color='#9467bd', linewidth=2)

        # 列4: 偏心方位角
        axes[4].set_xlabel('Eccentric Azimuth [°]')
        ea_min, ea_max = np.nanmin(ea), np.nanmax(ea)
        axes[4].set_xlim(ea_min - 0.05 * (ea_max - ea_min),
                        ea_max + 0.05 * (ea_max - ea_min))
        axes[4].plot(ea, z, color='#17becf', linewidth=2)

        plt.tight_layout()

        # 保存图片
        if output_dir:
            output_path = os.path.join(output_dir, 'ellipticity_multi_column.png')
            plt.savefig(output_path, dpi=150, bbox_inches='tight')

        # 转换为base64
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        return f'data:image/png;base64,{img_base64}'

    except Exception as e:
        print(f"生成多列椭圆度参数图表失败: {e}")
        return None

def generate_polar_orientation_plot(ellip_dir, output_dir=None):
    """
    生成极坐标方位角分布图
    基于 vis/dispEllip.py 的第二个图表（极坐标直方图）
    """
    try:
        # 读取椭圆度参数
        ellip_fpath = os.path.join(ellip_dir, 'ellipticity_parameters.csv')
        df = pd.read_csv(ellip_fpath, dtype=object)
        units = df.iloc[0, :]
        data = df.iloc[1:, :]

        phi_major = data['Azimuth_MajorAxis'].values.astype(np.float64)
        phi_minor = data['Azimuth_MinorAxis'].values.astype(np.float64)

        # 处理方位角数据 - 包含180度对称性
        phi_major0 = phi_major.copy()
        phi_major1 = phi_major + 180
        phi_major1[phi_major1 >= 360] -= 360

        phi_minor0 = phi_minor.copy()
        phi_minor1 = phi_minor + 180
        phi_minor1[phi_minor1 >= 360] -= 360

        # 合并数据
        all_major_angles = np.concatenate([phi_major0, phi_major1])
        all_minor_angles = np.concatenate([phi_minor0, phi_minor1])

        # 创建极坐标图
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5),
                                      subplot_kw={'projection': 'polar'})

        # 设置极坐标属性
        for ax in [ax1, ax2]:
            ax.set_theta_direction(-1)  # 顺时针
            ax.set_theta_offset(np.pi/2)  # 北方向为0度
            ax.set_xticks(np.radians(np.linspace(0, 360, 12, endpoint=False)))
            ax.set_yticklabels([])

        # 主轴方位角分布
        ax1.set_title('Major axis orientations', pad=20)
        n0, _, patches0 = ax1.hist(np.radians(all_major_angles),
                                  color='skyblue', edgecolor='k', bins=24, alpha=0.7)

        # 次轴方位角分布
        ax2.set_title('Minor axis orientations', pad=20)
        n1, _, patches1 = ax2.hist(np.radians(all_minor_angles),
                                  color='springgreen', edgecolor='k', bins=24, alpha=0.7)

        plt.tight_layout()

        # 保存图片
        if output_dir:
            output_path = os.path.join(output_dir, 'polar_orientations.png')
            plt.savefig(output_path, dpi=150, bbox_inches='tight')

        # 转换为base64
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        return f'data:image/png;base64,{img_base64}'

    except Exception as e:
        print(f"生成极坐标方位角分布图失败: {e}")
        return None
# 简单内存缓存，避免重复读取CSV（按输出目录区分）
ELLIP_CACHE = {}

def _load_ellipticity_arrays(ellip_dir):
    if ellip_dir in ELLIP_CACHE:
        return ELLIP_CACHE[ellip_dir]
    ellip_fpath = os.path.join(ellip_dir, 'ellipticity_parameters.csv')
    df = pd.read_csv(ellip_fpath, dtype=object)
    units = df.iloc[0, :]
    data = df.iloc[1:, :]
    z = data['Depth'].values.astype(np.float64)
    phi_major = data['Azimuth_MajorAxis'].values.astype(np.float64)
    phi_minor = data['Azimuth_MinorAxis'].values.astype(np.float64)
    d_major = data['Diameter_MajorAxis'].values.astype(np.float64)
    try:
        d_minor = data['Diameter_MinorAxis'].values.astype(np.float64)
    except Exception:
        d_minor = data['Diameter_MajorAxis'].values.astype(np.float64)
    center_x = data['Center_x'].values.astype(np.float64)
    center_y = data['Center_y'].values.astype(np.float64)
    try:
        fitting_error = data['FittingError'].values.astype(np.float64)
    except Exception:
        fitting_error = data['Fitting_Error'].values.astype(np.float64)
    payload = (units, z, phi_major, phi_minor, d_major, d_minor, center_x, center_y, fitting_error)
    ELLIP_CACHE[ellip_dir] = payload
    return payload


def generate_enhanced_plots(ellip_dir, amp_path=None, inc_path=None, azi_path=None,
                           dz=None, lenZ=5, cmapAmp='gray', cmapRad='gray_r', output_dir=None,
                           zTop=None, zCenter=None, quality='final'):
    """
    生成增强的可视化图表 - 更符合 dispEllip.py 的原始输出
    包含振幅图像、半径图像和其他参数的多列显示
    支持基于深度窗口的动态渲染（zTop / zCenter + lenZ）以及预览质量模式
    """
    try:
        # 质量控制：预览模式降低分辨率
        if quality == 'preview':
            plt.rcParams['savefig.dpi'] = 100
        else:
            plt.rcParams['savefig.dpi'] = 150
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['font.size'] = 10

        plots = {}

        # 从缓存加载椭圆度参数（无则读取并缓存）
        units, z_all, phi_major_all, phi_minor_all, d_major_all, d_minor_all, center_x_all, center_y_all, fitting_error_all = _load_ellipticity_arrays(ellip_dir)

        # 计算衍生参数
        # 与 generate_ellipticity_multi_column_plot 保持一致：轴比 = 长轴 / 短轴
        ratio_all = d_major_all / d_minor_all  # 轴比
        ed_all = np.sqrt(center_x_all**2 + center_y_all**2)  # 偏心距离
        ea_all = np.degrees(np.arctan2(center_y_all, center_x_all))  # 偏心方位角
        ea_all = (ea_all + 360) % 360  # 转换为0-360度

        # 处理phi的360度循环性（全局）
        phi_major0_all = phi_major_all.copy()
        phi_major1_all = (phi_major_all + 180) % 360
        phi_minor0_all = phi_minor_all.copy()
        phi_minor1_all = (phi_minor_all + 180) % 360

        # 计算窗口位置
        z_min_all, z_max_all = float(np.nanmin(z_all)), float(np.nanmax(z_all))
        if zCenter is not None and zTop is None:
            zTop = float(zCenter) - float(lenZ) / 2.0
        if zTop is None:
            zTop = z_min_all
        zTop = max(z_min_all, min(zTop, z_max_all - float(lenZ))) if z_max_all > z_min_all else z_min_all
        zBottom = zTop + float(lenZ)

        # 应用窗口掩码
        mask = (z_all >= zTop) & (z_all <= zBottom)
        if np.any(mask):
            z = z_all[mask]
            phi_major0 = phi_major0_all[mask]
            phi_major1 = phi_major1_all[mask]
            phi_minor0 = phi_minor0_all[mask]
            phi_minor1 = phi_minor1_all[mask]
            ratio = ratio_all[mask]
            fitting_error = fitting_error_all[mask]
            ed = ed_all[mask]
            ea = ea_all[mask]
        else:
            z = z_all
            phi_major0, phi_major1, phi_minor0, phi_minor1 = phi_major0_all, phi_major1_all, phi_minor0_all, phi_minor1_all
            ratio, fitting_error, ed, ea = ratio_all, fitting_error_all, ed_all, ea_all

        # 下采样处理
        if dz is not None and dz > 0:
            dz = float(dz)
            x_median = np.median(z)
            sz = len(z[(z >= x_median) & (z <= x_median + dz)])
        else:
            sz = 1
        if quality == 'preview':
            sz = max(int(sz * 2), 1)

        # 生成多列椭圆度参数图表（类似dispEllip.py的主图）
        plots['ellipticity_plot'] = generate_dispellip_style_plot(
            z, phi_major0, phi_major1, phi_minor0, phi_minor1,
            ratio, fitting_error, ed, ea,
            amp_path, inc_path, azi_path,
            ellip_dir, units, sz, lenZ, cmapAmp, cmapRad, output_dir
        )

        # 生成极坐标方位角分布图（不随窗口改变，展示全局分布）
        plots['polar_plot'] = generate_polar_orientation_plot(ellip_dir, output_dir)

        # 椭圆轴方位角分布直方图（全局）
        plots['orientation_plot'] = generate_orientation_histogram(
            phi_major_all, phi_minor_all, output_dir
        )

        plots['cross_section_plot'] = plots['polar_plot']
        plots['radius_plot'] = None

        # 附加元数据
        plots['meta'] = {
            'zMin': z_min_all,
            'zMax': z_max_all,
            'dz': float(dz) if dz is not None else None,
            'lenZ': float(lenZ),
            'window': {
                'zTop': float(zTop),
                'zBottom': float(zBottom)
            }
        }

        return plots

    except Exception as e:
        print(f"生成增强图表失败: {e}")
        # 回退到原有的简单图表
        return generate_all_plots(ellip_dir, output_dir)

def generate_orientation_histogram(phi_major, phi_minor, output_dir=None):
    """
    生成椭圆轴方位角分布的极坐标直方图 - 与 dispEllip.py 的风格一致
    """
    try:
        # 过滤有效数据
        phi_major_valid = phi_major[~np.isnan(phi_major)]
        phi_minor_valid = phi_minor[~np.isnan(phi_minor)]

        if len(phi_major_valid) == 0 and len(phi_minor_valid) == 0:
            print("没有有效的方位角数据")
            return None

        # 处理phi的360度循环性，与dispEllip.py保持一致
        phi_major1 = (phi_major_valid + 180) % 360
        phi_minor1 = (phi_minor_valid + 180) % 360

        # 创建极坐标子图
        fig, ax = plt.subplots(1, 2, figsize=(8, 4.5),
                              subplot_kw={'projection': 'polar'})

        # 设置极坐标属性，与dispEllip.py一致
        for i in range(2):
            ax[i].set_theta_direction(-1)  # 顺时针方向
            ax[i].set_theta_offset(np.pi/2)  # 从北方（y轴）开始
            ax[i].set_xticks(np.radians(np.linspace(0, 360, 12, endpoint=False)))
            ax[i].set_yticklabels([])

        # 主轴方位角分布
        if len(phi_major_valid) > 0:
            ax[0].set_title('Major axis orientations')
            # 合并两个180度的方位角，与dispEllip.py一致
            combined_major = np.concatenate([phi_major_valid, phi_major1])
            n0, _, patches0 = ax[0].hist(np.radians(combined_major),
                                        color='skyblue', edgecolor='k', bins=30)

        # 次轴方位角分布
        if len(phi_minor_valid) > 0:
            ax[1].set_title('Minor axis orientations')
            # 合并两个180度的方位角，与dispEllip.py一致
            combined_minor = np.concatenate([phi_minor_valid, phi_minor1])
            n1, _, patches1 = ax[1].hist(np.radians(combined_minor),
                                        color='springgreen', edgecolor='k', bins=30)

        plt.tight_layout()

        # 保存和转换为base64
        if output_dir:
            output_path = os.path.join(output_dir, 'ellipse_orientations.png')
            plt.savefig(output_path, dpi=150, bbox_inches='tight')

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()

        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        return f'data:image/png;base64,{img_base64}'

    except Exception as e:
        print(f"生成椭圆方位角极坐标直方图失败: {e}")
        return None

def generate_dispellip_style_plot(z, phi_major0, phi_major1, phi_minor0, phi_minor1,
                                 ratio, fitting_error, ed, ea,
                                 amp_path, inc_path, azi_path,
                                 ellip_dir, units, sz, lenZ, cmapAmp, cmapRad, output_dir,
                                 tight=True):
    """
    生成类似dispEllip.py风格的多列图表
    """
    try:
        # 读取ATV振幅数据
        atvAmp = None
        z_atvAmp = None
        if amp_path and os.path.exists(amp_path):
            try:
                amp_data, z_atvAmp, _, _ = read_csv(fpath=amp_path, azimuth_col=False)
                atvAmp = amp_data.copy()
                atvAmp[atvAmp < 0] = np.nan
            except Exception as e:
                print(f"读取振幅数据失败: {e}")

        # 读取钻孔半径数据
        atvRad = None
        z_atvRad = None
        radius_path = os.path.join(ellip_dir, 'borehole_radius.csv')
        if os.path.exists(radius_path):
            try:
                rad_data, z_atvRad, _, _ = read_csv(fpath=radius_path, azimuth_col=False)
                atvRad = rad_data.copy()
                atvRad[atvRad < 0] = np.nan
            except Exception as e:
                print(f"读取半径数据失败: {e}")

        # 读取倾角数据
        atvInc = None
        z_atvInc = None
        if inc_path and os.path.exists(inc_path):
            try:
                df_inc = pd.read_csv(inc_path, dtype=object)
                z_atvInc = df_inc.iloc[1:, 0].values.astype(np.float32)
                atvInc = df_inc.iloc[1:, 1].values.astype(np.float32)
            except Exception as e:
                print(f"读取倾角数据失败: {e}")

        # 读取方位角数据
        atvAzi = None
        z_atvAzi = None
        if azi_path and os.path.exists(azi_path):
            try:
                df_azi = pd.read_csv(azi_path, dtype=object)
                z_atvAzi = df_azi.iloc[1:, 0].values.astype(np.float32)
                atvAzi = df_azi.iloc[1:, 1].values.astype(np.float32)
            except Exception as e:
                print(f"读取方位角数据失败: {e}")

        # 决定要显示的列数
        n_cols = 2  # 至少有椭圆参数和轴比
        if atvAmp is not None: n_cols += 1
        if atvRad is not None: n_cols += 1
        if fitting_error is not None: n_cols += 1
        if ed is not None: n_cols += 1
        if atvInc is not None: n_cols += 1
        if atvAzi is not None: n_cols += 1

        # 创建图表
        fig, axes = plt.subplots(1, min(n_cols, 8), figsize=(2.2 * min(n_cols, 8), 8.5))
        if n_cols == 1:
            axes = [axes]

        col_idx = 0

        # 设置深度范围
        z_min, z_max = z.min(), z.min() + lenZ

        # 设置所有子图的通用属性
        for ax in axes:
            ax.invert_yaxis()
            ax.set_ylim(z_max, z_min)
            ax.xaxis.set_ticks_position('top')
            ax.xaxis.set_label_position('top')
            ax.grid(True, alpha=0.3)

        # 第一列：ATV振幅图像（如果可用）
        if atvAmp is not None and col_idx < len(axes):
            ax = axes[col_idx]
            ax.set_xlabel('Azimuth [°]')
            ax.set_xticks([0, 90, 180, 270, 360])
            ax.set_xlim(0, 360)
            ax.set_ylabel(f'Depth [{units["Depth"]}]')

            im_amp = ax.imshow(atvAmp, cmap=cmapAmp, aspect='auto',
                             extent=[0, 360, z_atvAmp.max(), z_atvAmp.min()],
                             zorder=1)
            col_idx += 1

        # 第二列：钻孔半径图像（如果可用）
        if atvRad is not None and col_idx < len(axes):
            ax = axes[col_idx]
            ax.set_xlabel('Azimuth [°]')
            ax.set_xticks([0, 90, 180, 270, 360])
            ax.set_xlim(0, 360)
            if col_idx > 0:
                ax.set_yticklabels([])

            im_rad = ax.imshow(atvRad, cmap=cmapRad, aspect='auto',
                             extent=[0, 360, z_atvRad.max(), z_atvRad.min()],
                             zorder=1)

            # 叠加椭圆轴方位角散点
            ax.plot(phi_major0[::sz], z[::sz], 'o', color='skyblue', markersize=2,
                   alpha=0.8, zorder=3, label='Major axis')
            ax.plot(phi_major1[::sz], z[::sz], 'o', color='skyblue', markersize=2,
                   alpha=0.8, zorder=3)
            ax.plot(phi_minor0[::sz], z[::sz], 'o', color='springgreen', markersize=2,
                   alpha=0.8, zorder=3, label='Minor axis')
            ax.plot(phi_minor1[::sz], z[::sz], 'o', color='springgreen', markersize=2,
                   alpha=0.8, zorder=3)
            col_idx += 1

        # 如果没有半径图像，则在第二列显示椭圆轴方位角
        elif col_idx < len(axes):
            ax = axes[col_idx]
            ax.set_xlabel('Azimuth [°]')
            ax.set_xticks([0, 90, 180, 270, 360])
            ax.set_xlim(0, 360)
            if col_idx > 0:
                ax.set_yticklabels([])

            ax.plot(phi_major0[::sz], z[::sz], 'o', color='skyblue', markersize=3,
                   alpha=0.8, label='Major axis')
            ax.plot(phi_major1[::sz], z[::sz], 'o', color='skyblue', markersize=3, alpha=0.8)
            ax.plot(phi_minor0[::sz], z[::sz], 'o', color='springgreen', markersize=3,
                   alpha=0.8, label='Minor axis')
            ax.plot(phi_minor1[::sz], z[::sz], 'o', color='springgreen', markersize=3, alpha=0.8)
            ax.legend(loc='upper right', fontsize=8)
            col_idx += 1

        # 轴比
        if col_idx < len(axes):
            ax = axes[col_idx]
            ax.set_xlabel('Axis Ratio [-]')
            ratio_range = ratio[(z >= z_min) & (z <= z_max)]
            ratio_min, ratio_max = np.nanmin(ratio_range), np.nanmax(ratio_range)
            margin = 0.05 * (ratio_max - ratio_min) if ratio_max > ratio_min else 0.01
            ax.set_xlim(ratio_min - margin, ratio_max + margin)
            ax.plot(ratio, z, 'r-', linewidth=2)
            if col_idx > 0:
                ax.set_yticklabels([])
            col_idx += 1

        # 拟合误差
        if fitting_error is not None and col_idx < len(axes):
            ax = axes[col_idx]
            ax.set_xlabel(f'Fitting Error [{units["FittingError"]}]')
            error_range = fitting_error[(z >= z_min) & (z <= z_max)]
            error_min, error_max = np.nanmin(error_range), np.nanmax(error_range)
            margin = 0.05 * (error_max - error_min) if error_max > error_min else 0.01
            ax.set_xlim(error_min - margin, error_max + margin)
            ax.plot(fitting_error, z, color='#ff7f0e', linewidth=2)
            if col_idx > 0:
                ax.set_yticklabels([])
            col_idx += 1

        # 偏心距离
        if ed is not None and col_idx < len(axes):
            ax = axes[col_idx]
            ax.set_xlabel(f'Eccentric Distance [{units["Center_x"]}]')
            ed_range = ed[(z >= z_min) & (z <= z_max)]
            ed_min, ed_max = np.nanmin(ed_range), np.nanmax(ed_range)
            margin = 0.05 * (ed_max - ed_min) if ed_max > ed_min else 0.01
            ax.set_xlim(ed_min - margin, ed_max + margin)
            ax.plot(ed, z, color='#9467bd', linewidth=2)
            if col_idx > 0:
                ax.set_yticklabels([])
            col_idx += 1

        # 倾角
        if atvInc is not None and col_idx < len(axes):
            ax = axes[col_idx]
            ax.set_xlabel('Tool Inclination [°]')
            inc_range = atvInc[(z_atvInc >= z_min) & (z_atvInc <= z_max)]
            inc_min, inc_max = np.nanmin(inc_range), np.nanmax(inc_range)
            margin = 0.05 * (inc_max - inc_min) if inc_max > inc_min else 0.01
            ax.set_xlim(inc_min - margin, inc_max + margin)
            ax.plot(atvInc, z_atvInc, 'k-', linewidth=2)
            if col_idx > 0:
                ax.set_yticklabels([])
            col_idx += 1

        # 方位角
        if atvAzi is not None and col_idx < len(axes):
            ax = axes[col_idx]
            ax.set_xlabel('Tool Azimuth [N°E]')
            azi_range = atvAzi[(z_atvAzi >= z_min) & (z_atvAzi <= z_max)]
            azi_min, azi_max = np.nanmin(azi_range), np.nanmax(azi_range)
            margin = 0.05 * (azi_max - azi_min) if azi_max > azi_min else 0.01
            ax.set_xlim(azi_min - margin, azi_max + margin)
            ax.plot(atvAzi, z_atvAzi, color='C7', linewidth=2)
            if col_idx > 0:
                ax.set_yticklabels([])
            col_idx += 1

        plt.tight_layout()

        # 保存图片
        if output_dir:
            output_path = os.path.join(output_dir, 'enhanced_ellipticity_plot.png')
            plt.savefig(output_path, dpi=150, bbox_inches='tight')

        # 转换为base64
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        return f'data:image/png;base64,{img_base64}'

    except Exception as e:
        print(f"生成dispEllip风格图表失败: {e}")
        # 回退到简单图表
        return generate_ellipticity_multi_column_plot(ellip_dir, output_dir)

def generate_all_plots(ellip_dir, output_dir=None):
    """
    生成所有可视化图表 - 按照 dispEllip.py 的实际输出
    """
    plots = {}

    print("生成多列椭圆度参数图表...")
    plots['ellipticity_plot'] = generate_ellipticity_multi_column_plot(ellip_dir, output_dir)

    print("生成极坐标方位角分布图...")
    polar_img = generate_polar_orientation_plot(ellip_dir, output_dir)
    # 为兼容前端，同时提供两个键
    plots['orientation_plot'] = polar_img
    plots['polar_plot'] = polar_img

    # 为了保持与原有接口的兼容性，同时提供第三个图表位置
    plots['cross_section_plot'] = plots['orientation_plot']  # 复用第二个图
    plots['radius_plot'] = None  # 第三个位置留空或可以生成其他图表

    # 基础元数据，便于前端显示滑条（无需窗口裁剪能力）
    try:
        _, z_all, *_ = _load_ellipticity_arrays(ellip_dir)
        plots['meta'] = {
            'zMin': float(np.nanmin(z_all)) if len(z_all) else None,
            'zMax': float(np.nanmax(z_all)) if len(z_all) else None,
            'dz': None,
            'lenZ': None,
            'window': None
        }
    except Exception:
        pass

    return plots