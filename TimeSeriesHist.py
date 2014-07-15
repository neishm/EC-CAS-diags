#Model vs Obs histogram

"""
It is important to note that the model histogram will consist of a full year's data
Whereas the observations may only exist for one season, causing them to look much different.
"""

def timeseries (models, fieldname, units, outdir, plot_months=None,timefilter=None):

  from plot_wrapper import Multiplot, Legend, Overlay, Text,Histogram
  import matplotlib.pyplot as pl
  import matplotlib as mpl
  from pygeode.timeaxis import months
  import pygeode as pyg
  import numpy as np
  from os.path import exists
  import math
  from os import makedirs

  from common import unit_scale

  from timeseries import get_sfc_mean, get_sfc_std, get_station_mean, get_station_std

  line_colours = ['blue', 'green', 'red']

  datasets = [d for d in models if d is not None]

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

  plots,StdDevs,Means,MaxMins= [],[],[],[]

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
    parts = []
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
        data = get_station_mean(d,location,fieldname)
        series.append(data)
        std.append(get_station_std(d,location,fieldname))

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

    #Squeeze out the data (we don't need axes or anything else)
    series = [s.squeeze().get() for s in series]
    series = [s[~np.isnan(s)] for s in series]

    #Find the max and mins of the datasets, lopping off the top and bottom 1% of data (outliers throwing off graph formatting)
    Max = int(max([max(sorted(s)[:int(len(s)*.99)]) for s in series if s != []]))
    Min = int(min([min(sorted(s)[int(len(s)*.01):]) for s in series if s != []]))

    #Set up colour scheme so obs are always green (assume obs are last data entry)
    colourset = ['cyan','red','blue','magenta']
    colours = []
    rectangles = []
    for i in range(len(datasets)-1):
      colours.append(colourset[i])
      rectangles.append(mpl.patches.Rectangle((0, 0), 1, 1, fc=colourset[i]))
    colours.append('green')
    rectangles.append(mpl.patches.Rectangle((0, 0), 1, 1, fc="g"))

    #Create bins and plot histogram

    parts.append(Histogram(series,color=colours,bins=range(Min,Max,1),lw=0))

    LocalStds = 'Standard Deviations: '
    LocalMeans = 'Mean Values (ppm): '
    LocalMaxMin = 'Max/Min Values (ppm): '
    for i,t in enumerate(series):
      if t != []:
        LocalStds += '%s | '%(str(np.round(np.std(t),1)))
        LocalMeans += '%d | '%(np.mean(t))
        LocalMaxMin += '%d/%d | '%(max(t),min(t))

    StdDevs.append(LocalStds)
    Means.append(LocalMeans)
    MaxMins.append(LocalMaxMin)

    theplot = Overlay (*parts, title=title.decode('latin-1'),xlabel='CO2 (ppm)', ylabel='Occurrences')
    plots.append (theplot)

  outdir = outdir + '/TimeSeriesHist-images_%s_%s'%('_'.join(d.name for d in datasets),fieldname)
  if not exists(outdir): makedirs(outdir)

  # Plot 4 timeseries per figure
  for i in range(0,len(plots),4):
    fig = pl.figure(figsize=(15,12))

    theplots = plots[i:i+4]
    theplots[-1] = Legend(theplots[-1],rectangles,[d.title for d in datasets],prop={'size':11})

    #Add statistics to each plot
    for j in range(4):
      theplots[j] = Text(theplots[j],.02,.98,StdDevs[i+j],size=11,verticalalignment='top')
      theplots[j] = Text(theplots[j],.02,.94,Means[i+j],size=11,verticalalignment='top')
      theplots[j] = Text(theplots[j],.02,.9,MaxMins[i+j],size=11,verticalalignment='top')

    theplots = Multiplot([[theplots[0],theplots[1]],[theplots[2],theplots[3]]])
    theplots.render(figure=fig)
    pl.tight_layout()    #Makes layout tighter - less clutter for 4 plots


    outfile = "%s/%s_timeseries_%s_%02d.png"%(outdir,'_'.join(d.name for d in datasets),fieldname,i/4+1)
    if not exists(outfile):
      fig.savefig(outfile)

  pl.close(fig)
