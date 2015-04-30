# Interface for CarbonTracker data

from . import DataProduct
class CT_Data(DataProduct):

  # Invariant data
  import numpy as np
  A_interface = [0., 6.575628, 336.772369, 1297.656128, 3010.146973, 5422.802734, 8356.252930000001, 11543.166992, 14665.645508, 17385.595703, 19348.775391, 20319.011719, 20348.916016, 19919.796875, 19184.544922, 18191.029297, 16990.623047, 15638.053711, 14192.009766, 12713.897461, 11262.484375, 9873.560546999999, 8564.624023, 7341.469727, 6199.839355, 4663.776367, 3358.425781, 2292.155518, 1463.16394, 857.945801, 450.685791, 204.637451, 76.16765599999999, 21.413612, 0.]
  A_interface = np.array(A_interface)

  B_interface = [1., 0.994204, 0.9734660000000001, 0.935157, 0.875518, 0.795385, 0.698224, 0.589317, 0.475016, 0.362203, 0.259554, 0.176091, 0.112979, 0.080777, 0.055474, 0.036227, 0.022189, 0.012508, 0.006322, 0.002765, 0.001, 0.000279, 5.5e-05, 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
  B_interface = np.array(B_interface)

  del np

  # List of all possible fields we expect from the data
  # (original_name, standard_name, units)
  field_list = (
    ('bg', 'CO2_background', 'ppm'),
    ('ff', 'CO2_fossil', 'ppm'),
    ('bio', 'CO2_bio', 'ppm'),
    ('ocean', 'CO2_ocean', 'ppm'),
    ('fires', 'CO2_fire', 'ppm'),
    ('fossil_imp', 'CO2_fossil_flux', 'mol m-2 s-1'),
    ('bio_flux_opt', 'CO2_bio_flux', 'mol m-2 s-1'),
    ('ocn_flux_opt', 'CO2_ocean_flux', 'mol m-2 s-1'),
    ('fire_flux_imp', 'CO2_fire_flux', 'mol m-2 s-1'),
    ('press', 'air_pressure', 'Pa'),
    ('gph', 'geopotential_height', 'm'),
  )
  # Helper methods

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats.netcdf import open
    import warnings
    # Ignore warnings about the vertical axis.
    # PyGeode complains because it sees a hybrid axis, but doesn't find
    # A and B coefficients to properly define it.
    with warnings.catch_warnings():
      warnings.filterwarnings("ignore", "Cannot create a proper Hybrid vertical axis")
      return open(filename)

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, data):
    from pygeode.axis import ZAxis
    from pygeode.timeaxis import StandardTime

    # Adjust the time axis for flux data.
    # The time is the mid-point of a 3-hour integration?
    # We will interpret this as being valid at the start of the integration,
    # although it's not clear what exactly CarbonTracker is providing...
    if 'bio_flux_opt' in data:
      taxis = data.date
      assert taxis.units == 'days'
      taxis = taxis.withnewvalues(taxis.values-(1./16))
      data = data.replace_axes(date=taxis)

    # Rename the 'date' axis to 'time', since that's what every other dataset
    # is using.
    data = data.rename_axes(date='time')

    # Don't worry about the date_components and decimal_date domain?
    # (Doesn't have any CO2-related variables).
    varnames = [v.name for v in data]
    if 'bio' not in varnames and 'bio_flux_opt' not in varnames: return data

    # Force vertical axis to be a ZAxis
    data = data.replace_axes(level = ZAxis)
    # Indicate the direction of the vertical axis
    if 'level' in data:
      data.level.atts['positive'] = 'up'

    # Apply fieldname conversions
    data = DataProduct.decode.__func__(cls,data)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in data)

    # Find the total CO2 (sum of components)
    if 'CO2_background' in data:
      data['CO2'] = data['CO2_background'] + data['CO2_fossil'] + data['CO2_bio'] + data['CO2_ocean'] + data['CO2_fire']
      data['CO2'].atts['units'] = data['CO2_background'].atts['units']

    # Create a total flux product
    if 'CO2_fire_flux' in data:
      data['CO2_flux'] = data['CO2_fossil_flux'] + data['CO2_bio_flux'] + data['CO2_ocean_flux'] + data['CO2_fire_flux']
      data['CO2_flux'].atts['units'] = data['CO2_fire_flux'].atts['units']

    # Add species name for all products (to assist in things like unit conversion)
    for varname in data:
      if varname.startswith('CO2'):
        data[varname].atts['specie'] = 'CO2'


    # Other (more heavily derived) products

    if 'air_pressure' in data:
      # Surface pressure
      # Get pressure at the bottom mid-level
      pmid = data['air_pressure'].squeeze(level=1)

      # Compute surface pressure from this
      # p1 = A1 + B1*Ps
      # pmid = (ps + A1 + B1*Ps) / 2 = Ps(1+B1)/2 + (0+A1)/2
      # Ps = (2*pmid - A1)/(1+B1)
      P0 = (2*pmid - cls.A_interface[1])/(cls.B_interface[1]+1)
      P0.atts['units'] = 'Pa'
      data['surface_pressure'] = P0

      # Vertical change in pressure
      #NOTE: generated from A/B interface values, not the 3D pressure field.
      #      3D pressure is used only to define the vertical levels.
      import numpy as np
      from pygeode.var import Var
      dA = -np.diff(cls.A_interface)
      dA = Var([data['air_pressure'].level], values=dA)
      dB = -np.diff(cls.B_interface)
      dB = Var([data['air_pressure'].level], values=dB)
      dp = dA + dB * data['surface_pressure']
      dp = dp.transpose('time','zaxis','lat','lon')
      dp.atts['units'] = 'Pa'
      data['dp'] = dp


    # Compute grid cell area
    # NOTE: will be different for fluxes and 3D mole fractions
    from ..common import get_area
    if 'CO2' in data:
      x = data['CO2'].squeeze(level=1)
    else:
      x = data['CO2_flux']
    data['cell_area'] = get_area(x.lat, x.lon).extend(0,x.time)


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
    molefractions = glob(dirname+"/CT????.molefrac_glb3x2_????-??-??.nc")
    fluxes = glob(dirname+"/CT????.flux1x1.????????.nc")

    # Blacklist the 2009-08-07 molefractions file, which has bad data at 10:30
    # (For CT2010 dataset)
    molefractions = [m for m in molefractions if "2009-08-07" not in m]

    return molefractions+fluxes

# Add this interface to the table.
from . import table
table['carbontracker'] = CT_Data



