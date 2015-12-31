# EC station data

# Obs locations provided by Doug Chan (2015/05/06)
obs_locations = dict(
  Alert           = (82.451065,  -62.506771,   200, 'Canada'),
  Candle_Lake     = (53.987108, -105.117939,   600, 'Canada'),
  Egbert          = (44.231006,  -79.783839,   251, 'Canada'),
  Chibougamau     = (49.69251,   -74.342296,   393, 'Canada'),
  Estevan_Point   = (49.382935, -126.544097,     7, 'Canada'),
  Fraserdale      = (49.875168,  -81.569774,   210, 'Canada'),
  Lac_Labiche     = (54.953809, -112.466649,   540, 'Canada'),
  Sable_Island    = (43.93227,   -60.01256,      5, 'Canada'),
  Bratts_Lake     = (50.201631, -104.711259,   595, 'Canada'),
  Esther          = (51.669987, -110.206175,   707, 'Canada'),
  Toronto         = (43.780491,  -79.46801,    198, 'Canada'),
  East_Trout_Lake = (54.353743, -104.986864,   493, 'Canada'),
  Behchoko        = (62.797934, -115.918255,   160, 'Canada'),
  Churchill       = (58.737902,  -93.820581,    29, 'Canada'),
  Cambridge_Bay   = (69.128401, -105.057707,    35, 'Canada'),
  Abbotsford      = (49.011313, -122.335505,  60.3, 'Canada'),
  Inuvik          = (68.317817, -133.534232,   113, 'Canada'),
  Turkey_Point    = (42.636451,  -80.554695,   231, 'Canada'),
  Chapais         = (49.822317,  -74.975274,   381, 'Canada'),
  Baker_Lake      = (64.331665,  -96.010433,  94.8, 'Canada'),
  Fort_McKay      = (57.187925, -111.642723,   250, 'Canada'),
  AMS13           = (57.149167, -111.6425,     250, 'Canada'),
  UofT            = (43.660465,  -79.398274, 109.8, 'Canada'),
)

from . import StationObsProduct
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
    from ..station_data import Station

    station, tracer, period = basename(filename).rstrip('.DAT').split('-')
    lat, lon, elevation, country = obs_locations[station]
    station = Station([station], lat=[lat], lon=[lon], elevation=[elevation], country=[country])

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
    taxis = StandardTime (values=taxis.values, units=taxis.units, startdate=taxis.startdate)

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
    files = glob(dirname+'/*-*-Hourly.DAT')
    # Exclude extra files in methane directory (e.g. Lac_Labiche2-CH4-Hourly.DAT)
    files = [f for f in files if '2-CH4' not in f]
    return files

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    import os
    for d in reversed(dirname.split(os.sep)):
      if d.startswith('EC-'): return d
    return None



# Add this interface to the table.
from . import table
table['ec-station-obs'] = EC_Station_Data

