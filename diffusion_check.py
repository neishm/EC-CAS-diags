# Compare the differences in CO2B when it's diffused / not diffused

from model_stuff import my_data
from movie_zonal import create_images
from common import convert_CO2

cons = my_data("validation_run_32bit")['km_zonalmean_eta']['CONS'] * convert_CO2
xons = my_data("cycletest5a")['km_zonalmean_eta']['XONS'] * convert_CO2

#co2b = my_data("validation_run_32bit")['km_zonalmean_eta']['CO2B'] * convert_CO2
#xo2b = my_data("cycletest5a")['km_zonalmean_eta']['XO2B'] * convert_CO2

create_images(cons, xons, title1='CONS (diffused)', title2='CONS (non-diffused)')
#create_images(co2b, xo2b, title1='CO2B (diffused)', title2='CO2B (non-diffused)')

#create_images(co2b-xo2b, title1='CO2B difference')
