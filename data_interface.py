# Generic data interface

class Data(object):

  # Cache the given data, with the given filename
  def _cache(self,data,filename):
    from pygeode.formats import netcdf
    from os.path import exists
    from os import mkdir

    # Make sure the data is in 32-bit precision
    if data.dtype.name != 'float32':
      data = data.as_type('float32')

    if not exists(self._tmpdir): mkdir(self._tmpdir)
    cachefile = self._tmpdir + '/' + filename

    # Pre-compute the data and save it, if this is the first time using it.
    if not exists(cachefile):
      print '===>', cachefile
      netcdf.save(cachefile, data)

    data = netcdf.open(cachefile).vars[0]

    return data

