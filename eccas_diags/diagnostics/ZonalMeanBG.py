###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################



from .movie_zonal import ZonalMean
class ZonalMeanBG(ZonalMean):
  """
  Samples data at a particular height, bins it into zones, and displays the
  result as a bargraph.
  """
  def __init__ (self, height, **kwargs):
    # This diagnostic always uses geopotential height for the vertical.
    kwargs['zaxis'] = 'gph'
    super(ZonalMeanBG,self).__init__(**kwargs)
    self.height = height

  def do (self, inputs):

    prefix = "ZonalMeanBG-images_%s_%s%s"%('_'.join(inp.name for inp in inputs), self.fieldname, self.suffix+self.end_suffix)

    fields = [inp.find_best(self.fieldname) for inp in inputs]
    fields = [f(height=self.height) for f in fields]

    title = '%s Concentration at %skm'%(self.fieldname,self.height)
    subtitles = [inp.title for inp in inputs]

    shape = (1,len(fields))

    movie = BG_Movie (fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio=1.4)

    movie.save (outdir=self.outdir, prefix=prefix)


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
    # Check if we have any data (otherwise np.averge fails).
    if len(NA) > 0:
      N=np.average(NA,weights=NAweights)
    else:
      N  = float('nan')
    if len(SA) > 0:
      S=np.average(SA,weights=SAweights)
    else:
      S  = float('nan')
    if len(TrA) > 0:
      Tr=np.average(TrA,weights=TrAweights)
    else:
      Tr = float('nan')

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
    if np.isfinite(N):
      ax.text(0,N+yspan/200.0,round(N,2))
    if np.isfinite(Tr):
      ax.text(2,Tr+yspan/200.0,round(Tr,2))
    if np.isfinite(S):
      ax.text(4,S+yspan/200.0,round(S,2))

    #Create and denote comparison bar
    barvals = filter(np.isfinite,[N,S,Tr])
    if len(barvals) > 0:
      barmax = max(barvals)
      barmin = min(barvals)
      ax.plot((1.5,1.5),(barmax,barmin),'b')
      ax.plot((1.45,1.55),(barmax,barmax),'b')
      ax.plot((1.45,1.55),(barmin,barmin),'b')
      ax.text(1.25,(barmax+barmin)/2.0,round(barmax-barmin,2),rotation='vertical')


from . import table
table['zonal-bargraph'] = ZonalMeanBG

