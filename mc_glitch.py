# Compare CO2 field with/without mass conservation on vertical diffusion

from model_stuff import my_data
from movie_zonal import create_images
from common import convert_CO2

data = my_data("validation_run_32bit")['km_zonalmean_eta'](year=2009,month=(1,6))
data6b = my_data("cycletest6b")['km_zonalmean_eta'](year=2009,month=(1,6))

mc = data['CONS'] * convert_CO2
nomc = data6b['CONS'] * convert_CO2

create_images(mc, nomc, title1='CONS (mass conservation)', title2='CONS (no mass cons.)')
#create_images(mc-nomc, title1='CONS conserv/non-conserv difference')
