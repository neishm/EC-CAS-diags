###############################################################################
# Copyright 2016 - Climate Research Division
#                  Environment and Climate Change Canada
#
# This file is part of the "EC-CAS diags" package.
#
# "EC-CAS diags" is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "EC-CAS diags" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with "EC-CAS diags".  If not, see <http://www.gnu.org/licenses/>.
###############################################################################


# Interface for reading / writing GEOS-CHEM data that is converted to the
# netCDF COARDS convenction (compatible with GAMAP routine BPCH2COARDS).


from . import DataProduct
class GEOSCHEM_Data(DataProduct):
  """
  GEOS-Chem data (converted to netCDF using the BPCH2COARDS utility).
  """

  # A and B interface values (for vertical coordinate)
  A_interface = dict()
  B_interface = dict()

  A_interface[47] = [
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

  B_interface[47] = [
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

  A_interface[72] = [
    0.000000E+00, 4.804826E-02, 6.593752E+00, 1.313480E+01,
    1.961311E+01, 2.609201E+01, 3.257081E+01, 3.898201E+01,
    4.533901E+01, 5.169611E+01, 5.805321E+01, 6.436264E+01,
    7.062198E+01, 7.883422E+01, 8.909992E+01, 9.936521E+01,
    1.091817E+02, 1.189586E+02, 1.286959E+02, 1.429100E+02,
    1.562600E+02, 1.696090E+02, 1.816190E+02, 1.930970E+02,
    2.032590E+02, 2.121500E+02, 2.187760E+02, 2.238980E+02,
    2.243630E+02, 2.168650E+02, 2.011920E+02, 1.769300E+02,
    1.503930E+02, 1.278370E+02, 1.086630E+02, 9.236572E+01,
    7.851231E+01, 6.660341E+01, 5.638791E+01, 4.764391E+01,
    4.017541E+01, 3.381001E+01, 2.836781E+01, 2.373041E+01,
    1.979160E+01, 1.645710E+01, 1.364340E+01, 1.127690E+01,
    9.292942E+00, 7.619842E+00, 6.216801E+00, 5.046801E+00,
    4.076571E+00, 3.276431E+00, 2.620211E+00, 2.084970E+00,
    1.650790E+00, 1.300510E+00, 1.019440E+00, 7.951341E-01,
    6.167791E-01, 4.758061E-01, 3.650411E-01, 2.785261E-01,
    2.113490E-01, 1.594950E-01, 1.197030E-01, 8.934502E-02,
    6.600001E-02, 4.758501E-02, 3.270000E-02, 2.000000E-02,
    1.000000E-02
  ]

  B_interface[72] = [
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
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00, 0.000000E+00, 0.000000E+00, 0.000000E+00,
    0.000000E+00
  ]

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import netcdf
    from pygeode.dataset import Dataset
    dataset = netcdf.open(filename)
    # Hack for the grid cell areas - remove time axis.
    dataset = list(dataset)
    for i, var in enumerate(dataset):
      if var.name.startswith('DXYP'):
        var = var.squeeze('time')
        dataset[i] = var

    # Make sure the longitudes are monotonic!
    dataset = [d.sorted('lon') for d in dataset]
    return Dataset(dataset)

  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, dataset):
    import numpy as np
    from pygeode.axis import Hybrid
    from pygeode.var import Var
    from pygeode.dataset import asdataset

    # Use some 'standardized' names, and locate a z-axis.
    zaxis = None
    dataset = list(dataset)
    for i, var in enumerate(dataset):
      if var.name.endswith('_CO2'):
        var.name = 'CO2'
        if var.atts['units'] == "v/v":  # From restart file?
          var.atts['units'] = "mol mol(dry_air)-1"
        else:  # From experiment output?
          var.atts['units'] = '1E-9 mol mol(dry_air)-1'
      if var.name.endswith('_CO'):
        var.name = 'CO'
        if var.atts['units'] == "v/v":  # From restart file?
          var.atts['units'] = "mol mol(dry_air)-1"
        else:  # From experiment output?
          var.atts['units'] = '1E-9 mol mol(dry_air)-1'
      if var.name == 'CO__SRCE__COanth':
        var.name = 'CO_anthropogenic_flux'
        var.atts['specie'] = 'CO'
        var.atts['units'] = 'molecules cm-2 s-1'
      if var.name == 'PORL_L_S__PCH4':
        var.name = 'CO_production'
        var.atts['units'] = 'molecules cm-3 s-1'
      # Treat ppbv units as ppb
      if var.atts.get('units',None) == 'ppbv':
        var.atts['units'] = 'ppb'
      if var.name == 'PSURF' or var.name.endswith('_PSURF') or var.name.endswith('_PS') or var.name.startswith('PEDGE_S'):
        # Special case: actually have 3D pressure (erroneously encoded?)
        if var.hasaxis('lev'):
          # Exception: data is not filled in
          # (e.g. GEOS-Chem_CO_CH4_source_2010.nc)
          if var[0,-1,0,0] == 0: continue
          # Note: this seems to be on interfaces (last level is the surface).
          # only keep last level, since we can generate pressure on mid-levels
          # from the formula.
          var = var.slice[:,0,:,:].squeeze('lev')
          var.name = 'surface_pressure'
          var.atts['units'] = 'hPa'
        if var.name.startswith('GMAO_'):
           var.atts['units'] = 'hPa'
        var.name = 'surface_pressure'
      if var.name.endswith('_QV'):
        var.name = 'specific_humidity'
        var.atts['units'] = 'kg(H2O) kg(air)-1'
      if var.name.endswith('_SPHU'):
        var.name = 'specific_humidity'
        var.atts['units'] = 'g(H2O) kg(air)-1'
      if var.name.startswith('DXYP'):
        var.name = 'cell_area'
      # Special case: vertical levels that we know the parameters for
      if var.hasaxis('lev'):
        zaxis = var.getaxis('lev')
      dataset[i] = var

    # Generate the expected vertical axis
    if zaxis is not None:
      nlev = len(zaxis)
      A_interface = np.array(cls.A_interface[nlev])
      B_interface = np.array(cls.B_interface[nlev])
      A = (A_interface[:-1] + A_interface[1:]) * 0.5
      B = (B_interface[:-1] + B_interface[1:]) * 0.5
      dA = (A_interface[:-1] - A_interface[1:])
      dB = (B_interface[:-1] - B_interface[1:])

      zaxis = Hybrid(zaxis.values, A=A, B=B)
      for i, var in enumerate(dataset):
        if var.hasaxis('lev'):
          dataset[i] = var.replace_axes(lev=zaxis)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Compute a pressure field.
    # Also, compute a dp field (vertical change in pressure within a gridbox).
    if 'surface_pressure' in data and zaxis is not None:
      Ps = data['surface_pressure']
      A = zaxis.auxasvar('A')
      B = zaxis.auxasvar('B')
      P = A + B*Ps
      P = P.transpose('time','zaxis','lat','lon')
      P.atts['units'] = 'mbar'
      data['air_pressure'] = P

      dA = Var([zaxis], values=dA)
      dB = Var([zaxis], values=dB)
      dP = dA + dB*Ps
      dP = dP.transpose('time','zaxis','lat','lon')
      dP.atts['units'] = 'mbar'
      data['dp'] = dP

    # Grid cell areas
    # Pick some arbitrary (but deterministic) variable to get the lat/lon
#    if 'cell_area' not in data:
#      var = sorted(data.values())[0]
#      from ..common import get_area
#      data['cell_area'] = get_area(var.lat,var.lon)

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
    files = []
    for filename in "GC_restart.20100101_G5_4x5_COv10_47L.nc", "GEOS-Chem_CO_combust_VOC_emiss_2010.nc", "GEOS-Chem_CO_CH4_source_2010.nc", "GEOS-Chem_CO_loss_freq_2010.nc", "ts*.nc":
      files.extend(glob(dirname+"/"+filename))
    return files

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    import os
    dirs = dirname.split(os.sep)
    if dirs[-1] == 'timeseries':
      dirs = dirs[:-1]
    return dirs[-1]


# Add this interface to the table.
from . import table
table['geoschem-coards'] = GEOSCHEM_Data

