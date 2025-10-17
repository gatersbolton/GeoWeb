"""
Python implementation of segmented (depth-wise) stress inversion converted from
`stressinv_ellipticity_depthwise.m`.

For each depth window of size `dz`, perform the same iterative neighborhood search
as the global solver, return a list of structures per window with fields:
zmid, zmin, zmax, Rank_Top40, Rank_Top40_all, a_range, b_range, c_range,
phi_range, S3_range, RMSE_store, para_cnt.
"""

import os
import sys
import json
import math
import numpy as np
import pandas as pd
from scipy.io import savemat


THIS_DIR = os.path.dirname(__file__)
V1_ROOT = os.path.abspath(os.path.join(THIS_DIR, os.pardir))
if V1_ROOT not in sys.path:
    sys.path.append(V1_ROOT)

from functions import ellip_orien, azimuth_rmse  # noqa: E402


def _centers(vmin: float, vmax: float, vint: float) -> np.ndarray:
    n = int(round((vmax - vmin) / vint))
    return vmin + vint * (np.arange(1, n + 1) - 0.5)


def _init_grid(a_min, a_max, a_int,
               b_min, b_max, b_int,
               c_min, c_max, c_int,
               phi_min, phi_max, phi_int,
               s3_min, s3_max, s3_int) -> np.ndarray:
    a_vals = _centers(a_min, a_max, a_int)
    b_vals = _centers(b_min, b_max, b_int)
    c_vals = _centers(c_min, c_max, c_int)
    phi_vals = _centers(phi_min, phi_max, phi_int)
    s3_vals = _centers(s3_min, s3_max, s3_int)
    grid = np.array(np.meshgrid(a_vals, b_vals, c_vals, phi_vals, s3_vals, indexing="ij"))
    return grid.reshape(5, -1).T


def _clip(cand: np.ndarray, mins, maxs) -> np.ndarray:
    y = cand.copy()
    for i in range(5):
        y[:, i] = np.clip(y[:, i], mins[i], maxs[i])
    return y


def _neighbors(top40: np.ndarray,
               a_int, b_int, c_int, phi_int, s3_int,
               a_new, b_new, c_new, phi_new, s3_new,
               mins, maxs) -> np.ndarray:
    ii = np.array([1.0, 2.0])
    offsets = np.array(np.meshgrid(ii, ii, ii, ii, ii, indexing="ij")).reshape(5, -1).T
    olds = np.array([a_int, b_int, c_int, phi_int, s3_int], dtype=float)
    news = np.array([a_new, b_new, c_new, phi_new, s3_new], dtype=float)
    all_next = []
    for k in range(min(40, len(top40))):
        center = top40[k, :5]
        cand = center - olds + news * offsets
        cand = _clip(cand, mins, maxs)
        close_to_90 = np.abs(cand[:, 1] - 90) < 5
        if np.any(close_to_90):
            cand[close_to_90, 2] = 0.0
        all_next.append(cand)
    if not all_next:
        return np.empty((0, 5), dtype=float)
    return np.vstack(all_next)


def invert_depthwise(input_filename: str,
                     output_filename: str,
                     dz: float = 25.0,
                     nan_thres: float = 0.5,
                     max_iteration: int = 100,
                     save_json_also: bool = True) -> list[dict]:
    # Load input
    df = pd.read_csv(input_filename, dtype=object)
    df = df.iloc[1:, :].astype(np.float64)
    A = df.values

    z = A[:, 0]
    z_start = math.floor(np.min(z) / dz) * dz
    z_end = math.ceil(np.max(z) / dz) * dz
    znew = np.arange(z_start, z_end + dz, dz, dtype=np.float64)

    # Fixed search ranges (same as MATLAB)
    a_min, a_max, a_int0 = 0.0, 360.0, 45.0
    b_min, b_max, b_int0 = -90.0, 0.0, 22.5
    c_min, c_max, c_int0 = 0.0, 90.0, 22.5
    phi_min, phi_max, phi_int0 = 0.0, 1.0, 0.25
    s3_min, s3_max, s3_int0 = 0.0, 1.0, 0.25
    mins = (a_min, b_min, c_min, phi_min, s3_min)
    maxs = (a_max, b_max, c_max, phi_max, s3_max)

    results = []

    for iz, zmid in enumerate(znew):
        print(f"Progress: {iz+1}/{len(znew)}")
        zmin = max(zmid - dz / 2.0, z_start)
        zmax = min(zmid + dz / 2.0, z_end)

        cond = (z >= zmin) & (z <= zmax)
        major_ms = A[cond, 1]
        btilt = A[cond, 8]
        bazi = A[cond, 9]

        if len(major_ms) == 0:
            results.append({
                "zmid": zmid, "zmin": zmin, "zmax": zmax,
                "Rank_Top40": np.nan, "Rank_Top40_all": np.nan,
                "a_range": np.nan, "b_range": np.nan, "c_range": np.nan,
                "phi_range": np.nan, "S3_range": np.nan,
                "RMSE_store": np.nan, "para_cnt": np.nan,
            })
            continue

        major_nan = np.isnan(major_ms)
        nan_ratio = np.sum(major_nan) / len(major_ms)
        if nan_ratio > nan_thres:
            results.append({
                "zmid": zmid, "zmin": zmin, "zmax": zmax,
                "Rank_Top40": np.nan, "Rank_Top40_all": np.nan,
                "a_range": np.nan, "b_range": np.nan, "c_range": np.nan,
                "phi_range": np.nan, "S3_range": np.nan,
                "RMSE_store": np.nan, "para_cnt": np.nan,
            })
            continue

        # Build initial grid and iterate
        initial = _init_grid(a_min, a_max, a_int0,
                             b_min, b_max, b_int0,
                             c_min, c_max, c_int0,
                             phi_min, phi_max, phi_int0,
                             s3_min, s3_max, s3_int0)
        total_cnt = initial.shape[0]

        a_range_cols, b_range_cols, c_range_cols = [], [], []
        phi_range_cols, s3_range_cols = [], []
        rmse_cols = []
        rank_top40_all = []

        a_int, b_int, c_int = a_int0, b_int0, c_int0
        phi_int, s3_int = phi_int0, s3_int0
        curr_candidates = initial.copy()

        n_sample = len(major_ms)
        iter_cnt = 0
        while (a_int > 0.5) and (iter_cnt < max_iteration):
            iter_cnt += 1
            rmse_this = np.full(total_cnt, np.nan)
            a_col = np.full(total_cnt, np.nan)
            b_col = np.full(total_cnt, np.nan)
            c_col = np.full(total_cnt, np.nan)
            phi_col = np.full(total_cnt, np.nan)
            s3_col = np.full(total_cnt, np.nan)

            k = len(curr_candidates)
            a_col[:k] = curr_candidates[:, 0]
            b_col[:k] = curr_candidates[:, 1]
            c_col[:k] = curr_candidates[:, 2]
            phi_col[:k] = curr_candidates[:, 3]
            s3_col[:k] = curr_candidates[:, 4]

            for idx in range(k):
                a, b, c, phi, s3 = curr_candidates[idx]
                major_fm = np.zeros(n_sample, dtype=float)
                for i in range(n_sample):
                    major, _ = ellip_orien(a=a, b=b, c=c, phi=phi, s3=s3, tl=btilt[i], az=bazi[i])
                    major_fm[i] = major
                rmse_this[idx] = azimuth_rmse(major_ms.copy(), major_fm)

            order = np.argsort(rmse_this[:k])
            top_idx = order[:min(40, k)]
            rank_top40 = np.c_[a_col[top_idx], b_col[top_idx], c_col[top_idx],
                               phi_col[top_idx], s3_col[top_idx], rmse_this[top_idx]]
            rank_top40_all.append(rank_top40)

            a_range_cols.append(a_col)
            b_range_cols.append(b_col)
            c_range_cols.append(c_col)
            phi_range_cols.append(phi_col)
            s3_range_cols.append(s3_col)
            rmse_cols.append(rmse_this)

            a_new = (2.0 / 3.0) * a_int
            b_new = (2.0 / 3.0) * b_int
            c_new = (2.0 / 3.0) * c_int
            phi_new = (2.0 / 3.0) * phi_int
            s3_new = (2.0 / 3.0) * s3_int

            curr_candidates = _neighbors(rank_top40,
                                         a_int, b_int, c_int, phi_int, s3_int,
                                         a_new, b_new, c_new, phi_new, s3_new,
                                         mins, maxs)
            a_int, b_int, c_int, phi_int, s3_int = a_new, b_new, c_new, phi_new, s3_new

        if len(rank_top40_all):
            Rank_Top40 = rank_top40_all[-1]
        else:
            Rank_Top40 = np.empty((0, 6), dtype=float)

        if len(a_range_cols):
            a_range = np.vstack(a_range_cols).T
            b_range = np.vstack(b_range_cols).T
            c_range = np.vstack(c_range_cols).T
            phi_range = np.vstack(phi_range_cols).T
            S3_range = np.vstack(s3_range_cols).T
            RMSE_store = np.vstack(rmse_cols).T
            Rank_Top40_all = np.stack(rank_top40_all, axis=2)
        else:
            a_range = b_range = c_range = phi_range = S3_range = RMSE_store = np.empty((initial.shape[0], 0))
            Rank_Top40_all = np.empty((40, 6, 0))

        results.append({
            "zmid": float(zmid),
            "zmin": float(zmin),
            "zmax": float(zmax),
            "Rank_Top40": Rank_Top40,
            "Rank_Top40_all": Rank_Top40_all,
            "a_range": a_range,
            "b_range": b_range,
            "c_range": c_range,
            "phi_range": phi_range,
            "S3_range": S3_range,
            "RMSE_store": RMSE_store,
            "para_cnt": int(initial.shape[0]),
        })

    # Save .mat (struct array-like)
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    # Convert list of dicts to MATLAB struct array using object array
    mat_param = []
    for item in results:
        mat_param.append({k: v for k, v in item.items()})
    savemat(output_filename, {"param": np.array(mat_param, dtype=object)}, do_compression=True)

    if save_json_also:
        json_path = os.path.splitext(output_filename)[0] + ".json"
        serializable = []
        for item in results:
            serializable.append({
                "zmid": item["zmid"],
                "zmin": item["zmin"],
                "zmax": item["zmax"],
                "Rank_Top40": np.array(item["Rank_Top40"]).tolist() if isinstance(item["Rank_Top40"], np.ndarray) else None,
                "para_cnt": None if isinstance(item["para_cnt"], float) and math.isnan(item["para_cnt"]) else item["para_cnt"],
            })
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False)

    return results


if __name__ == "__main__":
    input_filename = os.path.join(V1_ROOT, "data", "ST1_20210305_borehole_ellipticity_outputs",
                                  "ellipticity_parameters_outlier_filtered_dz0.025m_borehole_trajectory.csv")
    output_filename = os.path.join(V1_ROOT, "data", "ST1_20210305_stress_inversion_outputs", "EllipseStressInv_win25m_py.mat")
    print("Processing (depth-wise inversion)...")
    invert_depthwise(input_filename=input_filename, output_filename=output_filename, dz=25.0, nan_thres=0.5)
    print(f"Done. Output saved to {output_filename}")



