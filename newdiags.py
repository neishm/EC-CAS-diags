#!/usr/bin/env python

# Disable X-windows stuff
# (so the diagnostics will work even if there is not X11 connection)
import matplotlib
matplotlib.use('Agg')

import argparse
import ConfigParser
from os.path import exists
from glob import glob
import os

from eccas_diags.cache import Cache
from eccas_diags import interfaces

# Helper method - check if a value is a special marker for a command-line
# argument
def is_cmdline_arg (value):
  return value.startswith('{') and value.endswith('}')

# Helper method - split a command-line argument in a name, description, default
def split_cmdline_arg (value):
  param = value[1:-1]
  default = None
  desc = None
  if ':' in param:
    param, desc = param.split(':',1)
    if ':' in desc: desc, default = desc.split(':',1)
  return param, desc, default


# Extract command-line arguments

description = 'Produce various diagnostics (figures and animations).'

# Pass 1: get configuration file.
parser = argparse.ArgumentParser (description=description, epilog='Different arguments may exist for particular configuration files.', add_help=False)
parser.add_argument('-h', '--help', action='store_true', help="Display help message")
parser.add_argument('-f', '--configfile', default='default.cfg', type=argparse.FileType('r'), nargs='?')
args, extra_args = parser.parse_known_args()


# Start a new argument parser, now that we have the configuration file.
parser = argparse.ArgumentParser (description=description, add_help=True)
# Add this config file as an option
parser.add_argument('-f', '--configfile', help="Configuration file to use for the diagnostics.  Default is 'default.cfg'.  Currently using '%s'."%args.configfile.name)
parser.add_argument('--tmpdir', help="where to put any intermediate files that get generated, if they can't be stored in their usual location.  THIS SHOULD NOT BE IN YOUR HOME DIRECTORY.")

# Read the configuration file.
configparser = ConfigParser.SafeConfigParser()
configparser.readfp(args.configfile)

# Scan for special markup for command-line arguments
configoptions = parser.add_argument_group('options specific to %s'%args.configfile.name)
handled_params = []
for section in configparser.sections():
  for name, value in configparser.items(section):
    if is_cmdline_arg(value):
      param, desc, default = split_cmdline_arg(value)
      if param not in handled_params:
        configoptions.add_argument(param, default=default, help=desc)
        handled_params.append(param)

# Pass 2: Get all the parameters needed.
args = parser.parse_args()

# Re-scan the configuration parameters, filling in anything from the
# command-line.
# Remove sections that are unresolved (user did not provide a parameter).
for section in configparser.sections():
  for name, value in configparser.items(section):
    if is_cmdline_arg(value):
      param, desc, default = split_cmdline_arg(value)
      argname = param.lstrip('-').replace('-','_')
      if hasattr(args, argname):
        value = getattr(args,argname)
        if value is None:
          print "Omitting [%s] due to missing command-line parameter %s."%(section,param)
          configparser.remove_section(section)
          break
        configparser.set(section, name, value)


# Prep all the datasets.
datasets = []
for section in configparser.sections():
  print "Prepping [%s]"%section
  data_dirs = configparser.get(section,'dir').split()
  for data_dir in data_dirs:
    if len(glob(data_dir)) == 0:
      raise ValueError ("Directory '%s' doesn't exist"%data_dir)
  data_dirs = [f for fn in data_dirs for f in glob(fn)]
  data_type = configparser.get(section,'interface')
  data_interface = interfaces.table.get(data_type)
  if data_interface is None:
    raise ValueError ("Unknown interface type '%s'"%data_type)
  data_name = data_interface.get_dataname(data_dirs[0].rstrip('/'))
  if data_name is None:
    raise ValueError ("Unable to determine a name to use for '%s' data in directory %s"%(data_type,data_dirs[0]))
  print "Found dataset:", data_name
  if configparser.has_option(section,'desc'):
    desc = configparser.get(section,'desc')
  else:
    desc = section
  color = configparser.get(section,'color')

  if args.tmpdir is not None:
    fallback_dirs = [args.tmpdir]
  else: fallback_dirs = []
  
  cache = Cache(dir=data_dirs[0]+"/nc_cache", fallback_dirs=fallback_dirs)

  experiment = data_interface(data_dirs, name=data_name, title='%s (%s)'%(desc,data_name), color=color, cache=cache)

  datasets.append(experiment)

# Dump the output files to a subdirectory of the experiment data
from os import mkdir
expsection = configparser.sections()[0]
expdir = configparser.get(expsection,'dir')
outdir = expdir+"/diags"
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

from eccas_diags.diagnostics import timeseries
# CO2 Timeseries
try:
  timeseries.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['CO2 timeseries', e])
# CH4 Timeseries
try:
  timeseries.do_all (datasets, fieldname='CH4', units='ppb', outdir=outdir)
except Exception as e:
  failures.append(['CH4 timeseries', e])

from eccas_diags.diagnostics import movie_zonal
# CO2 Zonal mean movies
try:
  movie_zonal.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['CO2 movie_zonal', e])
# CO2 Zonal mean of spread
try:
  movie_zonal.do_all(datasets, fieldname='CO2_ensemblespread', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['CO2 movie_zonal spread', e])
# CH4 Zonal mean movies
try:
  movie_zonal.do_all(datasets, fieldname='CH4', units='ppb', outdir=outdir)
except Exception as e:
  failures.append(['CH4 movie_zonal', e])

from eccas_diags.diagnostics import movie_zonal_diff
# CO2 Zonal mean movies
try:
  movie_zonal_diff.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['CO2 movie_zonal_diff', e])

"""
# Count of CO2 'holes'
try:
  from eccas_diags.diagnostics.where_holes import where_holes
  where_holes (experiment=experiment, outdir=outdir)
except Exception as e:
  failures.append(['where_holes', e])

# KT sensitivity check
try:
  from eccas_diags.diagnostics.shortexper_diffcheck import shortexper_diffcheck
  shortexper_diffcheck (models=[experiment,control], obs=ec_obs, location="Toronto", outdir=outdir)
except Exception as e:
  failures.append(['diffcheck', e])
"""

from eccas_diags.diagnostics import xcol
from eccas_diags.diagnostics import xcol_enkf
from eccas_diags.diagnostics import xcol_diff
# XCO2
try:
  xcol.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2', e])
# XCO2 diff movies
try:
  xcol_diff.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2_diff', e])
# XH2O
try:
  xcol.do_all (datasets, fieldname='H2O', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XH2O', e])
# Average column of stats
try:
  xcol_enkf.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2 enkf', e])
# XCO2B
try:
  xcol.do_all (datasets, fieldname='CO2_background', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2B', e])
# Average column of stats
try:
  xcol_enkf.do_all (datasets, fieldname='CO2_background', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCO2B enkf', e])
# XCLA
try:
  xcol.do_all (datasets, fieldname='CO2_bio', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCLA', e])
# Average column of stats
try:
  xcol_enkf.do_all (datasets, fieldname='CO2_bio', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCLA enkf', e])
# XCOC
try:
  xcol.do_all (datasets, fieldname='CO2_ocean', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCOC', e])
# Average column of stats
try:
  xcol_enkf.do_all (datasets, fieldname='CO2_ocean', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCOC enkf', e])
# XCFF
try:
  xcol.do_all (datasets, fieldname='CO2_fossil', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCFF', e])
# Average column of stats
try:
  xcol_enkf.do_all (datasets, fieldname='CO2_fossil', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCFF enkf', e])
# XCBB
try:
  xcol.do_all (datasets, fieldname='CO2_fire', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCBB', e])
# Average column of stats
try:
  xcol_enkf.do_all (datasets, fieldname='CO2_fire', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['XCBB enkf', e])

# XCH4
try:
  xcol.do_all (datasets, fieldname='CH4', units='ppb', outdir=outdir)
except Exception as e:
  failures.append(['XCH4', e])

from eccas_diags.diagnostics import totalmass
# Total mass CO2
try:
  totalmass.do_all (datasets, fieldname='CO2', units='Pg(C)', outdir=outdir)
except Exception as e:
  failures.append(['totalmass CO2', e])
# Total mass CFF
try:
  totalmass.do_all (datasets, fieldname='CO2_fossil', units='Pg(C)', outdir=outdir)
except Exception as e:
  failures.append(['totalmass CO2_fossil', e])
from eccas_diags.diagnostics import totalmass_diff
# Total mass CO2 difference
try:
  totalmass_diff.do_all (datasets, fieldname='CO2', units='Pg(C)', outdir=outdir)
except Exception as e:
  failures.append(['totalmass_diff CO2', e])
# Total mass CH4
try:
  totalmass.do_all (datasets, fieldname='CH4', units='Pg', outdir=outdir)
except Exception as e:
  failures.append(['totalmass CH4', e])
# Total mass air
try:
  totalmass.do_all (datasets, fieldname='air', units='Pg', outdir=outdir)
  totalmass.do_all (datasets, fieldname='dry_air', units='Pg', outdir=outdir)
except Exception as e:
  failures.append(['totalmass air', e])
# Total mass H2O
try:
  totalmass.do_all (datasets, fieldname='H2O', units='Pg', outdir=outdir)
except Exception as e:
  failures.append(['totalmass H2O', e])

# Horizontal slice movie
from eccas_diags.diagnostics import horz_slice_diff
try:
  horz_slice_diff.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, level="1.0")
except Exception as e:
  failures.append(['horz_slice_movie', e])

#-------------------Jake's Diags------------------------

from eccas_diags.diagnostics import concentration_v_height
try:
  concentration_v_height.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['concentration vs. height', e])

from eccas_diags.diagnostics import FluxDiagnostic
try:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Monthly', plottype='BG')
except Exception as e:
  failures.append(['Flux Diagnostic - Bar Graph', e])
try:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Daily', plottype='BG')
except Exception as e:
  failures.append(['Flux Diagnostic - Bar Graph', e])
try:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Monthly', plottype='Map')
except Exception as e:
  failures.append(['Flux Diagnostic - Map', e])
try:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Daily', plottype='Map')
except Exception as e:
  failures.append(['Flux Diagnostic - Map', e])
try:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Monthly', plottype='MeanMap')
except Exception as e:
  failures.append(['Flux Diagnostic - Mean Map', e])
try:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Daily', plottype='MeanMap')
except Exception as e:
  failures.append(['Flux Diagnostic - Mean Map', e])


from eccas_diags.diagnostics import TimeSeriesHist as TSH
try:
  TSH.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['timeseries histogram', e])

from eccas_diags.diagnostics import TimeSeriesAlternate as TSA
try:
  TSA.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['time series alternate', e])

from eccas_diags.diagnostics import TimeSeriesRBP
try:
  TimeSeriesRBP.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir)
except Exception as e:
  failures.append(['time series rbp', e])
  raise

from eccas_diags.diagnostics import ZonalMeanBG
try:
  ZonalMeanBG.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir, height=0)
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

