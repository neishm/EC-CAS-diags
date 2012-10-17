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
from model_stuff import Experiment
experiment = Experiment(experiment_dir, name=experiment_name, title=experiment_title)
if control_dir is not None:
  control = Experiment(control_dir, name=control_name, title=control_title)
else:
  control = None

# Dump the output files to a subdirectory of the experiment data
from os.path import exists
from os import mkdir
outdir = experiment_dir+"/diags"
if not exists(outdir):
  mkdir(outdir)

# Some obs data that's needed by certain diagnostics
from ec_to_nc import ec_to_nc
ec_to_nc()

# Some standard diagnostics
failures = []

# Timeseries
try:
  from timeseries import timeseries
  timeseries (show=False, experiment=experiment, control=control, outdir=outdir)
except Exception as e:
  failures.append(['timeseries', e])

# Zonal mean movies
try:
  from movie_zonal import movie_zonal
  movie_zonal(gemfield = 'CO2', ctfield = 'co2', offset =    0, experiment=experiment, control=control, outdir=outdir)
  movie_zonal(gemfield = 'CLA', ctfield = 'bio', offset = -100, experiment=experiment, control=control, outdir=outdir)
except Exception as e:
  failures.append(['movie_zonal', e])

# Count of CO2 'holes'
try:
  from where_holes import where_holes
  where_holes (experiment=experiment, outdir=outdir)
except Exception as e:
  failures.append(['where_holes', e])

# KT sensitivity check
try:
  from shortexper_diffcheck import shortexper_diffcheck
  shortexper_diffcheck (experiment=experiment, control=control, location="Toronto", outdir=outdir)
except Exception as e:
  failures.append(['diffcheck', e])

# XCO2
try:
  from xco2 import xco2
  xco2 (experiment=experiment, control=control, outdir=outdir)
except Exception as e:
  failures.append(['xco2', e])

# Total mass CO2
try:
  from totalmass import totalmass
  totalmass (experiment=experiment, control=control, outdir=outdir)
except Exception as e:
  failures.append(['totalmass', e])

# Report any diagnostics that failed to run
if len(failures) > 0:
  print "WARNING:"
  print "The following diagnostics failed to run:"
  for diag, e in failures:
    print "%s: %s"%(diag,e)

