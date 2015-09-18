
from . import DataProduct
class TM5_Data(DataProduct):

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
    return netcdf.open(filename)


  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, dataset):
    from pygeode.axis import Hybrid
    from pygeode.ufunc import exp
    from pygeode.var import Var
    import numpy as np

    A_interface = dataset.A.get()
    B_interface = dataset.B.get()
    A = (A_interface[1:] + A_interface[:-1]) * 0.5
    B = (B_interface[1:] + B_interface[:-1]) * 0.5
    dA = (A_interface[1:] - A_interface[:-1])
    dB = (B_interface[1:] - B_interface[:-1])

    #TODO

    # Locate a z-axis
    dataset = list(dataset)
    zaxis = None
    for var in dataset:
      if var.hasaxis('LEVEL'):
        zaxis = var.getaxis('LEVEL')

    # Create a proper z-axis
    if zaxis is not None:
      zaxis = Hybrid(zaxis.values, A=A, B=B)
      for i, var in enumerate(dataset):
        if var.hasaxis('LEVEL'):
          dataset[i] = var.replace_axes(LEVEL=zaxis)

    # Apply fieldname conversions
    dataset = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Add pressure info
    if 'surface_pressure' in data and zaxis is not None:
      Ps = data['surface_pressure']
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


    # Grid cell areas
    # Pick some arbitrary (but deterministic) variable to get the lat/lon
    var = (v for v in sorted(data.values()) if v.hasaxis('lat') and v.hasaxis('lon')).next()
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
    return glob(dirname+"/ohfield_mcfcal.nc")



# Add this interface to the table.
from . import table
table['tm5'] = TM5_Data

