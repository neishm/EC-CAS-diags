# Opener for EC-CAS data
def eccas_opener (filename):
  from pygeode.formats import fstd
  from pygeode.ufunc import exp, log
  data = fstd.open(filename, squash_forecasts=True, raw_list=True)

  # Convert to a dictionary (for referencing by variable name)
  data = dict((var.name,var) for var in data)

  # Convert some standard quantities
  # (old_name, new_name, scale, offset, units)
  conversions = (
    ('GZ', 'geopotential_height', 10, None, 'm'),
    ('P0', 'surface_pressure', None, None, 'hPa'),
    ('TT', 'air_temperature', None, None, 'K'),
  )

  # EC-CAS specific conversions:
  from common import molecular_weight as mw
  convert_CO2 = 1E-9 * mw['air'] / mw['C'] * 1E6
  convert_CH4 = 1E-9 * mw['air'] / mw['CH4'] * 1E6
  convert_CO2_flux = mw['CO2'] / mw['C']
  conversions += (
    ('ECO2', 'CO2_flux', convert_CO2_flux, None, 'g/s'),
    ('ECBB', 'CO2_fire_flux', convert_CO2_flux, None, 'g/s'),
    ('ECFF', 'CO2_fossil_flux', convert_CO2_flux, None, 'g/s'),
    ('ECOC', 'CO2_ocean_flux', convert_CO2_flux, None, 'g/s'),
    ('ECLA', 'CO2_bio_flux', convert_CO2_flux, None, 'g/s'),
    ('CO2', 'CO2', convert_CO2, None, 'ppm'),
    ('CBB', 'CO2_fire', convert_CO2, None, 'ppm'),
    ('CFF', 'CO2_fossil', convert_CO2, None, 'ppm'),
    ('COC', 'CO2_ocean', convert_CO2, -100, 'ppm'),
    ('CLA', 'CO2_bio', convert_CO2, -100, 'ppm'),
    ('CO2B', 'CO2_background', convert_CO2, None, 'ppm'),
    ('CH4', 'CH4', convert_CH4, None, 'ppm'),
    ('CH4B', 'CH4_background', convert_CH4, None, 'ppm'),
    ('CHFF', 'CH4_fossil', convert_CH4, None, 'ppm'),
    ('CHBB', 'CH4_fire', convert_CH4, None, 'ppm'),
    ('CHOC', 'CH4_ocean', convert_CH4, None, 'ppm'),
    ('CHNA', 'CH4_natural', convert_CH4, None, 'ppm'),
    ('CHAG', 'CH4_agriculture', convert_CH4, None, 'ppm'),
  )

  # Do the conversions
  for old_name, new_name, scale, offset, units in conversions:
    if old_name in data:
      var = data.pop(old_name)
      if scale is not None: var *= scale
      if offset is not None: var += offset
      if units is not None: var.atts['units'] = units
      data[new_name] = var

  # Compute a pressure field
  P = None

  if 'surface_pressure' in data:

    Ps = data['surface_pressure']

    # eta coordinates?
    if any(var.hasaxis(fstd.Hybrid) for var in data.itervalues()):
      eta = set()
      for var in data.itervalues():
        if var.hasaxis(fstd.Hybrid):
          current = var.getaxis(fstd.Hybrid)
          current = set(zip(current.values, current.A, current.B))
          eta.update(current)
      eta = sorted(eta, reverse=True)
      eta, A, B = zip(*eta)
      eta = fstd.Hybrid(values=eta, A=A, B=B)
      A = eta.auxasvar('A')
      B = eta.auxasvar('B')
      P = A + B * Ps
      P /= 100 # hPa

    # zeta coordinates?
    if any(var.hasaxis(fstd.LogHybrid) for var in data.itervalues()):
      zeta = set()
      for var in data.itervalues():
        if var.hasaxis(fstd.LogHybrid):
          current = var.getaxis(fstd.LogHybrid)
          current = set(zip(current.values, current.A, current.B))
          zeta.update(current)
      zeta = sorted(zeta, reverse=True)
      zeta, A, B = zip(*zeta)
      zeta = fstd.LogHybrid(values=zeta, A=A, B=B)
      A = zeta.auxasvar('A')
      B = zeta.auxasvar('B')

      P = exp(A + B * log(Ps/100000))
      P = P.transpose('time','zeta','lat','lon')
      P /= 100 # hPa

  if P is not None:
    P.units = 'hPa'
    data['air_pressure'] = P

  # Grid cell areas
  if 'DX' in data:
    data['cell_area'] = data.pop('DX')
    data['cell_area'].atts['units'] = 'm2'
  """
  else:
    from common import get_area
    from warnings import warn
    warn ("Computing grid cell areas diagnostically, since DX not found.")
    var = data.itervalues().next()
    data['cell_area'] = get_area(var.lat, var.lon)
  """
  #TODO: compute cell_area for lat/lon.

  # TODO: post-process the fluxes into g m-2 s-1

  # General cleanup stuff

  # Make sure the variables have the appropriate names
  for name, var in data.iteritems():  var.name = name

  # Convert to a list
  data = list(data.values())

  return data



# Convert zonal mean data (on height)
def to_gph (var, z):
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  from pygeode.dataset import Dataset
  import numpy as np

  # Remove extra longitude from the data
  var = var.slice[:,:,:,:-1]
  GZ = GZ.slice[:,:,:,:-1]

  height = Height(range(68), name='height')

  var = interpolate(var, inaxis='zaxis', outaxis=height, inx=z/1000.)

  var = var.transpose(0,3,1,2)

  return var

# Wrapper for getting GEM data back out of a cached netcdf file
# (This will hook into the cache, to preserve FSTD axes after save/reloading)
def gem_load_cache_hook (dataset):
  from pygeode.formats.fstd import detect_fstd_axes
  data = list(dataset.vars)
  detect_fstd_axes(data)
  return data[0]


# Some useful criteria for searching for fields
def have_surface (varlist):
  from pygeode.axis import ZAxis
  from pygeode.formats.fstd import Hybrid, LogHybrid
  for var in varlist:
    if var.hasaxis(Hybrid):
      return 1.0 in var.getaxis(Hybrid).values
    if var.hasaxis(LogHybrid):
      return 1.0 in var.getaxis(LogHybrid).values
  # No vertical info?
  return False

def number_of_timesteps (varlist):
  from pygeode.axis import TAxis
  for var in varlist:
    if var.hasaxis(TAxis):
      return len(var.getaxis(TAxis))



# GEM data interface
class GEM_Data (object):
  def __init__ (self, experiment_dir, flux_dir, name, title, tmpdir=None):
    from cache import Cache
    from data_interface import DataInterface

    indir = experiment_dir

    self.name = name
    self.title = title
    fallback_dirs = [tmpdir] if tmpdir is not None else []
    cache = Cache(dir = indir + "/nc_cache", fallback_dirs=fallback_dirs, global_prefix=name+"_", load_hook=gem_load_cache_hook)

    files = []

    ##############################
    # Fluxes
    ##############################

    if flux_dir is not None:
      files.append(flux_dir+"/area_??????????")
      # Note: Internal units are g/s

    ##############################
    # EnKF output
    ##############################
    #TODO: remove

    files.append(indir+"/[0-9]*_???_chmmean")
    files.append(indir+"/[0-9]*_???_chmstd")

    ##############################
    # Model output
    ##############################

    files.append(indir+"/[0-9]*_[0-9]*")
    files.append(indir+"/km[0-9]*_[0-9]*")
    files.append(indir+"/dm[0-9]*_[0-9]*")
    files.append(indir+"/pm[0-9]*_[0-9]*")
    files.append(indir+"/k[0-9]*_[0-9]*")
    files.append(indir+"/d[0-9]*_[0-9]*")
    files.append(indir+"/p[0-9]*_[0-9]*")

    self.data = DataInterface(files, opener=eccas_opener, cache=cache)
    self.cache = cache

  # Helper function - find the best field matches that fit some criteria
  def find_best (self, fields, requirement=None, metric=None):

    # If we are given a single field name (not in a list), then return a
    # single field (also not in a list structure).
    collapse_result = False
    if isinstance(fields,str):
      fields = [fields]
      collapse_result = True

    if len(fields) == 1:
      candidates = zip(self.data.find(*fields))
    else:
      candidates = self.data.find(fields)

    if requirement is not None:
      candidates = filter(requirement, candidates)

    # Sort by the criteria (higher value is better)
    if metric is not None:
      candidates = sorted(candidates, key=metric, reverse=True)

    # Use the best result
    result = candidates[0]

    if collapse_result: result = result[0]
    return result


  # The data interface
  # Handles the computing of general diagnostic domains (zonal means, etc.)
  def get_data (self, domain, standard_name, stat='mean'):
    #TODO: update for new interface (doesn't work right now!)

    field = standard_name

    # Determine which data is needed

    # Surface data (lowest model level)
    if domain == 'sfc':
      data = self.find_best(field, requirement=have_surface, metric=number_of_timesteps)
    # Zonal mean, with data interpolated to a fixed set of geopotential heights
    elif domain == 'zonalmean_gph':
      data = self._find_3d_field(field,stat)
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
          c = self._find_3d_field(field,stat) * conversion
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
          c = self._find_3d_field(field,stat) * conversion
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
      tc = self.get_data('totalcolumn', standard_name, stat)
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
      if stat != 'mean': raise KeyError("Don't have stddev on fluxes")
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
      data = self._find_3d_field(field,stat)
      data = data.squeeze(lat=43.7833,lon=280.5333)

    else: raise ValueError ("Unknown domain '%s'"%domain)

    if stat == 'mean':
      prefix = '%s_%s'%(domain,field)
    else:
      prefix = '%s_%s_%s'%(stat,domain,field)
    return self.cache.write(data,prefix)


