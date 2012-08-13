# Compare GEM area emissions to original CarbonTracker fluxes.

from pygeode.formats import netcdf
import gemflux
from math import pi
import pygeode as pyg

ct = netcdf.open("/wrk1/EC-CAS/CarbonTracker/fluxes/CT2010.flux1x1.20090720.nc")
gem = gemflux.open("/wrk1/EC-CAS/GEM/inputs/emissions_v2/area_2009072000")

ct_co2 = (ct.fire_flux_imp + ct.bio_flux_opt + ct.fossil_imp + ct.ocn_flux_opt)(i_date=0).squeeze()
ct_co2.name = "CT_CO2_flux"

gem_co2 = gem.ECO2.squeeze()

r = 6370000
gem_area = 2 * pi * r**2 * (pyg.sind(gem.lat+0.45)-pyg.sind(gem.lat-0.45)) / (len(gem.lon)-1)
gem_area.name = "dxdy_GEM"

ct_area = 2 * pi * r**2 * (pyg.sind(ct.lat+0.5)-pyg.sind(ct.lat-0.5)) / len(ct.lon)
ct_area.name = "dxdy_CarbonTracker"

#print ct_area.get()
#quit()

## Convert CarbonTracker from (moles m-2 s-1) to (g/s)
#ct_co2 *= ct_area   # Integrate over each grid cell
#ct_co2 *= 12.01     # moles to g
#ct_co2.name = "CT_CO2_flux_converted"

# Convert GEM from g/s to moles m-2 s-1
gem_co2 /= gem_area  # Convert from total to mean value per grid cell
gem_co2 /= 12.01     # g to moles
gem_co2.name = "GEM_CO2_flux_converted"

#print gem_co2.max(), gem_co2.min()
#print ct_co2.max(), ct_co2.min()
#quit()

from pygeode.plot import plotvar
#import numpy as np
#dc = 0.2E6
#clevs = np.arange(-3E6, 3E6+dc, dc)
from movie_zonal import get_range, get_contours
clevs = get_contours(*get_range(gem_co2))
plotvar (gem_co2, clevs=clevs)
plotvar (ct_co2, clevs=clevs)

from matplotlib.pyplot import show
show()
#print ct_co2.min(), ct_co2.max(), ct_co2.mean()
#print gem_co2.min(), gem_co2.max(), gem_co2.mean()
