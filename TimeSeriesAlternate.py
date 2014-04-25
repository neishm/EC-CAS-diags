# CO2 timeseries

def timeseries (models, fieldname, units, outdir, plot_months=None,timefilter=None):

  from plot_shortcuts import plot, plot_stdfill
  from plot_wrapper import Multiplot, Legend, Overlay, Text, TwinX
  import matplotlib.pyplot as pl
  from pygeode.timeaxis import months
  import pygeode as pyg
  import numpy as np
  from os.path import exists
  import math
  from os import makedirs

  from common import unit_scale

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
      sfc_data.append(d.get_data('sfc',fieldname))
    except KeyError:
      # Put a 'None' placeholder to indicate this isn't model surface data
      sfc_data.append(None)

  sfc_std = []
  for d in datasets:
    try:
      sfc_std.append(d.get_data('sfc',fieldname,'std'))
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

  plots,diffs,DiffStats,DiffStds = [],[],[],[]

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

    for i in series:
      i.time.values = i.time.values + (int(lon)//15)*1.0/24.0    #Change to local time


    #------------Plot obs and model timeseries-----------
    parts = []
    for i in range(len(series)):
      color=line_colours[i]
      if std[i] is not None:
        parts.append(plot_stdfill(series[i],2*std[i],color=color))
      else:
        parts.append(plot(series[i],color=color))
    #-----------------------------------------------------


    Times = series[-1].time.get()    #Times where there are obs
    Times = Times[~np.isnan(Times)]    #Remove nans
    model = np.interp(Times,series[0].time.get(),series[0].squeeze().get())    #Interpolate model data to those points for comparison

    #Filter based on Day/Night (only affects difference line)
    if timefilter is not None:

      param1,param2 = 99,99    #Impossible to trip values to serve as placeholders

      hr = 1.0/24.0    #Conversion factor (Times is in days, filtering is written in hours)

      if timefilter == 'Day': param1 = 14*hr
      elif timefilter == 'Night' : param1 = 2*hr
      elif timefilter == 'NightDay' : param1,param2 = 14*hr,2*hr

      NewTimes=[]
      for i in series[-1].time.hour:
        q=i
        if param1 - 2*hr <= i <= param1 + 2*hr :    #If time is within 2 hrs of target time, add it to the new time list
          NewTimes.append(q)
        elif param2 - 2*hr <= i <= param2 + 2*hr :
          NewTimes.append(q)

      NewModel=[]
      #Grab the model times at the new times
      for i,t in enumerate(model):
        if Times[i] in NewTimes:
          NewModel.append(t)
      model = NewModel

      obs = series[1](l_time=NewTimes).squeeze().get()
      Times=NewTimes
    else:
      obs = series[1].squeeze().get()    #If not filtering, obs is just the default series[1]

    #------Difference Plot------
    Difference = obs-model    #Difference data

    TimesAx = pyg.NamedAxis(Times, 'time')    #Define an axis for Difference object

    #Determine shift needed to put difference plot under timeseries
    Shift = math.floor((np.nanmin(obs)-np.nanmax(Difference))/10.0)*10.0

    # Determine Mean and Max difference, and standard deviation
    DiffMean = np.mean(Difference[~np.isnan(Difference)])
    DiffStd = np.std(Difference[~np.isnan(Difference)])
    DiffStats.append('Mean Difference: %s | Max Difference: %s'%(round(DiffMean,1),round(np.nanmax(Difference),1)))
    DiffStds.append('Difference Std: %s'%(round(DiffStd,1)))

    #Rewrite Difference as a pygeode object and plot with wrappers
    Diff = pyg.Var([TimesAx],name = 'Diff', values=Difference)
    parts.append(TwinX(plot(Diff,color='magenta')))

    #Black baseline representing x = 0 line for difference
    Baseline = pyg.Var([pyg.NamedAxis([0,365],'time')],values=[0,0])
    parts.append(plot(Baseline,color='black'))

    #Temporary lines for context (testing)
    ContextLine = pyg.Var([pyg.NamedAxis([0,365],'time')],values=[10,10])
    parts.append(plot(ContextLine,color='black',alpha=.25))

    ContextLine = pyg.Var([pyg.NamedAxis([0,365],'time')],values=[-10,-10])
    parts.append(plot(ContextLine,color='black',alpha=.25))
    #---------------------------

    theplot = Overlay (*parts, title=title.decode('latin-1'),xlabel='', ylabel='%s %s'%(fieldname,units), xticks=xticks, xticklabels=xticklabels)
    plots.append (theplot)

  #Format image directory
  outdir = outdir + '/TimeSeriesAlternate-images_%s_%s'%('_'.join(d.name for d in datasets),fieldname)
  if not exists(outdir): makedirs(outdir)

  # Plot 4 timeseries per figure
  n = 4
  for i in range(0,len(plots),4):
    fig = pl.figure(figsize=(15,12))

    theplots = plots[i:i+4]
    # Put a legend on the last plot
    labels = [d.title for d in datasets]
    labels.append('Difference')
    theplots[-1] = Legend(theplots[-1], labels,prop={'size':11})

    #Add statistics to each plot
    for j in range(4):
      theplots[j] = Text(theplots[j],.01,.9,DiffStats[j+i],size=11)
      theplots[j] = Text(theplots[j],.01,.82,DiffStds[j+i],size=11)
      #theplots[j] = Text(theplots[j],.01,.76,std

    theplots = Multiplot([[p] for p in theplots])
    theplots.render(figure=fig)
    pl.tight_layout()    #Makes layout tighter - less clutter for 4 plots


    outfile = "%s/%s_timeseries_%s_%02d.png"%(outdir,'_'.join(d.name for d in datasets),fieldname,i/4+1)
    if not exists(outfile):
      fig.savefig(outfile)

  pl.close(fig)
