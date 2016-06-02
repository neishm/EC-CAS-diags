# Average column diagnostic

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.


from . import TimeVaryingDiagnostic
class XCol(TimeVaryingDiagnostic):
  """
  Show the average column of a field, animated in time.  Note that no averaging
  kernel is used in the average, it is simply weighted by air mass.
  """
  def _select_inputs (self, inputs):
    inputs = super(XCol,self)._select_inputs(inputs)
    selected = []
    for inp in inputs:
      # Use any inputs that we can successfully compute an avg column from.
      try:
        xcol = self._avgcolumn(inp,cache=False)
        selected.append(inp)
      except KeyError: pass

    return selected

  def _transform_inputs (self, inputs):
    from ..interfaces import DerivedProduct
    inputs = super(XCol,self)._transform_inputs(inputs)
    computed = []
    for inp in inputs:
      xcol = self._avgcolumn(inp)
      computed.append(DerivedProduct(xcol,source=inp))
    return computed

  # Compute total column of a tracer
  # (in kg/m2)
  def _totalcolumn (self, model, fieldname=None, cache=True):
    from ..common import find_and_convert, grav as g, number_of_levels, number_of_timesteps, rotate_grid
    fieldname = fieldname or self.fieldname

    c, dp = find_and_convert (model, [fieldname,'dp'], ['kg kg(air)-1', 'Pa'], maximize=(number_of_levels,number_of_timesteps))

    # Integrate
    data = (c*dp).sum('zaxis') / g
    data.name = fieldname
    data.atts['units'] = 'kg m-2'

    if 'specie' in c.atts:
      data.atts['specie'] = c.atts['specie']

    # Cache the data
    if cache:
      data = model.cache.write(data,prefix=model.name+"_totalcolumn_"+fieldname+self.suffix, suffix=self.end_suffix)

    data = rotate_grid(data)
    return data


  # Compute average column of a tracer
  def _avgcolumn (self, model, fieldname=None, cache=True):
    from ..common import find_and_convert, number_of_levels, number_of_timesteps, rotate_grid
    fieldname = fieldname or self.fieldname

    c, dp = find_and_convert(model, [fieldname,'dp'], [self.units,'Pa'], maximize=(number_of_levels,number_of_timesteps))

    data = (c*dp).sum('zaxis') / dp.sum('zaxis')
    data.name = fieldname
    if 'units' in c.atts:
      data.atts['units'] = c.atts['units']
    if 'specie' in c.atts:
      data.atts['specie'] = c.atts['specie']

    # Cache the data
    if cache:
      data = model.cache.write(data,prefix=model.name+"_avgcolumn_"+fieldname+self.suffix, suffix=self.end_suffix)

    data = rotate_grid(data)
    return data



  def do (self, inputs):
    from .movie import ContourMovie

    plotname = 'X'+self.fieldname
    prefix = '_'.join(inp.name for inp in inputs) + '_' + plotname + self.suffix + self.end_suffix

    fields = [inp.find_best(self.fieldname) for inp in inputs]
    subtitles = [inp.title for inp in inputs]
    title = '%s (in %s)'%(plotname,self.units)

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(fields),1)

    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

    movie.save (outdir=self.outdir, prefix=prefix)

from . import table
table['xcol'] = XCol

