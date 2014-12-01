from eccas import ECCAS_Data

class ECCAS_Bayesian(ECCAS_Data):

  field_list = list(ECCAS_Data.field_list)
  for i in range(1,12):
    field_list.append(('TL%02d'%i, 'CO2_landunit_%02d'%i, 'ug(C) kg(air)-1'))
  for i in range(1,12):
    field_list.append(('TO%02d'%i, 'CO2_oceanunit_%02d'%i, 'ug(C) kg(air)-1'))
  field_list = tuple(field_list)

# Instantiate the interface
interface = ECCAS_Bayesian()

# Define the open method as a function, so it's picklable.
def open_file (filename):
  return interface.open_file(filename)

