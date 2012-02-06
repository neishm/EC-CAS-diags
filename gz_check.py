# Compare the station heights to what height the model sees for that grid point.

from gaw_obs import obs_locations, data as obs
from model import gz

# Take GZ at the 'surface' level of the model, and assume it doesn't vary with time.
gz2 = gz(i_time=0).squeeze(eta=0.995)*10
gz = gz(i_time=0).squeeze(eta=1)*10

print "%40s%30s%10s%10s%15s%15s"%('Location', 'Country', 'Lat', 'Lon', 'obs height', 'model height')
print '-'*120

for location in sorted(obs_locations.keys()):
  lat, lon, country = obs_locations[location]
  if lon < 0: lon += 360
  print "%40s%30s%10.2f%10.2f%15d%15d"%(location,country,lat,lon,obs[location].atts['altitude'], gz.squeeze(lat=lat,lon=lon).get()), gz2.squeeze(lat=lat,lon=lon).get()

