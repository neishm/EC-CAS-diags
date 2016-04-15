# Average column diagnostic

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.


if True:

  def find_applicable_models (inputs, fieldname):
    from ..common import have_gridded_3d_data
    models = []
    for x in inputs:
      if any (fieldname in d and have_gridded_3d_data(d) for d in x.datasets):
        models.append(x)
    return models

from . import Diagnostic
class XCol(Diagnostic):
  """
  Show the average column of a field, animated in time.  Note that no averaging
  kernel is used in the average, it is simply weighted by air mass.
  """
  def _select_inputs (self, inputs):
    inputs = super(XCol,self)._select_inputs(inputs)
    return find_applicable_models(inputs, self.fieldname)
  def do (self, inputs):
    xcol (inputs, fieldname=self.fieldname, units=self.units, outdir=self.outdir)

if True:

  # Compute total column of a tracer
  # (in kg/m2)
  def totalcolumn (model, fieldname):
    from ..common import find_and_convert, grav as g, number_of_levels, number_of_timesteps

    c, dp = find_and_convert (model, [fieldname,'dp'], ['kg kg(air)-1', 'Pa'], maximize=(number_of_levels,number_of_timesteps))

    # Integrate
    data = (c*dp).sum('zaxis') / g
    data.name = fieldname
    data.atts['units'] = 'kg m-2'

    if 'specie' in c.atts:
      data.atts['specie'] = c.atts['specie']

    # Cache the data
    return model.cache.write(data,prefix=model.name+"_totalcolumn_"+fieldname)


  # Compute average column of a tracer
  def avgcolumn (model, fieldname, units):
    from ..common import find_and_convert, number_of_levels, number_of_timesteps
    c, dp = find_and_convert(model, [fieldname,'dp'], [units,'Pa'], maximize=(number_of_levels,number_of_timesteps))

    data = (c*dp).sum('zaxis') / dp.sum('zaxis')
    data.name = fieldname
    if 'units' in c.atts:
      data.atts['units'] = c.atts['units']
    if 'specie' in c.atts:
      data.atts['specie'] = c.atts['specie']

    # Cache the data
    return model.cache.write(data,prefix=model.name+"_avgcolumn_"+fieldname)




  # Get column average
  def get_xcol (experiment, fieldname, units):
    from ..common import rotate_grid, convert

    xcol = avgcolumn(experiment, fieldname, units)

    # Rotate the longitudes to 0,360
    if xcol.lon[1] < 0:
      xcol = rotate_grid(xcol)

    # Convert to the required units
    xcol = convert(xcol,units)

    return xcol


  def xcol (models, fieldname, units, outdir):
    from .movie import ContourMovie

    plotname = 'X'+fieldname
    prefix = '_'.join(m.name for m in models) + '_' + plotname

    fields = [get_xcol(m,fieldname,units) for m in models]
    subtitles = [m.title for m in models]
    title = '%s (in %s)'%(plotname,units)

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(fields),1)

    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

    movie.save (outdir=outdir, prefix=prefix)

from . import table
table['xcol'] = XCol

