# A container for holding multiple datasets of the same data
# (one dataset per domain).
# E.g., there may be surface and 3D output at different time frequencies.

# General interface
class DataInterface (object):
  def __init__ (self, datasets, cache):
    from pygeode.dataset import as_dataset
    self.datasets = tuple(as_dataset(d) for d in datasets)
    self.cache = cache
  def domains_for_field (self, field):
    for d in datasets:
      if field in d: yield d[field]
  def has_field (self, field):
    return len(list(self.domains_for_field(field))) > 0

# Helper function - given a list of files, and an opener method:
# 1) Scan through all files, determine what variables are present (and on what
#    domains).
# 2) Store this information in a file somewhere (so re-running doesn't require
#    a full rescan).
# 3) Group the data by domain, construct the corresponding datasets.
def create_datasets_by_domain (files, opener, post_processor=None):
  #TODO: allow for multiple files with the same time info (but mutually exclusive vars)
  # e.g., km, pm, dm files
  from glob import glob
  from pygeode.timeaxis import Time

  if post_processor is None:
    post_processor = lambda x: x

  # Expand any globbing patterns
  if isinstance(files,str): files = [files]
  globbed_files=files
  files = []
  for g in globbed_files:
    for f in glob(g):
      files.append(f)

  # Get the unique domains from the files
  # Keys are spatial axes, values are var:times dictionaries
  domain_times = dict()
  for f in files:
    d = opener(f)
    for var in d:
      # Extract spatial axis arrays
      spatial_axes = frozenset((type(a),tuple(a.values)) for a in var.axes[1:])
      # Extract time axis
      time_axis = (f,tuple(time2val(var.axes[0])))
      # Add this info
      timedict = domain_times.setdefault(spatial_axes,dict())
      timedict.setdefault(var.name,set()).add(time_axis)

  print "=== Domains after initial pass: ==="
  for spatial_axes, timedict in domain_times.iteritems():
    print "("+",".join("%s:%d"%(k.name,len(v)) for k,v in dict(spatial_axes).iteritems())+")", " ".join("%s[%s]"%(var,len(times)) for var,times in timedict.iteritems())

  # Go back and look for more time steps for the domains.
  # (E.g., we may be able to use 3D fields to extend surface timesteps)
  for spatial_axes, timedict in domain_times.iteritems():
    for other_spatial_axes, other_timedict in domain_times.iteritems():
      if other_spatial_axes is spatial_axes: continue
      if is_subset_of(spatial_axes,other_spatial_axes):
        for var,times in other_timedict.iteritems():
          timedict.setdefault(var,set()).update(times)

  print "=== Domains after second pass: ==="
  for spatial_axes, timedict in domain_times.iteritems():
    print "("+",".join("%s:%d"%(k.name,len(v)) for k,v in dict(spatial_axes).iteritems())+")", " ".join("%s[%s]"%(var,len(times)) for var,times in timedict.iteritems())

  # Build the full domains from the key/value pairs
  domain_vars = dict()
  for spatial_axes, timedict in domain_times.iteritems():
    # Split time axis by var
    for var, times in timedict.iteritems():
      axes = dict(spatial_axes,time=frozenset(times))
      axes = frozenset(axes.iteritems())
      domain_vars.setdefault(axes,set()).add(var)

  # Go back and look for other variables available for the specified times
  for axes, varlist in domain_vars.iteritems():
    for other_axes, other_varlist in domain_vars.iteritems():
      if other_axes is axes: continue
      if is_subset_of(axes,other_axes):
        varlist.update(other_varlist)

  # Look for redundant domains (all vars / axes available in another domain)
  for axes, varlist in domain_vars.items():
    for other_axes, other_varlist in domain_vars.items():
      if other_axes is axes: continue
      if is_subset_of(axes,other_axes):
        if set(varlist) <= set(other_varlist):
          print "!!!Found a redundant domain:"
          print '('+','.join("%s:%d"%(getattr(k,'name',k),len(v)) for k,v in dict(axes).iteritems())+'):', varlist
          del domain_vars[axes]

  print "Final domains:"
  for axes, varlist in domain_vars.iteritems():
    print '('+','.join("%s:%d"%(getattr(k,'name',k),len(v)) for k,v in dict(axes).iteritems())+'):', varlist

  # Construct a dataset from each domain
  # Use multifile interface to handle the logistics
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
        print "called opener on", filename
        print 'domain: ('+','.join("%s:%d"%(getattr(k,'name',k),len(v)) for k,v in dict(target_full_domain).iteritems())+'):', target_vars
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
    print make_opener()(files[0])
  return
  #TODO



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

create_datasets_by_domain ("/wrk6/neish/mn075/model/20090101*", opener)

