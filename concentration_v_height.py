

def CvHgraph(X,names=['','','']):

  """This function handles the actual graphing mechanisms"""

  import numpy as np
  import matplotlib.pyplot as plt

  #Figure prep
  fig = plt.figure(figsize=(6*len(X),9))

  for q,data in enumerate(X):    #For each data set

    #Determine subplot structure
    ax = fig.add_subplot(100+10*len(X)+q+1)

    data=data.squeeze()
    RegionHeights=np.zeros((3,data.shape[0]))
    RegionStds=np.zeros((3,data.shape[0]))

    for i in range(data.shape[0]):    #For each height level

      #Weighted averages of each region at this height and time
      N=float(data(lat=(30,90),Zaxis=i).nanmean('Lat').get())
      S=float(data(lat=(-90,-30),Zaxis=i).nanmean('Lat').get())
      Tr=float(data(lat=(-30,30),Zaxis=i).nanmean('Lat').get())

      #Organize values into an array
      RegionHeights[0][i]=N
      RegionHeights[1][i]=S
      RegionHeights[2][i]=Tr

      #Calculate standard deviation for each region
      RegionStds[0][i]=np.std(data(lat=(30,90),Zaxis=i).get())
      RegionStds[1][i]=np.std(data(lat=(-90,-30),Zaxis=i).get())
      RegionStds[2][i]=np.std(data(lat=(-30,30),Zaxis=i).get())

    #Plot data
    NL=ax.errorbar(RegionHeights[0],range(data.shape[0]),xerr=RegionStds[0],color='b',linestyle='solid')
    TrL=ax.errorbar(RegionHeights[2],range(data.shape[0]),xerr=RegionStds[2],color='g')
    SL=ax.errorbar(RegionHeights[1],range(data.shape[0]),xerr=RegionStds[1],color='r')

    #Plot aesthetics
    plt.title('Average CO$_{2}$ Concentration - %s'%(names[q]))
    ax.set_xlabel('CO$_{2}$ Concentration (ppm)')
    ax.set_ylabel('Height (km)')
    ax.grid(b=None, which='major', axis='both')
    ax.set_xlim(375,395)
    ax.legend([NL,SL,TrL], ['North Extratropics','South Extratropics','Tropics'],prop={'size':11})
  return fig



def plotCvH(field1,field2=None, field3=None, title1='plot1', title2='plot2', title3='plot3', palette=None, norm=None, preview=False, outdir='images',names=['','','']):

  """This function loops through the data time-wise and preps the data for the graphing function"""

  import matplotlib.pyplot as plt
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
  for i,t in enumerate(field1.time):

    data = field1(i_time=t)
    year = data.time.year[0]
    month = data.time.month[0]
    day = data.time.day[0]
    hour = data.time.hour[0]

    date = "%04d-%02d-%02d %02dz"%(year,month,day,hour)
    fname = "%s/%04d%02d%02d%02d.png"%(outdir,year,month,day,hour)

    #Don't bother creating the figure if it already exists
    if exists(fname) and preview is False:
      continue

    #Pass data to graphing function
    data = [d(time=t) for d in fields]
    # Skip if any data is unavailable at this time
    if any(len(d.time) == 0 for d in data): continue
    assert len(data[0].time) == 1
    fig = CvHgraph(data,names)

    #Add Timestamp
    plt.text(.75,.83,'%s/%s/%s'%(str(day).zfill(2),str(month).zfill(2),year),horizontalalignment='center',transform=plt.gca().transAxes)

    if preview is False:
      fig.savefig(fname)
      fig.clear()
      pbar.update(i*100/len(field1.time))
    else:
      break

  pbar.update(100)


def movie_CvH (models, fieldname, units, outdir):

  from common import convert
  from movie_zonal import zonalmean_gph

  assert len(models) > 0
  assert len(models) <= 3  # too many things to plot
  models = [m for m in models if m is not None]

  imagedir=outdir+"/images_%s_CvH%s"%('_'.join(m.name for m in models), fieldname)

  #Names of each model - For plot titles later
  Names = [m.name for m in models]

  fields = [zonalmean_gph(m,fieldname) for m in models]

  # Unit conversion
  fields = [convert(f,units) for f in fields]

  titles = [m.title for m in models]

  while len(fields) < 3: fields += [None]
  while len(titles) < 3: titles += [None]

  #Now that data is formatted, pass it to plot function
  plotCvH(field1=fields[0], field2=fields[1], field3=fields[2], title1=titles[0], title2=titles[1], title3=titles[2],preview=False, outdir=imagedir, names=Names)

  #Turn output images into movie file
  moviefile = "%s/%s_CvH%s.avi"%(outdir, '_'.join(m.name for m in models), fieldname)

  from os import system
  from os.path import exists
  if not exists(moviefile):
    system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))
