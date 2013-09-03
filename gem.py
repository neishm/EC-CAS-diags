
def rpnopen (filename):
  from pygeode.formats import fstd
  f = fstd.open(filename, squash_forecasts=True)
  return f

def rpnopen_sfconly (filename):
  f = rpnopen(filename)
  f = f(eta=1,zeta=1).squeeze()
  return f

# Extract a date from a GEM model filename
def file2date (filename):
  from re import search
  from datetime import datetime, timedelta
  out = search('([dkp][m]|)(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})_(?P<offset>\d+)(?P<units>([mh]|))(?P<enkf_ext>_chmmean|)$', filename).groupdict()
  units = out.pop('units')
  enkf_ext = out.pop('enkf_ext')
  out = dict([k,int(v)] for k,v in out.items())
  offset = out.pop('offset')

  # Convert to datetime object for manipulating the forecast time
  out = datetime(**out)
  if units == 'm':
    out += timedelta (minutes=offset)
  elif units == 'h' or units == '':
    out += timedelta (hours=offset)
  else: raise Exception

  # We have to be careful with the forecast hour in the file.
  # For EnKF, we have data before this forecast hour as well.
  if enkf_ext != '':
    out -= timedelta (hours=6)  #TODO: remove hard-coded EnKF cycle time
    # Add back the first time we output
    out += timedelta (hours=3)

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
    var = interpolate(var, inaxis='eta', outaxis=height, inx=GZ/1000.)
  elif var.hasaxis('zeta'):
    # Subset GZ on tracer levels (applicable to GEM4 output)
    GZ_zeta = GZ.zeta.values
    var_zeta = var.zeta.values
    indices = []
    for zeta in var_zeta:
      indices.append(np.where(GZ_zeta==zeta)[0][0])
    GZ = GZ(i_zeta=indices)
    var = interpolate(var, inaxis='zeta', outaxis=height, inx=GZ/1000.)

  var = var.transpose(0,3,1,2)
  return var


# New data interface - get data as needed on-the-fly.
# Replaces pre-computing everything with nc_cache.
# This should be faster, since we only compute what we need.

from data_interface import Data
class GEM_Data(Data):
  def __init__ (self, experiment_dir, flux_dir, name, title, tmpdir=None):
    from pygeode.formats.multifile import open_multi
    from pygeode.formats import fstd as rpn
    from pygeode.dataset import Dataset
    from glob import glob
    from pygeode.axis import ZAxis
    from common import fix_timeaxis

    indir = experiment_dir

    self.name = name
    self.title = title
    self._cachedir = indir + "/nc_cache"
    self._tmpdir = tmpdir
    if self._tmpdir is None:
      self._tmpdir = self._cachedir

    ##############################
    # Fluxes
    ##############################

    if flux_dir is not None:
      fluxes = open_multi(flux_dir+"/area_??????????", format=rpn, file2date=file2date_flux, opener=rpnopen)
      # Note: Internal units are g/s
      fluxes = fix_timeaxis(fluxes)
      self.fluxes = fluxes
    else:
      self.fluxes = Dataset([])

    ##############################
    # Data with vertical extent
    ##############################

    # First case - we have EnKF data (mean state)
    if len(glob(indir+"/*_???_chmmean")) > 0:
      # The output frequency is pretty much hard-coded on the EnKF side right
      # now, so don't bother trying to generalize.
      # (Can't properly test a generalization anyway)

      combined_3d = open_multi(indir+"/[0-9]*_???_chmmean", opener=rpnopen, file2date=file2date)
      combined_3d = fix_timeaxis(combined_3d)

      # The surface output is the same frequency as the 3D output
      # (no special high-frequency surface output)
      combined = combined_3d(eta=1,zeta=1).squeeze()


    # Second case - we have a single model integration
    else:
      # Open a single day of data, to determine at what times 3D data is saved.
      files_24h = sorted(glob(indir+"/*_024*"))
      testfile = files_24h[0]
      del files_24h
      testfile = rpn.open(testfile)
      # Assume we have 3D output for at least the 24h forecasts
      # Also, assume that 3D tracer output has corresponding 3D GZ output.
      testfield = 'GZ'
      levels = list(testfile[testfield].getaxis(ZAxis).values)
      # Get the rest of the files for this day, check the levels
      year = int(testfile.time.year[0])
      month = int(testfile.time.month[0])
      day = int(testfile.time.day[0])
      del testfile
      testfiles = sorted(glob(indir+"/*%04d%02d%02d00_???*"%(year,month,day)))
      testfiles = [rpn.open(f) for f in testfiles]
      testfiles = [f for f in testfiles if testfield in f]
      times_with_3d = [int(f.forecast.values[0]) for f in testfiles if list(f[testfield].getaxis(ZAxis).values) == levels]
      # Ignore 0h files, since we're already using the 24h forecasts
      if 0 in times_with_3d:
        times_with_3d.remove(0)

      dm_3d = [indir+"/dm*_%03d*"%h for h in times_with_3d]
      km_3d = [indir+"/km*_%03d*"%h for h in times_with_3d]
      pm_3d = [indir+"/pm*_%03d*"%h for h in times_with_3d]
      combined_3d = [indir+"/[0-9]*_%03d*"%h for h in times_with_3d]

      # Open the 3D files
      if any(len(glob(x))>0 for x in dm_3d):
        dm_3d = open_multi(dm_3d, opener=rpnopen, file2date=file2date)
        dm_3d = fix_timeaxis(dm_3d)
      else: dm_3d = Dataset([])
      if any(len(glob(x))>0 for x in km_3d):
        km_3d = open_multi(km_3d, opener=rpnopen, file2date=file2date)
        km_3d = fix_timeaxis(km_3d)
      else: km_3d = Dataset([])
      if any(len(glob(x))>0 for x in pm_3d):
        pm_3d = open_multi(pm_3d, opener=rpnopen, file2date=file2date)
        pm_3d = fix_timeaxis(pm_3d)
      else: pm_3d = Dataset([])

      if any(len(glob(x))>0 for x in combined_3d):
        combined_3d = open_multi(combined_3d, opener=rpnopen, file2date=file2date)
        combined_3d = fix_timeaxis(combined_3d)
      else: combined_3d = dm_3d + km_3d + pm_3d


      ##############################
      # Surface data (non-EnKF data)
      ##############################

      # Assume surface data is available in every output time.
      # Ignore 0h output - use 24h output instead.

      dm = [indir+"/dm*_%03d*"%i for i in range(1,25)]
      if any(len(glob(x))>0 for x in dm):
        dm = open_multi(dm, opener=rpnopen_sfconly, file2date=file2date)
        dm = fix_timeaxis(dm)
      else: dm = Dataset([])
      km = [indir+"/km*_%03d*"%i for i in range(1,25)]
      if any(len(glob(x))>0 for x in km):
        km = open_multi(km, opener=rpnopen_sfconly, file2date=file2date)
        km = fix_timeaxis(km)
      else: km = Dataset([])
      pm = [indir+"/pm*_%03d*"%i for i in range(1,25)]
      if any(len(glob(x))>0 for x in pm):
        pm = open_multi(pm, opener=rpnopen_sfconly, file2date=file2date)
        pm = fix_timeaxis(pm)
      else: pm = Dataset([])

      combined = [indir+"/[0-9]*_%03d*"%i for i in range(1,25)]
      if any(len(glob(x))>0 for x in combined):
        combined = open_multi(combined, opener=rpnopen_sfconly, file2date=file2date)
        combined= fix_timeaxis(combined)
      else: combined = dm + km + pm

    # End of EnKF / non-EnKF input mapping

    self.combined_3d = combined_3d
    self.combined = combined

    ##############################
    # Derived fields
    ##############################

    # (Things that may not have been output from the model, but that we can
    #  compute)

    # Sigma levels (momentum)
    if 'SIGM' not in self.combined_3d:
      try:
        testfield = self.combined_3d.GZ
      except AttributeError:
        testfield = self.combined_3d.TT
      Ps = self.combined_3d['P0'] * 100
      if testfield.hasaxis('eta'):
        A = testfield.eta.auxasvar('A')
        B = testfield.eta.auxasvar('B')
        P = A + B * Ps
        P = P.transpose('time','eta','lat','lon')
      elif testfield.hasaxis('zeta'):
        from pygeode.formats.fstd import LogHybrid
        from pygeode.formats.fstd_core import decode_levels
        from pygeode.ufunc import exp, log
        # Construct a momentum level axis from the prescribed momentum levels
        A = testfield.zeta.atts['a_m']
        B = testfield.zeta.atts['b_m']
        hy, kind = decode_levels(testfield.zeta.atts['ip1_m'])
        z = LogHybrid(values=hy, A=A, B=B)
        A = z.auxasvar('A')
        B = z.auxasvar('B')
        # Compute pressure
        P = exp(A + B * log(Ps/100000))
        P = P.transpose('time','zeta','lat','lon')
      else: raise TypeError("unknown vertical axis")
      sigma = P / Ps
      sigma.name = 'SIGM'
      self.combined_3d += sigma



    # Grid cell areas
    if 'DX' not in self.combined_3d:
      from common import get_area
      dxdy = get_area(self.combined.lat, self.combined.lon)
      self.combined_3d += dxdy
      self.combined += dxdy

    ##############################
    # Unit conversions
    ##############################

    # CO2 tracers are in ug/kg, but we'd like to have ppm for diagnostics.
    # Conversion factor (from ug C / kg air to ppm)
    from common import molecular_weight as mw
    convert_CO2 = 1E-9 * mw['air'] / mw['C'] * 1E6
    convert_CH4 = 1E-9 * mw['air'] / mw['CH4'] * 1E6
    convert_CO2_flux = mw['CO2'] / mw['C']
    for dataset_name in 'combined', 'combined_3d':
      dataset = getattr(self,dataset_name)
      # Convert CO2 units
      for co2_name in 'CO2', 'CO2B', 'CFF', 'CBB', 'COC', 'CLA':
        if co2_name in dataset:
          new_field = dataset[co2_name]*convert_CO2
          new_field.name = co2_name
          new_field.atts['units'] = 'ppm'
          dataset = dataset.replace_vars({co2_name:new_field})
      # Convert CH4 units
      for ch4_name in 'CH4', 'CH4B', 'CHFF', 'CHBB', 'CHOC', 'CHNA', 'CHAG':
        if ch4_name in dataset:
          new_field = dataset[ch4_name]*convert_CH4
          new_field.name = ch4_name
          new_field.atts['units'] = 'ppm'
          dataset = dataset.replace_vars({ch4_name:new_field})
      # Some fields were offset to avoid negative values in the model
      for co2_name in 'COC', 'CLA':
        if co2_name in dataset:
          new_field = dataset[co2_name] - 100
          new_field.name = co2_name
          dataset = dataset.replace_vars({co2_name:new_field})
      # Convert GZ units (from decametres to metres)
      if 'GZ' in dataset:
        GZ = dataset['GZ']*10
        GZ.name = 'GZ'
        dataset = dataset.replace_vars(GZ=GZ)

      setattr(self,dataset_name,dataset)

    # Convert CO2 flux units (g/s C to g/s CO2)
    for co2_name in 'ECO2', 'ECFF', 'ECBB', 'ECOC', 'ECLA':
      if co2_name in self.fluxes:
        new_field = self.fluxes[co2_name]*convert_CO2_flux
        new_field.name = co2_name
        new_field.atts['units'] = 'g/s'
        self.fluxes = self.fluxes.replace_vars({co2_name:new_field})

  # Helper functions - find the field (look in dm,km,pm,etc. files)

  # Instead of renaming all the variables in the model, patch on a mapping
  # to "standard" names.
  local_names = {
    'CO2':'CO2',
    'CH4':'CH4',
    'CO2_background':'CO2B',
    'geopotential_height':'GZ',
    'eddy_diffusivity':'KTN',
    'PBL_height':'H',
    'air':'air'
  }

  def _find_sfc_field (self, name):
    if name in self.combined: return self.combined[name]
    raise KeyError ("%s not found in model surface data."%name)

  def _find_3d_field (self, name):
    if name in self.combined_3d: return self.combined_3d[name]
    raise KeyError ("%s not found in model 3d data."%name)

  # The data interface
  # Handles the computing of general diagnostic domains (zonal means, etc.)
  def get_data (self, domain, standard_name, stat='mean'):

    if stat != 'mean':
      raise KeyError("Can only provide mean data at the moment")

    # Translate the standard name into the name used by GEM.
    if standard_name in self.local_names:
      field = self.local_names[standard_name]
    else:
      # No field name translation
      field = standard_name

    # Determine which data is needed

    # Surface data (lowest model level)
    if domain == 'sfc':
      data = self._find_sfc_field(field)
    # Zonal mean, with data interpolated to a fixed set of geopotential heights
    elif domain == 'zonalmean_gph':
      data = self._find_3d_field(field)
      GZ = self._find_3d_field('GZ')
      data = to_gph(data,GZ).nanmean('lon')
      data.atts['units'] = 'ppm'
    # "total column" (in kg/m2)
    elif domain == 'totalcolumn':
      from pygeode.axis import ZAxis
      from pygeode.var import Var
      from common import molecular_weight as mw, grav as g

      # Convert from ppm to kg / kg
      conversion = 1E-6 * mw[standard_name] / mw['air']

      Ps = self.combined_3d['P0'] * 100 # Get Ps on 3D field time frequency
      sigma = self.combined_3d['SIGM']

      # Case 1 - GEM3 (unstaggered) levels
      if sigma.hasaxis("eta"):
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
      elif sigma.hasaxis("zeta"):
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
      tc = self.get_data('totalcolumn', standard_name, stat)
      # Total column air (kg/m2)
      Mair = self.get_data('totalcolumn', 'air')
      # Compute the mass mixing ratio
      data = tc / Mair
      # Convert kg/kg to ppm
      data *= mw['air']/mw[standard_name] * 1E6

      data.name = field
      data.atts['units'] = 'ppm'

    elif domain == 'totalmass':
      # Total column (kg /m2)
      tc = self.get_data('totalcolumn', standard_name)
      area = self.combined_3d['DX']
      # Mass per grid area (kg)
      # Assume global grid - remove repeated longitude
      mass = (tc * area).slice[:,:,:-1].sum('lat','lon')
      # Convert from kg to Pg
      mass *= 1E-12
      data = mass
      data.name = field

    # Integrated flux (if available)
    elif domain == 'totalflux':
      from common import molecular_weight as mw
      if not hasattr(self,'fluxes'):
        raise KeyError ("Can't compute a total flux, because no fluxes are identified with this run.")
      # We have a slightly different naming convention for fluxes
      field = 'E'+field
      # Sum, skipping the last (repeated) longitude
      data = self.fluxes[field].slice[:,:,:-1].sum('lat','lon')
      # Convert from g/s to moles/s
      data /= mw[standard_name]
      data.name = field

    elif domain == 'Toronto':
      data = self._find_3d_field(field)
      data = data.squeeze(lat=43.7833,lon=280.5333)

    else: raise ValueError ("Unknown domain '%s'"%domain)

    return self._cache(data,'%s_%s_%s.nc'%(self.name,domain,field))


del Data

