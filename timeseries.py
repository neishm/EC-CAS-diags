def timeseries (show=True, outdir=None):

  from plot_shortcuts import plot
  from plot_wrapper import Multiplot, Legend
  import matplotlib.pyplot as pl
  from pygeode.timeaxis import months

  from ec_obs import obs_locations, data as obs_f
  #from gaw_obs import obs_locations, data as obs_f
  from model_stuff import my_data
  from common import convert_CO2
  from interfaces import control, control_title, experiment, experiment_name, experiment_title
  from carbontracker import data as ct

  from os.path import exists

  exper_co2 = experiment['sfc']['CO2'] * convert_CO2
  control_co2 = control['sfc']['CO2'] * convert_CO2
  # Use CarbonTracker data
  ct_co2 = ct['sfc'].co2
  ct_co2 = ct_co2.unfill(4.984605e+37)
  ct_title = "CarbonTracker"
  #from sr_timeseries import data as sr_data


  # Limit the time period to plot
  exper_co2 = exper_co2(year=2009, month=(6,9))
  control_co2 = control_co2(year=2009, month=(6,9))
  obs_f = obs_f(year=2009, month=(6,9))
  ct_co2 = ct_co2(year=2009, month=(6,9))

  # Create plots of each location
  xticks = []
  xticklabels = []
  for month in sorted(list(set(exper_co2.time.month))):
    for day in (1,15):
      val = exper_co2.time(month=month,day=day,hour=0).get()
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

    ct_series = ct_co2(lat=lat, lon=lon)
    if lon < 0: lon += 360  # Model data is from longitutes 0 to 360
    obs_series = obs_f[location]
    exper_series = exper_co2(lat=lat, lon=lon)
    control_series = control_co2(lat=lat, lon=lon)
    theplot = plot (exper_series, obs_series, control_series, title=title,
           xlabel='', ylabel='CO2 ppmV', xticks=xticks, xticklabels=xticklabels)
    plots.append (theplot)


  # Plot 4 timeseries per figure
  n = 4
  for i in range(0,len(plots),4):
    fig = pl.figure(figsize=(15,12))

    theplots = plots[i:i+4]
    # Put a legend on the last plot
    theplots[-1] = Legend(theplots[-1], [experiment_title, 'Obs', control_title])

    theplots = Multiplot([[p] for p in theplots])
    theplots.render(figure=fig)

    if outdir is not None:
      outfile = "%s/%s_timeseries_ec%02d.png"%(outdir,experiment_name,i/4+1)
      fig.savefig(outfile)

  if show:
    pl.show()

if __name__ == "__main__":
  timeseries()
