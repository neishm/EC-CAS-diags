from pygeode.volatile.plot_wrapper import Colorbar, Plot, Overlay, Multiplot
from pygeode.volatile.plot_shortcuts import pcolor, contour, contourf, Map

import matplotlib.pyplot as plt

from model import co2_zonal as co2, co2b_zonal as co2_ref

from os.path import exists
import numpy as np

#print co2.min(), co2.mean(), co2.max()
#print co2.stdev()
#quit()

# Force daily data
from pygeode.climat import dailymean
co2 = dailymean(co2)
co2_ref = dailymean(co2_ref)

#fig = plt.figure(figsize=(8,8))  # for single plot
fig = plt.figure(figsize=(12,6))  # double plot

# Loop over all available times
for t in range(len(co2.time)):

  data = co2(i_time=t)
  year = data.time.year[0]
  month = data.time.month[0]
  day = data.time.day[0]
#  hour = data.time.hour[0]

  date = "%04d-%02d-%02d"%(year,month,day)
  fname = "images/%04d%02d%02d.png"%(year,month,day)
  if exists(fname):
    print date, '(exists)'
    continue
  else:
    print date

  contours = list(np.arange(376,402+1,1))

  # CO2
  data = co2(i_time=t)
  plot1 = contourf(data, contours, title='CO2 ppmV '+date)
  plot1 = Colorbar(plot1)

  # CO2B
  data = co2_ref(i_time=t)
  plot2 = contourf(data, contours, title='CO2 ppmV (background) '+date)
  plot2 = Colorbar(plot2)

  # Put them together
  plot = Multiplot([[plot1,plot2]])

  plot.render(figure=fig)
  fig.savefig(fname)
  fig.clear()

#  break
#plt.show()
