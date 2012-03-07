from model_stuff import my_data
from common import convert_CO2

import numpy as np

co2 = my_data("validation_run_32bit")['km_sfc']['CO2'] * convert_CO2

time = co2.time
for year in sorted(set(time.year)):
  for month in sorted(set(time(year=year).month)):
    for day in sorted(set(time(year=year,month=month).day)):
      for hour in sorted(set(time(year=year,month=month,day=day).hour)):
        data = co2(year=year,month=month,day=day,hour=hour).squeeze().get()
        coords = np.where(data<1)
        lats = co2.lat.values[coords[0]]
        lons = co2.lon.values[coords[1]]
        assert len(lats) == len(lons)
        for lat,lon in zip(lats,lons):
          value = co2(year=year,month=month,day=day,hour=hour,lat=lat,lon=lon).get()
          print "%04d-%02d-%02d %02d:00 (%f,%f): %f"%(year,month,day,hour,lat,lon,value)

quit()

# Count the number of grid points that go down to ~0 ppmV (?!)

print 'shape:', co2.shape
print 'total gridpoints:', co2.size
print 'number of holes:', ((co2<1)*1).sum()
print 'number of near holes:', ((co2<=10)*1).sum()
print 'number of really low values:', ((co2<=100)*1).sum()
