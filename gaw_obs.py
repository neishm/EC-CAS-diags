from pygeode.formats import netcdf as nc
from common import fix_timeaxis

data = nc.open("gaw.nc")
data = fix_timeaxis(data)

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
  obs_locations[var.name] = (lat, lon, country)
del var, lat, lon, country

# Patch up Egbert station
# (They never have 2 consecutive hours of data, so no lines would get drawn
#  on plots unless we remove the 'gaps' in between.
import numpy as np
from pygeode.var import Var
from pygeode.timeaxis import StandardTime
Egbert = data.Egbert
values = Egbert.get()
times = Egbert.time.get()
indices = np.where(~np.isnan(values))
values = values[indices]
times = times[indices]
times = StandardTime(times, startdate=Egbert.time.startdate, units=Egbert.time.units)
Egbert = Var([times], values=values, name='Egbert', atts=Egbert.atts)
data = data.replace_vars(Egbert = Egbert)
del np, Egbert, values, times, indices
del Var, StandardTime
