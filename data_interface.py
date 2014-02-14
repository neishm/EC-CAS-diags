# A container for holding multiple datasets of the same data
# (one dataset per domain).
# E.g., there may be surface and 3D output at different time frequencies.

# General interface
class DataInterface (object):

  # Initialization - given a list of files, and an opener method:
  # 1) Scan through all files, determine what variables are present (and on what
  #    domains).
  # 2) Store this information in a file somewhere (so re-running doesn't require
  #    a full rescan).
  # 3) Store the full table of information inside the object, for further
  #    use at runtime.
  def __init__ (self, files, opener, cache, post_processor=None):
    from glob import glob
    from os.path import exists
    import cPickle as pickle
    from pygeode.progress import PBar
    from collections import namedtuple, defaultdict

    if post_processor is None:
      post_processor = lambda x: x

    # Expand any globbing patterns
    if isinstance(files,str): files = [files]
    globbed_files=files
    files = []
    for g in globbed_files:
      for f in glob(g):
        files.append(f)

    # Get the domain information from the files
    # Each entry is a tuple of (filename, varname, time_info, time, universal_time, spatial_axes, domain)
    entry = namedtuple('entry', 'file var time_info, time, universal_time, spatial_axes, domain')

    cachefile = cache.local_filename("domains")
    if exists(cachefile):
      table = pickle.load(open(cachefile,'r'))
    else:
      table = []

    table = map(entry._make,table)


    # Helper dictionary - keeps track of existing objects, so we can re-use them
    # Another dictionary keeps track of existing axes, so we can re-use the
    # object references where possible.
    object_lookup = dict()
    axis_lookup = dict()
    # Store one copy of all hashable items in the table
    for x in table:
      for obj in x:
        try:
          object_lookup.setdefault(obj,obj)
        except TypeError: continue

    # Store one copy of each spatial axis
    for x in table:
      for a in x.spatial_axes:
        axis_lookup.setdefault(encode_axis(a),a)
      spatial_axes = tuple(encode_axis(a) for a in x.spatial_axes)
      object_lookup.setdefault(spatial_axes,spatial_axes)


    handled_files = set(x.file for x in table)

    pbar = PBar (message = "Generating %s"%cachefile)

    for i,f in enumerate(files):
      pbar.update(i*100./len(files))
      if f in handled_files: continue  #TODO: check modification time?
      d = opener(f)
      for var in d:

        # Use existing spatial_axes where possible
        spatial_axes = tuple(axis_lookup.setdefault(encode_axis(a),a) for a in var.axes[1:])
        spatial_axes = object_lookup.setdefault(spatial_axes,spatial_axes)

        domain = tuple(encode_axis(a) for a in spatial_axes)
        domain = object_lookup.setdefault(domain,domain)

        # Use existing time axes where possible
        time_info, time, universal_time = encode_time_axis(var.axes[0])
        time_info = object_lookup.setdefault(time_info,time_info)

        for t, u in zip(time, universal_time):
          t = object_lookup.setdefault(t,t)
          u = object_lookup.setdefault(u,u)
          table.append(entry(file=f,var=var.name,time_info=time_info,time=t,universal_time=u,spatial_axes=spatial_axes,domain=domain))

    del handled_files  # No longer needed

    pickle.dump(map(tuple,table), open(cachefile,'w'))
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
        raise ValueError("'%s' not found in this data."%var)

    # Try each possible domain, until we find one that works for these variables
    for domain in self._domains:

      table = dict()
      for var in vars:
        table[var] = [x for x in self.table[var] if is_subset_of(domain,x.domain)]
        if len(table[var]) == 0: continue

      # Find common timesteps between all variables
      timesteps = [set(x.universal_time for x in table[var]) for var in vars]
      common_timesteps = set.intersection(*timesteps)

      if len(common_timesteps) == 0: continue

      varlist = []
      for var in vars:
        records = [x for x in table[var] if x.universal_time in common_timesteps]
        varlist.append(DataVar.construct(name=var, table=records, domain=domain, opener=self._opener))
      print [len(a[1]) for a in domain]
      if len(varlist) == 1:
        yield varlist[0]
      else:
        yield varlist


# Wrap a table of data into a variable
from pygeode.var import Var
class DataVar(Var):
  # Create a variable from a table
  @classmethod
  def construct (cls, name, table, domain, opener):
    import numpy as np

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
    time_pieces = []
    for x in table:
      timecls = x.time_info[0]
      startdate = dict(x.time_info[1])
      units = x.time_info[2]
      time_pieces.append(timecls(values=[x.time], startdate=startdate, units=units))
    time_axis = timecls.concat(time_pieces)

    # Get a mapping from time values to filenames
    filemap = [(v,x.file) for v,x in zip(time_axis.values,table)]
    filemap = sorted(filemap)
    time_axis = time_axis.sorted()

    axes = [time_axis] + list(spatial_axes)

    obj = cls(axes, name=name, dtype=float)

    obj._filemap = filemap
    obj._opener = opener
    obj._name = name

    return obj

  def getview (self, view, pbar):
    import numpy as np
    out = np.zeros(view.shape, dtype=self.dtype)
    for outtime, intime in enumerate(view.integer_indices[0]):
      t,f = self._filemap[intime]
      var = (v for v in self._opener(f) if v.name == self._name).next()
      out[outtime,...] = view.modify_slice(0, [intime]).get(var)
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


# Test it out
def opener (filename):
  from pygeode.formats import fstd
  data = fstd.open(filename, squash_forecasts=True, raw_list=True)
  # Could do unit conversions here, and add extra fields
  return data


from cache import Cache
cache = Cache(".", global_prefix='mytest_')

datasets = DataInterface("/wrk6/neish/mn075/model/20090101*", opener, cache)

"""
for co2, p0, gz in datasets.find('CO2', 'P0', 'GZ'):
  print co2
  print p0
  print gz
"""
for co2 in datasets.find('CO2'):
  print co2
  x = co2.get()
  print x.min()/414, x.max()/414
