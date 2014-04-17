# Cache interface


# Helper methods:

# A default hook for saving data to a file.
# All it does is wrap the var into a dataset.
def default_save_hook (var):
  from pygeode.dataset import asdataset
  return asdataset(var)

# A default hook for loading data back from a file.
# All it does is return the first variable it finds (assuming there's only one variable
# in the file).
def default_load_hook (dataset):
  return dataset.vars[0]


# Create a "unique" string to identify the spatial domain of a variable
def domain_hash (var):
  from pygeode.axis import TAxis
  import pickle, hashlib, base64

  # Get all the points in the domain
  data = [list(a.values) for a in var.axes if not isinstance(a,TAxis)]

  # Convert to a bytestream
  data = pickle.dumps(data)

  # Calculate a hash value
  data = hashlib.md5(data).digest()

  # Convert the hash value to a printable string
  data = base64.urlsafe_b64encode(data)

  # Only keep the first few characters
  data = data[:5]

  return data


# Error classes related to caching

class CacheWriteError (IOError): pass


# The Cache object:

class Cache (object):
  def __init__ (self, dir, fallback_dirs=[], global_prefix='', save_hook=default_save_hook, load_hook=default_load_hook, split_time=True):
    from os.path import exists, isdir
    from os import mkdir, remove

    self.save_hook = save_hook
    self.load_hook = load_hook
    self.global_prefix = global_prefix
    self.split_time = split_time

    self.read_dirs = []
    self.write_dir = None

    for write_dir in [dir]+fallback_dirs:

      try:

        if not exists(write_dir):
          mkdir(write_dir)

        if not isdir(write_dir):
          raise IOError ("%s is not a directory"%write_dir)

        # Determine all sources for *reading* pre-cached data
        self.read_dirs.append(write_dir+"/")

        # Try writing a dummy file, make sure this user has permission to write
        # into this directory.
        dummy = write_dir + "/dummy"
        f = file(dummy, 'a')
        f.close()
        remove(dummy)

        self.write_dir = write_dir + "/"
        return

      except IOError: continue
      except OSError: continue


  # Internal method - get the appropriate filename.
  # If it already exists, return the path to the existing file.
  # Otherwise, return a (non-existent) file inside the write_dir.
  def _full_path (self, filename):
    from os.path import exists
    for dir in self.read_dirs:
      if exists(dir+filename): return dir+filename
    if self.write_dir is None:
      raise CacheWriteError ("Nowhere to write files")
    return self.write_dir+filename


  # Write out the data
  def write (self, var, prefix):
    from os.path import exists
    from os import remove
    from pygeode.formats import netcdf
    from pygeode.formats.multifile import open_multi
    from common import fix_timeaxis
    import numpy as np

    # Make sure the data is saved with a consistent start date
    # (makes it easier to plot timeseries data from multiple sources)
    var = fix_timeaxis(var)

    # Apply the global prefix - a generic string that identifies the source
    # of the cache data
    prefix = self.global_prefix + prefix + '_' + domain_hash(var)

    # Make sure the data is in 32-bit precision
    # (sometimes diagnostics cause a 64-bit output - waste of space)
    if var.dtype.name != 'float32':
      var = var.as_type('float32')

    # Special case - no time axis
    if not var.hasaxis('time'):
      from warnings import warn
      warn ("Untested case - no time axis in data")
      filename = self._full_path(prefix + ".nc")
      if not exists(filename):
        dataset = self.save_hook(var)
        try:
          netcdf.save(filename, dataset)
        except KeyboardInterrupt:
          remove(filename)
          raise
      dataset = netcdf.open(filename)
      var = self.load_hook(dataset)
      return var

    taxis = var.getaxis('time')

    # For the usual case, split the data into individual files for each timestep

    # Generate a list of filenames
    pattern = ""
    if 'year' in taxis.auxarrays:
      years = ["%04d"%y for y in taxis.auxarrays['year']]
      pattern += "$Y"
    else:
      years = [''] * len(taxis)

    if 'month' in taxis.auxarrays:
      months = ["%02d"%m for m in taxis.auxarrays['month']]
      pattern += "$m"
    else:
      months = [''] * len(taxis)

    if 'day' in taxis.auxarrays:
      days = ["%02d"%d for d in taxis.auxarrays['day']]
      pattern += "$d"
    else:
      days = [''] * len(taxis)

    if 'hour' in taxis.auxarrays:
      hours = ["%02d"%h for h in taxis.auxarrays['hour']]
      pattern += "$H"
    else:
      hours = [''] * len(taxis)

    if 'minute' in taxis.auxarrays:
      minutes = ["%02d"%m for m in taxis.auxarrays['minute']]
      pattern += "$M"
    else:
      minutes = [''] * len(taxis)

    datestrings = [y+m+d+H+M for y,m,d,H,M in zip(years,months,days,hours,minutes)]
    first_date = datestrings[0]
    last_date = datestrings[-1]

    # Check if we already have the data in the cache
    # (look for the one big file that gets generated in the last stage)
    bigfile = self._full_path(prefix+"_"+datestrings[0]+"-"+datestrings[-1]+".nc")
    if not exists(bigfile):

      # Split into 1 file per timestep?
      # Useful for model output, where you might extend the data with extra timesteps later.
      if self.split_time is True:
        filenames = [self._full_path(prefix+"_"+datestring+".nc") for datestring in datestrings]

        # Determine which files aren't created yet
        uncached_stuff = [(i,f) for i,f in enumerate(filenames) if not exists(f)]
        if len(uncached_stuff) > 0:
          uncached_times, uncached_filenames = zip(*uncached_stuff)
        else:
          uncached_times, uncached_filenames = [], []

        # Loop over each time, save into a cache file
        from pygeode.progress import PBar
        pbar = PBar (message = "Caching %s"%prefix)
        for i,filename in zip(uncached_times, uncached_filenames):
          pbar.update(i*100./len(filenames))

          # Save the data
          data = var(i_time=i)
          try:
            netcdf.save(filename, data)
          except KeyboardInterrupt:
            # Clean up the partial file, if the user aborts the process.
            remove(filename)
            raise

        pbar.update(100)

        # Open the many small files
        var = open_multi(filenames, format=netcdf, pattern="_"+pattern+"\.nc")[var.name]
        # Use a consistent time axis (override the start date imposed by open_multi)
        var = fix_timeaxis(var)

      # (end of time split)

      # Load into memory
      var = var.load()

      # Compute ranges for the data
      sample = var.values.flatten()
      # Filter out NaN values
      sample = sample[np.isfinite(sample)]
      # Get a good range (covers most values)
      sample.sort()
      N = len(sample)
      low = sample[int(round((N-1)*0.001))]
      high = sample[int(round((N-1)*0.999))]
      var.atts['low'] = low
      var.atts['high'] = high

      # Apply any hooks for saving the var (extra metadata encoding?)
      dataset = self.save_hook(var)
      # Re-save back to a big file
      try:
        netcdf.save (bigfile, dataset)
      except KeyboardInterrupt:
        remove(bigfile)
        raise

    # (end of cache file creation)

    # Load the data from the big file
    dataset = netcdf.open(bigfile)

    # Apply any hooks for loading the var (extra metadata decoding?)
    var = self.load_hook(dataset)

    return var


  # Generate a filename, in a writeable location.
  # Assume the file will be read / written outside this class.
  def local_filename (self, prefix):

    return self.write_dir + self.global_prefix + prefix

