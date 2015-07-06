# Interface for EC-CAS timeseries data.
# Use the EC-CAS fieldnames / units, and the FSTD timeseries file format.

from . import eccas_dry, fstd_timeseries

class ECCAS_Timeseries(fstd_timeseries.FSTD_Timeseries, eccas_dry.ECCAS_Data):

  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    from os.path import exists
    if exists(dirname+"/time_series"):
      dirname += "/time_series"
    return glob(dirname+"/time_series*.fst")


# Add this interface to the table.
from . import table
table['eccas-timeseries'] = ECCAS_Timeseries

