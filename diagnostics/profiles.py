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

  # Find all unique observation fields
  # Discards identical fields from superset domains.
  def find_obs(obs, *fieldnames):
    handled = []
    for data in obs.find(*fieldnames):
      if isinstance(data,list):
        key = data[0].axes
      else:
        key = data.axes
      if key not in handled:
        yield data
      handled.append(key)

  # Bin the obs data into fixed levels
  def bin_obs (obs, fieldname, units, z_levels, z_bounds, years):
    from ..common import convert
    from pygeode.var import Var
    from pygeode.axis import Height
    import numpy as np

    z = Height(z_levels)

    outfields = []
    for obsfield,altitude in find_obs(obs,fieldname,'altitude'):

      obsfield = obsfield(l_year=years)
      altitude = altitude(l_year=years)

      obsfield = convert(obsfield,units)

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

      # Cache the binned data
#      obsfield = obs.cache.write(obsfield, prefix=obs.name+'_%s_zbin'%fieldname, split_time=False)

      outfields.append(obsfield)

    return outfields


  # Interpolate model data directly to aircraft site locations
  def sample_model_at_obs (model, obs, fieldname, units, z_levels, z_bounds, years):
    from ..common import have_gridded_3d_data, number_of_levels, number_of_timesteps, find_and_convert
    from pygeode.axis import Height
    from pygeode.interp import interpolate
    from ..station_data import Station

    z = Height(z_levels)

    field, gph_field = find_and_convert(model, [fieldname,'geopotential_height'], [units,'m'], requirement=have_gridded_3d_data, maximize = (number_of_levels,number_of_timesteps))

    # Concatenate all the available station locations into a single coordinate.
    station_names = []
    auxarrays = {}
    for obsfield in find_obs(obs,fieldname):
      station_names.extend(obsfield.station.values)
      for key, value in obsfield.station.auxarrays.iteritems():
        auxarrays.setdefault(key,[]).extend(value)
    stations = Station(values=station_names, **auxarrays)

    # Sample the model at the station locations
    outfield = StationSample(field, stations)
    gph = StationSample(gph_field, stations)

    outfield = outfield(l_year=years)
    gph = gph(l_year=years)

    # Cache the data for faster subsequent access.
      # Disable time splitting for the cache file, since open_multi doesn't work
    # very well with the encoded station data.
    print 'Sampling %s data at %s'%(model.name, list(outfield.station.values))
    outfield = model.cache.write(outfield, prefix=model.name+'_at_%s_%s_full'%(obs.name,fieldname), split_time=False)
    gph = model.cache.write(gph, prefix=model.name+'_at_%s_%s_full'%(obs.name,'geopotential_height'), split_time=False)

    # Interpolate the model to the fixed vertical levels.
    outfield = interpolate(outfield, inaxis='zaxis', outaxis=z, inx=gph)
    outfield = model.cache.write(outfield, prefix=model.name+'_at_%s_%s_zinterp'%(obs.name,fieldname), split_time=False)

    return [outfield]


  # Take an average of all pieces of data given
  # (averaged over all dimensions except height)
  def average_profile(data):
    import numpy as np
    from pygeode.concat import concat
    zindex = data[0].whichaxis('zaxis')
    zaxis = data[0].getaxis('zaxis')
    # Temporal average
    data = [v for v in data if len(v.time) > 0] # Ignore time periods with no data
    data = [v.nanmean('time') for v in data]
    # Average over all stations
    data = np.concatenate([d.get() for d in data])
    sum = np.nansum(data,axis=0)
    count = np.sum(np.isfinite(data),axis=0)
    data = sum/count
    return data

  def profiles (obs, models, fieldname, units, outdir):

    import numpy as np
    import matplotlib.pyplot as pl
    import numpy as np
    from os.path import exists
    from ..common import convert, select_surface, to_datetimes

    years = [2009,2010]
    year_string = str(years[0]) if len(years) == 1 else str(years[0])+'-'+str(years[-1])

    # The fixed height levels to interpolate the model data to
    z_levels =   [1000.,2000.,3000.,4000.,5000.,6000.]
    z_bounds = [500.,1500.,2500.,3500.,4500.,5500.,6500.]

    monthly_model = [dict() for m in range(len(models))]
    monthly_obs = dict()

    for obsfield in bin_obs(obs, fieldname, units, z_levels, z_bounds, years):
      for month in range(1,13):
        monthly_obs.setdefault(month,[]).append(obsfield(month=month))

    for i,model in enumerate(models):
      for modelfield in sample_model_at_obs(model, obs, fieldname, units, z_levels, z_bounds, years):
        for month in range(1,13):
          monthly_model[i].setdefault(month,[]).append(modelfield(month=month))

    fig = pl.figure(figsize=(6,6))

    season = 'Jan-Feb-Mar'
    months = [1,2,3]

    outfile = "%s/%s_timeseries_%s_%s_%s.png"%(outdir,'_'.join(d.name for d in models+[obs]),fieldname,season,year_string)

    obs_data = sum([monthly_obs[m] for m in months],[])
    obs_data = average_profile(obs_data)
    model_data = []
    for monthly_mod in monthly_model:
      mod_data = sum([monthly_mod[m] for m in months],[])
      mod_data = average_profile(mod_data)
      model_data.append(mod_data)

    ax = pl.subplot(111)
    for i in range(len(models)):
      pl.plot(model_data[i], z_levels, color=models[i].color, linestyle=models[i].linestyle, marker=models[i].marker, markersize=10, markeredgecolor=models[i].color, label=models[i].name)
    pl.plot(obs_data, z_levels, color=obs.color, linestyle=obs.linestyle, marker=obs.marker, markersize=10, markeredgecolor=obs.color, label='obs')
    pl.title('%s (%s)'%(season,year_string))
#    pl.xticks(np.linspace(388,393,6))
#    pl.xlim(387.5,393)
    pl.xlabel('%s [%s]'%(fieldname,units))
    pl.ylabel('Altitude [m]')
    pl.legend(loc='best')

    fig.savefig(outfile)

    return

    #TODO
#    # Get the time range for the model.
#    gettimes = lambda f: zip(*[f.time.auxarrays[v] for v in 'year','month'])
#
#    # Select the time period with which we have both obs and model data.
#    t0 = max(model_times[0],obs_times[0])
#    t1 = min(model_times[-1],obs_times[-1])
#    # Skip locations where we have no model/obs overlap
#    if t1 < t0: continue
#
#    ind = np.where([t >= t0 and t <= t1 for t in model_times])
#    outfield = outfield(li_time=ind)

    #TODO

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

