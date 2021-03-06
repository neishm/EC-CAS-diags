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


# Interface for reading GEOS5 data in non-standard netcdf format.
# Sample file: /wrk6/chan/GEOS_CH4_data/OH_3Dglobal.geos5.4x5.nc

from pygeode.axis import ZAxis
class Altitude(ZAxis): pass

from . import DataProduct
class GEOS5_Weird_Format(DataProduct):
  """
  A strange format encountered with some GEOS5 data.  It's in netCDF, but the
  axes are non-standard.  For instance, the time axis is 'tau0', which either
  represents the month number, or the number of hours since Jan 1, 1985.
  """

  field_list = (
    ('OH', 'OH', 'molecules cm-3'),
  )

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    from pygeode.axis import NamedAxis
    data = netcdf.open(filename)
    # If we have year information for OH climatology, then store it for future reference.
    if 'UCX-OH-' in filename:
      from pygeode.var import Var
      year = filename.split('_')[-1][:-3]
      year = Var(axes=[data.tau0], values=[int(year)]*12,name='year')
      data = data + year
    # Convert sigma coordinate from NCDim to NamedAxis to make it comparable.
    if 'sigma' in data:
      data = data.replace_axes(sigma=NamedAxis)
    return data

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, dataset):
    import numpy as np
    from pygeode.axis import Hybrid
    from pygeode.timeaxis import StandardTime
    from pygeode.var import Var
    from pygeode.dataset import asdataset
    from .geoschem_coards import GEOSCHEM_Data

    # Extract coordinate variables
    tau0 = getattr(dataset,'tau0',None)
    lon = getattr(dataset,'LON',None)
    lat = getattr(dataset,'LAT',None)
    alt = getattr(dataset,'ALT',None)
    sigma = getattr(dataset,'sigma',None)

    # Get the interface A and B values.
    A_m = np.array(GEOSCHEM_Data.A_interface[72])
    B_m = np.array(GEOSCHEM_Data.B_interface[72])
    A = (A_m[:-1] + A_m[1:]) * 0.5
    B = (B_m[:-1] + B_m[1:]) * 0.5
    dA = (A_m[:-1] - A_m[1:])
    dB = (B_m[:-1] - B_m[1:])

    # Generate the expected vertical axis
    if sigma is not None:
      # Special case - 59-level OH input
      if len(sigma) == 59:
        A = A[:59]
        B = B[:59]
        dA = dA[:59]
        dB = dB[:59]
      zaxis = Hybrid(values=(A+B*1000)/1000, A=A, B=B)
      A = Var(name='A', axes=[zaxis], values=A)
      B = Var(name='B', axes=[zaxis], values=B)
      dA = Var(name='dA', axes=[zaxis], values=dA)
      dB = Var(name='dB', axes=[zaxis], values=dB)

    # Generate the expected time axis
    if tau0 is not None:
      if len(tau0) == 12:
        if 'year' in dataset:
          taxis = StandardTime(year=dataset.year[:], month=tau0.values)
        else:
          taxis = StandardTime(month=tau0.values)
      elif len(tau0) == 576:
        taxis = StandardTime(tau0.values, units='hours', startdate=dict(year=1985,month=1,day=1))

    dataset = list(dataset)

    # Generate the expected vertical axis and time axis.
    # Also, transpose the axes into the expected order.
    for i, var in enumerate(dataset):
      if var.hasaxis('sigma'):
        var = var.replace_axes(sigma=zaxis)
      if var.hasaxis('tau0'):
        var = var.replace_axes(tau0=taxis)
      if var.hasaxis('time') and var.hasaxis('zaxis'):
        var = var.transpose('time','zaxis','lat','lon')
      dataset[i] = var

    # Apply fieldname conversions
    dataset = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Fake pressure field
    # (we don't have a real surface pressure?)
    if sigma is not None and tau0 is not None and lat is not None:
      P = (taxis*zaxis*lat*lon)*0 + A + B * 1000
      P.atts['units'] = 'hPa'
      data['air_pressure'] = P
#      print 'P ??', P[0,:,0,0]

      dP = (taxis*zaxis*lat*lon)*0 + dA + dB * 1000
      dP.atts['units'] = 'hPa'
      data['dp'] = dP
#      print 'dP ??', dP[0,:,0,0]

    if lat is not None and lon is not None:
      Ps = (taxis*lat*lon)*0 + 1000
      Ps.atts['units'] = 'hPa'
      data['surface_pressure'] = Ps
#      print 'mean Ps ??', Ps.mean()

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
    return glob(dirname+"/*.nc")  # Match any netcdf files in this directory.

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    import os
    dirs = dirname.split(os.sep)
    return dirs[-1]


# Add this interface to the table.
from . import table
table['geos5-weird-format'] = GEOS5_Weird_Format

