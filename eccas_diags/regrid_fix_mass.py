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


# Apply a global scale factor to the target 3D data, in order to have the
# same mass as the source data.

# Put the scaled field into a PyGeode operator, to speed it up.
# Otherwise, will end up calculating things multiple times.
from pygeode.var import Var
class CachedVar (Var):
  def __init__ (self, var, desc):
    from pygeode.var import Var, copy_meta
    self._var = var
    self._desc = desc
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

      var = view.get(self._var)
      logger.info(self._desc+": "+str(var.flatten()[0]))
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
      if varname in ('dry_air','dp','cell_area','gravity'):
        raise ValueError("need to keep this intact for proper unit conversion.")
      original_mass = find_and_convert (original_data, varname, 'Pg')
      original_mass = remove_repeated_longitude(original_mass)
      original_mass = original_mass.sum('lat','lon','zaxis')
      original_mass = CachedVar(original_mass, "Expected %s mass"%varname)
      current_mass = find_and_convert (data, varname, 'Pg')
      current_mass = remove_repeated_longitude(current_mass)
      current_mass = current_mass.sum('lat','lon','zaxis')
      current_mass = CachedVar(current_mass, "Uncorrected %s mass"%varname)
      airmass = find_and_convert (data, 'dry_air', 'Pg')
      airmass = remove_repeated_longitude(airmass)
      airmass = airmass.sum('lat','lon','zaxis')
      airmass = CachedVar(airmass, "Target air mass")
    except KeyError as e:
      logger.debug("Skipping '%s', since it's not in the original data.", varname)
      continue
    except ValueError as e:
      logger.info("Not scaling '%s' - %s", varname, e)
      scaled_dataset.append(var_test)
      continue

    # Calculate the mass error, and distribute it equally in the atmosphere.
    offset = (current_mass-original_mass)/airmass
    copy_meta (var_test, offset)
    offset.atts['units'] = 'Pg Pg(dry_air)-1'
    # Convert this offset to the original units of the variable.
    offset = find_and_convert(list(data.datasets[0]-offset.name)+[offset], offset.name, var_test.atts['units'])
    # Apply the offset.
    var = var_test - offset
    copy_meta (var_test, var)
    scaled_dataset.append(var)

  return DataInterface([scaled_dataset])


