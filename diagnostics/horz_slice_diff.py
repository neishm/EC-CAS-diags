# Horizontal slice movie.
# Takes a field at the given level from 2 experiments, computes a difference,
# and produces a movie.
# This is/was used for checking the effects of adding convection to tracers.

from . import TimeVaryingDiagnostic
class HorzSliceDiff(TimeVaryingDiagnostic):
  """
  Difference between two data products, sampled at a particular vertical level.
  """
  def _check_dataset (self, dataset):
    from ..common import have_gridded_3d_data
    if super(HorzSliceDiff,self)._check_dataset(dataset) is False:
      return False
    return have_gridded_3d_data(dataset)
  def __init__ (self, level, **kwargs):
    super(HorzSliceDiff,self).__init__(**kwargs)
    self.level = level
  def _input_combos (self, inputs):
    fieldname = self.fieldname
    n = len(inputs)
    for i in range(n):
      if not inputs[i].have(fieldname): continue
      for j in range(i+1,n):
        if not inputs[j].have(fieldname): continue
        f1 = inputs[i].find_best(fieldname)
        f2 = inputs[j].find_best(fieldname)
        if f1.lat == f2.lat and f1.lon == f2.lon:
          yield [inputs[i], inputs[j]]
  def _transform_inputs (self, inputs):
    from ..common import number_of_levels, number_of_timesteps, rotate_grid, find_and_convert, same_times
    from ..interfaces import DerivedProduct
    transformed = []
    for inp in inputs:
      c = find_and_convert(inp, self.fieldname, self.units, maximize=(number_of_levels,number_of_timesteps))

      # Apply the slice
      c = c(zaxis=float(self.level))

      # Rotate the longitudes to 0,360
      c = rotate_grid(c)

      # Cache the data
      c = inp.cache.write(c,prefix=inp.name+'_'+c.zaxis.name+self.level+"_"+self.fieldname+self.suffix, suffix=self.end_suffix)

      transformed.append(DerivedProduct(c, source=inp))

    fields = [tr.find_best(self.fieldname) for tr in transformed]

    # Use only the common timesteps between the fields
    fields = same_times (*fields)
    diff = fields[0]-fields[1]
    diff.name=self.fieldname+'_diff'
    # Cache the difference (so we get a global high/low for the colourbar)
    diff = inputs[0].cache.write(diff, prefix=inputs[0].name+'_'+self.fieldname+'_level'+self.level+"_diff_"+inputs[1].name+'_'+self.fieldname+self.suffix, suffix=self.end_suffix)
    diff = DerivedProduct(diff, source=inputs[0])
    diff.name = 'diff'
    diff.title = 'difference'
    transformed.append(diff)

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
table['horz-slice-diff'] = HorzSliceDiff

