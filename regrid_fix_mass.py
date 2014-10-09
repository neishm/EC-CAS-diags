# Apply a global scale factor to the target 3D data, in order to have the
# same mass as the source data.
def global_scale (data, original_data, grid_data):
  from common import can_convert, convert, same_times, first_timestep, remove_repeated_longitude
  from data_interface import DataInterface
  from pygeode.var import copy_meta
  input_datasets = list(data.datasets)
  output_datasets = []
  for input_dataset in input_datasets:
    output_dataset = []
    for var in input_dataset.vars:

      if not can_convert(var, 'molefraction'):
        print "Not scaling mass of '%s', since it's not a mixing ratio."%var.name
        output_dataset.append(var)
        continue

      dp, area = grid_data.find_best(['dp','cell_area'])
      dp = convert(dp,'Pa')
      area = convert(area,'m2')

      try:
        original_var, original_dp, original_area = original_data.find_best([var.name,'dp','cell_area'])
      except KeyError:
        print 'Not scaling mass of "%s" - original layer thickness and/or area information is unavailable.'%var.name
###        output_dataset.append(var)
        continue

      original_dp = convert(original_dp,'Pa')
      original_area = convert(original_area,'m2')
      # Need the timesteps to be consistent for all fields.
      var, dp, area, original_var, original_dp, original_area = same_times(var, dp, area, original_var, original_dp, original_area)

      original_mass = original_var * original_dp * original_area
      original_mass = remove_repeated_longitude(original_mass).sum('lat','lon','zaxis')
      mass = var * dp * area
      mass = remove_repeated_longitude(mass).sum('lat','lon','zaxis')

      # Do the scaling
      orig = var
      var = var / mass * original_mass
      copy_meta (orig, var)

      output_dataset.append(var)
    output_datasets.append(output_dataset)

  return DataInterface(output_datasets)


