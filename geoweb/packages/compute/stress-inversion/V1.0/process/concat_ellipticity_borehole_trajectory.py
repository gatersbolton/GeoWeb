"""
Code description:
Add borehole trajectory to ellipticity parameters as additional columns based on the measured depth.

Inputs:
1. File path of borehole ellipticity parameters (.csv file).
2. File path of borehole tilt (.csv file).
3. File path of borehole azimuth (.csv file).
4. Output file path (.csv file)

Outputs:
1. Borehole ellipticity and trajectory in a single csv file.

Created by Guangyu Wang @ University of Science and Technology of China.
September 17, 2025

Version 1.0
© Copyright Guanyu Wang, 2025. All rights reserved.
"""


# Import dependencies.
import pandas as pd
import numpy as np
import sys
sys.path.append('../')


# ---------------------- Input section ---------------------- #
# File path of borehole ellipticity parameters.
felp = "../data/ST1_20210305_borehole_ellipticity_outputs/ellipticity_parameters_outlier_filtered_dz0.025m.csv"
# File path of borehole tilt.
fbtl = "../data/ST1_20210305_DEV_ATV_up_main_TILT.csv"
# File path of borehole azimuth.
fbaz = "../data/ST1_20210305_DEV_ATV_up_main_AZIMUTH.csv"
# Output file path.
fout = '../data/ST1_20210305_borehole_ellipticity_outputs/ellipticity_parameters_outlier_filtered_dz0.025m_borehole_trajectory.csv'
# ----------------------------------------------------------- #

# Load ellipticity data.
df_elp = pd.read_csv(felp, dtype=object)
z_elp = df_elp['Depth'].values[1:].astype(np.float64)
v_elp = df_elp.iloc[1:, 1:].values.astype(np.float64)

# Load borehole trajectory data.
df_btl = pd.read_csv(fbtl, dtype=object)
df_baz = pd.read_csv(fbaz, dtype=object)
z_btl = df_btl.loc[1:, 'Depth'].values.astype(np.float32)
z_baz = df_baz.loc[1:, 'Depth'].values.astype(np.float32)
baz = df_baz.loc[1:, 'Azimuth'].values.astype(np.float32)
btl = df_btl.loc[1:, 'Tilt'].values.astype(np.float32)
if (baz < 0).any() or (baz > 360).any():
    print("Abnormal value in borehole azimuth detected")
    exit(1)
if (btl < 0).any() or (btl > 90).any():
    print("Abnormal value in borehole dip detected")
    exit(1)

# Interpolate borehole tilt on ellipticity depth.
btl_elp = np.interp(z_elp, z_btl, btl)
# Interpolate borehole azimuth on breakout depth.
baz_elp = np.interp(z_elp, z_baz, baz)

# Dataframe for units.
dfu = df_elp.iloc[:1, :].copy()
dfu['Borehole_Tilt'] = 'deg'
dfu['Borehole_Azimuth'] = 'deg'

# Dataframe for values.
dfv = pd.DataFrame(columns=dfu.columns, data=np.c_[z_elp, v_elp, btl_elp, baz_elp])

# Merge together.
df = pd.concat([dfu, dfv], ignore_index=True)

# Save dataframe.
df.to_csv(fout, index=False)

print("Data have been saved to %s" % fout)
