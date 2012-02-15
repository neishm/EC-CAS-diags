from movie_zonal import create_images
import numpy as np
from model import cons_zonal as cons

contours = np.arange(374.66,375.14+0.02,0.02)
create_images (cons, None, contours = contours, palette='Paired')

