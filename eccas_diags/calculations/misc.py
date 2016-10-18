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


# Miscellaneous wrappers for Var-related methods

from . import quick_calc

# Derivative function
@quick_calc
def deriv (dataset, daxis, **kwargs):

  # Skip variables with no time axis
  for invar in dataset:
    if not invar.hasaxis(daxis):
      #yield invar
      continue

    # Do the derivative
    outvar = invar.deriv(daxis, **kwargs)
    # Fix the output name
    outvar.name = invar.name

    yield outvar

