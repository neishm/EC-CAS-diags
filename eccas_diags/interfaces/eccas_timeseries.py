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


# Interface for EC-CAS timeseries data.
# Use the EC-CAS fieldnames / units, and the FSTD timeseries file format.

from . import eccas_dry, fstd_timeseries

class ECCAS_Timeseries(fstd_timeseries.FSTD_Timeseries, eccas_dry.ECCAS_Data):
  """
  EC-CAS model output (timeseries output at select locations).
  """

  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    from os.path import exists
    if exists(dirname+"/time_series"):
      dirname += "/time_series"
    return glob(dirname+"/time_series*.fst")


# Add this interface to the table.
from . import table
table['eccas-timeseries'] = ECCAS_Timeseries

