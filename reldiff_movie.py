#!/usr/bin/env python

conversion_factor = {'CO2':1E-3*28.97/12.01, 'CH4':28.97/16.04, 'TCO':28.97/28.010}
rename = {'TCO':'CO'}

from argparse import ArgumentParser
parser = ArgumentParser(description='Produces an animation of the relative difference between two experiments.')
parser.add_argument('control', help='Control data (netCDF).')
parser.add_argument('experiment', help='Experiment data (netCDF).')
parser.add_argument('outname', help='Name of the movie file to generate.')
parser.add_argument('--fps', default=25, type=int, help='Frames per second for the movie.  Default is %(default)s.')
parser.add_argument('--bitrate', default=1000, type=int, help='Frames per second for the movie.  Default is %(default)s.')
args = parser.parse_args()

try:
  import xarray
  import dask
  import fstd2nc
except ImportError:
  parser.error("You need to run the following command before using the script:\n\n. ssmuse-sh -p eccc/crd/ccmr/EC-CAS/master/fstd2nc_0.20180821.0\n")

import numpy as np
from matplotlib import pyplot as pl
from matplotlib import animation as an

# Ignore numpy warnings about things like invalid values (such as NaN).
import warnings
warnings.simplefilter("ignore")

control = xarray.open_dataset(args.control,chunks={'time':1})
experiment = xarray.open_dataset(args.experiment,chunks={'time':1})

# Get a minimal label for the control and experiment
# (part of filename that is unique).
from os.path import basename, splitext
control_name = splitext(basename(args.control))[0].split('_')
experiment_name = splitext(basename(args.experiment))[0].split('_')
i = -1
while control_name[i] == experiment_name[i]:
  i = i - 1
diag_type = ' '.join(control_name[i+1:])
control_name = '_'.join(control_name[:i+1])
experiment_name = '_'.join(experiment_name[:i+1])

# Find common timesteps between the experiments.
times = np.intersect1d(control.coords['time'], experiment.coords['time'])
control = control.sel(time=times)
experiment = experiment.sel(time=times)

# Loop over each tracer, produce a movie.
for tracer in control.data_vars.keys():
  if tracer not in experiment.data_vars: continue
  conversion = conversion_factor.get(tracer,1.0)
  data1 = control.data_vars[tracer] * conversion
  data2 = experiment.data_vars[tracer] * conversion
  reldiff = (data2-data1)/data1 * 100

  fig = pl.figure(figsize=(12,6))
  pl.suptitle(rename.get(tracer,tracer)+' '+diag_type,fontsize=16)
  frame1 = data1.isel(time=-1).plot(ax=pl.subplot(131),robust=True)
  cbar1 = fig.axes[-1]
  frame2 = data2.isel(time=-1).plot(ax=pl.subplot(132),robust=True)
  # Use same colorbar range for control and experiment.
  frame2.set_clim(frame1.get_clim())
  cbar2 = fig.axes[-1]
  frame3 = reldiff.isel(time=-1).plot(ax=pl.subplot(133),robust=True,cmap='RdBu_r',center=0.0)
  cbar3 = fig.axes[-1]
  # Adjust vertical scale for pressure levels.
  if 'pres' in control.dims:
    for frame in frame1, frame2, frame3:
      frame.axes.set_ylim(frame.axes.get_ylim()[::-1])
      if min(control.coords['pres']) <= 100:
        frame.axes.set_yscale('log')
  # Remove some labels to save space.
  cbar1.set_ylabel('')
  cbar2.set_ylabel('')
  cbar3.set_ylabel('')
  frame2.axes.get_yaxis().set_visible(False)
  frame3.axes.get_yaxis().set_visible(False)
  frame1.axes.set_title('')
  frame2.axes.set_title('')
  # Label the frames.
  frame1.axes.set_xlabel(control_name)
  frame2.axes.set_xlabel(experiment_name)
  frame3.axes.set_xlabel('relative diff (%)')
  # Remove excess whitespace.
  pl.tight_layout()

  movie = an.writers['avconv'](fps=args.fps, bitrate=args.bitrate, metadata={'comment':str(args)})
  outfile = args.outname+'_'+tracer+'.avi'
  with movie.saving(fig, outfile, 72):
    for i in fstd2nc.mixins._ProgressBar("Saving "+outfile, suffix='%(percent)d%% [%(myeta)s]').iter(range(control.dims['time'])):
      # Get date and time as formatted string.
      time = str(control.coords['time'].values[i])
      time = time[:10] + ' ' + time[11:16]
      frame3.axes.set_title(time)

      # Get the values for this frame.
      d1 = data1.isel(time=i).values.flatten()
      d1 = np.ma.masked_invalid(d1)
      frame1.set_array(d1)
      d2 = data2.isel(time=i).values.flatten()
      d2 = np.ma.masked_invalid(d2)
      frame2.set_array(d2)
      d3 = reldiff.isel(time=i).values.flatten()
      d3 = np.ma.masked_invalid(d3)
      frame3.set_array(d3)

      # Write this frame to the movie.
      movie.grab_frame()

