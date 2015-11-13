# Decorator to complete a unary calculation.
#
# The original function should take a single dataset, and generate the
# output vars.
#
# After applying the decorator, the function will take a data product and
# return a data product with the calculation applied.
#
# If caching is requested, the data will be cached as needed.
def unary_calc(func=None, cache=False):
  def wrapper(f):
    from pygeode.dataset import Dataset
    from ..interfaces import DerivedProduct
    def new_func (m):
      out_datasets = []
      for in_dataset in m.datasets:
        try:
          out_vars = list(f(in_dataset))
        except KeyError: continue
        if len(out_vars) == 0: continue
        if cache is True:
          out_vars = [m.cache.delayed_write(v, prefix=m.name+'_'+f.__name__+'_'+v.name) for v in out_vars]
        out_datasets.append(Dataset(out_vars))
      out_product = DerivedProduct(out_datasets, name=m.name+'_'+f.__name__, title=m.title, color=m.color, cache=m.cache)
      return out_product
    new_func.__name__ = f.__name__
    return new_func

  if func is None: return wrapper
  return wrapper(func)

