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

from . import table
table['horz-slice-diff'] = HorzSliceDiff

