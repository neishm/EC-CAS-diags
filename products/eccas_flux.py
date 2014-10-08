from eccas import ECCAS_Data

class ECCAS_Flux_Data(ECCAS_Data):

  field_list = (
    ('ECO2', 'CO2_flux', 'g(C) s-1'),
    ('ECBB', 'CO2_fire_flux', 'g(C) s-1'),
    ('ECFF', 'CO2_fossil_flux', 'g(C) s-1'),
    ('ECOC', 'CO2_ocean_flux', 'g(C) s-1'),
    ('ECLA', 'CO2_bio_flux', 'g(C) s-1'),
  )


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return glob(dirname+"/area_??????????")

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

# Instantiate the interface
interface = ECCAS_Flux_Data()

# Define the open method as a function, so it's picklable.
def open_file (filename):
  return interface.open_file(filename)


