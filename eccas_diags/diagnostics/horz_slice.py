# Horizontal slice movie.

from . import TimeVaryingDiagnostic
class HorzSlice(TimeVaryingDiagnostic):
  """
  Sample data at a particular vertical level.
  """

  def __str__ (self):
    return 'level'+self.level

  def _check_dataset (self, dataset):
    from ..common import have_gridded_3d_data, have_level
    if super(HorzSlice,self)._check_dataset(dataset) is False:
      return False
    return have_gridded_3d_data(dataset) and have_level(float(self.level))(dataset)
  def __init__ (self, level, **kwargs):
    super(HorzSlice,self).__init__(**kwargs)
    self.level = level
  def _transform_input (self, input):
    from ..common import number_of_timesteps, have_level, rotate_grid, find_and_convert
    from ..interfaces import DerivedProduct

    input = super(HorzSlice,self)._transform_input(input)
    c = find_and_convert(input, self.fieldname, self.units, maximize=number_of_timesteps, requirement=have_level(float(self.level)))

    # Apply the slice
    c = c(zaxis=float(self.level))

    # Rotate the longitudes to 0,360
    c = rotate_grid(c)

    # Cache the data
    c = input.cache.write(c,prefix=input.name+'_'+c.zaxis.name+self.level+"_"+self.fieldname+self.suffix, suffix=self.end_suffix)

    return DerivedProduct(c, source=input)


  def do (self, inputs):
    from .movie import ContourMovie

    plotname = self.fieldname+"_level"+self.level
    prefix = '_'.join(inp.name for inp in inputs) + '_' + plotname + self.suffix + self.end_suffix

    fields = [inp.datasets[0].vars[0] for inp in inputs]
    subtitles = [inp.title for inp in inputs]
    title = '%s at level %s'%(self.fieldname,self.level)

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(inputs),1)

    cmaps = [inp.cmap for inp in inputs]
    cap_extremes = [getattr(inp,'cap_extremes',False) for inp in inputs]

    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio, cmaps=cmaps, cap_extremes=cap_extremes)

    movie.save (outdir=self.outdir, prefix=prefix)


from . import table
table['horz-slice'] = HorzSlice

