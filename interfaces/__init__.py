
# Generic interface for model data.
# Each specific model would need to sub-class this, and implement the
# needed interfaces.
class ModelData (object):

  # Method to open a single file
  def open_file (filename):
    raise NotImplementedError

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  def decode (self, dataset):
    raise NotImplementedError

  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  def find_files (dirname):
    raise NotImplementedError

  # Method to fully reconstruct a model dataset that had been cached in
  # an intermediate format.
  def load_hook (dataset):
    return dataset

  # Method to re-encode data into the source context
  # (e.g., rename fields to what would be originally in these kinds of files)
  def encode (self, dataset):
    raise NotImplementedError

  # Method to write data to file(s).
  def write (self, datasets, dirname):
    raise NotImplementedError

  # Helper method to compute the change in pressure within a vertical layer.
  def compute_dp (zaxis, p0):
    raise NotImplementedError

  # Helper method to compute pressure levels from the given z-axis and surface pressure
  def compute_pressure (zaxis, p0):
    raise NotImplementedError


