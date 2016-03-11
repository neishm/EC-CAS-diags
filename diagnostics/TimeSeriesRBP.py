# regional bar plots

from .timeseries import find_applicable_models

if True:

  def find_applicable_obs (inputs, fieldname):
    from ..common import have_station_data
    obs_inputs = []
    for x in inputs:
      if x.name == 'GAW-2014':
        obs_inputs.append(x)
    return obs_inputs

  def do_all (inputs, fieldname, units, outdir, **kwargs):
    model_inputs = find_applicable_models(inputs, fieldname)
    obs_inputs = find_applicable_obs(inputs, fieldname)
    for obs in obs_inputs:
      Barplot (obs, model_inputs, fieldname, units, outdir, **kwargs)

  def Barplot (obs, models, fieldname, units, outdir, plot_months=None,ymin=350,ymax=420):

    from .plot_shortcuts import plot, plot_stdfill
    from .plot_wrapper import Multiplot, Legend, Overlay, Text
    import matplotlib.pyplot as pl
    import matplotlib as mpl
    from pygeode.timeaxis import months
    import pygeode as pyg
    import numpy as np
    from os.path import exists
    import math

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

    #Creating the data structure
    #Want to use array but needs to have non-fixed last dimension?
    Zones = [[],[],[],[],[]]
    Stds = [[],[],[],[],[]]

    for q in models+[obs]:
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

    for location in data[0].station:
      station_info = data[0](station=location).getaxis("station")
      lat = station_info.lat[0]
      lon = station_info.lon[0]

      #-----Record Data------
      for i,d in enumerate(data):
        d = d(station=location).squeeze().get()

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
    for i in range(len(data)-1):
      colours.append(colourset[i])
      rectangles.append(mpl.patches.Rectangle((0, 0), 1, 1, fc=colourset[i]))
    colours.append('green')
    rectangles.append(mpl.patches.Rectangle((0, 0), 1, 1, fc="g"))
    #-----------------------------

    for i in range(len(Zones)):

      xvalues = np.arange(len(data)+1)+i*(len(data)+1)    #Format plot based on number of datasets

      Zones[i].append(0)    #Add empty space between each region group
      Stds[i].append(0)

      pl.bar(xvalues,Zones[i],yerr = Stds[i],color = colours,width = 1,lw = 2, ecolor= 'black',capsize = 5)

      pl.text(xvalues[-1]-.5,Zones[i][-2]-((Zones[i][-2]-ymin)/2.0),Count[i],horizontalalignment = 'center')

    pl.xlim(-1,np.max(xvalues)+1)

    pl.title('Average %s Concentrations'%(fieldname))
    pl.ylim(ymin=ymin,ymax=ymax)
    pl.ylabel('%s (%s)'%(fieldname,units))
    pl.xticks(np.arange(5)*(len(data)+1)+len(data)/2.0,
      ['Northern\nHemisphere','Southern\nHemisphere','Tropics','North\nAmerica','Europe']
      ,horizontalalignment = 'center')
    pl.legend(rectangles,[d.title for d in models+[obs]],prop={'size':12})
    pl.text(.02,.96,'One standard deviation shown',transform = pl.gca().transAxes)

    #Format image directory
    outdir = outdir + '/TimeSeriesRBP-images_%s_%s'%('_'.join(d.name for d in models+[obs]),fieldname)
    if not exists(outdir):
      from os import makedirs
      makedirs(outdir)

    outfile = "%s/%s_timeseries_%s_%02d.png"%(outdir,'_'.join(d.name for d in models+[obs]),fieldname,i/4+1)
    if not exists(outfile):
      fig.savefig(outfile)

    pl.close(fig)

