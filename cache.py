# A place to hold temporary files
class Cache (object):
  def __init__ (self, dir, fallback_dirs=[], save_hook=None, load_hook=None):
    from os.path import exists, isdir
    from os import mkdir, remove

    self.save_hook = save_hook
    self.load_hook = load_hook

    for dir in [dir]+fallback_dirs:

      try:

        if not exists(dir):
          mkdir(dir)

        if not isdir(dir):
          raise IOError ("%s is not a directory"%dir)

        # Try writing a dummy file, make sure this user has permission to write
        # into this directory.
        dummy = dir + "/dummy"
        f = file(dummy, 'a')
        f.close()
        remove(dummy)

        self.dir = dir + "/"
        return

      except IOError: continue
      except OSError: continue

    raise IOError ("Unable to use any of the specified cache directories %s"%([dir]+fallback_dirs))

  # Write out the data
  def write (self, var, prefix):
    from os.path import exists
    from pygeode.formats import netcdf
    from pygeode.formats.multifile import open_multi
    import numpy as np

    # Apply any hooks for saving the var (extra metadata encoding?)
    if self.save_hook is not None:
      var = self.save_hook(var)

    # Make sure the data is in 32-bit precision
    # (sometimes diagnostics cause a 64-bit output - waste of space)
    if var.dtype.name != 'float32':
      var = var.as_type('float32')

    # Special case - no time axis
    if not var.hasaxis('time'):
      from warnings import warn
      warn ("Untested case - no time axis in data")
      filename = self.dir + prefix + ".nc"
      if not exists(filename):
        netcdf.save(filename, var)
      return netcdf.open(filename)[var.name]

    taxis = var.getaxis('time')

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

    datestrings = [y+m+d+h for y,m,d,h in zip(years,months,days,hours)]
    filenames = [self.dir+prefix+"_"+datestring+".nc" for datestring in datestrings]

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
      pbar.part(i,len(uncached_times))

      # Save the data
      data = var(i_time=i).load()
      netcdf.save(filename, data)

      # Compute ranges for the data
      sample = data.values.flatten()
      # Filter out NaN values
      sample = sample[np.isfinite(sample)]
      # Get a good range (covers most values)
      sample.sort()
      N = len(sample)
      low = sample[int(round((N-1)*0.001))]
      high = sample[int(round((N-1)*0.999))]
      with open(filename+".range.txt", "w") as f:
        f.write(str(low)+"\n")
        f.write(str(high)+"\n")

    pbar.update(100)

    # Compute global range over entire period
    global_range_file = self.dir+prefix+"_"+datestrings[0]+"-"+datestrings[-1]+".range.txt"
    if not exists(global_range_file):
      for filename in filenames:
        global_low = None
        global_high = None
        with open(filename+".range.txt", "r") as f:
          low = float(f.readline())
          high = float(f.readline())
        if global_low is None: global_low = low
        if global_high is None: global_high = high

        global_low = min(global_low, low)
        global_high = max(global_high, high)

      with open(global_range_file, "w") as f:
       f.write(str(global_low)+"\n")
       f.write(str(global_high)+"\n")

    # Re-load the data
    var = open_multi(filenames, format=netcdf, pattern="_"+pattern+"\.nc")[var.name]

    # Apply any hooks for loading the var (extra metadata decoding?)
    if self.load_hook is not None:
      var = self.load_hook(var)

    # Read global range
    with open(global_range_file,"r") as f:
      low = float(f.readline())
      high = float(f.readline())

    var.atts['low'] = low
    var.atts['high'] = high

    return var

