# Compare the differences in CO2B when it's diffused / not diffused

from model_stuff import my_data
from movie_zonal import create_images
from common import convert_CO2

data = my_data("cycletest6")['km_zonalmean_eta']
co2b = data.CO2B * convert_CO2
xo2b = data.XO2B * convert_CO2

create_images(co2b, xo2b, title1='CO2B (diffused)', title2='CO2B (non-diffused)')

