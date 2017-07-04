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



from . import Diagnostic
class VInterp (Diagnostic):
  """
  Vertical interpolation of fields.
  """

  def __str__ (self):
    return self.zaxis

  @classmethod
  def add_args (cls, parser, handled=[]):
    super(VInterp,cls).add_args(parser)
    if len(handled) > 0: return  # Only run once
    parser.add_argument('--zaxis', action='store', choices=('gph','plev','model'), default='gph', help="The vertical coordinate to use for vertical interpolation (e.g. for zonal mean plots).  Default is gph.")
    handled.append(True)
  def __init__ (self, zaxis='gph', **kwargs):
    super(VInterp,self).__init__(**kwargs)
    self.zaxis = zaxis
  def _check_dataset (self, dataset):
    from ..common import have_vertical_data
    if super(VInterp,self)._check_dataset(dataset) is False:
      return False
    if self.zaxis == 'gph' and 'geopotential_height' not in dataset:
      return False
    if self.zaxis == 'plev' and 'air_pressure' not in dataset:
      return False
    return have_vertical_data(dataset)
  def _transform_input (self, input):
    from ..interfaces import DerivedProduct
    if self.zaxis == 'gph':
      var = self._interp_gph (input)
    elif self.zaxis == 'plev':
      var = self._interp_pres (input)
    elif self.zaxis == 'model':
      var = input  # No interpolation
    else:
      raise ValueError("Unhandled zaxis type '%s'"%self.zaxis)
    return DerivedProduct(var, source=input)

  def _transform_inputs (self, inputs):
    inputs = super(VInterp,self)._transform_inputs(inputs)
    return [VInterp._transform_input(self,inp) for inp in inputs]

  # Interpolate to height
  def _interp_gph (self, model):
    from pygeode.interp import interpolate
    from pygeode.axis import Height
    from ..common import find_and_convert, number_of_levels, number_of_timesteps
    import numpy as np

    fieldname = self.fieldname

    var, z = find_and_convert(model, [fieldname,'geopotential_height'], [self.units,'m'], maximize=(number_of_levels,number_of_timesteps))

    height = Height(range(68), name='height')

    # Define the final expected order of axes
    # (since 'interpolate' moves the interpolated axis)
    axes = [a.name for a in var.axes]
    axes[var.whichaxis('zaxis')] = 'height'

    # Do the interpolation
    var = interpolate(var, inaxis='zaxis', outaxis=height, inx=z/1000.)

    # Recover the expected order of axes
    var = var.transpose(*axes)

    return var


  # Interpolate to pressure levels
  def _interp_pres (self, model):
    from pygeode.interp import interpolate
    from pygeode.axis import Pres
    from ..common import find_and_convert, number_of_levels, number_of_timesteps
    import numpy as np

    fieldname = self.fieldname

    var, p = find_and_convert(model, [fieldname,'air_pressure'], [self.units,'hPa'], maximize=(number_of_levels,number_of_timesteps))

    pres = Pres(np.exp(np.linspace(np.log(1000),np.log(.1),100)), name='pressure')

    # Define the final expected order of axes
    # (since 'interpolate' moves the interpolated axis)
    axes = [a.name for a in var.axes]
    axes[var.whichaxis('zaxis')] = 'pressure'

    # Do the interpolation
    var = interpolate(var, inaxis='zaxis', outaxis=pres, inx=p.log(), outx=pres.log())

    # Recover the expected order of axes
    var = var.transpose(*axes)

    return var




