from .movie_zonal import ZonalMean
from .diff import Diff
class ZonalMeanDiff(Diff,ZonalMean):
  """
  Difference between two zonal mean fields, animated in time.
  """

from . import table
table['zonal-mean-diff'] = ZonalMeanDiff

