
from . import TimeVaryingDiagnostic, ImageDiagnostic
class Totalmass(TimeVaryingDiagnostic,ImageDiagnostic):
  """
  Compute the total mass budget for a field.  Show the time variation as a
  1D line plot.
  """
  def __init__ (self, **kwargs):
    super(Totalmass,self).__init__(**kwargs)
    self.require_fieldname = False # Will provide our own checks below.

  def _select_inputs (self, inputs):
    inputs = super(Totalmass,self)._select_inputs(inputs)
    selected = []
    for inp in inputs:
      try:
        totalmass = self._compute_totalmass(inp,cache=False)
        selected.append(inp)
        continue
      except KeyError: pass
      try:
        totalflux = self._compute_totalflux(inp,cache=False)
        selected.append(inp)
        continue
      except KeyError: pass
    return selected

  # Compute the mass for each input.
  def _transform_inputs (self, inputs):
    from ..common import convert
    from ..interfaces import DerivedProduct
    from pygeode import timeutils
    from pygeode.var import Var
    inputs = super(Totalmass,self)._transform_inputs(inputs)

    computed = []
    last_totalmass = None
    for inp in inputs:
      try:
        totalmass = self._compute_totalmass (inp)
        totalmass = convert(totalmass,self.units)
        computed.append(DerivedProduct(totalmass, source=inp))
        last_totalmass = totalmass
      except KeyError: pass
      try:
        totalflux = self._compute_totalflux (inp)
        totalflux = convert(totalflux, self.units+' s-1')
        data = totalflux.get()
        # Get time interval
        time = totalflux.time
        dt = timeutils.delta(time, units='seconds')
        # Integrate over the flux period
        data = data * dt
        # Running sum
        data = data.cumsum()
        # Initial time is *after* the first sum
        assert time.units == 'days'
        time = time.__class__(values=time.values+dt/86400., units='days', startdate=time.startdate)
        # Re-wrap as a PyGeode var
        totalmass = Var([time], values=data, name=totalflux.name)
        # Update the flux units to reflect the time integration
        totalmass.atts['units'] = self.units
        # Identify the tracer specie (so the unit converter knows what to use for
        if 'specie' in totalflux.atts:
          totalmass.atts['specie'] = totalflux.atts['specie']

        # Find the closest "start" time in the flux data that aligns with the last model data
        if last_totalmass is not None:
          tx = float(min(set(time.values) & set(totalmass.time.values)))
          # Offset the flux mass
          totalmass -= float(totalmass(time=tx).get().squeeze())
          totalmass += float(last_totalmass(time=tx).get().squeeze())
        totalmass = DerivedProduct(totalmass, source=inp)
        totalmass.title += ' (integrated flux)'
        computed.append(totalmass)
      except KeyError: pass
    return computed

  # Total mass (Pg)
  def _compute_totalmass (self, model, cache=True):
    from ..common import can_convert, convert, find_and_convert, grav as g, number_of_levels, number_of_timesteps, remove_repeated_longitude
    fieldname = self.fieldname
    suffix = self.suffix

    specie = None

    # Do we have the pressure change in the vertical?
    if model.have('dp'):

      # Total air mass?
      if fieldname == 'air':
       dp, area = model.find_best(['dp','cell_area'], maximize=(number_of_levels,number_of_timesteps))
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

       c = c.as_type('float64')
       # Integrate to get total column
       tc = (c*dp).sum('zaxis') / g

    # Otherwise, if we only need air mass, assume a lid of 0hPa and take a
    # shortcut
    elif fieldname == 'air':
       from warnings import warn
       p0, area = model.find_best(['surface_pressure','cell_area'], maximize=number_of_timesteps)
       warn ("No 'dp' data found in '%s'.  Approximating total air mass from surface pressure"%model.name)
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
    if cache:
      data =  model.cache.write(data,prefix=model.name+"_totalmass_"+fieldname+suffix, force_single_precision=False)
    return data

  # Integrated flux (moles per second)
  def _compute_totalflux (self, model, cache=True):
    from ..common import convert, number_of_timesteps, remove_repeated_longitude

    fieldname = self.fieldname
    suffix = self.suffix

    # Check if we already have integrated flux (per grid cell)
    try:
      data = model.find_best(fieldname+'_flux', maximize=number_of_timesteps)
      data = convert(data,'mol s-1')
    # Otherwise, we need to integrate over the grid cell area.
    except ValueError:
      data, area = model.find_best([fieldname+'_flux','cell_area'], maximize=number_of_timesteps)
      # Convert the units, using the specified tracer name for mass conversion
      specie = data.atts['specie']
      data = convert(data,'mol m-2 s-1')
      area = convert(area,'m2')
      data = data*area
      data.atts['units'] = 'mol s-1'
      data.atts['specie'] = specie

    # Sum, skipping the last (repeated) longitude
    data = remove_repeated_longitude(data)
    data = data.as_type('float64')
    data = data.sum('lat','lon')
    data.name = fieldname

    # Cache the data
    if cache:
      data =  model.cache.write(data,prefix=model.name+"_totalflux_"+fieldname+suffix, force_single_precision=False)
    return data

  @staticmethod
  def _doplot (outfile, title, fields, colours, styles, labels):
    from pygeode.plot import plotvar
    import matplotlib.pyplot as pl

    fig = pl.figure(figsize=(15,12))
    ax = pl.subplot(111)
    for field, color, style in zip(fields, colours, styles):
      plotvar (field, color=color, ax=ax, linestyle=style, hold=True)
    ax.set_title(title)
    pl.legend(labels, loc='best')

    fig.savefig(outfile)

  def do (self, inputs):
    from os.path import exists

    fieldname = self.fieldname
    units = self.units
    outdir = self.outdir
    format = self.image_format
    suffix = self.suffix

    # Find common time period
    t0 = []
    t1 = []
    for inp in inputs:
      t0.append(inp.datasets[0].time.values[0])
      t1.append(inp.datasets[0].time.values[-1])
    t0 = max(t0)
    t1 = min(t1)

    # Set up whatever plots we can do
    fields = []
    colours = []
    styles = []
    labels = []

    for i,model in enumerate(inputs):

      mass = model.find_best(self.fieldname)
      mass = mass(time=(t0,t1))   # Limit time period to plot
      fields.append(mass)
      colours.append(model.color)
      styles.append(model.linestyle)
      labels.append(model.title)

    outfile = outdir + "/%s_totalmass_%s%s.%s"%('_'.join(inp.name for inp in inputs),fieldname,suffix,format)
    if not exists(outfile):
      title = "Total mass %s in %s"%(fieldname,units)
      self._doplot (outfile, title, fields, colours, styles, labels)

from . import table
table['totalmass'] = Totalmass

