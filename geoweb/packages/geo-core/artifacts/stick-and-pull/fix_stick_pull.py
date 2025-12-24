import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import sobel, gaussian_filter1d

# 中文字体与负号显示设置，避免方框字与负号异常
mpl.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'Arial Unicode MS', 'DejaVu Sans']
mpl.rcParams['axes.unicode_minus'] = False
from pathlib import Path

def load_image_gray01(path):
    im = Image.open(str(path)).convert('RGB')
    img_rgb = np.array(im)
    gray = np.array(im.convert('L'), dtype=np.float32) / 255.0
    # 归一化到 [0,1]
    gmin, gmax = float(gray.min()), float(gray.max())
    if gmax > gmin:
        gray = (gray - gmin) / (gmax - gmin)
    return gray, img_rgb  # 返回灰度[0,1]和原RGB（用于展示）

def valid_column_mask(gray, thr=0.02, min_frac=0.75):
    """
    thr: 将接近全黑的像素视为无效(例如黑带)；
    min_frac: 每列有效像素比例低于该值的列认为是无效列。
    """
    valid_px = gray > thr
    col_valid_ratio = valid_px.mean(axis=0)
    mask = col_valid_ratio >= min_frac
    # 若全都被判无效，回退为全有效
    if mask.mean() < 0.05:
        mask[:] = True
    return mask

def estimate_speed_from_image(gray, col_mask=None, gauss_ks=31):
    """
    用纵向梯度密度估计相对速度 v(y):
      - 快速段: 相邻行差分大 => v高
      - 缓慢段: 相邻行差分小 => v低
    """
    H, W = gray.shape
    if col_mask is None:
        col_mask = np.ones(W, dtype=bool)
    g = gray[:, col_mask]

    # 纵向梯度（Sobel）
    gy = sobel(g, axis=0, mode='nearest')
    e = np.median(np.abs(gy), axis=1)  # 对列取中位数，鲁棒抗竖纹
    # 平滑：高斯滤波（用 sigma 近似 gauss_ks 大小）
    sigma = max(1.0, gauss_ks / 6.0)
    e_smooth = gaussian_filter1d(e, sigma=sigma, mode='nearest')
    # 避免全零
    e_smooth = e_smooth - np.min(e_smooth)
    e_smooth = e_smooth / (np.mean(e_smooth) + 1e-6)
    e_smooth = np.clip(e_smooth, 1e-3, None)
    return e_smooth  # 相对速度曲线（均值~1）

def prepare_speed(v, power=1.6, q_clip=(2, 98)):
    """
    对输入速度做鲁棒处理：分位数裁剪 + 归一化 + 指数增强动态范围。
    power>1 会加大快慢差异；可从 1.2~2.0 之间调。
    """
    v = np.asarray(v).astype(np.float32).reshape(-1)
    lo, hi = np.percentile(v, q_clip)
    v = np.clip(v, lo, hi)
    v = (v - v.min()) / (v.max() - v.min() + 1e-6)  # 0~1
    v = 0.1 + 0.9 * v  # 防止出现0
    v = v ** power
    v /= (v.mean() + 1e-6)  # 均值归一到1
    v = np.clip(v, 1e-3, None)
    return v

def depth_axis_from_speed(v):
    """
    从相对速度 v(y) 构造单调的深度坐标 D[y]（线性缩放到 [0, H-1]）。
    由于原图是“按时间采样”的，D[y]≈∫ v dy 给出“等深度间距”的映射。
    """
    D = np.cumsum(v)
    D = (D - D[0]) / (D[-1] - D[0] + 1e-6)
    return D

def warp_image_along_depth(gray, D, out_h=None):
    """
    按单调深度坐标 D[y] 将图像重采样到等距深度网格。
    用 np.interp 按列插值，不依赖 SciPy。
    """
    H, W = gray.shape
    if out_h is None:
        out_h = H  # 输出高度与原图一致，便于对比
    # 目标深度网格（等间距）
    D_target = np.linspace(0.0, 1.0, out_h, dtype=np.float32)
    # 预先算好 y(D_target)
    # 这里要“反查”，即把等距深度映射回原始行索引
    y_coords = np.interp(D_target, D, np.arange(H, dtype=np.float32))

    out = np.empty((out_h, W), dtype=np.float32)
    for x in range(W):
        col = gray[:, x].astype(np.float32)
        out[:, x] = np.interp(y_coords, np.arange(H, dtype=np.float32), col)
    # 归一化到 [0,1]
    out = (out - out.min()) / (out.max() - out.min() + 1e-6)
    return out

def warp_rgb_along_depth(rgb, D, out_h=None):
    """
    使用同一深度轴 D 对 RGB 图逐列插值重采样，保留原图色彩。
    """
    H, W, C = rgb.shape
    if out_h is None:
        out_h = H
    D_target = np.linspace(0.0, 1.0, out_h, dtype=np.float32)
    y_coords = np.interp(D_target, D, np.arange(H, dtype=np.float32))

    out = np.empty((out_h, W, 3), dtype=np.float32)
    base = np.arange(H, dtype=np.float32)
    for c in range(3):
        for x in range(W):
            col = rgb[:, x, c].astype(np.float32)
            out[:, x, c] = np.interp(y_coords, base, col)
    # 限幅并转回 uint8
    out = np.clip(out, 0, 255).astype(np.uint8)
    return out

def fix_stick_pull(
    image_path,
    speed_csv="out/stick_pull_speed_profile.csv",          # 你的 v.csv 路径；为 None 时自动从图像估计
    speed_colname=None,      # v.csv 中的列名；None 则用第一列
    power=1.6,               # 动态范围增强
    q_clip=(2, 98),          # 分位数裁剪，抑制离群
    gauss_ks=31,             # 速度估计时的平滑窗口（奇数）
    show=True,
    save_path="out/stick_pull_fixed.png"
):
    gray, rgb = load_image_gray01(image_path)
    H, W = gray.shape

    # 有效列掩膜：排除黑带/坏列的干扰
    col_mask = valid_column_mask(gray, thr=0.02, min_frac=0.75)

    # 1) 速度曲线：优先用 v.csv；否则从图像估计
    if speed_csv is not None and Path(speed_csv).exists():
        df = pd.read_csv(speed_csv)
        if speed_colname is not None and speed_colname in df.columns:
            v_series = df[speed_colname]
        else:
            cols_lower = {c.lower(): c for c in df.columns}
            # 优先使用归一化速度
            for name in ["v_norm", "v", "speed", "velocity", "tool_speed", "toolspeed", "v_raw"]:
                if name in cols_lower:
                    v_series = df[cols_lower[name]]
                    break
            else:
                # 回退：选取数值型列，尽量避开行索引/深度列
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                avoid = {"row_index", "row", "depth", "z", "y", "index"}
                candidate = None
                for c in numeric_cols:
                    if c.lower() not in avoid:
                        candidate = c
                        break
                if candidate is None and numeric_cols:
                    candidate = numeric_cols[-1]
                if candidate is None:
                    raise ValueError("未在 CSV 中找到数值型速度列。")
                v_series = df[candidate]

        v = v_series.to_numpy(dtype=np.float32).reshape(-1)
        # 若长度与图像行数不同，插值到 H
        if len(v) != H:
            y_old = np.linspace(0, 1, len(v), dtype=np.float32)
            y_new = np.linspace(0, 1, H, dtype=np.float32)
            v = np.interp(y_new, y_old, v)
    else:
        v = estimate_speed_from_image(gray, col_mask=col_mask, gauss_ks=gauss_ks)

    # 2) 正则化 + 动态范围增强
    v_prepared = prepare_speed(v, power=power, q_clip=q_clip)

    # 3) 建立单调深度轴并重采样
    D = depth_axis_from_speed(v_prepared)
    corrected_gray = warp_image_along_depth(gray, D, out_h=H)
    corrected_rgb = warp_rgb_along_depth(rgb, D, out_h=H)

    # 4) 可视化：原图 vs 修复（并排）——仅输出文件，不弹窗
    if save_path or show:
        fig, axes = plt.subplots(1, 2, figsize=(7, 10), dpi=120)
        axes[0].imshow(rgb)
        axes[0].set_title("原图")
        axes[0].axis("off")
        axes[1].imshow(corrected_rgb)
        axes[1].set_title("去 Stick & Pull（重参数化后）")
        axes[1].axis("off")
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=150)
        plt.close(fig)

    return corrected_rgb, D, v_prepared

# ========================
# 使用示例：
# corrected, D, v_used = fix_stick_pull(
#     image_path="stick_pull.png",        # 换成你的路径
#     speed_csv="speed.csv",              # 若没有可靠速度就设为 None
#     speed_colname=None,                 # v.csv有表头就写列名
#     power=1.6,                          # 1.2~2.0 可调，大了更激进
#     q_clip=(2, 98),                     # 抑制离群
#     gauss_ks=31,                        # 图像自估速度时用
#     show=True,
#     save_path="compare_fix.png"
# )

if __name__ == "__main__":
    # ===== 手动参数设置 =====
    image_path = "stick_pull.png"
    speed_csv = "out/stick_pull_speed_profile.csv"   # 若没有可设为 None
    save_path = "out/stick_pull_fixed.png"
    show = False

    # 确保输出目录存在
    out_dir = os.path.dirname(save_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    corrected, D, v_used = fix_stick_pull(
        image_path=image_path,
        speed_csv=speed_csv,
        show=show,
        save_path=save_path
    )
    if save_path:
        print(f"[OK] 已保存对比图: {save_path}")