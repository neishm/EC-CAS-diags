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


# Modified interface for CT2016, which masks out the fluxes everywhere
# but Canada.

from .ct2016 import CT2016_Data
class CT2016_Canada_Data(CT2016_Data):
  """
  CarbonTracker CO2 products (molefractions, fluxes) from CT2016 and later.
  """

  # Modify the mask file so it has the same names for lat/lon
  @classmethod
  def open_file (cls, filename):
    from pygeode.formats import netcdf
    ct = super(CT2016_Canada_Data,cls).open_file(filename)
    mask = netcdf.open("/space/hall1/sitestore/eccc/crd/ccmr/scrd701/misc/regions/GCP_methane_regions_1x1.nc").REG
    mask = mask.sorted('LAT')
    mask = mask.rename_axes(LAT='latitude',LON='longitude')
    return ct + mask

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, data):
    from pygeode.dataset import asdataset
    from pygeode.var import copy_meta
    data = super(CT2016_Canada_Data,cls).decode(data)
    data = asdataset(data)
    if 'REG' in data and 'CO2_flux' in data:
      REG = data.REG
      data -= 'REG'
      co2_canada = data.CO2_flux*(REG==1)*(REG.lon>=-141)
      copy_meta(data.CO2_flux,co2_canada)
      co2_canada.name = 'CO2_Canada_flux'
      co2_no_canada = data.CO2_flux - co2_canada
      copy_meta(data.CO2_flux,co2_no_canada)
      co2_no_canada.name = 'CO2_no_Canada_flux'
      data = data + co2_canada + co2_no_canada
    return data

# Add this interface to the table.
from . import table
table['ct2016-canada'] = CT2016_Canada_Data

