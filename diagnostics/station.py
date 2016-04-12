# Station-based diagnostic (superclass)

from . import Diagnostic
class StationComparison(Diagnostic):
  @staticmethod
  def add_args (parser, handled=[]):
    super(StationComparison,StationComparison).add_args(parser)
    if len(handled) > 0: return  # Only run once
    group = parser.add_argument_group('options for station comparisons')
    group.add_argument('--stations', action='store', metavar='StationA,StationB,...', help='Comma-separated list of stations to look at.  Only part of the station name is needed.  By default, all available stations are used.')
    handled.append(True)
  def __init__(self, stations=None, **kwargs):
    super(StationComparison,self).__init__(**kwargs)
    if stations is not None:
      self.stations = stations.split(',')
    else:
      self.stations = None

  # Helper method - subset the obs at the explicit stations given by the user.
  def _select_obs_sites (self, obs):
    final_list = []
    from ..interfaces import DerivedProduct
    if self.stations is None: return obs
    out_datasets = []
    for dataset in obs.datasets:
      matches = [self._lookup_station(s) for s in dataset.station]
      matches = filter(None,matches)
      if len(matches) == 0: continue
      out_datasets.append(dataset(l_station=matches))
      final_list.extend(matches)
    obs = DerivedProduct(out_datasets, source=obs)
    obs.name = obs.name + '_'+','.join(s for s in final_list)
    return obs

  # Helper method - given an obs dataset, filter model data onto the same
  # points.
  @staticmethod
  def _sample_dataset_at_obs (obs, model):
    from pygeode.dataset import Dataset
    # Sample at the station locations
    fields = []
    for var in model.vars:
      fields.append(StationSample(var, obs.station))
    return Dataset(fields)

  # Helper method - determine if a dataset is in obs space (i.e., has a
  # station axis).
  # TODO: remove this some Dataset objects include a hasaxis routine.
  @staticmethod
  def _has_station_axis (dataset):
    for var in dataset.vars:
      if var.hasaxis('station'): return True
    return False

  # Interpolate model data directly to station locations
  #TODO: interpolate to the station height.
  def filter_inputs (self, inputs):
    from ..interfaces import DerivedProduct
    inputs = super(StationComparison,self).filter_inputs(inputs)
    obs = [m for m in inputs if any(self._has_station_axis(d) for d in m.datasets)][0]
    models = [m for m in inputs if m is not obs]
    # Subset the obs locations (if particular locations were given on the
    # command-line).
    obs = self._select_obs_sites(obs)

    # Sample all the model data at the obs locations
    out_models = []
    for m in models:
      datasets = []
      for od in obs.datasets:
        for md in m.datasets:
          datasets.append(self._sample_dataset_at_obs(od,md))
      m = DerivedProduct(datasets,source=m)
      m.name = m.name + '_at_%s'%obs.name
      out_models.append(m)
    return [obs] + out_models


  # Determine if a particular station matches a list of station names.
  def _lookup_station (self, station):
    string_filter = lambda x: x.lower().replace(' ','').replace('_','')
    station = string_filter(station)
    stations = [string_filter(s) for s in self.stations]
    for s in stations:
      if station.startswith(s): return s
    return None

# Sample a model field at station locations
#TODO: drop locations that aren't within the model grid.
#TODO: handle non-cartesian coordinates.
#TODO: handle timeseries data (data already output at particular lat/lon).
from pygeode.var import Var
class StationSample(Var):
  def __init__ (self, model_data, station_axis):
    from pygeode.var import Var, copy_meta
    import numpy as np
    # Determine which model lat/lon indices to sample at
    lat_indices = []
    lon_indices = []
    for lat in station_axis.lat:
      lat_indices.append(np.argmin(abs(model_data.lat.values-lat)))
    for lon in station_axis.lon:
      lon_indices.append(np.argmin(abs(model_data.lon.values%360-lon%360)))
    self.lat_indices = lat_indices
    self.lon_indices = lon_indices
    # Replace lat/lon axes with the station axis
    lat_iaxis = model_data.whichaxis('lat')
    lon_iaxis = model_data.whichaxis('lon')
    axes = list(model_data.axes)
    axes[lat_iaxis] = station_axis
    axes = axes[:lon_iaxis]+axes[lon_iaxis+1:]
    Var.__init__(self, axes, dtype=model_data.dtype)
    copy_meta(model_data,self)
    self.model_data = model_data
    self.station_axis = station_axis
    self.station_iaxis = self.whichaxis('station')
    self.lat_iaxis = lat_iaxis
    self.lon_iaxis = lon_iaxis
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
      lat_iaxis = self.lat_iaxis
      lon_iaxis = self.lon_iaxis
      assert indata.shape[lat_iaxis] == self.model_data.shape[lat_iaxis]
      assert indata.shape[lon_iaxis] == self.model_data.shape[lon_iaxis]
      for i,station in enumerate(station_axis.values):
        # Inject the station index into the output slice
        full_outsl = outsl[:istation]+(i,)+outsl[istation:]
        insl = [slice(None)]*self.model_data.naxes
        insl[lat_iaxis] = self.lat_indices[i]
        insl[lon_iaxis] = self.lon_indices[i]
        out[full_outsl] = indata[insl]
    pbar.update(100)
    return out
del Var


