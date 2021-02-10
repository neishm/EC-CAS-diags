###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################



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
          common_times = set(time.values) & set(last_totalmass.time.values)
          assert len(common_times) > 0
          tx = float(min(common_times))
          # Offset the flux mass
          totalmass -= float(totalmass(time=tx).get().squeeze())
          totalmass += float(last_totalmass(time=tx).get().squeeze())
        totalmass = DerivedProduct(totalmass, source=inp)
        totalmass.title += ' (integrated flux)'
        computed.append(totalmass)
      except KeyError:
        pass
      except AssertionError as e:
        from warnings import warn
        warn ("Skipping %s totalflux %s: %s"%(inp.name,self.fieldname,e.message))
        pass
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
       dp, area = model.find_best(['dp','blended_area'], maximize=(number_of_levels,number_of_timesteps))
       # Integrate to get total column
       dp = convert(dp,'Pa')
       tc = dp.sum('zaxis') / g

      # Total tracer mass?
      else:
       try:
         c, dp, area = find_and_convert(model, [fieldname,'dp','blended_area'], ['kg kg(air)-1', 'Pa', 'm2'], maximize=(number_of_levels,number_of_timesteps))
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
       p0, area = model.find_best(['surface_pressure','blended_area'], maximize=number_of_timesteps)
       warn ("No 'dp' data found in '%s'.  Approximating total air mass from surface pressure"%model.name)
       p0 = convert(p0,'Pa')
       tc = p0 / g
    else:
       raise KeyError("No 'dp' field found in '%s'.  Cannot compute total mass."%model.name)

    # Integrate horizontally
    # Assume global grid - remove repeated longitude
    area = convert(area,'m2')
    if tc.hasaxis('subgrid'):  # Yin-yan special case
      mass = (tc * area).sum('subgrid', 'y','x')
    else:
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
      data =  model.cache.write(data,prefix=model.name+"_totalmass_"+fieldname+suffix, force_single_precision=False, suffix=self.end_suffix)
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
      data, area = model.find_best([fieldname+'_flux','blended_area'], maximize=number_of_timesteps)
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
    if data.hasaxis('subgrid'):  # Yin-yan special case
      data = data.sum('subgrid', 'y','x')
    else:
      data = data.sum('lat','lon')
    data.name = fieldname

    # Cache the data
    if cache:
      data =  model.cache.write(data,prefix=model.name+"_totalflux_"+fieldname+suffix, force_single_precision=False, suffix=self.end_suffix)
    return data


  def do (self, inputs):
    import matplotlib.pyplot as pl
    from ..common import to_datetimes
    from os.path import exists

    outfile = self.outdir + "/%s_totalmass_%s%s.%s"%('_'.join(inp.name for inp in inputs),self.fieldname,self.suffix+self.end_suffix,self.image_format)
    if exists(outfile):
      return

    fig = pl.figure(figsize=(15,12))
    ax = pl.subplot(111)
    pl.title ("Total mass %s in %s"%(self.fieldname,self.units))

    # Find common time period
    t0 = []
    t1 = []
    for inp in inputs:
      t0.append(inp.find_best(self.fieldname).time.values[0])
      t1.append(inp.find_best(self.fieldname).time.values[-1])
    t0 = max(t0)
    t1 = min(t1)

    for inp in inputs:

      mass = inp.find_best(self.fieldname)(time=(t0,t1))
      dates = to_datetimes(mass.time)
      pl.plot(dates, mass.get(), color=inp.color, linestyle=inp.linestyle, marker=inp.marker, markeredgecolor=inp.color, label=inp.title)
    pl.legend(loc='best')

    fig.savefig(outfile)
    pl.close(fig)

from . import table
table['totalmass'] = Totalmass

