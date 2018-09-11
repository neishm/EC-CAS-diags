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

# CAMS interface, adapted from MACC interface.

from . import DataProduct
class CAMS_Data(DataProduct):
  """
  Model data from CAMSRA
  """

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('lnsp', 'logarithm_of_surface_pressure', ''),
    ('oh', 'OH', 'kg(OH) kg(air)-1'),
    ('q', 'specific_humidity', 'kg(H2O) kg(air)-1'),
    ('t', 'air_temperature', 'K'),
  )

  # Method to open a single file
  @classmethod
  def open_file (cls, filename):
    from pygeode.formats import netcdf
    from pygeode.dataset import Dataset
    from pygeode.timeaxis import StandardTime
    from ..common import fix_timeaxis
    f = netcdf.open(filename)
    # Fudge the axis so we start on the first of the month.
    time = StandardTime(year=f.time.year, month=f.time.month)
    f = f.replace_axes(time=time)
    # Use a consistent start date for all files.
    f = fix_timeaxis(f)
    # Hack in the interface values, so they are available from all datasets.
    # Assume these are the same for all CAMS data.
    if 'hyai' in f:
      cls.A_interface = f.hyai
      cls.B_interface = f.hybi
    # Remove vertical coordinate from surface pressure, so it can co-exist
    # with the 3D data.
    if 'lev' in f and len(f.lev) == 1:
      f = Dataset([v.squeeze('lev') if v.hasaxis('lev') else v for v in f])
    
    # The mid-point coefficients are on the same model levels as the data.
    if 'lev' in f:
      f = f.replace_axes(nhym=f.lev)
    return f


  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, dataset):
    from pygeode.axis import Hybrid
    from pygeode.ufunc import exp
    from pygeode.var import Var
    import numpy as np

    zaxis = None

    if 'lev' in dataset:
      A_interface = cls.A_interface
      B_interface = cls.B_interface
      A = dataset.hyam
      B = dataset.hybm

      dA = (A_interface[1:] - A_interface[:-1])
      dB = (B_interface[1:] - B_interface[:-1])

      # Create a proper z-axis
      zaxis = Hybrid(dataset.lev.values, A=A, B=B)
      dataset = dataset.replace_axes(lev=zaxis)

    # Apply fieldname conversions
    dataset = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Add pressure info
    if 'logarithm_of_surface_pressure' in data and zaxis is not None:
      Ps = exp(data['logarithm_of_surface_pressure'])
      Ps.atts['units'] = 'Pa'
      data['surface_pressure'] = Ps
      A = zaxis.auxasvar('A')
      B = zaxis.auxasvar('B')
      P = A + B*Ps
      P = P.transpose('time','zaxis','lat','lon')
      P.atts['units'] = 'Pa'
      data['air_pressure'] = P

      dA = Var([zaxis], values=dA)
      dB = Var([zaxis], values=dB)
      dP = dA + dB*Ps
      dP = dP.transpose('time','zaxis','lat','lon')
      dP.atts['units'] = 'Pa'
      data['dp'] = dP

    # Compute air density (for converting OH to number density).
    if 'air_pressure' in data and 'air_temperature' in data and 'specific_humidity' in data:
      T = data['air_temperature']
      q = data['specific_humidity']
      p = data['air_pressure']
      Rd = 287.05
      Tv = (1 + 0.608*q)*T
      rho = p / (Rd * Tv)
      rho.atts['units'] = 'kg(air) m-3'
      data['density'] = rho

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Add extra fields that will be useful for the diagnostics.
    data = cls._add_extra_fields(data)

    return data


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return glob(dirname+"/INPUT_CAMSRA_*.nc")



# Add this interface to the table.
from . import table
table['cams'] = CAMS_Data

