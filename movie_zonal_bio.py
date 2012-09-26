from carbontracker import data as ct

ct_co2 = ct['zonalmean_gph_24h']['bio']

from interfaces import control_title, control, experiment_title, experiment_name, experiment
from common import convert_CO2

control_co2 = control['zonalmean_gph']['CLA'] * convert_CO2 - 100
exper_co2 = experiment['zonalmean_gph']['CLA'] * convert_CO2 - 100

from movie_zonal import create_images

outdir="images_%s_zonalbio"%experiment_name
create_images (exper_co2, control_co2, ct_co2, title1=experiment_title, title2=control_title, title3='CarbonTracker',preview=False, outdir=outdir)
