
# Method to open a single file
def open_file (filename):
  from pygeode.formats import fstd
  return fstd.open(filename, raw_list=True)


# Method to decode an opened dataset (standardize variable names, and add any
# extra info needed (pressure values, cell area, etc.)
def decode (dataset, dry_air=False):
  from pygeode.formats import fstd
  from pygeode.ufunc import exp, log
  from pygeode.var import concat, Var
  from pygeode.axis import ZAxis
  from pygeode.dataset import asdataset

  dataset = asdataset(dataset)

  # Convert to a dictionary (for referencing by variable name)
  data = dict((var.name,var) for var in dataset)

  # Determine if we have ensemble spread data from EC-CAS
  chmstd = False
  for var in data.itervalues():
    if var.atts.get('etiket') == 'STDDEV':
      chmstd = True

  # Temporarily blacklist GZ and P0 from ensemble spread files.
  if chmstd:
    del data["GZ"]
    del data["P0"]

  # Special case: tracer is in mass mixing ratio w.r.t. dry air
  # Put it in moist air to be consistent with other experiments.
  if dry_air and 'HU' in data:
    data['CO2'] *= (1 - data['HU'])

  # Convert some standard quantities
  # (old_name, new_name, scale, offset, units)
  conversions = (
    ('GZ', 'geopotential_height', 'dam'),
    ('P0', 'surface_pressure', 'hPa'),
    ('TT', 'air_temperature', 'K'),
    ('HU', 'specific_humidity', 'kg(H2O) kg(air)-1'),
    ('DX', 'cell_area', 'm2'),
  )

  # EC-CAS specific conversions:
  suffix = ""
  if chmstd: suffix = "_ensemblespread"
  conversions += (
    ('ECO2', 'CO2_flux', 'g(C) s-1'),
    ('ECBB', 'CO2_fire_flux', 'g(C) s-1'),
    ('ECFF', 'CO2_fossil_flux', 'g(C) s-1'),
    ('ECOC', 'CO2_ocean_flux', 'g(C) s-1'),
    ('ECLA', 'CO2_bio_flux', 'g(C) s-1'),
    ('CO2', 'CO2'+suffix, 'ug(C) kg(air)-1'),
    ('CBB', 'CO2_fire'+suffix, 'ug(C) kg(air)-1'),
    ('CFF', 'CO2_fossil'+suffix, 'ug(C) kg(air)-1'),
    ('COC', 'CO2_ocean'+suffix, 'ug(C) kg(air)-1'),
    ('CLA', 'CO2_bio'+suffix, 'ug(C) kg(air)-1'),
    ('CO2B', 'CO2_background'+suffix, 'ug(C) kg(air)-1'),
    ('CH4', 'CH4', 'ug kg(air)-1'),
    ('CH4B', 'CH4_background', 'ug kg(air)-1'),
    ('CHFF', 'CH4_fossil', 'ug kg(air)-1'),
    ('CHBB', 'CH4_fire', 'ug kg(air)-1'),
    ('CHOC', 'CH4_ocean', 'ug kg(air)-1'),
    ('CHNA', 'CH4_natural', 'ug kg(air)-1'),
    ('CHAG', 'CH4_agriculture', 'ug kg(air)-1'),
  )

  # Do the conversions
  for old_name, new_name, units in conversions:
    if old_name in data:
      var = data.pop(old_name)
      var.atts['units'] = units
      data[new_name] = var

  # Offset the ocean and land fields by 100ppm
  from common import conversion_factor
  if 'CO2_ocean' in data:
    data['CO2_ocean'] -= conversion_factor('100 ppm', 'ug(C) kg(air)-1', context='CO2')
  if 'CO2_bio' in data:
    data['CO2_bio'] -= conversion_factor('100 ppm', 'ug(C) kg(air)-1', context='CO2')

  # Add a water tracer, if we have humidity
  if 'specific_humidity' in data:
    data['H2O'] = data['specific_humidity']

  # Compute a pressure field.
  # Also, compute a dp field (vertical change in pressure within a gridbox).
  P = None
  dP = None

  if 'surface_pressure' in data:

    Ps = data['surface_pressure']

    # eta coordinates?
    eta_vars = [var for var in data.itervalues() if var.hasaxis(fstd.Hybrid)]
    if len(eta_vars) > 0:
      eta = eta_vars[0].getaxis(fstd.Hybrid)
      A = eta.auxasvar('A')
      B = eta.auxasvar('B')
      P = A + B * Ps * 100
      P = P.transpose('time','forecast','eta','lat','lon')
      P /= 100 # hPa

      # dP
      #TODO: Use ptop as upper boundary, instead of ignoring (zeroing) that layer?
      # Need to overwrite the eta axis with a generic one before concatenating,
      # because eta axes require explict A/B arrays (which concat doesn't see)
      from pygeode.axis import ZAxis
      PP = P.replace_axes(eta=ZAxis(P.eta.values))
      P_k = concat(PP.slice[:,:,0,:,:].replace_axes(zaxis=ZAxis([-1.])), PP.slice[:,:,:-1,:,:]).replace_axes(zaxis=PP.zaxis)
      P_kp1 = concat(PP.slice[:,:,1:,:,:], PP.slice[:,:,-1,:,:].replace_axes(zaxis=ZAxis([2.]))).replace_axes(zaxis=PP.zaxis)
      dP = abs(P_kp1 - P_k)/2
      # Put the eta axis back
      dP = dP.replace_axes(zaxis=P.eta)

    # zeta coordinates?
    zeta_vars = [var for var in data.itervalues() if var.hasaxis(fstd.LogHybrid)]
    if len(zeta_vars) > 0:
      zeta = zeta_vars[0].getaxis(fstd.LogHybrid)
      A = zeta.auxasvar('A')
      B = zeta.auxasvar('B')
      pref = zeta.atts['pref']
      ptop = zeta.atts['ptop']

      P = exp(A + B * log(Ps*100/pref))
      P = P.transpose('time','forecast','zeta','lat','lon')
      P /= 100 # hPa

      # dP
      #TODO: produce dP for both thermodynamic and momentum levels
      # (currently just thermo)
      if set(zeta.auxarrays['A']) <= set(zeta.atts['a_t']):
        A_m = list(zeta.atts['a_m'])
        B_m = list(zeta.atts['b_m'])
        # Add model top (not a true level, but needed for dP calculation)
        # Also, duplicate the bottom (surface) level to get dP=0 at bottom
        import math
        A_m = [math.log(ptop)] + A_m + [A_m[-1]]
        B_m = [0] + B_m + [B_m[-1]]
        # Convert to Var objects
        zaxis = ZAxis(range(len(A_m)))
        A_m = Var(axes=[zaxis], values=A_m)
        B_m = Var(axes=[zaxis], values=B_m)
        # Compute pressure on (extended) momentum levels
        P_m = exp(A_m + B_m * log(Ps*100/pref))
        P_m = P_m.transpose('time','forecast','zaxis','lat','lon')
        # Compute dP
        P_m_1 = P_m.slice[:,:,1:,:,:]
        P_m_2 = P_m.slice[:,:,:-1,:,:].replace_axes(zaxis=P_m_1.zaxis)
        dP = P_m_1 - P_m_2
        # Put on proper thermodynamic levels
        from pygeode.formats.fstd_core import decode_levels
        values, kind = decode_levels(zeta.atts['ip1_t'])
        zaxis = fstd.LogHybrid(values=values, A=zeta.atts['a_t'], B=zeta.atts['b_t'])
        dP = dP.replace_axes(zaxis=zaxis)
        dP /= 100 # hPa


  if P is not None:
    P.atts['units'] = 'hPa'
    data['air_pressure'] = P

  if dP is not None:
    dP.atts['units'] = 'hPa'
    data['dp'] = dP  #TODO: better name?

  # Grid cell areas
  if 'cell_area' not in data:
    for varname in 'CO2_flux', 'surface_pressure':
      if varname in data:
        lat = data[varname].lat
        lon = data[varname].lon
        time = data[varname].time
        from common import get_area
        data['cell_area'] = get_area(lat,lon).extend(0,time)
        break

  # General cleanup stuff

  # Make sure the variables have the appropriate names
  for name, var in data.iteritems():  var.name = name

  # Convert to a list
  data = list(data.values())

  # Remove the forecast axis before returning the data
  # (not needed for any current diagnostics).
  from common import squash_forecasts
  data = map(squash_forecasts,data)

  return data


# Method to find all files in the given directory, which can be accessed
# through this interface.
def find_files (dirname):
  from os.path import exists
  from glob import glob

  files = []

  ##############################
  # Model output
  ##############################

  if exists (dirname+'/model'):
    model_dir = dirname+'/model'
  else:
    model_dir = dirname

  files.extend(glob(model_dir+"/[0-9]*_[0-9]*"))
  files.extend(glob(model_dir+"/km[0-9]*_[0-9]*"))
  files.extend(glob(model_dir+"/dm[0-9]*_[0-9]*"))
  files.extend(glob(model_dir+"/pm[0-9]*_[0-9]*"))
  files.extend(glob(model_dir+"/k[0-9]*_[0-9]*"))
  files.extend(glob(model_dir+"/d[0-9]*_[0-9]*"))
  files.extend(glob(model_dir+"/p[0-9]*_[0-9]*"))
  # Omit 0h forecasts
  files = [f for f in files if not f.endswith('_000') and not f.endswith('_000h')]

  ##############################
  # Fluxes
  ##############################

  files.extend(glob(dirname+"/area_??????????"))

  return files


# Wrapper for getting GEM data back out of a cached netcdf file
# (This will hook into the cache, to preserve FSTD axes after save/reloading)
def load_hook (dataset):
  from pygeode.formats.fstd import detect_fstd_axes
  data = list(dataset.vars)
  detect_fstd_axes(data)
  return data




# GEM data interface
class GEM_Data (object):
  def __init__ (self, experiment_dir, flux_dir, name, title, tmpdir=None, dry_air=False):
    from cache import Cache
    from data_interface import DataInterface
    from glob import glob

    indir = experiment_dir

    self.name = name
    self.title = title
    fallback_dirs = [tmpdir] if tmpdir is not None else []
    cache = Cache(dir = indir + "/nc_cache", fallback_dirs=fallback_dirs, global_prefix=name+"_", load_hooks=[load_hook])

    files = []

    ##############################
    # Model output
    ##############################

    files.extend(glob(indir+"/[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/km[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/dm[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/pm[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/k[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/d[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/p[0-9]*_[0-9]*"))
    # Omit 0h forecasts
    files = [f for f in files if not f.endswith('_000') and not f.endswith('_000h')]

    ##############################
    # Fluxes
    ##############################

    if flux_dir is not None:
      files.extend(glob(flux_dir+"/area_2009??????"))

    manifest = cache.full_path("manifest", writeable=True)

    # Ensemble mean data
    chmmean_files = [f for f in files if f.endswith('_chmmean')]
    chmmean_data = DataInterface.from_files(chmmean_files, opener=open_file, manifest=manifest)
    # Apply the conversions & transformations
    chmmean_data = DataInterface(map(decode,chmmean_data))

    # Ensemble spread data
    chmstd_files = [f for f in files if f.endswith('_chmstd')]
    chmstd_data = DataInterface.from_files(chmstd_files, opener=open_file, manifest=manifest)
    # Apply the conversions & transformations
    chmstd_data = DataInterface(map(decode,chmstd_data))

    # Area emissions
    flux_files = [f for f in files if '/area_' in f]
    flux_data = DataInterface.from_files(flux_files, opener=open_file, manifest=manifest)
    # Apply the conversions & transformations
    flux_data = DataInterface(map(decode,flux_data))

    # Forward model data
    forward_files = sorted(set(files)-set(chmmean_files)-set(chmstd_files)-set(flux_files))
    forward_data = DataInterface.from_files(forward_files, opener=open_file, manifest=manifest)
    # Apply the conversions & transformations
    forward_data = DataInterface([decode(fd, dry_air=dry_air) for fd in forward_data])

    # Fix the area emissions data, to have the proper lat/lon
    lat = forward_data.datasets[0].lat
    lon = forward_data.datasets[0].lon
    flux_data = DataInterface(d.replace_axes(lat=lat,lon=lon) for d in flux_data)

    # Combine all datasets into a single unit
    self.data = DataInterface(chmmean_data.datasets+chmstd_data.datasets+flux_data.datasets+forward_data.datasets)

    self.cache = cache


