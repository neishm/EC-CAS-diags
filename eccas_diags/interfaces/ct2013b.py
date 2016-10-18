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


# Interface for CT2013B molefraction data.
# Pretty much the same thing, except some preprocessing for
# pressure at the boundaries to get dp.

from .carbontracker import CT_Data
class CT2013B_Data(CT_Data):
  """
  CarbonTracker CO2 products (molefractions, fluxes) from CT2013B and later.
  """

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats.netcdf import open
    import warnings
    # Ignore warnings about the vertical axis.
    # PyGeode complains because it sees a hybrid axis, but doesn't find
    # A and B coefficients to properly define it.
    with warnings.catch_warnings():
      warnings.filterwarnings("ignore", "Cannot create a proper Hybrid vertical axis")
      data = open(filename)
    # Add a dp and surface pressure product, based on the pressure interfaces.
    #NOTE: this modifies what the data_scanner sees when opening the file, so
    # the manifest will expect to have access to these fields.  If things
    # are added/removed in the lines below, the manifest(s) will have to be
    # manually deleted so they can be reconstructed with the new fields.
    if 'pressure' in data:
      p = data['pressure']
      p0 = p.slice[:,0,:,:].squeeze('boundary')
      p0.name = 'surface_pressure'
      p0.atts['units'] = 'Pa'
      p_p = p.slice[:,:-1,:,:].replace_axes(boundary=data.level)
      p_m = p.slice[:,1:,:,:].replace_axes(boundary=data.level)
      dp = p_p - p_m
      dp.name = 'dp'
      dp.atts['units'] = 'Pa'
      # Pressure interpolated to mid-levels
      p_level = (p_p+p_m)/2
      p_level.name = 'air_pressure'
      p_level.atts['units'] = 'Pa'
      # Put in new fields
      data = data + p_level + p0 + dp
    # Same thing with geopotential height (defined on the boundaries, so
    # compute mid-level values).
    if 'gph' in data:
      gph = data['gph']
      gph_p = gph.slice[:,:-1,:,:].replace_axes(boundary=data.level)
      gph_m = gph.slice[:,1:,:,:].replace_axes(boundary=data.level)
      gph_level = (gph_p+gph_m)/2
      gph_level.name = 'geopotential_height'
      gph_level.atts['units'] = 'm'
      data = data + gph_level

    return data


# Add this interface to the table.
from . import table
table['ct2013b'] = CT2013B_Data



