###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################


# Extra stuff for difference diagnostics.
from . import Diagnostic
class Diff(Diagnostic):
  cache_diff = True  # Whether to cache the difference values.
                     # Note: this is needed for low/high values if the diff
                     # is plotted directly.

  @classmethod
  def add_args (cls, parser,  handled=[]):
    super(Diff,cls).add_args(parser)
    if len(handled) > 0: return  # Only run once
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

  # Helper method - get the best dataset to use for an input
  def _best_dataset (self, input):
    # First, find the best instance of the required field.
    field = input.find_best(self.fieldname)
    # Then, find the dataset where that instance came from.
    for dataset in input.datasets:
      if any(v is field for v in dataset):
        return dataset
    raise KeyError("Unable to find the required field in the dataset.")

  # Do the difference
  def _transform_inputs (self, inputs):
    from ..common import same_times
    from ..interfaces import DerivedProduct
    inputs = super(Diff,self)._transform_inputs(inputs)
    outputs = []
    # Find the best datasets to use (must include the field of interest).
    datasets = map(self._best_dataset, inputs)
    # First, get the fields of interest.
    fields = [datasets[0][self.fieldname], datasets[1][self.fieldname]]
    # Interpolate the second field to the first field?
    if self.interp_diff:
      fields[1] = nearesttime(fields[1], fields[0].time)
      fields[1] = self._interp(fields[1],fields[0])
    else:
      # Use only the common timesteps between the fields
      fields = same_times (*fields)
    # Calculate a difference field.
    diff = fields[0]-fields[1]
    diff.name=self.fieldname+'_diff'
    # Cache the difference (so we get a global high/low for the colourbar)
    if self.cache_diff:
      diff = inputs[0].cache.write(diff, prefix=inputs[0].name+'_'+str(self)+'_with_'+inputs[1].name+'_'+self.fieldname+self.suffix, suffix=self.end_suffix)
      # Use symmetric range for the difference.
      x = max(abs(diff.atts['low']),abs(diff.atts['high']))
      diff.atts['low'] = -x
      diff.atts['high'] = x
    # Add any extra fields from the first dataset, which may be needed later.
    outputs.append(diff)
    for field in datasets[0]:
      if field.name != self.fieldname:
        outputs.append(field)

    # Wrap into a data product.
    diff = DerivedProduct(outputs, source=inputs[0])
    diff.name = 'diff'
    if inputs[0].desc is not None and inputs[1].desc is not None:
      diff.title = '%s - %s'%(inputs[0].desc, inputs[1].desc)
    else:
      diff.title = 'Difference (%s - %s)'%(inputs[0].name, inputs[1].name)
    diff.cmap = 'bwr'
    # Colour out-of-range values instead of making them white.
    diff.cap_extremes = True
    return list(inputs) + [diff]

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

