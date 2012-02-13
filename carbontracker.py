# Interface for CarbonTracker data

from pygeode.formats import netcdf as nc
from pygeode.formats.multifile import openall, open_multi

def ct_file2date(filename):
  from re import search
  date = search("(?P<year>\d{4})-?(?P<month>\d{2})-?(?P<day>\d{2})\.nc$", filename).groupdict()
  date['year']  = int(date['year'])
  date['month'] = int(date['month'])
  date['day']   = int(date['day'])
  return date

molefractions = open_multi(files="/wrk1/EC-CAS/CarbonTracker/molefractions/CT2010.molefrac_glb3x2_????-??-??.nc", format=nc, file2date=ct_file2date)

molefractions_interface = open_multi(files="/wrk1/EC-CAS/CarbonTracker/molefractions_interface/molefrac_glb3x2_????-??-??.nc", format=nc, file2date=ct_file2date)

fluxes = open_multi(files="/wrk1/EC-CAS/CarbonTracker/fluxes/CT2010.flux1x1.????????.nc", format=nc, file2date=ct_file2date)

