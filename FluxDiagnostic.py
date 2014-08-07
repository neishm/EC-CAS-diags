# Get a flux product for the given experiment and tracer name.
def get_flux (model, fieldname):
  from common import convert, number_of_timesteps, remove_extra_longitude

  # Check if we already have the right units
  try:
    data = model.data.find_best(fieldname+'_flux', maximize=number_of_timesteps)
    data = convert(data,'mol m-2 s-1')
  # Otherwise, assume we have integrated flux, need to divide by area
  except ValueError:
    data, area = model.data.find_best([fieldname+'_flux','cell_area'], maximize=number_of_timesteps)
    data = convert(data,'mol s-1')
    area = convert(cell_area,'m2')
    data = data/area

  data.name = fieldname+'_flux'
  data.atts['units'] = 'mol m-2 s-1'

  # Strip out the extra longitude from the fluxes
  # (just for compatibility with Jake's code further below, which is hard-coded
  #  for a 400x200 grid).
  data = remove_extra_longitude(data)

  # Cache the data (mainly to get the high/low stats)
  data = model.cache.write(data, prefix='flux_'+fieldname)

  return data


def interpolategrid(datafile,store_directory):
  #Interpolates the transcom region grid to the model grid
  #Currently simply does this each time the program is run
  #However if it becomes a time issue it could be saved into
  #A file and then read back 

  import numpy as np
  from pygeode.formats import netcdf
  import scipy.interpolate as intp
  from os.path import exists

  if exists(store_directory):
    for line in store_directory:
      #Add code here for reading file
      pass

  f=netcdf.open(datafile)

  regions=f.regions.get()

  global RegionsList180by360    #Define the regions list on a 180 by 360 grid for carbontracker data
  RegionsList180by360 = regions

  lats=f.lat.get()
  lons=f.lon.get()
  lons.flags.writeable = True    #Make the array writeable
  lats.flags.writeable = True

  x,y,ZoneMeans=[],[],[]

  #Need to create a 1-D list of lat/lon co-ords from a 180 by 360 array (scipy.interpolate.griddata() won't take it in array form)
  for i in range(180):
    for q in range(360):
      if lons[q]<0:    #Fix lon system
        lons[q]+=360
      x.append(lats[i])
      y.append(lons[q])

  RegionsList=np.zeros((23,200,400))    #This will be the final interpolate region grid
  for i in range(23):
    BinaryRegions=np.zeros((180,360))
    BinaryRegions[np.where(regions==i)]=1    #Express current transcom region on this grid as 1 (Consists 100% of the region)
    BinaryRegions[np.where(regions!=i)]=0    #Every other region is a 0 (Is completely not the region in question)

    #Again, make it into 1-D list for griddata()
    z=BinaryRegions.flatten()

    #Interpolate this to a model-sized (200 by 400) grid
    BinaryRegionsInterp=intp.griddata((y,x),z,np.meshgrid(np.linspace(0,359,400),np.linspace(-89.5,89.5,200)),method='linear')

    RegionsList[i]=BinaryRegionsInterp

  #Add code here for saving RegionsList to store_directory if it becomes nessesary

  return RegionsList

def FluxPlot(data1,data2,data3,plottype='BG',names=['','','']):

  """
  Plots the data. plottype kwarg ('BG','Map','MeanMap') determines type of plot.
  """

  import numpy as np
  import matplotlib.pyplot as plt

  datas = [x for x in [data1,data2,data3] if x is not None]    #Create list of viable data

  latlongrid = np.meshgrid(np.linspace(0,359,400),np.linspace(-89.5,89.5,200))    #Create a co-ordinate grid
  latgrid = np.absolute(latlongrid[1])    #This will tell us the latitude of each point; needed for area weighting

  if plottype == 'BG':
    ZoneMeansLand = [[],[],[]]   #Up to three sets of data can be plotted
    ZoneMeansOcean = [[],[],[]]    #Data is split up between land and ocean for separate scaling

    PlotNum=len(datas) #Determine number of plots being made

    ax = plt.gca()    #Split into 2 axis so we can have 2 y scales
    ax2 = ax.twinx()

    for i in range(12):    #Land regions
      for t,data in enumerate(datas):

        data=data.squeeze().get()

        if data.shape == (180,360):    #If the input data is on the transcom grid
          RegionsList = RegionsList180by360
          latlongrid = np.meshgrid(np.linspace(0,359,360),np.linspace(-89.5,89.5,180))
          latgrid = np.absolute(latlongrid[1])
        elif data.shape == (200,400):    #If the input data is on the model grid
          RegionsList = RegionsList200by400
          latlongrid = np.meshgrid(np.linspace(0,359,400),np.linspace(-89.5,89.5,200))
          latgrid = np.absolute(latlongrid[1])

        RLG=latgrid[np.where(RegionsList[i]>0)] #Region Latitude Grid - Latitudes of the region's points
        AW=np.cos(np.radians(RLG)) #Latitude based area weights
        RPV=RegionsList[i][np.where(RegionsList[i]>0)] #Region Point Values - Values showing how much of each point's area is in the region (0 to 1, 1=fully in region)

        ZoneMeansLand[t].append(np.average((data[np.where(RegionsList[i]>0)]),weights=RPV*AW))   #Calculate average value of region, weighted by area and RPV

    for i in [x+12 for x in range(11)]:    #Ocean values - As above but for ocean transcom regions
      for t,data in enumerate(datas):

        data=data.squeeze().get()

        if data.shape == (180,360): 
          RegionsList = RegionsList180by360
          latlongrid = np.meshgrid(np.linspace(0,359,360),np.linspace(-89.5,89.5,180))
          latgrid = np.absolute(latlongrid[1])
        elif data.shape == (200,400): 
          RegionsList = RegionsList200by400
          latlongrid = np.meshgrid(np.linspace(0,359,400),np.linspace(-89.5,89.5,200))
          latgrid = np.absolute(latlongrid[1])

        RLG=latgrid[np.where(RegionsList[i]>0)]
        AW=np.cos(np.radians(RLG))
        RPV=RegionsList[i][np.where(RegionsList[i]>0)]

        ZoneMeansOcean[t].append(np.average((data[np.where(RegionsList[i]>0)]),weights=RPV*AW))

    #Plot the data
    F1,F2,F3 = ax.bar(np.array(range(12))*(PlotNum+1),ZoneMeansLand[0],width=1,lw=2,color='r'),None,None
    ax2.bar(np.arange(12,23,1)*(PlotNum+1),ZoneMeansOcean[0],width=1,lw=2,color='r',hatch='/')

    if data2 is not None: 
      F2 = ax.bar(np.array(range(12))*(PlotNum+1)+1,ZoneMeansLand[1],width=1,lw=2,color='b')
      ax2.bar(np.arange(12,23,1)*(PlotNum+1)+1,ZoneMeansOcean[1],width=1,lw=2,color='b',hatch='/')
    if data3 is not None:
      F3 = ax.bar(np.array(range(12))*(PlotNum+1)+2,ZoneMeansLand[2],width=1,lw=2,color='g')
      ax2.bar(np.arange(12,23,1)*(PlotNum+1)+2,ZoneMeansOcean[2],width=1,lw=2,color='g',hatch='/')

    #Define legend parameters
    Legend = [x for x in [F1,F2,F3] if x is not None]
    LegendNames = ['Experiment']
    if F2 is not None: LegendNames.append('Control')
    if F3 is not None: LegendNames.append('Carbon Tracker')

    plt.legend((Legend), (LegendNames))

    plt.title('Mean Flux by Transcom Region')
    plt.xticks([(x+.5)*(PlotNum+1) for x in range(23)],range(23))
    plt.xlim(0,23*(PlotNum+1))
    ax.set_xlabel('Transcom Regions')
    ax.set_ylabel('Flux (mol/m$^{2}$s)')

    """IMPORTANT NOTE
    Currently having trouble automating scale range - can't use high/low since these are the averaged values
    """
    ax.set_ylim(ymin=-.0000028,ymax=.0000014)
    ax2.set_ylim(ymin=-.0000005,ymax=.00000025)

    yfm = ax.yaxis.get_major_formatter() #Ensures that the axis uses scientific notation
    yfm.set_powerlimits([ 0, 0])

    plt.plot([0,100],[0,0],color='k',lw=2)    #Add x axis line

  elif plottype == 'Map':

    for i,t in enumerate(datas):
      ax=plt.subplot(100+10*len(datas)+i)    #Determine appropriate subplot
      plt.contourf(t.squeeze().get(),200,vmin=-.00004)    #Simply plot the flux as a contour plot
      plt.clim(FluxMin,FluxMax)    #Set colour range values
      #cbar=plt.colorbar(ticks=[-.00003,-.00002,-.00001,0,.00001,.00002])
      #cbar.ax.set_aspect(50)

      plt.xticks([],[])    #Remove lat/lon scales
      plt.yticks([],[])

      title='Flux Map-%s'%(names[i])
      plt.title(title)
    plt.tight_layout()    #Makes plot layout more efficient

  elif plottype == 'MeanMap':  

    for q,t in enumerate(datas):
      ax=plt.subplot(100+10*len(datas)+q)  
      Y=np.zeros((200,400))

      for i in range(23):
        Average=np.mean((t.squeeze().get()[np.where(RegionsList200by400[i]>0)])*RegionsList200by400[i][np.where(RegionsList200by400[i]>0)])
        Y[np.where(RegionsList200by400[i]>=.5)]=Average    #Here rounding is used to define region boundaries (which must be binary), but the average is still an unrounded value

      plt.gca().xaxis.set_major_locator(plt.NullLocator())
      plt.gca().yaxis.set_major_locator(plt.NullLocator())  
      plt.contourf(Y,100)
      plt.clim(FluxMin*.5,FluxMax*.5)
      plt.tight_layout()
      plt.title('Flux Mean Map-%s'%(names[q]))



def plotOrganize(flux1,flux2=None, flux3=None, names=['','',''], palette=None, norm=None, preview=False, outdir='images',timefilter=None,plottype='BG'):

  import matplotlib.pyplot as plt
  from plot_wrapper import Colorbar, Plot, Overlay, Multiplot
  from plot_shortcuts import pcolor, contour, contourf, Map
  from os import makedirs

  from pygeode.progress import PBar
  from pygeode.climat import monthlymean,dailymean
  from os.path import exists

  # Create output directory
  if not exists(outdir): makedirs(outdir)

  print 'Saving Flux %s images'%flux1.name
  pbar = PBar()

  global RegionsList200by400,FluxMax,FluxMin    #Compute the region grid on a 200 by 400 grid for the model data, as well as the max/min values to set the color range
  RegionsList200by400 = interpolategrid('/home/jake/MyDiags/Scripts/IntegratedScripts/regions.nc','/home/jake/MyDiags/Scripts/IntergratedScripts/FluxRelated/Interpolation')
  FluxMax = flux1.atts['high']
  FluxMin = flux1.atts['low']

  if timefilter=='Monthly':
    flux1=monthlymean(flux1)
    if flux2 is not None: flux2 = monthlymean(flux2)
    if flux3 is not None: flux3 = monthlymean(flux3)
  elif timefilter=='Daily':
    flux1=dailymean(flux1)
    if flux2 is not None: flux2 = dailymean(flux2)
    if flux3 is not None: flux3 = dailymean(flux3)

  for i,t in enumerate(range(len(flux1.time))):

    data = flux1(i_time=t)

    #Determine the relevant time values

    year = data.time.year[0]
    month = data.time.month[0]

    params = {'year':year,'month':month}    #This will be the dictionary of time kwargs used to isolate data
    TimeStamp = str(month) + '/' + str(year)
    date = '%04d-%02d'%(year,month)

    if timefilter is not 'Monthly':    #Day and hour specifications do not exist if monthly mean is selected  
      day = data.time.day[0]
      params['day'] = day
      date += '-%02d'%(day)
      TimeStamp = str(day) + '/' + TimeStamp

      # Quick kludge to workaround non-monotonic gph in CarbonTracker
      if year==2009 and month==8 and day==7: continue

      if timefilter is not 'Daily':    #Hour specifications do not exist if daily mean is selected
        hour = data.time.hour[0]
        params['hour'] = hour
        date += '-%02d'%(hour)

    fname = "%s/"%(outdir)
    fname += date
    fname += plottype
    fname += ".png"

    if exists(fname) and preview is False:
      continue

    #Determine number of plots to the figure and data for said plots
    PlotNum=1
    data1 = flux1(**params)
    data2 = None
    data3 = None
    if flux2 != None: 
      PlotNum=2
      data2 = flux2(**params)
    if flux3 != None: 
      PlotNum=3
      data3 = flux3(**params)

    #Define the figure and it's size
    if plottype != 'BG':fig = plt.figure(figsize=(7*PlotNum,7))
    else: fig = plt.figure(figsize=(6+2*PlotNum,8))

    #Call the actual plot-creation function
    FluxPlot(data1,data2,data3,plottype=plottype,names=names)

    #Add a timestamp to the figure
    plt.text(.9,.05,TimeStamp,horizontalalignment='center',transform=plt.gca().transAxes)

    if preview is False:
      fig.savefig(fname)
      fig.clear()
      pbar.update(i*100/len(flux1.time))
    else:
      break

  pbar.update(100)


def movie_flux (models, fieldname, units, outdir, timefilter=None,plottype='BG'):

  assert len(models) > 0
  assert len(models) <= 3  # too many things to plot
  models = [m for m in models if m is not None]

  imagedir=outdir+"/FluxDiag-%s-%s-images_%s_flux%s"%(plottype,timefilter,'_'.join(m.name for m in models), fieldname)

  fluxes = [get_flux(m,fieldname) for m in models]

  # Unit conversion
  #fluxes = [rescale(f,units) for f in fields]

  Names = [m.name for m in models]

  while len(fluxes) < 3: fluxes += [None]
  while len(Names) < 3: Names += [None]

  plotOrganize(flux1=fluxes[0], flux2=fluxes[1], flux3=fluxes[2], names=Names,preview=False, outdir=imagedir,timefilter=timefilter,plottype=plottype)

  moviefile = "%s/FluxDiag-%s-%s_%s_%s.avi"%(outdir, plottype, timefilter, '_'.join(m.name for m in models), fieldname)

  #If the timefilter is Monthly, don't bother making the movie - not enough frames
  if timefilter != 'Monthly':
    from os import system
    from os.path import exists
    if not exists(moviefile):
      system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))

