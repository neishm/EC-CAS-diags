# Helper method(s) for scanning through data files, constructing a table of
# contents, and sorting them into logical collections.

# Current version of the manifest file format.
# If this version doesn't match the existing manifest file, then the manifest
# is re-generated.
MANIFEST_VERSION="2"

# Scan through all the given files, produce a manifest of all data available.
def scan_files (files, interface, manifest=None):
  from os.path import exists, getatime, getmtime, normpath
  from os import utime
  import gzip
  import cPickle as pickle
  from pygeode.progress import PBar

  # Special case: no files given
  if len(files) == 0: return dict()

  # Strip out extra separators, etc. from the filenames.
  # Otherwise, if the files are scanned a second time with different
  # separators, it may cause the same file to be included more than once.
  files = [normpath(f) for f in files]


  # If an old manifest already exists, start with that.
  if manifest is not None and exists(manifest):
    with gzip.open(manifest,'r') as f:
      version = pickle.load(f)
      table = f.read()
      try:
        table = pickle.loads(table)
      except (ImportError, AttributeError, EOFError):
        version = None  # Unable to read the symbols, so treat this as an
                        # incompatible version
    mtime = getmtime(manifest)
  if manifest is None or not exists(manifest) or version != MANIFEST_VERSION:
    table = {}
    mtime = 0

  # Re-use axis objects wherever possible.
  axis_manager = AxisManager()
  for filename, (_interface,entries) in table.iteritems():
    for varname, axes, atts in entries:
      axis_manager.register_axes(axes)

  if manifest is not None:
    pbar = PBar (message = "Generating %s"%manifest)
  else:
    pbar = PBar (message = "Scanning files")

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
    table[f] = interface, entries
    for var in interface.open_file(f):

      axes = axis_manager.lookup_axes(var.axes)
      entries.append((var.name, axes, var.atts))

    modified_table = True


  if modified_table and manifest is not None:
    with gzip.open(manifest,'w') as f:
      pickle.dump(MANIFEST_VERSION, f)
      blob = pickle.dumps(table)
      f.write(blob)
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
  name = 'varlist'
  def __init__ (self, varnames):
    self.values = tuple(varnames)
  def __iter__ (self):  return iter(self.values)
  def __len__ (self): return len(self.values)
  def __repr__ (self): return "<%s>"%self.__class__.__name__
  def __cmp__ (self, other): return cmp(self.values, other.values)


# An interface for axis-manipulation methods.
# These methods are tied to a common object, which allows the re-use of
# previous values.
class AxisManager (object):
  def __init__ (self, axes=[]):
    self._hash_bins = {}  # Bin axis objects by hash value
    self._id_lookup = {}  # Reverse-lookup of an axis by id
    self._all_axes = []   # List of encountered axes (so the ids don't get
                          # recycled)
    # For flattening / unflattening axes
    self._flattened_axes = {}
    self._unflattened_axes = {}

    # For axes that are flattened and subsequently converted to a set
    self._settified_axes = {}
    self._unsettified_axes = {}

    # For union / intersection of axes
    self._unions = {}
    self._intersections = {}

    self.register_axes (axes)

  # Helper function: recycle an existing axis object if possible.
  # This allows axes to be compared by their ids, and makes pickling them
  # more space-efficient.
  def lookup_axis (self, axis):
    # Check if we've already looked at this exact object.
    axis_id = id(axis)
    if axis_id in self._id_lookup: return self._id_lookup[axis_id]
    # Store a reference to this axis, so the object id doesn't get recycled.
    self._all_axes.append(axis)
    values = tuple(axis.values)
    # Get a hash value that will be equal among axes that are equivalent
    axis_hash = hash((axis.name,type(axis),values))
    # Get all axes that have this hash (most likely, only 1 match (or none))
    hash_bin = self._hash_bins.setdefault(axis_hash,[])
    # Find one that is truly equivalent, otherwise add this new one to the cache.
    try:
      axis = hash_bin[hash_bin.index(axis)]
    except ValueError:
      hash_bin.append(axis)
    # Record this object id, in case we're passed it in again.
    self._id_lookup[axis_id] = axis

    return axis

  # Register an axis in this object (so we're aware of it for future reference)
  def register_axis (self, axis):
    self.lookup_axis (axis)

  # Look up multiple axes at a time, return as a tuple
  def lookup_axes (self, axes):
    return tuple(map(self.lookup_axis, axes))

  # Register multiple axes at a time
  def register_axes (self, axes):
    self.lookup_axes (axes)

  # Convert an axis to tuples of values and auxiliary arrays
  def flatten_axis (self, axis):
    axis = self.lookup_axis(axis)
    axis_id = id(axis)
    if axis_id in self._flattened_axes:
      return self._flattened_axes[axis_id]

    if isinstance(axis,Varlist):
      auxarrays = []
    else:
      auxarrays = [[(name,v) for v in axis.auxarrays[name]] for name in sorted(axis.auxarrays.keys())]
    assert all(len(aux) == len(axis.values) for aux in auxarrays)
    flat = tuple(zip(axis.values, *auxarrays))
    self._flattened_axes[axis_id] = flat
    self._unflattened_axes.setdefault(type(axis),dict())[flat] = axis
    return flat

  # Convert an axis to unordered set of tuples
  def settify_axis (self, axis):
    axis = self.lookup_axis(axis)
    axis_id = id(axis)
    if axis_id in self._settified_axes:
      return self._settified_axes[axis_id]

    out = frozenset(self.flatten_axis (axis))
    self._settified_axes[axis_id] = out
    self._unsettified_axes.setdefault(type(axis),dict())[out] = axis
    return out


  # Convert some flattened coordinates back into an axis
  def unflatten_axis (self, sample, values):
    import numpy as np
    values = tuple(sorted(values))
    # Check if we can already get one
    key = values
    axis = self._unflattened_axes.setdefault(type(sample),dict()).get(key,None)
    if axis is not None: return axis
    x = zip(*values)
    # Special case: empty axis
    if len(x) == 0:
      values = []
    else:
      values = x[0]
    auxarrays = {}
    for aux in x[1:]:
      name, arr = zip(*aux)
      auxarrays[name[0]] = np.array(arr)
    if isinstance(sample,Varlist):
      axis = Varlist(values)
    else:
      axis = sample.withnewvalues(values)
      # Only update the auxarrays if we have something to put
      # For empty axes, we don't want to erase the (empty) auxarrays already
      # created e.g. for the time axis.
      if len(auxarrays) > 0: axis.auxarrays = auxarrays

    axis = self.lookup_axis(axis)
    self._unflattened_axes[type(sample)][key] = axis
    return axis

  # Convert some settified coordinates back into an axis
  #TODO: store reverse _settified_axes as well?
  # (and do same with unflatten_axis()?)
  def unsettify_axis (self, sample, values):
    # Check if we can already get one
    key = values
    axis = self._unsettified_axes.setdefault(type(sample),dict()).get(key,None)
    if axis is not None: return axis

    axis = self.unflatten_axis(sample, values)

    self._unsettified_axes[type(sample)][key] = axis
    return axis

  # Merge axes together
  def get_axis_union (self, axes):
    key = tuple(sorted(map(id,axes)))
    if key in self._unions: return self._unions[key]
    values = map(self.settify_axis, axes)
    values = reduce(frozenset.union, values, frozenset())
    union = self.unsettify_axis (axes[0], values)
    self._unions[key] = union
    return union

  # Find common values between axes
  def get_axis_intersection (self, axes):
    key = tuple(sorted(map(id,axes)))
    if key in self._intersections: return self._intersections[key]
    values = map(self.settify_axis, axes)
    values = reduce(frozenset.intersection, values, values[0])
    intersection = self.unsettify_axis (axes[0], values)
    self._intersections[key] = intersection
    return intersection


# A domain (essentially a tuple of axes, with no deep comparisons)
class Domain (object):
  def __init__ (self, axes):
    self.axes = tuple(axes)
    # A unique representation of the domain.
    # Assumes there is only one object id for each possible axis object,
    # to save time in comparisons.
    self._id = tuple(map(id,self.axes))
  def __cmp__ (self, other):
    return cmp(self._id, other._id)
  def __hash__ (self):
    return hash(self._id)
  def __iter__ (self):
    return iter(self.axes)
  def __repr__ (self):
#    return "("+",".join("%s:%s"%(a.__class__.__name__,len(a)) for a in self.axes)+")"
    return "("+",".join(map(str,map(len,filter(None,self.axes))))+")"
  # Mask out an axis (convert it to a 'None' placeholder)
  def without_axis (self, axis_name):
    return Domain([None if a.name == axis_name else a for a in self.axes])
  # Unmask an axis type (re-insert an axis object where the 'None' placeholder was
  def with_axis (self, axis):
    return Domain([axis if a is None else a for a in self.axes])
  # Return the axis of the given name.
  # Returns None if no such axis name is found.
  def get_axis (self, axis_name):
    for axis in self.axes:
      if axis.name == axis_name: return axis
    return None




# Helper method - return all names of axes in a set of domains
def _get_axis_names (domains):
  names = set()
  for domain in domains:
    for axis in domain:
      names.add(axis.name)
  return names

# Helper method - aggregate along a particular axis
# Inputs:
#   domains: the set of original domains.
#   axis_name: the name of axis to aggregate the domains over.
# Input/Output:
#   used_domains: set of original domains that are covered by the output
#                 (i.e., ones that could be safely removed later).
#                 These are appended to an existing set passed in.
# Output: the domains that could be aggregated along to given axis.
#         Domains without that axis type are ignored.
def _aggregate_along_axis (domains, axis_name, used_domains, axis_manager):
  bins = {}
  touched_domains = set()
  for domain in domains:
    axis = domain.get_axis(axis_name)
    if axis is not None:
      touched_domains.add(domain)
      domain_group = domain.without_axis(axis_name)
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
      new_axis = axis_manager.get_axis_union (axis_bin.values())
      output.add(domain_group.with_axis(new_axis))

  if used_domains is not None:
    # Only consider a domain to be "used" if it was aggregated into a bigger
    # domain, *not* if it was directly copied to the output.
    used_domains.update(touched_domains - output)
  return domains | output


# Find a minimal set of domains that cover all available data
def _get_prime_domains (domains, axis_manager):
  axis_names = _get_axis_names(domains)
  # This may be an iterative process, that may need to be repeated.
  while True:
    used_domains = set()
    # Aggregate along one axis at a time.
    for axis_name in axis_names:
      domains = _aggregate_along_axis(domains, axis_name, used_domains, axis_manager)
    if len(used_domains) == 0: break  # Nothing aggregated
    domains -= used_domains  # Remove smaller pieces that are aggregated.

  return domains

# Try merging multiple domains together.
# For each pair of domains, look for an axis over which they could be
# concatenated.  All other axes will be intersected between domains.
def _merge_domains (d1, d2, axis_manager):
  domains = set()
  axis_names = _get_axis_names([d1,d2])
  # We need at least one of the two domains to contain all the types
  # (so we have a deterministic ordering of axes).
  # Make the first domain the one with all axes.
  #TODO: Check the relative order of the axes as well?
  if _get_axis_names([d1]) == axis_names:
    pass  # Already done
  elif _get_axis_names([d2]) == axis_names:
    d1, d2 = d2, d1  # Swap
  else:
    return set()  # Nothing can be done

  # Early termination if 2 or more axes are non-intersectable
  non_intersectable = 0
  for axis_name in axis_names:
    a1 = d1.get_axis(axis_name)
    a2 = d2.get_axis(axis_name)
    if a1 is None or a2 is None: continue
    a1 = axis_manager.settify_axis(a1)
    a2 = axis_manager.settify_axis(a2)
    if len(a1 & a2) == 0:
      non_intersectable += 1
  if non_intersectable > 1:
    return set()  # We will alway have an empty domain after a merge
                  # over any single axis.


  # Give the domains the same axes (broadcasting to extra axes)
  d2 = Domain([d2.get_axis(a.name) or a for a in d1.axes])
  for merge_axis_name in axis_names:
    m1 = d1.get_axis(merge_axis_name)
    m2 = d2.get_axis(merge_axis_name)
    merge_axis = axis_manager.get_axis_union([m1,m2])
    # Skip if we aren't actually getting a bigger axis.
    if merge_axis is m1 or merge_axis is m2: continue
    axes = [merge_axis if a1.name == merge_axis_name else axis_manager.get_axis_intersection([a1,a2]) for a1, a2 in zip(d1,d2)]
    # Skip if we don't have any overlap
    if any(len(a) == 0 for a in axes): continue
    domains.add(Domain(axes))

  return domains

def _merge_all_domains (domains, axis_manager):
  merged_domains = set(domains)
  while True:
    new_merged_domains = set()
    for d1 in domains:
      for d2 in merged_domains:
        new_merged_domains.update(_merge_domains(d1,d2,axis_manager))
    new_merged_domains -= merged_domains
    if len(new_merged_domains) == 0: break  # Nothing new added
    merged_domains.update(new_merged_domains)

  return domains | merged_domains

# Remove any domains that are proper subsets of other domains
# (Clean up anything that is not needed).
def _cleanup_subdomains (domains):
  junk_domains = set()
  for d1 in domains:
    for d2 in domains:
      if d1 is d2: continue
      assert d1 != d2
      if _get_axis_names([d1]) != _get_axis_names([d2]): continue
      axis_names = _get_axis_names([d2])
      values1 = [d1.get_axis(a).values for a in axis_names]
      values2 = [d2.get_axis(a).values for a in axis_names]
      if all(set(v1) <= set(v2) for v1, v2 in zip(values1,values2)):
        junk_domains.add(d1)
  return domains - junk_domains

# Scan a file manifest, return all possible domains available.
def _get_domains (manifest, force_common_axis):

  axis_manager = AxisManager()  # For memoized axis operations

  # Start by adding all domain pieces to the list
  domains = set()
  for interface, entries in manifest.itervalues():
    for var, axes, atts in entries:
      axes = axis_manager.lookup_axes([Varlist([var])]+list(axes))
      domains.add(Domain(axes))

  # For each common axis that's specified, build it from the pieces in the
  # domains.
  if len(force_common_axis) > 0:
    common_axes = {}
    for axis in force_common_axis:
      common_axes[axis] = axis_manager.get_axis_union([a for d in domains for a in d if a.name == axis])
    domains = set(Domain([common_axes.get(a.name,a) for a in d.axes]) for d in domains)

  # Reduce this to a minimal number of domains for data coverage
  domains = _get_prime_domains(domains, axis_manager)
  domains = _merge_all_domains(domains, axis_manager)
  domains = _cleanup_subdomains(domains)
  return domains


# Create a dataset from a set of files and an interface class
def from_files (filelist, interface, manifest=None, force_common_axis=()):
  manifest = scan_files (filelist, interface, manifest)
  domains = _get_domains(manifest, force_common_axis=force_common_axis)
  datasets = [_domain_as_dataset(d,manifest) for d in domains]
  return datasets

# Wrap a domain as a dataset.
# Requires the original file manifest, to determine where to get the data.
def _domain_as_dataset (domain, manifest):
  from pygeode.dataset import Dataset
  varlist = domain.get_axis('varlist')
  assert varlist is not None, "Unable to determine variable names"
  axes = filter(None,domain.without_axis('varlist').axes)
  return Dataset([DataVar.construct(name, axes, manifest) for name in varlist])


# Override Pygeode's common_dict implementation with our own
# (more optimized)
def common_dict (dicts):
  from collections import Counter
  items= set.union(*[set(d.iteritems()) for d in dicts])
  count = Counter(k for k,v in items)
  return dict([k,v] for k,v in items if count[k] == 1)


# Wrap a variable from a domain into a Var object
from pygeode.var import Var
class DataVar(Var):
  @classmethod
  def construct (cls, varname, axes, manifest):

    # Use an axis manager for accelerating axis operations.
    axis_manager = AxisManager()

    atts = []
    table = []
    # Scan through the manifest, collect a table of available axes.
    for filename, (interface, entries) in manifest.iteritems():
      for _varname, _axes, _atts in entries:
        if _varname == varname:
          atts.append(_atts)
          table.append((filename, interface, _axes))
          axis_manager.register_axes(_axes)
    # Get subset of attributes that are consistent among all sources of data
    atts = common_dict(atts)
    # Reduce the axes to only those that the variable actually has
    axis_types = set(type(a) for f,o,_axes in table for a in _axes)
    axes = [a for a in axes if type(a) in axis_types]
    axis_manager.register_axes(axes)

    obj = cls(axes, name=varname, dtype=float, atts=atts)
    obj._table = table
    obj._axis_manager = axis_manager
    obj._varname = varname  # In case the object gets renamed.

    #TODO: handle unsorted axes, using an extra argsort step?
    import numpy as np
    for a in obj.axes:
      assert np.all(a.values == np.sort(a.values)), "Unhandled case"

    return obj

  def getview (self, view, pbar):
    import numpy as np
    from pygeode.view import View, simplify
    out = np.zeros(view.shape, dtype=self.dtype)
    out[()] = float('nan')
    out_axes = view.clip().axes
    # Loop over all available files.
    for filename, interface, axes in self._table:
      subaxes = [self._axis_manager.get_axis_intersection([a1,a2]) for a1,a2 in zip(out_axes,axes)]
      outsl = [slice(None)]*len(subaxes)
      if any(len(a)==0 for a in subaxes): continue
      for i,(a1,a2) in enumerate(zip(out_axes,subaxes)):
        if len(a2) < len(a1):
          outsl[i] = simplify(np.searchsorted(a1.values, a2.values))
      var = [v for v in interface.open_file(filename) if v.name == self._varname][0]
      v = View(subaxes)
      chunk = v.get(var)
      # Note: this may break if there is more than one axis with integer indices.
      assert len([sl for sl in outsl if isinstance(sl,tuple)]) <= 1, "Unhandled advanced indexing case."
      out[outsl] = chunk

    return out

del Var

