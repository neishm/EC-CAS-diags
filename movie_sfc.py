def create_images (co2, contours, title='', palette=None):
  from pygeode.volatile.plot_wrapper import Colorbar, Plot, Overlay
  from pygeode.volatile.plot_shortcuts import pcolor, contour, contourf, Map

  import matplotlib.pyplot as plt

  from os.path import exists
  import numpy as np

  ## Zoom in over Toronto
  #lat = 43.7833
  #lon = 360 -79.4667
  #co2 = co2(lat=(lat-2,lat+2), lon=(lon-4,lon+4))
  ## Circle the city
  #city = Plot([360 -79.4667], [43.7833], 'o')

  #print co2.min(), co2.mean(), co2.max()
  #print co2.stdev()
  #quit()

  fig = plt.figure(figsize=(10,4))

  # Loop over all available times
  for t in range(len(co2.time)):

    data = co2(i_time=t)
    year = data.time.year[0]
    month = data.time.month[0]
    day = data.time.day[0]
    hour = data.time.hour[0]

    # Hourly:
    date = "%04d-%02d-%02d %02d:00"%(year,month,day,hour)
    fname = "images/%04d%02d%02d%02d.png"%(year,month,day,hour)
    # Daily:
  #  date = "%04d-%02d-%02d"%(year,month,day)
  #  fname = "images/%04d%02d%02d.png"%(year,month,day)
    if exists(fname):
      print date, '(exists)'
      continue
    else:
      print date

    plot = contourf(data, contours, title=title+' '+date, cmap=plt.get_cmap(palette))
    plot = Colorbar(plot)
  #  # Add the city
  #  plot = Overlay(plot, city)
    # Add the map
  #  plot = Map(plot, resolution='h')
    plot = Map(plot, resolution='c')

    plot.render(figure=fig)
    fig.savefig(fname)
    fig.clear()

#    break
#  plt.show()
