# Interface for CarbonTracker data

def ct_file2date(filename):
  from re import search
  date = search("(?P<year>\d{4})-?(?P<month>\d{2})-?(?P<day>\d{2})\.nc$", filename).groupdict()
  date['year']  = int(date['year'])
  date['month'] = int(date['month'])
  date['day']   = int(date['day'])
  return date

def ct_open (files):
  from pygeode.formats.multifile import open_multi
  from pygeode.formats import netcdf as nc
  from common import fix_timeaxis
  data = open_multi(files=files, format=nc, file2date=ct_file2date)
  data = data.rename_axes(date='time')
  data = fix_timeaxis(data)
  return data

molefractions = ct_open("/wrk1/EC-CAS/CarbonTracker/molefractions/CT2010.molefrac_glb3x2_????-??-??.nc")

molefractions_interface = ct_open("/wrk1/EC-CAS/CarbonTracker/molefractions_interface/molefrac_glb3x2_????-??-??.nc")

fluxes = ct_open("/wrk1/EC-CAS/CarbonTracker/fluxes/CT2010.flux1x1.????????.nc")

# Find the total CO2 (sum of components)
co2 = molefractions.bg + molefractions.ff + molefractions.bio + molefractions.ocean + molefractions.fires


