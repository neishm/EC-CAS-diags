# Interface for reading GEOS5 data in non-standard netcdf format.
# Sample file: /wrk6/chan/GEOS_CH4_data/OH_3Dglobal.geos5.4x5.nc

from pygeode.axis import ZAxis
class Altitude(ZAxis): pass

from . import DataProduct
class GEOS5_Weird_Format(DataProduct):

  field_list = (
    ('OH', 'OH', 'molecules cm-3'),
  )

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    return netcdf.open(filename)

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
    # Un-reverse them, because our z axis wasn't flipped in the data scanner.
    # (see 6031704f0cfcad7c355a7eb5003ad5ca6fc53df0)
    A_m = np.array(GEOSCHEM_Data.A_interface[72][::-1])
    B_m = np.array(GEOSCHEM_Data.B_interface[72][::-1])
    A = (A_m[:-1] + A_m[1:]) * 0.5
    B = (B_m[:-1] + B_m[1:]) * 0.5
    dA = abs(A_m[:-1] - A_m[1:])
    dB = abs(B_m[:-1] - B_m[1:])

    # Generate the expected vertical axis
    if sigma is not None:
      zaxis = Hybrid(values=B, A=A, B=B)
      A = Var(name='A', axes=[zaxis], values=A)
      B = Var(name='B', axes=[zaxis], values=B)
      dA = Var(name='dA', axes=[zaxis], values=dA)
      dB = Var(name='dB', axes=[zaxis], values=dB)

    # Generate the expected time axis
    if tau0 is not None:
      taxis = StandardTime(month=tau0.values)

    dataset = list(dataset)

    # Generate the expected vertical axis
    for i, var in enumerate(dataset):
      if var.hasaxis('sigma'):
        var = var.replace_axes(sigma=zaxis)
      if var.hasaxis('tau0'):
        var = var.replace_axes(tau0=taxis)
      dataset[i] = var

    dataset = asdataset(dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Grid cell areas
    # Pick some arbitrary (but deterministic) variable to get the lat/lon
    if lat is not None and lon is not None:
      from ..common import get_area
      data['cell_area'] = get_area(lat,lon)

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Convert to a list
    data = list(data.values())

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

