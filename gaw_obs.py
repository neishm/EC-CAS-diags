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

data = data.replace_vars(Egbert = data.Egbert.slice[1::2])
