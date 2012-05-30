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
  ct_co2 = ct_co2.mean('lon')
  ct_co2 = ct_co2.transpose(0,2,1)
  ct_co2 = dailymean(ct_co2)

  return ct_co2
