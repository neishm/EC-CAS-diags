#from model import co2
#from model import co2_ocean as co2
#from model import co2_bg as co2
from model import co2_eta932 as co2

from os.path import exists
import numpy as np

from movie_sfc import create_images

#contours = range(340,510,10)  # global
contours = range(370,410+1,1)  # 1km
create_images (co2, contours=contours, title='CO2 ppmV ~1km')
