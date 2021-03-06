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


def where_holes (experiment, outdir):
  from pygeode.formats import netcdf
  from os.path import exists
  from .timeseries import get_sfc_data

  co2 = get_sfc_data(experiment,'CO2')

  holes = (co2 < 100)

  count = (holes * 1).sum('time')
  count.name = "hole_count"

  outfile = outdir+"/%s_hole_count.nc"%experiment.name
  if not exists(outfile):
    netcdf.save(outfile, count)

