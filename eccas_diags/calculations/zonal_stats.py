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


from . import quick_calc

@quick_calc
def zonalmean (dataset):
  from ..common import remove_repeated_longitude

  for invar in dataset:
    if not invar.hasaxis('lon'):
      yield invar
      continue

    # Remove any repeated longtiude (for global data)
    invar = remove_repeated_longitude(invar)

    # Do the zonal mean
    yield invar.nanmean('lon')


@quick_calc
def zonalstdev (dataset):
  from ..common import remove_repeated_longitude

  for invar in dataset:
    if not invar.hasaxis('lon'):
      yield invar
      continue

    # Remove any repeated longtiude (for global data)
    invar = remove_repeated_longitude(invar)

    # Do the standard deviation (NOTE: single-pass algorithm, may lose precision)
    yield invar.nanstdev('lon')


