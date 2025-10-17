"""
The function library.
"""

# Import packages.
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math, sys 
from typing import Union
from ellipse import LsqEllipse
from matplotlib import colors
from skimage import exposure
from scipy.stats import circmean


def summary_dataframe(object, **kwargs):
    """
    From https://towardsdatascience.com/loading-well-log-data-from-dlis-using-python-9d48df9a23e2 by Andy McDonald.
    Summarize DLIS file channel info as a dataframe.
    
    Args:
        object (List of objects): - Channel objects in the DLIS file.
        **kwargs (Keyword arguments): - Attributes of the Channel and their user-defined column names in the dataframe,
                                        in the format of [AttriName='ColName'], such as [units='Units'].
    Returns: 
        df (Pandas.DataFrame): - Dataframe which contains info of all channels.
    """
    # Create an empty dataframe
    df = pd.DataFrame()
    
    # Iterate over each of the keyword arguments
    for _, (key, value) in enumerate(kwargs.items()):
        list_of_values = []
        
        # Iterate over each parameter and get the relevant key
        for item in object:
            # Account for any missing values.
            try:
                x = getattr(item, key)
                list_of_values.append(x)
            except:
                list_of_values.append('')
                continue
        
        # Add a new column to our data frame
        df[value]=list_of_values
    
    # Sort the dataframe by column 1 and return it
    return df.sort_values(df.columns[0])


def getChannel(frame, chName):
    """
    Get a channel of a frame in the DLIS file.

    Args:
        frame (Object): Frame.
        chName (String): Channel name.

    Returns:
        ch (Object): Channel.
    """
    for ch in frame.channels:
        if chName in str(ch):
            break
    return ch


def read_csv(fpath, azimuth_col=True, 
             vlim=(None, None)):
	"""
	Read image log data from a CSV file.

	Args:
		fpath (String): File path.
		azimuth_col (Bool): Whether the column name contains azimuth.
							Defaults to True.
		vlim (tuple): Clip log values, in the format of (min, max).
						Defaults to (None, None), which is not to clip the log values.
		
	Returns:
		value (Numpy.ndarray): Log value.
		z (Numpy.ndarray): Measured depth.
		phi (Numpy.ndarray): Azimuth.
		units (Dictionary): {'z': Measured depth unit, 
							 'value': Logging value unit}.
	"""
	# Load data.
	df = pd.read_csv(fpath, skipinitialspace=True, dtype=object)

	# Get azimuthal angles.
	if azimuth_col:
		phi = df.columns[1:]
		phi = np.array(phi, dtype=np.float64)
	else:
		n_phi = len(df.columns) - 1
		phi = np.linspace(0, 360, n_phi, endpoint=False)

	# Get tool depths.
	z = df.values[1:, 0].astype(np.float64)

	# Get log values.
	value = df.values[1:, 1:].astype(np.float64)

	# Clip log values if needed.
	vmin, vmax = vlim
	if vmin != None or vmax != None:
		value = np.clip(value, a_min=vmin, a_max=vmax)

	# Get units.
	units = {}
	units['z'] = df.values[0, 0]
	units['value'] = df.values[0, 1]

	return value, z, phi, units


def write_csv(fpath, value, z, phi, unitV, unitZ):
    """
    Write image log data to a CSV file.

    Args:
        fpath (String): Output file path.
        value (Numpy.ndarray): Log value.
        z (Numpy.ndarray): Measured depth.
        phi (Numpy.ndarray): Azimuth.
        unitV (String): Unit of log value.
        unitZ (String): Unit of measured depth.
    """
    # Column names.
    colName = ['Depth']
    
    # The first row contains units of measured depth and log value.
    unitRow = [unitZ]
    
    # Add new elements to column names and the unit row.
    for x in phi:
        colName.append(str(x))
        unitRow.append(unitV)
    
    # Create a dataframe of unit row.
    df0 = pd.DataFrame(data=[unitRow], columns=colName)
    
    # Create a dataframe of measured depth and log value.
    df1 = pd.DataFrame(data=np.c_[z, value], columns=colName)
    
    # Concatenate the two dataframes.
    df = pd.concat([df0, df1], ignore_index=True)
    
    # Write dataframe to file path.
    df.to_csv(fpath, index=False)
    

def polar2cart(radius, angle):
	"""
	Convert polar coordinates to Cartesian coordinates.

	Args:
		radius (Numpy.ndarray): Radius
		angle (Numpy.ndarray): Azimuthal angle.

	Returns:
		x (Numpy.ndarray): X-coordinates.
		y (Numpy.ndarray): Y-coordinates.
	"""
	x = np.zeros(radius.shape, dtype=np.float64)
	y = np.zeros(radius.shape, dtype=np.float64)
	if radius.ndim == 2:
		for j in range(radius.shape[-1]):
			x[:, j] = radius[:, j] * math.sin(math.radians(angle[j]))
			y[:, j] = radius[:, j] * math.cos(math.radians(angle[j]))
	elif radius.ndim == 1:
		x = radius * np.sin(np.radians(angle))
		y = radius * np.cos(np.radians(angle))
	else:
		raise ValueError("Dimension of radius can only be 1 or 2, get %d instead" % radius.ndim)
	return x, y


def resample(z, v, dz, method='average'):
    """
    Resample log data.

    Args:
        z (Numpy.ndarray): Measured depth.
        v (Numpy.ndarray): Log value. Must be 2d array.
        dz (Float): Depth spacing after resampling.
        method (String): Resampling method. 
                         Options are:
                         1 - 'nearest': Take the nearest neighbor as the resampled value.
                         2 - 'average': Take the mean value in [z-dz/2, z+dz/2] as the resampled value.
                         3 - 'median': Take the median value in [z-dz/2, z+dz/2] as the resampled value.
                         4 - 'rms': Take the root-mean-squre value in [z-dz/2, z+dz/2] as the resampled value.
                         5 - 'circmean': Take the circular mean value in [z-dz/2, z+dz/2] as the resampled value.
                         Defaults to 'average'.

    Returns:
        znew (Numpy.ndarray): Resampled measured depth.
        vnew (Numpy.ndarray): Resampled log value.
    """
    # New Measured depth after resampling.
    znew = np.arange(start=np.amin(z) // dz * dz, 
                     stop=np.amax(z) // dz * dz + 2 * dz, 
                     step=dz, 
                     dtype=np.float64)
    
    # Initialize a new log value array, filled with NaNs.
    vnew = np.full((len(znew), v.shape[-1]), fill_value=np.nan, dtype=np.float64)
    
    # Resampling.
    for i in range(len(znew)):
        sys.stdout.write('\rResampling: %.2f%%' % ((i+1) / len(znew) * 100))
        condition = (z > znew[i] - dz / 2) & (z <= znew[i] + dz / 2)  # Depth interval.
        index = np.argwhere(condition)  # Array-index in the depth interval.
        v_tmp = v[index]  # Logging value in the depth interval.
        z_tmp = z[index]  # Measured depth value in the depth interval.
        if len(v_tmp):  # If the depth interval contains log values.
            if method == 'nearest':  # Take the nearest neighbor.
                index_nn = np.argmin(np.abs(z_tmp - znew[i]))  # Array index of the nearest neighbor.
                vnew[i, :] = v_tmp[index_nn, :]
            if method == 'average':  # Take the average value.
                vnew[i, :] = np.nanmean(v_tmp, axis=0)
            if method == 'median':  # Take the median value.
                vnew[i, :] = np.nanmedian(v_tmp, axis=0)
            if method == 'rms':  # Take the root-mean-square value.
                vnew[i, :] = np.sqrt(np.nanmean(v_tmp**2, axis=0))
            if method == 'circmean':  # Take the circular mean value.
                v_tmp = np.deg2rad(v_tmp)
                vnew[i, :] = circmean(v_tmp, axis=0, high=math.pi, 
                                      nan_policy='omit')
                vnew[i, :] = np.rad2deg(vnew[i, :])
    sys.stdout.write('\n')
    
    # Remove missing values.
    df = pd.DataFrame(data=np.c_[znew, vnew])
    # df.dropna(axis='index', how='any', inplace=True)
    # df.reset_index(drop=True, inplace=True)
    
    znew, vnew = df.values[:, 0], df.values[:, 1:] 
    
    return znew, vnew


def interp_nn(z, v, zi):
	"""
	Interpolate image log to new measured depths
	using nearest-neighbor interpolation.

	Args:
		z (numpy.ndarray): Original measured depth.
		v (numpy.ndarray): Image log
		zi (numpy.ndarray): New measured depth.
	"""
	# Initialize the interpolated log values.
	vi = np.zeros((len(zi), v.shape[-1]), dtype=v.dtype)

	# Infer sampling spacing from original measured depth.
	dzs = np.diff(z)

	# In case that the sampling spacing is not uniform, 
	# take its maxima.
	dz = np.amax(dzs)

	# Interpolation.
	for i in range(len(zi)):
		sys.stdout.write("\rInterpolating: %.2f%%" % 
						 ((i + 1) / len(zi) * 100))
		# Find the nearest neighbor of new measured depth 
		# in a depth interval equivalent to the sampling
		# spacing of original measured depth.
		
		# Depth interval.
		c = (z > zi[i] - dz / 2) & (z <= zi[i] + dz / 2)
		
		# Original measured depth in the interval.
		zit = z[c]

		# Original log values in the interval. 
		vit = v[c, :]

		# The nearest neighbor to the new measured depth.
		ind = np.argmin(np.abs(zit - zi[i]))

		# Take its log value.
		vi[i, :] = vit[ind, :]

	sys.stdout.write("\n")

	return vi    


def angle360(theta):
    """
    Convert the angle from [-180, 180] degree to [0, 360) degree. The y-axis points north.
    :param theta: (numpy.ndarray, integer or float) - The angle ([-180, 180] degree) with respect to x-axis,
                                                      a.k.a. the four-quadrant angle.
    :return: phi: (numpy.ndarray, integer or float) - The angle ([0, 360) degree) with respect to north,
                                                      rotating clockwise.
    """
    if isinstance(theta, np.ndarray):
        phi = np.zeros(theta.shape, dtype=np.float64)
        if (theta < -180).any() | (theta > 180).any():
            c = (theta < -180) | (theta > 180)
            raise ValueError('The angle (theta) must be -180<=theta<=180. Get these values instead:', theta[c])
        else:
            c1 = (theta >= -180) & (theta <= 90)
            c2 = (theta > 90) & (theta <= 180)
            phi[c1] = 90 - theta[c1]
            phi[c2] = 450 - theta[c2]
    else:
        if -180 <= theta <= 90:
            phi = 90 - theta
        elif 90 < theta <= 180:
            phi = 450 - theta
        else:
            raise ValueError('The angle (theta) must be -180<=theta<=180. Get %.2f instead.' % theta)
    return phi


def loop360(x: Union[float, np.ndarray]):
	"""
	Loop the azimuth angle less than 0 or greater than 360.
	For example, azimuth angle -30 degree will be 330 degree, 
	and azimuth angle 390 degree will be 30 degree.

	Arg:
	x (numpy.ndarray or float): Azimuth angle [degree].

	Return:
	y (numpy.ndarray or float): Azimuth angle in [0, 360) degree. 
	"""
	if isinstance(x, np.ndarray):
		y = x.copy()
		y[y >= 360] = y[y >= 360] % 360
		y[y < 0] = y[y < 0] % 360
	else:
		y = x
		y = y % 360

	return y


def loop180(x: Union[float, np.ndarray]):
	"""
	Loop the azimuth angle less than 0 or greater than 180.
	For example, azimuth angle -30 degree will be 150 degree, 
	and azimuth angle 210 will be 30 degree.

	Arg:
	x (float or np.ndarray): Azimuth angle [degree].

	Return:
	y (float or np.ndarray): Azimuth angle in [0, 180) degree.
	"""
	if isinstance(x, np.ndarray):
		y = x.copy()
		y[y >= 180] = y[y >= 180] % 180
		y[y < 0] = y[y < 0] % 180
	else:
		y = x
		y = y % 180
	
	return y


def ellipse_fitting(x, y, mask=None):
    """
    Least-square ellipse fitting.
    Based on https://github.com/bdhammel/least-squares-ellipse-fitting/tree/master and
    https://math.stackexchange.com/questions/616645/determining-the-major-minor-axes-of-an-ellipse-from-general-form

    Args:
        x (Numpy.ndarray): X-coordinates of the points to fit.
        y (Numpy.ndarray): Y-coordinates of the points to fit.
        mask (Numpy.ndarray): Mask of the points. Only points with mask=0 will be used for fitting.

    Returns:
        ellipse (Dictionary): Parameters of the fitted ellipse.
                              1. 'lmajor' - Semi-major axis length.
                              2. 'lminor' - Semi-minor axis length.
                              3. 'center' - Ellipse center, in the form of (x, y).
                              4. 'angle' - The angle between x-axis and major axis.
    """
    # Initialize output as a dictionary.
    ellipse = {}
    
    # Ellipse fitting.
    if mask is not None:
        x = x[mask == 0]
        y = y[mask == 0]
    reg = LsqEllipse().fit(np.array(list(zip(x, y))))
    
    # Get coefficients of the general ellipse equation:
    # ax^2 + bxy + cy^2 + dx + ey + f = 0.
    coef = np.ravel(reg.coef_)
    a, b, c, d, e, f = tuple(c for c in coef)
    
    # Coefficient normalizing factor.
    q = 64 * ((f*(4*a*c - b**2) - a*e**2 + b*d*e - c*d**2) / (4*a*c - b**2)**2)  
    
    # Distance between center and focal point.
    s = 1/4 * math.sqrt(abs(q) * math.sqrt(b**2 + (a - c)**2))  
    
    # Semi-major axis length.
    lmajor = 1/8 * math.sqrt(2 * abs(q) * math.sqrt(b**2 + (a - c)**2) - 2*q*(a + c))
    ellipse['lmajor'] = lmajor  
    
    # Semi-minor axis length.
    lminor = math.sqrt(lmajor**2 - s**2)
    ellipse['lminor'] = lminor
    
    # Ellipse center coordinate.  
    x_center = (b*e - 2*c*d) / (4*a*c - b**2)  
    y_center = (b*d - 2*a*e) / (4*a*c - b**2)
    ellipse['center'] = (x_center, y_center)  
    
    # The angle between x-axis and major axis.
    if (q*a - q*c) == 0 and q*b == 0:
        angle = 0
    if (q*a - q*c) == 0 and q*b > 0:
        angle = math.degrees(1/4 * math.pi)
    if (q*a - q*c) == 0 and q*b < 0:
        angle = math.degrees(3/4 * math.pi)
    if (q*a - q*c) > 0 and q*b >= 0:
        angle = math.degrees(1/2 * math.atan(b / (a - c)))
    if (q*a - q*c) > 0 and q*b < 0:
        angle = math.degrees(1/2 * math.atan(b / (a - c)) + math.pi)
    if (q*a - q*c) < 0:
        angle = math.degrees(1/2 * math.atan(b / (a - c)) + math.pi/2)
    ellipse['angle'] = angle
    
    # The angle between x-axis and major axis.
    # if (b == 0) and (a < c):
    #     angle = 0
    # if (b == 0) and (a > c):
    #     angle = math.degrees(1/2 * math.pi)
    # if (b != 0) and (a < c):
    #     angle = math.degrees(1/2 * mpmath.acot((a - c) / 2*b))
    # if (b != 0) and (a > c):
    #     angle = math.degrees(1/2 * math.pi + 1/2 * mpmath.acot((a - c) / 2*b))
    # ellipse['angle'] = angle
    
    return ellipse


def histo_cmap(n, patches):
    fracs = n / n.max()
    norm = colors.Normalize(fracs.min(), fracs.max())
    for thisfrac, thispatch in zip(fracs, patches):
        color = plt.cm.rainbow(norm(thisfrac))
        thispatch.set_facecolor(color)
        
        
def crop_img_log(logval, z, h=None):
    """
    Crop image log in measured depth direction.

    Args:
        logval (Numpy.ndarray): Log value.
        z (Numpy.ndarray): Measured depth.  
        h (Int): Desired image log height after cropping.
                 If height is None, then it will be that of the original image log. 
                 Defaults to None.

    Returns:
        output (List of dictionaries): The cropped image log.
                                       {'value': log value, 
                                        'z': measured depth}.
                                        
    """       
    # Initialize output.
    output = []
    
    # Get log length.
    log_h = logval.shape[0]
    
    # Output shape.
    if h is None:
        h = log_h
        
    # Crop image log.
    sys.stdout.write('Cropping image log...')
    i = 0
    stop = 0
    while(stop == 0):
        top = i * h  # Top indice.
        bot = (i + 1) * h  # Bottom indice.
        if bot >= log_h:
            bot = log_h
            stop = 1
        crop_logval = logval[top:bot, :]  # Cropped image log.
        crop_z = z[top:bot]  # Cropped measured depth.
        output.append({'value': crop_logval, 'z': crop_z})
        i += 1
    sys.stdout.write(' Done.\n')

    return output


def minmax_scale(x):
    """
    Scale data range to 0 and 1 by its minimum and maximum values.

    Args:
        x (Numpy.ndarray): Input data.

    Returns:
        y (Numpy.ndarray): Scaled data.
    """
    min = np.nanmin(x)
    max = np.nanmax(x)
    y = (x - min) / (max - min)
    
    return y


def histeq_scale(x: np.ndarray):
    """
    Scale data range to 0 and 1 using histogram equalization.

    Args:
        x (numpy.ndarray): Input data.
    
    Returns:
        y (numpy.ndarray): Scaled data.
    """
    condition = np.invert(np.isnan(x))
    y = np.full(x.shape, fill_value=np.nan)
    y[condition] = exposure.equalize_hist(x[condition])
    
    return y


def angle2azimuth(x):
	"""
	Convert the azimuthal angle clockwise from north direction (y-axis) ([0, 180] degree)
	to the counter-clockwise angle from x-axis ([0, 180] degree).

	Args:
		x (float or numpy.ndarray): Counter-clockwise angle from x-axis [0, 180].
	
	Returns:
		y (float or numpy.ndarray): Azimuthal angle clockwise from north direction [0, 180]. 
	"""
	if isinstance(x, np.ndarray):
		if (x > 180).any() or (x < 0).any():
			n = len(x[(x > 180) | (x < 0)])
			raise ValueError("The input angle array x must satisfy 0<=x<=180, "
							 "got %d elements out of range." % n)
		else:
			y = x.copy()
			y[(y >= 0) & (y <= 90)] = 90 - y[(y >= 0) & (y <= 90)]
			y[(y > 90) & (y <= 180)] = 270 - y[(y > 90) & (y <= 180)]
	
	else:
		if 0 <= x <= 90:
			y = 90 - x
		elif 90 < x <= 180:
			y = 270 - x
		else:
			raise ValueError("The input angle x must satisfy 0<=x<=180, got %.2f instead." % x)

	return y


def azimuth2angle(x):
	"""
	Convert the azimuthal angle clockwise from north direction (y-axis) ([0, 180] degree)
	to the counter-clockwise angle from x-axis ([0, 180] degree).

	Args:
		x (float or numpy.ndarray): Azimuthal angle clockwise from north direction [0, 180]. 

	Returns:
		y (float or numpy.ndarray): Counter-clockwise angle from x-axis [0, 180]. 
	"""
	if isinstance(x, np.ndarray):
		if (x > 180).any() or (x < 0).any():
			n = len(x[(x > 180) | (x < 0)])
			raise ValueError("The input angle array x must satisfy 0<=x<=180, "
							 "got %d elements out of range." % n)
		else:
			y = x.copy()
			y[(y >= 0) & (y <= 90)] = 90 - y[(y >= 0) & (y <= 90)]
			y[(y > 90) & (y <= 180)] = 270 - y[(y > 90) & (y <= 180)]
	
	else:
		if 0 <= x <= 90:
			y = 90 - x
		elif 90 < x <= 180:
			y = 270 - x
		else:
			raise ValueError("The input angle x must satisfy 0<=x<=180, got %.2f instead." % x)

	return y


def mse(x0, x1):
    """
    Compute mean squared error between x0 and x1.

    Args:
        x0 (Numpy.ndarray): Data array 0.
        x1 (Numpy.ndarray): Data array 1.

    Returns:
        y (Numpy.ndarray): Mean squared error between x0 and x1.
    """
    if x0.ndim > 1 or x1.ndim > 1:
        raise ValueError('The inputs must be 1d arrays.')
    y = (x0 - x1) ** 2
    
    return y


def rm_neg_img(img, z):
    """
	Remove rows with negative values in the image log.

	Args:
		img (numpy.ndarray): The image log values.
		z (numpy.ndarray): Measured depth of the image log.

	Return:
		img_new (numpy.ndarray): Non-negative image log.
		z_new (numpy.ndarray): The corresponding measured depth.
		idx (int): Indexes of the preserved rows.
	"""
    idx = np.argwhere((img >= 0).all(axis=1))
    idx = np.squeeze(idx)
    img_new = img[idx, :]
    z_new = z[idx]

    return img_new, z_new, idx


def rm_neg_log(log, z):
    """
	Remove rows with negative values in 1d log.

	Args:
		log (numpy.ndarray): The log values.
		z (numpy.ndarray): Measured depth.

	Return:
		log_new (numpy.ndarray): Non-negative log.
		z_new (numpy.ndarray): The corresponding measured depth.
		idx (int): Indexes of the preserved rows.
	"""
    idx = np.argwhere(log >= 0)
    idx = np.squeeze(idx)
    log_new = log[idx]
    z_new = z[idx]

    return log_new, z_new, idx


def ellipse_axis_endpoints(xc, yc, d_major, d_minor, angle):
	"""
	Get ellipse axis endpoints coordinates.

	Args:
		xc (float): x-coordinate of the ellipse center.
		yc (float): y-coordinate of the ellipse center.
		d_major (float): major diameter.
		d_minor (float): minor diameter.
		angle (float): Counter-clockwise angle from x-axis to major axis [0, 180].

	Return:
		pts: (dictionary): Endpoint coordinates.
						   pts['major'] = [(x1_major, y1_major), 
						   				   (x2_major, y2_major)]
						   pts['minor'] = [(x1_minor, y1_minor), 
						   				   (x2_minor, y2_minor)]
	"""
	x1_major = xc + d_major/2 * math.cos(math.radians(angle))
	y1_major = yc + d_major/2 * math.sin(math.radians(angle))
	x2_major = xc - d_major/2 * math.cos(math.radians(angle))
	y2_major = yc - d_major/2 * math.sin(math.radians(angle))

	x1_minor = xc - d_minor/2 * math.sin(math.radians(angle))
	y1_minor = yc + d_minor/2 * math.cos(math.radians(angle))
	x2_minor = xc + d_minor/2 * math.sin(math.radians(angle))
	y2_minor = yc - d_minor/2 * math.cos(math.radians(angle))
	
	pts = {'major': [(x1_major, y1_major), (x2_major, y2_major)], 
		   'minor': [(x1_minor, y1_minor), (x2_minor, y2_minor)]}
	
	return pts


def borehole_stress(Sv: float, 
					Shmin: float,
					Aphi: float,
					euler_angles: list[float], 
					tilt: float, 
					azimuth: float, 
					PR: float, 
					Pd: float, 
					Pp: float, 
     				SHmax: float = None) -> dict:
	"""
	Compute priciple stress on the borehole cross section.

	Args:
	Sv (float): Far-field vertical stress [Mpa].
	Shmin (float): Far-field minimum horizontal stress [Mpa].
	Aphi (float): Relative stress magnitude.
				  Aphi = (n + 0.5) + (-1)^n * (phi - 0.5)
				  phi = (s2 - s3) / (s1 - s3)
				  n = 0: normal faulting regime (0 <= Aphi < 1).
				  n = 1: strike-slip faulting regime (1 <= Aphi <= 2).
				  n = 2: reverse faulting regime (2 < Aphi <= 3).
	euler_angles (list of float): Euler angles [deg] that define the 
								  far-field stress coordinate system
								  in terms of geographic coordinates.
								  In the format of [a, b, c].
								  a: Strike of Xs-Ys plane [deg]. 
          							 Measured clockwise from Xg to Xs.
								  b: Rake of Xs-Ys plane [deg].
									 Measured from strike line to Xs.
								  c: Dip of Xs-Ys plane [deg].
									 Measured from Xg-Yg plane to Xs-Ys plane.
	tilt (float): Borehole inclination angle [deg], 
 				  measured from Zg to Zb.
				  Range: [0, 90], with 0 means vertical borehole and 
				  90 means horizontal borehole.
	azimuth (float): Borehole inclination azimuth [deg], 
 					 measured clockwise from Xg to Xb.
					 Range: [0, 360).

	Returns:
	output (dict): 'sigma_rr': radial stress on borehole wall [MPa].
				   'sigma_theta': circumferential stress on borehole wall [MPa].
				   'sigma_zz': axial stress on borehole wall [MPa].
				   'sigma_thetaZ': tangential stress on borehole wall [MPa].
				   'smin': Minimum principle stress on borehole cross section [Mpa]
				   'smax': Maximum principle stress on borehole cross section [Mpa]
				   'theta_major': Ellipse major axis orientation from north [deg].
				   'theta_minor': Ellipse minor axis orientation from north [deg].
				   'Sb': stress tensor acting on borehole wall [MPa].
    
	- - - - - - - - - -
	Workflow:
	Project far-field stresses to the borehole cross section through 
	coordinate transformation.
	(Stress coordinate system -> Geographic coordinate system -> borehole coordinate system)

	Far-field stress tensor:
	[[s1, 0, 0], 
	 [0, s2, 0], 
	 [0, 0, s3]]
	s1 > s2 > s3

	Normal faulting:
	s1 = sv, s2 = SHmax, s3 = Shmin

	Strike-slip faulting:
	s1 = SHmax, s2 = Sv, s3 = Shmin

	Reverse faulting:
	s1 = SHmax, s2 = Shmin, s3 = Sv

	Stress coordinate system:
	s1 -> Xs
	s2 -> Ys
	s3 -> Zs

	Geographic coordinate system:
	North -> Xg
	East -> Yg
	Downward -> Zg

	Borehole coordinate system:
	High side -> Xb
	High side + 90 clockwise -> Yb
	Borehole axis downward -> Zb
	- - - - - - - - - -

	"""
	
	if Aphi is not None:
		# Calculate SHmax.
		# Normal faulting regime.
		if 0 <= Aphi < 1:
			n = 0
			phi = (Aphi - (n + 0.5)) / (-1)**n + 0.5
			SHmax = phi * (Sv - Shmin) + Shmin
		
		# Strike-slip faulting regime.
		if 1 <= Aphi <= 2:
			n = 1
			phi = (Aphi - (n + 0.5)) / (-1)**n + 0.5
			SHmax = (Sv - Shmin) / phi + Shmin
	
		# Reverse faulting regime.
		if 2 < Aphi <= 3:
			n = 2
			phi = (Aphi - (n + 0.5)) / (-1)**n + 0.5
			SHmax = (Shmin - Sv) / phi + Sv

	# Construct far-field stress tensor.
	s1, s2, s3 = tuple(sorted((Sv, SHmax, Shmin), reverse=True))
	S = np.zeros((3, 3), dtype=np.float64)
	S[0, 0] = s1
	S[1, 1] = s2
	S[2, 2] = s3

	# Transform input angles from degree to radius.
	a = math.radians(euler_angles[0])  # Euler angle a.
	b = math.radians(euler_angles[1])  # Euler angle b.
	c = math.radians(euler_angles[2])  # Euler angle c.
	tl = math.radians(tilt)  # Borehole inclination angle.
	az = math.radians(azimuth)  # Borehole inclination azimuth.

	# Projection (coordinate transformation) matrix of Euler angle.
	rs11 = math.cos(a) * math.cos(b)
	rs12 = math.sin(a) * math.cos(b)
	rs13 = -math.sin(b)
	
	rs21 = math.cos(a) * math.sin(b) * math.sin(c) - math.sin(a) * math.cos(c)
	rs22 = math.sin(a) * math.sin(b) * math.sin(c) + math.cos(a) * math.cos(c)
	rs23 = math.cos(b) * math.sin(c)
	
	rs31 = math.cos(a) * math.sin(b) * math.cos(c) + math.sin(a) * math.sin(c)
	rs32 = math.sin(a) * math.sin(b) * math.cos(c) - math.cos(a) * math.sin(c)
	rs33 = math.cos(b) * math.cos(c)
	
	Rs = [[rs11, rs12, rs13], 
		  [rs21, rs22, rs23], 
		  [rs31, rs32, rs33]]
	
	Rs = np.array(Rs, dtype=np.float64)

	# Projection (coordinate transformation) matrix of borehole inclination.
	rb11 = math.cos(tl) * math.cos(az)
	rb12 = math.cos(tl) * math.sin(az)
	rb13 = -math.sin(tl)

	rb21 = -math.sin(az)
	rb22 = math.cos(az)
	rb23 = 0

	rb31 = math.sin(tl) * math.cos(az)
	rb32 = math.sin(tl) * math.sin(az)
	rb33 = math.cos(tl)

	Rb = [[rb11, rb12, rb13], 
		  [rb21, rb22, rb23], 
		  [rb31, rb32, rb33]]

	Rb = np.array(Rb, dtype=np.float64)

	# Stress tensor projection. 
	# Far-field stress coordinates -> Geographic coordinates.
	# Far-field stress coordinates: xs -> S1, ys -> S2, zs -> S3
	# Geographic coordinates: X -> north, Y -> east, Z -> vertical (down)
	Sg = Rs.T @ S @ Rs

	# Stress tensor projection.
	# Geographic coordinates -> Borehole coordinates.
	# Borehole coordinates: 
	# xb -> radial, pointing to borehole highside,
	# yb -> orthogonal in a right-hand coordinate system, 
	# zb -> down along the borehole axis.
	Sb = Rb @ Sg @ Rb.T
	Sb[abs(Sb) < 1e-5] = 0

	s11 = Sb[0, 0]
	s12 = Sb[0, 1]
	s13 = Sb[0, 2]
	s22 = Sb[1, 1]
	s23 = Sb[1, 2]
	s33 = Sb[2, 2]

	# Net pressure.
	Pnet = Pd - Pp

	# Azimuth from borehole high side.
	theta = np.arange(0, 2*math.pi, 0.01, dtype=np.float64)

	# Radial stress acting on borehole wall.
	sigma_rr = Pnet * np.ones(len(theta), dtype=np.float64)

	# Circumferential stress acting on borehole wall.
	sigma_theta = s11 + s22 - 2 * (s11 - s22) * np.cos(2 * theta) \
				  - 4 * s12 * np.sin(2 * theta) - Pnet

	# Axial stress acting on borehole wall.
	sigma_zz = s33 - 2 * PR * (s11 - s22) * np.cos(2 * theta) \
			   - 4 * PR * s12 * np.sin(2 * theta)

	# Tangential stress acting on borehole wall.
	sigma_thetaZ = 2 * (s23 * np.cos(theta) - s13 * np.sin(theta))
	
	# Maximum effective principle stress on borehole cross section.
	smax = 0.5 * (s11 + s22) \
		   + 0.5 * math.sqrt((s11 - s22)**2 + 4 * s12**2) - Pp
	
	# Minimum effective principle stress.
	smin = 0.5 * (s11 + s22) \
		   - 0.5 * math.sqrt((s11 - s22)**2 + 4 * s12**2) - Pp

	# Ellipse orientation.
	x = abs(s11 - s22)
	y = 2 * s12
	theta_axis = math.atan(y / x) / 2
	theta_axis = math.degrees(theta_axis)
	
	# When s11 < s22,
	# theta_axis denotes the angle from the high-side clockwise
	# to the ellipse major axis.
	if s11 < s22:
		theta_major = azimuth - theta_axis
		theta_major = loop360(theta_major)
		theta_minor = theta_major + 90
		theta_minor = loop360(theta_minor)

	# When s11 > s22, 
	# theta_axis denotes the angle from the high-side counter-clockwise
	# to the minor axis.
	elif s11 > s22:
		theta_minor = azimuth + theta_axis
		theta_minor = loop360(theta_minor)
		theta_major = theta_minor + 90
		theta_major = loop360(theta_major)

	# When s11 = s22. 
	else:
		theta_major = np.nan
		theta_minor = np.nan
	
	output = {'sigma_rr': sigma_rr, 
			  'sigma_theta': sigma_theta, 
			  'sigma_zz': sigma_zz, 
			  'sigma_thetaZ': sigma_thetaZ, 
			  'smin': smin, 
			  'smax': smax, 
			  'theta_major': theta_major, 
			  'theta_minor': theta_minor,
			  'theta': theta, 
			  'Sb': Sb}
	
	return output


def ellip_orien(a: float, 
                b: float, 
                c: float, 
                phi: float, 
                s3: float, 
                tl: float, 
                az: float):
	"""
 	Foward modeling major and minor axis orientation of 
	borehole cross section.
	Use normalized principal stress (0 - 1).
	Set maximum principal stress s1 = 1.

	Args:
		a (float): Euler angle a of principal stress [deg].
		b (float): Euler angle b of principal stress [deg].
		c (float): Euler angle c of principal stress [deg].
		phi (float): Stress ratio ((s2 - s3) / (s1 - s3)).
		s3 (float): Minimum principal stress (normalized, 0 - 1).
		tl (float): Borehole inclination angle [deg].
		az (float): Borehole inclination azimuth [deg].
  
	Return:
		theta_major (float): Major axis azimuth of borehole cross section [deg, from North].
		theta_minor (float): Minor axis azimuth of borehole cross section [deg, from North].
	"""
	
	# Construct principal stress tensor.
	S = np.zeros((3, 3), dtype=np.float64)
	s1 = 1
	s2 = phi * (s1 - s3) + s3
	S[0, 0] = s1
	S[1, 1] = s2
	S[2, 2] = s3

	# Transform input angles from degree to radius.
	a = math.radians(a)  # Euler angle a.
	b = math.radians(b)  # Euler angle b.
	c = math.radians(c)  # Euler angle c.
	tl = math.radians(tl)  # Borehole inclination angle.
	az = math.radians(az)  # Borehole inclination azimuth.

	# Projection (coordinate transformation) matrix of Euler angle.
	rs11 = math.cos(a) * math.cos(b)
	rs12 = math.sin(a) * math.cos(b)
	rs13 = -math.sin(b)
	
	rs21 = math.cos(a) * math.sin(b) * math.sin(c) - math.sin(a) * math.cos(c)
	rs22 = math.sin(a) * math.sin(b) * math.sin(c) + math.cos(a) * math.cos(c)
	rs23 = math.cos(b) * math.sin(c)
	
	rs31 = math.cos(a) * math.sin(b) * math.cos(c) + math.sin(a) * math.sin(c)
	rs32 = math.sin(a) * math.sin(b) * math.cos(c) - math.cos(a) * math.sin(c)
	rs33 = math.cos(b) * math.cos(c)
	
	Rs = [[rs11, rs12, rs13], 
		  [rs21, rs22, rs23], 
		  [rs31, rs32, rs33]]
	
	Rs = np.array(Rs, dtype=np.float64)

	# Projection (coordinate transformation) matrix of borehole inclination.
	rb11 = math.cos(tl) * math.cos(az)
	rb12 = math.cos(tl) * math.sin(az)
	rb13 = -math.sin(tl)

	rb21 = -math.sin(az)
	rb22 = math.cos(az)
	rb23 = 0

	rb31 = math.sin(tl) * math.cos(az)
	rb32 = math.sin(tl) * math.sin(az)
	rb33 = math.cos(tl)

	Rb = [[rb11, rb12, rb13], 
		  [rb21, rb22, rb23], 
		  [rb31, rb32, rb33]]

	Rb = np.array(Rb, dtype=np.float64)

	# Stress tensor projection. 
	# Far-field stress coordinates -> Geographic coordinates.
	# Far-field stress coordinates: xs -> S1, ys -> S2, zs -> S3
	# Geographic coordinates: X -> north, Y -> east, Z -> vertical (down)
	Sg = Rs.T @ S @ Rs

	# Stress tensor projection.
	# Geographic coordinates -> Borehole coordinates.
	# Borehole coordinates: 
	# xb -> radial, pointing to borehole highside,
	# yb -> orthogonal in a right-hand coordinate system, 
	# zb -> down along the borehole axis.
	Sb = Rb @ Sg @ Rb.T
	Sb[Sb < 1e-5] = 0

	s11 = Sb[0, 0]
	s12 = Sb[0, 1]
	s22 = Sb[1, 1]

	# Ellipse orientation.
	x = abs(s11 - s22)
	y = 2 * s12
	theta_axis = math.atan(y / x) / 2
	theta_axis = math.degrees(theta_axis)
	
	# When s11 < s22,
	# theta denotes the angle from the high-side clockwise
	# to the ellipse major axis.
	if s11 < s22:
		theta_major = az - theta_axis
		theta_major = loop360(theta_major)
		theta_minor = theta_major + 90
		theta_minor = loop360(theta_minor)

	# When s11 > s22, 
	# theta denotes the angle from the high-side clockwise
	# to the minor axis.
	elif s11 > s22:
		theta_minor = az + theta_axis
		theta_minor = loop360(theta_minor)
		theta_major = theta_minor + 90
		theta_major = loop360(theta_major)

	# When s11 = s22. 
	else:
		theta_major = np.nan
		theta_minor = np.nan
	
	return theta_major, theta_minor


def azimuth_rmse(x1: Union[np.ndarray, float], 
                                   x2: Union[np.ndarray, float]) -> Union[np.ndarray, float]:
	"""
	Compute root-mean-square error (RMSE) between azimuth x1 and x2.

	Args:
		x1 (np.ndarray | float): Azimuth between 0° and 360°.
		x2 (np.ndarray | float): Azimuth between 0° and 360°.
  
	Returns:
		rmse (np.ndarray | float): RMSE between azimuth x1 and x2.
	"""
	# Inputs are arrays.
	if isinstance(x1, np.ndarray) and isinstance(x2, np.ndarray):
		if (x1 > 360).any() or (x1 < 0).any() or (x2 > 360).any() or (x2 < 0).any():
			raise ValueError("Input values can not be less than 0 or greater than 360")
		if len(x1) != len(x2):
			raise ValueError("Input arrays must have the same length, got %d and %d instead" % 
							(len(x1), len(x2)))
		x1[x1 > 180] -= 180
		x2[x2 > 180] -= 180
		n = len(x1)
	# Inputs are floats.
	else:
		if x1 > 360 or x1 < 0 or x2 > 360 or x2 < 0:
			raise ValueError("Input values can not be less than 0 or greater than 360")
		if x1 > 180:
			x1 -= 180
		if x2 > 180:
			x2 -= 180
		n = 1
	y = np.zeros((n, 3), dtype=np.float32)
	y[:, 0] = np.abs(x1 - x2)
	y[:, 1] = np.abs(x1 + 180 - x2)
	y[:, 2] = np.abs(x2 + 180 - x1)
	ymin = np.min(y, axis=1)
	rmse = np.sqrt(np.nanmean(ymin**2))
 
	return rmse


def split_consecutive(x: np.ndarray):
	"""
 	Split consecutive numbers.

	Args:
		x (np.ndarray): _description_

	Returns:
		_type_: _description_
	"""
	y = np.split(x, np.where(np.diff(x)!=1)[0]+1)

	return y


def euler_angle_to_stress_vector(a: float, 
                                 b: float, 
                                 c: float):
    a = math.radians(a)
    b = math.radians(b)
    c = math.radians(c)
    
    # An arbitrary stress tensor.
    S = [[1, 0, 0], 
         [0, 0, 0], 
         [0, 0, -1]]
    S = np.array(S)
    
    # Transformation matrix.
    R = [[math.cos(a)*math.cos(b), math.sin(a)*math.cos(b), -math.sin(b)], 
    	 [math.cos(a)*math.sin(b)*math.sin(c)-math.sin(a)*math.cos(c), math.sin(a)*math.sin(b)*math.sin(c)+math.cos(a)*math.cos(c), math.cos(b)*math.sin(c)], 
    	 [math.cos(a)*math.sin(b)*math.cos(c)+math.sin(a)*math.sin(c), math.sin(a)*math.sin(b)*math.cos(c)-math.cos(a)*math.sin(c), math.cos(b)*math.cos(c)]]
    R = np.array(R)
    
    # Transform to geographic coordinate system.
    Sg = R.T @ S @ R
    
    # Solve eigenvalues and eigenvectors.
    eigval, eigvec = np.linalg.eig(Sg)
    
    # Sort eigenvalues in descending order.
    ind = np.argsort(eigval)  # Ascending.
    ind = ind[::-1]  # Descending.
    
    # Get stress vectors.
    sv1 = eigvec[:, ind[0]]  # Vector of S1.
    sv2 = eigvec[:, ind[1]]  # Vector of S2.
    sv3 = eigvec[:, ind[2]]  # Vector of S3.
    
    return sv1, sv2, sv3


def stress_vector_to_strike_dip(sv: np.ndarray):
	phi = math.atan(abs(sv[1] / (sv[0] + 1e-6)))
	phi = math.degrees(phi)
	
	# Strike.
	if sv[1] >= 0 and sv[0] >= 0:
		strike = phi
	elif sv[1] >= 0 and sv[0] < 0:
		strike = 180 - phi
	elif sv[1] < 0 and sv[0] < 0:
		strike = 180 + phi
	elif sv[1] < 0 and sv[0] >= 0:
		strike = 360 - phi
	
	# Dip.
	theta = math.acos(abs(sv[2]))
	dip = 90 - math.degrees(theta)
 
	if dip == 90:
		strike = 0
 
	return strike, dip


def stress_on_fractures(strike:float, dip:float, 
                        a: float, b: float, c: float, 
                        S1: float, S2: float, S3: float, 
                        phi: float = None):
	"""
	Calculate normal, shear stress acting on the fracture plane and rake of the fracture.

	Args:
		strike (float): Strike direction of the fracture from Magnetic North, ranging from 0 to 360 [deg].
		dip (float): Dip angle of the fracture from horizon, ranging from 0 to 90 [deg].
		a (float): Euler angle a, i.e., strike/trend of S1, ranging from 0 to 360 [deg].
		b (float): Euler angle b, i.e., -plunge of S1, ranging from -90 to 90 [deg].
		c (float): Euler angle c, i.e., rake of S2, ranging from -90 to 90 [deg].
		S1 (float): Magnitude of the maximum principal stress.
		S2 (float): Magnitude of the intermediate principal stress.
		S3 (float): Magnitude of the minimum principal stress.
		phi (float, optional): Stress ratio. Defaults to None. If not None, S2 will be calculated from S1 and S3.

	Returns:
		Sn (float): Normal stress acting on the fracture plane.
		tau (float): Shear stress acting on the fracture plane.
		rake (float): Rake of the fracture [deg].
	"""
	# Degrees to radians.
	strike = math.radians(strike)
	dip = math.radians(dip)
	a = math.radians(a)
	b = math.radians(b)
	c = math.radians(c)
    
	# Define principal stress tensor.
	if phi is not None:
		S2 = (S1 - S3) * phi + S3
	S = [[S1, 0, 0], 
		 [0, S2, 0], 
		 [0, 0, S3]]
	S = np.array(S)

	# Transformation from principal stress to geographic coordinates system.
	R1 = [[math.cos(a)*math.cos(b), math.sin(a)*math.cos(b), -math.sin(b)], 
		  [math.cos(a)*math.sin(b)*math.sin(c)-math.sin(a)*math.cos(c), math.sin(a)*math.sin(b)*math.sin(c)+math.cos(a)*math.cos(c), math.cos(b)*math.sin(c)], 
		  [math.cos(a)*math.sin(b)*math.cos(c)+math.sin(a)*math.sin(c), math.sin(a)*math.sin(b)*math.cos(c)-math.cos(a)*math.sin(c), math.cos(b)*math.cos(c)]]
	R1 = np.array(R1)
	Sg = R1.T @ S @ R1

	# Transformation from geographic to fracture coordinate system.
	R2 = [[math.cos(strike), math.sin(strike), 0], 
		  [math.sin(strike)*math.cos(dip), -math.cos(strike)*math.cos(dip), -math.sin(dip)], 
		  [-math.sin(strike)*math.sin(dip), math.cos(strike)*math.sin(dip), -math.cos(dip)]]
	R2 = np.array(R2)
	Sf = R2 @ Sg @ R2.T

	# Solve for normal stress resolved on the fracture plane.
	Sn = Sf[2, 2]

	# Solve for rake of the slip vector.
	if Sf[2, 1] > 0:
		rake = math.atan(Sf[2, 1] / Sf[2, 0])
	elif (Sf[2, 1] < 0) & (Sf[2, 0] > 0):
		rake = math.pi - math.atan(Sf[2, 1] / (-Sf[2, 0]))
	else:
		rake = math.atan((-Sf[2, 1]) / (-Sf[2, 0])) - math.pi

	# Solve for shear stress resolved on the fracture plane.
	R3 = [[math.cos(rake), math.sin(rake), 0], 
		  [-math.sin(rake), math.cos(rake), 0], 
		  [0, 0, 1]]
	R3 = np.array(R3)
	Sr = R3 @ Sf @ R3.T
	tau = abs(Sr[2, 0])

	rake = math.degrees(rake)

	return Sn, tau, rake


def md2tvd(md:np.ndarray, alpha:np.ndarray):
	"""
	Convert measured depth to true vertical depth.

	Args:
		md (np.ndarray): Measured depth
		alpha (np.ndarray): Borehole inclination angle, from the vertical [deg].
	"""
	alpha = np.radians(alpha)  # Degrees to radians.
	tvd = np.cumsum(np.diff(md) * np.cos(alpha[1:]))
	tvd = np.hstack(([0], tvd))
 
	return tvd


def compute_aphi(phi: Union[np.ndarray, float], 
                 s1_dip: np.ndarray | float, 
                 s2_dip: np.ndarray | float, 
                 s3_dip: np.ndarray | float):
	if isinstance(phi, float) or isinstance(phi, int):
		phi = np.array([phi])
		s1_dip = np.array([s1_dip])
		s2_dip = np.array([s2_dip])
		s3_dip = np.array([s3_dip])
	elif isinstance(phi, np.ndarray):
		pass
	else:
		raise TypeError("Inputs parameter type must be one of (np.ndarray, float, int), got %s instead" % type(phi))
	
	aphi = np.full(len(phi), fill_value=np.nan)
	stress_regime = []

	for i in range(len(phi)):
		if np.isnan(s1_dip[i]):
			stress_regime.append('NaN')
			continue
		if (s1_dip[i] > s2_dip[i] >= s3_dip[i]) or (s1_dip[i] > s3_dip[i] >= s2_dip[i]):  # Normal faulting stress regime.
			n = 0
			stress_regime.append('Normal')
		if (s2_dip[i] > s1_dip[i] >= s3_dip[i]) or (s2_dip[i] > s3_dip[i] >= s1_dip[i]):  # Strike-slip faulting stress regime.
			n = 1
			stress_regime.append('Strike-slip')
		if (s3_dip[i] > s2_dip[i] >= s1_dip[i]) or (s3_dip[i] > s1_dip[i] >= s2_dip[i]):  # Reverse faulting stress regime.
			n = 2
			stress_regime.append('Reverse')
		aphi[i] = (n + 0.5) + (-1)**n * (phi[i] - 0.5)

	if len(aphi) == 1:
		aphi = aphi[0]
  
	if len(stress_regime) == 1:
		stress_regime = stress_regime[0]
	
	return aphi, stress_regime


def compute_general_stress_orien(s1_dip: np.ndarray | float, s1_azimuth: np.ndarray | float, 
								 s2_dip: np.ndarray | float, s2_azimuth: np.ndarray | float, 
								 s3_dip: np.ndarray | float, s3_azimuth: np.ndarray | float):
    if not isinstance(s1_dip, np.ndarray):
        s1_dip, s1_azimuth = np.array([s1_dip]), np.array([s1_azimuth])
        s2_dip, s2_azimuth = np.array([s2_dip]), np.array([s2_azimuth])
        s3_dip, s3_azimuth = np.array([s3_dip]), np.array([s3_azimuth])
    nsample = len(s1_dip)
    sv_dip = np.zeros(nsample, dtype=s1_dip.dtype)
    sv_azi = np.zeros(nsample, dtype=s1_dip.dtype)
    shmax_dip = np.zeros(nsample, dtype=s1_dip.dtype)
    shmax_azi = np.zeros(nsample, dtype=s1_dip.dtype)
    shmin_dip = np.zeros(nsample, dtype=s1_dip.dtype)
    shmin_azi = np.zeros(nsample, dtype=s1_dip.dtype)

    for i in range(nsample):
        _, stress_regime = compute_aphi(phi=0.5, s1_dip=s1_dip[i], s2_dip=s2_dip[i], s3_dip=s3_dip[i])
        
        if stress_regime == 'Normal':
            sv_dip[i], sv_azi[i] = s1_dip[i], s1_azimuth[i]
            shmax_dip[i], shmax_azi[i] = s2_dip[i], s2_azimuth[i]
            shmin_dip[i], shmin_azi[i] = s3_dip[i], s3_azimuth[i]
        
        elif stress_regime == 'Strike-slip':
            sv_dip[i], sv_azi[i] = s2_dip[i], s2_azimuth[i]
            shmax_dip[i], shmax_azi[i] = s1_dip[i], s1_azimuth[i]
            shmin_dip[i], shmin_azi[i] = s3_dip[i], s3_azimuth[i]
        
        elif stress_regime == 'Reverse':
            sv_dip[i], sv_azi[i] = s3_dip[i], s3_azimuth[i]
            shmax_dip[i], shmax_azi[i] = s1_dip[i], s1_azimuth[i]
            shmin_dip[i], shmin_azi[i] = s2_dip[i], s2_azimuth[i]
            
        elif stress_regime == 'NaN':
            sv_dip[i] = np.nan
            sv_azi[i] = np.nan
            shmax_dip[i] = np.nan
            shmax_azi[i] = np.nan
            shmin_dip[i] = np.nan
            shmin_azi[i] = np.nan
            
        else:
            raise ValueError("No such stress regime as %s" % stress_regime)
    
    if len(sv_dip) == 1:
        sv_dip, sv_azi = sv_dip[0], sv_azi[0]
        shmax_dip, shmax_azi = shmax_dip[0], shmax_azi[0]
        shmin_dip, shmin_azi = shmin_dip[0], shmin_azi[0]
    s = {'Sv dip': sv_dip, 'Sv azimuth': sv_azi, 
         'SHmax dip': shmax_dip, 'SHmax azimuth': shmax_azi, 
         'Shmin dip': shmin_dip, 'Shmin azimuth': shmin_azi}
    
    return s


def mirror_azimuth(azi):
	"""
 	Mirroring the azimuths. 

	Args:
		azi (numpy.ndarray): The input azimuths.
  
	Returns:
		two_halves (numpy.ndarray): The mirrored azimuths.
	"""
	bin_edges = np.arange(-5, 366, 10)
	number_of_strikes, bin_edges = np.histogram(azi, bin_edges)
	# Sum the last value with the first value.
	number_of_strikes[0] += number_of_strikes[-1]
	# Sum the first half 0-180° with the second half 180-360° to achieve the "mirrored behavior" of Rose Diagrams.
	half = np.sum(np.split(number_of_strikes[:-1], 2), 0)
	two_halves = np.concatenate([half, half])

	return two_halves