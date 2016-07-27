# Interface for reading / writing GEOS-CHEM data that is converted to netCDF
# from Feng Deng's scripts.


from . import DataProduct
class GEOSCHEM_Data(DataProduct):

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('Center_pressure', 'air_pressure', 'hPa'),
    ('CO2_mixing_ratio', 'CO2', '1E-6 mol mol(semidry_air)-1'),
    ('CO_mixing_ratio', 'CO', '1E-9 mol mol(semidry_air)-1'),
  )



  # A and B interface values (for vertical coordinate)

  A_interface = [
    0.000000E+00, 4.804826E-02, 6.593752E+00, 1.313480E+01,
    1.961311E+01, 2.609201E+01, 3.257081E+01, 3.898201E+01,
    4.533901E+01, 5.169611E+01, 5.805321E+01, 6.436264E+01,
    7.062198E+01, 7.883422E+01, 8.909992E+01, 9.936521E+01,
    1.091817E+02, 1.189586E+02, 1.286959E+02, 1.429100E+02,
    1.562600E+02, 1.696090E+02, 1.816190E+02, 1.930970E+02,
    2.032590E+02, 2.121500E+02, 2.187760E+02, 2.238980E+02,
    2.243630E+02, 2.168650E+02, 2.011920E+02, 1.769300E+02,
    1.503930E+02, 1.278370E+02, 1.086630E+02, 9.236572E+01,
    7.851231E+01, 5.638791E+01, 4.017541E+01, 2.836781E+01,
    1.979160E+01, 9.292942E+00, 4.076571E+00, 1.650790E+00,
    6.167791E-01, 2.113490E-01, 6.600001E-02, 1.000000E-02
  ]

  B_interface = [
    1.000000E+00, 9.849520E-01, 9.634060E-01, 9.418650E-01,
    9.203870E-01, 8.989080E-01, 8.774290E-01, 8.560180E-01,
    8.346609E-01, 8.133039E-01, 7.919469E-01, 7.706375E-01,
    7.493782E-01, 7.211660E-01, 6.858999E-01, 6.506349E-01,
    6.158184E-01, 5.810415E-01, 5.463042E-01, 4.945902E-01,
    4.437402E-01, 3.928911E-01, 3.433811E-01, 2.944031E-01,
    2.467411E-01, 2.003501E-01, 1.562241E-01, 1.136021E-01,
    6.372006E-02, 2.801004E-02, 6.960025E-03, 8.175413E-09,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00
  ]

  # Model levels
  # http://acmg.seas.harvard.edu/geos/doc/man/appendix_3.html#GEOS-5_reduced
  eta = [0.000028, 0.000127, 0.000399, 0.001109,
         0.002816, 0.006588, 0.014342, 0.023755,
         0.033814, 0.047641, 0.066559, 0.084313,
         0.099191, 0.116695, 0.137287, 0.161513,
         0.190061, 0.223772, 0.263587, 0.309854,
         0.353349, 0.390927, 0.428528, 0.466153,
         0.503795, 0.541449, 0.579115, 0.616790,
         0.654471, 0.685878, 0.711006, 0.736134,
         0.761265, 0.786400, 0.809021, 0.826616,
         0.841698, 0.856781, 0.871864, 0.886948,
         0.902031, 0.917116, 0.932200, 0.947285,
         0.962370, 0.977456, 0.992500          ][::-1]


  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    from pygeode.axis import ZAxis
    data = netcdf.open(filename)
    # Layer thickness (pressure)
    # hacked into the opener, since we want it to get collected into the
    # same domain as CO2, and the data_interface module isn't sophisticated
    # enough to re-group domains after the decoding step.
    p = data['Edge_pressure'].replace_axes(edge_level=ZAxis) # Make z-axis (so there aren't multiple NCDim axes going into the works)
    zdim = p.whichaxis('edge_level')
    upper_slice = [slice(None)]*p.naxes
    upper_slice[zdim] = slice(1,None)
    lower_slice = [slice(None)]*p.naxes
    lower_slice[zdim] = slice(0,-1)
    p_upper = p.slice[upper_slice].replace_axes(edge_level=data.layer, keep_old_name=False)
    p_lower = p.slice[lower_slice].replace_axes(edge_level=data.layer, keep_old_name=False)
    dp = p_lower - p_upper
    dp.name = 'dp'
    dp.atts['units'] = 'hPa'
    data = data + dp

    # Similarly, need to hack in surface pressure here.
    p0 = p(i_edge_level=0).squeeze()
    p0.name = 'surface_pressure'
    p0.atts['units'] = 'hPa'
    data = data + p0

    # Geopotential height (if available)
    if 'Edge_gpHeight' in data:
      h = data['Edge_gpHeight'].replace_axes(edge_level=ZAxis) # Make z-axis (so there aren't multiple NCDim axes going into the works)
      zdim = h.whichaxis('edge_level')
      upper_slice = [slice(None)]*h.naxes
      upper_slice[zdim] = slice(1,None)
      lower_slice = [slice(None)]*h.naxes
      lower_slice[zdim] = slice(0,-1)
      h_upper = h.slice[upper_slice].replace_axes(edge_level=data.layer, keep_old_name=False)
      h_lower = h.slice[lower_slice].replace_axes(edge_level=data.layer, keep_old_name=False)
      h = (h_upper+h_lower)/2
      h.name = 'geopotential_height'
      h.atts['units'] = 'm'
      data = data + h

    # Need to define the time axis
    # (not fully defined in the netcdf file).
    from re import search
    date = search("(?P<year>[0-9]{4})(?P<month>[0-9]{2})(?P<day>[0-9]{2})\.nc", filename).groupdict()
    date = dict([x,int(y)] for x,y in date.iteritems())
    from pygeode.timeaxis import StandardTime
    time = StandardTime(startdate=date, units='hours', values=range(24))
    # Need the time axis to have a consistent start date
    time = StandardTime(startdate={'year':2009, 'month':1, 'day':1}, units='hours', **time.auxarrays)
    data = data.replace_axes(time=time)

    return data

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls,dataset):
    import numpy as np
    from pygeode.axis import ZAxis, Hybrid

    # Hard-code the hybrid levels (needed for doing zonal mean plots on native
    # model coordinates).
    A_interface = np.array(cls.A_interface)
    B_interface = np.array(cls.B_interface)
    A = (A_interface[:-1] + A_interface[1:])/2
    B = (B_interface[:-1] + B_interface[1:])/2
    layer = Hybrid(cls.eta, A=A, B=B, name='layer')
    # Need to make the z-axis the right type (since there's no metadata hints
    # in the file to indicate the type)
    dataset = dataset.replace_axes(layer=layer, edge_level=ZAxis)
    if 'layer' in dataset:
      zaxis = dataset.layer
    elif 'edge_level' in dataset:
      zaxis = dataset.edge_level
    else: zaxis = None

    if zaxis is not None:
      zaxis.atts['positive'] = 'up'

    # Apply fieldname conversions
    data = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Add extra fields that will be useful for the diagnostics.
    data = cls._add_extra_fields(data)

    return data


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from glob import glob
    return glob(dirname+"/*.nc")


# Add this interface to the table.
from . import table
table['geoschem-feng-nc'] = GEOSCHEM_Data


