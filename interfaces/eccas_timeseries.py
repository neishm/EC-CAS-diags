# Interface for EC-CAS timeseries data.
# Use the EC-CAS fieldnames / units, and the FSTD timeseries file format.

from interfaces import eccas, fstd_timeseries

class ECCAS_Timeseries(fstd_timeseries.FSTD_Timeseries, eccas.ECCAS_Data):

  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    from os.path import exists
    if exists(dirname+"/time_series"):
      dirname += "/time_series"
    return glob(dirname+"/time_series*.fst")


# Give this class a standard reference name, to make it easier to auto-discover.
interface = ECCAS_Timeseries

