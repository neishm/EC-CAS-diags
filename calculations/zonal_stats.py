
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



