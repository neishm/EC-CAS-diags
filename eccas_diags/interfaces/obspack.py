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


# Interface for ObsPack data (surface and aircraft)

from . import SplitProduct
class ObsPack_Data(SplitProduct):

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
    # Skip non-stationary data.
    if data.atts['site_longitude'] == -1e34:
      return []
    # Attach a time axis
    time = StandardTime(values=data.time.get(), startdate = dict(year=1970,month=1,day=1), units='seconds')
    data = data.replace_axes(obs=time)
    # Attach a "station" axis to retain the lat/lon information.
    station = Station([data.atts['site_name']], station=[data.atts['site_name']], site_code=[data.atts['site_code']], lat=[data.atts['site_latitude']], lon=[data.atts['site_longitude']], country=[data.atts['site_country']])
    data = [v.extend(1, station) for v in data.vars]
    # Remove id and calendar variables.
    # Including them causes the data scanner to produce multiple versions of
    # the datasets (with/without these string/calendar dimensions).
    data = [v for v in data if v.naxes == 2]
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
  @classmethod
  def find_files (cls, dirname):
    from glob import glob
    from os.path import exists
    if exists(dirname+'/data'): dirname += '/data'
    if exists(dirname+'/nc'): dirname += '/nc'
    return sorted(glob(dirname+'/*'+cls.obstype+'*.nc'))

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @classmethod
  def get_dataname (cls, dirname):
    import os
    dirs = dirname.split(os.sep)
    while dirs[-1] in ('nc','data'): dirs = dirs[:-1]
    return dirs[-1]+'-'+cls.obstype


class ObsPack_Aircraft_Data(ObsPack_Data):
  """
  Aircraft measurements of tracers from the ObsPack dataset.
  http://www.esrl.noaa.gov/gmd/ccgg/obspack/
  """
  obstype = 'aircraft-pfp'

class ObsPack_Surface_Data(ObsPack_Data):
  """
  Station-based (continuous) measurements of tracers from the ObsPack dataset.
  http://www.esrl.noaa.gov/gmd/ccgg/obspack/
  """
  obstype = 'surface-insitu'

class ObsPack_Flask_Data(ObsPack_Data):
  """
  Station-based (flask) measurements of tracers from the ObsPack dataset.
  http://www.esrl.noaa.gov/gmd/ccgg/obspack/
  """
  obstype = 'surface-flask'

class ObsPack_Tower_Data(ObsPack_Data):
  """
  Tower measurements of tracers from the ObsPack dataset.
  http://www.esrl.noaa.gov/gmd/ccgg/obspack/
  """
  obstype = 'tower-insitu'

# Add this interface to the table.
from . import table
table['obspack-aircraft'] = ObsPack_Aircraft_Data
table['obspack-hourly'] = ObsPack_Surface_Data
table['obspack-flask'] = ObsPack_Flask_Data
table['obspack-tower'] = ObsPack_Tower_Data
