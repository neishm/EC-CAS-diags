from pygeode.volatile.plot_shortcuts import plot
from pygeode.volatile.plot_wrapper import Multiplot, Legend
from pygeode.timeaxis import months

from ec_obs import obs_locations, data as obs_f
#from gaw_obs import obs_locations, data as obs_f
from model import co2 as model_co2
#from sr_timeseries import data as sr_data


# Limit the time period to plot
model_co2 = model_co2(year=2009, month=(1,12))
obs_f = obs_f(year=2009, month=(1,12))
#sr_data = sr_data(year=2009, month=(4,5))

# Create plots of each location
xticks = []
xticklabels = []
for month in sorted(list(set(model_co2.time.month))):
  for day in (1,15):
    val = model_co2.time(month=month,day=day,hour=0).get()
    if len(val) == 0: continue
    assert len(val) == 1
    xticks.append(float(val[0]))
    xticklabels.append("%s %d"%(months[month], day))

plots = []
for location, (lat, lon, country) in sorted(obs_locations.items()):

  # Construct a title for the plot
  title = location + ' - (%4.2f'%abs(lat)
  if lat < 0: title += 'S'
  else: title += 'N'
  title += ',%5.2f'%abs(lon)
  if lon < 0: title += 'W'
  else: title += 'E'
  title += ') - ' + country

  if lon < 0: lon += 360  # Model data is from longitutes 0 to 360
  obs_series = obs_f[location]
  model_series = model_co2(lat=lat, lon=lon)
#  sr_series = sr_data[location]
#  theplot = plot (model_series, sr_series, obs_series, title=location,
#         xlabel='', ylabel='CO2 ppmV', xticks=xticks, xticklabels=xticklabels)
  theplot = plot (model_series, obs_series, title=title,
         xlabel='', ylabel='CO2 ppmV', xticks=xticks, xticklabels=xticklabels)
  plots.append (theplot)


# Plot 4 timeseries per figure
n = 4
for i in range(0,len(plots),4):
  theplots = plots[i:i+4]
  # Put a legend on the last plot
  #theplots[-1] = Legend(theplots[-1], ['Model (MN)', 'Model (SR)', 'Obs'])
  theplots[-1] = Legend(theplots[-1], ['Model', 'Obs'])

  theplots = Multiplot([[p] for p in theplots])
  theplots.render()

#  break

from matplotlib.pyplot import show
show()
