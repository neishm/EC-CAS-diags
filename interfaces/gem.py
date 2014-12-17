
from interfaces import ModelData
class GEM_Data(ModelData):

  # Define all the possible variables we might have in this dataset.
  # (original_name, standard_name, units)
  field_list = (
    ('GZ', 'geopotential_height', 'dam'),
    ('P0', 'surface_pressure', 'hPa'),
    ('TT', 'air_temperature', 'K'),
    ('HU', 'specific_humidity', 'kg(H2O) kg(air)-1'),
    ('DX', 'cell_area', 'm2'),
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

    # Apply fieldname conversions
    dataset = ModelData.decode.__func__(cls,dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Add a water tracer, if we have humidity
    if 'specific_humidity' in data:
      data['H2O'] = data['specific_humidity'].rename('H2O')

    # Compute a pressure field.
    # Also, compute a dp field (vertical change in pressure within a gridbox).
    if 'surface_pressure' in data:
      Ps = data['surface_pressure']
      for var in data.itervalues():
        if var.hasaxis('zaxis'):
          zaxis = var.getaxis('zaxis')
          # We might not be able to do this, e.g. for Hybrid axes or GZ levels
          try:
            data['air_pressure'] = cls.compute_pressure(zaxis, Ps)
            data['dp'] = cls.compute_dp(zaxis, Ps)
          except (TypeError, ValueError): pass
          break

    # Grid cell areas
    if 'cell_area' not in data:
      # Pick some arbitrary (but deterministic) variable to get the lat/lon
      var = sorted(data.values())[0]
      from common import get_area
      data['cell_area'] = get_area(var.lat,var.lon,flat=True).extend(0,var.time, var.forecast)

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Convert to a list
    data = list(data.values())

    # Remove the forecast axis before returning the data
    # (not needed for any current diagnostics).
    from common import squash_forecasts
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


  # Wrapper for getting GEM data back out of a cached netcdf file
  # (This will hook into the cache, to preserve FSTD axes after save/reloading)
  @staticmethod
  def load_hook (dataset):
    from pygeode.formats.fstd import detect_fstd_axes
    data = list(dataset.vars)
    detect_fstd_axes(data)
    return data


  # Method to re-encode data into the source context
  # (e.g., rename fields to what would be originally in these kinds of files)
  @classmethod
  def encode (cls, dataset):
    from common import convert
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
    data = ModelData.encode.__func__(cls,data)

    return data


  # Method to write data to file(s).
  @classmethod
  def write (cls, datasets, dirname):
    from pygeode.dataset import asdataset
    from pygeode.formats import fstd, fstd_core
    import numpy as np
    from datetime import datetime, timedelta
    from common import rotate_grid, add_repeated_longitude, increasing_latitudes

    cmc_start = datetime(year=1980, month=1, day=1)

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


  # Helper method to compute the change in pressure within a vertical layer.
  @staticmethod
  def compute_dp (zaxis, p0):
    from pygeode.formats import fstd
    from pygeode.var import Var
    from pygeode.ufunc import exp, log
    import math
    import numpy as np
    from common import convert

    p0 = convert(p0, 'Pa')

    # eta coordinates?
    if isinstance(zaxis,fstd.Hybrid):
      raise TypeError("Not enough information to compute pressure interfaces on GEM eta levels.")
#      # dP
#      #TODO: Use ptop as upper boundary, instead of ignoring (zeroing) that layer?
#      # Need to overwrite the eta axis with a generic one before concatenating,
#      # because eta axes require explict A/B arrays (which concat doesn't see)
#      from pygeode.axis import ZAxis
#      PP = P.replace_axes(eta=ZAxis(P.eta.values))
#      P_k = concat(PP.slice[:,:,0,:,:].replace_axes(zaxis=ZAxis([-1.])), PP.slice[:,:,:-1,:,:]).replace_axes(zaxis=PP.zaxis)
#      P_kp1 = concat(PP.slice[:,:,1:,:,:], PP.slice[:,:,-1,:,:].replace_axes(zaxis=ZAxis([2.]))).replace_axes(zaxis=PP.zaxis)
#      dP = abs(P_kp1 - P_k)/2
#      # Put the eta axis back
#      dP = dP.replace_axes(zaxis=P.eta)

    # zeta coordinates?
    elif isinstance(zaxis,fstd.LogHybrid):
      zeta = zaxis
      # Get the full set of coefficients
      a_m = zeta.atts['a_m']
      b_m = zeta.atts['b_m']
      a_t = zeta.atts['a_t']
      b_t = zeta.atts['b_t']
      # Add extra level at the lid
      a_m = np.array([math.log(zeta.atts['ptop'])] + list(a_m))
      b_m = np.array([0] + list(b_m))

      # Figure out if we have thermodynamic or momentum levels, and use the
      # other set of levels as the interfaces
      if set(zeta.A) <= set(a_m) and set(zeta.B) <= set(b_m):
        a_int = a_t
        b_int = b_t
      elif set(zeta.A) <= set(a_t) and set(zeta.B) <= set(b_t):
        a_int = a_m
        b_int = b_m
      else:
        raise ValueError ("Vertical axis must be entirely on model thermodynamic or momentum levels.")

      # Find indices of interfaces
      interface_ind = []
      for a in zeta.A:
        j = np.searchsorted(a_int, a) - 1
        if a_int[j+1] == a: j+= 1  # Check for lower boundary?
        interface_ind.append(j)
      # Add the bottom interface
      interface_ind.append(np.searchsorted(a_int, a))
      # Double-check we have the right things
      for a, j in zip(zeta.A, interface_ind[:-1]):
        assert a_int[j] <= a
      for a, j in zip(zeta.A, interface_ind[1:]):
        assert a_int[j] >= a

      # Define a dp operator
      a_upper = Var([zeta], values=a_int[interface_ind[:-1]])
      a_lower = Var([zeta], values=a_int[interface_ind[1:]])
      b_upper = Var([zeta], values=b_int[interface_ind[:-1]])
      b_lower = Var([zeta], values=b_int[interface_ind[1:]])
      p_upper = exp(a_upper + b_upper*log(p0/zeta.atts['pref']))
      p_lower = exp(a_lower + b_lower*log(p0/zeta.atts['pref']))
      dp = p_lower - p_upper

    else:
      raise TypeError("Can't handle '%s' axis in this GEM interface."%zaxis.__class__.__name__)

    if dp.hasaxis('forecast'):
      dp = dp.transpose('time','forecast','zaxis','lat','lon')
    else:
      dp = dp.transpose('time','zaxis','lat','lon')

    dp.name = 'dp'
    dp.atts['units'] = 'Pa'
    return dp

  # Helper method to compute pressure levels from the given z-axis and surface pressure
  @staticmethod
  def compute_pressure (zaxis, p0):
    from pygeode.formats import fstd
    from pygeode.ufunc import exp, log
    from common import convert

    p0 = convert(p0, 'Pa')

    # eta coordinates?
    if isinstance(zaxis, fstd.Hybrid):
      eta = zaxis
      A = eta.auxasvar('A')
      B = eta.auxasvar('B')
      p = A + B * p0

    # zeta coordinates?
    elif isinstance(zaxis, fstd.LogHybrid):
      zeta = zaxis
      A = zeta.auxasvar('A')
      B = zeta.auxasvar('B')
      pref = zeta.atts['pref']
      ptop = zeta.atts['ptop']
      p = exp(A + B * log(p0/zeta.atts['pref']))

    else:
      raise TypeError("Can't handle '%s' axis in this GEM interface."%zaxis.__class__.__name__)

    if p.hasaxis('forecast'):
      p = p.transpose('time','forecast','zaxis','lat','lon')
    else:
      p = p.transpose('time','zaxis','lat','lon')
    p.name = 'air_pressure'
    p.atts['units'] = 'Pa'
    return p






# Give this class a standard reference name, to make it easier to auto-discover.
interface = GEM_Data

