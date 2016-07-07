# Average column diagnostic with extra panel for differences

# Note: we aren't using any averaging kernal for this, so it's not directly
# comparable to satellite observations.


from .xcol import XCol
from .diff import Diff
class XColDiff(Diff,XCol):
  """
  Compute the difference of two fields, after taking the avarage column of
  each.
  """

from . import table
table['xcol-diff'] = XColDiff

