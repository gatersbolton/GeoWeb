"""
Code description:
Filter the outliers of borehole ellipticity based on the ellipse fitting error.


Inputs:
1. File path of borehole ellipticity parameters (.csv file).
2. Resampling depth interval. Defaults to 0.025 m.
3. Resampling method. Defaults to "average".
4. Output file path of the resampled ellipticity parameters (.csv file)

Outputs:
1. The resampled ellipticity parameters over the measured depth.


Created by Guangyu Wang @ University of Science and Technology of China.
September 16, 2025

Version 1.0
© Copyright Guanyu Wang, 2025. All rights reserved.
"""

import pandas as pd
import numpy as np
import sys
sys.path.append('..')
from functions import resample

# ---------------------- Input section ---------------------- #
# File path of the input ellipticity parameters.
fpin = "../data/ST1_20210305_borehole_ellipticity_outputs/ellipticity_parameters_outlier_filtered.csv"
# Resampling depth interval (m).
dz = 0.025
# Subsampling method.
# "average": taking the average value of each ellipticity parameters (circular mean for azimuths).
# "nearest": taking the nearest value of each ellipticity paramters.
method = "average"
# File path of the output ellipticity parameters.
fpout = "../data/ST1_20210305_borehole_ellipticity_outputs/ellipticity_parameters_outlier_filtered_dz0.025m.csv"
# ----------------------------------------------------------- #

# Load data.
df = pd.read_csv(fpin, dtype=object)
# Get measured depth.
z = df['Depth'].values[1:].astype(np.float64)
# Get major and minor axis azimuths.
phi = df.iloc[1:, 1:3].values.astype(np.float64)
# Get the rest of the data.
other = df.iloc[1:, 3:].values.astype(np.float64)

if method == "average":
    # Subsample major and minor axis azimuth using the circular mean window.
    z_sub, phi_sub = resample(z, phi, dz=dz, method='circmean')
    # Subsample the rest of the data using mean window.
    _, other_sub = resample(z, other, dz=dz, method='average')
elif method == "nearest":
    # Subsample major and minor axis azimuth using the circular mean window.
    z_sub, phi_sub = resample(z, phi, dz=dz, method='nearest')
    # Subsample the rest of the data using mean window.
    _, other_sub = resample(z, other, dz=dz, method='nearest')

# Concatenate the subsampled data.
data = np.c_[z_sub, phi_sub, other_sub]
# Construct new dataframe.
df_data = pd.DataFrame(data=data, columns=df.columns)
df_unit = df.iloc[:1, :].copy()
df_new = pd.concat([df_unit, df_data], ignore_index=True)
# Save new dataframe.
df_new.to_csv(fpout, index=False)
    