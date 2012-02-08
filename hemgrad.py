# Compute hemispheric gradient (from model and obs)

from globalview import data as gv
from model import co2 as model_co2
import numpy as np
from math import isnan

year = 2009

model_lats = []
model_data = []
model_bars = []
station_lats = []
station_data = []
station_bars = []
obs_code = []

stations = 'alt', 'brw', 'cba', 'shm', 'esp', 'mid', 'mnm', 'mlo', 'chr', 'smo', 'cfa', 'eic', 'cgo', 'bhd', 'mqa', 'spo'

for station in stations:
  for var in gv:
    if not var.name.startswith(station): continue
    lat = var.atts['lat']
    lon = var.atts['lon']

    times = gv.time.values
    # Get data for the desired year only
    values = var[np.where((times>=2009) & (times<2010))]
    avg = float(np.mean(values))
    if isnan(avg): continue
    station_lats.append(lat)
    station_data.append(avg)
    bars = float(np.std(values)) * 2
    station_bars.append(bars)

    obs_code.append(var.name)

    values = model_co2(lat=lat,lon=lon,year=year).get()
    avg = float( np.mean(values) )
    model_data.append(avg)
    bars = float( np.std(values) ) * 2
    model_bars.append(bars)
    # Adjust to the true latitude
    model_lats.append(float(model_co2(lat=lat).lat.values[0]))

# Plot this stuff
from pygeode.volatile.plot_wrapper import Plot, ErrorBar, Overlay, Legend
obs_plot = Plot(station_lats, station_data, 'ko', xlabel="Latitude", ylabel="CO2 (ppmV)",
  xlim=(-90,90), xticks=range(-90,90+30,30), title="CO2 Hemispheric Gradient %d"%year,
  label='Globalview obs')
obs_bars = ErrorBar(station_lats, station_data, yerr=station_bars, fmt=None, ecolor='k')
model_points = Plot(model_lats, model_data, 'rs', label='Model')
model_line = Plot(model_lats, model_data, 'r:')
model_bars = ErrorBar(model_lats, model_data, yerr=model_bars, fmt=None, ecolor='r')
plot = Overlay(obs_plot, obs_bars, model_line, model_points, model_bars)
plot = Legend(plot, loc='lower right', numpoints=1)

plot.render()
from matplotlib.pyplot import show
show()
