def where_holes (experiment, outdir):
  from pygeode.formats import netcdf
  from os.path import exists
  from timeseries import get_sfc_mean

  co2 = get_sfc_mean(experiment,'CO2')

  holes = (co2 < 100)

  count = (holes * 1).sum('time')
  count.name = "hole_count"

  outfile = outdir+"/%s_hole_count.nc"%experiment.name
  if not exists(outfile):
    netcdf.save(outfile, count)

