from .eccas_dry import ECCAS_Data

class ECCAS_Bayesian(ECCAS_Data):

  field_list = list(ECCAS_Data.field_list)
  for i in range(1,12):
    field_list.append(('TL%02d'%i, 'CO2_landunit_%02d'%i, 'ug(C) kg(dry_air)-1'))
  for i in range(1,12):
    field_list.append(('TO%02d'%i, 'CO2_oceanunit_%02d'%i, 'ug(C) kg(dry_air)-1'))
  field_list = tuple(field_list)

# Add this interface to the table.
from . import table
table['eccas-bayesian'] = ECCAS_Bayesian

