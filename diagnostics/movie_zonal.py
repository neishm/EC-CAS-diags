if True:

  def find_applicable_models (inputs, fieldname, zaxis):
    from ..common import have_gridded_3d_data
    models = []
    other_fieldname = {'gph':'geopotential_height','plev':'air_pressure'}[zaxis]
    for x in inputs:
      if any (fieldname in d and other_fieldname in d and have_gridded_3d_data(d) for d in x.datasets):
        models.append(x)
    return models

from . import TimeVaryingDiagnostic
class ZonalMean(TimeVaryingDiagnostic):
  """
  Zonal mean (or standard deviation) of a field, animated in time.
  """
  #
  """
  @classmethod
  def add_args (cls, parser, handled=[]):
    super(ZonalMean,cls).add_args(parser)
    if len(handled) > 0: return  # Only run once
    parser.add_argument('--zaxis', action='store', choices=('gph','plev'), default='gph', help="The vertical coordinate to use for vertical interplation (e.g. for zonal mean plots).  Default is gph.")
    handled.append(True)
  """
  def __init__ (self, zaxis='gph', typestat='mean', **kwargs):
    super(ZonalMean,self).__init__(**kwargs)
    self.zaxis = zaxis
    self.typestat = typestat
  def _select_inputs (self, inputs):
    inputs = super(ZonalMean,self)._select_inputs(inputs)
    return find_applicable_models(inputs, fieldname=self.fieldname, zaxis=self.zaxis)
  def do (self, inputs):
    movie_zonal(inputs, fieldname=self.fieldname, units=self.units, outdir=self.outdir, zaxis=self.zaxis, typestat=self.typestat, suffix=self.suffix)

if True:
  # Convert zonal mean data (on height)
  def zonalmean_gph (model, fieldname, units, typestat, suffix=""):
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
    if typestat == "mean":
      var_mean = var.nanmean('lon')
    else:
      # Make sure the zonal mean gets cached before use in subsequent
      # calculations.
      # Otherwise, it could cause an O(n^2) slowdown of the diagnostics.
      var_mean = zonalmean_gph (model, fieldname, units, typestat="mean", suffix=suffix)

    # Do a zonal standard deviation
    var_stdev = (var-var_mean).nanstdev('lon')
    var_stdev.name = fieldname
  
    if typestat == "stdev" : var=var_stdev   
    if typestat == "mean" : var=var_mean

    # Cache the zonalmean data
    var = model.cache.write(var, prefix=model.name+'_zonal'+typestat+'_gph_'+fieldname+suffix)

    return var


  # Convert zonal mean data (on pressure levels)
  def zonalmean_pres (model, fieldname, units, typestat, suffix=""):
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
    if typestat == "mean":
      var_mean = var.nanmean('lon')
    else:
      # Make sure the zonal mean gets cached before use in subsequent
      # calculations.
      # Otherwise, it could cause an O(n^2) slowdown of the diagnostics.
      var_mean = zonalmean_gph (model, fieldname, units, typestat="mean", suffix=suffix)

    # Do a zonal standard deviation
    var_stdev = (var-var_mean).nanstdev('lon')
    var_stdev.name = fieldname
  
    if typestat == "stdev" : var=var_stdev   
    if typestat == "mean" : var=var_mean

    # Cache the zonalmean data
    var = model.cache.write(var, prefix=model.name+'_zonal'+typestat+'_pres_'+fieldname+suffix)

    return var


from .movie import ZonalMovie
if True:

  def movie_zonal (models, fieldname, units, outdir, zaxis='gph', typestat='mean', suffix=""):

    assert zaxis in ('gph','plev')

    prefix = '_'.join(m.name for m in models) + '_zonal'+typestat+'_'+fieldname+'_on_'+zaxis+suffix
    title = 'Zonal %s %s (in %s)'%(typestat,fieldname,units)
    aspect_ratio = 1.0
    shape = (1,len(models))

    if zaxis == 'gph':
      fields = [zonalmean_gph(m,fieldname,units,typestat,suffix=suffix) for m in models]
    else:
      fields = [zonalmean_pres(m,fieldname,units,typestat,suffix=suffix) for m in models]

    subtitles = [m.title for m in models]

    movie = ZonalMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio=aspect_ratio)

    movie.save (outdir=outdir, prefix=prefix)


from . import table
table['zonal-movie'] = ZonalMean

