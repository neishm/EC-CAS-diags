# CO2 timeseries

def timeseries (models, fieldname, outdir, obstype):

  from plot_shortcuts import plot
  from plot_wrapper import Multiplot, Legend
  import matplotlib.pyplot as pl
  from pygeode.timeaxis import months

  if obstype == 'ec':
    from ec_obs import obs_locations, data as obs_f
  elif obstype == 'gaw':
    from gaw_obs import obs_locations, data as obs_f
  else:
    raise Exception   # Unknown obs type

  from os.path import exists

  models = [m for m in models if m is not None]

  model_data = [m.get_data('sfc',fieldname) for m in models]

  # Limit the time period to plot
  model_data = [x(year=2009, month=(6,9)) for x in model_data]
  obs_f = obs_f(year=2009, month=(6,9))

  # Limit the time period to the current experiment
  # (sometimes we have a really short experiment)
  timeaxis = model_data[0].time
  times = timeaxis.get()
  time1 = min(times)
  time2 = max(times)
  obs_f = obs_f(time=(time1,time2))
  model_data = [x(time=(time1,time2)) for x in model_data]

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

    series = [x(lat=lat, lon=lon) for x in model_data]
    # Make the obs the second entry
    # (to use the same default line colours as older versions of this diagnostic)
    obs_series = obs_f[location]
    series = series[:1] + [obs_series] + series[1:]

    theplot = plot (*series, title=title,
           xlabel='', ylabel='CO2 ppmV', xticks=xticks, xticklabels=xticklabels)
    plots.append (theplot)


  # Plot 4 timeseries per figure
  n = 4
  for i in range(0,len(plots),4):
    fig = pl.figure(figsize=(15,12))

    theplots = plots[i:i+4]
    # Put a legend on the last plot
    labels = [m.title for m in models]
    labels = labels[:1] + ['Obs'] + labels[1:]
    theplots[-1] = Legend(theplots[-1], labels)

    theplots = Multiplot([[p] for p in theplots])
    theplots.render(figure=fig)

    outfile = "%s/%s_timeseries_%s_%s%02d.png"%(outdir,'_'.join(m.name for m in models),fieldname,obstype,i/4+1)
    if not exists(outfile):
      fig.savefig(outfile)

  pl.close(fig)

