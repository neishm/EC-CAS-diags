def doplot (outfile, title, fields, colours, styles, labels):
  from pygeode.plot import plotvar
  import matplotlib.pyplot as pl

  fig = pl.figure(figsize=(15,12))
  ax = pl.subplot(111)
  for field, color, style in zip(fields, colours, styles):
    plotvar (field, color=color, ax=ax, linestyle=style, hold=True)
  ax.set_title(title)
  pl.legend(labels, loc='best')

  fig.savefig(outfile)

def totalmass (models, fieldname, pg_of, outdir):
  from os.path import exists
  from pygeode.var import Var
  from common import molecular_weight as mw
  from pygeode import timeutils

  totalmass_colours = 'blue', 'green', 'red', 'black'
  totalflux_colours = '#C0C0FF', '#C0FFC0', '#FFC0C0', 'grey'

  # Find common time period
  #TODO:  a method to query the time axis from the model without needing to grab an actual diagnostic field.
  t0 = max(m.get_data('totalmass',fieldname).time.values[0] for m in models if m is not None)
  t1 = min(m.get_data('totalmass',fieldname).time.values[-1] for m in models if m is not None)

  # Set up whatever plots we can do
  fields = []
  colours = []
  styles = []
  labels = []

  for i,model in enumerate(models):
    if model is None: continue

    # Total mass
    # Possibly change plot units (e.g. Pg CO2 -> Pg C)
    mass = model.get_data('totalmass',fieldname) / mw[fieldname] * mw[pg_of]
    mass = mass(time=(t0,t1))   # Limit time period to plot
    fields.append(mass)
    colours.append(totalmass_colours[i])
    styles.append('-')
    labels.append(model.title)

    # Total mass of background field
    try:
      # Possibly change plot units (e.g. Pg CO2 -> Pg C)
      mass = model.get_data('totalmass',fieldname+'_background') / mw[fieldname] * mw[pg_of]
      mass = mass(time=(t0,t1))
      fields.append(mass)
      colours.append(totalmass_colours[i])
      styles.append(':')
      labels.append('background')
    except KeyError: pass  # Background values not available
    except ValueError: pass  # Background values not available

    # Total flux, integrated in time
    try:
      totalflux = model.get_data('totalflux',fieldname)
      time = totalflux.time

      # Find the closest "start" time in the flux data that aligns with the model data
      try:
        tx = float(min(set(time.values) & set(mass.time.values)))
      except ValueError:   # No common timesteps between fluxes and model data?
        tx = min(tx for tx in time.values if tx > t0)

      totalflux = totalflux.get()
      # Get time interval
      dt = timeutils.delta(time, units='seconds')
      # Integrate over the flux period
      totalflux = totalflux * dt
      # Running sum
      totalflux = totalflux.cumsum()
      # Initial time is *after* the first sum
      assert time.units == 'days'
      time = time.__class__(values=time.values+dt/86400., units='days', startdate=time.startdate)
      # Convert from moles to Pg
      totalflux *= mw[pg_of]
      totalflux *= 1E-15  # g to Pg
      # Re-wrap as a PyGeode var
      totalflux = Var([time], values=totalflux)
      # Offset the flux mass
      totalflux -= float(totalflux(time=tx).get().squeeze())
      totalflux += float(mass(time=tx).get().squeeze())
      # Limit the time period to plot
      totalflux = totalflux(time=(t0,t1))
      fields.append(totalflux)
      colours.append(totalflux_colours[i])
      styles.append('-')
      labels.append('integrated flux')
    except KeyError: pass  # No flux available

  outfile = outdir + "/%s_totalmass_%s.png"%('_'.join(m.name for m in models if m is not None),fieldname)
  if not exists(outfile):
    if pg_of == fieldname:
      title = "Total mass %s (Pg)"%fieldname
    else:
      title = "Total mass %s (Pg %s)"%(fieldname,pg_of)
    doplot (outfile, title, fields, colours, styles, labels)

