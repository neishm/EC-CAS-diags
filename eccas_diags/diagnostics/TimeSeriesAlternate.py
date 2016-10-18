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
  def do (self, inputs):
    import numpy as np
    import matplotlib.pyplot as pl
    from os.path import exists
    import math
    from os import makedirs
    from ..common import detect_gaps, to_datetimes

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
            pl.plot(dates, fill_min, color=inp.color, linestyle='--')
            pl.plot(dates, fill_max, color=inp.color, linestyle='--')
          if inp.std_style == 'shade':
            pl.fill_between(dates, fill_min, fill_max, where=fill_mask, color=inp.color, linewidth=0, alpha=0.5)

        # Store some data for the difference plots further below.
        if j == 0:
          model_times = var.time
          model_values = values
        if j == len(inputs)-1:
          obs_times = var.time
          obs_values = values

        # Plot the timeseries
        pl.plot(dates, values, color=inp.color, linestyle=inp.linestyle, marker=inp.marker, markersize=markersize, markeredgecolor=inp.color)
        # Work around issue where pyplot autoscale ignores points with missing
        # data.
        pl.xlim(mindate,maxdate)

      pl.title(title)
      pl.ylabel('%s %s'%(self.fieldname,self.units))

      # ----- start of difference plot -----
      model_interp = np.interp(obs_times.values,model_times.values,model_values)    #Interpolate model data to those points for comparison

      #------Difference Plot------
      Difference = obs_values-model_interp    #Difference data

      TimesAx = to_datetimes(obs_times)

      # Determine Mean and Max difference, and standard deviation
      if sum(~np.isnan(Difference)) > 0:
        DiffMean = np.mean(Difference[~np.isnan(Difference)])
        DiffStd = np.std(Difference[~np.isnan(Difference)])
        pl.text(.01,.9,'Mean Difference: %s | Max Difference: %s'%(round(DiffMean,1),round(np.nanmax(Difference),1)),size=11)
        pl.text(.01,.82,'Difference Std: %s'%(round(DiffStd,1)),size=11)

      # Difference plot
      pl.twinx()
      # First, need to get the original axis lines in the legend.
      # (adapted from http://stackoverflow.com/a/23647410)
      for inp in inputs:
        pl.plot(np.nan, color=inp.color, linestyle=inp.linestyle, marker=inp.marker, markersize=markersize, markeredgecolor=inp.color)

      # Now, can plot the difference plot.
      pl.plot(TimesAx,Difference,color='magenta')

      #Black baseline representing x = 0 line for difference
      times = to_datetimes(model_times)
      times = [times[0], times[-1]]
      pl.plot(times, [0,0], color='black')

      #Temporary lines for context (testing)
      pl.plot(times,[10,10],color='black',alpha=.25)
      pl.plot(times,[-10,-10],color='black',alpha=.25)

      # ----- end of difference plot -----

      # Things to do on the last plot of the figure
      if i%n == (n-1) or i == nstations-1:
        # Put a legend on the last plot
        labels = [d.title for d in inputs]
        labels.append('Difference')
        pl.legend(labels, prop={'size':11})

        pl.tight_layout()

        # Save as an image file.
        fig.savefig(outfile)

        pl.close(fig)

from . import table
table['timeseries-diff'] = TimeseriesDiff

