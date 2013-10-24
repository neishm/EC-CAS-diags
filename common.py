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


# A Station axis.
# Each station is a entry along this dimension.
# Latitude and longitude are provided as auxilary arrays.
from pygeode.axis import Axis
class Station (Axis):
  name = 'station'
  def _val2str(self, val):  return val  # Value is already a string
del Axis

# Hook for encoding to a file
# Roughly follows CF Metadata conventions for station data
# http://cf-pcmdi.llnl.gov/documents/cf-conventions/1.6/aphs02.html
def station_axis_save_hook (var):
  from pygeode.dataset import asdataset, Dataset
  import numpy as np
  from pygeode.var import Var
  from pygeode.axis import Axis
  from copy import copy

  if not var.hasaxis('station'): return asdataset(var)

  var = copy(var)  # Shallow copy (so we can muck with the metadata)
  var.atts = dict(var.atts)

  # Consruct a generic 'station' axis (with a simple integer dimension)
  station = Axis(name='station', values=np.arange(len(var.station), dtype='int32'))

  # Get the lat/lon coordinates on this generic axis
  coordinates = [Var(axes=[station], values=val, name=name) for name,val in var.station.auxarrays.items()]
  var.atts['coordinates'] = ' '.join(c.name for c in coordinates)

  # Construct a 2D character array to hold station names
  name_strlen = max(len(station_name) for station_name in var.station.values)
  #TODO: make this a simple dimension (no coordinate values needed!)
  name_strlen = Axis (values=np.arange(name_strlen, dtype='int32'), name='name_strlen')
  dtype = '|S'+str(len(name_strlen))  # For a convenient view on the character array
                                      # (to help popluate it from strings)

  station_name = np.zeros([len(station), len(name_strlen)], dtype='|S1')
  station_name.view(dtype)[:,0] = var.station.values[:]
  station_name = Var([station,name_strlen], values=station_name, name='station_name')

  # Replace the station axis in the var (with the simple one created here)
  var = var.replace_axes(station=station)

  # Return everything needed to recreate the Station coordinate
  return Dataset([var, station_name]+coordinates)

#TODO: Create a special PyGeode axis class that will write only a dimension
# entry, no other metadata (BareDimension?)

# Hook for decoding a Station axis from a file.
# Reconstructs the information from a station_axis_save_hook() call.
def station_axis_load_hook (dataset):
  from copy import copy

  # If there is no station axis, then nothing to do.
  if not any(v.hasaxis('station') for v in dataset.vars):
    return dataset.vars[0]

  # Find the actual variable (the only thing with a 'coordinates' attribute
  var = [v for v in dataset if 'coordinates' in v.atts][0]

  # Make a shallow copy of the var (to edit the metadata in-place)
  var = copy(var)
  var.atts = dict(var.atts)

  # Find all the coordinates
  coordinates = {}
  for c in var.atts['coordinates'].split():
    coordinates[c] = dataset[c].get()
  del var.atts['coordinates']

  # Convert the 2D character array to a 1D string array
  station_name = dataset.station_name
  station_name = [''.join(s) for s in station_name.get()]
  station = Station(values=station_name, **coordinates)

  # Replace the station axis
  var = var.replace_axes(station=station)

  return var

