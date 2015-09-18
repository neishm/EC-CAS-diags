# Interface for reading GEOS5 data in non-standard netcdf format.
# Sample file: /wrk6/chan/GEOS_CH4_data/OH_3Dglobal.geos5.4x5.nc

from pygeode.axis import ZAxis
class Altitude(ZAxis): pass

from . import DataProduct
class GEOS5_Weird_Format(DataProduct):

  field_list = (
    ('OH', 'OH', 'molecules cm-3'),
  )

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, dataset):
    import numpy as np
    from pygeode.axis import Hybrid
    from pygeode.var import Var
    from pygeode.dataset import asdataset

    # Generate the expected vertical axis
    if dataset.hasaxis('sigma'):
      alt = dataset.ALT.get()
      zaxis = Altitude(alt)
      dataset = list(dataset)
      for i, var in enumerate(dataset):
        if var.hasaxis('sigma'):
          dataset[i] = var.replace_axes(sigma=zaxis)
      dataset = asdataset(dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Grid cell areas
    # Pick some arbitrary (but deterministic) variable to get the lat/lon
    var = sorted(data.values())[0]
    from ..common import get_area
    data['cell_area'] = get_area(var.lat,var.lon)

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
table['geo5-weird-format'] = GEOS5_Weird_Format

