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
from data_interface import Data
class EC_Station_Data (Data):
  name = 'EC'
  title = 'EC Station Obs'

  indir = "/wrk1/EC-CAS/surface/EC-2011"
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
  )

  def __init__ (self):
    from pygeode.formats import netcdf
    from os.path import exists
    from pygeode.dataset import Dataset
    from common import common_taxis, fix_timeaxis

    cachefile = './ec_co2.nc'
    if not exists(cachefile):
      data = []
      for station in self.obs_locations.keys():
        filename = '%s/%s/%s-CO2-Hourly.DAT'%(self.indir,station,station)
        stuff = read_station_data(filename)
        stuff = [var.rename(station+'_'+var.name) for var in stuff]

        # Fix Egbert (only has measurements every *other* hour, on odd hours)
        if station == 'Egbert':
          stuff = [var.slice[1::2] for var in stuff]
        data.extend(stuff)
      data = common_taxis(*data)
      data = Dataset(data)
      data = fix_timeaxis(data)
      netcdf.save(cachefile,data)

    self.data = netcdf.open(cachefile)

  # Get some data at a station (e.g. CO2_mean)
  def get_data (self, station, product):

    if '_' not in product:
      raise KeyError ("Expected something of the form FIELD_STAT")

    fieldname, stat = product.rsplit('_',2)
    #if fieldname != 'CO2':
    #  raise KeyError("Only CO2 data is available from this interface")

    return self.data[station+'_'+stat]


del Data


