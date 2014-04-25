# EC station data

# Grab data from a single file
def read_station_data (filename):

  import numpy as np
  from pygeode.timeaxis import StandardTime
  from pygeode import Var

  f = open(filename, "r")
  header = f.readline()
  data = zip(*[line.rstrip('\n').split(',') for line in f])
  f.close

  decyear = np.array ([float(x) for x in data[0]])
  year    = np.array ([int(x) for x in data[1]])
  doy     = np.array ([int(x) for x in data[2]])
  hourend = np.array ([int(x) for x in data[3]])
  mean    = np.array ([float(x) for x in data[4]])
  maxval  = np.array ([float(x) for x in data[5]])
  minval  = np.array ([float(x) for x in data[6]])
  std     = np.array ([float(x) for x in data[7]])
  nval    = np.array ([int(x) for x in data[8]])

  taxis = StandardTime (year=year, month=np.ones(len(year)), day=doy, hour=hourend, units='hours')

  mean   = Var([taxis], values=mean, name='mean')
  maxval = Var([taxis], values=maxval, name='max')
  minval = Var([taxis], values=minval, name='min')
  std    = Var([taxis], values=std, name='std')
  nval   = Var([taxis], values=nval, name='nval')

  return mean, maxval, minval, std, nval

# Data interface for EC station observations
class EC_Station_Data (object):
  name = 'EC'
  title = 'EC Station Obs'

  obs_locations = dict(
    East_Trout_Lake = (54.3500, -104.9833, 'Canada'),
    Chibougamau     = (49.6833,  -74.3333, 'Canada'),
    Alert           = (82.4500,  -62.5167, 'Canada'),
    Esther          = (51.6825, -110.2603, 'Canada'),
    Bratts_Lake     = (51.2,    -104.7   , 'Canada'),
    Egbert          = (44.2167,  -79.7833, 'Canada'),
    Candle_Lake     = (53.9833, -105.1167, 'Canada'),
    Toronto         = (43.7833,  -79.4667, 'Canada'),
    Fraserdale      = (49.8833,  -81.5667, 'Canada'),
    Estevan_Point   = (49.5833, -126.8667, 'Canada'),
    Sable_Island    = (43.9333,  -60.0167, 'Canada'),
    Lac_Labiche     = (54.95,   -112.45, 'Canada'),
#    Behchoko        = (62.8025, -116.0464, 'Canada'),
#    Cambridge_Bay   = (69.1172, -105.0531, 'Canada'),
#    Chapais         = (49.7833, -74.85, 'Canada'),
#    Churchill       = (58.7692, -94.16917, 'Canada'),
#    Inuvik          = (68.3617, -133.7306, 'Canada'),
#    Turkey_Point    = (42.681047,-80.332289, 'Canada'),
  )

  def __init__ (self):
    from pygeode.formats import netcdf
    from os.path import exists
    from pygeode.dataset import Dataset
    from common import common_taxis, fix_timeaxis
    from glob import glob
    from station_data import make_station_axis, encode_station_data, decode_station_data
    from pygeode.var import Var
    import numpy as np

    cachefile = './ec_obs.nc'
    if not exists(cachefile):
      data = {}
      for station in self.obs_locations.keys():
       for field,units,indir in [['CO2','ppm',"/wrk1/EC-CAS/surface/EC-2013"], ['CH4','ppb',"/wrk1/EC-CAS/surface_ch4/EC-2013"]]:
        filename = '%s/%s-%s-Hourly*.DAT'%(indir,station,field)
        # Needed for Esther CH4 data (to expand wildcard above)
        filename = glob(filename)[0]
        stuff = read_station_data(filename)
        # Put the expected units in here
        for var in stuff: var.atts['units'] = units

        data[(station,field,'mean')] = stuff[0]
        data[(station,field,'max')] = stuff[1]
        data[(station,field,'min')] = stuff[2]
        data[(station,field,'std')] = stuff[3]
        data[(station,field,'nval')] = stuff[4]

      # Create a common time axis over all data
      keys, vars = zip(*data.iteritems())
      vars = common_taxis(*vars)
      data = dict(zip(keys,vars))
      time = vars[0].time

      # Create a station axis
      stations = make_station_axis(self.obs_locations)

      fields = list(set(field for station,field,stat in data.iterkeys()))
      stats = list(set(stat for station,field,stat in data.iterkeys()))

      # Create the 2D datasets
      big_data = []
      for field in fields:
        for stat in stats:
          array = np.empty([len(time),len(stations)], dtype='float32')
          for i, station in enumerate(stations.values):
            array[:,i] = data[(station,field,stat)].get()
            units = data[(station,field,stat)].atts['units']
          var = Var([time,stations], values=array, name=field+'_'+stat)
          var.atts['units'] = units
          big_data.append(var)


      data = Dataset(big_data)
      data = fix_timeaxis(data)

      # Save the data
      data = encode_station_data(data)
      netcdf.save(cachefile,data)

      # End of cache file creation

    data = netcdf.open(cachefile)
    self.data = decode_station_data(data)

  # Get some data at a station (e.g. CO2_mean)
  def get_data (self, station, fieldname, stat='mean'):
    import numpy as np

    stations = self.data.station.values
    if station not in stations: raise KeyError

    s = np.where(stations == station)[0][0]

    return self.data[fieldname+'_'+stat](i_station=s).squeeze('station')
