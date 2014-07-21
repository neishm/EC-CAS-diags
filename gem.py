# Opener for EC-CAS data
def eccas_opener (filename):
  from pygeode.formats import fstd
  return fstd.open(filename, raw_list=True)


def eccas_products (dataset, chmmean=False, chmstd=False):
  from pygeode.formats import fstd
  from pygeode.ufunc import exp, log
  from pygeode.var import concat, Var
  from pygeode.axis import ZAxis

  # Convert to a dictionary (for referencing by variable name)
  data = dict((var.name,var) for var in dataset)

  # Temporarily blacklist GZ and P0 from ensemble spread files.
  if chmstd:
    del data["GZ"]
    del data["P0"]

  # Convert some standard quantities
  # (old_name, new_name, scale, offset, units)
  conversions = (
    ('GZ', 'geopotential_height', 10, None, 'm'),
    ('P0', 'surface_pressure', None, None, 'hPa'),
    ('TT', 'air_temperature', None, None, 'K'),
    ('HU', 'specific_humidity', None, None, 'kg kg-1'),
  )

  # EC-CAS specific conversions:
  from common import molecular_weight as mw
  convert_CO2 = 1E-9 * mw['air'] / mw['C'] * 1E6
  convert_CH4 = 1E-9 * mw['air'] / mw['CH4'] * 1E6
  convert_CO2_flux = mw['CO2'] / mw['C']
  suffix = ""
  #if chmmean: suffix = "_ensemblemean"
  if chmstd: suffix = "_ensemblespread"
  conversions += (
    ('ECO2', 'CO2_flux', convert_CO2_flux, None, 'g s-1'),
    ('ECBB', 'CO2_fire_flux', convert_CO2_flux, None, 'g s-1'),
    ('ECFF', 'CO2_fossil_flux', convert_CO2_flux, None, 'g s-1'),
    ('ECOC', 'CO2_ocean_flux', convert_CO2_flux, None, 'g s-1'),
    ('ECLA', 'CO2_bio_flux', convert_CO2_flux, None, 'g s-1'),
    ('CO2', 'CO2'+suffix, convert_CO2, None, 'ppm'),
    ('CBB', 'CO2_fire'+suffix, convert_CO2, None, 'ppm'),
    ('CFF', 'CO2_fossil'+suffix, convert_CO2, None, 'ppm'),
    ('COC', 'CO2_ocean'+suffix, convert_CO2, -100, 'ppm'),
    ('CLA', 'CO2_bio'+suffix, convert_CO2, -100, 'ppm'),
    ('CO2B', 'CO2_background'+suffix, convert_CO2, None, 'ppm'),
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

  # Add a water tracer, if we have humidity
  if 'specific_humidity' in data:
    q = data['specific_humidity']
    assert q.atts['units'] == 'kg kg-1'
    data['H2O'] = q / mw['H2O'] * mw['air'] * 1E6
    data['H2O'].atts['units'] = 'ppm'

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
    # Define air mass on the same domain as 3D pressure
    from common import Constant_Var
    data['air'] = Constant_Var(axes=P.axes, value=1.0E6)  # ppm

  if dP is not None:
    dP.atts['units'] = 'hPa'
    data['dp'] = dP  #TODO: better name?

  # Grid cell areas
  if 'DX' in data:
    data['cell_area'] = data.pop('DX')
    data['cell_area'].atts['units'] = 'm2'
  elif 'surface_pressure' in data:
    lat = data['surface_pressure'].lat
    lon = data['surface_pressure'].lon
    time = data['surface_pressure'].time
    from common import get_area
    data['cell_area'] = get_area(lat,lon).extend(0,time)


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

# Shortcuts functions with chmmean/chmstd flags set
def eccas_chmmean_products (dataset):
  return eccas_products(dataset, chmmean=True)
def eccas_chmstd_products (dataset):
  return eccas_products(dataset, chmstd=True)


# Wrapper for getting GEM data back out of a cached netcdf file
# (This will hook into the cache, to preserve FSTD axes after save/reloading)
def gem_load_cache_hook (dataset):
  from pygeode.formats.fstd import detect_fstd_axes
  data = list(dataset.vars)
  detect_fstd_axes(data)
  return data[0]


# Some useful criteria for searching for fields

def number_of_timesteps (varlist):
  from pygeode.axis import TAxis
  for var in varlist:
    if var.hasaxis(TAxis):
      return len(var.getaxis(TAxis))

def number_of_levels (varlist):
  from pygeode.axis import ZAxis
  for var in varlist:
    if var.hasaxis(ZAxis):
      return len(var.getaxis(ZAxis))


# GEM data interface
class GEM_Data (object):
  def __init__ (self, experiment_dir, flux_dir, name, title, tmpdir=None):
    from cache import Cache
    from data_interface import DataInterface
    from glob import glob

    indir = experiment_dir

    self.name = name
    self.title = title
    fallback_dirs = [tmpdir] if tmpdir is not None else []
    cache = Cache(dir = indir + "/nc_cache", fallback_dirs=fallback_dirs, global_prefix=name+"_", load_hook=gem_load_cache_hook)

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
    # Hack to read at least one model file, just to get the lat/lon
    # (fixes area emissions lat/lon mismatch with current emissions)
    eccas_opener(glob(indir+"/*[0-9]*_[0-9]*")[0])

    ##############################
    # Fluxes
    ##############################

    if flux_dir is not None:
      files.extend(glob(flux_dir+"/area_2009??????"))

    manifest = cache.full_path("manifest", writeable=True)

    # Ensemble mean data
    chmmean_files = [f for f in files if f.endswith('_chmmean')]
    chmmean_data = DataInterface.from_files(chmmean_files, opener=eccas_opener, manifest=manifest)
    # Apply the conversions & transformations
    chmmean_data = DataInterface(map(eccas_chmmean_products,chmmean_data))

    # Ensemble spread data
    chmstd_files = [f for f in files if f.endswith('_chmstd')]
    chmstd_data = DataInterface.from_files(chmstd_files, opener=eccas_opener, manifest=manifest)
    # Apply the conversions & transformations
    chmstd_data = DataInterface(map(eccas_chmstd_products,chmstd_data))

    # Area emissions
    flux_files = [f for f in files if '/area_' in f]
    flux_data = DataInterface.from_files(flux_files, opener=eccas_opener, manifest=manifest)
    # Apply the conversions & transformations
    flux_data = DataInterface(map(eccas_products,flux_data))

    # Forward model data
    forward_files = sorted(set(files)-set(chmmean_files)-set(chmstd_files)-set(flux_files))
    forward_data = DataInterface.from_files(forward_files, opener=eccas_opener, manifest=manifest)
    # Apply the conversions & transformations
    forward_data = DataInterface(map(eccas_products,forward_data))

    # Fix the area emissions data, to have the proper lat/lon
    lat = forward_data.datasets[0].lat
    lon = forward_data.datasets[0].lon
    flux_data = DataInterface(d.replace_axes(lat=lat,lon=lon) for d in flux_data)

    # Combine all datasets into a single unit
    self.data = DataInterface(chmmean_data.datasets+chmstd_data.datasets+flux_data.datasets+forward_data.datasets)

    self.cache = cache


  # The data interface
  # Handles the computing of general diagnostic domains (zonal means, etc.)
  def get_data (self, domain, standard_name):

    field = standard_name

    # Determine which data is needed

    # "total column" (in kg/m2)
    if domain == 'totalcolumn':
      from common import molecular_weight as mw, grav as g

      c, dp = self.data.find_best([field,'dp'], maximize=number_of_levels)
      # Convert from ppm to kg / kg
      c *= 1E-6 * mw[standard_name] / mw['air']

      # Integrate
      data = (c*dp*100).sum('zaxis') / g
      data.name = field
      data.atts['units'] = 'kg m-2'

    # Average column (ppm)
    elif domain == 'avgcolumn':

      c, dp = self.data.find_best([field,'dp'], maximize=number_of_levels)
      data = (c*dp).sum('zaxis') / dp.sum('zaxis')
      data.name = field
      if 'units' in c.atts:
        data.atts['units'] = c.atts['units']


    # Total mass (Pg)
    #TODO: re-use totalcolumn data from above
    elif domain == 'totalmass':
      from common import molecular_weight as mw, grav as g
      # Do we have the pressure change in the vertical?
      if self.data.have('dp'):
         c, dp, area = self.data.find_best([field,'dp','cell_area'], maximize=number_of_levels)
         # Convert from ppm to kg / kg
         c *= 1E-6 * mw[standard_name] / mw['air']

         # Integrate to get total column
         tc = (c*dp*100).sum('zaxis') / g

      # Otherwise, if we only need air mass, assume a lid of 0hPa and take a
      # shortcut
      elif field == 'air':
         from warnings import warn
         warn ("No 'dp' data found in '%s'.  Approximating total air mass from surface pressure"%self.name)
         p0, area = self.data.find_best(['surface_pressure','cell_area'], maximize=number_of_timesteps)
         tc = p0*100 / g
      else:
         raise KeyError("No 'dp' field found in '%s'.  Cannot compute total mass."%self.name)

      # Integrate horizontally
      # Assume global grid - remove repeated longitude
      mass = (tc * area).slice[:,:,:-1].sum('lat','lon')

      # Convert from kg to Pg
      mass *= 1E-12
      data = mass
      data.name = field
      data.atts['units'] = 'Pg'

    # Integrated flux (if available)
    elif domain == 'totalflux':
      from common import molecular_weight as mw

      data = self.data.find_best(field+'_flux', maximize=number_of_timesteps)

      # Sum, skipping the last (repeated) longitude
      data = data.slice[:,:,:-1].sum('lat','lon')
      # Convert from g/s to moles/s
      data /= mw[standard_name]
      data.name = field
      data.atts['units'] = 'mol s-1'

    elif domain == 'flux':
      from common import molecular_weight as mw
      data, area = self.data.find_best([field+'_flux','cell_area'])
      # Convert from g/s to moles/s
      data /= mw[standard_name]
      # Convert to moles/m2/s
      data = data.slice[:,:,:-1]  # remove repeated longitude
      if area.hasaxis('time'): area = area(i_time=0).squeeze()
      area = area.slice[:,:-1]  # remove repeated longitude
      data /= area
      data.name = field
      data.atts['units'] = 'mol m-2 s-1'

    elif domain == 'Toronto':
      data = self.data.find_best(field, maximize=number_of_levels)
      data = data.squeeze(lat=43.7833,lon=280.5333)
      data.name = field
      data.atts['units'] = 'ppm'

    else: raise ValueError ("Unknown domain '%s'"%domain)

    prefix = '%s_%s'%(domain,field)
    return self.cache.write(data,prefix)


