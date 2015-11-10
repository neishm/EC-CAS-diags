
def zonalmean (var):
  from ..common import remove_repeated_longitude

  # Remove any repeated longtiude (for global data)
  var = remove_repeated_longitude(var)

  # Do the zonal mean
  var = var.nanmean('lon')

  # Cache the data
  #TODO
#  var = model.cache.write(var, prefix='zonal'+typestat+'_pres_'+fieldname)

  return var

def zonalstd (var):
  from ..common import remove_repeated_longitude

  var_mean = zonalmean(var)

  # Remove any repeated longtiude (for global data)
  var = remove_repeated_longitude(var)

  # Do the zonal standard deviation
  var = (var-var_mean).nanstdev('lon')
  var.name = var_mean.name

  # Cache the data
  #TODO
#  var = model.cache.write(var, prefix='zonal'+typestat+'_pres_'+fieldname)

  return var


def all_zonalmean (model):
  from common import number_of_levels, number_of_timesteps
  from ..interfaces import DerivedProduct
  from pygeode.dataset import Dataset
  out_datasets = []
  for in_dataset in model.datasets:
    out_dataset = []
    for in_var in in_dataset:
      if not in_var.hasaxis('lon'): continue
      out_var = zonalmean(in_var)
      out_dataset.append(out_var)
    if len(out_dataset) == 0: continue
    out_dataset = Dataset(out_dataset)
    out_datasets.append(out_dataset)
  out = DerivedProduct(out_datasets, name=model.name+'_zonalmean', title=model.title, color=model.color, cache=model.cache)
  return out

