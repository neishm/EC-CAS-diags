from model_stuff import my_data
from movie_zonal import create_images

KTN = my_data("cycletest5b")['km_zonalmean_eta']['KTN']
KT  = my_data("cycletest5b")['pm_zonalmean_eta']['KT']

create_images(KTN, KT, title1="KT (chem version)", title2="KT (physics version)")
