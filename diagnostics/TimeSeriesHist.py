#Model vs Obs histogram

"""
It is important to note that the model histogram will consist of a full year's data
Whereas the observations may only exist for one season, causing them to look much different.
"""

from .timeseries import find_applicable_obs, find_applicable_models

from . import Diagnostic
class TimeseriesHist(Diagnostic):
  @staticmethod
  def do_all (inputs, fieldname, units, outdir, **kwargs):
    model_inputs = find_applicable_models(inputs, fieldname)
    obs_inputs = find_applicable_obs(inputs, fieldname)
    for obs in obs_inputs:
      timeseries (obs, model_inputs, fieldname, units, outdir, **kwargs)

if True:
  def timeseries (obs, models, fieldname, units, outdir, plot_months=None,timefilter=None):
    from .plot_wrapper import Multiplot, Legend, Overlay, Text,Histogram
    import matplotlib.pyplot as pl
    import matplotlib as mpl
    from pygeode.timeaxis import months
    import pygeode as pyg
    import numpy as np
    from os.path import exists
    import math
    from os import makedirs

    from ..common import convert, select_surface

    from .timeseries import sample_model_at_obs

    model_data = []
    model_spread = []
    for m in models:
      field = sample_model_at_obs(m,obs,fieldname,units=units)
      field = convert(field, units, context=fieldname)
      model_data.append(field)
      try:
        field = sample_model_at_obs(m,obs,fieldname+'_ensemblespread',units=units)
        field = convert(field, units, context=fieldname)
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

    plots,StdDevs,Means,MaxMins= [],[],[],[]
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

      #Squeeze out the data (we don't need axes or anything else)
      series = [d(station=location).squeeze().get() for d in data]
      series = [s[~np.isnan(s)] for s in series]

      #Find the max and mins of the datasets, lopping off the top and bottom 1% of data (outliers throwing off graph formatting)
      Max = int(max([max(sorted(s)[:int(len(s)*.99)]) for s in series if s != []]))
      Min = int(min([min(sorted(s)[int(len(s)*.01):]) for s in series if s != []]))

      #Set up colour scheme so obs are always green (assume obs are last data entry)
      colourset = ['cyan','red','blue','magenta']
      colours = []
      rectangles = []
      for i in range(len(data)-1):
        colours.append(colourset[i])
        rectangles.append(mpl.patches.Rectangle((0, 0), 1, 1, fc=colourset[i]))
      colours.append('green')
      rectangles.append(mpl.patches.Rectangle((0, 0), 1, 1, fc="g"))

      #Create bins and plot histogram

      parts.append(Histogram(series,color=colours,bins=range(Min,Max+1,1),lw=0))

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

      theplot = Overlay (*parts, title=title.decode('latin-1'),xlabel='%s (%s)'%(fieldname,units), ylabel='Occurrences')
      plots.append (theplot)

    outdir = outdir + '/TimeSeriesHist-images_%s_%s'%('_'.join(d.name for d in models+[obs]),fieldname)
    if not exists(outdir): makedirs(outdir)

    # Plot 4 timeseries per figure
    for i in range(0,len(plots),4):
      fig = pl.figure(figsize=(15,12))

      theplots = plots[i:i+4]
      theplots[-1] = Legend(theplots[-1],rectangles,[d.title for d in models+[obs]],prop={'size':11})

      #Add statistics to each plot
      for j in range(len(theplots)):
        theplots[j] = Text(theplots[j],.02,.98,StdDevs[i+j],size=11,verticalalignment='top')
        theplots[j] = Text(theplots[j],.02,.94,Means[i+j],size=11,verticalalignment='top')
        theplots[j] = Text(theplots[j],.02,.9,MaxMins[i+j],size=11,verticalalignment='top')

      # Add placeholders where there aren't enough plots for the figure
      theplots = (theplots+[None,None,None])[:4]

      theplots = Multiplot([[theplots[0],theplots[1]],[theplots[2],theplots[3]]])
      theplots.render(figure=fig)
      pl.tight_layout()    #Makes layout tighter - less clutter for 4 plots


      outfile = "%s/%s_timeseries_%s_%02d.png"%(outdir,'_'.join(d.name for d in models+[obs]),fieldname,i/4+1)
      if not exists(outfile):
        fig.savefig(outfile)

    pl.close(fig)

from . import table
table['timeseries-hist'] = TimeseriesHist

