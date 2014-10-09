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
    from regrid_horz import regridmodule

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
  from common import rotate_grid, have_repeated_longitude, remove_repeated_longitude, add_repeated_longitude
  # Make sure the source/target longitudes have the same range
  # (make them both 0..360).
  #TODO: rotate back to the target grid after regridding?
  source = rotate_grid(source)
  target_lon = rotate_grid(target_lon).lon
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
def do_horizontal_regridding (input_data, grid_data, out_interface):
  from common import can_convert, convert, first_timestep
  from data_interface import DataInterface
  from pygeode.var import copy_meta
  source_datasets = list(input_data.datasets)
  target_datasets = []
  for source_dataset in source_datasets:
    target_dataset = []
    for var in source_dataset.vars:
      # Don't interpolate variables with no lat/lon.
      if not var.hasaxis('lat') or not var.hasaxis('lon'):
        target_dataset.append(var)
        continue

      # Find the appropriate target grid.
      # If this variable is defined in the grid file, then use that specific grid.
      ##################################################################
      # Case 1: flux data (mass / m2 / s)
      ##################################################################
      if can_convert(var, 'kg m-2 s-1') or can_convert(var, 'kg m-2'):
        try:
          dummy_target = grid_data.find_best(var.name)
        # If the variable is not in the grid file, use a default.
        except KeyError:
          dummy_target = grid_data.datasets[0][0]
        var = horzregrid(var, dummy_target.lat, dummy_target.lon)

      ##################################################################
      # Case 2: flux data (mass / s)
      ##################################################################
      elif can_convert(var, 'kg s-1') or can_convert(var, 'kg'):
        if 'cell_area' not in source_dataset:
          print 'Dropping field "%s" - no grid area information available.'%var.name
          continue
        source_area = convert(source_dataset['cell_area'],'m2')
        try:
          # Try to find a grid area that has the same domain as the variable
          # (if the variable is defined in the target grid file).
          dummy_target, target_area = grid_data.find_best([var.name,'cell_area'])
        except KeyError:
          # Otherwise, look for any cell area information in the target grid.
          target_area = grid_data.find_best('cell_area')
          dummy_target = target_area

        target_area = convert(target_area, 'm2')
        target_area = first_timestep(target_area)
        orig = var
        var = var / source_area
        var = horzregrid(var, dummy_target.lat, dummy_target.lon)
        var = var * target_area
        copy_meta (orig, var)

      ##################################################################
      # Case 3: mixing ratio
      ##################################################################
      elif can_convert(var, 'molefraction'):
        # Find an appropriate target grid.
        # If this field is defined in the grid file, then use that definition.
        # Otherwise, find some other field with grid data (like 'dp').
        try:
          dummy_target = grid_data.find_best(var.name)
        except KeyError:
          dummy_target = grid_data.find_best('dp')
        # Do the regridding
        var = horzregrid(var, dummy_target.lat, dummy_target.lon)

      ##################################################################
      # Unhandled case
      ##################################################################
      else:
        print 'Dropping field "%s" - unhandled units "%s"'%(var.name,var.atts['units'])
        continue

      target_dataset.append(var)
    target_datasets.append(target_dataset)

  return DataInterface(target_datasets)


