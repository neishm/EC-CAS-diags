# Helper methods for dealing with the vertical regridding step

# Helper interface - vertical regridding
from pygeode.var import Var
class VertRegrid (Var):
  def __init__ (self, p0, source_p, source_dp, target_p, target_dp, source):
    from pygeode.var import Var, copy_meta
    from common import convert
    assert source_dp.axes == source.axes
    assert source_p.axes == source.axes
    assert target_p.axes == target_dp.axes
    zdim = source.whichaxis('zaxis')
    assert source_p.axes[:zdim] + source_p.axes[zdim+1:] == p0.axes
    assert target_p.axes[:zdim] + target_p.axes[zdim+1:] == p0.axes
    # Determine the order of the pressure levels.
    column_slice = [0]*source_p.naxes
    column_slice[zdim] = slice(None)
    sample_source_p = source_p[column_slice].flatten()
    sample_target_p = target_p[column_slice].flatten()
    self._invert_source = sample_source_p[0] < sample_source_p[1]
    self._invert_target = sample_target_p[0] < sample_target_p[1]
    # Store the source / target parameters.
    self._p0 = convert(p0,'Pa')
    self._source_dp = convert(source_dp,'Pa')
    self._target_dp = convert(target_dp,'Pa')
    self._source = source
    self._cache = [None, None]  # Store info on last data request
    Var.__init__(self, target_dp.axes, dtype='float32')
    copy_meta (source, self)
  def getview (self, view, pbar):
    import numpy as np
    from regrid_vert import regrid_vert
    import logging
    logger = logging.getLogger(__name__)

    # Un-slice the vertical axis of the target (get the whole domain)
    zdim = self.whichaxis('zaxis')
    zslice = view.slices[zdim]
    view = view.unslice(zdim)

    # Use cached values?
    last_key, cached_data = self._cache
    key = tuple(map(tuple, view.integer_indices))
    if key == last_key:
      target = cached_data

    else:

      # Get the target pressure info
      p0 = view.get(self._p0)
      target_dp = view.get(self._target_dp)
      # Flatten the arrays so they have dimensions [nz, everything else]
      target_shape = target_dp.shape
      nz_target = target_shape[zdim]
      p0 = p0.flatten()
      target_dp = np.rollaxis(target_dp, zdim).reshape(nz_target,-1)
      # Do we need to invert the z-axis of the target?
      if self._invert_target:
        target_dp = target_dp[::-1,:]
      # Compute target plevels
      target_plev = np.empty([target_dp.shape[0]+1,target_dp.shape[1]], dtype='float32')
      target_plev[0,:] = p0
      target_plev[1:,:] = p0.reshape(1,-1) - np.cumsum(target_dp,axis=0)
      # Check for a diagnostic level
      if target_dp[0,0] == 0:
        target_diagnostic_level = True
      else: target_diagnostic_level = False
      del target_dp

      # Get the source values & pressure
      source_view = view.replace_axis(zdim, self._source.zaxis)
      source_dp = source_view.get(self._source_dp)
      source = source_view.get(self._source)
      # Flatten the arrays so they have dimensions [nz, everything else]
      source_shape = source_dp.shape
      nz_source = source_shape[zdim]
      source_dp = np.rollaxis(source_dp, zdim).reshape(nz_source,-1)
      source = np.rollaxis(source, zdim).reshape(nz_source,-1)
      # Do we need to invert the z-axis of the source?
      if self._invert_source:
        source_dp = source_dp[::-1,:]
        source = source[::-1,:]
      # Compute source plevels
      source_plev = np.empty([source_dp.shape[0]+1,source_dp.shape[1]], dtype='float32')
      source_plev[0,:] = p0
      source_plev[1:,:] = p0.reshape(1,-1) - np.cumsum(source_dp,axis=0)
      del source_dp

      # Force the model tops to both be the same.
      # Easiest to just set them both to 0Pa.
      source_plev[-1,:] = 0.
      target_plev[-1,:] = 0.

      # Cast to the expected types
      source_plev = np.asarray(source_plev, dtype='float32')
      target_plev = np.asarray(target_plev, dtype='float32')
      source = np.asarray(source, dtype='float32')

      # Need to transpose to Fortran order?
      source_plev = source_plev.transpose()
      target_plev = target_plev.transpose()
      source = source.transpose()

      # Call the regridding routine
      target, source_colmass, target_colmass = regrid_vert(source_plev, target_plev, source)
      mass_diff = target_colmass - source_colmass
      logger.info("%s average source column mass: %s  average target column mass: %s  maximum difference: %s", self.name, np.mean(source_colmass), np.mean(target_colmass), max(abs(mass_diff)))

      # Transpose to C order
      target = target.transpose()

      # Fill in diagnostic level (won't have any sensible data right now)
      if target_diagnostic_level:
        target[0,:] = target[1,:]

      # Do we need to un-invert the grid?
      if self._invert_target:
        target = target[::-1,:]

      # Add the extra dimensions back in
      target = target.reshape((nz_target,)+target_shape[:zdim]+target_shape[zdim+1:])

      # Put the z-axis in the appropriate spot
      target = target.transpose (range(1,zdim+1)+[0]+range(zdim+1,self.naxes))
      self._cache[:] = key, target


    pbar.update(100)

    # Apply the final slicing
    slices = [slice(None)]*self.naxes
    slices[zdim] = zslice
    return target[slices]

    # Reshape to 2D array (zaxis, everything else)
del Var


# Do the vertical regridding step
def do_vertical_regridding (input_data, grid_data):

  from pygeode.axis import ZAxis
  from interfaces import DataInterface
  from common import compute_pressure, compute_dp
  import logging
  logger = logging.getLogger(__name__)

  source_datasets = list(input_data.datasets)
  target_datasets = []
  for source_dataset in source_datasets:
    target_dataset = []
    target_p = target_dp = None  # Generated further below
    for var in source_dataset.vars:
      # Don't interpolate 2D variables, just copy them.
      if not var.hasaxis('zaxis'):
        target_dataset.append(var)
        continue

      # Skip pressure-related variables (they will be re-generated)
      if var.name in ('air_pressure', 'dp'): continue

      #TODO: check units

      if 'surface_pressure' not in source_dataset or 'air_pressure' not in source_dataset or 'dp' not in source_dataset:
        logger.debug('Dropping field "%s" - no pressure information available to do the vertical interpolation.', var.name)
        continue
      p0 = source_dataset['surface_pressure']
      source_p = source_dataset['air_pressure']
      source_dp = source_dataset['dp']
      # Find the appropriate target grid.
      # If this variable is defined in the grid file, then use that specific grid.
      try:
        dummy_target = grid_data.find_best(var.name)
      # If the variable is not in the grid file, use a default.
      except KeyError:
#        dummy_target = grid_data.find_best('air_pressure')
        dummy_target = grid_data.find_best('dp')

      # Compute the dp for the target grid (forcing the source surface pressure)
      try:
        target_p = compute_pressure(dummy_target.zaxis, p0)
        target_dp = compute_dp(dummy_target.zaxis, p0)
        assert target_p.zaxis == target_dp.zaxis
      except ValueError:
        logger.debug("Skipping %s - unable to get pressure levels and/or dp", var.name)
        target_p = target_dp = None
        continue

      if var.hasaxis('lat') and var.hasaxis('lon'):
        var = VertRegrid(p0, source_p, source_dp, target_p, target_dp, var)
        target_dataset.append(var)
      else:
        logger.debug("Skipping %s - no spatial dimensions.", var.name)

    # Add some pressure information back in
    # (regenerated on appropriate grid).
    if target_p is not None and target_dp is not None:
      # Use the pressure info from the last converted variable
      target_dataset.extend([target_p, target_dp])

    target_datasets.append(target_dataset)

  return DataInterface(target_datasets)

# Alternative method - does a simple linear interpolation
def do_vertical_interpolation (input_data, grid_data):

  from pygeode.interp import interpolate
  from pygeode.axis import ZAxis
  from interfaces import DataInterface
  from common import convert, compute_pressure
  import logging
  logger = logging.getLogger(__name__)

  source_datasets = list(input_data.datasets)
  target_datasets = []
  for source_dataset in source_datasets:
    target_dataset = []
    target_p = None  # Generated further below
    for var in source_dataset.vars:
      # Don't interpolate 2D variables, just copy them.
      if not var.hasaxis('zaxis'):
        target_dataset.append(var)
        continue

      # Skip pressure-related variables (they will be re-generated)
      if var.name in ('air_pressure', 'dp'): continue

      if 'surface_pressure' not in source_dataset or 'air_pressure' not in source_dataset:
        logger.debug('Dropping field "%s" - no pressure information available to do the vertical interpolation.', var.name)
        continue
      p0 = source_dataset['surface_pressure']
      source_p = source_dataset['air_pressure']
      # Find the appropriate target grid.
      # If this variable is defined in the grid file, then use that specific grid.
      try:
        dummy_target = grid_data.find_best(var.name)
      # If the variable is not in the grid file, use a default.
      except KeyError:
#        dummy_target = grid_data.find_best('air_pressure')
        dummy_target = grid_data.find_best('dp')

      # Compute the pressure for the target grid (forcing the source surface pressure)
      try:
        target_p = compute_pressure(dummy_target.zaxis, p0)
      except ValueError:
        logger.debug("Skipping %s - unable to get pressure levels", var.name)
        target_p = None
        continue

      inx = convert(source_p,'Pa').log()
      outx = convert(target_p,'Pa').log()
      if var.hasaxis('lat') and var.hasaxis('lon'):
        var = interpolate (var, inaxis=source_p.zaxis, outaxis=target_p.zaxis, inx=inx,outx=outx, interp_type='linear', d_below=1.0, d_above=1.0)
        target_dataset.append(var)
      else:
        logger.debug("Skipping %s - no spatial dimensions.", var.name)
        continue

    # Add some pressure information back in
    # (regenerated on appropriate grid).
    if target_p is not None:
      # Use the pressure info from the last converted variable
      target_dataset.extend([target_p])

    target_datasets.append(target_dataset)

  return DataInterface(target_datasets)


