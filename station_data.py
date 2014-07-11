# Helper methods for dealing with station data

# A Station axis.
# Each station is a entry along this dimension.
# Latitude and longitude are provided as auxilary arrays.
from pygeode.axis import Axis
class Station (Axis):
  name = 'station'
  formatstr = "%s"
  # Override the __eq__ method for this axis, since there are currently
  # some assumptions in PyGeode about axes having numerical values.
  def __eq__ (self, other):
    if not isinstance(other,Station): return False
    return map(str,self.values) == map(str,other.values)
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
def station_axis_save_hook (var):
  from pygeode.dataset import asdataset, Dataset
  import numpy as np
  from pygeode.var import Var
  from pygeode.axis import Axis
  from copy import copy

  if not var.hasaxis('station'): return asdataset(var)

  var = copy(var)  # Shallow copy (so we can muck with the metadata)
  var.atts = dict(var.atts)

  # Consruct a generic 'station' axis (with a simple integer dimension)
  station = Axis(name='station', values=np.arange(len(var.station), dtype='int32'))

  # Get the lat/lon coordinates on this generic axis
  coordinates = [Var(axes=[station], values=val, name=name) for name,val in var.station.auxarrays.items()]

  var.atts['coordinates'] = ' '.join(c.name for c in coordinates)

  # Encode string-based coordinates (such as country)
  coordinates = [encode_string_var(c) if c.dtype.name.startswith('string') else c for c in coordinates]

  # Construct a 2D character array to hold station names
  station_name = encode_string_var(var.station)

  # Replace the station axis in the var (with the simple one created here)
  var = var.replace_axes(station=station)
  station_name = station_name.replace_axes(station=station)

  # Return everything needed to recreate the Station coordinate
  return Dataset([var, station_name]+coordinates)

#TODO: Create a special PyGeode axis class that will write only a dimension
# entry, no other metadata (BareDimension?)

# Hook for decoding a Station axis from a file.
# Reconstructs the information from a station_axis_save_hook() call.
def station_axis_load_hook (dataset):
  from copy import copy

  # If there is no station axis, then nothing to do.
  if not any(v.hasaxis('station') for v in dataset.vars):
    return dataset.vars[0]

  # Find the actual variable (the only thing with a 'coordinates' attribute
  var = [v for v in dataset if 'coordinates' in v.atts][0]

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

  return var

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

# Prep a station dataset for writing to netcdf
def encode_station_data (dataset):
  from pygeode.dataset import Dataset
  out_vars = []
  for i, var in enumerate(dataset.vars):
    stuff = station_axis_save_hook(var)
    # Append the data
    # Include station auxiliary data once only
    if i == 0:
      out_vars.extend(stuff.vars)
    else:
      out_vars.append(stuff[var.name])

  return Dataset(out_vars)

# Reconstruct station data from a netcdf file
def decode_station_data (dataset):
  from pygeode.dataset import Dataset

  # Collect the station auxiliary data (anything without a 'coordinates' attribute?)
  station_meta = [var for var in dataset.vars if 'coordinates' not in var.atts]

  # Similarly, collect the actual variables
  in_vars = [var for var in dataset.vars if 'coordinates' in var.atts]

  # Get the station axis
  station = station_axis_load_hook(dataset).station

  # Construct a dataset with the variables, and the decoded station axis
  dataset = Dataset(in_vars)
  dataset = dataset.replace_axes(station=station)

  return dataset

