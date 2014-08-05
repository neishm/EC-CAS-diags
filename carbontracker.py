# Interface for CarbonTracker data

# Invariant data
import numpy as np
A_interface = [0., 6.575628, 336.772369, 1297.656128, 3010.146973, 5422.802734, 8356.252930000001, 11543.166992, 14665.645508, 17385.595703, 19348.775391, 20319.011719, 20348.916016, 19919.796875, 19184.544922, 18191.029297, 16990.623047, 15638.053711, 14192.009766, 12713.897461, 11262.484375, 9873.560546999999, 8564.624023, 7341.469727, 6199.839355, 4663.776367, 3358.425781, 2292.155518, 1463.16394, 857.945801, 450.685791, 204.637451, 76.16765599999999, 21.413612, 0.]
A_interface = np.array(A_interface)

B_interface = [1., 0.994204, 0.9734660000000001, 0.935157, 0.875518, 0.795385, 0.698224, 0.589317, 0.475016, 0.362203, 0.259554, 0.176091, 0.112979, 0.080777, 0.055474, 0.036227, 0.022189, 0.012508, 0.006322, 0.002765, 0.001, 0.000279, 5.5e-05, 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
B_interface = np.array(B_interface)



# Helper methods

def ct_products (data):
  from pygeode.axis import ZAxis

  # Don't worry about the date_components and decimal_date domain?
  # (Doesn't have any CO2-related variables).
  varnames = [v.name for v in data]
  if 'bio' not in varnames and 'bio_flux_opt' not in varnames: return data

  # Force vertical axis to be a ZAxis
  data = data.replace_axes(level = ZAxis)

  # Convert to a dictionary (for referencing by variable name)
  data = dict((var.name,var) for var in data)

  # Convert some standard quantities
  # (old_name, new_name, scale, offset, units)
  conversions = (
    ('bg', 'CO2_background', 'ppm(CO2)'),
    ('ff', 'CO2_fossil', 'ppm(CO2)'),
    ('bio', 'CO2_bio', 'ppm(CO2)'),
    ('ocean', 'CO2_ocean', 'ppm(CO2)'),
    ('fires', 'CO2_fire', 'ppm(CO2)'),
    ('fossil_imp', 'CO2_fossil_flux', 'mol(CO2) m-2 s-1'),
    ('bio_flux_opt', 'CO2_bio_flux', 'mol(CO2) m-2 s-1'),
    ('ocn_flux_opt', 'CO2_ocean_flux', 'mol(CO2) m-2 s-1'),
    ('fire_flux_imp', 'CO2_fire_flux', 'mol(CO2) m-2 s-1'),
    ('press', 'air_pressure', 'Pa'),
    ('gph', 'geopotential_height', 'm'),
  )

  # Do the conversions
  for old_name, new_name, units in conversions:
    if old_name in data:
      var = data.pop(old_name)
      var.atts['units'] = units
      data[new_name] = var

  # Find the total CO2 (sum of components)
  if 'CO2_background' in data:
    data['CO2'] = data['CO2_background'] + data['CO2_fossil'] + data['CO2_bio'] + data['CO2_ocean'] + data['CO2_fire']
    data['CO2'].atts['units'] = data['CO2_background'].atts['units']

  # Create a total flux product
  if 'CO2_fire_flux' in data:
    data['CO2_flux'] = data['CO2_fossil_flux'] + data['CO2_bio_flux'] + data['CO2_ocean_flux'] + data['CO2_fire_flux']
    data['CO2_flux'].atts['units'] = data['CO2_fire_flux'].atts['units']

  # Fudge the tmie axis for all flux products.
  for varname in data:
    if varname.endswith('_flux'):
      # The time is the *midpoint* of the flux period.
      # Rewind to the *start* of the flux period (-1.5 hours)
      var = data[varname]
      time = var.time
      assert time.units == 'days'
      time = time.__class__(values=time.values - 0.0625, units='days', startdate=time.startdate)
      var = var.replace_axes(time=time)
      data[varname] = var


  # Other (more heavily derived) products

  if 'air_pressure' in data:
    # Surface pressure
    # Get pressure at the bottom mid-level
    pmid = data['air_pressure'].squeeze(level=1)

    # Compute surface pressure from this
    # p1 = A1 + B1*Ps
    # pmid = (ps + A1 + B1*Ps) / 2 = Ps(1+B1)/2 + (0+A1)/2
    # Ps = (2*pmid - A1)/(1+B1)
    P0 = (2*pmid - A_interface[1])/(B_interface[1]+1)
    P0.atts['units'] = 'Pa'
    data['surface_pressure'] = P0

    # Vertical change in pressure
    #NOTE: generated from A/B interface values, not the 3D pressure field.
    #      3D pressure is used only to define the vertical levels.
    import numpy as np
    from pygeode.var import Var
    dA = -np.diff(A_interface)
    dA = Var([data['air_pressure'].level], values=dA)
    dB = -np.diff(B_interface)
    dB = Var([data['air_pressure'].level], values=dB)
    dp = dA + dB * data['surface_pressure']
    dp = dp.transpose('time','zaxis','lat','lon')
    dp.atts['units'] = 'Pa'
    data['dp'] = dp


  # Compute grid cell area
  # NOTE: will be different for fluxes and 3D mole fractions
  from common import get_area
  if 'CO2' in data:
    x = data['CO2'].squeeze(level=1)
  else:
    x = data['CO2_flux']
  data['cell_area'] = get_area(x.lat, x.lon).extend(0,x.time)


  # General cleanup stuff

  # Make sure the variables have the appropriate names
  for name, var in data.iteritems():  var.name = name

  # Convert to a list
  data = list(data.values())

  return data




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



# Define the data interface for CarbonTracker

class CarbonTracker_Data (object):

  def __init__ (self, tmpdir=None):

    from cache import Cache
    from data_interface import DataInterface
    from glob import glob
    from pygeode.formats import netcdf

    # Higher-level information about the data
    self.name = 'CT2010'
    self.title = 'CarbonTracker'

    cachedir = '/wrk1/EC-CAS/CarbonTracker/nc_cache'
    fallback_dirs = [tmpdir] if tmpdir is not None else []
    self.cache = Cache (dir=cachedir, fallback_dirs=fallback_dirs, global_prefix=self.name+'_')

    molefractions = glob("/wrk1/EC-CAS/CarbonTracker/molefractions/CT2010.molefrac_glb3x2_????-??-??.nc")
    fluxes = glob("/wrk1/EC-CAS/CarbonTracker/fluxes/CT2010.flux1x1.????????.nc")

    manifest = self.cache.full_path("manifest", writeable=True)
    self.data = DataInterface.from_files (molefractions+fluxes, opener=netcdf.open, manifest=manifest)

    self.data = DataInterface(map(ct_products,self.data))

