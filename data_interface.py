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
  def __init__ (self, files, opener, cache):
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

    files = [f for f in files if not f.endswith("_000")]

    # Get the domain information from the files
    # Each entry is a tuple of (filename, varname, time_info, time, universal_time, spatial_axes, domain, atts)
    entry = namedtuple('entry', 'file var time_info, time, universal_time, spatial_axes, domain, atts')

    cachefile = cache.local_filename("domains")
    if exists(cachefile):
      table = pickle.load(open(cachefile,'r'))
      mtime = getmtime(cachefile)
    else:
      table = []
      mtime = 0

    table = map(entry._make,table)


    handled_files = set(x.file for x in table)

    pbar = PBar (message = "Generating %s"%cachefile)

    modified_table = False

    # Construct / add to the table
    for i,f in enumerate(files):
      pbar.update(i*100./len(files))
      if f in handled_files:
        # File has changed since last time?
        if getmtime(f) > mtime:
          # Remove existing info
          table = [t for t in table if t.file != f]
        else:
          # Otherwise, we've already dealt with the file, so skip it.
          continue
      # Always use the latest modification time to represent the valid time of
      # the whole table.
      mtime = max(mtime,getmtime(f))
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

      pickle.dump(map(tuple,table), open(cachefile,'w'))
      # Set the modification time to the latest file that was used.
      atime = getatime(cachefile)
      utime(cachefile,(atime,mtime))
      # Hack to force the saved mtime to not get truncated
      dt = mtime - getmtime(cachefile)
      utime(cachefile,(atime,mtime+dt))

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
      print [len(a[1]) for a in domain]
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
class DataVar(Var):
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


# Test it out
def stuff():
  from gem import GEM_Data
  gemdata = GEM_Data("/wrk6/neish/mn075/model", flux_dir="/wrk1/EC-CAS/GEM/inputs/emissions_v2", name="mn075", title="mn075")
#  print gemdata.get_data('sfc','CO2')
#  print gemdata.get_data('zonalmean_gph','CO2')
#  for dp in gemdata.data.find('dp'):
#    if len(dp.zaxis) > 1:
#      from pygeode.formats import netcdf
#      netcdf.save('dp.nc', dp(i_time=0))
  #"""
  print gemdata.get_data('totalcolumn', 'CO2')
  print gemdata.get_data('avgcolumn', 'CO2')
  print gemdata.get_data('totalmass', 'CO2')
  print gemdata.get_data('totalflux', 'CO2')
  print gemdata.get_data('Toronto', 'CO2')
  #"""

if __name__ == '__main__':
  from cProfile import run
  run("stuff()")
