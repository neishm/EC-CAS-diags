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
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument ("--dry-air", help="Interprets the tracers as being w.r.t. dry air.", action="store_const", const=True, dest="dry_air")
group.add_argument("--moist-air", help="Interprets the tracers as being w.r.t. moist air.", action="store_const", const=False, dest="dry_air")


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

from eccas_diags.cache import Cache

from eccas_diags import interfaces
if args.dry_air: eccas = interfaces.table['eccas-dry']
else: eccas = interfaces.table['eccas-moist']
eccas_flux = interfaces.table['eccas-flux']

experiment = eccas(experiment_dir, name=experiment_name, title=experiment_title, cache=Cache(dir=experiment_dir+"/nc_cache", fallback_dirs=[experiment_tmpdir], global_prefix=experiment_name+"_"))
# Duct-tape the flux data to the experiment data
#TODO: make the fluxes a separate product
if args.emissions is not None:
  flux = eccas_flux(args.emissions, cache=experiment.cache)
  # Fix the emissions lat/lon (not encoded exactly the same as the model output)
  lat = experiment.datasets[0].lat
  lon = experiment.datasets[0].lon
  experiment.datasets += tuple(d.replace_axes(lat=lat,lon=lon) for d in flux.datasets)

if control_dir is not None:
  control = eccas(control_dir, name=control_name, title=control_title, cache=Cache(dir=control_dir+"/nc_cache", fallback_dirs=[control_tmpdir], global_prefix=control_name+"_"))
else:
  control = None

carbontracker=None


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

# Write basic information to a history file.
from datetime import datetime
from sys import argv
history_file = open(outdir+"/history.txt","a")
history_file.write("=== %s ===\n"%datetime.now())
history_file.write(" ".join(argv)+"\n\n")

# Some standard diagnostics
failures = []

from eccas_diags.diagnostics.movie_zonal import movie_zonal
from eccas_diags.diagnostics.movie_zonal_diff import movie_zonal_diff
# CO2 Zonal mean movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['CO2 movie_zonal_diff', e])
# TT  Zonal mean movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='air_temperature', units='K', outdir=outdir)
except Exception as e:
  failures.append(['TT  movie_zonal_diff', e])
# UU  Zonal mean movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='zonal_wind', units='m s-1', outdir=outdir)
except Exception as e:
  failures.append(['UU  movie_zonal_diff', e])
# VV  Zonal mean movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='meridional_wind', units='m s-1', outdir=outdir)
except Exception as e:
  failures.append(['VV  movie_zonal_diff', e])
# HU  Zonal mean movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='H2O', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['HU  movie_zonal_diff', e])

# CO2 Zonal standard deviation movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='CO2', units='ppm', outdir=outdir, typestat='stdev' )
except Exception as e:
  failures.append(['CO2 movie_zonal_stdev', e])
# TT  Zonal standard deviation movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='air_temperature', units='K', outdir=outdir, typestat='stdev')
except Exception as e:
  failures.append(['TT  movie_zonal_stdev', e])
# UU  Zonal standard deviation movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='zonal_wind', units='m s-1', outdir=outdir, typestat='stdev')
except Exception as e:
  failures.append(['UU  movie_zonal_stdev', e])
# VV  Zonal standard deviation movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='meridional_wind', units='m s-1', outdir=outdir, typestat='stdev')
except Exception as e:
  failures.append(['VV  movie_zonal_stdev', e])
# HU  Zonal standard deviation movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='H2O', units='ppm', outdir=outdir, typestat='stdev')
except Exception as e:
  failures.append(['HU  movie_zonal_stdev', e])


from eccas_diags.diagnostics.xcol_diff import xcol_diff
# XCO2 diff movies
try:
  xcol_diff (models=[experiment,control], fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2_diff', e])

# Horizontal slice movie
from eccas_diags.diagnostics import horz_slice_diff
# Horizontal slice movie for CO2
try:
  horz_slice_diff.horz_slice_movie([experiment,control], fieldname='CO2', units='ppm', outdir=outdir, level="0.029")
  horz_slice_diff.horz_slice_movie([experiment,control], fieldname='CO2', units='ppm', outdir=outdir, level="0.75")
except Exception as e:
  failures.append(['horz_slice_movie for CO2', e])
# Horizontal slice movie for TT 
try:
  horz_slice_diff.horz_slice_movie([experiment,control], fieldname='air_temperature', units='K', outdir=outdir, level="0.029")
except Exception as e:
  failures.append(['horz_slice_movie for TT ', e])
# Horizontal slice movie for UU
try:
  horz_slice_diff.horz_slice_movie([experiment,control], fieldname='zonal_wind', units='m s-1', outdir=outdir, level="0.75")
except Exception as e:
  failures.append(['horz_slice_movie for UU ', e])
# Horizontal slice movie for VV
try:
  horz_slice_diff.horz_slice_movie([experiment,control], fieldname='meridional_wind', units='m s-1', outdir=outdir, level="0.75")
except Exception as e:
  failures.append(['horz_slice_movie for VV ', e])


# Report any diagnostics that failed to run
if len(failures) > 0:
  print "WARNING:"
  print "The following diagnostics failed to run:"
  for diag, e in failures:
    print "%s: %s"%(diag,e)

history_file.write("Finished: %s\n\n"%datetime.now())
history_file.close()

