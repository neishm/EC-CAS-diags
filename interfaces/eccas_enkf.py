from .eccas_dry import ECCAS_Data

class ECCAS_EnKF_Data(ECCAS_Data):

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import fstd
    dataset = fstd.open(filename, raw_list=True)

    # We need to rename the CO2 field from the ensemble spread  file, so it
    # doesn't get mixed up with the ensemble mean data (also called CO2).

    # Determine if we have ensemble spread data from EC-CAS
    # Add a suffix to the variable names, if we have ensemble spread data.
    for var in dataset:
      etiket = var.atts.get('etiket')
      if etiket in ('STDDEV','E2090KFN192'):
        var.name += "_ensemblespread"
      elif etiket in ('MEAN','E2AVGANNALL'):
        pass # No name clobbering for ensemble mean
      else:
        from warnings import warn
        warn ("Unable to determine if etiket '%s' is mean or spread.  Assuming mean."%etiket)

    return dataset


  # For our EnKF cycles, we need to hard-code the ig1/ig2 of the tracers.
  # This is so we match the ip1/ip2 of the EnKF initial file we're injecting
  # into.
  @staticmethod
  def _fstd_tweak_records (records):
    # Select non-coordinate records (things that aren't already using IP2)
    ind = (records['ip2'] == 0)
    # Hard code the ig1 / ig2
    records['ig1'][ind] = 56497
    records['ig2'][ind] = 90697
    # Update the coordinate records to be consistent.
    records['ip1'][~ind] = 56497
    records['ip2'][~ind] = 90697
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
    # Omit 0h forecasts
    files = [f for f in files if not f.endswith('_000') and not f.endswith('_000h')]

    return files



# Add this interface to the table.
from . import table
table['eccas-enkf'] = ECCAS_EnKF_Data

