"""
Code description:
Filter the outliers of borehole ellipticity based on the ellipse fitting error.


Inputs:
1. File path of borehole ellipticity parameters (.csv file).
2. Depth intervals for processing.
3. Maximum ellipse fitting error.
4. Output file path of the filtered ellipticity parameters (.csv file)

Outputs:
1. The filtered borehole ellipticity parameters, where the measurements with ellipse fitting error greater than the maximum ellipse fitting erorr are removed.


Created by Guangyu Wang @ University of Science and Technology of China.
September 16, 2025

Version 1.0
© Copyright Guanyu Wang, 2025. All rights reserved.
"""

import pandas as pd
import numpy as np
import sys
sys.path.append('..')


# ---------------------- Input section ---------------------- #
# Input file path.
fpin = "../data/ST1_20210305_borehole_ellipticity_outputs/ellipticity_parameters.csv"
# Depth interval for processing. Input None to use the minimum/maximum value.
zmin, zmax = 20, None
# Maximum ellipse fitting error (mm).
max_error = 1
# Output file path.
fpout = "../data/ST1_20210305_borehole_ellipticity_outputs/ellipticity_parameters_outlier_filtered.csv"
# ----------------------------------------------------------- #

# Load ellipticity dataframe.
df = pd.read_csv(fpin, dtype=object)
# Get measured depth.
z = df['Depth'].values[1:].astype(np.float64)
# Default depth interval.
if zmin is None:
    zmin = z.min()
if zmax is None:
    zmax = z.max()
# Drop samples outside the depth interval.
zidx = np.argwhere((z < zmin) | (z > zmax))
if len(zidx):
    zidx = np.squeeze(zidx)
    df.drop(index=zidx+1, inplace=True)  # +1 because the first row contains units.
    df.reset_index(drop=True, inplace=True)
# Get ellipse fitting error.
rmse = df['FittingError'].values[1:].astype(np.float64)
# Calculate statistic parameters of the ellipse fitting error, ignoring NaN values.
rmse_min = np.nanmin(rmse)
rmse_max = np.nanmax(rmse)
rmse_mean = np.nanmean(rmse)
rmse_std = np.nanstd(rmse)
# Print statistic parameters.
print('Ellipse fitting error before filtering: [min = %.2f, max = %.2f, mean = %.2f, std = %.2f]' 
      % (rmse_min, rmse_max, rmse_mean, rmse_std))
# Filter the outliers of ellipse fitting error.
idx = np.argwhere(rmse > max_error)
if len(idx):
    idx = np.squeeze(idx)
    df_new = df.drop(index=idx+1)
    df_new.reset_index(drop=True, inplace=True)
# Check if the outliers are all filtered.
rmse_check = df_new['FittingError'].values[1:].astype(np.float64)
rmse_check_min = np.nanmin(rmse_check)
rmse_check_max = np.nanmax(rmse_check)
rmse_check_mean = np.nanmean(rmse_check)
rmse_check_std = np.nanstd(rmse_check)
print('Ellipse fitting error after filtering: [min = %.2f, max = %.2f, mean = %.2f, std = %.2f]' 
      % (rmse_check_min, rmse_check_max, rmse_check_mean, rmse_check_std))
print('%d outliers removed' % (len(df) - len(df_new)))
df_new.to_csv(fpout, index=False)
print('Data saved to %s' % fpout)
