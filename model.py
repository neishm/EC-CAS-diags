from pygeode.formats import netcdf as nc
from pygeode.formats.multifile import openall

from common import convert, fix_timeaxis

sfc = openall(files="2009*_co2_sfc.nc", format=nc)
sfc = fix_timeaxis(sfc)

# Surface fields
# Convert model output from kg C / ug air  to ppmV
co2 = sfc.CO2 * convert
co2.name = 'CO2'
co2_bg = sfc.CO2B * convert
co2_bg.name = 'CO2B'

# Eta 0.995
#eta995 = openall(files="2009*_co2_eta995.nc", format=nc)
#co2_eta995 = eta995.CO2 * convert
#co2_eta995.name = 'CO2'

# Eta 0.932
eta932 = openall(files="2009*_co2_eta932.nc", format=nc)
co2_eta932 = eta932.CO2 * convert
co2_eta932.name = 'CO2'

# Ocean field
co2_ocean = sfc.COC * convert
co2_ocean.name = 'COC'

# Zonal means
#zonal = openall(files="2009*_co2_zonalmean_eta.nc", format=nc)
zonal = openall(files="2009*_co2_zonalmean_gph.nc", format=nc)
zonal = fix_timeaxis(zonal)
co2_zonal = zonal.CO2 * convert
co2_zonal.name = 'CO2'
co2b_zonal = zonal.CO2B * convert
co2b_zonal.name = 'CO2B'
coc_zonal = zonal.COC * convert
coc_zonal.name = 'COC'
cla_zonal = zonal.CLA * convert
cla_zonal.name = 'CLA'
cbb_zonal = zonal.CBB * convert
cbb_zonal.name = 'CBB'
cff_zonal = zonal.CFF * convert
cff_zonal.name = 'CFF'
cons_zonal = zonal.CONS * convert
cons_zonal.name = 'CONS'

# Dynamics fields
dynamics = openall(files="2009*_dynamics.nc", format=nc)
dynamics = fix_timeaxis(dynamics)
gz = dynamics.GZ
hu = dynamics.HU

dyn_zonal = openall(files="2009*_dyn_zonalmean_eta.nc", format=nc)
gz_zonal = dyn_zonal.GZ
hu_zonal = dyn_zonal.HU
