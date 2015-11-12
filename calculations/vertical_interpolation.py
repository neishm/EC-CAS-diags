
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
  from pygeode.dataset import Dataset
  out_datasets = []
  for in_dataset in model.datasets:
    if 'geopotential_height' not in in_dataset: continue
    z = in_dataset.geopotential_height
    out_dataset = []
    for in_var in in_dataset:
      if not in_var.hasaxis('zaxis'): continue
      out_var = gph(in_var,z)
      out_dataset.append(out_var)
    if len(out_dataset) == 0: continue
    out_dataset = Dataset(out_dataset)
    out_datasets.append(out_dataset)
  out = DerivedProduct(out_datasets, name=model.name+'_gph', title=model.title, color=model.color, cache=model.cache)
  #TODO: When there's more than one copy an an output field, use the one that had the largest number of vertical levels on input?
  return out

  
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
  from pygeode.dataset import Dataset
  out_datasets = []
  for in_dataset in model.datasets:
    if 'air_pressure' not in in_dataset: continue
    p = in_dataset.air_pressure
    out_dataset = []
    for in_var in in_dataset:
      if not in_var.hasaxis('zaxis'): continue
      out_var = pres(in_var,p)
      out_dataset.append(out_var)
    if len(out_dataset) == 0: continue
    out_dataset = Dataset(out_dataset)
    out_datasets.append(out_dataset)
  out = DerivedProduct(out_datasets, name=model.name+'_pres', title=model.title, color=model.color, cache=model.cache)
  #TODO: When there's more than one copy an an output field, use the one that had the largest number of vertical levels on input?
  return out

