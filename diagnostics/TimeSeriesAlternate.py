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
    from ..common import to_datetimes

    figwidth = 15

    #Format image directory
    outdir = self.outdir + '/TimeSeriesAlternate-images_%s_%s%s'%('_'.join(d.name for d in inputs),self.fieldname,self.suffix)
    if not exists(outdir): makedirs(outdir)

    # Create plots of each location
    # Plot 4 timeseries per figure
    n = 4
    station_axis = inputs[0].datasets[0].vars[0].station
    time1 = inputs[0].datasets[0].vars[0].time.values[0]
    time2 = inputs[0].datasets[0].vars[0].time.values[-1]
    for i,location in enumerate(station_axis.values):

      if i%n == 0:
        fig = pl.figure(figsize=(figwidth,12))
        stations_on_figure = []
      pl.subplot(n,1,i%n+1)
      station_info = station_axis(station=location)
      lat = station_info.lat[0]
      lon = station_info.lon[0]

      if self.stations is not None:
        s = self._lookup_station(location)
        stations_on_figure.append(s)

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
      for j,inp in enumerate(inputs):
        var = inp.find_best(self.fieldname)
        dates = to_datetimes(var.time)
        values = var.get(station=location).flatten()

        # Determine marker size based on the density of observations
        timevalues = var(station=location).time.values
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
        if inp.have(self.fieldname+'_std'):
          std = inp.find_best(self.fieldname+'_std').get(station=location).flatten()
          fill_min = values - 2*std
          fill_max = values + 2*std
          fill_mask = np.isfinite(fill_max)
          if inp.std_style == 'lines':
            pl.plot(dates, fill_min, color=inp.color, linestyle='--')
            pl.plot(dates, fill_max, color=inp.color, linestyle='--')
          if inp.std_style == 'shade':
            pl.fill_between(dates, fill_min, fill_max, where=fill_mask, color=inp.color, linewidth=0, alpha=0.5)

        # Store some data for the difference plots further below.
        if j == len(inputs)-1:
          obs_times = var.time
          obs_values = values
        else:
          model_times.append(var.time)
          model_values.append(values)

        # Plot the timeseries
        pl.plot(dates, values, color=inp.color, linestyle=inp.linestyle, marker=inp.marker, markersize=markersize, markeredgecolor=inp.color)

      pl.title(title)
      pl.ylabel('%s %s'%(self.fieldname,self.units))

      # ----- start of difference plot -----
      TimesAx = to_datetimes(obs_times)
      pl.twinx()
      # First, need to get the original axis lines in the legend.
      # (adapted from http://stackoverflow.com/a/23647410)
      for inp in inputs:
        pl.plot(np.nan, color=inp.color, linestyle=inp.linestyle, marker=inp.marker, markersize=markersize, markeredgecolor=inp.color)

      # Now, can plot the difference plots.
      for j,inp in enumerate(inputs[:-1]):
        model_interp = np.interp(obs_times.values,model_times[j].values,model_values[j])    #Interpolate model data to those points for comparison

        #------Difference Plot------
        Difference = obs_values-model_interp    #Difference data

#      # Determine Mean and Max difference, and standard deviation
#      if sum(~np.isnan(Difference)) > 0:
#        DiffMean = np.mean(Difference[~np.isnan(Difference)])
#        DiffStd = np.std(Difference[~np.isnan(Difference)])
#        pl.text(.01,.9,'Mean Difference: %s | Max Difference: %s'%(round(DiffMean,1),round(np.nanmax(Difference),1)),size=11)
#        pl.text(.01,.82,'Difference Std: %s'%(round(DiffStd,1)),size=11)

        # Difference plot
        pl.plot(TimesAx,Difference, color=inp.color, alpha=0.3)

      #Black baseline representing x = 0 line for difference
      times = to_datetimes(model_times[0])
      times = [times[0], times[-1]]
      pl.plot(times, [0,0], color='black')

#      #Temporary lines for context (testing)
#      pl.plot(times,[10,10],color='black',alpha=.25)
#      pl.plot(times,[-10,-10],color='black',alpha=.25)

      # ----- end of difference plot -----

      # Things to do on the last plot of the figure
      if i%n == (n-1) or i == len(station_axis)-1:
        # Put a legend on the last plot
        labels = [d.title for d in inputs] + ["obs - "+d.name for d in inputs[:-1]]
        pl.legend(labels, prop={'size':11})

        pl.tight_layout()

        # Save as an image file.
        if self.stations is not None:
          fig_id = ','.join(stations_on_figure)
        else:
          fig_id = '%02d'%(i/n+1)
        outfile = "%s/%s_timeseries_%s_%s%s.%s"%(outdir,'_'.join(d.name for d in inputs),self.fieldname,fig_id,self.suffix+self.end_suffix,self.image_format)
        if not exists(outfile):
          fig.savefig(outfile)

        pl.close(fig)

from . import table
table['timeseries-diff'] = TimeseriesDiff

