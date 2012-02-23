from movie_zonal import create_images
from model_stuff import open
from common import convert

co2_16 = open("/wrk1/neish/validation_run_16bit")['co2_zonalmean_eta']['CO2'] * convert
co2_32 = open("/wrk1/neish/validation_run_32bit")['co2_zonalmean_eta']['CO2'] * convert

contours = range(376,402+1,1) # total CO2 range

create_images (co2_16, co2_32, title1='CO2 (16-bit)', title2='CO2 (32-bit)', contours=contours)
