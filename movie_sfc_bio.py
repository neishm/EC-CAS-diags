# Generate a movie of the biogenic emissions from CarbonTracker
from movie_sfc import create_images

from carbontracker import fluxes
flux = fluxes.bio_flux_opt(month=1)

import numpy as np

#print flux.min(), flux.max()
#print flux.mean(), flux.stdev()

#contours = np.arange(-130e-6, 40e-6+5e-6, 5e-6)
#contours = np.arange(-40e-6, 20e-6+2e-6, 2e-6)
contours = np.arange(-40e-6, 15e-6+2e-6, 2e-6)

create_images(flux, contours, 'biogenic flux')
