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


from .gem import GEM_Data
from .eccas_dry import ECCAS_Data

class ECCAS_NoCanada(GEM_Data):
  """
  EC-CAS model output, with Canada masked out.
  """

  field_list = GEM_Data.field_list + (
    ('CO2', 'CO2_with_Canada', 'ug(C) kg(dry_air)-1'),
    ('NOCA', 'CO2', 'ug(C) kg(dry_air)-1'),
    ('XCO2', 'XCO2_with_Canada', 'ug(C) kg(dry_air)-1'),
    ('XNOC', 'XCO2', 'ug(C) kg(dry_air)-1'),
  )


  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    name = super(ECCAS_NoCanada,ECCAS_NoCanada).get_dataname(dirname)
    # Modify the name so it doesn't collide with the regular model output.
    return name+'_nocanada'



# Add this interface to the table.
from . import table
table['eccas-nocanada'] = ECCAS_NoCanada

