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

def totalmass (experiment, control, gemfluxes, carbontracker, gemfieldname, gemfluxname, ctfieldname, ctfluxname, outdir):
  from os.path import exists
  from pygeode.var import Var
  from common import molecular_weight as mw

  # Integrate the CarbonTracker fluxes over time
  ct_co2_flux = carbontracker.get_data('totalflux',ctfluxname)
  ct_co2_flux_time = ct_co2_flux.time
  ct_co2_flux = ct_co2_flux.get()
  # Integrate over a 3-hour period
  ct_co2_flux = ct_co2_flux * 3 * 60 * 60
  # Running sum
  ct_co2_flux = ct_co2_flux.cumsum()
  # Convert from moles to Pg C
  ct_co2_flux *= 12  # Moles to grams
  ct_co2_flux *= 1E-15  # g to Pg
  # Re-wrap as a PyGeode var
  ct_co2_flux = Var([ct_co2_flux_time], values=ct_co2_flux)

  # Integrate GEM fluxes over time
  if gemfluxes is not None:
    gem_co2_flux = gemfluxes.get_data('totalflux', gemfluxname)
    gem_co2_flux_time = gem_co2_flux.time
    gem_co2_flux = gem_co2_flux.get()
    # Integrate over a 3-hour period
    gem_co2_flux = gem_co2_flux * 3 * 60 * 60
    # Running sum
    gem_co2_flux = gem_co2_flux.cumsum()
    # Convert from moles to Pg C
    gem_co2_flux *= 12  # Moles to grams
    gem_co2_flux *= 1E-15  # g to Pg
    # Re-wrap as a PyGeode var
    gem_co2_flux = Var([gem_co2_flux_time], values=gem_co2_flux)


  # Limit CarbonTracker to experiment range
  t0 = float(experiment.dm.time[0])
  t1 = float(experiment.dm.time[-1])

  # CO2 mass (Pg C)

  # Convert from Pg CO2 to Pg C for the plot.
  conversion = mw['C'] / mw['CO2']
  exper_mass = experiment.get_data('totalmass', gemfieldname) * conversion
  # Special case: CO2 plot includes CO2 background field
  exper_bgmass = None
  if gemfieldname == 'CO2':
    try:
      exper_bgmass = experiment.get_data('totalmass', 'CO2B') * conversion
    except KeyError:
      exper_bgmass = None
  ct_mass = carbontracker.get_data('totalmass',ctfieldname)(time=(t0,t1)) * conversion

  ct_co2_flux = ct_co2_flux(time=(t0,t1))

  # Offset the flux mass
  ct_co2_flux += float(ct_mass(time=t0).get().squeeze())
  if gemfluxes is not None:
    gem_co2_flux += float(exper_mass(time=t0).get().squeeze())

  fields = [exper_mass]
  colors = ['blue']
  styles = ['-']
  labels = [experiment.title]

  if exper_bgmass is not None:
    fields.append(exper_bgmass)
    colors.append('blue')
    styles.append(':')
    labels.append('background')

  if gemfluxes is not None:
    fields.append(gem_co2_flux)
    colors.append('#C0C0FF')
    styles.append('-')
    labels.append('GEM flux')

  fields.extend([ct_mass, ct_co2_flux])
  colors.extend(['green', '#C0FFC0'])
  styles.extend(['-', '-'])
  labels.extend(['CarbonTracker', 'CT flux'])

  if control is not None:
    control_mass = control.get_data('totalmass', 'CO2') * conversion
    fields.extend([control_mass])
    colors.extend(['red'])
    styles.extend(['-'])
    labels.extend([control.title])
    try:
      control_bgmass = control.get_data('totalmass', 'CO2B') * conversion
      fields.extend([control_bgmass])
      colors.extend(['red'])
      styles.extend([':'])
      labels.extend(['control bg'])
    except KeyError: pass

  outfile = outdir + "/%s_totalmass_%s.png"%(experiment.name,gemfieldname)
  if not exists(outfile):
    doplot (outfile, "Total mass %s (Pg C)"%gemfieldname, fields, colors, styles, labels)

  # Air mass
  exper_airmass = experiment.get_data('totalmass', 'air')
  fields = [exper_airmass]
  colors = ['blue']
  styles = ['-']
  labels = [experiment.title]
  if control is not None:
    control_airmass = control.get_data('totalmass', 'air')
    fields.append(control_airmass)
    colors.append('red')
    styles.append('-')
    labels.append(control.title)
  outfile = outdir + "/%s_totalmass_air.png"%experiment.name
  if not exists(outfile):
    doplot (outfile, "Total air mass (Pg)", fields, colors, styles, labels)

