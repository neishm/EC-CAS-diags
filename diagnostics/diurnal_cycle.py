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

  def diurnal_cycle (obs, models, fieldname, units, outdir):
    print "doing diurnal cycle for obs = %s, models = %s"%(obs.name,[model.name for model in models])
    #TODO


