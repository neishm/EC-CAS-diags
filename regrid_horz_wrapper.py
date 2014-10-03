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
    from common import rotate_grid
    from math import pi
    import numpy as np
    source = rotate_grid(source)
    target_lon = rotate_grid(target_lon).lon

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


# Regrid a field
# Inputs:
#   field - The input field (PyGeode object)
#   lat   - The output latitudes (PyGeode object)
#   lon   - The output longitudes (PyGeode object)
# Output:
#   The regridded field (PyGeode object)
def regrid (field, lat, lon):
  from regrid_horz import regridmodule
  import numpy as np
  from pygeode.var import Var
  from math import pi
  from common import rotate_grid

  # Rotate the field so it's from 0 to 360
  field = rotate_grid(field)

  # Input coords
  lon1 = get_lonbounds(field.lon)
  sin1 = np.sin(get_latbounds(field.lat)/180.*pi)

  # Output coords
  lon2 = get_lonbounds(lon)
  sin2 = np.sin(get_latbounds(lat)/180.*pi)

  nt = field.shape[0]

  # Input data
  in_data = field.get()

  # Output data
  out_data = np.empty([nt,len(lat),len(lon)], dtype=in_data.dtype)


  # Loop over each time step, do the regridding
  for t in range(nt):
    q1 = in_data[t,:,:].T
    q2 = regridmodule.map_a2a (lon1, sin1, q1, lon2, sin2, ig=0, iv=0)
    out_data[t,:,:] = q2.T

  # Return the array (with coordinate metadata)
  axes = [field.axes[0], lat, lon]
  return Var(axes=axes, values=out_data, name=field.name)

# Do the horizontal regridding step
def do_horizontal_regridding (input_data, grid_data, out_interface):
  from common import is_mass_flux, is_mixing_ratio, convert
  from data_interface import DataInterface
  source_datasets = list(input_data.datasets)
  target_datasets = []
  for source_dataset in source_datasets:
#    source_dp = source_dataset.get('dp',None)
#    source_dp = convert(source_dp, 'Pa')
    target_dataset = []
    for var in source_dataset.vars:
      # Don't interpolate variables with no lat/lon.
      if not var.hasaxis('lat') or not var.hasaxis('lon'):
        print 'Not horizontall regridding %s'%var.name
        target_dataset.append(var)
        continue

      # Find the appropriate target grid.
      # If this variable is defined in the grid file, then use that specific grid.
      try:
        dummy_target = grid_data.find_best(var.name)
      # If the variable is not in the grid file, use a default.
      except KeyError:
        dummy_target = grid_data.datasets[0][0]

      # Do the regridding
      #TODO: scale by source / target dp to conserve mass
      var = HorzRegrid(var, dummy_target.lat, dummy_target.lon)
      target_dataset.append(var)
    target_datasets.append(target_dataset)

  return DataInterface(target_datasets)


