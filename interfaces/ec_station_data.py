# EC station data

# Hard-code the observation locations, since this information isn't provided
# in the data!
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
  Behchoko        = (62.8025, -116.0464, 'Canada'),
  Cambridge_Bay   = (69.1172, -105.0531, 'Canada'),
  Chapais         = (49.7833, -74.85, 'Canada'),
  Churchill       = (58.7692, -94.16917, 'Canada'),
  Inuvik          = (68.3617, -133.7306, 'Canada'),
  Turkey_Point    = (42.681047,-80.332289, 'Canada'),
)

from interfaces import StationObsProduct
class EC_Station_Data(StationObsProduct):

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('CO2_mean', 'CO2',     'ppm'),
    ('CO2_std',  'CO2_std', 'ppm'),
    ('CH4_mean', 'CH4',     'ppb'),
    ('CH4_std',  'CH4_std', 'ppb'),
  )


  # Method to open a single file
  @staticmethod
  def open_file (filename):

    import numpy as np
    from pygeode.timeaxis import StandardTime
    from pygeode import Var
    from pygeode.dataset import asdataset
    from os.path import basename
    from station_data import Station

    station, tracer, period = basename(filename).rstrip('.DAT').split('-')
    lat, lon, country = obs_locations[station]
    station = Station([station], lat=[lat], lon=[lon], country=[country])

    # Read the data and put each column into an array.
    with open(filename, "r") as f:
      header = f.readline()
      data = zip(*[line.rstrip('\n').split(',') for line in f])

    decyear = np.array ([float(x) for x in data[0]])
    year    = np.array ([int(x) for x in data[1]])
    doy     = np.array ([int(x) for x in data[2]])
    hourend = np.array ([int(x) for x in data[3]])
    mean    = np.array ([float(x) for x in data[4]])
    maxval  = np.array ([float(x) for x in data[5]])
    minval  = np.array ([float(x) for x in data[6]])
    std     = np.array ([float(x) for x in data[7]])
    nval    = np.array ([int(x) for x in data[8]])

    # Define the time axis.  Use a consistent start date, so the various
    # station records can be more easily compared.
    taxis = StandardTime (year=year, month=np.ones(len(year)), day=doy, hour=hourend, units='hours', startdate={'year':1980,'month':1,'day':1})

    # Build the variables.
    mean   = Var([taxis,station], values=mean.reshape(-1,1), name=tracer+'_mean')
    maxval = Var([taxis,station], values=maxval.reshape(-1,1), name=tracer+'_max')
    minval = Var([taxis,station], values=minval.reshape(-1,1), name=tracer+'_min')
    std    = Var([taxis,station], values=std.reshape(-1,1), name=tracer+'_std')
    nval   = Var([taxis,station], values=nval.reshape(-1,1), name=tracer+'_nval')

    return asdataset([mean, maxval, minval, std, nval])


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return glob(dirname+'/*-*-Hourly.DAT')

# Add this interface to the table.
from interfaces import table
table['ec-station-obs'] = EC_Station_Data

