# Generic data interface

class Data(object):

  # Cache the given data, with the given filename
  def _cache(self,data,filename):
    from pygeode.formats import netcdf
    from os.path import exists
    from os import mkdir
    import numpy as np

    # Make sure the data is in 32-bit precision
    if data.dtype.name != 'float32':
      data = data.as_type('float32')

    if not exists(self._tmpdir): mkdir(self._tmpdir)
    cachefile = self._tmpdir + '/' + filename

    # Pre-compute the data and save it, if this is the first time using it.
    if not exists(cachefile):
      print '===>', cachefile

      # Load the data into memory
      data = data.load()

      # Compute a range of the data
      sample = data.get().flatten()
      # Filter out NaN values
      sample = sample[np.isfinite(sample)]
      # Get a good range (covers most values)
      sample.sort()
      N = len(sample)
      low = sample[int(round((N-1)*0.001))]
      high = sample[int(round((N-1)*0.999))]
      data.atts['low'] = float(low)
      data.atts['high'] = float(high)

      netcdf.save(cachefile, data)

    data = netcdf.open(cachefile).vars[0]

    return data


