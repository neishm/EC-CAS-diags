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



from . import Diagnostic
class ZonalMean(Diagnostic):
  """
  Zonal mean (or standard deviation) of a field.
  """

  def __init__ (self, typestat='mean', **kwargs):
    super(ZonalMean,self).__init__(**kwargs)
    self.typestat = typestat
  def _check_dataset (self, dataset):
    from ..common import have_gridded_3d_data
    if super(ZonalMean,self)._check_dataset(dataset) is False:
      return False
    return have_gridded_3d_data(dataset)

  def _transform_inputs (self, inputs):
    from ..interfaces import DerivedProduct
    inputs = super(ZonalMean,self)._transform_inputs(inputs)
    return [DerivedProduct(ZonalMean._zonalmean(self,inp),source=inp) for inp in inputs]

  # Compute zonal mean.
  def _zonalmean (self, model, typestat=None):
    from ..common import remove_repeated_longitude

    fieldname = self.fieldname
    typestat = typestat or self.typestat

    var = model.find_best(fieldname)

    # Remove any repeated longtiude (for global data)
    var = remove_repeated_longitude(var)

    # Do the zonal mean
    if typestat == "mean":
      var_mean = var.nanmean('lon')
    else:
      # Make sure the zonal mean gets cached before use in subsequent
      # calculations.
      # Otherwise, it could cause an O(n^2) slowdown of the diagnostics.
      var_mean = self._zonalmean (model, typestat="mean")

    # Do a zonal standard deviation
    var_stdev = (var-var_mean).nanstdev('lon')
    var_stdev.name = fieldname
  
    if typestat == "stdev" : var=var_stdev   
    if typestat == "mean" : var=var_mean

    var = model.cache.write(var, prefix=model.name+'_zonal'+typestat+'_'+self.zaxis+'_'+fieldname+self.suffix, suffix=self.end_suffix)

    return var

