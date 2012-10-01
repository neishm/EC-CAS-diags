def shortexper_diffcheck(experiment, control, location, outdir):
  from pygeode.axis import Height
  from ec_obs import obs_locations, data as obs
  from common import convert_CO2
  from os.path import exists
  from pygeode.plot import plotvar
  from matplotlib import pyplot as pl

  lat, lon, country = obs_locations[location]
  lon += 360
  co2_obs = obs[location]
  # Limit to the length of the experiment
  time = experiment.dm.time.values
  co2_obs = co2_obs(time=(min(time),max(time)))

  fig = pl.figure(figsize=(15,15))

  for i,dataset in enumerate([experiment,control]):

    ktn = dataset.get_data('km',location,'KTN')
    co2 = dataset.get_data('dm',location,'CO2') * convert_CO2
    co2.name = 'CO2'
    gz = dataset.get_data('dm',location,'GZ')(i_time=0).squeeze()
    height = Height(gz.get() * 10)  # decametres to metres
    ktn = ktn.replace_axes(eta=height)
    co2 = co2.replace_axes(eta=height)
    pbl = dataset.get_data('pm',location,'H')

    axis = pl.subplot(3,2,0*2+i+1)
    plotvar(ktn(z=(0,10000)), ax=axis, title='%s KTN (%s)'%(location,dataset.name))
    plotvar(pbl, color='white', ax=axis, hold=True)

    axis = pl.subplot(3,2,1*2+i+1)
    plotvar(co2(z=(0,10000)), ax=axis, title='%s CO2 (%s)'%(location,dataset.name))
    plotvar(pbl, color='white', ax=axis, hold=True)

    axis = pl.subplot(3,2,2*2+i+1)
    plotvar(co2(z=0), color='blue', ax=axis, title='%s CO2 (%s)'%(location,dataset.name))
    plotvar(co2_obs, color='green', ax=axis, hold=True)

  outfile = outdir+"/%s_%s_diffcheck.png"%(experiment.name,location)
  if not exists(outfile):
    fig.savefig(outfile)

