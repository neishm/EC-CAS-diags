
from .movie_zonal import find_applicable_models

if True:

  def do_all (inputs, fieldname, units, outdir, **kwargs):
    models = find_applicable_models(inputs, fieldname)
    movie_CvH(models, fieldname, units, outdir, **kwargs)

from .movie import TiledMovie
class CvH_Movie(TiledMovie):
  def render_panel (self, ax, data, n):

    """This function handles the actual graphing mechanisms"""

    import numpy as np
    import matplotlib.pyplot as plt

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
    ax.set_title(self.subtitles[n])
    ax.set_xlabel('CO$_{2}$ Concentration (ppm)')
    ax.set_ylabel('Height (km)')
    ax.grid(b=None, which='major', axis='both')
    ax.set_xlim(375,395)
    ax.legend([NL,SL,TrL], ['North Extratropics','South Extratropics','Tropics'],prop={'size':11})


if True:

  def movie_CvH (models, fieldname, units, outdir):

    from ..common import convert
    from .movie_zonal import zonalmean_gph

    models = [m for m in models if m is not None]

    prefix = '%s_CvH%s'%('_'.join(m.name for m in models), fieldname)

    #Names of each model - For plot titles later
    subtitles = ['Average CO$_{2}$ Concentration - %s'%(m.name) for m in models]

    fields = [zonalmean_gph(m,fieldname,units,typestat="mean") for m in models]

    # Unit conversion
    fields = [convert(f,units) for f in fields]

    shape = (1,len(fields))

    movie = CvH_Movie(fields, title='CvH', subtitles=subtitles, shape=shape, aspect_ratio=1.5)

    movie.save(outdir=outdir, prefix=prefix)
