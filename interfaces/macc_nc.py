
from . import DataProduct
class MACC_Data(DataProduct):

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('lnsp', 'logarithm_of_surface_pressure', ''),
    ('co2', 'CO2', 'kg kg(air)-1'),
    ('q', 'specific_humidity', 'kg(H2O) kg(air)-1'),
  )

  A_interface = [
    0.000000, 2.000365, 3.102241, 4.666084, 6.827977, 9.746966,
    13.605424, 18.608931, 24.985718, 32.985710, 42.879242,
    54.955463, 69.520576, 86.895882, 107.415741, 131.425507,
    159.279404, 191.338562, 227.968948, 269.539581, 316.420746,
    368.982361, 427.592499, 492.616028, 564.413452, 643.339905,
    729.744141, 823.967834, 926.344910, 1037.201172, 1156.853638,
    1285.610352, 1423.770142, 1571.622925, 1729.448975, 1897.519287,
    2076.095947, 2265.431641, 2465.770508, 2677.348145, 2900.391357,
    3135.119385, 3381.743652, 3640.468262, 3911.490479, 4194.930664,
    4490.817383, 4799.149414, 5119.895020, 5452.990723, 5798.344727,
    6156.074219, 6526.946777, 6911.870605, 7311.869141, 7727.412109,
    8159.354004, 8608.525391, 9076.400391, 9562.682617, 10065.978516,
    10584.631836, 11116.662109, 11660.067383, 12211.547852, 12766.873047,
    13324.668945, 13881.331055, 14432.139648, 14975.615234, 15508.256836,
    16026.115234, 16527.322266, 17008.789062, 17467.613281, 17901.621094,
    18308.433594, 18685.718750, 19031.289062, 19343.511719, 19620.042969,
    19859.390625, 20059.931641, 20219.664062, 20337.863281, 20412.308594,
    20442.078125, 20425.718750, 20361.816406, 20249.511719, 20087.085938,
    19874.025391, 19608.572266, 19290.226562, 18917.460938, 18489.707031,
    18006.925781, 17471.839844, 16888.687500, 16262.046875, 15596.695312,
    14898.453125, 14173.324219, 13427.769531, 12668.257812, 11901.339844,
    11133.304688, 10370.175781, 9617.515625, 8880.453125, 8163.375000,
    7470.343750, 6804.421875, 6168.531250, 5564.382812, 4993.796875,
    4457.375000, 3955.960938, 3489.234375, 3057.265625, 2659.140625,
    2294.242188, 1961.500000, 1659.476562, 1387.546875, 1143.250000,
    926.507812, 734.992188, 568.062500, 424.414062, 302.476562,
    202.484375, 122.101562, 62.781250, 22.835938, 3.757813,
    0.000000, 0.000000
  ]
  B_interface = [
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000007, 0.000024, 0.000059, 0.000112, 0.000199,
    0.000340, 0.000562, 0.000890, 0.001353, 0.001992,
    0.002857, 0.003971, 0.005378, 0.007133, 0.009261,
    0.011806, 0.014816, 0.018318, 0.022355, 0.026964,
    0.032176, 0.038026, 0.044548, 0.051773, 0.059728,
    0.068448, 0.077958, 0.088286, 0.099462, 0.111505,
    0.124448, 0.138313, 0.153125, 0.168910, 0.185689,
    0.203491, 0.222333, 0.242244, 0.263242, 0.285354,
    0.308598, 0.332939, 0.358254, 0.384363, 0.411125,
    0.438391, 0.466003, 0.493800, 0.521619, 0.549301,
    0.576692, 0.603648, 0.630036, 0.655736, 0.680643,
    0.704669, 0.727739, 0.749797, 0.770798, 0.790717,
    0.809536, 0.827256, 0.843881, 0.859432, 0.873929,
    0.887408, 0.899900, 0.911448, 0.922096, 0.931881,
    0.940860, 0.949064, 0.956550, 0.963352, 0.969513,
    0.975078, 0.980072, 0.984542, 0.988500, 0.991984,
    0.995003, 0.997630, 1.000000
  ]

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    return netcdf.open(filename)


  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, dataset):
    from pygeode.axis import Hybrid
    from pygeode.ufunc import exp
    from pygeode.var import Var
    import numpy as np

    A_interface = np.array(cls.A_interface)
    B_interface = np.array(cls.B_interface)
    A = (A_interface[1:] + A_interface[:-1]) * 0.5
    B = (B_interface[1:] + B_interface[:-1]) * 0.5
    dA = (A_interface[1:] - A_interface[:-1])
    dB = (B_interface[1:] - B_interface[:-1])

    # Locate a z-axis
    dataset = list(dataset)
    zaxis = None
    for var in dataset:
      if var.hasaxis('level'):
        zaxis = var.getaxis('level')

    # Create a proper z-axis
    if zaxis is not None:
      zaxis = Hybrid(zaxis.values, A=A, B=B)
      for i, var in enumerate(dataset):
        if var.hasaxis('level'):
          dataset[i] = var.replace_axes(level=zaxis)

    # Apply fieldname conversions
    dataset = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Add pressure info
    if 'logarithm_of_surface_pressure' in data and zaxis is not None:
      Ps = exp(data['logarithm_of_surface_pressure'])
      Ps.atts['units'] = 'Pa'
      data['surface_pressure'] = Ps
      A = zaxis.auxasvar('A')
      B = zaxis.auxasvar('B')
      P = A + B*Ps
      P = P.transpose('time','zaxis','lat','lon')
      P.atts['units'] = 'Pa'
      data['air_pressure'] = P

      dA = Var([zaxis], values=dA)
      dB = Var([zaxis], values=dB)
      dP = dA + dB*Ps
      dP = dP.transpose('time','zaxis','lat','lon')
      dP.atts['units'] = 'Pa'
      data['dp'] = dP

    # Add extra fields that will be useful for the diagnostics.
    cls._add_extra_fields(data)

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Convert to a list
    data = list(data.values())

    return data


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return glob(dirname+"/macc_lnsp_*.nc")+glob(dirname+"/macc_ml_*.nc")



# Add this interface to the table.
from . import table
table['macc-nc'] = MACC_Data

