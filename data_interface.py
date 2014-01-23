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
    for var in d.vars:
      # Extract spatial axis arrays
      spatial_axes = frozenset((type(a),frozenset(a.values)) for a in var.axes[1:])
      # Extract time axis
      time_axis = time2val(var.axes[0])
      # Add this info
      timedict = domain_times.setdefault(spatial_axes,dict())
      timedict.setdefault(var.name,set()).update(time_axis)

  # Go back and look for more time steps for the domains.
  # (E.g., we may be able to use 3D fields to extend surface timesteps)
  for spatial_axes, timedict in domain_times.iteritems():
    for other_spatial_axes, other_timedict in domain_times.iteritems():
      if other_spatial_axes is spatial_axes: continue
      if is_subset_of(spatial_axes,other_spatial_axes):
        for var,times in other_timedict.iteritems():
          timedict.setdefault(var,set()).update(times)

  # Build the full domains from the key/value pairs
  domain_vars = dict()
  for spatial_axes, timedict in domain_times.iteritems():
    # Split time axis by var
    for var, times in timedict.iteritems():
      axes = dict(spatial_axes,time=frozenset(times))
      axes = frozenset(axes.iteritems())
      domain_vars.setdefault(axes,set()).add(var)


  for axes, varlist in domain_vars.iteritems():
    print '('+','.join("%s:%d"%(getattr(k,'name',k),len(v)) for k,v in dict(axes).iteritems())+'):', varlist
#  print domain_vars
  return

  #TODO


# Helper function - determine if one domain is a subset of another domain
def is_subset_of (axes1, axes2):
  axes1 = dict(axes1)
  axes2 = dict(axes2)
  for axis in axes2.keys():
    if axis not in axes1: return False
    if not (axes1[axis] <= axes2[axis]): return False
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
  data = fstd.open(filename, squash_forecasts=True)
  # Could do unit conversions here, and add extra fields
  return data

create_datasets_by_domain ("/wrk6/neish/mn075/model/20090101*", opener)

