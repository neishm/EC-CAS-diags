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
    from ..common import have_gridded_3d_data
    inputs = super(XCol,self)._select_inputs(inputs)
    selected = []
    for x in inputs:
      if any (have_gridded_3d_data(d) for d in x.datasets):
        selected.append(x)
    return selected


  # Compute total column of a tracer
  # (in kg/m2)
  def totalcolumn (self, model):
    from ..common import find_and_convert, grav as g, number_of_levels, number_of_timesteps
    fieldname = self.fieldname

    c, dp = find_and_convert (model, [fieldname,'dp'], ['kg kg(air)-1', 'Pa'], maximize=(number_of_levels,number_of_timesteps))

    # Integrate
    data = (c*dp).sum('zaxis') / g
    data.name = fieldname
    data.atts['units'] = 'kg m-2'

    if 'specie' in c.atts:
      data.atts['specie'] = c.atts['specie']

    # Cache the data
    return model.cache.write(data,prefix=model.name+"_totalcolumn_"+fieldname+self.suffix)


  # Compute average column of a tracer
  def avgcolumn (self, model):
    from ..common import find_and_convert, number_of_levels, number_of_timesteps
    fieldname = self.fieldname

    c, dp = find_and_convert(model, [fieldname,'dp'], [self.units,'Pa'], maximize=(number_of_levels,number_of_timesteps))

    data = (c*dp).sum('zaxis') / dp.sum('zaxis')
    data.name = fieldname
    if 'units' in c.atts:
      data.atts['units'] = c.atts['units']
    if 'specie' in c.atts:
      data.atts['specie'] = c.atts['specie']

    # Cache the data
    return model.cache.write(data,prefix=model.name+"_avgcolumn_"+fieldname+self.suffix)




  # Get column average
  def get_xcol (self, experiment):
    from ..common import rotate_grid, convert

    xcol = self.avgcolumn(experiment)

    # Rotate the longitudes to 0,360
    if xcol.lon[1] < 0:
      xcol = rotate_grid(xcol)

    # Convert to the required units
    xcol = convert(xcol,self.units)

    return xcol


  def do (self, inputs):
    from .movie import ContourMovie

    plotname = 'X'+self.fieldname
    prefix = '_'.join(inp.name for inp in inputs) + '_' + plotname + self.suffix

    fields = [self.get_xcol(inp) for inp in inputs]
    subtitles = [inp.title for inp in inputs]
    title = '%s (in %s)'%(plotname,self.units)

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(fields),1)

    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

    movie.save (outdir=self.outdir, prefix=prefix)

from . import table
table['xcol'] = XCol

