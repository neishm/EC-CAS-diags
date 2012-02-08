# Read globalview "extended record" data, convert to a single netcdf file

from glob import glob
from re import search

from pygeode.var import Var
from pygeode.axis import TAxis
from pygeode.formats import netcdf as nc

varlist = []

# Loop over all station data
for filename in glob("/wrk1/neish/globalview/gv_co2/*0_ext.co2"):
  varname = search("([a-z0-9]+_[0-9]{2}[A-Z][0-9])_ext\.co2$", filename).group(1)
  # Grab the smoothed values and timesteps
  times = []; values = []
  coord_line = False; lat=None; lon=None; alt=None; lst2utc=None
  for line in open(filename):

    if line.startswith('#'):
      if coord_line:
        lat, lon, alt, lst2utc = line.lstrip('#').split()
        coord_line = False
      if ' lat ' in line:
        coord_line = True  # next line contains coordinates
      continue  # ignore the rest of the headers

    time, value, ref, diff = line.split()
    times.append(float(time))
    values.append(float(value))
  times = TAxis(times, name='time')
  values = [v if v > 0 else float('nan') for v in values]
  atts = dict(lat=float(lat), lon=float(lon), alt=float(alt), lst2utc=float(lst2utc))
  varlist.append (Var([times], values=values, name=varname, atts=atts))

nc.save ("globalview.nc", varlist)
