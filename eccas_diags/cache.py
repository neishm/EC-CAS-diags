###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################


# Newer versions of netCDF don't allow _FillValue to be redefined.
# Probably don't need it anyway???
from pygeode.formats import netcdf
orig_put_attributes = netcdf.put_attributes
def put_attributes (fileid, varid, atts, version):
  if '_FillValue' in atts:
    atts.pop('_FillValue')
  ret = orig_put_attributes(fileid, varid, atts, version)
netcdf.put_attributes = put_attributes


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

  # Append specie name (if applicable).
  if 'specie' in var.atts:
    data.append(var.atts['specie'])

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
  def __init__ (self, write_dir, read_dirs=[]):

    # Set up the save/load hooks.
    from station_data import station_axis_save_hook, station_axis_load_hook
    def fstd_load_hook (dataset):
      from pygeode_rpn.fstd import detect_fstd_axes
      data = list(dataset.vars)
      detect_fstd_axes(data)
      return data
    self.save_hooks = [station_axis_save_hook]
    self.load_hooks = [station_axis_load_hook, fstd_load_hook]

    self.read_dirs = read_dirs
    self.write_dir = write_dir




  # Write out the data
  def write (self, var, prefix, suffix='', split_time=True, force_single_precision=True, _dryrun=False):
    from os.path import exists
    from os import remove, mkdir, rename
    from pygeode.formats import netcdf
    from pygeode.formats.multifile import open_multi
    from pygeode.dataset import asdataset
    from common import fix_timeaxis
    import numpy as np

    if var.size == 0:
      raise ValueError("No data to cache - field '%s' is empty.  Shape: %s  Prefix: %s"%(var.name,var.shape,prefix))

    # Make sure the data is saved with a consistent start date
    # (makes it easier to plot timeseries data from multiple sources)
    var = fix_timeaxis(var)

    # Apply a hash to the data's domain information
    prefix = prefix + '_' + domain_hash(var)

    # Make sure the data is in 32-bit precision
    # (sometimes diagnostics cause a 64-bit output - waste of space)
    if force_single_precision and (var.dtype.name != 'float32'):
      var = var.as_type('float32')

    # Special case - no time axis
    if not var.hasaxis('time'):
      filename = self.full_path(prefix + suffix + ".nc")
      if not exists(filename):
        filename = self.full_path(prefix + suffix + ".nc", writeable=True)
        if _dryrun: return filename
        dataset = asdataset([var])
        for save_hook in self.save_hooks:
          dataset = asdataset(save_hook(dataset))
        netcdf.save(filename+".tmp", dataset)
        rename(filename+".tmp",filename)
      dataset = netcdf.open(filename)
      for load_hook in self.load_hooks:
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
    bigfile = self.full_path(prefix+suffix+"_"+datestrings[0]+"-"+datestrings[-1]+".nc")
    if not exists(bigfile):

      bigfile = self.full_path(prefix+suffix+"_"+datestrings[0]+"-"+datestrings[-1]+".nc", writeable=True)
      if _dryrun: return bigfile

      # Split into 1 file per timestep?
      # Useful for model output, where you might extend the data with extra timesteps later.
      if split_time is True:

        # Loop over each time, save into a cache file
        from pygeode.progress import PBar
        pbar = PBar (message = "Caching %s"%prefix+suffix)
        for i, datestring in enumerate(datestrings):
          pbar.update(i*100./len(datestrings))

          filename = self.full_path(prefix+"_split/"+prefix+"_"+datestring+".nc")
          if exists(filename): continue
          filename = self.full_path(prefix+"_split/"+prefix+"_"+datestring+".nc", writeable=True)

          # Save the data
          data = asdataset([var(i_time=i)])
          for save_hook in self.save_hooks:
            data = asdataset(save_hook(data))
          netcdf.save(filename+".tmp", data)
          rename(filename+".tmp",filename)

        pbar.update(100)

        # Re-query for the files
        filenames = [self.full_path(prefix+"_split/"+prefix+"_"+datestring+".nc", existing=True) for datestring in datestrings]

        # Open the many small files
        var = open_multi(filenames, format=netcdf, pattern="_"+pattern+"\.nc")[var.name]
        # Use a consistent time axis (override the start date imposed by open_multi)
        var = fix_timeaxis(var)

        dataset = asdataset([var])
        for load_hook in self.load_hooks:
          dataset = asdataset(load_hook(dataset))
        var = dataset.vars[0]

      # (end of time split)

      # Load into memory
      var = var.load()

      # Compute ranges for the data
      try:
        var.atts['low'] = np.nanpercentile(var.values, 0.1)
        var.atts['high'] = np.nanpercentile(var.values, 99.9)
      # Fall back for older versions of numpy.
      except AttributeError:
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
      for save_hook in self.save_hooks:
        dataset = asdataset(save_hook(dataset))
      # Re-save back to a big file
      netcdf.save (bigfile+".tmp", dataset, version=4)
      rename(bigfile+".tmp",bigfile)

    # (end of cache file creation)

    # Load the data from the big file
    dataset = netcdf.open(bigfile)

    # Apply any hooks for loading the var (extra metadata decoding?)
    for load_hook in self.load_hooks:
      dataset = asdataset(load_hook(dataset))
    var = dataset.vars[0]

    # Force the time axis (we lose information about whether this was a monthly
    # mean, etc. once we write into netcdf).
    var = var.replace_axes(time=taxis)

    return var

  # Give the name of the cache file that would be created when write() is called
  def where_write (self, *args, **kwargs):
    kwargs['_dryrun'] = True
    filename = self.write(*args, **kwargs)
    return filename

  # Determine if the data was already cached.
  def exists (self, *args, **kwargs):
    from os.path import exists
    filename = self.where_write(*args,**kwargs)
    if exists(filename): return True
    else: return False

  # Given a filename, add the appropriate directory structure.
  # Parameters:
  #   existing (default: False) -  If True, the file must already exist.
  #   writeable (default: False) - If True, the file must be in a writeable location.
  def full_path (self, filename, existing=False, writeable=False):

    from os.path import exists, dirname, join
    from os import mkdir

    dirs=[]
    # Look at the writeable directory first (if it exists)
    if self.write_dir is not None:
      dirs.append(self.write_dir)
    # If we don't need to be writeable, can look at read-only directories
    if not writeable:
      dirs.extend(self.read_dirs)

    for dir in dirs:
      if exists(join(dir,filename)): return join(dir,filename)

    # No existing file found.
    # Did we need a file that already exists?
    if existing:
      raise CacheReadError ("No existing copy of '%s' was found."%filename)

    # Otherwise, we need somewhere to write a new file.
    if self.write_dir is None:
      raise CacheWriteError ("Nowhere to write '%s'"%filename)

    # Do we need to make a subdirectory?
    if not exists(dirname(join(self.write_dir,filename))):
      mkdir(dirname(join(self.write_dir,filename)))

    return join(self.write_dir,filename)

