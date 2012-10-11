
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
      print "===> %s"%filename
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


# New data interface - get data as needed on-the-fly.
# Replaces pre-computing everything with nc_cache.
# This should be faster, since we only compute what we need.

class Experiment(object):
  def __init__ (self, indir, name, title):
    from pygeode.formats.multifile import open_multi
    from pygeode.formats import rpn
    from glob import glob
    from pygeode.axis import ZAxis
    from common import fix_timeaxis

    self.name = name
    self.title = title
    self._tmpdir = indir + "/nc_cache"

    ##############################
    # Data with vertical extent
    ##############################

    # Open a single day of data, to determine at what times 3D data is saved.
    files_24h = sorted(glob(indir+"/dm*_024h"))
    testfile = files_24h[0]
    del files_24h
    testfile = rpn.open(testfile)
    # Assume we have 3D output for at least the 24h forecasts
    levels = list(testfile['CO2'].getaxis(ZAxis).values)
    # Get the rest of the files for this day, check the levels
    year = int(testfile.time.year[0])
    month = int(testfile.time.month[0])
    day = int(testfile.time.day[0])
    del testfile
    testfiles = sorted(glob(indir+"/dm%04d%02d%02d00_???h"%(year,month,day)))
    testfiles = [rpn.open(f) for f in testfiles]
    times_with_3d = [int(f.forecast.values[0]) for f in testfiles if list(f['CO2'].getaxis(ZAxis).values) == levels]
    # Ignore 0h files, since we're already using the 24h forecasts
    if 0 in times_with_3d:
      times_with_3d.remove(0)

    dm_3d = [indir+"/dm*_%03dh"%h for h in times_with_3d]
    km_3d = [indir+"/km*_%03dh"%h for h in times_with_3d]
    pm_3d = [indir+"/pm*_%03dh"%h for h in times_with_3d]

    # Open the 3D files
    dm_3d = open_multi(dm_3d, opener=rpnopen, file2date=file2date)
    km_3d = open_multi(km_3d, opener=rpnopen, file2date=file2date)
    pm_3d = open_multi(pm_3d, opener=rpnopen, file2date=file2date)

    self.dm_3d = fix_timeaxis(dm_3d)
    self.km_3d = fix_timeaxis(km_3d)
    self.pm_3d = fix_timeaxis(pm_3d)

    ##############################
    # Surface data
    ##############################

    # Assume surface data is available in every output time.
    # Ignore 0h output - use 24h output instead.
    dm = open_multi([indir+"/dm*%03dh"%i for i in range(1,25)], opener=rpnopen_sfconly, file2date=file2date)
    km = open_multi([indir+"/km*%03dh"%i for i in range(1,25)], opener=rpnopen_sfconly, file2date=file2date)
    pm = open_multi([indir+"/pm*%03dh"%i for i in range(1,25)], opener=rpnopen_sfconly, file2date=file2date)
    self.dm = fix_timeaxis(dm)
    self.km = fix_timeaxis(km)
    self.pm = fix_timeaxis(pm)

    ##############################
    # Derived fields
    ##############################

    # (Things that may not have been output from the model, but that we can
    #  compute)

    # Sigma levels
    # Assume this is usually available in the physics bus
    if 'SIGM' not in self.pm_3d:
      Ps = self.dm['P0'] * 100
      A = self.dm_3d.eta.auxasvar('A')
      B = self.dm_3d.eta.auxasvar('B')
      P = A + B * Ps
      P = P.transpose('time','eta','lat','lon')
      sigma = P / Ps
      sigma.name = 'SIGM'
      self.pm_3d += sigma

  # The data interface
  # Handles the computing of general diagnostic domains (zonal means, etc.)
  def get_data (self, filetype, domain, field):
    from os.path import exists
    from os import mkdir
    from pygeode.formats import netcdf

    assert filetype in ('dm', 'km', 'pm')
    assert domain in ('sfc', 'zonalmean_gph', 'Toronto')

    # Determine which data is needed
    if domain == 'sfc':
      data = getattr(self,filetype)[field]
    elif domain == 'zonalmean_gph':
      data = getattr(self,filetype+'_3d')
      data = to_gph(data,self.dm_3d).nanmean('lon')
      data = data[field]
    elif domain == 'Toronto':
      data = getattr(self,filetype+'_3d')[field]
      data = data.squeeze(lat=43.7833,lon=280.5333)
    else: raise Exception

    if not exists(self._tmpdir): mkdir(self._tmpdir)
    cachefile = self._tmpdir + '/%s_%s_%s.nc'%(filetype,domain,field)

    # Pre-compute the data and save it, if this is the first time using it.
    if not exists(cachefile):
      print '===>', cachefile
      netcdf.save(cachefile, data)

    data = netcdf.open(cachefile)[field]

    return data

