# Functions / constants common to multiple modules

# Molecular weights
molecular_weight = {'CO2':44.01, 'CH4':16.04, 'C':12., 'air':28.97, 'CO2_background':44.01, 'CO2_bio':44.01, 'CO2_ocean':44.01, 'CO2_fossil':44.01, 'CO2_fire':44.01, 'H2O':18.01528}

# Unit conversion
unit_scale = {'ppm':1E6, 'ppb':1E9}

grav = .980616e+1  # Taken from GEM-MACH file chm_consphychm_mod.ftn90

# Normalize the time axes to the same start date / units
def fix_timeaxis (data):
  from pygeode.timeaxis import StandardTime
  startdate = dict(year=2009, month=1, day=1)
  time = data.time
  time = StandardTime(units='days', startdate=startdate, **time.auxarrays)
  data = data.replace_axes(time=time)
  return data

# Convert a string to an int or float, if possible.  (Otherwise, keep it as a string)
def best_type (x):
  try: return int(x)
  except ValueError: pass
  try: return float(x)
  except ValueError:pass
  return x

# Put all variables on a common (and regularly spaced) time axis
# Also, filter out bad values
def common_taxis (*invars):
  import numpy as np
  from pygeode.timeaxis import StandardTime
  from pygeode import Var
  newvars = []
  startdate=dict(year=1950)  # arbitrary (but consistent) start date
  oldtimes = [var.time.reltime(units='hours',startdate=startdate) for var in invars]
  firsttime = min(times[0] for times in oldtimes)
  lasttime = max(times[-1] for times in oldtimes)
  newtimes = np.arange(firsttime, lasttime+1)
  taxis = StandardTime (values = newtimes, units='hours', startdate=startdate)
  # Adjust to a better start date
  taxis = StandardTime (units='hours', **taxis.auxarrays)
  for i in range(len(invars)):
    newvals = np.zeros(len(newtimes), dtype=invars[i].dtype)
    if newvals.dtype.name.startswith('float'):
      blank = float('nan')
    else:
      blank = 0
    newvals[:] = blank
    ind = np.searchsorted(newtimes, oldtimes[i])
    newvals[ind] = invars[i].get()
    newvals[np.where(newvals > 1e8)] = blank
    newvars.append(Var([taxis], values=newvals, name=invars[i].name, atts=invars[i].atts))

  return newvars


# Limit the vars to the region where they all overlap.
# Assuming the axes need to match on type only.
# NOTE: an exact match is required here - no error tolerance.
# NOTE: also assuming the values define the axis - will need to ensure things like time axis have the same start date, units before calling this method.
def overlapping (*varlist):
  from warnings import warn
  from pygeode.view import simplify

  # Get an initial set of axes
  axes = dict([a.__class__, a.values] for v in varlist for a in v.axes)

  # We need the axes to have unique values, or the mapping is ill defined.
  for axis_class in axes.keys():
    for var in varlist:
      if var.hasaxis(axis_class):
        values = var.getaxis(axis_class).values
        if len(set(values)) != len(values):
          warn ("non-unique '%s' axis found - cannot define a unique mapping between vars.  Ignoring this axis."%axis_class.__name__)
          del axes[axis_class]
          break

  # Reduce the axes to the common overlap
  for var in varlist:
    for a in var.axes:
      axis_class = a.__class__
      #TODO

  return varlist

# Adjust a lat/lon grid from -180,180 to 0,360
def rotate_grid (data):
  from pygeode.var import concat
  east = data(lon=(-180,0))
  west = data(lon=(0,180))

  oldlons = east.lon
  newlons = type(oldlons)(oldlons.values + 360)
  east = east.replace_axes(lon=newlons)

  return concat(west, east)

# Compute grid cell areas (how GEM does it)
def get_area (latvar, lonvar):

  import numpy as np
  from pygeode.var import Var
  from math import pi
  r = .637122e7  # Taken from consphy.cdk
  lats = latvar.values * (pi / 180)
  # Get the boundaries of the latitudes
  lat_bounds = (lats[:-1] + lats[1:]) * 0.5
  # Including the poles
  lat_bounds = np.concatenate([[-pi/2], lat_bounds, [pi/2]])
  # Length in y direction
  dlat = np.diff(lat_bounds)
  # Length in x direction (assuming global grid)
  lons = lonvar.values * (pi/180)
  # Assume global & equidistant longitudes
  dlon = lons[1] - lons[0]
  dlon = np.repeat(dlon, len(lons))

  dlat = dlat.reshape(-1,1)
  dlon = dlon.reshape(1,-1)
  clat = np.cos(lats).reshape(-1,1)
  dxdy = r*r * clat * dlat * dlon
  dxdy = np.asarray(dxdy, dtype='float32')
  dxdy = Var([latvar, lonvar], values=dxdy, name='DX')

  return dxdy


# Return a field of constant value over the given axes
from pygeode.var import Var
class Constant_Var (Var):
  def __init__ (self, value, *args, **kwargs):
    from pygeode.var import Var
    import numpy as np
    kwargs['dtype'] = np.array(value).dtype
    Var.__init__ (self, *args, **kwargs)
    self.value = value

  def getview (self, view, pbar):
    import numpy as np
    out = np.empty(view.shape, dtype=self.dtype)
    out[()] = self.value
    pbar.update(100)
    return out
del Var



# Flatten out a variable that has both a date-of-origin axis and a forecast
# axis.  Combine into a date-of-validity axis.
from pygeode.var import Var
class SquashForecasts(Var):
  def __init__ (self, var):
    from pygeode.var import Var, copy_meta
    from pygeode.timeutils import reltime
    origin_hours = reltime(var.time, units='hours').reshape([-1,1])
    forecast_hours = var.forecast.values.reshape([1,-1])
    validity_hours = origin_hours + forecast_hours
    # Construct new time axis
    time = type(var.time)(validity_hours.flatten(), units='hours', startdate = var.time.startdate)
    # Re-construct in the original units
    time = type(var.time)(startdate=var.time.startdate, units=var.time.units, **time.auxarrays)
    axes = [time]+[a for a in var.axes if a is not var.time and a is not var.forecast]
    Var.__init__(self, axes, dtype=var.dtype)
    copy_meta(var, self)
    self._var = var

  def getview (self, view, pbar):
    import numpy as np
    out = np.empty(view.shape, dtype=self.dtype)
    nt = len(self._var.time)
    nf = len(self._var.forecast)
    t = self.whichaxis('time')
    v = view.map_to(self._var, strict=False)
    for out_itime, in_itime in enumerate(view.integer_indices[t]):
      out[out_itime,...] = v.modify_slice(0,[in_itime//nf]).modify_slice(1,[in_itime%nf]).get(self._var)
      pbar.update(out_itime*100./len(view.integer_indices[t]))
    pbar.update(100)
    return out

del Var
def squash_forecasts(var):
  from pygeode.dataset import Dataset
  from pygeode.var import Var
  if not var.hasaxis('forecast'): return var
  if isinstance(var,Dataset):
    return Dataset(map(squash_forecasts,var), atts=var.atts)
  assert isinstance(var,Var), "Unhandled case '%s'"%type(var)
  return SquashForecasts(var)


# Get a keyword / value that can be used to select a surface level for the
# givem vertical axis.
from pygeode.axis import Pres, Hybrid
from pygeode.formats.fstd import LogHybrid
surface_values = {Pres:1000., Hybrid:1.0, LogHybrid:1.0}
surface_direction = {Pres:+1, Hybrid:+1, LogHybrid:+1}
del Pres, Hybrid, LogHybrid

# Find a surface value (or the closest level to the surface)
def select_surface (var):
  from pygeode.axis import ZAxis
  if not var.hasaxis(ZAxis): return var
  zaxis = var.getaxis(ZAxis)
  zaxis_type = type(zaxis)
  sfc_val = surface_values[zaxis_type]
  selection = dict([(zaxis.name,sfc_val)])
  return var(**selection)


# Criteria for ranking how close a dataset is to the surface
# (higher value is closer)
# To be used in the find_best() method.
def closeness_to_surface (varlist):
  from pygeode.axis import ZAxis
  for var in varlist:
    if var.hasaxis(ZAxis):
      zaxis = var.getaxis(ZAxis)
      return max(var.getaxis(ZAxis).values * surface_direction[type(zaxis)])

# Rank a dataset based on the number of timesteps available.
# To be used in the find_best() method.
def number_of_timesteps (varlist):
  from pygeode.axis import TAxis
  for var in varlist:
    if var.hasaxis(TAxis):
      return len(var.getaxis(TAxis))

# Rank a dataset based on the number of levels available.
# To be used in the find_best() method.
def number_of_levels (varlist):
  from pygeode.axis import ZAxis
  for var in varlist:
    if var.hasaxis(ZAxis):
      return len(var.getaxis(ZAxis))

# Check if we have data on a lat/lon grid.
# To be used in the find_best() method.
def have_gridded_data (varlist):
  from pygeode.axis import Lat, Lon
  for var in varlist:
    if var.hasaxis(Lat) and var.hasaxis(Lon): return True
  return False


