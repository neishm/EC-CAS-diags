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
# from Tailong He.


from . import DataProduct
class GEOSCHEM_Data(DataProduct):
  """
  GEOS-Chem tracer data, converted to netCDF by Tailong He (UofT).
  """

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('pressure', 'air_pressure', 'hPa'),
    ('co_emiss', 'CO_nonbio_flux', 'mol(CO) cm-2 s-1'),
    ('CO_ISO', 'CO_isoprene_flux', 'mol(CO) cm-2 s-1'),
    ('CO_MET', 'CO_methanol_flux', 'mol(CO) cm-2 s-1'),
    ('CO_MONO', 'CO_monoterpene_flux', 'mol(CO) cm-2 s-1'),
    ('CO_ACET', 'CO_acetone_flux', 'mol(CO) cm-2 s-1'),
    ('surf_area', 'cell_area', 'm2'),
    ('co_init', 'CO', 'mol mol(semidry_air)-1'),
  )


  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    data = netcdf.open(filename)
    return data
    #TODO
    # Need to define the time axis
    # (not fully defined in the netcdf file).
    if 'time' not in data or 'units' not in data.time.auxatts:
      from re import search
      date = search("(?P<year>[0-9]{4})(?P<month>[0-9]{2})(?P<day>[0-9]{2})\.nc", filename).groupdict()
      date = dict([x,int(y)] for x,y in date.iteritems())
      from pygeode.timeaxis import StandardTime
      time = StandardTime(startdate=date, units='hours', values=range(24))
      # Need the time axis to have a consistent start date
      time = StandardTime(startdate={'year':2009, 'month':1, 'day':1}, units='hours', **time.auxarrays)
      data = data.replace_axes(time=time)

    return data

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls,dataset):
    import numpy as np
    from pygeode.axis import Hybrid, Lat, Lon
    from pygeode.timeaxis import StandardTime
    from .geoschem_feng_nc import GEOSCHEM_Data as GC

    # Hard-code the hybrid levels (needed for doing zonal mean plots on native
    # model coordinates).
    A_interface = np.array(GC.A_interface)
    B_interface = np.array(GC.B_interface)
    A = (A_interface[:-1] + A_interface[1:])/2
    B = (B_interface[:-1] + B_interface[1:])/2
    level = Hybrid(GC.eta, A=A, B=B, name='level')
    # Need to make the z-axis the right type (since there's no metadata hints
    # in the file to indicate the type)
    dataset = dataset.replace_axes(level_centers=level)
    if 'level' in dataset:
      zaxis = dataset.level
    else: zaxis = None

    if zaxis is not None:
      zaxis.atts['positive'] = 'up'

    # Identify lat/lon axes
    dataset = dataset.replace_axes(lat=Lat, lon=Lon)

    # Fix time axis
    # Dates are stored as floating-poing numbers?
    if 'date_info' in dataset:
      times = dataset.date_info.get().flatten()
      # Convert to integers.
      times = np.array(times, dtype='int32')
      # Set to first of the month.
      times += 1
      # Create time axis.
      year = times//10000
      month = (times//100)%100
      day = times%100
      time = StandardTime(year=year,month=month,day=day,units='days',startdate=dict(year=2014,month=1,day=1))
      dataset = dataset.replace_axes(date_dim=time)

    # Remove "ground-level" dimension.
    dataset = dataset.squeeze()

    # Apply fieldname conversions
    data = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Generate a total CO flux (including biogenic components)
    if all('CO_'+n+'_flux' in data for n in ('nonbio','methanol','acetone','isoprene','monoterpene')):
      data['CO_flux'] = data['CO_nonbio_flux'] + data['CO_methanol_flux'] + data['CO_acetone_flux'] + data['CO_isoprene_flux'] + data['CO_monoterpene_flux']

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
    return glob(dirname+"/geoschem-emissions-djf1415.nc") + glob(dirname+"/geoschem_biogenic_prod_and_pressures.nc")


# Add this interface to the table.
from . import table
table['geoschem-tailong-nc'] = GEOSCHEM_Data


