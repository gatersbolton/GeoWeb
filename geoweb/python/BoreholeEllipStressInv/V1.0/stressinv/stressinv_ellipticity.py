"""
Python implementation of borehole ellipticity-based stress inversion (global over full depth),
converted from the MATLAB script `stressinv_ellipticity.m`.

Outputs are kept compatible in naming with the MATLAB version:
- Rank_Top40 (40 x 6): columns [a, b, c, phi, S3, RMSE]
- Rank_Top40_all (40 x 6 x iteration_cnt)
- a_range, b_range, c_range, phi_range, S3_range: shape (total_cnt, iteration_cnt),
  storing the candidate parameters explored per iteration (unused rows are NaN)
- RMSE_store: shape (total_cnt, iteration_cnt)
- para_cnt: total number of initial combinations

The forward model and azimuth RMSE come from `V1.0/functions.py` (ellip_orien, azimuth_rmse).
"""

import os
import sys
import json
import math
import numpy as np
import pandas as pd
from scipy.io import savemat
import time


# Make sure we can import from V1.0/functions.py when running this script directly
THIS_DIR = os.path.dirname(__file__)
V1_ROOT = os.path.abspath(os.path.join(THIS_DIR, os.pardir))
if V1_ROOT not in sys.path:
    sys.path.append(V1_ROOT)

from functions import ellip_orien, azimuth_rmse  # noqa: E402


def _load_numeric_matrix_from_csv(path: str) -> np.ndarray:
    # Detect Git LFS pointer file early
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = "".join([next(f, "") for _ in range(3)])
        if "git-lfs.github.com/spec/v1" in head:
            raise RuntimeError(
                f"Input file looks like a Git LFS pointer, not real data: {path}\n"
                "Please fetch large data files (e.g., run `git lfs install` then `git lfs pull`), "
                "or download the dataset from the project data source."
            )
    except FileNotFoundError:
        raise

    # Read CSV, drop unit/header row, coerce to numeric
    df = pd.read_csv(path, dtype=str)
    if len(df) > 0:
        df = df.iloc[1:, :]
    df = df.apply(pd.to_numeric, errors="coerce")

    # Basic shape sanity check
    if df.shape[1] < 10:
        raise ValueError(
            f"Unexpected CSV shape {df.shape} from {path}. "
            "Expecting at least 10 columns (Depth + parameters + tilt + azimuth). "
            "Ensure you used the concatenated file with borehole trajectory."
        )
    return df.values


def _build_initial_grid(a_min: float, a_max: float, a_int: float,
                        b_min: float, b_max: float, b_int: float,
                        c_min: float, c_max: float, c_int: float,
                        phi_min: float, phi_max: float, phi_int: float,
                        s3_min: float, s3_max: float, s3_int: float) -> np.ndarray:
    """
    Create initial candidate grid using interval midpoints, consistent with MATLAB code:
    value = min + interval * (index - 0.5)
    Returns an array of shape (N, 5) with columns [a, b, c, phi, s3].
    """
    def centers(vmin, vmax, vint):
        n = int(round((vmax - vmin) / vint))
        return vmin + vint * (np.arange(1, n + 1) - 0.5)

    a_vals = centers(a_min, a_max, a_int)
    b_vals = centers(b_min, b_max, b_int)
    c_vals = centers(c_min, c_max, c_int)
    phi_vals = centers(phi_min, phi_max, phi_int)
    s3_vals = centers(s3_min, s3_max, s3_int)

    grid = np.array(np.meshgrid(a_vals, b_vals, c_vals, phi_vals, s3_vals, indexing="ij"))
    combos = grid.reshape(5, -1).T  # (N, 5)
    return combos


def _clip_ranges(vals: np.ndarray,
                 mins: tuple[float, float, float, float, float],
                 maxs: tuple[float, float, float, float, float]) -> np.ndarray:
    y = vals.copy()
    y[:, 0] = np.clip(y[:, 0], mins[0], maxs[0])  # a
    y[:, 1] = np.clip(y[:, 1], mins[1], maxs[1])  # b
    y[:, 2] = np.clip(y[:, 2], mins[2], maxs[2])  # c
    y[:, 3] = np.clip(y[:, 3], mins[3], maxs[3])  # phi
    y[:, 4] = np.clip(y[:, 4], mins[4], maxs[4])  # s3
    return y


def _generate_neighbors(top40: np.ndarray,
                        a_int: float, b_int: float, c_int: float, phi_int: float, s3_int: float,
                        a_int_new: float, b_int_new: float, c_int_new: float, phi_int_new: float, s3_int_new: float,
                        mins: tuple[float, float, float, float, float],
                        maxs: tuple[float, float, float, float, float]) -> np.ndarray:
    """
    Generate next-iteration candidates around each of the 40 best solutions.
    For each dimension we place two candidates: center - old_int + new_int * t, t in {1, 2}.
    Total size per iteration: 2^5 * 40 = 1280.
    Also apply the special rule from MATLAB code: if abs(b - 90) < 5 then set c = 0.
    """
    ii = np.array([1.0, 2.0])
    offsets = np.array(np.meshgrid(ii, ii, ii, ii, ii, indexing="ij")).reshape(5, -1).T  # (32, 5)
    olds = np.array([a_int, b_int, c_int, phi_int, s3_int], dtype=float)
    news = np.array([a_int_new, b_int_new, c_int_new, phi_int_new, s3_int_new], dtype=float)

    all_next = []
    for k in range(min(40, len(top40))):
        center = top40[k, :5]  # [a,b,c,phi,s3]
        candidates = center - olds + news * offsets
        # Clip
        candidates = _clip_ranges(candidates, mins, maxs)
        # Special rule on c when |b-90|<5 (kept from MATLAB for compatibility)
        close_to_90 = np.abs(candidates[:, 1] - 90) < 5
        if np.any(close_to_90):
            candidates[close_to_90, 2] = 0.0
        all_next.append(candidates)

    if not all_next:
        return np.empty((0, 5), dtype=float)
    return np.vstack(all_next)


def _forward_major_a_list(candidates: np.ndarray, tilt: np.ndarray, azimuth: np.ndarray) -> np.ndarray:
    """
    For each candidate [a,b,c,phi,s3], forward-model the major-axis azimuth at all samples,
    then compute RMSE vs measured. This function only constructs the forward model holder;
    RMSE aggregation is done outside for clarity.
    """
    # Placeholder; we compute per-candidate forward values outside for memory control.
    raise NotImplementedError


def invert_global(input_filename: str,
                  output_filename: str,
                  max_iteration: int = 100,
                  save_json_also: bool = True,
                  sample_stride: int = 1) -> dict:
    # Load and parse input CSV robustly
    A = _load_numeric_matrix_from_csv(input_filename)

    # Columns per MATLAB script (1-based in MATLAB):
    # major_ms = A(:,2); btilt = A(:,9); bazi = A(:,10)
    major_ms = A[:, 1]
    btilt = A[:, 8]
    bazi = A[:, 9]

    # Optional subsampling along depth to speed up inversion
    if sample_stride is None or sample_stride < 1:
        sample_stride = 1
    if sample_stride > 1:
        major_ms = major_ms[::sample_stride]
        btilt = btilt[::sample_stride]
        bazi = bazi[::sample_stride]

    n_sample = len(major_ms)

    # Initial search ranges (same as MATLAB)
    a_min, a_max, a_int = 0.0, 360.0, 45.0
    b_min, b_max, b_int = -90.0, 0.0, 22.5
    c_min, c_max, c_int = 0.0, 90.0, 22.5
    phi_min, phi_max, phi_int = 0.0, 1.0, 0.25
    s3_min, s3_max, s3_int = 0.0, 1.0, 0.25

    mins = (a_min, b_min, c_min, phi_min, s3_min)
    maxs = (a_max, b_max, c_max, phi_max, s3_max)

    # Build initial grid
    initial = _build_initial_grid(a_min, a_max, a_int,
                                  b_min, b_max, b_int,
                                  c_min, c_max, c_int,
                                  phi_min, phi_max, phi_int,
                                  s3_min, s3_max, s3_int)
    total_cnt = initial.shape[0]

    # Allocate per-MATLAB output containers (fill with NaN for unused rows)
    # We do not know the final iteration count a priori; we keep lists and stack later.
    a_range_cols, b_range_cols, c_range_cols = [], [], []
    phi_range_cols, s3_range_cols = [], []
    rmse_cols = []
    rank_top40_all = []

    # Current candidates and intervals
    curr_candidates = initial.copy()
    iter_idx = 0

    while (a_int > 0.5) and (iter_idx < max_iteration):
        iter_idx += 1
        t0 = time.time()
        print(f"[GlobalInv] Iter {iter_idx} | step={a_int:.3f}° | candidates={len(curr_candidates)} | samples={n_sample}")

        # Prepare storage for this iteration
        rmse_this = np.full(total_cnt, np.nan, dtype=float)
        a_col = np.full(total_cnt, np.nan, dtype=float)
        b_col = np.full(total_cnt, np.nan, dtype=float)
        c_col = np.full(total_cnt, np.nan, dtype=float)
        phi_col = np.full(total_cnt, np.nan, dtype=float)
        s3_col = np.full(total_cnt, np.nan, dtype=float)

        k = len(curr_candidates)
        a_col[:k] = curr_candidates[:, 0]
        b_col[:k] = curr_candidates[:, 1]
        c_col[:k] = curr_candidates[:, 2]
        phi_col[:k] = curr_candidates[:, 3]
        s3_col[:k] = curr_candidates[:, 4]

        # Evaluate RMSE for each candidate
        for idx in range(k):
            a, b, c, phi, s3 = curr_candidates[idx]
            major_fm = np.zeros(n_sample, dtype=float)
            for i in range(n_sample):
                major, _ = ellip_orien(a=a, b=b, c=c, phi=phi, s3=s3, tl=btilt[i], az=bazi[i])
                major_fm[i] = major
            rmse = azimuth_rmse(major_ms.copy(), major_fm)
            rmse_this[idx] = rmse

        # Select Top 40
        order = np.argsort(rmse_this[:k])
        top_idx = order[:min(40, k)]
        rank_top40 = np.c_[
            a_col[top_idx], b_col[top_idx], c_col[top_idx],
            phi_col[top_idx], s3_col[top_idx], rmse_this[top_idx]
        ]
        rank_top40_all.append(rank_top40)

        # Store iteration columns
        a_range_cols.append(a_col)
        b_range_cols.append(b_col)
        c_range_cols.append(c_col)
        phi_range_cols.append(phi_col)
        s3_range_cols.append(s3_col)
        rmse_cols.append(rmse_this)

        # Update intervals
        a_int_new = (2.0 / 3.0) * a_int
        b_int_new = (2.0 / 3.0) * b_int
        c_int_new = (2.0 / 3.0) * c_int
        phi_int_new = (2.0 / 3.0) * phi_int
        s3_int_new = (2.0 / 3.0) * s3_int

        # Generate next iteration candidates around Top40
        next_candidates = _generate_neighbors(
            top40=rank_top40,
            a_int=a_int, b_int=b_int, c_int=c_int, phi_int=phi_int, s3_int=s3_int,
            a_int_new=a_int_new, b_int_new=b_int_new, c_int_new=c_int_new,
            phi_int_new=phi_int_new, s3_int_new=s3_int_new,
            mins=mins, maxs=maxs,
        )

        # Prepare for next loop
        curr_candidates = next_candidates
        a_int, b_int, c_int, phi_int, s3_int = a_int_new, b_int_new, c_int_new, phi_int_new, s3_int_new

        dt = time.time() - t0
        print(f"[GlobalInv] Iter {iter_idx} done in {dt:.2f}s | best RMSE={rank_top40[0,-1]:.4f}")

    # Final Rank_Top40 is the last one
    if len(rank_top40_all):
        Rank_Top40 = rank_top40_all[-1]
    else:
        Rank_Top40 = np.empty((0, 6), dtype=float)

    # Stack columns to form arrays of shape (total_cnt, iteration_cnt)
    if len(a_range_cols):
        a_range = np.vstack(a_range_cols).T
        b_range = np.vstack(b_range_cols).T
        c_range = np.vstack(c_range_cols).T
        phi_range = np.vstack(phi_range_cols).T
        S3_range = np.vstack(s3_range_cols).T
        RMSE_store = np.vstack(rmse_cols).T
        Rank_Top40_all = np.stack(rank_top40_all, axis=2)
    else:
        a_range = b_range = c_range = phi_range = S3_range = RMSE_store = np.empty((total_cnt, 0))
        Rank_Top40_all = np.empty((40, 6, 0))

    out = {
        "Rank_Top40": Rank_Top40,
        "Rank_Top40_all": Rank_Top40_all,
        "a_range": a_range,
        "b_range": b_range,
        "c_range": c_range,
        "phi_range": phi_range,
        "S3_range": S3_range,
        "RMSE_store": RMSE_store,
        "para_cnt": int(total_cnt),
    }

    # Save .mat for compatibility
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    savemat(output_filename, out)

    # Optional JSON for web consumption
    if save_json_also:
        json_path = os.path.splitext(output_filename)[0] + ".json"
        json_obj = {
            "Rank_Top40": out["Rank_Top40"].tolist(),
            "Rank_Top40_all": out["Rank_Top40_all"].tolist(),
            "para_cnt": out["para_cnt"],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_obj, f, ensure_ascii=False)

    return out


if __name__ == "__main__":
    # Defaults aligned with MATLAB script locations
    input_filename = os.path.join(V1_ROOT, "data", "ST1_20210305_borehole_ellipticity_outputs",
                                  "ellipticity_parameters_outlier_filtered_dz0.025m_borehole_trajectory.csv")
    output_filename = os.path.join(V1_ROOT, "data", "ST1_20210305_stress_inversion_outputs", "EllipseStressInv_py.mat")

    print("Processing (global inversion)...")
    # Use subsampling for faster turnaround on large datasets; adjust to 1 for full precision
    invert_global(input_filename=input_filename, output_filename=output_filename, sample_stride=5)
    print(f"Done. Output saved to {output_filename}")



