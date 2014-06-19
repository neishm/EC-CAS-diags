# A container for holding multiple datasets of the same data
# (one dataset per domain).
# E.g., there may be surface and 3D output at different time frequencies.

# Current version of the manifest file format.
# If this version doesn't match the existing manifest file, then the manifest
# is re-generated.
MANIFEST_VERSION="0~alpha5"

# Scan through all the given files, produce a manifest of all data available.
def scan_files (files, opener, manifest):
  from os.path import exists, getatime, getmtime
  from os import utime
  import gzip
  import cPickle as pickle
  from pygeode.progress import PBar

  # If an old manifest already exists, start with that.
  if exists(manifest):
    with gzip.open(manifest,'r') as f:
      version = pickle.load(f)
      table = pickle.load(f)
    mtime = getmtime(manifest)
  if not exists(manifest) or version != MANIFEST_VERSION:
    table = {}
    mtime = 0

  # Add these existing objects to the get_axis() function
  # (so it can re-use them)
  for filename, (_opener,entries) in table.iteritems():
    for varname, axes, atts in entries:
      map(_lookup_axis,axes)

  pbar = PBar (message = "Generating %s"%manifest)

  modified_table = False

  # Construct / add to the table
  for i,f in enumerate(files):
    pbar.update(i*100./len(files))
    if f in table:
      # File has changed since last time?
      if int(getmtime(f)) > mtime:
        # Remove existing info
        del table[f]
      else:
        # Otherwise, we've already dealt with the file, so skip it.
        continue
    # Always use the latest modification time to represent the valid time of
    # the whole table.
    mtime = max(mtime,int(getmtime(f)))

    # Record all variables from the file.
    entries = []
    table[f] = opener, entries
    for var in opener(f):

      axes = tuple(_lookup_axis(a) for a in var.axes)
      entries.append((var.name, axes, var.atts))

    modified_table = True


  if modified_table:
    with gzip.open(manifest,'w') as f:
      pickle.dump(MANIFEST_VERSION, f)
      pickle.dump(table, f)
    # Set the modification time to the latest file that was used.
    atime = getatime(manifest)
    utime(manifest,(atime,mtime))

  pbar.update(100)

  # Limit the results to the files that were requested.
  # Ignore the rest of the manifest.

  return dict((f,table[f]) for f in files)

# A list of variables (acts like an "axis" for the purpose of domain
# aggregating).
class Varlist (object):
  def __init__ (self, varnames):
    self.values = tuple(varnames)
  def __iter__ (self):  return iter(self.values)
  def __len__ (self): return len(self.values)
  def __repr__ (self): return "<%s>"%self.__class__.__name__


# Helper function: recycle an existing axis object if possible.
# This allows axes to be compared by their ids, and makes pickling them
# more space-efficient.
def _lookup_axis (axis, _hash_bins={}, _ids=[]):
  if id(axis) in _ids: return axis  # Already have this exact object.
  values = tuple(axis.values)
  # Get a hash value that will be equal among axes that are equivalent
  axis_hash = hash((type(axis),values))
  # Get all axes that have this hash (most likely, only 1 match (or none))
  hash_bin = _hash_bins.setdefault(axis_hash,[])
  # Find one that is truly equivalent, otherwise add this new one to the cache.
  try:
    axis = hash_bin[hash_bin.index(axis)]
  except ValueError:
    hash_bin.append(axis)
    _ids.append(id(axis))  # Record this object id, in case we're passed it
                           # in again.

  return axis

# A generic data interface.
# Essentially, a collection of datasets, with some convenience methods.
class DataInterface (object):

  # Helper function: produce a new axis of the given type
  @staticmethod
  def _create_axis (sample, values):
    if isinstance(sample,Varlist):
      axis = Varlist(sorted(values))
    else:
      axis = sample.withnewvalues(sorted(values))
    return _lookup_axis(axis)


  # Merge axes together
  @classmethod
  def _get_axis_union (cls, axes):
    values = [axis.values for axis in axes]
    values = reduce(set.union, values, set())
    return cls._create_axis (axes[0], values)

  # Find common values between axes
  @classmethod
  def _get_axis_intersection (cls, axes):
    values = [axis.values for axis in axes]
    values = reduce(set.intersection, values, set(values[0]))
    return cls._create_axis (axes[0], values)


  # A domain (essentially a tuple of axes, with no deep comparisons)
  class Domain (object):
    def __init__ (self, axes):
      self.axes = tuple(axes)
    # A unique representation of the domain.
    # Assumes there is only one object id for each possible axis object,
    # to save time in comparisons.
    def _id (self):
      return tuple(frozenset(a.values) if isinstance(a,Varlist) else id(a) for a in self.axes)
    def __cmp__ (self, other):
      return cmp(self._id(), other._id())
    def __hash__ (self):
      return hash(self._id())
    def __iter__ (self):
      return iter(self.axes)
    def __repr__ (self):
  #    return "("+",".join("%s:%s"%(a.__class__.__name__,len(a)) for a in self.axes)+")"
      return "("+",".join(map(str,map(len,filter(None,self.axes))))+")"
    # Mask out an axis type (convert it to a 'None' placeholder)
    def without_axis (self, axis_type):
      return DataInterface.Domain([None if isinstance(a,axis_type) else a for a in self.axes])
    # Unmask an axis type (re-insert an axis object where the 'None' placeholder was
    def with_axis (self, axis):
      return DataInterface.Domain([axis if a is None else a for a in self.axes])
    # Return the axis of the given type.
    # Returns None if no such axis type is found.
    def get_axis (self, axis_type):
      for axis in self.axes:
        if isinstance(axis,axis_type): return axis
      return None


#TODO -----


  # Helper method - return all types of axes in a set of domains
  @staticmethod
  def _get_axis_types (domains):
    types = set()
    for domain in domains:
      for axis in domain:
        types.add(type(axis))
    return types

  # Helper method - aggregate along a particular axis
  # Inputs:
  #   domains: the set of original domains.
  #   axis_type: the type of axis to aggregate the domains over.
  # Input/Output:
  #   used_domains: set of original domains that are covered by the output
  #                 (i.e., ones that could be safely removed later).
  #                 These are appended to an existing set passed in.
  # Output: the domains that could be aggregated along to given axis.
  #         Domains without that axis type are ignored.
  @classmethod
  def _aggregate_along_axis (cls, domains, axis_type, used_domains=None):
    bins = {}
    touched_domains = set()
    for domain in domains:
      axis = domain.get_axis(axis_type)
      if axis is not None:
        touched_domains.add(domain)
        domain_group = domain.without_axis(axis_type)
        axis_bin = bins.setdefault(domain_group,{})
        axis_bin[id(axis)] = axis
    # For each domain group, aggregate the axes together
    # NOTE: assumes that all the axis segments are consistent
    # (same origin, units, etc.)
    # Also, assumes the axis values should be monotonically increasing.
    output = set()
    for domain_group, axis_bin in bins.iteritems():
      if len(axis_bin) == 1:  # Only one axis piece (nothing to aggregate)
        axis = axis_bin.values()[0]
        output.add(domain_group.with_axis(axis))
      # Otherwise, need to aggregate pieces together.
      else:
        new_axis = cls._get_axis_union (axis_bin.values())
        output.add(domain_group.with_axis(new_axis))

    if used_domains is not None:
      # Only consider a domain to be "used" if it was aggregated into a bigger
      # domain, *not* if it was directly copied to the output.
      used_domains.update(touched_domains - output)
    return domains | output


  # Find a minimal set of domains that cover all available data
  @classmethod
  def _get_prime_domains (cls, domains):
    axis_types = cls._get_axis_types(domains)
    # This may be an iterative process, that may need to be repeated.
    while True:
      used_domains = set()
      # Aggregate along one axis at a time.
      for axis_type in axis_types:
        domains = cls._aggregate_along_axis(domains, axis_type, used_domains)
      if len(used_domains) == 0: break  # Nothing aggregated
      domains -= used_domains  # Remove smaller pieces that are aggregated.

    return domains

  # Try merging multiple domains together.
  # For each pair of domains, look for an axis over which they could be
  # concatenated.  All other axes will be intersected between domains.
  @classmethod
  def _merge_domains (cls, d1, d2):
    domains = set()
    axis_types = cls._get_axis_types([d1,d2])
    # We need at least one of the two domains to contain all the types
    # (so we have a deterministic ordering of axes).
    # Make the first domain the one with all axes.
    #TODO: Check the relative order of the axes as well?
    if cls._get_axis_types([d1]) == axis_types:
      pass  # Already done
    elif cls._get_axis_types([d2]) == axis_types:
      d1, d2 = d2, d1  # Swap
    else:
      return set()  # Nothing can be done
    # Give the domains the same axes (broadcasting to extra axes)
    d2 = cls.Domain([d2.get_axis(type(a)) or a for a in d1.axes])
    for merge_axis_type in axis_types:
      m1 = d1.get_axis(merge_axis_type)
      m2 = d2.get_axis(merge_axis_type)
      merge_axis = cls._get_axis_union([m1,m2])
      # Skip if we aren't actually getting a bigger axis.
      if merge_axis is m1 or merge_axis is m2: continue
      axes = [merge_axis if isinstance(a1,merge_axis_type) else cls._get_axis_intersection([a1,a2]) for a1, a2 in zip(d1,d2)]
      # Skip if we don't have any overlap
      if any(len(a) == 0 for a in axes): continue
      domains.add(cls.Domain(axes))

    return domains

  @classmethod
  def _merge_all_domains (cls, domains):
    merged_domains = set(domains)
    while True:
      new_merged_domains = set()
      for d1 in domains:
        for d2 in merged_domains:
          new_merged_domains.update(cls._merge_domains(d1,d2))
      new_merged_domains -= merged_domains
      if len(new_merged_domains) == 0: break  # Nothing new added
      merged_domains.update(new_merged_domains)

    return domains | merged_domains

  # Remove any domains that are proper subsets of other domains
  # (Clean up anything that is not needed).
  @classmethod
  def _cleanup_subdomains (cls, domains):
    junk_domains = set()
    for d1 in domains:
      for d2 in domains:
        if d1 is d2: continue
        assert d1 != d2
        if cls._get_axis_types([d1]) != cls._get_axis_types([d2]): continue
        axis_types = cls._get_axis_types([d2])
        values1 = [d1.get_axis(a).values for a in axis_types]
        values2 = [d2.get_axis(a).values for a in axis_types]
        if all(set(v1) <= set(v2) for v1, v2 in zip(values1,values2)):
          junk_domains.add(d1)
    return domains - junk_domains

  # Scan a file manifest, return all possible domains available.
  @classmethod
  def _get_domains (cls, manifest):

    # Start by adding all domain pieces to the list
    domains = set()
    for opener, entries in manifest.itervalues():
      for var, axes, atts in entries:
        domains.add(cls.Domain([Varlist([var])]+list(axes)))

    # Reduce this to a minimal number of domains for data coverage
    domains = cls._get_prime_domains(domains)
    domains = cls._merge_all_domains(domains)
    domains = cls._cleanup_subdomains(domains)
    return domains

#TODO -----

  # Generic initializer - takes a list of Datasets, stores it.
  def __init__ (self, datasets):
    self.datasets = tuple(datasets)

  # Create a dataset from a set of files and an opener
  @classmethod
  def from_files (cls, filelist, opener, manifest):
    manifest = scan_files (filelist, opener, manifest)
    domains = cls._get_domains(manifest)
    datasets = [cls._domain_as_dataset(d,manifest) for d in domains]
    return cls(datasets)

#TODO -----

  # Wrap a domain as a dataset.
  # Requires the original file manifest, to determine where to get the data.
  @staticmethod
  def _domain_as_dataset (domain, manifest):
    from pygeode.dataset import Dataset
    varlist = domain.get_axis(Varlist)
    assert varlist is not None, "Unable to determine variable names"
    axes = filter(None,domain.without_axis(Varlist).axes)
    return Dataset([DataVar.construct(name, axes, manifest) for name in varlist])

  #TODO

  # Get the requested variable(s).
  # The possible matches are returned one at a time, and the calling method
  # will have to figure out which one is the best.
  def find (self, *vars):

    for dataset in self.datasets:
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
      candidates = zip(self.find(*fields))
    else:
      candidates = list(self.find(*fields))

    if requirement is not None:
      candidates = filter(requirement, candidates)

    # Sort by the criteria (higher value is better)
    if maximize is not None:
      candidates = sorted(candidates, key=maximize, reverse=True)
    elif minimize is not None:
      candidates = sorted(candidates, key=minimize, reverse=False)

    if len(candidates) == 0:
      raise KeyError("Unable to find any matches for fields=%s, requirement=%s, maximize=%s, minimize=%s"%(fields, requirement, maximize, minimize))

    # Use the best result
    result = candidates[0]

    if collapse_result: result = result[0]
    return result


# Wrap a variable from a domain into a Var object
from pygeode.var import Var
class DataVar(Var):
  @classmethod
  def construct (cls, varname, axes, manifest):
    import numpy as np
    from pygeode.tools import common_dict

    # For all axes in the manifest, get their values as sets
    # (for faster checking of regions in getview)
    axis_values = {}

    atts = []
    table = []
    # Scan through the manifest, collect a table of available axes.
    for filename, (opener, entries) in manifest.iteritems():
      for _varname, _axes, _atts in entries:
        if _varname == varname:
          atts.append(_atts)
          table.append((filename, opener, _axes))
          for _axis in _axes:
            if id(_axis) not in axis_values:
              axis_values[id(_axis)] = frozenset(_axis.values)
    # Get subset of attributes that are consistent among all sources of data
    atts = common_dict(atts)
    # Reduce the axes to only those that the variable actually has
    axis_types = set(type(a) for f,o,_axes in table for a in _axes)
    axes = [a for a in axes if type(a) in axis_types]

    obj = cls(axes, name=varname, dtype=float, atts=atts)
    obj._table = table
    obj._axis_values = axis_values
    obj._varname = varname  # In case the object gets renamed.
    return obj

  def getview (self, view, pbar):
    import numpy as np
    from pygeode.view import View
    out = np.zeros(view.shape, dtype=self.dtype)
    out[()] = float('nan')
    clipped_view = view.clip()
    axis_values = [frozenset(a.values) for a in clipped_view.axes]
    lookup = {}  # Memoize the set intersections
    # Loop over all available files.
    for filename, opener, axes in self._table:
      # Check if there's any overlap between what we want and what's in the file
      overlap = True
      for a1, a2, v2 in zip(axes, clipped_view.axes, axis_values):
        assert type(a1) == type(a2), "Internal error"
        v1 = self._axis_values[id(a1)]
        if v1 not in lookup:
          lookup[v1] = len(v1 & v2)
        if lookup[v1] == 0: overlap = False
      if not overlap: continue
      var = [v for v in opener(filename) if v.name == self._varname][0]
      v = view.map_to(axes)
      chunk = v.get(var)
      outsl = v.map_to(clipped_view).slices
      # Note: this may break if there is more than one axis with integer indices.
      assert len([sl for sl in outsl if isinstance(sl,tuple)]) <= 1, "Unhandled advanced indexing case."
      out[outsl] = chunk

    return out

del Var



def my_opener(filename):
  from pygeode.formats import fstd
  return fstd.open(filename, raw_list=True)

if __name__ == '__main__':
  from glob import glob
  data = DataInterface.from_files(glob("/wrk6/neish/mn083/model/2009*"), opener=my_opener, manifest="/wrk6/neish/mn083/model/nc_cache/mn083_manifest")
  for dataset in data.datasets:
    print dataset
    if 'CO2' in dataset and len(dataset.forecast) > 1:
      print dataset.CO2(i_time=0,lat=10).mean()
  print len(data.datasets)
