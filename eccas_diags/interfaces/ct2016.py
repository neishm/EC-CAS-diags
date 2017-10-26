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


# Interface for CT2013B molefraction data.
# Pretty much the same thing, except some preprocessing for
# pressure at the boundaries to get dp.

from .ct2013b import CT2013B_Data
class CT2016_Data(CT2013B_Data):
  """
  CarbonTracker CO2 products (molefractions, fluxes) from CT2016 and later.
  """

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, data):
    # Rename latitude/longitude to lat/lon, for compatibility with the
    # diagnostics.
    renames = {}
    if 'latitude' in data:
      renames['latitude'] = 'lat'
    if 'longitude' in data:
      renames['longitude'] = 'lon'

    if len(renames) > 0:
      data = data.rename_axes(**renames)

    # The rest of the decoding should be the same as previous CarbonTracker
    # versions.
    return super(CT2016_Data,cls).decode(data)


# Add this interface to the table.
from . import table
table['ct2016'] = CT2016_Data



