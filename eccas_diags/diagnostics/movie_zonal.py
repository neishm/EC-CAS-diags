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



from .zonalmean import ZonalMean as Zonal
from .vinterp import VInterp
from . import TimeVaryingDiagnostic
class ZonalMean(Zonal,VInterp,TimeVaryingDiagnostic):
  """
  Zonal mean (or standard deviation) of a field, animated in time.
  """

  def __str__ (self):
    return 'zonal'+self.typestat+'_'+self.zaxis

  def do (self, inputs):
    from .movie import ZonalMovie

    prefix = '_'.join(inp.name for inp in inputs) + '_zonal'+self.typestat+'_'+self.fieldname+'_on_'+self.zaxis+self.suffix+self.end_suffix
    title = 'Zonal %s %s (in %s)'%(self.typestat,self.fieldname,self.units)
    aspect_ratio = 1.0
    shape = (1,len(inputs))

    subtitles = [inp.title for inp in inputs]

    fields = [inp.datasets[0].vars[0] for inp in inputs]

    cmaps = [inp.cmap for inp in inputs]
    cap_extremes = [getattr(inp,'cap_extremes',False) for inp in inputs]

    movie = ZonalMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio=aspect_ratio, cmaps=cmaps, cap_extremes=cap_extremes)

    movie.save (outdir=self.outdir, prefix=prefix)


from . import table
table['zonal-movie'] = ZonalMean

