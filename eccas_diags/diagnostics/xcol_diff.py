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


# Average column diagnostic with extra panel for differences

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.


from .xcol import XCol
from .diff import Diff
class XColDiff(Diff,XCol):
  """
  Compute the difference of two fields, after taking the avarage column of
  each.
  """

from . import table
table['xcol-diff'] = XColDiff

