# Timeseries diagnostic

# This method computes the surface values of a model dataset
def get_sfc_data (model, fieldname):
  from common import select_surface, have_gridded_data, closeness_to_surface, number_of_timesteps
  field = model.data.find_best(fieldname, requirement=have_gridded_data, maximize = (closeness_to_surface,number_of_timesteps))
  field = select_surface(field)
  # Cache the data for faster subsequent access
  field = model.cache.write(field, prefix='sfc_'+fieldname)
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
def sample_model_at_obs (model, obs, fieldname):
  from common import select_surface, have_gridded_data, closeness_to_surface, number_of_timesteps
  from station_data import station_axis_save_hook, station_axis_load_hook
  field = model.data.find_best(fieldname, requirement=have_gridded_data, maximize = (closeness_to_surface,number_of_timesteps))
  field = select_surface(field)

  series = obs.data.find_best(fieldname)

  # Sample at the station locations
  field = StationSample(field, series.getaxis('station'))

  # Cache the data for faster subsequent access.
  # Disable time splitting for the cache file, since open_multi doesn't work
  # very well with the encoded station data.
  field = model.cache.write(field, prefix='at_%s_%s'%(obs.name,fieldname), save_hooks=[station_axis_save_hook], load_hooks=[station_axis_load_hook], split_time=False)
  return field



def timeseries (obs, models, fieldname, units, outdir, plot_months=None):

  from plot_shortcuts import plot, plot_stdfill
  from plot_wrapper import Multiplot, Legend, Overlay
  import matplotlib.pyplot as pl
  from pygeode.timeaxis import months

  from os.path import exists

  from common import convert, select_surface

  model_line_colours = ['blue', 'red']
  obs_line_colour = 'green'

  models = [m for m in models if m is not None]

  model_data = []
  model_spread = []
  for m in models:
    field = sample_model_at_obs(m,obs,fieldname)
    field = convert(field, units, context=fieldname)
    model_data.append(field)
    try:
      field = sample_model_at_obs(m,obs,fieldname+'_ensemblespread')
      field = convert(field, units, context=fieldname)
      model_spread.append(field)
    except KeyError:  # No ensemble spread for this model data
      model_spread.append(None)

  obs_data = obs.data.find_best(fieldname)
  obs_data = select_surface(obs_data)
  # Cache the observation data, for faster subsequent access
  obs_data = obs.cache.write(obs_data, prefix='sfc_%s'%fieldname, split_time=False)

  obs_data = convert(obs_data, units, context=fieldname)
  try:
    obs_stderr = obs.data.find_best(fieldname+'_std')
    obs_stderr = convert(obs_stderr, units, context=fieldname)
  except KeyError:
    obs_stderr = None

  # Combine model and obs data together into one set
  data = model_data + [obs_data]
  spread = model_spread + [obs_stderr]
  line_colours = model_line_colours[:len(model_data)] + [obs_line_colour]

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
  xticks = []
  xticklabels = []

  # Determine the frequency of day ticks, based on the number of months of data
  nmonths = len(set(timeaxis.month))
  if nmonths == 1:
    daylist = range(1,32)
  else:
    daylist = (1,15)

  # Set the ticks
  for month in sorted(list(set(timeaxis.month))):
    for day in daylist:
      val = timeaxis(month=month,day=day,hour=0).get()
      if len(val) == 0: continue
      xticks.append(float(val[0]))
      xticklabels.append("%s %d"%(months[month], day))

  plots = []
  for location in data[0].station:
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

    parts = []
    for i in range(len(data)):
      if spread[i] is not None:
        parts.append(plot_stdfill(data[i](station=location),2*spread[i](station=location),color=line_colours[i]))
      else:
        parts.append(plot(data[i](station=location),color=line_colours[i]))

    theplot = Overlay (*parts, title=title.decode('latin-1'),
           xlabel='', ylabel='%s %s'%(fieldname,units), xticks=xticks, xticklabels=xticklabels)
    plots.append (theplot)


  # Plot 4 timeseries per figure
  n = 4
  for i in range(0,len(plots),4):
    fig = pl.figure(figsize=(15,12))

    theplots = plots[i:i+4]
    # Put a legend on the last plot
    labels = [d.title for d in models+[obs]]
    theplots[-1] = Legend(theplots[-1], labels)

    theplots = Multiplot([[p] for p in theplots])
    theplots.render(figure=fig)

    outfile = "%s/%s_timeseries_%s_%02d.png"%(outdir,'_'.join(d.name for d in models+[obs]),fieldname,i/4+1)
    if not exists(outfile):
      fig.savefig(outfile)

    pl.close(fig)

