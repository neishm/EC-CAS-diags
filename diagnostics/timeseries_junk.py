# Timeseries diagnostic

if True:

  def find_applicable_obs (inputs, fieldname):
    from ..common import have_station_data
    obs_inputs = []
    for x in inputs:
      if any(fieldname in d and have_station_data(d) for d in x.datasets):
        obs_inputs.append(x)
    return obs_inputs

  def find_applicable_models (inputs, fieldname):
    from ..common import have_gridded_data
    model_inputs = []
    for x in inputs:
      if any(fieldname in d and have_gridded_data(d) for d in x.datasets):
        model_inputs.append(x)
    return model_inputs

  # Interpolate model data directly to station locations
  #TODO: remove this, once other timeseries-type diagnostics are refactored.
  def sample_model_at_obs (model, obs, fieldname, units, suffix=""):
    from ..common import select_surface, have_gridded_data, closeness_to_surface, number_of_timesteps, find_and_convert
    from .station import StationSample
    field = find_and_convert(model, fieldname, units, requirement=have_gridded_data, maximize = (closeness_to_surface,number_of_timesteps))
    field = select_surface(field)

    series = obs.find_best(fieldname)

    # Sample at the station locations
    field = StationSample(field, series.getaxis('station'))

    # Cache the data for faster subsequent access.
    # Disable time splitting for the cache file, since open_multi doesn't work
    # very well with the encoded station data.
    field = model.cache.write(field, prefix=model.name+'_at_%s_%s%s'%(obs.name,fieldname,suffix), split_time=False)
    return field


