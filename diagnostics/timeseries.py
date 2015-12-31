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

  def do_all (inputs, fieldname, units, outdir, **kwargs):
    model_inputs = find_applicable_models(inputs, fieldname)
    # If there's no model data to plot, then don't bother plotting!
    if len(model_inputs) == 0: return
    obs_inputs = find_applicable_obs(inputs, fieldname)
    for obs in obs_inputs:
      timeseries (obs, model_inputs, fieldname, units, outdir, **kwargs)


  # This method computes the surface values of a model dataset
  def get_sfc_data (model, fieldname):
    from ..common import select_surface, have_gridded_data, closeness_to_surface, number_of_timesteps
    field = model.find_best(fieldname, requirement=have_gridded_data, maximize = (closeness_to_surface,number_of_timesteps))
    field = select_surface(field)
    # Cache the data for faster subsequent access
    field = model.cache.write(field, prefix=model.name+'_sfc_'+fieldname)
    return field

  # Sample a model field at station locations
  from pygeode.var import Var
  class StationSample(Var):
    def __init__ (self, model_data, station_axis):
      from pygeode.var import Var, copy_meta
      import numpy as np
      # Determine which model lat/lon indices to sample at
      lat_indices = []
      lon_indices = []
      for lat in station_axis.lat:
        lat_indices.append(np.argmin(abs(model_data.lat.values-lat)))
      for lon in station_axis.lon:
        lon_indices.append(np.argmin(abs(model_data.lon.values%360-lon%360)))
      self.lat_indices = lat_indices
      self.lon_indices = lon_indices
      # Replace lat/lon axes with the station axis
      lat_iaxis = model_data.whichaxis('lat')
      lon_iaxis = model_data.whichaxis('lon')
      axes = list(model_data.axes)
      axes[lat_iaxis] = station_axis
      axes = axes[:lon_iaxis]+axes[lon_iaxis+1:]
      Var.__init__(self, axes, dtype=model_data.dtype)
      copy_meta(model_data,self)
      self.model_data = model_data
      self.station_axis = station_axis
      self.station_iaxis = self.whichaxis('station')
      self.lat_iaxis = lat_iaxis
      self.lon_iaxis = lon_iaxis
    def getview (self, view, pbar):
      import numpy as np
      from pygeode.tools import loopover
      out = np.empty(view.shape, dtype=self.dtype)
      v = view.remove(self.station_iaxis)
      station_axis = self.station_axis
      istation = self.station_iaxis
      for outsl, (indata,) in loopover(self.model_data, v, pbar=pbar):
        # Make sure we have a full lat/lon field to slice from
        # (otherwise, this routine would have to be re-written)
        lat_iaxis = self.lat_iaxis
        lon_iaxis = self.lon_iaxis
        assert indata.shape[lat_iaxis] == self.model_data.shape[lat_iaxis]
        assert indata.shape[lon_iaxis] == self.model_data.shape[lon_iaxis]
        for i,station in enumerate(station_axis.values):
          # Inject the station index into the output slice
          full_outsl = outsl[:istation]+(i,)+outsl[istation:]
          insl = [slice(None)]*self.model_data.naxes
          insl[lat_iaxis] = self.lat_indices[i]
          insl[lon_iaxis] = self.lon_indices[i]
          out[full_outsl] = indata[insl]
      pbar.update(100)
      return out
  del Var

  # Interpolate model data directly to station locations
  #TODO: interpolate to the station height.
  def sample_model_at_obs (model, obs, fieldname, units):
    from ..common import select_surface, have_gridded_data, closeness_to_surface, number_of_timesteps, find_and_convert
    field = find_and_convert(model, fieldname, units, requirement=have_gridded_data, maximize = (closeness_to_surface,number_of_timesteps))
    field = select_surface(field)

    series = obs.find_best(fieldname)

    # Sample at the station locations
    field = StationSample(field, series.getaxis('station'))

    # Cache the data for faster subsequent access.
    # Disable time splitting for the cache file, since open_multi doesn't work
    # very well with the encoded station data.
    field = model.cache.write(field, prefix=model.name+'_at_%s_%s'%(obs.name,fieldname), split_time=False)
    return field



  def timeseries (obs, models, fieldname, units, outdir, plot_months=None):

    import numpy as np
    import matplotlib.pyplot as pl
    from os.path import exists
    from ..common import convert, select_surface, to_datetimes

    figwidth = 15

    models = [m for m in models if m is not None]

    if obs.color is not None:
      model_line_colours = [m.color for m in models]
      obs_line_colour = obs.color
    else:
      model_line_colours = ['blue', 'red']
      obs_line_colour = 'green'

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
    line_styles = ['-']*len(model_data) + ['None']
    markers = ['None']*len(model_data) + ['o']

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
        dt = min(filter(None,np.diff(values)))
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

