###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################


# Functions / constants common to multiple modules

# Month names
long_monthnames = [
  (1,'January'),
  (2,'February'),
  (3,'March'),
  (4,'April'),
  (5,'May'),
  (6,'June'),
  (7,'July'),
  (8,'August'),
  (9,'September'),
  (10,'October'),
  (11,'November'),
  (12,'December'),
]
short_monthnames = [(n,month[:3]) for n,month in long_monthnames]
del n,month

# Unit conversion
from units import define_conversion, define_unit, conversion_factor

# Define the molar masses
define_conversion ('mol(CO2)', '44.01 g(CO2)')
define_conversion ('mol(CH4)', '16.04 g(CH4)')
define_conversion ('mol(dry_air)', '28.97 g(dry_air)')
define_conversion ('mol(H2O)', '18.01528 g(H2O)')
define_conversion ('mol(CO)', '28.010 g(CO)')
define_conversion ('mol(OH)', '17.00 g(OH)')  # 17.01 according to wikipedia
                                              # 17.00 according to GEM-MACH

# The following is a hack to get mass in terms of carbon atoms
# I.e. to allow converting mass to Pg(C)
define_conversion ('g(CO2)', repr(12.01/44.01) + ' g(C)')
define_conversion ('g(CH4)', repr(12.01/16.04) + ' g(C)')
define_conversion ('g(CO)', repr(12.01/28.010) + ' g(C)')

# For the purpose of these diagnostics, assume mole fractions are always with
# respect to air.
define_conversion ('molefraction', 'mol mol(dry_air)-1')

# Also, assume pressure is air pressure.
define_conversion ('Pa', 'kg(air) m-1 s-2')

# Helper method - get unit conversion context
def get_conversion_context (var, context=None):
  return context or var.atts.get('specie') or var.name

# Convert a variable from one unit to another
def convert (var, units, context=None, table=None):
  if 'units' not in var.atts:
    raise ValueError ("Variable '%s' has no units defined, can't do unit conversion!"%var.name)
  if var.atts['units'] == units: return var  # No conversion necessary
  name = var.name
  context = get_conversion_context(var, context)
  scale = conversion_factor (var.atts['units'], units, context, table=table)
  var = var * scale
  var.atts['units'] = units
  var.name = name
  # Extra parameters from the cache interface
  if 'low' in var.atts: var.atts['low'] *= scale
  if 'high' in var.atts: var.atts['high'] *= scale
  return var

# Helper methods to determine if something is of a particular kind of unit.
def can_convert (var, units, context=None, table=None):
  try:
    convert (var, units, context=context, table=table)
    return True
  except ValueError: return False

# Helper method - make a copy of a variable.
def copy_var (var):
  from copy import copy
  var = copy(var)
  var.atts = copy(var.atts)
  return var

# Helper method - for the given field and units, determine what other fields
# are needed to do the unit conversion.
# Output: list of extra variable names, and list of exponents (+/-1) to apply
# to the variables (+1 = multiply by that variable, -1 = divide by that variable).
def _what_extra_fields (data, fieldname, units, table):
  from itertools import product
  from units import simplify, inverse
  possible_extra_fields = []
  possible_extra_units = []
  for f in ['dry_air', 'cell_area', 'dp', 'gravity', 'density']:
    try:
      v = data.find_best(f)
      possible_extra_fields.append(f)
      possible_extra_units.append(v.atts['units'])
    except KeyError: pass
  var = data.find_best(fieldname)
  errmsg = "Don't know how to convert %s %s from '%s' to '%s'.  Extra fields tried: %s"%(getattr(data,'name',''), fieldname, var.atts['units'], units, possible_extra_fields)
  # Apply proper context to the target units
  context = get_conversion_context(var)
  units = simplify(units, global_context=context, table=table)
  # Try all combinations of extra fields, see what gives the expected units.
  for exps in product(*[[-1,0,1]]*len(possible_extra_fields)):
    test = var.atts['units']
    for u,ex in zip(possible_extra_units, exps):
      if ex == 0: continue
      if ex == -1: u = inverse(u)
      test = test + ' ' + u
    # To check for a match, see if the only difference between the units is a
    # scale factor
    # First, reduce out all context-free units
    test = simplify(test + ' ' + inverse(units), table=table)
    # Then, apply the variable context to the remaining units, and see if
    # anything else cancels out.
    test = simplify(test, global_context=context, table=table)
    # See if this reduces to a scalar number (or nothing at all).
    if test == '': test = '1'
    try:
      float(test)
      out = zip(*[(f,ex) for f,ex in zip(possible_extra_fields,exps) if ex!=0])
      if len(out) > 0: return out
      return [], []
    except ValueError: pass
  raise ValueError (errmsg)

# Helper method - find the field in the dataset, and apply some unit conversion.
# Handle some extra logic, such as going between dry and moist air.
def find_and_convert (product, fieldnames, units, **conditions):
  from pygeode.dataset import Dataset
  from pygeode.var import Var
  from eccas_diags.interfaces import DataInterface
  from units import copy_default_table, define_conversion, parse_units, simplify, inverse

  # Allow a list of variables to be passed in.
  if isinstance(product,list) and isinstance(product[0],Var):
    product = Dataset(product)

  # Allow a single Dataset to be passed in.
  if isinstance(product,Dataset):
    product = DataInterface([product])

  return_list = True

  if isinstance(fieldnames,str):
    fieldnames = [fieldnames]
    return_list = False
  if isinstance(units,str): units = [units]*len(fieldnames)

  # Create a separate unit table for each variable, to handle things like
  # semi-dry air uniquely.
  tables = [copy_default_table() for fieldname in fieldnames]

  # Test table, with no entry for dry air.
  # So we can partially reduce the units without going from moles to mass.
  test_table = copy_default_table()
  del test_table['mol'].conversions['dry_air']

  # Convert semi-dry air based on the type of output units
  for fieldname, out_units, table in zip(fieldnames, units, tables):
    in_units = product.find_best(fieldname).atts.get('units','')
    in_units = simplify(in_units,table=test_table)
    # Allow the user to skip unit conversion by setting output units to None
    if out_units is None: continue
    out_units = simplify(out_units,table=test_table)
    all_units = in_units.split() + out_units.split()
    # If looking at molefractions, treat as dry air.
    if 'mol(semidry_air)-1' in all_units and 'mol(dry_air)-1' in all_units:
      define_conversion ('mol(semidry_air)', 'mol(dry_air)', table=table)
    # If converting molefractions to mass, then treat as dry air for the
    # purpose of getting mass, then redefine it as moist air afterwards.
    elif 'mol(semidry_air)-1' in all_units and 'g(air)-1' in all_units:
      define_conversion ('mol(semidry_air)', 'mol(dry_air) g(dry_air)-1 g(air)', table=table)
    # If looking at mass, then treat as moist air.
    elif 'g(semidry_air)-1' in all_units and 'g(air)-1' in all_units:
      define_conversion ('g(semidry_air)', 'g(air)', table=table)
    # If converting mass to mixing ratio, then treat as dry air.
    elif 'g(semidry_air)-1' in all_units and 'mol(dry_air)-1' in all_units:
      define_conversion ('g(semidry_air)', 'g(dry_air)', table=table)

  # Find out what extra fields are needed for the conversions
  extra_fields = []
  exponents = []  # +1 = multiply, -1 = divide
  for fieldname, unit, table in zip(fieldnames,units,tables):
    # Allow the user to skip unit conversion by setting output units to None
    if unit is None: continue
    f, exp = _what_extra_fields(product, fieldname, unit, table=table)
    extra_fields.extend(f)
    exponents.extend(exp)

  # Reduce to a unique set of extra fields
  if len(extra_fields) > 0:
    extra_fields, exponents = zip(*set(zip(extra_fields,exponents)))

  # Get all fields (original and extra)
  vars = product.find_best(list(fieldnames)+list(extra_fields), **conditions)

  # Split into the two categories
  vars, extra_vars = vars[:len(fieldnames)], vars[len(fieldnames):]

  # Apply the extra fields
  for i,fieldname in enumerate(fieldnames):
    # Allow the user to skip unit conversion by setting output units to None
    if units[i] is None: continue
    F, exp = _what_extra_fields(product, fieldname, units[i], table=tables[i])
    extra = [extra_vars[extra_fields.index(f)] for f in F]
    for v, e in zip(extra,exp):
      unit = vars[i].atts['units']
      specie = vars[i].atts.get('specie',None)
      assert e in (1,-1), "Unhandled exponent %d"%e
      if e == 1:
        vars[i] *= v
        vars[i].atts['units'] = unit + ' ' + v.atts['units']
      elif e == -1:
        vars[i] /= v
        vars[i].atts['units'] = unit + ' ' + inverse(v.atts['units'])
      vars[i].name = fieldname
      if specie is not None:
        vars[i].atts['specie'] = specie

  # Do any remaining unit conversions.
  # Skip conversions when output unit set to None.
  vars = [convert(v, unit, table=table) if unit is not None else v for v,unit,table in zip(vars,units,tables)]

  if return_list:
    return vars
  else:
    return vars[0]


grav = .980616e+1  # Taken from GEM-MACH file chm_consphychm_mod.ftn90

# Normalize the time axes to the same start date / units
def fix_timeaxis (data):
  from pygeode.timeaxis import StandardTime
  from pygeode.dataset import Dataset
  if not hasattr(data,'time'): return data  # No time axis found?
  startdate = dict(year=2009, month=1, day=1)
  time = data.time
  time = StandardTime(units='days', startdate=startdate, **time.auxarrays)
  if isinstance(data,Dataset):
    data = Dataset([v.replace_axes(time=time) if v.hasaxis('time') else v for v in data], atts=data.atts)
  elif data.hasaxis('time'):
    data = data.replace_axes(time=time)
  return data

# Convert a string to an int or float, if possible.  (Otherwise, keep it as a string)
def best_type (x):
  try: return int(x)
  except ValueError: pass
  try: return float(x)
  except ValueError:pass
  return x

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

# Convert a time axis to a list of datetime objects.
def to_datetimes(taxis):
  from datetime import datetime,timedelta
  ref = datetime(**taxis.startdate)
  units = taxis.units
  values = taxis.values
  return [ref+timedelta(**{units:v}) for v in values]

# Detect regularly-spaced data, and "fill in" the gaps with NaN values.
# Note: loads ALL the data into memory, so use with caution.
def detect_gaps(var):
  import numpy as np
  from collections import Counter
  from pygeode.var import Var, copy_meta
  # If no time values, do nothing.
  if len(var.time) <= 1: return var

  dt, count = Counter(np.diff(var.time.values)).most_common(1)[0]
  # If we have an extremely irregular time axis, then don't try to make it
  # regular (e.g. for flask data, which is taken whenever they remember to
  # do it?)
  if count < len(var.time)/10+2: return var
  start = var.time.values[0]
  stop = var.time.values[-1]
  n = int(round((stop-start)/dt)) + 1
  full_time = np.linspace(start, stop, n)
  full_values = np.empty((len(full_time),)+var.shape[1:],dtype=var.dtype)
  full_values[:] = float('nan')
  indices = np.asarray(np.round((var.time.values-start)/dt),dtype=int)
  full_values[indices,...] = var.get()
  taxis = type(var.time)(startdate=var.time.startdate, units=var.time.units, values=full_time)
  outvar = Var(axes=(taxis,)+var.axes[1:], values=full_values)
  copy_meta (var, outvar)
  return outvar

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

    # Figure out if we have thermodynamic or momentum levels, and use the
    # other set of levels as the interfaces
    if set(zeta.A) <= set(a_m) and set(zeta.B) <= set(b_m):
      #a_int = a_t
      #b_int = b_t
      raise ValueError ("Not computing dp on momentum levels.")
    elif set(zeta.A) <= set(a_t) and set(zeta.B) <= set(b_t):
      a_int = a_m
      b_int = b_m
    else:
      raise ValueError ("Vertical axis must be entirely on model thermodynamic or momentum levels.")

    # Find indices of interfaces
    a_upper = []
    a_lower = []
    b_upper = []
    b_lower = []
    for a in zeta.A:
      j = np.searchsorted(a_int, a)

      if j == 0:  # Beyond actual model lid?
        a_upper.append(a_int[j])
        b_upper.append(b_int[j])
      else:
        a_upper.append(a_int[j-1])
        b_upper.append(b_int[j-1])

      if j == len(a_int) or a_int[j] == a:  # Beyond model surface?
        a_lower.append(a_int[j-1])
        b_lower.append(b_int[j-1])
      else:
        a_lower.append(a_int[j])
        b_lower.append(b_int[j])

    # Define a dp operator
    a_upper = Var([zeta], values=a_upper)
    a_lower = Var([zeta], values=a_lower)
    b_upper = Var([zeta], values=b_upper)
    b_lower = Var([zeta], values=b_lower)
    p_upper = exp(a_upper + b_upper*log(p0/zeta.atts['pref']))
    p_lower = exp(a_lower + b_lower*log(p0/zeta.atts['pref']))
    dp = p_lower - p_upper
  else:
    raise TypeError("Can't handle '%s' axis."%zaxis.__class__.__name__)

  if dp.hasaxis('forecast'):
    dp = dp.transpose('time','forecast','zaxis')
  elif dp.hasaxis('time'):
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
  elif p.hasaxis('time'):
    p = p.transpose('time','zaxis')
  p.name = 'air_pressure'
  p.atts['units'] = 'Pa'
  return p




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


# Make a field positive (remove negative values)
from pygeode.var import Var
class Positive(Var):
  def __init__ (self, var):
    from pygeode.var import Var, copy_meta
    Var.__init__(self, var.axes, dtype=var.dtype)
    copy_meta(var, self)
    self._var = var
  def getview (self, view, pbar):
    import numpy as np
    out = np.array(view.get(self._var))
    out[out<0] = 0
    pbar.update(100)
    return out
del Var

def positive(var): return Positive(var)


# Get a keyword / value that can be used to select a surface level for the
# givem vertical axis.
from pygeode.axis import Pres, Hybrid
from pygeode.formats.fstd import LogHybrid, Height_wrt_Ground
surface_values = {Pres:1000., Hybrid:1.0, LogHybrid:1.0, Height_wrt_Ground:0.0}
surface_direction = {Pres:+1, Hybrid:+1, LogHybrid:+1, Height_wrt_Ground:-1}
# Rank the different axis types by preference (higher number is better)
surface_preference = {Pres:0, Hybrid:0, LogHybrid:0, Height_wrt_Ground:1}
del Pres, Hybrid, LogHybrid, Height_wrt_Ground

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
      rank = surface_preference.get(type(zaxis),0)
      value = max(var.getaxis(ZAxis).values * direction)
      # Prefer higher-ranked axis types.
      # Collapse (rank,value) tuple to a single value, for compatibility with
      # data_scanner logic.
      return rank*1E6+value

# Rank a dataset based on the number of timesteps available.
# To be used in the find_best() method.
def number_of_timesteps (varlist):
  from pygeode.axis import TAxis
  for var in varlist:
    if var.hasaxis(TAxis):
      return len(var.getaxis(TAxis))

# Rank a dataset based on the time duration.
def length_of_time (varlist):
  from pygeode.axis import TAxis
  from pygeode.timeutils import reltime
  for var in varlist:
    if var.hasaxis(TAxis):
      taxis = var.getaxis(TAxis)
      tvals = reltime(taxis,units='hours')
      if len(tvals) == 0: return 0
      return tvals[-1] - tvals[0]

# Rank a dataset based on the number of levels available.
# To be used in the find_best() method.
def number_of_levels (varlist):
  from pygeode.axis import ZAxis
  for var in varlist:
    if var.hasaxis(ZAxis):
      return len(var.getaxis(ZAxis))
  return 0  # No levels found

# Check if we have data on a lat/lon grid.
# To be used in the find_best() method.
def have_gridded_data (varlist):
  from pygeode.axis import Lat, Lon
  for var in varlist:
    if var.hasaxis(Lat) and var.hasaxis(Lon): return True
  return False

# Check if we have vertical structure in the data.
def have_vertical_data (varlist):
  from pygeode.axis import ZAxis
  for var in varlist:
    if var.hasaxis(ZAxis): return True
  return False

# Check if we have 3D data available (lat/lon/zaxis)
# To be used in the find_best() method.
def have_gridded_3d_data (varlist):
  from pygeode.axis import Lat, Lon, ZAxis
  for var in varlist:
    if var.hasaxis(Lat) and var.hasaxis(Lon) and var.hasaxis(ZAxis): return True
  return False

# Check if we have a particular vertical level
def have_level (level):
  def have_the_level (dataset):
    for var in dataset:
      if var.hasaxis('zaxis'):
        levels = var.getaxis('zaxis').values
        if any(l>= level*0.9 and l<=level*1.1 for l in levels):
          return True
    return False
  return have_the_level

# Check if we have a particular diagnostic level
def have_height (height):
  def have_the_height (dataset):
    for var in dataset:
      if var.hasaxis('height'):
        heights = var.getaxis('height').values
        if any(z == height for z in heights):
          return True
    return False
  return have_the_height

# Check if we have station data.
def have_station_data (varlist):
  for var in varlist:
    if var.hasaxis("station"): return True
  return False

# Similar to above, but must also have vertical structure.
def have_profile_data (varlist):
  from pygeode.axis import ZAxis
  for var in varlist:
    if var.hasaxis("station") and var.hasaxis(ZAxis): return True
  return False
