from . import quick_calc

@quick_calc
def zonalmean (dataset):
  from ..common import remove_repeated_longitude

  for invar in dataset:
    if not invar.hasaxis('lon'): continue

    # Remove any repeated longtiude (for global data)
    invar = remove_repeated_longitude(invar)

    # Do the zonal mean
    yield invar.nanmean('lon')


@quick_calc
def zonalstdev (dataset):
  from ..common import remove_repeated_longitude

  for invar in dataset:
    if not invar.hasaxis('lon'): continue

    # Remove any repeated longtiude (for global data)
    invar = remove_repeated_longitude(invar)

    # Do the standard deviation (NOTE: single-pass algorithm, may lose precision)
    yield invar.nanstdev('lon')


