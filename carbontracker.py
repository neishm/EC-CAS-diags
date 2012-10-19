# Interface for CarbonTracker data

def ct_file2date(filename):
  from re import search
  date = search("(?P<year>\d{4})-?(?P<month>\d{2})-?(?P<day>\d{2})\.nc$", filename).groupdict()
  date['year']  = int(date['year'])
  date['month'] = int(date['month'])
  date['day']   = int(date['day'])
  return date

def ct_opener (filename):
  from pygeode.formats import netcdf
  data = netcdf.open(filename)
  # kludge for PyGeode 0.6
  from pygeode.formats import cfmeta
  data = data.rename_axes(date='time')
  data = cfmeta.decode_cf(data)
  return data

def ct_open (files):
  from pygeode.formats.multifile import open_multi
  from pygeode.formats import netcdf as nc
  from common import fix_timeaxis
  data = open_multi(files=files, opener=ct_opener, file2date=ct_file2date)
  data = data.rename_axes(date='time')
  data = fix_timeaxis(data)
  return data

molefractions = ct_open("/wrk1/EC-CAS/CarbonTracker/molefractions/CT2010.molefrac_glb3x2_????-??-??.nc")
molefractions = molefractions - 'date_components' - 'decimal_date'

molefractions_interface = ct_open("/wrk1/EC-CAS/CarbonTracker/molefractions_interface/molefrac_glb3x2_????-??-??.nc")

fluxes = ct_open("/wrk1/EC-CAS/CarbonTracker/fluxes/CT2010.flux1x1.????????.nc")

# Find the total CO2 (sum of components)
co2 = molefractions.bg + molefractions.ff + molefractions.bio + molefractions.ocean + molefractions.fires
co2 = co2.rename('co2')

# Method for calculating zonal mean on-the-fly
def ct_zonal (field):
  from pygeode.climat import dailymean
  import numpy as np

  # Interpolate to geopotential height
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  height = Height(range(68))
  ct_co2 = interpolate(field, inaxis='level', outaxis=height, inx = molefractions.gph/1000)
  ct_co2 = ct_co2.nanmean('lon')
  ct_co2 = ct_co2.transpose(0,2,1)
  ct_co2 = dailymean(ct_co2)

  return ct_co2

# Similar to above, but use an average of the 22:30 and 1:30 to get
# a 00:00 field
def ct_zonal_24h (field):
  import numpy as np

  # Interpolate to geopotential height
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  height = Height(range(68))
  ct_co2 = interpolate(field, inaxis='level', outaxis=height, inx = molefractions.gph/1000)
  ct_co2 = ct_co2.nanmean('lon')
  ct_co2 = ct_co2.transpose(0,2,1)

  co2_2230 = ct_co2(hour=22,minute=30)(i_time = (0,364))

  co2_0130 = ct_co2(hour=1, minute=30)(i_time = (1,365))

  # New time axis
  from pygeode.timeaxis import StandardTime
  taxis = ct_co2.time
  taxis = StandardTime((co2_2230.time.values+co2_0130.time.values)/2, startdate=taxis.startdate, units=taxis.units)
  co2_2230 = co2_2230.replace_axes(time=taxis)
  co2_0130 = co2_0130.replace_axes(time=taxis)

  ct_co2 = ((co2_2230 + co2_0130)/2).rename(ct_co2.name)

  return ct_co2

data = {}
from pygeode.dataset import Dataset

# Zonal mean data
zonalmean = molefractions + co2
zonalmean = [ct_zonal_24h(v) for v in zonalmean]
zonalmean = Dataset(zonalmean)
data['zonalmean_gph_24h'] = zonalmean
del zonalmean 

# Surface data
surface = molefractions + co2
surface = surface(i_level=0)  # lowest level
surface = Dataset(surface)
data['sfc'] = surface
del surface

# Column averages
import numpy as np
from pygeode.var import Var
A_interface = [0., 6.575628, 336.772369, 1297.656128, 3010.146973, 5422.802734, 8356.252930000001, 11543.166992, 14665.645508, 17385.595703, 19348.775391, 20319.011719, 20348.916016, 19919.796875, 19184.544922, 18191.029297, 16990.623047, 15638.053711, 14192.009766, 12713.897461, 11262.484375, 9873.560546999999, 8564.624023, 7341.469727, 6199.839355, 4663.776367, 3358.425781, 2292.155518, 1463.16394, 857.945801, 450.685791, 204.637451, 76.16765599999999, 21.413612, 0.]
A_interface = np.array(A_interface)

B_interface = [1., 0.994204, 0.9734660000000001, 0.935157, 0.875518, 0.795385, 0.698224, 0.589317, 0.475016, 0.362203, 0.259554, 0.176091, 0.112979, 0.080777, 0.055474, 0.036227, 0.022189, 0.012508, 0.006322, 0.002765, 0.001, 0.000279, 5.5e-05, 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
B_interface = np.array(B_interface)

# Get pressure at the bottom mid-level
pmid = molefractions['press'].slice[:,0,:,:].squeeze()

# Compute surface pressure from this
# p1 = A1 + B1*Ps
# pmid = (ps + A1 + B1*Ps) / 2 = Ps(1+B1)/2 + (0+A1)/2
# Ps = (2*pmid - A1)/(1+B1)
Ps = (2*pmid - A_interface[1])/(B_interface[1]+1)
#Ps.name = 'P0'
#from pygeode.formats import netcdf
#netcdf.save("ct_p0.nc", Ps)

# Compute sigma at interfaces
dA = -np.diff(A_interface)
dA = Var([molefractions.level], values=dA)
dB = -np.diff(B_interface)
dB = Var([molefractions.level], values=dB)
dsigma = dA / Ps + dB
dsigma = dsigma.transpose('time', 'level', 'lat', 'lon').rename('dsigma')

sigma_top = A_interface[-1]/Ps + B_interface[-1]
sigma_bottom = 1
#from pygeode.formats import netcdf
#netcdf.save("ct_dsigma.nc", dsigma(i_time=0))
#raise Exception

cols = [(c*dsigma/(sigma_bottom-sigma_top)).sum('level').as_type('float32').rename(c.name) for c in molefractions+co2]
data['colavg'] = Dataset(cols)

from model_stuff import nc_cache
data = nc_cache ("/wrk1/EC-CAS/CarbonTracker/nc_cache", data)


# More heavily derived diagnostics

# Total mass
from math import pi
import numpy as np
from pygeode.var import Var
r = .637122e7  # Taken from consphy.cdk
g = .980616e1  # Taken from GEM-MACH file chm_consphychm_mod.ftn90
# Get latitudes
lats = molefractions.lat.values * (pi/180)
# Get lat boundaries
lat_bounds = (lats[:-1] + lats[1:]) * 0.5
# Including the poles
lat_bounds = np.concatenate([[-pi/2], lat_bounds, [pi/2]])
# Get the cell length
dlat = np.diff(lat_bounds)
# Get longitudes
lons = molefractions.lon.values * (pi/180)
# Assume global & equidistant longitudes
dlon = lons[1] - lons[0]
dlon = np.repeat(dlon, len(lons))

dlat = dlat.reshape(-1,1)
dlon = dlon.reshape(1,-1)
clat = np.cos(lats).reshape(-1,1)
dxdy = r * r * clat * dlat * dlon
dxdy = Var([molefractions.lat, molefractions.lon], values=dxdy, name='dxdy')

varlist = []
from common import convert_CO2
for colavg in data['colavg']:
  name = colavg.name
  # Convert column average from ppmV to ug C / kg air
  colavg /= convert_CO2
  # Calculate total column from average column
  totalcol = colavg * Ps / g * (sigma_bottom - sigma_top)
  # Sum over all grid cells to get total mass (in ug C)
  totalmass = (totalcol*dxdy).sum('lat','lon')
  # Convert from ug to Pg
  totalmass *= 1E-21
  totalmass.name = name
  totalmass = totalmass.as_type('float32')
  varlist.append(totalmass)
data['totalmass'] = Dataset(varlist)


# Cache these extra diagnostics
data = nc_cache ("/wrk1/EC-CAS/CarbonTracker/nc_cache", data)
