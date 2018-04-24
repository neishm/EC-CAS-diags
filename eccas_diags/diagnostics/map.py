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


# Code for handling map projections.

from . import Diagnostic
class Map(Diagnostic):
  @classmethod
  def add_args (cls, parser, handled=[]):
    super(Map,cls).add_args(parser)
    if len(handled) > 0: return  # Only run once
    group = parser.add_argument_group('options for map projections')
    group.add_argument('--region', choices=['global','north_america'], default='global', help="Which geographic region to plot the field.")
    handled.append(True)
  def __init__ (self, region, **kwargs):
    import numpy as np
    super(Map,self).__init__(**kwargs)
    self.plotvar_map_args = {}
    if region == 'north_america':
      self.plotvar_map_args = {
        'projection': {
          'width':9000000, 'height':7000000,
          'rsphere': (6378137.00,6356752.3142),
          'resolution': 'l', 'area_thresh': 1000., 'projection': 'lcc',
          'lat_1': 55.,'lat_2': 65, 'lat_0': 52, 'lon_0': -104.,
          'meridians': np.arange(10,360,30),
          'parallels': np.arange( 0, 80,20)
        },
      }
      end_suffix = self.end_suffix.split('_')
      end_suffix.append('NA')
      self.end_suffix = '_'.join(end_suffix)

