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
          # Otherwise, need the axes to match if we're not doing interpolation
          if (not self.interp_diff) and (ax1 != ax2):
            match = False
        # If all criteria on the axes are met, we can do a difference on these
        # fields.
        if match:
          yield inputs[i], inputs[j]

  # Helper method to do the interpolation.
  @staticmethod
  def _interp (field, target):
    from pygeode.interp import interpolate
    # Keep track of axis order, since PyGeode 1.0.x changes the order
    # after an interpolation.
    order = [type(a) for a in field.axes]
    for i,axistype in enumerate(order):
      axis1 = field.axes[i]
      axis2 = target.axes[i]
      # Check if interpolation is needed
      if axis1 == axis2: continue
      field = interpolate(field, inaxis=axistype, outaxis=target.getaxis(axistype))
      field = field.transpose(*order)
    return field

  # Do the differencel
  def _transform_inputs (self, inputs):
    from ..common import same_times
    from ..interfaces import DerivedProduct
    inputs = super(Diff,self)._transform_inputs(inputs)
    # Plot a difference field as well.
    fields = [inp.find_best(self.fieldname) for inp in inputs]
    # Interpolate the second field to the first field?
    if self.interp_diff:
      fields[1] = nearesttime(fields[1], fields[0].time)
      fields[1] = self._interp(fields[1],fields[0])
    else:
      # Use only the common timesteps between the fields
      fields = same_times (*fields)
    diff = fields[1]-fields[0]
    diff.name=self.fieldname+'_diff'
    # Cache the difference (so we get a global high/low for the colourbar)
    diff = inputs[0].cache.write(diff, prefix=inputs[0].name+'_'+str(self)+'_'+inputs[1].name+'_'+self.fieldname+self.suffix, suffix=self.end_suffix)
    # Use symmetric range for the difference.
    x = max(abs(diff.atts['low']),abs(diff.atts['high']))
    diff.atts['low'] = -x
    diff.atts['high'] = x
    # Wrap into a data product.
    diff = DerivedProduct(diff, source=inputs[0])
    diff.name = 'diff'
    diff.title = 'difference'
    diff.cmap = 'bwr'
    inputs.append(diff)
    return inputs

# Helper object - get nearest matches between two different time axes
from pygeode.var import Var
class NearestTime(Var):
  def __init__ (self, var, taxis):
    from pygeode.var import Var, copy_meta
    self.var = var
    # Normalize the time axis values so they're compatable with the source data
    taxis = type(taxis)(startdate=var.time.startdate, units=var.time.units, **taxis.auxarrays)
    # Output variable uses this new axis.
    axes = list(var.axes)
    axes[var.whichaxis('time')] = taxis
    Var.__init__(self, axes, dtype=var.dtype)
    copy_meta (var, self)
  def getview (self, view, pbar):
    import numpy as np
    itime = self.whichaxis('time')
    ind = view.integer_indices[itime]
    target_times = self.time.values[ind]
    source_taxis = self.var.axes[itime]
    source_ind = [np.argmin(abs(source_taxis.values-t)) for t in target_times]
    inview = view.replace_axis(itime, source_taxis, source_ind)
    return inview.get(self.var)
def nearesttime (var, taxis):
  return NearestTime(var,taxis)
del Var

