#!/usr/bin/env python

# Do some standard diagnostics on a model run.

import argparse

# Extract command-line arguments

parser = argparse.ArgumentParser (description='Do some standard diagnostics on a model run.', epilog="You must have write perimission in the experiment directory to create some intermediate files.")
parser.add_argument('experiment', help="location of the model output")
parser.add_argument('--desc', help="short description of the experient", default="Experiment")
parser.add_argument('--control', help="location of the control run (if desired)", default=None)

args = parser.parse_args()

experiment_dir = args.experiment
if experiment_dir == ".":
  experiment_name = "unnamed_exp"
else:
  experiment_name = experiment_dir.rstrip('/').split('/')[-1]
experiment_title = "%s (%s)"%(args.desc, experiment_name)

control_dir = args.control
if control_dir is not None:
  if control_dir == ".":
    control_name = "control"
    control_title = "Control"
  else:
    control_name = control_dir.rstrip('/').split('/')[-1]
    control_title = "Control (%s)"%control_name
else:
  control_name = None
  control_title = None


# Get the data
from model_stuff import get_data
experiment = get_data(experiment_dir)
if control_dir is not None:
  control = get_data(control_dir)
else:
  control = None

# By default, dump the output files to directory of the same name as the experiment.
outdir = experiment_name

# Set up some common keyword parameters to pass to the specific diagnostics
exp_args = dict(experiment_name=experiment_name, experiment_title=experiment_title, experiment=experiment, control_name=control_name, control_title=control_title, control=control, outdir=outdir)

# Some standard diagnostics

# Timeseries
from timeseries import timeseries
timeseries (show=False, **exp_args)

# Zonal mean movies
from movie_zonal import movie_zonal
movie_zonal(gemfield = 'CO2', ctfield = 'co2', offset =    0, **exp_args)
movie_zonal(gemfield = 'CLA', ctfield = 'bio', offset = -100, **exp_args)

# Count of CO2 'holes'
from where_holes import where_holes
where_holes (**exp_args)
