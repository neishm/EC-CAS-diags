# Average column diagnostic

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.

# Compute total column of a tracer
# (in kg/m2)
def totalcolumn (model, fieldname):
  from common import convert, grav as g, number_of_levels, number_of_timesteps

  c, dp = model.data.find_best([fieldname,'dp'], maximize=(number_of_levels,number_of_timesteps))
  c = convert(c, 'kg kg(air)-1')
  dp = convert(dp, 'Pa')

  # Integrate
  data = (c*dp).sum('zaxis') / g
  data.name = fieldname
  data.atts['units'] = 'kg m-2'

  # Cache the data
  return model.cache.write(data,prefix="totalcolumn_"+fieldname)


# Compute average column of a tracer
def avgcolumn (model, fieldname):
  from common import number_of_levels, number_of_timesteps
  c, dp = model.data.find_best([fieldname,'dp'], maximize=(number_of_levels,number_of_timesteps))
  data = (c*dp).sum('zaxis') / dp.sum('zaxis')
  data.name = fieldname
  if 'units' in c.atts:
    data.atts['units'] = c.atts['units']

  # Cache the data
  return model.cache.write(data,prefix="avgcolumn_"+fieldname)




# Get column average
def get_xcol (experiment, fieldname, units):
  from common import rotate_grid, convert

  xcol = avgcolumn(experiment, fieldname)

  # Rotate the longitudes to 0,360
  if xcol.lon[1] < 0:
    xcol = rotate_grid(xcol)

  # Convert to the required units
  xcol = convert(xcol,units)

  return xcol


def xcol (models, fieldname, units, outdir):
  from movie import ContourMovie

  plotname = 'X'+fieldname
  models = [m for m in models if m is not None]
  prefix = '_'.join(m.name for m in models) + '_' + plotname

  fields = [get_xcol(m,fieldname,units) for m in models]
  subtitles = [m.title for m in models]
  title = '%s (in %s)'%(plotname,units)

  aspect_ratio = 0.4  # height / width for each panel

  shape = (len(fields),1)

  movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

  movie.save (outdir=outdir, prefix=prefix)

