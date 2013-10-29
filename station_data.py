# Helper methods for dealing with station data

# Given a dictionary of obs locations, construct a station axis.
def make_station_axis (obs_locations):
  from common import Station

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
  from common import station_axis_save_hook
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
  from common import station_axis_load_hook
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

