###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################


# Decorator for a simple calculation function.
#
# Allows the function to work on an entire data product.
# Can also cache the calculation when needed.
def quick_calc(f):
  from pygeode.dataset import Dataset
  from ..interfaces import DerivedProduct
  from pygeode.var import Var
  def new_func (model,*args,**kwargs):
    # Special case: single variable (no data product metadata to deal with)
    if isinstance(model,Var): return list(f(Dataset([model]),*args,**kwargs))[0]
    out_datasets = []
    for in_dataset in model.datasets:
      try:
        out_vars = list(f(in_dataset,*args,**kwargs))
      except KeyError: continue
      if len(out_vars) == 0: continue
      out_datasets.append(Dataset(out_vars))
    out_product = DerivedProduct(out_datasets, source=model)
    out_product.name = out_product.name+'_'+f.__name__
    return out_product
  new_func.__name__ = f.__name__

  return new_func


