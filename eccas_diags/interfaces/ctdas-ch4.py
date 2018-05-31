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


# Interface for CTDAS-CH4 data

from . import DataProduct
class CTDAS(DataProduct):
  """
  CTDAS CH4 data
  """

  # List of all possible fields we expect from the data
  # (original_name, standard_name, units)
  field_list = (
    ('bio_flux_opt',  'CH4_natural_flux', 'Tg(CH4) year-1'),
    ('anth_flux_opt', 'CH4_fossil_flux',  'Tg(CH4) year-1'),
    ('fire_flux_imp', 'CH4_bioburn_flux', 'Tg(CH4) year-1'),
    ('term_flux_imp', 'CH4_agwaste_flux', 'Tg(CH4) year-1'),
    ('ocn_flux_imp',  'CH4_ocean_flux',   'Tg(CH4) year-1'),
  )
  # Helper methods

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats.netcdf import open
    from os.path import basename, splitext
    from pygeode.timeaxis import StandardTime
    f = open(filename)
    # Create the time axis.
    # Use the year/month from the filename.
    yyyymm = splitext(basename(filename))[0].split('_')[-2]
    year = int(yyyymm[:4])
    month = int(yyyymm[4:])
    taxis = StandardTime(year=[year], month=[month], units='days', startdate=dict(year=2000,month=1))
    f = f.extend(0,taxis)
    return f

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, data):

    from ..common import ndays_in_year

    # Apply fieldname conversions
    data = DataProduct.decode.__func__(cls,data)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in data)

    # Add species name for all products (to assist in things like unit conversion)
    for varname in data:
      if varname.startswith('CH4'):
        data[varname].atts['specie'] = 'CH4'
      # Convert units from mass/year to mass/day
      if 'units' in data[varname].atts:
        if data[varname].atts['units'] == 'Tg(CH4) year-1':
          data[varname] = data[varname] / ndays_in_year(data[varname].time)
          data[varname].atts['units'] = 'Tg(CH4) day-1'
      # Add default units to unprocessed data
      else:
        data[varname].atts['units'] = ''

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
    return glob(dirname+"/monthly_CH4_??????_1x1.nc")

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    from os import path
    dirname = path.normpath(dirname)
    name = dirname.split('/')[-2:]
    name = '_'.join(name)
    return name

# Add this interface to the table.
from . import table
table['ctdas-ch4'] = CTDAS



