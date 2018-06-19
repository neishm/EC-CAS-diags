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
    ('total_flux_opt','CH4_flux',         'Tg(CH4) year-1'),
    ('tempm', 'air_temperature', 'K'),
    ('presm', 'surface_pressure', 'Pa'),
    ('ch4', 'CH4', 'mol mol(semidry_air)-1'),
  )
  # Helper methods

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf as nc, hdf4
    from os.path import basename, splitext
    from pygeode.timeaxis import StandardTime
    from pygeode.axis import Lat, Lon, ZAxis
    from pygeode.var import Var
    import numpy as np
    # Case 1: netCDF flux file
    if filename.endswith('.nc'):
      f = nc.open(filename)
      # Use the date from the filename.
      yyyymm = splitext(basename(filename))[0].split('_')[-2]
      year = int(yyyymm[:4])
      month = int(yyyymm[4:])
      taxis = StandardTime(year=[year], month=[month], units='days', startdate=dict(year=2000,month=1))
      # Create the time axis.
      f = f.extend(0,taxis)
    # Case 2: HDF4 concentration file
    elif filename.endswith('.hdf'):
      f = hdf4.open(filename)
      # Use the date from the filename.
      yyyymmddhh = splitext(basename(filename))[0].split('_')[-2]
      year = int(yyyymmddhh[:4])
      month = int(yyyymmddhh[4:6])
      day = int(yyyymmddhh[6:8])
      hour = int(yyyymmddhh[8:])
      taxis = StandardTime(year=[year], month=[month], day=[day], hour=[hour], units='days', startdate=dict(year=2000,month=1))
      # Create the time axis.
      f = f.extend(0,taxis)
      # Store the hybrid a/b information for later use.
      at = f.atts['at']
      a = (at[:-1] + at[1:]) / 2
      a = Var(axes=[f.HYBRID], name='a', values=a)
      bt = f.atts['bt']
      b = (bt[:-1] + bt[1:]) / 2
      b = Var(axes=[f.HYBRID], name='b', values=b)
      f = f + a + b
      # Partial decoding of zaxis.
      # Can't create a full Hybrid axis here, because the diagnostic machinery
      # gets confused about the extra A/B auxiliary array.
      f = f.replace_axes(HYBRID=ZAxis)
      # Attach lat/lon  coordinates (for concentration files.)
      # Have to do it here in the opener, because the data_scanner can't handle
      # the default "dummy" lat/lon axes in the file.
      latbounds = np.linspace(-90,90,46)
      lat = (latbounds[:-1] + latbounds[1:]) / 2
      lat = Lat(lat)
      lonbounds = np.linspace(-180,180,61)
      lon = (lonbounds[:-1] + lonbounds[1:]) / 2
      lon = Lon(lon)
      f = f.replace_axes(LATglb600x400=lat, LONglb600x400=lon)
    return f

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, data):

    from ..common import ndays_in_year, compute_pressure
    from pygeode.axis import Hybrid

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
          data[varname].atts['specie'] = 'CH4'
      # Add default units to unprocessed data
      else:
        data[varname].atts['units'] = ''

    # Finish defining level coordinates (for concentration files.)
    hybrid = None
    for varname in data:
      if data[varname].hasaxis('HYBRID'):
        if hybrid is None:
          hybrid = Hybrid(data[varname].HYBRID.values, name='hybrid', A=data['a'].get(), B=data['b'].get())
        data[varname] = data[varname].replace_axes(HYBRID=hybrid)
    # Remove a,b variables.
    data.pop('a',None)
    data.pop('b',None)

    # Add pressure field (if not explicitly provided).
    if 'surface_pressure' in data and hybrid is not None:
      #try:
        air_pressure = compute_pressure(hybrid, data['surface_pressure'])
        air_pressure.name = 'air_pressure'
        data['air_pressure'] = air_pressure
      #except (TypeError, ValueError, AttributeError): pass


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
    return glob(dirname+"/monthly_CH4_??????_1x1.nc") + glob(dirname+"mmix_??????????_??????????_glb600x400.hdf")

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    # No versioning information in directory name, just use interface name.
    return 'CTDAS-CH4'

# Add this interface to the table.
from . import table
table['ctdas-ch4'] = CTDAS



