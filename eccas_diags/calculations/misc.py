# Miscellaneous wrappers for Var-related methods

from . import quick_calc

# Derivative function
@quick_calc
def deriv (dataset, daxis, **kwargs):

  # Skip variables with no time axis
  for invar in dataset:
    if not invar.hasaxis(daxis):
      #yield invar
      continue

    # Do the derivative
    outvar = invar.deriv(daxis, **kwargs)
    # Fix the output name
    outvar.name = invar.name

    yield outvar

