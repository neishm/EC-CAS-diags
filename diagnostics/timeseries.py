# Timeseries diagnostic

from . import TimeVaryingDiagnostic, ImageDiagnostic
from .station import StationComparison
class Timeseries(StationComparison,TimeVaryingDiagnostic,ImageDiagnostic):
  """
  Sample data at surface obs locations, and plot the result as a 1D line plot.
  """
  # Select a common time period for the data products, and convert to the
  # right units.  Also, pick out the field of interest.
  def _transform_inputs (self, inputs):
    from ..common import find_and_convert, convert, detect_gaps, fix_timeaxis
    from ..interfaces import DerivedProduct
    from pygeode.timeutils import reltime
    from pygeode.dataset import Dataset
    inputs = super(Timeseries,self)._transform_inputs(inputs)

    # First, need consistent time axis values across all inputs.
    inputs = [DerivedProduct(map(fix_timeaxis,inp), source=inp) for inp in inputs]

    fieldname = self.fieldname
    units = self.units
    suffix = self.suffix
    models = inputs[:-1]
    obs = inputs[-1]
    # Get common time period for model data.
    # Use the first model timeaxis as the range for plotting.
    timeaxis = None
    out_models = []
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

        # Check for missing data (so we don't connect this region with a line)
        field = detect_gaps(field)
        datasets.append(Dataset([field]))
      m = DerivedProduct(datasets, source=m)
      out_models.append(m)

    # Subset the obs times.
    datasets = []
    for od in obs.datasets:
      varlist = []

      for varname in (fieldname, fieldname+'_std', fieldname+'_uncertainty'):
        if varname in od:
          field = od[varname]
          field = convert(field, units, context=fieldname)
          field = field(time=(start,end))
        varlist.append(field)

      datasets.append(Dataset(varlist))
    out_obs = DerivedProduct(datasets, source=obs)

    return list(out_models)+[out_obs]

  def do (self, inputs):
    import numpy as np
    import matplotlib.pyplot as pl
    from os.path import exists
    from ..common import to_datetimes

    figwidth = 15

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
      for inp in inputs:
        var = inp.datasets[i][self.fieldname]
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
          std = inp.datasets[i][errname].get().flatten()
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
      if i%n == (n-1) or i == nstations-1:
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

