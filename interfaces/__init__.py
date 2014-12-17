
# Generic interface for model data.
# Each specific model would need to sub-class this, and implement the
# needed interfaces.
class ModelData (object):

  # List of fields that can be autoconverted
  # (original_name, standard_name, units)
  # To be filled out by the model interfaces that derive from this class.
  field_list = ()

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    raise NotImplementedError

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls,dataset):
    from pygeode.dataset import asdataset
    dataset = asdataset(dataset)

    # Convert to a dictionary (for referencing by variable name)
    dataset = dict((var.name,var) for var in dataset)

    # Do the fieldname / units conversions
    for old_name, new_name, units in cls.field_list:
      if old_name in dataset:
        var = dataset.pop(old_name)
        var.atts['units'] = units
        dataset[new_name] = var

    # Make sure the variables have the appropriate names
    for name, var in dataset.iteritems():  var.name = name

    dataset = asdataset(dataset.values())
    return dataset


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    raise NotImplementedError

  # Method to fully reconstruct a model dataset that had been cached in
  # an intermediate format.
  @staticmethod
  def load_hook (dataset):
    return dataset

  # Method to re-encode data into the source context
  # (e.g., rename fields to what would be originally in these kinds of files)
  @classmethod
  def encode (cls, dataset):
    from pygeode.dataset import asdataset
    from common import convert
    from warnings import warn

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Convert the field names and units
    for local_name, standard_name, units in cls.field_list:
      if standard_name in data:
        var = data.pop(standard_name)
        try:
          var = convert(var, units)
        except ValueError as e:
          warn ("Unable to encode '%s' to '%s': %s"%(standard_name, gem_name, e))
          continue
        data[local_name] = var

    # Check for any stragglers, remove them
    for varname in data.keys():
      if all(varname != name for name, n, u in cls.field_list):
        warn ("Dropping unrecognized field '%s'"%varname)
        data.pop(varname)

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Convert to a list
    data = list(data.values())

    return data

  # Method to write data to file(s).
  @staticmethod
  def write (datasets, dirname):
    raise NotImplementedError

  # Helper method to compute the change in pressure within a vertical layer.
  @staticmethod
  def compute_dp (zaxis, p0):
    raise NotImplementedError

  # Helper method to compute pressure levels from the given z-axis and surface pressure
  @staticmethod
  def compute_pressure (zaxis, p0):
    raise NotImplementedError

  # Initialize a model interface.
  # Scans the provided files, and constructs the datasets.
  def __init__ (self, name, title, files, manifest=None):
    from os.path import exists, isdir
    from glob import glob
    from data_interface import DataInterface
    self.name = name
    self.title = title
    expanded_files = []
    if isinstance(files,str): files = [files]
    for f in files:
      if isdir(f):
        expanded_files.extend(self.find_files(f))
      else:
        expanded_files.extend(glob(f))
    if len(expanded_files) == 0:
        raise ValueError("No matches for '%s'."%files)
    for f in expanded_files:
      if not exists(f):
        raise ValueError("File '%s' does not exist."%f)
    data = DataInterface.from_files(expanded_files, type(self), manifest=manifest)
    # Filter the data (get standard field names, etc.)
    data = data.filter(self.decode)
    self.data = data

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
  data = DataInterface.from_files(expanded_files, interface, manifest=manifest)

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

