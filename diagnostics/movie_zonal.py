if True:

  def find_applicable_models (inputs, fieldname):
    from ..common import have_gridded_data
    models = []
    for x in inputs:
      if any (fieldname in d and have_gridded_data(d) for d in x.datasets):
        models.append(x)
    if len(models) == 0:
      raise ValueError("No inputs match the criteria.")
    return models

  def do_all (inputs, fieldname, units, outdir, **kwargs):
    models = find_applicable_models(inputs, fieldname)
    movie_zonal(models, fieldname, units, outdir, **kwargs)

  # Convert zonal mean data (on height)
  def zonalmean_gph (model, fieldname, units):
    from pygeode.interp import interpolate
    from pygeode.axis import Height
    from ..common import find_and_convert, number_of_levels, number_of_timesteps, remove_repeated_longitude
    import numpy as np

    var, z = find_and_convert(model, [fieldname,'geopotential_height'], [units,'m'], maximize=(number_of_levels,number_of_timesteps))

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


  # Convert zonal mean data (on pressure levels)
  def zonalmean_pres (model, fieldname, units):
    from pygeode.interp import interpolate
    from pygeode.axis import Pres
    from ..common import find_and_convert, number_of_levels, number_of_timesteps, remove_repeated_longitude
    import numpy as np

    var, p = find_and_convert(model, [fieldname,'air_pressure'], [units,'hPa'], maximize=(number_of_levels,number_of_timesteps))

    pres = Pres(np.exp(np.linspace(np.log(1000),np.log(.1),100)), name='pressure')

    # Define the final expected order of axes
    # (since 'interpolate' moves the interpolated axis)
    axes = [a.name for a in var.axes]
    axes[var.whichaxis('zaxis')] = 'pressure'

    # Do the interpolation
    var = interpolate(var, inaxis='zaxis', outaxis=pres, inx=p.log(), outx=pres.log())

    # Recover the expected order of axes
    var = var.transpose(*axes)

    # Remove any repeated longtiude (for global data)
    var = remove_repeated_longitude(var)

    # Do the zonal mean
    var = var.nanmean('lon')

    # Cache the zonalmean data
    var = model.cache.write(var, prefix='zonalmean_pres_'+fieldname)

    return var


# Modify ContourMovie to hack in the "height" label
from .movie import ContourMovie
class ZonalMovie (ContourMovie):
  # Modify the panel rendering to show the y-axis on the first panel,
  # and override the latitude labels
  def render_panel (self, axis, field, n):
    from .movie import ContourMovie
    ContourMovie.render_panel (self, axis, field, n)
    if n == 0:
      axis.set_ylabel(field.zaxis.name)
    else:
      axis.set_ylabel('')
    if self.shape[1] >= 3:
      axis.set_xticks([-90,-60,-30,0,30,60,90])
      axis.set_xticklabels(['90S','','','EQ','','','90N'])
del ContourMovie


if True:

  def movie_zonal (models, fieldname, units, outdir, zaxis='gph'):

    assert zaxis in ('gph','plev')

    models = [m for m in models if m is not None]
    prefix = '_'.join(m.name for m in models) + '_zonal'+fieldname+'_on_'+zaxis
    title = 'Zonal mean %s (in %s)'%(fieldname,units)
    aspect_ratio = 1.0
    shape = (1,len(models))

    if zaxis == 'gph':
      fields = [zonalmean_gph(m,fieldname,units) for m in models]
    else:
      fields = [zonalmean_pres(m,fieldname,units) for m in models]

    subtitles = [m.title for m in models]

    movie = ZonalMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio=aspect_ratio)

    movie.save (outdir=outdir, prefix=prefix)

