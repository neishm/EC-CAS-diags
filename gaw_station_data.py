
# Get station data from a file
def read_station_data (filename):
  from datetime import datetime, timedelta
  from pygeode.var import Var
  from pygeode.timeaxis import StandardTime
  from common import best_type
  f = open(filename,'ro')
  comments = []
  year = []
  month = []
  day = []
  hour = []
  minute = []
  values = []
  std = []
  try:

    for line in f:
      line = line.rstrip('\n')
      if line.startswith('C'):
        comments.append(line)
      else:
        date1, time1, date2, time2, co2, nd, sd, f, cs, rem = line.split()

        # In what universe does 24-hour time go from 1:00 to 24:00????
        if time1 == '24:00':
          time1 = '23:00'
          fudge = timedelta(hours=1)
        else:
          fudge = timedelta(hours=0)

        time = datetime.strptime(date1+' '+time1, "%Y-%m-%d %H:%M") + fudge
        year.append(time.year)
        month.append(time.month)
        day.append(time.day)
        hour.append(time.hour)
        minute.append(time.minute)

        co2 = float(co2)
        if co2 < 0: co2 = float('nan')
        values.append(co2)

        sd = float(sd)
        if sd < 0: sd = float('nan')
        std.append(sd)

  except ValueError:
    print 'skipping %s - bad formatting'%filename
    return [None,None]

  # Get station name
  assert 'STATION NAME:' in comments[6]
  station_name = comments[6].split(':')[1].strip()

  # Get general metadata
  atts = {}
  for comment in comments:
    comment = comment[4:]
    if comment.strip() == '': break  # end of comments (ignore header after the blank line)
    if ':' in comment:
#      print '??', comment
      attname, attval = comment.split(':',1)
      attname = attname.replace(' ', '_')
      attname = attname.replace('/', '_')
      attname = attname.lower()
      attval = best_type(attval.strip())
      atts[attname] = attval
    else:  # continuation?
      atts[last_attname] += '\n' + comment

    last_attname = attname

  # Wrap in PyGeode Var
  time = StandardTime(year=year, month=month, day=day, hour=hour, minute=minute, units='hours')
  mean = Var([time], values=values, name=station_name+'_CO2_mean', atts=atts)
  std = Var([time], values=std, name=station_name+'_CO2_std', atts=atts)

  return [mean,std]


def gaw_station_opener (filename):
  from pygeode.formats import netcdf
  from station_data import station_axis_load_hook
  data = netcdf.open(filename)
  data = station_axis_load_hook(data)
  return data

class GAW_Station_Data (object):
  name = 'GAW'
  title = 'GAW-2014 Station Obs'

  indir = "/wrk1/EC-CAS/surface/GAW-2014/co2/hourly/y2009"

  def __init__ (self):

    from glob import glob
    from pygeode.dataset import Dataset
    from pygeode.formats import netcdf
    from pygeode.var import Var
    from os.path import exists
    import numpy as np

    from common import common_taxis, fix_timeaxis
    from station_data import make_station_axis, station_axis_save_hook
    from data_interface import DataInterface

    cachefile = './gaw_obs.nc'

    if not exists(cachefile):

      data = sum([read_station_data(filename) for filename in glob (self.indir+"/*.dat")],[])
      # Filter out bad data
      data = [d for d in data if d is not None]
      data = common_taxis(*data)

      # Use only one version of each station (first file found)
      unique_names = []
      unique = []
      for d in data:
        if d.name in unique_names: continue
        unique_names.append(d.name)
        unique.append(d)
      data = unique

      # Fill in location info
      obs_locations = {}
      for var in data:
        lat = float(var.atts['latitude'])
        lon = float(var.atts['longitude'])
        # Check for mis-spelling of 'territory'
        if 'country_territory' in var.atts:
          country = var.atts['country_territory']
        else:
          country = var.atts['country_teritory']
        obs_locations[var.name.rsplit('_',2)[0]] = (lat, lon, country)
      del var, lat, lon, country

      # Create a station axis
      stations = make_station_axis (obs_locations)

      # Find a suitable time axis
      time = data[0].time

      # Create large arrays to hold the data.
      co2_mean = np.empty([len(time),len(stations)], dtype='float32')
      co2_std = np.empty([len(time),len(stations)], dtype='float32')

      station_list = list(stations.values)
      for var in data:
        key = var.name
        if key.endswith('_CO2_mean'):
          station = key[:-9]
          s = station_list.index(station)
          co2_mean[:,s] = var.get()
        elif key.endswith('_CO2_std'):
          station = key[:-8]
          s = station_list.index(station)
          co2_std[:,s] = var.get()
        else: raise KeyError

      co2_mean = Var([time,stations], name='CO2_mean', values=co2_mean, atts={'units':'ppm'})
      co2_std = Var([time,stations], name='CO2_std', values=co2_std, atts={'units':'ppm'})

      data = Dataset([co2_mean, co2_std])
      data = fix_timeaxis(data)

      data = station_axis_save_hook(data)
      netcdf.save(cachefile, data)

      # End of cache file creation

    data = DataInterface.from_files([cachefile], opener=gaw_station_opener)

    # Rename CO2_mean to CO2
    data = data.filter(strip_mean)

    self.data = data

    # Find obs locations from the file
    #TODO: remove this once the diagnostics use the station axis directly.
    obs_locations = {}
    data = self.data.find_best('CO2')
    stations = data.station.values
    lats = data.station.lat
    lons = data.station.lon
    countries = data.station.country
    for station,lat,lon,country in zip(stations,lats,lons,countries):
      obs_locations[station] = (lat,lon,country)
    self.obs_locations = obs_locations

# Helper function - filter out '_mean' suffix from data
def strip_mean (varlist):
  out = []
  for var in varlist:
    if var.name.endswith('_mean'):
      var = var.rename(var.name.rsplit('_mean')[0])
    out.append(var)
  return out


