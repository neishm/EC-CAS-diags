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
def do_vertical_regridding (input_data, grid_data, conserve_mass, sample_field=None):

  from pygeode.interp import interpolate
  from interfaces import DataInterface
  from common import compute_pressure, compute_dp, have_gridded_3d_data, find_and_convert, convert
  import logging
  logger = logging.getLogger(__name__)
  regridded_dataset = []
  #TODO: handle multiple target grids
  if sample_field is not None:
    target_grid = grid_data.find_best(sample_field)
  else:
    # Find all z-axes
    lev_test = []
    for dataset in grid_data:
      for var in dataset:
        if var.hasaxis('zaxis'):
          z = var.getaxis('zaxis')
          lev_test.append((len(z),var))
          break
    del dataset, var
    # Pick the z-axis with the most number of levels.
    nlev, target_grid = max(lev_test)

  varnames = sorted(set(v.name for d in input_data.datasets for v in d))

  for varname in varnames:

    # Don't interpolate 2D variables, just copy them.
    var_test = input_data.find_best(varname)
    if not var_test.hasaxis('zaxis'):
      regridded_dataset.append(var_test)
      continue

    # Skip pressure-related variables (they will be re-generated)
    if varname in ('air_pressure', 'dp'): continue

    # Skip fields with no unit information
    if 'units' not in var_test.atts:
      logger.debug("Skipping %s - no units found.", varname)
      continue

    try:
      if conserve_mass:
        var, source_dp, source_p0, source_p = find_and_convert (input_data, [varname,'dp','surface_pressure','air_pressure'], ['g g(air)-1','Pa','Pa','Pa'], requirement=have_gridded_3d_data)
      else:
        var_units = var_test.atts['units']
        var, source_p0, source_p = find_and_convert (input_data, [varname,'surface_pressure','air_pressure'], [var_units,'Pa','Pa'], requirement=have_gridded_3d_data)
        # Special case: density should be normalized to a pseudo mass mixing
        # ratio.  Otherwise, extrapolation above the source lid can have
        # unrealistic values.
        #TODO: generalize this to all density units.
        if var_units == "molecules cm-3":
          var_specie = var.atts.get('specie',None)
          var /= source_p

    except ValueError as e:
      logger.debug('Dropping field "%s" - %s', varname, e.message)
      continue

    # Compute the dp for the target grid (forcing the source surface pressure)
    try:
      target_p = compute_pressure(target_grid.zaxis, source_p0)
      target_dp = compute_dp(target_grid.zaxis, source_p0)
      assert target_p.zaxis == target_dp.zaxis
    except ValueError:
      logger.debug("Skipping %s - unable to get pressure levels and/or dp", var.name)
      continue

    # Regrid the variable
    if conserve_mass:
      var = VertRegrid(source_p0, source_p, source_dp, target_p, target_dp, var)
    else:
      inx = convert(source_p,'Pa').log()
      outx = convert(target_p,'Pa').log()
      var = interpolate (var, inaxis=source_p.zaxis, outaxis=target_p.zaxis, inx=inx, outx=outx, interp_type='linear', d_below=0, d_above=0)
      # Restore density units after possible extrapolation.
      if var_units == "molecules cm-3":
        var *= target_p
        var.name = varname
        var.atts['units'] = var_units
        if var_specie is not None: var.atts['specie'] = var_specie

    regridded_dataset.append(var)

  # Add some pressure information back in
  # (regenerated on appropriate grid).
  try:
    regridded_dataset.append(target_dp)
  except NameError: pass

  return DataInterface([regridded_dataset])

