# -*- coding: utf-8 -*-
"""
根据 ATV 成像图估计纵向相对速度 v(y) 并可视化。

使用方式：直接在 main() 内部的“手动参数设置”区域修改参数后运行本脚本。
"""

import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

# 为了正确显示中文，设置常见支持中文的字体，并避免负号显示为方块
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ========== 工具函数 ==========

def load_gray_float(img_path):
    """加载图像 -> 灰度 float32，范围 [0,1]"""
    im = Image.open(img_path).convert("L")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    return arr

def auto_crop_right_black(arr, threshold=0.02, min_run=20):
    """
    粗略自动裁掉右侧纯黑区域（比如论文截图右侧黑边）。
    threshold: 认为“非黑”的列平均值下限（0~1）
    min_run  : 连续非黑列的最少数量，用于稳健检测
    """
    col_mean = arr.mean(axis=0)
    non_black = col_mean > threshold
    # 找到最右一段连续 non_black 的索引范围
    # 简化：从左往右第一个 non_black 为起点，最后一个 non_black 为终点
    idx = np.where(non_black)[0]
    if idx.size == 0:
        return arr  # 全黑就不裁
    left, right = idx[0], idx[-1]
    # 要求中间至少有 min_run 列是 non_black
    if right - left + 1 >= min_run:
        return arr[:, left:right+1]
    return arr

def moving_average_1d(x, k):
    """一维简单滑动平均（窗口 k，k 必须是奇数）"""
    if k < 2:
        return x
    if k % 2 == 0:
        k += 1
    pad = k // 2
    xpad = np.pad(x, (pad, pad), mode="edge")
    kernel = np.ones(k, dtype=np.float32) / k
    return np.convolve(xpad, kernel, mode="valid")

def compute_relative_speed(gray_img, smooth_win=21, roi_cols=None):
    """
    根据相邻行差分的平均绝对值，计算相对速度曲线 v(y)。
    gray_img : H x W 的灰度图（0~1）
    smooth_win: 对速度做一维平滑的窗口（奇数）
    roi_cols : (x0, x1) 可选，仅在这个列区间上统计（剔除边缘/刻度/空白）
    返回：
        v_raw  : 未归一化的速度指标（长度 H-1）
        v_norm : 归一化到 [0,1] 的速度（长度 H-1，0=慢，1=快）
    """
    H, W = gray_img.shape
    if roi_cols is None:
        x0, x1 = 0, W
    else:
        x0, x1 = roi_cols
        x0 = max(0, int(x0))
        x1 = min(W, int(x1))
        if x1 <= x0:
            x0, x1 = 0, W

    # 行间差分：变化越大 -> 相对速度越快
    diff = np.abs(np.diff(gray_img[:, x0:x1], axis=0))  # (H-1, roiW)
    v_raw = diff.mean(axis=1)                           # (H-1,)

    # 平滑
    v_smooth = moving_average_1d(v_raw, smooth_win)

    # 归一化到 [0,1]
    v_min, v_max = float(v_smooth.min()), float(v_smooth.max())
    if v_max > v_min:
        v_norm = (v_smooth - v_min) / (v_max - v_min)
    else:
        v_norm = np.zeros_like(v_smooth)

    return v_raw, v_norm

def save_csv(out_csv, v_raw, v_norm, start_depth=0.0, depth_per_row=None):
    """
    保存速度曲线为 CSV。
    start_depth  : 顶部对应的深度（同单位，比如 m）
    depth_per_row: 每行代表的深度增量（比如 m/row），若未知可设 None
    """
    y_idx = np.arange(len(v_norm))  # 对应行 y 与 y+1 的间隙，长度 H-1

    if depth_per_row is None:
        depth_col = y_idx.astype(float)  # 直接用行号代替深度
        depth_name = "row_index"
    else:
        depth_col = start_depth + (y_idx + 0.15) * float(depth_per_row)  # 取间隙的中心深度
        depth_name = "depth"

    data = np.column_stack([depth_col, v_raw, v_norm])
    header = f"{depth_name},v_raw,v_norm"
    np.savetxt(out_csv, data, delimiter=",", header=header, comments="", fmt="%.6f")

# ========== 可视化 ==========

def visualize_side_by_side(gray_img, v_norm, out_png, title=None):
    """
    左：速度条（纵向颜色）；中：原图；右：速度曲线（横=速度，纵=深度）。
    """
    H, W = gray_img.shape

    # 仅显示：左色卡 | 中原图 | 右速度曲线
    cbar_w = 40

    # 画图
    fig = plt.figure(figsize=(12, 10))
    right_w = max(int(W * 0.20), 120)
    gs = fig.add_gridspec(1, 3, width_ratios=[cbar_w, W, right_w], wspace=0.25)

    # 左：色卡（0~1 对应 v_norm）
    cax = fig.add_subplot(gs[0, 0])
    sm = plt.cm.ScalarMappable(norm=Normalize(vmin=0.0, vmax=1.0), cmap=plt.get_cmap())
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax)
    cbar.ax.set_ylabel("v_norm", rotation=90)

    # 中：原图
    ax0 = fig.add_subplot(gs[0, 1])
    ax0.imshow(gray_img, cmap="gray", aspect="auto")
    ax0.set_title("原始图像", fontsize=11)
    ax0.axis("off")

    # （取消速度条显示）

    # 右：速度曲线（纵向 y 轴与图像对齐，0 在上）
    ax2 = fig.add_subplot(gs[0, 2])
    y = np.arange(len(v_norm))
    ax2.plot(v_norm, y, linewidth=1.0)
    # 使顶部无空隙：明确设置 y 轴范围并去除额外边距
    ax2.set_ylim(len(v_norm) - 1, 0)
    ax2.margins(y=0)
    ax2.set_xlim(-0.05, 1.05)
    ax2.set_xlabel("相对速度 v_norm")
    ax2.set_ylabel("纵向位置（行号）")
    ax2.grid(True, linestyle="--", alpha=0.4)
    if title:
        fig.suptitle(title, y=0.98)

    plt.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)

# ========== 主流程 ==========

def main():
    # ===== 手动参数设置（请按需修改） =====
    image = r"./stick_pull.png"           # 输入图片路径
    outdir = r"./out"                     # 输出目录
    crop_black = False                     # 是否尝试自动裁掉右侧黑边/空白
    roi_cols = None                        # 仅在 [x0, x1) 列区间上计算；例如 (0, 600) 或 None
    smooth_win = 21                        # 速度曲线平滑窗口（奇数，越大越平滑）
    depth_per_row = None                   # 每行对应的深度增量（m/row 或 ft/row）。未知请设 None
    start_depth = 0.0                      # 顶部对应的深度（和 depth_per_row 同单位）

    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(image))[0]

    # 1) 读图
    img = load_gray_float(image)

    # 2) 可选自动裁黑边
    if crop_black:
        img = auto_crop_right_black(img, threshold=0.02, min_run=20)

    # 3) 计算相对速度
    v_raw, v_norm = compute_relative_speed(
        img,
        smooth_win=smooth_win,
        roi_cols=roi_cols
    )

    # 4) 保存 CSV
    out_csv = os.path.join(outdir, f"{base}_speed_profile.csv")
    save_csv(out_csv, v_raw, v_norm,
             start_depth=start_depth,
             depth_per_row=depth_per_row)

    # 5) 可视化
    out_png = os.path.join(outdir, f"{base}_speed_visualization.png")
    ttl = f"Speed profile from image: {base}"
    visualize_side_by_side(img, v_norm, out_png, title=ttl)

    print(f"[OK] 已生成：\n  - 速度曲线 CSV: {out_csv}\n  - 可视化 PNG : {out_png}")

if __name__ == "__main__":
    main()
