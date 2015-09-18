# Apply a global scale factor to the target 3D data, in order to have the
# same mass as the source data.

# Put the mass scaling into a PyGeode operator, to speed it up.
# Otherwise, will end up calculating the (pre-scaled) target mixing ratios
# twice.
# Modified from VertRegrid.
from pygeode.var import Var
class GlobalScale (Var):
  def __init__ (self, var_before, airmass_before, var_after, airmass_after):
    from pygeode.var import Var, copy_meta
    from common import have_repeated_longitude
    assert var_before.axes == airmass_before.axes
    assert var_after.axes == airmass_after.axes
    assert var_before.time == var_after.time
    self._repeated_source_lon = have_repeated_longitude(var_before)
    self._repeated_target_lon = have_repeated_longitude(var_after)
    self._var_before = var_before
    self._airmass_before = airmass_before
    self._var_after = var_after
    self._airmass_after = airmass_after
    self._cache = [None,None]  # Store info on last data request
    Var.__init__(self, var_after.axes, dtype=var_after.dtype)
    copy_meta (var_after, self)
  def getview (self, view, pbar):
    import numpy as np
    import logging
    logger = logging.getLogger(__name__)

    # Un-slice the lat,lon,z axes of the target (get the whole domain)
    #NOTE: assuming the order of dimensions is identical before/after
    latdim = self.whichaxis('lat')
    latslice = view.slices[latdim]
    londim = self.whichaxis('lon')
    lonslice = view.slices[londim]
    zdim = self.whichaxis('zaxis')
    zslice = view.slices[zdim]
    view = view.unslice(latdim,londim,zdim)

    # Use cached values?
    last_key, cached_data = self._cache
    key = tuple(map(tuple, view.integer_indices))
    if key == last_key:
      target = cached_data

    else:

      source_view = view.replace_axis(latdim,self._var_before.lat).replace_axis(londim,self._var_before.lon).replace_axis(zdim,self._var_before.zaxis)
      var_before = source_view.get(self._var_before)
      airmass_before = source_view.get(self._airmass_before)
      mass_before = (var_before*airmass_before)
      if self._repeated_source_lon:
        sl = [slice(None)] * self.naxes
        sl[londim] = slice(None,-1,None)
        mass_before = mass_before[sl]
      for dim in sorted([latdim,londim,zdim], reverse=True):
        mass_before = mass_before.sum(dim)
      del var_before, airmass_before

      var_after = view.get(self._var_after)
      airmass_after = view.get(self._airmass_after)
      mass_after = (var_after*airmass_after)
      if self._repeated_target_lon:
        sl = [slice(None)] * self.naxes
        sl[londim] = slice(None,-1,None)
        mass_after = mass_after[sl]
      for dim in sorted([latdim,londim,zdim], reverse=True):
        mass_after = mass_after.sum(dim)
      del airmass_after

      #NOTE: assuming that the time axis is the leftmost axis
      logger.info ("%s global scale factor to conserve mass: %s", self.name, (mass_before/mass_after))
      target = np.array(var_after)
      target *= (mass_before/mass_after)
      del var_after
      self._cache[:] = key, target

    pbar.update(100)

    # Apply the final slicing
    slices = [slice(None)]*self.naxes
    slices[latdim] = latslice
    slices[londim] = lonslice
    slices[zdim] = zslice
    return target[slices]


del Var

def global_scale (data, original_data, grid_data):
  from common import can_convert, convert, same_times, first_timestep, remove_repeated_longitude
  from interfaces import DataInterface
  import logging
  logger = logging.getLogger(__name__)
  input_datasets = list(data.datasets)
  output_datasets = []
  for input_dataset in input_datasets:
    output_dataset = []
    for var in input_dataset.vars:

      if not can_convert(var, 'molefraction'):
        logger.debug("Not scaling mass of '%s', since it's not a mixing ratio.", var.name)
        output_dataset.append(var)
        continue

      dp, area = grid_data.find_best(['dp','cell_area'])
      dp = convert(dp,'Pa')
      area = convert(area,'m2')
      airmass = dp * area

      try:
        original_var, original_dp, original_area = original_data.find_best([var.name,'dp','cell_area'])
      except KeyError:
        logger.info('Not scaling mass of "%s" - original layer thickness and/or area information is unavailable.', var.name)
        output_dataset.append(var)
        continue

      original_dp = convert(original_dp,'Pa')
      original_area = convert(original_area,'m2')
      original_airmass = original_dp * original_area

      # Need the timesteps to be consistent for all fields.
      var, airmass, original_var, original_airmass = same_times(var, airmass, original_var, original_airmass)

      # Do the scaling
      var = GlobalScale (original_var, original_airmass, var, airmass)

      output_dataset.append(var)
    output_datasets.append(output_dataset)

  return DataInterface(output_datasets)


