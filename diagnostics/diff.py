# Extra stuff for difference diagnostics.
from . import Diagnostic
class Diff(Diagnostic):

  @classmethod
  def add_args (cls, parser,  handled=[]):
    super(Diff,cls).add_args(parser)
    if len(handled) > 0: return  # Only run ones
    group = parser.add_argument_group('options for difference plots')
    group = group.add_mutually_exclusive_group()
    group.add_argument('--interp-diff', action='store_true', help="Allow fields to be spatially interpolated for difference plots.")
    group.add_argument('--no-interp-diff', action='store_const', const=False, dest='interp_diff', help="Only do difference plots for fields on the same grid (default).")
    handled.append(True)

  def __init__ (self, interp_diff, **kwargs):
    super(Diff,self).__init__(**kwargs)
    self.interp_diff = interp_diff

  # Select the fields to do the difference on.
  def _input_combos (self, inputs):
    from pygeode.timeaxis import Time
    n = len(inputs)
    for i in range(n):
      for j in range(i+1,n):
        f1 = inputs[i].find_best(self.fieldname)
        f2 = inputs[j].find_best(self.fieldname)
        if f1.naxes != f2.naxes: continue
        match = True
        for ax1, ax2 in zip(f1.axes, f2.axes):
          # Must have same types of axes
          if type(ax1) != type(ax2): match = False
          # Don't need the time axis to match (will subset it later).
          if isinstance(ax1,Time): continue
          # Otherwise, need the axes to match
          if ax1 != ax2: match = False
        # If all criteria on the axes are met, we can do a difference on these
        # fields.
        if match:
          yield inputs[i], inputs[j]

  # Do the differencel
  def _transform_inputs (self, inputs):
    from ..common import same_times
    from ..interfaces import DerivedProduct
    inputs = super(Diff,self)._transform_inputs(inputs)
    # Plot a difference field as well.
    fields = [inp.find_best(self.fieldname) for inp in inputs]
    # Use only the common timesteps between the fields
    fields = same_times (*fields)
    diff = fields[0]-fields[1]
    diff.name=self.fieldname+'_diff'
    # Cache the difference (so we get a global high/low for the colourbar)
    diff = inputs[0].cache.write(diff, prefix=inputs[0].name+'_'+str(self)+'_diff_'+inputs[1].name+'_'+self.fieldname+self.suffix, suffix=self.end_suffix)
    diff = DerivedProduct(diff, source=inputs[0])
    diff.name = 'diff'
    diff.title = 'difference'
    inputs.append(diff)
    return inputs

