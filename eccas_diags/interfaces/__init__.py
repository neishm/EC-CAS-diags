###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################


# Generic interface for a data product.
# Each specific product would need to sub-class this, and implement the
# needed interfaces.
from .data_scanner import DataInterface
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

    dataset = list(dataset)
    # Do the fieldname / units conversions
    lookup = dict((old_name,(new_name,units)) for old_name, new_name, units in cls.field_list)
    for var in dataset:
      if var.name in lookup:
        new_name, units = lookup[var.name]
        var.name = new_name
        var.atts['units'] = units

    return dataset

  # Extra fields (not from the dataset, but useful for conversions).
  # Needs to be explicitly called by each interface.
  # Expects 'dataset' to be a dictionary.
  @staticmethod
  def _add_extra_fields (dataset):
    from ..common import grav, get_area
    from pygeode.var import Var
    if isinstance(dataset,dict):
      dataset = dataset.values()
    varnames = [var.name for var in dataset]
    # Earth's gravitational constant
    if 'gravity' not in varnames:
      gravity = Var(axes=(), name='gravity', atts={'units':'m s-2'}, values=grav)
      dataset.append(gravity)
    # Grid cell area
    if 'cell_area' not in varnames:
      latlon = [var for var in dataset if var.hasaxis('lat') and var.hasaxis('lon')]
      if len(latlon) > 0:
        var = latlon[0]
        cell_area = get_area(var.lat,var.lon)
        cell_area.name = 'cell_area'
        dataset.append(cell_area)

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
    from ..common import find_and_convert
    from warnings import warn

    dataset = asdataset(dataset)

    # Warn about fields that aren't on the list (and won't be encoded)
    for var in dataset:
      if all(var.name != standard_name for local_name, standard_name, units in cls.field_list):
        warn ("Not encoding unrecognized field '%s'"%var.name)

    # Convert to the expected units and rename
    data = []
    for local_name, standard_name, units in cls.field_list:
      if standard_name in dataset:
        try:
          var = find_and_convert(dataset, standard_name, units)
          data.append(var.rename(local_name))
        except ValueError as e:
          warn ("Unable to encode '%s' to '%s': %s"%(standard_name, local_name, e))

    return data

  # Method to write data to file(s).
  @staticmethod
  def write (datasets, dirname):
    raise NotImplementedError

  # Indicates that the domains should not cross file boundaries.
  _per_file = False

  # Initialize a product interface.
  # Scans the provided files, and constructs the datasets.
  def __init__ (self, files, name, title='untitled', cache=None, rescan=False, color='black', linestyle='-', std_style='lines', marker=None, cmap='jet'):
    from .data_scanner import _Manifest, from_files
    from os.path import exists
    from os import remove
    from pygeode.dataset import asdataset
    self.name = name
    self.title = title
    self.cache = cache
    self.color = color
    self.linestyle = linestyle
    self.std_style = std_style
    self.marker = marker
    self.cmap = cmap
    if cache is not None:
      manifest = cache.full_path(name+"_manifest", writeable=True)
      if exists(manifest) and rescan: remove(manifest)
    else:
      manifest = None

    # Start a manifest (optionally, associate it with a file on disk).
    manifest = _Manifest(manifest)

    expanded_files = self.expand_files(files)
    if self._per_file:
      data = [from_files([f], type(self), manifest=manifest, save_manifest=False) for f in expanded_files]
      # Flush the manifest back to disk after all files are scanned.
      manifest.save()
      # Flatten into a single list
      data = sum(data,[])
    else:
      data = from_files(expanded_files, type(self), manifest=manifest)


    # Decode the data (get standard field names, etc.)
    data = map(self.decode, data)
    data = map(asdataset, data)
    # Store the data in this object.
    DataInterface.__init__(self,data)


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
    self.cmap = source.cmap
    if isinstance(datasets,Var):
      datasets = [Dataset([datasets])]
    elif hasattr(datasets,'__len__') and len(datasets) > 0 and isinstance(datasets[0],Var):
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

