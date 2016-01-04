# Decorator for a simple calculation function.
#
# Allows the function to work on an entire data product.
# Can also cache the calculation when needed.
def quick_calc(f):
  from pygeode.dataset import Dataset
  from ..interfaces import DerivedProduct
  from pygeode.var import Var
  def new_func (model):
    # Special case: single variable (no data product metadata to deal with)
    if isinstance(model,Var): return list(f(Dataset([model])))[0]
    out_datasets = []
    for in_dataset in model.datasets:
      try:
        out_vars = list(f(in_dataset))
      except KeyError: continue
      if len(out_vars) == 0: continue
      prefix = model.name+'_'+f.__name__
      out_datasets.append(Dataset(out_vars))
    out_product = DerivedProduct(out_datasets, name=prefix, title=model.title, cache=model.cache)
    out_product.color = model.color
    return out_product
  new_func.__name__ = f.__name__

  return new_func


