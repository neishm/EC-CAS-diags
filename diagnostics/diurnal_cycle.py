# Diurnal cycle diagnostic

def have_regular_time_axis(d):
  from pygeode.timeaxis import Time
  from pygeode.timeutils import reltime
  import numpy as np
  # Omit data with no time information.
  if 'time' not in d: return False
  # Omit data where the time is not a proper axis (e.g. for ObsPack).
  if not isinstance(d.time,Time): return False
  # Check the time of day for regular intervals 
  hours = sorted(set(reltime(d.time,units='hours')%24))
  if len(set(np.diff(hours))) == 1: return True
  return False

if True:

  from .timeseries import find_applicable_models
  def find_applicable_obs (inputs, fieldname):
    from ..common import have_station_data
    obs_inputs = []
    for x in inputs:
      if any(fieldname in d and have_station_data(d) and have_regular_time_axis(d) for d in x.datasets):
        obs_inputs.append(x)
    return obs_inputs

  def do_all (inputs, fieldname, units, outdir, **kwargs):
    model_inputs = find_applicable_models(inputs, fieldname)
    # If there's no model data to plot, then don't bother plotting!
    if len(model_inputs) == 0: return
    obs_inputs = find_applicable_obs(inputs, fieldname)
    for obs in obs_inputs:
      diurnal_cycle (obs, model_inputs, fieldname, units, outdir, **kwargs)

  # Compute a diurnal mean.
  # Takes a PyGeode Var object as input.
  # Returns the hour of the day, and the diurnal mean data as numpy arrays.
  # Note: only works on one timeseries at a time.
  def compute_diurnal_mean (var):
    import numpy as np
    from pygeode.timeutils import reltime
    assert len(var.axes) == 1
    hours = reltime(var.time, units='hours')
    hours_mod = hours%24
    data = var.get()
    diurnal_hours = sorted(set(hours_mod))
    out = []
    for h in diurnal_hours:
      current_data = data[hours_mod==h]
      count = np.nansum(np.isfinite(current_data))
      out.append (np.nansum(current_data) / count)
    return diurnal_hours, out

  def diurnal_cycle (obs, models, fieldname, units, outdir):
    from .timeseries import sample_model_at_obs
    from ..common import convert, long_monthnames, select_surface
    from matplotlib import pyplot as pl
    from os.path import exists
    print "doing diurnal cycle for obs = %s, models = %s"%(obs.name,[model.name for model in models])
    model_data = []
    for model in models:
      model_data.append(sample_model_at_obs(model,obs,fieldname,units))

    # Use model years for comparisons
    years = [set(mod_data.time.year) for mod_data in model_data]
    years = sorted(set.union(*years))
    print years

    obs_data = obs.find_best(fieldname)
    obs_data = select_surface(obs_data)
    # Cache the observation data, for faster subsequent access
    obs_data = obs.cache.write(obs_data, prefix=obs.name+'_sfc_%s'%fieldname, split_time=False)
    obs_data = convert(obs_data, units, context=fieldname)

    # Extract the data for each station,year,month.
    # Compute the diurnal means and do the plot.
    for station in obs_data.station.values:
      for year in years:
        outfile = "%s/%s_diurnal_cycle_%s_at_%s_for_%04d"%(outdir,'_'.join(d.name for d in models+[obs]), fieldname, station, year)
        fig = pl.figure(figsize=(10,10))
        pl.suptitle ("%s diurnal cycle at %s"%(fieldname,station), fontsize=18)
        for month, month_string in long_monthnames:
          if month <= 6: plotnum = 2*month-1
          else: plotnum = 2*(month-6)
          pl.subplot(6,2,plotnum)
          pl.title(month_string)

          for i in range(len(models)):
            current_model_data = model_data[i](station=station).squeeze('station')(year=year,month=month).squeeze()
            hours, data = compute_diurnal_mean(current_model_data)
            pl.plot(hours, data, color=models[i].color, linestyle=models[i].linestyle, marker=models[i].marker, markersize=10, markeredgecolor=models[i].color, label=models[i].name)

          current_obs_data = obs_data(station=station).squeeze('station')(year=year,month=month)
          hours, data = compute_diurnal_mean(current_obs_data)
          pl.plot(hours, data, color=obs.color, linestyle=obs.linestyle, linewidth=2, marker=obs.marker, markersize=10, markeredgecolor=obs.color, label=obs.title)
          hourticks = range(0,24,2)
          if plotnum in (11,12):
            pl.xticks(hourticks)
            pl.xlabel('hour')
          else:
            pl.xticks(hourticks,['']*len(hourticks))
          pl.xlim(0,24)
          if plotnum%2 == 1:
            pl.ylabel('[%s]'%units)
          # Don't use matplotlib's axis label offset (looks ugly).
          # http://stackoverflow.com/questions/24171064/matplotlib-remove-axis-label-offset-by-default
          pl.gca().get_yaxis().get_major_formatter().set_useOffset(False)
        pl.savefig(outfile)
        return
    #TODO


