from . import unary_calc

@unary_calc(cache=True)
def zonalmean (dataset):
  from ..common import remove_repeated_longitude

  for invar in dataset:
    if not invar.hasaxis('lon'): continue

    # Remove any repeated longtiude (for global data)
    invar = remove_repeated_longitude(invar)

    # Do the zonal mean
    yield invar.nanmean('lon')


@unary_calc(cache=True)
def zonalrms (dataset):
  from ..common import remove_repeated_longitude

  for invar in dataset:
    if not invar.hasaxis('lon'): continue

    # Remove any repeated longtiude (for global data)
    invar = remove_repeated_longitude(invar)

    outvar = (invar**2).nanmean('lon').sqrt()
    outvar.name = invar.name

    yield outvar

@unary_calc
def _zonal_filter (dataset):
  for invar in dataset:
    if not invar.hasaxis('lon'): continue
    yield invar


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
      # Cache the data (delayed)
      if model.cache is not None:
        out_var = model.cache.delayed_write(out_var, prefix=model.name+'_zonalmean_'+in_var.name)
      out_dataset.append(out_var)
    if len(out_dataset) == 0: continue
    out_dataset = Dataset(out_dataset)
    out_datasets.append(out_dataset)
  out = DerivedProduct(out_datasets, name=model.name+'_zonalmean', title=model.title, color=model.color, cache=model.cache)
  return out


def all_zonalstd (model):
  from common import number_of_levels, number_of_timesteps
  from ..interfaces import DerivedProduct
  from pygeode.dataset import Dataset
  out_datasets = []
  for in_dataset in model.datasets:
    out_dataset = []
    for in_var in in_dataset:
      if not in_var.hasaxis('lon'): continue
      mean_var = zonalmean(in_var)
      # Cache the mean data
      if model.cache is not None:
        # TODO: use the existing all_zonalmean function for this part?
        mean_var = model.cache.delayed_write(mean_var, prefix=model.name+'_zonalmean_'+in_var.name)
      # Subtract the mean before computing the standard deviation
      out_var = zonalstd(in_var-mean_var)
      out_var.name = in_var.name
      # Cache the data (delayed)
      if model.cache is not None:
        out_var = model.cache.delayed_write(out_var, prefix=model.name+'_zonalstd_'+in_var.name)
      out_dataset.append(out_var)
    if len(out_dataset) == 0: continue
    out_dataset = Dataset(out_dataset)
    out_datasets.append(out_dataset)
  out = DerivedProduct(out_datasets, name=model.name+'_zonalstd', title=model.title, color=model.color, cache=model.cache)
  return out


