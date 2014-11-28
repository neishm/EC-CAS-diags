import numpy as np
from pygeode.formats import netcdf
from pygeode.axis import Lat, Lon, NamedAxis
from pygeode.timeaxis import ModelTime365
from subprocess import Popen, PIPE


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

infile = Popen(["uncompress", "-c", "/wrk6/chan/transcom/fluxes/input.new.dat.Z"], bufsize=-1, stdout=PIPE).stdout

lon = Lon(np.linspace(-179.75,179.75,720))
lat = Lat(np.linspace(-89.75,89.75,360))
landregion = NamedAxis(np.arange(1,12), name='landregion')
oceanregion = NamedAxis(np.arange(1,12), name='oceanregion')
month = ModelTime365(month=np.arange(1,13))

ff90 = read_array(infile, (lat,lon), 'ff90')
ff95 = read_array(infile, (lat,lon), 'ff95')
nep  = read_array(infile, (month,lat,lon), 'nep')
ocean= read_array(infile, (month,lat,lon), 'ocean')
landunit = read_array(infile, (landregion,lat,lon), 'landunit')
oceanunit = read_array(infile, (month,oceanregion,lat,lon), 'oceanunit')
sf6  = read_array(infile, (landregion,lat,lon), 'sf6')

netcdf.save("/wrk6/neish/tmp/transcom_test.nc",[ff90,ff95,nep,ocean,landunit,oceanunit,sf6])

