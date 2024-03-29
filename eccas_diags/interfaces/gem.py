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


# Fix a bug in reduce_dimensionality.
from pygeode_rpn import fstd
from pygeode_rpn.fstd import FSTD_Var
from pygeode.axis import Pres
# Reduce the dimensionality of the given FSTD variable
def reduce_dimensionality (var, squash_forecasts=False):
  # Skip derived fields
  if not isinstance(var, FSTD_Var): return var

  remove_axes = []
  # Forecast (axis 1)
  if var.shape[1] == 1:
    if squash_forecasts:
      remove_axes += [1]
  # Vertical (axis 2)
  # Surface fields have a 'pressure' coordinate with a value of 0hPa
  if var.shape[2] == 1:
    if isinstance(var.axes[2], Pres) and var.axes[2].values == [0.]:
      remove_axes += [2]
  # K axis (axis 3)
  if var.shape[var.naxes-3] == 1:
    remove_axes += [var.naxes-3]

  if len(remove_axes) == 0: return var   # <============== added fix here
  return var.squeeze(*remove_axes)
fstd.reduce_dimensionality = reduce_dimensionality


from . import DataProduct
class GEM_Data(DataProduct):
  """
  GEM model output (in RPN format).
  """

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('GZ', 'geopotential_height', 'dam'),
    ('P0', 'surface_pressure', 'hPa'),
    ('PN', 'MSL_pressure', 'hPa'),
    ('TT', 'air_temperature', 'C'),
    ('UU', 'zonal_wind', 'knots'),
    ('VV', 'meridional_wind', 'knots'),
    ('WW', 'vertical_motion', 'Pa s-1'),
    ('HU', 'specific_humidity', 'kg(H2O) kg(air)-1'),
    ('DX', 'cell_area', 'm2'),
    ('H', 'PBL_height', 'm'),
    ('MASK', 'subgrid_weight', ''), # Note: local definition, not part of GEM.
  )

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode_rpn import fstd
    f = fstd.open(filename, raw_list=True, subgrid_axis=True)
    # Filter out degenerate subgrid axis, which seems to be applied to
    # lat/lon fields when reading data that's not on yin-yang grid.
    f = [v.squeeze('subgrid') if v.hasaxis('subgrid') else v for v in f]
    return f


  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, dataset):
    from pygeode_rpn import fstd
    from pygeode.ufunc import exp, log
    from pygeode.var import concat, Var
    from pygeode.axis import ZAxis
    from ..common import compute_pressure, compute_dp

    # Apply fieldname conversions
    dataset = DataProduct.decode.__func__(cls,dataset)

    # Remove top thermodynamic level from GEM 4.6 output (diagnostic level).
    zaxis = None
    for var in dataset:
      if var.hasaxis(fstd.LogHybrid):
        zaxis = var.getaxis(fstd.LogHybrid)
    if zaxis is not None and zaxis.atts['kind'] == 5 and zaxis.atts['version'] == 2:
      # Check if we have the problematic level in our data.
      if zaxis.A[0] == zaxis.atts['a_t'][0]:
        dataset = [var(i_zaxis=(1,len(zaxis))) if var.hasaxis(fstd.LogHybrid) else var for var in dataset]

    for var in list(dataset):
      varname = var.name

      # Add a water tracer, if we have humidity
      if varname == 'specific_humidity':
        dataset.append(var.rename('H2O'))
        dry_air = (1-var)
        dry_air.name = 'dry_air'
        dry_air.atts.update(units='kg(dry_air) kg(air)-1')
        dataset.append(dry_air)

      # Compute a pressure field.
      # Also, compute a dp field (vertical change in pressure within a gridbox).
      if varname == 'surface_pressure':
        # Skip ensemble calculations (like spread).
        if 'ensemble_op' in var.atts: continue
        Ps = var
        for v in list(dataset):
          if v.hasaxis('zaxis'):
            zaxis = v.getaxis('zaxis')
            # We might not be able to do this, e.g. for Hybrid axes or GZ levels
            try:
              air_pressure = compute_pressure(zaxis, Ps)
              air_pressure.name = 'air_pressure'
              dataset.append(air_pressure)
              dp = compute_dp(zaxis, Ps)
              dp.name = 'dp'
              dataset.append(dp)
            except (TypeError, ValueError): pass
            break

    # Grid cell areas
    if not any(var.name == 'cell_area' for var in dataset):
      # Pick some arbitrary variable to get the lat/lon
      latlon = [var for var in dataset if var.hasaxis('lat') and var.hasaxis('lon')]
      from ..common import get_area
      # Make sure this is gridded GEM data (not profile / timeseries data).
      if len(latlon) > 0:
        var = latlon[0]
        if var.hasaxis('forecast'):
          cell_area = get_area(var.lat,var.lon,flat=True).extend(0,var.time, var.forecast)
        else:
          cell_area = get_area(var.lat,var.lon,flat=True).extend(0,var.time)
        cell_area.name = 'cell_area'
        dataset.append(cell_area)

    # Blended grid cell area (contrubution from each subgrid).
    if not any(var.name == 'blended_area' for var in dataset):
      from ..common import get_blended_area
      try:
        blended_area = get_blended_area (dataset)
        dataset.append(blended_area)
      except (TypeError, ValueError): pass

    # Special case - already on pressure levels?
    # Can append a degenerate pressure field for the diagnostics.
    for var in list(dataset):
      if var.hasaxis('pres'):
        p = var.pres
        paxis = var.whichaxis('pres')
        p = p.extend(0,var.axes[:paxis])
        p = p.extend(paxis+1, var.axes[paxis+1:])
        p.atts['units'] = var.pres.units
        p.name = 'air_pressure'
        dataset.append(p)
        break

    # Add extra fields that will be useful for the diagnostics.
    dataset = cls._add_extra_fields(dataset)

    # Remove the forecast axis before returning the data
    # (not needed for any current diagnostics).
    from ..common import squash_forecasts
    dataset = map(squash_forecasts,dataset)

    return dataset


  # Method to find all files in the given directory, which can be accessed
  # through this interface.
  @staticmethod
  def find_files (dirname):
    from os.path import exists
    from glob import glob

    files = []

    ##############################
    # Model output
    ##############################

    if exists (dirname+'/model'):
      model_dir = dirname+'/model'
    else:
      model_dir = dirname

    files.extend(glob(model_dir+"/[0-9]*_[0-9]*"))
    files.extend(glob(model_dir+"/km[0-9]*_[0-9]*"))
    files.extend(glob(model_dir+"/dm[0-9]*_[0-9]*"))
    files.extend(glob(model_dir+"/pm[0-9]*_[0-9]*"))
    files.extend(glob(model_dir+"/k[0-9]*_[0-9]*"))
    files.extend(glob(model_dir+"/d[0-9]*_[0-9]*"))
    files.extend(glob(model_dir+"/p[0-9]*_[0-9]*"))
    files.extend(glob(model_dir+"/2[0-9]*.fst"))
    # Omit 0h forecasts if non-zero forecasts available.
    files_nonzero = [f for f in files if not f.endswith('_000') and not f.endswith('_000h')]
    if len(files_nonzero) > 0:
      files = files_nonzero
    # Omit netcdf files
    files = [f for f in files if not f.endswith('.nc')]


    return files



  # Method to re-encode data into the source context
  # (e.g., rename fields to what would be originally in these kinds of files)
  @classmethod
  def encode (cls, dataset):
    from ..common import convert
    from warnings import warn
    import logging
    from pygeode.timeaxis import Time, StandardTime
    logger = logging.getLogger(__name__)

    # Apply the conversions
    dataset = DataProduct.encode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Remove generated fields
    data.pop('air_pressure',None)
    data.pop('dp',None)

    # Make sure the variables are 32-bit precision.
    # (Otherwise, GEM may have problems reading them).
    for varname in data.keys():
      if data[varname].dtype != 'float32':
        data[varname] = data[varname].as_type('float32')

    # Convert climatological time axes to standard calendar.
    for varname in data.keys():
      var = data[varname]
      if var.hasaxis(Time):
        taxis = var.getaxis(Time)
        auxarrays = dict(**taxis.auxarrays)
        if not isinstance(taxis,StandardTime):
          logger.debug("Converting %s to standard calendar"%varname)
          taxis = StandardTime(units=taxis.units, **auxarrays)
          var = var.replace_axes(time=taxis)
        if 'year' not in auxarrays:
          logger.debug("Assigning arbitrary year to %s"%varname)
          auxarrays['year'] = [1980]*len(taxis)
          taxis = StandardTime(units=taxis.units, **auxarrays)
          var = var.replace_axes(time=taxis)
        data[varname] = var

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Convert to a list
    data = list(data.values())

    return data

  # Method to find a unique identifying string for this dataset, from the
  # given directory name.
  @staticmethod
  def get_dataname (dirname):
    import os
    dirs = dirname.split(os.sep)
    if dirs[-1] in ('model','pressure','timeseries'):
      dirs = dirs[:-1]
    return dirs[-1]


  # Method to write data to file(s).
  @classmethod
  def write (cls, datasets, dirname):
    from pygeode.dataset import asdataset
    from pygeode_rpn import fstd, fstd_core
    import numpy as np
    from datetime import datetime, timedelta
    from ..common import rotate_grid, add_repeated_longitude, increasing_latitudes

    cmc_start = datetime(year=1980, month=1, day=1)

    # Encode the data to the appropriate units / fieldnames
    datasets = [cls.encode(dataset) for dataset in datasets]

    # Rotate all longitudes to be in range (0,360)
    datasets = [[rotate_grid(d) for d in dataset] for dataset in datasets]

    # Make sure the latitudes are in increasing order
    datasets = [[increasing_latitudes(d) for d in dataset] for dataset in datasets]

    # Add a repeated longitude, for global data
    for i,dataset in enumerate(datasets):
      dataset = list(dataset)
      for j,var in enumerate(dataset):
        if not var.hasaxis('lon'): continue
        lon = var.lon.values
        if lon[-1] + 2*(lon[-1]-lon[-2]) > 360.:
          if lon[0] - 2*(lon[1]-lon[0]) < 0.:
            dataset[j] = add_repeated_longitude(var)
      datasets[i] = dataset

    # Collect everything in a set of FSTD records
    records = []
    for dataset in datasets:
      records.append(fstd.prepare_records(dataset))
    records = np.concatenate(records)

    # Eliminate duplicate records
    #(TODO)

    # Organize into different files (don't write yet)
    output = dict()
    coord_output = []
    for i,r in enumerate(records):
      if r['nomvar'] in ('!!  ','>>  ','^^  ', 'HY  '):
        coord_output.append(i)
        continue
      dateo = int(fstd_core.stamp2date(r['dateo'])[0])
      date = cmc_start + timedelta(seconds=dateo)
      forecast = r['npas'] * r['deet'] / 3600
      filename = dirname + "/" + cls._fstd_date2filename(date,forecast)
      output.setdefault(filename,[]).append(i)
    for filename in output:
      output[filename] = records[coord_output + output[filename]]
      cls._fstd_tweak_records(output[filename])

    # Write out the file(s)
    for filename in sorted(output.keys()):
      print '=>', filename
      fstd_core.write_records(filename, output[filename])


  # This little stub is needed by all GEM-related interfaces to indicate how
  # to convert dates to filenames.
  # Input: datetime object and forecast hour
  # Output: filename
  @staticmethod
  def _fstd_date2filename (date, forecast):
    return "%04d%02d%02d%02d_%03d"%(date.year,date.month,date.day,date.hour,forecast)

  # Any extra FSTD record tweaking would go into here.
  # Input/Output: array of FSTD records
  @staticmethod
  def _fstd_tweak_records (records):
    return  # Nothing done by default.



# Add this interface to the table.
from . import table
table['gem'] = GEM_Data

