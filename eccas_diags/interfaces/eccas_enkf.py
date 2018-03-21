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

class ECCAS_EnKF_Data(ECCAS_Data):
  """
  EC-CAS model output for Ensemble Kalman Filter experiments.
  """

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import fstd
    # Ugly hack to force the PyGeode FSTD interface to always associate the
    # !! record with the fields (override the IG*/IP* pairing).
    orig_attach_vertical_axes = fstd.attach_vertical_axes
    def hacked_attach_vertical_axes (varlist, vertical_records):
      vertical_records['ip1'] = varlist[0].atts['ig1']
      vertical_records['ip2'] = varlist[0].atts['ig2']
      vertical_records['ip3'] = varlist[0].atts['ig3']
      return orig_attach_vertical_axes (varlist, vertical_records)

    # Apply the hack, read the data, then remove the hack after we're done.
    fstd.attach_vertical_axes = hacked_attach_vertical_axes
    dataset = fstd.open(filename, raw_list=True)
    fstd.attach_vertical_axes = orig_attach_vertical_axes

    # We need to rename the CO2 field from the ensemble spread  file, so it
    # doesn't get mixed up with the ensemble mean data (also called CO2).

    # Determine if we have ensemble spread data from EC-CAS
    # Add a suffix to the variable names, if we have ensemble spread data.
    for var in dataset:
      etiket = var.atts.get('etiket')
      if etiket in ('STDDEV','E2090KFN192'):
        var.name += "_ensemblespread"
      elif etiket in ('MEAN','E2AVGANNALL','E2AVGANPALL','INITIAL'):
        pass # No name clobbering for ensemble mean
      else:
        from warnings import warn
        warn ("Unable to determine if etiket '%s' is mean or spread.  Data will not be used."%etiket)
        var.name += "_unknown"

    return dataset

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls,dataset):
    from .eccas_dry import ECCAS_Data
    from pygeode.dataset import Dataset

    dataset = list(dataset)

    # Limit the forecast period so there's no overlap.
    # Assuming a 6-hour interval between analyses, and exclude last (hour 6)
    # forecast.
    for i,var in enumerate(dataset):
      if var.hasaxis('forecast'):
        dataset[i] = var(forecast=(0.0,4.5))

    # Detect ensemble spread fields
    for var in dataset:
      if var.name.endswith('_ensemblespread'):
        var.name = var.name.rstrip('_ensemblespread')
        var.atts['ensemble_op'] = 'spread'

    # Do EC-CAS field decoding
    dataset = ECCAS_Data.decode.__func__(cls,dataset)

    # Add back ensemble spread suffix.
    dataset = list(dataset)
    for var in dataset:
      if var.atts.get('ensemble_op') == 'spread':
        var.name += '_ensemblespread'

    return dataset

  # For our EnKF cycles, we need to hard-code the ig1/ig2 of the tracers.
  # This is so we match the ip1/ip2 of the EnKF initial file we're injecting
  # into.
  @staticmethod
  def _fstd_tweak_records (records):
    # Select non-coordinate records (things that aren't already using IP2)
    ind = (records['ip2'] == 0)
    # Hard code the ig1 / ig2
    records['ig1'][ind] = 38992
    records['ig2'][ind] = 45710
    records['ig3'][ind] = 1
    # Update the coordinate records to be consistent.
    records['ip1'][~ind] = 38992
    records['ip2'][~ind] = 45710
    records['ip3'][~ind] = 1
    # Just for completion, set the typvar and deet as well.
    records['typvar'][ind] = 'A'
    records['deet'][ind] = 0


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from os.path import exists
    from glob import glob

    files = []

    ##############################
    # Model output
    ##############################

    if exists (dirname+'/model'):
      model_dir = dirname+'/model'
    else:
      model_dir = dirname

    files.extend(glob(model_dir+"/[0-9]*_[0-9]*chmmean"))
    files.extend(glob(model_dir+"/[0-9]*_[0-9]*chmstd"))
    files.extend(glob(model_dir+"/[0-9]*_[0-9]*analrms"))
    # Omit 0h forecasts
    files = [f for f in files if not f.endswith('_000') and not f.endswith('_000h')]

    return files



# Add this interface to the table.
from . import table
table['eccas-enkf'] = ECCAS_EnKF_Data

