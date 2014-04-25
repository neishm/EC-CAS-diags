# CO2 timeseries

def Barplot (models, fieldname, units, outdir, plot_months=None,ymin=350,ymax=420):

  from plot_shortcuts import plot, plot_stdfill
  from plot_wrapper import Multiplot, Legend, Overlay, Text
  import matplotlib.pyplot as pl
  import matplotlib as mpl
  from pygeode.timeaxis import months
  import pygeode as pyg
  import numpy as np
  from os.path import exists
  import math

  from common import unit_scale

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
    timeaxis = timeaxis(year=2014,month=plot_months)
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

  #Creating the data structure
  #Want to use array but needs to have non-fixed last dimension?
  Zones = [[],[],[],[],[]]
  Stds = [[],[],[],[],[]]

  for q in datasets:
    for i in range(5):
      Zones[i].append([])
      Stds[i].append([])

  #List of stations within the two continents in question
  NorthAmList = ['Alert','Barrow','Candle Lake','Chibougamau','East Trout Lake','Egbert','Estevan Point','Fraserdale',
    'Lac La Biche (Alberta)','Mauna Loa','Sable Island',]
  EuropeList = ['BEO Moussala','Jungfraujoch','Kollumerwaard','Monte Cimone','Neuglobsow','Pallas-Sammaltunturi','Plateau Rosa',
    'Puszcza Borecka/Diabla Gora','Schauinsland','Sonnblick','Westerland','Zeppelinfjellet (Ny-Alesund)','Zugspitze / Schneefernerhaus']

  #List for counting the number of stations in each group
  Count = [0,0,0,0,0]

  for location, (lat, lon, country) in sorted(obs_locations.items()):
    if lon < 0: lon += 360  # Model data is from longitudes 0 to 360

    series = []
    std = []
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

    # Limit the time period
    series = [x(time=(time1,time2)) for x in series]
    std = [s(time=(time1,time2)) if s is not None else None for s in std]

    #-----Record Data------
    for i,t in enumerate(series):
      d = t.squeeze().get()

      #Average values and standard deviations of each station's timeseries
      if lat > 30:
        #Add 1 to the region count on first run through
        if i == 0: Count[0]+=1
        Zones[0][i].append(np.mean(d[~np.isnan(d)]))
        Stds[0][i].append(np.std(d[~np.isnan(d)]))
      elif lat < -30:
        if i == 0: Count[1]+=1
        Zones[1][i].append(np.mean(d[~np.isnan(d)]))
        Stds[1][i].append(np.std(d[~np.isnan(d)]))
      else:
        if i == 0: Count[2]+=1
        Zones[2][i].append(np.mean(d[~np.isnan(d)]))
        Stds[2][i].append(np.std(d[~np.isnan(d)]))

      #Sort for Europe and NA stations
      if location in NorthAmList:
        if i == 0: Count[3]+=1
        Zones[3][i].append(np.mean(d[~np.isnan(d)]))
        Stds[3][i].append(np.std(d[~np.isnan(d)]))
      elif location in EuropeList:
        if i == 0: Count[4]+=1
        Zones[4][i].append(np.mean(d[~np.isnan(d)]))
        Stds[4][i].append(np.std(d[~np.isnan(d)]))

  #---------Process/Plot Data--------

  fig = pl.figure(figsize = (8,8))

  #Average the values of each Zone's dataset's station average
  for i in range(len(Zones)):
    for t in range(len(Zones[i])):
      d= np.array(Zones[i][t])
      s= np.array(Stds[i][t])
      Zones[i][t]= np.mean(d[~np.isnan(d)])
      Stds[i][t] = np.mean(s[~np.isnan(s)])

  #-----------------------------
  #Create colour and legend rectangle list such that the last value is green for observations
  colourset = ['blue','red','cyan','magenta']
  colours = []
  rectangles = []
  for i in range(len(datasets)-1):
    colours.append(colourset[i])
    rectangles.append(mpl.patches.Rectangle((0, 0), 1, 1, fc=colourset[i]))
  colours.append('green')
  rectangles.append(mpl.patches.Rectangle((0, 0), 1, 1, fc="g"))
  #-----------------------------

  for i in range(len(Zones)):

    xvalues = np.arange(len(datasets)+1)+i*(len(datasets)+1)    #Format plot based on number of datasets

    Zones[i].append(0)    #Add empty space between each region group
    Stds[i].append(0)

    pl.bar(xvalues,Zones[i],yerr = Stds[i],color = colours,width = 1,lw = 2, ecolor= 'black',capsize = 5)

    pl.text(xvalues[-1]-.5,Zones[i][-2]-((Zones[i][-2]-ymin)/2.0),Count[i],horizontalalignment = 'center')

  pl.xlim(-1,np.max(xvalues)+1)

  pl.title('Average %s Concentrations'%(fieldname))
  pl.ylim(ymin=ymin,ymax=ymax)
  pl.ylabel('%s (%s)'%(fieldname,units))
  pl.xticks(np.arange(5)*(len(datasets)+1)+len(datasets)/2.0,
    ['Northern\nHemisphere','Southern\nHemisphere','Tropics','North\nAmerica','Europe']
    ,horizontalalignment = 'center')
  pl.legend(rectangles,[d.title for d in datasets],prop={'size':12})
  pl.text(.02,.96,'One standard deviation shown',transform = pl.gca().transAxes)

  outfile = "%s/%s_timeseries_%s_%02d.png"%(outdir,'_'.join(d.name for d in datasets),fieldname,i/4+1)
  if not exists(outfile):
    fig.savefig(outfile)

  pl.close(fig)

