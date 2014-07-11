# Timeseries diagnostic

# Criteria for getting the data closest to the surface
# (and the maximum number of timesteps)
def surface_output_frequency (varlist):
  from common import closeness_to_surface, number_of_timesteps
  # Rank by closeness to surface first, then # of timesteps for tiebreaker
  return closeness_to_surface(varlist), number_of_timesteps(varlist)

#TODO: Interpolate directly to station locations
# This method computes the surface values of a model dataset
def get_sfc_data (model, fieldname):
  from common import select_surface, have_gridded_data
  field = model.data.find_best(fieldname, requirement=have_gridded_data, maximize = surface_output_frequency)
  field = select_surface(field)
  # Cache the data for faster subsequent access
  field = model.cache.write(field, prefix='sfc_'+fieldname)
  return field

# Get the ensemble mean surface values
# (or, the regular surface data for non-ensemble runs)
def get_sfc_mean (model, standard_name):
  for fieldname in standard_name, standard_name+"_ensemblemean":
    if model.data.have(fieldname):
      return get_sfc_data (model, fieldname)
  raise KeyError ("Can't find '%s' in '%s'"%(standard_name, model.name))

# Get the ensemble spread surface values (where applicable)
def get_sfc_std (model, standard_name):
  return get_sfc_data (model, standard_name+"_ensemblespread")


def timeseries (datasets, fieldname, units, outdir, plot_months=None):

  from plot_shortcuts import plot, plot_stdfill
  from plot_wrapper import Multiplot, Legend, Overlay
  import matplotlib.pyplot as pl
  from pygeode.timeaxis import months

  from os.path import exists

  from common import unit_scale

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
      sfc_data.append(get_sfc_mean(d,fieldname))
    except KeyError:
      # Put a 'None' placeholder to indicate this isn't model surface data
      sfc_data.append(None)

  sfc_std = []
  for d in datasets:
    try:
      sfc_std.append(get_sfc_std(d,fieldname))
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
      assert len(val) == 1
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
        data = d.get_data(location,fieldname,'mean')
        series.append(data)
        std.append(d.get_data(location,fieldname,'std'))

    # Scale to the plot units
    for i,x in enumerate(series):
      input_units = x.atts['units']
      if input_units == units: continue  # already in the correct units
      x = x / unit_scale[input_units] * unit_scale[units]
      x.name = fieldname
      series[i] = x
      if std[i] is not None:
        std[i] = std[i] / unit_scale[input_units] * unit_scale[units]

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

