from eccas import ECCAS_Data

class ECCAS_Moist(ECCAS_Data):

  # Modify the fields to all be w.r.t. moist air
  field_list = tuple((gem_name,long_name,units.replace('(dry_air)','(air)')) for gem_name,long_name,units in ECCAS_Data.field_list)

# Add this interface to the table.
from interfaces import table
table['eccas-moist'] = ECCAS_Moist

