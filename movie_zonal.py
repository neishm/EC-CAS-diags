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

def create_images (field1, field2=None, contours=None, title1='plot1', title2='plot2', palette=None, norm=None, preview=False):
  from pygeode.volatile.plot_wrapper import Colorbar, Plot, Overlay, Multiplot
  from pygeode.volatile.plot_shortcuts import pcolor, contour, contourf, Map

  import matplotlib.pyplot as plt

  from os.path import exists
  import numpy as np

  # Autogenerate contours?
  if contours is None:

    # Sample every 10th frame (for speedup)
    sample = field1.slice[::10,...]
    mean = sample.mean()
    stdev = sample.stdev()
    low = mean - 3*stdev
    high = mean + 3*stdev
    contours = get_contours(low,high)

  # Get the palette to use
  cmap = plt.get_cmap(palette)

  if field2 is None:
    fig = plt.figure(figsize=(8,8))  # single plot
  else:
    fig = plt.figure(figsize=(12,6))  # double plot

  # Loop over all available times
  for t in range(len(field1.time)):

    data = field1(i_time=t)
    year = data.time.year[0]
    month = data.time.month[0]
    day = data.time.day[0]
#    hour = data.time.hour[0]

    # Quick kludge to workaround non-monotonic gph in CarbonTracker
    if year==2009 and month==8 and day==7: continue

    date = "%04d-%02d-%02d"%(year,month,day)
    fname = "images/%04d%02d%02d.png"%(year,month,day)
    if exists(fname) and preview is False:
      print date, '(exists)'
      continue
    else:
      print date

    # 1st plot
    data = field1(year=year,month=month,day=day)
    assert len(data.time) == 1
    plot1 = contourf(data, contours, title=title1+' '+date, cmap=cmap, norm=norm)
    plot1 = Colorbar(plot1)

    # 2nd plot
    if field2 is not None:
      data = field2(year=year,month=month,day=day)
      if data.size == 0: continue # not available for this timestep
      plot2 = contourf(data, contours, title=title2+' '+date, cmap=cmap, norm=norm)
      plot2 = Colorbar(plot2)


    # Put them together
    if field2 is not None:
      plot = Multiplot([[plot1,plot2]])
    else:
      plot = plot1

    plot.render(figure=fig)
    if preview is False:
      fig.savefig(fname)
      fig.clear()
    else:
      break

  if preview is True:
    plt.show()
