def create_images (co2, co2_ref, contours, refname='(reference)'):
  from pygeode.volatile.plot_wrapper import Colorbar, Plot, Overlay, Multiplot
  from pygeode.volatile.plot_shortcuts import pcolor, contour, contourf, Map

  import matplotlib.pyplot as plt

  from os.path import exists
  import numpy as np

  #print co2.min(), co2.mean(), co2.max()
  #print co2.stdev()
  #quit()

  if co2_ref is None:
    fig = plt.figure(figsize=(8,8))  # single plot
  else:
    fig = plt.figure(figsize=(12,6))  # double plot

  # Loop over all available times
  for t in range(len(co2.time)):

    data = co2(i_time=t)
    year = data.time.year[0]
    month = data.time.month[0]
    day = data.time.day[0]
#    hour = data.time.hour[0]

    # Quick kludge to workaround non-monotonic gph in CarbonTracker
    if year==2009 and month==8 and day==7: continue

    date = "%04d-%02d-%02d"%(year,month,day)
    fname = "images/%04d%02d%02d.png"%(year,month,day)
    if exists(fname):
      print date, '(exists)'
      continue
    else:
      print date

    cmap = plt.get_cmap('Paired')

    # 1st plot
    data = co2(year=year,month=month,day=day)
    assert len(data.time) == 1
    plot1 = contourf(data, contours, title='CO2 ppmV '+date, cmap=cmap)
    plot1 = Colorbar(plot1)

    # 2nd plot
    if co2_ref is not None:
      data = co2_ref(year=year,month=month,day=day)
      if data.size == 0: continue # not available for this timestep
      plot2 = contourf(data, contours, title='CO2 ppmV (%s) '%refname+date, cmap=cmap)
      plot2 = Colorbar(plot2)


    # Put them together
    if co2_ref is not None:
      plot = Multiplot([[plot1,plot2]])
    else:
      plot = plot1

    plot.render(figure=fig)
    fig.savefig(fname)
    fig.clear()

#    break
#  plt.show()
