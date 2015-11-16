# Decorator for a simple calculation function.
#
# Allows the function to work on an entire data product.
# Can also cache the calculation when needed.
def quick_calc(f):
  from pygeode.dataset import Dataset
  from ..interfaces import DerivedProduct
  def new_func (*models, **kwargs):
    filter_vars = kwargs.get('vars',None) or kwargs.get('var',None)
    if isinstance(filter_vars,str): filter_vars = [filter_vars]
    out_datasets = []
    for in_datasets in zip(*[m.datasets for m in models]):
      try:
        out_vars = list(f(*in_datasets))
      except KeyError: continue
      if filter_vars is not None:
        out_vars = [v for v in out_vars if v.name in filter_vars]
      if len(out_vars) == 0: continue
      prefix = models[0].name+'_'+f.__name__
      if len(models) > 1:
        prefix += '_' + '_'.join(m.name for m in models[1:])
      out_datasets.append(Dataset(out_vars))
    out_product = DerivedProduct(out_datasets, name=prefix, title=m.title, color=m.color, cache=m.cache)
    return out_product
  new_func.__name__ = f.__name__

  return new_func


