from model_stuff import my_data
from movie_zonal import create_images

KTN = my_data("cycletest5b")['km_zonalmean_eta']['KTN']

create_images(KTN, title1="KT (chem version)")
