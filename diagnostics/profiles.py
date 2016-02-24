# Aircraft profile diagnostic

if True:

  def find_applicable_obs (inputs, fieldname):
    from ..common import have_station_data
    obs_inputs = []
    for x in inputs:
      if any(fieldname in d and 'altitude' in d and have_station_data(d) for d in x.datasets):
        obs_inputs.append(x)
    return obs_inputs

  def find_applicable_models (inputs, fieldname):
    from ..common import have_gridded_3d_data
    model_inputs = []
    for x in inputs:
      if any(fieldname in d and have_gridded_3d_data(d) for d in x.datasets):
        model_inputs.append(x)
    return model_inputs

  def do_all (inputs, fieldname, units, outdir, **kwargs):
    model_inputs = find_applicable_models(inputs, fieldname)
    # If there's no model data to plot, then don't bother plotting!
    if len(model_inputs) == 0: return
    obs_inputs = find_applicable_obs(inputs, fieldname)
    for obs in obs_inputs:
      profiles (obs, model_inputs, fieldname, units, outdir, **kwargs)

  from .timeseries import StationSample

  # Interpolate model data directly to aircraft site locations
  def sample_model_at_obs (model, obs, fieldname, units, z_levels, z_bounds):
    from ..common import have_gridded_3d_data, number_of_levels, number_of_timesteps, find_and_convert, convert
    from pygeode.timeaxis import StandardTime
    from scipy.interpolate import interp1d
    from pygeode.var import Var
    from pygeode.axis import Height
    from pygeode.interp import interpolate
    import numpy as np

    z = Height(z_levels)

    field, gph_field = find_and_convert(model, [fieldname,'geopotential_height'], [units,'m'], requirement=have_gridded_3d_data, maximize = (number_of_levels,number_of_timesteps))

    # Get the time range for the model.
    gettimes = lambda f: zip(*[f.time.auxarrays[v] for v in 'year','month'])
    model_times = gettimes(field)

    outfields = []
    for obsfield,altitude in obs.find(fieldname,'altitude'):

      # Sample the model at the station locations
      outfield = StationSample(field, obsfield.getaxis('station'))
      gph = StationSample(gph_field, obsfield.getaxis('station'))

      # Get the time range for the obs.
      obs_times = gettimes(obsfield)

      # Select the time period with which we have both obs and model data.
      t0 = max(model_times[0],obs_times[0])
      t1 = min(model_times[-1],obs_times[-1])
      # Skip locations where we have no model/obs overlap
      if t1 < t0: continue

      ind = np.where([t >= t0 and t <= t1 for t in model_times])
      outfield = outfield(li_time=ind)

      ind = np.where([t >= t0 and t <= t1 for t in obs_times])
      obsfield = obsfield(li_time=ind)
      altitude = altitude(li_time=ind)

      # Cache the data for faster subsequent access.
      # Disable time splitting for the cache file, since open_multi doesn't work
      # very well with the encoded station data.
      outfield = model.cache.write(outfield, prefix=model.name+'_at_%s_%s_full'%(obs.name,fieldname), split_time=False)
      gph = model.cache.write(gph, prefix=model.name+'_at_%s_%s_full'%(obs.name,'geopotential_height'), split_time=False)

      # Interpolate the model to the fixed vertical levels.
      outfield = interpolate(outfield, inaxis='zaxis', outaxis=z, inx=gph)
      outfield = model.cache.write(outfield, prefix=model.name+'_at_%s_%s_zinterp'%(obs.name,fieldname), split_time=False)

      # Bin the aircraft data into the fixed levels.
      binned_data = np.empty(obsfield.shape+(len(z_levels),))
      binned_data[()] = float('nan')
      obsfield = obsfield.load()
      altitude = altitude.load()
      for i in range(len(z_levels)):
        match = (altitude.values >= z_bounds[i]) & (altitude.values < z_bounds[i+1])
        match = np.where(match)
        binned_data[...,i][match] = obsfield.values[match]

      obsfield = Var(axes=obsfield.axes+(z,), values=binned_data, name=obsfield.name)

      # Just for a test
      obsfield = model.cache.write(obsfield, prefix=obs.name+'_%s_zbin'%fieldname, split_time=False)

      outfields.append((obsfield,outfield))

    return outfields



  def profiles (obs, models, fieldname, units, outdir):

    import numpy as np
    import matplotlib.pyplot as pl
    from os.path import exists
    from ..common import convert, select_surface, to_datetimes

    # The fixed height levels to interpolate the model data to
    z_levels =   [1000.,2000.,3000.,4000.,5000.,6000.]
    z_bounds = [500.,1500.,2500.,3500.,4500.,5500.,6500.]

    for m in models:
      for obsfield, modelfield in sample_model_at_obs(m,obs,fieldname,units,z_levels,z_bounds):
        pass

    return

    model_line_colours = [m.color for m in models]
    model_line_styles = [m.linestyle for m in models]
    obs_line_colour = obs.color
    obs_line_style = obs.linestyle
    model_markers = [m.marker for m in models]
    obs_marker = obs.marker

    model_data = []
    model_spread = []
    for m in models:
      field = sample_model_at_obs(m,obs,fieldname,units)
      model_data.append(field)
      try:
        field = sample_model_at_obs(m,obs,fieldname+'_ensemblespread',units)
        model_spread.append(field)
      except KeyError:  # No ensemble spread for this model data
        model_spread.append(None)

    obs_data = obs.find_best(fieldname)
    obs_data = select_surface(obs_data)
    # Cache the observation data, for faster subsequent access
    obs_data = obs.cache.write(obs_data, prefix=obs.name+'_sfc_%s'%fieldname, split_time=False)

    obs_data = convert(obs_data, units, context=fieldname)
    try:
      obs_stderr = obs.find_best(fieldname+'_std')
      obs_stderr = select_surface(obs_stderr)
      # Cache the observation data, for faster subsequent access
      obs_stderr = obs.cache.write(obs_stderr, prefix=obs.name+'_sfc_%s_std'%fieldname, split_time=False)
      obs_stderr = convert(obs_stderr, units, context=fieldname)
    except KeyError:
      obs_stderr = None

    # Combine model and obs data together into one set
    data = model_data + [obs_data]
    spread = model_spread + [obs_stderr]
    line_colours = model_line_colours[:len(model_data)] + [obs_line_colour]
    line_styles = model_line_styles + [obs_line_style]
    markers = model_markers + [obs_marker]

    # Use the first model data as a basis for the time axis.
    timeaxis = (d.getaxis('time') for d in data).next()
    # Limit the range to plot
    if plot_months is not None:
      timeaxis = timeaxis(year=2009,month=plot_months)
    times = timeaxis.get()
    time1 = min(times)
    time2 = max(times)

    data = [d(time=(time1,time2)) for d in data]
    spread = [None if s is None else s(time=(time1,time2)) for s in spread]

    # Create plots of each location
    # Plot 4 timeseries per figure
    n = 4
    for i,location in enumerate(data[0].station):
      if i%n == 0:
        fig = pl.figure(figsize=(figwidth,12))
      pl.subplot(4,1,i%4+1)
      station_info = data[0](station=location).getaxis("station")
      lat = station_info.lat[0]
      lon = station_info.lon[0]

      # Construct a title for the plot
      title = location + ' - (%4.2f'%abs(lat)
      if lat < 0: title += 'S'
      else: title += 'N'
      title += ',%5.2f'%abs(lon)
      if lon < 0: title += 'W'
      else: title += 'E'
      title += ')'
      if hasattr(station_info,'country'):
        title += ' - ' + station_info.country[0]

      # Fix issue with certain characters in station names
      title = title.decode('latin-1')

      for j in range(len(data)):
        dates = to_datetimes(data[j].time)
        values = data[j].get(station=location).flatten()

        # Determine marker size based on the density of observations
        timevalues = data[j](station=location).time.values
        timevalues = timevalues[np.isfinite(values)]
        dt = filter(None,np.diff(timevalues))
        if len(dt) > 0:
          # Choose a representative dt.
          dt = sorted(dt)[len(dt)/2]
        else:
          dt = float('nan')
        count = (time2-time1) / dt
        # Size of marker (in points) for roughly no overlap
        markersize = figwidth * 72.0 / count
        markersize = max(markersize,1.0)
        markersize = min(markersize,10.0)
        if np.isnan(markersize):
          markersize = 1.0

        # Draw standard deviation?
        if spread[j] is not None:
          std = spread[j].get(station=location).flatten()
          fill_min = values - 2*std
          fill_max = values + 2*std
          fill_mask = np.isfinite(fill_max)
          pl.fill_between(dates, fill_min, fill_max, where=fill_mask, color=line_colours[j], linewidth=0, alpha=0.5)
        pl.plot(dates, values, color=line_colours[j], linestyle=line_styles[j], marker=markers[j], markersize=markersize, markeredgecolor=line_colours[j])

      pl.title(title)
      pl.ylabel('%s %s'%(fieldname,units))

      # Things to do one the last plot of the figure
      if i%4 == 3:
        # Put a legend on the last plot
        labels = [d.title for d in models+[obs]]
        pl.legend(labels)

        # Save as an image file.
        outfile = "%s/%s_timeseries_%s_%02d.png"%(outdir,'_'.join(d.name for d in models+[obs]),fieldname,i/4+1)
        if not exists(outfile):
          fig.savefig(outfile)

        pl.close(fig)

