from movie_zonal import create_images
from model_stuff import my_data
from common import convert_CO2

co2_p5 = my_data("validation_run_32bit")['km_zonalmean_eta']['CO2'] * convert_CO2
co2_p7 = my_data("cycletest6")['km_zonalmean_eta']['CO2'] * convert_CO2

create_images (co2_p5, co2_p7, title1='CO2 (P5 run)', title2='CO2 (P7 run)')
