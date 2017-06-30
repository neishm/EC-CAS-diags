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


from .movie_zonal import ZonalMean
from .diff import Diff
class ZonalSTDofDiff(ZonalMean,Diff):
  """
  Zonal standard deviation of the difference between two fields, animated in time.
  """
  cache_diff = False
  rename_diff = False

  # Rename the CO2 field to CO2_diff, *after* difference and zonal std is done.
  # Need a different name, so the color bar is unassociated with the other
  # panels.
  def _transform_inputs(self, inputs):
    from pygeode.dataset import Dataset
    inputs = super(ZonalSTDofDiff,self)._transform_inputs(inputs)
    field = inputs[-1].datasets[0].vars[0]
    field.name += '_diff'
    inputs[-1].datasets = (Dataset([field]),)
    return inputs

from . import table
table['zonal-std-of-diff'] = ZonalSTDofDiff

