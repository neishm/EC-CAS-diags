from .xcol import XCol
from .movie_zonal import ZonalMean
class LatDist(ZonalMean,XCol):
  """
  Show the latitudonal distribution of a field, animated in time.  Values are
  averaged along the vertical and longitudonal directions.
  """
  def __init__(self, **kwargs):
    # Use "model levels" for zonal mean, to effectively ignore the vertical
    # structure (since we don't have vertical levels after avg column!)
    kwargs['zaxis'] = 'model'
    super(LatDist,self).__init__(**kwargs)
  def do (self, inputs):

    plotname = 'latdist_'+self.fieldname
    prefix = '_'.join(inp.name for inp in inputs) + '_' + plotname + self.suffix + self.end_suffix

    fields = [inp.find_best(self.fieldname) for inp in inputs]
    title = 'Latitudonal distribution of '+self.fieldname

    movie = LatDistMovie(fields, inputs, title=title, figsize=(10,4))

    movie.save (outdir=self.outdir, prefix=prefix)

# Instead of tiling the fields, overlay them all on a single plot.
# Copied and modified from ContourMovie code.
from .movie import Movie
class LatDistMovie(Movie):
  def __init__ (self, fields, inputs, title, **kwargs):
    self.inputs = inputs
    self.title = title
    Movie.__init__(self, fields, **kwargs)
  def render (self, fig, fields, datestring):
    from matplotlib import pyplot as pl
    from .contouring import get_contours
    pl.title (self.title + " " + datestring)

    for field,inp in zip(fields,self.inputs):
      pl.plot (field.lat.values, field.get().flatten(), color=inp.color, linestyle=inp.linestyle, label=inp.title)
    pl.legend(loc='best')
    # Use contour logic to pick a good range.
    low, high = self.global_range[fields[0].name]
    clevs = get_contours(low,high)
    pl.xlabel("Latitude")
    pl.xlim(-90,90)
    pl.ylabel("%s (%s)"%(fields[0].name,fields[0].atts['units']))
    pl.ylim(clevs[0],clevs[-1])

from . import table
table['lat-dist'] = LatDist

