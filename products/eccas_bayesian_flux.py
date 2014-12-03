from eccas_flux import ECCAS_Flux_Data

class ECCAS_Bayesian_Flux(ECCAS_Flux_Data):

  field_list = list(ECCAS_Flux_Data.field_list)
  for i in range(1,12):
    field_list.append(('EL%02d'%i, 'CO2_landunit_%02d_flux'%i, 'g(C) s-1'))
  for i in range(1,12):
    field_list.append(('EO%02d'%i, 'CO2_oceanunit_%02d_flux'%i, 'g(C) s-1'))
  field_list = tuple(field_list)

# Instantiate the interface
interface = ECCAS_Bayesian_Flux()

# Define the open method as a function, so it's picklable.
def open_file (filename):
  return interface.open_file(filename)

