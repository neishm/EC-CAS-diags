# XCO2 diagnostic

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.

# Get XCO2 in the right units (vmr)
def get_xco2 (experiment):
  from common import convert_CO2
  co2_col = experiment.get_data('dm', 'totalcolumn', 'CO2')
  xco2 = experiment.get_data('dm', 'avgcolumn', 'CO2')
  # Have values in kg C / kg air
  # Convert to ug C / kg air
  xco2 *= 1E9
  # Convert to vmr
  xco2 *= convert_CO2
  xco2.name = experiment.title  # Verbose name for plotting
  return xco2


def xco2 (experiment, control, outdir):
  import matplotlib.pyplot as pl
  from contouring import get_global_range, get_contours
  from pygeode.plot import plotvar
  from pygeode.progress import PBar
  from os.path import exists
  from os import makedirs
  from carbontracker import data as ct
  from common import rotate_grid

  imagedir = outdir + "/images_%s_XCO2"%experiment.name
  if not exists(imagedir): makedirs(imagedir)

  exper_xco2 = get_xco2(experiment)
  if control is not None:
    control_xco2 = get_xco2(control)
  ct_xco2 = ct['colavg']['co2'].rename('CarbonTracker')
  # Rotate the longitudes to 0,360
  ct_xco2 = rotate_grid(ct_xco2)

  if control is not None:
    low, high = get_global_range (exper_xco2, control_xco2, ct_xco2)
  else:
    low, high = get_global_range (exper_xco2, ct_xco2)
  clevs = get_contours(low, high)

  # Generate each individual frame
  if control is not None:
    fig = pl.figure(figsize=(8,10))
    n = 3
  else:
    fig = pl.figure(figsize=(10,8))
    n = 2

  times = exper_xco2.time.values
  pbar = PBar()
  print "Saving XCO2 images"
  for i,t in enumerate(times):

    taxis = exper_xco2.time(time=t)
    year, month, day, hour = taxis.year[0], taxis.month[0], taxis.day[0], taxis.hour[0]
    outfile = imagedir + "/%04d%02d%02d%02d.png"%(year,month,day,hour)

    if exists(outfile): continue

    fig.clear()

    ax = pl.subplot(n,1,1)
    plotvar (exper_xco2(time=t), ax=ax, clevs=clevs)

    if control is not None:
      ax = pl.subplot(n,1,2)
      plotvar (control_xco2(time=t), ax=ax, clevs=clevs)

    ax = pl.subplot(n,1,n)
    plotvar (ct_xco2(time=t), ax=ax, clevs=clevs)

    fig.savefig(outfile)

    pbar.update(i*100./len(times))

  # Generate the movie
  moviefile = "%s/%s_XCO2.avi"%(outdir,experiment.name)
  from os import system
  if not exists(moviefile):
    system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))
