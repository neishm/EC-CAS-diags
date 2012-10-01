def shortexper_diffcheck():
  from pygeode.formats import rpn, netcdf
  from pygeode.dataset import concat
  from pygeode.axis import Height
  from ec_obs import obs_locations, data as obs
  from common import convert_CO2, fix_timeaxis
  from os.path import exists
  from sys import argv
  from pygeode.plot import plotvar
  from matplotlib import pyplot as pl

  location = argv[1]
  lat, lon, country = obs_locations[location]
  lon += 360
  co2_obs = obs[location](year=2009, month=7, day=(20,27))

  experiment_names = argv[2:]
  n = len(experiment_names)

  fig = pl.figure()

  for i,experiment_name in enumerate(experiment_names):
    indir = "/wrk2/neish/"+experiment_name
    outfile = "%s_%s.nc"%(experiment_name,location)

    if not exists(outfile):
      dm = [rpn.open(indir+"/dm200907%02d00_%03dh"%(d,h)).squeeze('forecast') for d in range(20,27) for h in range(0,24,2)]
      km = [rpn.open(indir+"/km200907%02d00_%03dh"%(d,h)).squeeze('forecast') for d in range(20,27) for h in range(0,24,2)]
      pm = [rpn.open(indir+"/pm200907%02d00_%03dh"%(d,h)).squeeze('forecast') for d in range(20,27) for h in range(0,24,2)]

      dm = concat(dm)
      km = concat(km)
      pm = concat(pm)

      dm = fix_timeaxis(dm)
      km = fix_timeaxis(km)
      pm = fix_timeaxis(pm)

      ktn = km['KTN'](lat=lat, lon=lon)
      co2 = dm['CO2'](lat=lat, lon=lon) * convert_CO2
      co2.name = 'CO2'
      gz = dm['GZ'](lat=lat, lon=lon, i_time=0).squeeze()
      height = Height(gz.get() * 10)  # decametres to metres
      ktn = ktn.replace_axes(eta=height)
      co2 = co2.replace_axes(eta=height)
      pbl = pm['H'](lat=lat, lon=lon).squeeze()

      netcdf.save(outfile, [ktn,co2,pbl])

    f = netcdf.open(outfile)
    ktn = f['KTN']
    co2 = f['CO2']
    pbl = f['H']

    axis = pl.subplot(3,n,i+1)
    plotvar(ktn(z=(0,10000)), ax=axis)
    plotvar(pbl, color='white', ax=axis, hold=True)

    axis = pl.subplot(3,n,n+i+1)
    plotvar(co2(z=(0,10000)), ax=axis)
    plotvar(pbl, color='white', ax=axis, hold=True)

    axis = pl.subplot(3,n,2*n+i+1)
    plotvar(co2(z=0), color='blue', ax=axis)
    plotvar(co2_obs, color='green', ax=axis, hold=True)

  pl.show()

if __name__ == '__main__':
  shortexper_diffcheck()
