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
  # Domains are lists of axis types and values
  domains = []
  for f in files:
    d = opener(f)
    for var in d.vars:
      # Extract axis arrays (skip time axis)
      axes = [(type(a),tuple(a.values)) for a in var.axes[1:]]
      if axes not in domains:
        domains.append(axes)

  # For each domain, construct a table of variables and files
  var_tables = [{} for n in range(len(domains))]
  for f in files:
    d = opener(f)
    for var in d.vars:
      # Extract axis arrays (skip time axis)
      axes = [(type(a),tuple(a.values)) for a in var.axes[1:]]
      for domain, var_table in zip(domains,var_tables):
        # Check if these axes are a subset of the axes of this domain.
        # If so, then we can provide this variable on this domain, for this file. 
        if is_subset_of(domain,axes):
          if var.name not in var_table: var_table[var.name] = []
          var_table[var.name].append(f)


  # Not all variables may be available at the same timesteps (even for the same domain).
  # So, need to 
  # Define openers for the data (one for each domain)

  print domains
  print "number of domains:", len(domains)
#  print var_tables
  for domain, var_table in zip(domains,var_tables):
    print sorted(var_table.keys()), tuple(len(a[1]) for a in domain)
  pass #TODO
  #TODO: allow post-filtering (after multifile merge) for things like unit conversion.


# Helper function - determine if one domain is a subset of another domain
def is_subset_of (axes1, axes2):
#  # Eliminate axes that aren't in the first domain.
#  axes2 = [a2 for a2 in axes2 if any(a2[0] is a1[0] for a1 in axes1)]
  if len(axes1) != len(axes2): return False
  return all(set(a1[1]) <= set(a2[1]) for a1,a2 in zip(axes1,axes2))

# Test it out
def opener (filename):
  from pygeode.formats import fstd
  data = fstd.open(filename, squash_forecasts=True)
  # Could do unit conversions here, and add extra fields
  return data

create_datasets_by_domain ("/wrk6/neish/mn075/model/20090101*", opener)

