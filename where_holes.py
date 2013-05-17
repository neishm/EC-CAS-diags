def where_holes (experiment, outdir):
  from pygeode.formats import netcdf
  from os.path import exists

  co2 = experiment.get_data('sfc','CO2')

  holes = (co2 < 100)

  count = (holes * 1).sum('time')
  count.name = "hole_count"

  outfile = outdir+"/%s_hole_count.nc"%experiment.name
  if not exists(outfile):
    netcdf.save(outfile, count)

