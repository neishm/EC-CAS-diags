from matplotlib import pyplot as pl
#from pygeode.formats import netcdf
import xarray as xr

#experiments = {
#  'GEM-MACH': 'mn141_GEM-MACH_saprc_tropomass.nc',
#  'GEOS_v10': 'mn141_GEOS_v10_tropomass.nc',
#  'GEOS_v5': 'mn141_GEOS_v5_with_v10_strato_tropomass.nc',
#  'CAMS': 'mn141_CAMS_tropomass.nc',
#  'CCCma': 'mn141_CCCma_unscaled_tropomass.nc',
#  'Transcom': 'mn141_CH4-transcom_OH-input_tropomass.nc',
#}
#experiments = {
#  'GEM-MACH': 'mn141_GEM-MACH_saprc_totalmass.nc',
#  'GEOS_v10': 'mn141_GEOS_v10_totalmass.nc',
#  'GEOS_v5': 'mn141_GEOS_v5_with_v10_strato_totalmass.nc',
#  'CAMS': 'mn141_CAMS_totalmass.nc',
#  'CCCma': 'mn141_CCCma_unscaled_totalmass.nc',
#  'Transcom': 'mn141_CH4-transcom_OH-input_totalmass.nc',
#}
experiments = {
  'GEM-MACH (scaled)': 'mn141_GEM-MACH_saprc_scale0.65_tropomass.nc',
  'GEOS_v10 (scaled)': 'mn141_GEOS_v10_scale0.8_tropomass.nc',
  'GEOS_v5': 'mn141_GEOS_v5_with_v10_strato_tropomass.nc',
  'CAMS': 'mn141_CAMS_tropomass.nc',
  'CCCma (scaled)': 'mn141_CCCma_scale0.85_tropomass.nc',
  'Transcom': 'mn141_CH4-transcom_OH-input_tropomass.nc',
}

pl.figure('CO')
pl.figure('CH4')

for expname, filename in sorted(experiments.items()):
  #f = netcdf.open(filename)
  f = xr.open_dataset(filename)
  pl.figure('CO')
  pl.plot(f.time.values, f.TCO, label=expname)
  pl.xticks(rotation=45)
  pl.ylim(0.26,0.44)
  pl.title('CO tropo mass (Pg)')
  pl.tight_layout()
  pl.figure('CH4')
  pl.plot(f.time.values, f.CH4, label=expname)
  pl.xticks(rotation=45)
  pl.ylim(3.95,4.25)
  pl.title('CH4 tropo mass (Pg)')
  pl.tight_layout()

pl.figure('CO')
pl.legend(loc='best')
pl.figure('CH4')
pl.legend(loc='best')

pl.show()

