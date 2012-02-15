
#from model import co2_zonal as co2#, co2b_zonal as co2_ref
from carbontracker import molefractions

from pygeode.climat import dailymean

import numpy as np

# Interpolate to geopotential height
from pygeode.interp import interpolate
from model import dynamics
from pygeode.axis import Height
height = Height(range(68))
field = 'ff'
ct_co2 = interpolate(molefractions[field], inaxis='level', outaxis=height, inx = molefractions.gph/1000)
ct_co2 = ct_co2.mean('lon')
ct_co2 = ct_co2.transpose(0,2,1)
ct_co2 = dailymean(ct_co2)

from model import cff_zonal as gem_co2
#gem_co2 = gem_co2 - 100  # Biogenic offset
#gem_co2 = gem_co2 - 100  # Ocean offset

from movie_zonal import create_images
#contours = range(376,402+1,1) # total CO2 range
#contours = range(-30,4) # biogenic range
#contours = np.arange(-12,-2+0.2,0.5) # ocean range
#contours = np.arange(4,12+0.2,0.2) # fires range
contours = np.arange(10,50) # fossil fuels range
create_images (gem_co2, ct_co2, contours = contours, refname='CarbonTracker')

