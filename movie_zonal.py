# Convert zonal mean data (on height)
def zonalmean_gph (model, fieldname):
  from pygeode.interp import interpolate
  from pygeode.axis import Height
  from common import convert, number_of_levels, number_of_timesteps, remove_repeated_longitude
  import numpy as np

  var, z = model.data.find_best([fieldname,'geopotential_height'], maximize=(number_of_levels,number_of_timesteps))
  z = convert(z,'m')

  height = Height(range(68), name='height')

  # Define the final expected order of axes
  # (since 'interpolate' moves the interpolated axis)
  axes = [a.name for a in var.axes]
  axes[var.whichaxis('zaxis')] = 'height'

  # Do the interpolation
  var = interpolate(var, inaxis='zaxis', outaxis=height, inx=z/1000.)

  # Recover the expected order of axes
  var = var.transpose(*axes)

  # Remove any repeated longtiude (for global data)
  var = remove_repeated_longitude(var)

  # Do the zonal mean
  var = var.nanmean('lon')

  # Cache the zonalmean data
  var = model.cache.write(var, prefix='zonalmean_gph_'+fieldname)

  return var


# Modify ContourMovie to hack in the "height" label
from movie import ContourMovie
class ZonalMovie (ContourMovie):
  def render_panel (self, axis, field, n):
    from movie import ContourMovie
    ContourMovie.render_panel (self, axis, field, n)
    axis.set_ylabel(field.zaxis.name)
del ContourMovie

def movie_zonal (models, fieldname, units, outdir):

  from common import convert

  models = [m for m in models if m is not None]
  prefix = '_'.join(m.name for m in models) + '_zonal'+fieldname
  title = 'Zonal mean %s (in %s)'%(fieldname,units)
  aspect_ratio = 1.0
  shape = (1,len(models))

  fields = [zonalmean_gph(m,fieldname) for m in models]

  # Unit conversion
  fields = [convert(f,units) for f in fields]

  subtitles = [m.title for m in models]

  movie = ZonalMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio=aspect_ratio)

  movie.save (outdir=outdir, prefix=prefix)

