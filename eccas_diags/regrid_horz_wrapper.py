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


# Helper methods for dealing with horizontal regridding step

# Determine latitude bounds
# Assume a global grid (end points are -90 and +90).
# Assume we can just take the mid-points of the latitudes for the inner
# boundaries.
def get_latbounds (lat):
  import numpy as np
  lat = np.array(lat)
  bounds = np.empty([len(lat)+1], dtype=lat.dtype)
  bounds[1:-1] = (lat[0:-1] + lat[1:]) / 2
  # Increasing lats?
  if lat[1] > lat[0]:
    bounds[0] = -90.
    bounds[-1] = 90.
  # Decreasing lats?
  else:
    bounds[0] = 90.
    bounds[-1] = -90.
  return bounds 

# Determine longitude bounds
# Assume a global grid, with equispaced longitudes.
# Also assume the longitudes are monotonically increasing.
def get_lonbounds (lon):
  import numpy as np
  lon = np.array(lon)
  bounds = np.empty([len(lon)+1], dtype=lon.dtype)
  bounds[1:-1] = (lon[0:-1] + lon[1:]) / 2
  bounds[0] = lon[0] - 0.5*(lon[1]-lon[0])
  bounds[-1] = lon[-1] + 0.5*(lon[-1]-lon[-2])
  return bounds


# Helper interface - horizontal regridding
from pygeode.var import Var
class HorzRegrid (Var):
  def __init__ (self, source, target_lat, target_lon):
    from pygeode.var import Var, copy_meta
    from math import pi
    import numpy as np

    axes = list(source.axes)
    axes[source.whichaxis('lat')] = target_lat
    axes[source.whichaxis('lon')] = target_lon

    self._source = source

    # Input coords
    self._lon1 = get_lonbounds(source.lon)
    self._sin1 = np.sin(get_latbounds(source.lat)/180.*pi)

    # Output coords
    self._lon2 = get_lonbounds(target_lon)
    self._sin2 = np.sin(get_latbounds(target_lat)/180.*pi)

    Var.__init__(self, axes, dtype='float32')
    copy_meta (source, self)

  def getview (self, view, pbar):
    import numpy as np
    from regrid_horz import fvdasregridmodule as regridmodule

    # Un-slice the lat/lon axes.
    # We will always regrid the whole source grid onto the whole target grid,
    # then apply any final slicing to provide what was originally requested.
    latdim = self.whichaxis('lat')
    londim = self.whichaxis('lon')
    latslice = view.slices[latdim]
    lonslice = view.slices[londim]
    view = view.unslice(latdim, londim)

    # Get the target data
    lon1 = self._lon1
    sin1 = self._sin1

    # Get the source data
    source_view = view.replace_axis(latdim, self._source.lat).replace_axis(londim, self._source.lon)
    source = source_view.get(self._source)
    lon2 = self._lon2
    sin2 = self._sin2

    # Reshape the source data so it's [everything else, lat,lon]
    nlat_source = source.shape[latdim]
    nlon_source = source.shape[londim]
    nlat_target = view.shape[latdim]
    nlon_target = view.shape[londim]
    transpose = [i for i in range(self.naxes) if i not in [latdim,londim]] + [latdim,londim]
    transposed_source_shape = [source.shape[k] for k in transpose]
    transposed_target_shape = [view.shape[k] for k in transpose]
    untranspose = [None]*self.naxes
    for i,k in enumerate(transpose): untranspose[k] = i

    source = source.transpose(transpose)
    source = source.reshape([-1,nlat_source,nlon_source])

    # Cast to the expected type
    source = np.asarray(source, dtype='float32')
    lon1 = np.asarray(lon1, dtype='float32')
    sin1 = np.asarray(sin1, dtype='float32')
    lon2 = np.asarray(lon2, dtype='float32')
    sin2 = np.asarray(sin2, dtype='float32')

    # Loop over the source data, do the regridding, and collect into a
    # target array
    data = np.empty(transposed_target_shape, dtype='float32')
    data = data.reshape([-1,nlat_target,nlon_target])
    for i in range(data.shape[0]):
      data[i,:,:] = regridmodule.map_a2a (lon1, sin1, source[i,:,:].T, lon2, sin2, ig=0, iv=0).T
    data = data.reshape(transposed_target_shape)
    data = data.transpose(untranspose)

    # Get the final slice of the data
    slices = [slice(None)] * self.naxes
    slices[latdim] = latslice
    slices[londim] = lonslice
    return data[slices]

del Var

# Wrapper for using the above class
# (handles some details like repeated longitudes)
def horzregrid (source, target_lat, target_lon):
  from common import rotate_grid, have_repeated_longitude, remove_repeated_longitude, add_repeated_longitude, increasing_latitudes
  # Make sure the source/target longitudes have the same range
  # (make them both 0..360).
  #TODO: rotate back to the target grid after regridding?
  source = rotate_grid(source)
  target_lon = rotate_grid(target_lon).lon
  # Make sure we have increasing latitudes
  #TODO: flip back to the original target order after regridding?
  source = increasing_latitudes(source)
  target_lat = increasing_latitudes(target_lat).lat
  # Check if we need to remove a repeated longitude on the source / target
  if have_repeated_longitude(source):
    source = remove_repeated_longitude(source)
  if have_repeated_longitude(target_lon):
    repeat_target = True
    target_lon = remove_repeated_longitude(target_lon).lon
  else: repeat_target = False
  # Create the regridded variable
  target = HorzRegrid (source, target_lat, target_lon)
  # Do we need to add back in the repeated longitude?
  if repeat_target:
    target = add_repeated_longitude(target)

  return target


# Do the horizontal regridding step
def do_horizontal_regridding (input_data, grid_data, conserve_mass, sample_field=None):
  from common import find_and_convert, have_gridded_data
  from interfaces import DataInterface
  import logging
  logger = logging.getLogger(__name__)
  regridded_dataset = []
  if sample_field is not None:
    target_grid = grid_data.find_best(sample_field)
  else:
    #TODO: handle multiple target grids
    for dataset in grid_data:
      for var in dataset:
        if var.hasaxis('lat') and var.hasaxis('lon'):
          target_grid = var
    del dataset, var

  varnames = sorted(set(v.name for d in input_data.datasets for v in d))

  for varname in varnames:

    # Skip non-spatial fields
    var_test = input_data.find_best(varname)
    if not var_test.hasaxis('lat') or not var_test.hasaxis('lon'):
      continue

    # Skip pressure fields
    if varname == 'air_pressure' or varname == 'dp' or varname == 'surface_pressure':
      continue

    # Skip cell area
    if varname == 'cell_area':
      continue

    # If not conserving mass, then use the existing units.
    if not conserve_mass:
      try:
        var = input_data.find_best(varname, requirement=have_gridded_data)
      except ValueError as e:
        logger.debug('Dropping field "%s" - %s', varname, e)
        continue
      var = horzregrid(var, target_grid.lat, target_grid.lon)
      regridded_dataset.append(var)
      continue

    # Prepare the variables into the appropriate units for mass-conservative
    # regridding.

    ##################################################################
    # Case 1: flux
    ##################################################################
    try:
      var = find_and_convert (input_data, varname, 'g m-2 s-1', requirement=have_gridded_data)
    except ValueError:
      ##################################################################
      # Case 2: tracer field
      ##################################################################
      try:
        var = find_and_convert (input_data, varname, 'g m-2', requirement=have_gridded_data)
      except ValueError as e:
        logger.debug('Dropping field "%s" - %s', varname, e)
        continue

    # Regrid the variable
    var = horzregrid(var, target_grid.lat, target_grid.lon)
    regridded_dataset.append(var)

  return DataInterface([regridded_dataset])


