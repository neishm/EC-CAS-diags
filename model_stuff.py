
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

def rpnopen_eta932 (filename):
  f = rpnopen(filename)
  f = f(eta=0.932)
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


# Save intermediate netcdf files (for faster access)
def nc_cache (dirname, data):

  from os.path import exists
  from os import mkdir
  from pygeode.formats import netcdf as nc
  from pygeode.formats.multifile import openall
  from common import fix_timeaxis

  if not exists(dirname): mkdir(dirname)

  taxis = data.values()[0].time

  # Save the data in netcdf files, 1 file per month
  for year in sorted(set(taxis.year)):
    for month in sorted(set(taxis(year=year).month)):
      if len(taxis(year=year,month=month)) == 1:
        print "skipping year %d month %d - only one timestep available"%(year,month)
        continue
      for datatype in sorted(data.keys()):
        filename = dirname+"/%04d%02d_%s.nc"%(year,month,datatype)
        if exists(filename):
          print "skipping '%s' - already exists"%filename
          continue
        nc.save (filename, data[datatype](year=year,month=month))#, version=4)

  # Reload the data from these files
  data = dict(data)
  for datatype in sorted(data.keys()):
    data[datatype] = openall(files=dirname+"/*_%s.nc"%datatype, format=nc)
    data[datatype] = fix_timeaxis(data[datatype])

  return data


def open (indir, tmpdir=None):
  from pygeode.formats.multifile import open_multi
  from glob import glob

  data = dict()

  data['dm'] = dm = open_multi (indir+"/dm*", opener=rpnopen, file2date=file2date)
  data['dm_zonalmean_eta'] = dm.mean('lon')
  data['km_sfc'] = open_multi (indir+"/km*", opener=rpnopen_sfconly, file2date=file2date)
#  data['km_eta932'] = open_multi (indir+"/km*", opener=rpnopen_eta932, file2date=file2date)
  km_daily = open_multi (indir+"/km*_1440m", opener=rpnopen, file2date=file2date)
  data['km_zonalmean_eta'] = km_daily.mean('lon')

  # Optionally, add physics fields
  if len(glob(indir+"/pm*")) > 0:
    data['pm'] = pm = open_multi (indir+"/pm*", opener=rpnopen, file2date=file2date)
    data['pm_zonalmean_eta'] = pm.mean('lon')

  # Convert zonal mean data (on height)
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  from pygeode.dataset import Dataset
  height = Height(range(68), name='height')
  varlist = [var for var in km_daily if var.hasaxis('eta')]
  varlist = [interpolate(var, inaxis='eta', outaxis=height, inx=dm.GZ*10/1000) for var in varlist]
  varlist = [var.mean('lon') for var in varlist]
  varlist = [var.transpose(0,2,1) for var in varlist]
  data['km_zonalmean_gph'] = Dataset(varlist)

  # Cache the data in netcdf files?
  if tmpdir is not None: data = nc_cache(tmpdir, data)

  return data

# Shortcut for opening data in my directory
def my_data (name):
  return open (indir="/wrk1/neish/"+name, tmpdir="/wrk1/neish/nc_cache/"+name)
