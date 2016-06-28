# Horizontal slice movie.

from . import TimeVaryingDiagnostic
class HorzSlice(TimeVaryingDiagnostic):
  """
  Sample data at a particular vertical level.
  """
  def _check_dataset (self, dataset):
    from ..common import have_gridded_3d_data
    if super(HorzSlice,self)._check_dataset(dataset) is False:
      return False
    return have_gridded_3d_data(dataset)
  def __init__ (self, level, **kwargs):
    super(HorzSlice,self).__init__(**kwargs)
    self.level = level
  def _transform_inputs (self, inputs):
    from ..common import number_of_timesteps, have_level, rotate_grid, find_and_convert
    from ..interfaces import DerivedProduct

    inputs = super(HorzSlice,self)._transform_inputs(inputs)
    transformed = []
    for inp in inputs:
      c = find_and_convert(inp, self.fieldname, self.units, maximize=number_of_timesteps, requirement=have_level(float(self.level)))

      # Apply the slice
      c = c(zaxis=float(self.level))

      # Rotate the longitudes to 0,360
      c = rotate_grid(c)

      # Cache the data
      c = inp.cache.write(c,prefix=inp.name+'_'+c.zaxis.name+self.level+"_"+self.fieldname+self.suffix, suffix=self.end_suffix)

      transformed.append(DerivedProduct(c, source=inp))

    return transformed


  def do (self, inputs):
    from .movie import ContourMovie

    plotname = self.fieldname+"_level"+self.level
    prefix = '_'.join(inp.name for inp in inputs) + '_' + plotname + self.suffix + self.end_suffix

    fields = [inp.datasets[0].vars[0] for inp in inputs]
    subtitles = [inp.title for inp in inputs]
    title = '%s at level %s'%(self.fieldname,self.level)

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(inputs),1)

    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

    movie.save (outdir=self.outdir, prefix=prefix)


from . import table
table['horz-slice'] = HorzSlice

