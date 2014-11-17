# Interface for CarbonTracker data

# Get the proper date for the given filename
# (since the date inside the file is wrong!)
def ct_file2date(filename):
  from re import search
  date = search("(?P<year>\d{4})-?(?P<month>\d{2})-?(?P<day>\d{2})\.nc$", filename).groupdict()
  date['year']  = int(date['year'])
  date['month'] = int(date['month'])
  date['day']   = int(date['day'])
  return date


from interfaces import ModelData
class CTCH4_Data(ModelData):

  # Invariant data
  import numpy as np
  A_interface = [0., 6.575628, 336.772369, 1297.656128, 3010.146973, 5422.802734, 8356.252930000001, 11543.166992, 14665.645508, 17385.595703, 19348.775391, 20319.011719, 20348.916016, 19919.796875, 19184.544922, 18191.029297, 16990.623047, 15638.053711, 14192.009766, 12713.897461, 11262.484375, 9873.560546999999, 8564.624023, 7341.469727, 6199.839355, 4663.776367, 3358.425781, 2292.155518, 1463.16394, 857.945801, 450.685791, 204.637451, 76.16765599999999, 21.413612, 0.]
  A_interface = np.array(A_interface)

  B_interface = [1., 0.994204, 0.9734660000000001, 0.935157, 0.875518, 0.795385, 0.698224, 0.589317, 0.475016, 0.362203, 0.259554, 0.176091, 0.112979, 0.080777, 0.055474, 0.036227, 0.022189, 0.012508, 0.006322, 0.002765, 0.001, 0.000279, 5.5e-05, 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
  B_interface = np.array(B_interface)

  del np

  # List of all possible fields we expect from the data
  # (original_name, standard_name, units)
  field_list = (
    ('bgrnd', 'CH4_background', 'ppb'),
    ('fossil', 'CH4_fossil', 'ppb'),
    ('agwaste', 'CH4_agwaste', 'ppb'),
    ('ocean', 'CH4_ocean', 'ppb'),
    ('bioburn', 'CH4_bioburn', 'ppb'),
    ('natural', 'CH4_natural', 'ppb'),
    ('pressure', 'air_pressure', 'hPa'),
  )


  # Helper methods

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    data = netcdf.open(filename)
    # The time axis in the file is wrong!
    # Override the year, month, and day
    filedate = ct_file2date(filename)
    year = [filedate['year']]*len(data.time)
    month = [filedate['month']]*len(data.time)
    day = [filedate['day']]*len(data.time)
    hour= data.time.hour
    minute = data.time.minute
    from pygeode.timeaxis import StandardTime
    taxis = StandardTime(startdate=data.time.startdate, year=year, month=month, day=day, hour=hour, minute=minute, units='days')
    data = data.replace_axes(time=taxis)
    return data

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  def decode (self, data):
    from pygeode.axis import ZAxis

    # Don't worry about non-CH4 variables.
    varnames = [v.name for v in data]
    if 'fossil' not in varnames: return data

    # Force vertical axis to be a ZAxis
    data = data.replace_axes(lev = ZAxis)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in data)

    # Do the conversions
    for old_name, new_name, units in self.field_list:
      if old_name in data:
        var = data.pop(old_name)
        var.atts['units'] = units
        data[new_name] = var

    # Find the total CH4 (sum of components)
    if 'CH4_background' in data:
      data['CH4'] = data['CH4_background'] + data['CH4_fossil'] + data['CH4_agwaste'] + data['CH4_ocean'] + data['CH4_bioburn'] + data['CH4_natural']
      data['CH4'].atts['units'] = data['CH4_background'].atts['units']


    # Add species name for all products (to assist in things like unit conversion)
    for varname in data:
      if varname.startswith('CH4'):
        data[varname].atts['specie'] = 'CH4'


    # Other (more heavily derived) products

    if 'air_pressure' in data:
      # Surface pressure
      # Get pressure at the bottom mid-level
      pmid = data['air_pressure'].squeeze(lev=1) * 100.

      # Compute surface pressure from this
      # p1 = A1 + B1*Ps
      # pmid = (ps + A1 + B1*Ps) / 2 = Ps(1+B1)/2 + (0+A1)/2
      # Ps = (2*pmid - A1)/(1+B1)
      P0 = (2*pmid - self.A_interface[1])/(self.B_interface[1]+1)
      P0.atts['units'] = 'Pa'
      data['surface_pressure'] = P0

      # Vertical change in pressure
      #NOTE: generated from A/B interface values, not the 3D pressure field.
      #      3D pressure is used only to define the vertical levels.
      import numpy as np
      from pygeode.var import Var
      dA = -np.diff(self.A_interface)
      dA = Var([data['air_pressure'].lev], values=dA)
      dB = -np.diff(self.B_interface)
      dB = Var([data['air_pressure'].lev], values=dB)
      dp = dA/ + dB * data['surface_pressure']
      dp = dp.transpose('time','zaxis','lat','lon')
      dp.atts['units'] = 'Pa'
      data['dp'] = dp


    # Compute grid cell area
    from common import get_area
    if 'CH4' in data:
      x = data['CH4'].squeeze(lev=1)
    else:
      raise Exception ("This should not happen")
    data['cell_area'] = get_area(x.lat, x.lon).extend(0,x.time)


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
    return glob(dirname+"/????????.nc")

# Instantiate this interface
interface = CTCH4_Data()

# Define the open method as a function, so it's picklable.
def open_file (filename):
  return interface.open_file(filename)




# Define the data interface for CarbonTracker

class CarbonTracker_CH4 (object):

  def __init__ (self, tmpdir=None):

    from cache import Cache
    from data_interface import DataInterface
    from glob import glob
    from pygeode.formats import netcdf

    # Higher-level information about the data
    self.name = 'CTCH42010'
    self.title = 'CarbonTracker'

    cachedir = '/wrk6/eltonc/ct_ch4/molefractions/nc_cache'
    fallback_dirs = [tmpdir] if tmpdir is not None else []
    self.cache = Cache (dir=cachedir, fallback_dirs=fallback_dirs, global_prefix=self.name+'_')

    molefractions = glob("/wrk6/eltonc/ct_ch4/molefractions/2009????.nc")

    manifest = self.cache.full_path("manifest", writeable=True)
    self.data = DataInterface.from_files (molefractions, opener=open_file, manifest=manifest)

    self.data = DataInterface(map(interface.decode,self.data))


