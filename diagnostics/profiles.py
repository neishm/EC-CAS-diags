# Aircraft profile diagnostic

if True:

  def find_applicable_obs (inputs, fieldname):
    from ..common import have_station_data
    obs_inputs = []
    for x in inputs:
      if any(fieldname in d and 'altitude' in d and have_station_data(d) for d in x.datasets):
        obs_inputs.append(x)
    return obs_inputs

  def find_applicable_models (inputs, fieldname):
    from ..common import have_gridded_3d_data
    model_inputs = []
    for x in inputs:
      if any(fieldname in d and 'geopotential_height' in d and have_gridded_3d_data(d) for d in x.datasets):
        model_inputs.append(x)
    return model_inputs

from . import ImageDiagnostic
class AircraftProfiles(ImageDiagnostic):
  """
  Mean vertical profiles, sampled at obs locations.
  """
  def do_all (self, inputs, fieldname, units, outdir, **kwargs):
    # Apply any pre-filtering to the input data.
    inputs = self.filter_inputs(inputs)

    model_inputs = find_applicable_models(inputs, fieldname)
    # If there's no model data to plot, then don't bother plotting!
    if len(model_inputs) == 0: return
    obs_inputs = find_applicable_obs(inputs, fieldname)
    for obs in obs_inputs:
      profiles (obs, model_inputs, fieldname, units, outdir, format=self.image_format)

if True:
  from .timeseries import StationSample

  # Find all unique observation fields
  # Discards identical fields from superset domains.
  def find_obs(obs, *fieldnames):
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
  def bin_obs (obs, fieldname, units, z_levels, z_bounds, years):
    from ..common import convert
    from pygeode.var import Var
    from pygeode.axis import Height
    import numpy as np

    z = Height(z_levels)

    outfields = []
    for obsfield,altitude in find_obs(obs,fieldname,'altitude'):

      obsfield = obsfield(l_year=years)
      altitude = altitude(l_year=years)

      obsfield = convert(obsfield,units)

      # Bin the aircraft data into the fixed levels.
      binned_data = np.empty(obsfield.shape+(len(z_levels),))
      binned_data[()] = float('nan')
      obsfield = obsfield.load()
      altitude = altitude.load()
      for i in range(len(z_levels)):
        match = (altitude.values >= z_bounds[i]) & (altitude.values < z_bounds[i+1])
        match = np.where(match)
        binned_data[...,i][match] = obsfield.values[match]

      obsfield = Var(axes=obsfield.axes+(z,), values=binned_data, name=obsfield.name)

      # Cache the binned data
#      obsfield = obs.cache.write(obsfield, prefix=obs.name+'_%s_zbin'%fieldname, split_time=False)

      outfields.append(obsfield)

    return outfields


  # Interpolate model data directly to aircraft site locations
  def sample_model_at_obs (model, obs, fieldname, units, z_levels, z_bounds):
    from ..common import have_gridded_3d_data, number_of_levels, number_of_timesteps, find_and_convert
    from pygeode.axis import Height
    from pygeode.interp import interpolate
    from ..station_data import Station

    z = Height(z_levels)

    field, gph_field = find_and_convert(model, [fieldname,'geopotential_height'], [units,'m'], requirement=have_gridded_3d_data, maximize = (number_of_levels,number_of_timesteps))

    # Determine which years to do (based on available model data).
    # Look for years with more than a couple of timesteps (since for GEM we
    # can have a single 24h forecast from the end of the year, which gets
    # treated as valid at the start of the next year).
    years = set()
    for y in set(field.time.year):
      if sum(field.time.year==y) > 10: years.add(y)
    years = sorted(years)

    # Concatenate all the available station locations into a single coordinate.
    station_names = []
    auxarrays = {}
    for obsfield in find_obs(obs,fieldname):
      station_names.extend(obsfield.station.values)
      for key, value in obsfield.station.auxarrays.iteritems():
        auxarrays.setdefault(key,[]).extend(value)

    # Use only continental US/Canada sites
    keep = [False]*len(station_names)
    for i in range(len(station_names)):
      if auxarrays['country'][i] in ('United States','Canada'):
        keep[i] = True
      if 'Hawaii' in station_names[i]:
        keep[i] = False
    station_names = [s for k,s in zip(keep,station_names) if k]
    auxarrays = dict((key,[v for k,v in zip(keep,values) if k]) for key,values in auxarrays.iteritems())

    stations = Station(values=station_names, **auxarrays)

    # Sample the model at the station locations
    outfield = StationSample(field, stations)
    gph = StationSample(gph_field, stations)

    outfield = outfield(l_year=years)
    gph = gph(l_year=years)

    # Cache the data for faster subsequent access.
      # Disable time splitting for the cache file, since open_multi doesn't work
    # very well with the encoded station data.
    print 'Sampling %s data at %s'%(model.name, list(outfield.station.values))
    outfield = model.cache.write(outfield, prefix=model.name+'_at_%s_%s_full'%(obs.name,fieldname), split_time=False)
    gph = model.cache.write(gph, prefix=model.name+'_at_%s_%s_full'%(obs.name,'geopotential_height'), split_time=False)

    # Interpolate the model to the fixed vertical levels.
    outfield = interpolate(outfield, inaxis='zaxis', outaxis=z, inx=gph)
    outfield = model.cache.write(outfield, prefix=model.name+'_at_%s_%s_zinterp'%(obs.name,fieldname), split_time=False)

    return [outfield]

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


  def profiles (obs, models, fieldname, units, outdir, format='png'):

    import numpy as np
    import matplotlib.pyplot as pl
    import numpy as np
    from os.path import exists
    from ..common import convert, select_surface, to_datetimes

    # The fixed height levels to interpolate the model data to
    z_levels =   [1000.,2000.,3000.,4000.,5000.,6000.]
    z_bounds = [500.,1500.,2500.,3500.,4500.,5500.,6500.]

    monthly_model = [dict() for m in range(len(models))]
    monthly_obs = dict()

    # Extract model data at obs locations, and interpolate to fixed vertical
    # levels.
    for i,model in enumerate(models):
      for modelfield in sample_model_at_obs(model, obs, fieldname, units, z_levels, z_bounds):
       for year in sorted(set(modelfield.time.year)):
        for month in range(1,13):
          monthly_model[i].setdefault((year,month),[]).append(modelfield(year=year,month=month))

    # Use the model time period(s) to determine which years to consider
    # for comparisons.
    all_years = sorted(set(year for monthly_mod in monthly_model for (year,month) in monthly_mod.keys()))

    # Bin the obs data into fixed vertical levels.
    for obsfield in bin_obs(obs, fieldname, units, z_levels, z_bounds, all_years):
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

      outfile = "%s/%s_profiles_%s_%s_%s.%s"%(outdir,'_'.join(d.name for d in models+[obs]),fieldname,season,year_string,format)
      if exists(outfile): continue

      # Placeholder profile for missing data
      missing = np.empty([len(z_levels)])
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
        pl.plot(model_data[i], z_levels, color=models[i].color, linestyle=models[i].linestyle, linewidth=2, marker=models[i].marker, markersize=10, markeredgecolor=models[i].color, label=models[i].title)
        pl.plot(model_data[i]+model_std[i], z_levels, color=models[i].color, linestyle='--')
        pl.plot(model_data[i]-model_std[i], z_levels, color=models[i].color, linestyle='--')

      pl.plot(obs_data, z_levels, color=obs.color, linestyle=obs.linestyle, linewidth=2, marker=obs.marker, markersize=10, markeredgecolor=obs.color, label=obs.title)
      pl.fill_betweenx(z_levels, obs_data-obs_std, obs_data+obs_std, color=obs.color, alpha=0.2, linewidth=0)
      pl.title('%s (%s)'%(season,year_string))
      pl.xlabel('%s [%s]'%(fieldname,units))
      pl.ylabel('Altitude [m]')
      pl.legend(loc='best')

      fig.savefig(outfile)

from . import table
table['aircraft-profiles'] = AircraftProfiles

