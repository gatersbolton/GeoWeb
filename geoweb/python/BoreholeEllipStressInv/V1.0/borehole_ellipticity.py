"""
Code description:
Calculate borehole cross-sectional ellipticity using acoustic televiewer (ATV) traveltime logs.


Inputs:
1. ATV traveltime log (.csv file).
2. ATV tool's acoustic window traveltime (AWT) log (.csv file, optional).
3. ATV tool's AWT (when the AWT log is not available)
4. Radius of ATV tool's acoustic head.
5. Sonic velocity of borehole fluid.
6. A mutilplier for converting the ATV traveltime's unit to millisecond (optional).
7. ATV traveltime log's mask which will partially exclude the traveltime log from ellipse fitting (.csv file, optional).
8. Output directory path.


Outputs:
1. ellipticity_parameters.csv
   Ellipticity parameters including ellipse axis azimuths, ellipse axis diameters, ellipse fitting error, ATV tool's coordinates relative to the borehole's center).
   
2. centralized_traveltime.csv
   Centralized ATV traveltime log. 
   
3. borehole_radius.csv
   Borehole radius log, derived from the centralized ATV traveltime log.
   
4. borehole_cross_section_azimuths.csv
   Borehole cross-section's circumferential azimuths with respect to the true borehole center.


Created by Guangyu Wang @ University of Science and Technology of China.
June 27, 2025

Version 1.0
© Copyright Guanyu Wang, 2025. All rights reserved.
"""


# Import packages.
from functions import *
import sys, os
from scipy import interpolate


# ---------------------- Input section ---------------------- #
# File path to the ATV traveltime log.
fp_tt = './data/ST1_20210305_DEV_ATV_up_main_TT_NM.csv'
# File path to the ATV tool's acoustic window traveltime (AWT) log. 
# Optional. Input None if not available.
# The AWT is the two-way traveltime of the acoustic signal within the ATV tool.
fp_wtt = './data/ST1_20210305_DEV_ATV_up_main_WNDTIME.csv'
# When the AWT log is not available, define an AWT value (same unit as the ATV traveltime).
# Optional. Input None if the AWT log is available.
wtt = None
# Radius of the ATV tool's acoustic head (unit: meter).
rp = 0.019  # Reference value for ALT-QL40-ABI.
# Sonic velocity of borehole fluid (unit: m/s).
vf = 1480
# A mutilplier for converting the ATV traveltime's unit to millisecond.
# Input None if not needed.
beta = None
# File path of the ATV traveltime log's mask which will partially exclude the traveltime log from ellipse fitting.
# Optional.
fp_mask = None
# Output directory.
dir_out = './data/ST1_20210305_borehole_ellipticity_outputs'
# ----------------------------------------------------------- #


# Load ATV traveltime log.
sys.stdout.write('\rLoading ATV traveltime log...')
tt, z_tt, phi_tt, u_tt = read_csv(fpath=fp_tt, azimuth_col=False)
sys.stdout.write(' Done.\n')
print("Traveltime [%s]: %.3f - %.3f (mean: %.4f)" % \
	  (u_tt['value'], tt.min(), tt.max(), tt.mean()))
print("Measured depth [%s]: %.3f - %.3f (spacing: %.4f)" % 
      (u_tt['z'], z_tt.min(), z_tt.max(), np.diff(z_tt).mean()))
print("Azimuth [deg]: %.1f - %.1f (spacing: %.1f)" %
      (phi_tt.min(), phi_tt.max(), np.diff(phi_tt).mean()))
n, m = tt.shape


# Load AWT log if available.
if fp_wtt is not None:
	df_wtt = pd.read_csv(fp_wtt, dtype=object)
	uz = df_wtt.values[0, 0]  # Measured depth unit.
	uv = df_wtt.values[0, -1]  # Traveltime unit.
	df_wtt = df_wtt.iloc[1:, :].astype(np.float64)  # Remove the unit row.
	df_wtt.reset_index(drop=True, inplace=True)
	z_wtt = df_wtt.values[:, 0]  # Measured depth.
	wtt = df_wtt.values[:, -1]  # Travel time of acoustic window reflection. 
	idx = np.argwhere(wtt < 0)  # Check negative/abnormal value (e.g. -999)
	# Abnormal value detected in the AWT log.
	if len(idx):
		idx = np.squeeze(idx, axis=1)
		df_wtt.drop(index=idx, inplace=True)  # Remove rows with negative values.
		z_old = df_wtt.values[:, 0]
		wtt_old = df_wtt.values[:, -1]
		f = interpolate.interp1d(z_old, wtt_old, 
								 kind='nearest', 
								 fill_value='extrapolate')
		wtt = f(z_tt)  # Interpolate on the measured depth of ATV traveltime.
		z_wtt = z_tt.copy()
	# AWT log's measured depths are not identical to ATV traveltime log's measured depths.
	if len(z_wtt) != len(z_tt) or (z_wtt != z_tt).any():
		f = interpolate.interp1d(z_wtt, wtt, 
								 kind='nearest', 
								 fill_value='extrapolate')
		wtt = f(z_tt)  # Interpolate on the measured depth of ATV traveltime.
		z_wtt = z_tt.copy()

# If the AWT log is not available, use a constant AWT value .
else:
	wtt = np.ones(len(z_tt), dtype=np.float64) * float(wtt)
	z_wtt = z_tt.copy()
	uz = u_tt['z']
	uv = u_tt['value']
# Reshape the AWT log.	
wtt = np.tile(wtt, (m, 1)).T  # Repeat m times (n, ) -> (n, m).
print("Acoustic window traveltime [%s]: %.3f - %.3f (mean: %.3f)"\
	  % (uv, wtt.min(), wtt.max(), wtt.mean()))  


# Convert the traveltime unit to microsecond if needed.
if beta is not None:
	tt *= float(beta)  # Traveltime.
	wtt *= float(beta)  # Acoustic window traveltime.    


# Load ATV traveltime log's mask if available.
if fp_mask is not None:
	mask, z_mask, phi_mask, u_mask = read_csv(fpath=fp_mask, azimuth_col=False)
	if len(z_tt) != len(z_mask) or (z_tt - z_mask != 0).any():
		mask = interp_nn(z_mask, mask, z_tt)


# Create the output directory if not exist.
if not os.path.exists(dir_out):
    os.makedirs(dir_out)


# Initialize variables. 
param = np.full((len(tt), 8), fill_value=np.nan, dtype=np.float64)  # Ellipticity parameters.
param[:, 0] = z_tt  # Measured depth.
r = np.full(tt.shape, fill_value=np.nan, dtype=np.float64) # Measured borehole radius.
r_e = np.full(tt.shape, fill_value=np.nan, dtype=np.float64)  # Ellipse radius.
r_c = np.full(tt.shape, fill_value=np.nan, dtype=np.float64)  # Centralized borehole radius.
tt_c = np.full(tt.shape, fill_value=np.nan, dtype=np.float64)  # Centralized traveltime.
phi_c = np.full(tt.shape, fill_value=np.nan, dtype=np.float64)  # Centralized azimuth.


# Use the ellipse to fit the borehole cross section.
for i in range(len(tt)):
	sys.stdout.write('\rProcessing: %.2f%%' % ((i+1) / len(tt) * 100))

	# Check negative/abnormal values (e.g., -999).
	if (tt[i, :] < 0).any():
		continue
	
	# Compute borehole radius.
	r[i, :] = (tt[i, :] - wtt[i, :]) / 2 * 1e-6 * vf + rp  # Unit: m.
	r[i, :] *= 1e3  # Unit: mm.
	
	# Cartesian coordinate.
	x, y = polar2cart(radius=r[i, :], angle=phi_tt)

	# Determine cases.
	if fp_mask is None:
		case = 1  # Case 1: Ellipse fitted to all points.
	else:
		case = 2  # Case 2: Ellipse fitted to points without mask. 
		mx = mask[i, :].copy()
		rx = len(mx[mx != 0]) / len(mx)
		if rx > 0.7:
			case = 3  # Case 3: Mask portion exceeds 70%, quit ellipse fitting, assign NaNs.
	
	# Case 3:
	if case == 3:
		for j in range(1, 8):
			param[i, j] = np.nan
	
	# Case 1 or case 2:
	else:
		
		if case == 1:
			ellipse = ellipse_fitting(x, y, mask=None)  # Without mask.
		
		elif case == 2:
			ellipse = ellipse_fitting(x, y, mask=mask[i, :])  # With mask.
	
		# Ellipse center.
		x0, y0 = ellipse['center']  
		
		# Semi-major and semi-minor axes.
		a, b = ellipse['lmajor'], ellipse['lminor']  
		
		# Couter-clockwise angle between x-axis and major axis [0, pi].
		angle = ellipse['angle']  
		
		# Counter-clockwise angle from major axis.
		theta = loop360(loop360(-phi_tt) + 90 - angle)  
		
		# X-coordinates of the fitted ellipse [mm].
		xe = x0 + a * np.cos(np.radians(theta)) * math.cos(math.radians(angle)) -\
			b * np.sin(np.radians(theta)) * math.sin(math.radians(angle))  
		
		# Y-coordinates of the fitted ellipse [mm].
		ye = y0 + a * np.cos(np.radians(theta)) * math.sin(math.radians(angle)) +\
			b * np.sin(np.radians(theta)) * math.cos(math.radians(angle))
		
		# Fitted ellipse radius [mm].
		r_e[i, :] = np.sqrt((xe - x0)**2 + (ye - y0)**2) 
		
		# Centralized borehole radius[mm]. 
		r_c[i, :] = np.sqrt((x - x0)**2 + (y - y0)**2)
		
		# Centralized traveltime [us].
		tt_c[i, :] = (r_c[i, :] * 1e-3 - rp) / vf * 2 * 1e6 + wtt[i, :] 
		
		# Centralized azimuth [deg].
		phi_c[i, :] = angle360(np.degrees(np.arctan2((y - y0), (x - x0))))  
		
		# Major axis azimuth [deg]. 
		major_azimuth = angle2azimuth(angle)  

		# Minor axis azimuth [deg].
		minor_azimuth = loop360(major_azimuth + 90)  
		
		# Compute fitting error [mm].
		x1 = r_e[i, :]
		x2 = r_c[i, :]
		if fp_mask is not None:
			m = mask[i, :]
			x1 = x1[m == 0]
			x2 = x2[m == 0]
		rmse = np.sqrt(np.mean((x1 - x2)**2))

		# Store ellipse parameters. 
		param[i, 1] = major_azimuth
		param[i, 2] = minor_azimuth  
		param[i, 3] = 2 * a  
		param[i, 4] = 2 * b  
		param[i, 5] = x0  
		param[i, 6] = y0
		param[i, 7] = rmse
sys.stdout.write('\n')


# Convert traveltime back to its original unit.
if beta is not None:
	tt_c /= float(beta)  # us -> original unit.
	tt /= float(beta)  # us -> original unit.


# Save outputs.
sys.stdout.write('\rSaving outputs...')

# Ellipticity parameters.
colName = ['Depth', 'Azimuth_MajorAxis', 'Azimuth_MinorAxis',
		   'Diameter_MajorAxis', 'Diameter_MinorAxis', 
		   'Center_x', 'Center_y', 'FittingError']
unitRow = [u_tt['z'], 'deg', 'deg', 'mm', 'mm', 'mm', 'mm', 'mm']
df0 = pd.DataFrame(data=[unitRow], columns=colName)
df1 = pd.DataFrame(data=param, columns=colName)
df = pd.concat([df0, df1], ignore_index=True)
df.to_csv(os.path.join(dir_out, 'ellipticity_parameters.csv'), index=False)

# Centralized traveltime.
write_csv(fpath=os.path.join(dir_out, 'centralized_traveltime.csv'),  
          z=z_tt, 
          value=tt_c, 
          phi=phi_tt, 
          unitZ=u_tt['z'], 
          unitV=u_tt['value'])  

# Centralized borehole radius. 
write_csv(fpath=os.path.join(dir_out, 'borehole_radius.csv'),  
          z=z_tt, 
          value=r_c, 
          phi=phi_tt, 
          unitZ=u_tt['z'], 
          unitV='mm')

# Centralized azimuth.
write_csv(fpath=os.path.join(dir_out, 'borehole_cross_section_azimuths.csv'),  
          z=z_tt, 
          value=phi_c, 
          phi=phi_tt, 
          unitZ=u_tt['z'], 
          unitV='deg')

sys.stdout.write(' Done.\n')
