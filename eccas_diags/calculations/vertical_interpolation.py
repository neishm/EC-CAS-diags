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


from . import quick_calc

# Convert zonal mean data (on height)
@quick_calc
def gph (dataset):
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  from ..common import convert

  z = dataset['geopotential_height']
  z = convert(z, 'km')

  height = Height(range(68), name='height')

  for invar in dataset:
    if not invar.hasaxis('zaxis'):
      yield invar
      continue

    # Define the final expected order of axes
    # (since 'interpolate' moves the interpolated axis)
    axes = [a.name for a in invar.axes]
    axes[invar.whichaxis('zaxis')] = 'height'

    # Do the interpolation
    outvar = interpolate(invar, inaxis='zaxis', outaxis=height, inx=z)

    # Recover the expected order of axes
    outvar = outvar.transpose(*axes)

    yield outvar


  
# Convert zonal mean data (on pressure levels)
@quick_calc
def pres (dataset):
  from pygeode.interp import interpolate
  from pygeode.axis import Pres
  from ..common import convert
  import numpy as np

  p = dataset['air_pressure']
  p = convert (p, 'hPa')
  pres = Pres(np.exp(np.linspace(np.log(1000),np.log(.1),100)), name='pressure')

  for invar in dataset:

    if not invar.hasaxis('zaxis'):
      yield invar
      continue

    # Define the final expected order of axes
    # (since 'interpolate' moves the interpolated axis)
    axes = [a.name for a in invar.axes]
    axes[invar.whichaxis('zaxis')] = 'pressure'

    # Do the interpolation
    outvar = interpolate(invar, inaxis='zaxis', outaxis=pres, inx=p.log(), outx=pres.log())

    # Recover the expected order of axes
    outvar = outvar.transpose(*axes)

    yield outvar

