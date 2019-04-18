#!/usr/bin/env python

conversion_factor = {'CO2':1E-3*28.97/12.01, 'CH4':28.97/16.04, 'TCO':28.97/28.010}
rename = {'TCO':'CO'}

from argparse import ArgumentParser
parser = ArgumentParser(description='Produces an animation of the relative difference between two experiments.')
parser.add_argument('control', help='Control data (netCDF).')
parser.add_argument('experiment', help='Experiment data (netCDF).')
parser.add_argument('outname', help='Name of the movie file to generate.')
parser.add_argument('--fps', default=25, type=int, help='Frames per second for the movie.  Default is %(default)s.')
parser.add_argument('--bitrate', default=8000, type=int, help='Frames per second for the movie.  Default is %(default)s.')
args = parser.parse_args()

# Add paths to locally installed packages.
import sys
sys.path.append('/fs/ssm/eccc/crd/ccmr/EC-CAS/master/basemap_1.0.7rel_ubuntu-14.04-amd64-64/lib/python')

try:
  import xarray
  import dask
  import fstd2nc
except ImportError:
  parser.error("You need to run the following command before using the script:\n\n. ssmuse-sh -p eccc/crd/ccmr/EC-CAS/master/fstd2nc_0.20180821.0\n")

import numpy as np
from matplotlib import pyplot as pl
from matplotlib import animation as an
from mpl_toolkits.basemap import Basemap

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

  rect = (0,0,1,1) # Rectangle of visible area (for tight_layout)

  if 'lat' in control.dims and 'lon' in control.dims:
    fig = pl.figure(figsize=(8,10))
    def set_title(title):
      frame1.axes.set_title(rename.get(tracer,tracer)+' '+diag_type+' - '+title)
      frame2.axes.set_title('')
      frame3.axes.set_title('')
    # Set up frames, with map background.
    ax = pl.subplot(311)
    m = Basemap(projection='cyl', llcrnrlat=-90, urcrnrlat=90, llcrnrlon=0, urcrnrlon=360, ax=ax)
    m.drawcoastlines()
    m.drawparallels(np.arange(-60.,61.,30.),labels=[True,False,False,False])
    m.drawmeridians(np.arange(0,361.,60.))
    frame1 = data1.isel(time=-1).plot(ax=ax,robust=True)
    fig.axes[-1].set_ylabel('\n'+control_name) # Add label to colorbar.
    ax = pl.subplot(312)
    m = Basemap(projection='cyl', llcrnrlat=-90, urcrnrlat=90, llcrnrlon=0, urcrnrlon=360, ax=ax)
    m.drawcoastlines()
    m.drawparallels(np.arange(-60.,61.,30.),labels=[True,False,False,False])
    m.drawmeridians(np.arange(0,361.,60.))
    frame2 = data2.isel(time=-1).plot(ax=ax,robust=True)
    fig.axes[-1].set_ylabel('\n'+experiment_name)  # Add label to colorbar.
    ax = pl.subplot(313)
    m = Basemap(projection='cyl', llcrnrlat=-90, urcrnrlat=90, llcrnrlon=0, urcrnrlon=360, ax=ax)
    m.drawcoastlines()
    m.drawparallels(np.arange(-60.,61.,30.),labels=[True,False,False,False])
    m.drawmeridians(np.arange(0,361.,60.),labels=[False,False,False,True])
    frame3 = reldiff.isel(time=-1).plot(ax=ax,robust=True,cmap='RdBu_r',center=0.0)
    fig.axes[-1].set_ylabel('\nrelative diff (%)')  # Add label to colorbar.
    # Remove some labels that were generated by xarray.
    frame1.axes.set_xlabel('')
    frame2.axes.set_xlabel('')
    frame3.axes.set_xlabel('')
    frame1.axes.set_ylabel('')
    frame2.axes.set_ylabel('')
    frame3.axes.set_ylabel('')
    # Adjust layout to avoid cutting off lat/lon labels.
    rect=(0.02,0.02,1.02,1)
  else:
    fig = pl.figure(figsize=(12,6))
    pl.suptitle(rename.get(tracer,tracer)+' '+diag_type,fontsize=16)
    def set_title(title):
      frame1.axes.set_title('')
      frame2.axes.set_title('')
      frame3.axes.set_title(title)
    frame1 = data1.isel(time=-1).plot(ax=pl.subplot(131),robust=True)
    fig.axes[-1].set_ylabel('')  # Remove label on colorbar
    frame2 = data2.isel(time=-1).plot(ax=pl.subplot(132),robust=True)
    fig.axes[-1].set_ylabel('')  # Remove label on colorbar
    frame3 = reldiff.isel(time=-1).plot(ax=pl.subplot(133),robust=True,cmap='RdBu_r',center=0.0)
    fig.axes[-1].set_ylabel('')  # Remove label on colorbar
    # Remove some labels to save space.
    frame2.axes.get_yaxis().set_visible(False)
    frame3.axes.get_yaxis().set_visible(False)
    # Label the frames.
    frame1.axes.set_xlabel(control_name)
    frame2.axes.set_xlabel(experiment_name)
    frame3.axes.set_xlabel('relative diff (%)')

  # Use same colorbar range for control and experiment.
  frame2.set_clim(frame1.get_clim())

  # Adjust vertical scale for pressure levels.
  if 'pres' in control.dims:
    for frame in frame1, frame2, frame3:
      frame.axes.set_ylim(frame.axes.get_ylim()[::-1])
      if min(control.coords['pres']) <= 100:
        frame.axes.set_yscale('log')

  # Set a dummy title to reserve space in the layout.
  set_title('title')

  # Remove excess whitespace.
  pl.tight_layout(rect=rect)

  movie = an.writers['avconv'](fps=args.fps, bitrate=args.bitrate, metadata={'comment':str(args)})
  outfile = args.outname+'_'+tracer+'.avi'
  print ("Saving "+outfile)
  with movie.saving(fig, outfile, 72):
    for i in fstd2nc.mixins._ProgressBar("",suffix='%(percent)d%% [%(myeta)s]').iter(range(control.dims['time'])):
      # Get date and time as formatted string.
      time = str(control.coords['time'].values[i])
      time = time[:10] + ' ' + time[11:16]
      set_title(time)

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

