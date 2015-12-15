# Helper method(s) for scanning through data files, constructing a table of
# contents, and sorting them into logical collections.

# Current version of the manifest file format.
# If this version doesn't match the existing manifest file, then the manifest
# is re-generated.
MANIFEST_VERSION="2"

# Scan through all the given files, produce a manifest of all data available.
def scan_files (files, interface, manifest=None, axis_manager=None):
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
  # Use a global axis manager if available, otherwise use a local one here.
  if axis_manager is None:
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
  _memoized = dict()
  @classmethod
  def singlevar (cls, varname):
    var = cls._memoized.get(varname,None)
    if var is None:
      var = cls._memoized[varname] = cls([varname])
    return var


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

    self.register_axes (axes)

  # Helper function: recycle an existing axis object if possible.
  # This allows axes to be compared by their ids, and makes pickling them
  # more space-efficient.
  def lookup_axis (self, axis):
    # Check if we've already looked at this exact object.
    axis_id = id(axis)
    entry = self._id_lookup.get(axis_id,None)
    if entry is not None: return entry
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
    entry = self._flattened_axes.get(axis_id,None)
    if entry is not None: return entry

    if isinstance(axis,Varlist):
      auxarrays = []
    else:
      auxarrays = [[(name,v) for v in axis.auxarrays[name]] for name in sorted(axis.auxarrays.keys())]
    assert all(len(aux) == len(axis.values) for aux in auxarrays)
    flat = tuple(zip(axis.values, *auxarrays))
    self._flattened_axes[axis_id] = flat
# disabled this - otherwise we get the original (unsorted) axis where we may
# expect a sorted axis. (e.g. in DataVar)
#    self._unflattened_axes.setdefault(type(axis),dict())[flat] = axis
    return flat

  # Convert an axis to unordered set of tuples
  def settify_axis (self, axis):
    axis = self.lookup_axis(axis)
    axis_id = id(axis)
    entry = self._settified_axes.get(axis_id,None)
    if entry is not None: return entry

    out = frozenset(self.flatten_axis (axis))
    self._settified_axes[axis_id] = out
# disabled this - otherwise we get the original (unsorted) axis where we may
# expect a sorted axis. (e.g. in DataVar)
#    self._unsettified_axes.setdefault(type(axis),dict())[out] = axis
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



# A domain (essentially a tuple of axes, with no deep comparisons)
class Domain (object):
  def __init__ (self, axis_samples, axis_values):
    # Sample axis objects, for reconstructing axes of these types.
    # (may not contain the actual data that will be reconstructed).
    self.axis_samples = tuple(axis_samples)
    self.axis_names = tuple([a.name for a in axis_samples])
    # Store the axis values as sets, to make unions/intersections faster.
    self.axis_values = tuple(axis_values)
  def __cmp__ (self, other):
    key1 = (self.axis_names, self.axis_values)
    key2 = (other.axis_names, other.axis_values)
    return cmp(key1, key2)
  def __hash__ (self):
    return hash(self.axis_values)
  def __repr__ (self):
    return "("+",".join(map(str,map(len,filter(None,self.axis_values))))+")"
  # Mask out an axis (convert it to a 'None' placeholder)
  def which_axis (self, iaxis):
    if isinstance(iaxis,int): return iaxis
    assert isinstance(iaxis,str)
    if iaxis in self.axis_names:
      return self.axis_names.index(iaxis)
    return None
  def without_axis (self, iaxis):
    axis_values = list(self.axis_values)
    axis_values[self.which_axis(iaxis)] = None
    axis_values = tuple(axis_values)
    return type(self)(self.axis_samples, axis_values)
  # Unmask an axis type (re-insert an axis object where the 'None' placeholder was
  def with_axis (self, iaxis, values):
    assert isinstance(values,frozenset)
    axis_values = list(self.axis_values)
    axis_values[self.which_axis(iaxis)] = values
    axis_values = tuple(axis_values)
    return type(self)(self.axis_samples, axis_values)
  # Reconstructs the axes from the samples and values. 
  def make_axes (self, axis_manager):
    return [axis_manager.unsettify_axis(s,v) for (s,v) in zip(self.axis_samples, self.axis_values)]
  # Determine if the given axis is in this domain (given its name)
  def has_axis (self, axis_name):
    return axis_name in self.axis_names
  # Return the (unordered) values of a particular axis.
  def get_axis_values (self, iaxis):
    return self.axis_values[self.which_axis(iaxis)]




# Helper method - return all names of axes in a set of domains
# Returned in approximate order that they're found in the domains.
def _get_axis_names (domains):
  ordered_names = set()
  for domain in domains:
    ordered_names.update(enumerate(domain.axis_names))
  names = []
  for i,name in sorted(ordered_names,reverse=True):
    if name not in names:
      names.append(name)
  names = list(reversed(names))
  # Special case: time axis should be handled first (makes aggregating faster)
  if 'time' in names:
    names.remove('time')
    names = ['time'] + names
  return tuple(names)


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
def _aggregate_along_axis (domains, axis_name):
  output = set()
  bins = {}
  for domain in domains:
    iaxis = domain.which_axis(axis_name)
    if iaxis is None:
      output.add(domain)
      continue
    domain_group = domain.without_axis(iaxis)
    axis_bin = bins.setdefault(domain_group,set())
    axis_bin.add(domain.axis_values[iaxis])
  # For each domain group, aggregate the axes together
  # NOTE: assumes that all the axis segments are consistent
  # (same origin, units, etc.)
  # Also, assumes the axis values should be monotonically increasing.
  for domain_group, axis_bin in bins.iteritems():
    if len(axis_bin) == 1:  # Only one axis piece (nothing to aggregate)
      axis_values = axis_bin.pop()
    # Otherwise, need to aggregate pieces together.
    else:
      axis_values = frozenset.union(*axis_bin)
    output.add(domain_group.with_axis(axis_name,axis_values))

  return output


# Find a minimal set of domains that cover all available data
def _get_prime_domains (domains):
  axis_names = _get_axis_names(domains)
  # Aggregate along one axis at a time.
  for axis_name in axis_names:
    domains = _aggregate_along_axis(domains, axis_name)

  return domains

# Try merging multiple domains together.
# For each pair of domains, look for an axis over which they could be
# concatenated.  All other axes will be intersected between domains.
def _merge_domains (d1, d2):
  from copy import copy
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
  del axis_names

  # Pre-compute union and intersection of the axes.
  # Determine which axes may be useful to merge over.
  # Early termination if 2 or more axes are non-intersectable
  intersections = []
  unions = []
  merge_axes = []
  non_intersectable = 0
  for iaxis,v1 in enumerate(d1.axis_values):
    axis_name = d1.axis_samples[iaxis].name
    if d2.has_axis(axis_name):
      v2 = d2.get_axis_values(axis_name)
    else:
      v2 = v1
    if v1 is v2:
      intersection = v1
      union = v2
    else:
      intersection = v1 & v2
      union = v1 | v2
    # Would we get anything useful from merging this axis?
    # (note: other conditions would need to be met as well)
    if len(union) > len(v1) and len(union) > len(v2):
      merge_axes.append(iaxis)
    # Check for non-overlapping axes (can have up to 1 such dimension).
    if len(intersection) == 0:
      non_intersectable += 1
    # Store the union / intersection for use later.
    intersections.append(intersection)
    unions.append(union)
  if non_intersectable > 1:
    return set()  # We will alway have an empty domain after a merge
                  # where multiple dimensions have no overlap.


  # Test each axis to see if it can be a merge axis
  # (if the other axes have non-zero intersection).
  for iaxis in merge_axes:
    axis_values = list(intersections)
    axis_values[iaxis] = unions[iaxis]
    # Skip if we don't have any overlap
    if any(len(v) == 0 for v in axis_values): continue
    domain = copy(d1)
    domain.axis_values = tuple(axis_values)
    domains.add(domain)

  return domains

def _merge_all_domains (domains):
  merged_domains = set(domains)
  while True:
    new_merged_domains = set()
    for d1 in domains:
      for d2 in merged_domains:
        if d1 is d2: continue
        new_merged_domains.update(_merge_domains(d1,d2))
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
      values1 = [d1.get_axis_values(a) for a in axis_names]
      values2 = [d2.get_axis_values(a) for a in axis_names]
      if all(v1 <= v2 for v1, v2 in zip(values1,values2)):
        junk_domains.add(d1)
  return domains - junk_domains


# Get a common axis
# Note: assume the values are all intercomparable.
def _get_common_axis (manifest, axis_name):
  import numpy as np
  sample = None
  values = []
  for interface, entries in manifest.itervalues():
    for var, axes, atts in entries:
      for axis in axes:
        if axis.name != axis_name: continue
        if sample is None: sample = axis
        values.append(axis.values)
  values = np.concatenate(values)
  values = np.unique(values)
  return sample.withnewvalues(values)

# Scan a file manifest, return all possible domains available.
def _get_domains (manifest, axis_manager, force_common_axis=None):

  # Fetch a common axis?
  if force_common_axis is not None:
    common_axis = _get_common_axis(manifest, axis_name=force_common_axis)

  # Start by adding all domain pieces to the list
  domains = set()
  for interface, entries in manifest.itervalues():
    for var, axes, atts in entries:
      # Apply the common axis?
      axes = tuple(common_axis if a.name == force_common_axis else a for a in axes)
      # Map each entry to a domain.
      axes = (Varlist.singlevar(var),)+axes
      axis_values = map(axis_manager.settify_axis, axes)
      domains.add(Domain(axis_samples=axes, axis_values=axis_values))

  # Reduce this to a minimal number of domains for data coverage
  domains = _get_prime_domains(domains)
  domains = _merge_all_domains(domains)
  domains = _cleanup_subdomains(domains)
  return domains


# Extract variable attributes and table of files from the given manifest.
def get_var_info(manifest):
  from pygeode.tools import common_dict
  atts = dict()
  table = dict()
  for filename, (interface, entries) in manifest.iteritems():
    for _varname, _axes, _atts in entries:
      _attslist = atts.setdefault(_varname,[])
      if atts not in _attslist: _attslist.append(atts)
      table.setdefault(_varname,[]).append((filename, interface, _axes))
  atts = dict((_varname,common_dict(_attslist)) for (_varname,_attslist) in atts.iteritems())
  return atts, table

# Create a dataset from a set of files and an interface class
def from_files (filelist, interface, manifest=None, force_common_axis=None):
  axis_manager = AxisManager()
  manifest = scan_files (filelist, interface, manifest, axis_manager)
  domains = _get_domains(manifest, axis_manager, force_common_axis=force_common_axis)
  atts, table = get_var_info(manifest)
  datasets = [_domain_as_dataset(d,atts,table,axis_manager) for d in domains]
  return datasets

# Wrap a domain as a dataset.
def _domain_as_dataset (domain, atts, table, axis_manager):
  from pygeode.dataset import Dataset
  axes = domain.make_axes(axis_manager)
  ivarlist = domain.which_axis('varlist')
  assert ivarlist is not None, "Unable to determine variable names"
  varlist = axes[ivarlist]
  axes = axes[:ivarlist] + axes[ivarlist+1:]
  return Dataset([DataVar.construct(name, axes, atts[name], table[name], axis_manager) for name in varlist])



# Wrap a variable from a domain into a Var object
from pygeode.var import Var
class DataVar(Var):
  @classmethod
  def construct (cls, varname, axes, atts, table, axis_manager):

    # Reduce the axes to only those that the variable actually has
    axis_names = set(a.name for f,o,_axes in table for a in _axes)
    axes = [a for a in axes if a.name in axis_names]
    axis_manager.register_axes(axes)

    obj = cls(axes, name=varname, dtype=float, atts=atts)
    obj._table = table
    obj._axis_manager = axis_manager
    obj._varname = varname  # In case the object gets renamed.

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
      reorder = []
      mask = []
      if any(len(a)==0 for a in subaxes): continue
      for a1,a2 in zip(out_axes,subaxes):
        # Figure out where the input chunk fits into the output
        re = np.searchsorted(a2.values, a1.values)
        # Mask out elements that we don't actually have in the chunk
        m = [r<len(a2.values) and a2.values[r]==v for r,v in zip(re,a1.values)]
        m = np.array(m)
        # Convert mask to integer indices
        m = np.arange(len(m))[m]
        # and then to a slice (where possible)
        m = simplify(m)
        re = re[m]
        # Try to simplify the re-ordering array
        if np.all(re == np.sort(re)):
          re = simplify(re)
        reorder.append(re)
        mask.append(m)
      var = [v for v in interface.open_file(filename) if v.name == self._varname][0]
      v = View(subaxes)
      chunk = v.get(var)
      # Note: this may break if there is more than one axis with integer indices.
      assert len([r for r in reorder if isinstance(r,(tuple,np.ndarray))]) <= 1, "Unhandled advanced indexing case."
      assert len([m for m in mask if isinstance(m,(tuple,np.ndarray))]) <= 1, "Unhandled advanced indexing case."
      out[mask] = chunk[reorder]

    return out

del Var

