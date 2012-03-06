# Compare CO2 field with/without mass conservation on vertical diffusion

import numpy as np
from model_stuff import my_data
from movie_zonal import create_images
from common import convert_CO2
from carbontracker import co2 as ct_co2, ct_zonal, molefractions
ct_co2 = ct_zonal(ct_co2)
#ct_co2 = ct_zonal(molefractions['bio'])

data = my_data("validation_run_32bit")['km_zonalmean_gph']
data6b = my_data("cycletest6b")['km_zonalmean_gph']

#mc = data['CONS'] * convert_CO2
#nomc = data6b['CONS'] * convert_CO2
mc = data['CO2'] * convert_CO2
nomc = data6b['CO2'] * convert_CO2
#mc = data['CLA'] * convert_CO2 - 100
#nomc = data6b['CLA'] * convert_CO2 - 100

#create_images(mc, nomc, title1='CONS (mass conservation)', title2='CONS (no mass cons.)', contours = np.arange(374.66,375.14+0.02,0.02), palette='Paired')
create_images(mc, nomc, ct_co2, title1='CO2 (mass conservation)', title2='CO2 (no mass cons.)', title3='CarbonTracker CO2')
#create_images(mc, nomc, ct_co2, title1='CLA (mass conservation)', title2='CLA (no mass cons.)', title3='CarbonTracker biog. CO2')
