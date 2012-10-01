# Helper method for autogenerating contour levels
def get_contours(low,high):
  from math import log10, ceil, floor
  import numpy as np

  true_low = low
  true_high = high

#  print '?? low/high:', low, high
  # Make the numbers nice
  dx = high-low
#  print '?? dx:', dx
  digits = int(floor(log10(dx)))
#  print '?? digits:', digits
  # Adjust the low/high to the proper # of digits
  low  = floor(low /10**digits * 10) * 10**digits / 10
  high =  ceil(high/10**digits * 10) * 10**digits / 10
#  print '?? low/high:', low, high
  # Adjust so that dx is divisible into 20 units
  dx = high-low
#  print '?? dx:', dx

  count = dx / 10**digits * 10
#  print '?? count:', count
  count = int(round(count))
#  print '?? count:', count
  # Want a range that's divisible into a reasonable number of contours
  min_contours = 16
  max_contours = 24
  valid_contours = range(min_contours,max_contours+1)
  while not any(count%n == 0 for n in valid_contours):
    # Which end should we extend?
    if abs(low-true_low) < abs(high-true_high):
      low -= 10**digits / 10.
    else:
      high += 10**digits / 10.
    count += 1
#  print '?? count:', count
#  print '?? low/high:', low, high

  for n in valid_contours:
    if count%n == 0:
      contours = np.linspace(low,high,n+1)
#      print '?? contours:', contours
      return contours

# Helper method - determine a good high and low value for the given data
# (discard the bottom and top 0.1%, so our range at least covers 99.8% of the plot)
def get_range (var):
  import numpy as np
  sample = var
  sample = sample.get().flatten()
  # Filter out NaN values
  sample = sample[np.isfinite(sample)]
  sample.sort()
  N = len(sample)
#  print '?? N:', N
  low = sample[int(round((N-1)*0.001))]
  high = sample[int(round((N-1)*0.999))]
  return low, high

def create_images (field1, field2=None, field3=None, contours=None, title1='plot1', title2='plot2', title3='plot3', palette=None, norm=None, preview=False, outdir='images'):
  from plot_wrapper import Colorbar, Plot, Overlay, Multiplot
  from plot_shortcuts import pcolor, contour, contourf, Map

  import matplotlib.pyplot as plt

  from os.path import exists
  from os import makedirs
  import numpy as np

  # Create output directory?
  if not exists(outdir): makedirs(outdir)

  # Autogenerate contours?
  if contours is None:

    # Define low and high based on the actual distribution of values.
    low, high = get_range(field1)
    if field2 is not None:
      low2, high2 = get_range(field2)
      low = min(low,low2)
      high = max(high,high2)
    if field3 is not None:
      low3, high3 = get_range(field3)
      low = min(low,low3)
      high = max(high,high3)

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

  # Loop over all available times
  for t in range(len(field1.time)):

    data = field1(i_time=t)
    year = data.time.year[0]
    month = data.time.month[0]
    day = data.time.day[0]
    hour = data.time.hour[0]

    # Quick kludge to workaround non-monotonic gph in CarbonTracker
    if year==2009 and month==8 and day==7: continue

    date = "%04d-%02d-%02d %02dz"%(year,month,day,hour)
    fname = "%s/%04d%02d%02d%02d.png"%(outdir,year,month,day,hour)
    if exists(fname) and preview is False:
      print date, '(exists)'
      continue
    else:
      print date

    # 1st plot
    data = field1(year=year,month=month,day=day,hour=hour)
    assert len(data.time) == 1
    plot1 = contourf(data, contours, title=title1+' '+date, cmap=cmap, norm=norm)
    plot1 = Colorbar(plot1)

    # 2nd plot
    if field2 is not None:
      data = field2(year=year,month=month,day=day,hour=hour)
      if data.size == 0: continue # not available for this timestep
      plot2 = contourf(data, contours, title=title2+' '+date, cmap=cmap, norm=norm, ylabel='')
      plot2 = Colorbar(plot2)
    else: plot2 = None

    # 3rd plot
    if field3 is not None:
      data = field3(year=year,month=month,day=day,hour=hour)
      if data.size == 0: continue # not available for this timestep
      plot3 = contourf(data, contours, title=title3+' '+date, cmap=cmap, norm=norm, ylabel='')
      plot3 = Colorbar(plot3)
    else: plot3 = None


    # Put them together
    plot = Multiplot([[p for p in plot1,plot2,plot3 if p is not None]])

    plot.render(figure=fig)
    if preview is False:
      fig.savefig(fname)
      fig.clear()
    else:
      break

  if preview is True:
    plt.show()

def movie_zonal (gemfield, ctfield, offset, outdir, experiment, control):

  from carbontracker import data as ct

  ct_co2 = ct['zonalmean_gph_24h'][ctfield]

  from common import convert_CO2

  if control is not None:
    control_co2 = control.get_data('dm','zonalmean_gph',gemfield) * convert_CO2 + offset
  else:
    control_co2 = None
  exper_co2 = experiment.get_data('dm','zonalmean_gph',gemfield) * convert_CO2 + offset

  imagedir=outdir+"/images_%s_zonal%s"%(experiment.name, ctfield)

  if control is not None:

    create_images (exper_co2, control_co2, ct_co2, title1=experiment.title, title2=control.title, title3='CarbonTracker',preview=False, outdir=imagedir)

  else:

    create_images (exper_co2, ct_co2, title1=experiment.title, title2='CarbonTracker',preview=False, outdir=imagedir)

  moviefile = "%s/%s_zonal%s.avi"%(outdir,experiment.name,ctfield)

  from os import system
  from os.path import exists
  if not exists(moviefile):
    system("mencoder -o %s mf://%s/*.png -ovc lavc -lavcopts vcodec=msmpeg4v2"%(moviefile, imagedir))

