def doplot (outfile, title, fields, colors, styles, labels):
  from pygeode.plot import plotvar
  import matplotlib.pyplot as pl

  fig = pl.figure(figsize=(15,12))
  ax = pl.subplot(111)
  for field, color, style in zip(fields, colors, styles):
    plotvar (field, color=color, ax=ax, linestyle=style, hold=True)
  ax.set_title(title)
  pl.legend(labels, loc='best')

  fig.savefig(outfile)

def totalmass (experiment, control, outdir):
  from carbontracker import data as ct
  from os.path import exists

  # CO2 mass

  exper_mass = experiment.get_data('dm', 'totalmass', 'CO2')
  exper_bgmass = experiment.get_data('dm', 'totalmass', 'CO2B')
  ct_mass = ct['totalmass']['co2']
  fields = [exper_mass, exper_bgmass, ct_mass]
  colors = ['blue', 'blue', 'green']
  styles = ['-', ':', '-']
  labels = [experiment.title, 'background', 'CarbonTracker']
  if control is not None:
    control_mass = control.get_data('dm', 'totalmass', 'CO2')
    control_bgmass = control.get_data('dm', 'totalmass', 'CO2B')
    fields.extend([control_mass, control_bgmass])
    colors.extend(['red', 'red'])
    styles.extend(['-', ':'])
    labels.extend([control.title, 'control bg'])

  outfile = outdir + "/%s_totalmass_CO2.png"%experiment.name
  if not exists(outfile):
    doplot (outfile, "Total mass CO2 (Pg C)", fields, colors, styles, labels)

  # Air mass
  exper_airmass = experiment.get_data('dm', 'totalmass', 'air')
  control_airmass = control.get_data('dm', 'totalmass', 'air')
  fields = [exper_airmass, control_airmass]
  colors = ['blue', 'red']
  styles = ['-', '-']
  labels = [experiment.title, control.title]
  outfile = outdir + "/%s_totalmass_air.png"%experiment.name
  if not exists(outfile):
    doplot (outfile, "Total air mass (Pg)", fields, colors, styles, labels)

