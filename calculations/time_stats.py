from . import quick_calc

#TODO: Check if we have the full month, or only a partial version.
@quick_calc
def monthlymean (dataset):
  from pygeode.climat import monthlymean
  from pygeode.var import copy_meta

  for invar in dataset:
    if not invar.hasaxis('time'): continue

    # Do the monthly mean
    outvar = monthlymean(invar)
    # Fix the output name (don't append '_monthly_mean' to it).
    outvar.name = invar.name
    # Fix the metadata (dropped due to a bug in PyGeode)
    copy_meta(invar,outvar)

    yield outvar
