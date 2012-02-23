# Functions / constants common to multiple modules

# Conversion factor (from ug C / kg air to ppmV)
convert_CO2 = 1/414.22161

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
    newvals[ind] = invars[i].values
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
