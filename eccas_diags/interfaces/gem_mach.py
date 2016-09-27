from .gem import GEM_Data

class GEMMACH_Data(GEM_Data):
  """
  Model output from GEM-MACH experiments.
  """

  field_list = GEM_Data.field_list + (
    ('TCO', 'CO', 'ug kg(semidry_air)-1'),
  )


# Add this interface to the table.
from . import table
table['gem-mach'] = GEMMACH_Data

