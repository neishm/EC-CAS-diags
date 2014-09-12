
class GEM_Data(object):

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
  def decode (self, dataset):
    from pygeode.formats import fstd
    from pygeode.ufunc import exp, log
    from pygeode.var import concat, Var
    from pygeode.axis import ZAxis
    from pygeode.dataset import asdataset

    dataset = asdataset(dataset)

    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Do the conversions
    for old_name, new_name, units in self.field_list:
      if old_name in data:
        var = data.pop(old_name)
        var.atts['units'] = units
        data[new_name] = var

    # Add a water tracer, if we have humidity
    if 'specific_humidity' in data:
      data['H2O'] = data['specific_humidity']

    # Compute a pressure field.
    # Also, compute a dp field (vertical change in pressure within a gridbox).
    P = None
    dP = None

    if 'surface_pressure' in data:

      Ps = data['surface_pressure']

      # eta coordinates?
      eta_vars = [var for var in data.itervalues() if var.hasaxis(fstd.Hybrid)]
      if len(eta_vars) > 0:
        eta = eta_vars[0].getaxis(fstd.Hybrid)
        A = eta.auxasvar('A')
        B = eta.auxasvar('B')
        P = A + B * Ps * 100
        P = P.transpose('time','forecast','eta','lat','lon')
        P /= 100 # hPa

        # dP
        #TODO: Use ptop as upper boundary, instead of ignoring (zeroing) that layer?
        # Need to overwrite the eta axis with a generic one before concatenating,
        # because eta axes require explict A/B arrays (which concat doesn't see)
        from pygeode.axis import ZAxis
        PP = P.replace_axes(eta=ZAxis(P.eta.values))
        P_k = concat(PP.slice[:,:,0,:,:].replace_axes(zaxis=ZAxis([-1.])), PP.slice[:,:,:-1,:,:]).replace_axes(zaxis=PP.zaxis)
        P_kp1 = concat(PP.slice[:,:,1:,:,:], PP.slice[:,:,-1,:,:].replace_axes(zaxis=ZAxis([2.]))).replace_axes(zaxis=PP.zaxis)
        dP = abs(P_kp1 - P_k)/2
        # Put the eta axis back
        dP = dP.replace_axes(zaxis=P.eta)

      # zeta coordinates?
      zeta_vars = [var for var in data.itervalues() if var.hasaxis(fstd.LogHybrid)]
      if len(zeta_vars) > 0:
        zeta = zeta_vars[0].getaxis(fstd.LogHybrid)
        A = zeta.auxasvar('A')
        B = zeta.auxasvar('B')
        pref = zeta.atts['pref']
        ptop = zeta.atts['ptop']

        P = exp(A + B * log(Ps*100/pref))
        P = P.transpose('time','forecast','zeta','lat','lon')
        P /= 100 # hPa

        # dP
        #TODO: produce dP for both thermodynamic and momentum levels
        # (currently just thermo)
        if set(zeta.auxarrays['A']) <= set(zeta.atts['a_t']):
          A_m = list(zeta.atts['a_m'])
          B_m = list(zeta.atts['b_m'])
          # Add model top (not a true level, but needed for dP calculation)
          # Also, duplicate the bottom (surface) level to get dP=0 at bottom
          import math
          A_m = [math.log(ptop)] + A_m + [A_m[-1]]
          B_m = [0] + B_m + [B_m[-1]]
          # Convert to Var objects
          zaxis = ZAxis(range(len(A_m)))
          A_m = Var(axes=[zaxis], values=A_m)
          B_m = Var(axes=[zaxis], values=B_m)
          # Compute pressure on (extended) momentum levels
          P_m = exp(A_m + B_m * log(Ps*100/pref))
          P_m = P_m.transpose('time','forecast','zaxis','lat','lon')
          # Compute dP
          P_m_1 = P_m.slice[:,:,1:,:,:]
          P_m_2 = P_m.slice[:,:,:-1,:,:].replace_axes(zaxis=P_m_1.zaxis)
          dP = P_m_1 - P_m_2
          # Put on proper thermodynamic levels
          from pygeode.formats.fstd_core import decode_levels
          values, kind = decode_levels(zeta.atts['ip1_t'])
          zaxis = fstd.LogHybrid(values=values, A=zeta.atts['a_t'], B=zeta.atts['b_t'])
          dP = dP.replace_axes(zaxis=zaxis)
          dP /= 100 # hPa


    if P is not None:
      P.atts['units'] = 'hPa'
      data['air_pressure'] = P

    if dP is not None:
      dP.atts['units'] = 'hPa'
      data['dp'] = dP  #TODO: better name?

    # Grid cell areas
    if 'cell_area' not in data:
      # Pick some arbitrary (but deterministic) variable to get the lat/lon
      var = sorted(data.values())[0]
      from common import get_area
      data['cell_area'] = get_area(var.lat,var.lon).extend(0,var.time, var.forecast)

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

    ##############################
    # Fluxes
    ##############################

    files.extend(glob(dirname+"/area_??????????"))

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
  def encode (self, dataset):
    # Convert to a dictionary (for referencing by variable name)
    data = dict((var.name,var) for var in dataset)

    # Convert to GEM-friendly field names and units
    for gem_name, standard_name, units in self.field_list:
      if standard_name in data:
        var = data.pop(standard_name)
        var = convert(var, units)
        data[gem_name] = var

    # Remove generated fields
    data.pop('air_pressure',None)
    data.pop('dp',None)

    # Check for any stragglers, remove them
    for varname in data.keys():
      if all(varname != name for n, name, u in self.field_list):
        from warnings import warn
        warn ("Dropping unrecognized field '%s'"%varname)
        data.pop(varname)

    # General cleanup stuff

    # Make sure the variables have the appropriate names
    for name, var in data.iteritems():  var.name = name

    # Convert to a list
    data = list(data.values())

    return data


  # Method to write data to file(s).
  @staticmethod
  def write (datasets, dirname):
    from pygeode.dataset import asdataset
    from pygeode.formats import fstd, fstd_core
    from os.path import exists
    if len(datasets) > 1:
      raise ValueError("Unable to handle multiple datasets yet")

    dataset = asdataset(datasets[0])
    # Write the data into one file per hour / forecast
    #TODO: make this prettier
    for year in sorted(set(dataset.time.year)):
      dataset_y = dataset(year=year)
      for month in sorted(set(dataset_y.time.month)):
        dataset_ym = dataset_y(month=month)
        for day in sorted(set(dataset_ym.time.day)):
          dataset_ymd = dataset_ym(day=day)
          for hour in sorted(set(dataset_ymd.time.hour)):
            dataset_ymdh = dataset_ymd(hour=hour)
            if hasattr(dataset,'forecast'):
              for forecast in dataset_ymdh.forecast:
                dataset_ymdhf = dataset_ymdh(forecast=forecast)
                filename = dirname+"/%04d%02d%02d%02d_%03d"%(year,month,day,hour,forecast)
                fstd.save(filename,dataset_ymdhf)
            else:
              filename = dirname+"/%04d%02d%02d%02d_000"%(year,month,day,hour)
              fstd.save(filename,dataset_ymdh)


# Instantiate this interface
interface = GEM_Data()

# Define the open method as a function, so it's picklable.
def open_file (filename):
  return interface.open_file(filename)

