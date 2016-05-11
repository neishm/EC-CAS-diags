from .movie_zonal import ZonalMean
class ZonalMeanDiff(ZonalMean):
  """
  Difference between two zonal mean fields, animated in time.
  """
  def _input_combos (self, inputs):
    fieldname = self.fieldname
    n = len(inputs)
    for i in range(n):
      if not inputs[i].have(fieldname): continue
      for j in range(i+1,n):
        if not inputs[j].have(fieldname): continue
        f1 = inputs[i].find_best(fieldname)
        f2 = inputs[j].find_best(fieldname)
        if f1.lat == f2.lat:
          yield [inputs[i],inputs[j]]
  def _transform_inputs (self, inputs):
    from ..common import same_times
    from ..interfaces import DerivedProduct
    inputs = super(ZonalMeanDiff,self)._transform_inputs(inputs)
    # Plot a difference field as well.
    fields = [inp.find_best(self.fieldname) for inp in inputs]
    # Use only the common timesteps between the fields
    fields = same_times (*fields)
    diff = fields[0]-fields[1]
    diff.name=self.fieldname+'_diff'
    # Cache the difference (so we get a global high/low for the colourbar)
    diff = inputs[0].cache.write(diff, prefix=inputs[0].name+'_zonal'+self.typestat+'_gph_diff_'+inputs[1].name+'_'+self.fieldname+self.suffix)
    diff = DerivedProduct(diff, source=inputs[0])
    diff.name = 'diff'
    diff.title = 'difference'
    inputs.append(diff)
    return inputs

  def do (self, inputs):
    from .movie import ZonalMovie

    prefix = '_'.join(inp.name for inp in inputs) + '_zonal'+self.typestat+'_'+self.fieldname+'_on_'+self.zaxis+self.suffix
    title = 'Zonal %s %s (in %s)'%(self.typestat,self.fieldname,self.units)
    aspect_ratio = 1.0
    shape = (1,len(inputs))

    subtitles = [inp.title for inp in inputs]

    fields = [inp.datasets[0].vars[0] for inp in inputs]

    movie = ZonalMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio=aspect_ratio)

    movie.save (outdir=self.outdir, prefix=prefix)

from . import table
table['zonal-mean-diff'] = ZonalMeanDiff

