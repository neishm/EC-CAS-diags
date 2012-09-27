
# Some standard diagnostics

from interfaces import experiment_name
outdir = experiment_name

# Timeseries
from timeseries import timeseries
timeseries (show=False, outdir=outdir)

# Zonal mean movies
from movie_zonal import movie_zonal
movie_zonal(gemfield = 'CO2', ctfield = 'co2', offset =    0, outdir=outdir)
movie_zonal(gemfield = 'CLA', ctfield = 'bio', offset = -100, outdir=outdir)

