# Functions / constants common to multiple modules

# Unit conversion
from units import define_conversion, define_unit, conversion_factor

# Define the molar masses
define_conversion ('mol(CO2)', '44.01 g(CO2)')
define_conversion ('mol(CH4)', '16.04 g(CH4)')
define_conversion ('mol(dry_air)', '28.97 g(dry_air)')
define_conversion ('mol(H2O)', '18.01528 g(H2O)')

# The following is a hack to get mass in terms of carbon atoms
# I.e. to allow converting mass to Pg(C)
define_unit ('C_atoms_per_molecule', 'Carbon atoms in the molecule')
define_conversion ('g(C)', repr(1/12.01) + 'C_atoms_per_molecule mol')
define_conversion ('C_atoms_per_molecule(CO2)', '1')
define_conversion ('C_atoms_per_molecule(CH4)', '1')

# For the purpose of these diagnostics, assume mole fractions are always with
# respect to air.
define_conversion ('molefraction', 'mol mol(dry_air)-1')


# Convert a variable from one unit to another
def convert (var, units, context=None):
  if 'units' not in var.atts:
    raise ValueError ("Variable '%s' has no units defined, can't do unit conversion!"%var.name)
  if var.atts['units'] == units: return var  # No conversion necessary
  name = var.name
  if context is None:  context = var.atts.get('specie') or var.name
  scale = conversion_factor (var.atts['units'], units, context)
  var = var * scale
  var.atts['units'] = units
  var.name = name
  # Extra parameters from the cache interface
  if 'low' in var.atts: var.atts['low'] *= scale
  if 'high' in var.atts: var.atts['high'] *= scale
  return var

# Helper methods to determine if something is of a particular kind of unit.
def can_convert (var, units):
  try:
    convert (var, units)
    return True
  except ValueError: return False

def is_mixing_ratio (var):
  return can_convert (var, 'molefraction')

def is_concentration (var):
  return can_convert (var, 'mol m-3')

def is_mass_flux (var):
  return can_convert (var, 'mol m-2 s-1')

def is_integrated_mass_flux (var):
  return can_convert (var, 'mol s-1')


grav = .980616e+1  # Taken from GEM-MACH file chm_consphychm_mod.ftn90

# Normalize the time axes to the same start date / units
def fix_timeaxis (data):
  from pygeode.timeaxis import StandardTime
  if not hasattr(data,'time'): return data  # No time axis found?
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
  from pygeode.timeutils import reltime
  from pygeode import Var
  newvars = []
  startdate=dict(year=1950)  # arbitrary (but consistent) start date
  oldtimes = [reltime(var.time,units='hours',startdate=startdate) for var in invars]
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


# Find overlapping time axis between two variables
def same_times (*varlist):
  # Use the same start date (so relative values are comparable)
  varlist = map(fix_timeaxis,varlist)
  # Get a common set of time values
  times = [set(var.time.values) for var in varlist]
  times = reduce(set.intersection,times,times[0])
  times = sorted(times)
  if len(times) == 0:
    raise ValueError ("No overlapping timesteps found for %s"%(",".join(v.name for v in varlist)))
  return [var(l_time=times) for var in varlist]

# Grab the first available timestep of a variable, and remove the time info.
def first_timestep (var):
  if var.hasaxis('time'):
    var = var(i_time = 0)
    var = var.squeeze('time')
  # Strip out forecast info too?
  if var.hasaxis('forecast'):
    var = var(i_forecast = 0)
    var = var.squeeze('forecast')
  return var

# Adjust a lat/lon grid from -180,180 to 0,360
def rotate_grid (data):
  from pygeode.axis import Lon
  import numpy as np
  if not data.hasaxis('lon'): return data
  lon = np.array(data.getaxis('lon').values)
  # Check if already rotated
  if lon[1] > 0: return data
  lon[lon<0] += 360.
  lon = Lon(lon)
  data = data.replace_axes(lon=lon)
  # Re-sort the data
  return data.sorted('lon')

# Make sure the latitudes are monotonically increasing
def increasing_latitudes (data):
  if not data.hasaxis('lat'): return data

  # Check if already increasing
  lat = data.getaxis('lat')
  if lat.values[1] > lat.values[0]: return data

  slices = [slice(None)] * data.naxes
  slices[data.whichaxis('lat')] = slice(None,None,-1)
  data = data.slice[slices]
  return data

# Check if we have a repeated longitude (wraps around)
def have_repeated_longitude (data):
  import numpy as np
  if not data.hasaxis('lon'): return False
  v1 = data.lon.values[0]
  v2 = data.lon.values[-1]
  if np.allclose((v2-v1)%360, 0.):
    return True
  return False

# Remove repeated longitude from global data
def remove_repeated_longitude (data):
  if have_repeated_longitude(data):
    slices = [slice(None)]*data.naxes
    slices[data.whichaxis('lon')] = slice(0,len(data.lon)-1)
    data = data.slice[slices]
  return data

# Add an extra longitude for global data
def add_repeated_longitude (data):
  from pygeode.axis import Lon
  import numpy as np
  import warnings
  if not data.hasaxis('lon'): return data
  # Check if we already have a repeated longitude
  if have_repeated_longitude(data): return data
  # Otherwise, add it in as an extra array index
  lon = np.array(data.getaxis('lon').values)
  lon_indices = range(len(lon)) + [0]
  slices = [slice(None)]*data.naxes
  slices[data.whichaxis('lon')] = lon_indices
  # Temporarily disable warning about divide by zero, triggered because we
  # are repeated an axis value, which screws up the code for computing a
  # default relative tolerance
  #TODO: refactor this routine to avoid this trick.
  with warnings.catch_warnings():
    warnings.filterwarnings("ignore", "divide by zero")
    data = data.slice[slices]
  # Construct a new longitude axis with the repeated longitude
  lon = lon[lon_indices]
  lon[-1] += 360.
  lon = Lon(lon)
  data = data.replace_axes(lon=lon)
  return data


# Compute grid cell areas
# If flat is True, then use a 'flattened' surface for latitude weighting.
# E.g., use approximation cos(lat_center)*(lat_upper-lat_lower)
# The default is to use  sin(lat_upper) - sin(lat_lower)
def get_area (latvar, lonvar, flat=False):

  import numpy as np
  from pygeode.var import Var
  from math import pi
  r = .637122e7  # Taken from consphy.cdk
  lats = latvar.values * (pi / 180)
  # Get the boundaries of the latitudes
  lat_bounds = (lats[:-1] + lats[1:]) * 0.5
  # Including the poles
  lat_bounds = np.concatenate([[-pi/2], lat_bounds, [pi/2]])
  # Get the boundaries of the longitudes.
  # Assume the longitudes are equally spaced and monotonically increasing.
  lons = lonvar.values * (pi / 180)
  lon_bounds = np.empty([len(lons)+1], dtype=lons.dtype)
  lon_bounds[1:-1] = (lons[0:-1] + lons[1:]) / 2
  lon_bounds[0] = lon_bounds[1] - (lon_bounds[2] - lon_bounds[1])
  lon_bounds[-1] = lon_bounds[-2] + (lon_bounds[-2] - lon_bounds[-3])

  # Length in y direction
  dlat = abs(np.diff(lat_bounds))
  dlat = dlat.reshape([-1,1])
  # Length in x direction
  dlon = abs(np.diff(lon_bounds))
  dlon = dlon.reshape([1,-1])

  # Define some trig functions on latitude.
  clat = np.cos(lats).reshape([-1,1])
  dsinlat = abs(np.diff(np.sin(lat_bounds)))
  dsinlat = dsinlat.reshape([-1,1])

  if flat is True:
    dxdy = r*r * clat * dlat * dlon
  else:
    dxdy = r*r * dsinlat * dlon

  dxdy = Var([latvar, lonvar], values=dxdy)
  dxdy.atts['units'] = 'm2'

  return dxdy


# Helper method to compute the change in pressure within a vertical layer.
def compute_dp (zaxis, p0):
  from pygeode.formats import fstd
  from pygeode.var import Var
  from pygeode.ufunc import exp, log
  import math
  import numpy as np

  p0 = convert(p0, 'Pa')

  # eta coordinates?
  if isinstance(zaxis,fstd.Hybrid):
    raise TypeError("Not enough information to compute pressure interfaces on hybrid levels.")

  # zeta coordinates?
  elif isinstance(zaxis,fstd.LogHybrid):
    zeta = zaxis
    # Get the full set of coefficients
    a_m = zeta.atts['a_m']
    b_m = zeta.atts['b_m']
    a_t = zeta.atts['a_t']
    b_t = zeta.atts['b_t']
    # Add extra level at the lid
    a_m = np.array([math.log(zeta.atts['ptop'])] + list(a_m))
    b_m = np.array([0] + list(b_m))

    # Figure out if we have thermodynamic or momentum levels, and use the
    # other set of levels as the interfaces
    if set(zeta.A) <= set(a_m) and set(zeta.B) <= set(b_m):
      a_int = a_t
      b_int = b_t
    elif set(zeta.A) <= set(a_t) and set(zeta.B) <= set(b_t):
      a_int = a_m
      b_int = b_m
    else:
      raise ValueError ("Vertical axis must be entirely on model thermodynamic or momentum levels.")

    # Find indices of interfaces
    interface_ind = []
    for a in zeta.A:
      j = np.searchsorted(a_int, a) - 1
      if a_int[j+1] == a: j+= 1  # Check for lower boundary?
      interface_ind.append(j)
    # Add the bottom interface
    interface_ind.append(np.searchsorted(a_int, a))
    # Double-check we have the right things
    for a, j in zip(zeta.A, interface_ind[:-1]):
      assert a_int[j] <= a
    for a, j in zip(zeta.A, interface_ind[1:]):
      assert a_int[j] >= a

    # Define a dp operator
    a_upper = Var([zeta], values=a_int[interface_ind[:-1]])
    a_lower = Var([zeta], values=a_int[interface_ind[1:]])
    b_upper = Var([zeta], values=b_int[interface_ind[:-1]])
    b_lower = Var([zeta], values=b_int[interface_ind[1:]])
    p_upper = exp(a_upper + b_upper*log(p0/zeta.atts['pref']))
    p_lower = exp(a_lower + b_lower*log(p0/zeta.atts['pref']))
    dp = p_lower - p_upper

  else:
    raise TypeError("Can't handle '%s' axis."%zaxis.__class__.__name__)

  if dp.hasaxis('forecast'):
    dp = dp.transpose('time','forecast','zaxis')
  else:
    dp = dp.transpose('time','zaxis')

  dp.name = 'dp'
  dp.atts['units'] = 'Pa'
  return dp

# Helper method to compute pressure levels from the given z-axis and surface pressure
def compute_pressure (zaxis, p0):
  from pygeode.formats import fstd
  from pygeode.ufunc import exp, log

  p0 = convert(p0, 'Pa')

  # eta coordinates?
  if isinstance(zaxis, fstd.Hybrid):
    eta = zaxis
    A = eta.auxasvar('A')
    B = eta.auxasvar('B')
    p = A + B * p0

  # zeta coordinates?
  elif isinstance(zaxis, fstd.LogHybrid):
    zeta = zaxis
    A = zeta.auxasvar('A')
    B = zeta.auxasvar('B')
    pref = zeta.atts['pref']
    ptop = zeta.atts['ptop']
    p = exp(A + B * log(p0/zeta.atts['pref']))

  else:
    raise TypeError("Can't handle '%s' axis in this interface."%zaxis.__class__.__name__)

  if p.hasaxis('forecast'):
    p = p.transpose('time','forecast','zaxis')
  else:
    p = p.transpose('time','zaxis')
  p.name = 'air_pressure'
  p.atts['units'] = 'Pa'
  return p



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
    v = view.map_to(self._var, strict=False)
    tslice = list(view.integer_indices[0]//nf)
    fslice = list(view.integer_indices[0]%nf)
    # Collect forecasts from the same origin date together
    # (can read them all at once)
    tf_pairs = []
    for i,(t,f) in enumerate(zip(tslice,fslice)):
      if len(tf_pairs) > 0 and t == tf_pairs[-1][1]:
        tf_pairs[-1][0].append(i)
        tf_pairs[-1][2].append(f)
      else: tf_pairs.append(([i],t,[f]))

    for i,t,f in tf_pairs:
      data = v.modify_slice(0,[t]).modify_slice(1,f).get(self._var)
      out[i,...] = data.reshape(data.shape[1:])
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

# Force a variable to take on a superset of axis coordinates.
# E.g., extend a variable to a longer time period, putting missing values (NaN)
# where the variable is not defined.
# NOTE: assumes the coordinate values are in ascending order.
from pygeode.var import Var
class EmbiggenAxis (Var):
  def __init__ (self, var, iaxis, new_axis):
    from pygeode.var import Var, copy_meta
    axes = list(var.axes)
    axes[iaxis] = new_axis
    Var.__init__ (self, axes, dtype=var.dtype)
    copy_meta (var, self)
    self._var = var
    if var.dtype.name.startswith('float'):
      self._blank = float('nan')
    else:
      self._blank = 0
    self._iaxis = iaxis
    self._valid_axis_values = set(var.axes[iaxis].values)
  def getview (self, view, pbar):
    import numpy as np
    out = np.empty(view.shape, dtype=self.dtype)
    out[()] = self._blank
    # Find where we have actual data we can fill in.
    iaxis = self._iaxis
    requested_indices = view.integer_indices[iaxis]
    requested_values = view.subaxis(iaxis).values
    cromulent_values = sorted(self._valid_axis_values & set(requested_values))
    cromulent_axis = view.axes[iaxis].withnewvalues(cromulent_values)
    view = view.replace_axis(iaxis, cromulent_axis)
    outsl = [slice(None)]*self.naxes
    outsl[iaxis] = np.searchsorted(requested_values, cromulent_values)
    out[outsl] = view.get(self._var)

    return out
del Var

def embiggen_axis (var, old_axis, new_axis):
  iaxis = var.whichaxis(old_axis)
  return EmbiggenAxis(var, iaxis, new_axis)


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
  if zaxis_type in surface_values:
    sfc_val = surface_values[zaxis_type]
  else:
    from warnings import warn
    warn ("Incomplete information on z-axis.  Hopefully, the surface is being selected!")
    sfc_val = zaxis.values[{'up':0, 'down':-1}[zaxis.atts['positive']]]
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
      if type(zaxis) in surface_direction:
        direction = surface_direction[type(zaxis)]
      elif 'positive' in zaxis.atts:
        direction = {'up':-1, 'down':+1}[zaxis.atts['positive']]
      else: raise Exception ("Don't know how to find orientation of '%s'"%zaxis)
      return max(var.getaxis(ZAxis).values * direction)

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

# Check if we have 3D data available (lat/lon/zaxis)
# To be used in the find_best() method.
def have_gridded_3d_data (varlist):
  from pygeode.axis import Lat, Lon, ZAxis
  for var in varlist:
    if var.hasaxis(Lat) and var.hasaxis(Lon) and var.hasaxis(ZAxis): return True
  return False

# Check if we have station data.
def have_station_data (varlist):
  for var in varlist:
    if var.hasaxis("station"): return True
  return False


# Command-line argument parsing - helper classes

# Extend the argument parser to allow repeated groups of arguments
from argparse import HelpFormatter
class CustomHelpFormatter(HelpFormatter):
  def _format_actions_usage (self, actions, groups):
    import re
    text = super(CustomHelpFormatter,self)._format_actions_usage(actions,groups)
    superargs = []
    for action in actions:
      if hasattr(action,'_subargs'):
        superargs.append(action.option_strings[0])
    if len(superargs) == 0: return text
    pattern = '('+'|'.join(superargs)+')'
    text = re.sub(pattern,r'\1 {sub-arguments}',text)
    return text
del HelpFormatter

from argparse import ArgumentParser
class CustomArgumentParser(ArgumentParser):
  def __init__ (self, *args, **kwargs):
    kwargs['formatter_class'] = CustomHelpFormatter
    super(CustomArgumentParser,self).__init__(*args,**kwargs)
  # Add a nested argument group to this one?
  def add_superargument (self, *args, **kwargs):
    # Make it a boolean flag, so it can be parsed by the outer parser.
    kwargs['action'] = 'store_true'
    action = self.add_argument(*args,**kwargs)
    action._subargs = CustomArgumentParser(add_help=False,prog=action.option_strings[0])
    return action._subargs
  def format_help(self):
    from copy import copy
    x = copy(self)
    x._action_groups = list(x._action_groups)
    for action in self._actions:
      if hasattr(action,'_subargs'):
        group = copy(action._subargs)
        group.title = 'sub-arguments for %s'%action.option_strings[0]
        group.description = None
        group._group_actions = group._actions
        x._action_groups.append(group)
    return super(CustomArgumentParser,x).format_help()
  # Parse this thing out.
  def parse_args (self, args=None, namespace=None):
    import sys
    from argparse import Namespace

    superself = super(CustomArgumentParser,self)

    if args is None: args = sys.argv[1:]
    args = list(args)
    if namespace is None: namespace = Namespace()
    global_namespace = namespace

    # Try parsing all known args once, to trigger help menu, etc.
    superself.parse_known_args(args)

    split_indices = []
    split_actions = []
    for i,arg in enumerate(args):
      for action in self._actions:
        if not hasattr(action,'_subargs'): continue
        for opt in action.option_strings:
          if arg == opt or arg.startswith(opt+'='):
            split_indices.append(i)
            split_actions.append(action)
    split_indices.append(len(args))

    global_args = args[:split_indices[0]]
    subargs = {}
    for i,action in enumerate(split_actions):
      action = split_actions[i]
      namespaces = subargs.setdefault(action.dest,[])
      current_args = args[split_indices[i]:split_indices[i+1]]
      namespace, extra = action._subargs.parse_known_args(current_args)
      namespaces.append(namespace)
      global_args.append(current_args[0])
      global_args.extend(extra)

    # Consider anything that didn't parse yet to be part of the outer parser.
    superself.parse_args(global_args,global_namespace)

    # Attach the sub-arguments
    for name, value in subargs.iteritems():
      setattr(global_namespace,name,value)

    return global_namespace
del ArgumentParser

