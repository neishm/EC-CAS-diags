# GAW station data

from interfaces import StationObsProduct
class GAW_Station_Data(StationObsProduct):

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('CO2_mean', 'CO2',     'ppm'),
    ('CO2_std',  'CO2_std', 'ppm'),
  )

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from datetime import datetime, timedelta
    from pygeode.var import Var
    from pygeode.timeaxis import StandardTime
    from pygeode.dataset import Dataset
    from common import best_type
    from station_data import Station
    import numpy as np
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
      return Dataset([])

    # Get station name
    assert 'STATION NAME:' in comments[6]
    station_name = comments[6].split(':')[1].strip()

    # Get general metadata
    atts = {}
    for comment in comments:
      comment = comment[4:]
      # Ignore sections that start with '#' (meta-comment?)
      if comment.startswith('#'): continue
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

    # Define the time axis.  Use a consistent start date, so the various
    # station records can be more easily compared.
    time = StandardTime(year=year, month=month, day=day, hour=hour, minute=minute, units='hours', startdate={'year':1980,'month':1,'day':1})
    # Define the station axis.
    lat = float(atts['latitude'])
    lon = float(atts['longitude'])
    # Check for mis-spelling of 'territory'
    if 'country_territory' in atts:
      country = atts['country_territory']
    else:
      country = atts['country_teritory']
    station = Station([station_name], lat=[lat], lon=[lon], country=[country])

    # Wrap in PyGeode Vars
    mean = Var([time,station], values=np.asarray(values).reshape(-1,1), name='CO2_mean', atts=atts)
    std = Var([time,station], values=np.asarray(std).reshape(-1,1), name='CO2_std', atts=atts)

    return Dataset([mean,std])


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return glob(dirname+'/*.dat')

# Add this interface to the table.
from interfaces import table
table['gaw-station-obs'] = GAW_Station_Data

