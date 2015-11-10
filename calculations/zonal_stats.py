
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
  fieldnames = [v.name for d in model.datasets for v in d]
  fieldnames = sorted(set(fieldnames))
  outvars = []
  for fieldname in fieldnames:
    var = model.find_best(fieldname, maximize=(number_of_levels,number_of_timesteps))
    if not var.hasaxis('lon'): continue
    var = zonalmean(var)
    outvars.append(var)
  outdata = DerivedProduct(outvars, name=model.name+'_zonalmean', title=model.title, color=model.color, cache=model.cache)
  return outdata

