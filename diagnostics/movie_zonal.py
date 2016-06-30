
from . import TimeVaryingDiagnostic
class ZonalMean(TimeVaryingDiagnostic):
  """
  Zonal mean (or standard deviation) of a field, animated in time.
  """

  def __str__ (self):
    return 'zonal'+self.typestat+'_'+self.typestat

  @classmethod
  def add_args (cls, parser, handled=[]):
    super(ZonalMean,cls).add_args(parser)
    if len(handled) > 0: return  # Only run once
    parser.add_argument('--zonalmean-zaxis', dest='zaxis', action='store', choices=('gph','plev','model'), default='gph', help="The vertical coordinate to use for vertical interplation (e.g. for zonal mean plots).  Default is gph.")
    handled.append(True)
  def __init__ (self, zaxis='gph', typestat='mean', **kwargs):
    super(ZonalMean,self).__init__(**kwargs)
    self.zaxis = zaxis
    self.typestat = typestat
  def _check_dataset (self, dataset):
    from ..common import have_gridded_3d_data
    if super(ZonalMean,self)._check_dataset(dataset) is False:
      return False
    if self.fieldname not in dataset: return False
    if 'lon' not in dataset: return False
    if self.zaxis == 'gph' and 'geopotential_height' not in dataset:
      return False
    if self.zaxis == 'plev' and 'air_pressure' not in dataset:
      return False
    return have_gridded_3d_data(dataset)
  def _transform_input (self, input):
    from ..interfaces import DerivedProduct
    input = super(ZonalMean,self)._transform_input(input)
    if self.zaxis == 'gph':
      var = self._zonalmean_gph (input)
    elif self.zaxis == 'plev':
      var = self._zonalmean_pres (input)
    elif self.zaxis == 'model':
      var = self._zonalmean_model_lev (input)
    else:
      raise ValueError("Unhandled zaxis type '%s'"%self.zaxis)
    return DerivedProduct(var, source=input)

  # Convert zonal mean data (on height)
  def _zonalmean_gph (self, model, typestat=None):
    from pygeode.interp import interpolate
    from pygeode.axis import Height
    from ..common import find_and_convert, number_of_levels, number_of_timesteps, remove_repeated_longitude
    import numpy as np

    fieldname = self.fieldname
    typestat = typestat or self.typestat

    var, z = find_and_convert(model, [fieldname,'geopotential_height'], [self.units,'m'], maximize=(number_of_levels,number_of_timesteps))

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
      var_mean = self._zonalmean_gph (model, typestat="mean")

    # Do a zonal standard deviation
    var_stdev = (var-var_mean).nanstdev('lon')
    var_stdev.name = fieldname
  
    if typestat == "stdev" : var=var_stdev   
    if typestat == "mean" : var=var_mean

    # Cache the zonalmean data
    var = model.cache.write(var, prefix=model.name+'_zonal'+typestat+'_gph_'+fieldname+self.suffix, suffix=self.end_suffix)

    return var

  # Convert zonal mean data (on model levels)
  def _zonalmean_model_lev (self, model, typestat=None):
    from ..common import find_and_convert, number_of_levels, number_of_timesteps, remove_repeated_longitude
    import numpy as np

    fieldname = self.fieldname
    typestat = typestat or self.typestat

    var = find_and_convert(model, fieldname, self.units, maximize=(number_of_levels,number_of_timesteps))

    # Remove any repeated longtiude (for global data)
    var = remove_repeated_longitude(var)

    # Do the zonal mean
    if typestat == "mean":
      var_mean = var.nanmean('lon')
    else:
      # Make sure the zonal mean gets cached before use in subsequent
      # calculations.
      # Otherwise, it could cause an O(n^2) slowdown of the diagnostics.
      var_mean = self._zonalmean_model_lev (model, typestat="mean")

    # Do a zonal standard deviation
    var_stdev = (var-var_mean).nanstdev('lon')
    var_stdev.name = fieldname
  
    if typestat == "stdev" : var=var_stdev   
    if typestat == "mean" : var=var_mean

    # Cache the zonalmean data
    var = model.cache.write(var, prefix=model.name+'_zonal'+typestat+'_model_lev_'+fieldname+self.suffix)

    return var

  # Convert zonal mean data (on pressure levels)
  def _zonalmean_pres (self, model, typestat=None):
    from pygeode.interp import interpolate
    from pygeode.axis import Pres
    from ..common import find_and_convert, number_of_levels, number_of_timesteps, remove_repeated_longitude
    import numpy as np

    fieldname = self.fieldname
    typestat = typestat or self.typestat

    var, p = find_and_convert(model, [fieldname,'air_pressure'], [self.units,'hPa'], maximize=(number_of_levels,number_of_timesteps))

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
      var_mean = self._zonalmean_pres (model, typestat="mean")

    # Do a zonal standard deviation
    var_stdev = (var-var_mean).nanstdev('lon')
    var_stdev.name = fieldname
  
    if typestat == "stdev" : var=var_stdev   
    if typestat == "mean" : var=var_mean

    # Cache the zonalmean data
    var = model.cache.write(var, prefix=model.name+'_zonal'+typestat+'_pres_'+fieldname+self.suffix, suffix=self.end_suffix)

    return var


  def do (self, inputs):
    from .movie import ZonalMovie

    prefix = '_'.join(inp.name for inp in inputs) + '_zonal'+self.typestat+'_'+self.fieldname+'_on_'+self.zaxis+self.suffix+self.end_suffix
    title = 'Zonal %s %s (in %s)'%(self.typestat,self.fieldname,self.units)
    aspect_ratio = 1.0
    shape = (1,len(inputs))

    subtitles = [inp.title for inp in inputs]

    fields = [inp.datasets[0].vars[0] for inp in inputs]

    movie = ZonalMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio=aspect_ratio)

    movie.save (outdir=self.outdir, prefix=prefix)


from . import table
table['zonal-movie'] = ZonalMean

