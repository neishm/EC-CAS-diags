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
    pl.legend(loc='upper left')
    # Use contour logic to pick a good range.
    low, high = self.global_range[fields[0].name]
    clevs = get_contours(low,high)
    pl.xlabel("Latitude")
    pl.xlim(-90,90)
    pl.ylabel("%s (%s)"%(fields[0].name,fields[0].atts['units']))
    pl.ylim(clevs[0],clevs[-1])

from . import table
table['lat-dist'] = LatDist

