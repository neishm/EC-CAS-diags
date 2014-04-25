import numpy as np
import matplotlib.pyplot as plt
from pygeode import Var
import math

def rescale (field, units):
  from common import unit_scale
  input_units = field.atts['units']
  if input_units == units: return field
  low = field.atts['low']
  high = field.atts['high']
  name = field.name
  field = field / unit_scale[input_units] * unit_scale[units]
  field.name = name
  field.atts['low'] = low / unit_scale[input_units] * unit_scale[units]
  field.atts['high'] = high / unit_scale[input_units] * unit_scale[units]
  return field

def bargraph(DataList,Height,names=['','','']):

  #Grab the latitude values and create the appropriate weights
  LatWeights = []
  for t in DataList:
    LatWeights.append(np.cos(np.radians(t.lat.get())))

  #Squeeze superfluous dimensions/Turn DataList into numpy array version of itself
  ArrayDataList=[np.squeeze(d) for d in DataList]

  #Range is the co-ordinates of where to cut the data for the different regions
  Range=[round(ArrayDataList[0].shape[1]/180.0*60),round(ArrayDataList[0].shape[1]/180.0*120)]

  #Determine figure size
  fig = plt.figure(figsize=(5*len(ArrayDataList),8))

  for i,data in enumerate(ArrayDataList):    #For each dataset

    latsweights = LatWeights[i]

    #Determine subplot structure
    ax=fig.add_subplot(100+10*len(ArrayDataList)+i+1)

    SA,TrA,NA=np.split(np.squeeze(data[Height]),Range)  

    #Split up the latitude weights and delete NaN values
    SAweights=latsweights[~np.isnan(SA)]
    SA=SA[~np.isnan(SA)]
    TrAweights=latsweights[~np.isnan(TrA)]
    TrA=TrA[~np.isnan(TrA)]
    NAweights=latsweights[~np.isnan(NA)]
    NA=NA[~np.isnan(NA)]

    #Take weighted average of each region
    N=np.average(NA,weights=NAweights)
    S=np.average(SA,weights=SAweights) 
    Tr=np.average(TrA,weights=TrAweights) 

    #Yscale limits - high and low are slightly to constrictve
    yaxmax=max(d.atts['high'] for d in DataList)*1.015
    yaxmin=min(d.atts['low'] for d in DataList)/1.015

    #Plot data
    plt.bar((0,2,4),(N,Tr,S),width=1,color='k')

    #Plot aesthetics
    plt.ylim(ymax=yaxmax,ymin=yaxmin)
    plt.title('Average %s Concentration at height %s - %s'%(DataList[0].atts['nomvar'],Height,names[i]))
    plt.ylabel('%s Concentration (%s)'%(DataList[0].atts['nomvar'],DataList[0].atts['units']))
    plt.xticks((.5,2.5,4.5),('Northern\nExtratropics','Tropics','Southern\nExtratropics'))
    plt.xlim(0,5)
    plt.grid(axis='y',which='both')
    yspan=yaxmax-yaxmin

    #Create CO2 value label above each bar
    plt.text(0,N+yspan/200.0,round(N,2))
    plt.text(2,Tr+yspan/200.0,round(Tr,2))
    plt.text(4,S+yspan/200.0,round(S,2))

    #Create and denote comparison bar
    plt.plot((1.5,1.5),(max(N,S,Tr),min(N,S,Tr)),'b')
    plt.plot((1.45,1.55),(max(N,S,Tr),max(N,S,Tr)),'b')
    plt.plot((1.45,1.55),(min(N,S,Tr),min(N,S,Tr)),'b')
    plt.text(1.25,(max(N,S,Tr)+min(N,S,Tr))/2.0,round(max(N,S,Tr)-min(N,S,Tr),2),rotation='vertical')

  return fig

def plotBG(height, field1,field2=None, field3=None, names=['','',''], palette=None, norm=None, preview=False, outdir='images'):

  from plot_wrapper import Colorbar, Plot, Overlay, Multiplot
  from plot_shortcuts import pcolor, contour, contourf, Map
  from os.path import exists
  from os import makedirs

  from pygeode.progress import PBar

  # Create output directory?
  if not exists(outdir): makedirs(outdir)

  print 'Saving Zonal Comparison %s images'%field1.name
  pbar = PBar()

  fields = [d for d in [field1,field2,field3] if d is not None]

  # Loop over all available times
  for i,t in enumerate(range(len(field1.time))):

    data = field1(i_time=t)
    year = data.time.year[0]
    month = data.time.month[0]
    day = data.time.day[0]
    hour = data.time.hour[0]

    # Quick kludge to workaround non-monotonic gph in CarbonTracker
    if year==2009 and month==8 and day==7: continue

    #Define filename for the figure
    date = "%04d-%02d-%02d %02dz"%(year,month,day,hour)
    fname = "%s/ZBG-%04d%02d%02d%02d.png"%(outdir,year,month,day,hour)

    #Don't bother creating the figure if it already exists
    if exists(fname) and preview is False:
      continue

    #Pass data to plotting function
    data = [d(year=year,month=month,day=day,hour=hour) for d in fields]
    assert len(data[0].time) == 1
    fig=bargraph(data,height,names)

    #Add timestamp
    fig.text(2.5,399,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center')

    if preview is False:
      fig.savefig(fname)
      fig.clear()
      pbar.update(i*100/len(field1.time))
    else:
      break


def movie_bargraph (models, height, fieldname, units, outdir, stat='mean'):

  from common import unit_scale

  models = [m for m in models if m is not None]
  assert len(models) > 0
  assert len(models) <= 3  # too many things to plot

  imagedir=outdir+"/ZonalMeanBG-images_%s_flux%s"%('_'.join(m.name for m in models), fieldname)
  if stat != 'mean':
    imagedir += '_' + stat

  fields = [m.get_data('zonalmean_gph',fieldname,stat=stat) for m in models]

  # Unit conversion
  fields = [rescale(f,units) for f in fields]

  Names = [m.name for m in models]

  while len(fields) < 3: fields += [None]
  while len(Names) < 3: Names += [None]

  plotBG(height, field1=fields[0], field2=fields[1], field3=fields[2], names=Names,preview=False, outdir=imagedir)

  moviefile = "%s/%s_zonalmeanBG%s_%s.avi"%(outdir, '_'.join(m.name for m in models), fieldname, stat)


  from os import system
  from os.path import exists
  if not exists(moviefile):
    system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))

