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
  parser.add_argument('--crash', action='store_true', help="If there's an unexpected error when doing a diagnostic, terminate with a full stack trace.  The default behaviour is to continue on to the next diagnostic, and print a short warning message at the end.")
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
configparser = ConfigParser.SafeConfigParser(defaults=dict(color='black',linestyle='-',std_style='lines',marker='None'))
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

  cache = Cache(args.tmpdir, read_dirs=[data_dirs[0]+"/nc_cache"])

  color = configparser.get(section,'color')
  linestyle = configparser.get(section,'linestyle')
  std_style = configparser.get(section,'std_style')
  marker = configparser.get(section,'marker')
  experiment = data_interface(data_dirs, name=data_name, title=title, cache=cache, rescan=args.rescan, color=color, linestyle=linestyle, std_style=std_style, marker=marker)

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

# Inject some extra stuff not yet hooked into the command-line
kwargs = vars(args)
kwargs['outdir'] = outdir

# Helper method to invoke a diagnostic
# (handle all the steps of looking up the diagnostic, running it, and catching
# any exceptions).
def diag (diagname, fieldname, units, **extra):
  diagnostic = diagnostics.table[diagname]
  if diagname not in allowed_diagnostics: return
  try:
    d = diagnostic(fieldname=fieldname, units=units, **dict(kwargs,**extra))
    d.do_all(datasets)
  except Exception as e:
    failures.append([fieldname+' '+diagname, e])
    if args.crash:
      raise

##################################################
# Diagnostics
##################################################

diag ('timeseries', 'CO2', 'ppm')
diag ('timeseries', 'CH4', 'ppb')
diag ('timeseries', 'CO', 'ppb')

diag ('aircraft-profiles', 'CO2', 'ppm')

diag ('diurnal-cycle', 'CO2', 'ppm')
diag ('diurnal-cycle', 'CH4', 'ppb')
diag ('diurnal-cycle', 'CO', 'ppb')

diag ('zonal-movie', 'CO2', 'ppm')
diag ('zonal-movie', 'CO2_ensemblespread', 'ppm')
diag ('zonal-movie', 'CH4', 'ppb')
diag ('zonal-movie', 'CO2', 'ppm', typestat='stdev')
diag ('zonal-movie', 'CO', 'ppb', zaxis='model')

diag ('zonal-mean-diff', 'CO2', 'ppm')

diag ('xcol', 'CO2', 'ppm')
diag ('xcol', 'CO2_background', 'ppm')
diag ('xcol', 'CO2_bio', 'ppm')
diag ('xcol', 'CO2_ocean', 'ppm')
diag ('xcol', 'CO2_fossil', 'ppm')
diag ('xcol', 'CO2_fire', 'ppm')
diag ('xcol', 'CH4', 'ppb')
diag ('xcol', 'H2O', 'ppm')

diag ('xcol-diff', 'CO2', 'ppm')
diag ('xcol-diff', 'CH4', 'ppb')

diag ('xcol-enkf', 'CO2', 'ppm')
diag ('xcol-enkf', 'CO2_background', 'ppm')
diag ('xcol-enkf', 'CO2_bio', 'ppm')
diag ('xcol-enkf', 'CO2_ocean', 'ppm')
diag ('xcol-enkf', 'CO2_fossil', 'ppm')
diag ('xcol-enkf', 'CO2_fire', 'ppm')

diag ('totalmass', 'CO2', 'Pg(C)')
diag ('totalmass', 'CO2_fossil', 'Pg(C)')
diag ('totalmass', 'CH4', 'Pg')
diag ('totalmass', 'air', 'Pg')
diag ('totalmass', 'dry_air', 'Pg')
diag ('totalmass', 'H2O', 'Pg')
diag ('totalmass', 'CO', 'Pg')

diag ('totalmass-diff', 'CO2', 'Pg(C)')

diag ('horz-slice', 'CO', 'ppb', level="1.0")
diag ('horz-slice-diff', 'CO2', 'ppm', level="1.0")

diag ('concentration-v-height', 'CO2', 'ppm', xlim=(375,395))

diag ('flux-movie', 'CO2_flux', 'mol m-2 s-1', timefilter='Monthly', plottype='BG')
diag ('flux-movie', 'CO2_flux', 'mol m-2 s-1', timefilter='Daily', plottype='BG')
diag ('flux-movie', 'CO2_flux', 'mol m-2 s-1', timefilter='Monthly', plottype='Map')
diag ('flux-movie', 'CO2_flux', 'mol m-2 s-1', timefilter='Daily', plottype='Map')
diag ('flux-movie', 'CO2_flux', 'mol m-2 s-1', timefilter='Monthly', plottype='MeanMap')
diag ('flux-movie', 'CO2_flux', 'mol m-2 s-1', timefilter='Daily', plottype='MeanMap')

diag ('timeseries-hist', 'CO2', 'ppm')

diag ('timeseries-diff', 'CO2', 'ppm')

diag ('regional-bargraph', 'CO2', 'ppm')

diag ('zonal-bargraph', 'CO2', 'ppm', height=0)


# Report any diagnostics that failed to run
if len(failures) > 0:
  print "WARNING:"
  print "The following diagnostics failed to run:"
  for diag, e in failures:
    print "%s: %s"%(diag,e)
  if args.crash:
    raise

history_file.write("Finished: %s\n\n"%datetime.now())
history_file.close()

