"""
Visualize borehole cross-section and its ellipticity. 
"""


# Import packages.
import os, sys
sys.path.append('..')
from functions import *
from matplotlib.widgets import Slider, RangeSlider
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Ellipse


plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.directory'] = './'
plt.rcParams['font.family'] = 'Arial'

# Load ellipticity data.
fp_ellip = input("Borehole ellipticity directory: ") 

# Ellipse parameters.
sys.stdout.write("\rLoading... ")
df = pd.read_csv(os.path.join(fp_ellip, 'ellipse_parameters.csv'), dtype=object)
units = df.iloc[0, :]  # Units.
data = df.iloc[1:, :]  # Data.

# Major axis azimuth.
phi_major = data['Azimuth_MajorAxis'].values.astype(np.float64)  

# Minor axis azimuth.
phi_minor = data['Azimuth_MinorAxis'].values.astype(np.float64) 

# Major axis diameter.
d_major = data['Diameter_MajorAxis'].values.astype(np.float64)  

# Minor axis diameter.
d_minor = data['Diameter_MinorAxis'].values.astype(np.float64)

# Ellipse fitting error.
rms = data['FittingError'].values.astype(np.float64)

# Measured radius.
rm, zm, phim, um = read_csv(os.path.join(fp_ellip, 'measured_radius.csv'), 
						    azimuth_col=False)
# # Measured traveltime.
# tt, zt, phit, ut = read_csv(os.path.join(fp_ellip, 'measured_traveltime.csv'), 
# 							azimuth_col=False)

# Fitted ellipse radius.
re, ze, phie, ue = read_csv(os.path.join(fp_ellip, 'ellipse_radius.csv'), 
					  		azimuth_col=False)

# Centralized borehole radius.
rc, zc, phic, uc = read_csv(os.path.join(fp_ellip, 'centralized_radius.csv'), 
							azimuth_col=False)

# # Centralized traveltime.
# tc, ztc, phitc, utc = read_csv(os.path.join(fp_ellip, 'centralized_traveltime.csv'), 
# 							   azimuth_col=False)

sys.stdout.write("Done.\n")

# Remove negative values.
# _, _, idx = rm_neg_img(tt, zt)
# zm = zm[idx]  # Measured depth.
# zc = zc[idx]
# rm = rm[idx]  # Measured radius.
# re = re[idx, :]  # Ellipse radius.
# rc = rc[idx, :]  # Centralized radius.
# # tc = tc[idx, :]  # Centralized traveltime.
# rms = rms[idx]  # Fitting error.
# phi_major = phi_major[idx]  # Major axis azimuth.
# phi_minor = phi_minor[idx]  # Minor axis azimuth.
# d_major = d_major[idx]  # Major diameter.
# d_minor = d_minor[idx]  # Minor diameter.


# Load mask data.
fp_mask = input("Mask file path: ")
if fp_mask.lower() != 'none':
	sys.stdout.write("\rLoading... ")
	mask, z_mask, _, _ = read_csv(fp_mask, azimuth_col=False)
	if len(z_mask) != len(zc) or (z_mask != zc).any():
		mask = interp_nn(z_mask, mask, zc)
	mask[mask != 1] = 0
	sys.stdout.write("Done.\n")

# Borehole cross-sectional shape.
zmin = input("Minimum depth [%s] (enter 'none' to infer from file): " % um['z'])
zmax = input("Maximum depth [%s] (enter 'none' to infer from file): " % um['z'])
if zmin.lower() == 'none':
	zmin = zm.min()
else:
	zmin = float(zmin)
if zmax.lower() == 'none':
	zmax = zm.max()
else:
	zmax = float(zmax)
idx = np.argwhere((zm >= zmin) & (zm <= zmax))
idx = np.squeeze(idx)

z = zm[idx]  # Measured depth.
rm = rm[idx]  # Measured radius.
re = re[idx, :]  # Ellipse radius.
rc = rc[idx, :]  # Centralized radius.
# tt = tt[idx, :]  # Measured traveltime.
# tc = tc[idx, :]  # Centralizd traveltime.
rms = rms[idx]  # Fitting error.
uz = um['z']  # Measured depth unit.
ur = um['value']  # Radius unit.
pma = phi_major[idx]  # Major axis azimuth.
pmi = phi_minor[idx]  # Minor axis azimuth.
angle = azimuth2angle(pma)  # Ellipse major axis angle counter-clockwise from x-axis.
dma = d_major[idx]  # Major diameter.
dmi = d_minor[idx]  # Minor diameter.
if fp_mask.lower() != 'none':
    mask = mask[idx, :]  # Mask.

fig3 = plt.figure(figsize=(15, 7.3), num='Borehole Cross Section')
fig3.subplots_adjust(left=0.10, right=0.98, top=0.95, bottom=0.07)
gs = GridSpec(2, 3, 
			  width_ratios=[1, 1, 2],
			  height_ratios=[1, 1.3], 
			  hspace=0.37, wspace=0.30)
ax31 = fig3.add_subplot(gs[:, 0])
ax32 = fig3.add_subplot(gs[:, 1])
ax33 = fig3.add_subplot(gs[0, 2])
ax34 = fig3.add_subplot(gs[1, 2])

# Measured radius.
im31 = ax31.imshow(rm, aspect='auto', cmap='afmhot_r', 
		   		   extent=[0, 360, z.max(), z.min()])
# im31 = ax31.imshow(tt, aspect='auto', cmap='afmhot_r', 
# 		   		   extent=[0, 360, z.max(), z.min()])  # Delete.
ax31.set_xlim(0, 360)
ax31.set_xticks([0, 90, 180, 270, 360])
ax31.xaxis.set_ticks_position('top')
ax31.xaxis.set_label_position('top')
ax31.set_xlabel(r'Azimuth[$^\circ$]')
ax31.set_ylabel('Depth [%s]' % uz)
cb31 = fig3.colorbar(im31, location='top', pad=0.09, fraction=0.03)
cb31.ax.set_xlabel(ur)
line1 = ax31.axhline(z.min(), ls='--', lw=2, c='b')

# Colorbar range slider.
axRSlider31 = fig3.add_axes([0.11, 0.015, 0.12, 0.05])
RSlider31 = RangeSlider(axRSlider31, 'Range', np.nanmin(rm), np.nanmax(rm))
# RSlider31 = RangeSlider(axRSlider31, 'Range', np.nanmin(tt), np.nanmax(tt))  # Delete
def updateRslider31(val):
    im31.norm.vmin = val[0]
    im31.norm.vmax = val[1]
    fig3.canvas.draw_idle()
RSlider31.on_changed(updateRslider31)

# Centralized radius.
im32 = ax32.imshow(rc, aspect='auto', cmap='afmhot_r', 
				   extent=[0, 360, z.max(), z.min()])
# im32 = ax32.imshow(tc, aspect='auto', cmap='afmhot_r', 
# 				   extent=[0, 360, z.max(), z.min()])  # Delete
ax32.set_xlim(0, 360)
ax32.set_xticks([0, 90, 180, 270, 360])
ax32.xaxis.set_ticks_position('top')
ax32.xaxis.set_label_position('top')
ax32.set_xlabel(r'Azimuth[$^\circ$]')
ax32.set_ylabel('Depth [%s]' % uz)
# ax32.yaxis.set_ticklabels([])
cb32 = fig3.colorbar(im32, location='top', pad=0.09, fraction=0.03)
cb32.ax.set_xlabel(ur)
line2 = ax32.axhline(z.min(), ls='--', lw=2, c='b')

# Colorbar range slider.
axRSlider32 = fig3.add_axes([0.37, 0.015, 0.12, 0.05])
RSlider32 = RangeSlider(axRSlider32, 'Range', np.nanmin(rc), np.nanmax(rc))
# RSlider32 = RangeSlider(axRSlider32, 'Range', np.nanmin(tc), np.nanmax(tc))  # Delete
def updateRslider32(val):
    im32.norm.vmin = val[0]
    im32.norm.vmax = val[1]
    fig3.canvas.draw_idle()
RSlider32.on_changed(updateRslider32)

# Display mask above log image.
if fp_mask.lower() != 'none':
	# color = np.array([30/255, 144/255, 255/255, 0.6])
	color = np.array([44/255, 160/255, 44/255, 0.6])
	h, w = mask.shape
	mask_img = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
	ax31.imshow(mask_img, aspect='auto', extent=[0, 360, z.max(), z.min()])
	ax32.imshow(mask_img, aspect='auto', extent=[0, 360, z.max(), z.min()])

# Azimuthal variation.
phi = phim.copy()
p331, = ax33.plot(phi, re[0, :], lw=1.5, c='r', label='Fitted', 
				  zorder=3)
if fp_mask.lower() != 'none':
    mx = mask[0, :]
    p332, = ax33.plot(phi[mx == 0], rc[0, :][mx == 0], 'bo', 
                      label='Non-breakout', ms=2, zorder=2)
    p333, = ax33.plot(phi[mx == 1], rc[0, :][mx == 1], color='#ff7f0e', 
                      marker='o', ls='', label='Breakout', ms=2, zorder=2)
else:
	p332, = ax33.plot(phi, rc[0, :], 'bo', label='Measured', 
					ms=2, zorder=2)
ax33.set_xlim(0, 360)
ax33.set_ylim(min(re[0, :].min(), rc[0, :].min()),
			  max(re[0, :].max(), rc[0, :].max()))
ax33.set_xticks([0, 90, 180, 270, 360])
ax33.set_xlabel(r'Azimuth [$^\circ$]')
ax33.set_ylabel('Radius [%s]' % ur)
ax33.set_title("Fitting error: %.3f %s" % (rms[0], ur))
ax33.grid(ls=':', zorder=1)
ax33.legend()

# Borehole cross-sectional shape.
xelp, yelp = polar2cart(rc, phi)
ax34.set_aspect('equal')
if fp_mask.lower() != 'none':
	p341, = ax34.plot(xelp[0, :][mx==0], yelp[0, :][mx==0], 'bo', ms=3, 
					  zorder=1) 
	p344, = ax34.plot(xelp[0, :][mx==1], yelp[0, :][mx==1], 
					  marker='o', ms=3, color='#ff7f0e',  
					  ls='', 
					  zorder=1)
else:
	p341, = ax34.plot(xelp[0, :], yelp[0, :], 'bo', ms=3, 
					  zorder=2)
ax34.set_xlim(np.nanmin(xelp[0, :]), np.nanmax(xelp[0, :]))
ax34.set_ylim(np.nanmin(yelp[0, :]), np.nanmax(yelp[0, :]))
elp = Ellipse(xy=(0, 0), 
			  width=dma[0], 
			  height=dmi[0], 
			  angle=angle[0], 
			  fill=False, 
			  edgecolor='r', 
			  linestyle='-', 
			  linewidth=1.5, 
			  zorder=3)
ax34.add_patch(elp)
pts = ellipse_axis_endpoints(xc=0, yc=0, 
							 d_major=dma[0], 
							 d_minor=dmi[0], 
							 angle=angle[0])
x1_major, y1_major = pts['major'][0]
x2_major, y2_major = pts['major'][1]
x1_minor, y1_minor = pts['minor'][0]
x2_minor, y2_minor = pts['minor'][1]
p342,  = ax34.plot([x1_major, x2_major], 
                   [y1_major, y2_major], 
				   c='deepskyblue', 
       			   ls='-', 
             	   label='Major axis')
p343,  = ax34.plot([x1_minor, x2_minor], 
                   [y1_minor, y2_minor], 
				   c='limegreen', 
       			   ls='-', 
             	   label='Minor axis')
ax34.set_xlabel('X [%s]' % ur)
ax34.set_ylabel('Y [%s]' % ur)
ax34.legend(bbox_to_anchor=(1.41, 1))
ax34.grid(ls=':', zorder=1)
ax34.set_title(r'Major axis azimuth: $%.2f^\circ$'
				'\n'
			   r'$\mathrm{d_{max}}$: %.2f %s, $\mathrm{d_{min}}$: %.2f %s, ratio: %.3f'  
          		% (pma[0], 
               	   dma[0], uc['value'], 
                   dmi[0], uc['value'], 
                   dmi[0]/dma[0]))
ax34.set_xlim()

# Depth slider.
axZSlider3 = fig3.add_axes([0.01, 0.05, 0.04, 0.90])
ZSlider3 = Slider(ax=axZSlider3, 
				  orientation='vertical', 
                  label='Depth [%s]' % uz, 
                  valmin=z.min(), 
                  valmax=z.max(), 
                  valinit=z.min(), 
                  valstep=z, 
                  initcolor='none')
def updateZslider3(val):
	idx = np.squeeze(np.argwhere(z==val))
	if idx.ndim == 1:
		idx = idx[0]
	line1.set_ydata(val)
	line2.set_ydata(val)
	retmp = re[idx, :]  # Fitted radius.
	rctmp = rc[idx, :]  # Centralized radius.
	p331.set_data(phi, retmp)
	if fp_mask.lower() != 'none':
		mx = mask[idx, :]  # Mask.
		p332.set_data(phi[mx == 0], rctmp[mx == 0])
		p333.set_data(phi[mx == 1], rctmp[mx == 1])
		p341.set_data(xelp[idx][mx==0], yelp[idx][mx==0])
		p344.set_data(xelp[idx][mx==1], yelp[idx][mx==1])
	else:
		p332.set_data(phi, rctmp)
		p341.set_data(xelp[idx], yelp[idx])
	ax34.set_xlim(np.nanmin(xelp[idx, :]), np.nanmax(xelp[idx, :]))
	ax34.set_ylim(np.nanmin(yelp[idx, :]), np.nanmax(yelp[idx, :]))
	pts = ellipse_axis_endpoints(xc=0, yc=0, 
								 d_major=dma[idx], 
								 d_minor=dmi[idx], 
								 angle=angle[idx])
	x1_major, y1_major = pts['major'][0]
	x2_major, y2_major = pts['major'][1]
	x1_minor, y1_minor = pts['minor'][0]
	x2_minor, y2_minor = pts['minor'][1]
	p342.set_data([x1_major, x2_major], [y1_major, y2_major])
	p343.set_data([x1_minor, x2_minor], [y1_minor, y2_minor])
	elp.set_width(dma[idx])
	elp.set_height(dmi[idx])
	elp.set_angle(angle[idx])
	ax33.set_ylim(min(retmp.min(), rctmp.min()), max(retmp.max(), rctmp.max()))
	ax33.set_title("Fitting error: %.3f %s" % (rms[idx], ur))
	ax34.set_title(r'Major axis azimuth: $%.2f^\circ$'
				'\n'
			   r'$\mathrm{d_{max}}$: %.2f %s, $\mathrm{d_{min}}$: %.2f %s, ratio: %.3f'  
          		% (pma[idx], 
               	   dma[idx], uc['value'], 
                   dmi[idx], uc['value'], 
                   dmi[idx]/dma[idx]))
	fig3.canvas.draw_idle()
ZSlider3.on_changed(updateZslider3)

plt.show()

