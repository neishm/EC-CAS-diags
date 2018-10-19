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

# An array filled with zeros.
from pygeode.var import Var
class Zeros(Var):
  def __init__(self, axes, dtype='float64'):
    from pygeode.var import Var
    Var.__init__(self, axes, dtype=dtype)
  def getview (self, view, pbar):
    import numpy as np
    return np.zeros(view.shape, dtype=self.dtype)

class AimNorth_Data(ECCAS_Data):
  """
  Input files for Aim-North OSSE experiment.
  """

  field_list = (
    ('permafrost_emissions', 'CO2_permafrost_flux', 'kg(C) m-2 s-1'),
  )


  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    from pygeode.axis import Lat, Lon
    from pygeode.timeaxis import StandardTime
    from pygeode.concat import concat
    from pygeode.dataset import Dataset
    import numpy as np
    f = netcdf.open(filename)
    # Decode the coordinates.
    time = StandardTime(values=f.day.values-1, startdate={'year':2015,'month':1,'day':1}, units='days')
    f = f.replace_axes(latitude=Lat, longitude=Lon, day=time, keep_old_name=False)
    # Pad to full global grid (all latitudes).
    missing_lat = Lat(np.arange(34.25,-89.95-0.1,-0.1))
    zeros = Zeros([f.time,missing_lat,f.lon])
    full_grid = concat([f.permafrost_emissions,zeros],iaxis='lat')
    # Pad to full year
    missing_time_before = StandardTime(values=np.arange(0,f.time.values[0],1), startdate=f.time.startdate, units='days')
    missing_time_after = StandardTime(values=np.arange(f.time.values[-1]+1,365,1), startdate=f.time.startdate, units='days')
    zeros_before = Zeros([missing_time_before,full_grid.lat,full_grid.lon])
    zeros_after = Zeros([missing_time_after,full_grid.lat,full_grid.lon])
    all_year = concat([zeros_before,full_grid,zeros_after],iaxis='time')
    all_year.name = 'permafrost_emissions'
    return Dataset([all_year])

# Add this interface to the table.
from . import table
table['aim-north-osse'] = AimNorth_Data


