# Aircraft profile diagnostic

from . import TimeVaryingDiagnostic, ImageDiagnostic
class AircraftProfiles(TimeVaryingDiagnostic,ImageDiagnostic):
  """
  Mean vertical profiles, sampled at obs locations.
  """
  @classmethod
  def add_args (cls, parser, handled=[]):
    super(AircraftProfiles,cls).add_args(parser)
    if len(handled) > 0: return  # Only run once
    group = parser.add_argument_group('options for aircraft diagnostics')
    group.add_argument('--at-aircraft-times', action='store_true', help="Sample the model data at the aircraft times before computing the profiles.")
    handled.append(True)
  def __init__ (self, at_aircraft_times, **kwargs):
    super(AircraftProfiles,self).__init__(**kwargs)
    # The fixed height levels to interpolate the model data to
    self.z_levels =   [1000.,2000.,3000.,4000.,5000.,6000.]
    self.z_bounds = [500.,1500.,2500.,3500.,4500.,5500.,6500.]
    self.obstimes = at_aircraft_times
    if self.obstimes:
      self.suffix += '_obstimes'

  def _find_applicable_obs (self, inputs):
    from ..common import have_station_data
    obs_inputs = []
    for x in inputs:
      if any(self.fieldname in d and 'altitude' in d and have_station_data(d) for d in x.datasets):
        obs_inputs.append(x)
    return obs_inputs

  def _find_applicable_models (self, inputs):
    from ..common import have_gridded_3d_data
    model_inputs = []
    for x in inputs:
      if any(self.fieldname in d and 'geopotential_height' in d and have_gridded_3d_data(d) for d in x.datasets):
        model_inputs.append(x)
    return model_inputs

  def _input_combos (self, inputs):
    model_inputs = self._find_applicable_models(inputs)
    # If there's no model data to plot, then don't bother plotting!
    if len(model_inputs) == 0: return
    obs_inputs = self._find_applicable_obs(inputs)
    for obs in obs_inputs:
      yield list(model_inputs) + [obs]


  # Find all unique observation fields
  # Discards identical fields from superset domains.
  def _find_obs(self, obs, *fieldnames):
    handled = []
    for data in obs.find(*fieldnames):
      if isinstance(data,list):
        key = data[0].axes
      else:
        key = data.axes
      if key not in handled:
        yield data
      handled.append(key)

  # Bin the obs data into fixed levels
  def _bin_obs (self, obs, years):
    from ..common import convert
    from pygeode.var import Var
    from pygeode.axis import Height
    import numpy as np

    z = Height(self.z_levels)

    outfields = []
    for obsfield,altitude in self._find_obs(obs,self.fieldname,'altitude'):

      obsfield = obsfield(l_year=years)
      altitude = altitude(l_year=years)

      obsfield = convert(obsfield,self.units)

      # Bin the aircraft data into the fixed levels.
      binned_data = np.empty(obsfield.shape+(len(self.z_levels),))
      binned_data[()] = float('nan')
      obsfield = obsfield.load()
      altitude = altitude.load()
      for i in range(len(self.z_levels)):
        match = (altitude.values >= self.z_bounds[i]) & (altitude.values < self.z_bounds[i+1])
        match = np.where(match)
        binned_data[...,i][match] = obsfield.values[match]

      obsfield = Var(axes=obsfield.axes+(z,), values=binned_data, name=obsfield.name)

      outfields.append(obsfield)

    return outfields


  # Interpolate model data directly to aircraft site locations
  def _sample_model_at_obs (self, model, obs):
    from ..common import have_gridded_3d_data, number_of_levels, number_of_timesteps, find_and_convert
    from pygeode.axis import Height
    from pygeode.interp import interpolate
    from ..station_data import Station
    from .station import StationSample

    fieldname = self.fieldname

    z = Height(self.z_levels)

    field, gph_field = find_and_convert(model, [fieldname,'geopotential_height'], [self.units,'m'], requirement=have_gridded_3d_data, maximize = (number_of_levels,number_of_timesteps))

    # Determine which years to do (based on available model data).
    # Look for years with more than a couple of timesteps (since for GEM we
    # can have a single 24h forecast from the end of the year, which gets
    # treated as valid at the start of the next year).
    years = set()
    for y in set(field.time.year):
      if sum(field.time.year==y) > 10: years.add(y)
    years = sorted(years)

    # Loop over each obs dataset, and extract data at that location.
    for obsfield in self._find_obs(obs,fieldname):
      # Assuming we're looking at only one station at a time
      assert len(obsfield.station) == 1
      station = obsfield.station.values[0]
      country = obsfield.station.country[0]

      # Use only continental US/Canada sites
      if country not in ('United States','Canada'):
        print "Skipping non-continential site:", station
        continue
      if 'Hawaii' in station:
        print "Skipping Hawaii:", station
        continue

      # Sample the model at the station locations
      outfield = StationSample(field, obsfield.station)
      gph = StationSample(gph_field, obsfield.station)

      # Interpolate to obs times
      assert obsfield.time.units == outfield.time.units
      assert obsfield.time.startdate == outfield.time.startdate
      if self.obstimes:
        from pygeode.interp import interpolate
        outfield = interpolate(outfield,'time',obsfield.time,interp_type='linear')
        gph = interpolate(gph,'time',obsfield.time,interp_type='linear')
        outfield = outfield.transpose('time','station','zaxis')
        gph = gph.transpose('time','station','zaxis')

      # Subset the data for the years of interest.
      outfield = outfield(l_year=years)
      gph = gph(l_year=years)

      # Cache the data for faster subsequent access.
      # Disable time splitting for the cache file, since open_multi doesn't work
      # very well with the encoded station data.
      print 'Sampling %s data at %s'%(model.name, list(outfield.station.values))
      if len(outfield.time) == 0:
        print "Skipping - no obs times during this period."
        continue
      outfield = model.cache.write(outfield, prefix=model.name+'_at_%s_%s%s_full'%(obs.name,fieldname,self.suffix), split_time=False, suffix=self.end_suffix)
      gph = model.cache.write(gph, prefix=model.name+'_at_%s_%s%s_full'%(obs.name,'geopotential_height',self.suffix), split_time=False, suffix=self.end_suffix)

      # Interpolate the model to the fixed vertical levels.
      outfield = interpolate(outfield, inaxis='zaxis', outaxis=z, inx=gph)
      outfield = model.cache.write(outfield, prefix=model.name+'_at_%s_%s%s_zinterp'%(obs.name,fieldname,self.suffix), split_time=False, suffix=self.end_suffix)

      yield outfield


  def do (self, inputs):

    import numpy as np
    import matplotlib.pyplot as pl
    import numpy as np
    from os.path import exists
    from os import mkdir
    from ..common import convert, select_surface, to_datetimes

    outdir = self.outdir + '/aircraft-profiles' + self.suffix + self.end_suffix
    if not exists(outdir): mkdir(outdir)

    models = inputs[:-1]
    obs = inputs[-1]

    monthly_model = [dict() for m in range(len(models))]
    monthly_obs = dict()

    # Extract model data at obs locations, and interpolate to fixed vertical
    # levels.
    for i,model in enumerate(models):
      for modelfield in self._sample_model_at_obs(model, obs):
       for year in sorted(set(modelfield.time.year)):
        for month in range(1,13):
          monthly_model[i].setdefault((year,month),[]).append(modelfield(year=year,month=month))

    # Use the model time period(s) to determine which years to consider
    # for comparisons.
    all_years = sorted(set(year for monthly_mod in monthly_model for (year,month) in monthly_mod.keys()))

    # Bin the obs data into fixed vertical levels.
    for obsfield in self._bin_obs(obs, all_years):
     for year in sorted(set(obsfield.time.year)):
      for month in range(1,13):
        monthly_obs.setdefault((year,month),[]).append(obsfield(year=year,month=month))


    # Loop over each individual year, then do all years combined.
    for years in zip(all_years) + [all_years]:
     year_string = str(years[0]) if len(years) == 1 else str(years[0])+'-'+str(years[-1])
     for season, months in ('Dec-Jan-Feb',[0,1,2]), ('Mar-Apr-May',[3,4,5]), ('Jun-Jul-Aug',[6,7,8]), ('Sep-Oct-Nov',[9,10,11]), ('Annual',range(1,13)):
      # Broadcast years and months into pairs, and adjust to previous year
      # if month < 1
      keys = [(y,m) if m > 0 else (y-1,m+12) for y in years for m in months]

      fig = pl.figure(figsize=(6,6))

      outfile = "%s/%s_profiles_%s%s_%s_%s.%s"%(outdir,'_'.join(d.name for d in models+[obs]),self.fieldname,self.suffix+self.end_suffix,season,year_string,self.image_format)
      if exists(outfile): continue

      # Placeholder profile for missing data
      missing = np.empty([len(self.z_levels)])
      missing[:] = float('nan')

      obs_data = sum([monthly_obs.get((y,m),[]) for y,m in keys],[])
      obs_std = stddev_profile(obs_data)
      obs_data = average_profile(obs_data)
      if obs_data is None:
        obs_data = obs_std = missing

      model_data = []
      model_std = []
      for monthly_mod in monthly_model:
        mod_data = sum([monthly_mod.get((y,m),[]) for y,m in keys],[])
        mod_std = stddev_profile(mod_data)
        mod_data = average_profile(mod_data)
        model_data.append(mod_data)
        model_std.append(mod_std)

      ax = pl.subplot(111)
      for i in range(len(models)):
        if model_data[i] is None: continue
        pl.plot(model_data[i], self.z_levels, color=models[i].color, linestyle=models[i].linestyle, linewidth=2, marker=models[i].marker, markersize=10, markeredgecolor=models[i].color, label=models[i].title)
        pl.plot(model_data[i]+model_std[i], self.z_levels, color=models[i].color, linestyle='--')
        pl.plot(model_data[i]-model_std[i], self.z_levels, color=models[i].color, linestyle='--')

      pl.plot(obs_data, self.z_levels, color=obs.color, linestyle=obs.linestyle, linewidth=2, marker=obs.marker, markersize=10, markeredgecolor=obs.color, label=obs.title)
      pl.fill_betweenx(self.z_levels, obs_data-obs_std, obs_data+obs_std, color=obs.color, alpha=0.2, linewidth=0)
      pl.title('%s (%s)'%(season,year_string))
      pl.xlabel('%s [%s]'%(self.fieldname,self.units))
      pl.ylabel('Altitude [m]')
      pl.legend(loc='best')

      fig.savefig(outfile)



# Take an average of all pieces of data given
# (averaged over all dimensions except height)
def average_profile(data):
  import numpy as np
  if len(data) == 0: return None
  # Extract the data
  data = [v.get() for v in data]
  # Temporal average
  sum = [np.nansum(v,axis=0) for v in data]
  count = [np.sum(np.isfinite(v),axis=0) for v in data]
  data = [s/c for s,c in zip(sum,count)]
  # Average over all stations
  data = np.concatenate(data)
  sum = np.nansum(data,axis=0)
  count = np.sum(np.isfinite(data),axis=0)
  data = sum/count
  return data

# Take standard deviation of all pieces of data given
# (over all dimensions except height)
def stddev_profile(data):
  import numpy as np
  if len(data) == 0: return None
  mean = average_profile(data)
  # Extract the data
  data = [v.get()-mean for v in data]
  # Temporal stddev
  sum = [np.nansum(v**2,axis=0) for v in data]
  count = [np.sum(np.isfinite(v),axis=0) for v in data]
  data = [np.sqrt(s/c) for s,c in zip(sum,count)]
  # Std. dev. over all stations
  data = np.concatenate(data)
  sum = np.nansum(data**2,axis=0)
  count = np.sum(np.isfinite(data),axis=0)
  data = np.sqrt(sum/count)
  return data





from . import table
table['aircraft-profiles'] = AircraftProfiles

