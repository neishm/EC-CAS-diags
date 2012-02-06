from pygeode.formats import netcdf as nc
from common import fix_timeaxis
from pygeode.dataset import asdataset

obs_locations = dict(
  East_Trout_Lake = (54.3500, -104.9833),
  Chibougamau     = (49.6833,  -74.3333),
  Alert           = (82.4500,  -62.5167),
  Esther          = (51.6825, -110.2603),
  Bratts_Lake     = (51.2,    -104.7   ),
  Egbert          = (44.2167,  -79.7833),
  Candle_Lake     = (53.9833, -105.1167),
  Toronto         = (43.7833,  -79.4667),
  Fraserdale      = (49.8833,  -81.5667),
  Estevan_Point   = (49.5833, -126.8667),
  Sable_Island    = (43.9333,  -60.0167),
  Lac_Labiche     = (54.95,   -112.45),
)

# Add country info
for location in obs_locations.keys():
  obs_locations[location] += ('Canada',)

# Remove obs with no data for this time period
#del obs_locations['Bratts_Lake']
#del obs_locations['Egbert']
#del obs_locations['Estevan_Point']
#del obs_locations['Esther']

data = nc.open("co2_sfc_obs.nc")
varlist = list(data)
varlist = [var.rename(var.name[:-9]) for var in varlist if var.name.endswith('_CO2_mean')]
data = asdataset(varlist)
data = fix_timeaxis(data)

# Fix Egbert (only has measurements every *other* hour, on odd hours)
data = data.replace_vars(Egbert = data.Egbert.slice[1::2])
