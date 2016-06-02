# Average column diagnostic with extra panel for differences

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.


from .xcol import XCol
class XColDiff(XCol):
  """
  Compute the difference of two fields, after taking the avarage column of
  each.
  """
  def _input_combos (self, inputs):
    n = len(inputs)
    for i in range(n):
      for j in range(i+1,n):
        f1 = inputs[i].find_best(self.fieldname)
        f2 = inputs[j].find_best(self.fieldname)
        if f1.lat == f2.lat and f1.lon == f2.lon:
          yield inputs[i], inputs[j]

  def _transform_inputs (self, inputs):
    from ..common import same_times
    from ..interfaces import DerivedProduct
    inputs = super(XColDiff,self)._transform_inputs(inputs)
    # Plot a difference field as well.
    fields = [inp.find_best(self.fieldname) for inp in inputs]
    # Use only the common timesteps between the fields
    fields = same_times (*fields)
    diff = fields[0]-fields[1]
    diff.name=self.fieldname+'_diff'
    # Cache the difference (so we get a global high/low for the colourbar)
    diff = inputs[0].cache.write(diff, prefix=inputs[0].name+'_xcol_diff_'+inputs[1].name+'_'+self.fieldname+self.suffix, suffix=self.end_suffix)
    diff = DerivedProduct(diff, source=inputs[0])
    diff.name = 'diff'
    diff.title = 'difference'
    inputs.append(diff)
    return inputs


  def do (self, inputs):

    from .movie import ContourMovie

    plotname = 'X'+self.fieldname
    prefix = '_'.join(inp.name for inp in inputs) + plotname + self.suffix + self.end_suffix

    fields = [inp.datasets[0].vars[0] for inp in inputs]
    subtitles = [inp.title for inp in inputs]
    title = '%s (in %s)'%(plotname,self.units)

    aspect_ratio = 0.4  # height / width for each panel

    shape = (len(fields),1)
   
    movie = ContourMovie(fields, title=title, subtitles=subtitles, shape=shape, aspect_ratio = aspect_ratio)

    movie.save (outdir=self.outdir, prefix=prefix)

from . import table
table['xcol-diff'] = XColDiff

