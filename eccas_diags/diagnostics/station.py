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


# Station-based diagnostic (superclass)

from . import Diagnostic
class StationComparison(Diagnostic):
  @classmethod
  def add_args (cls, parser, handled=[]):
    super(StationComparison,cls).add_args(parser)
    if len(handled) > 0: return  # Only run once
    group = parser.add_argument_group('options for station comparisons')
    group.add_argument('--stations', action='store', metavar='StationA,StationB,...', help='Comma-separated list of stations to look at.  Only part of the station name is needed.  By default, all available stations are used.')
    group.add_argument('--no-require-obs', action='store_true', help="Do station comparisons for all requested fields, even fields that don't have any observation data.")
    handled.append(True)
  def __init__(self, stations=None, no_require_obs=None, **kwargs):
    super(StationComparison,self).__init__(**kwargs)
    if stations is not None:
      self.stations = stations.split(',')
    else:
      self.stations = None
    self.no_require_obs = no_require_obs

  # Override the input criteria for the no_require_obs case.
  def _select_inputs (self, inputs):
    from ..interfaces import DerivedProduct
    selected = []
    for i in inputs:
      # If this is an obs dataset that has NO data for this fieldname,
      # and we want to force the diagnostic anyway, then include all
      # obs locations for sampling the model at.
      # The obs will be (hopefully) dropped at a later stage when it's
      # apparent there's no actual data available.
      if self.no_require_obs and self._has_station_axis(i) and not i.have(self.fieldname):
        selected.append(i)
        continue
      # Otherwise, use the usual criteria (copied from the Diagnostic base
      # class).
      datasets = filter(self._check_dataset,i.datasets)
      if len(datasets) == 0: continue  # No matches for this product?
      if list(datasets) == list(i.datasets):
        selected.append(i)
      else:
        selected.append(DerivedProduct(datasets,source=i))
    return selected

  # Helper method - subset the obs at the explicit stations given by the user.
  def _select_obs_sites (self, obs):
    final_list = []
    from ..interfaces import DerivedProduct
    if self.stations is None: return obs
    out_datasets = []
    for dataset in obs.datasets:
      # Determine which stations were selected by the user
      matches = []
      for s in dataset.station:
        name = self._lookup_station(s)
        if name is not None:
          matches.append(s)
          if name not in final_list:
            final_list.append(name)
      if len(matches) == 0: continue
#      print "?? want to match:", matches
      # Subset at these stations
      out_datasets.append(dataset(l_station=matches))
#      print "?? result:", dataset(l_station=matches)
    obs = DerivedProduct(out_datasets, source=obs)
    return obs

  # Helper method - given an obs dataset, sample model data at the same
  # points.
  def _sample_model_at_obs (self, model, obs):
    from pygeode.dataset import Dataset
    from pygeode.axis import concat
    from ..common import closeness_to_surface, number_of_timesteps, select_surface
    from ..interfaces import DerivedProduct

    # Determine which obs fields are available at which stations.
    obs_stations = dict()
    for obs_dataset in obs.datasets:
      for obs_var in obs_dataset:
        obs_stations.setdefault(obs_var.name,[]).append(obs_var.station)
    obs_stations = dict([(varname,concat(s)) for varname,s in obs_stations.iteritems()])

    # For the case where we're forcing a station sample when we don't actually
    # have the obs field, we need to provide a list of all stations.
    if self.no_require_obs and self.fieldname not in obs_stations:
      all_stations = []
      for varname in sorted(obs_stations.keys()):
        if obs_stations[varname] not in all_stations:
          all_stations.append(obs_stations[varname])
      obs_stations[self.fieldname] = concat(all_stations)


    # Sample at *all* obs sites for the cache file.
    fields = sorted(set(obs_stations.keys()))
    fields = [f for f in fields if model.have(f)]
    try:
      # First, try more generic match with 2D lat/lon fields.
      vars_allsites = model.find_best(fields+['lat','lon'], maximize = (closeness_to_surface,number_of_timesteps))
      lat, lon = vars_allsites[-2:]
      vars_allsites = vars_allsites[:-2]
    except KeyError:
      # If lat/lon fields not available, assume lat and lon are axes inside
      # the field (no explicit 2D fields available).
      vars_allsites = model.find_best(fields, maximize = (closeness_to_surface,number_of_timesteps))
      lat, lon = None, None
    # Sample at *all* applicable sites, and make one cache file.
    vars_allsites = map(select_surface,vars_allsites)
    vars_allsites = [StationSample(var,obs_stations[var.name],lat=lat,lon=lon) for var in vars_allsites]
    vars_allsites = [model.cache.write(var, prefix=model.name+'_at_%s_%s%s'%(obs.name,var.name,self.suffix), split_time=False, suffix=self.end_suffix) if len(var.time) > 0 else var for var in vars_allsites]

    out_datasets = []

    # Do a 1:1 sampling of the model at the obs sites
    for obs_dataset in obs.datasets:

      # Select out the particular station we want for this iteration.
      vars = [var(l_station=obs_dataset.station.station) for var in vars_allsites]
      if len(vars) > 0:
        out_datasets.append(Dataset(vars))

    # Wrap it up as a DataProduct, and we're done.
    out = DerivedProduct(out_datasets,source=model)
    return out


  # Helper method - determine if a dataset is in obs space (i.e., has a
  # station axis).
  # TODO: remove this some Dataset objects include a hasaxis routine.
  @staticmethod
  def _has_station_axis (product):
    for dataset in product.datasets:
      for var in dataset.vars:
        if var.hasaxis('station'): return True
    return False

  # For each observation dataset,
  # interpolate model data directly to station locations.
  def _input_combos (self, inputs):
    all_obs = [m for m in inputs if self._has_station_axis(m)]
    models = [m for m in inputs if m not in all_obs]

    # Loop over each obs product
    for obs in all_obs:
      if len(obs.datasets) == 0: continue
      # Loop over each model
      out_models = []
      for m in models:
        # Sample model dataset at each applicable obs dataset.
        m = self._sample_model_at_obs(m,obs)
        if len(m.datasets) == 0: continue  # Ignore non-applicable models.
        # Subset the obs locations (if particular locations were given on the
        # command-line).
        m = self._select_obs_sites(m)
        out_models.append(m)
      if len(out_models) == 0: continue  # Don't do obs-only diagnostic.
      # Subset the obs locations (if particular locations were given on the
      # command-line).
      obs = self._select_obs_sites(obs)
      if len(obs.datasets) == 0: continue  # Ignore combos where the obs don't
                                           # match anything in the user list.
      yield out_models + [obs]


  # Determine if a particular station matches a list of station names.
  def _lookup_station (self, station):
    string_filter = lambda x: x.lower().replace(' ','').replace('_','')
    station = string_filter(station)
    stations = [string_filter(s) for s in self.stations]
    for s in stations:
      if station.startswith(s): return s
    return None

# Sample a model field at station locations
#TODO: handle timeseries data (data already output at particular lat/lon).
from pygeode.var import Var
class StationSample(Var):
  def __init__ (self, model_data, station_axis, lat=None,lon=None):
    from pygeode.var import Var, copy_meta
    import numpy as np
    # Get model lat/lon, broadcasted to all model dimensions.
    yaxis_loc = model_data.whichaxis('yaxis')
    xaxis_loc = model_data.whichaxis('xaxis')
    if model_data.hasaxis('lat') and model_data.hasaxis('lon'):
      model_lat = model_data.getaxis('lat').values
      model_lat = model_lat.reshape([len(model_lat) if a.name == 'lat' else 1 for a in model_data.axes])
      model_lon = model_data.getaxis('lon').values
      model_lon = model_lon.reshape([len(model_lon) if a.name == 'lon' else 1 for a in model_data.axes])
    elif lat is not None and lon is not None:
      model_lat = lat.get().reshape([model_data.shape[i] if i in (yaxis_loc,xaxis_loc) else 1 for i in range(model_data.naxes)])
      model_lon = lon.get().reshape([model_data.shape[i] if i in (yaxis_loc,xaxis_loc) else 1 for i in range(model_data.naxes)])
    else:
      raise ValueError("Unable to find lat/lon information for %s."%model_data.name)
    model_rlat = model_lat / 180. * np.pi
    model_rlon = model_lon / 180. * np.pi
    # Determine which model lat/lon indices to sample at
    yaxis_indices = []
    xaxis_indices = []
    for lat,lon in zip(station_axis.lat,station_axis.lon):
      # Use modifed haversine formula for distance.
      # Just need to compare relative distances, so don't need proper units.
      rlat = lat / 180. * np.pi
      rlon = lon / 180. * np.pi
      distance = np.sin((model_rlat-rlat)/2)**2 + np.cos(model_rlat)*np.cos(rlat) * np.sin((model_rlon-rlon)/2)**2
      min_distance = np.min(distance)
      ind = zip(*np.where(distance==min_distance))[0]
      # Omit points that are outside the boundary of our domain.
      # Flag these points by setting the indices to None.
      matched_lat = model_lat[tuple(np.mod(ind,model_lat.shape))]
      matched_lon = model_lon[tuple(np.mod(ind,model_lon.shape))]
      if abs(lat-matched_lat) <= 5 and abs(abs(lon-matched_lon)-180) >= 175:
        yaxis_indices.append(ind[yaxis_loc])
        xaxis_indices.append(ind[xaxis_loc])
      else:
        yaxis_indices.append(None)
        xaxis_indices.append(None)
    self.yaxis_indices = yaxis_indices
    self.xaxis_indices = xaxis_indices
    # Replace lat/lon axes with the station axis
    axes = list(model_data.axes)
    axes[yaxis_loc] = station_axis
    axes = axes[:xaxis_loc]+axes[xaxis_loc+1:]
    Var.__init__(self, axes, dtype=model_data.dtype)
    copy_meta(model_data,self)
    self.model_data = model_data
    self.station_axis = station_axis
    self.station_iaxis = self.whichaxis('station')
    self.yaxis_loc = yaxis_loc
    self.xaxis_loc = xaxis_loc
  def getview (self, view, pbar):
    import numpy as np
    from pygeode.tools import loopover
    out = np.empty(view.shape, dtype=self.dtype)
    v = view.remove(self.station_iaxis)
    station_axis = self.station_axis
    istation = self.station_iaxis
    for outsl, (indata,) in loopover(self.model_data, v, pbar=pbar):
      # Make sure we have a full lat/lon field to slice from
      # (otherwise, this routine would have to be re-written)
      yaxis_loc = self.yaxis_loc
      xaxis_loc = self.xaxis_loc
      assert indata.shape[yaxis_loc] == self.model_data.shape[yaxis_loc]
      assert indata.shape[xaxis_loc] == self.model_data.shape[xaxis_loc]
      for i,station in enumerate(station_axis.values):
        # Inject the station index into the output slice
        full_outsl = outsl[:istation]+(i,)+outsl[istation:]
        insl = [slice(None)]*self.model_data.naxes
        insl[yaxis_loc] = self.yaxis_indices[i]
        insl[xaxis_loc] = self.xaxis_indices[i]
        if insl[yaxis_loc] is not None and insl[xaxis_loc] is not None:
          out[full_outsl] = indata[insl]
        else:
          out[full_outsl] = float('nan')
    pbar.update(100)
    return out
del Var


