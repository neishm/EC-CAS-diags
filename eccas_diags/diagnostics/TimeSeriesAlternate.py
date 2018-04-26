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


# timeseries with difference plot


from .timeseries import Timeseries
class TimeseriesDiff(Timeseries):
  """
  Difference between two datasets, sampled at obs locations.
  """
  def __init__ (self, stat=None, **kwargs):
    import numpy as np
    super(TimeseriesDiff,self).__init__(**kwargs)
    self.stat = stat
    if stat is not None:
      end_suffix = self.end_suffix.split('_')
      end_suffix.append(stat)
      self.end_suffix = '_'.join(end_suffix)

  def do (self, inputs):
    import numpy as np
    import matplotlib.pyplot as pl
    from os.path import exists
    import math
    from os import makedirs
    from ..common import detect_gaps, to_datetimes
    from collections import OrderedDict
    from datetime import datetime

    figwidth = 15

    #Format image directory
    outdir = self.outdir + '/TimeSeriesAlternate-images_%s_%s%s'%('_'.join(d.name for d in inputs),self.fieldname,self.suffix)
    if not exists(outdir): makedirs(outdir)

    # Create plots of each location
    # Plot 4 timeseries per figure
    n = 4

    # Get global time axis range for the data (in relative units).
    # Needed for calculating marker size.
    time1 = min(d.time.values[0] for inp in inputs for d in inp.datasets if len(d.time) > 0)
    time2 = max(d.time.values[-1] for inp in inputs for d in inp.datasets if len(d.time) > 0)
    # Get global date range for the data (as datetime objects).
    # Needed for forcing the scale of the plot.
    mindate = min(to_datetimes(d.time)[0] for inp in inputs for d in inp.datasets if len(d.time) > 0)
    maxdate = max(to_datetimes(d.time)[-1] for inp in inputs for d in inp.datasets if len(d.time) > 0)

    # Loop over individual stations
    nstations = len(inputs[0].datasets)
    for i in range(nstations):

      if self.stations is None:
        fig_id = '%02d'%(i/n+1)
      else:
        fig_id = ','.join(inputs[0].datasets[j].vars[0].station[0] for j in range(i,min(i+n,nstations)))
      outfile = "%s/%s_timeseries_%s_%s%s.%s"%(outdir,'_'.join(d.name for d in inputs),self.fieldname,fig_id,self.suffix+self.end_suffix,self.image_format)

      # Skip plots that have already been generated.
      if exists(outfile): continue

      station_axis = inputs[0].datasets[i].vars[0].station
      assert len(station_axis) == 1, "Unable to handle multi-station datasets"
      location = station_axis.station[0]

      if i%n == 0:
        fig = pl.figure(figsize=(figwidth,12))
      pl.subplot(n,1,i%n+1)
      station_info = station_axis(station=location)
      lat = station_info.lat[0]
      lon = station_info.lon[0]

      # Construct a title for the plot
      title = location + ' - (%4.2f'%abs(lat)
      if lat < 0: title += 'S'
      else: title += 'N'
      title += ',%5.2f'%abs(lon)
      if lon < 0: title += 'W'
      else: title += 'E'
      title += ')'
      if hasattr(station_info,'country'):
        title += ' - ' + station_info.country[0]

      # Fix issue with certain characters in station names
      title = title.decode('latin-1')

      # Loop over each product, and plot the data for this location.
      model_times = []  # Store for difference plots after.
      model_values = []
      # Don't plot the data for the monthly stats variant.
      do_plot = (self.stat!='monthly')

      for j,inp in enumerate(inputs):

        var = inp.datasets[i][self.fieldname]
        # Check for missing data (so we don't connect this region with a line)
        var = detect_gaps(var)

        dates = to_datetimes(var.time)

        values = var.get().flatten()

        # Determine marker size based on the density of observations
        timevalues = var.time.values
        timevalues = timevalues[np.isfinite(values)]
        dt = filter(None,np.diff(timevalues))
        if len(dt) > 0:
          # Choose a representative dt.
          dt = sorted(dt)[len(dt)/2]
        else:
          dt = float('nan')
        count = (time2-time1) / dt
        # Size of marker (in points) for roughly no overlap
        markersize = figwidth * 72.0 / count
        markersize = max(markersize,1.0)
        markersize = min(markersize,10.0)
        if np.isnan(markersize):
          markersize = 1.0

        # Draw standard deviation?
        for errname in (self.fieldname+'_std', self.fieldname+'_uncertainty'):
         if errname in inp.datasets[i]:
          std = detect_gaps(inp.datasets[i][errname]).get().flatten()
          fill_min = values - 2*std
          fill_max = values + 2*std
          fill_mask = np.isfinite(fill_max)
          if inp.std_style == 'lines':
            if do_plot:
              pl.plot(dates, fill_min, color=inp.color, linestyle='--')
              pl.plot(dates, fill_max, color=inp.color, linestyle='--')
          if inp.std_style == 'shade':
            if do_plot:
              pl.fill_between(dates, fill_min, fill_max, where=fill_mask, color=inp.color, linewidth=0, alpha=0.5)

        # Store some data for the difference plots further below.
        if j == len(inputs)-1:
          obs_times = var.time
          obs_values = values
        else:
          model_times.append(var.time)
          model_values.append(values)

        # Plot the timeseries
        if do_plot:
          pl.plot(dates, values, color=inp.color, linestyle=inp.linestyle, marker=inp.marker, markersize=markersize, markeredgecolor=inp.color)

      # Work around issue where pyplot autoscale ignores points with missing
      # data.
      pl.xlim(mindate,maxdate)

      pl.title(title)
      pl.ylabel('%s %s'%(self.fieldname,self.units))

      # ----- start of difference plot -----
      TimesAx = to_datetimes(obs_times)
      if self.stat != 'monthly':
        pl.twinx()
      # First, need to get the original axis lines in the legend.
      # (adapted from http://stackoverflow.com/a/23647410)
      # Note: no longer works in more recent matplotlib.  This somehow extends
      # the beginning of the time axis to the year 2000??
      #for inp in inputs:
        #pl.plot(np.nan, color=inp.color, linestyle=inp.linestyle, marker=inp.marker, markersize=markersize, markeredgecolor=inp.color)

      # Now, can plot the difference plots.
      for j,inp in enumerate(inputs[:-1]):
        model_interp = np.interp(obs_times.values,model_times[j].values,model_values[j])    #Interpolate model data to those points for comparison

        #------Difference Plot------
        Difference = model_interp-obs_values    #Difference data

#      # Determine Mean and Max difference, and standard deviation
#      if sum(~np.isnan(Difference)) > 0:
#        DiffMean = np.mean(Difference[~np.isnan(Difference)])
#        DiffStd = np.std(Difference[~np.isnan(Difference)])
#        pl.text(.01,.9,'Mean Difference: %s | Max Difference: %s'%(round(DiffMean,1),round(np.nanmax(Difference),1)),size=11)
#        pl.text(.01,.82,'Difference Std: %s'%(round(DiffStd,1)),size=11)

        # Difference plot
        if self.stat is None:
          pl.plot(TimesAx,Difference, color=inp.color, alpha=0.3, label=inp.title+" bias")

        elif self.stat == 'monthly':
          # Compute monthly statistics?
          #monthly = pandas.Series(Difference,TimesAx).resample('M',how=('mean','std','count'),loffset='15D')
          month_bins = OrderedDict()
          for t,v in zip(TimesAx,Difference):
            if not np.isfinite(v): continue
            month_bins.setdefault(datetime(t.year,t.month,15),[]).append(v)
          months = list(month_bins.keys())
          values = list(map(np.mean,month_bins.values()))
          counts = list(map(len,month_bins.values()))
          std = list(map(np.std,month_bins.values()))
          if len(months) > 0:
            pl.errorbar(months, values, yerr=std, marker='o', markersize=10, capsize=10, linestyle='none', color=inp.color, markeredgecolor=inp.color, alpha=1.0, label=inp.title+" bias")
            # Label the number of data points on one of the plots.
            if j == 0:
              for month, value, count in zip(months,values,counts):
                pl.text(month, value, "   "+str(count), horizontalalignment='left', verticalalignment='center')

      #Black baseline representing x = 0 line for difference
      times = to_datetimes(model_times[0])
      times = [times[0], times[-1]]
      pl.plot(times, [0,0], color='black')

#      #Temporary lines for context (testing)
#      pl.plot(times,[10,10],color='black',alpha=.25)
#      pl.plot(times,[-10,-10],color='black',alpha=.25)

      # ----- end of difference plot -----

      # Things to do on the last plot of the figure
      if i%n == (n-1) or i == nstations-1:
        # Put a legend on the last plot
        pl.legend(prop={'size':11})

        pl.tight_layout()

        # Save as an image file.
        fig.savefig(outfile)

        pl.close(fig)

from . import table
table['timeseries-diff'] = TimeseriesDiff

