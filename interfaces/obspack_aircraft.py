# Interface for ObsPack aircraft data

from . import SplitProduct
class ObsPack_Aircraft_Data(SplitProduct):

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('value',    'CO2',      'mol mol(dry_air)-1'),
    ('altitude', 'altitude', 'm'),
  )

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    from pygeode.timeaxis import StandardTime
    from ..station_data import Station
    # Open the file
    data = netcdf.open(filename)
    # Attach a time axis
    time = StandardTime(values=data.time.get(), startdate = dict(year=1970,month=1,day=1), units='seconds')
    data = data.replace_axes(obs=time)
    # Attach a "station" axis to retain the lat/lon information.
    station = Station([data.atts['site_name']], site_code=[data.atts['site_code']], lat=[data.atts['site_latitude']], lon=[data.atts['site_longitude']], country=[data.atts['site_country']])
    data = [v.extend(1, station) for v in data.vars]
    return data

  # Decoding of the fields.
  @classmethod
  def decode (cls,dataset):
    from . import SplitProduct
    # Do generic decoding first
    dataset = SplitProduct.decode.__func__(cls,dataset)
    # Remove time variable, since we've wrapped it into a time axis.
    dataset = [v for v in dataset if v.name != 'time']
    return dataset

  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    from os.path import exists
    if exists(dirname+'/data'): dirname += '/data'
    if exists(dirname+'/nc'): dirname += '/nc'
    return glob(dirname+'/*aircraft-pfp*.nc')

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    import os
    dirs = dirname.split(os.sep)
    while dirs[-1] in ('nc','data'): dirs = dirs[:-1]
    return dirs[-1]


# Add this interface to the table.
from . import table
table['obspack-aircraft'] = ObsPack_Aircraft_Data

