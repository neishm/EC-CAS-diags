
# Generic interface for model data.
# Each specific model would need to sub-class this, and implement the
# needed interfaces.
class ModelData (object):

  # Method to open a single file
  def open_file (filename):
    raise NotImplementedError

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  def decode (self, dataset):
    raise NotImplementedError

  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  def find_files (dirname):
    raise NotImplementedError

  # Method to fully reconstruct a model dataset that had been cached in
  # an intermediate format.
  def load_hook (dataset):
    return dataset

  # Method to re-encode data into the source context
  # (e.g., rename fields to what would be originally in these kinds of files)
  def encode (self, dataset):
    raise NotImplementedError

  # Method to write data to file(s).
  def write (self, datasets, dirname):
    raise NotImplementedError

  # Helper method to compute the change in pressure within a vertical layer.
  def compute_dp (zaxis, p0):
    raise NotImplementedError

  # Helper method to compute pressure levels from the given z-axis and surface pressure
  def compute_pressure (zaxis, p0):
    raise NotImplementedError

# Helper method - get a model interface
def get_model_interface (model_name):
  import importlib
  # Try to find a module with the given name
  # Note: hyphens '-' are mangled to underscores '_' when looking for a module.
  model = importlib.import_module('interfaces.'+model_name.replace('-','_'))
  return model.interface

# Helper method - open the specified file(s) through the given model interface,
# and return a model data object.
def read_model_data (model_name, files, manifest=None):
  from os.path import exists, isdir
  from glob import glob
  from data_interface import DataInterface
  import importlib
  interface = get_model_interface(model_name)
  expanded_files = []
  for f in files:
    if isdir(f):
      expanded_files.extend(interface.find_files(f))
    else:
      expanded_files.extend(glob(f))
  if len(expanded_files) == 0:
      raise ValueError("No matches for '%s'."%files)
  for f in expanded_files:
    if not exists(f):
      raise ValueError("File '%s' does not exist."%f)
  #TODO: remove this call, once the manifest is changed to contain a simple model string instead of an opener function.
  opener = importlib.import_module('interfaces.'+model_name.replace('-','_')).open_file
  data = DataInterface.from_files(expanded_files, opener=opener, manifest=manifest)

  # Filter the data (get standard field names, etc.)
  data = data.filter(interface.decode)

  return data

# Helper method - write some data into file(s), using the specified model
# interface.
def write_model_data (model_name, dirname, datasets):
  from os.path import exists, isdir
  from os import makedirs
  # Try to find a module with the given name
  interface = get_model_interface(model_name)
  # Make sure we have a directory to put this.
  if not isdir(dirname):
    if exists (dirname):
      raise ValueError ("'%s' is not a directory."%dirname)
    else: makedirs(dirname)
  # Encode the data in a representation suitable for the given model type.
  datasets = map(interface.encode, datasets)

  # Write it out
  interface.write (datasets, dirname)

