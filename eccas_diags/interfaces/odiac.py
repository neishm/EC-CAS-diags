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


# Interface for ODIAC data

from . import DataProduct
class ODIAC(DataProduct):
  """
  ODIAC CO2 data
  """

  # List of all possible fields we expect from the data
  # (original_name, standard_name, units)
  field_list = (
    ('land', 'CO2_bio_flux', 'g(C) m-2 day-1'),
    ('intl_bunker', 'CO2_intl_bunker_flux', 'g(C) m-2 day-1'),
  )
  # Helper methods

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats.netcdf import open
    from os.path import basename, splitext
    from pygeode.timeaxis import StandardTime
    f = open(filename)
    # Complete the time axis.
    # Use the year from the filename.
    year = splitext(basename(filename))[0].split('_')[-1]
    year = int(year)
    taxis = StandardTime(year=[year]*12, month=f.month, units='days')
    f = f.replace_axes(month=taxis)
    return f

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, data):

    # Apply fieldname conversions
    data = DataProduct.decode.__func__(cls,data)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in data)

    # Add species name for all products (to assist in things like unit conversion)
    for varname in data:
      if varname.startswith('CO2'):
        data[varname].atts['specie'] = 'CO2'

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
    molefractions = glob(dirname+"/odiac2017_1x1d_????.nc")

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    from os import path
    dirname = path.normpath(dirname)
    name = dirname.split('/')[i-2:]
    name = '_'.join(name)
    return name

# Add this interface to the table.
from . import table
table['odiac'] = ODIAC



