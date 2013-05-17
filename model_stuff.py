
def rpnopen (filename):
  from pygeode.formats import rpn
  try:
    # For RPN interface v0.6+
    f = rpn.open(filename, squash_forecasts=True)
  except TypeError:
    # For RPN interface < v0.6
    f = rpn.open(filename)
  f = f.squeeze()
  return f

def rpnopen_sfconly (filename):
  f = rpnopen(filename)
  f = f(eta=1,zeta=1).squeeze()
  return f

# Extract a date from a GEM model filename
def file2date (filename):
  from re import search
  from datetime import datetime, timedelta
  out = search('[dkp][m](?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})_(?P<offset>\d+)(?P<units>([mh]|))$', filename).groupdict()
  units = out.pop('units')
  out = dict([k,int(v)] for k,v in out.items())
  offset = out.pop('offset')

  # Convert to datetime object for manipulating the forecast time
  out = datetime(**out)
  if units == 'm':
    out += timedelta (minutes=offset)
  elif units == 'h' or units == '':
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

# Extract a date from a flux file
def file2date_flux (filename):
  from re import search
  from datetime import datetime, timedelta
  out = search('area_(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})$', filename).groupdict()
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
def to_gph (var, GZ):
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  from pygeode.dataset import Dataset
  import numpy as np

  # Remove extra longitude from the data
  var = var.slice[:,:,:,:-1]
  GZ = GZ.slice[:,:,:,:-1]

  height = Height(range(68), name='height')

  if var.hasaxis('eta'):
    var = interpolate(var, inaxis='eta', outaxis=height, inx=GZ*10/1000)
  elif var.hasaxis('zeta'):
    # Subset GZ on tracer levels (applicable to GEM4 output)
    GZ_zeta = GZ.zeta.values
    var_zeta = var.zeta.values
    indices = []
    for zeta in var_zeta:
      indices.append(np.where(GZ_zeta==zeta)[0][0])
    GZ = GZ(i_zeta=indices)
    var = interpolate(var, inaxis='zeta', outaxis=height, inx=GZ*10/1000)

  var = var.transpose(0,3,1,2)
  return var


# New data interface - get data as needed on-the-fly.
# Replaces pre-computing everything with nc_cache.
# This should be faster, since we only compute what we need.

from data_interface import Data
class GEM_Data(Data):
  def __init__ (self, indir, name, title):
    from pygeode.formats.multifile import open_multi
    from pygeode.formats import rpn
    from pygeode.dataset import Dataset
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
    files_24h = sorted(glob(indir+"/dm*_024*"))
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
    testfiles = sorted(glob(indir+"/dm%04d%02d%02d00_???*"%(year,month,day)))
    testfiles = [rpn.open(f) for f in testfiles]
    times_with_3d = [int(f.forecast.values[0]) for f in testfiles if list(f['CO2'].getaxis(ZAxis).values) == levels]
    # Ignore 0h files, since we're already using the 24h forecasts
    if 0 in times_with_3d:
      times_with_3d.remove(0)

    dm_3d = [indir+"/dm*_%03d*"%h for h in times_with_3d]
    km_3d = [indir+"/km*_%03d*"%h for h in times_with_3d]
    pm_3d = [indir+"/pm*_%03d*"%h for h in times_with_3d]

    # Open the 3D files
    if any(len(glob(x))>0 for x in dm_3d):
      dm_3d = open_multi(dm_3d, opener=rpnopen, file2date=file2date)
      self.dm_3d = fix_timeaxis(dm_3d)
    else: self.dm_3d = Dataset([])
    if any(len(glob(x))>0 for x in km_3d):
      km_3d = open_multi(km_3d, opener=rpnopen, file2date=file2date)
      self.km_3d = fix_timeaxis(km_3d)
    else: self.km_3d = Dataset([])
    if any(len(glob(x))>0 for x in pm_3d):
      pm_3d = open_multi(pm_3d, opener=rpnopen, file2date=file2date)
      self.pm_3d = fix_timeaxis(pm_3d)
    else: self.pm_3d = Dataset([])



    ##############################
    # Surface data
    ##############################

    # Assume surface data is available in every output time.
    # Ignore 0h output - use 24h output instead.
    dm = [indir+"/dm*_%03d*"%i for i in range(1,25)]
    if any(len(glob(x))>0 for x in dm):
      dm = open_multi(dm, opener=rpnopen_sfconly, file2date=file2date)
      self.dm = fix_timeaxis(dm)
    else: self.dm = Dataset([])
    km = [indir+"/km*_%03d*"%i for i in range(1,25)]
    if any(len(glob(x))>0 for x in km):
      km = open_multi(km, opener=rpnopen_sfconly, file2date=file2date)
      self.km = fix_timeaxis(km)
    else: self.km = Dataset([])
    pm = [indir+"/pm*_%03d*"%i for i in range(1,25)]
    if any(len(glob(x))>0 for x in pm):
      pm = open_multi(pm, opener=rpnopen_sfconly, file2date=file2date)
      self.pm = fix_timeaxis(pm)
    else: self.pm = Dataset([])

    ##############################
    # Derived fields
    ##############################

    # (Things that may not have been output from the model, but that we can
    #  compute)

    # Sigma levels through debug field?
    # (works around Mantis issue #2355)
    for (SIGMA_name, DBG_name) in [('SIGM','3DB1'),('SIGT','3DB2')]:
      if SIGMA_name not in self.pm_3d and DBG_name in self.pm_3d:
        # Note: the debug field is missing surface values, have to re-create.
        from pygeode.var import concat
        from pygeode.var import Var
        import numpy as np
        sigma = self.pm_3d[DBG_name]
        sigma_bottom = sigma.slice[:,-1,:,:]
        # Override the values
        sigma_bottom = Var(axes=sigma_bottom.axes, values=np.ones(sigma_bottom.shape))
        sigma_rest = sigma.slice[:,:-1,:,:]
        # Recombine
        sigma = concat(sigma_rest,sigma_bottom)
        sigma.name = SIGMA_name
        self.pm_3d += sigma

    # Sigma levels - generated for GEM3 levels
    # Assume this is usually available in the physics bus
    if 'SIGM' not in self.pm_3d:
      test_field = (v for v in self.dm_3d if v.hasaxis(ZAxis)).next()
      assert test_field.hasaxis('eta')  # only works for 'eta' coordinates.
      Ps = self.dm_3d['P0'] * 100
      A = self.dm_3d.eta.auxasvar('A')
      B = self.dm_3d.eta.auxasvar('B')
      P = A + B * Ps
      P = P.transpose('time','eta','lat','lon')
      sigma = P / Ps
      sigma.name = 'SIGM'
      self.pm_3d += sigma



    # Grid cell areas
    if 'DX' not in self.pm_3d:
      from common import get_area
      dxdy = get_area(self.dm.lat, self.dm.lon)
      self.pm_3d += dxdy
      self.pm += dxdy

    ##############################
    # Unit conversions
    ##############################

    # CO2 tracers are in ug/kg, but we'd like to have ppm for diagnostics.
    # Conversion factor (from ug C / kg air to ppm)
    from common import molecular_weight as mw
    convert_CO2 = 1E-9 * mw['air'] / mw['C'] * 1E6
    for dataset_name in 'dm', 'dm_3d':
      dataset = getattr(self,dataset_name)
      for co2_name in 'CO2', 'CO2B', 'CFF', 'CBB', 'COC', 'CLA':
        if co2_name in dataset:
          new_field = dataset[co2_name]*convert_CO2
          new_field.name = co2_name
          dataset = dataset.replace_vars({co2_name:new_field})
      setattr(self,dataset_name,dataset)

  # Helper functions - find the field (look in dm,km,pm,etc. files)

  def _find_sfc_field (self, name):
    for dataset in self.dm, self.km, self.pm:
      if name in dataset: return dataset[name]
    raise KeyError ("%s not found in model surface data."%name)

  def _find_3d_field (self, name):
    for dataset in self.dm_3d, self.km_3d, self.pm_3d:
      if name in dataset: return dataset[name]
    raise KeyError ("%s not found in model 3d data."%name)

  # The data interface
  # Handles the computing of general diagnostic domains (zonal means, etc.)
  def get_data (self, domain, field):
    from os.path import exists
    from os import mkdir
    from pygeode.formats import netcdf

    # Determine which data is needed

    # Surface data (lowest model level)
    if domain == 'sfc':
      data = self._find_sfc_field(field)
    # Zonal mean, with data interpolated to a fixed set of geopotential heights
    elif domain == 'zonalmean_gph':
      data = self._find_3d_field(field)
      GZ = self._find_3d_field('GZ')
      data = to_gph(data,GZ).nanmean('lon')
    # "total column" (in kg/m2)
    elif domain == 'totalcolumn':
      from pygeode.axis import ZAxis
      from pygeode.var import Var
      from common import molecular_weight as mw, grav as g

      # Convert from ppm to kg / kg
      conversion = 1E-6 * mw['CO2'] / mw['air']

      test_field = self._find_3d_field('CO2')

      Ps = self.dm_3d['P0'] * 100 # Get Ps on 3D field time frequency
      sigma = self.pm_3d['SIGM']

      # Case 1 - GEM3 (unstaggered) levels
      if test_field.hasaxis("eta"):
        # Compute mixing ratio at half levels
        # Special case: air mass (not an actual output field)
        if field is 'air':
          c_half = 1
        else:
          c = self._find_3d_field(field) * conversion
          # Interpolate concentration to half levels
          c1 = c.slice[:,:-1,:,:]
          c2 = c.slice[:,1:,:,:]
          c2 = c2.replace_axes(eta=c1.eta)
          c_half = (c2 + c1) / 2
        # Compute sigma layers
        sigma1 = sigma.slice[:,:-1,:,:]
        sigma2 = sigma.slice[:,1:,:,:]
        sigma2 = sigma2.replace_axes(eta=sigma1.eta)
        dsigma = (sigma2-sigma1)
        # Integrate the tracer
        col = (c_half * dsigma).sum('eta')
        assert (col.naxes == 3)
        # Scale by Ps/g
        data = col * Ps / g
        data.name = field

      # Case 2 - GEM4 (staggered levels)
      elif test_field.hasaxis("zeta"):
        if field is 'air':
          c_kp1 = 1
        else:
          c = self._find_3d_field(field) * conversion
          # Assuming we have an unused "surface" diagnositic level
          assert 1.0 in c.getaxis("zeta").values
          c_kp1 = c.slice[:,1:-1,:,:]
        sigma_kp1 = sigma.slice[:,1:,:,:]
        sigma_k = sigma.slice[:,:-1,:,:]
        # Put everything on the same levels
        if isinstance(c_kp1,Var):
          c_kp1 = c_kp1.replace_axes(zeta=sigma_k.zeta)
        sigma_kp1 = sigma_kp1.replace_axes(zeta=sigma_k.zeta)
        # Do the summation
        col = ( (sigma_kp1 - sigma_k) * c_kp1 ).sum('zeta')
        # Scale by Ps/g
        data = col * Ps / g
        data.name = field

      else: raise Exception   # Unrecognized vertical coordinate

    # Average column (ppm)
    elif domain == 'avgcolumn':
      from common import molecular_weight as mw
      # Total column (kg/m2)
      tc = self.get_data('totalcolumn', field)
      # Total column air (kg/m2)
      Mair = self.get_data('totalcolumn', 'air')
      # Compute the mass mixing ratio
      data = tc / Mair
      # Convert kg/kg to ppm
      data *= mw['air']/mw['CO2'] * 1E6

      data.name = field

    elif domain == 'totalmass':
      # Total column (kg C/m2)
      tc = self.get_data('totalcolumn', field)
      area = self.pm_3d['DX']
      # Mass per grid area (kg)
      # Assume global grid - remove repeated longitude
      mass = (tc * area).slice[:,:,:-1].sum('lat','lon')
      # Convert from kg to Pg
      mass *= 1E-12
      data = mass
      data.name = field

    elif domain == 'Toronto':
      data = self._find_3d_field(field)
      data = data.squeeze(lat=43.7833,lon=280.5333)

    else: raise ValueError ("Unknown domain '%s'"%domain)

    # Make sure the data is in 32-bit precision
    if data.dtype.name != 'float32':
      data = data.as_type('float32')

    if not exists(self._tmpdir): mkdir(self._tmpdir)
    cachefile = self._tmpdir + '/%s_%s.nc'%(domain,field)

    # Pre-compute the data and save it, if this is the first time using it.
    if not exists(cachefile):
      print '===>', cachefile
      netcdf.save(cachefile, data)

    data = netcdf.open(cachefile)[field]

    return data

class GEM_Fluxes(Data):
  def __init__ (self, indir, name, title):
    from pygeode.formats.multifile import open_multi
    from pygeode.formats import rpn
    from pygeode.dataset import Dataset
    from glob import glob
    from pygeode.axis import ZAxis
    from common import fix_timeaxis

    self.name = name
    self.title = title
    self._tmpdir = indir + "/nc_cache"

    fluxes = open_multi(indir+"/area_??????????", format=rpn, file2date=file2date_flux, opener=rpnopen)
    fluxes = fix_timeaxis(fluxes)
    self.fluxes = fluxes

  def get_data (self, domain, field):
    from os.path import exists
    from os import mkdir
    from pygeode.formats import netcdf

    assert domain in ('sum',)

    # Determine which data is needed
    if domain == 'sum':
      # Sum, skipping the last (repeated) longitude
      data = self.fluxes[field].slice[:,:,:-1].sum('lat','lon')
    else: raise Exception

    # Make sure the data is in 32-bit precision
    if data.dtype.name != 'float32':
      data = data.as_type('float32')

    if not exists(self._tmpdir): mkdir(self._tmpdir)
    cachefile = self._tmpdir + '/%s_%s.nc'%(domain,field)

    # Pre-compute the data and save it, if this is the first time using it.
    if not exists(cachefile):
      print '===>', cachefile
      netcdf.save(cachefile, data)

    data = netcdf.open(cachefile)[field]

    return data


del Data
