from interfaces import experiment, experiment_name
from common import convert_CO2
from pygeode.formats import netcdf

co2 = experiment['sfc']['CO2'] * convert_CO2

holes = (co2 < 100)

count = (holes * 1).sum('time')
count.name = "hole_count"

netcdf.save("%s_hole_count.nc"%experiment_name, count)

