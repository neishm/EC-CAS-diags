# Interface for reading Transcom3 input data.

# Helper method - read a raw binary record
def read_array (f, axes, name):
  from pygeode.var import Var
  import numpy as np
  dimensions = [len(a) for a in axes]
  # Input is in big-endian?
  i4 = np.dtype('>i4')
  r8 = np.dtype('>f8')
  size = np.fromfile(file=f,dtype=i4,count=1)[0] / 8
  assert size == reduce(int.__mul__,dimensions,1)
  data = np.fromfile(file=f,dtype=r8,count=size)
  size2 = np.fromfile(file=f,dtype=i4,count=1)[0] / 8
  assert size2 == size
  data =  data.reshape(dimensions)
  return Var(axes, values=data, name=name)

class Transcom3(object):

  @staticmethod
  def open_file (filename):
    import numpy as np
    from pygeode.formats import netcdf
    from pygeode.axis import Lat, Lon, NamedAxis
    from pygeode.timeaxis import ModelTime365
    from pygeode.dataset import Dataset
    from subprocess import Popen, PIPE
    if filename.endswith("input.new.dat.Z"):
      infile = Popen(["uncompress", "-c", filename], bufsize=-1, stdout=PIPE).stdout
    elif filename.endswith("input.new.dat"):
      infile = open(filename,mode='rb')
    else:
      raise ValueError("Unrecognized file '%s'"%filename)

    lon = Lon(np.linspace(-179.75,179.75,720))
    lat = Lat(np.linspace(-89.75,89.75,360))
    landregion = NamedAxis(np.arange(1,12), name='landregion')
    oceanregion = NamedAxis(np.arange(1,12), name='oceanregion')
    month = ModelTime365(month=np.arange(1,13), units='days')

    ff90 = read_array(infile, (lat,lon), 'ff90')
    ff95 = read_array(infile, (lat,lon), 'ff95')
    nep  = read_array(infile, (month,lat,lon), 'nep')
    ocean= read_array(infile, (month,lat,lon), 'ocean')
    landunit = read_array(infile, (landregion,lat,lon), 'landunit')
    oceanunit = read_array(infile, (month,oceanregion,lat,lon), 'oceanunit')
    sf6  = read_array(infile, (landregion,lat,lon), 'sf6')

    return Dataset([ff90,ff95,nep,ocean,landunit,oceanunit,sf6])


  @staticmethod
  def decode (data):
    from pygeode.dataset import Dataset
    # Set up outputs
    # Right now, only need landunit & oceanunit.
    outdata = []
    if 'landunit' in data:
      for i in range(1,len(data.landregion)+1):
        var = data.landunit.squeeze(landregion=i)
        var.name = "CO2_landunit_%02d_flux"%i
        outdata.append(var)
    if 'oceanunit' in data:
      for i in range(1,len(data.oceanregion)+1):
        var = data.oceanunit.squeeze(oceanregion=i)
        var.name = "CO2_oceanunit_%02d_flux"%i
        outdata.append(var)

    # Set the units, 
    for var in outdata:
      var.atts['units'] = 'kg(C) m-2 s-1'
      var.atts['specie'] = 'CO2'

    return Dataset(outdata)

# Give this class a standard reference name, to make it easier to auto-discover.
interface = Transcom3


