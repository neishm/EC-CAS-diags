from model_stuff import my_data
from common import convert_CO2
co2 = my_data("validation_run_32bit")['km_eta932']['CO2'] * convert_CO2

from os.path import exists
import numpy as np

from movie_sfc import create_images

#contours = range(340,510,10)  # global
contours = range(370,410+1,1)  # 1km
create_images (co2, contours=contours, title='CO2 ppmV ~1km')
