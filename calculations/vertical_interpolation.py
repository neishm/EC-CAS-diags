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
    if not invar.hasaxis('zaxis'): continue

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

    if not invar.hasaxis('zaxis'): continue

    # Define the final expected order of axes
    # (since 'interpolate' moves the interpolated axis)
    axes = [a.name for a in invar.axes]
    axes[invar.whichaxis('zaxis')] = 'pressure'

    # Do the interpolation
    outvar = interpolate(invar, inaxis='zaxis', outaxis=pres, inx=p.log(), outx=pres.log())

    # Recover the expected order of axes
    outvar = outvar.transpose(*axes)

    yield outvar

