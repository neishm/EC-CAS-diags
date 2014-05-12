# Interface for CarbonTracker data

# Invariant data
import numpy as np
A_interface = [0., 6.575628, 336.772369, 1297.656128, 3010.146973, 5422.802734, 8356.252930000001, 11543.166992, 14665.645508, 17385.595703, 19348.775391, 20319.011719, 20348.916016, 19919.796875, 19184.544922, 18191.029297, 16990.623047, 15638.053711, 14192.009766, 12713.897461, 11262.484375, 9873.560546999999, 8564.624023, 7341.469727, 6199.839355, 4663.776367, 3358.425781, 2292.155518, 1463.16394, 857.945801, 450.685791, 204.637451, 76.16765599999999, 21.413612, 0.]
A_interface = np.array(A_interface)

B_interface = [1., 0.994204, 0.9734660000000001, 0.935157, 0.875518, 0.795385, 0.698224, 0.589317, 0.475016, 0.362203, 0.259554, 0.176091, 0.112979, 0.080777, 0.055474, 0.036227, 0.022189, 0.012508, 0.006322, 0.002765, 0.001, 0.000279, 5.5e-05, 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
B_interface = np.array(B_interface)



# Helper methods

def ct_opener (filename):
  from pygeode.formats import netcdf
  from pygeode.axis import ZAxis

  data = netcdf.open(filename)
  data = data - 'date_components' - 'decimal_date'

  # Force vertical axis to be a ZAxis
  data = data.replace_axes(level = ZAxis)

  # Convert to a dictionary (for referencing by variable name)
  data = dict((var.name,var) for var in data)

  # Convert some standard quantities
  # (old_name, new_name, scale, offset, units)
  conversions = (
    ('bg', 'CO2_background', None, None, 'ppm'),
    ('ff', 'CO2_fossil', None, None, 'ppm'),
    ('bio', 'CO2_bio', None, None, 'ppm'),
    ('ocean', 'CO2_ocean', None, None, 'ppm'),
    ('fires', 'CO2_fire', None, None, 'ppm'),
    ('fossil_imp', 'CO2_fossil_flux', None, None, 'mol m-2 s-1'),
    ('bio_flux_opt', 'CO2_bio_flux', None, None, 'mol m-2 s-1'),
    ('ocn_flux_opt', 'CO2_ocean_flux', None, None, 'mol m-2 s-1'),
    ('fire_flux_imp', 'CO2_fire_flux', None, None, 'mol m-2 s-1'),
    ('press', 'air_pressure', 1E-2, None, 'hPa'),
    ('gph', 'geopotential_height', None, None, 'm'),
  )

  # Do the conversions
  for old_name, new_name, scale, offset, units in conversions:
    if old_name in data:
      var = data.pop(old_name)
      if scale is not None: var *= scale
      if offset is not None: var += offset
      if units is not None: var.atts['units'] = units
      data[new_name] = var

  # Find the total CO2 (sum of components)
  if 'CO2_background' in data:
    data['CO2'] = data['CO2_background'] + data['CO2_fossil'] + data['CO2_bio'] + data['CO2_ocean'] + data['CO2_fire']

  # Create a total flux product
  if 'CO2_fire_flux' in data:
    data['CO2_flux'] = data['CO2_fossil_flux'] + data['CO2_bio_flux'] + data['CO2_ocean_flux'] + data['CO2_fire_flux']

  # Other (more heavily derived) products

  if 'air_pressure' in data:
    # Surface pressure
    # Get pressure at the bottom mid-level
    pmid = data['air_pressure'].squeeze(level=1) * 100.

    # Compute surface pressure from this
    # p1 = A1 + B1*Ps
    # pmid = (ps + A1 + B1*Ps) / 2 = Ps(1+B1)/2 + (0+A1)/2
    # Ps = (2*pmid - A1)/(1+B1)
    P0 = (2*pmid - A_interface[1])/(B_interface[1]+1)
    data['surface_pressure'] = P0 / 100.

    # Vertical change in pressure
    #NOTE: generated from A/B interface values, not the 3D pressure field.
    #      3D pressure is used only to define the vertical levels.
    import numpy as np
    from pygeode.var import Var
    dA = -np.diff(A_interface)
    dA = Var([data['air_pressure'].level], values=dA)
    dB = -np.diff(B_interface)
    dB = Var([data['air_pressure'].level], values=dB)
    dp = dA/100. + dB * data['surface_pressure']
    dp = dp.transpose('time','zaxis','lat','lon')
    dp.units = 'hPa'
    data['dp'] = dp

    # Air mixing ratio (constant)
    from common import Constant_Var
    # (ppm)
    data['air'] = Constant_Var(axes=data['air_pressure'].axes, value=1.0E6)

  # Compute grid cell area
  # NOTE: will be different for fluxes and 3D mole fractions
  from common import get_area
  if 'CO2' in data:
    x = data['CO2'].squeeze(level=1)
  else:
    x = data['CO2_flux']
  data['cell_area'] = get_area(x.lat, x.lon).extend(0,x.time)
  data['cell_area'].atts['units'] = 'm2'


  # General cleanup stuff

  # Make sure the variables have the appropriate names
  for name, var in data.iteritems():  var.name = name

  # Convert to a list
  data = list(data.values())

  return data


# Method for calculating zonal mean on-the-fly
def ct_zonal (field):
  from pygeode.climat import dailymean
  import numpy as np

  # Interpolate to geopotential height
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  height = Height(range(68))
  ct_co2 = interpolate(field, inaxis='level', outaxis=height, inx = molefractions.gph/1000)
  ct_co2 = ct_co2.nanmean('lon')
  ct_co2 = ct_co2.transpose(0,2,1)
  ct_co2 = dailymean(ct_co2)

  return ct_co2

# Similar to above, but use an average of the 22:30 and 1:30 to get
# a 00:00 field
def ct_zonal_24h (field,gph):
  import numpy as np

  # Interpolate to geopotential height
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  height = Height(range(68))
  ct_co2 = interpolate(field, inaxis='level', outaxis=height, inx = gph/1000)
  ct_co2 = ct_co2.nanmean('lon')
  ct_co2 = ct_co2.transpose(0,2,1)

  co2_2230 = ct_co2(hour=22,minute=30)(i_time = (0,364))

  co2_0130 = ct_co2(hour=1, minute=30)(i_time = (1,365))

  # New time axis
  from pygeode.timeaxis import StandardTime
  taxis = ct_co2.time
  taxis = StandardTime((co2_2230.time.values+co2_0130.time.values)/2, startdate=taxis.startdate, units=taxis.units)
  co2_2230 = co2_2230.replace_axes(time=taxis)
  co2_0130 = co2_0130.replace_axes(time=taxis)

  ct_co2 = ((co2_2230 + co2_0130)/2).rename(ct_co2.name)

  return ct_co2


# Some useful criteria for searching for fields
def have_surface (varlist):
  from pygeode.axis import ZAxis
  from pygeode.formats.fstd import Hybrid, LogHybrid
  for var in varlist:
    if var.hasaxis('level'):
      return 1 in var.level.values
  # No vertical info?
  return False

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

    # Higher-level information about the data
    self.name = 'CT2010'
    self.title = 'CarbonTracker'

    cachedir = '/wrk1/EC-CAS/CarbonTracker/nc_cache'
    fallback_dirs = [tmpdir] if tmpdir is not None else []
    self.cache = Cache (dir=cachedir, fallback_dirs=fallback_dirs, global_prefix=self.name+'_')

    molefractions = "/wrk1/EC-CAS/CarbonTracker/molefractions/CT2010.molefrac_glb3x2_????-??-??.nc"
    fluxes = "/wrk1/EC-CAS/CarbonTracker/fluxes/CT2010.flux1x1.????????.nc"

    manifest = self.cache.full_path("manifest", writeable=True)
    self.data = DataInterface ([molefractions,fluxes], opener=ct_opener, manifest=manifest)


  # Data interface
  def get_data (self, domain, field, stat='mean'):

    if stat != 'mean':
      raise KeyError("No '%s' stat available for CarbonTracker"%stat)

    # Zonal mean (over geopotential height)
    if domain == 'zonalmean_gph':
      data, gph = self.data.find_best([field,'geopotential_height'], maximize=number_of_levels)
      data = ct_zonal_24h(data,gph)
      data.atts['units'] = 'ppm'

    # "surface" data (lowest level of molefractions dataset)
    elif domain == 'sfc':
      data = self.data.find_best(field, requirement=have_surface, maximize=number_of_timesteps)
      data = data(level=1)

    # Total column
    elif domain == 'totalcolumn':
      from common import molecular_weight as mw, grav as g

      c, dp = self.data.find_best([field,'dp'], maximize=number_of_levels)
      # Convert from ppm to kg / kg
      c *= 1E-6 * mw[field] / mw['air']

      # Integrate
      data = (c*dp*100).sum('zaxis') / g
      data.name = field
      data.atts['units'] = 'kg m-2'


    # Column averages
    elif domain == 'avgcolumn':
      from common import molecular_weight as mw
      tc = self.get_data('totalcolumn', field)
      tc_air = self.get_data('totalcolumn','air')
      data = tc / tc_air
      # Convert kg/kg to ppm
      data *= mw['air']/mw[field] * 1E6

      data.name = field
      data.atts['units'] = 'ppm'

    # Total mass
    elif domain == 'totalmass':
      from common import molecular_weight as mw, grav as g
      c, dp, area = self.data.find_best([field,'dp','cell_area'], maximize=number_of_levels)
      # Convert from ppm to kg / kg
      c *= 1E-6 * mw[field] / mw['air']

      # Integrate to get total column
      tc = (c*dp*100).sum('zaxis') / g

      # Integrate horizontally
      mass = (tc * area).sum('lat','lon')

      # Convert from kg to Pg
      mass *= 1E-12
      data = mass
      data.name = field
      data.atts['units'] = 'Pg'


    # Integrated fluxes (moles s-1)
    elif domain == 'totalflux':
      data, area = self.data.find_best([field+'_flux','cell_area'], maximize=number_of_timesteps)
      data = (data*area).sum('lat','lon')
      data.name = field
      data.atts['units'] = 'mol s-1'
      # The time is the *midpoint* of the flux period.
      # Rewind to the *start* of the flux period (-1.5 hours)
      time = data.time
      assert time.units == 'days'
      time = time.__class__(values=time.values - 0.0625, units='days', startdate=time.startdate)
      data = data.replace_axes(time=time)

    elif domain == 'flux':
      data = self.fluxes[field]
      # The time is the *midpoint* of the flux period.
      # Rewind to the *start* of the flux period (-1.5 hours)
      time = data.time
      assert time.units == 'days'
      time = time.__class__(values=time.values - 0.0625, units='days', startdate=time.startdate)
      data = data.replace_axes(time=time)
      return data   # No caching

    else: raise ValueError ("Unknown domain '%s'"%domain)

    units = data.atts.get('units',None)
    data = self.cache.write(data,prefix='%s_%s'%(domain,field))
    return data

