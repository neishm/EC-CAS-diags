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


from eccas_flux import ECCAS_Flux_Data

class ECCAS_Bayesian_Flux(ECCAS_Flux_Data):

  field_list = list(ECCAS_Flux_Data.field_list)
  for i in range(1,12):
    field_list.append(('EL%02d'%i, 'CO2_landunit_%02d_flux'%i, 'g(C) s-1'))
  for i in range(1,12):
    field_list.append(('EO%02d'%i, 'CO2_oceanunit_%02d_flux'%i, 'g(C) s-1'))
  field_list = tuple(field_list)

# Add this interface to the table.
from . import table
#table['eccas-bayesian-flux'] = ECCAS_Bayesian_Flux

