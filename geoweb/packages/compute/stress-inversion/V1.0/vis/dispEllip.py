"""
Visualize ellipticity of the borehole cross-section.
"""


# Import packages.
import sys
sys.path.append('..')
from functions import *
from matplotlib.widgets import Slider, RangeSlider
from matplotlib.gridspec import GridSpec


# ---------------------- Input section ---------------------- #
# File path to ellipticity parameters.
ellip_fpath = '../data/borehole_ellipticity_outputs/ellipticity_parameters.csv'
# Resampling ellipticity parameters over the measured depth using the following dz interval.
# You may input None to skip the resampling (m, or ft, or other length units, depending on the measured depth in the ATV logs). 
dz = 0.1
# File path to the ATV amplitude log.
fp_atvAmp = '../data/ST1_20210305_DEV_ATV_up_main_AMP_NM.csv'
# File path to the borehole radius log.
fp_atvRad = '../data/borehole_ellipticity_outputs/borehole_radius.csv'
# Colormap for the ATV amplitude log.
cmapAmp = 'gray'
# Colormap for the ATV traveltime log.
cmapRad = 'gray_r'
# File path to the ATV-measured borehole inclination.
fp_atvInc = '../data/ST1_20210305_DEV_ATV_up_main_TILT.csv'
# Fila path to the ATV-measured borehole azimuth.
fp_atvAzi = '../data/ST1_20210305_DEV_ATV_up_main_AZIMUTH.csv'
# Length for display (m, or ft, or other length units, depending on the measured depth in the ATV logs).
lenZ = 5
# ----------------------------------------------------------- #

# Matplotlib global settings. 
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 12

# Load ellipticity data.
# Ellipse parameters.
df = pd.read_csv(ellip_fpath, dtype=object)
units = df.iloc[0, :]  # Units.
data = df.iloc[1:, :]  # Data.
uz = units['Depth']  # Measured depth unit.
z = data['Depth'].values.astype(np.float64)  # Measured depth.

# Major axis azimuth.
phi_major0 = data['Azimuth_MajorAxis'].values.astype(np.float64)  
phi_major1 = loop360(phi_major0 + 180) 

# Minor axis azimuth.
phi_minor0 = data['Azimuth_MinorAxis'].values.astype(np.float64) 
phi_minor1 = loop360(phi_minor0 + 180)

# Major axis diameter.
d_major = data['Diameter_MajorAxis'].values.astype(np.float64)  

# Minor axis diameter.
d_minor = data['Diameter_MinorAxis'].values.astype(np.float64)

# Ellipse center coodinates.
x_center = data['Center_x'].values.astype(np.float64) 
y_center = data['Center_y'].values.astype(np.float64) 

# Ellipse fitting error.
rms = data['FittingError'].values.astype(np.float64)

# Compute axis ratio (minor/major) of the ellipse.
ratio = d_minor / d_major

# Compute median and standard deviation of major and minor axis azimuth.
phi_major_mean = min(np.mean(phi_major0), np.mean(phi_major1))
phi_major_std = min(np.std(phi_major0), np.std(phi_major1))
phi_minor_mean = min(np.mean(phi_minor0), np.mean(phi_minor1))
phi_minor_std = min(np.std(phi_minor0), np.std(phi_minor1))

# Compute eccentric distance of the probe.
ed = np.sqrt(x_center**2 + y_center**2)

# Compute eccentric azimuth of the probe.
x_probe, y_probe = -x_center, -y_center
ea = np.arctan2(y_center, x_center)  # [-pi, pi], oriented counter-clockwise from x-axis (East).
ea = np.degrees(ea)  # Radian to degree.
ea = angle360(ea)  # [0, 360], oriented clockwise from North (y-axis).

# Load image log (ATV amplitude).
sys.stdout.write('\rLoading ATV amplitude log...')
atvAmp, z_atvAmp, _, u_atvAmp = read_csv(fp_atvAmp, azimuth_col=False)
sys.stdout.write(' Done\n')
atvAmp[atvAmp < 0] = np.nan

# Load image log (ATV borehole radius).
sys.stdout.write('\rLoading borehole radius log...')
atvRad, z_atvRad, _, u_atvRad = read_csv(fp_atvRad, azimuth_col=False)
sys.stdout.write(' Done\n')
atvRad[atvRad < 0] = np.nan

# Load tool incliation.
df = pd.read_csv(fp_atvInc, dtype=object)
z_atvInc = df.iloc[1:, 0].values.astype(np.float32)
atvInc = df.iloc[1:, 1].values.astype(np.float32)

# Load tool azimuth.
df = pd.read_csv(fp_atvAzi, dtype=object)
z_atvAzi = df.iloc[1:, 0].values.astype(np.float32)
atvAzi = df.iloc[1:, 1].values.astype(np.float32)

# Enter display length.
print('Measured Depth range: %.2f - %.2f %s' % (z.min(), z.max(), units['Depth']))
if isinstance(lenZ, str) and lenZ.lower() == 'all':
    lenZ = z.max() - z.min()

# Down-sampling.
if dz != None:
	dz = float(dz)
	x = np.median(z)
	sz = len(z[(z >= x) & (z <= x + dz)])
else:
	sz = 1

# Plot axes azimuth, axis ratio, fitting error, tool eccentric distance, eccentric azimuth, incliation, and azimuth.	
fig = plt.figure(figsize=(15, 7.3), num='Ellipticity')
fig.subplots_adjust(top=0.96, bottom=0.03, left=0.08, right=0.98, wspace=0.30)
gs = GridSpec(2, 8, height_ratios=(1, 60), hspace=0.25)
ax = []
for i in range(8):
	ax.append(fig.add_subplot(gs[1, i]))
cbaxAmp = fig.add_subplot(gs[0, 0])
cbaxRad = fig.add_subplot(gs[0, 1])

zminInit, zmaxInit = z.min(), z.min() + lenZ

for i in range(8):
	ax[i].invert_yaxis()
	ax[i].set_ylim(zmaxInit, zminInit)
	ax[i].xaxis.set_ticks_position('top')
	ax[i].xaxis.set_label_position('top')
	if i > 0:
		ax[i].yaxis.set_ticklabels([])
  
# ATV amplitude.
ax[0].set_xlabel('Azimuth [°]')
ax[0].set_xticks([0, 90, 180, 270, 360])
ax[0].set_xlim(0, 360)
ax[0].set_ylabel('Depth [%s]' % units['Depth'])
imAmp = ax[0].imshow(atvAmp, cmap=cmapAmp, aspect='auto', extent=[0, 360, z_atvAmp.max(), z_atvAmp.min()], zorder=1)
ax[0].grid(ls=':', zorder=2)
cbar = fig.colorbar(imAmp, cax=cbaxAmp, orientation='horizontal')
cbar.ax.set_title(f" {u_atvAmp['value']}")
cbar.ax.xaxis.set_label_position('top')

# ATV borehole radius.
imRad = ax[1].imshow(atvRad, cmap=cmapRad, aspect='auto', extent=[0, 360, z_atvAmp.max(), z_atvAmp.min()], zorder=2)
cbar = fig.colorbar(imRad, cax=cbaxRad, orientation='horizontal')
cbar.ax.set_title(f" {u_atvRad['value']}")
cbar.ax.xaxis.set_label_position('top')

# Axes azimuth.
ax[1].set_xlabel('Azimuth [°]')
ax[1].set_xticks([0, 90, 180, 270, 360])
ax[1].set_xlim(0, 360)
# s = np.round(3 + (1 - ratio) * 100 * (9 - 3))  # Point size related to elliptical axis ratio.
# s = s.astype(np.int32)
# ax[0].scatter(phi_major0, z, s=s, c=rms, cmap='viridis', vmin=0, vmax=1, 
#               zorder=5, rasterized=True)
# ax[0].scatter(phi_major1, z, s=s, c=rms, cmap='viridis', vmin=0, vmax=1, 
#               zorder=5, rasterized=True)
ax[1].plot(phi_major0[::sz], z[::sz], c='skyblue', ls='',  
		   marker='o', ms=3, zorder=3, rasterized=True)
ax[1].plot(phi_major1[::sz], z[::sz], c='skyblue', ls='', 
		   marker='o', ms=3, zorder=3, rasterized=True)
ax[1].plot(phi_minor0[::sz], z[::sz], c='springgreen', ls='', 
		   marker='o', ms=3, label='Minor axis', zorder=3)
ax[1].plot(phi_minor1[::sz], z[::sz], c='springgreen', ls='', 
		   marker='o', ms=3, zorder=3)
ax[1].grid(ls=':', zorder=1)

# Axis ratio.
ax[2].set_xlabel('Axis Ratio [-]')
ratioInit = ratio[(z >= zminInit) & (z <= zmaxInit)]
ratioInitMin, ratioInitMax = np.nanmin(ratioInit), np.nanmax(ratioInit)
ax[2].set_xlim(ratioInitMin - 0.05 * (ratioInitMax - ratioInitMin), 
               ratioInitMax + 0.05 * (ratioInitMax - ratioInitMin))
ax[2].plot(ratio, z, c='r', zorder=2, lw=2)
ax[2].grid(ls=':', zorder=1)

# Ellipse fitting error (RMSE).
ax[3].set_xlabel('Fitting Error [%s]' % units['Diameter_MajorAxis'])
rmsInit = rms[(z >= zminInit) & (z <= zmaxInit)]
rmsInitMin, rmsInitMax = np.nanmin(rmsInit), np.nanmax(rmsInit)
ax[3].set_xlim(rmsInitMin - 0.05 * (rmsInitMax - rmsInitMin), 
               rmsInitMax + 0.05 * (rmsInitMax - rmsInitMin))
ax[3].plot(rms, z, c='#ff7f0e', zorder=2, lw=2)
ax[3].grid(ls=':', zorder=1)

# Tool eccentric distance.
ax[4].set_xlabel('Eccentric Distance [%s]' % units['Center_x'])
edInit = ed[(z >= zminInit) & (z <= zmaxInit)]
edInitMin, edInitMax = np.nanmin(edInit), np.nanmax(edInit)
ax[4].set_xlim(edInitMin - 0.05 * (edInitMax - edInitMin), 
               edInitMax + 0.05 * (edInitMax - edInitMin))
ax[4].plot(ed, z, c='#9467bd', zorder=2, lw=2)
ax[4].grid(ls=':', zorder=1)

# Tool eccentric azimuth.
ax[5].set_xlabel('Eccentric Azimuth [°]')
eaInit = ea[(z >= zminInit) & (z <= zmaxInit)]
eaInitMin, eaInitMax = np.nanmin(eaInit), np.nanmax(eaInit)
ax[5].set_xlim(eaInitMin - 0.05 * (eaInitMax - eaInitMin), 
               eaInitMax + 0.05 * (eaInitMax - eaInitMin))
ax[5].plot(ea, z, c='#17becf', zorder=2, lw=2)
ax[5].grid(ls=':', zorder=1)

# Tool inclination.
ax[6].set_xlabel('Tool inclination [°]')
atvIncInit = atvInc[(z_atvInc >= zminInit) & (z_atvInc <= zmaxInit)]
atvIncInitMin, atvIncInitMax = np.nanmin(atvIncInit), np.nanmax(atvIncInit)
ax[6].set_xlim(atvIncInitMin - 0.05 * (atvIncInitMax - atvIncInitMin), 
               atvIncInitMax + 0.05 * (atvIncInitMax - atvIncInitMin))
ax[6].plot(atvInc, z_atvInc, c='k', zorder=2, lw=2)
ax[6].grid(ls=':', zorder=1)

# Tool azimuth.
ax[7].set_xlabel('Tool azimuth [N°E]')
atvAziInit = atvAzi[(z_atvAzi >= zminInit) & (z_atvAzi <= zmaxInit)]
atvAziInitMin, atvAziInitMax = np.nanmin(atvAziInit), np.nanmax(atvAziInit)
ax[7].set_xlim(atvAziInitMin - 0.05 * (atvAziInitMax - atvAziInitMin), 
               atvAziInitMax + 0.05 * (atvAziInitMax - atvAziInitMin))
ax[7].plot(atvAzi, z_atvAzi, c='C7', zorder=2, lw=2)
ax[7].grid(ls=':', zorder=1)

# Depth slider.
zInit = z.min()
axZSlider = fig.add_axes([0.01, 0.05, 0.03, 0.90])
zSlider = Slider(ax=axZSlider, 
                 label=f"Depth({units['Depth']})", 
                 valmin=z.min(), 
                 valmax=z.max(), 
                 valinit=zInit, 
                 orientation='vertical', 
                 valstep=z)
def updateZslider(val):
    zmin, zmax = zSlider.val, zSlider.val + lenZ
    ratioZ = ratio[(z >= zmin) & (z <= zmax)]
    ratioZMin, ratioZMax = np.nanmin(ratioZ), np.nanmax(ratioZ)
    rmsZ = rms[(z >= zmin) & (z <= zmax)]
    rmsZMin, rmsZMax = np.nanmin(rmsZ), np.nanmax(rmsZ)
    edZ = ed[(z >= zmin) & (z <= zmax)]
    edZMin, edZMax = np.nanmin(edZ), np.nanmax(edZ)
    eaZ = ea[(z >= zmin) & (z <= zmax)]
    eaZMin, eaZMax = np.nanmin(eaZ), np.nanmax(eaZ)
    atvIncZ = atvInc[(z_atvInc >= zmin) & (z_atvInc <= zmax)]
    atvIncZMin, atvIncZMax = np.nanmin(atvIncZ), np.nanmax(atvIncZ)
    atvAziZ = atvAzi[(z_atvAzi >= zmin) & (z_atvAzi <= zmax)]
    atvAziZMin, atvAziZMax = np.nanmin(atvAziZ), np.nanmax(atvAziZ)
    for i in range(8):
        ax[i].set_ylim(zmax, zmin)
    ax[2].set_xlim(ratioZMin - 0.05 * (ratioZMax - ratioZMin), 
                   ratioZMax + 0.05 * (ratioZMax - ratioZMin))
    ax[3].set_xlim(rmsZMin - 0.05 * (rmsZMax - rmsZMin), 
                   rmsZMax + 0.05 * (rmsZMax - rmsZMin))
    ax[4].set_xlim(edZMin - 0.05 * (edZMax - edZMin), 
                   edZMax + 0.05 * (edZMax - edZMin))
    ax[5].set_xlim(eaZMin - 0.05 * (eaZMax - eaZMin), 
                   eaZMax + 0.05 * (eaZMax - eaZMin))
    ax[6].set_xlim(atvIncZMin - 0.05 * (atvIncZMax - atvIncZMin), 
                   atvIncZMax + 0.05 * (atvIncZMax - atvIncZMin))
    ax[7].set_xlim(atvAziZMin - 0.05 * (atvAziZMax - atvAziZMin), 
                   atvAziZMax + 0.05 * (atvAziZMax - atvAziZMin)) 
    fig.canvas.draw_idle()
zSlider.on_changed(updateZslider)

# Colorbar range slider (ATV amplitude).
axRSliderAmp = fig.add_axes([0.44, 0.93, 0.13, 0.05])
RSliderAmp = RangeSlider(axRSliderAmp, 'Amp Range', np.nanmin(atvAmp), np.nanmax(atvAmp))
def updateRsliderAmp(val):
	imAmp.norm.vmin = val[0]
	imAmp.norm.vmax = val[1]
	fig.canvas.draw_idle()
RSliderAmp.on_changed(updateRsliderAmp)

# Colorbar range slider (ATV borehole radius).
axRSliderRad = fig.add_axes([0.74, 0.93, 0.13, 0.05])
RSliderRad = RangeSlider(axRSliderRad, 'Rad Range', np.nanmin(atvRad), np.nanmax(atvRad))
def updateRsliderRad(val):
	imRad.norm.vmin = val[0]
	imRad.norm.vmax = val[1]
	fig.canvas.draw_idle()
RSliderRad.on_changed(updateRsliderRad)

# Polar histrogram.
fig1, ax1 = plt.subplots(1, 2, figsize=(8, 4.5),  
						 subplot_kw={'projection': 'polar'}, 
						 num='Ellipse Orientations')
for i in range(2):
	ax1[i].set_theta_direction(-1)
	ax1[i].set_theta_offset(np.pi/2)
	ax1[i].set_xticks(np.radians(np.linspace(0, 360, 12, endpoint=False)))
	ax1[i].set_yticklabels([])
ax1[0].set_title(r'Major axis orientations')
n0, _, patches0 = ax1[0].hist(np.radians(np.r_[phi_major0, phi_major1]),
						      color='skyblue', edgecolor='k', bins=30)
ax1[1].set_title(r'Minor axis orientations')
n1, _, patches1 = ax1[1].hist(np.radians(np.r_[phi_minor0, phi_minor1]),
						      color='springgreen', edgecolor='k', bins=30)
fig1.tight_layout()

plt.show()
