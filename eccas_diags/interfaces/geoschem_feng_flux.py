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


# Interface for reading / writing GEOS-CHEM data that is converted to netCDF
# from Feng Deng's scripts.


from . import DataProduct
class GEOSCHEM_Data(DataProduct):
  """
  GEOS-Chem flux data, converted to netCDF by Feng Deng (UofT).
  """

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('gpp', 'CO2_gpp_flux', 'molecules cm-2 s-1'),
    ('rsp', 'CO2_rsp_flux', 'molecules cm-2 s-1'),
    ('ff', 'CO2_fossil_flux', 'molecules cm-2 s-1'),
    ('ocn', 'CO2_ocean_flux', 'molecules cm-2 s-1'),
    ('bb', 'CO2_fire_flux', 'g m-2'),
    ('shp', 'CO2_fossil_flux', 'molecules cm-2 s-1'),
  )

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    from common import rotate_grid
    from pygeode.dataset import Dataset
    data = netcdf.open(filename)

    # Need to define the time axis
    # (not fully defined in the netcdf file).
    from re import search
    from datetime import datetime, timedelta
    from pygeode.timeaxis import StandardTime
    prefix = filename.split('/')[-1].split('.')[0]
    if prefix == 'bio':
      # Posterior fluxes have a year
      try:
        date = search("bio\.(?P<year>[0-9]{4})(?P<doy>[0-9]{3})\.geos\.4x5", filename).groupdict()
        date = datetime(year=int(date['year']), month=1, day=1) + timedelta(days=int(date['doy'])-1)
        date = dict(year=date.year, month=date.month, day=date.day)
        time = StandardTime(startdate=date, units='hours', values=range(0,24,3))
      # Prior fluxes don't have a year
      except AttributeError:
        date = search("bio\.(?P<doy>[0-9]{3})\.geos\.4x5", filename).groupdict()
        date = datetime(year=2009, month=1, day=1) + timedelta(days=int(date['doy'])-1)
        date = dict(year=date.year, month=date.month, day=date.day)
        time = StandardTime(startdate=date, units='hours', values=range(0,24,3))

    elif prefix == 'ff_ocn_bb':
      date = search("(?P<year>[0-9]{4})(?P<month>[0-9]{2})\.geos\.4x5", filename).groupdict()
      date = dict(year=int(date['year']), month=int(date['month']))
      time = StandardTime(startdate=date, units='hours', values=[0])
    elif prefix == 'ship':
      date = search("ship\.(?P<month>[0-9]{2})\.geos\.4x5\.nc", filename).groupdict()
      time = StandardTime(year=[2009], month=[int(date['month'])])
    else:
      time = data.time

    # Need the time axis to have a consistent start date
    time = StandardTime(startdate={'year':2009, 'month':1, 'day':1}, units='hours', **time.auxarrays)
    data = data.replace_axes(time=time)

    # Rotate the longitudes so they start at 0 (same as 3D COARDS fields).
    data = data.map(rotate_grid)


    # Rename 'latitude' axis to 'lat', for compatibility with 3D COARDS data.
    data = data.rename_axes(latitude='lat')

    # Hack for the grid cell areas - remove time axis.
    # Copied from geoschem-coards interface.
    data = list(data)
    for i, var in enumerate(data):
      if var.name.startswith('DXYP'):
        var = var.squeeze('time')
        data[i] = var

    return data

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls,dataset):
    import numpy as np
    from pygeode.dataset import asdataset

    # Apply fieldname conversions
    data = DataProduct.decode.__func__(cls,dataset)
    data = asdataset(data)

    # Detect climatologies (had to add a fake year in the file opener)
    if 'CO2_shipping_flux' in data:
      from pygeode.timeutils import modify
      data = data.replace_axes(time=modify(dataset.time, exclude='year'))

    # Compute total biospheric flux
    if 'CO2_gpp_flux' in data:
      bio = data.CO2_gpp_flux + data.CO2_rsp_flux
      bio.name = 'CO2_bio_flux'
      data += bio

    # Set specie name
    for var in data:
      if var.name.startswith('CO2'):
        var.atts['specie'] = 'CO2'

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in data)

    # Change units of biomass burning (from monthly total to rate)
    if 'CO2_fire_flux' in data:
      from calendar import monthrange
      from pygeode.var import Var
      bb = data['CO2_fire_flux']
      year = bb.time.year
      month = bb.time.month
      ndays = [monthrange(y,m)[1] for y,m in zip(year,month)]
      ndays = Var(axes=[bb.time], values=ndays)
      bb /= ndays
      bb /= 86400
      bb.atts['units'] = 'g m-2 s-1'
      bb.atts['specie'] = 'CO2'
      data['CO2_fire_flux'] = bb

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Add extra fields that will be useful for the diagnostics.
    data = cls._add_extra_fields(data)

    # Remove degenenerate vertical axis
    for i, var in enumerate(data):
      if var.hasaxis('level'):
        data[i] = var.squeeze('level')

    return data


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return glob(dirname+"/*.nc")


# Add this interface to the table.
from . import table
table['geoschem-feng-flux'] = GEOSCHEM_Data


