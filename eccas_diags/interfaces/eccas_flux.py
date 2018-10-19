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


from .eccas_dry import ECCAS_Data

class ECCAS_Flux_Data(ECCAS_Data):
  """
  Flux input files for EC-CAS experiments (RPN format).
  """

  field_list = (
    ('ECO2', 'CO2_flux', 'g(C) s-1'),
    ('ECBB', 'CO2_fire_flux', 'g(C) s-1'),
    ('ECFF', 'CO2_fossil_flux', 'g(C) s-1'),
    ('ECOC', 'CO2_ocean_flux', 'g(C) s-1'),
    ('ECLA', 'CO2_bio_flux', 'g(C) s-1'),
    ('ECIB', 'CO2_intl_bunker_flux', 'g(C) s-1'),
    ('ECH4', 'CH4_flux', 'g(CH4) s-1'),
    ('ECHF', 'CH4_fossil_flux', 'g(CH4) s-1'),
    ('ECHB', 'CH4_bioburn_flux', 'g(CH4) s-1'),
    ('ECHO', 'CH4_ocean_flux', 'g(CH4) s-1'),
    ('ECNA', 'CH4_natural_flux', 'g(CH4) s-1'),
    ('ECAG', 'CH4_agwaste_flux', 'g(CH4) s-1'),
    ('ECO', 'CO_flux', 'g(CO) s-1'),
    ('ECAN', 'CO2_Canada_flux', 'g(C) s-1'),
    ('ENOC', 'CO2_no_Canada_flux', 'g(C) s-1'),
    ('ECPF', 'CO2_permafrost_flux', 'g(C) s-1'),
  )


  # Method to open a single file
  # Override gem.open_file to "squash" the forecast axis, because we may have
  # arbitrary combinations of origin dates and forecast hours which don't form
  # complete axes.  Without squashing, the fstd.open call could fail.
  @staticmethod
  def open_file (filename):
    from pygeode.formats import fstd
    return fstd.open(filename, raw_list=True, squash_forecasts=True)

  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return glob(dirname+"/area_??????????")

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    # Modify name so that it's clear this is the data on the EC-CAS grid,
    # not the original data.
    name = super(ECCAS_Flux_Data,ECCAS_Flux_Data).get_dataname(dirname)
    return name + '_eccas-grid'

  # Extra step to convert fluxes from mass / m2 / s to mass / g.
  @classmethod
  def encode (cls, dataset):
    from ..common import can_convert, convert, get_area
    from pygeode.var import copy_meta
    import logging
    logger = logging.getLogger(__name__)

    dataset = list(dataset)

    # Check the flux units, and optionally scale by grid area.
    area = None
    for var in dataset:
      if var.name == 'cell_area': area = var
    if area is None:
      dummy = None
      for var in dataset:
        if var.hasaxis('lat') and var.hasaxis('lon'):
          dummy = var
      if dummy is not None:
        area = get_area(dummy.lat, dummy.lon, flat=True)
    if area is None:
      logger.debug("Dropping dataset with no lat/lon information.")
      return []

    for i, var in enumerate(dataset):
      if can_convert(var,'g m-2 s-1'):
        orig = var
        var *= area
        copy_meta(orig,var)
        var.atts['units'] += area.atts['units']
        dataset[i] = var

    # Create total flux products
    dataset = dict((var.name,var) for var in dataset)
    if 'CH4_flux' not in dataset:
      try:
        dataset['CH4_flux'] = dataset['CH4_agwaste_flux'] + dataset['CH4_bioburn_flux'] + dataset['CH4_fossil_flux'] + dataset['CH4_natural_flux']
      except KeyError: pass
    for name,var in dataset.items():
      var.name = name
    dataset = list(dataset.values())

    # Continue with the encoding
    return ECCAS_Data.encode.__func__(cls,dataset)

  # Tell the parent GEM interface what filenames to use for writing data.
  @staticmethod
  def _fstd_date2filename (date, forecast):
    return "area_%04d%02d%02d%02d"%(date.year,date.month,date.day,date.hour)

  # We need to edit the FSTD records before they're written, in order to
  # set IP2 to the hour of day (needed by the emissions preprocessor).
  @staticmethod
  def _fstd_tweak_records (records):
    from pygeode.formats.fstd_core import stamp2date
    # Select non-coordinate records (things that aren't already using IP2)
    ind = (records['ip2'] == 0)
    # Set IP2 to the hour
    records['ip2'][ind] = (stamp2date(records['dateo'][ind]) / 3600) % 24
    # Set other defaults that may be expected by the emissions preprocessor
    records['typvar'][ind] = 'F'
    records['deet'][ind] = 0


# Add this interface to the table.
from . import table
table['eccas-flux'] = ECCAS_Flux_Data


