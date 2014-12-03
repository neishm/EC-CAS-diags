from gem import GEM_Data

class ECCAS_Data(GEM_Data):

  field_list = GEM_Data.field_list + (
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
    ('OH', 'OH', 'molecules m-3'),
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

    # Add species name for all products (to assist in things like unit conversion)
    for varname in data:
      if varname.startswith('CO2'):
        data[varname].atts['specie'] = 'CO2'
      elif varname.startswith('CH4'):
        data[varname].atts['specie'] = 'CH4'


    # Convert froma dictionary back to a list
    dataset = list(data.values())

    return dataset


  # Method to re-encode data into the source context
  # (e.g., rename fields to what would be originally in these kinds of files)
  def encode (self, dataset):
    from gem import GEM_Data
    from common import conversion_factor
    # Call the generic GEM encoder to convert to the right units and field names
    dataset = GEM_Data.encode(self, dataset)
    # Do some extra stuff to offset COC / CLA fields
    for i, var in enumerate(dataset):
      if var.name in ('COC','CLA'):
        dataset[i] = (var + conversion_factor('100 ppm', 'ug(C) kg(air)-1', context='CO2')).as_type('float32')
    return dataset

  # For our forward cycles, we need to hard-code the ig1/ig2 of the tracers.
  # This is so we match the ip1/ip2 of the wind archive we're injecting
  # into the "analysis" files.
  @staticmethod
  def _fstd_tweak_records (records):
    # Select non-coordinate records (things that aren't already using IP2)
    ind = (records['ip2'] == 0)
    # Hard code the ig1 / ig2
    records['ig1'][ind] = 88320
    records['ig2'][ind] = 57863
    # Update the coordinate records to be consistent.
    records['ip1'][~ind] = 88320
    records['ip2'][~ind] = 57863
    # Just for completion, set the typvar and deet as well.
    records['typvar'][ind] = 'A'
    records['deet'][ind] = 0


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

    if len(forward_files) == 0 and len(chmmean_files) == 0 and len(chmstd_files) == 0:
      raise ValueError ("No data found at %s"%experiment_dir)

    # Fix the area emissions data, to have the proper lat/lon
    if len(forward_data.datasets) > 0:
      lat = forward_data.datasets[0].lat
      lon = forward_data.datasets[0].lon
    elif len(chmmean_data.datasets) > 0:
      lat = chmmean_data.datasets[0].lat
      lon = chmmean_data.datasets[0].lon
    else:
      raise ValueError ("Don't know how to fix the emissions lat/lon")
    flux_data = DataInterface(d.replace_axes(lat=lat,lon=lon) for d in flux_data)
    # Decode the emissions fields
    import eccas_flux
    flux_data = DataInterface([eccas_flux.interface.decode(fd) for fd in flux_data])

    # Combine all datasets into a single unit
    self.data = DataInterface(chmmean_data.datasets+chmstd_data.datasets+flux_data.datasets+forward_data.datasets)

    self.cache = cache


