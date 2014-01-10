# A container for holding multiple datasets of the same data
# (one dataset per domain).
# E.g., there may be surface and 3D output at different time frequencies.

# General interface
class DataInterface (object):
  def __init__ (self, datasets, cache):
    pass #TODO
  def domains_for_field (self, field):
    pass #TODO
  def has_field (self, field):
    pass #TODO

# Helper function - given a list of files, and an opener method:
# 1) Scan through all files, determine what variables are present (and on what
#    domains).
# 2) Store this information in a file somewhere (so re-running doesn't require
#    a full rescan).
# 3) Group the data by domain, construct the corresponding datasets.
def create_datasets_by_domain (files, opener):
  pass #TODO

