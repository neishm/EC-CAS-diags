from pygeode.timeaxis import StandardTime, months
from pygeode.var import Var
from pygeode.dataset import asdataset

from common import convert_CO2, fix_timeaxis
from ec_obs import obs_locations


# Read Shuzhan's files
varlist = []
for location in obs_locations.keys():
  filename = "shuzhan_timeseries/timeseries_CO2_2009010100_2009030100_at%s"%location
  data = list(open(filename,'ro'))
  times = data[::2]
  data = data[1::2]
  year  = [int(t[0:4]) for t in times]
  month = [int(t[4:6]) for t in times]
  day   = [int(t[6:8]) for t in times]
  hour  = [int(t[8:10]) for t in times]
  data = [float(d.split()[0])*convert_CO2 for d in data]
  time = StandardTime(year=year, month=month, day=day, hour=hour)
  data = Var([time], values=data, name=location)
  varlist.append(data)
data = asdataset(varlist)
del varlist


# Normalize the time axes to the same start date / units
data = fix_timeaxis(data)

