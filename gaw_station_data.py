
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

  # Add units
  atts['units'] = 'ppm'

  # Wrap in PyGeode Var
  time = StandardTime(year=year, month=month, day=day, hour=hour, minute=minute, units='hours')
  mean = Var([time], values=values, name=station_name+'_CO2_mean', atts=atts)
  std = Var([time], values=std, name=station_name+'_CO2_std', atts=atts)

  return [mean,std]


from data_interface import Data
class GAW_Station_Data (Data):
  name = 'GAW'
  title = 'GAW-2012 Station Obs'

  indir = "/wrk1/EC-CAS/surface/GAW-2012/co2/hourly/y2009"

  def __init__ (self):

    from glob import glob
    from pygeode.dataset import Dataset
    from pygeode.formats import netcdf
    from os.path import exists

    from common import common_taxis, fix_timeaxis

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

      data = Dataset(data)
      data = fix_timeaxis(data)
      netcdf.save(cachefile, data)

    data = netcdf.open(cachefile)

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

    # Fix Egbert data - they're missing every other hour
    data = data.replace_vars(Egbert_CO2_mean = data.Egbert_CO2_mean.slice[1::2].rename_axes(time='time01'),
                             Egbert_CO2_std = data.Egbert_CO2_std.slice[1::2].rename_axes(time='time01'))

    self.data = data
    self.obs_locations = obs_locations

  def get_data (self, station, field, stat='mean'):
    return self.data[station+'_'+field+'_'+stat]


del Data

