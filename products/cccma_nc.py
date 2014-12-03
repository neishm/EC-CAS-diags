
class CCCMA_Data(object):

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
  def decode (self, dataset):
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
    if 'time' in dataset and 'climatology' in dataset.time:
      new_taxis = modify(dataset.time, exclude='year')
      dataset = dataset.replace_axes(time=new_taxis)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Do the conversions
    for old_name, new_name, units in self.field_list:
      if old_name in data:
        var = data.pop(old_name)
        var.atts['units'] = units
        data[new_name] = var

    # Compute a pressure field.
    if 'surface_pressure' in data and have_zaxis:
      Ps = data['surface_pressure']
      P = data['ap'] + data['b'] * Ps
      P = P.transpose('time','lev','lat','lon')
      P.atts['units'] = 'Pa'
      data['air_pressure'] = P

    # Grid cell areas
    from common import get_area
    if 'surface_pressure' in data:
      Ps = data['surface_pressure']
      data['cell_area'] = get_area(Ps.lat,Ps.lon)

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
    return glob(dirname+"/*.nc")





# Instantiate this interface
interface = CCCMA_Data()

# Define the open method as a function, so it's picklable.
def open_file (filename):
  return interface.open_file(filename)

