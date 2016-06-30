# Extra stuff for difference diagnostics.
from . import Diagnostic
class Diff(Diagnostic):

  @classmethod
  def add_args (cls, parser,  handled=[]):
    super(Diff,cls).add_args(parser)
    if len(handled) > 0: return  # Only run ones
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--interp-diff', action='store_true', help="Allow fields to be spatially interpolated for difference plots.")
    group.add_argument('--no-interp-diff', action='store_const', const=False, dest='interp_diff', help="Only do difference plots for fields on the same grid (default).")
    handled.append(True)

  def __init__ (self, interp_diff, **kwargs):
    super(Diff,self).__init__(**kwargs)
    self.interp_diff = interp_diff

  # Augment difference plot logic to interpolate fields.
  #TODO: move full difference logic here, not just interpolation case.
  def _input_combos (self, inputs):
    if not self.interp_diff:
      return super(Diff,self)._input_combos(inputs)
    else:
      raise NotImplementedError("Interpolation not implemented yet.")

