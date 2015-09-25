
from . import DataProduct
class GEM_Data(DataProduct):

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('GZ', 'geopotential_height', 'dam'),
    ('P0', 'surface_pressure', 'hPa'),
    ('TT', 'air_temperature', 'K'),
    ('UU', 'zonal_wind', 'knots'),
    ('VV', 'meridional_wind', 'knots'),
    ('HU', 'specific_humidity', 'kg(H2O) kg(air)-1'),
    ('DX', 'cell_area', 'm2'),
    ('H', 'PBL_height', 'm'),
  )

  # Method to open a single file
  @staticmethod
  def open_file (filename):
    from pygeode.formats import fstd
    return fstd.open(filename, raw_list=True)


  # Method to decode an opened dataset (standardize variable names, and add any
  # extra info needed (pressure values, cell area, etc.)
  @classmethod
  def decode (cls, dataset):
    from pygeode.formats import fstd
    from pygeode.ufunc import exp, log
    from pygeode.var import concat, Var
    from pygeode.axis import ZAxis
    from ..common import compute_pressure, compute_dp

    # Apply fieldname conversions
    dataset = DataProduct.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Add a water tracer, if we have humidity
    if 'specific_humidity' in data:
      data['H2O'] = data['specific_humidity'].rename('H2O')
      data['dry_air'] = 1-data['specific_humidity']
      data['dry_air'].atts.update(units='kg kg(air)-1')

    # Compute a pressure field.
    # Also, compute a dp field (vertical change in pressure within a gridbox).
    if 'surface_pressure' in data:
      Ps = data['surface_pressure']
      for var in data.itervalues():
        if var.hasaxis('zaxis'):
          zaxis = var.getaxis('zaxis')
          # We might not be able to do this, e.g. for Hybrid axes or GZ levels
          try:
            data['air_pressure'] = compute_pressure(zaxis, Ps)
            data['dp'] = compute_dp(zaxis, Ps)
          except (TypeError, ValueError): pass
          break

    # Grid cell areas
    if 'cell_area' not in data:
      # Pick some arbitrary (but deterministic) variable to get the lat/lon
      var = sorted(data.values())[0]
      from ..common import get_area
      # Make sure this is gridded GEM data (not profile / timeseries data).
      if var.hasaxis('lat') and var.hasaxis('lon'):
        data['cell_area'] = get_area(var.lat,var.lon,flat=True).extend(0,var.time, var.forecast)

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Convert to a list
    data = list(data.values())

    # Remove the forecast axis before returning the data
    # (not needed for any current diagnostics).
    from ..common import squash_forecasts
    data = map(squash_forecasts,data)

    return data


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
    # Omit 0h forecasts
    files = [f for f in files if not f.endswith('_000') and not f.endswith('_000h')]


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
        if not isinstance(taxis,StandardTime):
          logger.debug("Converting %s to standard calendar"%varname)
          auxarrays = dict(**taxis.auxarrays)
          if 'year' not in auxarrays:
            logger.debug("Assigning arbitrary year to %s"%varname)
            auxarrays['year'] = [1980]*len(taxis)
          new_taxis = StandardTime(units=taxis.units, **auxarrays)
          data[varname] = var.replace_axes(time=new_taxis)

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Convert to a list
    data = list(data.values())

    # Apply the conversions
    data = DataProduct.encode.__func__(cls,data)

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
    from pygeode.formats import fstd, fstd_core
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

