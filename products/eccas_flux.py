from gem import GEM_Data

class ECCAS_Flux_Data(GEM_Data):

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


# Instantiate the interface
interface = ECCAS_Flux_Data()

# Define the open method as a function, so it's picklable.
def open_file (filename):
  return interface.open_file(filename)


