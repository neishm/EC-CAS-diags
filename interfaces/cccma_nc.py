
from . import DataProduct
class CCCMA_Data(DataProduct):

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('ndoh', 'OH', 'molecules m-3'),
    ('ps', 'surface_pressure', 'Pa'),
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
    from pygeode.ufunc import exp, log
    from pygeode.axis import Hybrid
    from pygeode.dataset import asdataset
    from pygeode.timeutils import modify

    dataset = asdataset(dataset)

    # Create a proper hybrid axis
    if 'lev' in dataset:
      new_zaxis = Hybrid(dataset.lev.values, A=dataset.ap.get(), B=dataset.b.get(), name='lev')
      dataset = dataset.replace_axes(lev=new_zaxis)
      have_zaxis = True
    else: have_zaxis = False

    # Is time axis a climatology?
    #TODO: update pygeode to automatically recognize a climatology axis
    if 'time' in dataset and 'climatology' in dataset.time.atts:
      new_taxis = modify(dataset.time, exclude='year')
      dataset = dataset.replace_axes(time=new_taxis)

    # Apply fieldname conversions
    dataset = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Compute a pressure field.
    if 'surface_pressure' in data and have_zaxis:
      Ps = data['surface_pressure']
      P = data['ap'] + data['b'] * Ps
      P = P.transpose('time','lev','lat','lon')
      P.atts['units'] = 'Pa'
      data['air_pressure'] = P

    # Remove variables with no lat/lon extent.
    # (they break things in the regridding routines)
    for varname, var in data.items():
      if not var.hasaxis('lat') or not var.hasaxis('lon'):
        del data[varname]

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
    return glob(dirname+"/*.nc")


# Add this interface to the table.
from . import table
table['cccma-nc'] = CCCMA_Data

