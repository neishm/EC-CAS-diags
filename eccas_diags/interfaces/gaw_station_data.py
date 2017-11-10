###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################


# GAW station data

from . import SplitProduct
class GAW_Station_Data(SplitProduct):
  """
  Greenhouse gas measurments from the GAW network.
  """

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
    from datetime import datetime, timedelta
    from pygeode.var import Var
    from pygeode.timeaxis import StandardTime
    from pygeode.dataset import Dataset
    from ..common import best_type
    from ..station_data import Station
    import numpy as np
    from re import search
    f = open(filename,'ro')
    specie = 'Unknown'
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

        # Get time zone info
        if line.startswith('C24 TIME ZONE: '):
          fudge = search("UTC(.*)",line).group(1)
          if fudge == "": fudge = "0"
          tz_fudge = timedelta(hours=-int(fudge))
        # Get specie info
        if line.startswith('C18 PARAMETER: '):
          specie = line.split(':')[1].strip()

        if line.startswith('C'):
          comments.append(line)
        else:
          date1, time1, date2, time2, val, nd, sd, f, cs, rem = line.split()

          # In what universe does 24-hour time go from 1:00 to 24:00????
          fudge = tz_fudge
          if time1 == '24:00':
            time1 = '23:00'
            fudge = fudge + timedelta(hours=1)

          time = datetime.strptime(date1+' '+time1, "%Y-%m-%d %H:%M") + fudge
          year.append(time.year)
          month.append(time.month)
          day.append(time.day)
          hour.append(time.hour)
          minute.append(time.minute)

          val = float(val)
          if val < 0: val = float('nan')
          values.append(val)

          sd = float(sd)
          if sd < 0: sd = float('nan')
          std.append(sd)

    except (ValueError,AttributeError) as e:
      print 'skipping %s - bad formatting'%filename
      print 'message:', e.message
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
    time = StandardTime(year=year, month=month, day=day, hour=hour, units='hours', startdate={'year':1980,'month':1,'day':1})
    # Define the station axis.
    lat = float(atts['latitude'])
    lon = float(atts['longitude'])
    altitude = float(atts['altitude'])
    # Check for mis-spelling of 'territory'
    if 'country_territory' in atts:
      country = atts['country_territory']
    else:
      country = atts['country_teritory']
    station = Station([station_name], station=[station_name], lat=[lat], lon=[lon], altitude=[altitude], country=[country])

    # Wrap in PyGeode Vars
    mean = Var([time,station], values=np.asarray(values).reshape(-1,1), name=specie+'_mean', atts=atts)
    std = Var([time,station], values=np.asarray(std).reshape(-1,1), name=specie+'_std', atts=atts)

    return Dataset([mean,std])


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return sorted(glob(dirname+'/*.dat'))

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    type = 'unknown'
    import os
    for d in reversed(dirname.split(os.sep)):
      if d in ('hourly','event'):
        type = d
      if d.startswith('GAW-'): return d+'-'+type
      # Special case - Doug's directory (no version info available?)
      if d == 'gaw_ch4_obs': return d+'-'+type
    return None


# Add this interface to the table.
from . import table
table['gaw-station-obs'] = GAW_Station_Data

