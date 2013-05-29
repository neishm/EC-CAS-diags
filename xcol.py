# Average column diagnostic

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.

# Get column average
def get_xcol (experiment, fieldname):
  from common import rotate_grid

  xcol = experiment.get_data('avgcolumn', fieldname)

  # Rotate the longitudes to 0,360
  if xcol.lon[1] < 0:
    xcol = rotate_grid(xcol)

  xcol.name = experiment.title  # Verbose name for plotting
  return xcol


def xcol (models, fieldname, outdir):
  import matplotlib.pyplot as pl
  from contouring import get_global_range, get_contours
  from pygeode.plot import plotvar
  from pygeode.progress import PBar
  from os.path import exists
  from os import makedirs

  plotname = 'X'+fieldname

  models = [m for m in models if m is not None]

  imagedir = outdir + "/images_%s_%s"%('_'.join(m.name for m in models),plotname)
  if not exists(imagedir): makedirs(imagedir)

  model_data = [get_xcol(m,fieldname) for m in models]

  low, high = get_global_range (*model_data)
  clevs = get_contours(low, high)

  # Generate each individual frame
  assert len(model_data) in (2,3)
  if len(model_data) == 3:
    fig = pl.figure(figsize=(8,10))
    n = 3
  else:
    fig = pl.figure(figsize=(10,8))
    n = 2

  times = model_data[0].time.values
  pbar = PBar()
  print "Saving %s images"%plotname
  for i,t in enumerate(times):

    taxis = model_data[0].time(time=t)
    year, month, day, hour = taxis.year[0], taxis.month[0], taxis.day[0], taxis.hour[0]
    outfile = imagedir + "/%04d%02d%02d%02d.png"%(year,month,day,hour)

    if exists(outfile): continue

    fig.clear()

    for k in range(n):
      ax = pl.subplot(n,1,k+1)
      plotvar (model_data[k](time=t), ax=ax, clevs=clevs)

    fig.savefig(outfile)

    pbar.update(i*100./len(times))

  # Generate the movie
  moviefile = "%s/%s_%s.avi"%(outdir,'_'.join(m.name for m in models),plotname)
  from os import system
  if not exists(moviefile):
    system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))
