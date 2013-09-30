
def shortexper_diffcheck(models, obs, location, outdir):
  from pygeode.axis import Height
  from os.path import exists
  from pygeode.plot import plotvar
  from contouring import get_range, get_contours
  from matplotlib import pyplot as pl
  import numpy as np

  lat, lon, country = obs.obs_locations[location]
  lon += 360
  co2_obs = obs.get_data(location,'CO2')
  # Limit to the length of the experiment
  test_field = models[0].get_data(location,'CO2')
  time = test_field.time.values
  del test_field
  co2_obs = co2_obs(time=(min(time),max(time)))

  assert len(models) in (1,2)

  if len(models) == 1:
    fig = pl.figure(figsize=(15,15))
    n = 2
  else:
    fig = pl.figure(figsize=(8,15))
    n = 1

  # Initialize ranges
  ktn_min = float('inf')
  ktn_max = float('-inf')
  co2_min = float('inf')
  co2_max = float('-inf')
  co2_sfc_min = np.nanmin(co2_obs.get())
  co2_sfc_max = np.nanmax(co2_obs.get())
  if np.isnan(co2_sfc_min): co2_sfc_min = float('inf')
  if np.isnan(co2_sfc_max): co2_sfc_max = float('-inf')

  # Get the data, and compute the global ranges
  for i,dataset in enumerate(models):

    if dataset is None: continue

    ktn = dataset.get_data(location,'eddy_diffusivity')
    mn, mx = get_range(ktn)
    ktn_min = min(ktn_min, mn)
    ktn_max = max(ktn_max, mx)

    co2 = dataset.get_data(location,'CO2')
    mn, mx = get_range(co2)
    co2_min = min(co2_min, mn)
    co2_max = max(co2_max, mx)

    if not ( co2.hasaxis("hybrid") or co2.hasaxis("loghybrid") ):
      raise TypeError("Unrecognized z axis type %s"%co2.getaxis("zaxis"))
    co2_sfc_min = min(co2_sfc_min, co2(zaxis=1.0).min())
    co2_sfc_max = max(co2_sfc_max, co2(zaxis=1.0).max())

  # Do the plots
  for i,dataset in enumerate(models):

    if dataset is None: continue

    ktn = dataset.get_data(location,'eddy_diffusivity')
    co2 = dataset.get_data(location,'CO2')
    co2.name = 'CO2'

    # Put the variables on a height coordinate
    # TODO: proper vertical interpolation
    gz = dataset.get_data(location,'geopotential_height')(i_time=0).squeeze()
    # Match GZ to the tracer levels (in GEM4, GZ has both thermo/momentum levs)
    co2_iz = np.searchsorted(gz.zaxis.values, co2.zaxis.values)
    ktn_iz = np.searchsorted(gz.zaxis.values, ktn.zaxis.values)
    co2_height = Height(gz.get(i_zaxis=co2_iz))
    ktn_height = Height(gz.get(i_zaxis=ktn_iz))
    ktn = ktn.replace_axes(zaxis=ktn_height)
    co2 = co2.replace_axes(zaxis=co2_height)
    pbl = dataset.get_data(location,'PBL_height')
    # Adjust pbl to use the same height units for plotting.
    pbl *= Height.plotatts.get('scalefactor',1)

    axis = pl.subplot(3,n,0*n+i+1)
    plotvar(ktn(z=(0,10000)), ax=axis, title='%s KTN (%s)'%(location,dataset.name), clevs=get_contours(ktn_min,ktn_max))
    plotvar(pbl, color='white', ax=axis, hold=True)

    axis = pl.subplot(3,n,1*n+i+1)
    plotvar(co2(z=(0,10000)), ax=axis, title='%s CO2 (%s)'%(location,dataset.name), clevs=get_contours(co2_min,co2_max))
    plotvar(pbl, color='white', ax=axis, hold=True)

    axis = pl.subplot(3,n,2*n+i+1)
    plotvar(co2(z=0), color='blue', ax=axis, title='%s CO2 (%s)'%(location,dataset.name))
    plotvar(co2_obs, color='green', ax=axis, hold=True)
    axis.set_ylim([co2_sfc_min,co2_sfc_max])
    axis.legend ([dataset.title, 'Obs'])

  outfile = outdir+"/%s_%s_diffcheck.png"%('_'.join(m.name for m in models if m is not None),location)
  if not exists(outfile):
    fig.savefig(outfile)

  pl.close(fig)
