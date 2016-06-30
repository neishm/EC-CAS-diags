# Horizontal slice movie.
# Takes a field at the given level from 2 experiments, computes a difference,
# and produces a movie.
# This is/was used for checking the effects of adding convection to tracers.

from .horz_slice import HorzSlice
from .diff import Diff
class HorzSliceDiff(Diff,HorzSlice):
  """
  Difference between two data products, sampled at a particular vertical level.
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
        if f1.lat == f2.lat and f1.lon == f2.lon:
          yield [inputs[i], inputs[j]]
  def _transform_inputs (self, inputs):
    from ..common import number_of_levels, number_of_timesteps, rotate_grid, find_and_convert, same_times
    from ..interfaces import DerivedProduct

    inputs = super(HorzSliceDiff,self)._transform_inputs(inputs)

    fields = [inp.find_best(self.fieldname) for inp in inputs]

    # Use only the common timesteps between the fields
    fields = same_times (*fields)
    diff = fields[0]-fields[1]
    diff.name=self.fieldname+'_diff'
    # Cache the difference (so we get a global high/low for the colourbar)
    diff = inputs[0].cache.write(diff, prefix=inputs[0].name+'_'+self.fieldname+'_level'+self.level+"_diff_"+inputs[1].name+'_'+self.fieldname+self.suffix, suffix=self.end_suffix)
    diff = DerivedProduct(diff, source=inputs[0])
    diff.name = 'diff'
    diff.title = 'difference'
    inputs.append(diff)

    return inputs


from . import table
table['horz-slice-diff'] = HorzSliceDiff

