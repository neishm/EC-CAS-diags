#!/usr/bin/env python

# Disable X-windows stuff
# (so the diagnostics will work even if there is not X11 connection)
import matplotlib
matplotlib.use('Agg')

import argparse
import ConfigParser
from os.path import exists, basename, splitext
from shutil import copy
from glob import glob
import os
from datetime import datetime

from eccas_diags.cache import Cache
from eccas_diags import interfaces, diagnostics

now = datetime.now()

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

def make_parser(add_help=True):
  description = 'Produce various diagnostics (figures and animations).'
  epilog='Different arguments may exist for particular configuration files.'

  parser = argparse.ArgumentParser (description=description, epilog=epilog, add_help=add_help)
  parser.add_argument('-f', '--configfile', type=argparse.FileType('r'), nargs='?', help="Configuration file to use for the diagnostics.")
  parser.add_argument('--tmpdir', help="where to put any intermediate files that get generated, if they can't be stored in their usual location.  THIS SHOULD NOT BE IN YOUR HOME DIRECTORY.")
  parser.add_argument('--rescan', action='store_true', help="Force the input files to be re-scanned.  Useful if the interfaces have changed since the last time the script was run.")
  parser.add_argument('--list-diagnostics', action='store_true', help="List all the available diagnostics, then exit.")
  parser.add_argument('--diagnostics', action='store', metavar="diagname1,diagname2,...", help="Comma-separated list of diagnostics to run.  By default, all available diagnostics are run.")
  return parser

parser = make_parser(add_help=False)
args, extra_args = parser.parse_known_args()

parser = make_parser(add_help=True)

if args.list_diagnostics:
  print "Available diagnostics:\n"
  for diagname, diagclass in sorted(diagnostics.table.items()):
    print '%s%s'%(diagname,diagclass.__doc__ or '\n  ???')
  quit()

# Determine which diagnostics will be considered from running.
# By default, all possible diagnostics will be run, unless specific ones are
# given on the command-line.
if args.diagnostics is not None:
  allowed_diagnostics = args.diagnostics.split(',')
else:
  allowed_diagnostics = list(diagnostics.table.keys())
for d in sorted(allowed_diagnostics):
  if d not in diagnostics.table:
    parser.error("Unknown diagnostic '%s'.  Use the '--list-diagnostics' option to see all available diagnostics."%d)

# Add diagnostic-specific command-line arguments.
for diagname,diagclass in sorted(diagnostics.table.items()):
  diagclass.add_args(parser)

if args.configfile is None:
  parser.print_help()
  quit()

# Read the configuration file.
configparser = ConfigParser.SafeConfigParser(defaults=dict(color='black',linestyle='-',marker='None'))
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
  if configparser.has_option(section,'title'):
    title = configparser.get(section,'title')
  else:
    title = '%s (%s)'%(desc,data_name)

  if args.tmpdir is not None:
    fallback_dirs = [args.tmpdir]
  else: fallback_dirs = []
  
  cache = Cache(dir=data_dirs[0]+"/nc_cache", fallback_dirs=fallback_dirs)

  experiment = data_interface(data_dirs, name=data_name, title=title, cache=cache, rescan=args.rescan)
  experiment.color = configparser.get(section,'color')
  experiment.linestyle = configparser.get(section,'linestyle')
  experiment.marker = configparser.get(section,'marker')

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
from sys import argv
# Helper function to quote arguments with spaces in them.
def quote_arg (s):
  if ' ' not in s: return s
  if '=' in s:
    key,value = s.split('=',1)
    return key+'='+quote_arg(value)
  return '"'+s+'"'

history_file = open(outdir+"/history.txt","a")
history_file.write("=== %s ===\n"%now)
history_file.write(" ".join(quote_arg(v) for v in argv)+"\n\n")

# Make a snapshot of the config file for posterity.
configbase, configext = splitext(basename(args.configfile.name))
copy(args.configfile.name, outdir+"/"+configbase+now.strftime(".%Y%m%d_%H:%M:%S")+configext)


# Some standard diagnostics
failures = []

timeseries = diagnostics.table['timeseries']
kwargs = timeseries.handle_args(args)
# CO2 Timeseries
try:
 if 'timeseries' in allowed_diagnostics:
  timeseries.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['CO2 timeseries', e])
# CH4 Timeseries
try:
 if 'timeseries' in allowed_diagnostics:
  timeseries.do_all (datasets, fieldname='CH4', units='ppb', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['CH4 timeseries', e])

# Aircraft profiles
profiles = diagnostics.table['aircraft-profiles']
kwargs = profiles.handle_args(args)
try:
 if 'aircraft-profiles' in allowed_diagnostics:
  profiles.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['CO2 aircraft profiles', e])

# Diurnal cycle
diurnal_cycle = diagnostics.table['diurnal-cycle']
kwargs = diurnal_cycle.handle_args(args)
try:
 if 'diurnal-cycle' in allowed_diagnostics:
  diurnal_cycle.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['CO2 diurnal cycle', e])
try:
 if 'diurnal-cycle' in allowed_diagnostics:
  diurnal_cycle.do_all (datasets, fieldname='CH4', units='ppb', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['CH4 diurnal cycle', e])

movie_zonal = diagnostics.table['zonal-movie']
kwargs = movie_zonal.handle_args(args)
# CO2 Zonal mean movies
try:
 if 'zonal-movie' in allowed_diagnostics:
  movie_zonal.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['CO2 movie_zonal', e])
# CO2 Zonal mean of spread
try:
 if 'zonal-movie' in allowed_diagnostics:
  movie_zonal.do_all(datasets, fieldname='CO2_ensemblespread', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['CO2 movie_zonal spread', e])
# CH4 Zonal mean movies
try:
 if 'zonal-movie' in allowed_diagnostics:
  movie_zonal.do_all(datasets, fieldname='CH4', units='ppb', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['CH4 movie_zonal', e])

movie_zonal_diff = diagnostics.table['zonal-mean-diff']
kwargs = movie_zonal_diff.handle_args(args)
# CO2 Zonal mean movies
try:
 if 'zonal-mean-diff' in allowed_diagnostics:
  movie_zonal_diff.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
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

xcol = diagnostics.table['xcol']
xcol_enkf = diagnostics.table['xcol-enkf']
xcol_diff = diagnostics.table['xcol-diff']
kwargs = xcol.handle_args(args)
kwargs_enkf = xcol_enkf.handle_args(args)
kwargs_diff = xcol_diff.handle_args(args)
# XCO2
try:
 if 'xcol' in allowed_diagnostics:
  xcol.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['XCO2', e])
# XCO2 diff movies
try:
 if 'xcol-diff' in allowed_diagnostics:
  xcol_diff.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir, **kwargs_diff)
except Exception as e:
  failures.append(['XCO2_diff', e])
# XH2O
try:
 if 'xcol' in allowed_diagnostics:
  xcol.do_all (datasets, fieldname='H2O', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['XH2O', e])
# Average column of stats
try:
 if 'xcol-enkf' in allowed_diagnostics:
  xcol_enkf.do_all (datasets, fieldname='CO2', units='ppm', outdir=outdir, **kwargs_enkf)
except Exception as e:
  failures.append(['XCO2 enkf', e])
# XCO2B
try:
 if 'xcol' in allowed_diagnostics:
  xcol.do_all (datasets, fieldname='CO2_background', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['XCO2B', e])
# Average column of stats
try:
 if 'xcol-enkf' in allowed_diagnostics:
  xcol_enkf.do_all (datasets, fieldname='CO2_background', units='ppm', outdir=outdir, **kwargs_enkf)
except Exception as e:
  failures.append(['XCO2B enkf', e])
# XCLA
try:
 if 'xcol' in allowed_diagnostics:
  xcol.do_all (datasets, fieldname='CO2_bio', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['XCLA', e])
# Average column of stats
try:
 if 'xcol-enkf' in allowed_diagnostics:
  xcol_enkf.do_all (datasets, fieldname='CO2_bio', units='ppm', outdir=outdir, **kwargs_enkf)
except Exception as e:
  failures.append(['XCLA enkf', e])
# XCOC
try:
 if 'xcol' in allowed_diagnostics:
  xcol.do_all (datasets, fieldname='CO2_ocean', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['XCOC', e])
# Average column of stats
try:
 if 'xcol-enkf' in allowed_diagnostics:
  xcol_enkf.do_all (datasets, fieldname='CO2_ocean', units='ppm', outdir=outdir, **kwargs_enkf)
except Exception as e:
  failures.append(['XCOC enkf', e])
# XCFF
try:
 if 'xcol' in allowed_diagnostics:
  xcol.do_all (datasets, fieldname='CO2_fossil', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['XCFF', e])
# Average column of stats
try:
 if 'xcol-enkf' in allowed_diagnostics:
  xcol_enkf.do_all (datasets, fieldname='CO2_fossil', units='ppm', outdir=outdir, **kwargs_enkf)
except Exception as e:
  failures.append(['XCFF enkf', e])
# XCBB
try:
 if 'xcol' in allowed_diagnostics:
  xcol.do_all (datasets, fieldname='CO2_fire', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['XCBB', e])
# Average column of stats
try:
 if 'xcol-enkf' in allowed_diagnostics:
  xcol_enkf.do_all (datasets, fieldname='CO2_fire', units='ppm', outdir=outdir, **kwargs_enkf)
except Exception as e:
  failures.append(['XCBB enkf', e])

# XCH4
try:
 if 'xcol' in allowed_diagnostics:
  xcol.do_all (datasets, fieldname='CH4', units='ppb', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['XCH4', e])
try:
 if 'xcol-diff' in allowed_diagnostics:
  xcol_diff.do_all (datasets, fieldname='CH4', units='ppb', outdir=outdir, **kwargs_diff)
except Exception as e:
  failures.append(['XCH4_diff', e])

totalmass = diagnostics.table['totalmass']
kwargs = totalmass.handle_args(args)
# Total mass CO2
try:
 if 'totalmass' in allowed_diagnostics:
  totalmass.do_all (datasets, fieldname='CO2', units='Pg(C)', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['totalmass CO2', e])
# Total mass CFF
try:
 if 'totalmass' in allowed_diagnostics:
  totalmass.do_all (datasets, fieldname='CO2_fossil', units='Pg(C)', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['totalmass CO2_fossil', e])

totalmass_diff = diagnostics.table['totalmass-diff']
kwargs_diff = totalmass_diff.handle_args(args)
# Total mass CO2 difference
try:
 if 'totalmass-diff' in allowed_diagnostics:
  totalmass_diff.do_all (datasets, fieldname='CO2', units='Pg(C)', outdir=outdir, **kwargs_diff)
except Exception as e:
  failures.append(['totalmass_diff CO2', e])
# Total mass CH4
try:
 if 'totalmass' in allowed_diagnostics:
  totalmass.do_all (datasets, fieldname='CH4', units='Pg', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['totalmass CH4', e])
# Total mass air
try:
 if 'totalmass' in allowed_diagnostics:
  totalmass.do_all (datasets, fieldname='air', units='Pg', outdir=outdir, **kwargs)
  totalmass.do_all (datasets, fieldname='dry_air', units='Pg', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['totalmass air', e])
# Total mass H2O
try:
 if 'totalmass' in allowed_diagnostics:
  totalmass.do_all (datasets, fieldname='H2O', units='Pg', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['totalmass H2O', e])

# Horizontal slice movie
horz_slice_diff = diagnostics.table['horz-slice-diff']
kwargs = horz_slice_diff.handle_args(args)
try:
 if 'horz-slice-diff' in allowed_diagnostics:
  horz_slice_diff.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, level="1.0", **kwargs)
except Exception as e:
  failures.append(['horz_slice_movie', e])

#-------------------Jake's Diags------------------------

from eccas_diags.diagnostics import concentration_v_height
concentration_v_height = diagnostics.table['concentration-v-height']
kwargs = concentration_v_height.handle_args(args)
try:
 if 'concentration-v-height' in allowed_diagnostics:
  concentration_v_height.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['concentration vs. height', e])

FluxDiagnostic = diagnostics.table['flux-movie']
kwargs = FluxDiagnostic.handle_args(args)
try:
 if 'flux-movie' in allowed_diagnostics:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Monthly', plottype='BG', **kwargs)
except Exception as e:
  failures.append(['Flux Diagnostic - Bar Graph', e])
try:
 if 'flux-movie' in allowed_diagnostics:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Daily', plottype='BG', **kwargs)
except Exception as e:
  failures.append(['Flux Diagnostic - Bar Graph', e])
try:
 if 'flux-movie' in allowed_diagnostics:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Monthly', plottype='Map', **kwargs)
except Exception as e:
  failures.append(['Flux Diagnostic - Map', e])
try:
 if 'flux-movie' in allowed_diagnostics:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Daily', plottype='Map', **kwargs)
except Exception as e:
  failures.append(['Flux Diagnostic - Map', e])
try:
 if 'flux-movie' in allowed_diagnostics:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Monthly', plottype='MeanMap', **kwargs)
except Exception as e:
  failures.append(['Flux Diagnostic - Mean Map', e])
try:
 if 'flux-movie' in allowed_diagnostics:
  FluxDiagnostic.do_all(datasets, fieldname='CO2', units='ppm', outdir=outdir, timefilter='Daily', plottype='MeanMap', **kwargs)
except Exception as e:
  failures.append(['Flux Diagnostic - Mean Map', e])


TSH = diagnostics.table['timeseries-hist']
kwargs = TSH.handle_args(args)
try:
 if 'timeseries-hist' in allowed_diagnostics:
  TSH.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['timeseries histogram', e])

TSA = diagnostics.table['timeseries-diff']
kwargs = TSA.handle_args(args)
try:
 if 'timeseries-diff' in allowed_diagnostics:
  TSA.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['time series alternate', e])

TimeSeriesRBP = diagnostics.table['regional-bargraph']
kwargs = TimeSeriesRBP.handle_args(args)
try:
 if 'regional-bargraph' in allowed_diagnostics:
  TimeSeriesRBP.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir, **kwargs)
except Exception as e:
  failures.append(['time series rbp', e])
  raise

ZonalMeanBG = diagnostics.table['zonal-bargraph']
kwargs = ZonalMeanBG.handle_args(args)
try:
 if 'zonal-bargraph' in allowed_diagnostics:
  ZonalMeanBG.do_all(datasets,fieldname='CO2', units='ppm', outdir=outdir, height=0, **kwargs)
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

