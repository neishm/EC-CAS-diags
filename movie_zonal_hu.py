# Movie of zonal mean humidity

from model import hu_zonal
from movie_zonal import create_images
from matplotlib import colors
import numpy as np

#print hu_zonal.min(), hu_zonal.max()
#print hu_zonal.mean(), hu_zonal.stdev()

#contours = [1e-7, 3.16e-6, 1e-6, 3.16e-5, 1e-5, 3.16e-4, 1e-4, 3.16e-3, 1e-3, 3.16e-2, 1e-2]
#contours = np.logspace(-6, -5, 20)
contours = np.linspace(1e-6,5e-6,20)

#create_images(hu_zonal, None, title1='HU', contours=contours, norm=colors.LogNorm())
create_images(hu_zonal, None, title1='HU', contours=contours)
