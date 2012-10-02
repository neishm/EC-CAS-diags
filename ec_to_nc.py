# Convert EC station obs to netcdf

# Put all variables on a common (and regularly spaced) time axis
# Also, filter out bad values
def common_taxis (*invars):
  import numpy as np
  from pygeode.timeaxis import StandardTime
  from pygeode import Var
  newvars = []
  startdate=dict(year=1950)  # arbitrary (but consistent) start date
  oldtimes = [var.time.reltime(units='hours',startdate=startdate) for var in invars]
  firsttime = min(times[0] for times in oldtimes)
  lasttime = max(times[-1] for times in oldtimes)
  newtimes = np.arange(firsttime, lasttime+1)
  taxis = StandardTime (values = newtimes, units='hours', startdate=startdate)
  # Adjust to a better start date
  taxis = StandardTime (units='hours', **taxis.auxarrays)
  for i in range(len(invars)):
    newvals = np.zeros(len(newtimes), dtype=invars[i].dtype)
    if newvals.dtype.name.startswith('float'):
      blank = float('nan')
    else:
      blank = 0
    newvals[:] = blank
    ind = np.searchsorted(newtimes, oldtimes[i])
    newvals[ind] = invars[i].values
    newvals[np.where(newvals > 1e8)] = blank
    newvars.append(Var([taxis], values=newvals, name=invars[i].name))

  return newvars

# Grab data from a single file
def getdata (filename):

  import numpy as np
  from pygeode.timeaxis import StandardTime
  from pygeode import Var

  f = open(filename, "r")
  header = f.readline()
  data = zip(*[line.rstrip('\n').split(',') for line in f])
  f.close

  decyear = np.array ([float(x) for x in data[0]])
  year    = np.array ([int(x) for x in data[1]])
  doy     = np.array ([int(x) for x in data[2]])
  hourend = np.array ([int(x) for x in data[3]])
  mean    = np.array ([float(x) for x in data[4]])
  maxval  = np.array ([float(x) for x in data[5]])
  minval  = np.array ([float(x) for x in data[6]])
  std     = np.array ([float(x) for x in data[7]])
  nval    = np.array ([int(x) for x in data[8]])

  taxis = StandardTime (year=year, month=np.ones(len(year)), day=doy, hour=hourend, units='hours')

  mean   = Var([taxis], values=mean, name='mean')
  maxval = Var([taxis], values=maxval, name='max')
  minval = Var([taxis], values=minval, name='min')
  std    = Var([taxis], values=std, name='std')
  nval   = Var([taxis], values=nval, name='nval')

  return mean, maxval, minval, std, nval

def ec_to_nc():

  from glob import glob
  from pygeode.dataset import asdataset
  from os.path import exists

  outfile = "co2_sfc_obs.nc"
  if exists(outfile): return

  varlist = []

  for stationdir in glob("/wrk1/EC-CAS/surface/EC-2011/*/"):
    station = stationdir.split('/')[-2]
    print "Reading data from", station
    filenames = glob(stationdir+"*-Hourly.DAT")
    for filename in filenames:
      field = filename.split('/')[-1].split('-')[1]
      if field != "CO2": continue
#      print "...", field
      stuff = getdata(filename)
      for var in stuff:
        var.name = station + "-" + field + "-" + var.name
      varlist.extend(stuff)

  varlist = common_taxis(*varlist)

  d = asdataset(varlist)

  from pygeode.formats import netcdf
  netcdf.save(outfile, d)
