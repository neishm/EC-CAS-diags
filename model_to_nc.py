from pygeode.formats.multifile import open_multi
from pygeode.formats import netcdf as nc

def rpnopen (filename):
  from pygeode.formats import rpn
  f = rpn.open(filename)
#  f = f.squeeze(rpn.F)
  f = f.squeeze()
  return f

def rpnopen_sfconly (filename):
  f = rpnopen(filename)
  f = f(eta=1).squeeze()
  return f

def rpnopen_eta995 (filename):
  f = rpnopen(filename)
  f = f(eta=0.995)
  return f

# Extract a date from a GEM model filename
def file2date (filename):
  from re import search
  from datetime import datetime, timedelta
  out = search('[dkp][m](?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})_(?P<offset>\d+)(?P<units>[m])$', filename).groupdict()
  units = out.pop('units')
  out = dict([k,int(v)] for k,v in out.items())
  offset = out.pop('offset')

  # Convert to datetime object for manipulating the forecast time
  out = datetime(**out)
  if units == 'm':
    out += timedelta (minutes=offset)
  elif units == 'h':
    out += timedelta (hours=offset)
  else: raise Exception

  # Convert back to dictionary
  out = dict(year=out.year, month=out.month, day=out.day, hour=out.hour, minute=out.minute)
  return out


# Extract a date from an analysis file
def file2date_anlm (filename):
  from re import search
  from datetime import datetime, timedelta
  out = search('anlm(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})_000$', filename).groupdict()
  out = dict([k,int(v)] for k,v in out.items())
  return out


# Shortcut for saving - skip if it already exists
def save (filename, data):
  from os.path import exists
  from pygeode.formats import netcdf as nc
  if exists(filename):
    print "skipping '%s' - already exists"%filename
    return
  nc.save (filename, data)

year = 2009
month = 12

# Convert dynamics fields
#dm = open_multi ("model_data/dm%04d%02d*_1440m"%(year,month), opener=rpnopen, file2date=file2date)
#save("%04d%02d_dynamics.nc"%(year,month), dm)

# Convert the surface data
sfc = open_multi ("model_data/km%04d%02d*"%(year,month), opener=rpnopen_sfconly, file2date=file2date)
save("%04d%02d_co2_sfc.nc"%(year,month), sfc)

# Convert the 2nd lowest level
data = open_multi ("model_data/km%04d%02d*"%(year,month), opener=rpnopen_eta995, file2date=file2date)
save("%04d%02d_co2_eta995.nc"%(year,month), data)


# Convert 3D data
#atm = open_multi ("model_data/km%04d%02d*_1440m"%(year,month), opener=rpnopen, file2date=file2date)
## Only 1 level
#atm = atm(eta=0.5)
#print atm
#nc.save("%04d%02d_co2_500mb.nc"%(year,month), atm)

# Convert zonal mean data (over eta levels)
km = open_multi ("model_data/km%04d%02d*_1440m"%(year,month), opener=rpnopen, file2date=file2date)
zonal = km.mean('lon')
save("%04d%02d_co2_zonalmean_eta.nc"%(year,month), zonal)

# Convert zonal mean data (pressure levels)
quit()
km = open_multi ("model_data/km%04d%02d*_1440m"%(year,month), opener=rpnopen, file2date=file2date)
anlm = open_multi ("wind_data/anlm%04d%02d*"%(year,month), opener=rpnopen, file2date=file2date_anlm)

p0 = anlm.P0 * 100  # Pa
p0 = p0.load()
co2 = km.CO2

eta = co2.eta
A = eta.auxasvar('A')
B = eta.auxasvar('B')

pres = A + B*p0
pres = pres / 100 # hPa

from pygeode.axis import Pres, Hybrid
plevs = Pres(eta.values*1000)

# Interpolate!
from pygeode.interp import interpolate
from common import overlapping

# Remove timesteps where we have no corresponding pressure
co2, pres = overlapping(co2, pres)

co2 = interpolate (co2, inaxis=Hybrid, outaxis=plevs, inx=pres.log(), outx = plevs.log())

#nc.save("%04d%02d_co2_zonalmean.nc"%(year,month), zonal)

