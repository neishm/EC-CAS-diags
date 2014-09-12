from gem import GEM_Data

class ECCAS_Data(GEM_Data):

  field_list = GEM_Data.field_list + (
    ('ECO2', 'CO2_flux', 'g(C) s-1'),
    ('ECBB', 'CO2_fire_flux', 'g(C) s-1'),
    ('ECFF', 'CO2_fossil_flux', 'g(C) s-1'),
    ('ECOC', 'CO2_ocean_flux', 'g(C) s-1'),
    ('ECLA', 'CO2_bio_flux', 'g(C) s-1'),
    ('CO2', 'CO2', 'ug(C) kg(air)-1'),
    ('CBB', 'CO2_fire', 'ug(C) kg(air)-1'),
    ('CFF', 'CO2_fossil', 'ug(C) kg(air)-1'),
    ('COC', 'CO2_ocean', 'ug(C) kg(air)-1'),
    ('CLA', 'CO2_bio', 'ug(C) kg(air)-1'),
    ('CO2B', 'CO2_background', 'ug(C) kg(air)-1'),
    ('CH4', 'CH4', 'ug kg(air)-1'),
    ('CH4B', 'CH4_background', 'ug kg(air)-1'),
    ('CHFF', 'CH4_fossil', 'ug kg(air)-1'),
    ('CHBB', 'CH4_fire', 'ug kg(air)-1'),
    ('CHOC', 'CH4_ocean', 'ug kg(air)-1'),
    ('CHNA', 'CH4_natural', 'ug kg(air)-1'),
    ('CHAG', 'CH4_agriculture', 'ug kg(air)-1'),
  )

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  def decode (self, dataset):
    from pygeode.dataset import asdataset
    from common import conversion_factor
    from gem import GEM_Data

    dataset = GEM_Data.decode(self, dataset)

    # Determine if we have ensemble spread data from EC-CAS
    chmstd = False
    for var in dataset:
      if var.atts.get('etiket') == 'STDDEV':
        chmstd = True

    # Add a suffix to the variable names, if we have ensemble spread data.
    if chmstd:
      for var in dataset:
        var.name += "_ensemblespread"

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Offset the ocean and land fields by 100ppm
    if 'CO2_ocean' in data:
      data['CO2_ocean'] -= conversion_factor('100 ppm', 'ug(C) kg(air)-1', context='CO2')
    if 'CO2_bio' in data:
      data['CO2_bio'] -= conversion_factor('100 ppm', 'ug(C) kg(air)-1', context='CO2')

    # Convert froma dictionary back to a list
    dataset = list(data.values())

    return dataset


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob

    files = GEM_Data.find_files(dirname)

    # Search for flux data as well
    files.extend(glob(dirname+"/area_??????????"))

    return files

# Instantiate the interface
interface = ECCAS_Data()

# Define the open method as a function, so it's picklable.
def open_file (filename):
  return interface.open_file(filename)


# GEM data interface
class GEM_Data (object):
  def __init__ (self, experiment_dir, flux_dir, name, title, tmpdir=None):
    from cache import Cache
    from data_interface import DataInterface
    from glob import glob

    indir = experiment_dir

    self.name = name
    self.title = title
    fallback_dirs = [tmpdir] if tmpdir is not None else []
    cache = Cache(dir = indir + "/nc_cache", fallback_dirs=fallback_dirs, global_prefix=name+"_", load_hooks=[interface.load_hook])

    files = []

    ##############################
    # Model output
    ##############################

    files.extend(glob(indir+"/[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/km[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/dm[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/pm[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/k[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/d[0-9]*_[0-9]*"))
    files.extend(glob(indir+"/p[0-9]*_[0-9]*"))
    # Omit 0h forecasts
    files = [f for f in files if not f.endswith('_000') and not f.endswith('_000h')]

    ##############################
    # Fluxes
    ##############################

    if flux_dir is not None:
      files.extend(glob(flux_dir+"/area_2009??????"))

    manifest = cache.full_path("manifest", writeable=True)

    # Ensemble mean data
    chmmean_files = [f for f in files if f.endswith('_chmmean')]
    chmmean_data = DataInterface.from_files(chmmean_files, opener=open_file, manifest=manifest)
    # Apply the conversions & transformations
    chmmean_data = DataInterface(map(interface.decode,chmmean_data))

    # Ensemble spread data
    chmstd_files = [f for f in files if f.endswith('_chmstd')]
    chmstd_data = DataInterface.from_files(chmstd_files, opener=open_file, manifest=manifest)
    # Apply the conversions & transformations
    chmstd_data = DataInterface(map(interface.decode,chmstd_data))

    # Area emissions
    flux_files = [f for f in files if '/area_' in f]
    flux_data = DataInterface.from_files(flux_files, opener=open_file, manifest=manifest)
    # Apply the conversions & transformations
    flux_data = DataInterface(map(interface.decode,flux_data))

    # Forward model data
    forward_files = sorted(set(files)-set(chmmean_files)-set(chmstd_files)-set(flux_files))
    forward_data = DataInterface.from_files(forward_files, opener=open_file, manifest=manifest)
    # Apply the conversions & transformations
    forward_data = DataInterface([interface.decode(fd) for fd in forward_data])

    # Fix the area emissions data, to have the proper lat/lon
    lat = forward_data.datasets[0].lat
    lon = forward_data.datasets[0].lon
    flux_data = DataInterface(d.replace_axes(lat=lat,lon=lon) for d in flux_data)

    # Combine all datasets into a single unit
    self.data = DataInterface(chmmean_data.datasets+chmstd_data.datasets+flux_data.datasets+forward_data.datasets)

    self.cache = cache


