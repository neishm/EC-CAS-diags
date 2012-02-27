from movie_zonal import create_images
import numpy as np
from model_stuff import my_data
from common import convert_CO2

cons = my_data("validation_run_32bit")['km_zonalmean_gph']['CONS'] * convert_CO2

contours = np.arange(374.66,375.14+0.02,0.02)
create_images (cons, title1='CONS', contours = contours, palette='Paired')

