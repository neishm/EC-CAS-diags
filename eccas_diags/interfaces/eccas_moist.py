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


from .eccas_dry import ECCAS_Data

class ECCAS_Moist(ECCAS_Data):
  """
  EC-CAS model output from older experiments, where tracers were defined w.r.t.
  moist air.
  """

  # Modify the fields to all be w.r.t. moist air
  field_list = tuple((gem_name,long_name,units.replace('(dry_air)','(air)')) for gem_name,long_name,units in ECCAS_Data.field_list)

# Add this interface to the table.
from . import table
table['eccas-moist'] = ECCAS_Moist

