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



from . import DataProduct
class TM5_Data(DataProduct):
  """
  Data from the TM5 model.  Currently only handles the OH field that was used
  for methane loss in the TransCom CH4 intercomparison protocol.
  """

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('OH', 'OH', 'molecules cm-3'),
    ('PSURF', 'surface_pressure', 'Pa'),
  )

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    from pygeode.var import Var
    dataset = netcdf.open(filename)
    # Put the dA / dB in here.
    A_interface = dataset.A.get()
    B_interface = dataset.B.get()
    dA = (A_interface[:-1] - A_interface[1:])
    dB = (B_interface[:-1] - B_interface[1:])
    dA = Var(name='dA', axes=[dataset.LEVEL], values=dA)
    dB = Var(name='dB', axes=[dataset.LEVEL], values=dB)
    # Put the A and B coefficients for staggered levels in here.
    A_t = (A_interface[1:] + A_interface[:-1]) * 0.5
    B_t = (B_interface[1:] + B_interface[:-1]) * 0.5
    A_t = Var(name='A_t', axes=[dataset.LEVEL], values=A_t)
    B_t = Var(name='B_t', axes=[dataset.LEVEL], values=B_t)
    dataset = dataset + dA + dB + A_t + B_t
    return dataset


  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, dataset):
    from pygeode.axis import Hybrid
    from pygeode.timeaxis import StandardTime
    from pygeode.ufunc import exp
    from pygeode.var import Var
    import numpy as np


    # Get some axis info that will be needed for further calculations.
    A_t = getattr(dataset,'A_t',None)
    B_t = getattr(dataset,'B_t',None)
    dA = getattr(dataset,'dA',None)
    dB = getattr(dataset,'dB',None)
    zaxis = getattr(dataset,'LEVEL',None)
    lat = getattr(dataset,'LATITUDE',None)
    lon = getattr(dataset,'LONGITUDE',None)
    time = getattr(dataset,'TIME',None)

    # Create a proper z-axis
    if zaxis is not None and A_t is not None and B_t is not None:
      zaxis = Hybrid(zaxis.values, A=A_t.get(), B=B_t.get())

    # Create a proper time axis
    if time is not None:
      time = StandardTime(month=time.values)

    dataset = list(dataset)

    for i, var in enumerate(dataset):
      if var.hasaxis('LEVEL'):
        var = var.replace_axes(LEVEL=zaxis)
      if var.hasaxis('TIME'):
        var = var.replace_axes(TIME=time)
      # Refresh the variables that were already extracted.
      if var.name == 'A_t': A_t = var
      if var.name == 'B_t': B_t = var
      if var.name == 'dA': dA = var
      if var.name == 'dB': dB = var
      dataset[i] = var

    # Apply fieldname conversions
    dataset = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Add pressure info
    if 'surface_pressure' in data and zaxis is not None:
      Ps = data['surface_pressure']
      P = A_t + B_t*Ps
      P = P.transpose('time','zaxis','lat','lon')
      P.atts['units'] = 'Pa'
      data['air_pressure'] = P

      dP = dA + dB*Ps
      dP = dP.transpose('time','zaxis','lat','lon')
      dP.atts['units'] = 'Pa'
      data['dp'] = dP

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
    return glob(dirname+"/ohfield_mcfcal.nc")



# Add this interface to the table.
from . import table
table['tm5'] = TM5_Data

