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
    from collections import namedtuple
    from itertools import imap

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
    # Each entry is a tuple of (filename, time, varname, spatial_axes)
    entry = namedtuple('entry', 'file time var spatial_axes')

    cachefile = cache.local_filename("domains")
    if exists(cachefile):
      table = pickle.load(open(cachefile,'r'))
    else:
      table = set()

    table = set(imap(entry._make,table))

    # Helper dictionary - keeps track of existing objects, so we can re-use them
    object_lookup = dict()
    for x in table:
      object_lookup[x.spatial_axes] = x.spatial_axes
      for a in x.spatial_axes:
        object_lookup[a] = a

    handled_files = set(x.file for x in table)

    pbar = PBar (message = "Generating %s"%cachefile)

    for i,f in enumerate(files):
      pbar.update(i*100./len(files))
      if f in handled_files: continue
      d = opener(f)
      for var in d:
        # Extract spatial axis arrays
        spatial_axes = [(type(a),tuple(map(float,a.values))) for a in var.axes[1:]]
        # Use existing objects where possible
        spatial_axes = [object_lookup.setdefault(a,a) for a in spatial_axes]
        # Convert to frozenset (to make it hashable)
        spatial_axes = frozenset(spatial_axes)
        spatial_axes = object_lookup.setdefault(spatial_axes,spatial_axes)
        # Add each available timestep as a separate entry
        for t in time2val(var.axes[0]):
          table.add(entry(f,float(t),var.name,spatial_axes))

    del handled_files  # No longer needed

    pickle.dump(set(imap(tuple,table)), open(cachefile,'w'))
    pbar.update(100)


    # Go back and look for more other domains we can satisfy with the available
    # data.
    # (E.g., we may be able to use 3D fields as surface data)
    unique_spatial_axes = set(x.spatial_axes for x in table)
    for x in set(table):
      for s in unique_spatial_axes:
        if s is x.spatial_axes: continue
        if is_subset_of(s,x.spatial_axes):
          table.add(entry(file=x.file, time=x.time, var=x.var, spatial_axes=s))

    self.table = table


  # Get the requested variable(s).
  # The following filters are applied:
  # - Only use the timesteps where all variables are defined concurrently
  # - The variables must all be on the same spatial axes
  # - Optionally, a user-specified filter is applied to meet particular criteria
  # - If more than one spatial domain matches, then the one with the largest
  #   size is chosen.
  def find (self, *vars, **kwargs):
    from itertools import ifilter
    from operator import mul
    extra_filter = kwargs.pop('extra_filter',None)
    if len(kwargs) > 0:
      raise TypeError("got an unexpected keyword argument '%s'"%kwargs.keys()[0])
    # Get the available times/domains for each var
    tables = [filter(lambda x: x.var == var, self.table) for var in vars]
    if extra_filter is not None:
      tables = [filter(extra_filter,table) for table in tables]
    for var,table in zip(vars,tables):
      if len(table) == 0:
        raise ValueError("Can't find any matching data for %s"%var)

    # Get the available spatial domains
    domains = [set(x.spatial_axes for x in table) for table in tables]
    common_domains = set.intersection(*domains)
    if len(common_domains) == 0:
      raise ValueError("Can't find a common spatial domain for %s"%vars)

    # Sort by domain size (try largest domain first)
    domain_size = lambda s: reduce(mul,[len(v) for v in s.spatial_axes.values()])
    common_domains = sorted(common_domains, key=domain_size, reverse=True)
    for domain in common_domains:
      # Check if we have data for this domain at common timesteps
      timesteps = [set(x.time for x in table) for table in tables]
      common_timesteps = set.intersection(*timesteps)
      if len(common_timesteps) == 0: continue
      # Filter for these timesteps
      tables = [filter(lambda x: x.time in common_timesteps, table) for table in tables]
      # Construct variables from these tables
      #TODO
      break
    else:
      raise ValueError("Can't find any common timesteps for %s"%vars)


def blah():
  # Construct a dataset from each domain
  # Use multifile interface to handle the logistics
  datasets = []
  for domain, vars in domain_vars.iteritems():
    domain = dict(domain)  # Re-construct dictionary from frozenset
    full_domain = dict(domain)  # for debugging only
    # Get list of files to iterate over, and the corresponding times
    # Also, remove the time info from the domain.
    files, times = zip(*domain.pop('time'))
    # Concatenate all times together
    times = sum(times,())

    # Need a dummy function wrapper to properly bind the variables
    def make_opener():
      original_opener = opener
      target_spatial_axes = domain
      target_vars = vars
      target_times = set(times)
      target_full_domain = domain  # for debugging only
      def domain_specific_opener(filename):
#        print "called opener on", filename
#        print 'domain: ('+','.join("%s:%d"%(getattr(k,'name',k),len(v)) for k,v in dict(target_full_domain).iteritems())+'):', target_vars
        import numpy as np
        from pygeode.dataset import asdataset
        d = original_opener(filename)
        varlist = []
        for varname in target_vars:
          var = (v for v in d if v.name == varname).next()
          # Extract data on the domain we want
          slices = []
          for axis in var.axes:
            if type(axis) not in target_spatial_axes:
              slices.append(slice(None))
              continue
            target_values = target_spatial_axes[type(axis)]
            if target_values == tuple(axis.values):
              slices.append(slice(None))
              continue
            sl = []
            for i,v in enumerate(axis.values):
              if v in target_values: sl.append(i)
            assert len(sl) > 0, "Internal error with data_interface - we were promised data, but there's nothing for the specified domain :("
            # Special case: single integer
            if len(sl) == 1: sl = sl[0]
            # Special case: regularly spaced interval
            elif len(set(np.diff(sl))) == 1:
              delta = sl[1] - sl[0]
              sl = slice(sl[0],sl[-1]+1,delta)
            slices.append(sl)
          # Apply the slicing
          var = var.slice[slices]
          varlist.append(var)
        return asdataset(varlist)
      return domain_specific_opener
    # Work around a bug in multifile (looks for lists but not tuples)
    files =  list(files)
    datasets.append(open_multi(files, opener=make_opener(), file2date=file2date))
  return datasets



# Helper function - determine if one domain is a subset of another domain
def is_subset_of (axes1, axes2):
  axes1 = dict(axes1)
  axes2 = dict(axes2)
  for axis in axes2.keys():
    if axis not in axes1: return False
    if not (set(axes1[axis]) <= set(axes2[axis])): return False
  return True

# Helper function - convert a time axis to an array of values
def time2val (timeaxis):
  from pygeode.timeutils import reltime
  startdate = dict(year=2009, month=1, day=1)
  units = 'hours'
  return list(reltime(timeaxis, startdate=startdate, units=units))


# Test it out
def opener (filename):
  from pygeode.formats import fstd
  data = fstd.open(filename, squash_forecasts=True, raw_list=True)
  # Could do unit conversions here, and add extra fields
  return data


from cache import Cache
cache = Cache(".", global_prefix='mytest_')

datasets = DataInterface("/wrk6/neish/mn075/model/20090101*", opener, cache)

