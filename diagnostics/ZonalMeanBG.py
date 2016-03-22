
from .movie_zonal import find_applicable_models

from . import Diagnostic
class ZonalMeanBG(Diagnostic):
  @staticmethod
  def do_all (inputs, fieldname, units, outdir, **kwargs):
    models = find_applicable_models(inputs, fieldname, zaxis='gph')
    movie_bargraph(models, fieldname, units, outdir, **kwargs)


from .movie import TiledMovie
class BG_Movie (TiledMovie):
  def render_panel (self, ax, data, n):

    import numpy as np

    #Grab the latitude values and create the appropriate weights
    latsweights = np.cos(np.radians(data.lat.get()))

    #Range is the co-ordinates of where to cut the data for the different regions
    Range=[round(len(data.lat)/180.0*60),round(len(data.lat)/180.0*120)]

    SA,TrA,NA=np.split(np.squeeze(data.get()),Range)  

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
    yaxmin, yaxmax = self.global_range[data.name]
    yaxmax *= 1.015
    yaxmin /= 1.015

    #Plot data
    ax.bar((0,2,4),(N,Tr,S),width=1,color='k')

    #Plot aesthetics
    ax.set_ylim(ymax=yaxmax,ymin=yaxmin)
    ax.set_title(self.subtitles[n])
    ax.set_ylabel('%s Concentration (%s)'%(data.name,data.atts['units']))
    ax.set_xticks((.5,2.5,4.5))
    ax.set_xticklabels(('Northern\nExtratropics','Tropics','Southern\nExtratropics'))
    ax.set_xlim(0,5)
    ax.grid(axis='y',which='both')
    yspan=yaxmax-yaxmin

    #Create CO2 value label above each bar
    ax.text(0,N+yspan/200.0,round(N,2))
    ax.text(2,Tr+yspan/200.0,round(Tr,2))
    ax.text(4,S+yspan/200.0,round(S,2))

    #Create and denote comparison bar
    ax.plot((1.5,1.5),(max(N,S,Tr),min(N,S,Tr)),'b')
    ax.plot((1.45,1.55),(max(N,S,Tr),max(N,S,Tr)),'b')
    ax.plot((1.45,1.55),(min(N,S,Tr),min(N,S,Tr)),'b')
    ax.text(1.25,(max(N,S,Tr)+min(N,S,Tr))/2.0,round(max(N,S,Tr)-min(N,S,Tr),2),rotation='vertical')


if True:


  def movie_bargraph (models, fieldname, units, outdir, height):

    from ..common import convert
    from .movie_zonal import zonalmean_gph

    prefix = "ZonalMeanBG-images_%s_%s"%('_'.join(m.name for m in models), fieldname)

    fields = [zonalmean_gph(m,fieldname,units,typestat="mean") for m in models]
    fields = [f(height=height) for f in fields]

    # Unit conversion
    fields = [convert(f,units) for f in fields]

    title = '%s Concentration at %skm'%(fieldname,height)
    subtitles = [m.title for m in models]

    shape = (1,len(fields))

    movie = BG_Movie (fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio=1.4)

    movie.save (outdir=outdir, prefix=prefix)

from . import table
table['zonal-bargraph'] = ZonalMeanBG

