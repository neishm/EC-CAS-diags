# A generic data interface.
# Essentially, a collection of datasets, with some convenience methods.
class DataInterface (object):

  # Generic initializer - takes a list of Datasets, stores it.
  def __init__ (self, datasets):
    from pygeode.dataset import asdataset
    self.datasets = tuple(map(asdataset,datasets))

  # Allow the underlying datasets to be iterated over
  def __iter__ (self):
    return iter(self.datasets)


  # Get the requested variable(s).
  # The possible matches are returned one at a time, and the calling method
  # will have to figure out which one is the best.
  def find (self, *vars, **kwargs):
    requirement=kwargs.pop('requirement',None)
    if len(kwargs) > 0:
      raise TypeError("Unexpected keyword arguments: %s"%kwargs.keys())

    for dataset in self.datasets:
      # Check if this dataset meets any extra requirements
      if requirement is not None:
        if not requirement(dataset):
          continue
      # Check if all the variables are in the dataset
      if all(v in dataset for v in vars):
        varlist = [dataset[v] for v in vars]
        if len(varlist) == 1: yield varlist[0]
        else: yield varlist

  # Determine if a given variable is in the data somewhere
  def have (self, var):
    for dataset in self.datasets:
      if var in dataset: return True
    return False

  # Helper function - find the best field matches that fit some criteria
  def find_best (self, fields, requirement=None, maximize=None, minimize=None):

    # If we are given a single field name (not in a list), then return a
    # single field (also not in a list structure).
    collapse_result = False
    if isinstance(fields,str):
      fields = [fields]
      collapse_result = True

    if len(fields) == 1:
      candidates = zip(self.find(*fields,requirement=requirement))
    else:
      candidates = list(self.find(*fields,requirement=requirement))

    # At the very least, order by domain shapes
    # (so we never have an arbitrary order of matches)
    def domain_size (varlist):
      return sorted((v.name,v.shape) for v in varlist)
    candidates = sorted(candidates, key=domain_size, reverse=True)

    if isinstance(maximize,tuple):
      # Will be sorted by increasing order, so need to reverse the cost
      # functions here.
      maximize = lambda x,F=maximize: [-f(x) for f in F]

    if isinstance(minimize,tuple):
      minimize = lambda x,F=minimize: [f(x) for f in F]

    # Sort by the criteria (higher value is better)
    if maximize is not None:
      candidates = sorted(candidates, key=maximize)
    elif minimize is not None:
      candidates = sorted(candidates, key=minimize)

    if len(candidates) == 0:
      raise KeyError("Unable to find any matches for fields=%s, requirement=%s, maximize=%s, minimize=%s"%(fields, requirement, maximize, minimize))

    # Use the best result
    result = candidates[0]

    if collapse_result: result = result[0]
    return result



# Generic interface for a data product.
# Each specific product would need to sub-class this, and implement the
# needed interfaces.
class DataProduct (DataInterface):

  # List of fields that can be autoconverted
  # (original_name, standard_name, units)
  # To be filled out by the products that derive from this class.
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

    # Extra fields (not from the dataset, but useful for conversions)
    from ..common import grav, get_area
    from pygeode.var import Var
    # Earth's gravitational constant
    if 'gravity' not in dataset:
      dataset['gravity'] = Var(axes=(), name='gravity', atts={'units':'m s-2'}, values=grav)
    # Grid cell area
    if 'cell_area' not in dataset:
      for var in dataset.values():
        if var.hasaxis('lat') and var.hasaxis('lon'):
          dataset['cell_area'] = get_area(var.lat,var.lon)
          break

    # Make sure the variables have the appropriate names
    for name, var in dataset.iteritems():  var.name = name

    dataset = asdataset(dataset.values())
    return dataset


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    raise NotImplementedError

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    import os
    dirs = dirname.split(os.sep)
    # Default behaviour - return the lowest directory name
    return dirs[-1]


  # Method to find all relevant files for the given patterns.
  # Evaluates globbing patterns, and searches directories.
  @classmethod
  def expand_files (cls, files):
    from os.path import exists, isdir
    from glob import glob
    expanded_files = []
    if isinstance(files,str): files = [files]
    for f in files:
      if isdir(f):
        expanded_files.extend(cls.find_files(f))
      else:
        expanded_files.extend(glob(f))
    if len(expanded_files) == 0:
        raise ValueError("No matches for '%s'."%files)
    for f in expanded_files:
      if not exists(f):
        raise ValueError("File '%s' does not exist."%f)
    return expanded_files


  # Method to re-encode data into the source context
  # (e.g., rename fields to what would be originally in these kinds of files)
  @classmethod
  def encode (cls, dataset):
    from pygeode.dataset import asdataset
    from ..common import convert
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
          warn ("Unable to encode '%s' to '%s': %s"%(standard_name, local_name, e))
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


  # Any axis that should be common among datasets.
  # Final values will be superset of values from all variables.
  _common_axis = None

  # Indicates that the domains should not cross file boundaries.
  _per_file = False

  # Initialize a product interface.
  # Scans the provided files, and constructs the datasets.
  def __init__ (self, files, name, title='untitled', cache=None, rescan=False, color='black', linestyle='-', std_style='lines', marker=None):
    from .data_scanner import from_files
    from os.path import exists
    from os import remove
    self.name = name
    self.title = title
    self.cache = cache
    self.color = color
    self.linestyle = linestyle
    self.std_style = std_style
    self.marker = marker
    if cache is not None:
      manifest = cache.full_path(name+"_manifest", writeable=True)
      if exists(manifest) and rescan: remove(manifest)
    else:
      manifest = None

    expanded_files = self.expand_files(files)
    if self._per_file:
      data = [from_files([f], type(self), manifest=manifest, force_common_axis=self._common_axis) for f in expanded_files]
      # Flatten into a single list
      data = sum(data,[])
    else:
      data = from_files(expanded_files, type(self), manifest=manifest, force_common_axis=self._common_axis)
    # Decode the data (get standard field names, etc.)
    data = map(self.decode, data)
    # Store the data in this object.
    DataInterface.__init__(self,data)


# A sub-class to handle station obs data.
class StationObsProduct(DataProduct):
  _common_axis = 'time'


# A sub-class to handle data that should be treated independently for each
# file.
class SplitProduct(DataProduct):
  _per_file = True

# A special class to represent derived data as a "product"
class DerivedProduct (DataProduct):
  # Override the __init__ to take a list of variables, not filenames.
  def __init__ (self, datasets, source):
    from pygeode.var import Var
    from pygeode.dataset import Dataset
    self.name = source.name
    self.title = source.title
    self.cache = source.cache
    self.color = source.color
    self.linestyle = source.linestyle
    self.std_style = source.std_style
    self.marker = source.marker
    if isinstance(datasets,Var):
      datasets = [Dataset([datasets])]
    elif hasattr(datasets,'__len__') and isinstance(datasets[0],Var):
      datasets = [Dataset(datasets)]
    elif isinstance(datasets,Dataset):
      datasets = [datasets]
    # Store the data in this object.
    DataInterface.__init__(self,datasets)


# Find all available interfaces
table = {}
def _load_interfaces ():
  import pkgutil
  import importlib
  for loader, name, ispkg in pkgutil.walk_packages(__path__):
    if ispkg: continue
    importlib.import_module(__name__+'.'+name)
_load_interfaces()  # Allow the interfaces to add their entries to this table

