#!/usr/bin/env python

# Do some standard diagnostics on a model run.

# Disable X-windows stuff
import matplotlib
matplotlib.use('Agg')

import argparse
from os.path import exists
import os

# Extract command-line arguments

parser = argparse.ArgumentParser (description='Do some standard diagnostics on a model run.', epilog="You must have write perimission in the experiment directory to create some intermediate files.")
parser.add_argument('experiment', help="Location of the model output.")
parser.add_argument('--desc', help="Short description of the experient.", default="Experiment")
parser.add_argument('--control', help="Location of the control run (if desired).", default=None)
parser.add_argument('--emissions', help="Location of the model emissions.")
parser.add_argument('--tmpdir', help="where to put any intermediate files that get generated, if they can't be stored in their usual location.  THIS SHOULD NOT BE IN YOUR HOME DIRECTORY.")

args = parser.parse_args()

experiment_dir = args.experiment
if not exists(experiment_dir):
  raise IOError ("experiment directory '%s' doesn't exist"%experiment_dir)
if experiment_dir == ".":
  experiment_name = "unnamed_exp"
else:
  experiment_name = experiment_dir.rstrip('/').split('/')[-1]
experiment_title = "%s (%s)"%(args.desc, experiment_name)
experiment_tmpdir = None
if not os.access(experiment_dir, os.R_OK | os.W_OK | os.X_OK):
  print "Can't write into experiment directory - redirecting any generated intermediate files to --tmpdir"
  assert args.tmpdir is not None, "Need --tmpdir to put intermediate files in."
  experiment_tmpdir = args.tmpdir

control_dir = args.control
if control_dir is not None:
  if not exists(control_dir):
    raise IOError ("control directory '%s' doesn't exist"%control_dir)
  if control_dir == ".":
    control_name = "control"
    control_title = "Control"
  else:
    control_name = control_dir.rstrip('/').split('/')[-1]
    control_title = "Control (%s)"%control_name
  control_tmpdir = None
  if not os.access(control_dir, os.R_OK | os.W_OK | os.X_OK):
    print "Can't write into control directory - redirecting any generated intermediate files to --tmpdir"
    assert args.tmpdir is not None, "Need --tmpdir to put intermediate files in."
    control_tmpdir = args.tmpdir
else:
  control_name = None
  control_title = None

# Check for 'model' subdirectory for experiment
rootdir = experiment_dir
if exists(experiment_dir+"/model"):
  experiment_dir += "/model"
if control_dir is not None and exists(control_dir+"/model"):
  control_dir += "/model"

# Get the data
from gem import GEM_Data
flux_dir = args.emissions
experiment = GEM_Data(experiment_dir, flux_dir=flux_dir, name=experiment_name, title=experiment_title, tmpdir=experiment_tmpdir)
if control_dir is not None:
  control = GEM_Data(control_dir, flux_dir=None, name=control_name, title=control_title, tmpdir=control_tmpdir)
else:
  control = None

# CarbonTracker data
#TODO: limit CT data to time range of experiment.
from carbontracker import CarbonTracker_Data
carbontracker = CarbonTracker_Data()

# Observation data
from ec_station_data import EC_Station_Data
ec_obs = EC_Station_Data()
from gaw_station_data import GAW_Station_Data
gaw_obs = GAW_Station_Data()


# Dump the output files to a subdirectory of the experiment data
from os import mkdir
outdir = rootdir+"/diags"
try:
  mkdir(outdir)
except OSError:
  pass   # directory already exists or can't be created

if not exists(outdir) or not os.access (outdir, os.R_OK | os.W_OK | os.X_OK):
  print "Cannot put diagnostics into %s.  Putting them in --tmpdir instead."%outdir
  assert args.tmpdir is not None, "Need --tmpdir to put diags in."
  outdir=args.tmpdir

# Some standard diagnostics
failures = []

# Timeseries
try:
  from timeseries import timeseries
  timeseries (datasets=[experiment,ec_obs,control], fieldname='CH4', outdir=outdir)
  #timeseries (datasets=[experiment,gaw_obs,control], fieldname='CH4', outdir=outdir)
except Exception as e:
  failures.append(['timeseries', e])
  raise

# Zonal mean movies
try:
  from movie_zonal import movie_zonal
  movie_zonal(models=[experiment,control,None], fieldname='CH4', outdir=outdir)
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
  shortexper_diffcheck (models=[experiment,control], obs=ec_obs, location="Toronto", outdir=outdir)
except Exception as e:
  failures.append(['diffcheck', e])

# XCH4
try:
  from xcol import xcol
  xcol (models=[experiment,control,None], fieldname='CH4', outdir=outdir)
except Exception as e:
  failures.append(['xch4', e])
  raise

# Total mass CH4
try:
  from totalmass import totalmass
  totalmass (models=[experiment,None,control], fieldname='CH4', pg_of='CH4', outdir=outdir)
  totalmass (models=[experiment,None,control], fieldname='air', pg_of='air', outdir=outdir)
except Exception as e:
  failures.append(['totalmass', e])

# Report any diagnostics that failed to run
if len(failures) > 0:
  print "WARNING:"
  print "The following diagnostics failed to run:"
  for diag, e in failures:
    print "%s: %s"%(diag,e)

