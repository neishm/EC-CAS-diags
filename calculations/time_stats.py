from . import quick_calc

# Helper method:
# Select months that have full data coverage
def full_months(var):
  from datetime import datetime, timedelta
  from pygeode.timeutils import delta
  from ..common import to_datetimes
  dates = to_datetimes(var.time)
  dt = delta(var.time)
  dt = timedelta(**{var.time.units:dt})
  # Figure out which months start and the beginning and finish at the end
  have_month_start = dict()
  have_month_end = dict()
  for date in dates:
    ym = date.year, date.month
    # For month beginning, allow for a lack of 0-hour data
    if (date-2*dt).month != date.month:
      have_month_start[ym] = True
    if (date+dt).month != date.month:
      have_month_end[ym] = True
  # Collect all the time indices that are in a full month
  time_indices = []
  for i,date in enumerate(dates):
    ym = date.year, date.month
    if have_month_start.get(ym,False) and have_month_end.get(ym,False):
      time_indices.append(i)
  return var.slice[time_indices,...]


# Monthly mean calculation
@quick_calc
def monthlymean (dataset):
  from pygeode.climat import monthlymean
  from pygeode.var import copy_meta

  for invar in dataset:
    if not invar.hasaxis('time'):
      yield invar
      continue

    # Use only full months
    invar = full_months(invar)

    # Do the monthly mean
    outvar = monthlymean(invar)
    # Fix the output name (don't append '_monthly_mean' to it).
    outvar.name = invar.name
    # Fix the metadata (dropped due to a bug in PyGeode)
    copy_meta(invar,outvar)

    yield outvar
