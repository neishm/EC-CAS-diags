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

molefractions_interface = ct_open("/wrk1/EC-CAS/CarbonTracker/molefractions_interface/molefrac_glb3x2_????-??-??.nc")

fluxes = ct_open("/wrk1/EC-CAS/CarbonTracker/fluxes/CT2010.flux1x1.????????.nc")

# Find the total CO2 (sum of components)
co2 = molefractions.bg + molefractions.ff + molefractions.bio + molefractions.ocean + molefractions.fires


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
zonalmean = molefractions + co2.rename('co2') - 'date_components' - 'decimal_date'
zonalmean = [ct_zonal_24h(v) for v in zonalmean]
zonalmean = Dataset(zonalmean)
data['zonalmean_gph_24h'] = zonalmean
del zonalmean 

# Surface data
surface = molefractions + co2.rename('co2') - 'date_components' - 'decimal_date'
surface = surface(i_level=0)  # lowest level
surface = Dataset(surface)
data['sfc'] = surface
del surface

from model_stuff import nc_cache
data = nc_cache ("/wrk1/neish/nc_cache/carbontracker", data)
