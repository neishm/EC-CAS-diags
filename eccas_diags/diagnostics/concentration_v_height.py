

from .movie_zonal import ZonalMean
class Concentration_VS_Height(ZonalMean):
  """
  Vertial profiles, averaged by zonal region and animated in time.
  """
  def __init__ (self, xlim=None, **kwargs):
    # This diagnostic always uses geopotential height for the vertical.
    kwargs['zaxis'] = 'gph'
    super(Concentration_VS_Height,self).__init__(**kwargs)
    self.xlim = xlim

  def do (self, inputs):

    prefix = '%s_CvH%s%s%s'%('_'.join(inp.name for inp in inputs), self.fieldname, self.suffix, self.end_suffix)

    #Names of each model - For plot titles later
    subtitles = ['Average %s Concentration - %s'%(self.fieldname,inp.name) for inp in inputs]

    fields = [inp.find_best(self.fieldname) for inp in inputs]

    shape = (1,len(fields))

    movie = CvH_Movie(fields, xlim=self.xlim, title='CvH', subtitles=subtitles, shape=shape, aspect_ratio=1.5)

    movie.save(outdir=self.outdir, prefix=prefix)


from .movie import TiledMovie
class CvH_Movie(TiledMovie):
  def __init__ (self, fields, xlim, **kwargs):
    self.xlim = xlim
    TiledMovie.__init__(self,fields,**kwargs)
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
    ax.set_xlabel('%s Concentration (%s)'%(data.name,data.atts['units']))
    ax.set_ylabel('Height (km)')
    ax.grid(b=None, which='major', axis='both')
    if self.xlim is not None:
      ax.set_xlim(self.xlim)
    ax.legend([NL,SL,TrL], ['North Extratropics','South Extratropics','Tropics'],prop={'size':11})


from . import table
table['concentration-v-height'] = Concentration_VS_Height


