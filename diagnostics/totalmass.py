
if True:


  def find_applicable_models (inputs, fieldname):
    from ..common import have_gridded_3d_data
    models = []
    for x in inputs:
      if any ((fieldname in d and have_gridded_3d_data(d)) or fieldname+'_flux' in d for d in x.data.datasets):
        models.append(x)
    if len(models) == 0:
      raise ValueError("No inputs match the criteria.")
    return models


  def do_all (datasets, fieldname, units, outdir, **kwargs):
    models = find_applicable_models(datasets, fieldname)
    totalmass (models, fieldname, units, outdir, **kwargs)


  # Total mass (Pg)
  def compute_totalmass (model, fieldname):
    from ..common import can_convert, convert, find_and_convert, grav as g, number_of_levels, number_of_timesteps, remove_repeated_longitude
    specie = None

    # Do we have the pressure change in the vertical?
    if model.data.have('dp'):

      # Total air mass?
      if fieldname == 'air':
       dp, area = model.data.find_best(['dp','cell_area'], maximize=(number_of_levels,number_of_timesteps))
       # Integrate to get total column
       dp = convert(dp,'Pa')
       tc = dp.sum('zaxis') / g

      # Total tracer mass?
      else:
       try:
         c, dp, area = find_and_convert(model, [fieldname,'dp','cell_area'], ['kg kg(air)-1', 'Pa', 'm2'], maximize=(number_of_levels,number_of_timesteps))
         specie = c.atts.get('specie',None)
       except ValueError:
         #raise ValueError("Don't know how to compute mass from units of '%s'"%c.atts['units'])
         raise


       # Integrate to get total column
       tc = (c*dp).sum('zaxis') / g

    # Otherwise, if we only need air mass, assume a lid of 0hPa and take a
    # shortcut
    elif fieldname == 'air':
       from warnings import warn
       warn ("No 'dp' data found in '%s'.  Approximating total air mass from surface pressure"%model.name)
       p0, area = model.data.find_best(['surface_pressure','cell_area'], maximize=number_of_timesteps)
       p0 = convert(p0,'Pa')
       tc = p0 / g
    else:
       raise KeyError("No 'dp' field found in '%s'.  Cannot compute total mass."%model.name)

    # Integrate horizontally
    # Assume global grid - remove repeated longitude
    area = convert(area,'m2')
    mass = remove_repeated_longitude(tc * area).sum('lat','lon')

    # Convert from kg to Pg
    mass *= 1E-12
    data = mass
    data.name = fieldname
    data.atts['units'] = 'Pg'
    if specie is not None:
      data.atts['specie'] = specie

    # Cache the data
    return model.cache.write(data,prefix="totalmass_"+fieldname)

  # Integrated flux (moles per second)
  def compute_totalflux (model, fieldname):
    from ..common import convert, number_of_timesteps, remove_repeated_longitude

    # Check if we already have integrated flux (per grid cell)
    try:
      data = model.data.find_best(fieldname+'_flux', maximize=number_of_timesteps)
      data = convert(data,'mol s-1')
    # Otherwise, we need to integrate over the grid cell area.
    except ValueError:
      data, area = model.data.find_best([fieldname+'_flux','cell_area'], maximize=number_of_timesteps)
      # Convert the units, using the specified tracer name for mass conversion
      specie = data.atts['specie']
      data = convert(data,'mol m-2 s-1')
      area = convert(area,'m2')
      data = data*area
      data.atts['units'] = 'mol s-1'
      data.atts['specie'] = specie

    # Sum, skipping the last (repeated) longitude
    data = remove_repeated_longitude(data)
    data = data.sum('lat','lon')
    data.name = fieldname

    # Cache the data
    return model.cache.write(data,prefix="totalflux_"+fieldname)


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

  def totalmass (models, fieldname, units, outdir, normalize_air_mass=False):
    from os.path import exists
    from pygeode.var import Var
    from ..common import convert
    from pygeode import timeutils

    totalmass_colours = 'blue', 'green', 'red', 'black'
    totalflux_colours = '#C0C0FF', '#C0FFC0', '#FFC0C0', 'grey'

    # Find common time period
    #TODO:  a method to query the time axis from the model without needing to grab an actual diagnostic field.
    t0 = []
    t1 = []
    for m in models:
      if m is None: continue
      try:
        t0.append(compute_totalmass(m,fieldname).time.values[0])
        t1.append(compute_totalmass(m,fieldname).time.values[-1])
      except Exception: pass
      try:
        t0.append(compute_totalflux(m,fieldname).time.values[0])
        t1.append(compute_totalflux(m,fieldname).time.values[-1])
      except Exception: pass
    if len(t0) == 0 or len(t1) == 0:
      raise ValueError("Unable to find any '%s' data in %s."%(fieldname,[m.name for m in models if m is not None]))
    t0 = max(t0)
    t1 = min(t1)

    # Set up whatever plots we can do
    fields = []
    colours = []
    styles = []
    labels = []

    for i,model in enumerate(models):
      if model is None: continue

      # Check for 3D fields, compute total mass.
      try:
        # Get model air mass, if we are normalizing the tracer mass.
        if normalize_air_mass:
          airmass = compute_totalmass(model,'dry_air')(time=(t0,t1)).load()
          airmass0 = float(airmass.values[0])

        # Total mass
        # Possibly change plot units (e.g. Pg CO2 -> Pg C)
        mass = compute_totalmass(model,fieldname)
        mass = convert(mass, units)
        mass = mass(time=(t0,t1))   # Limit time period to plot
        if normalize_air_mass:
          mass = mass / airmass * airmass0
        fields.append(mass)
        if model.color is not None:
          colours.append(model.color)
        else:
          colours.append(totalmass_colours[i])
        styles.append('-')
        labels.append(model.title)
      except KeyError: pass  # No 3D field available.

      # Total flux, integrated in time
      try:
        totalflux = compute_totalflux(model,fieldname)
        flux_units = totalflux.atts['units']
        flux_specie = totalflux.atts['specie']
        time = totalflux.time

        # Find the closest "start" time in the flux data that aligns with the last model data
        mass = fields[-1]
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
        # Re-wrap as a PyGeode var
        totalflux = Var([time], values=totalflux, name=fieldname)
        # Update the flux units to reflect the time integration
        totalflux.atts['units'] = flux_units + ' s'
        # Identify the tracer specie (so the unit converter knows what to use for
        # molar mass, etc.)
        totalflux.atts['specie'] = flux_specie
        # Convert from moles to Pg
        totalflux = convert(totalflux, units)
        # Offset the flux mass
        totalflux -= float(totalflux(time=tx).get().squeeze())
        totalflux += float(mass(time=tx).get().squeeze())
        # Limit the time period to plot
        totalflux = totalflux(time=(t0,t1))
        fields.append(totalflux)
        if model.color is not None:
          colours.append(model.color)
        else:
          colours.append(totalflux_colours[i])
        styles.append('-')
        labels.append('integrated flux')
      except (KeyError, IndexError): pass  # No flux and/or mass field available

    outfile = outdir + "/%s_totalmass_%s%s.png"%('_'.join(m.name for m in models if m is not None),fieldname,'_normalized_by_dryair' if normalize_air_mass else '')
    if not exists(outfile):
      title = "Total mass %s in %s"%(fieldname,units)
      doplot (outfile, title, fields, colours, styles, labels)
