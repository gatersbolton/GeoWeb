"""
Display image logs in csv files.
"""


# Import packages.
import sys
sys.path.append('..')
from functions import read_csv, interp_nn
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.widgets import Slider, RangeSlider, Button


# Load data.
fp_img = input('Image log file path (.csv): ')
sys.stdout.write('\rLoading...')
img, z_img, phi_img, u_img = read_csv(fp_img, azimuth_col=False)
img[img < 0] = np.nan
sys.stdout.write('Done\n')
print("Image log value [%s]: %.3f - %.3f (mean: %.3f)" %
	  (u_img['value'], np.nanmin(img), np.nanmax(img), np.nanmean(img)))
print("Measured depth [%s]: %.3f - %.3f (spacing: %.4f)" % 
      (u_img['z'], z_img.min(), z_img.max(), np.diff(z_img).mean()))
print("Azimuth [deg]: %.1f - %.1f (spacing: %.1f)" % 
      (phi_img.min(), phi_img.max(), np.diff(phi_img).mean()))

# Whether to clip log values or not.
s = input("Clip log values? [y/n]: ")
if s.lower() == 'y':
    vmin = float(input("Input the minimum value: "))
    vmax = float(input("Input the maximum value: "))
elif s.lower() == 'n':
    vmin = np.nanmin(img)
    vmax = np.nanmax(img)

fp_boa = input("Breakout azimuth file path (enter 'none' to skip): ")
if fp_boa.lower() != 'none':
    df = pd.read_csv(fp_boa)
    z_bo = df['Depth'].values[1:].astype(np.float64)  # Breakout measured depth.
    phi_bo = df['Azimuth'].values[1:].astype(np.float64)  # Breakout azimuth.
    op = df['Opening'].values[1:].astype(np.float64)  # Breakout opening.
    op2 = np.zeros((2, len(op)), dtype=np.float64)  # A two-row breakout opening array.
    op2[0, :] = op / 2  # The first row contains openings left to the breakout azimuth.
    op2[1, :] = op / 2  # The second row contains openings right to the breakout azimuth.
    # Some breakout openings might exceed the range of [0, 360] degree, limit them in that range.
    for j in range(len(op)):
        if phi_bo[j] - op2[0, j] < 0:
            op2[0, j] = phi_bo[j] - 0
        if phi_bo[j] + op2[1, j] > 360:
            op2[1, j] = 360 - phi_bo[j]

fp_bom = input("Mask file path (enter 'none' to skip): ")
if fp_bom.lower() != 'none':
	bo_mask, z_mask, _, _ = read_csv(fp_bom)
	if len(z_mask) != len(z_img):
		bo_mask = interp_nn(z_mask, bo_mask, z_img)
	elif (z_mask != z_img).any():
		bo_mask = interp_nn(z_mask, bo_mask, z_img)

# Initilize figure.
lenZ = input(f"Measured depth length for display (Unit: {u_img['z']}) (enter 'all' to display the whole image): ")
if lenZ.lower() == 'all':
    lenZ = z_img.max() - z_img.min()
else:
    lenZ = float(lenZ)
cm = input("Colormap for the log image ('afmhot', 'afmhot_r' or others): ")
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.directory'] = './'
plt.rcParams['font.family'] = 'Arial'
fig, ax = plt.subplots(figsize=(4, 7.3), num='Image Log Viewer')
fig.subplots_adjust(left=0.35, right=0.95, top=0.95, bottom=0.05)

# Display image log.
im = ax.imshow(img, cmap=cm, aspect='auto', extent=[0, 360, z_img.max(), z_img.min()], 
               vmin=vmin, vmax=vmax)

# Display breakout as errorbars.
if fp_boa.lower() != 'none':
    ax.errorbar(x=phi_bo, y=z_bo, xerr=op2, fmt='o', c='g', lw=2, capsize=4)

# Display breakout as masks.
if fp_bom.lower() != 'none':
    color = np.array([30/255, 144/255, 255/255, 0.6])
    h, w = bo_mask.shape
    mask_img = bo_mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
    ax.imshow(mask_img, aspect='auto', extent=[0, 360, z_img.max(), z_img.min()])
    
ax.xaxis.set_ticks_position('top')
ax.xaxis.set_label_position('top')
ax.set_xticks(ticks=[0, 90, 180, 270, 360])
ax.set_xlabel(r'Azimuth [$^\circ$]', fontweight='bold', fontsize=11)
ax.ticklabel_format(axis='y', style='plain')
ax.set_ylim(z_img.min()+lenZ, z_img.min())
ax.set_ylabel(f"Depth [{u_img['z']}]", fontweight='bold', fontsize=11)
ax.tick_params(labelsize=11)
cbar = fig.colorbar(im, location='top', pad=0.08, fraction=0.1)
cbar.ax.set_xlabel(u_img['value'], fontsize=11)
cbar.ax.tick_params(labelsize=11)

# Depth slider.
zInit = z_img.min()
axZSlider = fig.add_axes([0.05, 0.05, 0.1, 0.7])
zSlider = Slider(ax=axZSlider, 
                 label=f"Depth({u_img['z']})", 
                 valmin=z_img.min(), 
                 valmax=z_img.max(), 
                 valinit=zInit, 
                 orientation='vertical', 
                 valstep=z_img)
def updateZslider(val):
    ax.set_ylim(zSlider.val+lenZ, zSlider.val)
    fig.canvas.draw_idle()
zSlider.on_changed(updateZslider)

# Colorbar range slider.
axRSlider = fig.add_axes([0.35, 0.95, 0.4, 0.05])
RSlider = RangeSlider(axRSlider, 'Range', 
                      vmin, 
                      vmax)
def updateRslider(val):
    im.norm.vmin = val[0]
    im.norm.vmax = val[1]
    fig.canvas.draw_idle()
RSlider.on_changed(updateRslider)

# Reset button for depth.
axResetZ = fig.add_axes([0.05, 0.9, 0.17, 0.05])
buttonZ = Button(axResetZ, 'Reset\n Depth', hovercolor='0.975')
def resetZ(event):
    zSlider.reset()
buttonZ.on_clicked(resetZ)
# Reset button for amplitude colorbar.
axResetCM = fig.add_axes([0.05, 0.84, 0.17, 0.05])
buttonCM = Button(axResetCM, 'Reset\n Colormap', hovercolor='0.975')
def resetCM(event):
    RSlider.reset()
buttonCM.on_clicked(resetCM)

plt.show()
