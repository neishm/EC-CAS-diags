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
    # From original files
    #   geoschem-emissions-djf1415.nc
    #   geoschem_biogenic_prod_and_pressures.nc
    ('pressure', 'pressure_edges', 'hPa'),
    ('co_emiss', 'CO_nonbio_flux', 'molecules(CO) cm-2 s-1'),
    ('CO_ISO', 'CO_isoprene_flux', 'molecules(CO) cm-2 s-1'),
    ('CO_MET', 'CO_methanol_flux', 'molecules(CO) cm-2 s-1'),
    ('CO_MONO', 'CO_monoterpene_flux', 'molecules(CO) cm-2 s-1'),
    ('CO_ACET', 'CO_acetone_flux', 'molecules(CO) cm-2 s-1'),
    ('surf_area', 'cell_area', 'm2'),
    ('co_init', 'CO', 'mol mol(semidry_air)-1'),
    # From updated file
    # geoschem-monthly-mean-emissions-2015.nc
    ('p_center', 'pressure_edges', 'hPa'),
    #('co_init', 'CO', 'mol mol(semidry_air)-1'),
    #('surf_area', 'cell_area', 'm2'),
    ('an_emiss', 'CO_anthro_flux', 'molecules(CO) cm-2 s-1'),
    ('bb_emiss', 'CO_biomass_flux', 'molecules(CO) cm-2 s-1'),
    ('bf_emiss', 'CO_biofuel_flux', 'molecules(CO) cm-2 s-1'),
    ('isoprenes', 'CO_isoprene_flux', 'molecules(CO) cm-2 s-1'),
    ('methanols', 'CO_methanol_flux', 'molecules(CO) cm-2 s-1'),
    ('monos', 'CO_monoterpene_flux', 'molecules(CO) cm-2 s-1'),
    ('acetones', 'CO_acetone_flux', 'molecules(CO) cm-2 s-1'),
  )


  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    from pygeode.axis import ZAxis, Height, TAxis
    data = netcdf.open(filename)
    # Annotate some of the axes with specific types, to help the data_scanner
    # figure things out.  Otherwise, get weird crashes.
    data = data.replace_axes(date_time=TAxis, ground_level=Height, level=ZAxis, level_centers=ZAxis, level_edges=ZAxis)
    # Use consistent name for level_centers across the files.
    data = data.rename_axes(level='level_centers')
    return data

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls,dataset):
    import numpy as np
    from pygeode.axis import Hybrid, Lat, Lon
    from pygeode.timeaxis import StandardTime
    from .geoschem_feng_nc import GEOSCHEM_Data as GC
    from ..common import compute_pressure

    # Hard-code the hybrid levels (needed for doing zonal mean plots on native
    # model coordinates).
    A_interface = np.array(GC.A_interface)
    B_interface = np.array(GC.B_interface)
    A = (A_interface[:-1] + A_interface[1:])/2
    B = (B_interface[:-1] + B_interface[1:])/2
    # Note: for compute_pressure need hybrid A and B w.r.t. Pascals, not hPa.
    level = Hybrid(GC.eta, A=A*100, B=B, name='level_centers')
    # Need to make the z-axis the right type (since there's no metadata hints
    # in the file to indicate the type)
    dataset = dataset.replace_axes(level_centers=level)
    if 'level_centers' in dataset:
      zaxis = dataset.level_centers
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
      dataset = dataset.replace_axes(date_dim=time, datetime=time)

    # Remove "ground-level" dimension.
    dataset = dataset.squeeze()

    # Apply fieldname conversions
    data = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Collect non-bio fields together?
    if all('CO_'+n+'_flux' in data for n in ('anthro','biomass','biofuel')):
      data['CO_nonbio_flux'] = data['CO_anthro_flux'] + data['CO_biomass_flux'] + data['CO_biofuel_flux']

    # Generate a total CO flux (including biogenic components)
    if all('CO_'+n+'_flux' in data for n in ('nonbio','methanol','acetone','isoprene','monoterpene')):
      data['CO_flux'] = data['CO_nonbio_flux'] + data['CO_methanol_flux'] + data['CO_acetone_flux'] + data['CO_isoprene_flux'] + data['CO_monoterpene_flux']

    # Generate a surface pressure field.
    # NOTE: pressure is actually the pressure at the interfaces (from surface onward).
    if 'pressure_edges' in data:
      data['surface_pressure'] = data['pressure_edges'](i_level_centers=0).squeeze('level_centers')
      # Re-compute pressure at the centers.
      # The levels encoded for pressure_edges are actually the centers.
      data['air_pressure'] = compute_pressure(data['pressure_edges'].level_centers,data['surface_pressure'])

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
    return glob(dirname+"/geoschem-emissions-djf1415.nc") + glob(dirname+"/geoschem_biogenic_prod_and_pressures.nc") + glob(dirname+"/geoschem-monthly-mean-emissions-2015_fixed-area.nc")


# Add this interface to the table.
from . import table
table['geoschem-tailong-nc'] = GEOSCHEM_Data


