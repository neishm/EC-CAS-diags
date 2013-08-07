# CO2 timeseries

def timeseries (datasets, fieldname, outdir):

  from plot_shortcuts import plot
  from plot_wrapper import Multiplot, Legend
  import matplotlib.pyplot as pl
  from pygeode.timeaxis import months

  from os.path import exists

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
      sfc_data.append(d.get_data('sfc',fieldname))
    except KeyError:
      sfc_data.append(None)

  # Use the first model data as a basis for the time axis.
  timeaxis = (s.getaxis('time') for s in sfc_data if s is not None).next()
  # Limit the range to plot
  #timeaxis = timeaxis(year=2009,month=(6,9))
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
    for s,d in zip(sfc_data,datasets):
      if s is not None:
        series.append(s(lat=lat, lon=lon))
      else:
        # For now, assume that we have exactly one obs dataset,
        # so this command shouldn't fail.
        series.append(d.get_data(location,fieldname+'_mean'))

    # Limit the time period to plot
    series = [x(time=(time1,time2)) for x in series]

    units = series[0].atts.get('units','')
    theplot = plot (*series, title=title,
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

