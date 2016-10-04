#Model vs Obs histogram

"""
It is important to note that the model histogram will consist of a full year's data
Whereas the observations may only exist for one season, causing them to look much different.
"""

from .timeseries import Timeseries
class TimeseriesHist(Timeseries):
  """
  Histogram of a field sampled at obs locations.
  """
  def do (self, inputs):
    import numpy as np
    import matplotlib.pyplot as pl
    from os.path import exists
    import math
    from os import makedirs

    figwidth = 15

    outdir = self.outdir + '/TimeSeriesHist-images_%s_%s%s'%('_'.join(d.name for d in inputs),self.fieldname,self.suffix)
    if not exists(outdir): makedirs(outdir)

    # Create plots of each location
    # Plot 4 timeseries per figure
    n = 4

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
      ax = pl.subplot(2,2,i%n+1)
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

      #Squeeze out the data (we don't need axes or anything else)
      series = [inp.datasets[i][self.fieldname].get().flatten() for inp in inputs]
      series = [s[~np.isnan(s)] for s in series]

      #Find the max and mins of the datasets, lopping off the top and bottom 1% of data (outliers throwing off graph formatting)
      Max = int(max([max(sorted(s)[:int(len(s)*.99)]) for s in series if s != []]))
      Min = int(min([min(sorted(s)[int(len(s)*.01):]) for s in series if s != []]))

      #Create bins and plot histogram
      colours = [inp.color for inp in inputs]
      pl.hist(series, color=colours, bins=range(Min,Max+1,1), lw=0)

      pl.title(title)
      pl.xlabel('%s (%s)'%(self.fieldname,self.units))
      pl.ylabel('Occurrences')

      LocalStds = 'Standard Deviations: '
      LocalMeans = 'Mean Values (ppm): '
      LocalMaxMin = 'Max/Min Values (ppm): '
      for s in series:
        if s != []:
          LocalStds += '%s | '%(str(np.round(np.std(s),1)))
          LocalMeans += '%d | '%(np.mean(s))
          LocalMaxMin += '%d/%d | '%(max(s),min(s))

      #Add statistics to each plot
      pl.text(.02,.98,LocalStds,size=11,verticalalignment='top',transform=ax.transAxes)
      pl.text(.02,.94,LocalMeans,size=11,verticalalignment='top',transform=ax.transAxes)
      pl.text(.02,.9,LocalMaxMin,size=11,verticalalignment='top',transform=ax.transAxes)

      # Things to do on the last plot of the figure
      if i%n == (n-1) or i == nstations-1:
        # Put a legend on the last plot
        labels = [d.title for d in inputs]
        pl.legend(labels,prop={'size':11})

        pl.tight_layout()    #Makes layout tighter - less clutter for 4 plots

        # Save as an image file.
        fig.savefig(outfile)

        pl.close(fig)

from . import table
table['timeseries-hist'] = TimeseriesHist

