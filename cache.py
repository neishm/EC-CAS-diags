# Cache interface


# Helper methods:

# Create a "unique" string to identify the spatial domain of a variable
# and the units.
def domain_hash (var):
  from pygeode.axis import TAxis
  import pickle, hashlib, base64

  # Get all the points in the domain
  data = [list(a.values) for a in var.axes if not isinstance(a,TAxis)]

  # Append the unit information
  if 'units' in var.atts:
    data.append(var.atts['units'])

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

class CacheReadError (IOError): pass
class CacheWriteError (IOError): pass


# The Cache object:

class Cache (object):
  def __init__ (self, dir, fallback_dirs=[], global_prefix='', save_hooks=[], load_hooks=[], split_time=True):
    from os.path import exists, isdir
    from os import mkdir, remove

    self.save_hooks = save_hooks
    self.load_hooks = load_hooks
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



  # Write out the data
  def write (self, var, prefix, save_hooks=[], load_hooks=[]):
    from os.path import exists
    from os import remove
    from pygeode.formats import netcdf
    from pygeode.formats.multifile import open_multi
    from pygeode.dataset import asdataset
    from common import fix_timeaxis
    import numpy as np

    # Make sure the data is saved with a consistent start date
    # (makes it easier to plot timeseries data from multiple sources)
    var = fix_timeaxis(var)

    # Apply a hash to the data's domain information
    prefix = prefix + '_' + domain_hash(var)

    # Make sure the data is in 32-bit precision
    # (sometimes diagnostics cause a 64-bit output - waste of space)
    if var.dtype.name != 'float32':
      var = var.as_type('float32')

    # Special case - no time axis
    if not var.hasaxis('time'):
      from warnings import warn
      warn ("Untested case - no time axis in data")
      filename = self.full_path(prefix + ".nc")
      if not exists(filename):
        filename = self.full_path(prefix + ".nc", writeable=True)
        dataset = asdataset([var])
        for save_hook in save_hooks + self.save_hooks:
          dataset = asdataset(save_hook(dataset))
        try:
          netcdf.save(filename, dataset)
        except KeyboardInterrupt:
          remove(filename)
          raise
      dataset = netcdf.open(filename)
      for load_hook in self.load_hooks + load_hooks:
        dataset = asdataset(load_hook(dataset))
      var = dataset.vars[0]
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
    bigfile = self.full_path(prefix+"_"+datestrings[0]+"-"+datestrings[-1]+".nc")
    if not exists(bigfile):

      bigfile = self.full_path(prefix+"_"+datestrings[0]+"-"+datestrings[-1]+".nc", writeable=True)

      # Split into 1 file per timestep?
      # Useful for model output, where you might extend the data with extra timesteps later.
      if self.split_time is True:

        # Loop over each time, save into a cache file
        from pygeode.progress import PBar
        pbar = PBar (message = "Caching %s"%self.global_prefix+prefix)
        for i, datestring in enumerate(datestrings):
          pbar.update(i*100./len(datestrings))

          filename = self.full_path(prefix+"_"+datestring+".nc")
          if exists(filename): continue
          filename = self.full_path(prefix+"_"+datestring+".nc", writeable=True)

          # Save the data
          data = asdataset([var(i_time=i)])
          for save_hook in save_hooks + self.save_hooks:
            data = asdataset(save_hook(data))
          try:
            netcdf.save(filename, data)
          except KeyboardInterrupt:
            # Clean up the partial file, if the user aborts the process.
            remove(filename)
            raise

        pbar.update(100)

        # Re-query for the files
        filenames = [self.full_path(prefix+"_"+datestring+".nc", existing=True) for datestring in datestrings]

        # Open the many small files
        var = open_multi(filenames, format=netcdf, pattern="_"+pattern+"\.nc")[var.name]
        # Use a consistent time axis (override the start date imposed by open_multi)
        var = fix_timeaxis(var)

        dataset = asdataset([var])
        for load_hook in self.load_hooks + load_hooks:
          dataset = asdataset(load_hook(dataset))
        var = dataset.vars[0]

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
      dataset = asdataset([var])
      for save_hook in save_hooks + self.save_hooks:
        dataset = asdataset(save_hook(dataset))
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
    for load_hook in self.load_hooks + load_hooks:
      dataset = asdataset(load_hook(dataset))
    var = dataset.vars[0]

    return var


  # Given a filename, add the appropriate directory structure.
  # Parameters:
  #   existing (default: False) -  If True, the file must already exist.
  #   writeable (default: False) - If True, the file must be in a writeable location.
  def full_path (self, name, existing=False, writeable=False):
    filename = self.global_prefix + name

    from os.path import exists

    dirs=[]
    # Look at the writeable directory first (if it exists)
    if self.write_dir is not None:
      dirs.append(self.write_dir)
    # If we don't need to be writeable, can look at read-only directories
    if not writeable:
      dirs.extend(self.read_dirs)

    for dir in dirs:
      if exists(dir+filename): return dir+filename

    # No existing file found.
    # Did we need a file that already exists?
    if existing:
      raise CacheReadError ("No existing copy of '%s' was found."%filename)

    # Otherwise, we need somewhere to write a new file.
    if self.write_dir is None:
      raise CacheWriteError ("Nowhere to write '%s'"%filename)

    return self.write_dir+filename

