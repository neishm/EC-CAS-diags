def totalmass (experiment, control, outdir):
  from pygeode.plot import plotvar
  import matplotlib.pyplot as pl
  from carbontracker import data as ct
  from os.path import exists

  outfile = outdir + "/%s_totalmass_CO2.png"%experiment.name
  if exists(outfile): return

  exper_mass = experiment.get_data('dm', 'totalmass', 'CO2')
  exper_bgmass = experiment.get_data('dm', 'totalmass', 'CO2B')
  if control is not None:
    control_mass = control.get_data('dm', 'totalmass', 'CO2')
    control_bgmass = control.get_data('dm', 'totalmass', 'CO2B')
  ct_mass = ct['totalmass']['co2']

  fig = pl.figure(figsize=(15,12))
  ax = pl.subplot(111)
  titles = [experiment.title, 'background', 'CarbonTracker']
  plotvar (exper_mass, color='blue', ax=ax, title="Total mass CO2 (Pg C)")
  plotvar (exper_bgmass, color='blue', ax=ax, linestyle=':', hold=True)
  plotvar (ct_mass, color='green', ax=ax, hold=True)
  if control is not None:
    plotvar (control_mass, color='red', ax=ax, hold=True)
    plotvar (control_bgmass, color='red', ax=ax, linestyle=':', hold=True)
    titles.append(control.title)
    titles.append("control bg")
  pl.legend(titles)

  fig.savefig(outfile)

