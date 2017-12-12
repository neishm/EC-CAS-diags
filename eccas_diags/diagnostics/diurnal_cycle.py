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


# Start with the timeseries diagnostic, and further process the data to get
# the diurnal cycle.
from .timeseries import Timeseries
class DiurnalCycle(Timeseries):
  """
  Mean diurnal cycle, sampled at obs locations.
  """
  # Only use data that has a regularly-spaced time axis.
  def _check_dataset (self, dataset):
    if super(DiurnalCycle,self)._check_dataset(dataset) is False:
      return False
    return have_regular_time_axis(dataset)

  # Compute a diurnal mean.
  # Takes a PyGeode Var object as input.
  # Returns the hour of the day, and the diurnal mean data as numpy arrays.
  # Note: only works on one timeseries at a time.
  @staticmethod
  def compute_diurnal_mean_stddev (var):
    import numpy as np
    from pygeode.timeutils import reltime
    assert len(var.axes) == 1
    hours = reltime(var.time, units='hours')
    hours_mod = hours%24
    data = var.get()
    diurnal_hours = sorted(set(hours_mod))
    mean = []
    stddev = []
    for h in diurnal_hours:
      current_data = data[hours_mod==h]
      count = np.nansum(np.isfinite(current_data))
      m = np.nansum(current_data) / count
      mean.append (m)
      v = np.nansum((current_data-m)**2)/(count-1)
      stddev.append (np.sqrt(v))
    # Wrap around to the start of the next day (complete cycle)
    # Also, wrap to the end of the previous day, in case the first hour is > 0.
    if len(diurnal_hours) > 0:
      diurnal_hours = [diurnal_hours[-1]-24] + diurnal_hours + [diurnal_hours[0]+24]
      mean = [mean[-1]] + mean + [mean[0]]
      stddev = [stddev[-1]] + stddev + [stddev[0]]
    return np.array(diurnal_hours), np.array(mean), np.array(stddev)

  # Do the diurnal cycle plots.
  def do (self, inputs):
    from ..common import long_monthnames
    from matplotlib import pyplot as pl
    from os.path import exists
    from os import mkdir

    outdir = self.outdir + '/diurnal-cycle' + self.suffix + self.end_suffix
    if not exists(outdir): mkdir(outdir)

    # Determine years for comparisons
    years = set()
    for inp in inputs:
      for d in inp.datasets:
        t = d.vars[0].getaxis('time')
        for y in set(t.year):
          if sum(t.year==y) > 10: years.add(y)
    years = sorted(years)

    # Extract the data for each station,year,month.
    # Compute the diurnal means and do the plot.
    nstations = len(inputs[0].datasets)
    for i in range(nstations):
      station = inputs[0].datasets[i].station.station[0]
      for year in years:
        outfile = "%s/%s_diurnal_cycle_%s_at_%s_for_%04d%s%s.%s"%(outdir,'_'.join(d.name for d in inputs), self.fieldname, station.replace('/','^'), year, self.suffix, self.end_suffix, self.image_format)
        if exists(outfile): continue
        fig = pl.figure(figsize=(10,10))
        title = "%s diurnal cycle at %s (%04d)"%(self.fieldname,station,year)
        # Fix issue with certain characters in station names
        title = title.decode('latin-1')
        pl.suptitle (title, fontsize=18)
        for month, month_string in long_monthnames:
          if month <= 6: plotnum = 2*month-1
          else: plotnum = 2*(month-6)
          pl.subplot(6,2,plotnum)
          pl.title(month_string)

          for inp in inputs:
            data = inp.datasets[i][self.fieldname](station=station)(year=year,month=month).squeeze()
            if len(data.axes) == 0: continue
            hours, data, std = self.compute_diurnal_mean_stddev(data)
            pl.plot(hours, data, color=inp.color, linestyle=inp.linestyle, linewidth=2, marker=inp.marker, markersize=10, markeredgecolor=inp.color, label=inp.title)
            if inp.std_style == 'lines':
              pl.plot(hours, data+std, color=inp.color, linestyle='--')
              pl.plot(hours, data-std, color=inp.color, linestyle='--')

            if inp.std_style == 'shade':
              pl.fill_between(hours, data-std, data+std, color=inp.color, alpha=0.2, linewidth=0)
          hourticks = range(0,26,2)
          if plotnum in (11,12):
            pl.xticks(hourticks)
            pl.xlabel('hour')
          else:
            pl.xticks(hourticks,['']*len(hourticks))
          pl.xlim(0,24)
          if plotnum%2 == 1:
            pl.ylabel('[%s]'%self.units)
          # Don't use matplotlib's axis label offset (looks ugly).
          # http://stackoverflow.com/questions/24171064/matplotlib-remove-axis-label-offset-by-default
          pl.gca().get_yaxis().get_major_formatter().set_useOffset(False)
        fig.savefig(outfile)
        pl.close(fig)

from . import table
table['diurnal-cycle'] = DiurnalCycle

