# Convert zonal mean data (on height)
def zonalmean_gph (model, fieldname):
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  from common import number_of_levels, number_of_timesteps, remove_extra_longitude
  import numpy as np

  var, z = model.data.find_best([fieldname,'geopotential_height'], maximize=(number_of_levels,number_of_timesteps))
  assert z.atts['units'] == 'm'

  height = Height(range(68), name='height')

  # Define the final expected order of axes
  # (since 'interpolate' moves the interpolated axis)
  axes = [a.name for a in var.axes]
  axes[var.whichaxis('zaxis')] = 'height'

  # Do the interpolation
  var = interpolate(var, inaxis='zaxis', outaxis=height, inx=z/1000.)

  # Recover the expected order of axes
  var = var.transpose(*axes)

  # Remove any repeated longtiude (for global data)
  var = remove_extra_longitude(var)

  # Do the zonal mean
  var = var.nanmean('lon')

  # Cache the zonalmean data
  var = model.cache.write(var, prefix='zonalmean_gph_'+fieldname)

  return var



def rescale (field, units):
  from common import unit_scale
  input_units = field.atts['units']
  if input_units == units: return field
  low = field.atts['low']
  high = field.atts['high']
  name = field.name
  field = field / unit_scale[input_units] * unit_scale[units]
  field.name = name
  field.atts['low'] = low / unit_scale[input_units] * unit_scale[units]
  field.atts['high'] = high / unit_scale[input_units] * unit_scale[units]
  return field

def create_images (field1, field2=None, field3=None, contours=None, title1='plot1', title2='plot2', title3='plot3', palette=None, norm=None, outdir='images'):
  from contouring import get_global_range, get_contours
  from plot_wrapper import Colorbar, Plot, Overlay, Multiplot
  from plot_shortcuts import pcolor, contour, contourf, Map

  import matplotlib.pyplot as plt

  from os.path import exists
  from os import makedirs
  import numpy as np

  from pygeode.progress import PBar

  # Create output directory?
  if not exists(outdir): makedirs(outdir)

  # Autogenerate contours?
  if contours is None:

    # Define low and high based on the actual distribution of values.
    low, high = get_global_range(*[f for f in [field1,field2,field3] if f is not None])
    contours = get_contours(low,high)

  # Get the palette to use
  cmap = plt.get_cmap(palette)

  if field2 is None:
    fig = plt.figure(figsize=(8,8))  # single plot
  elif field3 is None:
    fig = plt.figure(figsize=(12,6))  # double plot
  else:
    fig = plt.figure(figsize=(12,4))  # triple plot

  # Adjust the defaults of the subplots (the defaults give too much blank space on the sides)
  plt.subplots_adjust (left=0.06, right=0.96)

  print "Saving zonal mean %s images"%field1.name
  pbar = PBar()

  # Loop over all available times
  for i,t in enumerate(field1.time):

    data = field1(time=t)
    year = data.time.year[0]
    month = data.time.month[0]
    day = data.time.day[0]
    hour = data.time.hour[0]

    fname = "%s/%04d%02d%02d%02d.png"%(outdir,year,month,day,hour)
    if exists(fname): continue

    # 1st plot
    data = field1(time=t)
    date = data.time.formatvalue(t, fmt="$Y-$m-$d ${H}z")
    assert len(data.time) == 1
    plot1 = contourf(data, contours, title=title1+' '+date, cmap=cmap, norm=norm)
    plot1 = Colorbar(plot1)

    # 2nd plot
    if field2 is not None:
      data = field2(time=t)
      if data.size == 0: continue # not available for this timestep
      date = data.time.formatvalue(data.time.values[0], fmt="$Y-$m-$d ${H}z")
      plot2 = contourf(data, contours, title=title2+' '+date, cmap=cmap, norm=norm, ylabel='')
      plot2 = Colorbar(plot2)
    else: plot2 = None

    # 3rd plot
    if field3 is not None:
      data = field3(time=t)
      if data.size == 0: continue # not available for this timestep
      date = data.time.formatvalue(data.time.values[0], fmt="$Y-$m-$d ${H}z")
      plot3 = contourf(data, contours, title=title3+' '+date, cmap=cmap, norm=norm, ylabel='')
      plot3 = Colorbar(plot3)
    else: plot3 = None


    # Put them together
    plot = Multiplot([[p for p in plot1,plot2,plot3 if p is not None]])

    plot.render(figure=fig)

    fig.savefig(fname)
    fig.clear()
    pbar.update(i*100/len(field1.time))

  plt.close(fig)

def movie_zonal (models, fieldname, units, outdir):

  from common import unit_scale

  assert len(models) > 0
  assert len(models) <= 3  # too many things to plot
  models = [m for m in models if m is not None]

  imagedir=outdir+"/images_%s_zonal%s"%('_'.join(m.name for m in models), fieldname)

  fields = [zonalmean_gph(m,fieldname) for m in models]

  # Unit conversion
  fields = [rescale(f,units) for f in fields]

  titles = [m.title for m in models]

  while len(fields) < 3: fields += [None]
  while len(titles) < 3: titles += [None]

  create_images (field1=fields[0], field2=fields[1], field3=fields[2], title1=titles[0], title2=titles[1], title3=titles[2], outdir=imagedir)

  moviefile = "%s/%s_zonal%s.avi"%(outdir, '_'.join(m.name for m in models), fieldname)

  from os import system
  from os.path import exists
  if not exists(moviefile):
    system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))

