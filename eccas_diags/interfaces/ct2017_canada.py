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


# Interface for CT2017 data.

from .ct2016_canada import CT2016_Canada_Data
class CT2017_Canada_Data(CT2016_Canada_Data):
  """
  CarbonTracker CO2 products (molefractions, fluxes) from CT2017 and later.
  """

  # List of all possible fields we expect from the data
  # (original_name, standard_name, units)
  field_list = CT2016_Canada_Data.field_list + (
    ('fm', 'CO2_fossil_flux', 'mol m-2 s-1'),
    ('fo', 'CO2_fossil_flux', 'mol m-2 s-1'),
    ('b4', 'CO2_bio_flux', 'mol m-2 s-1'),
    ('bc', 'CO2_bio_flux', 'mol m-2 s-1'),
    ('oi', 'CO2_ocean_flux', 'mol m-2 s-1'),
    ('oc', 'CO2_ocean_flux', 'mol m-2 s-1'),
    ('w4', 'CO2_fire_flux', 'mol m-2 s-1'),
    ('wc', 'CO2_fire_flux', 'mol m-2 s-1'),
  )

# Add this interface to the table.
from . import table
table['ct2017-canada'] = CT2017_Canada_Data



