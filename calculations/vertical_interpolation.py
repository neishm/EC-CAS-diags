
# Convert zonal mean data (on height)
def gph (var, z):
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  from ..common import convert

  z = convert(z, 'm')

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

def all_gph (model):
  from common import number_of_levels, number_of_timesteps
  from ..interfaces import DerivedProduct
  fieldnames = [v.name for d in model.datasets for v in d]
  fieldnames = sorted(set(fieldnames))
  outvars = []
  for fieldname in fieldnames:
    try:
      if fieldname == 'geopotential_height': continue
      var, z = model.find_best([fieldname,'geopotential_height'], maximize=(number_of_levels,number_of_timesteps))
      if not var.hasaxis('zaxis'): continue
      var = gph(var,z)
      outvars.append(var)
    except KeyError: pass # Unable to get concurrent var / geopotential height
  outdata = DerivedProduct(outvars, name=model.name+'_gph', title=model.title, color=model.color, cache=model.cache)
  return outdata
  
# Convert zonal mean data (on pressure levels)
def pres (var, p):
  from pygeode.interp import interpolate
  from pygeode.axis import Pres
  from ..common import convert
  import numpy as np

  p = convert (p, 'hPa')
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

def all_pres (model):
  from common import number_of_levels, number_of_timesteps
  from ..interfaces import DerivedProduct
  fieldnames = [v.name for d in model.datasets for v in d]
  fieldnames = sorted(set(fieldnames))
  outvars = []
  for fieldname in fieldnames:
    try:
      if fieldname == 'air_pressure': continue
      var, z = model.find_best([fieldname,'air_pressure'], maximize=(number_of_levels,number_of_timesteps))
      if not var.hasaxis('zaxis'): continue
      var = pres(var,z)
      outvars.append(var)
    except KeyError: pass # Unable to get concurrent var / geopotential height
  outdata = DerivedProduct(outvars, name=model.name+'_pres', title=model.title, color=model.color, cache=model.cache)
  return outdata
  

