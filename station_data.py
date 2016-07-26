# Helper methods for dealing with station data

# A Station axis.
# Each station is a entry along this dimension.
# Latitude and longitude are provided as auxilary arrays.
from pygeode.axis import Axis
class Station (Axis):
  name = 'station'
  formatstr = "%s"
  # Workaround a bug with the Axis class.  It tries to find a relative
  # tolerance, but the code for finding nonzeros axis values breaks on
  # string arrays (at least for the numpy in Ubuntu 10.04)
  #TODO: remove this once Ubuntu 10.04 is no longer supported.
  def __init__ (self, values, *args, **kwargs):
    if 'rtol' not in kwargs: kwargs['rtol']=1e-5
    from pygeode.axis import Axis
    Axis.__init__(self, values, *args, **kwargs)
  # Override the __eq__ method for this axis, since there are currently
  # some assumptions in PyGeode about axes having numerical values.
  def __eq__ (self, other):
    if not isinstance(other,Station): return False
    return map(str,self.values) == map(str,other.values)
  # Override str_as_val to allow indexing by station name
  def str_as_val(self, key, s):
    return s
  # Override get_slice to allow indexing by station name
  def get_slice (self, kwargs, ignore_mismatch=False):
    import numpy as np
    stations = list(self.values)
    for key in kwargs.iterkeys():
      if key.startswith('i_'):
        indices = kwargs.pop(key)
        key = key[2:]
        if not self.has_alias(key): continue
        return indices
        continue
      if key.startswith('l_'):
        names = kwargs.pop(key)
        key = key[2:]
        if not self.has_alias(key): continue
        return [stations.index(n) for n in names]
        continue
      if not self.has_alias(key): continue
      station = kwargs.pop(key)
      if station not in self.values:
        raise IndexError("station '%s' not found in Station axis."%station)
      s = np.where(self.values == station)[0][0]
      return s
  # Create our own map_to interface, since PyGeode will choke on string arrays
  def map_to(self, other):
    if not self.isparentof(other) and not other.isparentof(self): return None
    stations = list(self.values)
    indices = []
    for station in list(other.values):
      if station not in stations:
        indices.append(-1)
      else:
        indices.append(stations.index(station))
    return indices
  # Need to override _getitem_asvar, because slicing a string array with None
  # causes numpy to add an extra dimension?
  def _getitem_asvar (self, slices):
    from pygeode.axis import Axis
    if slices is None: return self
    return Axis._getitem_asvar (self, slices)

del Axis

# Convert a 1D string variable into a 2D character variable
# (useful for encoding string arrays into netcdf)
def encode_string_var (var):
  import numpy as np
  from pygeode.var import Var
  from pygeode.axis import Axis

  # Construct a 2D character array to hold strings
  strlen = max(len(string) for string in var.values)
  #TODO: make this a simple dimension (no coordinate values needed!)
  strlen_axis = Axis (values=np.arange(strlen, dtype='int32'), name=var.name+"_strlen")
  dtype = '|S'+str(strlen)  # For a convenient view on the character array
                                      # (to help popluate it from strings)

  data = np.zeros(list(var.shape)+[strlen], dtype='|S1')
  data.view(dtype)[...,0] = var.values
  var = Var(list(var.axes)+[strlen_axis], values=data, name=var.name+"_name")
  return var

# Convert a 2D character variable back into a 1D string variable
def decode_string_var (var):
  from pygeode.var import Var

  name = var.name
  if name.endswith('_name'):
    name = name[:-5]
  data = [''.join(s) for s in var.get()]
  return Var(axes=var.axes[:-1], values=data, name=name)




# Hook for encoding to a file
# Roughly follows CF Metadata conventions for station data
# http://cf-pcmdi.llnl.gov/documents/cf-conventions/1.6/aphs02.html
# NOTE: Assumes there is only one station axis to encode.
def station_axis_save_hook (dataset):
  import numpy as np
  from pygeode.var import Var
  from pygeode.axis import Axis
  from copy import copy

  outvars = []
  station = None  # start with no station axis
  for var in dataset:

    if not var.hasaxis('station'):
      outvars.append(var)
      continue

    var = copy(var)  # Shallow copy (so we can muck with the metadata)
    var.atts = dict(var.atts)

    # First station data encountered?
    # Need to construct a station axis
    if station is None:
      # Consruct a generic 'station' axis (with a simple integer dimension)
      station = Axis(name='station', values=np.arange(len(var.station), dtype='int32'))

      # Get the lat/lon coordinates on this generic axis
      coordinates = [Var(axes=[station], values=val, name=name) for name,val in var.station.auxarrays.items()]

      coordinate_names = ' '.join(c.name for c in coordinates)

      # Encode string-based coordinates (such as country)
      coordinates = [encode_string_var(c) if c.dtype.name.startswith('string') else c for c in coordinates]

      # Construct a 2D character array to hold station names
      station_name = encode_string_var(var.station)

    # Fix possible bug in netcdf - can't encode an empty string??
    # Or, maybe it's a problem with ncview
    if len(coordinate_names) == 0: coordinate_names = ' '
    var.atts['coordinates'] = coordinate_names

    # Replace the station axis in the var (with the simple one created here)
    var = var.replace_axes(station=station)
    station_name = station_name.replace_axes(station=station)

    # Return everything needed to recreate the Station coordinate
    outvars.append(var)

  if station is not None:
    outvars.extend([station_name]+coordinates)
  return outvars

#TODO: Create a special PyGeode axis class that will write only a dimension
# entry, no other metadata (BareDimension?)

# Hook for decoding a Station axis from a file.
# Reconstructs the information from a station_axis_save_hook() call.
def station_axis_load_hook (dataset):
  from copy import copy

  # If there is no station axis, then nothing to do.
  if not any(v.hasaxis('station') for v in dataset.vars):
    return dataset.vars

  outvars = []

  # Find the actual variables (the things with a 'coordinates' attribute
  invars = [v for v in dataset if 'coordinates' in v.atts]

  for var in invars:
    # Make a shallow copy of the var (to edit the metadata in-place)
    var = copy(var)
    var.atts = dict(var.atts)

    # Find all the coordinates
    coordinates = {}
    for c in var.atts['coordinates'].split():
      if c in dataset:
        coordinates[c] = dataset[c].get()
      elif c+"_name" in dataset:
        coordinates[c] = decode_string_var(dataset[c+"_name"]).get()
    del var.atts['coordinates']

    # Convert the 2D character array to a 1D string array
    station_name = decode_string_var(dataset.station_name)
    station = Station(values=station_name.values, **coordinates)

    # Replace the station axis
    var = var.replace_axes(station=station)

    outvars.append(var)

  return outvars

# Given a dictionary of obs locations, construct a station axis.
def make_station_axis (obs_locations):

  # Construct an alphabetically sorted arrays of stations
  stations = sorted(obs_locations.keys())
  lats = []
  lons = []
  countries = []
  for station in stations:
    lat, lon, country = obs_locations[station]
    lats.append(lat)
    lons.append(lon)
    countries.append(country)

  return Station(values=stations, lat=lats, lon=lons, country=countries)

