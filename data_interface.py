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
      map(get_axis,axes)

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

      axes = tuple(get_axis(a) for a in var.axes)
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

  return table

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
def get_axis (axis, _hash_bins={}, _ids=[]):
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

# Helper function: produce a new axis of the given type
def create_axis (sample, values):
  if isinstance(sample,Varlist):
    axis = Varlist(sorted(values))
  else:
    axis = sample.withnewvalues(sorted(values))
  return get_axis(axis)


# Merge axes together
def get_axis_union (axes):
  values = [axis.values for axis in axes]
  values = reduce(set.union, values, set())
  return create_axis (axes[0], values)

# Find common values between axes
def get_axis_intersection (axes):
  values = [axis.values for axis in axes]
  values = reduce(set.intersection, values, set(values[0]))
  return create_axis (axes[0], values)


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
    return Domain([None if isinstance(a,axis_type) else a for a in self.axes])
  # Unmask an axis type (re-insert an axis object where the 'None' placeholder was
  def with_axis (self, axis):
    return Domain([axis if a is None else a for a in self.axes])
  # Return the axis of the given type.
  # Returns None if no such axis type is found.
  def get_axis (self, axis_type):
    for axis in self.axes:
      if isinstance(axis,axis_type): return axis
    return None


# Helper method - return all types of axes in a set of domains
def get_axis_types (domains):
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
def aggregate_along_axis (domains, axis_type, used_domains=None):
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
      new_axis = get_axis_union (axis_bin.values())
      output.add(domain_group.with_axis(new_axis))

  if used_domains is not None:
    # Only consider a domain to be "used" if it was aggregated into a bigger
    # domain, *not* if it was directly copied to the output.
    used_domains.update(touched_domains - output)
  return domains | output


# Find a minimal set of domains that cover all available data
def get_prime_domains (domains):
  axis_types = get_axis_types(domains)
  # This may be an iterative process, that may need to be repeated.
  while True:
    used_domains = set()
    # Aggregate along one axis at a time.
    for axis_type in axis_types:
      domains = aggregate_along_axis(domains, axis_type, used_domains)
    if len(used_domains) == 0: break  # Nothing aggregated
    domains -= used_domains  # Remove smaller pieces that are aggregated.

  return domains

# Try merging multiple domains together.
# For each pair of domains, look for an axis over which they could be
# concatenated.  All other axes will be intersected between domains.
def merge_domains (d1, d2):
  domains = set()
  axis_types = get_axis_types([d1,d2])
  # We need at least one of the two domains to contain all the types
  # (so we have a deterministic ordering of axes).
  # Make the first domain the one with all axes.
  #TODO: Check the relative order of the axes as well?
  if get_axis_types([d1]) == axis_types:
    pass  # Already done
  elif get_axis_types([d2]) == axis_types:
    d1, d2 = d2, d1  # Swap
  else:
    return set()  # Nothing can be done
  # Give the domains the same axes (broadcasting to extra axes)
  d2 = Domain([d2.get_axis(type(a)) or a for a in d1.axes])
  for merge_axis_type in axis_types:
    m1 = d1.get_axis(merge_axis_type)
    m2 = d2.get_axis(merge_axis_type)
    merge_axis = get_axis_union([m1,m2])
    # Skip if we aren't actually getting a bigger axis.
    if merge_axis is m1 or merge_axis is m2: continue
    axes = [merge_axis if isinstance(a1,merge_axis_type) else get_axis_intersection([a1,a2]) for a1, a2 in zip(d1,d2)]
    # Skip if we don't have any overlap
    if any(len(a) == 0 for a in axes): continue
    domains.add(Domain(axes))

  return domains

def merge_all_domains (domains):
  merged_domains = set(domains)
  while True:
    new_merged_domains = set()
    for d1 in domains:
      for d2 in merged_domains:
        new_merged_domains.update(merge_domains(d1,d2))
    new_merged_domains -= merged_domains
    if len(new_merged_domains) == 0: break  # Nothing new added
    merged_domains.update(new_merged_domains)

  return domains | merged_domains

# Remove any domains that are proper subsets of other domains
# (Clean up anything that is not needed).
def cleanup_subdomains (domains):
  junk_domains = set()
  for d1 in domains:
    for d2 in domains:
      if d1 is d2: continue
      assert d1 != d2
      if get_axis_types([d1]) != get_axis_types([d2]): continue
      axis_types = get_axis_types([d2])
      values1 = [d1.get_axis(a).values for a in axis_types]
      values2 = [d2.get_axis(a).values for a in axis_types]
      if all(set(v1) <= set(v2) for v1, v2 in zip(values1,values2)):
        junk_domains.add(d1)
  return domains - junk_domains

# Scan a file manifest, return all possible domains available.
def get_domains (manifest):

  # Start by adding all domain pieces to the list
  domains = set()
  for opener, entries in manifest.itervalues():
    for var, axes, atts in entries:
      domains.add(Domain([Varlist([var])]+list(axes)))

  # Reduce this to a minimal number of domains for data coverage
  domains = get_prime_domains(domains)
  domains = merge_all_domains(domains)
  domains = cleanup_subdomains(domains)
  return domains

# Wrap a variable from a domain into a Var object
from pygeode.var import Var
class DataVar(Var):
  @classmethod
  def construct (cls, varname, axes, manifest):
    import numpy as np
    from pygeode.tools import common_dict

    atts = []
    table = []
    # Scan through the manifest, collect a table of available axes.
    for filename, (opener, entries) in manifest.iteritems():
      for _varname, _axes, _atts in entries:
        if _varname == varname:
          atts.append(_atts)
          table.append((filename, opener, _axes))
    # Get subset of attributes that are consistent among all sources of data
    atts = common_dict(atts)
    # Reduce the axes to only those that the variable actually has
    axis_types = set(type(a) for f,o,_axes in table for a in _axes)
    axes = [a for a in axes if type(a) in axis_types]

    obj = cls(axes, name=varname, dtype=float, atts=atts)
    obj._table = table
    return obj

  #TODO
  def getview (self, view, pbar):
    import numpy as np
    out = np.zeros(view.shape, dtype=self.dtype)
    #TODO: retain var for next loop, in case there's multiple timesteps per file
    for outtime, intime in enumerate(view.integer_indices[0]):
      t,f = self._filemap[intime]
      var = (v for v in self._opener(f) if v.name == self._name).next()
      out[outtime,...] = view.modify_slice(0, [intime]).get(var)
      pbar.update(outtime*100./len(view.integer_indices[0]))
    pbar.update(100)
    return out
del Var


# Wrap a domain as a dataset.
# Requires the original file manifest, to determine where to get the data.
def domain_as_dataset (domain, manifest):
  from pygeode.dataset import Dataset
  varlist = domain.get_axis(Varlist)
  assert varlist is not None, "Unable to determine variable names"
  axes = filter(None,domain.without_axis(Varlist).axes)
  return Dataset([DataVar.construct(name, axes, manifest) for name in varlist])

# General interface
class DataInterface (object):

  # Initialization - given a list of files, and an opener method:
  # 1) Scan through all files, determine what variables are present (and on what
  #    domains).
  # 2) Store this information in a file somewhere (so re-running doesn't require
  #    a full rescan).
  # 3) Store the full table of information inside the object, for further
  #    use at runtime.
  def __init__ (self, files, opener, manifest):
    from glob import glob
    from os.path import exists, getatime, getmtime
    from os import utime
    import cPickle as pickle
    from pygeode.progress import PBar
    from collections import namedtuple, defaultdict

    # Expand any globbing patterns
    if isinstance(files,str): files = [files]
    globbed_files=files
    files = []
    for g in globbed_files:
      for f in glob(g):
        files.append(f)

    files = [f for f in files if not f.endswith("_000") and not f.endswith("_000h")]

    # Get the domain information from the files
    # Each entry is a tuple of (filename, varname, time_info, time, universal_time, spatial_axes, domain, atts)
    entry = namedtuple('entry', 'file var time_info, time, universal_time, spatial_axes, domain, atts')

    if exists(manifest):
      with open(manifest,'r') as f:
        version = pickle.load(f)
        table = pickle.load(f)
      mtime = getmtime(manifest)
    if not exists(manifest) or version != MANIFEST_VERSION:
      table = []
      mtime = 0

    table = map(entry._make,table)


    handled_files = set(x.file for x in table)

    pbar = PBar (message = "Generating %s"%manifest)

    modified_table = False

    # Construct / add to the table
    for i,f in enumerate(files):
      pbar.update(i*100./len(files))
      if f in handled_files:
        # File has changed since last time?
        if int(getmtime(f)) > mtime:
          # Remove existing info
          table = [t for t in table if t.file != f]
        else:
          # Otherwise, we've already dealt with the file, so skip it.
          continue
      # Always use the latest modification time to represent the valid time of
      # the whole table.
      mtime = max(mtime,int(getmtime(f)))
      d = opener(f)
      for var in d:

        spatial_axes = var.axes[1:]
        domain = tuple(encode_axis(a) for a in spatial_axes)

        atts = tuple(sorted(var.atts.items()))

        time_info, time, universal_time = encode_time_axis(var.axes[0])

        for t, u in zip(time, universal_time):
          table.append(entry(file=f,var=var.name,time_info=time_info,time=t,universal_time=u,spatial_axes=spatial_axes,domain=domain,atts=atts))

      modified_table = True

    del handled_files  # No longer needed

    if modified_table:
      # Store the info in a file, so we don't have to re-scan all the data again.
      # First, re-use the same object where possible, so we don't have any
      # redundant information in the pickle file (and we get a smaller memory
      # footprint)

      object_lookup = dict()
      axis_lookup = dict()
      for i,x in enumerate(table):
        time_info = object_lookup.setdefault(x.time_info,x.time_info)
        time = object_lookup.setdefault(x.time,x.time)
        universal_time = object_lookup.setdefault(x.universal_time,x.universal_time)
        spatial_axes = tuple(axis_lookup.setdefault(encode_axis(a),a) for a in x.spatial_axes)
        spatial_axes = object_lookup.setdefault(spatial_axes,spatial_axes)
        domain = tuple(object_lookup.setdefault(d,d) for d in x.domain)
        domain = object_lookup.setdefault(domain,domain)
        atts = object_lookup.setdefault(x.atts,x.atts)
        table[i] = entry(file=x.file, var=x.var, time_info=time_info, time=time, universal_time=universal_time, spatial_axes = spatial_axes, domain=domain, atts=atts)

      with open(manifest,'w') as f:
        pickle.dump(MANIFEST_VERSION, f)
        pickle.dump(map(tuple,table), f)
      # Set the modification time to the latest file that was used.
      atime = getatime(manifest)
      utime(manifest,(atime,mtime))

    pbar.update(100)

    # Store the table of available data.
    # Use a dictionary indexed by variable, since we will be interested in
    # getting data only for particular variables anyway.
    # (Saves time in searching for relevant data for the query).
    self.table = defaultdict(list)
    for x in table:
      self.table[x.var].append(x)
    # Store the available domains.  The order of domains is not important,
    # but for debugging purposes should be deterministic.
    self._domains = sorted(set(x.domain for x in table))

    self._opener = opener


  # Get the requested variable(s).
  # The following filters are applied:
  # - Only use the timesteps where all variables are defined concurrently
  # - The variables must all be on the same spatial axes
  # The possible matches are returned one at a time, and the calling method
  # will have to figure out which one is the best.
  def find (self, *vars):

    for var in vars:
      if var not in self.table:
        raise KeyError("'%s' not found in this data."%var)

    # Try each possible domain, until we find one that works for these variables
    for domain in self._domains:

      compatible_domains = [d for d in self._domains if is_subset_of(domain,d)]

      table = dict()
      for var in vars:
        table[var] = [x for x in self.table[var] if x.domain in compatible_domains]
        if len(table[var]) == 0: continue

      # Find common timesteps between all variables
      timesteps = [set(x.universal_time for x in table[var]) for var in vars]
      common_timesteps = set.intersection(*timesteps)

      if len(common_timesteps) == 0: continue

      varlist = []
      for var in vars:
        records = [x for x in table[var] if x.universal_time in common_timesteps]
        varlist.append(DataVar.construct(name=var, table=records, domain=domain, opener=self._opener))
      if len(varlist) == 1:
        yield varlist[0]
      else:
        yield varlist

  # Determine if a given variable is in the data somewhere
  def have (self, var):
    return var in self.table

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



# Wrap a table of data into a variable
from pygeode.var import Var
class DataVar_old(Var):
  # Create a variable from a table
  @classmethod
  def construct (cls, name, table, domain, opener):
    import numpy as np
    from pygeode.tools import common_dict

    # Get spatial axes
    # Start with something big enough to represent the domain
    for x in table:
      if is_subset_of(domain,x.domain):
        spatial_axes = list(x.spatial_axes)
        break
    else:
      raise ValueError ("Invalid domain")

    domain = dict(domain)

    # Reduce the spatial axes to the same values as the domain
    for ia, axis in enumerate(spatial_axes):
      if type(axis) not in domain: continue  # Axis not part of domain restriction
      sl = []
      target_values = set(domain[type(axis)])
      for i,v in enumerate(axis.values):
        if v in target_values:
          sl.append(i)
      # Special case: single integer
      if len(sl) == 1: sl = sl[0]
      # Special case: regularly spaced interval
      elif len(set(np.diff(sl))) == 1:
        delta = sl[1] - sl[0]
        sl = slice(sl[0],sl[-1]+1,delta)
      spatial_axes[ia] = axis.slice[sl]

    # Get time axis
    timecls = set(x.time_info[0] for x in table)
    startdate = set(x.time_info[1] for x in table)
    units = set(x.time_info[2] for x in table)
    values = [x.time for x in table]
    # Fast case: the pieces of the time axis all have the same class, units,
    # and startdate.
    if len(timecls) == 1 and len(startdate) == 1 and len(units) == 1:
      timecls = timecls.pop()
      startdate = dict(startdate.pop())
      units = units.pop()
      time_axis = timecls(values=sorted(values), startdate=startdate, units=units)
    # Otherwise, need to do a lot of extra work
    else:
      from warnings import warn
      time_pieces = []
      for x in table:
        timecls = x.time_info[0]
        startdate = dict(x.time_info[1])
        units = x.time_info[2]
        time_pieces.append(timecls(values=[x.time], startdate=startdate, units=units))
      time_axis = timecls.concat(time_pieces).sorted()

    # Get a mapping from time values to filenames
    filemap = [(v,x.file) for v,x in zip(values,table)]
    filemap = sorted(filemap)

    axes = [time_axis] + list(spatial_axes)

    # Get attributes
    atts = common_dict([dict(x.atts) for x in table])

    obj = cls(axes, name=name, dtype=float, atts=atts)

    obj._filemap = filemap
    obj._opener = opener
    obj._name = name

    return obj

  def getview (self, view, pbar):
    import numpy as np
    out = np.zeros(view.shape, dtype=self.dtype)
    #TODO: retain var for next loop, in case there's multiple timesteps per file
    for outtime, intime in enumerate(view.integer_indices[0]):
      t,f = self._filemap[intime]
      var = (v for v in self._opener(f) if v.name == self._name).next()
      out[outtime,...] = view.modify_slice(0, [intime]).get(var)
      pbar.update(outtime*100./len(view.integer_indices[0]))
    pbar.update(100)
    return out
del Var


# Helper function - convert an Axis object to an encoded value
# The result can be hashed and compared.
def encode_axis (axis):
  return (type(axis),tuple(axis.values))

# Helper function - encode a time axis (requires some extra encoding)
# Returns 2 parts - a time type (including reference date / units), and the
# particular offset array for this time period.
def encode_time_axis (axis):
  startdate = tuple(sorted(axis.startdate.items()))
  values = tuple(axis.values)
  return (type(axis), startdate, axis.units), values, time2val(axis)

# Helper function - determine if one domain is a subset of another domain
def is_subset_of (axes1, axes2):
  axes1 = dict(axes1)
  axes2 = dict(axes2)
  for axis in axes2.keys():
    if axis not in axes1: return False
    if not (set(axes1[axis]) <= set(axes2[axis])): return False
  return True

# Helper function - convert a time axis to an array of values
# Used only for matching with other time axes
def time2val (timeaxis):
  year = timeaxis.auxarrays['year']
  month = timeaxis.auxarrays['month']
  day = timeaxis.auxarrays['day']
  hour = timeaxis.auxarrays.get('hour',[0]*len(timeaxis))
  minute = timeaxis.auxarrays.get('minute',[0]*len(timeaxis))
  second = timeaxis.auxarrays.get('second',[0]*len(timeaxis))
  return tuple("%04d%02d%02d%02d%02d%02d"%(y,m,d,H,M,S) for y,m,d,H,M,S in zip(year,month,day,hour,minute,second))

def my_opener(filename):
  from pygeode.formats import fstd
  return fstd.open(filename, raw_list=True)

if __name__ == '__main__':
  from glob import glob
  manifest = scan_files(glob("/wrk6/neish/mn083/model/2009*"), opener=my_opener, manifest="/wrk6/neish/mn083/model/nc_cache/mn083_manifest")
  domains = get_domains(manifest)
  for d in domains:
    print d, d.axes
    print domain_as_dataset(d, manifest)
  print len(domains)
