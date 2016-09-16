# Timeseries diagnostic

from . import TimeVaryingDiagnostic, ImageDiagnostic
from .station import StationComparison
class Timeseries(TimeVaryingDiagnostic,ImageDiagnostic,StationComparison):
  """
  Sample data at surface obs locations, and plot the result as a 1D line plot.
  """
  # Further modify the station sampling logic to select only surface level
  # (and cache the data).
  def _transform_inputs (self, inputs):
    from ..common import find_and_convert, convert, detect_gaps, fix_timeaxis
    from ..interfaces import DerivedProduct
    from pygeode.timeutils import reltime
    inputs = super(Timeseries,self)._transform_inputs(inputs)

    # First, need consistent time axis values across all inputs.
    inputs = [DerivedProduct(map(fix_timeaxis,inp), source=inp) for inp in inputs]

    fieldname = self.fieldname
    units = self.units
    suffix = self.suffix
    models = inputs[:-1]
    obs = inputs[-1]
    # Cache the model data
    # Use the first model timeaxis as the range for plotting.
    timeaxis = None
    cached_models = []
    for m in models:
      datasets = []
      # Assuming obs and models have 1:1 mapping of datasets
      # (should be the case for the current implementation of
      # StationComparison, which we're deriving from).
      for md in m.datasets:
        field = md[fieldname]
        field = convert(field, units)

        # Apply time axis subsetting, but only if start or end are unspecified.
        if timeaxis is None:
          timeaxis = field.getaxis('time')

        start, end = self.date_range

        if start is None:
          start = timeaxis.values[0]
        else:
          start = timeaxis.str_as_val(key=None,s=start.strftime("%d %b %Y"))

        if end is None:
          end = timeaxis.values[-1]
        else:
          end = timeaxis.str_as_val(key=None,s=end.strftime("%d %b %Y"))

        field = field(time=(start,end))

        # Cache the data for faster subsequent access.
        # Disable time splitting for the cache file, since open_multi doesn't work
        # very well with the encoded station data.
        # Only cache if we have some data in this time period.
        if len(field.time) > 0:
          field = m.cache.write(field, prefix=m.name+'_at_%s_%s%s'%(obs.name,field.name,suffix), split_time=False, suffix=self.end_suffix)
        # Check for missing data (so we don't connect this region with a line)
        field = detect_gaps(field)
        datasets.append(Dataset([field]))
      m = DerivedProduct(datasets, source=m)
      cached_models.append(m)

    # Cache the obs data
    datasets = []
    for od in obs.datasets:
      varlist = []

      # Cached the obs values and std. deviation (if it exists)
      for errname in (fieldname, fieldname+'_std', fieldname+'_uncertainty'):
        if errname in od:
          field = od[errname]
          field = convert(field, units, context=fieldname)
          field = field(time=(start,end))
          # Cache obs data, but only  if we have some data in this time range.
          if len(field.time) > 0:
            field = obs.cache.write(field, prefix=obs.name+'_sfc_%s%s'%(errname,suffix), split_time=False, suffix=self.end_suffix)
        varlist.append(field)

      datasets.append(Dataset(varlist))
    cached_obs = DerivedProduct(datasets, source=obs)

    return list(cached_models)+[cached_obs]

  def do (self, inputs):
    import numpy as np
    import matplotlib.pyplot as pl
    from os.path import exists
    from ..common import to_datetimes

    figwidth = 15

    # Create plots of each location
    # Plot 4 timeseries per figure
    n = 4
    station_axis = inputs[0].datasets[0].vars[0].station
    time1 = inputs[0].datasets[0].vars[0].time.values[0]
    time2 = inputs[0].datasets[0].vars[0].time.values[-1]
    for i,location in enumerate(station_axis.values):

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

      mindate = maxdate = None
      for inp in inputs:
        var = inp.find_best(self.fieldname)
        dates = to_datetimes(var.time)
        # Keep track of min/max date range. (To force it at the end of this
        # iteration)
        if mindate is None: mindate = dates[0]
        if maxdate is None: maxdate = dates[-1]
        mindate = min(mindate,dates[0])
        maxdate = max(maxdate,dates[0])

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

        # Plot the timeseries
        pl.plot(dates, values, color=inp.color, linestyle=inp.linestyle, marker=inp.marker, markersize=markersize, markeredgecolor=inp.color)
        # Work around issue where pyplot autoscale ignores points with missing
        # data.
        pl.xlim(mindate,maxdate)

      pl.title(title)
      pl.ylabel('%s %s'%(self.fieldname,self.units))

      # Things to do on the last plot of the figure
      if i%n == (n-1) or i == len(station_axis)-1:
        # Put a legend on the last plot
        labels = [d.title for d in inputs]
        pl.legend(labels)

        pl.tight_layout()

        # Save as an image file.
        fig_id = '%02d'%(i/n+1)
        outfile = "%s/%s_timeseries_%s_%s%s.%s"%(self.outdir,'_'.join(d.name for d in inputs),self.fieldname,fig_id,self.suffix+self.end_suffix,self.image_format)
        if not exists(outfile):
          fig.savefig(outfile)

        pl.close(fig)

from . import table
table['timeseries'] = Timeseries

