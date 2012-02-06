from glob import glob
from datetime import datetime, timedelta

from pygeode.var import Var
from pygeode.timeaxis import StandardTime
from pygeode.dataset import asdataset

from common import best_type, common_taxis

varlist = []

for filename in glob ("/wrk1/nassar/obs/GAW-2012/co2/hourly/y2009/*.dat"):
  print filename
  f = open(filename,'ro')
  comments = []
  year = []
  month = []
  day = []
  hour = []
  minute = []
  values = []
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

  except ValueError:
    print 'skipping file with shitty formatting'
    continue

  # Get station name
  assert 'STATION NAME:' in comments[6]
  name = comments[6].split(':')[1].strip()

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
  data = Var([time], values=values, name=name, atts=atts)

  varlist.append(data)

varlist = common_taxis(*varlist)
data = asdataset(varlist)
del varlist


from pygeode.formats import netcdf as nc
nc.save("gaw.nc", data)

