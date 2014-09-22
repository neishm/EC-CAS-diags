# EC station data

from datetime import datetime, timedelta
from pygeode.timeaxis import StandardTime
import numpy as np

# Hard-code the start/end dates of the whole dataset
# (Make this period big enough to contain all the data).
start_date = datetime(year=1988, month=1, day=1)  # Don't change this one!
end_date = datetime(year=2013, month=12, day=31)  # You can change this one, though.


# Derive a common time axis from this date range
# (will be applied to all stations)
time_values = np.arange((end_date - start_date).total_seconds() / 3600, dtype=int)
common_timeaxis = StandardTime(startdate = dict(year=start_date.year, month=start_date.month, day=start_date.day), values = time_values, units='hours')

del datetime, timedelta, StandardTime, np, time_values


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

# Specify the different tracers that could be available (and the units)
tracer_info = dict(
  CO2 = 'ppm',
  CH4 = 'ppb',
)

# Method to open a single file
def open_file (filename):

  import numpy as np
  from pygeode.timeaxis import StandardTime
  from pygeode import Var
  from pygeode.dataset import asdataset
  from os.path import basename
  from station_data import Station

  station, tracer, period = basename(filename).rstrip('.DAT').split('-')
  station = Station([station])

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

  taxis = StandardTime (year=year, month=np.ones(len(year)), day=doy, hour=hourend, units='hours', startdate=common_timeaxis.startdate)

  # Define the variables
  # Need to add a station axis here, to force DataInterface to treat each
  # station separately (otherwise, it may merge different station data along
  # the time axis).
  # Instead, we'll re-combine all the stations together explicitly at the end.
  mean   = Var([taxis], values=mean, name=tracer+'_mean').extend(1,station)
  maxval = Var([taxis], values=maxval, name=tracer+'_max').extend(1,station)
  minval = Var([taxis], values=minval, name=tracer+'_min').extend(1,station)
  std    = Var([taxis], values=std, name=tracer+'_std').extend(1,station)
  nval   = Var([taxis], values=nval, name=tracer+'_nval').extend(1,station)

  return asdataset([mean, maxval, minval, std, nval])


# Method to decode an opened dataset (standardize variable names, and add any
# extra info needed (pressure values, cell area, etc.)
def decode (varlist):
  from station_data import Station
  from common import embiggen_axis
  varlist = list(varlist)

  # Get a proper station axis (fill in the location info)
  stations = varlist[0].station.values
  lat, lon, country = zip(*[obs_locations[s] for s in stations])
  station_axis = Station(stations, lat=lat, lon=lon, country=country)

  varlist = [var.replace_axes(station=station_axis) for var in varlist]

  # Strip 'mean' suffix
  for var in varlist:
    if var.name.endswith('_mean'):
      var.name = var.name.rstrip('_mean')
      name = var.name  # Remember this for later use

  # Get the proper units
  units = tracer_info[name]
  for var in varlist:
    if not var.name.endswith('_nval'):
      var.atts['units'] = units

  # Impose a common time axis on the data (will be shared with all stations)
  for i, var in varlist:
    varlist[i] = embiggen_axis (var, 'time', common_timeaxis)


  return varlist


# Method to find all files in the given directory, which can be accessed
# through this interface.
def find_files (dirname):
  from glob import glob
  return glob(dirname+'/*-*-Hourly.DAT')


# Need special hooks for saving to netcdf and loading back in
# (in order to preserve the station axis)
from station_data import station_axis_save_hook as save_hook, station_axis_load_hook as load_hook

# Re-combine all the stations into a single domain.
#NOTE: not used (and not completed)
def finalize_datasets (datasets):
  from pygeode.dataset import asdataset
  from common import embiggen_axis

  # If everything is already in a single dataset, then there's nothing to do.
  if len(datasets) == 1: return datasets

  # Collect everything into a common time axis
  taxis = [set(dataset.time.values) for dataset in datasets]
  taxis = reduce(set.union, taxis, set())
  taxis = sorted(taxis)
  taxis = taxis = datasets[0].time.withnewvalues(taxis)

#  # Expand all the variables onto this time axis
#  varlist = [embiggen_axis(v,'time',taxis) for dataset in datasets for v in dataset]

#  return varlist

  # Concatenate variables together
  # Organize the data into a lookup table by variable name
  vardict = dict()
  for dataset in datasets:
    for var in dataset:
      var = embiggen_axis(var,'time',taxis)
      vardict.setdefault(var.name,[]).append(var)

  #TODO

  # Create a common time axis for all variables
  for name in vardict.keys():
    vardict[name] = common_taxis(*vardict[name])

  return [asdataset(varlist) for varlist in vardict.itervalues()]


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

# A routine to open the netcdf data (and decode the station axis)
def ec_station_opener (filename):
  from pygeode.formats import netcdf
  from station_data import station_axis_load_hook
  data = netcdf.open(filename)
  data = station_axis_load_hook(data)
  return data

# Data interface for EC station observations
class EC_Station_Data (object):
  name = 'EC'
  title = 'EC Station Obs'


  def __init__ (self):
    from pygeode.formats import netcdf
    from os.path import exists
    from pygeode.dataset import Dataset
    from common import common_taxis, fix_timeaxis
    from glob import glob
    from station_data import make_station_axis, station_axis_save_hook
    from pygeode.var import Var
    import numpy as np
    from data_interface import DataInterface

    cachefile = './ec_obs.nc'
    if not exists(cachefile):
      data = {}
      for station in obs_locations.keys():
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
      stations = make_station_axis(obs_locations)

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
          if not var.name.endswith('_nval'):
            var.atts['units'] = units
          big_data.append(var)


      data = Dataset(big_data)
      data = fix_timeaxis(data)

      # Save the data
      data = station_axis_save_hook(data)
      netcdf.save(cachefile,data)

      # End of cache file creation

    self.data = DataInterface.from_files([cachefile], opener=ec_station_opener)

    # Rename CO2_mean to CO2
    self.data = self.data.filter(strip_mean)


# Helper function - filter out '_mean' suffix from data
def strip_mean (varlist):
  out = []
  for var in varlist:
    if var.name.endswith('_mean'):
      var = var.rename(var.name.rsplit('_mean')[0])
    out.append(var)
  return out

