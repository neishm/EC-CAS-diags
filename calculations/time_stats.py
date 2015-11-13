from . import quick_calc

#TODO: Check if we have the full month, or only a partial version.
@quick_calc(cache=True)
def monthlymean (dataset):
  from pygeode.climat import monthlymean

  for invar in dataset:
    if not invar.hasaxis('time'): continue

    # Do the monthly mean
    outvar = monthlymean(invar)
    # Fix the output name (don't append '_monthly_mean' to it).
    outvar.name = invar.name

    yield outvar
