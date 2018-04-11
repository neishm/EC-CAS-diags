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


# Horizontal slice movie.

from . import TimeVaryingDiagnostic
class HorzSlice(TimeVaryingDiagnostic):
  """
  Sample data at a particular vertical level.
  """

  short_name = True  # Use shortened name for difference field.

  def __str__ (self):
    if hasattr(self,'level'):
      return 'level'+self.level
    else:
      return self.height+'m'

  def _check_dataset (self, dataset):
    from ..common import have_gridded_3d_data, have_level, have_height
    if super(HorzSlice,self)._check_dataset(dataset) is False:
      return False
    if hasattr(self,'level'):
      return have_gridded_3d_data(dataset) and have_level(float(self.level))(dataset)
    else:
      return have_gridded_3d_data(dataset) and have_height(float(self.height))(dataset)
  def __init__ (self, level=None, height=None, **kwargs):
    super(HorzSlice,self).__init__(**kwargs)
    if level is not None:
      self.level = level
    elif height is not None:
      self.height = height
    else:
      raise ValueError("Expected a level or height value.")
  def _transform_input (self, input):
    from ..common import number_of_timesteps, have_level, have_height, rotate_grid, find_and_convert
    from ..interfaces import DerivedProduct

    if hasattr(self,'level'):
      z = self.level
      c = find_and_convert(input, self.fieldname, self.units, maximize=number_of_timesteps, requirement=have_level(float(z)))
    else:
      z = self.height
      c = find_and_convert(input, self.fieldname, self.units, maximize=number_of_timesteps, requirement=have_height(float(z)))

    c = c(zaxis=float(z))

    # Rotate the longitudes to 0,360
    c = rotate_grid(c)

    # Cache the data
    c = input.cache.write(c,prefix=input.name+'_'+c.zaxis.name+z+"_"+self.fieldname+self.suffix, suffix=self.end_suffix)

    return DerivedProduct(c, source=input)

  def _transform_inputs (self, inputs):
    inputs = super(HorzSlice,self)._transform_inputs(inputs)
    return [HorzSlice._transform_input(self,inp) for inp in inputs]

  def do (self, inputs):
    from .movie import ContourMovie

    if hasattr(self,'level'):
      plotname = self.fieldname+"_level"+self.level
      title = '%s at level %s'%(self.fieldname,self.level)
    else:
      plotname = self.fieldname+"_"+self.height+"m"
      title = '%s at height %s'%(self.fieldname,self.height)
    prefix = '_'.join(inp.name for inp in inputs) + '_' + plotname + self.suffix + self.end_suffix

    fields = [inp.datasets[0].vars[0] for inp in inputs]
    subtitles = [inp.title for inp in inputs]

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(inputs),1)

    cmaps = [inp.cmap for inp in inputs]
    cap_extremes = [getattr(inp,'cap_extremes',False) for inp in inputs]

    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio, cmaps=cmaps, cap_extremes=cap_extremes)

    movie.save (outdir=self.outdir, prefix=prefix)


from . import table
table['horz-slice'] = HorzSlice

