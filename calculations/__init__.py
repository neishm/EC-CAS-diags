# Decorator for a simple calculation function.
#
# Allows the function to work on an entire data product.
# Can also cache the calculation when needed.
def quick_calc(f):
  from pygeode.dataset import Dataset
  from ..interfaces import DerivedProduct
  def new_func (model):
    out_datasets = []
    for in_dataset in model.datasets:
      try:
        out_vars = list(f(in_dataset))
      except KeyError: continue
      if len(out_vars) == 0: continue
      prefix = model.name+'_'+f.__name__
      out_datasets.append(Dataset(out_vars))
    out_product = DerivedProduct(out_datasets, name=prefix, title=model.title, color=model.color, cache=model.cache)
    return out_product
  new_func.__name__ = f.__name__

  return new_func


