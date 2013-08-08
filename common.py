# Functions / constants common to multiple modules

# Molecular weights
molecular_weight = {'CO2':44.01, 'CH4':16.04, 'C':12., 'air':28.97}

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

