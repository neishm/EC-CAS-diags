#!/usr/bin/env python

# Put multiple movie panels together into 1 movie

# Disable X-windows stuff
import matplotlib
matplotlib.use('Agg')

from pygeode.formats import netcdf
from common import same_times
from diagnostics.movie import ZonalMovie
from diagnostics.movie import ContourMovie
from glob import glob

#  ---- User defined input parameters ---
tmpdir="/wrk3/armasmp/tmp/"
exper="spcas006"
experdir="/wrk3/armasmp/enkf/exp/archive"+"/"+exper
#  Only 2 types of movies possible now: avgcolumn or zonalmean_gph
#type="avgcolumn"
type="zonalmean_gph"
date_range="201412272100-201501090900"
#  --------------------------------------

filename_CO2=tmpdir+exper+"_"+type+"_CO2_ensemblespread_*_"+date_range+".nc"
filename_CH4=tmpdir+exper+"_"+type+"_CH4_ensemblespread_*_"+date_range+".nc"
filename_CO=tmpdir+exper+"_"+type+"_CO_ensemblespread_*_"+date_range+".nc"
outdir_name=experdir+"/diags"
out_prefix=exper+"_"+type+"_ensemblespread_3gases_"+date_range

# Evaluate wildcard to match an actual file
filename_CO2 = glob(filename_CO2)[0]
filename_CH4 = glob(filename_CH4)[0]
filename_CO  = glob(filename_CO )[0]
print "filename CO2 is ", filename_CO2
print "filename CH4 is ", filename_CH4
print "filename CO  is ", filename_CO

#  --- Open input files ---
CO2_file = netcdf.open(filename_CO2).CO2_ensemblespread
CH4_file = netcdf.open(filename_CH4).CH4_ensemblespread
CO_file = netcdf.open(filename_CO).CO_ensemblespread

#  --- Create the movie ---
subtitles = ['CO2', 'CH4', 'CO']
CO2, CH4, CO = same_times(CO2_file, CH4_file, CO_file)
if type == "zonalmean_gph":
   movie = ZonalMovie([CO2,CH4,CO], title='Forecast ensemble spread', subtitles=subtitles, shape=(1,3), aspect_ratio = 1.0, cmaps=['jet','jet', 'jet'])
if type == "avgcolumn":
   movie = ContourMovie([CO2,CH4,CO], title='Forecast ensemble spread', subtitles=subtitles, shape=(3,1), aspect_ratio = 0.4, cmaps=['jet','jet', 'jet'])

#  --- Save the movie ---
movie.save (outdir=outdir_name, prefix=out_prefix)
