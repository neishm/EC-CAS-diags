# Timeseries diagnostic

#TODO: Interpolate directly to station locations
# This method computes the surface values of a model dataset
def get_sfc_data (model, fieldname):
  from common import select_surface, have_gridded_data, closeness_to_surface, number_of_timesteps
  field = model.data.find_best(fieldname, requirement=have_gridded_data, maximize = (closeness_to_surface,number_of_timesteps))
  field = select_surface(field)
  # Cache the data for faster subsequent access
  field = model.cache.write(field, prefix='sfc_'+fieldname)
  return field

# Get station data.
# Assume there is only one dataset, with station data in it.
def get_station_data (obs, location, fieldname):
  import numpy as np
  field = obs.data.find_best(fieldname)
  stations = field.station.values
  if location not in stations:
    raise KeyError ("Station '%s' not found in obs"%location)
  return field(station=location).squeeze('station')  # No caching


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



def timeseries (datasets, fieldname, units, outdir, plot_months=None):

  from plot_shortcuts import plot, plot_stdfill
  from plot_wrapper import Multiplot, Legend, Overlay
  import matplotlib.pyplot as pl
  from pygeode.timeaxis import months

  from os.path import exists

  from common import convert

  line_colours = ['blue', 'green', 'red']

  datasets = [d for d in datasets if d is not None]

  # Extract all observation locations from the datasets
  obs_locations = {}
  for d in datasets:
    if hasattr(d,'obs_locations'):
      obs_locations.update(d.obs_locations)

#  ##TODO
#  # Limit the time period to the current experiment
#  # (sometimes we have a really short experiment)
#  timeaxis = model_data[0].time
#  times = timeaxis.get()
#  time1 = min(times)
#  time2 = max(times)
#  obs_f = obs_f(time=(time1,time2))
#  model_data = [x(time=(time1,time2)) for x in model_data]

  # For model data, pre-fetch the surface data
  sfc_data = []
  for d in datasets:
    try:
      sfc_data.append(get_sfc_data(d,fieldname))
    except KeyError:
      # Put a 'None' placeholder to indicate this isn't model surface data
      sfc_data.append(None)

  sfc_std = []
  for d in datasets:
    try:
      # Try finding an ensemble spread
      sfc_std.append(get_sfc_data(d,fieldname+'_ensemblespread'))
    except KeyError:
      # Put a 'None' placeholder to indicate this isn't model surface data
      sfc_std.append(None)

  # Use the first model data as a basis for the time axis.
  timeaxis = (s.getaxis('time') for s in sfc_data if s is not None).next()
  # Limit the range to plot
  if plot_months is not None:
    timeaxis = timeaxis(year=2009,month=plot_months)
  times = timeaxis.get()
  time1 = min(times)
  time2 = max(times)

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
  for location, (lat, lon, country) in sorted(obs_locations.items()):

    # Construct a title for the plot
    title = location + ' - (%4.2f'%abs(lat)
    if lat < 0: title += 'S'
    else: title += 'N'
    title += ',%5.2f'%abs(lon)
    if lon < 0: title += 'W'
    else: title += 'E'
    title += ') - ' + country

    if lon < 0: lon += 360  # Model data is from longitudes 0 to 360

    series = []
    std = []
    plot_units = ''
    for s,sd,d in zip(sfc_data,sfc_std,datasets):
      if s is not None:
        series.append(s(lat=lat, lon=lon))
        if sd is not None:
          std.append(sd(lat=lat,lon=lon))
        else:
          std.append(None)
      else:
        # For now, assume that we have an obs dataset,
        # so this command shouldn't fail.
        data = get_station_data(d, location,fieldname)
        series.append(data)
        std.append(get_station_data(d, location,fieldname+'_std'))

    # Scale to the plot units
    for i,x in enumerate(series):
      series[i] = convert(x,units)
      if std[i] is not None:
        std[i] = convert(std[i],units)

    # Limit the time period to plot
    series = [x(time=(time1,time2)) for x in series]
    std = [s(time=(time1,time2)) if s is not None else None for s in std]

    parts = []
    for i in range(len(series)):
      color=line_colours[i]
      if std[i] is not None:
        parts.append(plot_stdfill(series[i],2*std[i],color=color))
      else:
        parts.append(plot(series[i],color=color))

    theplot = Overlay (*parts, title=title.decode('latin-1'),
           xlabel='', ylabel='%s %s'%(fieldname,units), xticks=xticks, xticklabels=xticklabels)
    plots.append (theplot)


  # Plot 4 timeseries per figure
  n = 4
  for i in range(0,len(plots),4):
    fig = pl.figure(figsize=(15,12))

    theplots = plots[i:i+4]
    # Put a legend on the last plot
    labels = [d.title for d in datasets]
    theplots[-1] = Legend(theplots[-1], labels)

    theplots = Multiplot([[p] for p in theplots])
    theplots.render(figure=fig)

    outfile = "%s/%s_timeseries_%s_%02d.png"%(outdir,'_'.join(d.name for d in datasets),fieldname,i/4+1)
    if not exists(outfile):
      fig.savefig(outfile)

    pl.close(fig)

