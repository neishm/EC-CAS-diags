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
  lat = experiment.data.datasets[0].lat
  lon = experiment.data.datasets[0].lon
  experiment.data.datasets += tuple(d.replace_axes(lat=lat,lon=lon) for d in flux.data.datasets)

if control_dir is not None:
  control = eccas(control_dir, name=control_name, title=control_title, cache=Cache(dir=control_dir+"/nc_cache", fallback_dirs=[control_tmpdir], global_prefix=control_name+"_"))
else:
  control = None

# CarbonTracker data
carbontracker = interfaces.table['carbontracker'](["/wrk1/EC-CAS/CarbonTracker"], name='CT2010', title='CarbonTracker', cache=Cache('/wrk1/EC-CAS/CarbonTracker/nc_cache', fallback_dirs=filter(None,[args.tmpdir]), global_prefix='CT2010_'))
carbontracker_ch4 = interfaces.table['carbontracker-ch4']("/wrk6/eltonc/ct_ch4/molefractions/2009????.nc", name='CTCH42010', title='CarbonTracker', cache=Cache('/wrk6/eltonc/ct_ch4/molefractions/nc_cache', fallback_dirs=filter(None,[args.tmpdir]), global_prefix='CTCH42010_'))

# Observation data
ec_obs = interfaces.table['ec-station-obs']("/wrk1/EC-CAS/surface/EC-2013", name="EC", title="EC Station Obs", cache=Cache(args.tmpdir, global_prefix="ec-station-obs_", split_time=False))
gaw_obs = interfaces.table['gaw-station-obs']("/wrk1/EC-CAS/surface/GAW-2014/co2/hourly/y2009", name="GAW", title='GAW-2014 Station Obs', cache=Cache(args.tmpdir, global_prefix="gaw-station-obs_", split_time=False))


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

from eccas_diags.timeseries import timeseries
# CO2 Timeseries
try:
  timeseries (models=[experiment,control], obs=ec_obs, fieldname='CO2', units='ppm', outdir=outdir)
  timeseries (models=[experiment,control], obs=gaw_obs, fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['CO2 timeseries', e])
# CH4 Timeseries
try:
  timeseries (models=[experiment,control], obs=ec_obs, fieldname='CH4', units='ppb', outdir=outdir)
except Exception as e:
  failures.append(['CH4 timeseries', e])

from eccas_diags.movie_zonal import movie_zonal
# CO2 Zonal mean movies
try:
  movie_zonal(models=[experiment,control,carbontracker], fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['CO2 movie_zonal', e])
# CO2 Zonal mean of spread
try:
  movie_zonal(models=[experiment,control], fieldname='CO2_ensemblespread', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['CO2 movie_zonal spread', e])
# CH4 Zonal mean movies
try:
  movie_zonal(models=[experiment,control,None], fieldname='CH4', units='ppb', outdir=outdir)
except Exception as e:
  failures.append(['CH4 movie_zonal', e])
from eccas_diags.movie_zonal_diff import movie_zonal_diff
# CO2 Zonal mean movies
try:
  if control is not None:
    movie_zonal_diff(models=[experiment,control], fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['CO2 movie_zonal_diff', e])

# Count of CO2 'holes'
try:
  from eccas_diags.where_holes import where_holes
  where_holes (experiment=experiment, outdir=outdir)
except Exception as e:
  failures.append(['where_holes', e])

# KT sensitivity check
try:
  from eccas_diags.shortexper_diffcheck import shortexper_diffcheck
  shortexper_diffcheck (models=[experiment,control], obs=ec_obs, location="Toronto", outdir=outdir)
except Exception as e:
  failures.append(['diffcheck', e])

from eccas_diags.xcol import xcol
from eccas_diags.xcol_enkf import xcol_enkf
from eccas_diags.xcol_diff import xcol_diff
# XCO2
try:
  xcol (models=[experiment,control,carbontracker], fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2', e])
# XCO2 diff movies
try:
  xcol_diff (models=[experiment,control], fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2_diff', e])
# XH2O
try:
  xcol (models=[experiment,control,None], fieldname='H2O', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XH2O', e])
# Average column of stats
try:
  xcol_enkf (model=experiment, fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2 enkf', e])
# XCO2B
try:
  xcol (models=[experiment,control,carbontracker], fieldname='CO2_background', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2B', e])
# Average column of stats
try:
  xcol_enkf (model=experiment, fieldname='CO2_background', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2B enkf', e])
# XCLA
try:
  xcol (models=[experiment,control,carbontracker], fieldname='CO2_bio', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCLA', e])
# Average column of stats
try:
  xcol_enkf (model=experiment, fieldname='CO2_bio', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCLA enkf', e])
# XCOC
try:
  xcol (models=[experiment,control,carbontracker], fieldname='CO2_ocean', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCOC', e])
# Average column of stats
try:
  xcol_enkf (model=experiment, fieldname='CO2_ocean', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCOC enkf', e])
# XCFF
try:
  xcol (models=[experiment,control,carbontracker], fieldname='CO2_fossil', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCFF', e])
# Average column of stats
try:
  xcol_enkf (model=experiment, fieldname='CO2_fossil', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCFF enkf', e])
# XCBB
try:
  xcol (models=[experiment,control,carbontracker], fieldname='CO2_fire', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCBB', e])
# Average column of stats
try:
  xcol_enkf (model=experiment, fieldname='CO2_fire', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCBB enkf', e])

# XCH4
try:
  xcol (models=[experiment,control,None], fieldname='CH4', units='ppb', outdir=outdir)
except Exception as e:
  failures.append(['XCH4', e])

from eccas_diags.totalmass import totalmass
# Total mass CO2
try:
  totalmass (models=[experiment,None,control], fieldname='CO2', units='Pg(C)', outdir=outdir, normalize_air_mass=True)
  totalmass (models=[experiment,None,control], fieldname='CO2', units='Pg(C)', outdir=outdir)
except Exception as e:
  failures.append(['totalmass CO2', e])
# Total mass CFF
try:
  totalmass (models=[experiment,carbontracker,control], fieldname='CO2_fossil', units='Pg(C)', outdir=outdir, normalize_air_mass=True)
  totalmass (models=[experiment,carbontracker,control], fieldname='CO2_fossil', units='Pg(C)', outdir=outdir)
except Exception as e:
  failures.append(['totalmass CO2_fossil', e])
from eccas_diags.totalmass_diff import totalmass_diff
# Total mass CO2 difference
try:
  totalmass_diff (models=[experiment,control], fieldname='CO2', units='Pg(C)', outdir=outdir, normalize_air_mass=True)
  totalmass_diff (models=[experiment,control], fieldname='CO2', units='Pg(C)', outdir=outdir)
except Exception as e:
  failures.append(['totalmass_diff CO2', e])
# Total mass CH4
try:
  totalmass (models=[experiment,None,control], fieldname='CH4', units='Pg', outdir=outdir)
except Exception as e:
  failures.append(['totalmass CH4', e])
# Total mass air
try:
  totalmass (models=[experiment,None,control], fieldname='air', units='Pg', outdir=outdir)
  totalmass (models=[experiment,None,control], fieldname='dry_air', units='Pg', outdir=outdir)
except Exception as e:
  failures.append(['totalmass air', e])
# Total mass H2O
try:
  totalmass (models=[experiment,None,control], fieldname='H2O', units='Pg', outdir=outdir)
except Exception as e:
  failures.append(['totalmass H2O', e])

# Horizontal slice movie
from eccas_diags.horz_slice_diff import horz_slice_movie
try:
  horz_slice_movie(models=[experiment,control], fieldname='CO2', level="1.0", units='ppm', outdir=outdir) 
except Exception as e:
  failures.append(['horz_slice_movie', e])

#-------------------Jake's Diags------------------------

from eccas_diags.concentration_v_height import movie_CvH
try:
  movie_CvH(models=[experiment,control],fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['concentration vs. height', e])

from eccas_diags.FluxDiagnostic import movie_flux
try:
  movie_flux(models=[experiment], fieldname='CO2', units='ppm', outdir=outdir, timefilter='Monthly', plottype='BG')
except Exception as e:
  failures.append(['Flux Diagnostic - Bar Graph', e])
try:
  movie_flux(models=[experiment], fieldname='CO2', units='ppm', outdir=outdir, timefilter='Daily', plottype='BG')
except Exception as e:
  failures.append(['Flux Diagnostic - Bar Graph', e])
try:
  movie_flux(models=[experiment], fieldname='CO2', units='ppm', outdir=outdir, timefilter='Monthly', plottype='Map')
except Exception as e:
  failures.append(['Flux Diagnostic - Map', e])
try:
  movie_flux(models=[experiment], fieldname='CO2', units='ppm', outdir=outdir, timefilter='Daily', plottype='Map')
except Exception as e:
  failures.append(['Flux Diagnostic - Map', e])
try:
  movie_flux(models=[experiment], fieldname='CO2', units='ppm', outdir=outdir, timefilter='Monthly', plottype='MeanMap')
except Exception as e:
  failures.append(['Flux Diagnostic - Mean Map', e])
try:
  movie_flux(models=[experiment], fieldname='CO2', units='ppm', outdir=outdir, timefilter='Daily', plottype='MeanMap')
except Exception as e:
  failures.append(['Flux Diagnostic - Mean Map', e])


from eccas_diags import TimeSeriesHist as TSH
try:
  TSH.timeseries(models=[experiment],obs=ec_obs,fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['timeseries histogram', e])

from eccas_diags import TimeSeriesAlternate as TSA
try:
  TSA.timeseries(models=[experiment],obs=ec_obs,fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['time series alternate', e])

from eccas_diags.TimeSeriesRBP import Barplot
try:
  Barplot(models=[experiment,control], obs=gaw_obs,fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['time series rbp', e])

from eccas_diags.ZonalMeanBG import movie_bargraph
try:
  movie_bargraph(models=[experiment,control], height=0,fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['zonal mean bargraph', e])



#----------------End of Jake's Diags--------------------


# Report any diagnostics that failed to run
if len(failures) > 0:
  print "WARNING:"
  print "The following diagnostics failed to run:"
  for diag, e in failures:
    print "%s: %s"%(diag,e)

history_file.write("Finished: %s\n\n"%datetime.now())
history_file.close()

