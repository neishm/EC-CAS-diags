
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
  out = search('[dkp][m](?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})_(?P<offset>\d+)(?P<units>[mh])$', filename).groupdict()
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

  for datatype in sorted(data.keys()):
   taxis = data[datatype].time

   # Save the data in netcdf files, 1 file per month
   for year in sorted(set(taxis.year)):
    for month in sorted(set(taxis(year=year).month)):
      if len(taxis(year=year,month=month)) == 1:
        print "skipping year %d month %d - only one timestep available"%(year,month)
        continue
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


# Convert zonal mean data (on height)
def to_gph (dataset, dm):
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  from pygeode.dataset import Dataset
  height = Height(range(68), name='height')
  varlist = [var for var in dataset if var.hasaxis('eta')]
  varlist = [interpolate(var, inaxis='eta', outaxis=height, inx=dm.GZ*10/1000) for var in varlist]
  varlist = [var.transpose(0,3,1,2) for var in varlist]
  return Dataset(varlist)


# Given a model data directory, get the useful data out of it.
# Cache the data in netcdf format, for faster subsequent access.
def get_data (indir):
  from model_stuff import rpnopen, rpnopen_sfconly, file2date, to_gph, nc_cache
  from pygeode.formats.multifile import open_multi

  data = dict()
  tmpdir = indir + "/nc_cache"

  dm_24h = open_multi(indir+"/dm*_024h", opener=rpnopen, file2date=file2date)
#  km_24h = open_multi(indir+"/km*_024h", opener=rpnopen, file2date=file2date)
#  pm_24h = open_multi(indir+"/pm*_024h", opener=rpnopen, file2date=file2date)
#  stuff_24h = dm_24h + km_24h + pm_24h
  stuff_24h = dm_24h
  dm = open_multi([indir+"/dm*%03dh"%i for i in range(0,24,2)], opener=rpnopen, file2date=file2date)
  km = open_multi([indir+"/km*%03dh"%i for i in range(0,24,2)], opener=rpnopen, file2date=file2date)
  pm = open_multi([indir+"/pm*%03dh"%i for i in range(0,24,2)], opener=rpnopen, file2date=file2date)
  stuff = dm + km + pm

  data['sfc'] = dm(eta=1)
  data['pm_sfc'] = pm(eta=1)
  data['km_sfc'] = km(eta=1)
#  data['toronto'] = stuff.squeeze(lat=43.7833,lon=280.5333)
#  data['zonalmean_eta'] = stuff_24h.mean('lon')
  data['zonalmean_gph'] = to_gph(stuff_24h,stuff_24h).nanmean('lon')
  data = nc_cache(tmpdir, data)

  return data

