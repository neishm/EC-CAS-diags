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


from .gem import GEM_Data

class ECCAS_Data(GEM_Data):
  """
  EC-CAS model output for forward runs (no assimilation).
  For recent experiments, where tracers are defined w.r.t. dry air.
  """

  field_list = GEM_Data.field_list + (
    ('CO2', 'CO2', 'ug(C) kg(dry_air)-1'),
    ('CBB', 'CO2_fire', 'ug(C) kg(dry_air)-1'),
    ('CFF', 'CO2_fossil', 'ug(C) kg(dry_air)-1'),
    ('COC', 'CO2_ocean', 'ug(C) kg(dry_air)-1'),
    ('CLA', 'CO2_bio', 'ug(C) kg(dry_air)-1'),
    ('CO2B', 'CO2_background', 'ug(C) kg(dry_air)-1'),
    ('CH4', 'CH4', 'ug kg(dry_air)-1'),
    ('CH4B', 'CH4_background', 'ug kg(dry_air)-1'),
    ('CHFF', 'CH4_fossil', 'ug kg(dry_air)-1'),
    ('CHBB', 'CH4_fire', 'ug kg(dry_air)-1'),
    ('CHOC', 'CH4_ocean', 'ug kg(dry_air)-1'),
    ('CHNA', 'CH4_natural', 'ug kg(dry_air)-1'),
    ('CHAG', 'CH4_agriculture', 'ug kg(dry_air)-1'),
    ('TCO', 'CO', 'ug kg(dry_air)-1'),
    ('OH', 'OH', 'molecules m-3'),
    ('KTN', 'eddy_diffusivity', 'm2 s-1'),
    ('XCO2', 'XCO2', 'ug(C) kg(dry_air)-1'),
    ('XCH4', 'XCH4', 'ug kg(dry_air)-1'),
  )

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls,dataset):
    from ..common import conversion_factor
    from .gem import GEM_Data

    # Do generic GEM field decoding
    dataset = GEM_Data.decode.__func__(cls,dataset)

    for var in dataset:
      # Offset the ocean and land fields by 100ppm
      varname = var.name
      if varname == 'CO2_ocean':
        var -= conversion_factor('100 ppm', 'ug(C) kg(dry_air)-1', context='CO2')
      if varname == 'CO2_bio':
        var -= conversion_factor('100 ppm', 'ug(C) kg(dry_air)-1', context='CO2')
  
      # Add species name for all products (to assist in things like unit conversion)
      if varname.startswith('CO2'):
        var.atts['specie'] = 'CO2'
      elif varname.startswith('CH4'):
        var.atts['specie'] = 'CH4'
      elif varname.startswith('CO'):
        var.atts['specie'] = 'CO'

      # Fix any name clobbering from doing math on the fields.
      var.name = varname

    return dataset


  # Method to re-encode data into the source context
  # (e.g., rename fields to what would be originally in these kinds of files)
  @classmethod
  def encode (cls, dataset):
    from ..common import conversion_factor
    from .gem import GEM_Data
    # Call the generic GEM encoder to convert to the right units and field names
    dataset = GEM_Data.encode.__func__(cls,dataset)
    # Do some extra stuff to offset COC / CLA fields
    for i, var in enumerate(dataset):
      if var.name in ('COC','CLA'):
        dataset[i] = (var + conversion_factor('100 ppm', 'ug(C) kg(dry_air)-1', context='CO2')).as_type('float32')
    return dataset

  # For our forward cycles, we need to hard-code the ig1/ig2 of the tracers.
  # This is so we match the ip1/ip2 of the wind archive we're injecting
  # into the "analysis" files.
  @staticmethod
  def _fstd_tweak_records (records):
    import numpy as np

    # Select non-coordinate records (things that aren't already using IP2)
    ind = (records['ip2'] == 0)

    # First check for uniform latitudes
    lat = records['nomvar'] == '^^  '
    lat = records[lat]['data_func'][0]()
    dlat = np.diff(lat)
    if np.allclose(dlat,0.9):
      # Hard code the ig1 / ig2
      records['ig1'][ind] = 38992
      records['ig2'][ind] = 45710
      # Update the coordinate records to be consistent.
      records['ip1'][~ind] = 38992
      records['ip2'][~ind] = 45710

    # Otherwise, assume gaussian
    else:
      # Hard code the ig1 / ig2
      records['ig1'][ind] = 88320
      records['ig2'][ind] = 57863
      # Update the coordinate records to be consistent.
      records['ip1'][~ind] = 88320
      records['ip2'][~ind] = 57863

    # Just for completion, set the typvar and deet as well.
    records['typvar'][ind] = 'A'
    records['deet'][ind] = 0


# Add this interface to the table.
from . import table
table['eccas-dry'] = ECCAS_Data

