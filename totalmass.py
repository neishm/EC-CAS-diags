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

def totalmass (experiment, control, gemfluxes, outdir):
  from carbontracker import data as ct
  from os.path import exists
  from pygeode.var import Var

  # Integrate the CarbonTracker fluxes over time
  ct_fluxes = ct['totalflux']
  ct_co2_flux = ct_fluxes.fossil_imp + ct_fluxes.bio_flux_opt + ct_fluxes.ocn_flux_opt + ct_fluxes.fire_flux_imp
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
    gem_co2_flux = gemfluxes.get_data('sum', 'ECO2')
    gem_co2_flux_time = gem_co2_flux.time
    gem_co2_flux = gem_co2_flux.get()
    # Integrate over a 3-hour period
    gem_co2_flux = gem_co2_flux * 3 * 60 * 60
    # Running sum
    gem_co2_flux = gem_co2_flux.cumsum()
    gem_co2_flux *= 1E-15  # g to Pg
    # Re-wrap as a PyGeode var
    gem_co2_flux = Var([gem_co2_flux_time], values=gem_co2_flux)


  # Limit CarbonTracker to experiment range
  t0 = float(experiment.dm.time[0])
  t1 = float(experiment.dm.time[-1])

  # CO2 mass

  exper_mass = experiment.get_data('dm', 'totalmass', 'CO2')
  try:
    exper_bgmass = experiment.get_data('dm', 'totalmass', 'CO2B')
  except KeyError:
    exper_bgmass = None
  ct_mass = ct['totalmass']['co2'](time=(t0,t1))

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
    fields.append(bgmass)
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
    control_mass = control.get_data('dm', 'totalmass', 'CO2')
    fields.extend([control_mass])
    colors.extend(['red'])
    styles.extend(['-'])
    labels.extend([control.title])
    try:
      control_bgmass = control.get_data('dm', 'totalmass', 'CO2B')
      fields.extend([control_bgmass])
      colors.extend(['red'])
      styles.extend([':'])
      labels.extend(['control bg'])
    except KeyError: pass

  outfile = outdir + "/%s_totalmass_CO2.png"%experiment.name
  if not exists(outfile):
    doplot (outfile, "Total mass CO2 (Pg C)", fields, colors, styles, labels)

  # Air mass
  exper_airmass = experiment.get_data('dm', 'totalmass', 'air')
  fields = [exper_airmass]
  colors = ['blue']
  styles = ['-']
  labels = [experiment.title]
  if control is not None:
    control_airmass = control.get_data('dm', 'totalmass', 'air')
    fields.append(control_airmass)
    colors.append('red')
    styles.append('-')
    labels.append(control.title)
  outfile = outdir + "/%s_totalmass_air.png"%experiment.name
  if not exists(outfile):
    doplot (outfile, "Total air mass (Pg)", fields, colors, styles, labels)

