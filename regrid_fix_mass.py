# Apply a global scale factor to the target 3D data, in order to have the
# same mass as the source data.

# Put the scaled field into a PyGeode operator, to speed it up.
# Otherwise, will end up calculating things multiple times.
from pygeode.var import Var
class CachedVar (Var):
  def __init__ (self, var):
    from pygeode.var import Var, copy_meta
    self._var = var
    self._cache = [None,None]  # Store info on last data request
    Var.__init__(self, var.axes, dtype=var.dtype)
    copy_meta (var, self)
  def getview (self, view, pbar):
    import numpy as np
    import logging
    logger = logging.getLogger(__name__)

    # Use cached values?
    last_key, cached_data = self._cache
    key = tuple(map(tuple, view.integer_indices))
    if key == last_key:
      return cached_data

    else:

      print '::: Scanning %s'%self._var.name
      var = view.get(self._var)
      self._cache[:] = key, var

    pbar.update(100)

    return var


del Var

def global_scale (data, original_data, grid_data):
  from pygeode.var import copy_meta
  from common import find_and_convert, remove_repeated_longitude
  from interfaces import DataInterface
  import logging
  logger = logging.getLogger(__name__)
  scaled_dataset = []
  varnames = sorted(set(v.name for d in data.datasets for v in d))

  for varname in varnames:

    var_test = data.find_best(varname)
    try:
      original_mass = find_and_convert (original_data, varname, 'Pg')
      original_mass = remove_repeated_longitude(original_mass)
      original_mass = original_mass.sum('lat','lon','zaxis')
      original_mass = CachedVar(original_mass)
      current_mass = find_and_convert (data, varname, 'Pg')
      current_mass = remove_repeated_longitude(current_mass)
      current_mass = current_mass.sum('lat','lon','zaxis')
      current_mass = CachedVar(current_mass)
      airmass = find_and_convert (data, 'dry_air', 'Pg')
      airmass = remove_repeated_longitude(airmass)
      airmass = airmass.sum('lat','lon','zaxis')
      airmass = CachedVar(airmass)
    except KeyError as e:
      logger.debug("Skipping '%s', since it's not in the original data.", varname)
      continue
    except ValueError as e:
      logger.debug("Not scaling '%s' - %s", varname, e)
      scaled_dataset.append(var_test)
      continue
    logger.info ("Original mass of %s (Pg): %s", varname, original_mass.get(i_time=0))
    logger.info ("Uncorrected mass of target %s (Pg): %s", varname, current_mass.get(i_time=0))

    # Calculate the mass error, and distribute it equally in the atmosphere.
    offset = (current_mass-original_mass)/airmass
    copy_meta (var_test, offset)
    offset.atts['units'] = 'Pg Pg(dry_air)-1'
    # Convert this offset to the original units of the variable.
    offset = find_and_convert(list(grid_data.datasets[0].vars)+[offset], offset.name, var_test.atts['units'])
    # Apply the offset.
    var = var_test - offset
    copy_meta (var_test, var)
    scaled_dataset.append(var)

  return DataInterface([scaled_dataset])


